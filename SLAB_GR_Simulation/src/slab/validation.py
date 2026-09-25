"""Automated physics validation suite (TESTS 0–10).

TEST 9 (accelerated observer's frame) and TEST 10 (distant-observer signal timeline) and the
high-precision-reference part of TEST 8 were added in the engine upgrade (docs/additions/engine.md).

The main simulation is only marked 'validated' if every test passes.  Each
test records the equation being checked, the numbers obtained, the
tolerance, the pass/fail verdict and the literature reference.
"""
from __future__ import annotations

import datetime as _dt
import math
import time
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import constants as C
from .constants import DerivedQuantities, BRIEF_EXPECTATIONS
from .units import Units
from .metric import Schwarzschild, V, R, TH, PH
from .curvature import (riemann_lower, kretschmann_by_contraction, kretschmann_closed_form, kretschmann_schwarzschild,
                        tidal_tensor, tidal_eigenvalues_frame, tidal_eigenvalues_radial_closed_form, comoving_tetrad,
                        radial_unit_vector_closed_form)
from .geodesic import (rhs_tau, rhs_lnr, rhs_first_integral_lnr, initial_state_radial, RadialInfallE1, energy, norm,
                       IR, IV, ITAU, IUV, IUR, IEK, IE, IL)
from .integrators import DormandPrince54, integrate_scipy_dop853
from .trajectory import Simulation, SimulationConfig
from .accelerated import (rindler_flat_check, hovering_check, thrust_energy_closed_form, crossover_radius_geo,
                          inertial_diff_along_thrust_SI)
from .signals import compute_signal_timeline, one_plus_z_E1_closed_form, late_time_slopes
from .reference import thrust_radial_reference, plunge_reference, e1_reference_check


def _rel(a: float, b: float) -> float:
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


class Test:
    def __init__(self, tid: str, name: str, equation: str, reference: str):
        self.d = {"id": tid, "name": name, "equation": equation, "reference": reference, "checks": [], "passed": True}

    def check(self, label: str, value, expected=None, tol=None, kind="rel", note: str = ""):
        ok = True
        err = None
        if expected is not None and tol is not None:
            err = _rel(value, expected) if kind == "rel" else abs(value - expected)
            ok = bool(err <= tol)
        elif tol is not None:
            err = abs(value)
            ok = bool(err <= tol)
        self.d["checks"].append({"label": label, "value": value, "expected": expected, "error": err, "tolerance": tol,
                                 "error_kind": kind, "passed": ok, "note": note})
        self.d["passed"] = self.d["passed"] and ok
        return ok

    def finite(self, label: str, arr, note: str = ""):
        a = np.asarray(arr, dtype=float)
        ok = bool(np.all(np.isfinite(a)))
        self.d["checks"].append({"label": label, "value": float(np.max(np.abs(a))) if ok else "non-finite", "expected": "finite",
                                 "error": None, "tolerance": None, "error_kind": "finite", "passed": ok, "note": note})
        self.d["passed"] = self.d["passed"] and ok
        return ok


# ---------------------------------------------------------------------------
def test0_constants(dq: DerivedQuantities) -> dict:
    t = Test("TEST 0", "Constant provenance and internal consistency",
             "l_P = sqrt(hbar G / c^3);  M = 1e18 M_sun", "CODATA 2022 (Mohr, Newell, Taylor & Tiesinga, Rev. Mod. Phys. 97, 025002 (2025)); G and l_P unchanged from CODATA 2018")
    t.check("l_P (CODATA) vs sqrt(hbar G/c^3)", dq.l_P_from_hbar_G_c, C.l_P, 1e-6, note="internal consistency of the CODATA constants")
    t.check("M [kg] vs brief 1.98847e48", dq.M_kg, BRIEF_EXPECTATIONS["M_kg"], 1e-5)
    return t.d


def test1_schwarzschild_radius(dq: DerivedQuantities) -> dict:
    t = Test("TEST 1", "Schwarzschild radius", "r_s = 2GM/c^2 ; GM/c^3", "Schwarzschild 1916; MTW §31.2")
    r_s = 2.0 * C.G * dq.M_kg / C.c**2
    t.check("r_s [m] recomputed inline vs DerivedQuantities", r_s, dq.r_s_m, 1e-15)
    t.check("r_s [m] vs brief 2.95334e21", dq.r_s_m, BRIEF_EXPECTATIONS["r_s_m"], 1e-5)
    t.check("r_s [ly] vs brief 312,168", dq.r_s_ly, BRIEF_EXPECTATIONS["r_s_ly"], 1e-5, note="Julian light-year 9.4607304725808e15 m")
    t.check("GM/c^3 [yr] vs brief 156,084", dq.GM_over_c3_years, BRIEF_EXPECTATIONS["GM_over_c3_years"], 1e-5, note="Julian year")
    return t.d


