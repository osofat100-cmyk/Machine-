#!/usr/bin/env python3
"""
Public, professional methods run on the same PEARL prices, with the same costs and the same start
as robot 2 ($1,000 on 25 Jun 20:38). None of them uses future prices: each decides at the end of a
day and trades at the next minute's price.

  1. Wells Fargo Investment Institute style: 3% in PEARL, 97% in USDC, rebalanced on the first day
     of every month (WFII suggests about 2-3% in digital assets with disciplined rebalancing).
  2. Grayscale-style trend rule: hold PEARL while the daily close is above its 50-day average,
     otherwise USDC (needs 50 days of prices before it can act).
  3. Institutional trend-following (Moskowitz-Ooi-Pedersen, Hurst-Ooi-Pedersen): hold PEARL while
     the past 30 days' return is positive, sized to a 10% yearly volatility target
     (share = 10% / PEARL's recent yearly volatility, at most 100%), rebalanced daily, never short.
  4. Just holding PEARL.

    python3 benchmarks.py         # -> data/benchmarks.csv (and robot 2 for comparison)
"""
import csv
import math

import numpy as np
import pandas as pd

from engine import FEE, HALF_GAP, decimals

START = 240                         # robot 2 can first act at minute 240 (needs 4 hours)
TRAIN_END, THIN_END = "2026-10-01", "2026-09-21"


def load():
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    ts = df["time"].values.astype("datetime64[m]").astype(np.int64)
    cl, hi, lo = df.close.values.astype(float), df.high.values.astype(float), df.low.values.astype(float)
    kap = np.empty(len(cl))                       # same cost rule as robot 2
    seen = [-10 ** 9] * 10
    for k in range(len(cl)):
        for d in range(max(decimals(cl[k]), decimals(hi[k]), decimals(lo[k])) + 1):
            seen[d] = k
        dec = max(d for d in range(10) if seen[d] > k - 1440)
        kap[k] = FEE + max(HALF_GAP, 0.5 * 10.0 ** -dec / cl[k])
    return ts, cl, kap


def simulate(ts, cl, kap, target):
    """target(day_index, closes_so_far) -> PEARL share 0..1, decided at each day's last minute.
    Returns hourly values (from START) and the minute index of each value."""
    day = ts // 1440
    last_of_day = np.flatnonzero(np.diff(day) != 0)          # last minute of each day
    cash, coins = 1000.0, 0.0
    daily_closes, out_t, out_v = [], [], []
    pend = None
    decide_at = {int(k): i for i, k in enumerate(last_of_day)}
    for k in range(START, len(cl)):
        c = cl[k]
        if pend is not None:                                # rebalance at this minute's price
            v = cash + coins * c
            want = pend * v / c
            dq = want - coins
            if dq > 0:
                coins, cash = coins + dq, cash - dq * c * (1 + kap[k])
            elif dq < 0:
                coins, cash = coins + dq, cash - dq * c * (1 - kap[k])
            pend = None
        if k in decide_at:
            daily_closes.append(c)
            x = target(len(daily_closes) - 1, daily_closes, ts[k])
            if x is not None:
                cur = coins * c / (cash + coins * c)
                if abs(x - cur) > 1e-9:
                    pend = x
        if (k - START) % 60 == 0 or k == len(cl) - 1:
            out_t.append(k)
            out_v.append(cash + coins * c * (1 - kap[k]))
    return np.array(out_t), np.array(out_v)


def wells_fargo(i, closes, t):
    first_day_of_month = np.datetime64(int(t), "m").astype("datetime64[D]").astype(object).day == 1
    return 0.03 if i == 0 or first_day_of_month else None


def ma50(i, closes, t):
    if len(closes) < 50:
        return 0.0
    return 1.0 if closes[-1] > np.mean(closes[-50:]) else 0.0


def tsmom(i, closes, t):
    if len(closes) < 31:
        return 0.0
    r = np.diff(np.log(closes[-31:]))
    vol = r.std(ddof=1) * math.sqrt(365)
    if closes[-1] <= closes[-31] or vol <= 0:
        return 0.0
    return min(1.0, 0.10 / vol)


def hold(i, closes, t):
    return 1.0 if i == 0 else None


def stats(tt, vv, ts):
    cut = int(np.searchsorted(ts, int(np.datetime64(TRAIN_END, "m").astype(np.int64)))) - 1
    thin = int(np.searchsorted(ts, int(np.datetime64(THIN_END, "m").astype(np.int64))))
    at = lambda k: vv[min(int(np.searchsorted(tt, k, side="right")) - 1, len(vv) - 1)]
    peak = np.maximum.accumulate(vv)
    worst = float(((peak - vv) / peak).max() * 100)
    return vv[-1], 1000 * vv[-1] / at(cut), (vv[-1] / at(thin) - 1) * 100, worst


def robot_curve(ts, cl, kap, f_override):
    z = np.load("data/robot2_run.npz")
    fills = [(int(a), int(b), float(c)) for a, b, c in z["fills"]]
    tt = np.arange(START, len(cl), 60)
    tt = np.append(tt, len(cl) - 1)
    vv = []
    for at in tt:
        v = 1000.0
        for kb, ks, f in fills:
            if kb > at:
                break
            f = f if f_override is None else f_override
            end = ks if (ks != -1 and ks <= at) else at
            v *= 1 - f + f * cl[end] * (1 - kap[end]) / (cl[kb] * (1 + kap[kb]))
        vv.append(v)
    return tt, np.array(vv)


def main():
    ts, cl, kap = load()
    rows = []
    for name, rule in (("Wells Fargo style: 3% PEARL, rebalanced monthly", wells_fargo),
                       ("Grayscale style: 50-day average trend rule", ma50),
                       ("Institutional trend-following, 10% risk target", tsmom),
                       ("Just holding PEARL", hold)):
        tt, vv = simulate(ts, cl, kap, rule)
        rows.append((name, *stats(tt, vv, ts)))
    for name, f in (("Robot 2, Kelly risk (what it used)", None), ("Robot 2, 100% per buy", 1.0)):
        tt, vv = robot_curve(ts, cl, kap, f)
        rows.append((name, *stats(tt, vv, ts)))
    print(f"{'':<50}{'Nov 20':>9}{'gain':>8}{'Oct-Nov':>9}{'from 21 Sep':>13}{'worst drop':>12}")
    for name, w, te, aft, dd in rows:
        print(f"{name:<50}{f'${w:,.0f}':>9}{f'{w / 10 - 100:+.0f}%':>8}{f'${te:,.0f}':>9}{f'{aft:+.0f}%':>13}{f'{dd:.0f}%':>12}")
    with open("data/benchmarks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "nov20_$", "gain_%", "oct_nov_per_1000_$", "from_21sep_%", "worst_drop_%"])
        for name, v, te, aft, dd in rows:
            w.writerow([name, round(v), round(v / 10 - 100), round(te), round(aft), round(dd)])


if __name__ == "__main__":
    main()
