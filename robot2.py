#!/usr/bin/env python3
"""
Robot 2, all parts connected in one robot (docs/machine_math.tex). The backtest and the live
practice bot both run this class, so what is tested is what runs.

Every minute
  1. price numbers U, D, R and the cost of a trade
  2. every buy%/sell% setting (0.1% steps) trades its own $1,000 account, never reset
  3. the chosen line's best setting (smoothed landscape) is offered to the 1,440 timing machines
  4. the robot takes the setting of the safest timing (middle of the biggest high-money group)
     and buys or sells, putting in the Kelly share of its money
Every hour
  5. the watcher checks for a trajectory change; a finished trajectory goes into the library
  6. the 100 lines update their memory: line p keeps p of the old data at each change, and the
     3 most similar past trajectories get extra weight w that fades as the new trajectory grows
  7. each line picks its best setting; each pick is judged 5 minutes ... 14 days later
  8. the robot follows the middle of the biggest group of lines with above-average accuracy

At minute t the robot only uses prices from before t. A decision fills at the next minute.

    python3 robot2.py            # run from 25 Jun with $1,000 and no data -> data/robot2_run.npz
    python3 robot2.py check      # structural checks
"""
import math
import sys
import time
from collections import deque

import numpy as np

from engine import (AT_LOW, BORROW, DELTAS, FEE, HALF_GAP, K_WOBBLE, MIN_HOURS, NEAR_HIGH, STEP, TIE,
                    WINDOW, Book, decimals, safest, smoother)

KEEP = np.arange(1, 101) / 100.0
HORIZONS = [5, 15, 30, 60, 120, 240, 480, 720, 1440, 2880, 4320, 7200, 10080, 20160]   # minutes
SNAP_HOURS = 72
LN1000 = math.log(1000.0)


