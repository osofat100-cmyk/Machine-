#!/usr/bin/env python3
"""
The fixed number from the good averaging level (story size 85: buy after a 43% fall, sell after a 278% rise)
on every month, 25 Jun - 20 Nov 2026.

  one run:     $1,000 on 25 Jun, kept going to 20 Nov
  each month:  a fresh $1,000 at the start of every calendar month (June starts 25 Jun, November ends 20 Nov)

Training minutes from spikes/data/train.csv; the last month's minutes are taken from price_server.py one at a
time. Same rules as every test: decision on a minute's close, filled at the next minute's close, 0.7% per side.

    python3 spikes/all_months.py   -> spikes/all_months.csv, spikes/all_months_graph.png
"""
import json
import os

import numpy as np
import pandas as pd

from all_stories import walk_minutes
from dip_top import COST, Robot, simulate

HERE = os.path.dirname(os.path.abspath(__file__))


def run_with_log(times, close, x, y):
    """Same rules as simulate(), also returns the trades and the value at every hour."""
    r, cash, coins, pend, trades, curve = Robot(x, y), 1000.0, 0.0, None, [], []
    for t, c in zip(times, close):
        if pend == "BUY":
            coins, cash = cash / (c * (1 + COST)), 0.0
            r.filled("BUY", c)
            trades.append((t, "BUY", c, coins * c * (1 - COST)))
        elif pend == "SELL":
            cash, coins = coins * c * (1 - COST), 0.0
            r.filled("SELL", c)
            trades.append((t, "SELL", c, cash))
        pend = r.step(c)
        if t.endswith(":00"):
            curve.append((t, c, cash + coins * c * (1 - COST)))
    return cash + coins * close[-1] * (1 - COST), trades, curve


def main():
    with open(os.path.join(HERE, "dip_top_stories_winner.json")) as f:
        w = json.load(f)
    x, y = w["x"], w["y"]
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"))
    t_train = train["time"].str[:16].str.replace("T", " ").tolist()
    t_test, c_test, _ = walk_minutes(8797)
    times = t_train + t_test
    close = np.concatenate([train["close"].to_numpy(np.float64), c_test])
    assert len(set(times)) == len(times) and times == sorted(times)

    last = [i for i, t in enumerate(times) if t >= "2026-10-22"]
    v_last, _ = simulate(close[last[0]:], x, y)
    assert abs(v_last - 1300.24) < 0.01, v_last
    print(f"bug check: 22 Oct - 20 Nov alone gives ${v_last:,.2f}, same as the price-server test")
    print(f"fixed number: buy after a {x:.0%} fall, sell after a {y:.0%} rise (no stop-loss)\n")

    end, trades, curve = run_with_log(times, close, x, y)
    hold = close[-1] / close[0] * 1000 * (1 - COST) / (1 + COST)
    print(f"ONE RUN, $1,000 on {times[0][:10]} kept going to {times[-1][:10]}:")
    for t, a, p, v in trades:
        print(f"  {t}  {a:<4} at {p:.4f}  account ${v:,.2f}")
    print(f"  end: ${end:,.2f}   just holding PEARL: ${hold:,.2f}\n")

    rows = []
    month = np.array([t[:7] for t in times])
    for m in sorted(set(month)):
        idx = np.where(month == m)[0]
        c = close[idx]
        v, n = simulate(c, x, y)
        h = c[-1] / c[0] * 1000 * (1 - COST) / (1 + COST)
        part = "before 22 Oct (learned from)" if times[idx[-1]] < "2026-10-22" else (
            "after 22 Oct (unseen)" if times[idx[0]] >= "2026-10-22" else "both")
        rows.append({"month": m, "from": times[idx[0]][:10], "to": times[idx[-1]][:10], "robot_$": round(v, 2),
                     "trades": int(n), "holding_$": round(h, 2), "data": part})
    r = pd.DataFrame(rows)
    print("EACH MONTH, a fresh $1,000:")
    print(r.to_string(index=False))
    r.to_csv(os.path.join(HERE, "all_months.csv"), index=False)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cv = pd.DataFrame(curve, columns=["t", "price", "value"])
    cv["t"] = pd.to_datetime(cv["t"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    a1.plot(cv["t"], cv["value"], lw=2, label=f"robot, fixed 43% / 278% (\\${end:,.0f})")
    a1.plot(cv["t"], 1000 * cv["price"] / close[0] * (1 - COST) / (1 + COST), color="grey", ls=":",
            label=f"just holding PEARL (\\${hold:,.0f})")
    a1.axvline(pd.Timestamp("2026-10-22"), color="red", lw=1, label="22 Oct: the fixed number was made from before this")
    a1.set_ylabel("\\$ (start \\$1,000 on 25 Jun)")
    a1.set_title("One run, 25 Jun - 20 Nov")
    a1.legend()
    a1.grid(alpha=0.3)
    a2.plot(cv["t"], cv["price"], color="black", lw=1)
    for t, a, p, _ in trades:
        a2.scatter([pd.Timestamp(t)], [p], color="green" if a == "BUY" else "red", s=80, zorder=3)
        a2.annotate(f"{a} {p:.3f}", (pd.Timestamp(t), p), textcoords="offset points", xytext=(5, 8), fontsize=9)
    a2.set_ylabel("PEARL price")
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "all_months_graph.png"), dpi=110)
    print("saved spikes/all_months_graph.png")


if __name__ == "__main__":
    main()
