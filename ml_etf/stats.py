"""
Statistics (PLAN.md section 10): Sharpe, information ratio, R2_OS, Pesaran-Timmermann, (deflated) Sharpe,
Diebold-Mariano, stationary block bootstrap, probability of backtest overfitting (CSCV), worst drop.
"""
from itertools import combinations
from math import e, sqrt

import numpy as np
from scipy.stats import kurtosis, norm, skew

EULER = 0.5772156649015329


def sharpe(r):
    r = np.asarray(r)
    sd = r.std(ddof=1)
    return 0.0 if sd == 0 else r.mean() / sd * sqrt(252)


def max_drop(values):
    v = np.asarray(values)
    peak = np.maximum.accumulate(v)
    return float((v / peak - 1).min())


def r2_os(y, f, bench):
    """1 - sum (y - f)^2 / sum (y - bench)^2 (Campbell & Thompson)."""
    y, f, bench = map(np.asarray, (y, f, bench))
    return 1.0 - np.sum((y - f) ** 2) / np.sum((y - bench) ** 2)


def pesaran_timmermann(actual_up, forecast_up):
    """Pesaran & Timmermann (1992) direction test -> (hit rate, statistic, one-sided p-value)."""
    y = np.asarray(actual_up, bool)
    z = np.asarray(forecast_up, bool)
    n = len(y)
    p_hat = np.mean(y == z)
    py, pz = y.mean(), z.mean()
    p_star = py * pz + (1 - py) * (1 - pz)
    v_hat = p_star * (1 - p_star) / n
    v_star = ((2 * py - 1) ** 2 * pz * (1 - pz) + (2 * pz - 1) ** 2 * py * (1 - py)) / n   # original 1992 form
    if v_hat - v_star <= 0:
        return p_hat, float("nan"), float("nan")
    s = (p_hat - p_star) / sqrt(v_hat - v_star)
    return p_hat, s, 1 - norm.cdf(s)


def expected_max_sharpe(n_trials, var):
    """Expected best Sharpe of n_trials skill-free strategies (Bailey & Lopez de Prado 2014)."""
    return sqrt(var) * ((1 - EULER) * norm.ppf(1 - 1 / n_trials) + EULER * norm.ppf(1 - 1 / (n_trials * e)))


def psr(r, sr_star):
    """Probabilistic Sharpe ratio of daily returns r against threshold sr_star (both in daily units)."""
    r = np.asarray(r)
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3 = skew(r)
    g4 = kurtosis(r, fisher=False)
    den = sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return float(norm.cdf((sr - sr_star) * sqrt(T - 1) / den))


def dsr(r, n_trials):
    """Deflated Sharpe ratio with trial variance V = 1/T (PLAN.md section 10)."""
    T = len(r)
    return psr(r, expected_max_sharpe(n_trials, 1.0 / T))


def newey_west_var(d, lags):
    d = np.asarray(d) - np.mean(d)
    T = len(d)
    v = d @ d / T
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1)
        v += 2 * w * (d[k:] @ d[:-k]) / T
    return v


def diebold_mariano(e1, e2, lags):
    """Squared-error loss; positive statistic = model 2 forecasts better. -> (statistic, two-sided p-value)."""
    d = np.asarray(e1) ** 2 - np.asarray(e2) ** 2
    v = newey_west_var(d, lags)
    if v <= 0:
        return float("nan"), float("nan")
    s = d.mean() / sqrt(v / len(d))
    return float(s), float(2 * (1 - norm.cdf(abs(s))))


def stationary_bootstrap_index(T, mean_block, rng):
    """One resample of 0..T-1 by the Politis & Romano (1994) stationary bootstrap."""
    idx = np.empty(T, dtype=np.int64)
    p = 1.0 / mean_block
    i = rng.integers(T)
    for k in range(T):
        idx[k] = i
        i = rng.integers(T) if rng.random() < p else (i + 1) % T
    return idx


def bootstrap(fn, data, reps=2000, mean_block=21, seed=0):
    """95% range of fn(data[resampled rows]) -> (low, high)."""
    rng = np.random.default_rng(seed)
    T = len(data)
    vals = np.array([fn(data[stationary_bootstrap_index(T, mean_block, rng)]) for _ in range(reps)])
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def pbo(returns, blocks):
    """Probability of backtest overfitting by CSCV (Bailey, Borwein, Lopez de Prado & Zhu 2017).
    returns: T x N daily returns (one column per tried setting); blocks: label per row (e.g. year).
    -> (pbo, number of splits)"""
    labels = sorted(set(blocks))
    S = len(labels)
    rows = {b: np.where(np.asarray(blocks) == b)[0] for b in labels}
    lam = []
    for ins in combinations(range(S), S // 2):
        is_rows = np.concatenate([rows[labels[k]] for k in ins])
        oos_rows = np.concatenate([rows[labels[k]] for k in range(S) if k not in ins])
        perf_is = np.array([sharpe(returns[is_rows, j]) for j in range(returns.shape[1])])
        perf_oos = np.array([sharpe(returns[oos_rows, j]) for j in range(returns.shape[1])])
        best = int(np.argmax(perf_is))
        rank = (np.sum(perf_oos < perf_oos[best]) + 0.5 * (np.sum(perf_oos == perf_oos[best]) - 1) + 1)
        w = rank / (returns.shape[1] + 1)
        lam.append(np.log(w / (1 - w)))
    lam = np.array(lam)
    return float(np.mean(lam <= 0)), len(lam)
