#!/usr/bin/env python3
"""
Re-pick robot 2's fixed numbers using ONLY prices before 1 Oct 2026.

The numbers that were picked earlier after looking at Oct-Nov:
  window        2, 4 or 8 hours          (was 4)
  "at the low"  0.10, 0.23 or 0.50 %     (was 0.23)
  "near the high" 1.0, 1.8 or 3.0 %      (was 1.8)
  parts         everything on, library off, timing off, both off   (was both off)

Every run: $1,000 on 25 Jun, memory empty, all money in each buy, stopped at 30 Sep 23:59.
  Stage 1: the 27 combinations of the three numbers, everything on.
           Safest, not luckiest: a combination's score is the average of its own money and its
           neighbours' in the grid. The highest score wins.
  Stage 2: at the winning numbers, the 4 part choices. The most money on 30 Sep wins.

This program only opens data/PEARL-USDT_min1_before_oct.csv (made here from the history file,
keeping only minutes before 1 Oct). Results -> data/choose_before_oct.csv. The winning robot, as it
stands at 30 Sep 23:59, is saved to data/robot2_oct1.pkl for the Oct-Nov test.

    python3 choose_before_oct.py
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import csv
import itertools
import multiprocessing as mp
import pickle
import shutil
import time

import pandas as pd

from robot2 import Robot2, feed

CUT = "2026-10-01"
BEFORE = "data/PEARL-USDT_min1_before_oct.csv"
WINDOWS = [120, 240, 480]
LOWS = [0.10, 0.23, 0.50]
HIGHS = [1.0, 1.8, 3.0]
PARTS = {"everything on": {},
         "library off": {"borrow": False},
         "timing off": {"adapt_interval": False, "fixed_interval": 1},
         "both off": {"borrow": False, "adapt_interval": False, "fixed_interval": 1}}
TMP = "data/choose_tmp"


def make_before():
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    df = df[df["time"] < pd.Timestamp(CUT, tz="UTC")]
    df.to_csv(BEFORE, index=False, date_format="%Y-%m-%dT%H:%M:%SZ")
    return len(df), df["time"].iloc[-1]


def run(job):
    key, (w, a, h, parts) = job
    df = pd.read_csv(BEFORE, parse_dates=["time"])
    assert df["time"].iloc[-1] < pd.Timestamp(CUT, tz="UTC")
    t0 = time.time()
    r = feed(Robot2(risk=1.0, window=w, at_low=a, near_high=h, **PARTS[parts]), df)
    with open(f"{TMP}/{key}.pkl", "wb") as f:
        pickle.dump(r, f, protocol=pickle.HIGHEST_PROTOCOL)
    buys = sum(1 for t in r.trades if t[1] == "BUY")
    return key, (w, a, h, parts), r.value(), buys, time.time() - t0


def pool_run(jobs, results):
    with mp.Pool(4) as pool:
        for key, cfg, v, buys, sec in pool.imap_unordered(run, jobs):
            results[key] = (cfg, v, buys)
            print(f"  {len(results):>2}  window {cfg[0] // 60}h  low {cfg[1]:.2f}  high {cfg[2]:.1f}  "
                  f"{cfg[3]:<14} ${v:>9,.0f}  {buys:>3} buys  ({sec:.0f}s)", flush=True)


def main():
    os.makedirs(TMP, exist_ok=True)
    n, last = make_before()
    print(f"{n:,} minutes, last one {last}", flush=True)
    results = {}

    grid = list(itertools.product(range(3), range(3), range(3)))
    key = lambda i, j, k, p: f"{i}{j}{k}_{p.replace(' ', '_')}"
    print("stage 1: 27 combinations, everything on", flush=True)
    pool_run([(key(i, j, k, "everything on"), (WINDOWS[i], LOWS[j], HIGHS[k], "everything on"))
              for i, j, k in grid], results)

    money = {(i, j, k): results[key(i, j, k, "everything on")][1] for i, j, k in grid}
    score = {}
    for c in grid:
        near = [c] + [n for n in grid if sum(abs(x - y) for x, y in zip(c, n)) == 1]
        score[c] = sum(money[n] for n in near) / len(near)
    best = max(grid, key=lambda c: score[c])
    i, j, k = best
    print(f"chosen numbers: window {WINDOWS[i] // 60}h, low {LOWS[j]:.2f}, high {HIGHS[k]:.1f} "
          f"(score ${score[best]:,.0f}, own ${money[best]:,.0f})", flush=True)

    print("stage 2: the 4 part choices at those numbers", flush=True)
    pool_run([(key(i, j, k, p), (WINDOWS[i], LOWS[j], HIGHS[k], p)) for p in PARTS if p != "everything on"],
             results)
    parts = max(PARTS, key=lambda p: results[key(i, j, k, p)][1])
    win = key(i, j, k, parts)
    print(f"chosen parts: {parts} (${results[win][1]:,.0f} on 30 Sep)", flush=True)

    shutil.copy(f"{TMP}/{win}.pkl", "data/robot2_oct1.pkl")
    with open("data/choose_before_oct.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["window_h", "at_low_%", "near_high_%", "parts", "sep30_$", "buys", "grid_score_$", "chosen"])
        for kk, ((wn, a, h, p), v, buys) in sorted(results.items()):
            c = (WINDOWS.index(wn), LOWS.index(a), HIGHS.index(h))
            w.writerow([wn // 60, a, h, p, round(v), buys,
                        round(score[c]) if p == "everything on" else "", "yes" if kk == win else ""])
    shutil.rmtree(TMP)
    print(f"saved data/robot2_oct1.pkl: window {WINDOWS[i] // 60}h, low {LOWS[j]:.2f}, high {HIGHS[k]:.1f}, {parts}")


if __name__ == "__main__":
    main()
