"""Regular black-hole toy metrics in ingoing-EF form  ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2.

Each model documents: the exact f(r), its literature source, its
assumptions, where it differs from Schwarzschild, and its observational
status.  All are static, spherically symmetric, with areal radius r, so the
validated Schwarzschild machinery (EF geodesic equations, Kretschmann
closed form K = f''^2 + 4f'^2/r^2 + 4(1-f)^2/r^4, tidal tensor) applies
unchanged — only f(r) is replaced.

IMPORTANT: these are TOY MODELS.  The radial infall is integrated inward
through the inner (Cauchy) horizon of each model; the inner horizons of
regular black holes are believed to be unstable (mass inflation), which
these static toy metrics ignore entirely.

Verification status of citations: transcribed from the author's knowledge;
no network access in the build session — see references.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np

from ..metric import StaticSphericalMetric
from ..geodesic import rhs_first_integral_lnr, first_integral_velocity, IR, IV, ITAU, IUV, IUR, norm
from ..integrators import DormandPrince54
from ..curvature import kretschmann_closed_form
from ..trajectory import Simulation
from ..checkpoints import dumps
from . import BANNER, MENU_TITLE


# NOTE ON UNITS.  The toy models are integrated in units of their CORE LENGTH l (r -> r/l) with the
# dimensionless mass parameter mu = M/l (~1e52 for l = 1e4 Planck lengths and M = 1e18 M_sun).  In units of M
# the core scale l ~ 1e-52 makes powers such as (r^2 + g^2)^(-7/2) overflow double precision; in core units
# every quantity of interest is O(1) near the core and only harmless underflows occur far from it.
# The Schwarzschild horizon sits at r = 2 mu in these units.
@dataclass(frozen=True)
class Hayward(StaticSphericalMetric):
    """Hayward (2006) regular black hole.  f = 1 - 2 M r^2 / (r^3 + 2 M l^2)  ->  in core units (l = 1):
    f = 1 - 2 mu r^2 / (r^3 + 2 mu).

    Source: S. A. Hayward, Phys. Rev. Lett. 96, 031103 (2006), eq. (2) with 2 M l^2 in the
    denominator (l a length of order the Planck length).  De Sitter core f ~ 1 - r^2/l^2.
    """
    name: str = "Hayward (2006) regular black hole"
    established: bool = False
    citation: str = "Hayward, Phys. Rev. Lett. 96, 031103 (2006)"
    M: float = 1.0          # mass in core units (= mu = M/l)
    ell: float = 1.0        # core length in core units (kept for the formulas; = 1)

    # overflow-safe forms with q = r^3/D in [0, 1):  f' = -(2 mu r/D)(2 - 3q),  f'' = -(4 mu/D)(1 - 9q + 9q^2)
    def f(self, r):
        D = r**3 + 2.0 * self.M * self.ell**2
        return 1.0 - 2.0 * self.M * r * r / D

    def df(self, r):
        D = r**3 + 2.0 * self.M * self.ell**2
        q = r**3 / D
        return -(2.0 * self.M * r / D) * (2.0 - 3.0 * q)

    def d2f(self, r):
        D = r**3 + 2.0 * self.M * self.ell**2
        q = r**3 / D
        return -(4.0 * self.M / D) * (1.0 - 9.0 * q + 9.0 * q * q)


@dataclass(frozen=True)
class Bardeen(StaticSphericalMetric):
    """Bardeen (1968) regular black hole.  f = 1 - 2 M r^2 / (r^2 + g^2)^{3/2}.

    Source: J. M. Bardeen, in Proc. GR5 (Tbilisi, 1968), p. 174; interpreted as a magnetic
    monopole in nonlinear electrodynamics by Ayón-Beato & García, Phys. Lett. B 493, 149 (2000).
    """
    name: str = "Bardeen (1968) regular black hole"
    established: bool = False
    citation: str = "Bardeen (1968) GR5 Tbilisi p.174; Ayón-Beato & García, Phys. Lett. B 493, 149 (2000)"
    M: float = 1.0          # mass in core units (mu)
    g: float = 1.0          # core length in core units

    # overflow/underflow-safe forms with w = s^{-1/2}, p = r^2/s in [0, 1):
    #   f = 1 - 2 mu p w,  f' = -2 mu r w^3 (2 - 3p),  f'' = -2 mu w^3 (2 - 15p + 15p^2)
    def f(self, r):
        s = r * r + self.g**2
        return 1.0 - 2.0 * self.M * (r * r / s) / math.sqrt(s)

    def df(self, r):
        s = r * r + self.g**2
        w = 1.0 / math.sqrt(s)
        p = r * r / s
        return -2.0 * self.M * r * w * w * w * (2.0 - 3.0 * p)

    def d2f(self, r):
        s = r * r + self.g**2
        w = 1.0 / math.sqrt(s)
        p = r * r / s
        return -2.0 * self.M * w * w * w * (2.0 - 15.0 * p + 15.0 * p * p)


@dataclass(frozen=True)
class Dymnikova(StaticSphericalMetric):
    """Dymnikova (1992) 'G-lump' regular black hole.  f = 1 - (r_g/r)(1 - exp(-r^3/r_*^3)),
    r_g = 2M, r_*^3 = r_g r_0^2, with r_0 a de Sitter core scale (f ~ 1 - r^2/r_0^2 at the centre).

    Source: I. Dymnikova, Gen. Relativ. Gravit. 24, 235 (1992).
    """
    name: str = "Dymnikova (1992) regular black hole"
    established: bool = False
    citation: str = "Dymnikova, Gen. Relativ. Gravit. 24, 235 (1992)"
    M: float = 1.0          # mass in core units (mu)
    r0: float = 1.0         # core length in core units

    @property
    def rstar3(self):
        return 2.0 * self.M * self.r0**2

    def _q(self, r):
        """q = r^3 / r_*^3 in log space (r up to 2 mu ~ 1e52 in core units)."""
        lq = 3.0 * math.log(r) - math.log(self.rstar3)
        return math.exp(lq) if lq < 700.0 else math.inf

    def _mass_terms(self, r):
        """m = M (1 - e^-q) via expm1 (no cancellation for q << 1), m' = 3 e q M / r, m'' = 3 e q M (2 - 3q)/r^2."""
        q = self._q(r)
        if q > 700.0:
            return self.M, 0.0, 0.0
        e = math.exp(-q)
        m = -self.M * math.expm1(-q)
        mp = 3.0 * e * q * self.M / r
        mpp = 3.0 * e * q * self.M * (2.0 - 3.0 * q) / (r * r)
        return m, mp, mpp

    def f(self, r):
        m, _, _ = self._mass_terms(r)
        return 1.0 - 2.0 * m / r

    def df(self, r):
        m, mp, _ = self._mass_terms(r)
        return 2.0 * m / (r * r) - 2.0 * mp / r

    def d2f(self, r):
        m, mp, mpp = self._mass_terms(r)
        return -4.0 * m / r**3 + 4.0 * mp / (r * r) - 2.0 * mpp / r