def test2_horizon_regularity(sim: Simulation) -> dict:
    t = Test("TEST 2", "Horizon regularity of the integration coordinates (ingoing Eddington–Finkelstein)",
             "ds^2 = -f dv^2 + 2 dv dr + r^2 dOmega^2, f = 1 - 2M/r ; all metric, Christoffel, Riemann and RHS quantities finite at r = 2M",
             "Eddington 1924; Finkelstein 1958; MTW Box 31.2; Wald §6.4")
    m = sim.metric
    r_h = 2.0
    th = math.pi / 2
    t.finite("metric g_ab at r = 2M", m.g_lower(r_h, th))
    t.finite("inverse metric g^ab at r = 2M", m.g_upper(r_h, th))
    t.finite("Christoffel symbols at r = 2M", m.christoffel(r_h, th))
    t.finite("Riemann tensor R_abcd at r = 2M", riemann_lower(m, r_h, th))
    ref = RadialInfallE1()
    y_h = np.array([0.0, r_h, th, 0.0, ref.uv(r_h), ref.ur(r_h), 0.0, 0.0, 0.0, 1.0])
    t.finite("geodesic RHS dy/dtau at r = 2M", rhs_tau(m, y_h))
    t.finite("geodesic RHS dy/dlnr at r = 2M", rhs_lnr(m, math.log(r_h), y_h))
    # smoothness across the horizon: RHS difference between r = 2M(1 +/- eps) is O(eps)
    eps = 1e-6
    ya = y_h.copy(); ya[IR] = r_h * (1 + eps); ya[IUV], ya[IUR] = ref.uv(ya[IR]), ref.ur(ya[IR])
    yb = y_h.copy(); yb[IR] = r_h * (1 - eps); yb[IUV], yb[IUR] = ref.uv(yb[IR]), ref.ur(yb[IR])
    da, db = rhs_tau(m, ya), rhs_tau(m, yb)
    t.check("|RHS(2M(1+eps)) - RHS(2M(1-eps))|_max, eps=1e-6", float(np.max(np.abs(da - db))), None, 1e-4, kind="abs",
            note="continuity of the equations of motion through the horizon")
    # Kruskal coordinates at the horizon
    kr = m.kruskal(0.0, r_h)
    t.check("Kruskal U at horizon", kr["U"], 0.0, 1e-300, kind="abs")
    t.finite("Kruskal (T, X) at horizon", [kr["T"], kr["X"]])
    # the trajectory's horizon step: analytic values u^v = 1/2, u^r = -1 at r = 2M for E = 1
    ms = sim.milestone_states.get("horizon")
    if ms is not None:
        t.check("u^v at horizon (numerical) vs 1/2", ms["u_v"], 0.5, 1e-9)
        t.check("u^r at horizon (numerical) vs -1", ms["u_r"], -1.0, 1e-9)
    for which, seg in (("ending on", next((s for s in sim.segments if s.slug_to == "horizon"), None)),
                       ("starting on", next((s for s in sim.segments if s.slug_from == "horizon"), None))):
        if seg is None:
            continue
        rej = seg.n_rejected
        interior_rej = int(rej[2:].sum())   # rejections after the first step (index 1 = first step of the segment)
        t.check(f"rejected steps in the segment {which} the horizon, excluding the segment's first step", interior_rej, 0, 0, kind="abs",
                note=f"total rejections {int(rej.sum())} (first-step rejections are a segment-restart artefact of the carried-over step size)")
        t.check(f"step-size ratio min/max in the segment {which} the horizon (no collapse)", float(seg.h[1:].min() / seg.h[1:].max()), None, None, kind="abs",
                note="informational; must stay well above ~1e-3")
        t.check(f"no step-size collapse {which} the horizon: min step > 1e-3 x max step", 1e-3 * float(seg.h[1:].max()) / float(seg.h[1:].min()), None, 1.0, kind="abs")
        t.check(f"max normalized error estimate in the segment {which} the horizon", float(seg.err.max()), None, 1.0, kind="abs")
    return t.d


def test3_radial_geodesic(sim: Simulation) -> dict:
    t = Test("TEST 3", "Radial E = 1 geodesic vs analytic solution",
             "dr/dtau = -c sqrt(r_s/r) ;  u^v = x/(1+x), x = sqrt(r/2M) ; v(r) = -4M[x^3/3 - x^2/2 + x - ln(1+x)] + C",
             "Taylor & Wheeler, Exploring Black Holes (2000) ch. 3; MTW (1973) ch. 25 and ch. 31 (section numbers from memory — INSUFFICIENT DATA TO VERIFY)")
    cols = sim.columns
    t.check("max |u^r/u^r_analytic - 1| over all steps", float(np.nanmax(np.abs(cols["ur_reldiff_E1"]))), None, 1e-9, kind="abs")
    t.check("max |u^v/u^v_analytic - 1| over all steps", float(np.nanmax(np.abs(cols["uv_reldiff_E1"]))), None, 1e-9, kind="abs")
    ref = RadialInfallE1()
    # v increments per milestone vs analytic
    worst = 0.0
    worst_tau = 0.0
    ms = sim.milestone_states
    mls = sim.milestones
    table = []
    for a, b in zip(mls[:-1], mls[1:]):
        dv_num = ms[b.slug]["dv_segment_geo"]
        dv_an = ref.v_between(a.r_geo, b.r_geo)
        dt_num = ms[b.slug]["dtau_segment_geo"]
        dt_an = ref.tau_between(a.r_geo, b.r_geo)
        table.append({"from": a.slug, "to": b.slug, "dv_numeric": dv_num, "dv_analytic": dv_an, "rel_err_dv": _rel(dv_num, dv_an),
                      "dtau_numeric": dt_num, "dtau_analytic": dt_an, "rel_err_dtau": _rel(dt_num, dt_an)})
        worst = max(worst, _rel(dv_num, dv_an))
        worst_tau = max(worst_tau, _rel(dt_num, dt_an))
    t.d["segment_table"] = table
    t.check("max relative error of Delta v per milestone segment (vs series-evaluated analytic v(r))", worst, None, 1e-9, kind="abs")
    t.check("max relative error of Delta tau per milestone segment", worst_tau, None, 1e-9, kind="abs")
    return t.d


def test4_proper_time_benchmark(sim: Simulation) -> dict:
    t = Test("TEST 4", "Horizon-to-singularity proper-time benchmark",
             "tau(r_s -> 0) = (2/3) r_s/c = 4GM/(3c^3) for E = 1 radial free fall",
             "MTW §25.5 eq. (25.38) (cycloid solution); Taylor & Wheeler 'Exploring Black Holes' (2000) ch. 3")
    ms = sim.milestone_states
    ref = RadialInfallE1()
    r_qg = sim.milestones[-1].r_geo
    dtau_num = ms["r_QG"]["tau_total_geo"] - ms["horizon"]["tau_total_geo"]
    dtau_an = ref.tau_between(2.0, r_qg)
    t.check("tau(horizon -> r_QG) numeric [GM/c^3]", dtau_num, dtau_an, 1e-9,
            note=f"analytic 4M/3 (1 - (r_QG/2M)^(3/2)); the missing tail (r_QG -> 0) is {ref.tau_to_center(r_qg):.3e} GM/c^3")
    yrs = sim.units.t_to_years(dtau_num)
    t.check("tau(horizon -> r_QG) [yr] vs 4GM/(3c^3) in years", yrs, sim.dq.tau_horizon_to_singularity_years, 1e-9)
    t.check("4GM/(3c^3) [yr] vs brief 208,112", sim.dq.tau_horizon_to_singularity_years, BRIEF_EXPECTATIONS["tau_horizon_to_singularity_years"], 1e-5)
    # also from r0
    dtau_tot = ms["r_QG"]["tau_total_geo"]
    t.check("tau(r0 -> r_QG) numeric vs analytic", dtau_tot, ref.tau_between(sim.milestones[0].r_geo, r_qg), 1e-9)
    return t.d


