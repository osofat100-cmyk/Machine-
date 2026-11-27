#!/usr/bin/env python3
"""
The live machine re-picking every 1, 2, 3 ... 1,440 minutes (one day): 1,440 separate runs.

Same machine as machine_sim.py: starts on PEARL's first day on BigONE with no data,
re-picks the top of the smoothed 0.5%-100% buy/sell landscape from everything seen
so far, and stays in USDC while no setting has made money. Each run starts with $1,000.

The setting the machine would pick at a given minute does not depend on how often it
re-picks, so the pick is worked out once for every minute, and each of the 1,440 runs
uses the picks at its own re-pick times.

    python3 machine_speed.py          # -> machine_speed.png, data/machine_speed.csv
"""
import bisect
import csv
import multiprocessing as mp

import numpy as np

from landscape import COST, Market

STEPS = np.round(np.arange(0.5, 100.0001, 0.5), 2)
M = PB = PS = None


def smoother(n, sigma=2.0):
    """Matrix that blurs a length-n axis like landscape.smooth (edges repeat)."""
    r = int(3 * sigma)
    w = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    w /= w.sum()
    G = np.zeros((n, n))
    for i in range(n):
        for k, wk in zip(range(-r, r + 1), w):
            G[i, min(n - 1, max(0, i + k))] += wk
    return G


def all_events(m):
    """Every buy and sell of every one of the 40,000 settings, in time order."""
    c = m.close
    B = [m.buys(x) for x in STEPS]
    S = [m.sells(x) for x in STEPS]
    t, sid, kind, amt = [], [], [], []
    ns = len(STEPS)
    for j, bi in enumerate(B):
        if not bi:
            continue
        for i, si in enumerate(S):
            setting = i * ns + j                 # row = sell %, column = buy %
            cash, pos = 1000.0, 0
            while True:
                k = bisect.bisect_left(bi, pos)
                if k == len(bi):
                    break
                b = bi[k]
                coins = cash / (c[b + 1] * (1 + COST))
                t.append(b); sid.append(setting); kind.append(1); amt.append(coins)
                k = bisect.bisect_left(si, b + 1)
                if k == len(si):
                    break
                s = si[k]
                cash, pos = coins * c[s + 1] * (1 - COST), s + 1
                t.append(s); sid.append(setting); kind.append(-1); amt.append(cash)
    order = np.argsort(np.array(t), kind="stable")
    return np.array(t)[order], np.array(sid)[order], np.array(kind)[order], np.array(amt)[order]


def pick_every_minute(m, ev):
    """For every minute: the buy % and sell % the machine would pick from the data before it (nan = stay in USDC)."""
    t, sid, kind, amt = ev
    ns = len(STEPS)
    cash = np.full(ns * ns, 1000.0)
    coins = np.zeros(ns * ns)
    holding = np.zeros(ns * ns, bool)
    G = smoother(ns)
    pb = np.full(m.n, np.nan)
    ps = np.full(m.n, np.nan)
    e = 0
    for end in range(1, m.n):
        while e < len(t) and t[e] <= end - 2:
            s = sid[e]
            if kind[e] == 1:
                coins[s], holding[s] = amt[e], True
            else:
                cash[s], holding[s] = amt[e], False
            e += 1
        if not holding.any() and e == 0:
            continue                              # nothing has traded yet: stay in USDC
        val = np.where(holding, coins * m.close[end - 1] * (1 - COST), cash).reshape(ns, ns)
        sm = G @ val @ G.T
        i, j = np.unravel_index(sm.argmax(), sm.shape)
        if sm[i, j] > 1000.0:
            pb[end], ps[end] = STEPS[j], STEPS[i]
        if end % 20000 == 0:
            print(f"  picks worked out up to {m.time[end]:%b %d}", flush=True)
    return pb, ps


def init(m, pb, ps):
    global M, PB, PS
    M, PB, PS = m, pb, ps


def run(every):
    """One machine that re-picks every `every` minutes. Returns final $ and an hourly curve."""
    m, c = M, M.close
    cash, coins, b, s, buys, curve = 1000.0, 0.0, np.nan, np.nan, 0, []
    for k in range(m.n - 1):
        if k % every == 0 and k > 0:
            b, s = PB[k], PS[k]
        if b == b:                                # has a setting (not nan)
            if coins == 0 and m.at_low[k] and m.chg4[k] <= -b:
                coins, cash, buys = cash / (c[k + 1] * (1 + COST)), 0.0, buys + 1
            elif coins > 0 and m.near_high[k] and m.up_low[k] >= s:
                cash, coins = coins * c[k + 1] * (1 - COST), 0.0
        if every in (1, 60, 1440) and k % 60 == 0:
            curve.append(cash + coins * c[k])
    final = cash + coins * c[-1] * (1 - COST)
    return every, final, buys, curve + [final]