class Robot2:
    def __init__(self, eta=14.0, risk="kelly", borrow=True, buy_max=30.0, sell_max=50.0,
                 adapt_interval=True, fixed_interval=1, judge=None):
        # adapt_interval / fixed_interval / judge exist to switch parts off in tests
        self.eta, self.risk, self.borrow = float(eta), risk, borrow
        self.adapt_interval, self.fixed_interval = adapt_interval, int(fixed_interval)
        self.judge = list(HORIZONS if judge is None else judge)
        self.buy = np.round(np.arange(STEP, buy_max + 1e-9, STEP), 1)
        self.sell = np.round(np.arange(STEP, sell_max + 1e-9, STEP), 1)
        self.nb, self.ns = len(self.buy), len(self.sell)
        self.N = self.nb * self.ns
        self.B = np.tile(self.buy, self.ns)
        self.S = np.repeat(self.sell, self.nb)
        self.Ks = smoother(self.ns).astype(np.float32)
        self.KbT = np.ascontiguousarray(smoother(self.nb).astype(np.float32).T)

        cap = 1 << 16
        self.ts = np.zeros(cap, np.int64)
        self.hi, self.lo, self.cl = np.zeros(cap), np.zeros(cap), np.zeros(cap)
        self.U, self.D, self.R = (np.full(cap, np.nan) for _ in range(3))
        self.kap = np.full(cap, FEE + HALF_GAP)
        self.dec_seen = [-10 ** 9] * 10
        self.n = 0
        self.book = Book(self.B, self.S)                 # one account per setting, never reset

        # hours, watcher, library
        self.cur_hour = None
        self.hk, self.hc, self.r = [], [], []
        self.lnv_last = np.full(self.N, LN1000)          # ln value of every setting at the last hour
        self.snap = {}                                   # hour -> ln values (recent hours only)
        self.start_lnv = np.full(self.N, LN1000)
        self.start = self.i = 0
        self.W = self.Sp = self.Sm = 0.0
        self.zW = self.zP = self.zM = 0
        self.library = []
        self.borrowed, self.w, self.bsum = [], 0.0, None

        # the 100 lines
        self.sig = np.zeros((len(KEEP), self.N))         # weighted ln growth per line and setting
        self.line_picks = []                             # per hour: setting index picked by each line
        self.queue = {H: deque() for H in self.judge}    # picks waiting to be judged
        self.pos, self.nz = np.zeros(len(KEEP)), np.zeros(len(KEEP))
        self.win, self.loss = np.zeros(len(KEEP)), np.zeros(len(KEEP))
        self.line = len(KEEP) - 1                        # followed line (index); 100% until accuracy exists
        self.M = np.ones(self.N, np.float32)             # landscape = M x current account values
        self.mdirty = True
        self.SA = self.SB = None
        self.pick = None

        # the 1,440 timing machines
        nd = len(DELTAS)
        self.m_cash, self.m_coins = np.full(nd, 1000.0), np.zeros(nd)
        self.m_b, self.m_s = np.full(nd, np.nan), np.full(nd, np.nan)
        self.m_pb = self.m_ps = None
        self.F = np.full(nd, 1000.0)
        self.interval = self.fixed_interval

        # the robot's own account
        self.cash, self.coins, self.pending, self.f_next = 1000.0, 0.0, None, 1.0
        self.setting = None
        self.trades = []                                 # (minute ts, action, price, value, setting, interval, f)
        self.fills = []                                  # (buy fill index, sell fill index or -1, f)
        self.rec = []

    # ------------------------------------------------------------------------------ minutes
    def step(self, ts_min, high, low, close):
        k = self.n
        if k == len(self.ts):
            for name in ("ts", "hi", "lo", "cl", "U", "D", "R", "kap"):
                old = getattr(self, name)
                new = np.full(2 * len(old), np.nan) if old.dtype == np.float64 else np.zeros(2 * len(old), old.dtype)
                new[:len(old)] = old
                setattr(self, name, new)
        self.ts[k], self.hi[k], self.lo[k], self.cl[k] = ts_min, high, low, close
        self.n = k + 1
        if k >= WINDOW:
            U = (close / self.lo[k - WINDOW + 1:k + 1].min() - 1) * 100
            D = (1 - close / self.hi[k - WINDOW + 1:k + 1].max()) * 100
            R = (close / self.cl[k - WINDOW] - 1) * 100
        else:
            U = D = R = math.nan
        self.U[k], self.D[k], self.R[k] = U, D, R
        for d in range(max(decimals(close), decimals(high), decimals(low)) + 1):
            self.dec_seen[d] = k
        dec = max(d for d in range(10) if self.dec_seen[d] > k - 1440)
        kap = FEE + max(HALF_GAP, 0.5 * 10.0 ** -dec / close)
        self.kap[k] = kap

        hour = ts_min // 60
        if self.cur_hour is not None and hour != self.cur_hour:
            self._hour(k)
        self.cur_hour = hour

        self.book.minute(close, U, D, R, kap)
        self._judge(k)
        kr = k - WINDOW
        self._machines(kr, close, U, D, R, kap)
        action = self._robot(k, close, U, D, R, kap)
        self.pick = self._pick(close, kap)
        if kr >= 0 and kr % 60 == 0:
            self.rec.append((int(ts_min), self.value(close), self.interval,
                             self.setting[0] if self.setting else math.nan,
                             self.setting[1] if self.setting else math.nan,
                             self.line + 1, self.w, len(self.library), float(self.coins > 0)))
        return action

    def value(self, c=None):
        c = self.cl[self.n - 1] if c is None else c
        return self.cash + self.coins * c * (1 - self.kap[self.n - 1])

    def _setting_value(self, th, t):
        bk = self.book
        return bk.coins[th] * self.cl[t] * (1 - self.kap[t]) if bk.hold[th] else bk.cash[th]

    def _top(self, S):
        f = int(S.argmax())
        top = S.flat[f]
        if top <= 1000.0 * (1 + 1e-6):
            return -1
        tied = S >= top * (1 - TIE)
        if np.count_nonzero(tied) > 1:
            rows, cols = np.nonzero(tied)
            m = int(((rows - rows.mean()) ** 2 + (cols - cols.mean()) ** 2).argmin())
            return int(rows[m]) * self.nb + int(cols[m])
        return f

    def _pick(self, c, kap):
        """Best setting of the followed line, now: smoothed  M x (each setting's account value)."""
        bk = self.book
        if bk.dirty or self.mdirty:
            A = (np.where(bk.hold, 0.0, bk.cash) * self.M).astype(np.float32)
            Bm = (np.where(bk.hold, bk.coins, 0.0) * self.M).astype(np.float32)
            self.SA = self.Ks @ A.reshape(self.ns, self.nb) @ self.KbT
            self.SB = self.Ks @ Bm.reshape(self.ns, self.nb) @ self.KbT
            bk.dirty = self.mdirty = False
        th = self._top(self.SA + np.float32(c * (1 - kap)) * self.SB)
        return None if th < 0 else (float(self.B[th]), float(self.S[th]))

    def _judge(self, k):
        """Picks whose waiting time ends now: did their setting make money?"""
        for H in self.judge:
            qd = self.queue[H]
            while qd and qd[0][0] <= k:
                _, q, th, v0 = qd.popleft()
                y = math.log(self._setting_value(th, k) / v0)
                if abs(y) > 1e-12:
                    self.nz[q] += 1
                    if y > 0:
                        self.pos[q] += 1
                        self.win[q] += math.expm1(y)
                    else:
                        self.loss[q] += -math.expm1(y)

    def kelly(self, q):
        if self.nz[q] == 0:
            return 0.01
        a, neg = self.pos[q] / self.nz[q], self.nz[q] - self.pos[q]
        if self.pos[q] == 0:
            return 0.01
        if neg == 0:
            return float(min(1.0, max(0.01, a)))
        R = (self.win[q] / self.pos[q]) / (self.loss[q] / neg)
        return float(min(1.0, max(0.01, a - (1 - a) / R)))

    def _machines(self, kr, c, U, D, R, kap):
        if self.m_pb is not None:
            m = self.m_pb
            self.m_coins[m] = self.m_cash[m] / (c * (1 + kap))
            self.m_cash[m] = 0.0
            self.m_pb = None
        if self.m_ps is not None:
            m = self.m_ps
            self.m_cash[m] = self.m_coins[m] * c * (1 - kap)
            self.m_coins[m] = 0.0
            self.m_ps = None
        if kr > 0:
            upd = (kr % DELTAS) == 0
            if self.pick is None:
                self.m_b[upd] = self.m_s[upd] = np.nan
            else:
                self.m_b[upd], self.m_s[upd] = self.pick
        hold = self.m_coins > 0
        if U <= AT_LOW:
            m = ~hold & (self.m_b <= -R)
            if m.any():
                self.m_pb = m
        if D <= NEAR_HIGH:
            m = hold & (self.m_s <= U)
            if m.any():
                self.m_ps = m
        self.F = self.m_cash + self.m_coins * (c * (1 - kap))

    def _robot(self, k, c, U, D, R, kap):
        if self.pending == "BUY":
            put = self.f_next * self.cash
            self.coins += put / (c * (1 + kap))
            self.cash -= put
            self.fills.append([k, -1, self.f_next])
        elif self.pending == "SELL":
            self.cash += self.coins * c * (1 - kap)
            self.coins = 0.0
            self.fills[-1][1] = k
        if self.pending:
            self.trades.append((int(self.ts[k]), self.pending, c, self.value(c), self.setting, self.interval,
                                self.f_next if self.pending == "BUY" else None))
            self.pending = None
        if k < WINDOW:
            return None
        self.interval = safest(self.F) if self.adapt_interval else self.fixed_interval
        b, s = self.m_b[self.interval - 1], self.m_s[self.interval - 1]
        self.setting = None if b != b else (float(b), float(s))
        holding = self.coins > 0
        if self.setting is None:
            pass
        elif not holding and U <= AT_LOW and R <= -b:
            self.pending = "BUY"
            self.f_next = self.kelly(self.line) if self.risk == "kelly" else float(self.risk)
        elif holding and D <= NEAR_HIGH and U >= s:
            self.pending = "SELL"
        return self.pending

    # ------------------------------------------------------------------------------ hours
    def _hour(self, k):
        """First minute of a new hour, before that minute is processed. Uses prices up to k-1."""
        j = len(self.hk)
        self.hk.append(k)
        self.hc.append(self.cl[k - 1])
        lnv = np.log(self.book.value(self.cl[k - 1], self.kap[k - 1]))
        self.sig += lnv - self.lnv_last
        self.lnv_last = lnv
        self.snap[j] = lnv.copy()
        for old in [h for h in self.snap if h < j - SNAP_HOURS]:
            del self.snap[old]
        if len(self.hc) >= 2:
            self.r.append(100.0 * math.log(self.hc[-1] / self.hc[-2]))
            while self.i <= len(self.r) - 1:
                ns = self._watch(self.i)
                if ns is None:
                    self.i += 1
                else:
                    self._change(ns)
        self._refresh_borrow()
        self._lines(j, k)

    def _watch(self, i):
        n = i - self.start
        if n < MIN_HOURS:
            return None
        past = np.array(self.r[self.start:i])
        mu, sd = past.mean(), past.std(ddof=1)
        z = (self.r[i] - mu) / sd if sd > 0 else 0.0
        self.W = max(0.0, self.W + z * z - 1 - K_WOBBLE)
        self.Sp = max(0.0, self.Sp + z - K_WOBBLE)
        self.Sm = max(0.0, self.Sm - z - K_WOBBLE)
        if self.W == 0:
            self.zW = i + 1
        if self.Sp == 0:
            self.zP = i + 1
        if self.Sm == 0:
            self.zM = i + 1
        hits = [zp for zp, v in ((self.zW, self.W), (self.zP, self.Sp), (self.zM, self.Sm)) if v > self.eta]
        return max(self.start + MIN_HOURS, min(hits)) if hits else None

    def _snap_at(self, h):
        if h in self.snap:
            return self.snap[h]
        oldest = min(self.snap)                          # should not happen: changes start within hours
        print(f"[warn] hour {h} is older than the kept snapshots; using hour {oldest}", flush=True)
        return self.snap[oldest]

    def _change(self, ns):
        """Trajectory [start, ns) has ended. Save it; the 100 lines keep p of the older data."""
        rr = np.array(self.r[self.start:ns])
        lnv_ns = self._snap_at(ns)
        self.library.append({"a": self.start, "b": ns, "hours": ns - self.start, "detected": len(self.r),
                             "mu": float(rr.mean()), "sd": float(rr.std(ddof=1)),
                             "lnV": (lnv_ns - self.start_lnv).astype(np.float32)})
        G = self.lnv_last - lnv_ns                       # the new trajectory's growth so far
        self.sig = KEEP[:, None] * (self.sig - G) + G
        self.start = self.i = ns
        self.W = self.Sp = self.Sm = 0.0
        self.zW = self.zP = self.zM = ns
        self.start_lnv = lnv_ns.copy()

    def _refresh_borrow(self):
        lib = self.library
        if not self.borrow or not lib:
            return
        n_new = len(self.r) - self.start
        if n_new < MIN_HOURS or len(lib) <= BORROW:
            chosen = list(range(len(lib)))
        else:
            rr = np.array(self.r[self.start:])
            mu, sd = rr.mean(), rr.std(ddof=1)
            m, s = mu / sd, math.log(sd)
            lm = np.array([t["mu"] / t["sd"] for t in lib])
            ls = np.array([math.log(t["sd"]) for t in lib])
            ln = np.array([t["hours"] for t in lib], float)
            dm = np.abs(m - lm) / np.sqrt(lm.var() + 1 / n_new + 1 / ln)
            ds = np.abs(s - ls) / np.sqrt(ls.var() + 0.5 / n_new + 0.5 / ln)
            chosen = sorted(np.argsort(dm + ds, kind="stable")[:BORROW].tolist())
        if chosen != self.borrowed or self.bsum is None:
            self.bsum = np.sum([lib[q]["lnV"].astype(np.float64) for q in chosen], axis=0)
            self.borrowed = chosen
        self.w = max(0.0, 1.0 - n_new / sum(lib[q]["hours"] for q in chosen))

    def _lines(self, j, k):
        """Every line picks a setting; picks are queued to be judged; the robot chooses its line."""
        base = self.sig if self.w == 0 else self.sig + self.w * self.bsum
        L = (1000.0 * np.exp(base)).astype(np.float32).reshape(len(KEEP), self.ns, self.nb)
        Sm = np.matmul(np.matmul(self.Ks, L), self.KbT)
        picks = np.array([self._top(Sm[q]) for q in range(len(KEEP))], np.int32)
        self.line_picks.append(picks)
        t0 = k - 1
        for q in np.flatnonzero(picks >= 0):
            th = int(picks[q])
            v0 = self._setting_value(th, t0)
            for H in self.judge:
                self.queue[H].append((t0 + H, int(q), th, v0))
        if self.nz.any():
            a = np.where(self.nz > 0, self.pos / np.maximum(self.nz, 1), -1.0)
            self.line = safest(a) - 1
        extra = 0.0 if self.w == 0 else self.w * self.bsum
        self.M = np.exp(LN1000 + self.sig[self.line] + extra - self.lnv_last).astype(np.float32)
        self.mdirty = True
        self.pick = self._pick(self.cl[k - 1], self.kap[k - 1])