def test5_kretschmann(sim: Simulation) -> dict:
    t = Test("TEST 5", "Kretschmann scalar", "K = R_abcd R^abcd = 48 G^2 M^2/(c^4 r^6)  (contraction of the EF Riemann tensor vs closed form)",
             "Henry 2000, ApJ 535, 350, doi:10.1086/308819")
    m, u, dq = sim.metric, sim.units, sim.dq
    worst = 0.0
    for r in [100.0, 10.0, 3.0, 2.0, 1.0, 0.1, 1e-3, 1e-10, 1e-20, sim.milestones[-1].r_geo]:
        Kc = kretschmann_by_contraction(m, r)
        Kf = kretschmann_schwarzschild(1.0, r)
        worst = max(worst, _rel(Kc, Kf))
    t.check("max rel diff: einsum contraction vs 48M^2/r^6 over r in {100..r_QG} incl. r = 2M", worst, None, 1e-12, kind="abs")
    r_m = dq.r_s_m
    K_SI = 48.0 * C.G**2 * dq.M_kg**2 / (C.c**4 * r_m**6)
    t.check("SI conversion at r = r_s: 48G^2M^2/(c^4 r^6) vs geometrized/M_m^4", u.kretschmann_to_SI(kretschmann_schwarzschild(1.0, 2.0)), K_SI, 1e-12)
    t.check("log10 K at r_s [m^-4]", math.log10(K_SI), None, None, kind="abs", note="informational")
    # tidal eigenvalues in the comoving frame vs closed form, incl. inside
    worst_t = 0.0
    ref = RadialInfallE1()
    for r in [10.0, 2.0, 0.5, 1e-5, 1e-30]:
        uvec = np.array([ref.uv(r), ref.ur(r), 0.0, 0.0])
        lam = tidal_tensor(m, r, math.pi / 2, uvec, E=1.0)["eigenvalues"]
        cf = tidal_eigenvalues_radial_closed_form(1.0, r)
        worst_t = max(worst_t, _rel(lam[0], cf[0]), _rel(lam[1], cf[1]), _rel(lam[2], cf[2]))
        if r >= 0.5:   # Gram–Schmidt frame is only well conditioned outside / near the horizon
            tet = comoving_tetrad(m, r, math.pi / 2, uvec)
            n_cf = radial_unit_vector_closed_form(m, r, uvec)
            worst_t = max(worst_t, float(np.max(np.abs(tet[1] - n_cf)) / np.max(np.abs(n_cf))))
    t.check("tidal eigenvalues (-2M/r^3, M/r^3, M/r^3) [r = 10 .. 1e-30] and radial tetrad vector vs closed form", worst_t, None, 1e-9, kind="abs",
            note="comoving frame built from the Killing energy (well conditioned); plain Gram–Schmidt checked for r >= M")
    r_qg = sim.milestones[-1].r_geo
    uvec = np.array([ref.uv(r_qg), ref.ur(r_qg), 0.0, 0.0])
    lam = tidal_tensor(m, r_qg, math.pi / 2, uvec, E=1.0)["eigenvalues"]
    t.check("radial tidal eigenvalue at r_QG vs -2M/r^3 (explicit contraction)", float(lam[0]), -2.0 / r_qg**3, 1e-9)
    lam_f = tidal_eigenvalues_frame(m, r_qg, math.pi / 2, uvec)
    t.check("radial tidal eigenvalue at r_QG vs -2M/r^3 (closed form used in outputs)", float(lam_f[0]), -2.0 / r_qg**3, 1e-12)
    # orbital motion: closed form (-(2+3t^2), 1+3t^2, 1) M/r^3 vs explicit contraction (exterior, well conditioned)
    from .geodesic import initial_state_radial as _isr
    worst_o = 0.0
    for L in (2.5, 3.9):
        for r in (10.0, 3.0, 2.0, 1.0):
            y1 = _isr(m, r, 1.0, L)
            l1 = tidal_eigenvalues_frame(m, r, math.pi / 2, y1[IUV:IUV + 4])
            lc = np.sort(tidal_tensor(m, r, math.pi / 2, y1[IUV:IUV + 4], E=y1[IEK])["eigenvalues"])
            worst_o = max(worst_o, float(np.max(np.abs(l1 - lc) / np.max(np.abs(l1)))))
    t.check("orbital-motion tidal eigenvalues: closed form -(2+3L^2/r^2), 1+3L^2/r^2, 1 (x M/r^3) vs explicit contraction", worst_o, None, 1e-9, kind="abs")
    return t.d


def test6_rqg(dq: DerivedQuantities) -> dict:
    t = Test("TEST 6", "Quantum-curvature radius", "48 G^2 M^2/(c^4 r_QG^6) = 1/l_P^4  ->  r_QG = (48 G^2 M^2 l_P^4/c^4)^(1/6)",
             "definition; Planck length CODATA 2022")
    from scipy.optimize import brentq
    import mpmath as mp

    def g(log10r):
        return (math.log10(48.0) + 2.0 * math.log10(dq.M_m) - 6.0 * log10r) - math.log10(dq.K_planck)

    log10_r = brentq(g, -30.0, 0.0, xtol=1e-15)
    r_num = 10.0 ** log10_r
    mp.mp.dps = 40
    r_mp = (48 * mp.mpf(C.G) ** 2 * mp.mpf(dq.M_kg) ** 2 * mp.mpf(C.l_P) ** 4 / mp.mpf(C.c) ** 4) ** (mp.mpf(1) / 6)
    t.check("r_QG numerical root (log-space brentq) vs closed form", r_num, dq.r_QG_m, 1e-12)
    t.check("r_QG closed form (double) vs mpmath 40-digit", dq.r_QG_m, float(r_mp), 1e-14)
    t.check("r_QG vs brief 1.39e-16 m (brief quoted to 3 s.f.)", dq.r_QG_m, BRIEF_EXPECTATIONS["r_QG_m"], 5e-3)
    K_at = 48.0 * C.G**2 * dq.M_kg**2 / (C.c**4 * dq.r_QG_m**6)
    t.check("K(r_QG) / K_Planck", K_at / dq.K_planck, 1.0, 1e-12)
    t.d["calculation"] = {
        "48 G^2 M^2 / c^4 [m^2]": 48.0 * C.G**2 * dq.M_kg**2 / C.c**4,
        "l_P^4 [m^4]": C.l_P**4,
        "product [m^6]": 48.0 * C.G**2 * dq.M_kg**2 / C.c**4 * C.l_P**4,
        "r_QG = product^(1/6) [m]": dq.r_QG_m,
        "r_QG / r_s": dq.r_QG_over_rs,
        "mpmath_40_digits": mp.nstr(r_mp, 30),
    }
    return t.d


