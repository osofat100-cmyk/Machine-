#!/usr/bin/env python3
"""
Run the "buy the crash, sell the pump" rule at every percentage and graph the result.

    pip install matplotlib
    python3 sweep.py              # -> sweep.png and data/sweep_*.csv

  DROP %: buy after PEARL falls this much in 4 hours (at its 4-hour low)
  PUMP %: sell when PEARL is this much above its 4-hour low (near its 4-hour high)
Each run starts with $1000 and trades the whole history, paying 1.4% per round trip.
"""
import bisect
import csv

import numpy as np
import pandas as pd

from signals import features

COST = 0.007


def make_sim(df, F):
    c = df["close"].values
    n = len(c)
    up_low = F["up from 4h low %"].values
    chg4 = F["change last 4h %"].values
    dn_high = F["down from 4h high %"].values
    at_low = up_low <= 0.23
    near_high = dn_high <= 1.8

    def buys(drop):
        return np.flatnonzero(at_low & (chg4 <= -drop) & (np.arange(n) < n - 1)).tolist()

    def sells(pump):
        return np.flatnonzero(near_high & (up_low >= pump) & (np.arange(n) < n - 1)).tolist()

    def run(bi, si):
        cash, pos, trades = 1000.0, 0, 0
        while True:
            k = bisect.bisect_left(bi, pos)
            if k == len(bi):
                return cash, trades
            i = bi[k]
            coins = cash / (c[i + 1] * (1 + COST))
            k = bisect.bisect_left(si, i + 1)
            if k == len(si):
                return coins * c[-1] * (1 - COST), trades + 1
            j = si[k]
            cash, pos, trades = coins * c[j + 1] * (1 - COST), j + 1, trades + 1

    return buys, sells, run


