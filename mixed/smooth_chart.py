#!/usr/bin/env python3
"""Smoothed view: each line as its average over the last 3 days (72 hours), so short spikes and dips are evened out.
Team 3, Team 1, the old 24-hour run, holding Bitcoin and holding SPY, all cut at the same last hour; the 22 Sep - 1 Oct peak
window is shaded.   python3 mixed/smooth_chart.py -> mixed/smooth_chart.png"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(name):
    d = pd.read_csv(os.path.join(HERE, name))
    d = d[d.value.notna()]
    return d.set_index(pd.to_datetime(d.time))


t3, t1, old = load("watcher_team3.csv"), load("watcher_team1.csv"), load("watcher_hourly_3m_ultra_avg24.csv")
end = t3.index[-1]
t3, t1, old = t3[:end], t1[:end], old[:end]
lines = [("Team 3", t3.value, "#eb6834", 2.6), ("Team 1", t1.value, "#2a78d6", 2.0), ("Old 24-hour run", old.value, "#8f8d86", 2.0),
         ("Holding Bitcoin", t3.btc_hold, "#8a4fd3", 2.0), ("Holding SPY", t3.spy_hold, "#16855c", 2.0)]
fig, ax = plt.subplots(figsize=(13, 6.4), facecolor=SURF)
ax.axvspan(pd.Timestamp("2026-09-22"), pd.Timestamp("2026-10-01 23:00"), color=INK2, alpha=0.08, lw=0)
ax.text(pd.Timestamp("2026-09-26 12:00"), 1345, "22 Sep - 1 Oct", ha="center", fontsize=9, color=INK2)
for name, s, col, lw in lines:
    ax.plot(s.index, s, color=col, lw=0.7, alpha=0.25)
    m = s.rolling(72, min_periods=1).mean()
    ax.plot(m.index, m, color=col, lw=lw, label=f"{name}: 3-day average ${m.iloc[-1]:,.0f}")
    ax.plot([m.index[-1]], [m.iloc[-1]], "o", color=col, ms=7, mec=SURF, mew=2)
ax.axhline(1000, color=INK2, lw=1, alpha=0.5)
ax.set_ylim(800, 1380)
ax.set_title(f"Smoothed (3-day average), 25 Aug to {end:%d %b %H:%M}. Faint lines are the hour-by-hour values.",
             loc="left", fontsize=12.5, color=INK, weight="bold")
ax.set_ylabel("Money ($, every line started at $1,000)", color=INK2, fontsize=9)
ax.legend(loc="lower left", fontsize=9.5, frameon=False)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
ax.grid(axis="y", color=GRID, lw=1); ax.set_facecolor(SURF)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
for sp in ("left", "bottom"):
    ax.spines[sp].set_color(GRID)
ax.tick_params(colors=INK2, labelsize=8.5)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "smooth_chart.png"), dpi=120, facecolor=SURF)
print("cut at", end)
