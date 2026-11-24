#!/usr/bin/env python3
"""Model race (stopped early): every copy's money at the last market time ALL runs reached, by AI.
    python3 crypto/model_race_chart.py -> crypto/model_race_chart.png"""
import csv
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["text.parse_math"] = False
HERE = os.path.dirname(os.path.abspath(__file__))
ULTRA = json.load(open(os.path.join(HERE, "ultra_runs_at_1211.json")))   # all 19 first-rule Ultra runs, replayed
TAGS = {"Ultra (all 19 earlier runs)": list(ULTRA), "Kimi K3.1 Pro": [f"kimi_c{i}" for i in range(1, 6)],
        "Nemotron 3.5 Super": [f"super_c{i}" for i in range(1, 6)],
        "Nemotron 3.5 Lightning": [f"lightning_c{i}" for i in range(1, 6)]}
COL = {"Ultra (all 19 earlier runs)": "#2a78d6", "Kimi K3.1 Pro": "#eb6834", "Nemotron 3.5 Super": "#1baf7a", "Nemotron 3.5 Lightning": "#eda100"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
data = {}
for g, ts in TAGS.items():
    for t in ts:
        if g.startswith("Ultra"):
            continue
        rows = [r for r in csv.DictReader(open(os.path.join(HERE, f"answers_1m_every5_v4a_{t}.csv")))
                if r.get("time") and r["time"] != "time" and r["value"]]
        data[t] = ({r["time"]: (float(r["value"]), float(r["btc_hold"])) for r in rows}, rows[-1]["time"])
common = min(v[1] for v in data.values())
btc = data["kimi_c1"][0][common][1]
fig, ax = plt.subplots(figsize=(14, 5.8), facecolor=SURF)
x = 0
for g, ts in TAGS.items():
    vals = [ULTRA[t] for t in ts] if g.startswith("Ultra") else [data[t][0][common][0] for t in ts]
    xs = list(range(x, x + len(vals)))
    ax.bar(xs, [v - 1000 for v in vals], color=COL[g], width=0.75)
    for xi, v in (zip(xs, vals) if not g.startswith("Ultra") else []):
        ax.annotate(f"${v:,.0f}", (xi, v - 1000), xytext=(0, 3 if v >= 1000 else -3), textcoords="offset points",
                    ha="center", va="bottom" if v >= 1000 else "top", fontsize=8, color=INK2)
    avg = sum(vals) / len(vals)
    ax.annotate(f"{g}\naverage ${avg:,.0f}", ((xs[0] + xs[-1]) / 2, 31), xytext=(0, 0), textcoords="offset points",
                ha="center", va="top", fontsize=9, color=INK, weight="bold")
    x += len(vals) + 1
ax.axhline(0, color=INK2, lw=1)
ax.axhline(btc - 1000, color=INK, lw=1.5, ls=(0, (4, 3)))
ax.annotate(f"holding Bitcoin ${btc:,.0f}", (x - 1.5, btc - 1000), xytext=(0, -12), textcoords="offset points",
            ha="right", fontsize=8, color=INK)
ax.set_xticks([])
ax.set_ylabel("Gain or loss from $1,000", color=INK2, fontsize=9)
ax.set_ylim(-25, 35)
ax.set_title(f"Model race, stopped early: every copy at the same market time (18 Nov 05:31 to {common[11:]} UTC, 6.7 hours)",
             loc="left", fontsize=11.5, color=INK, weight="bold")
for s in ("top", "right", "bottom"):
    ax.spines[s].set_visible(False)
ax.spines["left"].set_color(GRID)
ax.tick_params(colors=INK2, labelsize=8)
ax.set_facecolor(SURF)
fig.tight_layout()
fig.savefig(os.path.join(HERE, "model_race_chart.png"), dpi=110, facecolor=SURF)
print(os.path.join(HERE, "model_race_chart.png"), common)