def feed(robot, df, log=None, every=20000):
    ts = df["time"].values.astype("datetime64[m]").astype(np.int64)
    hi, lo, cl = df["high"].values.astype(float), df["low"].values.astype(float), df["close"].values.astype(float)
    t0 = time.time()
    for q in range(len(ts)):
        robot.step(int(ts[q]), hi[q], lo[q], cl[q])
        if log and q and q % every == 0:
            log(f"  {np.datetime64(int(ts[q]), 'm')}  robot ${robot.value():,.0f}  line {robot.line + 1}%  "
                f"every {robot.interval} min  {len(robot.library) + 1} trajectories  ({time.time() - t0:.0f}s)")
    return robot


def money_at(robot, f_override, at):
    """The robot's money at minute `at` if each buy had put in f_override (None = what it used)."""
    c, kap, v = robot.cl, robot.kap, 1000.0
    for kb, ks, f in robot.fills:
        if kb > at:
            break
        f = f if f_override is None else f_override
        end = ks if (ks != -1 and ks <= at) else at
        v *= 1 - f + f * c[end] * (1 - kap[end]) / (c[kb] * (1 + kap[kb]))
    return v


def run():
    import pandas as pd
    log = lambda *a: print(*a, flush=True)
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"])
    r = feed(Robot2(), df, log)
    cut = int(np.searchsorted(r.ts[:r.n], int(np.datetime64("2026-10-01", "m").astype(np.int64)))) - 1
    thin = int(np.searchsorted(r.ts[:r.n], int(np.datetime64("2026-09-21", "m").astype(np.int64))))
    end, k0 = r.n - 1, WINDOW
    hold = lambda a, b: 1000 * r.cl[b] * (1 - r.kap[b]) / (r.cl[a] * (1 + r.kap[a]))
    log(f"\nRobot 2, all parts connected: $1,000 on {np.datetime64(int(r.ts[k0]), 'm')}, memory empty")
    log(f"{'risk':<22}{'20 Nov':>10}{'gain':>10}{'to 30 Sep':>11}{'1 Oct-20 Nov':>14}{'from 21 Sep':>13}")
    for name, f in (("Kelly (what it used)", None), ("100% per buy", 1.0), ("50% per buy", 0.5)):
        w, a, t = money_at(r, f, end), money_at(r, f, cut), money_at(r, f, thin)
        log(f"{name:<22}{f'${w:,.0f}':>10}{f'{w / 10 - 100:+.0f}%':>10}{f'${a:,.0f}':>11}"
            f"{f'${1000 * w / a:,.0f}':>14}{f'{(w / t - 1) * 100:+.0f}%':>13}")
    w, a, t = hold(k0, end), hold(k0, cut), hold(k0, thin)
    log(f"{'just holding':<22}{f'${w:,.0f}':>10}{f'{w / 10 - 100:+.0f}%':>10}{f'${a:,.0f}':>11}"
        f"{f'${hold(cut, end):,.0f}':>14}{f'{(hold(thin, end) / 1 - 1000) / 10:+.0f}%':>13}")
    log(f"\n{len(r.fills)} buys, {len(r.library) + 1} trajectories; followed line now {r.line + 1}%, "
        f"updating every {r.interval} min; Kelly share used: "
        f"{', '.join(f'{f:.0%}' for _, _, f in r.fills[:12])}{' ...' if len(r.fills) > 12 else ''}")
    rec = np.array(r.rec, float)
    np.savez_compressed("data/robot2_run.npz", rec=rec, fills=np.array(r.fills, float), ts=r.ts[:r.n],
                        cl=r.cl[:r.n], kap=r.kap[:r.n], line_picks=np.array(r.line_picks))
    log("saved data/robot2_run.npz")


