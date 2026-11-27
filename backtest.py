#!/usr/bin/env python3
"""
Test simple trading rules on past PEARL prices, WITH trading costs included.

    python3 fetch_history.py --pair PEARL-USDT --period hour1 --days 150
    python3 backtest.py                                  # hourly PEARL-USDT
    python3 backtest.py --file data/PEARL-USDT_min1.csv --resample 15

How it stays honest:
  * A rule decides at the close of a candle and trades at the NEXT candle's open
    (it never sees the future).
  * Every buy and sell pays the exchange fee plus half the bid/ask spread.
  * Settings are picked on the first part of the data (TRAIN) and then judged on
    the last part (TEST), which the rule has never seen.

Each rule returns, for every candle, 1 (hold PEARL) or 0 (hold dollars).
"""
import argparse
import csv
from itertools import product


# ---------- data ----------
def load(path, resample=1):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append([r["time"], float(r["open"]), float(r["high"]), float(r["low"]),
                         float(r["close"]), float(r["volume"])])
    if resample > 1:  # merge N small candles into one bigger candle
        out = []
        for i in range(0, len(rows) - resample + 1, resample):
            c = rows[i:i + resample]
            out.append([c[0][0], c[0][1], max(x[2] for x in c), min(x[3] for x in c),
                        c[-1][4], sum(x[5] for x in c)])
        rows = out
    return rows


def sma(values, n):
    """Simple moving average; None until there are n values."""
    out, s = [None] * len(values), 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


# ---------- rules ----------
def rule_trend(c, fast, slow):
    """TREND: hold PEARL while the fast average is above the slow average."""
    close = [x[4] for x in c]
    f, s = sma(close, fast), sma(close, slow)
    return [1 if s[i] is not None and f[i] > s[i] else 0 for i in range(len(c))]


def rule_breakout(c, enter_n, exit_n):
    """BREAKOUT: buy when price closes above the highest high of the last
    enter_n candles; sell when it closes below the lowest low of the last exit_n."""
    pos, out = 0, []
    for i in range(len(c)):
        if i >= enter_n and pos == 0 and c[i][4] > max(x[2] for x in c[i - enter_n:i]):
            pos = 1
        elif i >= exit_n and pos == 1 and c[i][4] < min(x[3] for x in c[i - exit_n:i]):
            pos = 0
        out.append(pos)
    return out


def rule_dip(c, n, drop_pct, stop_pct):
    """BUY THE DIP: buy when price falls drop_pct% below its n-candle average;
    sell when it gets back to the average, or cut the loss at stop_pct%."""
    close = [x[4] for x in c]
    avg = sma(close, n)
    pos, entry, out = 0, 0.0, []
    for i in range(len(c)):
        if avg[i] is not None:
            if pos == 0 and close[i] < avg[i] * (1 - drop_pct / 100):
                pos, entry = 1, close[i]
            elif pos == 1 and (close[i] >= avg[i] or close[i] < entry * (1 - stop_pct / 100)):
                pos = 0
        out.append(pos)
    return out


def rule_swing(c, rise_pct, drop_pct):
    """SWING: buy once price has risen rise_pct% from its lowest point;
    sell once price has fallen drop_pct% from its highest point since buying."""
    pos, low, high, out = 0, c[0][4], c[0][4], []
    for x in c:
        p = x[4]
        if pos == 0:
            low = min(low, p)
            if p >= low * (1 + rise_pct / 100):
                pos, high = 1, p
        else:
            high = max(high, p)
            if p <= high * (1 - drop_pct / 100):
                pos, low = 0, p
        out.append(pos)
    return out


def rule_user(c, rise_pct, trail_pct, stop_pct, target_pct=1.6, floor_pct=1.5):
    """USER RULE (see ALGORITHM.md).
    Holding dollars: buy once price is rise_pct% above its lowest point.
    Holding PEARL:   once price has reached +target_pct% over the buy price, sell when it
                     falls trail_pct% from its highest point, never lower than +floor_pct%.
                     Before that, sell if it falls stop_pct% from its highest point."""
    pos, low, high, buy, out = 0, c[0][4], 0.0, 0.0, []
    for x in c:
        p = x[4]
        if pos == 0:
            low = min(low, p)
            if p >= low * (1 + rise_pct / 100):
                pos, buy, high = 1, p, p
        else:
            high = max(high, p)
            if high >= buy * (1 + target_pct / 100):
                sell_line = max(buy * (1 + floor_pct / 100), high * (1 - trail_pct / 100))
            else:
                sell_line = high * (1 - stop_pct / 100)
            if p <= sell_line:
                pos, low = 0, p
        out.append(pos)
    return out


