#!/usr/bin/env python3
"""
Dip and top: the user's plan, nothing added.
  BUY with all the money when PEARL has fallen X% from its highest price since the last sell.
  SELL everything when PEARL is Y% above the buy price.
  No stop-loss. X = 1..99%, Y = 1..300% (29,700 pairs). The pair that makes the most money on the training
  months (25 Jun - 21 Oct) is tested on the last month (22 Oct - 20 Nov), one minute at a time.
Cost per side 0.7% (0.2% fee + 0.5% half gap); a decision on a minute's close fills at the next minute's close.

    python3 spikes/dip_top.py choose   -> spikes/dip_top_train.csv, spikes/dip_top_winner.json, spikes/dip_top_graph.png
    python3 spikes/dip_top.py test     -> spikes/dip_top_last_month.csv
    python3 spikes/dip_top.py smooth   pick the middle of the highest AREA, not the highest single peak:
                                       every pair scored by the average of all pairs within +-5% buy and +-5% sell
                                       -> spikes/dip_top_smooth_winner.json, spikes/dip_top_smooth_graph.png
    python3 spikes/dip_top.py test smooth  -> spikes/dip_top_smooth_last_month.csv
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
from numba import njit, prange

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COST = 0.007
XS = np.arange(1, 100) / 100
YS = np.arange(1, 301) / 100


@njit(cache=True)
def simulate(close, x, y):
    cash, coins, buy, top, pending, trades = 1000.0, 0.0, 0.0, close[0], 0, 0
    for t in range(close.shape[0]):
        c = close[t]
        if pending == 1:
            coins, cash, buy, trades = cash / (c * (1 + COST)), 0.0, c, trades + 1
        elif pending == -1:
            cash, coins, top, trades = coins * c * (1 - COST), 0.0, c, trades + 1
        pending = 0
        if coins > 0:
            if c >= buy * (1 + y):
                pending = -1
        else:
            if c > top:
                top = c
            if c <= top * (1 - x):
                pending = 1
    return cash + coins * close[-1] * (1 - COST), trades


@njit(parallel=True, cache=True)
def grid(close, xs, ys):
    val = np.empty((xs.shape[0], ys.shape[0]))
    trd = np.empty((xs.shape[0], ys.shape[0]), dtype=np.int64)
    for i in prange(xs.shape[0]):
        for j in range(ys.shape[0]):
            val[i, j], trd[i, j] = simulate(close, xs[i], ys[j])
    return val, trd


class Robot:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.holding, self.buy, self.top = False, 0.0, None

    def filled(self, action, price):
        self.holding = action == "BUY"
        if self.holding:
            self.buy = price
        else:
            self.top = price

    def step(self, c):
        if self.top is None:
            self.top = c
        if self.holding:
            return "SELL" if c >= self.buy * (1 + self.y) else None
        self.top = max(self.top, c)
        return "BUY" if c <= self.top * (1 - self.x) else None


def choose():
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert train["time"].iloc[-1] < pd.Timestamp("2026-10-22", tz="UTC")
    close = train["close"].to_numpy(np.float64)
    t0 = time.time()
    val, trd = grid(close, XS, YS)
    print(f"{len(XS) * len(YS):,} buy/sell pairs on {len(close):,} training minutes ({time.time() - t0:.0f}s)")

    # bug check: the live robot must make exactly the same trades as the fast simulator
    for x, y in ((0.10, 0.20), (0.05, 0.08), (0.30, 0.50)):
        r, cash, coins, pend, n = Robot(x, y), 1000.0, 0.0, None, 0
        for c in close:
            if pend == "BUY":
                coins, cash, n = cash / (c * (1 + COST)), 0.0, n + 1
                r.filled("BUY", c)
            elif pend == "SELL":
                cash, coins, n = coins * c * (1 - COST), 0.0, n + 1
                r.filled("SELL", c)
            pend = r.step(c)
        v = cash + coins * close[-1] * (1 - COST)
        sv, sn = simulate(close, x, y)
        assert abs(v - sv) < 1e-6 and n == sn, (x, y, v, sv, n, sn)
    print("bug check: live robot and simulator agree")

    rows = [(int(round(XS[i] * 100)), int(round(YS[j] * 100)), round(val[i, j], 2), int(trd[i, j]))
            for i in range(len(XS)) for j in range(len(YS))]
    df = pd.DataFrame(rows, columns=["buy_after_fall_%", "sell_after_rise_%", "training_$", "trades"])
    df = df.sort_values("training_$", ascending=False)
    df.to_csv(os.path.join(HERE, "dip_top_train.csv"), index=False)
    w = df.iloc[0]
    win = {"x": float(w["buy_after_fall_%"]) / 100, "y": float(w["sell_after_rise_%"]) / 100,
           "training_$": float(w["training_$"]), "training_trades": int(w["trades"])}
    with open(os.path.join(HERE, "dip_top_winner.json"), "w") as f:
        json.dump(win, f, indent=2)
    hold = close[-1] / close[0] * 1000 * (1 - COST) / (1 + COST)
    print(f"just holding PEARL over the training months: ${hold:,.2f}")
    print("top 15:")
    print(df.head(15).to_string(index=False))
    print(f"winner: buy after a {win['x']:.0%} fall, sell after a {win['y']:.0%} rise: "
          f"${win['training_$']:,.2f} on the training months, {win['training_trades']} trades")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    X, Y = np.meshgrid(XS * 100, YS * 100, indexing="ij")
    fig = plt.figure(figsize=(13, 9))
    ax = fig.add_subplot(projection="3d")
    ax.plot_surface(X, Y, val, cmap="viridis", linewidth=0, antialiased=True, alpha=0.95)
    ax.plot_surface(X, Y, np.full_like(val, hold), color="red", alpha=0.25)
    ax.scatter([win["x"] * 100], [win["y"] * 100], [win["training_$"]], color="red", s=80, depthshade=False)
    ax.set_xlabel("buy after PEARL falls this % from its top")
    ax.set_ylabel("sell after PEARL rises this % above the buy")
    ax.set_zlabel("\\$ at the end of the training months")
    ax.set_title(f"All {len(XS) * len(YS):,} buy/sell pairs, \\$1,000 on 25 Jun -> 21 Oct (training months)\n"
                 f"red sheet = just holding (\\${hold:,.0f}), red dot = most money: buy after "
                 f"{win['x']:.0%} fall, sell after {win['y']:.0%} rise (\\${win['training_$']:,.0f})")
    ax.view_init(elev=30, azim=-125)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dip_top_graph.png"), dpi=110)
    print("saved spikes/dip_top_graph.png")


WINDOW = 5


def smooth():
    df = pd.read_csv(os.path.join(HERE, "dip_top_train.csv"))
    grid_ = df.pivot(index="buy_after_fall_%", columns="sell_after_rise_%", values="training_$")
    v = grid_.to_numpy()
    n, m = v.shape
    avg = np.empty_like(v)
    for i in range(n):
        for j in range(m):
            avg[i, j] = v[max(0, i - WINDOW):i + WINDOW + 1, max(0, j - WINDOW):j + WINDOW + 1].mean()
    i, j = np.unravel_index(np.argmax(avg), avg.shape)
    x, y = int(grid_.index[i]), int(grid_.columns[j])
    trades = int(df[(df["buy_after_fall_%"] == x) & (df["sell_after_rise_%"] == y)]["trades"].iloc[0])
    win = {"x": x / 100, "y": y / 100, "area_average_$": round(float(avg[i, j]), 2),
           "own_training_$": round(float(v[i, j]), 2), "training_trades": trades, "window": f"+-{WINDOW}%"}
    with open(os.path.join(HERE, "dip_top_smooth_winner.json"), "w") as f:
        json.dump(win, f, indent=2)
    order = np.argsort(-avg, axis=None)[:10]
    print(f"best areas (average of every pair within +-{WINDOW}% buy and +-{WINDOW}% sell):")
    for k in order:
        a, b = np.unravel_index(k, avg.shape)
        print(f"  buy after {grid_.index[a]}% fall, sell after {grid_.columns[b]}% rise: area average "
              f"${avg[a, b]:,.2f}, this pair alone ${v[a, b]:,.2f}")
    print(f"winner (middle of the best area): buy after a {x}% fall, sell after a {y}% rise; area average "
          f"${avg[i, j]:,.2f}, this pair alone ${v[i, j]:,.2f}, {trades} training trades")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    X, Y = np.meshgrid(grid_.index.to_numpy(), grid_.columns.to_numpy(), indexing="ij")
    fig = plt.figure(figsize=(20, 8.5))
    for k, (z, title) in enumerate(((v, "Each pair alone (spiky = luck)"),
                                    (avg, f"Area average, +-{WINDOW}% around each pair (the safe hill)")), 1):
        ax = fig.add_subplot(1, 2, k, projection="3d")
        ax.plot_surface(X, Y, z, cmap="viridis", linewidth=0, antialiased=True, alpha=0.95)
        ax.scatter([x], [y], [z[i, j]], color="red", s=80, depthshade=False)
        ax.set_xlabel("buy after PEARL falls this % from its top")
        ax.set_ylabel("sell after PEARL rises this % above the buy")
        ax.set_zlabel("\\$ at the end of the training months")
        ax.set_title(title + f"\nred dot = chosen: buy after {x}% fall, sell after {y}% rise "
                     f"(\\${z[i, j]:,.0f})")
        ax.view_init(elev=30, azim=-125)
    fig.suptitle("Training months 25 Jun - 21 Oct, $1,000 start".replace("$", "\\$"), fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(os.path.join(HERE, "dip_top_smooth_graph.png"), dpi=110)
    print("saved spikes/dip_top_smooth_graph.png")


def test():
    tag = "_smooth" if "smooth" in sys.argv[2:] else ""
    with open(os.path.join(HERE, f"dip_top{tag}_winner.json")) as f:
        w = json.load(f)
    robot, port = Robot(w["x"], w["y"]), 8792
    print(f"dip and top: buy after a {w['x']:.0%} fall from the top, sell after a {w['y']:.0%} rise; no stop-loss")
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
        order, coins, prev = "NONE", 0.0, None
        while True:
            conn.request("GET", f"/next?order={order}&share=1.0")
            m = json.loads(conn.getresponse().read())
            if m.get("done"):
                acct = m["account"]
                break
            assert prev is None or m["ts"] == prev + 1, "minutes must come one at a time, in order"
            prev = m["ts"]
            if m["coins"] != coins:
                robot.filled("BUY" if m["coins"] > coins else "SELL", m["close"])
                coins = m["coins"]
            order = robot.step(m["close"]) or "NONE"
    finally:
        server.terminate()

    print(f"\n{acct['first']} -> {acct['last']} ({acct['minutes']:,} minutes, handed over one at a time)")
    for t in acct["trades"]:
        print(f"  {t['time']}  {t['action']:<4} at {t['price']:.4f}  account ${t['value']:,.2f}  ({t['source']})")
    still = f" (still holding {acct['coins']:,.2f} PEARL, valued at the last price)" if acct["coins"] > 0 else ""
    print(f"dip and top: $1,000 -> ${acct['value']:,.2f} after {len(acct['trades'])} trades{still}")
    print(f"just holding PEARL: $1,000 -> ${acct['holding']:,.2f}")
    with open(os.path.join(HERE, f"dip_top{tag}_last_month.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["time_utc", "action", "price", "account_$", "source"])
        for t in acct["trades"]:
            wr.writerow([t["time"], t["action"], t["price"], round(t["value"], 2), t["source"]])
        wr.writerow(["end " + acct["last"], "", "", round(acct["value"], 2), ""])
        wr.writerow(["just holding", "", "", round(acct["holding"], 2), ""])


if __name__ == "__main__":
    {"choose": choose, "test": test, "smooth": smooth}[sys.argv[1]]()
