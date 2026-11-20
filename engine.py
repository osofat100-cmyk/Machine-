#!/usr/bin/env python3
"""
The one engine behind robot 2. The backtest, the replay test and the live bot all feed
minutes into this same code, so what is tested is what runs.

Per minute (docs/machine_math.tex):
  1. the three 4-hour numbers U, D, R
  2. every buy%/sell% setting (0.1% steps) trades its own $1,000 inside the current trajectory
  3. landscape = those settings' money x the borrowed past trajectories, smoothed; top = the pick
  4. 1,440 interval machines (update every 1..1,440 min) each take the pick on their own schedule
  5. the robot uses the safest interval's current setting and trades
Per hour:
  6. the watcher checks whether the trajectory has ended; if so the trajectory goes into the
     library and the data restarts from where the change began
  7. the borrowed set (whole library for the first 12 hours, then the 3 most similar) and its
     weight w = max(0, 1 - new hours / borrowed hours) are refreshed

Nothing here reads a price later than the minute being processed. A decision made on minute k
fills at minute k+1's close and pays the cost of that minute on each side:
    cost = 0.2% fee + half the buy/sell gap, where the gap is at least 1% and at least one price tick
(until 10 Jul 2026 BigONE quoted PEARL in whole cents, a tick of about 2% of the price).
"""
import math

import numpy as np

FEE = 0.002                        # exchange fee per buy and per sell
HALF_GAP = 0.005                   # half the usual buy/sell gap
COST = FEE + HALF_GAP              # 0.7% per side when the price tick is small
AT_LOW, NEAR_HIGH = 0.23, 1.8      # "at the 4-hour low" / "near the 4-hour high", in %
WINDOW = 240                       # 4 hours of minutes
STEP = 0.1                         # settings grid step, %
SIGMA_STEPS = 10                   # smoothing: 10 steps = 1%
DELTAS = np.arange(1, 1441)        # update intervals, minutes
K_WOBBLE = 0.5                     # watcher ignores wobbles below half a usual step
MIN_HOURS = 12                     # hours before a trajectory can be measured
BORROW = 3                         # similar past trajectories borrowed
TIE = 1e-5                         # settings within $0.01 per $1,000 of the top count as tied


def smoother(n, sigma=SIGMA_STEPS):
    """Matrix that averages each point with its neighbours (bell curve).
    Past the top of the grid the landscape really is flat, so the top edge repeats.
    Below 0.1% there are no settings, so the bottom edge averages only the neighbours that exist."""
    r = int(3 * sigma)
    w = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    K = np.zeros((n, n))
    for i in range(n):
        for k, wk in zip(range(-r, r + 1), w):
            if i + k >= 0:
                K[i, min(n - 1, i + k)] += wk
    return K / K.sum(axis=1, keepdims=True)


def decimals(x):
    """How many decimal places a price uses."""
    for d in range(9):
        if abs(x * 10 ** d - round(x * 10 ** d)) < 1e-7:
            return d
    return 9


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


class Book:
    """Every setting's own $1,000 account inside one trajectory. Starts in USDC."""

    def __init__(self, B, S, at_low=AT_LOW, near_high=NEAR_HIGH):
        self.B, self.S, self.at_low, self.near_high = B, S, at_low, near_high
        n = len(B)
        self.cash = np.full(n, 1000.0)
        self.coins = np.zeros(n)
        self.hold = np.zeros(n, bool)
        self.pb = self.ps = None       # decisions waiting for the next minute's price
        self.traded = False
        self.dirty = True              # accounts changed since the landscape was last smoothed

    def minute(self, c, U, D, R, kap=COST):
        """Fill last minute's decisions at this close, then decide for this minute."""
        if self.pb is not None:
            m = self.pb
            self.coins[m] = self.cash[m] / (c * (1 + kap))
            self.cash[m] = 0.0
            self.hold[m] = True
            self.pb, self.dirty, self.traded = None, True, True
        if self.ps is not None:
            m = self.ps
            self.cash[m] = self.coins[m] * c * (1 - kap)
            self.coins[m] = 0.0
            self.hold[m] = False
            self.ps, self.dirty = None, True
        if U <= self.at_low and R <= -STEP:
            m = ~self.hold & (self.B <= -R)
            if m.any():
                self.pb = m
        if D <= self.near_high and U >= STEP:
            m = self.hold & (self.S <= U)
            if m.any():
                self.ps = m

    def value(self, c, kap=COST):
        return np.where(self.hold, self.coins * (c * (1 - kap)), self.cash)


