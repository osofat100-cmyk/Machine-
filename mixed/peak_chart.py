#!/usr/bin/env python3
"""The two-Ultra hourly run measured only against its own peak: money, the highest point so far, and how far
below that peak it is each hour.   python3 mixed/peak_chart.py -> mixed/peak_chart.png"""
import csv
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF, BLUE, RED = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6", "#e34948"


def main():
    rows = [r for r in csv.DictReader(open(os.path.join(HERE, "watcher_hourly_3m_ultra.csv"))) if r.get("value")]
    t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows]
    v = [float(r["value"]) for r in rows]
    pk, peaks = 0.0, []
    for x in v:
        pk = max(pk, x)
        peaks.append(pk)
    dd = [100 * (x / p - 1) for x, p in zip(v, peaks)]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 7.5), facecolor=SURF, sharex=True, gridspec_kw={"height_ratios": [2, 1.2]})
    a1.plot(t, v, color=BLUE, lw=2.2, label="Two Ultras: money")
    a1.plot(t, peaks, color=INK, lw=1.4, ls=(0, (4, 3)), label="Its highest point so far (peak)")
    i = v.index(max(v))
    a1.annotate(f"peak ${max(v):,.0f}\n{t[i]:%d %b %H:%M}", (t[i], v[i]), xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=9, color=INK, weight="bold")
    a1.annotate(f"now ${v[-1]:,.0f}", (t[-1], v[-1]), xytext=(8, 0), textcoords="offset points", fontsize=9,
                color=BLUE, weight="bold", va="center")
    a1.axhline(1000, color=INK2, lw=1, alpha=0.5)
    a1.set_ylabel("Money ($, started at $1,000)", color=INK2, fontsize=9)
    a1.set_title(f"Two Ultras against their own peak, 25 Aug to {t[-1]:%d %b %H:%M}", loc="left", fontsize=13,
                 color=INK, weight="bold")
    a1.legend(loc="upper left", fontsize=9, frameon=False)
    a2.fill_between(t, dd, 0, color=RED, alpha=0.35, lw=0)
    a2.plot(t, dd, color=RED, lw=1.2)
    a2.annotate(f"{dd[-1]:+.1f}% from peak", (t[-1], dd[-1]), xytext=(8, 0), textcoords="offset points", fontsize=9,
                color=RED, weight="bold", va="center")
    j = dd.index(min(dd))
    a2.annotate(f"deepest {min(dd):.1f}%", (t[j], dd[j]), xytext=(-10, 0), textcoords="offset points", ha="right", va="center",
                fontsize=8, color=INK2)
    a2.axhline(0, color=INK2, lw=1)
    a2.set_ylabel("% below its peak (0 = at a new peak)", color=INK2, fontsize=9)
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
    fig.savefig(os.path.join(HERE, "peak_chart.png"), dpi=110, facecolor=SURF)


if __name__ == "__main__":
    main()
