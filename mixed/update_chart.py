#!/usr/bin/env python3
"""The standard update graph: the weekly-average run, the earlier 24-hour-average run, holding Bitcoin and holding
SPY on the same dates. Top: money. Bottom: each one's % below ITS OWN peak (0 = at a new peak).
    python3 mixed/update_chart.py -> mixed/update_chart.png (+ printed numbers)"""
import csv
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(name):
    return [r for r in csv.DictReader(open(os.path.join(HERE, name))) if r.get("value")]


def main():
    wk = load("watcher_hourly_3m_ultra_week.csv")
    old = load("watcher_hourly_3m_ultra_avg24.csv")
    t_end = wk[-1]["time"]
    old = [r for r in old if r["time"] <= t_end]                      # same dates only
    series = {
        "Two Ultras, weekly-average rule (now running)": (wk, "value", "#2a78d6", 2.4),
        "Two Ultras, 24-hour-average rule (earlier run)": (old, "value", "#eb6834", 1.8),
        "Holding Bitcoin": (wk, "btc_hold", INK, 1.6),
        "Holding SPY": (wk, "spy_hold", "#898781", 1.6)}
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 8), facecolor=SURF, sharex=True, gridspec_kw={"height_ratios": [2, 1.4]})
    print(f"Same dates, 25 Aug to {t_end}; each against its own peak:")
    for name, (rows, key, col, lw) in series.items():
        t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows]
        v = [float(r[key]) for r in rows]
        pk, dd = 0.0, []
        for x in v:
            pk = max(pk, x)
            dd.append(100 * (x / pk - 1))
        ls = (0, (4, 3)) if name == "Holding Bitcoin" else ((0, (1, 2)) if name == "Holding SPY" else "-")
        a1.plot(t, v, color=col, lw=lw, ls=ls, label=name)
        a2.plot(t, dd, color=col, lw=lw * 0.8, ls=ls)
        print(f"  {name:50s} now ${v[-1]:8.2f} | peak ${pk:8.2f} | {dd[-1]:+5.1f}% from peak | deepest {min(dd):+5.1f}%")
    a1.axhline(1000, color=INK2, lw=1, alpha=0.5)
    a1.set_ylabel("Money ($, started at $1,000)", color=INK2, fontsize=9)
    a1.set_title(f"25 Aug to {t_end[8:10]} {datetime.strptime(t_end, '%Y-%m-%d %H:%M'):%b %H:%M}: the runs and the markets",
                 loc="left", fontsize=13, color=INK, weight="bold")
    a1.legend(loc="best", fontsize=8.5, frameon=False)
    a2.axhline(0, color=INK2, lw=1)
    a2.set_ylabel("% below its own peak (0 = new peak)", color=INK2, fontsize=9)
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for ax in (a1, a2):
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "update_chart.png"), dpi=110, facecolor=SURF)


if __name__ == "__main__":
    main()
