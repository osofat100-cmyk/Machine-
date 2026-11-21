#!/usr/bin/env python3
"""
crypto_balancer 3.1.1 (pip crypto-balancer, kept unchanged in third_party/) on the sealed test, 1 Oct - 20 Nov 2026.

Its own Portfolio, SimpleBalancer and Executor make every decision, the same calls its main.py makes. Only the exchange
is a stand-in, like the DummyExchange its own tests use:
  - balances are price_server.py's account (the server keeps the money, this program never opens the test prices)
  - the rate is the minute's close (the real one uses the order-book middle)
  - an order it places is sent with the next request and filled at the next minute's close,
    cost 0.2% fee + max(0.5%, half a price step), the same rule as every other test
  - BigONE's real PEARL/USDT limits from CCXT: amount step 0.0001, smallest order 2 USDT. BigONE gives no smallest
    amount (None); the program's own CCXTExchange crashes comparing to None, so the stand-in uses 0 there.

Settings from the debate: targets PEARL 20 / USDT 80, threshold 15 (trade when PEARL leaves 5-35%), run once an hour.

    python3 test_balancer.py [--threshold 15] [--every 60] [--port 8766] [--out data/balancer_test.csv]
"""
import argparse
import csv
import http.client
import json
import math
import subprocess
import sys
import time

sys.path.insert(0, "third_party/crypto_balancer-3.1.1")
from crypto_balancer.executor import Executor  # noqa: E402
from crypto_balancer.portfolio import Portfolio  # noqa: E402
from crypto_balancer.simple_balancer import SimpleBalancer  # noqa: E402

PAIR = "PEARL/USDT"
TARGETS = {"PEARL": 20.0, "USDT": 80.0}
LIMITS = {PAIR: {"amount": {"min": 0.0, "max": None}, "cost": {"min": 2.0, "max": 500000.0},
                 "price": {"min": None, "max": None}}}
STEP = 0.0001


class SealedExchange:
    """Stand-in for crypto_balancer's CCXTExchange: same attributes, backed by the price server's account."""

    name = "sealed test (BigONE limits)"
    fee = 0.002

    def __init__(self, balances, close):
        self.balances = balances
        self.rates = {PAIR: close}
        self.pairs = [PAIR]
        self.limits = LIMITS
        self.pending = []

    def preprocess_order(self, order):
        if order.pair not in self.limits:
            return None
        lim = self.limits[order.pair]
        order.amount = math.floor(order.amount / STEP + 1e-9) * STEP
        order.price = round(order.price / STEP) * STEP
        if order.price == 0 or order.amount == 0:
            return None
        if order.amount < lim["amount"]["min"] or order.amount * order.price < lim["cost"]["min"]:
            return None
        order.type_ = "LIMIT"
        return order

    def execute_order(self, order):
        self.pending.append(order)
        return {"symbol": order.pair, "side": order.direction, "amount": order.amount, "price": order.price}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=15.0)
    ap.add_argument("--every", type=int, default=60, help="run the balancer every N minutes")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--out", default="data/balancer_test.csv")
    a = ap.parse_args()

    server = subprocess.Popen([sys.executable, "price_server.py", "--port", str(a.port)], stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", a.port, timeout=30)
                conn.connect()
                break
            except OSError:
                time.sleep(0.2)
        pending, decisions, runs, prev_ts, t0 = [], [], 0, None, time.time()
        while True:
            if pending:
                o = pending.pop(0)
                conn.request("GET", f"/next?order={o.direction}&qty={o.amount}")
            else:
                conn.request("GET", "/next?order=NONE")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                acct = m["account"]
                break
            assert prev_ts is None or m["ts"] == prev_ts + 1, "minutes must come one at a time, in order"
            prev_ts = m["ts"]
            if pending or m["ts"] % a.every:
                continue
            runs += 1
            ex = SealedExchange({"PEARL": m["coins"], "USDT": m["cash"]}, m["close"])
            portfolio = Portfolio.make_portfolio(TARGETS, ex, a.threshold)
            res = Executor(portfolio, ex, SimpleBalancer()).run(trade=True)
            if ex.pending:
                decisions.append((m["time"], round(portfolio.balances_pct["PEARL"], 2), str(ex.pending[0])))
            pending = ex.pending
    finally:
        server.terminate()

    hold, value = acct["holding"], acct["value"]
    print(f"crypto_balancer 3.1.1, PEARL {TARGETS['PEARL']:.0f} / USDT {TARGETS['USDT']:.0f}, threshold "
          f"{a.threshold:g}, run every {a.every} min: {runs:,} runs over {acct['minutes']:,} minutes "
          f"({time.time() - t0:.0f}s)")
    for (t, pct, order), fill in zip(decisions, acct["trades"]):
        print(f"  {t}  PEARL was {pct:5.2f}%  {order:<40}  filled {fill['time']} at {fill['price']:.4f}  "
              f"account ${fill['value']:,.2f}  ({fill['source']})")
    print(f"crypto_balancer: $1,000 -> ${value:,.2f} after {len(acct['trades'])} trades")
    print(f"just holding PEARL: $1,000 -> ${hold:,.2f}")
    print(f"20% PEARL bought once, never rebalanced: about $1,000 -> ${800 + 0.2 * hold:,.2f}")

    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["decided_utc", "pearl_pct_before", "order", "filled_utc", "price", "account_$", "cash", "coins",
                    "source"])
        for (t, pct, order), fill in zip(decisions, acct["trades"]):
            w.writerow([t, pct, order, fill["time"], fill["price"], round(fill["value"], 2),
                        round(fill["cash"], 2), round(fill["coins"], 4), fill["source"]])
        w.writerow(["end " + acct["last"], "", "", "", "", round(value, 2), round(acct["cash"], 2),
                    round(acct["coins"], 4), ""])
        w.writerow(["just holding", "", "", "", "", round(hold, 2), "", "", ""])
        w.writerow(["20/80 never rebalanced (about)", "", "", "", "", round(800 + 0.2 * hold, 2), "", "", ""])


if __name__ == "__main__":
    main()
