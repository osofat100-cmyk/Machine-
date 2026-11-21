"""
Spike robot: zigzag spikes, the odds table, a fast simulator for the search, and the live robot.
See spikes/PLAN.md.
"""
import numpy as np
from numba import njit

COST = 0.007            # per side: 0.2% fee + 0.5% half gap (PEARL's price step is far below 0.5%)
STEP = 0.001            # odds table resolution: 0.1% of size
TABLE = 5000            # sizes 0% .. 500%


@njit(cache=True)
def zigzag(close, theta):
    """Sizes of all finished up-spikes and down-spikes (as fractions)."""
    ups, downs = [], []
    up = True
    lo = hi = close[0]
    started = False
    for c in close:
        if not started:
            if c >= lo * (1 + theta):
                up, hi, started = True, c, True
            elif c <= hi * (1 - theta):
                up, lo, started = False, c, True
            lo, hi = min(lo, c), max(hi, c)
            continue
        if up:
            if c > hi:
                hi = c
            elif c <= hi * (1 - theta):
                ups.append(hi / lo - 1)
                up, lo = False, c
        else:
            if c < lo:
                lo = c
            elif c >= lo * (1 + theta):
                downs.append(1 - lo / hi)
                up, hi = True, c
    return np.array(ups), np.array(downs)


def odds(sizes, x):
    """odds[i] = chance a spike that has reached size i*STEP reaches (i*STEP + x)."""
    grid = np.arange(TABLE + 1) * STEP
    s = np.sort(sizes)
    at_least = len(s) - np.searchsorted(s, grid - 1e-12, side="left")
    k = int(round(x / STEP))
    further = np.concatenate([at_least[k:], np.zeros(k, dtype=at_least.dtype)])
    with np.errstate(divide="ignore", invalid="ignore"):
        o = np.where(at_least > 0, further / np.maximum(at_least, 1), 0.0)
    return o


def tables(close, theta, x):
    ups, downs = zigzag(np.asarray(close, dtype=np.float64), theta)
    return odds(ups, x), odds(downs, x), ups, downs


@njit(cache=True)
def _look(table, size):
    i = int(size / STEP)
    if i < 0:
        i = 0
    if i >= table.shape[0]:
        i = table.shape[0] - 1
    return table[i]


@njit(cache=True)
def simulate(close, theta, up_odds, down_odds, p_buy, p_sell, stop):
    """$1,000 in USDT. Decision on minute t's close fills at minute t+1's close. Returns (end value, trades)."""
    cash, coins = 1000.0, 0.0
    entry = 0.0
    pending = 0                     # +1 buy, -1 sell, sent with the next minute
    up = True
    lo = hi = close[0]
    started = False
    trades = 0
    for t in range(close.shape[0]):
        c = close[t]
        if pending == 1 and cash > 0:
            coins = cash / (c * (1 + COST))
            cash = 0.0
            entry = c
            trades += 1
        elif pending == -1 and coins > 0:
            cash = coins * c * (1 - COST)
            coins = 0.0
            trades += 1
        pending = 0
        # spike state, updated with this minute
        if not started:
            if c >= lo * (1 + theta):
                up, hi, started = True, c, True
            elif c <= hi * (1 - theta):
                up, lo, started = False, c, True
            lo, hi = min(lo, c), max(hi, c)
        elif up:
            if c > hi:
                hi = c
            elif c <= hi * (1 - theta):
                up, lo = False, c
        else:
            if c < lo:
                lo = c
            elif c >= lo * (1 + theta):
                up, hi = True, c
        if not started:
            continue
        # decisions
        if coins > 0:
            if stop > 0 and c <= entry * (1 - stop):
                pending = -1
            elif up and _look(up_odds, c / lo - 1) < p_sell:
                pending = -1
        elif cash > 0:
            if not up and _look(down_odds, 1 - c / hi) < p_buy:
                pending = 1
    value = cash + coins * close[-1] * (1 - COST)
    return value, trades


class Robot:
    """The live robot: gets one minute at a time, returns "BUY", "SELL" or None. Same rules as simulate()."""

    def __init__(self, theta, up_odds, down_odds, p_buy, p_sell, stop):
        self.theta, self.up_odds, self.down_odds = theta, up_odds, down_odds
        self.p_buy, self.p_sell, self.stop = p_buy, p_sell, stop
        self.up, self.lo, self.hi, self.started = True, None, None, False
        self.holding, self.entry = False, 0.0

    def filled(self, action, price):
        self.holding = action == "BUY"
        if self.holding:
            self.entry = price

    def step(self, c):
        th = self.theta
        if self.lo is None:
            self.lo = self.hi = c
        if not self.started:
            if c >= self.lo * (1 + th):
                self.up, self.hi, self.started = True, c, True
            elif c <= self.hi * (1 - th):
                self.up, self.lo, self.started = False, c, True
            self.lo, self.hi = min(self.lo, c), max(self.hi, c)
        elif self.up:
            if c > self.hi:
                self.hi = c
            elif c <= self.hi * (1 - th):
                self.up, self.lo = False, c
        else:
            if c < self.lo:
                self.lo = c
            elif c >= self.lo * (1 + th):
                self.up, self.hi = True, c
        if not self.started:
            return None
        if self.holding:
            if self.stop > 0 and c <= self.entry * (1 - self.stop):
                return "SELL"
            if self.up and _look(self.up_odds, c / self.lo - 1) < self.p_sell:
                return "SELL"
        elif not self.up and _look(self.down_odds, 1 - c / self.hi) < self.p_buy:
            return "BUY"
        return None
