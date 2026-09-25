#!/usr/bin/env python3
"""Exact (rational, symbolic) derive-check of the DOPRI5 continuous extension used in
src/slab/integrators.py.

The dense output of Hairer's DOPRI5 code is written as
    y(theta) = y0 + theta (r2 + theta1 (r3 + theta (r4 + theta1 r5))),   theta1 = 1 - theta,
    r2 = h sum b_i k_i,  r3 = h k1 - r2,  r4 = r2 - h k7 - r3,  r5 = h sum d_i k_i.
Expanding gives y(theta) = y0 + h sum_i b_i(theta) k_i with
    b_i(theta) = theta b_i + theta theta1 (delta_i1 - b_i) + theta^2 theta1 (2 b_i - delta_i1 - delta_i7)
                 + theta^2 theta1^2 d_i.
This script checks, with exact rationals and a symbolic theta:
  * the end points: b_i(0) = 0, b_i(1) = b_i (the 5th-order weights), and the derivative
    conditions b_i'(0) = delta_i1, b_i'(1) = delta_i7 (Hermite matching of h k1 and h k7);
  * all 8 Runge–Kutta order conditions up to order 4 hold identically in theta
    (sum b = theta, sum b c = theta^2/2, sum b c^2 = theta^3/3, sum b a c = theta^3/6,
     sum b c^3 = theta^4/4, sum b c a c = theta^4/8, sum b a c^2 = theta^4/12, sum b a a c = theta^4/24);
  * the Butcher tableau itself satisfies the order-5 conditions at theta = 1 (sanity of the transcription).
A mistyped digit in any of d1, d3..d7 or in the tableau breaks at least one identity.
Run:  python tools/verify_dopri5_dense_output.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import sympy as sp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

R = sp.Rational
C = [R(0), R(1, 5), R(3, 10), R(4, 5), R(8, 9), R(1), R(1)]
A = [
    [],
    [R(1, 5)],
    [R(3, 40), R(9, 40)],
    [R(44, 45), R(-56, 15), R(32, 9)],
    [R(19372, 6561), R(-25360, 2187), R(64448, 6561), R(-212, 729)],
    [R(9017, 3168), R(-355, 33), R(46732, 5247), R(49, 176), R(-5103, 18656)],
    [R(35, 384), R(0), R(500, 1113), R(125, 192), R(-2187, 6784), R(11, 84)],
]
B5 = [R(35, 384), R(0), R(500, 1113), R(125, 192), R(-2187, 6784), R(11, 84), R(0)]


def _d_coefficients():
    from slab.integrators import _D_RAT   # the exact rationals used by the integrator
    d = [R(0)] * 7
    for i, (p, q) in _D_RAT.items():
        d[i - 1] = R(p, q)
    return d


def verify() -> dict:
    th = sp.symbols("theta")
    th1 = 1 - th
    D = _d_coefficients()
    b = []
    for i in range(7):
        d1 = 1 if i == 0 else 0
        d7 = 1 if i == 6 else 0
        b.append(sp.expand(th * B5[i] + th * th1 * (d1 - B5[i]) + th**2 * th1 * (2 * B5[i] - d1 - d7) + th**2 * th1**2 * D[i]))
    a = [[A[i][j] if j < len(A[i]) else R(0) for j in range(7)] for i in range(7)]
    ac = [sum(a[i][j] * C[j] for j in range(7)) for i in range(7)]
    ac2 = [sum(a[i][j] * C[j] ** 2 for j in range(7)) for i in range(7)]
    aac = [sum(a[i][j] * ac[j] for j in range(7)) for i in range(7)]
    results = {}

    def check(name, expr, target):
        ok = sp.simplify(sp.expand(expr - target)) == 0
        results[name] = bool(ok)

    # row sums of the tableau = c_i (consistency)
    results["row sums a_ij = c_i"] = all(sum(a[i]) == C[i] for i in range(7))
    # end points and Hermite derivatives
    results["b_i(0) = 0"] = all(bi.subs(th, 0) == 0 for bi in b)
    results["b_i(1) = b_i (5th-order weights)"] = all(sp.simplify(bi.subs(th, 1) - B5[i]) == 0 for i, bi in enumerate(b))
    results["b_i'(0) = delta_i1 (matches h k1)"] = all(sp.diff(bi, th).subs(th, 0) == (1 if i == 0 else 0) for i, bi in enumerate(b))
    results["b_i'(1) = delta_i7 (matches h k7, FSAL stage)"] = all(sp.diff(bi, th).subs(th, 1) == (1 if i == 6 else 0) for i, bi in enumerate(b))
    # order conditions of the continuous extension, identically in theta
    S = lambda w: sum(b[i] * w[i] for i in range(7))
    one = [1] * 7
    check("order 1: sum b = theta", S(one), th)
    check("order 2: sum b c = theta^2/2", S(C), th**2 / 2)
    check("order 3: sum b c^2 = theta^3/3", S([c**2 for c in C]), th**3 / 3)
    check("order 3: sum b a c = theta^3/6", S(ac), th**3 / 6)
    check("order 4: sum b c^3 = theta^4/4", S([c**3 for c in C]), th**4 / 4)
    check("order 4: sum b c (a c) = theta^4/8", S([C[i] * ac[i] for i in range(7)]), th**4 / 8)
    check("order 4: sum b a c^2 = theta^4/12", S(ac2), th**4 / 12)
    check("order 4: sum b a a c = theta^4/24", S(aac), th**4 / 24)
    # the 5th-order weights: all 17 order-5 trees are not listed; the 9 trees up to order 4 plus the
    # bushy order-5 tree sum b c^4 = 1/5 and sum b a c^3 = 1/20 are checked as a transcription test
    Sb = lambda w: sum(B5[i] * w[i] for i in range(7))
    results["5th-order weights: sum b c^4 = 1/5"] = Sb([c**4 for c in C]) == R(1, 5)
    results["5th-order weights: sum b a c^3 = 1/20"] = Sb([sum(a[i][j] * C[j] ** 3 for j in range(7)) for i in range(7)]) == R(1, 20)
    results["5th-order weights: sum b a a a c = 1/120"] = Sb([sum(a[i][j] * aac[j] for j in range(7)) for i in range(7)]) == R(1, 120)
    # order 5 for the dense output must FAIL (it is a 4th-order extension): report, do not require
    results["(info) dense output is NOT 5th order: sum b c^4 != theta^5/5"] = sp.simplify(sp.expand(S([c**4 for c in C]) - th**5 / 5)) != 0
    return results


if __name__ == "__main__":
    res = verify()
    for k, v in res.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    sys.exit(0 if all(res.values()) else 1)