def main():
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"]).set_index("time")
    F = features(df)
    ok = F.notna().all(axis=1).values
    df, F = df[ok], F[ok]
    hold = 1000 * df["close"].iloc[-1] / df["close"].iloc[0] * (1 - COST) ** 2
    buys, sells, run = make_sim(df, F)
    print(f"{df.index[0]:%b %d} -> {df.index[-1]:%b %d}, just holding: ${hold:.0f}")
    print(f"check: drop 6.4 / pump 11.4 -> ${run(buys(6.4), sells(11.4))[0]:.0f}")

    fine = np.round(np.arange(1.0, 100.01, 0.1), 1)
    b_fixed, s_fixed = buys(6.4), sells(11.4)
    drop_line = [run(buys(x), s_fixed) for x in fine]
    pump_line = [run(b_fixed, sells(x)) for x in fine]

    coarse = np.round(np.arange(1.0, 100.01, 0.5), 1)
    B = [buys(x) for x in coarse]
    S = [sells(x) for x in coarse]
    grid = np.array([[run(b, s)[0] for b in B] for s in S])  # rows = pump, cols = drop

    with open("data/sweep_lines.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["percent", "final_$_varying_drop(pump=11.4)", "trades", "final_$_varying_pump(drop=6.4)", "trades"])
        for x, (d, dt), (p, pt) in zip(fine, drop_line, pump_line):
            w.writerow([x, round(d, 2), dt, round(p, 2), pt])
    pd.DataFrame(grid, index=coarse, columns=coarse).round(0).to_csv("data/sweep_grid.csv",
                                                                     index_label="pump% \\ drop%")
    i, j = np.unravel_index(grid.argmax(), grid.shape)
    print(f"best of {grid.size} combos: drop {coarse[j]}% / pump {coarse[i]}% -> ${grid[i, j]:.0f}")
    print(f"combos that beat holding: {(grid > hold).sum()} of {grid.size}; "
          f"that made any profit: {(grid > 1000).sum()}; lost money: {(grid < 1000).sum()}")
    plot(fine, drop_line, pump_line, coarse, grid, hold, df)


def plot(fine, drop_line, pump_line, coarse, grid, hold, df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    ink, ink2, muted, gridc, surface = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
    blue = "#2a78d6"
    plt.rcParams.update({"font.size": 11, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})

    def smooth(y, k=21):
        y = np.asarray(y, float)
        pad = np.pad(y, k // 2, mode="edge")
        return np.convolve(pad, np.ones(k) / k, mode="valid")

    fig = plt.figure(figsize=(12, 15), facecolor=surface)
    gs = fig.add_gridspec(3, 1, height_ratios=[1, 1, 1.5], hspace=0.38)
    period = f"{df.index[0]:%b %d} – {df.index[-1]:%b %d, %Y}"
    fig.suptitle(f"What $1,000 became with each setting  ·  PEARL on BigONE, {period}",
                 fontsize=15, x=0.06, ha="left", y=0.965)

    for row, (line, name, fixed, now) in enumerate((
            (drop_line, "DROP %  (buy after it falls this much in 4 hours)", "sell setting fixed at 11.4%", 6.4),
            (pump_line, "PUMP %  (sell when it is this much above the 4-hour low)", "buy setting fixed at 6.4%", 11.4))):
        ax = fig.add_subplot(gs[row])
        ax.set_facecolor(surface)
        y = [v for v, _ in line]
        ax.plot(fine, y, color=blue, lw=1, alpha=0.25)
        ax.plot(fine, smooth(y), color=blue, lw=2.2)
        for level, label in ((hold, f"just holding ${hold:,.0f}"), (1000, "start $1,000")):
            ax.axhline(level, color=muted, lw=1, ls=(0, (4, 3)))
            ax.text(99.5, level, label, color=ink2, fontsize=10, ha="right", va="bottom")
        k = int(round((now - 1) / 0.1))
        ax.plot([now], [y[k]], "o", ms=8, color=blue, mec=surface, mew=2)
        ax.annotate(f"current setting {now}% → ${y[k]:,.0f}", (now, y[k]), xytext=(14, 6),
                    textcoords="offset points", fontsize=10, color=ink)
        ax.set_xlim(1, 100)
        ax.set_ylim(0, max(max(y), hold) * 1.12)
        ax.set_xlabel(name)
        ax.set_ylabel("final money ($)")
        ax.set_title(f"Changing the {name.split()[0]} setting  ({fixed})", loc="left", fontsize=12, color=ink)
        ax.grid(axis="y", color=gridc, lw=0.8)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    ax = fig.add_subplot(gs[2])
    ramp = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
    cmap = LinearSegmentedColormap.from_list("blue", ramp)
    xs, ys = coarse <= 30, coarse <= 50          # past these nothing changes (never buys / never sells)
    sub, cx, cy = grid[np.ix_(ys, xs)], coarse[xs], coarse[ys]
    im = ax.imshow(sub, origin="lower", aspect="auto", cmap=cmap,
                   extent=[cx[0] - 0.25, cx[-1] + 0.25, cy[0] - 0.25, cy[-1] + 0.25])
    ax.contour(cx, cy, sub, levels=[hold], colors=[ink], linewidths=1.6)
    ax.plot([6.4], [11.4], "o", ms=8, color="#eb6834", mec=surface, mew=2)
    ax.annotate("current setting (6.4%, 11.4%)", (6.4, 11.4), xytext=(-20, -26), textcoords="offset points",
                fontsize=10, color=ink)
    ax.set_xlabel("DROP %  (buy setting)  ·  past 25% it never buys")
    ax.set_ylabel("PUMP %  (sell setting)  ·  past ~42% it never sells")
    ax.set_title(f"Every combination  ·  darker = more money  ·  inside the black line = beat holding "
                 f"(${hold:,.0f})", loc="left", fontsize=12, color=ink)
    cb = fig.colorbar(im, ax=ax, pad=0.015)
    cb.set_label("final money ($)", color=ink2)
    cb.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    fig.savefig("sweep.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("saved sweep.png")


if __name__ == "__main__" and "--all" not in __import__("sys").argv:
    main()


def full_map():
    """Every buy% x sell% pair from 0.5 to 100 in 0.5 steps -> sweep_all.png + data/sweep_all.csv"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"]).set_index("time")
    F = features(df)
    ok = F.notna().all(axis=1).values
    df, F = df[ok], F[ok]
    hold = 1000 * df["close"].iloc[-1] / df["close"].iloc[0] * (1 - COST) ** 2
    buys, sells, run = make_sim(df, F)
    steps = np.round(np.arange(0.5, 100.01, 0.5), 1)
    B, S = [buys(x) for x in steps], [sells(x) for x in steps]
    res = [[run(b, s) for b in B] for s in S]                 # rows = sell %, cols = buy %
    money = np.array([[m for m, _ in row] for row in res])
    trades = np.array([[t for _, t in row] for row in res])
    pd.DataFrame(money, index=steps, columns=steps).round(0).to_csv(
        "data/sweep_all.csv", index_label="sell% \\ buy%")

    cat = np.where(trades == 0, 0, np.where(money < 1000, 1, np.where(money < hold, 2, 3)))
    names = ["never buys (keeps $1,000)", "lost money", f"made money, less than holding ${hold:,.0f}",
             f"beat holding ${hold:,.0f}"]
    colors = ["#e1e0d9", "#e34948", "#9ec5f4", "#256abf"]
    counts = [(cat == k).sum() for k in range(4)]
    for k in range(4):
        print(f"{names[k]:<40} {counts[k]:>6} of {cat.size}")

    surface, ink, ink2, muted = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
    plt.rcParams.update({"font.size": 11, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    fig, ax = plt.subplots(figsize=(11, 10.5), facecolor=surface)
    ax.imshow(cat, origin="lower", cmap=ListedColormap(colors), vmin=-0.5, vmax=3.5, aspect="equal",
              extent=[0.25, 100.25, 0.25, 100.25], interpolation="nearest")
    ax.set_xlabel("BUY %  - how far PEARL falls in 4 hours before we buy")
    ax.set_ylabel("SELL %  - how far it rises above the 4-hour low before we sell")
    ax.set_title(f"All {cat.size:,} buy/sell combinations, 0.5% to 100%  ·  $1,000 from "
                 f"{df.index[0]:%b %d} to {df.index[-1]:%b %d}", loc="left", fontsize=13, pad=12)
    ax.set_xticks(range(0, 101, 10))
    ax.set_yticks(range(0, 101, 10))
    examples = [(1, 2), (1, 25), (1, 50), (25, 1), (50, 1), (6.4, 11.4), (5, 25), (25, 25)]
    for bx, sy in examples:
        bi, si = int(round(bx / 0.5)) - 1, int(round(sy / 0.5)) - 1
        m = run(buys(bx), sells(sy))[0] if (bx, sy) == (6.4, 11.4) else money[si, bi]
        ax.plot([bx], [sy], "o", ms=7, color=ink, mec=surface, mew=1.5)
        off = (8, -16) if (bx, sy) == (1, 25) else (8, 6)
        ax.annotate(f"{bx:g}/{sy:g}: ${m:,.0f}", (bx, sy), xytext=off, textcoords="offset points",
                    fontsize=9.5, color=ink,
                    bbox=dict(boxstyle="round,pad=0.2", fc=surface, ec="none", alpha=0.85))
    ax.legend(handles=[Patch(color=colors[k], label=f"{names[k]}  ({counts[k]:,})") for k in (3, 2, 1, 0)],
              loc="upper right", frameon=True, facecolor=surface, edgecolor="#e1e0d9", fontsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.savefig("sweep_all.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("saved sweep_all.png")
    return steps, money, trades, hold, run, buys, sells


if __name__ == "__main__" and "--all" in __import__("sys").argv:
    full_map()
