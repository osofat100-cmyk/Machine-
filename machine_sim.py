#!/usr/bin/env python3
"""
Replay the live machine from PEARL's first day on BigONE, with no data at the start.

Every REFIT minutes it re-runs the whole buy%/sell% landscape (0.5% to 100%) on all
the data it has seen so far, smooths it, and moves to the top of the hill. If no
setting has made money yet, it stays in USDC. Between re-picks it trades minute by
minute, paying 0.7% each side.

    python3 machine_sim.py                  # re-pick once a day -> machine_sim.png, data/machine_sim.csv
    python3 machine_sim.py --refit 60       # every hour (slower)
"""
import argparse
import csv
import multiprocessing as mp

import numpy as np

from landscape import COST, Market, smooth

STEPS = np.round(np.arange(0.5, 100.0001, 0.5), 2)
M = B = S = None


def init():
    global M, B, S
    M = Market(warmup=240)                      # start 4 hours after the first price
    B = [M.buys(x) for x in STEPS]
    S = [M.sells(x) for x in STEPS]


def pick(end):
    """Top of the smoothed landscape using only minutes before `end`. None = stay in USDC."""
    if end < 60:
        return None
    grid = np.empty((len(STEPS), len(STEPS)))
    for j, b in enumerate(B):
        if not b or b[0] >= end - 1:            # never bought yet at this buy % -> keeps $1000
            grid[:, j] = 1000.0
            continue
        for i, s in enumerate(S):
            grid[i, j] = M.run(b, s, end)[0]
    sm = smooth(grid, 2.0)                      # about 1% wide
    i, j = np.unravel_index(sm.argmax(), sm.shape)
    if sm[i, j] <= 1000.0:
        return None
    return float(STEPS[j]), float(STEPS[i]), float(sm[i, j])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refit", type=int, default=1440, help="minutes between re-picks")
    a = ap.parse_args()

    init()
    m, c = M, M.close
    ends = list(range(a.refit, m.n, a.refit))
    print(f"{m.time[0]:%b %d %H:%M} -> {m.time[-1]:%b %d %H:%M}: {m.n:,} minutes, {len(ends):,} re-picks "
          f"x {len(STEPS) ** 2:,} settings each", flush=True)
    with mp.Pool(mp.cpu_count(), initializer=init) as pool:
        picks = pool.map(pick, ends, chunksize=8)

    cash, coins, rows, trades = 1000.0, 0.0, [], 0
    setting = None
    for k in range(m.n - 1):
        if k % a.refit == 0 and k > 0:
            setting = picks[k // a.refit - 1]
        if setting:
            b, s, _ = setting
            if coins == 0 and m.at_low[k] and m.chg4[k] <= -b:
                coins, cash = cash / (c[k + 1] * (1 + COST)), 0.0
                trades += 1
            elif coins > 0 and m.near_high[k] and m.up_low[k] >= s:
                cash, coins = coins * c[k + 1] * (1 - COST), 0.0
        if k % 60 == 0:
            rows.append((m.time[k], cash + coins * c[k], 1000 * c[k] / c[0] * (1 - COST),
                         setting[0] if setting else "", setting[1] if setting else ""))
    final = cash + coins * c[-1] * (1 - COST)
    hold = 1000 * c[-1] / c[0] * (1 - COST) ** 2
    rows.append((m.time[-1], final, hold, rows[-1][3], rows[-1][4]))

    with open("data/machine_sim.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "machine_$", "just_holding_$", "buy_pct", "sell_pct"])
        for t, v, h, b, s in rows:
            w.writerow([t.strftime("%Y-%m-%d %H:%M"), round(v, 2), round(h, 2), b, s])
    print(f"machine: $1,000 -> ${final:,.0f} with {trades} buys   just holding: ${hold:,.0f}")
    for t, v, h, b, s in rows[:: max(1, len(rows) // 12)]:
        print(f"  {t:%b %d}: machine ${v:>7,.0f}  holding ${h:>7,.0f}  setting {b}/{s}")
    plot(rows, final, hold, a.refit)


def plot(rows, final, hold, refit):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    blue, orange = "#2a78d6", "#eb6834"
    plt.rcParams.update({"font.size": 12, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    t = [r[0] for r in rows]
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 10), facecolor=surface, sharex=True,
                                  gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.12})
    for a_ in (ax, ax2):
        a_.set_facecolor(surface)
        a_.grid(axis="y", color=gridc, lw=0.8)
        for side in ("top", "right"):
            a_.spines[side].set_visible(False)
    ax.plot(t, [r[2] for r in rows], color=muted, lw=1.8, ls=(0, (5, 3)))
    ax.plot(t, [r[1] for r in rows], color=blue, lw=2.4)
    ax.axhline(1000, color=gridc, lw=1)
    ax.annotate(f"just holding  ${hold:,.0f}", (t[-1], rows[-1][2]), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=11, color=ink2)
    ax.annotate(f"the machine  ${final:,.0f}", (t[-1], rows[-1][1]), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=11, color=ink, weight="bold")
    ax.set_ylabel("account value ($)")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title(f"The live machine from day one: starts with no data, re-picks the best buy/sell % every "
                 f"{'hour' if refit == 60 else 'day' if refit == 1440 else f'{refit} minutes'} from everything seen so far",
                 loc="left", fontsize=13, pad=10)
    bs = [(r[0], r[3], r[4]) for r in rows if r[3] != ""]
    ax2.step([x[0] for x in bs], [x[1] for x in bs], where="post", color=blue, lw=2, label="buy % it was using")
    ax2.step([x[0] for x in bs], [x[2] for x in bs], where="post", color=orange, lw=2, label="sell % it was using")
    ax2.set_ylabel("setting (%)")
    ax2.legend(loc="lower right", frameon=False, fontsize=11)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.savefig("machine_sim.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("saved machine_sim.png")


if __name__ == "__main__":
    main()
