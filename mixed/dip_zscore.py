#!/usr/bin/env python3
"""
Dips measured in each coin's own "normal wiggle" (volatility) instead of in percent, then sorted by depth, timescale
and speed - a read-only check on our hourly coin prices (1 Aug - 23 Nov 2026, through mixed/hourly_server.py; DHN-USD
left out for bad data). No trader is changed.

  sigma^2(t) = L * sigma^2(t-1) + (1 - L) * r(t)^2,  L = 0.5^(1/168)      each coin's hourly volatility, 1-week memory
  z_n(t)     = d_n(t) / ( sigma(t-1) * sqrt((n-1)(2n-1)/(6n)) )           gap from the n-hour average, in "wiggles"
  v(t)       = ln(P(t)/P(t-6)) / ( sigma(t-1) * sqrt(6) )                 speed of the last 6 hours
  next move  = ln(P(t+1+h)/P(t+1)) minus the average coin's move over the same hours   (market taken out)

Groups use fixed, pre-set thresholds (-2 = deep, -1 = small), so nothing is tuned on this data. Every group reports the
number of separate DAYS it happened on, the mean and the median, and a t-statistic computed from day averages
(Newey-West, 1 lag), because dips cluster on crash days.

    python3 mixed/dip_zscore.py -> mixed/dip_zscore.json, mixed/dip_zscore.png (+ printed table)
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dip_regression as D  # noqa: E402

LAM = 0.5 ** (1 / 168)
WINDOWS = (24, 168, 720)
H = 24                                     # next day


def scale(n):
    return math.sqrt((n - 1) * (2 * n - 1) / (6 * n))


def nw_t(x):
    """t-statistic of the mean of a daily series, Newey-West with one lag."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 5:
        return float("nan")
    e = x - x.mean()
    g0 = (e * e).sum() / n
    g1 = (e[1:] * e[:-1]).sum() / n
    var = (g0 + g1) / n                      # g0 + 2 * (1/2) * g1
    return float(x.mean() / math.sqrt(var)) if var > 0 else float("nan")


