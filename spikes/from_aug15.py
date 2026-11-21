#!/usr/bin/env python3
"""
Same method as stories.py, but nothing before 15 Aug 2026 counts.

  training:   15 Aug - 21 Oct
  practice:   all 300 story sizes picked on 15 Aug - 21 Sep, run on 22 Sep - 21 Oct; the most gainful size is locked
  fixed number: that size's pick from all of 15 Aug - 21 Oct -> spikes/dip_top_aug15_winner.json (committed before the test)
  test:       python3 spikes/dip_top.py test aug15   (22 Oct - 20 Nov, one minute at a time)
  report:     python3 spikes/from_aug15.py report    (all 300 sizes on the last month, one run 15 Aug - 20 Nov, graphs)

    python3 spikes/from_aug15.py choose
"""
import json
import os
import sys

import numpy as np
import pandas as pd

from dip_top import COST, XS, YS, grid, simulate
from stories import pick

HERE = os.path.dirname(os.path.abspath(__file__))
T = lambda s: pd.Timestamp(s, tz="UTC")  # noqa: E731
START, SPLIT, CUT = T("2026-08-15"), T("2026-09-22"), T("2026-10-22")
SIZES = range(1, 301)


def load():
    df = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    assert df["time"].iloc[-1] < CUT
    return df


def choose():
    df = load()
    # bug check: the same code with the old start must reproduce stories.py's practice-3 number for size 85
    old = df[df["time"] < SPLIT]["close"].to_numpy(np.float64)
    mon = df[(df["time"] >= SPLIT) & (df["time"] < CUT)]["close"].to_numpy(np.float64)
    v_old, _ = grid(old, XS, YS)
    i, j, _ = pick(v_old, 85)
    assert abs(simulate(mon, XS[i], YS[j])[0] - 2401.31) < 0.01
    print("bug check: old start reproduces the earlier practice result for size 85 ($2,401.31)")

    d = df[df["time"] >= START]
    assert d["time"].iloc[0] >= START
    choose_part = d[d["time"] < SPLIT]["close"].to_numpy(np.float64)
    month = d[d["time"] >= SPLIT]["close"].to_numpy(np.float64)
    full = d["close"].to_numpy(np.float64)
    hold = month[-1] / month[0] * 1000 * (1 - COST) / (1 + COST)
    print(f"training {len(full):,} minutes {d['time'].iloc[0]} -> {d['time'].iloc[-1]}; practice: choose on "
          f"{len(choose_part):,} minutes before 22 Sep, run 22 Sep - 21 Oct (holding PEARL ${hold:,.2f})")

    v_c, _ = grid(choose_part, XS, YS)
    v_f, _ = grid(full, XS, YS)
    rows = []
    for k in SIZES:
        a, b, _ = pick(v_c, k)
        val, n = simulate(month, XS[a], YS[b])
        fa, fb, _ = pick(v_f, k)
        rows.append({"story_size": k, "practice_pick": f"{XS[a]:.0%}/{YS[b]:.0%}", "practice_$": round(val, 2),
                     "practice_trades": int(n), "fixed_pick": f"{XS[fa]:.0%}/{YS[fb]:.0%}",
                     "x": float(XS[fa]), "y": float(YS[fb])})
    r = pd.DataFrame(rows)
    best = r.loc[r["practice_$"].idxmax()]
    own, n = simulate(full, best["x"], best["y"])
    win = {"x": best["x"], "y": best["y"], "story_size": int(best["story_size"]),
           "practice_$": float(best["practice_$"]), "own_training_$": round(float(own), 2), "training_trades": int(n),
           "training": "15 Aug - 21 Oct"}
    r.to_csv(os.path.join(HERE, "aug15_choose.csv"), index=False)
    with open(os.path.join(HERE, "dip_top_aug15_winner.json"), "w") as f:
        json.dump(win, f, indent=2)
    print(r.sort_values("practice_$", ascending=False).head(12).drop(columns=["x", "y"]).to_string(index=False))
    print(f"\nlocked: story size {win['story_size']} (practice ${win['practice_$']:,.2f}); fixed number from "
          f"15 Aug - 21 Oct: buy after a {win['x']:.0%} fall, sell after a {win['y']:.0%} rise "
          f"(${own:,.2f} on the training months, {n} trades)")


