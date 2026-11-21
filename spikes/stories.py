#!/usr/bin/env python3
"""
"Stories": lower the resolution of the buy/sell graph so one-off lucky peaks merge with their neighbours.

Story size k: the 99 x 300 graph (buy after 1..99% fall, sell after 1..300% rise) is cut into k x k blocks,
starting at 1%; each block's height = the average money of the pairs inside it. The pick for size k is the
middle pair of the highest block. k = 1 is the original graph, k = 300 is one block.

Which size is most gainful is measured on months the pick did not see:
  practice 1: choose on 25 Jun - 21 Jul, run on 22 Jul - 21 Aug
  practice 2: choose on 25 Jun - 21 Aug, run on 22 Aug - 21 Sep
  practice 3: choose on 25 Jun - 21 Sep, run on 22 Sep - 21 Oct
  gain = the three months one after another (end value x end value / 1,000 / 1,000)
The most gainful size is locked, its pick is taken from all training months (25 Jun - 21 Oct)
-> spikes/dip_top_stories_winner.json. Then the last month once: python3 spikes/dip_top.py test stories

    python3 spikes/stories.py   -> spikes/stories.csv, spikes/dip_top_stories_winner.json, spikes/stories_graph.png
"""
import json
import os

import numpy as np
import pandas as pd

from dip_top import XS, YS, grid, simulate

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = range(1, 301)
T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731
PRACTICE = [(T("2026-07-22"), T("2026-08-22")), (T("2026-08-22"), T("2026-09-22")), (T("2026-09-22"), T("2026-10-22"))]


def blocks(v, k):
    """Average of each k x k block (blocks start at the first row/column; the last ones may be smaller)."""
    n, m = v.shape
    rb, cb = np.arange(0, n, k), np.arange(0, m, k)
    s = np.add.reduceat(np.add.reduceat(v, rb, axis=0), cb, axis=1)
    cnt = np.outer(np.diff(np.append(rb, n)), np.diff(np.append(cb, m)))
    return s / cnt, rb, cb


def pick(v, k):
    """Middle pair of the highest block -> (row, col, block average)."""
    n, m = v.shape
    a, rb, cb = blocks(v, k)
    bi, bj = np.unravel_index(np.argmax(a), a.shape)
    r0, r1 = rb[bi], min(rb[bi] + k, n) - 1
    c0, c1 = cb[bj], min(cb[bj] + k, m) - 1
    return (r0 + r1) // 2, (c0 + c1) // 2, a[bi, bj]


