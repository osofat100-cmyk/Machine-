#!/usr/bin/env python3
"""
Four robots, following docs/machine_math.tex (Sections 3-10). Each starts with $1,000 on
25 Jun and trades PEARL-USDT minute by minute to 20 Nov, paying 0.7% per buy and per sell.

  1. No data          - setting from the data so far; update interval adapts
  2. All data, adapts - setting from (all data) x (data so far); update interval adapts
  3. Stays at 10/34   - never updates
  4. All data, fixed  - setting like robot 2; update interval picked once on day one

Settings: buy % and sell % in 0.1% steps. Update intervals: every 1 ... 1,440 minutes.
Safest interval: middle of the biggest run of intervals at or above the average money.

    python3 robots.py          # -> robots.png, data/robots_*.csv   (takes a while)
"""
import bisect
import csv
import time
from array import array

import numpy as np

from landscape import COST, Market

STEP = 0.1                      # % grid step
SIGMA = 10                      # smoothing: 10 grid steps = 1%
DELTAS = np.arange(1, 1441)     # update every 1 ... 1,440 minutes


def grids(m):
    """0.1% grid up to the largest moves in the data + 3% (beyond that the landscape is flat)."""
    bmax = float(np.nanmax(-m.chg4[m.at_low]))
    smax = float(np.nanmax(m.up_low[m.near_high]))
    buy = np.round(np.arange(STEP, min(100.0, bmax + 3) + 1e-9, STEP), 1)
    sell = np.round(np.arange(STEP, min(100.0, smax + 3) + 1e-9, STEP), 1)
    return buy, sell


def smoother(n, sigma):
    r = int(3 * sigma)
    w = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    w /= w.sum()
    K = np.zeros((n, n))
    for i in range(n):
        for k, wk in zip(range(-r, r + 1), w):
            K[i, min(n - 1, max(0, i + k))] += wk
    return K


def all_events(m, buy, sell):
    """Every buy and sell of every setting over the whole history, in time order."""
    c = m.close
    B = [m.buys(x) for x in buy]
    S = [m.sells(x) for x in sell]
    nb = len(buy)
    t, sid, kind, amt = array("i"), array("i"), array("b"), array("d")
    for j, bi in enumerate(B):
        if not bi:
            continue
        for i, si in enumerate(S):
            setting = i * nb + j
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
    t = np.frombuffer(t, dtype=np.int32)
    order = np.argsort(t, kind="stable")
    return (t[order], np.frombuffer(sid, dtype=np.int32)[order],
            np.frombuffer(kind, dtype=np.int8)[order], np.frombuffer(amt, dtype=np.float64)[order])


class HillTop:
    """Top of the smoothed landscape: K_s V K_b^T, then the highest point."""

    def __init__(self, nb, ns):
        self.Kb = smoother(nb, SIGMA).astype(np.float32)
        self.Ks = smoother(ns, SIGMA).astype(np.float32)

    def __call__(self, V):
        S = self.Ks @ V @ self.Kb.T
        i, j = np.unravel_index(S.argmax(), S.shape)
        return float(S[i, j]), (i, j)


def landscape_picks(m, ev, buy, sell, log=print):
    """For every minute: robot 1's pick (data so far) and robot 2's pick (all data x data so far)."""
    t, sid, kind, amt = ev
    nb, ns = len(buy), len(sell)
    top = HillTop(nb, ns)
    cash = np.full(nb * ns, 1000.0)
    coins = np.zeros(nb * ns)
    holding = np.zeros(nb * ns, bool)

    # V_all: every setting's money over all the data
    for e in range(len(t)):
        s = sid[e]
        if kind[e] == 1:
            coins[s], holding[s] = amt[e], True
        else:
            cash[s], holding[s] = amt[e], False
    v_all = np.where(holding, coins * m.close[-1] * (1 - COST), cash).reshape(ns, nb)
    prior = (v_all / 1000.0).astype(np.float32)
    v, (i, j) = top(v_all.astype(np.float32))
    log(f"all-data hill top: buy {buy[j]}% / sell {sell[i]}% (smoothed ${v:,.0f})")

    cash[:] = 1000.0; coins[:] = 0.0; holding[:] = False
    PB1 = np.full(m.n, np.nan); PS1 = np.full(m.n, np.nan)
    PB2 = np.full(m.n, np.nan); PS2 = np.full(m.n, np.nan)
    e, t0 = 0, time.time()
    for end in range(1, m.n):
        while e < len(t) and t[e] <= end - 2:
            s = sid[e]
            if kind[e] == 1:
                coins[s], holding[s] = amt[e], True
            else:
                cash[s], holding[s] = amt[e], False
            e += 1
        V = np.where(holding, coins * m.close[end - 1] * (1 - COST), cash).reshape(ns, nb).astype(np.float32)
        if e > 0:
            v1, (i, j) = top(V)
            if v1 > 1000.0:
                PB1[end], PS1[end] = buy[j], sell[i]
        v2, (i, j) = top(V * prior)
        if v2 > 1000.0:
            PB2[end], PS2[end] = buy[j], sell[i]
        if end % 20000 == 0:
            log(f"  landscapes up to {m.time[end]:%b %d}  ({time.time() - t0:.0f}s)")
    return PB1, PS1, PB2, PS2