class Engine:
    def __init__(self, eta=12.0, resets=True, adapt_interval=True, fixed_interval=1,
                 buy_max=30.0, sell_max=50.0, exit_on_none=False, similar=True, tick_cost=True,
                 window=WINDOW, at_low=AT_LOW, near_high=NEAR_HIGH, half_gap=HALF_GAP, worst_fills=False):
        # the last five exist for the robustness tests; the robot itself uses the defaults
        self.window, self.at_low, self.near_high = int(window), at_low, near_high
        self.half_gap, self.worst_fills = half_gap, worst_fills
        self.eta, self.resets = float(eta), resets
        self.adapt_interval, self.fixed_interval = adapt_interval, int(fixed_interval)
        self.exit_on_none, self.similar, self.tick_cost = exit_on_none, similar, tick_cost
        self.buy = np.round(np.arange(STEP, buy_max + 1e-9, STEP), 1)
        self.sell = np.round(np.arange(STEP, sell_max + 1e-9, STEP), 1)
        self.nb, self.ns = len(self.buy), len(self.sell)
        self.B = np.tile(self.buy, self.ns)            # setting index = sell row * nb + buy column
        self.S = np.repeat(self.sell, self.nb)
        self.Ks = smoother(self.ns).astype(np.float32)
        self.KbT = np.ascontiguousarray(smoother(self.nb).astype(np.float32).T)

        cap = 1 << 16                                   # minute history (grows as needed)
        self.ts = np.zeros(cap, np.int64)
        self.hi, self.lo, self.cl = np.zeros(cap), np.zeros(cap), np.zeros(cap)
        self.U, self.D, self.R = np.full(cap, np.nan), np.full(cap, np.nan), np.full(cap, np.nan)
        self.kap = np.full(cap, COST)                   # cost per side on each minute
        self.dec_seen = [-10 ** 9] * 10                 # minute each number of decimals was last seen
        self.n = 0

        self.book = Book(self.B, self.S, at_low, near_high)
        self.book_k = 0                                 # next minute the book has to process
        self.P = None                                   # borrowed-data factor per setting
        self.prior_dirty = True
        self.SA = self.SB = None
        self.pick = None                                # (buy %, sell %) from data up to last minute

        nd = len(DELTAS)                                # interval machines
        self.m_cash, self.m_coins = np.full(nd, 1000.0), np.zeros(nd)
        self.m_b, self.m_s = np.full(nd, np.nan), np.full(nd, np.nan)
        self.m_pb = self.m_ps = None
        self.F = np.full(nd, 1000.0)
        self.G = np.full(nd, 1000.0)
        self.F_start = np.full(nd, 1000.0)
        self.expPG = None
        self.interval = self.fixed_interval

        self.cash, self.coins, self.pending = 1000.0, 0.0, None     # the robot's own account
        self.setting = None
        self.trades = []

        self.cur_hour = None                            # hourly closes and the watcher
        self.hc, self.hk, self.Fhist, self.r = [], [], [], []
        self.start = 0                                  # current trajectory starts at return index
        self.i = 0                                      # next return the watcher has to process
        self.W = self.Sp = self.Sm = 0.0
        self.zW = self.zP = self.zM = 0
        self.snaps = {}
        self.library = []
        self.borrowed, self.w, self._sum = [], 0.0, None
        self.rec = []                                   # hourly record

    # ------------------------------------------------------------------ minutes
    def step(self, ts_min, high, low, close):
        """Feed one finished minute. Returns 'BUY', 'SELL' or None (the robot's decision)."""
        k = self.n
        if k == len(self.ts):
            for name in ("ts", "hi", "lo", "cl", "U", "D", "R", "kap"):
                old = getattr(self, name)
                new = np.full(2 * len(old), np.nan) if old.dtype == np.float64 else np.zeros(2 * len(old), old.dtype)
                new[:len(old)] = old
                setattr(self, name, new)
        self.ts[k], self.hi[k], self.lo[k], self.cl[k] = ts_min, high, low, close
        self.n = k + 1
        W = self.window
        if k >= W:
            U = (close / self.lo[k - W + 1:k + 1].min() - 1) * 100
            D = (1 - close / self.hi[k - W + 1:k + 1].max()) * 100
            R = (close / self.cl[k - W] - 1) * 100
        else:
            U = D = R = math.nan
        self.U[k], self.D[k], self.R[k] = U, D, R
        kap = FEE + self.half_gap
        if self.tick_cost:                               # the gap can't be smaller than one price tick
            for d in range(max(decimals(close), decimals(high), decimals(low)) + 1):
                self.dec_seen[d] = k
            dec = max(d for d in range(10) if self.dec_seen[d] > k - 1440)
            kap = FEE + max(self.half_gap, 0.5 * 10.0 ** -dec / close)
        self.kap[k] = kap

        hour = ts_min // 60                              # hour boundary: the previous hour is complete
        if self.cur_hour is not None and hour != self.cur_hour:
            self._hour(k)
        self.cur_hour = hour

        self.book.minute(close, U, D, R, kap)
        self.book_k = k + 1

        kr = k - W                                       # minutes since trading could start
        self._machines(kr, close, U, D, R, kap)
        action = self._robot(k, close, U, D, R, kap)
        self.pick = self._pick(close, kap)
        if kr >= 0 and kr % 60 == 0:
            self.rec.append((int(ts_min), self.value(close), self.interval,
                             self.setting[0] if self.setting else math.nan,
                             self.setting[1] if self.setting else math.nan,
                             len(self.library), self.w, self.coins > 0))
        return action

    def value(self, c=None):
        c = self.cl[self.n - 1] if c is None else c
        return self.cash + self.coins * c * (1 - self.kap[self.n - 1])

    def _pick(self, c, kap):
        bk = self.book
        if bk.dirty or self.prior_dirty:
            A = np.where(bk.hold, 0.0, bk.cash).astype(np.float32)
            Bm = np.where(bk.hold, bk.coins, 0.0).astype(np.float32)
            if self.P is not None:
                A *= self.P
                Bm *= self.P
            self.SA = self.Ks @ A.reshape(self.ns, self.nb) @ self.KbT
            self.SB = self.Ks @ Bm.reshape(self.ns, self.nb) @ self.KbT
            bk.dirty = self.prior_dirty = False
        if not bk.traded and self.P is None:
            return None
        S = self.SA + np.float32(c * (1 - kap)) * self.SB
        f = int(S.argmax())
        top = S.flat[f]
        if top <= 1000.0 * (1 + 1e-6):
            return None
        tied = S >= top * (1 - TIE)
        if np.count_nonzero(tied) > 1:                  # a flat top: take its middle, not a random corner
            rows, cols = np.nonzero(tied)
            d = (rows - rows.mean()) ** 2 + (cols - cols.mean()) ** 2
            q = int(d.argmin())
            return float(self.buy[cols[q]]), float(self.sell[rows[q]])
        return float(self.buy[f % self.nb]), float(self.sell[f // self.nb])

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
        if U <= self.at_low:
            m = ~hold & (self.m_b <= -R)
            if m.any():
                self.m_pb = m
        if D <= self.near_high:
            m = hold & (self.m_s <= U)
            if m.any():
                self.m_ps = m
        if self.exit_on_none:
            m = hold & np.isnan(self.m_b)
            if m.any():
                self.m_ps = m if self.m_ps is None else (self.m_ps | m)
        self.F = self.m_cash + self.m_coins * (c * (1 - kap))

    def _robot(self, k, c, U, D, R, kap):
        if self.pending:
            px = c
            if self.worst_fills:                         # robustness test: worst price of the fill minute
                px = self.hi[k] if self.pending == "BUY" else self.lo[k]
            if self.pending == "BUY":
                self.coins, self.cash = self.cash / (px * (1 + kap)), 0.0
            else:
                self.cash, self.coins = self.coins * px * (1 - kap), 0.0
            self.trades.append((int(self.ts[k]), self.pending, px, self.value(c), self.setting, self.interval))
            self.pending = None
        if k < self.window:
            return None
        if self.adapt_interval:
            self.interval = safest(self.G)               # G is from the minute before
        idx = self.interval - 1
        b, s = self.m_b[idx], self.m_s[idx]
        self.setting = None if b != b else (float(b), float(s))
        holding = self.coins > 0
        if self.setting is None:
            if holding and self.exit_on_none:
                self.pending = "SELL"
        elif not holding and U <= self.at_low and R <= -b:
            self.pending = "BUY"
        elif holding and D <= self.near_high and U >= s:
            self.pending = "SELL"
        G = self.F / self.F_start
        self.G = G if self.expPG is None else G * self.expPG
        return self.pending

    # ------------------------------------------------------------------ hours
    def _hour(self, k):
        """Called on the first minute of a new hour, before that minute is processed."""
        self.hc.append(self.cl[k - 1])
        self.hk.append(k)
        self.Fhist.append(self.F.astype(np.float32))
        if len(self.hc) < 2:
            return
        self.r.append(100.0 * math.log(self.hc[-1] / self.hc[-2]))
        if not self.resets:
            return
        j = len(self.r) - 1
        while self.i <= j:                               # normally one pass; more after a reset
            self._replay_book_to(self.hk[self.i + 1])
            new_start = self._watch(self.i)
            if new_start is None:
                self.i += 1
            else:
                self._close(new_start)
        self._refresh_prior()
        self.pick = self._pick(self.cl[k - 1], self.kap[k - 1])

    def _replay_book_to(self, k_target):
        while self.book_k < k_target:
            q = self.book_k
            self.book.minute(self.cl[q], self.U[q], self.D[q], self.R[q], self.kap[q])
            self.book_k = q + 1

    def _snap(self, idx):
        if idx not in self.snaps:
            q = self.book_k - 1
            self.snaps[idx] = self.book.value(self.cl[q], self.kap[q]).astype(np.float32)

    def _watch(self, i):
        """Process hourly return i. Returns the new trajectory's start if this one has ended."""
        n = i - self.start
        if n >= MIN_HOURS:
            past = np.array(self.r[self.start:i])
            mu, sd = past.mean(), past.std(ddof=1)
            z = (self.r[i] - mu) / sd if sd > 0 else 0.0
            self.W = max(0.0, self.W + z * z - 1 - K_WOBBLE)
            self.Sp = max(0.0, self.Sp + z - K_WOBBLE)
            self.Sm = max(0.0, self.Sm - z - K_WOBBLE)
            zero = False
            if self.W == 0:
                self.zW, zero = i + 1, True
            if self.Sp == 0:
                self.zP, zero = i + 1, True
            if self.Sm == 0:
                self.zM, zero = i + 1, True
            hits = [zp for zp, v in ((self.zW, self.W), (self.zP, self.Sp), (self.zM, self.Sm)) if v > self.eta]
            if hits:
                return max(self.start + MIN_HOURS, min(hits))
            if zero:
                self._snap(i + 1)
                keep = {self.zW, self.zP, self.zM, self.start + MIN_HOURS}
                for key in [q for q in self.snaps if q not in keep]:
                    del self.snaps[key]
        if i + 1 == self.start + MIN_HOURS:
            self._snap(i + 1)
        return None

    def _close(self, new_start):
        """The trajectory [start, new_start) is over: save it, restart the data at new_start."""
        a = self.start
        rr = np.array(self.r[a:new_start])
        self.library.append({
            "a": a, "b": new_start, "hours": new_start - a, "detected": len(self.r),
            "mu": float(rr.mean()), "sd": float(rr.std(ddof=1)),
            "lnV": np.log(self.snaps[new_start] / 1000.0).astype(np.float32),
            "lnG": np.log(self.Fhist[new_start] / self.Fhist[a]).astype(np.float32),
        })
        self.start = self.i = new_start
        self.W = self.Sp = self.Sm = 0.0
        self.zW = self.zP = self.zM = new_start
        self.snaps = {}
        self.book = Book(self.B, self.S, self.at_low, self.near_high)
        self.book_k = self.hk[new_start]
        self.F_start = self.Fhist[new_start].astype(np.float64)

    def _refresh_prior(self):
        lib = self.library
        n_new = len(self.r) - self.start
        if not lib:
            return
        if n_new < MIN_HOURS or len(lib) <= BORROW or not self.similar:
            chosen = list(range(len(lib)))
        else:
            rr = np.array(self.r[self.start:])
            mu, sd = rr.mean(), rr.std(ddof=1)
            m, s = mu / sd, math.log(sd)
            lm = np.array([t["mu"] / t["sd"] for t in lib])
            ls = np.array([math.log(t["sd"]) for t in lib])
            ln = np.array([t["hours"] for t in lib], float)
            # each difference is measured against how much trajectories differ from each other
            # plus how uncertain the measurement still is (direction ~ 1/n, instability ~ 1/2n)
            dm = np.abs(m - lm) / np.sqrt(lm.var() + 1 / n_new + 1 / ln)
            ds = np.abs(s - ls) / np.sqrt(ls.var() + 0.5 / n_new + 0.5 / ln)
            chosen = sorted(np.argsort(dm + ds, kind="stable")[:BORROW].tolist())
        n_b = sum(lib[q]["hours"] for q in chosen)
        w = max(0.0, 1.0 - n_new / n_b)
        if chosen != self.borrowed or w != self.w:
            if chosen != self.borrowed or self._sum is None:      # add up the borrowed data once
                lnP = lib[chosen[0]]["lnV"].astype(np.float64)
                lnG = lib[chosen[0]]["lnG"].astype(np.float64)
                for q in chosen[1:]:
                    lnP = lnP + lib[q]["lnV"]
                    lnG = lnG + lib[q]["lnG"]
                self._sum = (lnP, lnG)
            self.borrowed, self.w = chosen, w
            if w > 0:
                self.P = np.exp(w * self._sum[0]).astype(np.float32)
                self.expPG = np.exp(w * self._sum[1])
            else:
                self.P = self.expPG = None
            self.prior_dirty = True

    # ------------------------------------------------------------------ helpers
    def trajectories(self):
        """Finished trajectories plus the current one, as (start, end) return indices."""
        return [(t["a"], t["b"]) for t in self.library] + [(self.start, len(self.r))]


def feed(engine, df, log=None, every=20000):
    """Feed a DataFrame with columns time, high, low, close (one row per minute)."""
    ts = (df["time"].values.astype("datetime64[m]").astype(np.int64))
    hi, lo, cl = df["high"].values.astype(float), df["low"].values.astype(float), df["close"].values.astype(float)
    for q in range(len(ts)):
        engine.step(int(ts[q]), hi[q], lo[q], cl[q])
        if log and q and q % every == 0:
            log(f"  {np.datetime64(int(ts[q]), 'm')}  robot ${engine.value():,.0f}  "
                f"trajectories {len(engine.library) + 1}")
    return engine
