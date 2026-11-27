#!/usr/bin/env python3
"""556isback/anotherRebalancer, rebalancer.py unchanged: calpair() (PyPortfolioOpt min_volatility weights from
2,000 15-minute closes) and manager() (trade any weight gap > threshold and > $5, market orders).

rebalancer.py runs its live loop at import, so only its imports and function definitions are executed; this
program then does what its last lines do: iteratey() once at start, then schedule.every().day.at("00:00").
Stand-ins: `api.Exchange` (its ccxt connection; README says this file must be edited per exchange) backed by the
price server, with its own settings coins=['PEARL'] (USDT is hard-coded as base), reTry 3, threshold 0.005 (default);
`logbot` (Discord webhook logger) prints nothing.

    python run_anotherrebalancer.py --port 8834
"""
import argparse
import ast
import math
import os
import sys
import types

import pandas as pd

import common

SRC = os.path.join(common.HERE, "downloads", "556isback_anotherRebalancer", "rebalancer.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8834)
    a = ap.parse_args()
    feed = common.Feed(a.port)
    logs = []

    class Exchange:
        def __init__(self):
            self.coins = ["PEARL"]
            self.reTry = 3
            self.threshold = 0.005

        def load_markets(self):
            pass

        def fetchOhlcv(self):
            c = feed.candles(15, 2000)
            df = pd.DataFrame({"Timestamp": pd.to_datetime(c["ts"] * 60, unit="s"), "open": c["open"],
                               "high": c["high"], "low": c["low"], "close": c["close"], "volume": c["volume"]})
            return {"PEARL": df}

        def balances(self):
            return {"PEARL": feed.coins, "USDT": feed.cash}

        def pos(self, payload):
            size = math.floor(float(payload["size"]) / common.STEP + 1e-9) * common.STEP
            if size * feed.price < common.MIN_COST:
                return False
            feed.market(payload["side"], size, f"pos {payload}")
            return True

    sys.modules["api"] = types.SimpleNamespace(Exchange=Exchange)
    sys.modules["logbot"] = types.SimpleNamespace(logs=lambda message, log_to_discord=True: logs.append(message))

    tree = ast.parse(open(SRC).read())
    keep = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
    ns = {"__name__": "rebalancer"}
    exec(compile(ast.Module(body=keep, type_ignores=[]), SRC, "exec"), ns)
    ns["time"] = types.SimpleNamespace(sleep=lambda s: None, strftime=__import__("time").strftime,
                                       localtime=lambda *x: __import__("time").gmtime(feed.now * 60),
                                       time=lambda: feed.now * 60)

    runs, weights_seen = 0, []
    first = True
    while True:
        if first or (feed.now % 1440 == 0):
            first = False
            runs += 1
            weights, data3, api = ns["calpair"]()
            weights_seen.append((feed.time, dict(weights)))
            ns["manager"](weights, data3, api)
        if not feed.step():
            break
    acct = feed.finish()
    label = "min_volatility weights over PEARL (+USDT), threshold 0.005, daily 00:00"
    common.report(f"anotherRebalancer [{label}] {runs} runs", acct)
    print("weights:", weights_seen[:2], "...", weights_seen[-1:])
    feed.save(os.path.join(common.HERE, "log_anotherrebalancer.csv"), acct)
    w = sorted({round(v.get("PEARL", 0), 4) for _, v in weights_seen})
    common.sealed.record("556isback/anotherRebalancer", label, "A", len(acct["trades"]), acct["value"], "ran",
                         f"weights it chose for PEARL: {w[:5]}; with one coin, min_volatility puts 100% in it "
                         f"(weights sum to 1 among coins, USDT gets 1 - sum = 0), so it buys and holds. "
                         f"Live: no dry-run mode (api.pos sends real market orders); logbot needs a Discord URL")


if __name__ == "__main__":
    main()
