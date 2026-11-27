#!/usr/bin/env python3
"""
Structural checks for the robot 2 engine. Each prints PASS or FAIL.

    python3 checks.py            # all checks (a few minutes)

 1. cost         a buy and a sell at the same price lose exactly 1 - 0.993/1.007
 2. book         the engine's per-setting accounts equal a separate, simple simulation
 3. watcher      the engine finds the same trajectories as trajectories.split()
 4. library      each saved trajectory's money equals a simple simulation of just that stretch
 5. no future    changing prices AFTER a moment changes nothing the robot did BEFORE it
 6. restart      stopping, saving and reloading the engine gives the same result as running straight through
"""
import pickle
import sys

import numpy as np
import pandas as pd

from engine import AT_LOW, COST, NEAR_HIGH, WINDOW, Book, Engine, feed
from trajectories import split

ETA = 14.0


def simple(e, b, s, k0, k1):
    """One setting, $1,000, decisions on minutes k0..k1-1, value at minute k1-1. Plain loop."""
    cash, coins, pend = 1000.0, 0.0, None
    for k in range(k0, k1):
        c, kap = e.cl[k], e.kap[k]
        if pend == "B":
            coins, cash = cash / (c * (1 + kap)), 0.0
        elif pend == "S":
            cash, coins = coins * c * (1 - kap), 0.0
        pend = None
        U, D, R = e.U[k], e.D[k], e.R[k]
        if coins == 0 and U <= AT_LOW and R <= -b:
            pend = "B"
        elif coins > 0 and D <= NEAR_HIGH and U >= s:
            pend = "S"
    return cash + coins * e.cl[k1 - 1] * (1 - e.kap[k1 - 1])


def report(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)
    return ok


def main():
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    rng = np.random.default_rng(7)
    results = []

    # 1. cost
    bk = Book(np.array([1.0]), np.array([1.0]))
    bk.minute(2.0, 0.0, 5.0, -5.0)           # decides to buy
    bk.minute(2.0, 5.0, 0.0, 0.0)            # buy fills at 2.0, decides to sell
    bk.minute(2.0, 5.0, 5.0, 0.0)            # sell fills at 2.0
    results.append(report("1. cost", abs(bk.cash[0] - 1000 * 0.993 / 1.007) < 1e-9,
                          f"$1,000 -> ${bk.cash[0]:.4f} after one round trip at the same price"))

    # 2. book (no resets: one book over the whole history)
    e0 = feed(Engine(resets=False), df)
    val = e0.book.value(e0.cl[e0.n - 1], e0.kap[e0.n - 1])
    worst = 0.0
    for _ in range(300):
        q = int(rng.integers(len(e0.B)))
        worst = max(worst, abs(val[q] - simple(e0, e0.B[q], e0.S[q], 0, e0.n)))
    results.append(report("2. book", worst < 1e-6, f"300 random settings, biggest gap ${worst:.2e}"))

    # 3-4. watcher and library (with resets)
    e1 = feed(Engine(eta=ETA), df)
    hourly = df.set_index("time")["close"].resample("1h").last().dropna()
    _, segs = split(hourly, ETA)
    mine = e1.trajectories()                       # the last one is still open, so compare its start only
    same = [tuple(x) for x in segs[:-1]] == [tuple(x) for x in mine[:-1]] and segs[-1][0] == mine[-1][0]
    results.append(report("3. watcher", same, f"{len(segs)} trajectories from both"))

    worst, n = 0.0, 0
    for t in e1.library:
        k0, k1 = e1.hk[t["a"]] if t["a"] else 0, e1.hk[t["b"]]
        for _ in range(40):
            q = int(rng.integers(len(e1.B)))
            want = simple(e1, e1.B[q], e1.S[q], k0, k1)
            worst = max(worst, abs(1000 * np.exp(float(t["lnV"][q])) - want) / want)
            n += 1
    k0 = e1.hk[e1.start]
    val = e1.book.value(e1.cl[e1.n - 1], e1.kap[e1.n - 1])
    for _ in range(200):
        q = int(rng.integers(len(e1.B)))
        want = simple(e1, e1.B[q], e1.S[q], k0, e1.n)
        worst = max(worst, abs(val[q] - want) / want)
        n += 1
    results.append(report("4. library", worst < 1e-5, f"{n} setting/trajectory pairs, biggest gap {worst * 100:.5f}%"))

    # 5. no future: scramble everything after a cut; nothing before it may change
    cut = int(len(df) * 0.55)
    alt = df.copy()
    f = np.exp(np.cumsum(rng.normal(0, 0.004, len(df) - cut)))
    for col in ("high", "low", "close"):
        alt.loc[alt.index[cut:], col] = df[col].values[cut:] * f * 1.3
    e2 = feed(Engine(eta=ETA), alt)
    ts_cut = int(df["time"].values[cut].astype("datetime64[m]").astype(np.int64))
    tr1 = [t for t in e1.trades if t[0] < ts_cut]
    tr2 = [t for t in e2.trades if t[0] < ts_cut]
    rec1 = [r for r in e1.rec if r[0] < ts_cut]
    rec2 = [r for r in e2.rec if r[0] < ts_cut]
    lib1 = [(t["a"], t["b"], t["detected"]) for t in e1.library if t["detected"] <= cut // 60 - 5]
    lib2 = [(t["a"], t["b"], t["detected"]) for t in e2.library if t["detected"] <= cut // 60 - 5]
    ok = tr1 == tr2 and np.array_equal(np.array(rec1, float), np.array(rec2, float), equal_nan=True) and lib1 == lib2
    results.append(report("5. no future", ok, f"{len(tr1)} trades, {len(rec1)} hourly records and "
                                              f"{len(lib1)} trajectories before the cut are identical"))

    # 6. restart: run to the cut, save, load, continue
    e3 = feed(Engine(eta=ETA), df.iloc[:cut])
    e3 = pickle.loads(pickle.dumps(e3))
    feed(e3, df.iloc[cut:])
    ok = e3.trades == e1.trades and abs(e3.value() - e1.value()) < 1e-9 and np.allclose(e3.F, e1.F)
    results.append(report("6. restart", ok, f"${e3.value():,.2f} vs ${e1.value():,.2f}"))

    print("\nall checks passed" if all(results) else "\nSOME CHECKS FAILED")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
