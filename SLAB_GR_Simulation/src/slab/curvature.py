"""Curvature of the ingoing-EF static spherical metric.

Riemann tensor (fully covariant, coordinate basis (v, r, theta, phi)) for
ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2.  Independent nonzero components
(derived by hand from the Schwarzschild-coordinate tensor under
t = v - r_*; re-derived symbolically in tools/derive_ef_curvature.py):

    R_{vrvr}       = f''/2
    R_{v th v th}  = r f f'/2                R_{v ph v ph} = r f f'/2 sin^2
    R_{v th r th}  = -r f'/2                 R_{v ph r ph} = -r f'/2 sin^2
    R_{r th r th}  = 0                       R_{r ph r ph} = 0
    R_{th ph th ph}= r^2 (1 - f) sin^2

For Schwarzschild (f = 1 - 2M/r) these are -2M/r^3, M f/r, -M/r, 0, 2 M r sin^2:
all finite at r = 2M (horizon regularity of the curvature description).

Kretschmann scalar K = R_abcd R^abcd.  For a general f(r):
    K = f''^2 + 4 f'^2/r^2 + 4 (1-f)^2/r^4     (EXACT)
which for Schwarzschild is 48 M^2 / r^6.  The validation suite computes K
BOTH from the closed form AND by explicit index contraction of the
components above (numpy einsum) and compares them.

Tidal tensor: E_{mu nu} = R_{mu alpha nu beta} u^alpha u^beta projected on
an orthonormal comoving tetrad gives the 3x3 symmetric matrix E_ij whose
eigenvalues lambda_i give the geodesic-deviation (tidal) accelerations
    D^2 xi^i / dtau^2 = - E_ij xi^j
(MTW §31.2, eq. 31.6; Wald §3.3).  For radial motion in Schwarzschild the
eigenvalues are (-2M/r^3, +M/r^3, +M/r^3): radial stretching 2M L/r^3 and
transverse compression M L/r^3 for a body of proper length L.  This holds
for ANY radial 4-velocity because the Schwarzschild Riemann tensor is
invariant under boosts in the (t, r) plane.
"""
from __future__ import annotations

import math

import numpy as np

from .metric import StaticSphericalMetric, V, R, TH, PH


def riemann_lower(metric: StaticSphericalMetric, r: float, theta: float) -> np.ndarray:
    """Fully covariant Riemann tensor R[a, b, c, d] in the EF coordinate basis."""
    f = metric.f(r)
    fp = metric.df(r)
    fpp = metric.d2f(r)
    s2 = math.sin(theta) ** 2
    Rm = np.zeros((4, 4, 4, 4))

    def put(a, b, c, d, val):
        # impose R_abcd = -R_bacd = -R_abdc = R_cdab
        for (i, j, k, l, sgn) in ((a, b, c, d, 1), (b, a, c, d, -1), (a, b, d, c, -1), (b, a, d, c, 1),
                                  (c, d, a, b, 1), (d, c, a, b, -1), (c, d, b, a, -1), (d, c, b, a, 1)):
            Rm[i, j, k, l] = sgn * val

    put(V, R, V, R, 0.5 * fpp)
    put(V, TH, V, TH, 0.5 * r * f * fp)
    put(V, PH, V, PH, 0.5 * r * f * fp * s2)
    put(V, TH, R, TH, -0.5 * r * fp)
    put(V, PH, R, PH, -0.5 * r * fp * s2)
    put(TH, PH, TH, PH, r * r * (1.0 - f) * s2)
    # R_{r th r th} = R_{r ph r ph} = 0 exactly
    return Rm


def kretschmann_closed_form(metric: StaticSphericalMetric, r: float) -> float:
    """K = f''^2 + 4 f'^2/r^2 + 4(1-f)^2/r^4  (exact for any f(r))."""
    f, fp, fpp = metric.f(r), metric.df(r), metric.d2f(r)
    return fpp * fpp + 4.0 * fp * fp / (r * r) + 4.0 * (1.0 - f) ** 2 / r**4


def kretschmann_schwarzschild(M: float, r: float) -> float:
    """K = 48 M^2 / r^6 (geometrized).  EXACT GR RESULT."""
    return 48.0 * M * M / r**6