def main():
    m = Market(warmup=240)
    print(f"{m.time[0]:%b %d %H:%M} -> {m.time[-1]:%b %d %H:%M}: {m.n:,} minutes", flush=True)
    ev = all_events(m)
    print(f"{len(ev[0]):,} buys and sells across the 40,000 settings", flush=True)
    pb, ps = pick_every_minute(m, ev)
    print("running the 1,440 machines...", flush=True)
    with mp.Pool(mp.cpu_count(), initializer=init, initargs=(m, pb, ps)) as pool:
        res = sorted(pool.map(run, range(1, 1441), chunksize=8))
    hold = 1000 * m.close[-1] / m.close[0] * (1 - COST) ** 2
    with open("data/machine_speed.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["repick_every_minutes", "final_$", "buys"])
        for every, final, buys, _ in res:
            w.writerow([every, round(final, 2), buys])
    finals = np.array([r[1] for r in res])
    print(f"just holding: ${hold:,.0f}")
    for every in (1, 2, 5, 15, 30, 60, 120, 240, 480, 720, 1440):
        print(f"  every {every:>4} min: ${finals[every - 1]:,.0f}  ({res[every - 1][2]} buys)")
    print(f"beat holding: {(finals > hold).sum()} of 1,440   lowest ${finals.min():,.0f} (every {finals.argmin() + 1} min)"
          f"   highest ${finals.max():,.0f} (every {finals.argmax() + 1} min)   middle ${np.median(finals):,.0f}")
    times = [m.time[k] for k in range(0, m.n - 1, 60)] + [m.time[-1]]
    hold_curve = [1000 * m.close[k] / m.close[0] * (1 - COST) for k in range(0, m.n - 1, 60)] + [hold]
    plot(res, hold, times, hold_curve)


def plot(res, hold, times, hold_curve):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    blue = "#2a78d6"
    plt.rcParams.update({"font.size": 12, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    x = np.array([r[0] for r in res])
    y = np.array([r[1] for r in res])
    k = 31
    ys = np.convolve(np.pad(y, k // 2, mode="edge"), np.ones(k) / k, mode="valid")

    fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 11), facecolor=surface,
                                 gridspec_kw={"height_ratios": [1.3, 1], "hspace": 0.35})
    for a_ in (ax, bx):
        a_.set_facecolor(surface)
        a_.grid(axis="y", color=gridc, lw=0.8)
        for side in ("top", "right"):
            a_.spines[side].set_visible(False)
        a_.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))

    ax.plot(x, y, color=blue, lw=0.8, alpha=0.3)
    ax.plot(x, ys, color=blue, lw=2.4)
    ax.axhline(hold, color=ink2, lw=1.4, ls=(0, (5, 3)))
    ax.text(1440, hold, f"just holding ${hold:,.0f} ", ha="right", va="bottom", fontsize=10.5, color=ink2)
    for every, label in ((1, "every minute"), (60, "every hour"), (1440, "every day")):
        ax.plot([every], [y[every - 1]], "o", ms=8, color=blue, mec=surface, mew=2)
        ax.annotate(f"{label}: ${y[every - 1]:,.0f}", (every, y[every - 1]), xytext=(8, 10),
                    textcoords="offset points", fontsize=10.5, color=ink,
                    ha="right" if every == 1440 else "left")
    ax.set_xlim(0, 1450)
    ax.set_xticks([1, 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1440])
    ax.set_xticklabels(["1m", "2h", "4h", "6h", "8h", "10h", "12h", "14h", "16h", "18h", "20h", "22h", "24h"])
    ax.set_xlabel("how often the machine re-picks its buy/sell %  (every 1 minute ... every 1,440 minutes)")
    ax.set_ylabel("money on Nov 20 ($)")
    ax.set_title("1,440 machines, each starting Jun 25 with $1,000 and no data  ·  thin line = each run, "
                 "thick = smoothed", loc="left", fontsize=12.5, pad=10)

    curves = {r[0]: r[3] for r in res if r[3]}
    bx.plot(times, hold_curve, color=muted, lw=1.6, ls=(0, (5, 3)), label=f"just holding  ${hold:,.0f}")
    for every, col, label in ((1, "#2a78d6", "every minute"), (60, "#eb6834", "every hour"),
                              (1440, "#1baf7a", "every day")):
        bx.plot(times, curves[every], color=col, lw=1.8, label=f"{label}  ${curves[every][-1]:,.0f}")
    bx.legend(loc="upper left", frameon=False, fontsize=10.5)
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    bx.set_ylabel("account value ($)")
    bx.set_title("Account over time for three of them", loc="left", fontsize=12.5, pad=10)
    fig.savefig("machine_speed.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("saved machine_speed.png")


if __name__ == "__main__":
    main()