MODEL_DOCS = {
    "hayward": {
        "metric": "ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2,  f = 1 - 2 M r^2/(r^3 + 2 M l^2)",
        "citation": "Hayward, S. A., Phys. Rev. Lett. 96, 031103 (2006)",
        "assumptions": "static, spherically symmetric, one free length l; matter content is an effective anisotropic fluid violating the strong energy condition in the core",
        "differs_from_GR": "f -> 1 - r^2/l^2 (de Sitter) as r -> 0 instead of -2M/r; curvature bounded, K_max ~ O(1/l^4); inner horizon near r ~ l",
        "observational_support": "NONE — l is unobservable for any astrophysical black hole (exterior indistinguishable from Schwarzschild)",
    },
    "bardeen": {
        "metric": "f = 1 - 2 M r^2/(r^2 + g^2)^{3/2}",
        "citation": "Bardeen (1968) GR5, Tbilisi; Ayón-Beato & García, Phys. Lett. B 493, 149 (2000)",
        "assumptions": "static, spherically symmetric; sourced by a nonlinear-electrodynamics magnetic monopole of charge g",
        "differs_from_GR": "de Sitter core, finite curvature; inner horizon",
        "observational_support": "NONE",
    },
    "dymnikova": {
        "metric": "f = 1 - (2M/r)(1 - exp(-r^3/(2 M r_0^2)))",
        "citation": "Dymnikova, I., Gen. Relativ. Gravit. 24, 235 (1992)",
        "assumptions": "static, spherically symmetric; vacuum-like anisotropic fluid with p_r = -rho",
        "differs_from_GR": "de Sitter core with density rho_0 = 3/(8 pi r_0^2); exterior deviation exponentially small",
        "observational_support": "NONE",
    },
}


