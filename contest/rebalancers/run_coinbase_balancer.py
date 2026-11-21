#!/usr/bin/env python3
"""sandybradley/Coinbase-Balancer, coinbase_balancer.py unchanged except what its own README says to edit
(keys and `lastweights`). Every top-level statement runs except its last four (iteratey(); BlockingScheduler();
add_job; scheduler.start()); this program then does what they do: iteratey() at start and every hour.

The script routes everything through BTC as the hub (pairs ASSET-BTC, prices in BTC). Here the hub is USDT, so
the stand-in `cbpro` lists PEARL-BTC where "BTC" means USDT: lastweights = {"PEARL": 0.2, "BTC": 0.8}.
Its orders are limit orders 0.7% away from the price, cancelled at the next hourly run; the stand-in rests them
and fills one when a minute's low/high touches it (at the next minute's close). Product sizes like Coinbase
PEARL: base_min_size 0.01, quote_increment 0.0001. BigONE's smallest order (2 USDT) refuses smaller ones.

    python run_coinbase_balancer.py --port 8835
"""
import argparse
import ast
import os
import sys
import types

import common

SRC = os.path.join(common.HERE, "downloads", "sandybradley_Coinbase-Balancer", "coinbase_balancer.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8835)
    a = ap.parse_args()
    feed = common.Feed(a.port)
    refused = []

    class PublicClient:
        def get_product_ticker(self, product_id):
            assert product_id == "PEARL-BTC", product_id
            return {"price": str(feed.price)}

        def get_products(self):
            return [{"id": "PEARL-BTC", "base_currency": "PEARL", "quote_currency": "BTC",
                     "base_min_size": "0.01", "quote_increment": "0.0001"}]

    class AuthenticatedClient:
        def __init__(self, *args):
            pass

        def get_accounts(self):
            return [{"currency": "PEARL", "balance": str(feed.coins)}, {"currency": "BTC", "balance": str(feed.cash)}]

        def get_orders(self):
            return [{"product_id": "PEARL-BTC", "id": lid} for lid in feed.limits]

        def cancel_order(self, order_id):
            feed.cancel(order_id)
            return order_id

        def place_limit_order(self, product_id, side, price, size):
            if float(size) * float(price) < common.MIN_COST:
                refused.append((feed.time, side, size, price))
                return {"message": "size too small"}
            return {"id": feed.limit(side, float(size), float(price), f"{side} {size} @ {price}")}

    sys.modules["cbpro"] = types.SimpleNamespace(PublicClient=PublicClient, AuthenticatedClient=AuthenticatedClient)
    tree = ast.parse(open(SRC).read())
    body = tree.body[:-4]
    tail = [ast.unparse(n) for n in tree.body[-4:]]
    assert tail == ["iteratey()", "scheduler = BlockingScheduler()",
                    "scheduler.add_job(iteratey, 'interval', hours=1)", "scheduler.start()"], tail
    ns = {"__name__": "coinbase_balancer"}
    keep = [n for n in body if not (isinstance(n, ast.ImportFrom) and n.module.startswith("apscheduler"))]
    exec(compile(ast.Module(body=keep, type_ignores=[]), SRC, "exec"), ns)
    ns["lastweights"] = {"PEARL": 0.2, "BTC": 0.8}
    ns["print"] = lambda *x, **k: None

    runs, start = 0, feed.now
    while True:
        if (feed.now - start) % 60 == 0:
            runs += 1
            ns["iteratey"]()
        if not feed.step():
            break
    acct = feed.finish()
    label = "PEARL 0.2 / hub 0.8 (hub BTC = USDT), hourly, limit orders 0.7% away"
    common.report(f"Coinbase-Balancer [{label}] {runs} runs", acct)
    feed.save(os.path.join(common.HERE, "log_coinbase_balancer.csv"), acct)
    common.sealed.record("sandybradley/Coinbase-Balancer", label, "A", len(acct["trades"]), acct["value"], "ran",
                         f"hub BTC relabelled as USDT; its threshold 0.001 is in hub units (0.001 USDT here) so it "
                         f"re-quotes every hour; {len(refused)} orders under 2 USDT refused. Live: written for the "
                         f"retired Coinbase Pro API (cbpro), BTC-hub only")


if __name__ == "__main__":
    main()
