#!/usr/bin/env python3
"""
Can a linear regression find the best "average" to measure dips against, the dip size worth buying, and any
time-of-day pattern? Checked on our own hourly coin prices (1 Aug - 23 Nov 2026), which this program gets ONLY by
stepping through mixed/hourly_server.py (the one program that opens the sealed data).

The model, for coin i at hour t:
    d(n)  = ln( price / average price over the last n hours )          "how far below its n-hour average" (dip < 0)
    r(h)  = ln( price h hours later / price now )                       "what it did next"
    r(h)  = a + b * d(n) + error                                        b < 0 means: the bigger the dip, the bigger the rise
Fitted two ways: (1) across coins at the same moment (does the coin that dipped MORE than the others bounce more than
the others? - the Fama-MacBeth method, non-overlapping periods), and (2) pooled raw (includes whole-market moves).
Everything is chosen on the FIRST half (to 30 Sep) and then checked on the SECOND half (1 Oct - 23 Nov).

    python3 mixed/dip_regression.py  -> mixed/dip_regression.json, mixed/dip_regression.png (+ printed summary)
"""
import http.client
import json
import math
import os
import socket
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = [24, 72, 168, 336]          # 1 day, 3 days, 1 week, 2 weeks
HORIZONS = [24, 72, 168]              # what happens over the next 1, 3, 7 days
SPLIT = "2026-10-01 00:00"
COST = 0.001                          # 0.05% to buy + 0.05% to sell
EDGES = [-np.inf, -15, -10, -5, -2, 0, 2, 5, 10, np.inf]


def collect():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "hourly_server.py"), "--port", str(port)],
                            stdout=subprocess.PIPE, text=True, env=dict(os.environ, START="2026-08-01 00:00"))
    line = proc.stdout.readline()
    assert line.startswith("ready"), line
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=300)
    times, rows, coins = [], [], None
    while True:
        conn.request("POST", "/next", json.dumps({"orders": {}}), {"Content-Type": "application/json"})
        out = json.loads(conn.getresponse().read())
        if out.get("done"):
            break
        if out.get("universe"):
            coins = [u["symbol"] for u in out["universe"] if u["kind"] == "crypto"]
        st = out["step"]
        times.append(st["time"])
        rows.append([st["close"].get(c, np.nan) for c in coins])
        if out.get("last_step"):
            break
    conn.close()
    proc.terminate()
    return pd.DataFrame(rows, index=times, columns=coins, dtype=float)


def fama_macbeth(d, fwd, idx):
    """Cross-sectional slope at each sampled hour; returns mean slope, its t-statistic and the number of periods."""
    bs = []
    for t in idx:
        x, y = d.iloc[t].values, fwd.iloc[t].values
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 30:
            continue
        x, y = x[ok] - x[ok].mean(), y[ok] - y[ok].mean()
        if (x * x).sum() > 0:
            bs.append((x * y).sum() / (x * x).sum())
    bs = np.array(bs)
    if len(bs) < 3:
        return float("nan"), float("nan"), len(bs)
    return float(bs.mean()), float(bs.mean() / (bs.std(ddof=1) / math.sqrt(len(bs)))), len(bs)


