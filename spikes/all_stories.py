#!/usr/bin/env python3
"""
All 300 story sizes x {fixed, re-picked every day} = 600 versions of the dip-and-top robot on the last month
(22 Oct - 20 Nov), $1,000 each.

  fixed:     pick from all training months (before 22 Oct), never changed.
  adaptive:  every day at 00:00, pick again from the training months + the test minutes already handed over.

The test minutes are taken from price_server.py one at a time (no orders); each day's pick only uses minutes
before that day. A fast simulator then runs all 600 versions with the same rules as the server (a decision on a
minute's close fills at the next minute's close, 0.7% per side). Bug check: a few versions are also run through
the real server one minute at a time and must give the same dollars.

    python3 spikes/all_stories.py   -> spikes/all_stories.csv, spikes/all_stories_graph.png
"""
import http.client
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd
from numba import njit

from dip_top import COST, XS, YS, Robot, grid
from stories import pick

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIZES = range(1, 301)


def serve(port):
    p = subprocess.Popen([sys.executable, "price_server.py", "--port", str(port), "--file",
                          "data/sealed/PEARL_last_month.csv"], cwd=ROOT, stdout=subprocess.DEVNULL)
    for _ in range(100):
        try:
            c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
            c.connect()
            return p, c
        except OSError:
            time.sleep(0.2)


def walk_minutes(port=8795):
    server, conn = serve(port)
    times, closes = [], []
    try:
        while True:
            conn.request("GET", "/next?order=NONE")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                return times, np.array(closes), m["account"]["holding"]
            times.append(m["time"])
            closes.append(m["close"])
    finally:
        server.terminate()
        server.wait()


@njit(cache=True)
def simulate_daily(close, xs, ys):
    """Same rules as dip_top.simulate, but the buy/sell pair may change each minute (xs[t], ys[t])."""
    cash, coins, buy, top, pending, trades = 1000.0, 0.0, 0.0, close[0], 0, 0
    for t in range(close.shape[0]):
        c = close[t]
        if pending == 1:
            coins, cash, buy, trades = cash / (c * (1 + COST)), 0.0, c, trades + 1
        elif pending == -1:
            cash, coins, top, trades = coins * c * (1 - COST), 0.0, c, trades + 1
        pending = 0
        if coins > 0:
            if c >= buy * (1 + ys[t]):
                pending = -1
        else:
            if c > top:
                top = c
            if c <= top * (1 - xs[t]):
                pending = 1
    return cash + coins * close[-1] * (1 - COST), trades


def through_server(x_by_day, port):
    """One version through the real price server, one minute at a time."""
    server, conn = serve(port)
    robot, order, coins, day = Robot(*x_by_day[0]), "NONE", 0.0, -1
    try:
        while True:
            conn.request("GET", f"/next?order={order}&share=1.0")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                return m["account"]["value"]
            if m["coins"] != coins:
                robot.filled("BUY" if m["coins"] > coins else "SELL", m["close"])
                coins = m["coins"]
            if m["time"].endswith("00:00"):
                day += 1
                robot.x, robot.y = x_by_day[day]
            order = robot.step(m["close"]) or "NONE"
    finally:
        server.terminate()
        server.wait()


def main():
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert train["time"].iloc[-1] < pd.Timestamp("2026-10-22", tz="UTC")
    tr = train["close"].to_numpy(np.float64)
    times, test, hold = walk_minutes()
    day_start = [i for i, t in enumerate(times) if t.endswith("00:00")]
    assert day_start[0] == 0 and len(day_start) == 30
    print(f"test month: {len(test):,} minutes in {len(day_start)} days; holding PEARL ${hold:,.2f}", flush=True)

    t0, grids = time.time(), []
    for d, s in enumerate(day_start):
        v, _ = grid(np.concatenate([tr, test[:s]]), XS, YS)       # only minutes before this day
        grids.append(v)
    print(f"30 daily buy/sell graphs ({time.time() - t0:.0f}s)", flush=True)

    day_of = np.searchsorted(np.array(day_start), np.arange(len(test)), side="right") - 1
    rows, picks = [], {}
    for k in SIZES:
        daily = []
        for v in grids:
            i, j, _ = pick(v, k)
            daily.append((float(XS[i]), float(YS[j])))
        picks[k] = daily
        for mode, plan in (("fixed", [daily[0]] * 30), ("adaptive", daily)):
            xs = np.array([plan[d][0] for d in day_of])
            ys = np.array([plan[d][1] for d in day_of])
            val, n = simulate_daily(test, xs, ys)
            rows.append({"story_size": k, "version": mode, "end_$": round(val, 2), "trades": int(n),
                         "first_pick": f"{plan[0][0]:.0%}/{plan[0][1]:.0%}",
                         "different_daily_picks": len(set(plan))})
    r = pd.DataFrame(rows)

    # bug check: fast simulator vs the real price server, one minute at a time
    for n, (k, mode) in enumerate(((85, "fixed"), (1, "fixed"), (1, "adaptive"), (4, "adaptive"))):
        plan = picks[k] if mode == "adaptive" else [picks[k][0]] * 30
        real = through_server(plan, 8796 + n)
        fast = float(r[(r["story_size"] == k) & (r["version"] == mode)]["end_$"].iloc[0])
        assert abs(real - fast) < 0.02, (k, mode, real, fast)
        print(f"bug check: story {k} {mode}: server ${real:,.2f} = simulator ${fast:,.2f}", flush=True)

    r.to_csv(os.path.join(HERE, "all_stories.csv"), index=False)
    for mode in ("fixed", "adaptive"):
        s = r[r["version"] == mode]["end_$"]
        print(f"\n{mode}: of 300 story sizes, {(s > hold).sum()} beat holding (${hold:,.2f}), {(s > 1000).sum()} "
              f"made money; worst ${s.min():,.2f}, middle ${s.median():,.2f}, average ${s.mean():,.2f}, "
              f"best ${s.max():,.2f}")
    print("\nsmall story sizes (where the pick can move):")
    print(r[r["story_size"] <= 10].pivot(index="story_size", columns="version", values="end_$").to_string())
    print("\nbest 10 of all 600 (best of many tries on one month = partly luck):")
    print(r.sort_values("end_$", ascending=False).head(10).to_string(index=False))
    print("\nthe one locked before the test (size 85):")
    print(r[r["story_size"] == 85].to_string(index=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(16, 8))
    for mode, col in (("fixed", "tab:blue"), ("adaptive", "tab:orange")):
        s = r[r["version"] == mode]
        ax.plot(s["story_size"], s["end_$"], color=col, lw=1.8,
                label=f"{mode}: {(s['end_$'] > hold).sum()}/300 beat holding, middle \\${s['end_$'].median():,.0f}")
    ax.axhline(hold, color="grey", ls=":", lw=2, label=f"just holding PEARL (\\${hold:,.0f})")
    ax.axhline(1000, color="black", ls="--", lw=0.8, label="\\$1,000 start")
    ax.axvline(85, color="red", lw=1, label="size 85, locked before the test")
    ax.set_xscale("log")
    ax.set_xlabel("story size (k x k neighbouring buy/sell pairs merged; 1 = full detail)")
    ax.set_ylabel("\\$ on 20 Nov (start \\$1,000 on 22 Oct)")
    ax.set_title("All 600 versions on the last month, handed over one minute at a time")
    ax.legend()
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "all_stories_graph.png"), dpi=110)
    print("saved spikes/all_stories_graph.png")


if __name__ == "__main__":
    main()
