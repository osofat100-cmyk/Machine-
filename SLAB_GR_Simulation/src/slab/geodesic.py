"""Timelike worldlines (geodesic or rocket-propelled) in ingoing EF coordinates.

State vector (10 components, geometrized units, M = 1):
    y = [v_seg, r, theta, phi, u^v, u^r, u^theta, u^phi, tau_seg, E_k]
E_k is the Killing energy carried as its own (well-conditioned) variable:
dE_k/dtau = 0 for geodesics, -alpha u^r under radial thrust.  It is used to
build the comoving frame deep inside the hole, where f u^v - u^r evaluated
from the 4-velocity components suffers catastrophic cancellation.
v_seg and tau_seg are measured from the start of the current integration
segment (offsets are carried by the driver), which keeps their relative
error control tight even deep inside the hole where the remaining proper
time is tiny compared with the elapsed proper time.

Equations of motion (second-order geodesic equation with optional thrust):
    du^a/dtau = -Gamma^a_bc u^b u^c + a^a,     dx^a/dtau = u^a
with a^a the 4-acceleration.  For a rocket with constant proper
acceleration alpha directed along -n (inward along the observer's local
radial axis), a^a = -alpha n^a/|n|, n = (u^v, E, 0, 0), E = f u^v - u^r,
|n|^2 = g(n,n) = 1 + r^2[(u^theta)^2 + sin^2 theta (u^phi)^2] (= 1 for
radial motion).  n is orthogonal to u, so g(u,u) = -1 is preserved exactly
by the continuous equations, and g(a,a) = alpha^2.

Two choices of independent variable are supported:
    'tau' : x = tau                (dy/dx = F(y))
    'lnr' : x = ln r               (dy/dx = F(y) * r / u^r),  valid while u^r < 0
The 'lnr' form is what makes the 10^41-decade range in r tractable: the
step in ln r is bounded, so the step in r (and in tau) shrinks
automatically as the curvature K ~ r^-6 rises.

Conserved quantities for geodesics (Killing symmetries):
    E = f u^v - u^r          (energy per unit mass; -u_v)
    L = r^2 sin^2theta u^phi (angular momentum per unit mass)
    g(u,u) = -1              (normalization)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .metric import StaticSphericalMetric, Schwarzschild, V, R, TH, PH

IV, IR, ITH, IPH, IUV, IUR, IUTH, IUPH, ITAU, IEK = range(10)
NSTATE = 10
STATE_NAMES = ["v_seg", "r", "theta", "phi", "u_v", "u_r", "u_theta", "u_phi", "tau_seg", "E_killing"]


@dataclass(frozen=True)
class Thrust:
    """Constant proper acceleration (geometrized, 1/M) along the local radial axis.

    alpha > 0 : thrust INWARD (along -n); alpha < 0 : outward.
    Optional radial window [r_on_min, r_on_max] (geometrized) in which the engine runs.
    """

    alpha: float = 0.0
    r_on_min: float = 0.0
    r_on_max: float = math.inf

    def active(self, r: float) -> bool:
        return self.alpha != 0.0 and self.r_on_min <= r <= self.r_on_max


def energy(metric: StaticSphericalMetric, y: np.ndarray) -> float:
    """Killing energy E = f u^v - u^r = -u_v.

    NUMERICAL CAVEAT: deep inside the hole f u^v and u^r are individually
    ~sqrt(2M/r) (10^19 at r_QG) while E = O(1), so this expression suffers
    catastrophic cancellation; use :func:`energy_conditioning_scale` to
    interpret the drift (see physics_notes.md, 'Conserved quantities')."""
    return metric.f(y[IR]) * y[IUV] - y[IUR]


def energy_conditioning_scale(metric: StaticSphericalMetric, y: np.ndarray) -> float:
    """Magnitude of the terms that cancel in E; E is numerically resolvable only to
    ~ eps_machine * this scale."""
    return max(abs(metric.f(y[IR]) * y[IUV]), abs(y[IUR]), 1.0)


def angular_momentum(y: np.ndarray) -> float:
    return y[IR] ** 2 * math.sin(y[ITH]) ** 2 * y[IUPH]


def norm(metric: StaticSphericalMetric, y: np.ndarray) -> float:
    r, th = y[IR], y[ITH]
    f = metric.f(r)
    return (-f * y[IUV] ** 2 + 2.0 * y[IUV] * y[IUR]
            + r * r * (y[IUTH] ** 2 + math.sin(th) ** 2 * y[IUPH] ** 2))


def norm_conditioning_scale(metric: StaticSphericalMetric, y: np.ndarray) -> float:
    """Largest term in g(u,u); the residual g(u,u)+1 is only resolvable to eps_machine * this.
    O(1) for radial motion; ~L^2/r^2 for L != 0 deep inside (u^phi = L/r^2 -> 1e74 at r_QG)."""
    r, th = y[IR], y[ITH]
    f = metric.f(r)
    return max(abs(f * y[IUV] ** 2), abs(2.0 * y[IUV] * y[IUR]), r * r * (y[IUTH] ** 2 + math.sin(th) ** 2 * y[IUPH] ** 2), 1.0)


def radial_unit_norm(y: np.ndarray) -> float:
    """|n| for n = (u^v, E, 0, 0): sqrt(1 + r^2 [(u^theta)^2 + sin^2 theta (u^phi)^2]) (exact identity
    from g(u,u) = -1 and E = f u^v - u^r; well conditioned)."""
    r, th = y[IR], y[ITH]
    return math.sqrt(1.0 + r * r * (y[IUTH] ** 2 + math.sin(th) ** 2 * y[IUPH] ** 2))


def four_acceleration(metric: StaticSphericalMetric, y: np.ndarray, thrust: Thrust) -> np.ndarray:
    """a^mu = -alpha n^mu/|n| with n the outward radial vector orthogonal to u."""
    a = np.zeros(4)
    r = y[IR]
    if thrust.active(r):
        E = y[IEK]
        k = thrust.alpha / radial_unit_norm(y)
        a[V] = -k * y[IUV]
        a[R] = -k * E
    return a


def rhs_tau(metric: StaticSphericalMetric, y: np.ndarray, thrust: Thrust | None = None) -> np.ndarray:
    """dy/dtau.  Written out explicitly (no Christoffel array build) for speed."""
    r, th = y[IR], y[ITH]
    uv, ur, uth, uph = y[IUV], y[IUR], y[IUTH], y[IUPH]
    f = metric.f(r)
    fp = metric.df(r)
    s, co = math.sin(th), math.cos(th)
    if abs(co) < 1e-14:
        co = 0.0     # equatorial plane: cos(pi/2) = 6e-17 in floating point would seed a spurious u^theta
                     # through the source term sin cos (u^phi)^2, which is amplified enormously when u^phi ~ L/r^2
    s2 = s * s
    ang = uth * uth + s2 * uph * uph          # (u^th)^2 + sin^2 (u^ph)^2
    d = np.empty(NSTATE)
    d[IV] = uv
    d[IR] = ur
    d[ITH] = uth
    d[IPH] = uph
    # du^v/dtau = -(f'/2)(u^v)^2 + r * ang
    d[IUV] = -0.5 * fp * uv * uv + r * ang
    # du^r/dtau = -(f f'/2)(u^v)^2 + f' u^v u^r + r f * ang
    d[IUR] = -0.5 * f * fp * uv * uv + fp * uv * ur + r * f * ang
    # du^th/dtau = -(2/r) u^r u^th + sin cos (u^ph)^2
    d[IUTH] = -2.0 * ur * uth / r + s * co * uph * uph
    # du^ph/dtau = -(2/r) u^r u^ph - 2 cot u^th u^ph
    d[IUPH] = -2.0 * ur * uph / r - (2.0 * co / s * uth * uph if s != 0.0 else 0.0)
    d[ITAU] = 1.0
    d[IEK] = 0.0
    if thrust is not None and thrust.active(r):
        E = y[IEK]                      # well-conditioned Killing energy (equals f u^v - u^r)
        k = thrust.alpha / math.sqrt(1.0 + r * r * ang)   # alpha / |n|
        d[IUV] += -k * uv
        d[IUR] += -k * E
        d[IEK] = -k * ur                # dE/dtau = -a_v = -(alpha/|n|) u^r
    return d


def rhs_lnr(metric: StaticSphericalMetric, x: float, y: np.ndarray, thrust: Thrust | None = None) -> np.ndarray:
    """dy/d(ln r) = (dy/dtau) * r / u^r,  with r := exp(x) taken from the independent variable.

    The state's r component is NOT evolved (derivative 0): it is a passive copy that callers must
    overwrite with exp(x) (the driver does).  Integrating dr/dx = exp(x) alongside would accumulate an
    absolute error that dwarfs the exponentially decaying true value deep inside."""
    y = y.copy()
    y[IR] = math.exp(x)
    d = rhs_tau(metric, y, thrust)
    d = d * (y[IR] / y[IUR])
    d[IR] = 0.0
    return d


def initial_state_radial(metric: StaticSphericalMetric, r0: float, E: float, L: float = 0.0,
                         theta0: float = math.pi / 2, phi0: float = 0.0, inward: bool = True) -> np.ndarray:
    """Timelike initial state at radius r0 with specific energy E and angular momentum L.

    u^r = -sqrt(E^2 - f (1 + L^2/r^2)),   u^v = (1 + L^2/r^2) / (E + |u^r|)   [regular at f = 0],
    u^phi = L / (r^2 sin^2 theta).  For E = 1, L = 0 this is free fall from rest at infinity.
    """
    f = metric.f(r0)
    s2 = math.sin(theta0) ** 2
    Veff = f * (1.0 + L * L / (r0 * r0 * s2))
    disc = E * E - Veff
    if -1e-12 * E * E < disc < 0.0:
        disc = 0.0                      # start exactly at a turning point (rest) up to round-off
    elif 0.0 < disc <= 8.0 * 2.220446049250313e-16 * max(E * E, Veff):
        disc = 0.0                      # positive round-off of E^2 - V (e.g. E = sqrt(f(r0)) typed for 'rest'):
                                        # sqrt would otherwise turn 1e-16 into a spurious u^r ~ -1e-8
    if disc < 0.0:
        raise ValueError(f"E^2 = {E*E} < effective potential {Veff} at r0 = {r0}: not a real radial velocity")
    ur = -math.sqrt(disc) if inward else math.sqrt(disc)
    # From E = f u^v - u^r  and  the null-free relation  f (u^v)^2 - 2 E u^v + (1 + L^2/r^2) = 0:
    # u^v = (1 + L^2/r^2)/(E + sqrt(E^2 - Veff))   (the root regular at f = 0)
    uv = (1.0 + L * L / (r0 * r0 * s2)) / (E + math.sqrt(disc))
    if not inward:
        # outward-moving root; only valid for f > 0
        uv = (E + math.sqrt(disc)) / f
    y = np.zeros(NSTATE)
    y[IV] = 0.0
    y[IR] = r0
    y[ITH] = theta0
    y[IPH] = phi0
    y[IUV] = uv
    y[IUR] = ur
    y[IUTH] = 0.0
    y[IUPH] = L / (r0 * r0 * s2) if L != 0.0 else 0.0
    y[ITAU] = 0.0
    y[IEK] = E
    return y


# ---------------------------------------------------------------------------
# First-integral (Killing) formulation — INDEPENDENT cross-check of the second-order form
# ---------------------------------------------------------------------------
IE, IL = 4, 5
FI_STATE_NAMES = ["v_seg", "r", "theta", "phi", "E", "L", "tau_seg"]


def first_integral_velocity(metric: StaticSphericalMetric, r: float, E: float, L: float, theta: float = math.pi / 2):
    """(u^v, u^r, u^phi) from the constants of motion for INWARD equatorial motion."""
    f = metric.f(r)
    s2 = math.sin(theta) ** 2
    q = 1.0 + L * L / (r * r * s2)
    disc = E * E - f * q
    ur = -math.sqrt(max(disc, 0.0))
    uv = q / (E - ur)       # = q/(E + |u^r|): regular at f = 0
    uph = L / (r * r * s2)
    return uv, ur, uph


def rhs_first_integral_lnr(metric: StaticSphericalMetric, x: float, y: np.ndarray, thrust: Thrust | None = None) -> np.ndarray:
    """d/d(ln r) of [v_seg, r, theta, phi, E, L, tau_seg] using the first integrals.

    Geodesic: dE/dtau = dL/dtau = 0.  Radial thrust a = -alpha n: dE/dtau = -a_v = -alpha u^r, dL/dtau = 0.
    """
    r = math.exp(x)
    E, L, th = y[IE], y[IL], y[2]
    uv, ur, uph = first_integral_velocity(metric, r, E, L, th)
    if ur == 0.0:
        raise ValueError("ln r formulation is invalid at a turning point (u^r = 0); use the tau form")
    d = np.zeros(7)
    fac = r / ur
    d[0] = uv * fac
    d[1] = r
    d[3] = uph * fac
    if thrust is not None and thrust.active(r):
        d[IE] = (-thrust.alpha * ur / math.sqrt(1.0 + L * L / (r * r * math.sin(th) ** 2))) * fac
    d[6] = fac
    return d


def proper_time_to_center(metric: StaticSphericalMetric, r: float, E: float, L: float, theta: float = math.pi / 2,
                          n: int = 4000) -> float:
    """Classical proper time from r to r = 0 for FREE FALL with constants (E, L):
        tau = int_0^r dr' / sqrt(E^2 - f(r')(1 + L^2/r'^2)).
    Evaluated with the substitution r' = exp(x) (integrand ~ r'^{1/2} for L = 0, ~ r'^{3/2}
    for L != 0 near the centre) by composite Simpson quadrature on x in [ln r - 70, ln r].
    Exact closed forms exist for E = 1, L = 0 ((2/3) sqrt(r^3/2M)); this general form is used
    for the 'remaining proper time' column when L != 0 or E != 1.  It assumes coasting
    (no thrust) from r inward and is a classical-GR extrapolation, not a validated quantity."""
    if r <= 0.0:
        return 0.0
    s2 = math.sin(theta) ** 2
    x1 = math.log(r)
    x0 = x1 - 70.0
    x = np.linspace(x0, x1, n + 1)
    rr = np.exp(x)
    try:
        fvals = metric.f(rr)                         # vectorized metric (Schwarzschild: 1 - 2M/r)
        if np.ndim(fvals) == 0:
            raise TypeError
    except Exception:
        fvals = np.array([metric.f(float(v)) for v in rr])
    disc = E * E - fvals * (1.0 + L * L / (rr * rr * s2))
    val = np.where(disc > 0.0, rr / np.sqrt(np.where(disc > 0.0, disc, 1.0)), 0.0)
    w = np.full(n + 1, 2.0); w[1::2] = 4.0; w[0] = w[-1] = 1.0
    h = (x1 - x0) / n
    return float(np.sum(w * val) * h / 3.0)


# ---------------------------------------------------------------------------
# Analytic reference solution: Schwarzschild, E = 1, L = 0 (radial free fall from rest at infinity)
# ---------------------------------------------------------------------------
class RadialInfallE1:
    """Closed-form E = 1 radial geodesic (EXACT GR RESULT; MTW ch. 25 radial geodesics — section/box numbers from memory, INSUFFICIENT DATA TO VERIFY; Taylor & Wheeler 2000 ch. 3).

    With x = sqrt(r/2M):
        dr/dtau = -sqrt(2M/r)                 tau(r) = -(4M/3) x^3 + C_tau
        u^v     = x/(1+x)                     v(r)   = -4M [x^3/3 - x^2/2 + x - ln(1+x)] + C_v
    Proper time from the horizon (x = 1) to r = 0:  4M/3.
    """

    def __init__(self, M: float = 1.0):
        self.M = M

    def ur(self, r: float) -> float:
        return -math.sqrt(2.0 * self.M / r)

    def uv(self, r: float) -> float:
        x = math.sqrt(r / (2.0 * self.M))
        return x / (1.0 + x)

    def tau_to_center(self, r: float) -> float:
        """Proper time remaining from r to r = 0."""
        return (2.0 / 3.0) * r ** 1.5 / math.sqrt(2.0 * self.M)

    def tau_between(self, r_from: float, r_to: float) -> float:
        return self.tau_to_center(r_from) - self.tau_to_center(r_to)

    def v_between(self, r_from: float, r_to: float) -> float:
        return self._v(r_to) - self._v(r_from)

    def _v(self, r: float) -> float:
        x = math.sqrt(r / (2.0 * self.M))
        return -4.0 * self.M * self._bracket(x)

    @staticmethod
    def _bracket(x: float) -> float:
        """B(x) = x^3/3 - x^2/2 + x - ln(1+x) = sum_{n>=4} (-1)^n x^n / n, evaluated without cancellation."""
        if x < 0.05:
            tot, term, n = 0.0, x**4, 4
            sign = 1.0
            while True:
                add = sign * term / n
                tot += add
                if abs(add) < 1e-18 * abs(tot):
                    break
                term *= x; n += 1; sign = -sign
                if n > 200:
                    break
            return tot
        return x**3 / 3.0 - x * x / 2.0 + x - math.log1p(x)

    def tau_horizon_to_center(self) -> float:
        return 4.0 * self.M / 3.0
