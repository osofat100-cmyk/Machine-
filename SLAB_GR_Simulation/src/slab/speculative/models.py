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
from ..geodesic import rhs_lnr, initial_state_radial, IR, IV, ITAU, IUV, IUR, norm
from ..integrators import DormandPrince54
from ..curvature import kretschmann_closed_form
from ..trajectory import Simulation
from ..checkpoints import dumps
from . import BANNER, MENU_TITLE


@dataclass(frozen=True)
class Hayward(StaticSphericalMetric):
    """Hayward (2006) regular black hole.  f = 1 - 2 M r^2 / (r^3 + 2 M l^2).

    Source: S. A. Hayward, Phys. Rev. Lett. 96, 031103 (2006), eq. (2) with 2 M l^2 in the
    denominator (l a length of order the Planck length).  De Sitter core f ~ 1 - r^2/l^2.
    """
    name: str = "Hayward (2006) regular black hole"
    established: bool = False
    citation: str = "Hayward, Phys. Rev. Lett. 96, 031103 (2006)"
    M: float = 1.0
    ell: float = 1e-3

    def f(self, r):
        return 1.0 - 2.0 * self.M * r * r / (r**3 + 2.0 * self.M * self.ell**2)

    def df(self, r):
        D = r**3 + 2.0 * self.M * self.ell**2
        return -2.0 * self.M * (2.0 * r * D - 3.0 * r**4) / D**2

    def d2f(self, r):
        D = r**3 + 2.0 * self.M * self.ell**2
        Dp = 3.0 * r * r
        N = 2.0 * r * D - 3.0 * r**4
        Np = 2.0 * D + 2.0 * r * Dp - 12.0 * r**3
        return -2.0 * self.M * (Np * D - 2.0 * N * Dp) / D**3


@dataclass(frozen=True)
class Bardeen(StaticSphericalMetric):
    """Bardeen (1968) regular black hole.  f = 1 - 2 M r^2 / (r^2 + g^2)^{3/2}.

    Source: J. M. Bardeen, in Proc. GR5 (Tbilisi, 1968), p. 174; interpreted as a magnetic
    monopole in nonlinear electrodynamics by Ayón-Beato & García, Phys. Lett. B 493, 149 (2000).
    """
    name: str = "Bardeen (1968) regular black hole"
    established: bool = False
    citation: str = "Bardeen (1968) GR5 Tbilisi p.174; Ayón-Beato & García, Phys. Lett. B 493, 149 (2000)"
    M: float = 1.0
    g: float = 1e-3

    def f(self, r):
        return 1.0 - 2.0 * self.M * r * r / (r * r + self.g**2) ** 1.5

    def df(self, r):
        s = r * r + self.g**2
        # d/dr [ r^2 s^{-3/2} ] = 2 r s^{-3/2} - 3 r^3 s^{-5/2}
        return -2.0 * self.M * (2.0 * r * s**-1.5 - 3.0 * r**3 * s**-2.5)

    def d2f(self, r):
        s = r * r + self.g**2
        # d/dr [2 r s^{-3/2} - 3 r^3 s^{-5/2}] = 2 s^{-3/2} - 6 r^2 s^{-5/2} - 9 r^2 s^{-5/2} + 15 r^4 s^{-7/2}
        return -2.0 * self.M * (2.0 * s**-1.5 - 15.0 * r * r * s**-2.5 + 15.0 * r**4 * s**-3.5)


@dataclass(frozen=True)
class Dymnikova(StaticSphericalMetric):
    """Dymnikova (1992) 'G-lump' regular black hole.  f = 1 - (r_g/r)(1 - exp(-r^3/r_*^3)),
    r_g = 2M, r_*^3 = r_g r_0^2, with r_0 a de Sitter core scale (f ~ 1 - r^2/r_0^2 at the centre).

    Source: I. Dymnikova, Gen. Relativ. Gravit. 24, 235 (1992).
    """
    name: str = "Dymnikova (1992) regular black hole"
    established: bool = False
    citation: str = "Dymnikova, Gen. Relativ. Gravit. 24, 235 (1992)"
    M: float = 1.0
    r0: float = 1e-3

    @property
    def rstar3(self):
        return 2.0 * self.M * self.r0**2

    def _mass(self, r):
        return self.M * (1.0 - math.exp(-r**3 / self.rstar3))

    def f(self, r):
        return 1.0 - 2.0 * self._mass(r) / r

    def df(self, r):
        e = math.exp(-r**3 / self.rstar3)
        m = self.M * (1.0 - e)
        mp = self.M * e * 3.0 * r * r / self.rstar3
        return 2.0 * m / (r * r) - 2.0 * mp / r

    def d2f(self, r):
        e = math.exp(-r**3 / self.rstar3)
        m = self.M * (1.0 - e)
        mp = self.M * e * 3.0 * r * r / self.rstar3
        mpp = self.M * e * (6.0 * r / self.rstar3 - 9.0 * r**4 / self.rstar3**2)
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


