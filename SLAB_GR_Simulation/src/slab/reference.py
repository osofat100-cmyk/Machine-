"""High-precision (mpmath, >= 30 significant digits) reference solutions for scenarios WITHOUT an
elementary closed form, used to extend the TEST 8 convergence table.

Both references are built from first integrals and 1-D quadrature, i.e. a formulation that shares no
code with the engine's second-order Runge–Kutta integration (independent check):

(a) Radial rocket with constant inward proper acceleration alpha (engine on everywhere), L = 0.
    EXACT GR RESULT: dE/dtau = -alpha u^r  =>  E(r) = E0 + alpha (r0 - r)   (closed form),
    u^r = -sqrt(E(r)^2 - f),  u^v = 1/(E + sqrt(E^2 - f)),  so
        Delta tau = int dr / sqrt(E(r)^2 - f(r)),     Delta v = int u^v/|u^r| dr
    (elliptic-type integrals: no elementary closed form).  Example: the 'thrust_1g' scenario,
    alpha = 9.81 m/s^2 = 1.61e5 in geometrized units (unit c^4/GM), E rising from 1 to 3.2e7 at r_s.
(b) Equatorial geodesic plunge with angular momentum L (E = 1 here, no turning point for L < 4M):
        Delta tau = int dr/sqrt(E^2 - f (1 + L^2/r^2)),   Delta phi = int (L/r^2)/|u^r| dr,
        Delta v = int u^v/|u^r| dr with u^v = (1 + L^2/r^2)/(E + |u^r|).
Quadrature: mpmath tanh-sinh on x = ln r, split at every milestone and every decade of r, at
``dps`` decimal digits (default 35); the quadrature error estimate is returned and is ~1e-30.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

import mpmath as mp


def _pieces(r_hi, r_lo):
    """Break [r_lo, r_hi] (in ln r) at every power of ten."""
    x_hi, x_lo = mp.log(r_hi), mp.log(r_lo)
    k_hi = int(mp.floor(x_hi / mp.log(10)))
    k_lo = int(mp.ceil(x_lo / mp.log(10)))
    cuts = [x_hi] + [mp.mpf(k) * mp.log(10) for k in range(k_hi, k_lo - 1, -1) if x_lo < mp.mpf(k) * mp.log(10) < x_hi] + [x_lo]
    return cuts


def _quad_scaled(g, a, b):
    """mp.quad of g on [a, b] after normalizing g by its midpoint value: mp.quad's stopping test is
    absolute (~10^-dps), so pieces worth 1e-50 would otherwise be accepted after one level."""
    s = g((a + b) / 2) * (b - a)
    if s == 0:
        s = mp.mpf(1)
    val, e = mp.quad(lambda x: g(x) / s, [a, b], error=True)
    return val * s, e * abs(s)


def _integrate(integrand_r, r_hi, r_lo, near_hi_scale=None):
    """int_{r_lo}^{r_hi} g(r) dr = int g(e^x) e^x dx, piecewise tanh-sinh; returns (value, error estimate).

    near_hi_scale: if the integrand varies on a scale ``s`` just below r_hi (the rocket's energy
    E = E0 + alpha (r0 - r) changes by O(1) over r0 - r ~ 1/alpha), the interval [r_hi - 1e4 s, r_hi]
    is first integrated linearly in (r_hi - r) with breakpoints at every decade of s."""
    tot, err = mp.mpf(0), mp.mpf(0)
    if near_hi_scale is not None:
        s = mp.mpf(near_hi_scale)
        width = min(mp.mpf(10) ** 4 * s, (r_hi - r_lo) / 2)
        pts = [mp.mpf(0)] + [s * mp.mpf(10) ** k for k in range(-6, 5) if s * mp.mpf(10) ** k < width] + [width]
        for a, b in zip(pts[:-1], pts[1:]):
            val, e = _quad_scaled(lambda d: integrand_r(r_hi - d), a, b)
            tot += val
            err += abs(e)
        r_hi = r_hi - width
    cuts = _pieces(r_hi, r_lo)
    for a, b in zip(cuts[1:], cuts[:-1]):
        val, e = _quad_scaled(lambda x: integrand_r(mp.exp(x)) * mp.exp(x), a, b)
        tot += val
        err += abs(e)
    return tot, err


def thrust_radial_reference(r_points: Sequence[float], E0: float, alpha: float, r0: float, M: float = 1.0,
                            dps: int = 35) -> Dict[str, List]:
    """Segment increments between consecutive radii (decreasing) for the radial constant-thrust rocket."""
    with mp.workdps(dps):
        M_, a_, E0_, r0_ = mp.mpf(M), mp.mpf(alpha), mp.mpf(E0), mp.mpf(r0)
        E = lambda r: E0_ + a_ * (r0_ - r)
        # E^2 - f = (E - 1)(E + 1) + 2M/r written without cancellation near E = 1 at large r
        disc = lambda r: (E(r) - 1) * (E(r) + 1) + 2 * M_ / r
        dtau_dr = lambda r: 1 / mp.sqrt(disc(r))
        dv_dr = lambda r: 1 / ((E(r) + mp.sqrt(disc(r))) * mp.sqrt(disc(r)))
        out = {"r": [float(x) for x in r_points], "dtau": [0.0], "dv": [0.0], "u_r": [], "E": [], "quad_err": 0.0}
        rp = [mp.mpf(x) for x in r_points]
        errmax = mp.mpf(0)
        for i, r in enumerate(rp):
            out["u_r"].append(float(-mp.sqrt(disc(r))))
            out["E"].append(float(E(r)))
            if i == 0:
                continue
            sc = (1 / a_) if (i == 1 and a_ != 0) else None     # E(r) varies on the scale 1/alpha below r0
            t, e1 = _integrate(dtau_dr, rp[i - 1], r, sc)
            v, e2 = _integrate(dv_dr, rp[i - 1], r, sc)
            out["dtau"].append(float(t))
            out["dv"].append(float(v))
            errmax = max(errmax, e1 / abs(t), e2 / abs(v))
        out["quad_rel_err_max"] = float(errmax)
        out["dps"] = dps
        return out


def plunge_reference(r_points: Sequence[float], E: float, L: float, M: float = 1.0, dps: int = 35) -> Dict[str, List]:
    """Segment increments (tau, v, phi) for an inward equatorial geodesic with constants (E, L), no turning point."""
    with mp.workdps(dps):
        M_, E_, L_ = mp.mpf(M), mp.mpf(E), mp.mpf(L)
        q = lambda r: 1 + L_ * L_ / (r * r)
        disc = lambda r: E_ * E_ - (1 - 2 * M_ / r) * q(r)
        dtau_dr = lambda r: 1 / mp.sqrt(disc(r))
        dv_dr = lambda r: q(r) / ((E_ + mp.sqrt(disc(r))) * mp.sqrt(disc(r)))
        dphi_dr = lambda r: (L_ / (r * r)) / mp.sqrt(disc(r))
        rp = [mp.mpf(x) for x in r_points]
        out = {"r": [float(x) for x in r_points], "dtau": [0.0], "dv": [0.0], "dphi": [0.0], "u_r": []}
        errmax = mp.mpf(0)
        for i, r in enumerate(rp):
            out["u_r"].append(float(-mp.sqrt(disc(r))))
            if i == 0:
                continue
            vals = []
            for g in (dtau_dr, dv_dr, dphi_dr):
                val, e = _integrate(g, rp[i - 1], r)
                vals.append(float(val))
                errmax = max(errmax, e / abs(val))
            out["dtau"].append(vals[0]); out["dv"].append(vals[1]); out["dphi"].append(vals[2])
        out["quad_rel_err_max"] = float(errmax)
        out["dps"] = dps
        return out


def e1_reference_check(dps: int = 35) -> float:
    """Self-test of the quadrature machinery on the E = 1, L = 0 case, which HAS a closed form:
    tau(r_s -> 1e-30 r_s) = (4M/3)(1 - (1e-30)^(3/2)); returns the relative error (expected < 1e-28)."""
    with mp.workdps(dps):
        r_lo = mp.mpf(2) * mp.mpf(10) ** -30
        val, _ = _integrate(lambda r: 1 / mp.sqrt(2 / r), mp.mpf(2), r_lo)
        exact = (mp.mpf(4) / 3) * (1 - (r_lo / 2) ** mp.mpf(1.5))
        return float(abs(val / exact - 1))
