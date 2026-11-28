#!/usr/bin/env python3
"""Picture of the random-trader test: where each team lands among the 1,000 random traders, at two hours.
    python3 mixed/random_chart.py -> mixed/random_chart.png (reads mixed/random_test.json)"""
import csv
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
r = json.load(open(os.path.join(HERE, "random_test.json")))["0.2"]


def load(f):
    return {x["time"]: float(x["value"]) for x in csv.DictReader(open(os.path.join(HERE, f))) if x.get("value")}


t1, old = load("watcher_team1.csv"), load("watcher_hourly_3m_ultra_avg24.csv")
fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), facecolor=SURF)
for ax, (key, title) in zip(axes, [("2026-09-27 07:00", "27 Sep 07:00 (Team 1's peak)"),
                                   ("2026-11-20 23:00", "20 Nov 23:00 (when Team 1 stopped)")]):
    xs = sorted(x for x in r[key] if x is not None)
    ax.hist(xs, bins=40, color="#c9c7c0", edgecolor=SURF)
    for name, v, col in (("Team 1", t1[key], "#2a78d6"), ("Old 24-hour run", old[key], "#8f8d86")):
        beat = 100 * sum(x < v for x in xs) / len(xs)
        ax.axvline(v, color=col, lw=2.4)
        right = name == "Team 1"
        ax.text(v, ax.get_ylim()[1] * 0.92, (f" {name} ${v:,.0f}\n beats {beat:.0f}%" if right else
                                             f"{name} ${v:,.0f} \nbeats {beat:.0f}% "),
                color=INK, fontsize=9.5, weight="bold", va="top", ha="left" if right else "right")
    ax.axvline(xs[int(len(xs) * 0.95)], color="#c0392b", lw=1.2, ls="--")
    ax.text(xs[int(len(xs) * 0.95)], ax.get_ylim()[1] * 0.55, " needed to\n count as skill\n (beat 95%)",
            color="#c0392b", fontsize=8.5, va="top")
    ax.set_title(title, loc="left", fontsize=12, color=INK, weight="bold")
    ax.set_xlabel("Money of each random trader ($, all started at $1,000)", color=INK2, fontsize=9)
    ax.set_facecolor(SURF)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_yticks([])
    ax.tick_params(colors=INK2, labelsize=8.5)
fig.suptitle("1,000 random traders with Team 1's limits (10 holdings, buy only in a dip, no loss sales, ~150 sells)",
             x=0.01, ha="left", fontsize=12.5, color=INK, weight="bold")
fig.tight_layout()
fig.savefig(os.path.join(HERE, "random_chart.png"), dpi=120, facecolor=SURF)