def run_model(model: StaticSphericalMetric, sim: Simulation, r_stop_geo: float, rtol=1e-10) -> Dict:
    """Radial E = 1 infall in the toy metric from r = r_s(Schwarzschild) down to r_stop, ln r mode."""
    r_h = 2.0
    y0 = initial_state_radial(model, r_h, 1.0, 0.0)
    integ = DormandPrince54(rtol=rtol, atol=np.array([1e-12, 0, 1e-14, 1e-14, 0, 0, 1e-14, 1e-14, 1e-12]), max_step=0.02)

    def fun(x, y):
        return rhs_lnr(model, x, y)

    def resync(x, y):
        y = y.copy(); y[IR] = math.exp(x); return y

    res = integ.integrate(fun, math.log(r_h), y0, math.log(r_stop_geo), after_step=resync)
    r = np.exp(res.x)
    K = np.array([kretschmann_closed_form(model, ri) for ri in r])
    K_sch = 48.0 / r**6
    fvals = np.array([model.f(ri) for ri in r])
    f_sch = 1.0 - 2.0 / r
    u = sim.units
    dev = np.abs(fvals / f_sch - 1.0)
    idx_dev = int(np.argmax(dev > 1e-2)) if np.any(dev > 1e-2) else None
    # inner horizon: sign change of f inside
    inner = None
    sgn = np.sign(fvals)
    for i in range(1, len(sgn)):
        if sgn[i - 1] < 0 <= sgn[i]:
            inner = float(r[i]); break
    out = {
        "banner": BANNER,
        "model": model.name,
        "parameters": {k: getattr(model, k) for k in model.__dataclass_fields__ if k not in ("name", "established", "citation")},
        "parameter_note": "core length in units of GM/c^2; in metres multiply by M_m",
        "status": res.status,
        "n_steps": int(res.n_accepted),
        "max_norm_residual": float(np.max(np.abs([norm(model, yy) + 1 for yy in res.y]))),
        "r_geo": r.tolist(),
        "log10_r_over_rs": np.log10(r / 2.0).tolist(),
        "log10_K_SI": [u.log10_kretschmann_to_SI(math.log10(k)) if k > 0 else None for k in K],
        "log10_K_schwarzschild_SI": [u.log10_kretschmann_to_SI(math.log10(k)) for k in K_sch],
        "log10_K_over_Kplanck": [u.log10_kretschmann_to_SI(math.log10(k)) - math.log10(sim.dq.K_planck) if k > 0 else None for k in K],
        "f": fvals.tolist(),
        "tau_since_horizon_years": [u.t_to_years(t) for t in res.y[:, ITAU]],
        "u_r": res.y[:, IUR].tolist(),
        "K_max_log10_SI": float(np.max([u.log10_kretschmann_to_SI(math.log10(k)) for k in K if k > 0])),
        "r_1pct_deviation_from_schwarzschild_m": float(u.r_to_SI(r[idx_dev])) if idx_dev is not None else None,
        "inner_horizon_r_m": u.r_to_SI(inner) if inner is not None else None,
        "reaches_r0_in_finite_proper_time": "no (de Sitter core: r ~ exp(-tau/l), asymptotic approach)" if model.f(1e-12 * model.__dict__.get("ell", model.__dict__.get("g", model.__dict__.get("r0", 1e-3)))) > 0 else "unknown",
        "tau_horizon_to_stop_years": u.t_to_years(res.y[-1, ITAU]),
        "docs": MODEL_DOCS,
    }
    return out


def run_speculative_suite(sim: Simulation, out_dir: Path, core_length_over_M: float | None = None) -> Dict:
    """Run all toy models with the same core length (default: 1e4 l_P in geometrized units) and
    the Schwarzschild reference on the same grid.  Writes JSON to out_dir and returns the payload."""
    out_dir.mkdir(parents=True, exist_ok=True)
    lP = sim.dq.l_P_over_M
    ell = core_length_over_M if core_length_over_M is not None else 1e4 * lP
    r_stop = 1e-2 * ell
    results = {}
    for key, model in (("hayward", Hayward(ell=ell)), ("bardeen", Bardeen(g=ell)), ("dymnikova", Dymnikova(r0=ell))):
        try:
            results[key] = run_model(model, sim, r_stop)
        except Exception as e:  # pragma: no cover
            results[key] = {"banner": BANNER, "model": model.name, "error": repr(e)}
    payload = {
        "menu_title": MENU_TITLE,
        "banner": BANNER,
        "core_length_geo": ell,
        "core_length_m": sim.units.r_to_SI(ell),
        "core_length_in_planck_lengths": ell / lP,
        "r_stop_m": sim.units.r_to_SI(r_stop),
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
