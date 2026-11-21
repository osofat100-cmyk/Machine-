#!/usr/bin/env python3
"""
How much to smooth, decided by the training months alone (the user's four steps).

1. Hide part of the training: two practice tests
     A: choose on 25 Jun - 21 Aug, hidden month 22 Aug - 21 Sep
     B: choose on 25 Jun - 21 Sep, hidden month 22 Sep - 21 Oct
2. Every smoothing level W = 1..100%: average each buy/sell pair with all pairs within +-W% buy and +-W% sell,
   pick the middle of the highest area on the choose months, run that pair on the hidden month
   (fresh $1,000, the same way the last-month test starts).
3. Safest level = the one whose WORST practice result is highest
   (tie -> higher average of the two -> the middle level of the tie).
4. Lock that level, pick the pair from all training months (25 Jun - 21 Oct) -> spikes/dip_top_safe_winner.json.
   Then: python3 spikes/dip_top.py test safe   (the last month, one minute at a time)

    python3 spikes/safe_smooth.py   -> spikes/safe_smooth.csv, spikes/dip_top_safe_winner.json, spikes/safe_smooth_graph.png
"""
import json
import os

import numpy as np
import pandas as pd

from dip_top import XS, YS, grid, simulate

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS = range(1, 101)
T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731
FOLDS = [("A", T("2026-08-22"), T("2026-09-22")), ("B", T("2026-09-22"), T("2026-10-22"))]


def box_mean(v, w):
    """Average of every cell within +-w rows and +-w columns (fewer at the edges)."""
    n, m = v.shape
    s = np.zeros((n + 1, m + 1))
    s[1:, 1:] = v.cumsum(0).cumsum(1)
    i0 = np.clip(np.arange(n) - w, 0, n)
    i1 = np.clip(np.arange(n) + w + 1, 0, n)
    j0 = np.clip(np.arange(m) - w, 0, m)
    j1 = np.clip(np.arange(m) + w + 1, 0, m)
    total = s[i1][:, j1] - s[i0][:, j1] - s[i1][:, j0] + s[i0][:, j0]
    count = (i1 - i0)[:, None] * (j1 - j0)[None, :]
    return total / count


def pick(v, w):
    a = box_mean(v, w)
    i, j = np.unravel_index(np.argmax(a), a.shape)
    return i, j, a[i, j]


def check_box_mean():
    rng = np.random.default_rng(0)
    v = rng.random((99, 300))
    for w in (1, 5, 37, 100):
        a = box_mean(v, w)
        for i, j in ((0, 0), (50, 150), (98, 299), (3, 297)):
            b = v[max(0, i - w):i + w + 1, max(0, j - w):j + w + 1].mean()
            assert abs(a[i, j] - b) < 1e-9, (w, i, j)