def pooled(d, fwd, idx):
    x = d.iloc[idx].values.ravel()
    y = fwd.iloc[idx].values.ravel()
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    b = ((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum()
    a = y.mean() - b * x.mean()
    r2 = 1 - ((y - a - b * x) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return float(a), float(b), float(r2)


def main():
    px = collect()
    T = len(px)
    split = int(np.searchsorted(px.index.values, SPLIT))
    print(f"{T} hours, {px.shape[1]} coins, {px.index[0]} .. {px.index[-1]}; first half ends at row {split}")
    out = {"hours": T, "coins": int(px.shape[1]), "split": SPLIT, "table": [], "half_life_hours": {}}
    dev = {n: np.log(px / px.rolling(n, min_periods=n).mean()) for n in WINDOWS}
    fw = {h: np.log(px.shift(-h) / px) for h in HORIZONS}
    # speed of mean reversion: change in the gap next hour = a + b * gap  ->  half-life = -ln2 / ln(1 + b)
    for n in WINDOWS:
        x = dev[n].iloc[:split].values[:-1]
        dx = dev[n].iloc[:split].values[1:] - x
        ok = np.isfinite(x) & np.isfinite(dx)
        b = (x[ok] * dx[ok]).sum() / (x[ok] ** 2).sum()
        out["half_life_hours"][n] = float(-math.log(2) / math.log(1 + b)) if -1 < b < 0 else None
    print("half-life of a gap from its average (hours):", {n: (round(v, 1) if v else None) for n, v in out["half_life_hours"].items()})
    print(f"{'avg':>5} {'next':>5} | first half: slope   t  (n) | second half: slope   t  (n) | pooled raw slope first / second")
    for n in WINDOWS:
        for h in HORIZONS:
            i1 = list(range(n, split - h, h))
            i2 = list(range(split, T - h, h))
            b1, t1, k1 = fama_macbeth(dev[n], fw[h], i1)
            b2, t2, k2 = fama_macbeth(dev[n], fw[h], i2)
            a1p, b1p, r1 = pooled(dev[n], fw[h], i1)
            a2p, b2p, r2 = pooled(dev[n], fw[h], i2)
            out["table"].append({"avg_hours": n, "next_hours": h, "first": {"slope": b1, "t": t1, "periods": k1},
                                 "second": {"slope": b2, "t": t2, "periods": k2},
                                 "pooled_first": {"a": a1p, "b": b1p, "r2": r1}, "pooled_second": {"a": a2p, "b": b2p, "r2": r2}})
            print(f"{n:5d} {h:5d} | {b1:+.3f} {t1:+5.1f} ({k1:3d})          | {b2:+.3f} {t2:+5.1f} ({k2:3d})           | {b1p:+.3f} / {b2p:+.3f}")
    best = min(out["table"], key=lambda r: r["first"]["t"] if np.isfinite(r["first"]["t"]) else 0)
    out["chosen_on_first_half"] = {k: best[k] for k in ("avg_hours", "next_hours", "first", "second", "pooled_first")}
    a, b = best["pooled_first"]["a"], best["pooled_first"]["b"]
    out["buy_threshold_pct"] = float(100 * (math.exp(-(COST - a) / abs(b)) - 1)) if b < 0 else None
    print(f"chosen on the first half: {best['avg_hours']}-hour average, next {best['next_hours']} hours; "
          f"first-half slope {best['first']['slope']:+.3f} (t {best['first']['t']:+.1f}); "
          f"second-half slope {best['second']['slope']:+.3f} (t {best['second']['t']:+.1f}); "
          f"break-even dip from the pooled fit: {out['buy_threshold_pct']}")
    # what actually followed dips of each size, second half only, weekly average
    labels = ["below -15%", "-15 to -10%", "-10 to -5%", "-5 to -2%", "-2 to 0%", "0 to +2%", "+2 to +5%", "+5 to +10%", "above +10%"]
    d2 = dev[168].iloc[split:] * 100
    out["buckets_second_half_weekly_avg"] = {}
    for h in HORIZONS:
        y = (np.exp(fw[h].iloc[split:]) - 1) * 100
        rel = y.sub(y.mean(axis=1), axis=0)
        rows = []
        for lo, hi, lab in zip(EDGES, EDGES[1:], labels):
            m = (d2 > lo) & (d2 <= hi) & np.isfinite(y)
            cnt = int(m.values.sum())
            rows.append({"bucket": lab, "count": cnt,
                         "mean_next_pct": float(y.where(m).stack().mean()) if cnt else None,
                         "mean_vs_average_coin_pct": float(rel.where(m).stack().mean()) if cnt else None,
                         "share_up_pct": float(100 * (y.where(m).stack() > 0).mean()) if cnt else None})
        out["buckets_second_half_weekly_avg"][h] = rows
        print(f"after the next {h} hours (second half, gap vs weekly average):")
        for r in rows:
            if r["count"]:
                print(f"   {r['bucket']:12s} n={r['count']:6d}  mean {r['mean_next_pct']:+6.2f}%  vs average coin "
                      f"{r['mean_vs_average_coin_pct']:+6.2f}%  up {r['share_up_pct']:.0f}% of the time")
    # time of day and day of week: the average coin's hourly move
    m = np.log(px / px.shift(1)).mean(axis=1).dropna() * 100
    hrs = pd.Series([int(t[11:13]) for t in m.index], index=m.index)
    dow = pd.Series(pd.to_datetime(m.index).dayofweek, index=m.index)
    def groups(g):
        res = []
        for k, v in m.groupby(g):
            res.append({"key": int(k), "mean_pct": float(v.mean()), "t": float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))), "n": int(len(v))})
        return res
    out["hour_of_day_utc"], out["day_of_week"] = groups(hrs), groups(dow)
    hs = sorted(out["hour_of_day_utc"], key=lambda r: r["mean_pct"])
    print("hour of day (UTC), average coin's move per hour: lowest", [(r["key"], round(r["mean_pct"], 3), round(r["t"], 1)) for r in hs[:3]],
          "highest", [(r["key"], round(r["mean_pct"], 3), round(r["t"], 1)) for r in hs[-3:]],
          "| hours with |t| > 2:", sum(abs(r["t"]) > 2 for r in hs), "of 24 (about 1 expected by chance)")
    print("day of week (0 = Monday):", [(r["key"], round(r["mean_pct"], 3), round(r["t"], 1)) for r in out["day_of_week"]])
    json.dump(out, open(os.path.join(HERE, "dip_regression.json"), "w"), indent=1)
    chart(out, labels)


def chart(out, labels):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["text.parse_math"] = False
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    cols = {24: "#9ec5f4", 72: "#2a78d6", 168: "#184f95"}
    names = {24: "next 1 day", 72: "next 3 days", 168: "next 7 days"}
    fig, axes = plt.subplots(2, 1, figsize=(13, 8.5), facecolor=SURF, sharex=True)
    for ax, key, title in ((axes[0], "mean_next_pct", "Average move afterwards (%), by how far the coin was from its weekly average"),
                           (axes[1], "mean_vs_average_coin_pct", "The same, compared with the average coin over the same days (%)")):
        for j, h in enumerate(HORIZONS):
            rows = out["buckets_second_half_weekly_avg"][h]
            xs = [i + (j - 1) * 0.27 for i in range(len(rows))]
            ys = [r[key] if r[key] is not None else 0 for r in rows]
            ax.bar(xs, ys, width=0.25, color=cols[h], label=names[h])
        ax.axhline(0, color=INK2, lw=1)
        ax.set_title(title, loc="left", fontsize=11.5, color=INK, weight="bold")
        ax.set_ylabel("%", color=INK2, fontsize=9)
        ax.grid(axis="y", color=GRID, lw=1)
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
    axes[0].legend(loc="best", fontsize=9, frameon=False)
    rows = out["buckets_second_half_weekly_avg"][72]
    axes[1].set_xticks(range(len(labels)), [f"{lab}\n(n={r['count']:,})" for lab, r in zip(labels, rows)], fontsize=8, color=INK2)
    axes[1].set_xlabel("Gap between the coin's price and its own weekly average at that hour (dips on the left). "
                       "Second half of the data only: 1 Oct - 23 Nov 2026.", color=INK2, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "dip_regression.png"), dpi=110, facecolor=SURF)


if __name__ == "__main__":
    main()
