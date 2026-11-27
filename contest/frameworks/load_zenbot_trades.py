"""Stand-in for `zenbot backfill`: put PEARL minutes into Zenbot's MongoDB trades collection.

Zenbot works on trades, not candles. Each minute (history from 26 Jun + the sealed minutes exported through the
price server) becomes 4 trades: open at :00, then low and high (up candle) or high and low (down candle) at :15 and
:30, close at :45, each a quarter of the minute's volume. Selector poloniex.PEARL-USDT: Zenbot's shipped poloniex
products list has a PEARL-USDT entry (min total 1, increment 1e-8), so the shipped code accepts it unchanged.

    venv_jesse/bin/python load_zenbot_trades.py
"""
import os
import sys

import pandas as pd
import pymongo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_jesse  # noqa: E402  (same continuous, day-aligned minutes)

SELECTOR = "poloniex.PEARL-USDT"


def main():
    hist, test = run_jesse.load()
    db = pymongo.MongoClient("127.0.0.1", 27017)["zenbot4"]
    db.trades.delete_many({"selector": SELECTOR})
    docs, n = [], 0
    for arr in (hist, test):
        for ts, o, c, h, l, v in arr:
            size = max(v / 4.0, 1e-6)
            seq = (o, l, h, c) if c >= o else (o, h, l, c)
            for k, price in enumerate(seq):
                n += 1
                tid = f"{SELECTOR}-{n}"
                docs.append({"_id": tid, "id": tid, "trade_id": n, "time": int(ts) + k * 15000, "size": size,
                             "price": float(price), "side": "buy" if k % 2 else "sell", "selector": SELECTOR})
            if len(docs) >= 50000:
                db.trades.insert_many(docs, ordered=False)
                docs = []
    if docs:
        db.trades.insert_many(docs, ordered=False)
    db.trades.create_index([("selector", 1), ("time", 1)])
    first = db.trades.find_one({"selector": SELECTOR}, sort=[("time", 1)])["time"]
    last = db.trades.find_one({"selector": SELECTOR}, sort=[("time", -1)])["time"]
    print(n, "trades", pd.to_datetime(first, unit="ms"), "->", pd.to_datetime(last, unit="ms"))


if __name__ == "__main__":
    main()