def plunge_simulation(cfg: SimulationConfig) -> Simulation:
    """The L = 3.5 GM/c equatorial plunge from 20 r_s used by TESTS 7 and 10."""
    cfgL = SimulationConfig(**{**cfg.to_dict(), "L_over_M": 3.5, "r0_over_rs": 20.0, "rtol": 1e-11, "thrust_alpha_SI": 0.0,
                               "E": 1.0, "thrust_r_on_max_over_rs": math.inf})
    simL = Simulation(cfgL, verbose=False)
    simL.run()
    simL.postprocess()
    return simL


def thrust_simulation(cfg: SimulationConfig, accel_SI: float = 9.81) -> Simulation:
    """The 'thrust_1g' scenario (inward 1 g rocket from 100 r_s, engine on to r_QG) used by TESTS 9 and 10."""
    c2 = SimulationConfig(**{**cfg.to_dict(), "thrust_alpha_SI": accel_SI, "E": 1.0, "L_over_M": 0.0,
                             "thrust_r_on_min_over_rs": 0.0, "thrust_r_on_max_over_rs": math.inf})
    simT = Simulation(c2, verbose=False)
    simT.run()
    simT.postprocess()
    return simT


def test7_conservation(sim: Simulation, simL: Simulation | None = None) -> dict:
    t = Test("TEST 7", "Conserved quantities along the geodesic",
             "E = f u^v - u^r = const ; L = r^2 sin^2 u^phi = const ; g(u,u) = -1", "Killing symmetries; MTW §25.2")
    s = sim.summary()
    cols = sim.columns
    t.check("max |g(u,u) + 1| over all steps (raw)", s["max_abs_norm_residual"], None, 1e-9, kind="abs",
            note="well conditioned for radial motion (terms O(1)); see the conditioned version for L != 0")
    t.check("max |g(u,u) + 1| / conditioning scale", s["max_abs_norm_residual_conditioned"], None, 1e-9, kind="abs")
    t.check("max |L - L0| (benchmark has L = 0: trivially conserved)", s["max_abs_L_drift"], None, 1e-12, kind="abs")
    # non-trivial angular-momentum conservation: equatorial plunge with L = 3.5 GM/c from 20 r_s to r_QG
    if simL is None:
        simL = plunge_simulation(sim.cfg)
    sL = simL.summary()
    t.check("L = 3.5 plunge: max |L - L0| / L0 over all steps", sL["max_abs_L_drift"] / 3.5, None, 1e-8, kind="abs",
            note=f"{sL['n_steps_total']} steps, modes {[sg.mode for sg in simL.segments][:3]}... ; u^theta stays exactly 0: "
                 f"{bool(np.all(simL.columns['u_theta'] == 0.0))}")
    t.check("L = 3.5 plunge: max conditioned |g(u,u)+1|", sL["max_abs_norm_residual_conditioned"], None, 1e-9, kind="abs")
    t.check("L = 3.5 plunge: max conditioned E drift", sL["max_E_drift_conditioned"], None, 1e-9, kind="abs")
    t.check("max |E(u) - E_k| where E is well conditioned (|f u^v|,|u^r| < 10, i.e. r > 0.01 r_s)", s["max_abs_E_drift_where_well_conditioned"], None, 1e-9, kind="abs",
            note="E(u) = f u^v - u^r from the integrated 4-velocity vs the separately carried Killing energy E_k")
    t.check("max |E - E0| / conditioning scale (all steps)", s["max_E_drift_conditioned"], None, 1e-9, kind="abs",
            note="E = f u^v - u^r cancels two terms ~sqrt(2M/r) ~ 1e19 at r_QG; the raw drift "
                 f"{s['max_abs_E_drift_raw']:.3e} is rtol x that magnitude, i.e. tolerance-level error of the huge velocity "
                 "components, not an error in the conserved energy itself (see physics_notes.md §4)")
    return t.d


