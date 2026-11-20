#!/usr/bin/env python3
"""
How fragile is robot 2? Each run changes ONE thing and reports the money for
  TRAIN  25 Jun - 30 Sep   (thin market: fills there were not achievable at size)
  TEST    1 Oct - 20 Nov   (liquid market; per $1,000 at the start of the period)

    python3 robustness.py              # -> data/robustness.csv   (about 15 minutes)

None of these runs is used to choose anything. They show how much the result depends on
assumptions (fill prices, costs), on the rule's fixed numbers, and on the start date.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import csv
import multiprocessing as mp
import sys

import numpy as np
import pandas as pd

from engine import Engine, feed

TRAIN_END = "2026-10-01"
DF = None


def run(cfg):
    global DF
    if DF is None:
        DF = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    name, kw, start = cfg
    df = DF if start is None else DF[DF["time"] >= pd.Timestamp(start, tz="UTC")]
    e = feed(Engine(**kw), df)
    rec = np.array(e.rec, dtype=float)
    cut = int(np.datetime64(TRAIN_END, "m").astype(np.int64))
    before = rec[rec[:, 0] < cut]
    train = before[-1, 1] if len(before) else 1000.0
    k0, kc, kz = e.window, int(np.searchsorted(e.ts[:e.n], cut)) - 1, e.n - 1
    hold = lambda a, z: 1000 * e.cl[z] * (1 - e.kap[z]) / (e.cl[a] * (1 + e.kap[a]))
    out = (name, train, 1000 * e.value() / train, e.value(), len(e.trades), len(e.library) + 1,
           hold(k0, kc), hold(kc, kz), hold(k0, kz))
    print(f"  {name:<34} train ${out[1]:>7,.0f}  test ${out[2]:>6,.0f}  whole ${out[3]:>7,.0f}  "
          f"trades {out[4]:>3}", flush=True)
    return out


def main():
    eta = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    base = {"eta": eta}
    cfgs = [
        ("as built", base, None),
        ("never reset", {"resets": False}, None),
        ("fills at the worst price of the minute", {**base, "worst_fills": True}, None),
        ("cost 1.2% per side instead of 0.7%", {**base, "half_gap": 0.010}, None),
        ("2-hour window instead of 4", {**base, "window": 120}, None),
        ("8-hour window instead of 4", {**base, "window": 480}, None),
        ("'at the low' 0.10% instead of 0.23%", {**base, "at_low": 0.10}, None),
        ("'at the low' 0.50% instead of 0.23%", {**base, "at_low": 0.50}, None),
        ("'near the high' 1.0% instead of 1.8%", {**base, "near_high": 1.0}, None),
        ("'near the high' 3.0% instead of 1.8%", {**base, "near_high": 3.0}, None),
        ("start 11 Jul (after cent prices)", base, "2026-07-11"),
        ("start 1 Aug", base, "2026-08-01"),
        ("start 1 Sep", base, "2026-09-01"),
        ("update every minute (no interval choice)", {**base, "adapt_interval": False, "fixed_interval": 1}, None),
        ("borrow the whole library, not the 3 most similar", {**base, "similar": False}, None),
        ("never reset + worst fills", {"resets": False, "worst_fills": True}, None),
    ]
    print(f"{len(cfgs)} runs, sensitivity {eta}", flush=True)
    with mp.Pool(mp.cpu_count()) as pool:
        rows = pool.map(run, cfgs, chunksize=1)
    with open("data/robustness.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "train_$_30Sep", "test_$_per_1000", "whole_$", "trades", "trajectories",
                    "hold_train_$", "hold_test_$", "hold_whole_$"])
        for r in rows:
            w.writerow([r[0]] + [round(x, 2) if isinstance(x, float) else x for x in r[1:]])
    print(f"\n{'run':<50}{'TRAIN':>9}{'TEST':>9}{'hold TEST':>11}{'trades':>8}")
    for r in rows:
        print(f"{r[0]:<50}{f'${r[1]:,.0f}':>9}{f'${r[2]:,.0f}':>9}{f'${r[7]:,.0f}':>11}{r[4]:>8}")


if __name__ == "__main__":
    main()
