#!/usr/bin/env python3
"""How far above the market the two-Ultra hourly run is at the end of each day (UTC):
   % above Bitcoin = (team / holding Bitcoin - 1) x 100, and the same against holding SPY.
    python3 mixed/daily_edge.py -> mixed/daily_edge.png (+ printed table)"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF, BLUE, GRAY = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6", "#898781"


def main():
    rows = [r for r in csv.DictReader(open(os.path.join(HERE, "watcher_hourly_3m_ultra.csv"))) if r.get("value")]
    last = {}
    for r in rows:
        last[r["time"][:10]] = r                       # the day's last hour seen so far
    days = sorted(last)
    vb = [100 * (float(last[d]["value"]) / float(last[d]["btc_hold"]) - 1) for d in days]
    vs = [100 * (float(last[d]["value"]) / float(last[d]["spy_hold"]) - 1) for d in days]
    for d, a, b in zip(days, vb, vs):
        r = last[d]
        print(f"{d} {r['time'][11:]}  team ${float(r['value']):8.2f}  vs Bitcoin {a:+6.1f}%  vs SPY {b:+6.1f}%")
    fig, ax = plt.subplots(figsize=(13, 5.5), facecolor=SURF)
    x = range(len(days))
    ax.bar([i - 0.2 for i in x], vb, width=0.38, color=BLUE, label="% above holding Bitcoin")
    ax.bar([i + 0.2 for i in x], vs, width=0.38, color=GRAY, label="% above holding SPY")
    for i, (a, b) in enumerate(zip(vb, vs)):
        for xx, v in ((i - 0.2, a), (i + 0.2, b)):
            ax.annotate(f"{v:+.1f}", (xx, v), xytext=(0, 3 if v >= 0 else -3), textcoords="offset points",
                        ha="center", va="bottom" if v >= 0 else "top", fontsize=7, color=INK2)
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(list(x), [d[5:] for d in days], fontsize=8, color=INK2, rotation=0)
    ax.set_ylabel("% above the market (end of each day)", color=INK2, fontsize=9)
    ax.set_title("Two Ultras: how far above the market at the end of each day (above 0 = beating it)",
                 loc="left", fontsize=12.5, color=INK, weight="bold")
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_facecolor(SURF)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "daily_edge.png"), dpi=110, facecolor=SURF)


if __name__ == "__main__":
    main()
