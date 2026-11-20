#!/usr/bin/env python3
"""
Merging instead of resetting (docs/machine_math.tex, section 11), tested on PEARL's history.

  * Every setting (b, s) keeps ONE practice account from the first minute, never reset.
  * 100 lines: line p keeps p = 1%..100% of the old data each time the watcher (engine.py,
    sensitivity 14) sees the trajectory change. Data j changes old counts with weight p^j.
  * Every hour each line picks the top of its smoothed landscape.
  * Accuracy of a line = share of its past picks that made money H minutes later, counting only
    picks whose H minutes have already passed. H runs from 5 minutes to 14 days.
  * Risk = share of money put in on a buy: fixed 1%..100%, or Kelly  f = a - (1 - a) / R.
  * Merged robot: every hour follows the middle of the biggest stretch of lines with accuracy at or
    above the average.

Variations: 100 lines x 100 risk levels, 100 lines x Kelly x 14 horizons, merged x 14 horizons x
(Kelly + 100 risk levels). Chosen on 25 Jun - 30 Sep, checked on 1 Oct - 20 Nov.

    python3 merge_lines.py          # -> data/merge_*.csv, data/merge_lines.npz, merge_lines.png
    python3 merge_lines.py plot     # redraw the chart from saved results
"""
import csv
import math
import sys
import time

import numpy as np
import pandas as pd

from engine import AT_LOW, NEAR_HIGH, TIE, Book, Engine, feed, safest

ETA = 14.0
P = np.arange(1, 101) / 100.0                    # keep fractions
RISK = np.arange(1, 101) / 100.0                 # fixed risk levels
HORIZONS = [("5 min", 5), ("15 min", 15), ("30 min", 30), ("1 hour", 60), ("2 hours", 120),
            ("4 hours", 240), ("8 hours", 480), ("12 hours", 720), ("1 day", 1440), ("2 days", 2880),
            ("3 days", 4320), ("5 days", 7200), ("7 days", 10080), ("14 days", 20160)]
TRAIN_END = "2026-10-01"
log = lambda *a: print(*a, flush=True)


# ---------------------------------------------------------------------------- 1. the lines
def build(df):
    """Run the tested engine once for prices, costs, hour boundaries and trajectory changes, then
    the continuous accounts, the 100 lines and their hourly picks."""
    t0 = time.time()
    e = feed(Engine(eta=ETA), df)
    n, hk = e.n, np.array(e.hk)
    changes = {}
    for t in e.library:                            # detected at boundary t["detected"], starts at t["b"]
        changes.setdefault(t["detected"], []).append(t["b"])
    need = {s for v in changes.values() for s in v}
    log(f"engine pass {time.time() - t0:.0f}s: {n:,} minutes, {len(hk):,} hours, {len(e.library)} trajectory changes")

    N, nl = len(e.B), len(P)
    book = Book(e.B, e.S)
    sig = np.zeros((nl, N))                         # line sums of weighted hourly log growth
    lnv_prev = np.full(N, math.log(1000.0))
    snaps = {}
    pick = np.full((len(hk), nl), -1, np.int32)     # setting index picked by each line at each hour
    ev_t, ev_s, ev_k, ev_a = [], [], [], []
    bmap = {int(k): j for j, k in enumerate(hk)}
    Ks, KbT, ns, nb = e.Ks, e.KbT, e.ns, e.nb
    t0 = time.time()
    for k in range(n):
        j = bmap.get(k)
        if j is not None:
            lnv = np.log(book.value(e.cl[k - 1], e.kap[k - 1]))
            sig += lnv - lnv_prev
            lnv_prev = lnv
            if j in need:
                snaps[j] = lnv.copy()
            for s in changes.get(j, []):            # trajectory changed: keep p of the older data
                d = lnv - snaps[s]
                sig = P[:, None] * (sig - d) + d
            L = (1000.0 * np.exp(sig)).astype(np.float32).reshape(nl, ns, nb)
            S = np.matmul(np.matmul(Ks, L), KbT)
            for q in range(nl):
                Sq = S[q]
                f = int(Sq.argmax())
                top = Sq.flat[f]
                if top <= 1000.0 * (1 + 1e-6):
                    continue
                tied = Sq >= top * (1 - TIE)
                if np.count_nonzero(tied) > 1:
                    rows, cols = np.nonzero(tied)
                    m = int(((rows - rows.mean()) ** 2 + (cols - cols.mean()) ** 2).argmin())
                    f = int(rows[m]) * nb + int(cols[m])
                pick[j, q] = f
            if j % 500 == 0:
                log(f"  hour {j:,}/{len(hk):,}  ({time.time() - t0:.0f}s)")
        pb, ps = book.pb, book.ps
        book.minute(e.cl[k], e.U[k], e.D[k], e.R[k], e.kap[k])
        if pb is not None:
            i = np.flatnonzero(pb)
            ev_t.append(np.full(len(i), k, np.int32)); ev_s.append(i.astype(np.int32))
            ev_k.append(np.ones(len(i), np.int8)); ev_a.append(book.coins[i].copy())
        if ps is not None:
            i = np.flatnonzero(ps)
            ev_t.append(np.full(len(i), k, np.int32)); ev_s.append(i.astype(np.int32))
            ev_k.append(np.zeros(len(i), np.int8)); ev_a.append(book.cash[i].copy())
    log(f"lines pass {time.time() - t0:.0f}s")
    ev = [np.concatenate(x) for x in (ev_t, ev_s, ev_k, ev_a)]
    order = np.lexsort((ev[0], ev[1]))
    ev = [x[order] for x in ev]
    ptr = np.searchsorted(ev[1], np.arange(N + 1))
    return {"e": e, "hk": hk, "pick": pick, "ev": ev, "ptr": ptr, "book": book}