def test8_convergence(cfg: SimulationConfig) -> dict:
    t = Test("TEST 8", "Convergence with tolerance + independent integrator/formulation cross-checks",
             "error(tau_h->QG), error(Delta v) vs analytic for rtol = 1e-6 .. 1e-12; SciPy DOP853; first-integral form",
             "Hairer, Nørsett & Wanner 1993 ch. II; Dormand & Prince 1980")
    ref = RadialInfallE1()
    rows = []
    prev = None
    monotone = True
    for rtol in [1e-6, 1e-8, 1e-10, 1e-12]:
        # step cap lifted (max_step_lnr = 5) so that the error controller alone sets the step
        c2 = SimulationConfig(**{**cfg.to_dict(), "rtol": rtol, "atol": rtol * 1e-2, "max_step_lnr": 5.0, "thrust_r_on_max_over_rs": math.inf})
        sim = Simulation(c2, verbose=False)
        t0 = time.time()
        sim.run()
        sim.postprocess()
        ms = sim.milestone_states
        r_qg = sim.milestones[-1].r_geo
        dtau = ms["r_QG"]["tau_total_geo"] - ms["horizon"]["tau_total_geo"]
        e_tau = _rel(dtau, ref.tau_between(2.0, r_qg))
        dv = ms["r_QG"]["v_total_geo"] - ms["horizon"]["v_total_geo"]
        e_v = _rel(dv, ref.v_between(2.0, r_qg))
        e_ur = float(np.nanmax(np.abs(sim.columns["ur_reldiff_E1"])))
        rows.append({"rtol": rtol, "steps": sim.summary()["n_steps_total"], "err_tau_h_to_QG": e_tau, "err_dv_h_to_QG": e_v,
                     "max_err_ur": e_ur, "wall_s": time.time() - t0})
        cur = max(e_tau, e_ur)
        if prev is not None and cur > prev and cur > 1e-12:
            monotone = False
        prev = cur
    t.d["convergence_table"] = rows
    t.check("errors decrease monotonically with tolerance (exemption only below 1e-12)", 1.0 if monotone else 0.0, 1.0, 0.0, kind="abs")
    t.check("error(tau) at rtol=1e-12 (uncapped step)", rows[-1]["err_tau_h_to_QG"], None, 1e-9, kind="abs")
    t.check("max error(u^r) at rtol=1e-12 (uncapped step)", rows[-1]["max_err_ur"], None, 1e-9, kind="abs")
    ratio = rows[0]["max_err_ur"] / max(rows[2]["max_err_ur"], 1e-300)
    t.check("convergence ratio error(rtol=1e-6)/error(rtol=1e-10) >= 100 (checked as 100/ratio <= 1)", 100.0 / ratio, None, 1.0, kind="abs",
            note=f"ratio = {ratio:.3e} over four decades of tolerance")
    # --- independent integrator: SciPy DOP853 on the same ln r system, horizon -> r_QG
    m = Schwarzschild()
    y0 = np.array([0.0, 2.0, math.pi / 2, 0.0, ref.uv(2.0), ref.ur(2.0), 0.0, 0.0, 0.0, 1.0])
    r_qg = (Simulation(cfg, verbose=False)).milestones[-1].r_geo

    def fun(x, y):
        return rhs_lnr(m, x, y)

    sol = integrate_scipy_dop853(fun, math.log(2.0), y0, math.log(r_qg), rtol=1e-13, atol=1e-16)
    dtau_sp = sol.y[ITAU, -1]
    t.check("SciPy DOP853 (rtol 1e-13) tau(h -> QG) vs analytic", float(dtau_sp), ref.tau_between(2.0, r_qg), 1e-9)
    t.check("SciPy DOP853 Delta v(h -> QG) vs analytic", float(sol.y[IV, -1]), ref.v_between(2.0, r_qg), 1e-9)
    # --- independent formulation: first integrals (E, L) instead of the second-order geodesic equation
    y0f = np.array([0.0, 2.0, math.pi / 2, 0.0, 1.0, 0.0, 0.0])
    integ = DormandPrince54(rtol=1e-12, atol=np.array([1e-14, 0, 1e-14, 1e-14, 1e-14, 1e-14, 1e-14]), max_step=0.05)
    resf = integ.integrate(lambda x, y: rhs_first_integral_lnr(m, x, y), math.log(2.0), y0f, math.log(r_qg))
    t.check("first-integral formulation tau(h -> QG) vs analytic", float(resf.y[-1, 6]), ref.tau_between(2.0, r_qg), 1e-9)
    t.check("first-integral formulation Delta v(h -> QG) vs analytic", float(resf.y[-1, 0]), ref.v_between(2.0, r_qg), 1e-9)
    t.check("second-order vs first-integral tau(h -> QG) (two formulations agree)", rows[-1]["err_tau_h_to_QG"] + _rel(float(resf.y[-1, 6]), ref.tau_between(2.0, r_qg)), None, 2e-9, kind="abs")
    _test8_high_precision_references(t, cfg)
    return t.d


def _segment_errors(sim: Simulation, refd: dict, keys=("dtau", "dv")) -> dict:
    ms = [sim.milestone_states[m.slug] for m in sim.milestones]
    out = {}
    name = {"dtau": "dtau_segment_geo", "dv": "dv_segment_geo"}
    for k in keys:
        out[f"max_rel_err_{k}_per_segment"] = max(_rel(ms[i][name[k]], refd[k][i]) for i in range(1, len(ms)))
    out["max_rel_err_u_r_at_milestones"] = max(_rel(ms[i]["u_r"], refd["u_r"][i]) for i in range(len(ms)))
    if "E" in refd:
        out["max_rel_err_E_at_milestones"] = max(_rel(ms[i]["E_killing"], refd["E"][i]) for i in range(len(ms)))
    if "dphi" in refd:
        # phi is stored as an absolute angle (unlike v_seg/tau_seg), so per-segment increments below ~1e-15 rad
        # deep inside are not resolvable: compare the accumulated angle at each milestone instead
        phi_ref = np.cumsum(refd["dphi"])
        phi_num = [float(sim.segments[0].y[0, 3] - sim.segments[0].y[0, 3])] + [float(sg.y[-1, 3] - sim.segments[0].y[0, 3]) for sg in sim.segments]
        out["max_rel_err_phi_at_milestones"] = max(_rel(phi_num[i], phi_ref[i]) for i in range(1, len(phi_num)))
    return out


