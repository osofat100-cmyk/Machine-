"""Writers: CSV (inspection), JSON (metadata), HDF5 (full resolution), and the
JavaScript data file consumed by the interactive viewer."""
from __future__ import annotations

import csv
import datetime as _dt
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np

from . import constants as C
from .checkpoints import dumps, sanitize as _sanitize
from .trajectory import Simulation, REGIME_VALIDATED, REGIME_EXTREME, REGIME_PLANCK, PLANCK_MESSAGE

LOG_BANNER = "LOGARITHMIC VISUALIZATION — NOT TO SCALE"


def _finite_or_str(x):
    if isinstance(x, (float, np.floating)):
        if math.isnan(x):
            return "nan"
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def metadata(sim: Simulation) -> dict:
    dq = sim.dq
    return {
        "project": "SLAB_GR_Simulation",
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "metric": sim.metric.name,
        "metric_established_physics": sim.metric.established,
        "coordinate_system": sim.cfg.coordinate_system,
        "integrator": sim.cfg.integrator,
        "internal_units": "geometrized G = c = 1, M = 1: length unit GM/c^2, time unit GM/c^3, r_s = 2",
        "config": sim.cfg.to_dict(),
        "config_hash": sim.config_hash,
        "constants": C.PRIMARY_CONSTANTS,
        "derived": dq.as_dict(),
        "regimes": {"codes": {0: REGIME_VALIDATED, 1: REGIME_EXTREME, 2: REGIME_PLANCK},
                    "extreme_curvature_length_m": sim.cfg.extreme_curvature_length_m,
                    "planck_boundary_lengths_in_lP": sim.cfg.planck_boundary_lengths,
                    "note": "Regime labels are a display convention (see physics_notes.md §9); the physics is identical "
                            "classical GR everywhere up to r_QG, where the validated integration STOPS."},
        "planck_message": PLANCK_MESSAGE,
        "kruskal_time_origin_note": "Kruskal/Penrose coordinates use the Schwarzschild time translation that puts the "
                                    "horizon crossing at v = 0 (V_K = 1); this is an exact symmetry of the metric.",
        "column_descriptions": COLUMN_DESCRIPTIONS,
    }