def values(d, theta, times):
    """Continuous account value of setting theta at the given minutes (after that minute's fills)."""
    e, (et, es, ek, ea), ptr = d["e"], d["ev"], d["ptr"]
    i0, i1 = ptr[theta], ptr[theta + 1]
    q = np.searchsorted(et[i0:i1], times, side="right") - 1
    out = np.full(len(times), 1000.0)
    has = q >= 0
    idx = i0 + q[has]
    hold = ek[idx] == 1
    tt = np.asarray(times)[has]
    out[has] = np.where(hold, ea[idx] * e.cl[tt] * (1 - e.kap[tt]), ea[idx])
    return out


# ---------------------------------------------------------------------------- 2. accuracy
def outcomes(d):
    """For every horizon and line: (time the outcome is known, log result) of each hourly pick."""
    e, hk, pick = d["e"], d["hk"], d["pick"]
    tau = hk - 1                                     # pick at boundary j is made on minute hk[j]-1
    res = {name: [None] * len(P) for name, _ in HORIZONS}
    per_theta = {}
    for q in range(len(P)):
        for j in np.flatnonzero(pick[:, q] >= 0):
            per_theta.setdefault(int(pick[j, q]), []).append((q, j))
    raw = {name: [[] for _ in P] for name, _ in HORIZONS}
    for theta, lst in per_theta.items():
        js = np.array([j for _, j in lst])
        qs = np.array([q for q, _ in lst])
        v0 = values(d, theta, tau[js])
        for name, H in HORIZONS:
            t1 = tau[js] + H
            ok = t1 <= e.n - 1
            v1 = values(d, theta, t1[ok])
            y = np.log(v1 / v0[ok])
            for q, tk, yy in zip(qs[ok], t1[ok], y):
                raw[name][q].append((tk, yy))
    for name, _ in HORIZONS:
        for q in range(len(P)):
            a = np.array(sorted(raw[name][q])) if raw[name][q] else np.zeros((0, 2))
            y = a[:, 1] if len(a) else np.zeros(0)
            nz = np.abs(y) > 1e-12
            res[name][q] = {"t": a[:, 0].astype(np.int64) if len(a) else np.zeros(0, np.int64),
                            "pos": np.cumsum(y > 1e-12), "nz": np.cumsum(nz),
                            "win": np.cumsum(np.where(y > 1e-12, np.expm1(np.maximum(y, 0)), 0.0)),
                            "loss": np.cumsum(np.where(y < -1e-12, -np.expm1(np.minimum(y, 0)), 0.0))}
    return res


def acc_matrix(acc_h, times):
    """Accuracy of every line at each of the given minutes (nan = no outcome known yet)."""
    out = np.full((len(times), len(P)), np.nan)
    for q, st in enumerate(acc_h):
        c = np.searchsorted(st["t"], times, side="right")
        ok = c > 0
        nz = np.zeros(len(times))
        pos = np.zeros(len(times))
        nz[ok], pos[ok] = st["nz"][c[ok] - 1], st["pos"][c[ok] - 1]
        good = nz > 0
        out[good, q] = pos[good] / nz[good]
    return out