def main():
    px = D.collect().drop(columns=D.EXCLUDE, errors="ignore")
    r = np.log(px / px.shift(1))
    sig = np.sqrt((r ** 2).ewm(alpha=1 - LAM, adjust=False).mean()).shift(1)
    sig.iloc[:168] = np.nan                                           # let the volatility estimate settle for a week
    z = {n: np.log(px / px.rolling(n, min_periods=n).mean()) / (sig * scale(n)) for n in WINDOWS}
    v = np.log(px / px.shift(6)) / (sig * math.sqrt(6))
    fwd = np.log(px.shift(-(H + 1)) / px.shift(-1)) * 100
    rel = fwd.sub(fwd.mean(axis=1), axis=0)
    days = pd.Series([t[:10] for t in px.index], index=px.index)
    day_code = np.repeat(pd.factorize(days)[0], px.shape[1])
    hours = np.array([int(t[11:13]) for t in px.index])
    relv, fwdv = rel.values.ravel(), fwd.values.ravel()

    def group(name, mask):
        m = mask.values.ravel() & np.isfinite(relv)
        if m.sum() == 0:
            return {"group": name, "count": 0}
        d = day_code[m]
        sums, cnts = np.bincount(d, weights=relv[m]), np.bincount(d)
        daily = sums[cnts > 0] / cnts[cnts > 0]
        return {"group": name, "count": int(m.sum()), "days": int((cnts > 0).sum()),
                "mean_vs_market_pct": float(relv[m].mean()), "median_vs_market_pct": float(np.median(relv[m])),
                "share_beating_market_pct": float(100 * (relv[m] > 0).mean()),
                "mean_raw_pct": float(fwdv[m].mean()), "median_raw_pct": float(np.median(fwdv[m])),
                "day_mean_pct": float(daily.mean()), "t_by_day": nw_t(daily)}

    z24, z168, z720 = z[24], z[168], z[720]
    groups = [
        ("Weekly: deep dip (z <= -2)", z168 <= -2), ("Weekly: small dip (-2 to -1)", (z168 > -2) & (z168 <= -1)),
        ("Weekly: normal (-1 to 1)", (z168 > -1) & (z168 < 1)), ("Weekly: small spike (1 to 2)", (z168 >= 1) & (z168 < 2)),
        ("Weekly: big spike (z >= 2)", z168 >= 2),
        ("Daily: deep dip (z <= -2)", z24 <= -2), ("Daily: small dip (-2 to -1)", (z24 > -2) & (z24 <= -1)),
        ("Daily: big spike (z >= 2)", z24 >= 2),
        ("Short-term dip only (day deep, week normal)", (z24 <= -2) & (z168 > -1)),
        ("Deep on day, week and month", (z24 <= -2) & (z168 <= -2) & (z720 <= -2)),
        ("Deep weekly dip, FAST (crash, v <= -2)", (z168 <= -2) & (v <= -2)),
        ("Deep weekly dip, SLOW (slide, v > -1)", (z168 <= -2) & (v > -1)),
    ]
    hr = pd.DataFrame(np.repeat(hours[:, None], px.shape[1], axis=1), index=px.index, columns=px.columns)
    for nm, lo, hi in (("Asia hours 00-08 UTC", 0, 8), ("Europe hours 08-14 UTC", 8, 14), ("US hours 14-24 UTC", 14, 24)):
        groups.append((f"Daily deep dip in {nm}", (z24 <= -2) & (hr >= lo) & (hr < hi)))
    rows = [group(n, m) for n, m in groups]
    print(f"{px.shape[1]} coins, {px.index[0]} .. {px.index[-1]}; next move = following 24 hours from the next hour's price")
    print(f"{'group':46s} {'coin-hours':>10s} {'days':>5s} {'mean vs mkt':>11s} {'median':>8s} {'beat mkt':>8s} {'raw mean':>8s} {'t (days)':>8s}")
    for x in rows:
        if x["count"]:
            print(f"{x['group']:46s} {x['count']:10d} {x['days']:5d} {x['mean_vs_market_pct']:+10.2f}% {x['median_vs_market_pct']:+7.2f}% "
                  f"{x['share_beating_market_pct']:7.0f}% {x['mean_raw_pct']:+7.2f}% {x['t_by_day']:+8.1f}")
    # one shared slope (all coins on the same scale): next move vs z, fitted across coins each hour, averaged by day
    slopes = {}
    for key, zz in (("z24", z24), ("z168", z168)):
        b = np.full(len(px), np.nan)
        X, Y = zz.values, rel.values
        for t in range(len(px)):
            ok = np.isfinite(X[t]) & np.isfinite(Y[t])
            if ok.sum() >= 30:
                x = X[t][ok] - X[t][ok].mean()
                if (x * x).sum() > 0:
                    b[t] = (x * Y[t][ok]).sum() / (x * x).sum()
        s = pd.Series(b, index=px.index)
        res = {}
        for nm, sel in (("all hours", np.ones(len(px), bool)), ("Asia", hours < 8), ("Europe", (hours >= 8) & (hours < 14)),
                        ("US", hours >= 14)):
            daily = s[sel].groupby(days[sel]).mean().dropna()
            res[nm] = {"slope_pct_per_z": float(daily.mean()), "t_by_day": nw_t(daily.values), "days": int(len(daily))}
        slopes[key] = res
        print(f"shared slope, next-day move (% vs market) per 1 z of {key}: " +
              "; ".join(f"{k} {v_['slope_pct_per_z']:+.3f} (t {v_['t_by_day']:+.1f})" for k, v_ in res.items()))
    out = {"groups": rows, "slopes": slopes, "settings": {"lambda": LAM, "windows": WINDOWS, "next_hours": H,
           "groups_tested": len(rows), "slopes_tested": 8, "excluded": D.EXCLUDE}}
    json.dump(out, open(os.path.join(HERE, "dip_zscore.json"), "w"), indent=1)
    chart(rows)


def chart(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["text.parse_math"] = False
    INK, INK2, GRID, SURF, BLUE, GRAY = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#2a78d6", "#898781"
    rows = [x for x in rows if x["count"]][::-1]
    fig, ax = plt.subplots(figsize=(13, 7.5), facecolor=SURF)
    for i, x in enumerate(rows):
        solid = abs(x["t_by_day"]) >= 3
        ax.barh(i - 0.19, x["mean_vs_market_pct"], height=0.36, color=BLUE if solid else "#9ec5f4")
        ax.barh(i + 0.19, x["median_vs_market_pct"], height=0.36, color=GRAY if solid else "#cfcdc8")
        ax.annotate(f"mean {x['mean_vs_market_pct']:+.2f}%, median {x['median_vs_market_pct']:+.2f}%, t {x['t_by_day']:+.1f}, "
                    f"{x['days']} days", (max(x["mean_vs_market_pct"], x["median_vs_market_pct"], 0), i), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8, color=INK2)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(range(len(rows)), [x["group"] for x in rows], fontsize=8.5, color=INK)
    lo = min(min(x["mean_vs_market_pct"], x["median_vs_market_pct"]) for x in rows)
    hi = max(max(x["mean_vs_market_pct"], x["median_vs_market_pct"]) for x in rows)
    ax.set_xlim(min(-0.6, lo * 1.1), max(0.6, hi) * 2.6)
    ax.set_xlabel("Move over the next 24 hours compared with the average coin (%). Blue = mean, gray = median. "
                  "Pale bars: t below 3, so not distinguishable from luck.", color=INK2, fontsize=9)
    ax.set_title("What coins did the day after each kind of dip or spike (dips sized by each coin's own volatility)",
                 loc="left", fontsize=12, color=INK, weight="bold")
    ax.grid(axis="x", color=GRID, lw=1)
    ax.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dip_zscore.png"), dpi=110, facecolor=SURF)


if __name__ == "__main__":
    main()