COLUMN_DESCRIPTIONS = {
    "segment": "index of the milestone segment", "step_h": "accepted integrator step (in ln r for mode_is_lnr=1, else in tau [GM/c^3])",
    "err_estimate": "normalized embedded RK5(4) error estimate of the step (<= 1 by construction)",
    "n_rejected": "rejected attempts before this step", "mode_is_lnr": "1 if independent variable is ln r, 0 if tau",
    "r_geo": "areal radius in units of GM/c^2", "r_m": "areal radius [m]", "r_over_rs": "r / r_s",
    "v_geo": "ingoing EF advanced time v [GM/c^3]", "t_ef_geo": "t_EF = v - r [GM/c^3]",
    "t_schw_geo": "Schwarzschild coordinate time t = v - r_* (distant-observer bookkeeping; +inf at r_s)",
    "tau_geo": "proper time since start [GM/c^3]", "tau_s": "proper time [s]", "tau_years": "proper time [Julian yr]",
    "tau_since_horizon_years": "proper time since horizon crossing [yr]",
    "tau_to_center_est_years": "classical-GR extrapolation of the proper time remaining to r=0 assuming free fall with the current (E, L): (2/3) sqrt(r^3/(2GM)) for E=1, L=0, general quadrature otherwise (thrust ignored)",
    "theta,phi": "angular coordinates (equatorial runs: theta = pi/2, phi accumulates for L != 0)",
    "u_v,u_r,u_theta,u_phi": "4-velocity components in EF coordinates (geometrized)",
    "a_v,a_r": "4-acceleration components (nonzero only with thrust)", "a_magnitude_SI": "proper acceleration [m/s^2]",
    "E": "Killing energy f u^v - u^r (cancellation-limited deep inside; see E_conditioning_scale)",
    "E_conditioning_scale": "magnitude of the cancelling terms in E", "E_drift_conditioned": "(E - E0)/conditioning scale",
    "L": "specific angular momentum", "norm_residual": "g(u,u) + 1 (should be 0; raw)",
    "norm_conditioning_scale": "largest term in g(u,u) (round-off floor of the residual is eps * this)",
    "norm_residual_conditioned": "(g(u,u)+1)/conditioning scale",
    "K_SI_log10": "log10 Kretschmann scalar [m^-4]", "K_over_Kplanck_log10": "log10 (K / l_P^-4)",
    "curvature_length_m": "K^(-1/4) [m]",
    "tidal_lambda1..3_geo": "eigenvalues of the tidal tensor E_ij in the comoving frame (1/M^2), boost-invariant frame method",
    "tidal_closed_form_reldiff": "cross-check: frame method vs (-2M/r^3, M/r^3, M/r^3) for radial motion, or vs explicit contraction for L != 0 where well conditioned",
    "tidal_radial_SI_per_m": "most negative eigenvalue (radial, stretching) [s^-2 per m]",
    "tidal_transverse_SI_per_m": "positive eigenvalue (transverse, compressing) [s^-2 per m]",
    "radial_stretch_m_s2": "SIGNED relative acceleration across body_length_m along the eigen-direction of the most negative eigenvalue (radial): positive = separation (stretching) [m/s^2]",
    "transverse_compress_m_s2": "SIGNED relative acceleration across body_length_m along the largest positive eigenvalue: negative = approach (compression) [m/s^2]",
    "tidal_radial_newtonian_SI_per_m": "2GM/r^3 (weak-field expression) — equals the GR radial eigenvalue for radial motion",
    "lc_out_drdtEF": "outgoing radial null direction dr/dt_EF = f/(2-f)", "lc_in_drdtEF": "ingoing radial null direction dr/dt_EF = -1",
    "worldline_drdtEF": "observer worldline slope dr/dt_EF", "dr_dt_schw": "coordinate velocity dr/dt (outside only)",
    "redshift_1pz_to_infinity": "1+z of a radially outgoing signal from the observer received at infinity (outside only)",
    "gamma_rel_to_E1_faller": "Lorentz factor relative to the local E=1 free-faller", "v_rel_to_E1_faller": "relative speed / c",
    "kruskal_U,V,T,X": "Kruskal–Szekeres coordinates (nan when beyond double range)",
    "penrose_Ut,Vt,T,X": "compactified Kruskal coordinates atan(U), atan(V)",
    "ur_analytic_E1,uv_analytic_E1": "closed-form E=1 radial geodesic", "ur_reldiff_E1": "(u_r - analytic)/analytic",
    "regime_code": "0 validated, 1 extreme curvature, 2 Planck boundary",
}


def write_csv(sim: Simulation, path: Path) -> None:
    cols = sim.columns
    keys = list(cols.keys())
    with open(path, "w", newline="") as fh:
        fh.write(f"# SLAB_GR_Simulation trajectory — metric: {sim.metric.name}; coordinates: {sim.cfg.coordinate_system}\n")
        fh.write(f"# internal units geometrized (G=c=M=1); SI columns marked _m, _s, _years, _SI, _m_s2\n")
        w = csv.writer(fh)
        w.writerow(keys)
        n = len(cols[keys[0]])
        for i in range(n):
            w.writerow([repr(float(cols[k][i])) for k in keys])


def write_hdf5(sim: Simulation, path: Path) -> None:
    import h5py

    cols = sim.columns
    with h5py.File(path, "w") as h:
        h.attrs["metadata_json"] = dumps(metadata(sim))
        h.attrs["summary_json"] = dumps(sim.summary())
        g = h.create_group("trajectory")
        for k, v in cols.items():
            g.create_dataset(k, data=v, compression="gzip")
        gs = h.create_group("segments_raw")
        for seg in sim.segments:
            sg = gs.create_group(f"segment_{seg.index:02d}")
            sg.attrs.update({"slug_from": seg.slug_from, "slug_to": seg.slug_to, "mode": seg.mode,
                             "v_offset": seg.v_offset, "tau_offset": seg.tau_offset, "status": seg.status,
                             "n_rhs_evals": seg.n_rhs_evals})
            sg.create_dataset("x", data=seg.x)
            sg.create_dataset("y", data=seg.y)
            sg.create_dataset("h", data=seg.h)
            sg.create_dataset("err", data=seg.err)
            sg.create_dataset("n_rejected", data=seg.n_rejected)
        gm = h.create_group("milestones")
        for slug, d in sim.milestone_states.items():
            gm.create_dataset(slug, data=np.bytes_(dumps(d)))