def stats_at(st, t):
    """Accuracy, win/loss ratio and Kelly fraction of one line, using outcomes known by minute t."""
    c = int(np.searchsorted(st["t"], t, side="right"))
    if c == 0 or st["nz"][c - 1] == 0:
        return math.nan, math.nan, 0.01
    pos, nz = st["pos"][c - 1], st["nz"][c - 1]
    a = pos / nz
    neg = nz - pos
    if pos == 0:
        return a, 0.0, 0.01
    if neg == 0:
        return a, math.inf, float(min(1.0, max(0.01, a)))
    R = (st["win"][c - 1] / pos) / (st["loss"][c - 1] / neg)
    return a, R, float(min(1.0, max(0.01, a - (1 - a) / R)))


# ---------------------------------------------------------------------------- 3. robots
def trades(d, setting_at):
    """The robot's buys and sells. setting_at(j) = setting index used during hour j (or -1).
    Returns list of [buy_decision_minute, buy_fill_minute, sell_fill_minute or -1]."""
    e, hk = d["e"], d["hk"]
    cand = d.setdefault("cand", np.flatnonzero((e.U[:e.n] <= AT_LOW) | (e.D[:e.n] <= NEAR_HIGH)))
    hour_of = np.searchsorted(hk, cand, side="right") - 1
    out, holding, ready = [], False, 0
    for k, j in zip(cand, hour_of):
        if k < ready or k >= e.n - 1 or j < 0:
            continue
        th = setting_at(int(j))
        if th < 0:
            continue
        b, s = e.B[th], e.S[th]
        if not holding and e.U[k] <= AT_LOW and e.R[k] <= -b:
            out.append([int(k), int(k) + 1, -1])
            holding, ready = True, k + 1
        elif holding and e.D[k] <= NEAR_HIGH and e.U[k] >= s:
            out[-1][2] = int(k) + 1
            holding, ready = False, k + 1
    return out


def money(d, tr, risk, at):
    """Value at minute `at` for each risk level in `risk` (array, or one per trade for Kelly)."""
    e = d["e"]
    c, kap = e.cl, e.kap
    risk = np.asarray(risk, float)
    v = np.ones(risk.shape[-1] if risk.ndim > 1 else len(risk))
    for n_, (kd, kb, ks) in enumerate(tr):
        if kb > at:
            break
        r = risk[n_] if risk.ndim > 1 else risk
        buy = c[kb] * (1 + kap[kb])
        if ks != -1 and ks <= at:
            m = c[ks] * (1 - kap[ks]) / buy
        else:
            m = c[at] * (1 - kap[at]) / buy
        v = v * (1 - r + r * m)
    return 1000.0 * v


