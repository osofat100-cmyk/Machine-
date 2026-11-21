#!/usr/bin/env python3
"""
What spikes did the robot learn from, and what did it apply them to?

    python3 spikes/explain.py [--every1]
      1. every training spike at the winner's size: start/end time and price, size
      2. the odds table: at each drop/rise size, the chance of going x further, and where the robot acts
      3. the last-month test again through price_server.py (one minute at a time), logging the spike state
         behind every decision
"""
import http.client
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

from spikes import STEP, Robot, tables

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TAG = "_1pct" if "--every1" in sys.argv else ""


def spike_list(t, c, theta):
    """Finished zigzag spikes with their start and end (same rule as spikes.zigzag)."""
    out, up, started = [], True, False
    lo = hi = c[0]
    lo_i = hi_i = 0
    for i, p in enumerate(c):
        if not started:
            if p >= lo * (1 + theta):
                up, hi, hi_i, started = True, p, i, True
            elif p <= hi * (1 - theta):
                up, lo, lo_i, started = False, p, i, True
            if p < lo:
                lo, lo_i = p, i
            if p > hi:
                hi, hi_i = p, i
            continue
        if up:
            if p > hi:
                hi, hi_i = p, i
            elif p <= hi * (1 - theta):
                out.append(("UP", t[lo_i], lo, t[hi_i], hi, hi / lo - 1))
                up, lo, lo_i = False, p, i
        else:
            if p < lo:
                lo, lo_i = p, i
            elif p >= lo * (1 + theta):
                out.append(("DOWN", t[hi_i], hi, t[lo_i], lo, 1 - lo / hi))
                up, hi, hi_i = True, p, i
    return out


def main():
    with open(os.path.join(HERE, f"winner{TAG}.json")) as f:
        w = json.load(f)
    th, x = w["theta"], w["x"]
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"))
    c = train["close"].to_numpy(np.float64)
    t = train["time"].str[:16].str.replace("T", " ").to_numpy()
    up_o, down_o, ups, downs = tables(c, th, x)

    print(f"=== 1. Training spikes at {th:.0%} (25 Jun - 21 Oct), the ones the odds were learned from")
    sp = spike_list(t, c, th)
    for kind in ("UP", "DOWN"):
        rows = [s for s in sp if s[0] == kind]
        sizes = np.array([s[5] for s in rows])
        print(f"{kind}: {len(rows)} spikes, smallest {sizes.min():.1%}, middle {np.median(sizes):.1%}, "
              f"biggest {sizes.max():.1%}")
        for s in sorted(rows, key=lambda r: -r[5])[:12]:
            print(f"   {s[1]} {s[2]:.4f} -> {s[3]} {s[4]:.4f}   {s[5]:6.1%}")
        print(f"   ... {len(rows) - 12} more, the smallest: " +
              ", ".join(f"{s[5]:.1%}" for s in sorted(rows, key=lambda r: r[5])[:6]))

    print(f"\n=== 2. Odds table: chance a move that has gone this far goes {x:.0%} further")
    for name, tab, p, act in (("drop", down_o, w["p_buy"], "BUY"), ("rise", up_o, w["p_sell"], "SELL")):
        line = []
        for size in (0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.25, 0.30, 0.40, 0.60):
            o = tab[min(int(size / STEP), len(tab) - 1)]
            line.append(f"{size:.0%}:{o:.0%}{'*' if o < p else ''}")
        print(f"  {name}: " + "  ".join(line))
        print(f"     * = {act} (chance below {p:.0%})")

    print("\n=== 3. Last month through the price server: the spike behind every decision")
    robot = Robot(th, up_o, down_o, w["p_buy"], w["p_sell"], w["stop"])
    port = 8791
    server = subprocess.Popen([sys.executable, "price_server.py", "--port", str(port), "--file",
                               "data/sealed/PEARL_last_month.csv"], cwd=ROOT, stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                conn.connect()
                break
            except OSError:
                time.sleep(0.2)
        order, coins = "NONE", 0.0
        while True:
            conn.request("GET", f"/next?order={order}&share=1.0")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                break
            if m["coins"] != coins:
                robot.filled("BUY" if m["coins"] > coins else "SELL", m["close"])
                print(f"     filled {m['time']} at {m['close']:.4f}")
                coins = m["coins"]
            p = m["close"]
            a = robot.step(p)
            order = a or "NONE"
            if a == "BUY":
                d = 1 - p / robot.hi
                print(f"  {m['time']} BUY: price {p:.4f} is {d:.1%} below the down-spike's high {robot.hi:.4f}; "
                      f"chance of {x:.0%} more drop {down_o[int(d / STEP)]:.0%} < {w['p_buy']:.0%}")
            elif a == "SELL":
                if robot.stop > 0 and p <= robot.entry * (1 - robot.stop):
                    print(f"  {m['time']} SELL: stop-loss, price {p:.4f} is {1 - p / robot.entry:.1%} below the "
                          f"buy {robot.entry:.4f}")
                else:
                    r = p / robot.lo - 1
                    print(f"  {m['time']} SELL: price {p:.4f} is {r:.1%} above the up-spike's low {robot.lo:.4f}; "
                          f"chance of {x:.0%} more rise {up_o[min(int(r / STEP), len(up_o) - 1)]:.0%} < "
                          f"{w['p_sell']:.0%}")
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
