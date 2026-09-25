"""Static spherically symmetric metrics in ingoing Eddington–Finkelstein form.

    ds^2 = -f(r) dv^2 + 2 dv dr + r^2 (dtheta^2 + sin^2 theta dphi^2)

with  v = t + r_*  (advanced time),  dr_*/dr = 1/f.

For Schwarzschild, f(r) = 1 - 2M/r and the chart (v, r, theta, phi) is
regular across the future event horizon r = 2M: every metric coefficient,
its inverse, every Christoffel symbol and every Riemann component is finite
there.  This is the coordinate system used for ALL numerical integration in
this project (the horizon crossing is never integrated in Schwarzschild
(t, r) coordinates).  Kruskal–Szekeres coordinates are computed
analytically from (v, r) for the causal diagram (see :func:`kruskal`).

References (see references.md):
  * Eddington 1924 (Nature 113, 192); Finkelstein 1958 (Phys. Rev. 110, 965)
  * Misner, Thorne & Wheeler, "Gravitation" (1973), §31.4, Box 31.2
  * Wald, "General Relativity" (1984), §6.4
  * Kruskal 1960 (Phys. Rev. 119, 1743); Szekeres 1960 (Publ. Math. Debrecen 7, 285)

Coordinate index convention: 0 = v, 1 = r, 2 = theta, 3 = phi.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

V, R, TH, PH = 0, 1, 2, 3


@dataclass(frozen=True)
class StaticSphericalMetric:
    """Base class: subclasses provide f, df/dr and d^2f/dr^2.

    ``established`` marks whether the metric is an EXACT, experimentally
    supported solution of Einstein's equations (Schwarzschild) or a
    SPECULATIVE toy model (everything in slab.speculative).
    """

    name: str = "abstract"
    established: bool = False
    citation: str = ""

    # --- to be overridden -------------------------------------------------
    def f(self, r: float) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    def df(self, r: float) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    def d2f(self, r: float) -> float:  # pragma: no cover - abstract
        raise NotImplementedError

    # --- metric tensor ------------------------------------------------------
    def g_lower(self, r: float, theta: float) -> np.ndarray:
        g = np.zeros((4, 4))
        g[V, V] = -self.f(r)
        g[V, R] = g[R, V] = 1.0
        g[TH, TH] = r * r
        g[PH, PH] = r * r * math.sin(theta) ** 2
        return g

    def g_upper(self, r: float, theta: float) -> np.ndarray:
        """Exact inverse: g^{vv}=0, g^{vr}=1, g^{rr}=f, g^{thth}=1/r^2, g^{phph}=1/(r^2 sin^2)."""
        gi = np.zeros((4, 4))
        gi[V, R] = gi[R, V] = 1.0
        gi[R, R] = self.f(r)
        gi[TH, TH] = 1.0 / (r * r)
        gi[PH, PH] = 1.0 / (r * r * math.sin(theta) ** 2)
        return gi

    def dot(self, r: float, theta: float, a: np.ndarray, b: np.ndarray) -> float:
        """Inner product g(a, b) written out explicitly (no matrix build)."""
        f = self.f(r)
        s2 = math.sin(theta) ** 2
        return (-f * a[V] * b[V] + a[V] * b[R] + a[R] * b[V]
                + r * r * (a[TH] * b[TH] + s2 * a[PH] * b[PH]))

    # --- Christoffel symbols Gamma^a_{bc} --------------------------------
    def christoffel(self, r: float, theta: float) -> np.ndarray:
        """All Christoffel symbols of the ingoing-EF metric, Gamma[a, b, c].

        Derived by hand and re-derived symbolically in tools/derive_ef_curvature.py.
        Nonzero components (f' = df/dr):
          G^v_vv = f'/2          G^v_thth = -r            G^v_phph = -r sin^2
          G^r_vv = f f'/2        G^r_vr   = -f'/2         G^r_thth = -r f
          G^r_phph = -r f sin^2  G^th_rth = 1/r           G^th_phph = -sin cos
          G^ph_rph = 1/r         G^ph_thph = cot
        """
        f = self.f(r)
        fp = self.df(r)
        s, co = math.sin(theta), math.cos(theta)
        G = np.zeros((4, 4, 4))
        G[V, V, V] = 0.5 * fp
        G[V, TH, TH] = -r
        G[V, PH, PH] = -r * s * s
        G[R, V, V] = 0.5 * f * fp
        G[R, V, R] = G[R, R, V] = -0.5 * fp
        G[R, TH, TH] = -r * f
        G[R, PH, PH] = -r * f * s * s
        G[TH, R, TH] = G[TH, TH, R] = 1.0 / r
        G[TH, PH, PH] = -s * co
        G[PH, R, PH] = G[PH, PH, R] = 1.0 / r
        if s != 0.0:
            G[PH, TH, PH] = G[PH, PH, TH] = co / s
        return G

    # --- null directions ----------------------------------------------------
    def null_slopes_ef_time(self, r: float) -> tuple[float, float]:
        """Radial null directions expressed as dr/dt_EF with t_EF = v - r.

        ingoing:   v = const  ->  dr/dt_EF = -1 (always)
        outgoing:  dr/dv = f/2 -> dr/dt_EF = f/(2 - f)
                   (= +1 far away, 0 on the horizon, -> -1 as r -> 0)
        """
        f = self.f(r)
        return (f / (2.0 - f), -1.0)

    def outgoing_drdv(self, r: float) -> float:
        return 0.5 * self.f(r)


@dataclass(frozen=True)
class Schwarzschild(StaticSphericalMetric):
    """Exact Schwarzschild solution, geometrized with G = c = 1 and mass M (default 1).

    EXACT GR RESULT: Schwarzschild 1916, Sitzungsber. Preuss. Akad. Wiss. 189.
    """

    name: str = "Schwarzschild"
    established: bool = True
    citation: str = "Schwarzschild (1916); MTW (1973) ch. 31; Wald (1984) ch. 6"
    M: float = 1.0

    @property
    def r_s(self) -> float:
        return 2.0 * self.M

    def f(self, r: float) -> float:
        return 1.0 - 2.0 * self.M / r

    def df(self, r: float) -> float:
        return 2.0 * self.M / (r * r)

    def d2f(self, r: float) -> float:
        return -4.0 * self.M / (r * r * r)

    # ---- Schwarzschild-coordinate quantities (regular only for r != 2M) ---
    def tortoise(self, r: float) -> float:
        """r_* = r + 2M ln|r/2M - 1|  (diverges to -inf at the horizon)."""
        x = r / (2.0 * self.M) - 1.0
        if x == 0.0:
            return -math.inf
        return r + 2.0 * self.M * math.log(abs(x))

    def schwarzschild_t(self, v: float, r: float) -> float:
        """Coordinate time t = v - r_*  (distant-observer bookkeeping; +inf at r = 2M)."""
        rs = self.tortoise(r)
        return v - rs if math.isfinite(rs) else math.inf

    def kruskal(self, v: float, r: float) -> dict:
        """Kruskal–Szekeres null coordinates (U, V) and (T, X) from ingoing EF (v, r).

        With V_K = exp(v/4M) and U_K = -(r/2M - 1) exp(r/2M) exp(-v/4M):
            T = (V_K + U_K)/2,  X = (V_K - U_K)/2,
            T^2 - X^2 = U_K V_K = (1 - r/2M) exp(r/2M)         (standard Kruskal relation)
        The map is smooth through r = 2M (U_K = 0 there).  Values that would
        overflow double precision (v/4M > ~700) are reported through the
        log-space fields and the compactified (Penrose-type) coordinates
        Ut = atan(U_K), Vt = atan(V_K), T~ = (Vt+Ut)/2, X~ = (Vt-Ut)/2.
        """
        M = self.M
        lnV = v / (4.0 * M)
        x = r / (2.0 * M) - 1.0
        # ln|U| = ln|x| + r/2M - v/4M ; sign(U) = -sign(x)
        if x == 0.0:
            lnU = -math.inf
            sgnU = 0.0
        else:
            lnU = math.log(abs(x)) + r / (2.0 * M) - lnV
            sgnU = -math.copysign(1.0, x)

        def _exp(a: float) -> float:
            return math.exp(a) if a < 700.0 else math.inf

        Vk = _exp(lnV)
        Uk = sgnU * _exp(lnU) if math.isfinite(lnU) else 0.0
        T = 0.5 * (Vk + Uk) if math.isfinite(Vk) and math.isfinite(Uk) else math.nan
        X = 0.5 * (Vk - Uk) if math.isfinite(Vk) and math.isfinite(Uk) else math.nan
        # compactified: atan(exp(a)) evaluated stably
        Vt = _atan_exp(lnV)
        Ut = sgnU * _atan_exp(lnU) if math.isfinite(lnU) else 0.0
        return {
            "U": Uk, "V": Vk, "T": T, "X": X,
            "lnV": lnV, "ln_abs_U": lnU, "sign_U": sgnU,
            "Ut": Ut, "Vt": Vt, "Tt": 0.5 * (Vt + Ut), "Xt": 0.5 * (Vt - Ut),
        }


def _atan_exp(a: float) -> float:
    """atan(exp(a)) without overflow: for large a, pi/2 - exp(-a)."""
    if a > 30.0:
        return 0.5 * math.pi - math.exp(-a)
    if a < -30.0:
        return math.exp(a)
    return math.atan(math.exp(a))
