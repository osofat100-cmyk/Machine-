"""Relative accelerations in the proper reference frame of an ACCELERATED observer (thrust mode).

Physics (derived in docs/additions/engine.md §1; tags there):

In the proper reference frame of an observer with proper acceleration a^i (spatial axes
Fermi–Walker transported, i.e. non-rotating), the metric to the order needed here is

    ds^2 = -[(1 + a_j x^j)^2 + R_0i0j x^i x^j] dt^2 + (terms that do not affect a particle at rest)
           + [delta_ij + O(x^2)] dx^i dx^j,

where t is the observer's proper time on the worldline x = 0 (MTW §13.6 gives the part linear in
x; the quadratic terms are in Ni & Zimmermann 1978, Phys. Rev. D 17, 1473).  For a free particle
momentarily at rest at x^i = xi^i the geodesic equation gives (Gamma^i_00 = -1/2 d_i g_00)

    d^2 xi^i/dt^2 = -a^i  -  a^i (a_j xi^j)  -  R^i_0j0 xi^j  +  O(xi^2, velocity terms).

The first term is the uniform "falling behind" of every free particle; the DIFFERENTIAL
acceleration of a free particle at xi relative to one released at the origin is

    delta a^i = -[ R^i_0j0 + a^i a_j ] xi^j = -[E^i_j + a^i a_j] xi^j.

Sign convention (same as the tidal columns): positive = separation.  Along the thrust axis
(xi = L a_hat, either ahead or behind) the inertial part is -a^2 L < 0, i.e. an approach
(compression) of magnitude a^2 L / c^2 in SI units; it vanishes transverse to the thrust axis
(a_j xi^j = 0) and exactly when the engine is off.  For the rocket used here the thrust axis is the
radial direction n, which is an eigen-direction of the tidal tensor for any 4-velocity
(E_1j = 0 for j != 1, checked in tests), so the radial total is simply

    radial_total = -(lambda_radial + a^2) L.

Exact flat-space check (Rindler): free particles at rest at proper distance l ahead of an
observer with constant proper acceleration a stay at inertial rest, and their position in the
observer's instantaneous rest frame is xi_l(tau) = (1/a + l)/cosh(a tau) - 1/a, so
xi_L - xi_0 = L/cosh(a tau), whose second derivative at tau = 0 is exactly -a^2 L.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

from .constants import c as C_LIGHT
from .metric import StaticSphericalMetric, Schwarzschild
from .geodesic import Thrust, rhs_tau, IV, IR, ITH, IUV, IUR, IEK, NSTATE
from .integrators import DormandPrince54


@dataclass(frozen=True)
class FlatEF(StaticSphericalMetric):
    """Minkowski space written in the same ingoing null form, f = 1:
    ds^2 = -dv^2 + 2 dv dr + r^2 dOmega^2  (t = v - r, x = r gives -dt^2 + dx^2 radially).
    Used ONLY for the independent flat-space (Rindler) check of the accelerated-frame terms."""

    name: str = "Minkowski (f = 1, ingoing null form)"
    established: bool = True
    citation: str = "special relativity"

    def f(self, r):
        return 1.0 + 0.0 * r

    def df(self, r):
        return 0.0 * r

    def d2f(self, r):
        return 0.0 * r


# ---------------------------------------------------------------------------
# The inertial term itself
# ---------------------------------------------------------------------------
def inertial_relative_accel(a_vec: np.ndarray, xi: np.ndarray) -> np.ndarray:
    """-a (a . xi): differential acceleration (w.r.t. a free particle at the origin) of a free particle
    at rest at xi in the observer's non-rotating proper reference frame, from the frame's own
    acceleration (any consistent units; spatial frame components)."""
    a_vec = np.asarray(a_vec, dtype=float)
    return -a_vec * float(np.dot(a_vec, xi))


def inertial_diff_along_thrust_SI(a_SI: float, length_m: float) -> float:
    """Signed (positive = separation) inertial differential acceleration across a proper length
    L along the thrust axis: -a^2 L / c^2 [m/s^2].  Exactly 0 for a = 0."""
    if a_SI == 0.0:
        return 0.0
    return -(a_SI * a_SI) * length_m / (C_LIGHT * C_LIGHT)


def thrust_energy_closed_form(E0: float, alpha: float, r0: float, r):
    """EXACT for radial motion with constant inward proper acceleration alpha (geometrized) switched on
    over the whole range: dE/dtau = -alpha u^r  =>  dE/dr = -alpha  =>  E(r) = E0 + alpha (r0 - r)."""
    return E0 + alpha * (r0 - np.asarray(r, dtype=float))


def crossover_radius_geo(alpha_geo: float, M: float = 1.0) -> float:
    """Radius where the radial tidal eigenvalue 2M/r^3 equals the inertial term alpha^2 (radial
    motion): r_x = (2M/alpha^2)^(1/3).  Below r_x curvature dominates."""
    return (2.0 * M / (alpha_geo * alpha_geo)) ** (1.0 / 3.0) if alpha_geo != 0.0 else math.inf


# ---------------------------------------------------------------------------
# Independent numerical checks (used by validation TEST 9 and tests/test_accelerated_frame.py)
# ---------------------------------------------------------------------------
def _poly_second_derivative_at_zero(tau: np.ndarray, x: np.ndarray, deg: int = 3) -> float:
    """Fit x(tau) = c0 + c1 tau^2 + ... + c_deg tau^(2 deg) (time-symmetric data: release from rest in a
    static or uniformly accelerated frame) and return x''(0) = 2 c1."""
    A = np.vstack([tau ** (2 * k) for k in range(deg + 1)]).T
    coef, *_ = np.linalg.lstsq(A, x, rcond=None)
    return 2.0 * coef[1]


def rindler_flat_check(a: float = 1.0, L: float = 0.1, r0: float = 1.0e4, tau_max: float = 2.0,
                       n_eval: int = 201, rtol: float = 1e-13) -> Dict:
    """Flat space, engine-integrated: observer with constant inward proper acceleration a (engine thrust
    model, rhs_tau with f = 1), two free particles (engine geodesics) released at rest at the observer
    and a proper distance L AHEAD (inward, along the thrust).  Their positions xi(tau) in the observer's
    instantaneous rest frame are compared with the exact Rindler result and the differential
    acceleration at tau = 0 with -a^2 L."""
    m = FlatEF()
    th = math.pi / 2
    y_obs = np.zeros(NSTATE); y_obs[IR] = r0; y_obs[ITH] = th; y_obs[IUV] = 1.0; y_obs[IEK] = 1.0
    integ = DormandPrince54(rtol=rtol, atol=np.full(NSTATE, 1e-15), max_step=0.02)
    tau_grid = np.linspace(0.0, tau_max, n_eval)
    thrust = Thrust(alpha=a)
    ro = integ.integrate(lambda x, y: rhs_tau(m, y, thrust), 0.0, y_obs, tau_max, t_eval=tau_grid)
    Yo = ro.y_eval
    # observer vs the exact hyperbola (tests the engine's thrust implementation in flat space)
    x_exact = r0 - (np.cosh(a * tau_grid) - 1.0) / a
    t_exact = np.sinh(a * tau_grid) / a
    obs_err = float(np.max(np.abs(np.column_stack([Yo[:, IR] - x_exact, (Yo[:, IV] - Yo[:, IR] + r0) - t_exact]))))
    xi = {}
    for label, ell in (("origin", 0.0), ("ahead", L)):
        y_p = np.zeros(NSTATE); y_p[IR] = r0 - ell; y_p[ITH] = th; y_p[IUV] = 1.0; y_p[IEK] = 1.0
        tp_max = 1.2 * math.cosh(a * tau_max) * (1.0 / a + ell) + 1.0
        rp = integ.integrate(lambda x, y: rhs_tau(m, y), 0.0, y_p, tp_max, dense_output=True)
        sol = rp.dense
        out = []
        for k in range(len(tau_grid)):
            vo, ro_, uv, ur = Yo[k, IV], Yo[k, IR], Yo[k, IUV], Yo[k, IUR]
            to = vo - ro_ + r0                      # inertial t = v - r (+ const so that t = 0 at start)
            ut, ux = uv - ur, ur
            from scipy.optimize import brentq

            def g(tp):
                yp = sol(tp)
                dt = (yp[IV] - yp[IR] + (r0 - ell)) - to
                dx = yp[IR] - ro_
                return -dt * ut + dx * ux           # g(X_p - X_o, u_o) = 0 on the rest-frame slice
            tp = brentq(g, 0.0, tp_max * 0.999, xtol=1e-15, rtol=1e-15, maxiter=200)
            yp = sol(tp)
            dt = (yp[IV] - yp[IR] + (r0 - ell)) - to
            dx = yp[IR] - ro_
            out.append(dt * ux - dx * ut)            # xi along the INWARD (thrust) axis: -g(Delta, n)
        xi[label] = np.array(out)
    exact0 = (1.0 / a) / np.cosh(a * tau_grid) - 1.0 / a
    exactL = (1.0 / a + L) / np.cosh(a * tau_grid) - 1.0 / a
    diff = xi["ahead"] - xi["origin"]
    small = tau_grid <= 0.3 / a + 1e-12
    acc_diff = _poly_second_derivative_at_zero(tau_grid[small], diff[small], deg=5)
    acc_origin = _poly_second_derivative_at_zero(tau_grid[small], xi["origin"][small], deg=5)
    return {
        "a_geo": a, "L_geo": L, "tau_max": tau_max,
        "observer_vs_exact_hyperbola_max_abs": obs_err,
        "xi_origin_vs_exact_max_abs": float(np.max(np.abs(xi["origin"] - exact0))),
        "xi_ahead_vs_exact_max_abs": float(np.max(np.abs(xi["ahead"] - exactL))),
        "separation_vs_L_over_cosh_max_rel": float(np.max(np.abs(diff - L / np.cosh(a * tau_grid)) / L)),
        "separation_at_tau_max_over_L": float(diff[-1] / L),
        "measured_diff_accel_at_0": float(acc_diff),
        "predicted_inertial_term_-a2L": -a * a * L,
        "measured_origin_accel_at_0": float(acc_origin),
        "predicted_origin_accel_-a": -a,
    }


def _proper_radial_distance_static(r: float) -> float:
    """F(r) with dF/dr = 1/sqrt(1 - 2/r) (M = 1): sqrt(r(r-2)) + 2 ln(sqrt(r) + sqrt(r-2))."""
    return math.sqrt(r * (r - 2.0)) + 2.0 * math.log(math.sqrt(r) + math.sqrt(r - 2.0))


def hovering_check(r0: float, L: float = 1e-3, tau_max: float | None = None, n_eval: int = 41, rtol: float = 1e-13,
                   sign: float = +1.0) -> Dict:
    """Schwarzschild (M = 1): a static observer at r0 held by the engine thrust (outward proper
    acceleration a = M/(r0^2 sqrt(f0))), and two free particles released from rest (engine geodesics) at
    the observer and a proper radial distance L ahead along the thrust axis (sign=+1: outward = ahead,
    sign=-1: inward = behind).  The static observer's rest frame is the slice t = const, where the proper
    radial distance is exact (F(r) above), so xi(tau) is measured without approximation.

    Predictions: xi_0''(0) = -a (exact); differential xi_L'' - xi_0'' = -(lambda_radial + a^2) xi to first
    order in L, with lambda_radial = -2M/r0^3 (static frame); the exact initial acceleration of the
    particle at xi is -(1/2) sqrt(f1) f'(r1)/f0 (lapse N^2 = f/f0)."""
    m = Schwarzschild()
    th = math.pi / 2
    f0 = m.f(r0)
    a = 1.0 / (r0 * r0 * math.sqrt(f0))
    lam = -2.0 / r0 ** 3
    if tau_max is None:
        tau_max = 0.15 * math.sqrt((r0 - 2.0) / a)     # short compared with the fall time over the distance to r_s
    tau_grid = np.linspace(0.0, tau_max, n_eval)
    integ = DormandPrince54(rtol=rtol, atol=np.full(NSTATE, 1e-16), max_step=0.01)
    # observer: at rest, outward thrust alpha = -a (Thrust.alpha > 0 means inward)
    y_obs = np.zeros(NSTATE); y_obs[IR] = r0; y_obs[ITH] = th
    y_obs[IUV] = 1.0 / math.sqrt(f0); y_obs[IEK] = math.sqrt(f0)      # static: u^r = 0, E = f u^v = sqrt(f0)
    ro = integ.integrate(lambda x, y: rhs_tau(m, y, Thrust(alpha=-a)), 0.0, y_obs, tau_max, t_eval=tau_grid)
    hover_err = float(np.max(np.abs(ro.y_eval[:, IR] - r0)))
    t_obs = tau_grid / math.sqrt(f0)                  # static observer: t = tau / sqrt(f0), t = 0 at release
    F0 = _proper_radial_distance_static(r0)
    # r1 with F(r1) - F0 = sign * L  (Newton on F, dF/dr = 1/sqrt(f))
    r1 = r0 + sign * L * math.sqrt(f0)
    for _ in range(50):
        g = _proper_radial_distance_static(r1) - F0 - sign * L
        r1 -= g * math.sqrt(m.f(r1))
        if abs(g) < 1e-16:
            break
    xi = {}
    from scipy.optimize import brentq
    for label, rr in (("origin", r0), ("ahead", r1)):
        y_p = np.zeros(NSTATE); y_p[IR] = rr; y_p[ITH] = th
        y_p[IUV] = 1.0 / math.sqrt(m.f(rr)); y_p[IEK] = math.sqrt(m.f(rr))   # released from rest
        rstar0 = m.tortoise(rr)
        tp_max = 1.5 * tau_max + 0.1
        rp = integ.integrate(lambda x, y: rhs_tau(m, y), 0.0, y_p, tp_max, dense_output=True)
        sol = rp.dense
        out = []
        for tt in t_obs:
            def g(tp):
                yp = sol(tp)
                return (yp[IV] - m.tortoise(yp[IR]) + rstar0) - tt
            tp = brentq(g, 0.0, tp_max, xtol=1e-16, rtol=1e-15, maxiter=200) if tt > 0 else 0.0
            out.append(sign * (_proper_radial_distance_static(sol(tp)[IR]) - F0))
        xi[label] = np.array(out)
    diff = xi["ahead"] - xi["origin"]
    acc_diff = _poly_second_derivative_at_zero(tau_grid, diff, deg=4)
    acc_origin = sign * _poly_second_derivative_at_zero(tau_grid, xi["origin"], deg=4)   # along +r
    f1 = m.f(r1)
    exact_ahead = -0.5 * math.sqrt(f1) * m.df(r1) / f0          # d^2 xi_r/dtau^2 of the particle at r1 (along +r)
    exact_diff = sign * (exact_ahead - (-a))
    return {
        "r0_geo": r0, "r0_over_rs": r0 / 2.0, "L_geo": L, "direction": "outward (ahead of the outward thrust)" if sign > 0 else "inward (behind)",
        "a_geo": a, "lambda_radial_geo": lam, "a2_over_abs_lambda": a * a / abs(lam),
        "observer_hover_max_abs_dr": hover_err,
        "measured_origin_accel_along_r": float(acc_origin), "predicted_-a": -a,
        "measured_diff_accel": float(acc_diff),
        "exact_lapse_diff_accel": float(exact_diff),
        "predicted_-(lambda+a2)L": float(-(lam + a * a) * L),
        "tidal_only_prediction_-lambdaL": float(-lam * L),
    }
