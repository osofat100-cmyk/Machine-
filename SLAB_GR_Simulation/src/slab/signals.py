"""Distant-observer received-signal timeline (Schwarzschild exterior only).

EXACT GR RESULTS used here (geometrized, M = 1; derivation in docs/additions/engine.md §2):

* Retarded (outgoing null) time  u = t - r_* = v - 2 r_*(r),  r_* = r + 2M ln|r/2M - 1|.
  Radially outgoing light rays are the lines u = const, so a distant static observer (whose
  proper time equals t far away) receives the radial signal emitted at event (v, r) at
  t_obs = u + const: the reception-time interval between the start emission and the emission at
  this event is  Delta t_receive = u - u_start.
* Along the emitter's worldline du/dtau = u^v - 2 u^r / f = 1 + z  (frequency ratio emitted/received
  for the radially outgoing photon; E = 1: 1 + z = 1/(1 - sqrt(r_s/r))).
* Late-time approach: near the horizon f -> 0 with u^r -> -E_h finite, so 1 + z ~ 2 E_h/f and
  u = v - 2r - 4M ln(r/2M - 1) + ... gives  1 + z ~ C exp(u/4M): the observed signal is redshifted
  exponentially with e-folding time 4GM/c^3 = 1/kappa (surface gravity kappa = 1/4M), while the
  emitter's proper time stays finite.  No signal emitted at r <= r_s ever reaches the observer.

NUMERICAL APPROXIMATION: the emitter state at each requested radius comes from the validated engine,
either by integrating to that radius exactly (the driver's segment integration: event location in
tau mode, end point in ln r mode; method 'exact', any E, L, thrust) or from one ln r integration with
Hairer's dense output (method 'dense', only where the exterior is integrated in ln r).  Near the
horizon f is evaluated as (r - 2M)/r, which is exact to rounding (Sterbenz) - the textbook
1 - 2M/r loses all digits of f at r/r_s - 1 ~ 1e-12.  The reported eps = r/r_s - 1 is the value of
the double-precision radius actually reached (exact subtraction), not the nominal target.
"""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

from .constants import YEAR
from .metric import Schwarzschild
from .geodesic import IV, IR, IUV, IUR, ITAU, IEK, rhs_lnr

TIMELINE_NOTE = ("Distant-observer received-signal timeline (EXACT GR RESULT evaluated on the validated numerical "
                 "worldline; exterior only). eps = r/r_s - 1 of the emission event; t_receive_years = reception-time "
                 "interval on a distant static observer's clock between the radial signal emitted at the start and the "
                 "one emitted at this event, (u - u_start) GM/c^3 with u = v - 2 r_*; one_plus_z = frequency ratio "
                 "emitted/received for that radially outgoing signal (= du/dtau); tau_years = emitter proper time since the "
                 "start; t_schw_years = Schwarzschild coordinate time of emission since the start event. As eps -> 0, "
                 "1+z grows as exp(u/4M) (e-folding time late_time_efold_years = 4GM/c^3), t_receive -> infinity while tau "
                 "converges to the finite horizon-crossing proper time. Signals emitted at r <= r_s never reach the observer "
                 "(not listed). Julian years.")


def f_accurate(r, M: float = 1.0):
    """f = 1 - 2M/r evaluated as (r - 2M)/r: exact subtraction near r = 2M (full relative precision of f)."""
    return (r - 2.0 * M) / r


def retarded_time(metric, v: float, r: float) -> float:
    """u = v - 2 r_*(r) (outgoing null coordinate); NaN at and inside the horizon or for non-Schwarzschild metrics."""
    if not isinstance(metric, Schwarzschild) or not (r > 2.0 * metric.M):
        return math.nan
    return v - 2.0 * metric.tortoise(r)


def one_plus_z(uv: float, ur: float, r: float, M: float = 1.0) -> float:
    """1 + z = u^v - 2 u^r/f for a radially outgoing signal received at infinity (r > 2M)."""
    return uv - 2.0 * ur / f_accurate(r, M)


def one_plus_z_E1_closed_form(r, M: float = 1.0):
    """E = 1 radial infall: 1 + z = 1/(1 - sqrt(2M/r)), evaluated as -1/expm1(-log1p(eps)/2), eps = r/2M - 1."""
    eps = np.asarray(r, dtype=float) / (2.0 * M) - 1.0
    return -1.0 / np.expm1(-0.5 * np.log1p(eps))


def eps_grid(eps_start: float, eps_min: float = 1e-12, points_per_decade: int = 20) -> np.ndarray:
    decades = math.log10(eps_start) - math.log10(eps_min)
    n = max(2, int(math.ceil(decades * points_per_decade)) + 1)
    return np.logspace(math.log10(eps_start), math.log10(eps_min), n)


def _row(metric, y: np.ndarray, v: float, tau: float) -> Dict[str, float]:
    r = float(y[IR])
    return {"r": r, "v": v, "tau": tau, "uv": float(y[IUV]), "ur": float(y[IUR]), "E": float(y[IEK])}


