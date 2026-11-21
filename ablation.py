#!/usr/bin/env python3
"""
Which part of robot 2 helps or hurts? Runs robot2.py with one part switched off at a time,
each from 25 Jun with $1,000 and no data, and compares with everything on (data/robot2_run.npz).

    python3 ablation.py                   # all variants -> data/ablation.csv
    python3 ablation.py "timing off"      # only variants whose name contains the text
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import csv
import multiprocessing as mp
import time

import numpy as np
import pandas as pd

from robot2 import WINDOW, Robot2, feed, money_at

VARIANTS = [
    ("timing off (use the newest pick every minute)", {"adapt_interval": False, "fixed_interval": 1}),
    ("library off", {"borrow": False}),
    ("accuracy judged after 3 days only", {"judge": [4320]}),
    ("library off + timing off", {"borrow": False, "adapt_interval": False, "fixed_interval": 1}),
]


def run(v):
    name, kw = v
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    t0 = time.time()
    r = feed(Robot2(**kw), df)
    print(f"  {name}: done in {time.time() - t0:.0f}s", flush=True)
    return name, summarize(r.ts[:r.n], r.fills, r.cl, r.kap, r.n)


def summarize(ts, fills, cl, kap, n):
    from types import SimpleNamespace
    r = SimpleNamespace(fills=[list(f) for f in fills], cl=cl, kap=kap)
    cut = int(np.searchsorted(ts, int(np.datetime64("2026-10-01", "m").astype(np.int64)))) - 1
    thin = int(np.searchsorted(ts, int(np.datetime64("2026-09-21", "m").astype(np.int64))))
    out = {"buys": len(fills)}
    for lab, f in (("kelly", None), ("full", 1.0)):
        w, a, t = money_at(r, f, n - 1), money_at(r, f, cut), money_at(r, f, thin)
        out[lab] = (w, 1000 * w / a, (w / t - 1) * 100)
    return out


def main():
    import sys
    pick = [v for v in VARIANTS if any(a in v[0] for a in sys.argv[1:])] or VARIANTS
    print(f"{len(pick)} runs", flush=True)
    with mp.Pool(len(pick)) as pool:
        res = dict(pool.map(run, pick))
    z = np.load("data/robot2_run.npz")
    res = {"everything on": summarize(z["ts"], z["fills"].astype(object).tolist() and
                                      [[int(a), int(b), float(c)] for a, b, c in z["fills"]],
                                      z["cl"], z["kap"], len(z["ts"])), **res}
    cl, kap = z["cl"], z["kap"]
    ts = z["ts"]
    n = len(cl)
    cut = int(np.searchsorted(ts, int(np.datetime64("2026-10-01", "m").astype(np.int64)))) - 1
    thin = int(np.searchsorted(ts, int(np.datetime64("2026-09-21", "m").astype(np.int64))))
    hold = lambda a, b: 1000 * cl[b] * (1 - kap[b]) / (cl[a] * (1 + kap[a]))
    print(f"\n{'robot 2':<48}{'buys':>6}{'Nov 20 (100%)':>15}{'Oct-Nov':>9}{'from 21 Sep':>13}{'Nov 20 (Kelly)':>16}")
    rows = []
    for name, o in res.items():
        w, te, aft = o["full"]
        rows.append([name, o["buys"], round(w), round(te), round(aft), round(o["kelly"][0])])
        print(f"{name:<48}{o['buys']:>6}{f'${w:,.0f}':>15}{f'${te:,.0f}':>9}{f'{aft:+.0f}%':>13}{f'${o['kelly'][0]:,.0f}':>16}")
    h = [hold(WINDOW, n - 1), hold(cut, n - 1), (hold(thin, n - 1) / 1000 - 1) * 100]
    print(f"{'just holding':<48}{'':>6}{f'${h[0]:,.0f}':>15}{f'${h[1]:,.0f}':>9}{f'{h[2]:+.0f}%':>13}")
    old = {}                                    # keep rows from earlier runs of other variants
    if os.path.exists("data/ablation.csv"):
        with open("data/ablation.csv", newline="") as f:
            old = {r[0]: r for r in list(csv.reader(f))[1:] if r and r[0] != "just holding"}
    old.update({r[0]: r for r in rows})
    order = ["everything on"] + [v[0] for v in VARIANTS]
    with open("data/ablation.csv", "w", newline="") as f:
        w_ = csv.writer(f)
        w_.writerow(["robot", "buys", "nov20_full_risk_$", "oct_nov_per_1000_$", "from_21sep_%", "nov20_kelly_$"])
        w_.writerows(sorted(old.values(), key=lambda r: order.index(r[0]) if r[0] in order else len(order)))
        w_.writerow(["just holding", "", round(h[0]), round(h[1]), round(h[2]), ""])


if __name__ == "__main__":
    main()