def run_all(d, acc):
    e, hk, pick = d["e"], d["hk"], d["pick"]
    cut = int(np.searchsorted(e.ts[:e.n], int(np.datetime64(TRAIN_END, "m").astype(np.int64)))) - 1
    end = e.n - 1
    out = {"cut": cut, "end": end}

    # A. fixed line x fixed risk, and fixed line x Kelly per horizon
    grid_tr, grid_te = np.zeros((len(P), len(RISK))), np.zeros((len(P), len(RISK)))
    kel_tr, kel_te = np.zeros((len(P), len(HORIZONS))), np.zeros((len(P), len(HORIZONS)))
    ntr = np.zeros(len(P), int)
    for q in range(len(P)):
        tr = trades(d, lambda j, q=q: int(pick[j, q]))
        ntr[q] = len(tr)
        a, b = money(d, tr, RISK, cut), money(d, tr, RISK, end)
        grid_tr[q], grid_te[q] = a, 1000 * b / a
        for h, (name, _) in enumerate(HORIZONS):
            f = np.array([[stats_at(acc[name][q], kd)[2]] for kd, _, _ in tr]) if tr else np.zeros((0, 1))
            a, b = money(d, tr, f, cut)[0], money(d, tr, f, end)[0]
            kel_tr[q, h], kel_te[q, h] = a, 1000 * b / a
    out.update(grid_tr=grid_tr, grid_te=grid_te, kel_tr=kel_tr, kel_te=kel_te, ntr=ntr)
    log("fixed lines done")

    # B. merged robot: each hour follow the middle of the biggest stretch of accurate lines
    m_tr, m_te = np.zeros((len(HORIZONS), len(RISK) + 1)), np.zeros((len(HORIZONS), len(RISK) + 1))
    m_line = np.zeros((len(HORIZONS), len(hk)), int)
    m_n = np.zeros(len(HORIZONS), int)
    for h, (name, _) in enumerate(HORIZONS):
        line = np.full(len(hk), 99)
        A = acc_matrix(acc[name], hk - 1)
        for j in range(len(hk)):
            if not np.all(np.isnan(A[j])):
                line[j] = safest(np.nan_to_num(A[j], nan=-1.0)) - 1
        m_line[h] = line
        tr = trades(d, lambda j: int(pick[j, line[j]]))
        m_n[h] = len(tr)
        f = np.array([[stats_at(acc[name][line[np.searchsorted(hk, kd, side="right") - 1]], kd)[2]]
                      for kd, _, _ in tr]) if tr else np.zeros((0, 1))
        a = np.concatenate([money(d, tr, RISK, cut), money(d, tr, f, cut)])
        b = np.concatenate([money(d, tr, RISK, end), money(d, tr, f, end)])
        m_tr[h], m_te[h] = a, 1000 * b / a
        log(f"  merged, accuracy after {name:<8}: {len(tr)} trades; train ${a[-1]:,.0f} test ${m_te[h, -1]:,.0f} (Kelly)")
    out.update(m_tr=m_tr, m_te=m_te, m_line=m_line, m_n=m_n)

    # accuracy table over the whole history (descriptive)
    acc_all = np.array([[stats_at(acc[name][q], end)[0] for q in range(len(P))] for name, _ in HORIZONS])
    out["acc_all"] = acc_all
    hold = lambda a_, b_: 1000 * e.cl[b_] * (1 - e.kap[b_]) / (e.cl[a_] * (1 + e.kap[a_]))
    k0 = int(hk[0])
    out["hold"] = (hold(k0, cut), hold(cut, end), hold(k0, end))
    return out


# ---------------------------------------------------------------------------- 4. choosing
def biggest_high_area(Z):
    """Cells of the biggest connected area at or above the average; returns its middle cell."""
    high = Z >= Z.mean()
    if not high.any():
        high[:] = True
    seen = np.zeros_like(high)
    best = []
    for i0, j0 in zip(*np.nonzero(high)):
        if seen[i0, j0]:
            continue
        comp, stack = [], [(i0, j0)]
        seen[i0, j0] = True
        while stack:
            i, j = stack.pop()
            comp.append((i, j))
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < Z.shape[0] and 0 <= b < Z.shape[1] and high[a, b] and not seen[a, b]:
                    seen[a, b] = True
                    stack.append((a, b))
        if len(comp) > len(best) or (len(comp) == len(best) and np.mean([Z[x] for x in comp]) > np.mean([Z[x] for x in best])):
            best = comp
    ci, cj = np.mean([x[0] for x in best]), np.mean([x[1] for x in best])
    mid = min(best, key=lambda x: (x[0] - ci) ** 2 + (x[1] - cj) ** 2)
    return mid, len(best)