def report():
    from all_months import run_with_log
    from all_stories import walk_minutes
    df = load()
    d = df[df["time"] >= START]
    with open(os.path.join(HERE, "dip_top_aug15_winner.json")) as f:
        win = json.load(f)
    r = pd.read_csv(os.path.join(HERE, "aug15_choose.csv"))
    t_test, c_test, hold_last = walk_minutes(8798)
    r["last_month_$"] = [round(simulate(c_test, x, y)[0], 2) for x, y in zip(r["x"], r["y"])]
    r.to_csv(os.path.join(HERE, "aug15_choose.csv"), index=False)

    times = d["time"].dt.strftime("%Y-%m-%d %H:%M").tolist() + t_test
    close = np.concatenate([d["close"].to_numpy(np.float64), c_test])
    end, trades, curve = run_with_log(times, close, win["x"], win["y"])
    hold = close[-1] / close[0] * 1000 * (1 - COST) / (1 + COST)
    print(f"locked fixed number: buy after a {win['x']:.0%} fall, sell after a {win['y']:.0%} rise")
    print(f"last month alone: ${simulate(c_test, win['x'], win['y'])[0]:,.2f} (holding PEARL ${hold_last:,.2f})")
    print(f"\nONE RUN, $1,000 on 15 Aug kept going to 20 Nov:")
    for t, a, p, v in trades:
        print(f"  {t}  {a:<4} at {p:.4f}  account ${v:,.2f}")
    print(f"  end: ${end:,.2f}   just holding PEARL: ${hold:,.2f}")
    s = r["last_month_$"]
    print(f"\nall 300 sizes on the last month (shown after locking): {(s > hold_last).sum()} beat holding, "
          f"{(s > 1000).sum()} made money, average ${s.mean():,.2f}, middle ${s.median():,.2f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(17, 11))
    a1.plot(r["story_size"], r["practice_$"], lw=1.8, label="practice month 22 Sep - 21 Oct (used to choose)")
    a1.plot(r["story_size"], r["last_month_$"], lw=1.8, label="last month 22 Oct - 20 Nov (shown after locking)")
    a1.axhline(hold_last, color="grey", ls=":", lw=2, label=f"holding PEARL, last month (\\${hold_last:,.0f})")
    a1.axhline(1000, color="black", ls="--", lw=0.8)
    a1.axvline(win["story_size"], color="red", lw=1.2, label=f"locked size {win['story_size']}")
    a1.set_xlabel("story size")
    a1.set_ylabel("\\$ (start \\$1,000)")
    a1.set_title("Training from 15 Aug only: every story size 1-300")
    a1.legend()
    a1.grid(alpha=0.3)
    cv = pd.DataFrame(curve, columns=["t", "price", "value"])
    cv["t"] = pd.to_datetime(cv["t"])
    a2.plot(cv["t"], cv["value"], lw=2, label=f"robot {win['x']:.0%} / {win['y']:.0%} (\\${end:,.0f})")
    a2.plot(cv["t"], 1000 * cv["price"] / close[0] * (1 - COST) / (1 + COST), color="grey", ls=":",
            label=f"just holding PEARL (\\${hold:,.0f})")
    for t, a, p, v in trades:
        a2.scatter([pd.Timestamp(t)], [v], color="green" if a == "BUY" else "red", s=70, zorder=3)
    a2.axvline(pd.Timestamp("2026-10-22"), color="red", lw=1, label="22 Oct: last month starts")
    a2.set_ylabel("\\$ (start \\$1,000 on 15 Aug)")
    a2.set_title("One run 15 Aug - 20 Nov (green = buy, red = sell)")
    a2.legend()
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "aug15_graph.png"), dpi=110)
    print("saved spikes/aug15_graph.png")


if __name__ == "__main__":
    {"choose": choose, "report": report}[sys.argv[1]]()
