"""
Inputs, targets and the purge rule (PLAN.md sections 2-4).

Everything works on plain arrays over trading days t = 0..T-1:
  O[t, i], C[t, i], V[t, i]  adjusted open, adjusted close, volume of symbol i
  rate[t]                     cash rate (bond-equivalent annual %)
Inputs on day t use only rows <= t (rolling windows look back). Targets on day t look forward and may only be used
for training when the purge rule allows.
"""
import numpy as np
import pandas as pd

SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
SPY = 0
HORIZONS = (1, 5, 21)
GAP = 5
SYM_FEATURES = ["r1", "r5", "r21", "r63", "r252", "vol21", "vol63", "d50", "d200", "volchg", "rank21", "rank63"]
MKT_FEATURES = ["spy_r21", "spy_r63", "spy_d200", "spy_vol21", "breadth", "dispersion"]


def load(path):
    df = pd.read_csv(path)
    return arrays(df)


def arrays(df):
    """CSV/DataFrame (date, rate, SYM_open, SYM_close, SYM_volume ...) -> dict of numpy arrays."""
    return {"dates": df["date"].astype(str).to_numpy(),
            "rate": df["rate"].to_numpy(float),
            "O": np.column_stack([df[f"{s}_open"].to_numpy(float) for s in SYMBOLS]),
            "C": np.column_stack([df[f"{s}_close"].to_numpy(float) for s in SYMBOLS]),
            "V": np.column_stack([df[f"{s}_volume"].to_numpy(float) for s in SYMBOLS])}


def join(a, b):
    """Append panel b after panel a (used as test days are handed out)."""
    return {k: np.concatenate([a[k], b[k]]) for k in a}


def cash_growth(rate):
    """g[t] = growth of cash on day t, using the previous day's rate (g[0] = 1)."""
    g = np.ones(len(rate))
    g[1:] = (1.0 + rate[:-1] / 100.0) ** (1.0 / 252.0)
    return g


def inputs(p):
    """-> (S, M): S[t, i, f] per-symbol inputs (SYM_FEATURES), M[t, f] market inputs (MKT_FEATURES). NaN where the
    look-back is not yet full."""
    C = pd.DataFrame(p["C"])
    V = pd.DataFrame(p["V"])
    ret = C.pct_change()
    cols = {}
    for k in (1, 5, 21, 63, 252):
        cols[f"r{k}"] = C / C.shift(k) - 1
    cols["vol21"] = ret.rolling(21).std()
    cols["vol63"] = ret.rolling(63).std()
    cols["d50"] = C / C.rolling(50).mean() - 1
    cols["d200"] = C / C.rolling(200).mean() - 1
    cols["volchg"] = np.log(V.rolling(5).mean() / V.rolling(63).mean())
    n = C.shape[1]
    cols["rank21"] = (cols["r21"].rank(axis=1) - 1) / (n - 1)
    cols["rank63"] = (cols["r63"].rank(axis=1) - 1) / (n - 1)
    for name in ("rank21", "rank63"):
        cols[name][cols[name.replace("rank", "r")].isna().any(axis=1)] = np.nan
    S = np.stack([cols[f].to_numpy() for f in SYM_FEATURES], axis=2)
    M = np.column_stack([cols["r21"][SPY], cols["r63"][SPY], cols["d200"][SPY], cols["vol21"][SPY],
                         (cols["d200"] > 0).mean(axis=1).where(cols["d200"].notna().all(axis=1)),
                         cols["r21"].std(axis=1, ddof=0).where(cols["r21"].notna().all(axis=1))])
    return S, M


def selection_X(S, M, t):
    """Rows for day t (or an array of days): one row per symbol = its inputs + market inputs."""
    t = np.atleast_1d(t)
    n = S.shape[1]
    sym = S[t].reshape(len(t) * n, S.shape[2])
    mkt = np.repeat(M[t], n, axis=0)
    return np.hstack([sym, mkt])


def timing_X(S, M, t):
    """Rows for day t (or an array of days): SPY's inputs + market inputs."""
    t = np.atleast_1d(t)
    return np.hstack([S[t, SPY, :], M[t]])


def targets(p, h):
    """-> (sel[t, i], tim[t]): selection and timing targets for decisions after day t's close, filled at t+1's open,
    held h days. NaN when the window runs past the data."""
    O, g = p["O"], cash_growth(p["rate"])
    T = len(O)
    R = np.full(O.shape, np.nan)
    bill = np.full(T, np.nan)
    logg = np.concatenate([[0.0], np.cumsum(np.log(g))])     # logg[k] = sum of log g[0..k-1]
    for t in range(T - 1 - h):
        R[t] = O[t + 1 + h] / O[t + 1] - 1
        bill[t] = np.exp(logg[t + 2 + h] - logg[t + 2]) - 1    # growth on days t+2 .. t+1+h
    sel = R - R.mean(axis=1, keepdims=True)
    tim = R[:, SPY] - bill
    return sel, tim


def train_days(tau, h, first):
    """Purge rule: training rows t with t + 1 + h <= tau - GAP (and t >= first, the first day with full inputs)."""
    last = tau - GAP - 1 - h
    return np.arange(first, last + 1) if last >= first else np.arange(0)


def first_full(S, M):
    """First day on which every input is present."""
    ok = ~np.isnan(S).any(axis=(1, 2)) & ~np.isnan(M).any(axis=1)
    return int(np.argmax(ok)) if ok.any() else None