def log10_kretschmann_schwarzschild(M: float, r: float) -> float:
    return math.log10(48.0) + 2.0 * math.log10(M) - 6.0 * math.log10(r)


def kretschmann_by_contraction(metric: StaticSphericalMetric, r: float, theta: float = math.pi / 2) -> float:
    """K = R_abcd R^abcd computed by explicit index raising with g^{-1} (numerical check)."""
    Rl = riemann_lower(metric, r, theta)
    gi = metric.g_upper(r, theta)
    Ru = np.einsum("ae,bf,cg,dh,efgh->abcd", gi, gi, gi, gi, Rl)
    return float(np.einsum("abcd,abcd->", Rl, Ru))


def comoving_tetrad(metric: StaticSphericalMetric, r: float, theta: float, u: np.ndarray) -> np.ndarray:
    """Orthonormal tetrad e[A] (A = 0..3) with e[0] = u, built by Gram–Schmidt on
    (u, d_r, d_theta, d_phi) with the Lorentzian metric.  e[1] is the observer's
    local 'radial' spatial direction (outward for exterior observers)."""
    basis = [np.array(u, dtype=float)]
    for k in (R, TH, PH):
        w = np.zeros(4)
        w[k] = 1.0
        for e in basis:
            ee = metric.dot(r, theta, e, e)
            w = w - (metric.dot(r, theta, w, e) / ee) * e
        nrm = metric.dot(r, theta, w, w)
        basis.append(w / math.sqrt(abs(nrm)))
    return np.array(basis)


def comoving_tetrad_conditioned(metric: StaticSphericalMetric, r: float, theta: float, u: np.ndarray, E: float) -> np.ndarray:
    """Well-conditioned comoving tetrad.  The radial spatial direction is built from the
    Killing energy E supplied as an independent number, n = (u^v, E, 0, 0)/|n|, which avoids
    the cancellation 1 + u^v u^r -> 0 that ruins the Gram–Schmidt construction for r << M.
    The angular directions are obtained by Gram–Schmidt against u and n (no cancellation)."""
    u = np.asarray(u, dtype=float)
    n = np.array([u[V], E, 0.0, 0.0])
    n = n / math.sqrt(abs(metric.dot(r, theta, n, n)))
    basis = [u, n]
    for k in (TH, PH):
        w = np.zeros(4); w[k] = 1.0
        for e in basis:
            ee = metric.dot(r, theta, e, e)
            w = w - (metric.dot(r, theta, w, e) / ee) * e
        basis.append(w / math.sqrt(abs(metric.dot(r, theta, w, w))))
    return np.array(basis)


def radial_unit_vector_closed_form(metric: StaticSphericalMetric, r: float, u: np.ndarray) -> np.ndarray:
    """For radial motion the outward spatial unit vector orthogonal to u is
    n = (u^v, E, 0, 0) with E = f u^v - u^r  (see physics_notes.md §5)."""
    E = metric.f(r) * u[V] - u[R]
    return np.array([u[V], E, 0.0, 0.0])


def tidal_tensor(metric: StaticSphericalMetric, r: float, theta: float, u: np.ndarray, E: float | None = None) -> dict:
    """Tidal (electric Weyl) tensor in the comoving orthonormal frame.

    If the Killing energy E is supplied the well-conditioned tetrad is used (required for
    r << M); otherwise plain Gram–Schmidt (fine outside and near the horizon).
    Returns E_ij (3x3), its eigenvalues (ascending) and eigenvectors, and the tetrad.
    """
    Rl = riemann_lower(metric, r, theta)
    tet = comoving_tetrad_conditioned(metric, r, theta, u, E) if E is not None else comoving_tetrad(metric, r, theta, u)
    # E_{mu nu} = R_{mu alpha nu beta} u^alpha u^beta
    Emn = np.einsum("manb,a,b->mn", Rl, u, u)
    Eij = np.einsum("im,jn,mn->ij", tet[1:], tet[1:], Emn)
    Eij = 0.5 * (Eij + Eij.T)
    w, vecs = np.linalg.eigh(Eij)
    return {"E_ij": Eij, "eigenvalues": w, "eigenvectors": vecs, "tetrad": tet}