RULES = {
    "user":     (rule_user,     {"rise_pct": [1, 2, 3, 5, 7, 10],
                                 "trail_pct": [0.5, 1, 2, 3, 5],
                                 "stop_pct": [1, 2, 3, 5, 7, 10]}),
    "swing":    (rule_swing,    {"rise_pct": [0.5, 1, 1.5, 2, 3, 4, 5, 7, 10],
                                 "drop_pct": [0.5, 1, 1.5, 2, 3, 4, 5, 7, 10]}),
    "trend":    (rule_trend,    {"fast": [6, 12, 24], "slow": [24, 48, 96, 168]}),
    "breakout": (rule_breakout, {"enter_n": [24, 48, 96], "exit_n": [12, 24, 48]}),
    "dip":      (rule_dip,      {"n": [12, 24, 48], "drop_pct": [3, 5, 8], "stop_pct": [8, 15]}),
}


# ---------- simulator ----------
def simulate(c, signal, fee_pct, half_spread_pct, start=0, end=None):
    """Start with $1000. Returns (final $, number of round trips, win rate, worst drop %)."""
    end = len(c) if end is None else end
    cost = (fee_pct + half_spread_pct) / 100
    cash, coins, buy_cost = 1000.0, 0.0, 0.0
    trades = wins = 0
    peak, worst = 1000.0, 0.0
    for i in range(start, end - 1):
        price = c[i + 1][1]  # next candle's open
        if signal[i] == 1 and coins == 0:
            buy_cost = cash
            coins, cash = cash * (1 - cost) / price, 0.0
        elif signal[i] == 0 and coins > 0:
            cash, coins = coins * price * (1 - cost), 0.0
            trades += 1
            wins += cash > buy_cost
        value = cash + coins * c[i + 1][4]
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak * 100)
    final = cash + coins * c[end - 1][4] * (1 - cost)  # value if we sold at the end
    return final, trades, (wins / trades * 100 if trades else 0.0), worst


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="data/PEARL-USDT_hour1.csv")
    ap.add_argument("--resample", type=int, default=1, help="merge N candles into one")
    ap.add_argument("--fee", type=float, default=0.2, help="exchange fee %% per trade")
    ap.add_argument("--half-spread", type=float, default=0.35,
                    help="half the bid/ask gap in %% (cost of a market order). Use 0 for ideal limit orders")
    ap.add_argument("--train", type=float, default=0.6, help="share of data used to pick settings")
    args = ap.parse_args()

    c = load(args.file, args.resample)
    split = int(len(c) * args.train)
    print(f"{args.file}: {len(c)} candles  {c[0][0]} -> {c[-1][0]}")
    print(f"TRAIN = first {split} candles (to {c[split][0]}), TEST = the rest")
    print(f"cost per trade: {args.fee}% fee + {args.half_spread}% half-spread "
          f"= {2 * (args.fee + args.half_spread):.2f}% per round trip\n")

    always = [1] * len(c)
    hold_tr = simulate(c, always, args.fee, args.half_spread, 0, split)[0] / 10 - 100
    hold_te, _, _, hold_worst = simulate(c, always, args.fee, args.half_spread, split, len(c))
    print(f"{'rule':<10}{'best settings (picked on TRAIN)':<42}{'TRAIN %':>9}{'TEST %':>9}"
          f"{'trades':>8}{'win %':>7}{'worst drop %':>14}")
    print(f"{'hold':<10}{'just buy and hold PEARL':<42}{hold_tr:>9.1f}{hold_te / 10 - 100:>9.1f}"
          f"{'-':>8}{'-':>7}{hold_worst:>14.1f}")

    for name, (fn, grid) in RULES.items():
        best = None
        for combo in product(*grid.values()):
            params = dict(zip(grid.keys(), combo))
            if name == "trend" and params["fast"] >= params["slow"]:
                continue
            sig = fn(c, **params)
            final, *_ = simulate(c, sig, args.fee, args.half_spread, 0, split)
            if best is None or final > best[0]:
                best = (final, params, sig)
        tr_final, params, sig = best
        te_final, trades, winrate, worst = simulate(c, sig, args.fee, args.half_spread, split, len(c))
        ptxt = ", ".join(f"{k}={v}" for k, v in params.items())
        print(f"{name:<10}{ptxt:<42}{(tr_final / 10 - 100):>9.1f}{(te_final / 10 - 100):>9.1f}"
              f"{trades:>8}{winrate:>7.0f}{worst:>14.1f}")

    print("\nTEST % is the number that matters: it is profit on data the rule never saw.")
    print("Compare it with 'hold'. A rule is only useful if it beats holding or loses much less in drops.")


if __name__ == "__main__":
    main()
