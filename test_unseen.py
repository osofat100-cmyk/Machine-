#!/usr/bin/env python3
"""
The unseen test, 1 Oct - 20 Nov 2026.

Robot 2 as chosen by choose_before_oct.py knows only prices before 1 Oct (data/robot2_oct1.pkl).
On 1 Oct it starts with $1,000 in USDC. It asks price_server.py for the next minute, decides,
sends its order with the next request, and so on, one minute at a time. This program never opens
the test prices; the server keeps the account and fills every order at the minute after the decision.

    python3 test_unseen.py        # starts the price server itself -> data/unseen_test.csv, data/unseen_curve.csv
"""
import csv
import http.client
import json
import pickle
import subprocess
import sys
import time

import numpy as np

PORT = 8765
ROBOT = "data/robot2_oct1.pkl"
SERVER = [sys.executable, "price_server.py", "--port", str(PORT)]
OCT1 = int(np.datetime64("2026-10-01T00:00", "m").astype(np.int64))


def main():
    with open(ROBOT, "rb") as f:
        r = pickle.load(f)
    last = int(r.ts[r.n - 1])
    assert last < OCT1, "the robot must not know any minute from 1 Oct on"
    print(f"robot 2 knows {r.n:,} minutes, the last one {np.datetime64(last, 'm')}; "
          f"window {r.window // 60}h, at the low {r.at_low}%, near the high {r.near_high}%, "
          f"library {'on' if r.borrow else 'off'}, timing {'on' if r.adapt_interval else 'off'}, "
          f"{'Kelly' if r.risk == 'kelly' else f'{float(r.risk):.0%} per buy'}", flush=True)

    # new practice account on 1 Oct: $1,000 USDC. A buy decided at 23:59 on 30 Sep (from earlier
    # prices only) is kept; anything else from before 1 Oct is dropped.
    keep_buy = r.pending == "BUY" and r.coins == 0
    r.cash, r.coins, r.trades, r.fills = 1000.0, 0.0, [], []
    r.pending = "BUY" if keep_buy else None

    server = subprocess.Popen(SERVER)
    try:
        for _ in range(100):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
                conn.connect()
                break
            except OSError:
                time.sleep(0.2)
        curve, prev_ts, t0 = [], None, time.time()
        while True:
            order = r.pending or "NONE"
            share = r.f_next if order == "BUY" else 1.0
            conn.request("GET", f"/next?order={order}&share={share}")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                acct = m["account"]
                break
            assert prev_ts is None or m["ts"] == prev_ts + 1, "minutes must come one at a time, in order"
            prev_ts = m["ts"]
            r.step(m["ts"], m["high"], m["low"], m["close"])
            if m["ts"] % 60 == 0:
                curve.append((m["time"], m["source"], m["close"], m["value"], r.value()))
            if m["ts"] % 10080 == 0:
                print(f"  {m['time']}  account ${m['value']:,.2f}  ({time.time() - t0:.0f}s)", flush=True)
    finally:
        server.terminate()

    print(f"\n{acct['first']} -> {acct['last']}  ({acct['minutes']:,} minutes, handed over one at a time)")
    for t in acct["trades"]:
        print(f"  {t['time']}  {t['action']:<4} at {t['price']:.4f}  account ${t['value']:,.2f}  ({t['source']})")
    print(f"robot 2: $1,000 -> ${acct['value']:,.2f} after {len(acct['trades'])} trades"
          f"   (robot's own count ${r.value():,.2f})")
    print(f"just holding PEARL: $1,000 -> ${acct['holding']:,.2f}")

    with open("data/unseen_test.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "action", "price", "account_$", "source"])
        for t in acct["trades"]:
            w.writerow([t["time"], t["action"], t["price"], round(t["value"], 2), t["source"]])
        w.writerow(["end " + acct["last"], "", "", round(acct["value"], 2), ""])
        w.writerow(["just holding", "", "", round(acct["holding"], 2), ""])
    with open("data/unseen_curve.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "source", "price", "account_$", "robot_own_count_$"])
        w.writerows(curve)


if __name__ == "__main__":
    main()
