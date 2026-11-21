#!/usr/bin/env python3
"""
The PEARL strategy (normal mode + spike mode) and a second-by-second tester.
The live bot (pearl_bot.py) uses this same code, so tests and live behave the same.

NORMAL MODE
  Holding USDC:  buy when price rises RISE% above its lowest point.
  Holding PEARL: once up TARGET% (1.6%), sell when it drops TRAIL% from its high,
                 never below +FLOOR% (1.5%). Before that, sell if it drops STOP% from its high.

SPIKE MODE (within SPIKE_SECS seconds)
  Drop spike (falls DROP_SPIKE%), holding USDC: buy the hole, sell at +BOUNCE% or
                             -BOUNCE_STOP%, or after BOUNCE_SECS seconds.
  Rise spike (rises RISE_SPIKE%), holding PEARL: sell into the spike.
  Rise spike, holding USDC:  don't buy for 10 minutes.

Test:
    python3 strategy.py data/coinbase_trades.csv
    python3 strategy.py data/gate_trades.csv --rise 999     # spike mode only
"""
import argparse
from collections import deque

COST = 0.7  # % per side: 0.2% fee + 0.5% half the buy/sell gap  (= 1.4% round trip)


class Strategy:
    def __init__(self, rise=7.0, trail=3.0, stop=5.0, target=1.6, floor=1.5,
                 rise_spike=2.0, drop_spike=5.0, spike_secs=30,
                 bounce=2.0, bounce_stop=10.0, bounce_secs=1800,
                 spikes_on=True):
        self.p = dict(rise=rise, trail=trail, stop=stop, target=target, floor=floor,
                      rise_spike=rise_spike, drop_spike=drop_spike,
                      spike_secs=spike_secs, bounce=bounce, bounce_stop=bounce_stop,
                      bounce_secs=bounce_secs, spikes_on=spikes_on)
        self.mode = "USDC"
        self.kind = None          # "normal" or "bounce" while holding PEARL
        self.low = None
        self.high = 0.0
        self.buy_price = 0.0
        self.buy_time = 0.0
        self.no_buy_until = 0.0
        self.window = deque()     # recent (time, price) for spike detection

    # ---------- the lines the bot is waiting for ----------
    def sell_line(self):
        p = self.p
        if self.kind == "bounce":
            return self.buy_price * (1 - p["bounce_stop"] / 100)
        if self.high >= self.buy_price * (1 + p["target"] / 100):
            return max(self.buy_price * (1 + p["floor"] / 100), self.high * (1 - p["trail"] / 100))
        return self.high * (1 - p["stop"] / 100)

    def buy_line(self):
        return self.low * (1 + self.p["rise"] / 100)

    # ---------- one new price ----------
    def update(self, t, price):
        """Returns (action, reason) - action is 'BUY', 'SELL' or None."""
        p = self.p
        self.window.append((t, price))
        while self.window[0][0] < t - p["spike_secs"]:
            self.window.popleft()
        lo = min(q for _, q in self.window)
        hi = max(q for _, q in self.window)
        up_spike = p["spikes_on"] and price >= lo * (1 + p["rise_spike"] / 100)
        down_spike = p["spikes_on"] and price <= hi * (1 - p["drop_spike"] / 100)

        if self.mode == "USDC":
            self.low = price if self.low is None else min(self.low, price)
            if up_spike:
                self.no_buy_until = t + 600
                return None, ""
            if down_spike:
                return self._buy(t, price, "bounce"), f"drop spike {p['drop_spike']}% in {p['spike_secs']}s"
            if t >= self.no_buy_until and price >= self.buy_line():
                return self._buy(t, price, "normal"), f"rose {p['rise']}% from low"
            return None, ""

        self.high = max(self.high, price)
        if up_spike:
            return self._sell(price), "sold into rise spike"
        if self.kind == "bounce":
            if price >= self.buy_price * (1 + p["bounce"] / 100):
                return self._sell(price), f"bounce +{p['bounce']}%"
            if price <= self.sell_line():
                return self._sell(price), f"bounce failed -{p['bounce_stop']}%"
            if t - self.buy_time > p["bounce_secs"]:
                return self._sell(price), "bounce timed out"
            return None, ""
        if down_spike:  # drop spikes usually bounce - don't sell into the hole
            return None, ""
        if price <= self.sell_line():
            locked = self.high >= self.buy_price * (1 + p["target"] / 100)
            return self._sell(price), ("dropped from high, profit locked" if locked else "dropped from high")
        return None, ""

    def _buy(self, t, price, kind):
        self.mode, self.kind = "PEARL", kind
        self.buy_price, self.buy_time, self.high = price, t, price
        return "BUY"

    def _sell(self, price):
        self.mode, self.kind, self.low = "USDC", None, price
        return "SELL"


def run(series, cost=COST, **params):
    """Replay prices. Trades fill at the NEXT price, paying `cost` % each side.
    Returns dict with final $, trades, wins, worst drop, and per-reason counts."""
    s = Strategy(**params)
    cash, coins, spent = 1000.0, 0.0, 0.0
    trades = wins = 0
    peak, worst = 1000.0, 0.0
    reasons = {}
    pending = None
    for t, price in series:
        if pending:  # fill the order decided on the previous price
            act, why = pending
            if act == "BUY":
                spent, coins, cash = cash, cash / (price * (1 + cost / 100)), 0.0
            else:
                cash, coins = coins * price * (1 - cost / 100), 0.0
                trades += 1
                win = cash > spent
                wins += win
                r = reasons.setdefault(why, [0, 0])
                r[0] += 1
                r[1] += win
            pending = None
        act, why = s.update(t, price)
        if act:
            pending = (act, why)
        value = cash + coins * price
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak * 100)
    final = cash + coins * series[-1][1] * (1 - cost / 100)
    return {"final": final, "trades": trades, "wins": wins, "worst": worst, "reasons": reasons}


def main():
    from patterns import load
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    for name, default in [("rise", 7.0), ("trail", 3.0), ("stop", 5.0), ("rise_spike", 2.0),
                          ("drop_spike", 5.0), ("spike_secs", 30), ("bounce", 2.0),
                          ("bounce_stop", 10.0), ("bounce_secs", 1800)]:
        ap.add_argument("--" + name.replace("_", "-"), type=type(default), default=default)
    ap.add_argument("--no-spikes", action="store_true")
    a = ap.parse_args()
    series = load(a.file)
    params = {k: v for k, v in vars(a).items() if k not in ("file", "no_spikes")}
    params["spikes_on"] = not a.no_spikes
    r = run(series, **params)
    hold = 1000 * series[-1][1] / series[0][1] * (1 - COST / 100) ** 2
    print(f"$1000 -> ${r['final']:.0f}   (just holding: ${hold:.0f})   trades {r['trades']}  "
          f"wins {r['wins']}  worst drop {r['worst']:.0f}%")
    for why, (n, w) in sorted(r["reasons"].items(), key=lambda x: -x[1][0]):
        print(f"   {why:<35} {n:>4} sells, {w} wins")


if __name__ == "__main__":
    main()