def main():
    check_box_mean()
    print("bug check: fast area average matches the slow one")
    df = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert df["time"].iloc[-1] < T("2026-10-22")
    full = df["close"].to_numpy(np.float64)

    v_full, _ = grid(full, XS, YS)
    i, j, _ = pick(v_full, 5)
    with open(os.path.join(HERE, "dip_top_smooth_winner.json")) as f:
        old = json.load(f)
    assert (XS[i], YS[j]) == (old["x"], old["y"]), "W=5 must give the same pick as before"
    print("bug check: level 5% gives the same pick as the earlier +-5% run (38% / 272%)")

    rows = {w: {"level_%": w} for w in LEVELS}
    for name, start, end in FOLDS:
        choose = df[df["time"] < start]["close"].to_numpy(np.float64)
        hidden = df[(df["time"] >= start) & (df["time"] < end)]["close"].to_numpy(np.float64)
        assert len(hidden) == (end - start).total_seconds() / 60
        v, _ = grid(choose, XS, YS)
        hold = hidden[-1] / hidden[0] * 1000 * (1 - 0.007) / (1 + 0.007)
        print(f"practice {name}: choose {len(choose):,} minutes to {start.date()}, hidden month "
              f"{start.date()} - {(end - pd.Timedelta(days=1)).date()} ({len(hidden):,} minutes); "
              f"holding PEARL in the hidden month: ${hold:,.2f}")
        for w in LEVELS:
            a, b, _ = pick(v, w)
            val, n = simulate(hidden, XS[a], YS[b])
            rows[w].update({f"{name}_buy_%": int(round(XS[a] * 100)), f"{name}_sell_%": int(round(YS[b] * 100)),
                            f"{name}_hidden_$": round(val, 2), f"{name}_trades": int(n)})
        rows["hold_" + name] = hold
    holds = {k: rows.pop(k) for k in ("hold_A", "hold_B")}

    r = pd.DataFrame(list(rows.values()))
    r["worst_$"] = r[["A_hidden_$", "B_hidden_$"]].min(axis=1)
    r["average_$"] = r[["A_hidden_$", "B_hidden_$"]].mean(axis=1)
    best = r[r["worst_$"] == r["worst_$"].max()]
    best = best[best["average_$"] == best["average_$"].max()]
    level = int(best["level_%"].iloc[len(best) // 2])
    tied = list(best["level_%"])

    i, j, area = pick(v_full, level)
    own, n = simulate(full, XS[i], YS[j])
    win = {"x": float(XS[i]), "y": float(YS[j]), "level_%": level, "tied_levels": tied,
           "area_average_$": round(float(area), 2), "own_training_$": round(float(own), 2), "training_trades": int(n),
           "practice_A_$": float(best["A_hidden_$"].iloc[0]), "practice_B_$": float(best["B_hidden_$"].iloc[0])}
    for w in LEVELS:
        a, b, _ = pick(v_full, w)
        r.loc[r["level_%"] == w, ["final_buy_%", "final_sell_%"]] = (int(round(XS[a] * 100)), int(round(YS[b] * 100)))
    r.to_csv(os.path.join(HERE, "safe_smooth.csv"), index=False)
    with open(os.path.join(HERE, "dip_top_safe_winner.json"), "w") as f:
        json.dump(win, f, indent=2)

    print(r[r["level_%"].isin([1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100])].to_string(index=False))
    print(f"\nsafest level: +-{level}% (worst practice ${best['worst_$'].iloc[0]:,.2f}, average "
          f"${best['average_$'].iloc[0]:,.2f}; tied levels {tied[0]}-{tied[-1]}: {len(tied)})")
    print(f"locked pick from all training months: buy after a {win['x']:.0%} fall, sell after a {win['y']:.0%} rise "
          f"(area average ${area:,.2f}, this pair alone ${own:,.2f}, {n} trades)")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(21, 8.5))
    ax = fig.add_subplot(1, 2, 1)
    ax.plot(r["level_%"], r["A_hidden_$"], label="practice A: hidden 22 Aug - 21 Sep")
    ax.plot(r["level_%"], r["B_hidden_$"], label="practice B: hidden 22 Sep - 21 Oct")
    ax.plot(r["level_%"], r["worst_$"], color="black", lw=2.5, label="worse of the two (what is maximised)")
    ax.axhline(holds["hold_A"], color="tab:blue", ls=":", label=f"holding PEARL, A (\\${holds['hold_A']:,.0f})")
    ax.axhline(holds["hold_B"], color="tab:orange", ls=":", label=f"holding PEARL, B (\\${holds['hold_B']:,.0f})")
    ax.axhline(1000, color="grey", ls="--", label="\\$1,000 start")
    ax.axvspan(tied[0] - 0.5, tied[-1] + 0.5, color="red", alpha=0.12)
    ax.axvline(level, color="red", lw=2, label=f"chosen level +-{level}%")
    ax.set_xlabel("smoothing level: average over +-this % buy and sell")
    ax.set_ylabel("\\$ at the end of the hidden month (start \\$1,000)")
    ax.set_title("Steps 1-3: every smoothing level 1-100%, tested on months it could not see")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    ax = fig.add_subplot(1, 2, 2, projection="3d")
    X, Y = np.meshgrid(XS * 100, YS * 100, indexing="ij")
    a = box_mean(v_full, level)
    ax.plot_surface(X, Y, a, cmap="viridis", linewidth=0, antialiased=True, alpha=0.95)
    ax.scatter([win["x"] * 100], [win["y"] * 100], [area], color="red", s=80, depthshade=False)
    ax.set_xlabel("buy after PEARL falls this % from its top")
    ax.set_ylabel("sell after PEARL rises this % above the buy")
    ax.set_zlabel("area-average \\$ (training months)")
    ax.set_title(f"Step 4: all training months smoothed at +-{level}%\nred dot = locked pick: buy after "
                 f"{win['x']:.0%} fall, sell after {win['y']:.0%} rise")
    ax.view_init(elev=30, azim=-125)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "safe_smooth_graph.png"), dpi=110)
    print("saved spikes/safe_smooth_graph.png")


if __name__ == "__main__":
    main()