def safest(F):
    """Middle of the biggest run of intervals at or above the average (ties: higher run average)."""
    high = F >= F.mean()
    x = np.concatenate(([0], high.astype(np.int8), [0]))
    d = np.diff(x)
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1
    lengths = ends - starts + 1
    cand = np.flatnonzero(lengths == lengths.max())
    if len(cand) > 1:
        cand = [max(cand, key=lambda q: F[starts[q]:ends[q] + 1].mean())]
    a, z = starts[cand[0]], ends[cand[0]]
    return int(DELTAS[(a + z) // 2])


class Account:
    def __init__(self):
        self.cash, self.coins, self.buys = 1000.0, 0.0, 0

    def step(self, m, k, b, s):
        c = m.close
        if b != b:                                 # no setting yet: stay in USDC
            return
        if self.coins == 0 and m.at_low[k] and m.chg4[k] <= -b:
            self.coins, self.cash, self.buys = self.cash / (c[k + 1] * (1 + COST)), 0.0, self.buys + 1
        elif self.coins > 0 and m.near_high[k] and m.up_low[k] >= s:
            self.cash, self.coins = self.coins * c[k + 1] * (1 - COST), 0.0

    def value(self, price):
        return self.cash + self.coins * price * (1 - COST)


def run_robots(m, PB, PS, choose, accounts, record, F_prior=None):
    """Run the 1,440 interval machines on picks (PB, PS) and the robots that read them.
    choose(F) -> {robot: interval} each minute. Returns each interval machine's final money."""
    c = m.close
    n_d = len(DELTAS)
    cash = np.full(n_d, 1000.0)
    coins = np.zeros(n_d)
    b = np.full(n_d, np.nan)
    s = np.full(n_d, np.nan)
    F = np.full(n_d, 1000.0)
    for k in range(m.n - 1):
        intervals = choose(F if F_prior is None else F_prior * F / 1000.0)
        for name, d in intervals.items():
            u = (k // d) * d
            accounts[name].step(m, k, PB[u] if u > 0 else np.nan, PS[u] if u > 0 else np.nan)
        if k > 0:
            upd = (k % DELTAS) == 0
            b[upd], s[upd] = PB[k], PS[k]
        if m.at_low[k] or m.near_high[k]:
            hold = coins > 0
            has = ~np.isnan(b)
            buy = has & ~hold & m.at_low[k] & (m.chg4[k] <= -np.nan_to_num(b, nan=1e9))
            sell = has & hold & m.near_high[k] & (m.up_low[k] >= np.nan_to_num(s, nan=1e9))
            coins[buy], cash[buy] = cash[buy] / (c[k + 1] * (1 + COST)), 0.0
            cash[sell], coins[sell] = coins[sell] * c[k + 1] * (1 - COST), 0.0
        F = cash + coins * c[k] * (1 - COST)
        record(k, intervals)
    return cash + coins * c[-1] * (1 - COST)


def main():
    log = lambda *a: print(*a, flush=True)
    m = Market(warmup=240)
    buy, sell = grids(m)
    log(f"{m.time[0]:%b %d %H:%M} -> {m.time[-1]:%b %d %H:%M}: {m.n:,} minutes")
    log(f"grid: buy 0.1-{buy[-1]}%, sell 0.1-{sell[-1]}% at 0.1% = {len(buy) * len(sell):,} settings "
        f"(the rest of the 0.1-100% grid is flat)")
    t0 = time.time()
    ev = all_events(m, buy, sell)
    log(f"{len(ev[0]):,} buys and sells across all settings ({time.time() - t0:.0f}s)")
    PB1, PS1, PB2, PS2 = landscape_picks(m, ev, buy, sell, log)
    np.savez_compressed("data/robots_picks.npz", PB1=PB1, PS1=PS1, PB2=PB2, PS2=PS2)

    names = ["1. No data", "2. All data, adapts", "3. Stays at 10/34", "4. All data, fixed interval"]
    acc = {n: Account() for n in names}
    hourly = {n: [] for n in names}
    paths = {"1. No data": [], "2. All data, adapts": []}
    times = []

    def rec1(k, iv):
        if k % 60 == 0:
            times.append(m.time[k])
            hourly[names[0]].append(acc[names[0]].value(m.close[k]))
            paths[names[0]].append((iv[names[0]], PB1[(k // iv[names[0]]) * iv[names[0]]],
                                    PS1[(k // iv[names[0]]) * iv[names[0]]]))
        acc[names[2]].step(m, k, 10.0, 34.0)       # robot 3 trades alongside
        if k % 60 == 0:
            hourly[names[2]].append(acc[names[2]].value(m.close[k]))

    log("running robot 1 (and robot 3) with the 1,440 interval machines...")
    F_all = run_robots(m, PB1, PS1, lambda F: {names[0]: safest(F)}, acc, rec1)
    fixed = safest(F_all)
    log(f"robot 1's interval machines over all the data -> safest interval {fixed} min "
        f"(robot 4 keeps this)")

    def rec2(k, iv):
        if k % 60 == 0:
            for n in names[1], names[3]:
                hourly[n].append(acc[n].value(m.close[k]))
            paths[names[1]].append((iv[names[1]], PB2[(k // iv[names[1]]) * iv[names[1]]],
                                    PS2[(k // iv[names[1]]) * iv[names[1]]]))

    log("running robots 2 and 4...")
    run_robots(m, PB2, PS2, lambda G: {names[1]: safest(G), names[3]: fixed}, acc, rec2, F_prior=F_all)

    final = {n: acc[n].value(m.close[-1]) for n in names}
    hold = 1000 * m.close[-1] / m.close[0] * (1 - COST) ** 2
    hold_curve = [1000 * m.close[k] / m.close[0] * (1 - COST) for k in range(0, m.n - 1, 60)]
    for n in names:
        hourly[n].append(final[n])
    hold_curve.append(hold)
    times.append(m.time[-1])

    # month ends
    month_idx = {}
    for idx, tm in enumerate(times):
        month_idx[tm.strftime("%Y-%m")] = idx
    rows = [(f"{times[i]:%b %d}", [hourly[n][i] for n in names], hold_curve[i]) for i in month_idx.values()]
    with open("data/robots_monthly.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date"] + names + ["just holding"])
        for d, vals, h in rows:
            w.writerow([d] + [round(v, 2) for v in vals] + [round(h, 2)])
    with open("data/robots_hourly.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time"] + names + ["just holding", "robot1_interval", "robot1_buy", "robot1_sell",
                                       "robot2_interval", "robot2_buy", "robot2_sell"])
        for i, tm in enumerate(times):
            p1 = paths[names[0]][i] if i < len(paths[names[0]]) else ("", "", "")
            p2 = paths[names[1]][i] if i < len(paths[names[1]]) else ("", "", "")
            w.writerow([tm.strftime("%Y-%m-%d %H:%M")] + [round(hourly[n][i], 2) for n in names]
                       + [round(hold_curve[i], 2)] + list(p1) + list(p2))

    log("\nmoney at each month end (and the last day):")
    log(f"{'':<8}" + "".join(f"{n:>30}" for n in names) + f"{'just holding':>15}")
    for d, vals, h in rows:
        log(f"{d:<8}" + "".join(f"{v:>30,.0f}" for v in vals) + f"{h:>15,.0f}")
    for n in names:
        log(f"{n:<30} ${final[n]:,.0f}  ({acc[n].buys} buys)")
    log(f"{'just holding':<30} ${hold:,.0f}")
    plot(times, hourly, hold_curve, names, final, hold, paths)


def plot(times, hourly, hold_curve, names, final, hold, paths):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    colors = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
    plt.rcParams.update({"font.size": 12, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 11), facecolor=surface, sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1], "hspace": 0.12})
    for a_ in (ax, bx):
        a_.set_facecolor(surface)
        a_.grid(axis="y", color=gridc, lw=0.8)
        for side in ("top", "right"):
            a_.spines[side].set_visible(False)
    ax.plot(times, hold_curve, color=muted, lw=1.6, ls=(0, (5, 3)), label=f"just holding  ${hold:,.0f}")
    same = np.allclose(hourly[names[1]], hourly[names[3]])
    for n, col in zip(names, colors):
        note = "  (same line as 4)" if same and n == names[1] else ""
        ax.plot(times, hourly[n], color=col, lw=3.2 if note else 1.8, label=f"{n}  ${final[n]:,.0f}{note}")
    ax.legend(loc="upper left", frameon=False, fontsize=11)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_ylabel("account value ($)")
    ax.set_title("Four robots, each starting 25 Jun with $1,000 (0.1% settings, 1-1,440 minute intervals)",
                 loc="left", fontsize=13, pad=10)
    for n, col, ls in ((names[0], colors[0], "-"), (names[1], colors[1], "-")):
        p = paths[n]
        bx.plot(times[:len(p)], [x[1] for x in p], color=col, lw=1.4, ls=ls, label=f"{n}: buy %")
        bx.plot(times[:len(p)], [x[2] for x in p], color=col, lw=1.4, ls=(0, (3, 2)), label=f"{n}: sell %")
    bx.set_ylabel("setting (%)")
    bx.legend(loc="upper right", frameon=False, fontsize=10, ncol=2)
    bx.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.savefig("robots.png", dpi=110, facecolor=surface, bbox_inches="tight")
    print("saved robots.png", flush=True)


if __name__ == "__main__":
    main()
