#!/usr/bin/env python3
"""
Learn, then freeze: find the best buy/sell setting from the data up to a month's end, then
trade with that one setting, never changing it, from that day to the last day.

  Learn from Jun 25 - Jul 31, trade Aug 1 - Nov 20
  Learn from Jun 25 - Aug 31, trade Sep 1 - Nov 20
  Learn from Jun 25 - Sep 30, trade Oct 1 - Nov 20
  Learn from Jun 25 - Oct 31, trade Nov 1 - Nov 20

Best setting = top of the smoothed 0.1% landscape (same as the robots).
Each trading period starts with $1,000 and is compared with just holding.

    python3 frozen.py
"""
import numpy as np

from landscape import COST, Market
from robots import Account, HillTop, all_events, grids

CUTOFFS = ["2026-08-01", "2026-09-01", "2026-10-01", "2026-11-01"]


def landscape_at(m, ev, nb, ns, end):
    """Every setting's money using only minutes before `end`."""
    t, sid, kind, amt = ev
    cash = np.full(nb * ns, 1000.0)
    coins = np.zeros(nb * ns)
    holding = np.zeros(nb * ns, bool)
    last = np.searchsorted(t, end - 1)            # events with t <= end - 2
    for e in range(last):
        s = sid[e]
        if kind[e] == 1:
            coins[s], holding[s] = amt[e], True
        else:
            cash[s], holding[s] = amt[e], False
    return np.where(holding, coins * m.close[end - 1] * (1 - COST), cash).reshape(ns, nb)


def trade_fixed(m, start, b, s):
    a = Account()
    for k in range(start, m.n - 1):
        a.step(m, k, b, s)
    return a.value(m.close[-1]), a.buys


def main():
    m = Market(warmup=240)
    buy, sell = grids(m)
    ev = all_events(m, buy, sell)
    top = HillTop(len(buy), len(sell))
    print(f"{'AI':<6}{'learns from':<18}{'keeps forever':>16}{'trades':>16}{'ends with':>11}{'gain/loss':>11}{'holding':>10}")
    for n, day in enumerate(CUTOFFS, 1):
        end = int(np.searchsorted(m.time.values, np.datetime64(day + "T00:00")))
        V = landscape_at(m, ev, len(buy), len(sell), end).astype(np.float32)
        _, (i, j) = top(V)
        b, s = float(buy[j]), float(sell[i])
        final, buys = trade_fixed(m, end, b, s)
        hold = 1000 * m.close[-1] / m.close[end] * (1 - COST) ** 2
        learn = f"{m.time[0]:%b %d} - {m.time[end - 1]:%b %d}"
        period = f"{m.time[end]:%b %d} - {m.time[-1]:%b %d}"
        print(f"{n:<6}{learn:<18}{f'{b}% / {s}%':>16}{period:>16}{f'${final:,.0f}':>11}"
              f"{f'{final - 1000:+,.0f}':>11}{f'${hold:,.0f}':>10}   ({buys} buys)")

if __name__ == "__main__":
    main()