def stretch_middle(v):
    v = np.asarray(v, float)
    high = v >= v.mean()
    if not high.any():
        high[:] = True
    x = np.concatenate(([0], high.astype(int), [0]))
    dd = np.diff(x)
    s, z = np.flatnonzero(dd == 1), np.flatnonzero(dd == -1) - 1
    L = z - s + 1
    best = max(np.flatnonzero(L == L.max()), key=lambda q: v[s[q]:z[q] + 1].mean())
    return int((s[best] + z[best]) // 2)


def report(o):
    ht, hte, hw = o["hold"]
    log(f"\njust holding: train ${ht:,.0f}, test ${hte:,.0f} per $1,000")
    log("\nACCURACY over the whole history (share of picks that made money), by keep fraction:")
    log(f"{'after':<10}" + "".join(f"{f'{p}%':>7}" for p in (1, 10, 25, 50, 75, 90, 100)))
    for h, (name, _) in enumerate(HORIZONS):
        log(f"{name:<10}" + "".join(f"{o['acc_all'][h, p - 1] * 100:>6.0f}%" for p in (1, 10, 25, 50, 75, 90, 100)))

    g_tr, g_te = o["grid_tr"], o["grid_te"]
    (qi, ri), size = biggest_high_area(g_tr)
    log(f"\n100 lines x 100 risk levels (10,000 runs):")
    log(f"  beat holding on the test: {(g_te > hte).sum():,} of 10,000; made money on the test: {(g_te > 1000).sum():,}")
    log(f"  chosen on train (middle of the biggest high area, {size:,} cells): keep {P[qi]:.0%}, risk {RISK[ri]:.0%}"
        f" -> train ${g_tr[qi, ri]:,.0f}, TEST ${g_te[qi, ri]:,.0f}")
    log(f"  never reset (keep 100%, risk 100%): train ${g_tr[99, 99]:,.0f}, test ${g_te[99, 99]:,.0f}")
    log(f"  keep 1%, risk 100%: train ${g_tr[0, 99]:,.0f}, test ${g_te[0, 99]:,.0f}")

    k_tr, k_te = o["kel_tr"], o["kel_te"]
    (qi, hi), size = biggest_high_area(k_tr)
    log(f"\n100 lines x Kelly risk x 14 horizons (1,400 runs):")
    log(f"  beat holding on the test: {(k_te > hte).sum():,} of 1,400; made money: {(k_te > 1000).sum():,}")
    log(f"  chosen on train: keep {P[qi]:.0%}, accuracy after {HORIZONS[hi][0]} -> train ${k_tr[qi, hi]:,.0f}, "
        f"TEST ${k_te[qi, hi]:,.0f}")

    m_tr, m_te = o["m_tr"], o["m_te"]
    log(f"\nMERGED robot (follows the most accurate stable group of lines, re-chosen every hour):")
    log(f"{'accuracy after':<16}{'trades':>7}{'train Kelly':>13}{'TEST Kelly':>12}{'train 100%':>12}{'TEST 100%':>11}")
    for h, (name, _) in enumerate(HORIZONS):
        log(f"{name:<16}{o['m_n'][h]:>7}{f'${m_tr[h, -1]:,.0f}':>13}{f'${m_te[h, -1]:,.0f}':>12}"
            f"{f'${m_tr[h, 99]:,.0f}':>12}{f'${m_te[h, 99]:,.0f}':>11}")
    hk_ = stretch_middle(m_tr[:, -1])
    log(f"  chosen on train (Kelly): accuracy after {HORIZONS[hk_][0]} -> TEST ${m_te[hk_, -1]:,.0f}")
    log(f"  all merged variations beating holding on the test: {(m_te > hte).sum()} of {m_te.size}")
    return {"grid": biggest_high_area(g_tr)[0], "kelly": biggest_high_area(k_tr)[0], "merged_h": hk_}


def save(o):
    np.savez_compressed("data/merge_lines.npz", **{k: v for k, v in o.items() if isinstance(v, np.ndarray)},
                        hold=np.array(o["hold"]), cut=o["cut"], end=o["end"])
    with open("data/merge_grid.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["keep_%", "risk_%", "train_$", "test_$_per_1000"])
        for q in range(len(P)):
            for r in range(len(RISK)):
                w.writerow([q + 1, r + 1, round(o["grid_tr"][q, r], 2), round(o["grid_te"][q, r], 2)])
    with open("data/merge_merged.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["accuracy_after", "trades", "train_$_kelly", "test_$_kelly", "train_$_risk100", "test_$_risk100"])
        for h, (name, _) in enumerate(HORIZONS):
            w.writerow([name, o["m_n"][h], round(o["m_tr"][h, -1], 2), round(o["m_te"][h, -1], 2),
                        round(o["m_tr"][h, 99], 2), round(o["m_te"][h, 99], 2)])


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    z = np.load("data/merge_lines.npz")
    ht, hte, _ = z["hold"]
    surface, ink, ink2, muted, gridc = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
    plt.rcParams.update({"font.size": 11, "text.color": ink, "axes.labelcolor": ink2,
                         "xtick.color": muted, "ytick.color": muted, "axes.edgecolor": "#c3c2b7"})
    fig, axs = plt.subplots(2, 2, figsize=(14, 11), facecolor=surface,
                            gridspec_kw={"hspace": 0.38, "wspace": 0.22})
    for a_ in axs.flat:
        a_.set_facecolor(surface)
        for side in ("top", "right"):
            a_.spines[side].set_visible(False)

    ax = axs[0, 0]
    cols = {"1 hour": "#2a78d6", "1 day": "#eb6834", "7 days": "#1baf7a"}
    names = [n for n, _ in HORIZONS]
    for name, col in cols.items():
        h = names.index(name)
        ax.plot(np.arange(1, 101), z["acc_all"][h] * 100, color=col, lw=2, label=f"right after {name}")
    ax.axhline(50, color=muted, lw=1, ls=(0, (4, 3)))
    ax.set_xlabel("keep % of old data at a trajectory change (1 = reset, 100 = never reset)")
    ax.set_ylabel("picks that made money (%)")
    ax.set_title("Accuracy of each line over the whole history", loc="left", fontsize=12)
    ax.legend(frameon=False, fontsize=10)
    ax.grid(axis="y", color=gridc, lw=0.7)

    (qi, ri), _ = biggest_high_area(z["grid_tr"])
    for ax, Z, title in ((axs[0, 1], z["grid_tr"], "TRAIN 25 Jun - 30 Sep: $1,000 became"),
                         (axs[1, 0], z["grid_te"], "TEST 1 Oct - 20 Nov (unseen): $1,000 became")):
        im = ax.imshow(Z.T, origin="lower", aspect="auto", extent=[0.5, 100.5, 0.5, 100.5], cmap="RdBu",
                       norm=TwoSlopeNorm(vcenter=1000, vmin=min(Z.min(), 900), vmax=max(Z.max(), 1100)))
        ax.contour(np.arange(1, 101), np.arange(1, 101), Z.T, levels=[ht if "TRAIN" in title else hte],
                   colors=[ink], linewidths=1.4)
        ax.plot([qi + 1], [ri + 1], "o", ms=9, color="#eb6834", mec=surface, mew=2)
        ax.set_xlabel("keep % of old data")
        ax.set_ylabel("risk: % of money put in per buy")
        ax.set_title(title + "  (black line = just holding)", loc="left", fontsize=12)
        cb = fig.colorbar(im, ax=ax, pad=0.01)
        cb.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))

    ax = axs[1, 1]
    x = np.arange(len(HORIZONS))
    ax.bar(x - 0.2, z["m_te"][:, -1], width=0.4, color="#2a78d6", label="Kelly risk")
    ax.bar(x + 0.2, z["m_te"][:, 99], width=0.4, color="#9ec5f4", label="100% risk")
    ax.axhline(hte, color=ink2, lw=1.4, ls=(0, (5, 3)))
    ax.text(len(x) - 0.5, hte, f"just holding ${hte:,.0f} ", ha="right", va="bottom", fontsize=10, color=ink2)
    ax.axhline(1000, color=muted, lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=9)
    ax.set_xlabel("accuracy measured this long after each pick")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_title("Merged robot, TEST 1 Oct - 20 Nov (unseen)", loc="left", fontsize=12)
    ax.set_ylim(0, 1950)
    ax.legend(frameon=False, fontsize=10, loc="upper left", ncol=2)
    ax.grid(axis="y", color=gridc, lw=0.7)
    fig.suptitle("Merging instead of resetting: 100 keep-lines x 100 risk levels x 14 accuracy horizons",
                 x=0.06, ha="left", fontsize=14, y=0.97)
    fig.savefig("merge_lines.png", dpi=110, facecolor=surface, bbox_inches="tight")
    log("saved merge_lines.png")


CACHE = "data/merge_build.npz"


def save_build(d):
    e = d["e"]
    np.savez(CACHE, n=e.n, cl=e.cl[:e.n], kap=e.kap[:e.n], U=e.U[:e.n], D=e.D[:e.n], R=e.R[:e.n],
             ts=e.ts[:e.n], B=e.B, S=e.S, hk=d["hk"], pick=d["pick"], ptr=d["ptr"],
             ev_t=d["ev"][0], ev_s=d["ev"][1], ev_k=d["ev"][2], ev_a=d["ev"][3])


def load_build(n_rows):
    import os
    from types import SimpleNamespace
    if not os.path.exists(CACHE):
        return None
    z = np.load(CACHE)
    if int(z["n"]) != n_rows:
        return None
    e = SimpleNamespace(**{k: z[k] for k in ("cl", "kap", "U", "D", "R", "ts", "B", "S")}, n=int(z["n"]))
    return {"e": e, "hk": z["hk"], "pick": z["pick"], "ptr": z["ptr"],
            "ev": [z["ev_t"], z["ev_s"], z["ev_k"], z["ev_a"]]}


def main():
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    d = load_build(len(df))
    if d is None:
        d = build(df)
        save_build(d)
    else:
        log("using the saved lines from data/merge_build.npz")
    t0 = time.time()
    acc = outcomes(d)
    log(f"accuracy outcomes {time.time() - t0:.0f}s")
    o = run_all(d, acc)
    save(o)
    report(o)
    plot()


def check():
    """Checks on the first four weeks of data."""
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"]).iloc[:40000]
    d = build(df)
    e, hk, pick = d["e"], d["hk"], d["pick"]
    ok_all = True

    # 1. line 100% never resets, so it must pick exactly what the never-reset engine picks
    e0 = Engine(resets=False)
    ts = df["time"].values.astype("datetime64[m]").astype(np.int64)
    hi, lo, cl = df.high.values.astype(float), df.low.values.astype(float), df.close.values.astype(float)
    bset = {int(k): j for j, k in enumerate(hk)}
    mine, theirs = [], []
    for q in range(len(df)):
        if q in bset:
            j = bset[q]
            th = pick[j, 99]
            mine.append(None if th < 0 else (float(e.B[th]), float(e.S[th])))
            theirs.append(e0.pick)
        e0.step(int(ts[q]), hi[q], lo[q], cl[q])
    same = sum(a == b for a, b in zip(mine, theirs))
    ok = same == len(mine)
    ok_all &= ok
    log(f"{'PASS' if ok else 'FAIL'}  line 100% = never-reset engine: {same}/{len(mine)} hourly picks identical"
        f" ({sum(x is not None for x in mine)} of them real settings)")

    # 2. value lookups from the trade list equal the accounts themselves
    rng = np.random.default_rng(3)
    th = rng.integers(len(e.B), size=400)
    book_v = d["book"].value(e.cl[e.n - 1], e.kap[e.n - 1])
    gap = max(abs(values(d, int(t), np.array([e.n - 1]))[0] - book_v[t]) for t in th)
    ok = gap < 1e-6
    ok_all &= ok
    log(f"{'PASS' if ok else 'FAIL'}  account values from the trade list: biggest gap ${gap:.2e} over 400 settings")

    # 3. the risk formula equals a plain minute-by-minute account
    q, r = 49, 0.37
    tr = trades(d, lambda j: int(pick[j, q]))
    fast = money(d, tr, np.array([r]), e.n - 1)[0]
    cash, coins, pend = 1000.0, 0.0, None
    for k in range(e.n):
        c, kap = e.cl[k], e.kap[k]
        if pend == "B":
            put = r * cash
            coins, cash = put / (c * (1 + kap)), cash - put
        elif pend == "S":
            cash, coins = cash + coins * c * (1 - kap), 0.0
        pend = None
        j = int(np.searchsorted(hk, k, side="right")) - 1
        if j < 0 or pick[j, q] < 0 or k >= e.n - 1:
            continue
        b, s = e.B[pick[j, q]], e.S[pick[j, q]]
        if coins == 0 and e.U[k] <= AT_LOW and e.R[k] <= -b:
            pend = "B"
        elif coins > 0 and e.D[k] <= NEAR_HIGH and e.U[k] >= s:
            pend = "S"
    slow = cash + coins * e.cl[e.n - 1] * (1 - e.kap[e.n - 1])
    ok = abs(fast - slow) < 1e-6 and len(tr) > 0
    ok_all &= ok
    log(f"{'PASS' if ok else 'FAIL'}  risk formula: ${fast:,.4f} vs plain account ${slow:,.4f} ({len(tr)} trades)")

    # 4. accuracy only uses picks whose outcome was already known
    acc = outcomes(d)
    name, H = HORIZONS[8]
    bad = 0
    for t in rng.integers(hk[50], e.n - 1, size=30):
        a1 = stats_at(acc[name][30], int(t))[0]
        y = []
        for j in range(len(hk)):
            if hk[j] - 1 + H <= t and pick[j, 30] >= 0:
                v0, v1 = values(d, int(pick[j, 30]), np.array([hk[j] - 1, hk[j] - 1 + H]))
                y.append(math.log(v1 / v0))
        y = np.array(y)
        nz = np.abs(y) > 1e-12
        a2 = (y > 1e-12).sum() / nz.sum() if nz.sum() else math.nan
        bad += not ((math.isnan(a1) and math.isnan(a2)) or abs(a1 - a2) < 1e-12)
    ok = bad == 0
    ok_all &= ok
    log(f"{'PASS' if ok else 'FAIL'}  accuracy rebuilt from scratch at 30 random moments: {30 - bad}/30 identical")
    log("\nall checks passed" if ok_all else "\nSOME CHECKS FAILED")


def export(path="data/variations.json"):
    """Everything the variations page needs: three surfaces x three periods, and account lines."""
    import json
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    d = load_build(len(df))
    acc = outcomes(d)
    z = np.load("data/merge_lines.npz")
    e, hk, pick = d["e"], d["hk"], d["pick"]
    cut, end = int(z["cut"]), int(z["end"])
    r0 = lambda a: np.round(a, 0).astype(int).tolist()
    periods = {"whole": lambda tr, te: tr * te / 1000, "train": lambda tr, te: tr, "test": lambda tr, te: te}
    out = {"keep": list(range(1, 101)), "risk": list(range(1, 101)), "horizons": [n for n, _ in HORIZONS],
           "hold": {"whole": float(z["hold"][2]), "train": float(z["hold"][0]), "test": float(z["hold"][1])},
           "grid": {}, "kelly": {}, "merged": {}}
    for p, f in periods.items():
        out["grid"][p] = r0(f(z["grid_tr"], z["grid_te"]))             # [keep][risk]
        out["kelly"][p] = r0(f(z["kel_tr"], z["kel_te"]))               # [keep][horizon]
        out["merged"][p] = r0(f(z["m_tr"], z["m_te"]))                  # [horizon][risk 1..100, Kelly]

    # account lines, hour by hour from day one
    h3 = [n for n, _ in HORIZONS].index("3 days")
    A = acc_matrix(acc["3 days"], hk - 1)
    line = np.full(len(hk), 99)
    for j in range(len(hk)):
        if not np.all(np.isnan(A[j])):
            line[j] = safest(np.nan_to_num(A[j], nan=-1.0)) - 1
    tr_m = trades(d, lambda j: int(pick[j, line[j]]))
    f_m = np.array([[stats_at(acc["3 days"][line[np.searchsorted(hk, kd, side="right") - 1]], kd)[2]]
                    for kd, _, _ in tr_m])
    tr_100 = trades(d, lambda j: int(pick[j, 99]))
    tr_43 = trades(d, lambda j: int(pick[j, 42]))
    times = [int(hk[j]) - 1 for j in range(len(hk))] + [end]
    k0 = int(hk[0]) - 1
    lines = {
        "Just holding PEARL": [1000 * e.cl[t] * (1 - e.kap[t]) / (e.cl[k0] * (1 + e.kap[k0])) for t in times],
        "Never reset (keep 100%, risk 100%)": [money(d, tr_100, np.array([1.0]), t)[0] for t in times],
        "Merged robot, risk 100%": [money(d, tr_m, np.array([1.0]), t)[0] for t in times],
        "Merged robot, Kelly risk": [money(d, tr_m, f_m, t)[0] for t in times],
        "Keep 43%, risk 77% (picked on Jun-Sep)": [money(d, tr_43, np.array([0.77]), t)[0] for t in times],
    }
    out["times"] = [int(e.ts[t]) for t in times]
    out["lines"] = {k: r0(np.array(v)) for k, v in lines.items()}
    out["thin_until"] = int(np.datetime64("2026-09-21", "m").astype(np.int64))
    out["cut"] = int(e.ts[cut])
    out["trades"] = {"Merged robot, risk 100%": len(tr_m), "Never reset (keep 100%, risk 100%)": len(tr_100),
                     "Keep 43%, risk 77% (picked on Jun-Sep)": len(tr_43), "Merged robot, Kelly risk": len(tr_m)}
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    for k, v in out["lines"].items():
        log(f"{k:<42} $1,000 -> ${v[-1]:,}   (on 21 Sep: ${v[int(np.searchsorted(out['times'], out['thin_until']))]:,})")
    log(f"saved {path}")


if __name__ == "__main__":
    if "plot" in sys.argv:
        plot()
    elif "check" in sys.argv:
        check()
    elif "export" in sys.argv:
        export()
    else:
        main()
