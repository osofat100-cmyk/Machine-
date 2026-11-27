#!/usr/bin/env python3
"""crypto-reflex 1.0.2 (PyPI) and hammertoe/crypto_balancer GitHub master (2019-03-19, cc5ed85), unchanged.

Their own Portfolio, SimpleBalancer and Executor (mode 'mid') decide; only the exchange is a stand-in shaped like
their CCXTExchange (rates as {'mid','high','low'}; no order book here, so all three are the minute's close; amounts
truncated to BigONE's 0.0001 step, smallest order 2 USDT). Run like the README's cron line: every 5 minutes,
a fresh exchange object each run. Orders are limit orders at mid in the real program; here they fill at the next
minute's close, same as the crypto_balancer 3.1.1 test.

    python run_reflex.py --pkg reflex|master --threshold 2.0 [--every 5] --port 8831
"""
import argparse
import math
import os
import sys

import common

PKG = {"reflex": ("downloads/pypi_crypto-reflex/crypto_reflex-1.0.2", "crypto_reflex", "crypto-reflex 1.0.2"),
       "master": ("downloads/hammertoe_crypto_balancer", "crypto_balancer", "hammertoe/crypto_balancer master cc5ed85")}
PAIR = "PEARL/USDT"
TARGETS = {"PEARL": 20.0, "USDT": 80.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", choices=PKG, required=True)
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--every", type=int, default=5)
    ap.add_argument("--port", type=int, required=True)
    a = ap.parse_args()
    path, mod, name = PKG[a.pkg]
    sys.path.insert(0, os.path.join(common.HERE, path))
    Executor = __import__(f"{mod}.executor", fromlist=["Executor"]).Executor
    Portfolio = __import__(f"{mod}.portfolio", fromlist=["Portfolio"]).Portfolio
    SimpleBalancer = __import__(f"{mod}.simple_balancer", fromlist=["SimpleBalancer"]).SimpleBalancer

    class StandIn:
        """Same attributes as their CCXTExchange."""
        name = "sealed test (BigONE limits)"
        fee = 0.002

        def __init__(self, feed):
            p = feed.price
            self.balances = {"PEARL": feed.coins, "USDT": feed.cash}
            self.rates = {PAIR: {"mid": p, "high": p, "low": p}}
            self.pairs = [PAIR]
            self.limits = {PAIR: {"amount": {"min": 0.0, "max": None}, "cost": {"min": common.MIN_COST, "max": None},
                                  "price": {"min": None, "max": None}}}
            self.feed = feed

        def preprocess_order(self, order):
            if order.pair not in self.limits:
                return None
            lim = self.limits[order.pair]
            order.amount = math.floor(order.amount / common.STEP + 1e-9) * common.STEP
            order.price = round(order.price / common.STEP) * common.STEP
            if order.price == 0 or order.amount == 0:
                return None
            if order.amount < lim["amount"]["min"] or order.amount * order.price < lim["cost"]["min"]:
                return None
            order.type_ = "LIMIT"
            return order

        def execute_order(self, order):
            self.feed.market(order.direction, order.amount, str(order))
            return {"symbol": order.pair, "side": order.direction, "amount": order.amount, "price": order.price}

    feed, runs = common.Feed(a.port), 0
    while True:
        if feed.now % a.every == 0 and not feed.queue:
            runs += 1
            ex = StandIn(feed)
            portfolio = Portfolio.make_portfolio(TARGETS, ex, a.threshold, "USDT")
            Executor(portfolio, ex, SimpleBalancer()).run(trade=True, mode="mid")
        if not feed.step():
            break
    acct = feed.finish()
    label = f"PEARL 20 / USDT 80, threshold {a.threshold:g}, every {a.every} min, mode mid"
    common.report(f"{name} [{label}] {runs} runs", acct)
    out = os.path.join(common.HERE, f"log_{a.pkg}_t{a.threshold:g}.csv")
    feed.save(out, acct)
    src = "README example" if a.threshold == 2.0 else ("config.ini.example" if a.threshold == 0.2 else "chosen")
    common.sealed.record(name, label, "A", len(acct["trades"]), acct["value"], "ran",
                         f"threshold from {src}; every 5 min from README cron; limit-at-mid orders filled at next "
                         f"close; live use crashes on BigONE (None min amount, same as 3.1.1)")


if __name__ == "__main__":
    main()
