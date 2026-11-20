#!/usr/bin/env python3
"""
The "buy the crash, sell the pump" rule as a landscape of settings, plus the
walk-forward test (pick the setting from the past only, trade the next week).

  BUY  when PEARL fell BUY% or more in 4 hours and is at its 4-hour low (within 0.23%)
  SELL when it is SELL% or more above its 4-hour low and near its 4-hour high (within 1.8%)

    python3 landscape.py fine          # 0.1% steps over the active area + 0.02% zoom on the hill
    python3 landscape.py walk          # walk-forward test, re-picking the setting every week
"""
import bisect
import json
import sys

import numpy as np
import pandas as pd

COST = 0.007        # 0.7% per side = 1.4% round trip
AT_LOW, NEAR_HIGH = 0.23, 1.8


class Market:
    """Minute prices plus the three numbers the rule looks at, computed once."""

    def __init__(self, path="data/PEARL-USDT_min1.csv", warmup=10080, df=None):
        if df is None:
            df = pd.read_csv(path, parse_dates=["time"]).set_index("time")
        c, h, l = df["close"], df["high"], df["low"]
        up_low = (c / l.rolling(240).min() - 1) * 100
        dn_high = (1 - c / h.rolling(240).max()) * 100
        chg4 = (c / c.shift(240) - 1) * 100
        keep = np.arange(len(df)) >= warmup          # same start as earlier tests (Jul 2)
        self.time = df.index[keep]
        self.close = c.values[keep]
        self.up_low = up_low.values[keep]
        self.dn_high = dn_high.values[keep]
        self.chg4 = chg4.values[keep]
        self.n = len(self.close)
        self.at_low = self.up_low <= AT_LOW
        self.near_high = self.dn_high <= NEAR_HIGH
        last = np.arange(self.n) < self.n - 1
        # sort once so any threshold's signal list is a quick lookup
        self._buy_order = np.flatnonzero(self.at_low & last)
        self._sell_order = np.flatnonzero(self.near_high & last)

    def buys(self, pct):
        i = self._buy_order
        return i[self.chg4[i] <= -pct].tolist()

    def sells(self, pct):
        i = self._sell_order
        return i[self.up_low[i] >= pct].tolist()

    def run(self, bi, si, end=None):
        """$1000 traded on minutes before `end`. Returns (final $, trades)."""
        end = self.n if end is None else end
        c = self.close
        cash, pos, trades = 1000.0, 0, 0
        while True:
            k = bisect.bisect_left(bi, pos)
            if k == len(bi) or bi[k] >= end - 1:
                return cash, trades
            i = bi[k]
            coins = cash / (c[i + 1] * (1 + COST))
            k = bisect.bisect_left(si, i + 1)
            if k == len(si) or si[k] >= end - 1:
                return coins * c[end - 1] * (1 - COST), trades + 1
            j = si[k]
            cash, pos, trades = coins * c[j + 1] * (1 - COST), j + 1, trades + 1

    def grid(self, buy_steps, sell_steps, end=None):
        B = [self.buys(x) for x in buy_steps]
        S = [self.sells(x) for x in sell_steps]
        res = [[self.run(b, s, end) for b in B] for s in S]   # rows = sell, cols = buy
        money = np.array([[m for m, _ in r] for r in res])
        trades = np.array([[t for _, t in r] for r in res])
        return money, trades


def smooth(a, sigma):
    """Gaussian blur over the grid; sigma in grid steps; edges repeat."""
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, r, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, p)


def best_setting(m, end, buy_steps, sell_steps, sigma_pct=1.0):
    """Top of the smoothed hill using only minutes before `end`."""
    money, trades = m.grid(buy_steps, sell_steps, end)
    step = buy_steps[1] - buy_steps[0]
    sm = smooth(money, sigma_pct / step)
    i, j = np.unravel_index(sm.argmax(), sm.shape)
    return buy_steps[j], sell_steps[i], sm[i, j]


