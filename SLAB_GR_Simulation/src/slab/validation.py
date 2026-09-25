"""Automated physics validation suite (TESTS 0–8).

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
                        tidal_tensor, tidal_eigenvalues_radial_closed_form, comoving_tetrad, radial_unit_vector_closed_form)
from .geodesic import (rhs_tau, rhs_lnr, rhs_first_integral_lnr, initial_state_radial, RadialInfallE1, energy, norm,
                       IR, IV, ITAU, IUV, IUR, IEK, IE, IL)
from .integrators import DormandPrince54, integrate_scipy_dop853
from .trajectory import Simulation, SimulationConfig


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
             "l_P = sqrt(hbar G / c^3);  M = 1e18 M_sun", "CODATA 2018 (Tiesinga et al. 2021)")
    t.check("l_P (CODATA) vs sqrt(hbar G/c^3)", dq.l_P_from_hbar_G_c, C.l_P, 1e-6, note="consistency of transcribed constants")
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
    seg = next((s for s in sim.segments if s.slug_to == "horizon"), None)
    if seg is not None:
        t.check("rejected steps in the segment ending on the horizon", int(seg.n_rejected.sum()), 0, 0, kind="abs",
                note="no step-size collapse approaching r = 2M")
        t.check("max normalized error estimate in that segment", float(seg.err.max()), None, 1.0, kind="abs")
    seg2 = next((s for s in sim.segments if s.slug_from == "horizon"), None)
    if seg2 is not None:
        t.check("first accepted step size (ln r) just inside the horizon", float(seg2.h[1]), None, None, kind="abs",
                note="informational: ln r step immediately after crossing")
        t.check("rejected steps in the segment starting on the horizon", int(seg2.n_rejected.sum()), 0, 0, kind="abs")
    return t.d


def test3_radial_geodesic(sim: Simulation) -> dict:
    t = Test("TEST 3", "Radial E = 1 geodesic vs analytic solution",
             "dr/dtau = -c sqrt(r_s/r) ;  u^v = x/(1+x), x = sqrt(r/2M) ; v(r) = -4M[x^3/3 - x^2/2 + x - ln(1+x)] + C",
             "MTW §25.5 & Box 31.2; Wald problem 6.4")
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
             "Henry 2000, ApJ 535, 350; MTW ex. 31.1")
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
    t.check("radial tidal eigenvalue at r_QG vs -2M/r^3", float(lam[0]), -2.0 / r_qg**3, 1e-9)
    return t.d


def test6_rqg(dq: DerivedQuantities) -> dict:
    t = Test("TEST 6", "Quantum-curvature radius", "48 G^2 M^2/(c^4 r_QG^6) = 1/l_P^4  ->  r_QG = (48 G^2 M^2 l_P^4/c^4)^(1/6)",
             "definition; Planck length CODATA 2018")
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


def test7_conservation(sim: Simulation) -> dict:
    t = Test("TEST 7", "Conserved quantities along the geodesic",
             "E = f u^v - u^r = const ; L = r^2 sin^2 u^phi = const ; g(u,u) = -1", "Killing symmetries; MTW §25.2")
    s = sim.summary()
    cols = sim.columns
    t.check("max |g(u,u) + 1| over all steps", s["max_abs_norm_residual"], None, 1e-9, kind="abs")
    t.check("max |L - L0|", s["max_abs_L_drift"], None, 1e-12, kind="abs")
    t.check("max |E(u) - E_k| where E is well conditioned (|f u^v|,|u^r| < 10, i.e. r > 0.01 r_s)", s["max_abs_E_drift_where_well_conditioned"], None, 1e-9, kind="abs",
            note="E(u) = f u^v - u^r from the integrated 4-velocity vs the separately carried Killing energy E_k")
    t.check("max |E - E0| / conditioning scale (all steps)", s["max_E_drift_conditioned"], None, 1e-9, kind="abs",
            note="E = f u^v - u^r cancels two terms ~sqrt(2M/r) ~ 1e19 at r_QG; raw drift = "
                 f"{s['max_abs_E_drift_raw']:.3e} is round-off of those terms, not integration error (see physics_notes.md)")
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
        if prev is not None and cur > prev and cur > 1e-11:
            monotone = False
        prev = cur
    t.d["convergence_table"] = rows
    t.check("errors decrease monotonically with tolerance (until the ~1e-11 round-off floor)", 1.0 if monotone else 0.0, 1.0, 0.0, kind="abs")
    t.check("error(tau) at rtol=1e-12 (uncapped step)", rows[-1]["err_tau_h_to_QG"], None, 1e-9, kind="abs")
    t.check("max error(u^r) at rtol=1e-12 (uncapped step)", rows[-1]["max_err_ur"], None, 1e-9, kind="abs")
    t.check("convergence ratio error(rtol=1e-6)/error(rtol=1e-10) > 10", rows[0]["max_err_ur"] / max(rows[2]["max_err_ur"], 1e-300), None, None, kind="abs",
            note="informational: how much the error shrinks over four decades of tolerance")
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
    return t.d


def run_all_tests(cfg: SimulationConfig, root: Path) -> dict:
    t_start = time.time()
    dq = DerivedQuantities(cfg.M_solar)
    base = SimulationConfig(**{**cfg.to_dict(), "thrust_alpha_SI": 0.0, "E": 1.0, "L_over_M": 0.0,
                                 "thrust_r_on_max_over_rs": math.inf})
    sim = Simulation(base, verbose=False)
    sim.run()
    sim.postprocess()
    tests: List[dict] = [
        test0_constants(dq), test1_schwarzschild_radius(dq), test2_horizon_regularity(sim), test3_radial_geodesic(sim),
        test4_proper_time_benchmark(sim), test5_kretschmann(sim), test6_rqg(dq), test7_conservation(sim), test8_convergence(base),
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
            "Constant values transcribed from CODATA 2018; no network access to NIST in the build session (INSUFFICIENT DATA TO RE-VERIFY ONLINE).",
            "M_sun = 1.98847e30 kg as specified in the brief; IAU 2015 nominal GM_sun/G gives 1.98841e30 kg (3e-5 relative).",
            "All 'years' are Julian years (365.25 d).",
        ],
    }
    return report