def _test8_high_precision_references(t: Test, cfg: SimulationConfig) -> None:
    """Scenarios WITHOUT an elementary closed form vs 35-digit mpmath quadrature of first integrals
    (slab.reference): the 1 g rocket (E(r) = E0 + alpha (r0 - r) exact, tau and v elliptic-type integrals)
    over the full range r0 -> r_QG, and the L = 3.5 GM/c plunge (tau, v, phi)."""
    t.check("mpmath quadrature self-test: tau(r_s -> 1e-30 r_s) for E = 1 vs closed form (35 digits)", e1_reference_check(), None, 1e-28, kind="abs")
    rows = []
    refd = None
    alpha = horizon_index = None
    prev, monotone = None, True
    for rtol in [1e-6, 1e-8, 1e-10, 1e-12]:
        c2 = SimulationConfig(**{**cfg.to_dict(), "rtol": rtol, "atol": rtol * 1e-2, "max_step_lnr": 5.0, "thrust_alpha_SI": 9.81,
                                 "E": 1.0, "L_over_M": 0.0, "thrust_r_on_min_over_rs": 0.0, "thrust_r_on_max_over_rs": math.inf})
        sim = Simulation(c2, verbose=False)
        t0 = time.time()
        sim.run()
        if refd is None:
            rp = [m.r_geo for m in sim.milestones]
            alpha = sim.thrust.alpha
            horizon_index = [m.slug for m in sim.milestones].index("horizon")
            refd = thrust_radial_reference(rp, 1.0, alpha, rp[0], dps=35)
        e = _segment_errors(sim, refd)
        e.update({"rtol": rtol, "steps": int(sum(len(sg.x) - 1 for sg in sim.segments)), "wall_s": time.time() - t0})
        rows.append(e)
        cur = max(e["max_rel_err_dtau_per_segment"], e["max_rel_err_u_r_at_milestones"])
        if prev is not None and cur > prev and cur > 1e-12:
            monotone = False
        prev = cur
    t.d["convergence_table_thrust_1g_vs_mpmath"] = rows
    t.d["thrust_1g_reference"] = {"method": "35-digit mpmath tanh-sinh quadrature of dtau/dr = 1/sqrt(E(r)^2 - f), dv/dr = u^v/|u^r|, "
                                            "E(r) = 1 + alpha (r0 - r) (exact); milestone segments r0 -> r_QG",
                                  "alpha_geo": float(alpha), "quad_rel_err_max": refd["quad_rel_err_max"],
                                  "E_at_horizon": refd["E"][horizon_index]}
    t.check("1 g rocket (no closed form) vs mpmath: quadrature error estimate", refd["quad_rel_err_max"], None, 1e-25, kind="abs")
    t.check("1 g rocket vs mpmath: errors decrease monotonically with rtol", 1.0 if monotone else 0.0, 1.0, 0.0, kind="abs")
    last = rows[-1]
    t.check("1 g rocket vs mpmath at rtol=1e-12: max rel error of dtau per milestone segment (r0 -> r_QG)", last["max_rel_err_dtau_per_segment"], None, 1e-9, kind="abs")
    t.check("1 g rocket vs mpmath at rtol=1e-12: max rel error of dv per milestone segment", last["max_rel_err_dv_per_segment"], None, 1e-9, kind="abs")
    t.check("1 g rocket vs mpmath at rtol=1e-12: max rel error of u^r at milestones", last["max_rel_err_u_r_at_milestones"], None, 1e-9, kind="abs")
    t.check("1 g rocket: carried Killing energy vs exact E(r) = 1 + alpha (r0 - r) at milestones", last["max_rel_err_E_at_milestones"], None, 1e-9, kind="abs")
    ratio = rows[0]["max_rel_err_dtau_per_segment"] / max(rows[2]["max_rel_err_dtau_per_segment"], 1e-300)
    t.check("1 g rocket: convergence ratio error(rtol=1e-6)/error(rtol=1e-10) >= 100 (checked as 100/ratio <= 1)", 100.0 / ratio, None, 1.0, kind="abs",
            note=f"ratio = {ratio:.3e}")
    # L = 3.5 plunge from 100 r_s (exterior in tau mode with event-located milestones, interior in ln r)
    rowsL = []
    refL = None
    for rtol in [1e-8, 1e-10, 1e-12]:
        c3 = SimulationConfig(**{**cfg.to_dict(), "rtol": rtol, "L_over_M": 3.5, "E": 1.0, "thrust_alpha_SI": 0.0,
                                 "thrust_r_on_max_over_rs": math.inf})
        sim = Simulation(c3, verbose=False)
        t0 = time.time()
        sim.run()
        if refL is None:
            refL = plunge_reference([m.r_geo for m in sim.milestones], 1.0, 3.5, dps=35)
        e = _segment_errors(sim, refL)
        e.update({"rtol": rtol, "steps": int(sum(len(sg.x) - 1 for sg in sim.segments)), "wall_s": time.time() - t0})
        rowsL.append(e)
    t.d["convergence_table_plunge_L3.5_vs_mpmath"] = rowsL
    t.check("L = 3.5 plunge vs mpmath: quadrature error estimate", refL["quad_rel_err_max"], None, 1e-25, kind="abs")
    lastL = rowsL[-1]
    worstL = max(lastL["max_rel_err_dtau_per_segment"], lastL["max_rel_err_dv_per_segment"], lastL["max_rel_err_phi_at_milestones"],
                 lastL["max_rel_err_u_r_at_milestones"])
    t.check("L = 3.5 plunge vs mpmath at rtol=1e-12: max rel error of (dtau, dv per segment; accumulated phi and u^r at milestones), r0 = 100 r_s -> r_QG",
            worstL, None, 1e-9, kind="abs")
    t.check("L = 3.5 plunge: error at rtol=1e-8 > error at rtol=1e-12 (convergence)",
            1.0 if rowsL[0]["max_rel_err_dtau_per_segment"] > lastL["max_rel_err_dtau_per_segment"] else 0.0, 1.0, 0.0, kind="abs")