def run_model(model: StaticSphericalMetric, sim: Simulation, r_stop_core: float, ell_m: float, rtol=1e-10) -> Dict:
    """Radial E = 1 infall in the toy metric from the Schwarzschild horizon r = 2 mu down to r_stop (core units),
    ln r mode.  ell_m = core length in metres (unit conversion)."""
    mu = model.M
    r_h = 2.0 * mu
    # FIRST-INTEGRAL formulation (E, L exact; u^v, u^r reconstructed algebraically at every step).
    # The second-order geodesic equation for u^v is exponentially UNSTABLE when integrated inward through a
    # de Sitter-like core (f' < 0 there flips the sign of the Riccati term -(f'/2)(u^v)^2): perturbations grow
    # by ~e per e-fold of r, i.e. by ~1e17 across the core region of these models.  The first-integral form has
    # no such mode and is exact for geodesics.  (In Schwarzschild the same mode decays, which is why the
    # validated run uses the second-order form and cross-checks it against this one in TEST 8.)
    y0 = np.array([0.0, r_h, math.pi / 2, 0.0, 1.0, 0.0, 0.0])          # [v_seg, r, theta, phi, E, L, tau_seg]
    integ = DormandPrince54(rtol=rtol, atol=np.array([0.0, 0, 1e-14, 1e-14, 1e-14, 1e-14, 0.0]), max_step=0.02)

    def fun(x, y):
        return rhs_first_integral_lnr(model, x, y)

    res = integ.integrate(fun, math.log(r_h), y0, math.log(r_stop_core))
    r = np.exp(res.x)                                   # core units
    vel = np.array([first_integral_velocity(model, ri, 1.0, 0.0) for ri in r])   # (u^v, u^r, u^phi)
    with np.errstate(all="ignore"):
        K = np.array([kretschmann_closed_form(model, ri) for ri in r])       # per l^4
    log10_K_sch = math.log10(48.0) + 2.0 * math.log10(mu) - 6.0 * np.log10(r)   # log space: r^6 overflows
    fvals = np.array([model.f(ri) for ri in r])
    f_sch = 1.0 - 2.0 * mu / r
    from ..constants import c as _c, YEAR as _YEAR
    log10_l4 = 4.0 * math.log10(ell_m)
    to_SI_logK = None
    to_SI_logK = lambda k: (math.log10(k) - log10_l4) if (k is not None and k > 0 and math.isfinite(k)) else None
    to_years = lambda t: t * ell_m / _c / _YEAR
    dev = np.abs(fvals / f_sch - 1.0)
    idx_dev = int(np.argmax(dev > 1e-2)) if np.any(dev > 1e-2) else None
    # inner horizon: sign change of f inside
    inner = None
    sgn = np.sign(fvals)
    for i in range(1, len(sgn)):
        if sgn[i - 1] < 0 <= sgn[i]:
            inner = float(r[i]); break
    logK_SI = [to_SI_logK(k) for k in K]
    logK_sch_SI = [float(v - log10_l4) for v in log10_K_sch]
    out = {
        "banner": BANNER,
        "model": model.name,
        "parameters": {"mu = M / l": mu, "core_length_m": ell_m},
        "parameter_note": "integrated in units of the core length l; mu = M/l",
        "status": res.status,
        "n_steps": int(res.n_accepted),
        "formulation": "first integrals (E = 1, L = 0), ln r independent variable; see comment in run_model",
        "max_E_drift": float(np.max(np.abs(res.y[:, 4] - 1.0))),
        "r_geo": (r / mu).tolist(),                                     # in units of GM/c^2 for compatibility
        "log10_r_over_rs": np.log10(r / (2.0 * mu)).tolist(),
        "log10_K_SI": logK_SI,
        "log10_K_schwarzschild_SI": logK_sch_SI,
        "log10_K_over_Kplanck": [(v - math.log10(sim.dq.K_planck)) if v is not None else None for v in logK_SI],
        "f": fvals.tolist(),
        "tau_since_horizon_years": [to_years(t) for t in res.y[:, 6]],
        "u_r": vel[:, 1].tolist(),
        "K_max_log10_SI": float(max(v for v in logK_SI if v is not None)),
        "r_1pct_deviation_from_schwarzschild_m": float(r[idx_dev] * ell_m) if idx_dev is not None else None,
        "inner_horizon_r_m": inner * ell_m if inner is not None else None,
        "reaches_r0_in_finite_proper_time": "no (de Sitter core: r ~ exp(-tau/l), asymptotic approach)" if model.f(1e-6) > 0 else "unknown",
        "tau_horizon_to_stop_years": to_years(res.y[-1, 6]),
        "docs": MODEL_DOCS,
    }
    return out


