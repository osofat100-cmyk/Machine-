#!/usr/bin/env python3
"""Chart of the 3-month hourly two-AI runs vs holding Bitcoin and holding SPY.
    python3 mixed/hourly_chart.py -> mixed/hourly_chart.png"""
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
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
RUNS = [("hourly_3m_ultra", "Two Ultras (running)", "#2a78d6", 2.4), ("hourly_3m_skeptic", "Sceptic version (stopped)", "#eb6834", 1.6),
        ("hourly_3m", "GLM decider (stopped)", "#1baf7a", 1.6), ("company:company_haiku", "Haiku company (stopped)", "#6250d6", 1.6)]


def load(tag):
    p = os.path.join(HERE, f"company_{tag.split(':')[1]}_hours.csv" if tag.startswith("company:") else f"watcher_{tag}.csv")
    if not os.path.exists(p):
        return None
    rows = [r for r in csv.DictReader(open(p)) if r.get("value")]
    t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows]
    return t, [float(r["value"]) for r in rows], [float(r["btc_hold"]) for r in rows], [float(r["spy_hold"]) for r in rows]


def main():
    fig, ax = plt.subplots(figsize=(13, 6.5), facecolor=SURF)
    main_run = load("hourly_3m_ultra")
    t, v, b, s = main_run
    ax.plot(t, b, color=INK, lw=1.6, ls=(0, (4, 3)), label="Holding Bitcoin")
    ax.plot(t, s, color="#898781", lw=1.6, ls=(0, (1, 2)), label="Holding SPY (stocks)")
    ends = [[b[-1], "Bitcoin", INK, t[-1]], [s[-1], "SPY", "#898781", t[-1]]]
    for tag, name, col, lw in RUNS:
        got = load(tag)
        if not got:
            continue
        stopped = "stopped" in name
        ax.plot(got[0], got[1], color=col, lw=lw,
                label=(f"{name.replace(')', '')} at {got[0][-1]:%d %b %H:%M}: ${got[1][-1]:,.0f})" if stopped else name))
        if not stopped:
            ends.append([got[1][-1], f"{name.split(' (')[0]}", col, got[0][-1]])
        dp = os.path.join(HERE, f"decider_{tag}.csv")
        if tag == "hourly_3m_ultra" and os.path.exists(dp):
            vt = dict(zip(got[0], got[1]))
            for r in csv.DictReader(open(dp)):
                tt = datetime.strptime(r["time"], "%Y-%m-%d %H:%M")
                if json.loads(r["actions"]) and tt in vt and tt != got[0][0]:
                    ax.plot(tt, vt[tt], "o", ms=4, color=col, mec=SURF, mew=1)
    right = sorted([e for e in ends if e[3] == t[-1]])
    for j in range(1, len(right)):
        right[j].append(max(right[j][0], right[j - 1][-1] + 9) if len(right[j - 1]) > 4 else max(right[j][0], right[j - 1][0] + 9))
    for e in ends:
        y, name, col, tt = e[:4]
        ylab = e[4] if len(e) > 4 else y
        ax.annotate(f"{name}  ${y:,.0f}", (tt, y), xytext=(tt, ylab) if tt == t[-1] else (8, 8),
                    textcoords="data" if tt == t[-1] else "offset points", fontsize=9, color=col, va="center",
                    weight="bold")
    ax.axhline(1000, color=INK2, lw=1, alpha=0.5)
    ax.set_title(f"3-month hourly test: $1,000 each, 25 Aug to {t[-1]:%d %b %H:%M} so far (dots = trades)",
                 loc="left", fontsize=13, color=INK, weight="bold")
    ax.set_ylabel("Money ($)", color=INK2, fontsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_facecolor(SURF)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.legend(loc="upper left", fontsize=8.5, frameon=False)
    fig.tight_layout()
    out = os.path.join(HERE, "hourly_chart.png")
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