# ---------------------------------------------------------------------------
def test9_accelerated_frame(sim: Simulation, simT: Simulation) -> dict:
    t = Test("TEST 9", "Accelerated observer's proper reference frame: inertial (Rindler-type) differential term",
             "d^2 xi^i/dtau^2 = -a^i - [R^i_0j0 + a^i a_j] xi^j  =>  differential along the thrust axis: -(lambda_radial + a^2) L",
             "MTW §13.6 (proper reference frame, linear order); Ni & Zimmermann 1978, Phys. Rev. D 17, 1473 (second-order metric); "
             "exact Rindler solution (flat space)")
    # (a) flat space, exact Rindler comparison (engine thrust + engine geodesics, f = 1)
    rd = rindler_flat_check(a=1.0, L=0.1, tau_max=2.0)
    t.d["rindler_flat"] = rd
    t.check("flat space: engine-integrated thrusting observer vs exact hyperbola (a = 1, tau <= 2)", rd["observer_vs_exact_hyperbola_max_abs"], None, 1e-9, kind="abs")
    t.check("flat space: free particle at the observer, rest-frame position vs (1/a)(1/cosh(a tau) - 1)", rd["xi_origin_vs_exact_max_abs"], None, 1e-9, kind="abs")
    t.check("flat space: free particle L ahead, separation vs exact L/cosh(a tau) (relative to L)", rd["separation_vs_L_over_cosh_max_rel"], None, 1e-8, kind="abs",
            note=f"separation shrinks to {rd['separation_at_tau_max_over_L']:.4f} L at a tau = 2 (exact 1/cosh 2 = {1/math.cosh(2):.4f})")
    t.check("flat space: measured differential acceleration at tau = 0 vs -a^2 L", rd["measured_diff_accel_at_0"], rd["predicted_inertial_term_-a2L"], 1e-6)
    t.check("flat space: measured acceleration of the co-located free particle vs -a", rd["measured_origin_accel_at_0"], rd["predicted_origin_accel_-a"], 1e-6)
    # (b) Schwarzschild, static (hovering) observer held by the engine; tidal and inertial terms comparable
    hov = []
    for r0, sign in ((4.0, 1.0), (2.2, 1.0), (2.2, -1.0)):
        h = hovering_check(r0, L=1e-3, sign=sign)
        hov.append(h)
        tag = f"r0 = {r0 / 2:g} r_s, particle {'ahead (outward)' if sign > 0 else 'behind (inward)'}"
        t.check(f"hovering observer ({tag}): engine thrust holds r fixed", h["observer_hover_max_abs_dr"], None, 1e-10, kind="abs")
        t.check(f"hovering ({tag}): co-located free particle accelerates at -a", h["measured_origin_accel_along_r"], h["predicted_-a"], 1e-6)
        t.check(f"hovering ({tag}): measured differential acceleration vs exact lapse value", h["measured_diff_accel"], h["exact_lapse_diff_accel"], 1e-5)
        t.check(f"hovering ({tag}): measured vs -(lambda + a^2) L  [a^2/|lambda| = {h['a2_over_abs_lambda']:.3f}]",
                h["measured_diff_accel"], h["predicted_-(lambda+a2)L"], 2e-2, note="first order in L = 1e-3 M")
        t.check(f"hovering ({tag}): tidal-only prediction -lambda L would be wrong by (informational)",
                _rel(h["tidal_only_prediction_-lambdaL"], h["measured_diff_accel"]), None, None, kind="abs",
                note="shows that the inertial term is required in an accelerated frame")
    t.d["hovering_checks"] = hov
    # (c) the output columns on the thrust_1g scenario
    cols = simT.columns
    a_SI = simT.units.accel_to_SI(abs(simT.thrust.alpha))
    Lb = simT.cfg.body_length_m
    expected = inertial_diff_along_thrust_SI(a_SI, Lb)
    t.check("thrust_1g: inertial_diff_radial_m_s2 = -a^2 L/c^2 at every step (engine on)",
            float(np.max(np.abs(cols["inertial_diff_radial_m_s2"] - expected))) / abs(expected), None, 1e-15, kind="abs",
            note=f"a = {a_SI:g} m/s^2, L = {Lb:g} m: a^2 L/c^2 = {abs(expected):.4e} m/s^2")
    t.check("thrust_1g: radial_total_diff = radial_stretch + inertial_diff",
            float(np.max(np.abs(cols["radial_total_diff_m_s2"] - cols["radial_stretch_m_s2"] - cols["inertial_diff_radial_m_s2"])
                         / np.abs(cols["radial_total_diff_m_s2"]).clip(1e-300))), None, 1e-12, kind="abs")
    t.check("free-fall benchmark: inertial_diff_radial_m_s2 exactly 0 (engine off)", float(np.max(np.abs(sim.columns["inertial_diff_radial_m_s2"]))), 0.0, 0.0, kind="abs")
    r_geo = cols["r_geo"]
    E_cf = thrust_energy_closed_form(1.0, simT.thrust.alpha, r_geo[0], r_geo)
    relE = np.abs(cols["E_killing"] / E_cf - 1.0)
    t.check("thrust_1g: carried Killing energy vs exact E(r) = 1 + alpha (r0 - r) at every step (max rel)", float(np.max(relE)), None, 1e-8, kind="abs",
            note=f"the maximum sits in the first steps (r0 - r ~ 1e-9 M) where r = exp(ln r) is rounded to ~3e-14 and dE/dr = alpha = 1.6e5; "
                 f"inside the horizon max rel = {float(np.max(relE[r_geo <= 2.0])):.1e} (milestones: TEST 8)")
    # (d) informational: how the inertial term compares with the tidal term along the fall
    rx = crossover_radius_geo(simT.thrust.alpha)
    ms = simT.milestone_states
    comp = []
    for m in simT.milestones:
        d = ms[m.slug]
        tid = d["radial_stretch_accel_m_s2"]
        comp.append({"milestone": m.slug, "r_over_rs": m.r_over_rs, "radial_stretch_m_s2": tid, "inertial_diff_m_s2": expected,
                     "abs_ratio_inertial_to_tidal": abs(expected) / abs(tid)})
    t.d["thrust_1g_inertial_vs_tidal"] = comp
    t.d["crossover"] = {"r_x_over_rs": rx / 2.0, "r_x_m": simT.units.r_to_SI(rx), "r_x_ly": simT.units.m_to_ly(simT.units.r_to_SI(rx)),
                        "definition": "2GM L/r^3 = a^2 L/c^2 (radial motion): inertial term dominates for r > r_x, curvature below"}
    t.check("thrust_1g: ratio |inertial|/|tidal| at the start (100 r_s) (informational)", comp[0]["abs_ratio_inertial_to_tidal"], None, None, kind="abs")
    t.check("thrust_1g: ratio |inertial|/|tidal| at the horizon (informational)",
            next(c for c in comp if c["milestone"] == "horizon")["abs_ratio_inertial_to_tidal"], None, None, kind="abs")
    t.check("thrust_1g: crossover radius r_x/r_s where the two are equal (informational)", rx / 2.0, None, None, kind="abs",
            note=f"= {t.d['crossover']['r_x_ly']:.3g} ly; below r_x the tidal (curvature) term dominates")
    return t.d