def run_speculative_suite(sim: Simulation, out_dir: Path, core_length_over_M: float | None = None) -> Dict:
    """Run all toy models with the same core length (default: 1e4 l_P in geometrized units) and
    the Schwarzschild reference on the same grid.  Writes JSON to out_dir and returns the payload."""
    out_dir.mkdir(parents=True, exist_ok=True)
    lP = sim.dq.l_P_over_M
    ell = core_length_over_M if core_length_over_M is not None else 1e4 * lP    # in units of GM/c^2
    ell_m = sim.units.r_to_SI(ell)
    mu = 1.0 / ell                                                                # M / l
    r_stop = 1e-2                                                                 # core units
    results = {}
    # Bardeen's charge g is NOT its core scale: near the centre f ~ 1 - 2 M r^2/g^3, i.e. a de Sitter radius
    # sqrt(g^3/2M).  Choosing g = (2 mu)^(1/3) (core units) gives all three models the same de Sitter core radius l.
    for key, model in (("hayward", Hayward(M=mu)), ("bardeen", Bardeen(M=mu, g=(2.0 * mu) ** (1.0 / 3.0))), ("dymnikova", Dymnikova(M=mu))):
        try:
            results[key] = run_model(model, sim, r_stop, ell_m)
        except Exception as e:  # pragma: no cover
            results[key] = {"banner": BANNER, "model": model.name, "error": repr(e)}
    payload = {
        "menu_title": MENU_TITLE,
        "banner": BANNER,
        "core_length_geo": ell,
        "core_length_m": ell_m,
        "core_length_in_planck_lengths": ell / lP,
        "r_stop_m": r_stop * ell_m,
        "note": ("Each toy model is integrated with the SAME validated EF geodesic engine, only f(r) differs. "
                 "The choice of core length is arbitrary (1e4 Planck lengths here) and has NO observational basis. "
                 "Inner-horizon instabilities (mass inflation) are ignored. These curves must never be read as predictions."),
        "models": results,
        "schwarzschild_reference": {
            "K_at_rQG_log10_SI": math.log10(sim.dq.K_planck),
            "tau_horizon_to_center_years": sim.dq.tau_horizon_to_singularity_years,
        },
    }
    (out_dir / "speculative_models.json").write_text(dumps(payload))
    # CSV per model
    for key, res in results.items():
        if "r_geo" not in res:
            continue
        with open(out_dir / f"{key}_radial_infall.csv", "w") as fh:
            fh.write(f"# {MENU_TITLE}\n# {BANNER}\n# model: {res['model']}\n")
            fh.write("r_geo,log10_r_over_rs,f,log10_K_SI,log10_K_schwarzschild_SI,tau_since_horizon_years,u_r\n")
            for i in range(len(res["r_geo"])):
                fh.write(f"{res['r_geo'][i]!r},{res['log10_r_over_rs'][i]!r},{res['f'][i]!r},{res['log10_K_SI'][i]!r},"
                         f"{res['log10_K_schwarzschild_SI'][i]!r},{res['tau_since_horizon_years'][i]!r},{res['u_r'][i]!r}\n")
    return payload
