#!/usr/bin/env python3
"""
Chart of the identical-copies test: 10 copies of the first golden-rule version deciding every 60 minutes
(copies 1-5 on the first key, 1-5 on the second key), with the original First-every-60 run and holding Bitcoin.

    python3 crypto/copies_chart.py   -> crypto/copies_chart.png
"""
import csv
import json
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(tag):
    p = os.path.join(HERE, f"answers_1m_every60_v4a_{tag}.csv")
    if not os.path.exists(p):
        return [], [], []
    rows = [r for r in csv.DictReader(open(p)) if r.get("time") and r["time"] != "time" and r["value"]]
    t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows]
    return t, [float(r["value"]) for r in rows], [float(r["btc_hold"]) for r in rows]


def main():
    ot, ov, ob = load("ultrafast")
    res = json.load(open(os.path.join(HERE, "result_1m_every60_v4a_ultrafast.json")))   # true final values at 20:59
    ot, ov, ob = ot + [datetime(2026, 11, 23, 20, 59)], ov + [res["ai"]["value"]], ob + [res["btc_hold"]["value"]]
    fig, axes = plt.subplots(2, 1, figsize=(13, 10), facecolor=SURF, sharex=True, sharey=True)
    for ax, key, title in ((axes[0], 1, "first key"), (axes[1], 2, "second key")):
        ax.plot(ot, ob, color=INK, lw=2, ls=(0, (4, 3)), label="Holding Bitcoin")
        ax.plot(ot, ov, color="#898781", lw=3, alpha=0.6, label="Original run (finished)")
        ends = [[ov[-1], ov[-1], "original", ot[-1], INK2], [ob[-1], ob[-1], "Bitcoin", ot[-1], INK]]
        for c in range(1, 6):
            t, v, _ = load(f"ultrafast_k{key}c{c}")
            if not t:
                continue
            ax.plot(t, v, color=SLOTS[c - 1], lw=2, label=f"copy {c}", solid_capstyle="round")
            ends.append([v[-1], v[-1], f"copy {c}", t[-1], INK2])
        ends.sort()
        for j in range(1, len(ends)):
            ends[j][1] = max(ends[j][1], ends[j - 1][1] + 7)
        for y, yl, name, tt, col in ends:
            ax.annotate(f"{name}  ${y:,.0f}", (tt, y), xytext=(6, yl - y), textcoords="offset points", fontsize=8,
                        color=col, va="center")
        ax.axhline(1000, color=INK2, lw=1, alpha=0.5)
        ax.set_title(f"Identical copies on the {title}: first golden rule, deciding every 60 min", loc="left",
                     fontsize=12, color=INK, weight="bold")
        ax.set_ylabel("Money ($, started at $1,000)", color=INK2, fontsize=9)
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
        ax.legend(loc="lower left", fontsize=8, frameon=False, ncol=4)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    axes[1].set_xlabel("Market time (UTC); copies end where they have reached so far", color=INK2, fontsize=9)
    fig.tight_layout()
    out = os.path.join(HERE, "copies_chart.png")
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