def bug_checks():
    rng = np.random.default_rng(1)
    v = rng.random((99, 300))
    a, _, _ = blocks(v, 1)
    assert np.allclose(a, v), "size 1 must be the original graph"
    a, _, _ = blocks(v, 300)
    assert a.shape == (1, 1) and abs(a[0, 0] - v.mean()) < 1e-12, "size 300 must be one block"
    for k in (2, 7, 40, 99):
        a, rb, cb = blocks(v, k)
        for bi, bj in ((0, 0), (len(rb) - 1, len(cb) - 1), (len(rb) // 2, len(cb) // 3)):
            slow = v[rb[bi]:rb[bi] + k, cb[bj]:cb[bj] + k].mean()
            assert abs(a[bi, bj] - slow) < 1e-12, (k, bi, bj)
    w = np.zeros((99, 300))
    w[40:50, 100:110] = 5
    w[10, 10] = 100
    assert pick(w, 1)[:2] == (10, 10), "size 1 picks the single lucky peak"
    i, j, _ = pick(w, 10)
    assert 40 <= i < 50 and 100 <= j < 110, "size 10 must pick the thick area, not the lucky peak"


def main():
    bug_checks()
    print("bug checks passed: size 1 = original, size 300 = one block, blocks match a slow average, "
          "size 1 picks a lone peak, size 10 picks the thick area instead")
    df = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert df["time"].iloc[-1] < T("2026-10-22")

    rows = {k: {"story_size": k} for k in SIZES}
    holds = []
    for p, (start, end) in enumerate(PRACTICE, 1):
        choose = df[df["time"] < start]["close"].to_numpy(np.float64)
        month = df[(df["time"] >= start) & (df["time"] < end)]["close"].to_numpy(np.float64)
        v, _ = grid(choose, XS, YS)
        holds.append(month[-1] / month[0] * 1000 * (1 - 0.007) / (1 + 0.007))
        print(f"practice {p}: choose {len(choose):,} minutes before {start.date()}, run {start.date()} - "
              f"{(end - pd.Timedelta(days=1)).date()}; holding PEARL that month ${holds[-1]:,.2f}")
        for k in SIZES:
            i, j, _ = pick(v, k)
            val, n = simulate(month, XS[i], YS[j])
            rows[k].update({f"p{p}_buy_%": int(round(XS[i] * 100)), f"p{p}_sell_%": int(round(YS[j] * 100)),
                            f"p{p}_$": round(val, 2), f"p{p}_trades": int(n)})
    r = pd.DataFrame(list(rows.values()))
    r["gain_$"] = 1000 * r["p1_$"] / 1000 * r["p2_$"] / 1000 * r["p3_$"] / 1000
    hold_gain = 1000 * np.prod(np.array(holds) / 1000)

    full = df["close"].to_numpy(np.float64)
    v_full, _ = grid(full, XS, YS)
    for k in SIZES:
        i, j, _ = pick(v_full, k)
        r.loc[r["story_size"] == k, ["final_buy_%", "final_sell_%"]] = (int(round(XS[i] * 100)), int(round(YS[j] * 100)))
    best_k = int(r.loc[r["gain_$"].idxmax(), "story_size"])
    i, j, area = pick(v_full, best_k)
    own, n = simulate(full, XS[i], YS[j])
    win = {"x": float(XS[i]), "y": float(YS[j]), "story_size": best_k, "block_average_$": round(float(area), 2),
           "own_training_$": round(float(own), 2), "training_trades": int(n),
           "practice_gain_$": round(float(r["gain_$"].max()), 2), "holding_practice_gain_$": round(float(hold_gain), 2)}
    r.to_csv(os.path.join(HERE, "stories.csv"), index=False)
    with open(os.path.join(HERE, "dip_top_stories_winner.json"), "w") as f:
        json.dump(win, f, indent=2)

    show = r[r["story_size"].isin([1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300])]
    print(show.to_string(index=False))
    top = r.sort_values("gain_$", ascending=False).head(8)
    print("\nmost gainful story sizes over the three practice months:")
    print(top[["story_size", "p1_$", "p2_$", "p3_$", "gain_$", "final_buy_%", "final_sell_%"]].to_string(index=False))
    print(f"holding PEARL through the same three months: ${hold_gain:,.2f}")
    print(f"\nlocked: story size {best_k}; pick from all training months: buy after a {win['x']:.0%} fall, "
          f"sell after a {win['y']:.0%} rise (block average ${area:,.2f}, this pair alone ${own:,.2f}, {n} trades)")
    return r, v_full, win, hold_gain


def graph(r, v_full, win, hold_gain):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    k = win["story_size"]
    fig = plt.figure(figsize=(22, 8.5))
    ax = fig.add_subplot(1, 2, 1)
    ax.plot(r["story_size"], r["gain_$"], color="black", lw=2, label="spike robot, 3 practice months in a row")
    ax.axhline(hold_gain, color="tab:orange", ls=":", label=f"holding PEARL, same 3 months (\\${hold_gain:,.0f})")
    ax.axhline(1000, color="grey", ls="--", label="\\$1,000 start")
    ax.axvline(k, color="red", lw=2, label=f"most gainful story size: {k}")
    ax.set_xscale("log")
    ax.set_xlabel("story size k (k x k neighbouring buy/sell pairs merged into one; 1 = full detail)")
    ax.set_ylabel("\\$1,000 run through 22 Jul - 21 Oct, each month picked before it")
    ax.set_title("Every story size 1-300, judged on months the pick could not see")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3, which="both")

    a, rb, cb = blocks(v_full, k)
    xs = np.array([XS[min(b + k, len(XS)) - 1] + XS[b] for b in rb]) / 2 * 100
    ys = np.array([YS[min(b + k, len(YS)) - 1] + YS[b] for b in cb]) / 2 * 100
    ax = fig.add_subplot(1, 2, 2, projection="3d")
    if a.shape[0] > 1 and a.shape[1] > 1:
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        ax.plot_surface(X, Y, a, cmap="viridis", linewidth=0.3, edgecolor="k", alpha=0.9)
    else:
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        ax.bar3d(X.ravel(), Y.ravel(), 0, 3, 3, a.ravel())
    ax.scatter([win["x"] * 100], [win["y"] * 100], [win["block_average_$"]], color="red", s=80, depthshade=False)
    ax.set_xlabel("buy after PEARL falls this % from its top")
    ax.set_ylabel("sell after PEARL rises this % above the buy")
    ax.set_zlabel("block average \\$ (training months)")
    ax.set_title(f"All training months at story size {k} ({a.shape[0]} x {a.shape[1]} blocks)\nred dot = locked pick: "
                 f"buy after {win['x']:.0%} fall, sell after {win['y']:.0%} rise")
    ax.view_init(elev=30, azim=-125)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "stories_graph.png"), dpi=110)
    print("saved spikes/stories_graph.png")


if __name__ == "__main__":
    graph(*main())
