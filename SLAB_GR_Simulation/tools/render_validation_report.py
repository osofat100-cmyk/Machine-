#!/usr/bin/env python3
"""Render validation_report.json into docs/validation_report.md (human-readable final report)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fmt(x):
    if isinstance(x, float):
        if x == 0:
            return "0"
        return f"{x:.6e}" if (abs(x) >= 1e5 or abs(x) < 1e-3) else f"{x:.9g}"
    return str(x)


EXTRA_TABLES = {
    "convergence_table_thrust_1g_vs_mpmath": "1 g rocket (no closed form) vs 35-digit mpmath quadrature reference, milestone segments r0 -> r_QG, step cap lifted",
    "thrust_1g_reference": "Reference used for the 1 g rocket",
    "convergence_table_plunge_L3.5_vs_mpmath": "L = 3.5 GM/c plunge vs 35-digit mpmath quadrature reference (r0 = 100 r_s -> r_QG)",
    "rindler_flat": "Flat-space (Rindler) check, engine-integrated observer and free particles (geometrized units)",
    "hovering_checks": "Static (hovering) observer held by the engine in Schwarzschild: measured vs predicted differential acceleration",
    "thrust_1g_inertial_vs_tidal": "thrust_1g: inertial term (-a^2 L/c^2) vs radial tidal stretching across 2 m at the milestones",
    "crossover": "Radius where the radial tidal term equals the inertial term (1 g)",
    "late_time_E1": "Late-time received-signal behaviour, E = 1 benchmark",
    "late_time_thrust_1g": "Late-time received-signal behaviour, thrust_1g",
    "late_time_L": "Late-time received-signal behaviour, L = 3.5 plunge",
}


def _extra(w, title, obj) -> None:
    """Generic rendering of the extra tables added with TESTS 8 (references), 9 and 10."""
    w(f"\n{title}:\n")
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        keys = list(obj[0].keys())
        w("| " + " | ".join(keys) + " |\n|" + "---|" * len(keys))
        for r in obj:
            w("| " + " | ".join(fmt(r.get(k)) for k in keys) + " |")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            w(f"* {k}: `{fmt(v)}`")


def main() -> None:
    rep = json.loads((ROOT / "validation_report.json").read_text())
    out = []
    w = out.append
    w("# SLAB_GR_Simulation — validation report\n")
    w(f"Generated: {rep['generated_utc']}  ·  status: **{rep['validation_status']}**  ·  {rep['n_passed']}/{rep['n_tests']} tests passed  ·  wall time {rep['wall_time_s']:.1f} s\n")
    w("Every number below is computed by `src/slab/validation.py` from the constants in `src/slab/constants.py`; nothing is typed in by hand. "
      "Tags: **EXACT GR RESULT** (closed-form consequence of the Schwarzschild solution), **NUMERICAL** (integrated/rooted value with the quoted error), "
      "**BRIEF** (value quoted in the project brief, used only as a comparison target).\n")
    w("## 1. Physical constants and provenance\n")
    w("| symbol | value | unit | source | verification status |\n|---|---|---|---|---|")
    for k, c in rep["constants"].items():
        w(f"| {k} | {c['value']!r} | {c['unit']} | {c['source']} | {c['verification']} |")
    w("\n## 2. Derived quantities (computed at run time)\n")
    w("| quantity | value |\n|---|---|")
    for k, v in rep["derived_quantities"].items():
        w(f"| {k} | {fmt(v)} |")
    w("\nBrief expectations (comparison targets only): " + ", ".join(f"{k} = {v!r}" for k, v in rep["brief_expectations"].items()) + "\n")
    w("## 3. Tests\n")
    for t in rep["tests"]:
        w(f"### {t['id']} — {t['name']}  ·  **{'PASS' if t['passed'] else 'FAIL'}**\n")
        w(f"Equation(s): `{t['equation']}`  \nReference: {t['reference']}\n")
        w("| check | value | expected | error | tolerance | result | note |\n|---|---|---|---|---|---|---|")
        for c in t["checks"]:
            w(f"| {c['label']} | {fmt(c['value'])} | {fmt(c['expected']) if c['expected'] is not None else '—'} | "
              f"{fmt(c['error']) if c['error'] is not None else '—'} | {fmt(c['tolerance']) if c['tolerance'] is not None else '—'} | "
              f"{'ok' if c['passed'] else 'FAIL'} | {c.get('note', '')} |")
        if "calculation" in t:
            w("\nStep-by-step calculation:\n")
            for k, v in t["calculation"].items():
                w(f"* {k}: `{v}`")
        if "segment_table" in t:
            w("\nPer-segment comparison with the analytic E = 1 solution (geometrized units):\n")
            w("| from | to | Δv numeric | Δv analytic | rel. err | Δτ numeric | Δτ analytic | rel. err |\n|---|---|---|---|---|---|---|---|")
            for r in t["segment_table"]:
                w(f"| {r['from']} | {r['to']} | {fmt(r['dv_numeric'])} | {fmt(r['dv_analytic'])} | {fmt(r['rel_err_dv'])} | {fmt(r['dtau_numeric'])} | {fmt(r['dtau_analytic'])} | {fmt(r['rel_err_dtau'])} |")
        if "convergence_table" in t:
            w("\nConvergence with tolerance (step cap lifted so that the error controller alone sets the step):\n")
            w("| rtol | steps | rel. err τ(h→r_QG) | rel. err Δv(h→r_QG) | max rel. err u^r | wall [s] |\n|---|---|---|---|---|---|")
            for r in t["convergence_table"]:
                w(f"| {r['rtol']:g} | {r['steps']} | {fmt(r['err_tau_h_to_QG'])} | {fmt(r['err_dv_h_to_QG'])} | {fmt(r['max_err_ur'])} | {r['wall_s']:.2f} |")
        for key, title in EXTRA_TABLES.items():
            if key in t:
                _extra(w, title, t[key])
        w("")
    s = rep["benchmark_summary"]
    w("## 4. Benchmark run summary\n")
    for k in ("n_steps_total", "n_rhs_evals_total", "n_rejected_total", "max_err_estimate", "max_abs_norm_residual",
              "max_abs_E_drift_raw", "max_E_drift_conditioned", "max_abs_E_drift_where_well_conditioned", "max_abs_L_drift",
              "max_tidal_closed_form_reldiff", "tau_total_years_at_end", "tau_since_horizon_years_at_end"):
        w(f"* {k}: `{fmt(s[k])}`")
    w("\n### Milestones\n")
    w("| milestone | r [m] | r / r_s | τ total [yr] | log10 K [m⁻⁴] | log10 K/K_P | radial stretch [m/s² per 2 m] | regime |\n|---|---|---|---|---|---|---|---|")
    for m in s["milestones"]:
        w(f"| {m['slug']} | {fmt(m['r_m'])} | {fmt(m['r_over_rs'])} | {fmt(m['tau_total_years'])} | {m['log10_K_SI']:.3f} | {m['log10_K_over_K_planck']:.3f} | {fmt(m['radial_stretch_accel_m_s2'])} | {m['regime']} |")
    w("\n## 5. Verification caveats\n")
    for c in rep["verification_caveats"]:
        w(f"* {c}")
    w("\nWhere a value could not be independently verified in this build environment it is marked above; no gap was filled with an assumption.\n")
    (ROOT / "docs" / "validation_report.md").write_text("\n".join(out))
    print("wrote docs/validation_report.md")


if __name__ == "__main__":
    main()