def compute_signal_timeline(sim, eps_min: float = 1e-12, points_per_decade: int = 20, method: str = "exact") -> Dict:
    """Build the received-signal table for the simulation's scenario (general E, L, thrust).

    method 'exact': integrate from the initial state to each requested radius with the driver's own
    segment integration (event-located in tau mode, exact end point in ln r mode).
    method 'dense': a single ln r integration from r0 with Hairer's dense output evaluated at ln r_k
    (only valid when the whole exterior is integrated in ln r: E >= 1 with u^r < 0, L = 0, inward thrust)."""
    m = sim.metric
    M = getattr(m, "M", 1.0)
    rs = 2.0 * M
    y0 = sim.initial_state()
    r0 = float(y0[IR])
    empty = {"note": TIMELINE_NOTE, "method": method, "eps": [], "r_over_rs": [], "t_receive_years": [], "one_plus_z": [],
             "tau_years": [], "t_schw_years": [], "u_ret_geo": [], "late_time_efold_years": 4.0 * M * sim.dq.M_s / YEAR}
    if not isinstance(m, Schwarzschild) or r0 <= rs:
        empty["note"] = TIMELINE_NOTE + " EMPTY: start radius not outside the Schwarzschild horizon."
        return empty
    eps = eps_grid(r0 / rs - 1.0, eps_min, points_per_decade)
    r_targets = rs * (1.0 + eps)
    r_targets[0] = r0
    rows = [_row(m, y0, 0.0, 0.0)]
    status = "complete"
    if method == "dense":
        if sim._choose_mode(y0, r0) != "lnr":
            raise ValueError("dense timeline requires the exterior to be integrated in ln r (E >= 1, L = 0, inward thrust)")
        th = sim.thrust
        if th.alpha != 0.0 and (th.r_on_min > 0.0 or math.isfinite(th.r_on_max)):
            raise ValueError("dense timeline: a thrust window (engine switching) needs the piecewise 'exact' method")
        integ = sim._integrator(mode="lnr")
        xk = np.log(r_targets[1:])
        res = integ.integrate(lambda x, y: rhs_lnr(m, x, y, sim.thrust), math.log(r0), y0.copy(), float(xk[-1]), t_eval=xk)
        for x, yv in zip(res.x_eval, res.y_eval):
            yv = yv.copy()
            yv[IR] = math.exp(x)
            rows.append(_row(m, yv, float(yv[IV]), float(yv[ITAU])))
    elif method == "exact":
        y = y0.copy()
        v_off = tau_off = 0.0
        h_prev = mode_prev = None
        for rt in r_targets[1:]:
            try:
                res, mode = sim.integrate_segment(y, float(rt), h0=h_prev, h0_mode=mode_prev)
            except Exception as exc:          # e.g. a hovering / outward-thrust scenario that never approaches r_s
                status = f"stopped before eps = {rt / rs - 1.0:.3e}: {exc}"
                break
            h_prev, mode_prev = (float(res.h[-1]) if len(res.h) > 1 else None), mode
            ye = res.y[-1].copy()
            v_off += ye[IV]
            tau_off += ye[ITAU]
            rows.append(_row(m, ye, v_off, tau_off))
            y = ye.copy()
            y[IV] = 0.0
            y[ITAU] = 0.0
    else:
        raise ValueError(f"unknown method {method!r}")
    r = np.array([w["r"] for w in rows])
    v = np.array([w["v"] for w in rows])
    tau = np.array([w["tau"] for w in rows])
    uv = np.array([w["uv"] for w in rows])
    ur = np.array([w["ur"] for w in rows])
    keep = r > rs
    r, v, tau, uv, ur = r[keep], v[keep], tau[keep], uv[keep], ur[keep]
    rstar = np.array([m.tortoise(float(x)) for x in r])
    u = v - 2.0 * rstar
    t = v - rstar
    opz = uv - 2.0 * ur / f_accurate(r, M)
    to_yr = sim.dq.M_s / YEAR
    eps_eff = r / rs - 1.0
    out = {
        "note": TIMELINE_NOTE,
        "method": method,
        "status": status,
        "eps": eps_eff.tolist(),
        "r_over_rs": (r / rs).tolist(),
        "t_receive_years": ((u - u[0]) * to_yr).tolist(),
        "one_plus_z": opz.tolist(),
        "tau_years": (tau * to_yr).tolist(),
        "t_schw_years": ((t - t[0]) * to_yr).tolist(),
        "u_ret_geo": u.tolist(),
        "tau_geo": tau.tolist(),
        "t_receive_geo": (u - u[0]).tolist(),
        "E_killing": [w["E"] for w, k in zip(rows, keep) if k],
        "late_time_efold_years": 4.0 * M * to_yr,
        "late_time_efold_geo": 4.0 * M,
        "points_per_decade": points_per_decade,
        "eps_min_requested": eps_min,
    }
    return out


def late_time_slopes(tl: Dict, eps_below: float = 1e-8) -> Dict[str, float]:
    """Diagnostics of the late-time behaviour from a timeline dict (geometrized):
    d ln(1+z)/du (-> 1/4M), reception-time increment per decade of eps (-> 4M ln 10), and the
    emitter proper-time increment over the same range (-> 0)."""
    eps = np.array(tl["eps"])
    u = np.array(tl["t_receive_geo"])
    lz = np.log(np.array(tl["one_plus_z"]))
    tau = np.array(tl["tau_geo"])
    sel = eps <= eps_below
    if sel.sum() < 3:
        return {"n": int(sel.sum())}
    i0, i1 = np.where(sel)[0][0], np.where(sel)[0][-1]
    slope = (lz[i1] - lz[i0]) / (u[i1] - u[i0])
    decades = math.log10(eps[i0] / eps[i1])
    local = np.diff(lz[sel]) / np.diff(u[sel])
    return {
        "n": int(sel.sum()),
        "eps_range": [float(eps[i0]), float(eps[i1])],
        "dln1pz_du": float(slope),
        "dln1pz_du_times_4M": float(slope * 4.0),
        "max_local_dev_of_4M_dln1pz_du_from_1": float(np.max(np.abs(4.0 * local - 1.0))),
        "t_receive_per_decade_geo": float((u[i1] - u[i0]) / decades),
        "t_receive_per_decade_expected_4Mln10": 4.0 * math.log(10.0),
        "tau_increment_over_range_geo": float(tau[i1] - tau[i0]),
        "t_receive_increment_over_range_geo": float(u[i1] - u[i0]),
    }
