#!/usr/bin/env python3
"""pegahcarter/rebalance: py/rebalance.run(portfolio, i) unchanged, with its own py/portfolio.Portfolio class.

The program is a simulator only (its live-order lines are commented out and Exchange.create_order lacks `self`).
Its simulate.py calls rebalance.run every INTERVAL = 1 hour; the target is equal weight for every coin
(avg_weight = 1/len(coins)), so with COINS = ['PEARL', 'USDT'] it is 50/50 - the weights cannot be set without a
code change. Each hour a Portfolio is built from the real account (Portfolio.__init__ only reads its own price
file, so the object is filled in directly), rebalance.run trades on it, and the change in PEARL units is sent
to the price server as one order.

    python run_pegahcarter.py --port 8836
"""
import argparse
import math
import os
import sys

import numpy as np

import common

sys.path.insert(0, os.path.join(common.HERE, "downloads", "pegahcarter_rebalance"))
from py import rebalance  # noqa: E402
from py.portfolio import Portfolio  # noqa: E402

COINS = ["PEARL", "USDT"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8836)
    a = ap.parse_args()
    feed = common.Feed(a.port)
    runs, start = 0, feed.now
    while True:
        if (feed.now - start) % 60 == 0 and not feed.queue:
            runs += 1
            p = Portfolio.__new__(Portfolio)
            p.PORTFOLIO_START_VALUE, p.tx_count = None, 0
            p.dates = np.array([feed.time])
            p.hist_prices = np.array([[feed.price, 1.0]])
            p.units = np.array([feed.coins, feed.cash], dtype=float)
            p.start_units = p.units.copy()
            p.avg_weight = 1.0 / len(COINS)
            p.coins = {c: [{"cum_units": u}] for c, u in zip(COINS, p.units)}
            p = rebalance.run(p, 0)
            d = p.units[0] - p.start_units[0]
            qty = math.floor(abs(d) / common.STEP + 1e-9) * common.STEP
            if qty * feed.price >= common.MIN_COST:
                feed.market("BUY" if d > 0 else "SELL", qty, f"rebalance.run moved PEARL units by {d:+.4f}")
        if not feed.step():
            break
    acct = feed.finish()
    label = "equal weight PEARL 50 / USDT 50 (fixed by code), hourly, trade if > $10"
    common.report(f"pegahcarter/rebalance [{label}] {runs} runs", acct)
    feed.save(os.path.join(common.HERE, "log_pegahcarter.csv"), acct)
    common.sealed.record("pegahcarter/rebalance", label, "A", len(acct["trades"]), acct["value"], "ran",
                         "simulator only (live order code commented out; Exchange.create_order missing self); "
                         "weights are 1/number of coins, not settable; INTERVAL = 1 h from variables.py")


if __name__ == "__main__":
    main()