def check():
    """Structural checks on the first four weeks (and a restart test)."""
    import pickle
    import pandas as pd
    df = pd.read_csv("data/PEARL-USDT_min1.csv", parse_dates=["time"]).iloc[:40000]
    ok_all = True

    def report(name, ok, detail):
        nonlocal ok_all
        ok_all &= bool(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)

    # 1. with the library off, every line picks exactly what the tested 100-lines program picked
    r0 = feed(Robot2(borrow=False), df)
    z = np.load("data/merge_build.npz")
    mine = np.array(r0.line_picks)
    theirs = z["pick"][:len(mine)]
    report("1. lines = 100-lines program", np.array_equal(mine, theirs),
           f"{len(mine)} hours x 100 lines, {int((mine == theirs).sum()):,} of {mine.size:,} picks identical")

    # 2. accuracy counted live equals accuracy rebuilt afterwards from the same picks
    from merge_lines import HORIZONS as MH, load_build, outcomes
    d = load_build(len(pd.read_csv("data/PEARL-USDT_min1.csv")))
    acc = outcomes(d)
    T = r0.n - 1
    pos = np.zeros(100)
    nz = np.zeros(100)
    for name, _ in MH:
        for q in range(100):
            st = acc[name][q]
            c = int(np.searchsorted(st["t"], T, side="right"))
            if c:
                pos[q] += st["pos"][c - 1]
                nz[q] += st["nz"][c - 1]
    report("2. accuracy", np.array_equal(pos, r0.pos) and np.array_equal(nz, r0.nz),
           f"{int(nz.sum()):,} judged picks; live counts equal the counts rebuilt afterwards")

    # 3. the per-minute pick equals smoothing the followed line's landscape directly
    r1 = Robot2()
    ts = df["time"].values.astype("datetime64[m]").astype(np.int64)
    hi, lo, cl = df.high.values.astype(float), df.low.values.astype(float), df.close.values.astype(float)
    bad = n = 0
    rng = np.random.default_rng(5)
    probe = set(rng.integers(3000, len(df), 40).tolist())
    for q in range(len(df)):
        r1.step(int(ts[q]), hi[q], lo[q], cl[q])
        if q in probe:
            k = r1.n - 1
            extra = 0.0 if r1.w == 0 else r1.w * r1.bsum
            v = r1.book.value(r1.cl[k], r1.kap[k])
            L = (1000.0 * np.exp(r1.sig[r1.line] + extra + np.log(v) - r1.lnv_last)).astype(np.float32)
            th = r1._top(r1.Ks @ L.reshape(r1.ns, r1.nb) @ r1.KbT)
            direct = None if th < 0 else (float(r1.B[th]), float(r1.S[th]))
            bad += direct != r1.pick
            n += 1
    report("3. per-minute pick", bad == 0, f"{n - bad}/{n} random minutes identical to a direct calculation")

    # 4. no future: change every price after a cut; nothing before it may change
    cut = 25000
    alt = df.copy()
    f = np.exp(np.cumsum(np.random.default_rng(9).normal(0, 0.004, len(df) - cut)))
    for col in ("high", "low", "close"):
        alt.loc[alt.index[cut:], col] = df[col].values[cut:] * f * 1.3
    r2 = feed(Robot2(), alt)
    tc = int(ts[cut])
    same = ([t for t in r1.trades if t[0] < tc] == [t for t in r2.trades if t[0] < tc]
            and [x for x in r1.rec if x[0] < tc] == [x for x in r2.rec if x[0] < tc])
    report("4. no future", same, f"{len([t for t in r1.trades if t[0] < tc])} trades and every hourly record "
                                 f"before the cut are identical")

    # 5. restart: stop half way, save, load, continue
    r3 = feed(Robot2(), df.iloc[:20000])
    r3 = pickle.loads(pickle.dumps(r3))
    feed(r3, df.iloc[20000:])
    report("5. restart", r3.trades == r1.trades and abs(r3.value() - r1.value()) < 1e-9,
           f"${r3.value():,.2f} vs ${r1.value():,.2f}")
    print("\nall checks passed" if ok_all else "\nSOME CHECKS FAILED", flush=True)


if __name__ == "__main__":
    if "check" in sys.argv:
        check()
    else:
        run()