def reference_radial_frame(metric: StaticSphericalMetric, r: float) -> tuple[np.ndarray, np.ndarray]:
    """Orthonormal radial frame that exists for all r > 0: the 4-velocity u_ref of the E = 1 radial
    infaller and its outward radial unit vector n_ref = (u_ref^v, 1, 0, 0)."""
    f = metric.f(r)
    ur = -math.sqrt(max(1.0 - f, 0.0))
    uv = 1.0 / (1.0 - ur)                      # = 1/(1 + sqrt(1-f)); regular at f = 0
    return np.array([uv, ur, 0.0, 0.0]), np.array([uv, 1.0, 0.0, 0.0])


def tidal_eigenvalues_frame(metric: StaticSphericalMetric, r: float, theta: float, u: np.ndarray) -> np.ndarray:
    """Tidal eigenvalues for an ARBITRARY 4-velocity without catastrophic cancellation.

    The curvature 2-form of any metric ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2 is diagonal in
    the bivector basis of every radially boosted orthonormal frame (0 = radial observer,
    1 = radial, 2 = theta, 3 = phi), with
        R_0101 = f''/2 = A,   R_0202 = R_0303 = f'/(2r) = B,   R_2323 = (1-f)/r^2 = C,
        R_1212 = R_1313 = -f'/(2r) = D = -B      (boost invariance in the (0,1) plane <=> D = -B).
    With the observer's frame components u_hat = (g, p, q, s) in the frame of the reference
    E = 1 radial infaller (which exists for all r > 0), E_ab = R_acbd u^c u^d reads
        E_00 = A p^2 + B (q^2 + s^2)        E_11 = A g^2 + D (q^2 + s^2)
        E_22 = B g^2 + D p^2 + C s^2        E_33 = B g^2 + D p^2 + C q^2
        E_01 = -A p g   E_02 = -B q g   E_03 = -B s g   E_12 = -D p q   E_13 = -D p s   E_23 = -C q s
    and the eigenvalues of E^a_b = eta^{ac} E_cb are {0, lambda_1, lambda_2, lambda_3}.
    For Schwarzschild A = -2M/r^3, B = M/r^3, C = 2M/r^3, D = -M/r^3.  The matrix is scaled
    to O(1) before the eigenvalue solve (entries reach 1e186 for L != 0 at r_QG).
    """
    f, fp, fpp = metric.f(r), metric.df(r), metric.d2f(r)
    A, B, C = 0.5 * fpp, 0.5 * fp / r, (1.0 - f) / (r * r)
    D = -B
    u_ref, n_ref = reference_radial_frame(metric, r)
    p = metric.dot(r, theta, u, n_ref)
    q = r * u[TH]
    s_ = r * math.sin(theta) * u[PH]
    # g = -g(u, u_ref) analytically equals sqrt(1 + p^2 + q^2 + s^2); use the latter so that the
    # 4-velocity is exactly on the mass shell (otherwise the null eigenvalue E u = 0 leaks into the
    # smallest tidal eigenvalue when |u| ~ 1e3 and g(u,u) = -1 holds only to ~1e-9 absolute)
    g = math.sqrt(1.0 + p * p + q * q + s_ * s_)
    E = np.array([
        [A * p * p + B * (q * q + s_ * s_), -A * p * g, -B * q * g, -B * s_ * g],
        [-A * p * g, A * g * g + D * (q * q + s_ * s_), -D * p * q, -D * p * s_],
        [-B * q * g, -D * p * q, B * g * g + D * p * p + C * s_ * s_, -C * q * s_],
        [-B * s_ * g, -D * p * s_, -C * q * s_, B * g * g + D * p * p + C * q * q],
    ])
    scale = float(np.max(np.abs(E)))
    if scale == 0.0 or not math.isfinite(scale):
        return np.full(3, np.nan)
    eta = np.diag([-1.0, 1.0, 1.0, 1.0])
    w = np.linalg.eigvals(eta @ (E / scale)).real
    w = np.sort(w)
    i0 = int(np.argmin(np.abs(w)))       # E u = 0: discard the null eigenvalue
    return np.delete(w, i0) * scale


def tidal_eigenvalues_radial_closed_form(M: float, r: float) -> tuple[float, float, float]:
    """(-2M/r^3, M/r^3, M/r^3): exact for any radially moving observer in Schwarzschild."""
    return (-2.0 * M / r**3, M / r**3, M / r**3)