def write_json(sim: Simulation, path: Path) -> None:
    payload = {"metadata": metadata(sim), "summary": sim.summary(),
               "milestones": [m.__dict__ for m in sim.milestones],
               "milestone_states": sim.milestone_states,
               "checkpoints": sim.checkpoint_list()}
    Path(path).write_text(dumps(payload))


def render_samples(sim: Simulation, n_samples: int) -> Dict[str, list]:
    """Resample the full-resolution trajectory uniformly in log10(r) for rendering.
    The full-resolution data are preserved in the HDF5/CSV files; the viewer only interpolates."""
    cols = sim.columns
    lr = cols["log10_r_over_rs"]
    # union of uniform log-spaced targets and all milestone radii
    targets = np.linspace(lr[0], lr[-1], n_samples)
    mil = np.array([math.log10(m.r_over_rs) for m in sim.milestones])
    # milestone values can differ from the sampled end points by ~1 ulp: clamp into the data range
    targets = np.clip(np.unique(np.concatenate([targets, mil])), lr.min(), lr.max())[::-1]
    targets = np.unique(targets)[::-1]
    # lr is decreasing; interpolate on reversed arrays
    order = np.argsort(lr)
    out: Dict[str, list] = {}
    keys = [k for k in cols.keys()]
    for k in keys:
        vals = cols[k]
        good = np.isfinite(vals[order])
        if good.sum() < 2:
            out[k] = [None] * len(targets)
            continue
        xi = lr[order][good]
        yi = vals[order][good]
        interp = np.interp(targets, xi, yi, left=np.nan, right=np.nan)
        # do not extrapolate into regions where the column is undefined (e.g. t_schw inside)
        lo, hi = xi.min(), xi.max()
        interp[(targets < lo - 1e-12) | (targets > hi + 1e-12)] = np.nan
        out[k] = [None if not np.isfinite(x) else float(x) for x in interp]
    out["log10_r_over_rs"] = [float(t) for t in targets]
    # radius columns exactly consistent with the log axis (not interpolated)
    out["r_over_rs"] = [float(10.0 ** t) for t in targets]
    out["r_geo"] = [2.0 * x for x in out["r_over_rs"]]
    out["r_m"] = [x * sim.dq.r_s_m for x in out["r_over_rs"]]
    out["regime_code"] = [None if v is None else int(round(v)) for v in out["regime_code"]]
    return out


def write_render_data(sim: Simulation, js_path: Path, json_path: Path, n_samples: int, extra: dict | None = None) -> None:
    samples = render_samples(sim, n_samples)
    meta = metadata(sim)
    ms = sim.milestone_states
    payload = {
        "banner_log": LOG_BANNER,
        "banner_firstperson": "Qualitative visualization — trajectory calculations remain relativistic.",
        "planck_message": PLANCK_MESSAGE,
        "metadata": {k: meta[k] for k in ("project", "generated_utc", "metric", "metric_established_physics",
                                          "coordinate_system", "integrator", "internal_units", "config", "derived",
                                          "regimes", "kruskal_time_origin_note")},
        "summary": sim.summary(),
        "milestones": [{"slug": m.slug, "label": m.label, "r_geo": m.r_geo, "r_m": m.r_m, "r_over_rs": m.r_over_rs,
                        "log10_r_over_rs": math.log10(m.r_over_rs), "kind": m.kind, "note": m.note,
                        "tau_years": ms[m.slug]["tau_total_years"] if m.slug in ms else None,
                        "regime": ms[m.slug]["regime"] if m.slug in ms else None} for m in sim.milestones],
        "samples": samples,
        "n_samples": len(samples["log10_r_over_rs"]),
    }
    if extra:
        payload.update(extra)
    txt = json.dumps(_sanitize(payload), allow_nan=False)
    Path(json_path).write_text(txt)
    Path(js_path).write_text("// Generated by SLAB_GR_Simulation/run_simulation.py — do not edit.\nwindow.SLAB_DATA = " + txt + ";\n")
