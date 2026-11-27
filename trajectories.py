#!/usr/bin/env python3
"""
Split PEARL's price history into trajectories with a watcher that only looks backwards.

Every hour:
  r  = % price change over the hour
  mu, sigma = average and spread of r since the current trajectory began (its direction/speed
              and its usual instability), measured on the hours before this one
  z  = (r - mu) / sigma                       how unusual this hour is
  W  = max(0, W + z^2 - 1 - k)                adds up instability higher than usual
  S+ = max(0, S+ + z - k),  S- = max(0, S- - z - k)   adds up a change of direction
When W, S+ or S- passes the sensitivity level h, the trajectory is over. The new one starts
where that sum last stood at zero (where the change began). The first MIN_HOURS of a
trajectory only measure it; nothing is checked yet.

    python3 trajectories.py            # -> trajectories.png, data/trajectories.csv
"""
import csv

import numpy as np
import pandas as pd

K = 0.5               # small wobbles below half a usual step are ignored
MIN_HOURS = 12        # hours needed before a trajectory's average and spread mean anything
LEVELS = [3, 6, 12, 24]


def hourly(path="data/PEARL-USDT_min1.csv"):
    df = pd.read_csv(path, parse_dates=["time"]).set_index("time")
    c = df["close"].resample("1h").last().dropna()
    return c


def split(c, h, k=K, min_hours=MIN_HOURS):
    """Returns a list of (start_hour_index, end_hour_index) trajectories."""
    r = 100 * np.diff(np.log(c.values))            # % change each hour (index i = hour i+1)
    segs, start = [], 0
    W = Sp = Sm = 0.0
    zeroW = zeroP = zeroM = 0
    i = 0
    while i < len(r):
        n = i - start
        if n < min_hours:
            i += 1
            continue
        past = r[start:i]
        mu, sd = past.mean(), past.std(ddof=1)
        z = (r[i] - mu) / sd if sd > 0 else 0.0
        W = max(0.0, W + z * z - 1 - k)
        Sp = max(0.0, Sp + z - k)
        Sm = max(0.0, Sm - z - k)
        if W == 0:
            zeroW = i + 1
        if Sp == 0:
            zeroP = i + 1
        if Sm == 0:
            zeroM = i + 1
        fired = [(zeroW, W), (zeroP, Sp), (zeroM, Sm)]
        hit = [zp for zp, v in fired if v > h]
        if hit:
            new_start = max(start + min_hours, min(hit))   # where the change began
            segs.append((start, new_start))
            start = new_start
            W = Sp = Sm = 0.0
            zeroW = zeroP = zeroM = start
            i = start
            continue
        i += 1
    segs.append((start, len(r)))
    return r, segs


def describe(c, r, segs):
    rows = []
    for a, b in segs:
        part = r[a:b]
        hours = b - a
        rows.append({
            "start": c.index[a], "end": c.index[min(b, len(c) - 1)], "days": hours / 24,
            "price_change_%": (c.values[min(b, len(c) - 1)] / c.values[a] - 1) * 100,
            "direction_%_per_day": part.mean() * 24,
            "instability_%_per_hour": part.std(ddof=1) if hours > 1 else 0.0,
        })
    return rows


def main():
    c = hourly()
    print(f"{c.index[0]:%b %d} -> {c.index[-1]:%b %d}: {len(c):,} hours")
    results = {}
    for h in LEVELS:
        r, segs = split(c, h)
        rows = describe(c, r, segs)
        results[h] = (segs, rows)
        days = np.array([x["days"] for x in rows])
        print(f"\nsensitivity h={h:<3} {len(segs):>3} trajectories   length: normal {np.median(days):.1f} days, "
              f"shortest {days.min():.1f}, longest {days.max():.1f}")
        for x in rows:
            print(f"   {x['start']:%b %d %H:%M} - {x['end']:%b %d %H:%M}  {x['days']:5.1f} d  "
                  f"price {x['price_change_%']:+6.0f}%  direction {x['direction_%_per_day']:+6.1f}%/day  "
                  f"instability {x['instability_%_per_hour']:4.1f}%/h")
    with open("data/trajectories.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sensitivity_h", "start", "end", "days", "price_change_%", "direction_%_per_day",
                    "instability_%_per_hour"])
        for h, (_, rows) in results.items():
            for x in rows:
                w.writerow([h, f"{x['start']:%Y-%m-%d %H:%M}", f"{x['end']:%Y-%m-%d %H:%M}", round(x["days"], 2),
                            round(x["price_change_%"], 1), round(x["direction_%_per_day"], 2),
                            round(x["instability_%_per_hour"], 2)])
    plot(c, results)


def plot(c, results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    fills = ["#cde2fb", "#fde3d6"]
    plt.rcParams.update({"font.size": 11, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    fig, axes = plt.subplots(len(results), 1, figsize=(12, 3.1 * len(results)), facecolor=surface, sharex=True,
                             gridspec_kw={"hspace": 0.32})
    for ax, (h, (segs, rows)) in zip(axes, results.items()):
        ax.set_facecolor(surface)
        for n, (a, b) in enumerate(segs):
            ax.axvspan(c.index[a], c.index[min(b, len(c) - 1)], color=fills[n % 2], lw=0, zorder=0)
        ax.plot(c.index, c.values, color="#1c5cab", lw=1.1, zorder=2)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:.2f}"))
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_yticks([0.2, 0.3, 0.5, 1.0, 1.5, 2.0])
        days = np.median([x["days"] for x in rows])
        ax.set_title(f"Sensitivity {h}: {len(segs)} trajectories, normally {days:.1f} days long",
                     loc="left", fontsize=11.5)
        ax.grid(axis="y", color=gridc, lw=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.suptitle("Where the watcher says PEARL changed trajectory (each shaded band is one trajectory)",
                 x=0.06, ha="left", fontsize=13, y=0.915)
    fig.savefig("trajectories.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("\nsaved trajectories.png")


if __name__ == "__main__":
    main()
