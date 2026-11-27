"""
The fast account simulator (PLAN.md section 7). day_server.py implements the same rules separately in plain Python;
the sealed test checks that both give the same dollars to the cent.

    run(O, C, g, W, start)  ->  values[t], cash_end, shares_end, trades, costs
O, C: adjusted opens / closes (T x 13); g: cash growth per day (T); W: target weights (T x 13), a NaN row means
"no new target that day" (a row of zeros means all cash). The account starts with $1,000 cash at the open of day
`start`; days before `start` are ignored and their value is NaN.
"""
import numpy as np
from numba import njit

COST = 0.0005


@njit(cache=True)
def rebalance(cash, sh, o, w, cost):
    n = sh.shape[0]
    V = cash
    for i in range(n):
        V += sh[i] * o[i]
    trades = 0
    paid = 0.0
    for i in range(n):                                   # sell what is above target
        target = w[i] * V
        have = sh[i] * o[i]
        if have > target + 1e-9:
            q = sh[i] - target / o[i]
            cash += q * o[i] * (1.0 - cost)
            paid += q * o[i] * cost
            sh[i] -= q
            trades += 1
    need_total = 0.0
    for i in range(n):
        need = w[i] * V - sh[i] * o[i]
        if need > 1e-9:
            need_total += need * (1.0 + cost)
    if need_total > 0.0:
        scale = min(1.0, cash / need_total)
        for i in range(n):                               # buy what is below target
            need = w[i] * V - sh[i] * o[i]
            if need > 1e-9:
                spend = need * scale
                sh[i] += spend / o[i]
                cash -= spend * (1.0 + cost)
                paid += spend * cost
                trades += 1
    return cash, trades, paid


@njit(cache=True)
def run(O, C, g, W, start, cost=COST):
    T, n = O.shape
    values = np.full(T, np.nan)
    cash = 1000.0
    sh = np.zeros(n)
    trades = 0
    paid = 0.0
    for t in range(start, T):
        if t > start:
            cash *= g[t]
        if not np.isnan(W[t, 0]):
            cash, k, p = rebalance(cash, sh, O[t], W[t], cost)
            trades += k
            paid += p
        v = cash
        for i in range(n):
            v += sh[i] * C[t, i]
        values[t] = v
    return values, cash, sh, trades, paid


def weights_from_choices(T, n, choice_days, choices):
    """choice_days[k]: the day whose OPEN the k-th target fills at; choices[k]: symbol index, or -1 for cash.
    Consecutive identical choices are sent only once."""
    W = np.full((T, n), np.nan)
    last = None
    for d, c in zip(choice_days, choices):
        if d >= T or c == last:
            continue
        W[d] = 0.0
        if c >= 0:
            W[d, c] = 1.0
        last = c
    return W