def test10_signal_timeline(sim: Simulation, simT: Simulation, simL: Simulation) -> dict:
    t = Test("TEST 10", "Distant-observer received-signal timeline",
             "u = v - 2 r_*;  1+z = du/dtau = u^v - 2u^r/f;  1+z ~ exp(u/4M) (kappa = 1/4M);  E = 1: 1+z = 1/(1 - sqrt(r_s/r))",
             "MTW §31.3–31.4 (freezing/redshift at the horizon, from memory); surface gravity kappa = 1/4M: Wald §12.5 (from memory)")
    tl = compute_signal_timeline(sim, method="exact")
    r = np.array(tl["r_over_rs"]) * 2.0
    eps = np.array(tl["eps"])
    t.check("timeline reaches eps = r/r_s - 1 <= 1.1e-12", float(eps[-1]), None, 1.1e-12, kind="abs", note=f"{len(eps)} emission radii")
    opz = np.array(tl["one_plus_z"])
    t.check("E = 1: 1+z vs closed form 1/(1 - sqrt(r_s/r)) over eps = 99 .. 1e-12 (max rel)", float(np.max(np.abs(opz / one_plus_z_E1_closed_form(r) - 1.0))), None, 1e-9, kind="abs")
    ref = RadialInfallE1()
    m = sim.metric
    u_cf = np.array([ref.v_between(r[0], x) - 2.0 * (m.tortoise(x) - m.tortoise(r[0])) for x in r])
    u_num = np.array(tl["t_receive_geo"])
    t.check("E = 1: t_receive vs closed form Delta v(r) - 2 Delta r_*(r) (max abs error / max(1, |value|))",
            float(np.max(np.abs(u_num - u_cf) / np.maximum(1.0, np.abs(u_cf)))), None, 1e-9, kind="abs")
    tld = compute_signal_timeline(sim, method="dense")
    t.check("dense output (one ln r integration, Hairer continuous extension) vs exact per-radius integration: 1+z",
            float(np.max(np.abs(np.array(tld["one_plus_z"]) / opz - 1.0))), None, 1e-9, kind="abs")
    t.check("dense vs exact: t_receive (max abs / max(1,|value|))",
            float(np.max(np.abs(np.array(tld["t_receive_geo"]) - u_num) / np.maximum(1.0, np.abs(u_num)))), None, 1e-9, kind="abs")
    sl = late_time_slopes(tl, 1e-8)
    t.d["late_time_E1"] = sl
    t.check("E = 1: 4M d ln(1+z)/du for eps <= 1e-8 -> 1 (redshift e-folds every 4GM/c^3)", sl["dln1pz_du_times_4M"], 1.0, 1e-2,
            note=f"max local deviation {sl['max_local_dev_of_4M_dln1pz_du_from_1']:.2e}")
    t.check("E = 1: reception time per decade of eps -> 4M ln 10 = 9.2103 M", sl["t_receive_per_decade_geo"], sl["t_receive_per_decade_expected_4Mln10"], 1e-2)
    t.check("t_receive strictly increasing (-> infinity as eps -> 0)", 1.0 if bool(np.all(np.diff(u_num) > 0)) else 0.0, 1.0, 0.0, kind="abs",
            note=f"t_receive(eps_min) = {tl['t_receive_years'][-1]:.6e} yr; +{sl['t_receive_per_decade_geo'] * sim.units.t_to_years(1.0):.4e} yr per further decade of eps, without bound")
    tau_h = sim.milestone_states["horizon"]["tau_total_geo"]
    t.check("emitter proper time at eps_min vs horizon-crossing proper time of the main run (finite)", tl["tau_geo"][-1], tau_h, 1e-9,
            note=f"proper time elapsed over the last {math.log10(sl['eps_range'][0] / sl['eps_range'][1]):.1f} decades of eps: {sl['tau_increment_over_range_geo']:.3e} GM/c^3 "
                 f"while t_receive advanced {sl['t_receive_increment_over_range_geo']:.2f} GM/c^3")
    # per-sample columns of the main trajectory
    c = sim.columns
    inside = c["r_geo"] <= 2.0
    t.check("trajectory columns u_ret_geo / t_receive_years are null inside the horizon and finite outside",
            1.0 if (np.all(np.isnan(c["t_receive_years"][inside])) and np.all(np.isfinite(c["t_receive_years"][~inside]))) else 0.0, 1.0, 0.0, kind="abs")
    # general scenarios (thrust, L != 0): the late-time law is universal
    for name, s_ in (("thrust_1g (E -> 3.2e7)", simT), ("L = 3.5 plunge from 20 r_s (tau mode)", simL)):
        tg = compute_signal_timeline(s_, method="exact")
        sg = late_time_slopes(tg, 1e-8)
        t.d[f"late_time_{name.split()[0]}"] = sg
        t.check(f"{name}: 4M d ln(1+z)/du for eps <= 1e-8 -> 1", sg["dln1pz_du_times_4M"], 1.0, 1e-2)
        t.check(f"{name}: t_receive strictly increasing, timeline reaches eps <= 1.1e-12",
                1.0 if (np.all(np.diff(tg["t_receive_geo"]) > 0) and tg["eps"][-1] <= 1.1e-12) else 0.0, 1.0, 0.0, kind="abs")
    return t.d



def run_all_tests(cfg: SimulationConfig, root: Path) -> dict:
    t_start = time.time()
    dq = DerivedQuantities(cfg.M_solar)
    base = SimulationConfig(**{**cfg.to_dict(), "thrust_alpha_SI": 0.0, "E": 1.0, "L_over_M": 0.0,
                                 "thrust_r_on_max_over_rs": math.inf})
    sim = Simulation(base, verbose=False)
    sim.run()
    sim.postprocess()
    simL = plunge_simulation(base)
    simT = thrust_simulation(base)
    tests: List[dict] = [
        test0_constants(dq), test1_schwarzschild_radius(dq), test2_horizon_regularity(sim), test3_radial_geodesic(sim),
        test4_proper_time_benchmark(sim), test5_kretschmann(sim), test6_rqg(dq), test7_conservation(sim, simL), test8_convergence(base),
        test9_accelerated_frame(sim, simT), test10_signal_timeline(sim, simT, simL),
    ]
    n_pass = sum(1 for x in tests if x["passed"])
    report = {
        "project": "SLAB_GR_Simulation",
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "wall_time_s": time.time() - t_start,
        "benchmark_configuration": base.to_dict(),
        "constants": C.PRIMARY_CONSTANTS,
        "derived_quantities": dq.as_dict(),
        "brief_expectations": BRIEF_EXPECTATIONS,
        "n_tests": len(tests),
        "n_passed": n_pass,
        "all_passed": n_pass == len(tests),
        "validation_status": "VALIDATED" if n_pass == len(tests) else "NOT VALIDATED",
        "tests": tests,
        "benchmark_summary": sim.summary(),
        "verification_caveats": [
            "Constants checked against CODATA 2022 (Rev. Mod. Phys. 97, 025002 (2025)) by web search on 2026-09-25; NIST pages themselves could not be fetched from the build environment (see references.md).",
            "M_sun = 1.98847e30 kg as specified in the brief; IAU 2015 nominal GM_sun/G gives 1.98841e30 kg (3e-5 relative).",
            "All 'years' are Julian years (365.25 d).",
        ],
    }
    return report
