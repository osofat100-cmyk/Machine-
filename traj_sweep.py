#!/usr/bin/env python3
"""
Plan step: choose the watcher's sensitivity without hindsight.

Runs robot 2 (cold start 25 Jun, trajectory resets) at many sensitivity levels, plus a robot
that never resets. Levels are judged on 25 Jun - 30 Sep only; the chosen level is then checked
on 1 Oct - 20 Nov, which played no part in choosing it.

    python3 traj_sweep.py            # -> data/traj_sweep.csv, data/traj_sweep_curves.npz, traj_sweep.png
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import csv
import multiprocessing as mp
import sys
import time

import numpy as np
import pandas as pd

from engine import Engine, feed

LEVELS = [3, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 40]
TRAIN_END = "2026-10-01"
DF = None


def load():
    return pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])


def run(cfg):
    global DF
    if DF is None:
        DF = load()
    name, kw = cfg
    t0 = time.time()
    e = feed(Engine(**kw), DF)
    rec = np.array(e.rec, dtype=float)
    print(f"  {name:<14} done in {time.time() - t0:.0f}s: ${e.value():,.0f}, {len(e.library) + 1} trajectories",
          flush=True)
    return name, {"rec": rec, "final": e.value(), "trades": len(e.trades), "kap": e.kap[:e.n].copy(),
                  "trajectories": len(e.library) + 1, "F": e.F.copy(), "trade_list": e.trades}


def middle_of_best_stretch(values):
    """Index of the middle of the biggest run of values at or above their average."""
    v = np.asarray(values, float)
    high = np.concatenate(([0], (v >= v.mean()).astype(int), [0]))
    d = np.diff(high)
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1
    lengths = ends - starts + 1
    best = max(np.flatnonzero(lengths == lengths.max()), key=lambda q: v[starts[q]:ends[q] + 1].mean())
    return int((starts[best] + ends[best]) // 2), (int(starts[best]), int(ends[best]))


def main():
    cfgs = [(f"eta {h}", {"eta": h}) for h in LEVELS] + [("never reset", {"resets": False})]
    print(f"{len(cfgs)} runs on {mp.cpu_count()} cores", flush=True)
    with mp.Pool(mp.cpu_count()) as pool:
        out = dict(pool.map(run, cfgs, chunksize=1))

    df = load()
    ts = df["time"].values.astype("datetime64[m]").astype(np.int64)
    cl = df["close"].values.astype(float)
    cut_ts = int(np.datetime64(TRAIN_END, "m").astype(np.int64))
    k_cut = int(np.searchsorted(ts, cut_ts)) - 1                 # last minute of 30 Sep
    k0 = 240
    kap = out[cfgs[0][0]]["kap"]                                  # cost per side on each minute
    hold = lambda a, z: 1000 * cl[z] * (1 - kap[z]) / (cl[a] * (1 + kap[a]))
    hold_train, hold_test, hold_all = hold(k0, k_cut), hold(k_cut, len(cl) - 1), hold(k0, len(cl) - 1)

    rows = []
    for name, _ in cfgs:
        o = out[name]
        rec = o["rec"]
        train = rec[rec[:, 0] <= ts[k_cut]][-1, 1]
        rows.append([name, o["trajectories"], o["trades"], train, 1000 * o["final"] / train, o["final"]])
    with open("data/traj_sweep.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "trajectories", "robot_trades", "train_$_30Sep", "test_$_per_1000_1Oct-20Nov", "final_$"])
        for r in rows:
            w.writerow(r[:3] + [round(x, 2) for x in r[3:]])
        w.writerow(["just holding", "", "", round(hold_train, 2), round(hold_test, 2), round(hold_all, 2)])
    np.savez_compressed("data/traj_sweep_curves.npz", **{n.replace(" ", "_"): out[n]["rec"] for n, _ in cfgs})
    import pickle
    with open("data/traj_sweep_trades.pkl", "wb") as f:
        pickle.dump({n: out[n]["trade_list"] for n, _ in cfgs}, f)

    print(f"\n{'run':<14}{'trajectories':>13}{'trades':>8}{'TRAIN to 30 Sep':>17}{'TEST 1 Oct-20 Nov':>19}{'whole period':>14}")
    for r in rows:
        print(f"{r[0]:<14}{r[1]:>13}{r[2]:>8}{f'${r[3]:,.0f}':>17}{f'${r[4]:,.0f}':>19}{f'${r[5]:,.0f}':>14}")
    print(f"{'just holding':<14}{'':>13}{'':>8}{f'${hold_train:,.0f}':>17}{f'${hold_test:,.0f}':>19}{f'${hold_all:,.0f}':>14}")
    lv = [r for r in rows if r[0].startswith("eta")]
    mid, (a, z) = middle_of_best_stretch([r[3] for r in lv])
    print(f"\nchosen on TRAIN only: biggest high stretch is {lv[a][0]} .. {lv[z][0]}; middle = {lv[mid][0]}")
    print(f"  its TEST result: ${lv[mid][4]:,.0f} per $1,000   (just holding ${hold_test:,.0f}, "
          f"never reset ${rows[-1][4]:,.0f})")


def plot():
    """Draw traj_sweep.png from the saved results."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    blue, orange = "#2a78d6", "#eb6834"
    plt.rcParams.update({"font.size": 12, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    res = pd.read_csv("data/traj_sweep.csv")
    curves = np.load("data/traj_sweep_curves.npz")
    lv = res[res["run"].str.startswith("eta")].reset_index(drop=True)
    mid, _ = middle_of_best_stretch(lv["train_$_30Sep"].values)
    chosen = lv["run"][mid]
    hold = res[res["run"] == "just holding"].iloc[0]
    never = res[res["run"] == "never reset"].iloc[0]

    df = load()
    ts = df["time"].values.astype("datetime64[m]").astype(np.int64)
    cl = df["close"].values.astype(float)
    t = lambda rec: rec[:, 0].astype("datetime64[m]").astype("datetime64[s]").astype(object)
    rec_n, rec_c = curves["never_reset"], curves[chosen.replace(" ", "_")]
    hold_curve = 1000 * cl[np.searchsorted(ts, rec_n[:, 0].astype(np.int64))] / cl[240]
    cut = np.datetime64(TRAIN_END).astype("datetime64[s]").astype(object)
    thin = np.datetime64("2026-09-21").astype("datetime64[s]").astype(object)

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 11), facecolor=surface,
                                 gridspec_kw={"height_ratios": [1.5, 1], "hspace": 0.3})
    for a_ in (ax, bx):
        a_.set_facecolor(surface)
        a_.grid(axis="y", color=gridc, lw=0.8)
        for side in ("top", "right"):
            a_.spines[side].set_visible(False)
        a_.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.axvspan(t(rec_n)[0], thin, color="#f0efec", lw=0)
    ax.text(t(rec_n)[40], 6500, "thin market until 21 Sep: a typical minute traded $5-13,\nso these trades could not really be made at this size",
            fontsize=10, color=ink2, va="top")
    ax.axvline(cut, color=ink2, lw=1.2, ls=(0, (2, 2)))
    ax.text(cut, 6500, "  unseen test period", fontsize=10, color=ink2, va="top")
    ax.plot(t(rec_n), hold_curve, color=muted, lw=1.6, ls=(0, (5, 3)), label="just holding PEARL")
    ax.plot(t(rec_n), rec_n[:, 1], color=blue, lw=1.9, label="robot 2, never resets")
    ax.plot(t(rec_c), rec_c[:, 1], color=orange, lw=1.9,
            label=f"robot 2 with trajectory resets (sensitivity {chosen.split()[1]}, chosen on data before 1 Oct)")
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.88), frameon=False, fontsize=10.5)
    ax.set_ylim(0, 6800)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_ylabel("account value ($)")
    ax.set_title("Robot 2 from 25 Jun with $1,000 and no data", loc="left", fontsize=13, pad=10)

    names = [r.split()[1] for r in lv["run"]] + ["never\nresets"]
    vals = list(lv["test_$_per_1000_1Oct-20Nov"]) + [never["test_$_per_1000_1Oct-20Nov"]]
    cols = [orange if r == chosen else "#9ec5f4" for r in lv["run"]] + [blue]
    bx.bar(range(len(vals)), vals, color=cols, width=0.66)
    for k, v in enumerate(vals):
        bx.text(k, v + 20, f"${v:,.0f}", ha="center", va="bottom", fontsize=9, color=ink)
    hv = hold["test_$_per_1000_1Oct-20Nov"]
    bx.axhline(hv, color=ink2, lw=1.4, ls=(0, (5, 3)))
    bx.text(-0.4, hv + 25, f"just holding ${hv:,.0f}", fontsize=10, color=ink2, va="bottom")
    bx.axhline(1000, color=muted, lw=1)
    bx.text(-0.4, 1000 + 25, "start $1,000", fontsize=10, color=ink2, va="bottom")
    bx.set_xticks(range(len(vals)))
    bx.set_xticklabels(names)
    bx.set_ylim(0, 1950)
    bx.set_xlabel("watcher sensitivity (low = resets often, high = resets rarely)")
    bx.set_title("Unseen test, 1 Oct - 20 Nov: what $1,000 became at each sensitivity (orange = the one chosen beforehand)",
                 loc="left", fontsize=12, pad=10)
    fig.savefig("traj_sweep.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("saved traj_sweep.png")


if __name__ == "__main__":
    if "plot" not in sys.argv:
        main()
    plot()
