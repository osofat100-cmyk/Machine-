#!/usr/bin/env python3
"""
When do the identical copies trade, and when do they split apart? 10 identical copies of the first golden-rule
version deciding every 60 minutes plus the original run, replayed through the test server (checked to the cent).

  - trades actually carried out (buys + sells) per day of the test, for every run
  - per hour: how many different portfolios the 11 runs hold, and the average overlap of every pair
    (1 = same 10 coins, 0 = nothing in common)
  - the hour each copy first held something different from the original

    python3 crypto/copies_timing.py   -> crypto/copies_timing.json, crypto/copies_timing_chart.png
"""
import itertools
import json
import os
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flat_ground_replay as F  # noqa: E402

SPECS = [("original", "v4a", 60, "ultrafast")] + \
        [(f"copy {c if k == 1 else c + 5}", "v4a", 60, f"ultrafast_k{k}c{c}") for k in (1, 2) for c in range(1, 6)]


def main():
    steps, groups, runs, values = F.replay(SPECS)
    first = F.WARMUP
    marks = sorted({i for i, st in enumerate(steps) if i >= first and st["time"].endswith(":31")} | {len(steps) - 1})
    names = [s[0] for s in SPECS]
    day_of = lambda kidx: min(5, (kidx - first) // (24 * 60))      # day 0..5 of the test (last day is 15.5 h)
    trades_by_day = {n: [0] * 6 for n in names}
    for n in names:
        for kidx, sold, bought in runs[n]["trades"]:
            if kidx > first + 1:                                   # leave out the opening 10 buys
                trades_by_day[n][day_of(kidx)] += len(sold) + len(bought)
    held = {n: [] for n in names}
    for n in names:
        cur, t = set(), 0
        tr = runs[n]["trades"]
        for kidx in range(len(steps)):
            while t < len(tr) and tr[t][0] == kidx:
                cur = (cur - set(tr[t][1])) | set(tr[t][2])
                t += 1
            if kidx in marks:
                held[n].append(frozenset(cur))
    jac = lambda a, b: len(a & b) / len(a | b) if a | b else 1.0
    overlap = [float(np.mean([jac(held[a][i], held[b][i]) for a, b in itertools.combinations(names, 2)]))
               for i in range(len(marks))]
    distinct = [len({held[n][i] for n in names}) for i in range(len(marks))]
    split = {n: next((steps[marks[i]]["time"] for i in range(len(marks)) if held[n][i] != held["original"][i]), None)
             for n in names if n != "original"}
    out = {"times": [steps[i]["time"] for i in marks], "trades_by_day": trades_by_day, "overlap": overlap,
           "distinct_portfolios": distinct, "first_split_from_original": split,
           "end": {n: values[n][-1] for n in names}}
    json.dump(out, open(os.path.join(HERE, "copies_timing.json"), "w"), indent=1)
    days = ["18 Nov", "19 Nov", "20 Nov", "21 Nov", "22 Nov", "23 Nov"]
    print("trades per day (opening buys left out):", days)
    for n in sorted(names, key=lambda n: -out["end"][n]):
        print(f"{n:9s} end {out['end'][n]:8.2f} trades {trades_by_day[n]} total {sum(trades_by_day[n])}")
    tot = np.sum([trades_by_day[n] for n in names], axis=0)
    print("all 11 runs per day:", list(tot), "-> per run per day:", [round(x / 11, 1) for x in tot])
    for d in range(6):
        idx = [i for i, m in enumerate(marks) if day_of(m) == d]
        print(f"{days[d]}: average pair overlap {np.mean([overlap[i] for i in idx]):.2f}, "
              f"different portfolios among 11 at day end {distinct[idx[-1]]}")
    print("first hour each copy held something different from the original:", split)
    chart(out, days)


def chart(out, days):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    plt.rcParams["text.parse_math"] = False
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    t = [datetime.strptime(x, "%Y-%m-%d %H:%M") for x in out["times"]]
    fig, axes = plt.subplots(3, 1, figsize=(13, 11), facecolor=SURF)
    tot = np.sum(list(out["trades_by_day"].values()), axis=0) / len(out["trades_by_day"])
    ax = axes[0]
    labels = [d + (" (15.5 h)" if i == 5 else "") for i, d in enumerate(days)]
    ax.bar(labels, tot, color="#2a78d6", width=0.6)
    for i, v in enumerate(tot):
        ax.annotate(f"{v:.1f}", (i, v), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9, color=INK)
    ax.set_title("Trades per run per day (average of the 11 identical runs; opening buys left out)", loc="left",
                 fontsize=12, color=INK, weight="bold")
    ax.set_ylabel("Buys + sells", color=INK2, fontsize=9)
    axes[1].plot(t, out["overlap"], color="#2a78d6", lw=2)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_title("How alike the 11 identical runs' holdings are (average of every pair: 1 = same 10 coins)",
                      loc="left", fontsize=12, color=INK, weight="bold")
    axes[1].set_ylabel("Overlap", color=INK2, fontsize=9)
    axes[2].plot(t, out["distinct_portfolios"], color="#eb6834", lw=2, drawstyle="steps-post")
    axes[2].set_ylim(0, 11.5)
    axes[2].set_title("How many different portfolios the 11 identical runs hold (1 = all identical, 11 = all different)",
                      loc="left", fontsize=12, color=INK, weight="bold")
    axes[2].set_ylabel("Portfolios", color=INK2, fontsize=9)
    for ax in axes:
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    for ax in axes[1:]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    axes[2].set_xlabel("Market time (UTC)", color=INK2, fontsize=9)
    fig.tight_layout()
    p = os.path.join(HERE, "copies_timing_chart.png")
    fig.savefig(p, dpi=110, facecolor=SURF)
    print(p)


if __name__ == "__main__":
    main()
