#!/usr/bin/env python3
"""The standard update graph: both two-Ultra runs, holding Bitcoin and holding SPY, all cut at the same last hour.
Left: the whole test, with each line's peak marked. Right: the last days enlarged, with each line's ending dollars
written on it, so the picture and the printed table show the same numbers.
    python3 mixed/update_chart.py -> mixed/update_chart.png (+ printed numbers)"""
import csv
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patheffects as pe

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
ZOOM_DAYS = 5


def load(name):
    return [r for r in csv.DictReader(open(os.path.join(HERE, name))) if r.get("value")]


def spread(ys, gap):
    """Move label heights apart so none overlap; keeps their order."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for a, b in zip(order, order[1:]):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    shift = sum(out[i] - ys[i] for i in order) / len(ys)
    return [y - shift for y in out]


def main():
    wk = load("watcher_hourly_3m_ultra_week.csv")
    day = load("watcher_hourly_3m_ultra_avg24.csv")
    t_end = min(wk[-1]["time"], day[-1]["time"])                      # the same last hour for every line
    wk = [r for r in wk if r["time"] <= t_end]
    day = [r for r in day if r["time"] <= t_end]
    series = [("AI, 24-hour rule", day, "value", "#eb6834", 2.0),
              ("AI, weekly rule", wk, "value", "#2a78d6", 2.0),
              ("Holding SPY", day, "spy_hold", "#16855c", 2.0),
              ("Holding Bitcoin", day, "btc_hold", "#8a4fd3", 2.0)]
    end = datetime.strptime(t_end, "%Y-%m-%d %H:%M")
    z0 = end - timedelta(days=ZOOM_DAYS)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6.6), facecolor=SURF, gridspec_kw={"width_ratios": [2.1, 1]})
    print(f"Same hour for every line: {t_end}. Each against its own peak:")
    ends, zlo, zhi = [], 1e9, 0
    for name, rows, key, col, lw in series:
        t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows]
        v = [float(r[key]) for r in rows]
        ip = max(range(len(v)), key=lambda i: v[i])
        a1.plot(t, v, color=col, lw=lw, label=name)
        a1.plot([t[ip]], [v[ip]], "o", color=col, ms=7, mec=SURF, mew=2, zorder=5)
        a1.annotate(f"peak ${v[ip]:,.0f}", (t[ip], v[ip]), xytext=(0, -15 if key == "spy_hold" else 10),
                    textcoords="offset points", ha="center", fontsize=9, color=INK, weight="bold", zorder=6,
                    path_effects=[pe.withStroke(linewidth=3.5, foreground=SURF)])
        a1.plot([t[-1]], [v[-1]], "o", color=col, ms=6, mec=SURF, mew=2)
        zt = [x for x in t if x >= z0]
        zv = v[-len(zt):]
        a2.plot(zt, zv, color=col, lw=lw + 0.4)
        a2.plot([zt[-1]], [zv[-1]], "o", color=col, ms=8, mec=SURF, mew=2)
        zlo, zhi = min(zlo, min(zv)), max(zhi, max(zv))
        ends.append((name, v[-1], col))
        print(f"  {name:18s} ends ${v[-1]:8.2f} | peak ${v[ip]:8.2f} on {rows[ip]['time']} | {100 * (v[-1] / v[ip] - 1):+5.1f}% from peak")
    # ending dollars written beside the enlarged panel, spaced so they never overlap
    ys = spread([e[1] for e in ends], (zhi - zlo) * 0.085)
    for (name, val, col), y in zip(ends, ys):
        a2.annotate(f"${val:,.2f}", (end, val), xytext=(end + timedelta(hours=ZOOM_DAYS * 2.2), y), textcoords="data",
                    fontsize=11, weight="bold", color=INK, va="center", annotation_clip=False,
                    arrowprops={"arrowstyle": "-", "color": col, "lw": 1.2})
        a2.annotate(name, (end, val), xytext=(end + timedelta(hours=ZOOM_DAYS * 2.2), y - (zhi - zlo) * 0.036),
                    textcoords="data", fontsize=8.5, color=INK2, va="center", annotation_clip=False)
    a1.axhline(1000, color=INK2, lw=1, alpha=0.5)
    a1.axvspan(z0, end, color=INK2, alpha=0.07, lw=0)
    a1.set_title(f"The whole test: 25 Aug to {end:%d %b %H:%M}", loc="left", fontsize=12.5, color=INK, weight="bold")
    a1.set_ylabel("Money ($, every line started at $1,000)", color=INK2, fontsize=9)
    a1.legend(loc="lower left", fontsize=9, frameon=False)
    a1.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    a2.set_title(f"The last {ZOOM_DAYS} days, enlarged (shaded part on the left)", loc="left", fontsize=12.5, color=INK,
                 weight="bold")
    a2.set_xlim(z0, end + timedelta(hours=ZOOM_DAYS * 1.2))
    a2.set_ylim(zlo - (zhi - zlo) * 0.08, zhi + (zhi - zlo) * 0.08)
    a2.xaxis.set_major_locator(mdates.DayLocator())
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    for ax in (a1, a2):
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8.5)
    fig.tight_layout()
    fig.subplots_adjust(right=0.885, wspace=0.13)
    fig.savefig(os.path.join(HERE, "update_chart.png"), dpi=120, facecolor=SURF)


if __name__ == "__main__":
    main()