def walk_forward(m, every_days=7, first_days=28, window_days=None, step=0.5):
    """Each week: pick the setting from past data only, trade the next week with it."""
    buy_steps = np.round(np.arange(step, 26.0 + 1e-9, step), 2)
    sell_steps = np.round(np.arange(step, 45.0 + 1e-9, step), 2)
    per_day = 1440
    start = first_days * per_day
    c, cash, coins, picks, daily = m.close, 1000.0, 0.0, [], []
    t = start
    while t < m.n - 1:
        lo = 0 if window_days is None else max(0, t - window_days * per_day)
        sub = Market.__new__(Market)                       # view of the past only
        for k in ("close", "up_low", "dn_high", "chg4", "at_low", "near_high"):
            setattr(sub, k, getattr(m, k)[lo:t])
        sub.n = t - lo
        sub.time = m.time[lo:t]
        last = np.arange(sub.n) < sub.n - 1
        sub._buy_order = np.flatnonzero(sub.at_low & last)
        sub._sell_order = np.flatnonzero(sub.near_high & last)
        b, s, score = best_setting(sub, None, buy_steps, sell_steps)
        stop = min(m.n - 1, t + every_days * per_day)
        picks.append((m.time[t], b, s, round(score)))
        for i in range(t, stop):                            # trade the next week, minute by minute
            if coins == 0 and m.at_low[i] and m.chg4[i] <= -b:
                coins, cash = cash / (c[i + 1] * (1 + COST)), 0.0
            elif coins > 0 and m.near_high[i] and m.up_low[i] >= s:
                cash, coins = coins * c[i + 1] * (1 - COST), 0.0
            if (i - start) % per_day == 0:
                daily.append((m.time[i], cash + coins * c[i]))
        t = stop
    final = cash + coins * c[-1] * (1 - COST)
    hold = 1000 * c[-1] / c[start] * (1 - COST) ** 2
    daily.append((m.time[-1], final))
    return final, hold, picks, daily


def fixed_curve(m, b, s, start, per_day=1440):
    """Daily account value for one fixed setting, starting with $1000 at minute `start`."""
    c, cash, coins, daily = m.close, 1000.0, 0.0, []
    for i in range(start, m.n - 1):
        if coins == 0 and m.at_low[i] and m.chg4[i] <= -b:
            coins, cash = cash / (c[i + 1] * (1 + COST)), 0.0
        elif coins > 0 and m.near_high[i] and m.up_low[i] >= s:
            cash, coins = coins * c[i + 1] * (1 - COST), 0.0
        if (i - start) % per_day == 0:
            daily.append((m.time[i], cash + coins * c[i]))
    daily.append((m.time[-1], cash + coins * c[-1] * (1 - COST)))
    return daily


def main():
    m = Market()
    what = sys.argv[1] if len(sys.argv) > 1 else "walk"
    print(f"{m.time[0]:%b %d} -> {m.time[-1]:%b %d}: {m.n} minutes")
    if what == "fine":
        out = {}
        for name, bs, ss in (("fine", np.round(np.arange(0.1, 26.0001, 0.1), 2), np.round(np.arange(0.1, 45.0001, 0.1), 2)),
                             ("zoom", np.round(np.arange(8, 12.0001, 0.02), 2), np.round(np.arange(30, 38.0001, 0.02), 2))):
            money, trades = m.grid(bs, ss)
            sm = smooth(money, 1.0 / (bs[1] - bs[0]))
            i, j = np.unravel_index(money.argmax(), money.shape)
            k, l = np.unravel_index(sm.argmax(), sm.shape)
            print(f"{name}: {money.size:,} settings | best exact: buy {bs[j]} sell {ss[i]} -> ${money[i, j]:,.0f} "
                  f"({trades[i, j]} trades) | top of smoothed hill: buy {bs[l]} sell {ss[k]} -> ${sm[k, l]:,.0f}")
            out[name] = {"buy": bs.tolist(), "sell": ss.tolist(), "raw": np.round(money).astype(int).tolist(),
                         "smooth": np.round(sm).astype(int).tolist(), "trades": trades.astype(int).tolist()}
        with open("data/landscape_fine.json", "w") as f:
            json.dump(out, f, separators=(",", ":"))
    else:
        for window in (None, 60, 30):
            final, hold, picks, _ = walk_forward(m, window_days=window)
            label = "all past data" if window is None else f"last {window} days"
            print(f"\nWalk-forward, re-pick weekly from {label}: $1000 -> ${final:,.0f}   "
                  f"(just holding over the same weeks: ${hold:,.0f})")
            print("  week of    buy%  sell%")
            for t, b, s, _ in picks:
                print(f"  {t:%b %d}   {b:>5}  {s:>5}")


if __name__ == "__main__":
    main()
