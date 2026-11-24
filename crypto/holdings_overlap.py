#!/usr/bin/env python3
"""
Do the crypto golden-rule runs make the same choices? Rebuilds which coins every finished run held at every hourly
mark (replayed through the test server by flat_ground_replay.replay, checked to the cent), then measures overlap:

  overlap(A, B) at an hour = coins held by both / coins held by either (Jaccard: 1 = identical, 0 = nothing shared)

It reports, per pair of runs, the average overlap in the first 12 hours and afterwards, plus how many different
coins each run ever held and how many coins all runs held at once.

    python3 crypto/holdings_overlap.py   -> crypto/holdings_overlap.json, crypto/holdings_overlap_chart.png
"""
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flat_ground_replay as F  # noqa: E402


def main():
    steps, groups, runs, values = F.replay()
    marks = sorted({i for i, st in enumerate(steps) if i >= F.WARMUP and st["time"].endswith(":31")} | {len(steps) - 1})
    held = {}
    for name, r in runs.items():
        cur, t, out = set(), 0, []
        for kidx in range(len(steps)):
            while t < len(r["trades"]) and r["trades"][t][0] == kidx:
                _, sold, bought = r["trades"][t]
                cur = (cur - set(sold)) | set(bought)
                t += 1
            if kidx in set(marks):
                out.append(frozenset(cur))
        held[name] = out
    label = {n: f"{'First' if r['v'] == 'v4a' else 'Second'} {r['k']}" for n, r in runs.items()}
    names = sorted(runs, key=lambda n: (runs[n]["v"], runs[n]["k"]))
    jac = lambda a, b: len(a & b) / len(a | b) if a | b else 1.0
    early = [i for i, m in enumerate(marks) if m - marks[0] < 12 * 60]
    late = [i for i, m in enumerate(marks) if m - marks[0] >= 12 * 60]
    pairs = []
    for a, b in itertools.combinations(names, 2):
        e = np.mean([jac(held[a][i], held[b][i]) for i in early])
        l = np.mean([jac(held[a][i], held[b][i]) for i in late])
        pairs.append({"a": label[a], "b": label[b], "early": float(e), "late": float(l)})
    common = [len(frozenset.intersection(*[held[n][i] for n in names])) for i in range(len(marks))]
    distinct = {label[n]: len(set().union(*held[n])) for n in names}
    mean_curve = [float(np.mean([jac(held[a][i], held[b][i]) for a, b in itertools.combinations(names, 2)]))
                  for i in range(len(marks))]
    out = {"pairs": pairs, "coins_all_runs_share": common, "distinct_coins_ever_held": distinct,
           "mean_overlap_by_hour": mean_curve, "times": [steps[i]["time"] for i in marks]}
    json.dump(out, open(os.path.join(HERE, "holdings_overlap.json"), "w"), indent=1)
    print("mean overlap all pairs: first 12h %.2f, after %.2f" % (np.mean([p["early"] for p in pairs]),
                                                                  np.mean([p["late"] for p in pairs])))
    focus = {"First 60", "Second 15", "Second 30", "First 15", "First 30", "Second 60"}
    for p in sorted(pairs, key=lambda p: -p["late"]):
        if p["a"] in focus and p["b"] in focus:
            print(f"{p['a']:10s} vs {p['b']:10s} early {p['early']:.2f} late {p['late']:.2f}")
    print("coins all 15 runs held at once: start", common[0], "after 12h", common[12], "after 24h", common[24],
          "end", common[-1])
    print("distinct coins ever held:", distinct)
    print("first-hour actions identical across runs:",
          len({json.dumps(json.loads(r["saved"][0]["actions"])) for r in runs.values()}) == 1)
    chart(out)


def chart(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    plt.rcParams["text.parse_math"] = False
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    t = [datetime.strptime(x, "%Y-%m-%d %H:%M") for x in out["times"]]
    fig, axes = plt.subplots(2, 1, figsize=(13, 7.5), facecolor=SURF, sharex=True)
    axes[0].plot(t, out["mean_overlap_by_hour"], color="#2a78d6", lw=2)
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("How alike are the 15 runs' holdings? (average overlap of every pair: 1 = identical, 0 = nothing shared)",
                      loc="left", fontsize=12, color=INK, weight="bold")
    axes[0].set_ylabel("Average overlap", color=INK2, fontsize=9)
    axes[1].plot(t, out["coins_all_runs_share"], color="#eb6834", lw=2)
    axes[1].set_ylim(0, 10.5)
    axes[1].set_title("Coins held by ALL 15 runs at the same time (out of 10)", loc="left", fontsize=12, color=INK,
                      weight="bold")
    axes[1].set_ylabel("Coins", color=INK2, fontsize=9)
    for ax in axes:
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    axes[1].set_xlabel("Market time (UTC)", color=INK2, fontsize=9)
    fig.tight_layout()
    p = os.path.join(HERE, "holdings_overlap_chart.png")
    fig.savefig(p, dpi=110, facecolor=SURF)
    print(p)


if __name__ == "__main__":
    main()
