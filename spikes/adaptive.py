#!/usr/bin/env python3
"""
Last month (22 Oct - 20 Nov), two versions of the dip-and-top robot, both picked with story size 85
(the averaging chosen on the practice months, see stories.py):

  fixed:     one buy/sell pair from all training months (before 22 Oct), never changed.
  adaptive:  every day at 00:00 it re-tests all 29,700 buy/sell pairs on the training months PLUS every test
             minute it has been handed so far, averages them the same way, and switches to the new pair.

The price server hands out one minute at a time; the robot never sees a minute before it happens.

    python3 spikes/adaptive.py fixed      -> spikes/adaptive_fixed_curve.csv
    python3 spikes/adaptive.py adaptive   -> spikes/adaptive_daily_picks.csv, spikes/adaptive_adaptive_curve.csv
    python3 spikes/adaptive.py graph      -> spikes/adaptive_graph.png
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

from dip_top import XS, YS, Robot, grid
from stories import pick

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STORY = 85


def choose(closes):
    v, _ = grid(np.asarray(closes, dtype=np.float64), XS, YS)
    i, j, _ = pick(v, STORY)
    return float(XS[i]), float(YS[j])


def run(mode):
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert train["time"].iloc[-1] < pd.Timestamp("2026-10-22", tz="UTC")
    seen = list(train["close"].to_numpy(np.float64))
    x, y = choose(seen)
    with open(os.path.join(HERE, "dip_top_stories_winner.json")) as f:
        locked = json.load(f)
    assert (x, y) == (locked["x"], locked["y"]), "day-1 pick must equal the locked fixed pick"
    robot = Robot(x, y)
    print(f"{mode}: day-1 pick buy after {x:.0%} fall, sell after {y:.0%} rise")

    port = 8793 if mode == "fixed" else 8794
    server = subprocess.Popen([sys.executable, "price_server.py", "--port", str(port), "--file",
                               "data/sealed/PEARL_last_month.csv"], cwd=ROOT, stdout=subprocess.DEVNULL)
    picks, curve = [], []
    try:
        for _ in range(100):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
                conn.connect()
                break
            except OSError:
                time.sleep(0.2)
        order, coins, prev, first = "NONE", 0.0, None, True
        while True:
            conn.request("GET", f"/next?order={order}&share=1.0")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                acct = m["account"]
                break
            assert prev is None or m["ts"] == prev + 1
            prev = m["ts"]
            if m["coins"] != coins:
                robot.filled("BUY" if m["coins"] > coins else "SELL", m["close"])
                coins = m["coins"]
            if mode == "adaptive" and m["time"].endswith("00:00") and not first:
                robot.x, robot.y = choose(seen)          # only minutes already handed over
            if m["time"].endswith("00:00"):
                picks.append((m["time"][:10], round(robot.x * 100), round(robot.y * 100), len(seen)))
                print(f"  {m['time'][:10]}: buy after {robot.x:.0%} fall, sell after {robot.y:.0%} rise "
                      f"(learned from {len(seen):,} minutes)  account ${m['value']:,.2f}", flush=True)
            first = False
            seen.append(m["close"])
            order = robot.step(m["close"]) or "NONE"
            if m["ts"] % 60 == 0:
                curve.append((m["time"], m["close"], round(m["value"], 2)))
    finally:
        server.terminate()

    for t in acct["trades"]:
        print(f"  {t['time']}  {t['action']:<4} at {t['price']:.4f}  account ${t['value']:,.2f}  ({t['source']})")
    print(f"{mode}: $1,000 -> ${acct['value']:,.2f} after {len(acct['trades'])} trades; "
          f"just holding PEARL ${acct['holding']:,.2f}")
    with open(os.path.join(HERE, f"adaptive_{mode}_curve.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "price", "account_$"])
        w.writerows(curve)
        w.writerow(["trades", json.dumps(acct["trades"]), round(acct["value"], 2)])
    if mode == "adaptive":
        with open(os.path.join(HERE, "adaptive_daily_picks.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["day", "buy_after_fall_%", "sell_after_rise_%", "minutes_learned_from"])
            w.writerows(picks)


def graph():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    load = lambda m: pd.read_csv(os.path.join(HERE, f"adaptive_{m}_curve.csv"))  # noqa: E731
    fx, ad = load("fixed"), load("adaptive")
    fx, ad = fx[fx["time_utc"] != "trades"], ad[ad["time_utc"] != "trades"]
    for d in (fx, ad):
        d["t"] = pd.to_datetime(d["time_utc"])
        d["price"] = d["price"].astype(float)
        d["account_$"] = d["account_$"].astype(float)
    hold = 1000 * fx["price"] / fx["price"].iloc[0] * (1 - 0.007) / (1 + 0.007)
    pk = pd.read_csv(os.path.join(HERE, "adaptive_daily_picks.csv"), parse_dates=["day"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(fx["t"], fx["account_$"], lw=2, label=f"version 1, fixed pick (\\${fx['account_$'].iloc[-1]:,.0f})")
    a1.plot(ad["t"], ad["account_$"], lw=2, label=f"version 2, re-picked every day (\\${ad['account_$'].iloc[-1]:,.0f})")
    a1.plot(fx["t"], hold, ls=":", color="grey", label=f"just holding PEARL (\\${hold.iloc[-1]:,.0f})")
    a1.axhline(1000, color="black", lw=0.8, ls="--")
    a1.set_ylabel("account \\$")
    a1.set_title("Last month, 22 Oct - 20 Nov, handed over one minute at a time")
    a1.legend()
    a1.grid(alpha=0.3)
    a2.step(pk["day"], pk["buy_after_fall_%"], where="post", label="buy after this % fall")
    a2.step(pk["day"], pk["sell_after_rise_%"] / 10, where="post", label="sell after this % rise (/10)")
    a2.set_ylabel("version 2's daily pick")
    a2.legend()
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "adaptive_graph.png"), dpi=110)
    print("saved spikes/adaptive_graph.png")


if __name__ == "__main__":
    graph() if sys.argv[1] == "graph" else run(sys.argv[1])
