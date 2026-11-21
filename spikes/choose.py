#!/usr/bin/env python3
"""
Search the 27,783 spike robots on the training months only and pick the winner (spikes/PLAN.md).

    python3 spikes/choose.py
      -> spikes/choose.csv     every robot: choose-period and check-period money, score
      -> spikes/winner.json    the winning settings
      -> spikes/spike_types.txt the two kinds of spike at the winner's theta
"""
import itertools
import json
import os
import time

import numpy as np
import pandas as pd
from numba import njit, prange

from spikes import simulate, tables

HERE = os.path.dirname(os.path.abspath(__file__))
THETAS = [0.02, 0.03, 0.04, 0.05, 0.07, 0.10, 0.15]
PS = [0.01] + [i / 100 for i in range(5, 100, 5)] + [0.99]
XS = [0.02, 0.04, 0.08]
STOPS = [0.0, 0.10, 0.20]
SPLIT = pd.Timestamp("2026-09-22", tz="UTC")


@njit(parallel=True, cache=True)
def run_all(close, theta, up_odds, down_odds, pb, ps, stops):
    n = pb.shape[0]
    val = np.empty(n)
    trd = np.empty(n, dtype=np.int64)
    for i in prange(n):
        val[i], trd[i] = simulate(close, theta, up_odds, down_odds, pb[i], ps[i], stops[i])
    return val, trd


def two_kinds(sizes):
    """Split spike sizes into small and extreme (2-means on log size)."""
    z = np.log(sizes)
    a, b = np.percentile(z, 25), np.percentile(z, 90)
    for _ in range(100):
        big = np.abs(z - b) < np.abs(z - a)
        a2, b2 = z[~big].mean(), z[big].mean()
        if abs(a2 - a) + abs(b2 - b) < 1e-12:
            break
        a, b = a2, b2
    return sizes[~big], sizes[big]


def main():
    df = pd.read_csv(os.path.join(HERE, "data/train.csv"), parse_dates=["time"])
    choose = df[df["time"] < SPLIT]["close"].to_numpy(np.float64)
    check = df[df["time"] >= SPLIT]["close"].to_numpy(np.float64)
    print(f"choose {len(choose):,} minutes to {df[df['time'] < SPLIT]['time'].iloc[-1]}, "
          f"check {len(check):,} minutes to {df['time'].iloc[-1]}", flush=True)

    pairs = list(itertools.product(range(len(PS)), range(len(PS)), range(len(STOPS))))
    pb = np.array([PS[i] for i, _, _ in pairs])
    ps = np.array([PS[j] for _, j, _ in pairs])
    st = np.array([STOPS[k] for _, _, k in pairs])
    rows, t0 = [], time.time()
    for a, th in enumerate(THETAS):
        for c, x in enumerate(XS):
            up_o, down_o, ups, downs = tables(choose, th, x)
            v1, n1 = run_all(choose, th, up_o, down_o, pb, ps, st)
            v2, n2 = run_all(check, th, up_o, down_o, pb, ps, st)
            for m, (i, j, k) in enumerate(pairs):
                rows.append((a, i, j, c, k, th, PS[i], PS[j], x, STOPS[k], v1[m], n1[m], v2[m], n2[m]))
        print(f"  theta {th:.0%}: {len(ups)} up-spikes, {len(downs)} down-spikes in the choose months "
              f"({time.time() - t0:.0f}s)", flush=True)

    r = pd.DataFrame(rows, columns=["ti", "bi", "si", "xi", "ki", "theta", "p_buy", "p_sell", "x", "stop",
                                    "choose_$", "choose_trades", "check_$", "check_trades"])
    r["both"] = np.sqrt(r["choose_$"] / 1000 * r["check_$"] / 1000)
    dims = (len(THETAS), len(PS), len(PS), len(XS), len(STOPS))
    cube = np.full(dims, np.nan)
    idx = tuple(r[c].to_numpy() for c in ("ti", "bi", "si", "xi", "ki"))
    cube[idx] = r["both"].to_numpy()
    total, count = cube.copy(), np.ones(dims)
    for ax in range(5):
        for sh in (1, -1):
            nb = np.roll(cube, sh, axis=ax)
            edge = [slice(None)] * 5
            edge[ax] = 0 if sh == 1 else -1
            nb[tuple(edge)] = np.nan
            ok = ~np.isnan(nb)
            total[ok] += nb[ok]
            count[ok] += 1
    r["score"] = (total / count)[idx]
    r = r.sort_values("score", ascending=False)
    r.drop(columns=["ti", "bi", "si", "xi", "ki"]).to_csv(os.path.join(HERE, "choose.csv"), index=False)

    w = r.iloc[0]
    win = {k: float(w[k]) for k in ("theta", "p_buy", "p_sell", "x", "stop")}
    win.update({"choose_$": round(float(w["choose_$"]), 2), "check_$": round(float(w["check_$"]), 2),
                "score": round(float(w["score"]), 4)})
    full = df["close"].to_numpy(np.float64)
    up_o, down_o, ups, downs = tables(full, win["theta"], win["x"])
    v, n = simulate(full, win["theta"], up_o, down_o, win["p_buy"], win["p_sell"], win["stop"])
    win["all_training_$"], win["all_training_trades"] = round(float(v), 2), int(n)
    with open(os.path.join(HERE, "winner.json"), "w") as f:
        json.dump(win, f, indent=2)

    with open(os.path.join(HERE, "spike_types.txt"), "w") as f:
        for name, s in (("up", ups), ("down", downs)):
            small, big = two_kinds(s)
            f.write(f"{name}-spikes at theta {win['theta']:.0%}, all training months: {len(s)}\n")
            for kind, part in (("small", small), ("extreme", big)):
                f.write(f"  {kind:<8} {len(part):>4} spikes, {np.min(part):6.1%} to {np.max(part):6.1%}, "
                        f"middle {np.median(part):6.1%}\n")
    print(open(os.path.join(HERE, "spike_types.txt")).read())

    hold_c = choose[-1] / choose[0] * 1000 * (1 - COST_2)
    hold_k = check[-1] / check[0] * 1000 * (1 - COST_2)
    print(f"just holding: choose months ${hold_c:,.0f}, check month ${hold_k:,.0f}")
    print("top 10 by score:")
    print(r.drop(columns=["ti", "bi", "si", "xi", "ki"]).head(10).to_string(index=False))
    print("winner:", json.dumps(win))


COST_2 = 0.014

if __name__ == "__main__":
    main()
