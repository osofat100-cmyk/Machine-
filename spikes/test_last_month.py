#!/usr/bin/env python3
"""
The last-month test, 22 Oct - 20 Nov 2026.

The spike robot uses the winner from choose.py and odds tables from the training months only. On 22 Oct it
starts with $1,000 in USDT. price_server.py hands it one minute at a time from the sealed last-month file and
keeps the account; an order fills at the close of the minute after the decision, cost 0.7% per side.
This program never opens the test prices.

    python3 spikes/test_last_month.py   -> spikes/last_month_trades.csv, spikes/last_month_curve.csv
"""
import csv
import http.client
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

from spikes import Robot, tables

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = 8790
SEALED = "data/sealed/PEARL_last_month.csv"


def main():
    with open(os.path.join(HERE, "winner.json")) as f:
        w = json.load(f)
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert train["time"].iloc[-1] < pd.Timestamp("2026-10-22", tz="UTC")
    up_o, down_o, ups, downs = tables(train["close"].to_numpy(np.float64), w["theta"], w["x"])
    robot = Robot(w["theta"], up_o, down_o, w["p_buy"], w["p_sell"], w["stop"])
    print(f"spike robot: spikes of {w['theta']:.0%}, buy below {w['p_buy']:.0%}, sell below {w['p_sell']:.0%}, "
          f"x {w['x']:.0%}, stop {w['stop']:.0%}; odds from {len(ups)} up / {len(downs)} down training spikes")

    server = subprocess.Popen([sys.executable, "price_server.py", "--port", str(PORT), "--file", SEALED],
                              cwd=ROOT, stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
                conn.connect()
                break
            except OSError:
                time.sleep(0.2)
        order, coins_before, prev_ts, curve, decided = "NONE", 0.0, None, [], []
        while True:
            conn.request("GET", f"/next?order={order}&share=1.0")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                acct = m["account"]
                break
            assert prev_ts is None or m["ts"] == prev_ts + 1, "minutes must come one at a time, in order"
            prev_ts = m["ts"]
            if m["coins"] != coins_before:
                robot.filled("BUY" if m["coins"] > coins_before else "SELL", m["close"])
                coins_before = m["coins"]
            action = robot.step(m["close"])
            order = action or "NONE"
            if action:
                decided.append((m["time"], action, m["close"]))
            if m["ts"] % 60 == 0:
                curve.append((m["time"], m["source"], m["close"], round(m["value"], 2)))
    finally:
        server.terminate()

    print(f"\n{acct['first']} -> {acct['last']} ({acct['minutes']:,} minutes, handed over one at a time)")
    for t in acct["trades"]:
        print(f"  {t['time']}  {t['action']:<4} at {t['price']:.4f}  account ${t['value']:,.2f}  ({t['source']})")
    print(f"spike robot: $1,000 -> ${acct['value']:,.2f} after {len(acct['trades'])} trades")
    print(f"just holding PEARL: $1,000 -> ${acct['holding']:,.2f}")
    print(f"keeping the $1,000 in USDT: $1,000")

    with open(os.path.join(HERE, "last_month_trades.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["time_utc", "action", "price", "account_$", "source"])
        for t in acct["trades"]:
            wr.writerow([t["time"], t["action"], t["price"], round(t["value"], 2), t["source"]])
        wr.writerow(["end " + acct["last"], "", "", round(acct["value"], 2), ""])
        wr.writerow(["just holding", "", "", round(acct["holding"], 2), ""])
    with open(os.path.join(HERE, "last_month_curve.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["time_utc", "source", "price", "account_$"])
        wr.writerows(curve)


if __name__ == "__main__":
    main()
