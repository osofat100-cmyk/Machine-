#!/usr/bin/env python3
"""
Day-by-day view of the finished crypto golden-rule runs (practice $1,000, 18 Nov 05:31 -> 23 Nov 21:00 UTC, 5.65 days).

1. Growth in the first 24 hours only, and whether that day-1 rate, repeated, predicts the money at 72 hours (day 3)
   and at the end.
2. Flat-ground money over time: the market-adjusted value  1000 * (run / start) / (Bitcoin / start)^beta,
   using each run's beta from golden_flat_ground.py.  This is the run with the market's effect taken out,
   hour by hour, so you can see whether the flat-ground gain kept climbing or hit a level and stopped.
   Saved as crypto/golden_flat_ground_chart.png.

    python3 crypto/golden_growth_days.py
"""
import csv
import json
import math
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import statsmodels.api as sm

plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
START = datetime(2026, 11, 18, 5, 31)
END = datetime(2026, 11, 23, 21, 0)
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(v, k):
    res = os.path.join(HERE, f"result_1m_every{k}_{v}_ultrafast.json")
    if not os.path.exists(res):
        return None
    acc = json.load(open(res))
    rows = [r for r in csv.DictReader(open(os.path.join(HERE, f"answers_1m_every{k}_{v}_ultrafast.csv")))
            if r.get("time") and r["time"] != "time" and r["value"] and r["time"].endswith(":31")]
    t = [datetime.strptime(r["time"], "%Y-%m-%d %H:%M") for r in rows] + [END]
    a = np.array([float(r["value"]) for r in rows] + [acc["ai"]["value"]])
    b = np.array([float(r["btc_hold"]) for r in rows] + [acc["btc_hold"]["value"]])
    return t, a, b


def at(t, x, when):
    return x[t.index(when)]


def main():
    days = [START + timedelta(hours=24 * d) for d in range(1, 6)]
    table, curves = [], {}
    for v, name in (("v4a", "First"), ("v4b", "Second")):
        for k in (2, 3, 4, 5, 10, 15, 30, 60):
            got = load(v, k)
            if not got:
                continue
            t, a, b = got
            ra, rb = np.diff(np.log(a)), np.diff(np.log(b))
            fit = sm.OLS(ra, sm.add_constant(rb)).fit()
            beta = fit.params[1]
            flat = 1000 * (a / a[0]) / (b / b[0]) ** beta
            curves[(name, k)] = (t, flat)
            d1 = at(t, a, days[0])
            g1 = d1 / 1000                                      # day-1 multiplier
            row = {"run": f"{name} every {k}", "day1": d1, "day1_rate_pct": 100 * (g1 - 1),
                   "day3_actual": at(t, a, days[2]), "day3_predicted": 1000 * g1 ** 3,
                   "end_actual": a[-1], "end_predicted": 1000 * g1 ** (135.5 / 24),
                   "flat_by_day": [at(t, flat, d) - 1000 for d in days] + [flat[-1] - 1000]}
            table.append(row)
    btc = load("v4a", 60)
    t, _, b = btc
    print("Bitcoin: day1 %.2f  day3 %.2f  end %.2f" % (at(t, b, days[0]), at(t, b, days[2]), b[-1]))
    for r in table:
        print(f"{r['run']:16s} day1 {r['day1']:8.2f} ({r['day1_rate_pct']:+.2f}%/day)  day3 actual {r['day3_actual']:8.2f} "
              f"predicted {r['day3_predicted']:8.2f}  end actual {r['end_actual']:8.2f} predicted {r['end_predicted']:8.2f}  "
              f"flat by day {' '.join('%+6.1f' % x for x in r['flat_by_day'])}")
    json.dump(table, open(os.path.join(HERE, "golden_growth_days.json"), "w"), indent=1, default=str)

    fig, axes = plt.subplots(2, 1, figsize=(13, 10), facecolor=SURF, sharex=True)
    for ax, name, title in ((axes[0], "First", "First version (golden rule only)"),
                            (axes[1], "Second", "Second version (golden rule + spread the risk + trade rarely)")):
        ks = [k for (n, k) in curves if n == name]
        ends = []
        for i, k in enumerate(ks):
            tt, flat = curves[(name, k)]
            y = flat - 1000
            ax.plot(tt, y, color=SLOTS[i], lw=2, label=f"every {k} min", solid_capstyle="round")
            ends.append([y[-1], y[-1], k, tt[-1]])
        ends.sort()                                   # spread end labels so they do not overlap
        for j in range(1, len(ends)):
            ends[j][1] = max(ends[j][1], ends[j - 1][1] + 6.5)
        for y_end, y_lab, k, t_end in ends:
            ax.annotate(f"every {k}  {y_end:+.0f}", (t_end, y_end), xytext=(t_end + timedelta(minutes=40), y_lab),
                        textcoords="data", fontsize=8, color=INK2, va="center")
        ax.axhline(0, color=INK2, lw=1, alpha=0.6)
        for d in days:
            ax.axvline(d, color=GRID, lw=1, zorder=0)
        ax.set_title(f"Crypto flat-ground gain over time: {title}", loc="left", fontsize=12, color=INK, weight="bold")
        ax.set_ylabel("Gain with the market's effect removed ($)", color=INK2, fontsize=9)
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
        ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=4)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    axes[1].set_xlabel("Market time (UTC). Vertical lines = each 24 hours from the start.", color=INK2, fontsize=9)
    fig.tight_layout()
    out = os.path.join(HERE, "golden_flat_ground_chart.png")
    fig.savefig(out, dpi=110, facecolor=SURF)
    print(out)


if __name__ == "__main__":
    main()
