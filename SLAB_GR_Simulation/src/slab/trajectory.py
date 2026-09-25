"""Milestone-segmented integration of the infalling worldline + post-processing.

The driver integrates from milestone to milestone (stopping EXACTLY at each
milestone radius through the integrator's event location), writes a
versioned checkpoint after every segment, and stores each segment's raw
step records so that a later session can resume from the newest checkpoint
without recomputing earlier segments.
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from . import constants as C
from .constants import DerivedQuantities
from .units import Units
from .metric import Schwarzschild, StaticSphericalMetric, V, R
from .geodesic import (Thrust, rhs_tau, rhs_lnr, initial_state_radial, energy, energy_conditioning_scale,
                       angular_momentum, norm, norm_conditioning_scale, proper_time_to_center,
                       four_acceleration, RadialInfallE1, IV, IR, ITH, IPH, IUV, IUR, IUTH, IUPH, ITAU, IEK, NSTATE, STATE_NAMES)
from .integrators import DormandPrince54, IntegrationResult
from .curvature import (kretschmann_closed_form, tidal_tensor, tidal_eigenvalues_frame, tidal_eigenvalues_radial_closed_form,
                        log10_kretschmann_schwarzschild)
from .milestones import Milestone, build_milestones
from .checkpoints import write_checkpoint, config_hash, dumps
from .accelerated import inertial_diff_along_thrust_SI
from .signals import compute_signal_timeline, f_accurate, retarded_time

REGIME_VALIDATED = "CLASSICAL GR — VALIDATED"
REGIME_EXTREME = "CLASSICAL GR — EXTREME CURVATURE"
REGIME_PLANCK = "PLANCK-CURVATURE BOUNDARY"
REGIME_SPECULATIVE = "SPECULATIVE QUANTUM MODEL"
PLANCK_MESSAGE = ("PLANCK-CURVATURE THRESHOLD REACHED.\n"
                  "CLASSICAL GENERAL RELATIVITY IS NO LONGER RELIABLE.\n"
                  "NO EXPERIMENTALLY VERIFIED THEORY DETERMINES THE CONTINUATION.")


@dataclass
class SimulationConfig:
    M_solar: float = 1.0e18
    r0_over_rs: float = 100.0
    E: float = 1.0                      # specific energy (E = 1: rest at infinity)
    L_over_M: float = 0.0               # specific angular momentum in units of GM/c
    thrust_alpha_SI: float = 0.0        # proper acceleration [m/s^2]; > 0 inward
    thrust_r_on_min_over_rs: float = 0.0
    thrust_r_on_max_over_rs: float = math.inf
    body_length_m: float = 2.0          # proper length for tidal-difference display
    rtol: float = 1e-12
    atol: float = 1e-14                 # applied to v_seg, theta, phi, tau_seg (see notes)
    max_step_lnr: float = 0.05          # max step in ln r (interior / lnr mode)
    max_dr_over_r_tau: float = 0.05     # max |dr|/r per step in tau mode
    extreme_curvature_length_m: float = 1.0e4   # K^(-1/4) below which GR is beyond direct tests (labelling convention)
    planck_boundary_lengths: float = 10.0       # K^(-1/4) <= this * l_P -> 'PLANCK-CURVATURE BOUNDARY'
    include_isco: bool = True
    include_photon_sphere: bool = True
    render_samples: int = 3000
    coordinate_system: str = "ingoing Eddington–Finkelstein (v, r, theta, phi)"
    integrator: str = "Dormand–Prince RK5(4), adaptive, FSAL, PI step control"
    notes: str = ""

    @classmethod
    def from_json(cls, path: Path) -> "SimulationConfig":
        d = json.loads(Path(path).read_text())
        d = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        for k in ("thrust_r_on_max_over_rs",):
            if isinstance(d.get(k), str):
                d[k] = float(d[k])
        return cls(**d)

    def to_dict(self) -> dict:
        d = asdict(self)
        if math.isinf(d["thrust_r_on_max_over_rs"]):
            d["thrust_r_on_max_over_rs"] = "inf"
        return d


@dataclass
class SegmentRecord:
    index: int
    slug_from: str
    slug_to: str
    mode: str
    v_offset: float
    tau_offset: float
    x: np.ndarray
    y: np.ndarray
    h: np.ndarray
    err: np.ndarray
    n_rejected: np.ndarray
    n_rhs_evals: int
    status: str
    wall_time_s: float


def _concat_results(parts: List[IntegrationResult]) -> IntegrationResult:
    """Join consecutive integration pieces (each starting where the previous ended) into one record."""
    if len(parts) == 1:
        return parts[0]
    first = parts[0]
    xs = [first.x] + [p.x[1:] for p in parts[1:]]
    ys = [first.y] + [p.y[1:] for p in parts[1:]]
    hs = [first.h] + [p.h[1:] for p in parts[1:]]
    es = [first.err] + [p.err[1:] for p in parts[1:]]
    rj = [first.n_rejected] + [p.n_rejected[1:] for p in parts[1:]]
    return IntegrationResult(
        x=np.concatenate(xs), y=np.concatenate(ys), h=np.concatenate(hs), err=np.concatenate(es), n_rejected=np.concatenate(rj),
        n_rhs_evals=sum(p.n_rhs_evals for p in parts), n_accepted=sum(p.n_accepted for p in parts),
        n_rejected_total=sum(p.n_rejected_total for p in parts), terminated_by_event=parts[-1].terminated_by_event,
        status="+".join(p.status for p in parts), max_err=max(p.max_err for p in parts), min_h=min(p.min_h for p in parts),
        max_h=max(p.max_h for p in parts))


class Simulation:
    def __init__(self, config: SimulationConfig, metric: Optional[StaticSphericalMetric] = None,
                 project_dir: Optional[Path] = None, verbose: bool = True):
        self.cfg = config
        self.dq = DerivedQuantities(config.M_solar)
        self.units = Units(self.dq)
        self.metric = metric if metric is not None else Schwarzschild(M=1.0)
        self.project_dir = Path(project_dir) if project_dir else None
        self.verbose = verbose
        self.thrust = Thrust(alpha=self.units.accel_from_SI(config.thrust_alpha_SI),
                             r_on_min=2.0 * config.thrust_r_on_min_over_rs,
                             r_on_max=2.0 * config.thrust_r_on_max_over_rs)
        self.milestones: List[Milestone] = build_milestones(self.dq, config.r0_over_rs,
                                                            config.extreme_curvature_length_m,
                                                            config.include_isco, config.include_photon_sphere)
        self.segments: List[SegmentRecord] = []
        self.stopped_early = False
        self.milestone_states: Dict[str, dict] = {}
        self.config_hash = config_hash(config.to_dict())
        self.checkpoint_paths: List[str] = []

    # ------------------------------------------------------------------
    def log(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    # ------------------------------------------------------------------
    def initial_state(self) -> np.ndarray:
        r0 = self.milestones[0].r_geo
        return initial_state_radial(self.metric, r0, self.cfg.E, self.cfg.L_over_M)

    def _choose_mode(self, y: np.ndarray, r_from: float) -> str:
        r_s = 2.0
        if y[IUR] >= 0.0:
            return "tau"
        if r_from <= r_s:
            return "lnr"
        if self.cfg.L_over_M == 0.0 and self.thrust.alpha >= 0.0:
            return "lnr"
        return "tau"

    def _integrator(self, rtol: Optional[float] = None, atol: Optional[float] = None, mode: str = "lnr") -> DormandPrince54:
        rtol = self.cfg.rtol if rtol is None else rtol
        atol = self.cfg.atol if atol is None else atol
        # relative-only control (atol = 0) for v_seg, r, u^v, u^r, tau_seg: they span up to 40 decades
        # (per-segment v/tau increments are ~1e-55 M deep inside); atol only for the O(1) angles/E
        atol_vec = np.array([0.0, 0.0, atol, atol, 0.0, 0.0, atol, atol, 0.0, atol])
        if mode == "lnr":
            return DormandPrince54(rtol=rtol, atol=atol_vec, max_step=self.cfg.max_step_lnr)
        frac = self.cfg.max_dr_over_r_tau

        def max_step_fn(x, y):
            r = y[IR]
            ur = abs(y[IUR])
            h1 = frac * r / ur if ur > 0 else math.inf
            h2 = frac * math.sqrt(r**3 / self.metric.M if hasattr(self.metric, "M") else r**3)
            return min(h1, h2)

        return DormandPrince54(rtol=rtol, atol=atol_vec, max_step_fn=max_step_fn)

    # ------------------------------------------------------------------
    def integrate_segment(self, y_start: np.ndarray, r_to: float, rtol=None, atol=None,
                          h0: Optional[float] = None, h0_mode: Optional[str] = None) -> tuple[IntegrationResult, str]:
        """Integrate from the state y_start (at r = y_start[IR]) to r = r_to (< r_start).
        h0/h0_mode: last accepted step of the previous segment (reused if the mode is unchanged).

        If an edge of the thrust window (engine switching on/off, a discontinuity of the right-hand side)
        lies strictly inside the segment, the segment is integrated in pieces that end exactly on the edge
        (the error controller cannot step across a jump in dy/dx) and the pieces are concatenated."""
        r_from = float(y_start[IR])
        edges = sorted({e for e in (self.thrust.r_on_max, self.thrust.r_on_min)
                        if self.thrust.alpha != 0.0 and math.isfinite(e) and r_to < e < r_from}, reverse=True)
        if not edges:
            return self._integrate_piece(y_start, r_to, rtol, atol, h0, h0_mode)
        pieces = []
        y = y_start.copy()
        mode_first = None
        for target in edges + [r_to]:
            res, mode = self._integrate_piece(y, target, rtol, atol, h0, h0_mode, keep_clocks=bool(pieces),
                                              x_offset=(pieces[-1][0].x[-1] if pieces and pieces[-1][1] == "tau" else None))
            pieces.append((res, mode))
            mode_first = mode_first or mode
            y = res.y[-1].copy()
            y[IR] = target
            h0, h0_mode = (float(res.h[-1]) if len(res.h) > 1 else None), mode
        return _concat_results([p[0] for p in pieces]), mode_first if len({p[1] for p in pieces}) == 1 else "+".join(p[1] for p in pieces)

    def _integrate_piece(self, y_start: np.ndarray, r_to: float, rtol=None, atol=None,
                         h0: Optional[float] = None, h0_mode: Optional[str] = None, keep_clocks: bool = False,
                         x_offset: Optional[float] = None) -> tuple[IntegrationResult, str]:
        r_from = y_start[IR]
        mode = self._choose_mode(y_start, r_from)
        metric = self.metric
        # engine state decided ONCE per piece (pieces never straddle a window edge): evaluating the window
        # per stage would flip it at the last ulp of a piece that ends on an edge (a jump the step control
        # can only approach Zeno-fashion)
        thrust = Thrust(alpha=self.thrust.alpha) if self.thrust.active(math.sqrt(r_from * r_to)) else None
        y0 = y_start.copy()
        if not keep_clocks:
            y0[IV] = 0.0
            y0[ITAU] = 0.0
        integ = self._integrator(rtol, atol, mode)
        h_start = h0 if (h0 is not None and h0_mode == mode and h0 > 0) else None
        if mode == "lnr":
            x0, x1 = math.log(r_from), math.log(r_to)

            def fun(x, y):
                return rhs_lnr(metric, x, y, thrust)      # uses r = exp(x); the state's r is only a diagnostic copy

            res = integ.integrate(fun, x0, y0, x1, h0=h_start)
            res.y[:, IR] = np.exp(res.x)   # r is the independent variable: exact
        else:
            def fun(x, y):
                return rhs_tau(metric, y, thrust)

            def event(x, y):
                return y[IR] - r_to

            # generous upper bound on proper time: free-fall time from r_from plus margin
            tau_max = 20.0 * (r_from ** 1.5) + 1e3
            x0 = 0.0 if x_offset is None else float(x_offset)
            res = integ.integrate(fun, x0, y0, x0 + tau_max, event=event, h0=h_start)
            if not res.terminated_by_event:
                raise RuntimeError(f"tau-mode segment did not reach r = {r_to}: status {res.status}")
        return res, mode

    # ------------------------------------------------------------------
    def run(self, resume_from: Optional[dict] = None, stop_after: Optional[str] = None) -> None:
        cfg = self.cfg
        self.stopped_early = False
        if resume_from is None:
            y = self.initial_state()
            v_off, tau_off = 0.0, 0.0
            start_idx = 0
            self._record_milestone(0, y, v_off, tau_off, "initial")
            self._checkpoint(0, y, v_off, tau_off)
        else:
            y = np.array(resume_from["state_geometrized"], dtype=float)
            v_off = float(resume_from["v_offset"])
            tau_off = float(resume_from["tau_offset"])
            start_idx = int(resume_from["milestone_index"])
            # segments beyond the resume point (from an older, longer run of the same config) are stale
            self.segments = [sg for sg in self.segments if sg.index < start_idx]
            if self.milestones[start_idx].slug not in self.milestone_states:
                self._record_milestone(start_idx, y, v_off, tau_off, "resumed")
            else:
                self.milestone_states[self.milestones[start_idx].slug]["status"] = "resumed"
        h_prev, mode_prev = None, None
        for i in range(start_idx, len(self.milestones) - 1):
            m_from, m_to = self.milestones[i], self.milestones[i + 1]
            t0 = time.time()
            res, mode = self.integrate_segment(y, m_to.r_geo, h0=h_prev, h0_mode=mode_prev)
            h_prev, mode_prev = (float(res.h[-1]) if len(res.h) > 1 else None), mode
            wall = time.time() - t0
            seg = SegmentRecord(i, m_from.slug, m_to.slug, mode, v_off, tau_off, res.x, res.y, res.h, res.err,
                                res.n_rejected, res.n_rhs_evals, res.status, wall)
            self.segments.append(seg)
            y_end = res.y[-1].copy()
            v_off += y_end[IV]
            tau_off += y_end[ITAU]
            y = y_end.copy()
            y[IV] = 0.0
            y[ITAU] = 0.0
            y[IR] = m_to.r_geo  # exact milestone radius (event location accuracy ~1e-15 relative)
            self.log(f"  segment {i:2d} {m_from.slug:>18s} -> {m_to.slug:<18s} mode={mode} steps={res.n_accepted:6d} "
                     f"rej={res.n_rejected_total:4d} maxerr={res.max_err:.2e} wall={wall:.2f}s "
                     f"tau_total={self.units.t_to_years(tau_off):.6e} yr")
            self._record_milestone(i + 1, y, v_off, tau_off, "reached", dv_segment=y_end[IV], dtau_segment=y_end[ITAU])
            if self.project_dir is not None:
                self._save_segment(seg)       # segment archive first, then the checkpoint that points past it
            self._checkpoint(i + 1, y, v_off, tau_off)
            if stop_after is not None and m_to.slug == stop_after:
                self.stopped_early = True
                self.log(f"stopping after milestone '{stop_after}' as requested (checkpoint written)")
                return
        self.log(PLANCK_MESSAGE)

    # ------------------------------------------------------------------
    def _record_milestone(self, idx: int, y: np.ndarray, v_off: float, tau_off: float, status: str,
                          dv_segment: float = 0.0, dtau_segment: float = 0.0) -> None:
        m = self.milestones[idx]
        d = self.describe_state(y, v_off + y[IV], tau_off + y[ITAU])
        d.update({"milestone_index": idx, "slug": m.slug, "label": m.label, "status": status,
                  "dv_segment_geo": dv_segment, "dtau_segment_geo": dtau_segment,
                  "dtau_segment_years": self.units.t_to_years(dtau_segment)})
        self.milestone_states[m.slug] = d

    def _checkpoint(self, idx: int, y: np.ndarray, v_off: float, tau_off: float) -> None:
        if self.project_dir is None:
            return
        m = self.milestones[idx]
        payload = {
            "project": "SLAB_GR_Simulation",
            "milestone_index": idx,
            "milestone_slug": m.slug,
            "milestone_label": m.label,
            "n_milestones": len(self.milestones),
            "config": self.cfg.to_dict(),
            "config_hash": self.config_hash,
            "metric": self.metric.name,
            "coordinate_system": self.cfg.coordinate_system,
            "state_names": STATE_NAMES,
            "state_geometrized": y.tolist(),
            "v_offset": v_off,
            "tau_offset": tau_off,
            "state_SI": self.describe_state(y, v_off + y[IV], tau_off + y[ITAU]),
            "regime": self.milestone_states[m.slug]["regime"],
            "is_final": idx == len(self.milestones) - 1,
        }
        p = write_checkpoint(self.project_dir / "checkpoints", idx, m.slug, payload)
        self.checkpoint_paths.append(str(p.relative_to(self.project_dir)))
        state_path = self.project_dir / "simulation_state.json"
        state = {
            "project": "SLAB_GR_Simulation",
            "status": "complete" if payload["is_final"] else "in_progress",
            "latest_checkpoint": str(p.relative_to(self.project_dir)),
            "milestone_index": idx,
            "milestone_slug": m.slug,
            "n_milestones": len(self.milestones),
            "config_hash": self.config_hash,
            "regime": payload["regime"],
            "r_m": payload["state_SI"]["r_m"],
            "r_over_rs": payload["state_SI"]["r_over_rs"],
            "tau_total_years": payload["state_SI"]["tau_total_years"],
            "how_to_resume": "python run_simulation.py --resume [--tag <tag> | --out-dir <dir>]   (config is taken from the checkpoint)",
            "updated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        }
        state_path.write_text(dumps(state))

    def _save_segment(self, seg: SegmentRecord) -> None:
        """Segment archives are versioned like checkpoints (never overwritten)."""
        d = self.project_dir / "data" / "segments"
        d.mkdir(parents=True, exist_ok=True)
        version = 1
        while (d / f"segment_{seg.index:02d}_{seg.slug_from}_to_{seg.slug_to}_{self.config_hash}_v{version:03d}.npz").exists():
            version += 1
        np.savez_compressed(d / f"segment_{seg.index:02d}_{seg.slug_from}_to_{seg.slug_to}_{self.config_hash}_v{version:03d}.npz",
                            x=seg.x, y=seg.y, h=seg.h, err=seg.err, n_rejected=seg.n_rejected,
                            meta=np.array(json.dumps({"index": seg.index, "slug_from": seg.slug_from, "slug_to": seg.slug_to,
                                                      "mode": seg.mode, "v_offset": seg.v_offset, "tau_offset": seg.tau_offset,
                                                      "n_rhs_evals": seg.n_rhs_evals, "status": seg.status,
                                                      "wall_time_s": seg.wall_time_s})))

    def checkpoint_list(self) -> List[str]:
        """All checkpoint files of this configuration present on disk (newest version per milestone)."""
        if self.project_dir is None:
            return list(self.checkpoint_paths)
        out = []
        for p in sorted((self.project_dir / "checkpoints").glob("ckpt_*_v*.json")):
            try:
                if json.loads(p.read_text()).get("config_hash") == self.config_hash:
                    out.append(str(p.relative_to(self.project_dir)))
            except Exception:
                continue
        return out

    def load_segments(self) -> None:
        """Reload previously integrated segments (for --resume / re-export) and rebuild the milestone table."""
        d = self.project_dir / "data" / "segments"
        latest: Dict[int, tuple] = {}
        for p in sorted(d.glob(f"segment_*_{self.config_hash}_v*.npz")):
            z = np.load(p, allow_pickle=False)
            meta = json.loads(str(z["meta"]))
            ver = int(p.stem.rsplit("_v", 1)[1])
            if meta["index"] not in latest or ver > latest[meta["index"]][0]:
                latest[meta["index"]] = (ver, SegmentRecord(meta["index"], meta["slug_from"], meta["slug_to"], meta["mode"],
                                                            meta["v_offset"], meta["tau_offset"], z["x"], z["y"], z["h"], z["err"],
                                                            z["n_rejected"], meta["n_rhs_evals"], meta["status"], meta["wall_time_s"]))
        self.segments = [latest[k][1] for k in sorted(latest)]
        # contiguity: indices 0..n-1 and each segment starts where the previous one ended
        for k, sg in enumerate(self.segments):
            if sg.index != k:
                raise RuntimeError(f"segment archives are not contiguous: missing segment {k} (found {sorted(latest)})")
            if k > 0:
                prev = self.segments[k - 1]
                r_prev_end = self.milestones[k].r_geo
                if abs(sg.y[0, IR] / r_prev_end - 1.0) > 1e-9 or abs(sg.v_offset - (prev.v_offset + prev.y[-1, IV])) > 1e-9 * max(1.0, abs(sg.v_offset)):
                    raise RuntimeError(f"segment {k} does not start where segment {k-1} ended")
        self.milestone_states = {}
        for seg in self.segments:
            if seg.index == 0:
                self._record_milestone(0, seg.y[0], seg.v_offset, seg.tau_offset, "initial")
            y_end = seg.y[-1].copy()
            y_state = y_end.copy()
            y_state[IV] = 0.0
            y_state[ITAU] = 0.0
            y_state[IR] = self.milestones[seg.index + 1].r_geo
            self._record_milestone(seg.index + 1, y_state, seg.v_offset + y_end[IV], seg.tau_offset + y_end[ITAU], "reached",
                                   dv_segment=y_end[IV], dtau_segment=y_end[ITAU])

    # ------------------------------------------------------------------
    def regime(self, r_geo: float) -> str:
        K = kretschmann_closed_form(self.metric, r_geo)
        K_SI = self.units.kretschmann_to_SI(K)
        ell = K_SI ** (-0.25)
        if ell <= self.cfg.planck_boundary_lengths * C.l_P:
            return REGIME_PLANCK
        if ell <= self.cfg.extreme_curvature_length_m:
            return REGIME_EXTREME
        return REGIME_VALIDATED

    def describe_state(self, y: np.ndarray, v_total: float, tau_total: float) -> dict:
        """SI description of one state (used for milestones/checkpoints)."""
        m, u = self.metric, self.units
        r = y[IR]
        K = kretschmann_closed_form(m, r)
        K_SI = u.kretschmann_to_SI(K)
        lam = tidal_eigenvalues_frame(m, r, y[ITH], y[IUV:IUPH + 1])
        kr = m.kruskal(v_total, r) if isinstance(m, Schwarzschild) else {}
        Lb = self.cfg.body_length_m
        d = {
            "r_geo": r, "r_m": u.r_to_SI(r), "r_over_rs": r / 2.0, "log10_r_over_rs": math.log10(r / 2.0),
            "v_total_geo": v_total, "tau_total_geo": tau_total,
            "tau_total_s": u.t_to_SI(tau_total), "tau_total_years": u.t_to_years(tau_total),
            "u_v": y[IUV], "u_r": y[IUR], "u_theta": y[IUTH], "u_phi": y[IUPH],
            "E": energy(m, y), "E_killing": y[IEK], "L": angular_momentum(y), "norm_residual": norm(m, y) + 1.0,
            "norm_residual_conditioned": (norm(m, y) + 1.0) / norm_conditioning_scale(m, y),
            "log10_K_SI": math.log10(K_SI), "log10_K_over_K_planck": math.log10(K_SI / self.dq.K_planck),
            "curvature_length_m": K_SI ** (-0.25),
            "tidal_eigenvalues_SI_per_m": [u.tidal_to_SI(x) for x in lam],
            "radial_stretch_accel_m_s2": -u.tidal_to_SI(lam[0]) * Lb,
            "transverse_compress_accel_m_s2": -u.tidal_to_SI(lam[-1]) * Lb,
            "t_schwarzschild_geo": m.schwarzschild_t(v_total, r) if isinstance(m, Schwarzschild) else float("nan"),
            "kruskal": kr,
            "regime": self.regime(r),
        }
        return d

    # ------------------------------------------------------------------
    def postprocess(self) -> Dict[str, np.ndarray]:
        """Concatenate segments and compute all derived quantities per accepted step."""
        m, u, dq, cfg = self.metric, self.units, self.dq, self.cfg
        rows: List[dict] = []
        r_s = 2.0
        ref = RadialInfallE1(1.0)
        tau_h: Optional[float] = None
        for seg in self.segments:
            for k in range(len(seg.x)):
                if k == 0 and seg.index > 0:
                    continue  # duplicate of previous segment's end point
                y = seg.y[k]
                r = y[IR]
                v = seg.v_offset + y[IV]
                tau = seg.tau_offset + y[ITAU]
                rows.append({"seg": seg.index, "mode": seg.mode, "x": seg.x[k], "h": seg.h[k], "err": seg.err[k],
                             "nrej": seg.n_rejected[k], "y": y, "v": v, "tau": tau})
        N = len(rows)
        self.E0 = energy(m, rows[0]["y"])
        cols: Dict[str, np.ndarray] = {k: np.full(N, np.nan) for k in [
            "segment", "step_h", "err_estimate", "n_rejected", "mode_is_lnr",
            "r_geo", "r_m", "r_over_rs", "log10_r_over_rs", "v_geo", "t_ef_geo", "t_schw_geo", "t_schw_years",
            "tau_geo", "tau_s", "tau_years", "tau_since_horizon_geo", "tau_since_horizon_years", "tau_to_center_est_geo",
            "tau_to_center_est_years", "theta", "phi", "u_v", "u_r", "u_theta", "u_phi", "u_lower_v", "u_lower_r",
            "a_v", "a_r", "a_magnitude_SI", "E", "E_killing", "E_conditioning_scale", "E_drift_conditioned", "L", "norm_residual", "norm_conditioning_scale", "norm_residual_conditioned",
            "K_geo_log10", "K_SI_log10", "K_over_Kplanck_log10", "curvature_length_m",
            "tidal_lambda1_geo", "tidal_lambda2_geo", "tidal_lambda3_geo",
            "tidal_radial_SI_per_m", "tidal_transverse_SI_per_m", "radial_stretch_m_s2", "transverse_compress_m_s2",
            "tidal_radial_newtonian_SI_per_m", "tidal_closed_form_reldiff",
            "inertial_diff_radial_m_s2", "radial_total_diff_m_s2",
            "lc_out_drdtEF", "lc_in_drdtEF", "worldline_drdtEF", "dr_dt_schw", "redshift_1pz_to_infinity",
            "u_ret_geo", "t_receive_years",
            "gamma_rel_to_E1_faller", "v_rel_to_E1_faller",
            "kruskal_U", "kruskal_V", "kruskal_T", "kruskal_X", "penrose_Ut", "penrose_Vt", "penrose_T", "penrose_X",
            "ur_analytic_E1", "uv_analytic_E1", "ur_reldiff_E1", "uv_reldiff_E1", "regime_code"]}
        regime_names = {0: REGIME_VALIDATED, 1: REGIME_EXTREME, 2: REGIME_PLANCK}
        Lb = cfg.body_length_m
        a_thrust_SI = u.accel_to_SI(abs(self.thrust.alpha))
        # Kruskal/Penrose diagram: use the Schwarzschild time-translation symmetry to put the
        # horizon crossing at v = 0 (V_K = 1); otherwise exp(v/4M) overflows for v ~ 10^3 M.
        self.v_ref_kruskal = 0.0
        for row in rows:
            if row["y"][IR] <= r_s:
                self.v_ref_kruskal = row["v"]
                break
        for i, row in enumerate(rows):
            y = row["y"]
            r = y[IR]
            v = row["v"]
            tau = row["tau"]
            f = m.f(r)
            cols["segment"][i] = row["seg"]
            cols["step_h"][i] = row["h"]
            cols["err_estimate"][i] = row["err"]
            cols["n_rejected"][i] = row["nrej"]
            cols["mode_is_lnr"][i] = 1.0 if row["mode"] == "lnr" else 0.0
            cols["r_geo"][i] = r
            cols["r_m"][i] = u.r_to_SI(r)
            cols["r_over_rs"][i] = r / r_s
            cols["log10_r_over_rs"][i] = math.log10(r / r_s)
            cols["v_geo"][i] = v
            cols["t_ef_geo"][i] = v - r
            ts = m.schwarzschild_t(v, r) if isinstance(m, Schwarzschild) else float("nan")
            cols["t_schw_geo"][i] = ts
            cols["t_schw_years"][i] = u.t_to_years(ts) if math.isfinite(ts) else ts
            cols["tau_geo"][i] = tau
            cols["tau_s"][i] = u.t_to_SI(tau)
            cols["tau_years"][i] = u.t_to_years(tau)
            if r <= r_s and tau_h is None:
                tau_h = tau
            cols["tau_since_horizon_geo"][i] = (tau - tau_h) if tau_h is not None else float("nan")
            cols["tau_since_horizon_years"][i] = u.t_to_years(tau - tau_h) if tau_h is not None else float("nan")
            # remaining proper time to r = 0: classical-GR extrapolation assuming free fall from the current
            # (E, L).  Closed form for E = 1, L = 0; general quadrature otherwise (thrust ignored from here on).
            if y[IEK] == 1.0 and y[IUPH] == 0.0 and y[IUTH] == 0.0:
                trem = ref.tau_to_center(r)
            else:
                trem = proper_time_to_center(m, r, y[IEK], angular_momentum(y), y[ITH])
            cols["theta"][i] = y[ITH]
            cols["phi"][i] = y[IPH]
            cols["tau_to_center_est_geo"][i] = trem
            cols["tau_to_center_est_years"][i] = u.t_to_years(trem)
            uv, ur, uth, uph = y[IUV], y[IUR], y[IUTH], y[IUPH]
            cols["u_v"][i], cols["u_r"][i], cols["u_theta"][i], cols["u_phi"][i] = uv, ur, uth, uph
            cols["u_lower_v"][i] = -f * uv + ur
            cols["u_lower_r"][i] = uv
            a = four_acceleration(m, y, self.thrust)
            cols["a_v"][i], cols["a_r"][i] = a[V], a[R]
            cols["a_magnitude_SI"][i] = u.accel_to_SI(abs(self.thrust.alpha)) if self.thrust.active(r) else 0.0
            cols["E"][i] = energy(m, y)
            cols["E_killing"][i] = y[IEK]
            cols["E_conditioning_scale"][i] = energy_conditioning_scale(m, y)
            cols["E_drift_conditioned"][i] = (energy(m, y) - y[IEK]) / energy_conditioning_scale(m, y)
            cols["L"][i] = angular_momentum(y)
            cols["norm_residual"][i] = norm(m, y) + 1.0
            cols["norm_conditioning_scale"][i] = norm_conditioning_scale(m, y)
            cols["norm_residual_conditioned"][i] = (norm(m, y) + 1.0) / norm_conditioning_scale(m, y)
            K = kretschmann_closed_form(m, r)
            lK = math.log10(K)
            cols["K_geo_log10"][i] = lK
            lK_SI = u.log10_kretschmann_to_SI(lK)
            cols["K_SI_log10"][i] = lK_SI
            cols["K_over_Kplanck_log10"][i] = lK_SI - math.log10(dq.K_planck)
            cols["curvature_length_m"][i] = 10.0 ** (-0.25 * lK_SI)
            lam = tidal_eigenvalues_frame(m, r, y[ITH], y[IUV:IUPH + 1])
            cols["tidal_lambda1_geo"][i], cols["tidal_lambda2_geo"][i], cols["tidal_lambda3_geo"][i] = lam
            lam_SI = [u.tidal_to_SI(x) for x in lam]
            cols["tidal_radial_SI_per_m"][i] = lam_SI[0]          # most negative eigenvalue: stretching axis
            cols["tidal_transverse_SI_per_m"][i] = lam_SI[-1]     # positive: compression
            cols["radial_stretch_m_s2"][i] = -lam_SI[0] * Lb
            cols["transverse_compress_m_s2"][i] = -lam_SI[-1] * Lb
            # accelerated observer's frame: inertial differential term -a (a.xi) along the thrust axis
            # (the thrust axis n is the radial tidal eigen-direction, so the two add; docs/additions/engine.md §1)
            inert = inertial_diff_along_thrust_SI(a_thrust_SI, Lb) if self.thrust.active(r) else 0.0
            cols["inertial_diff_radial_m_s2"][i] = inert
            cols["radial_total_diff_m_s2"][i] = cols["radial_stretch_m_s2"][i] + inert
            cols["tidal_radial_newtonian_SI_per_m"][i] = 2.0 * dq.GM / u.r_to_SI(r) ** 3
            if y[IUPH] == 0.0 and y[IUTH] == 0.0:
                cf = tidal_eigenvalues_radial_closed_form(1.0, r)
                cols["tidal_closed_form_reldiff"][i] = max(abs(lam[0] - cf[0]) / abs(cf[0]), abs(lam[2] - cf[2]) / abs(cf[2]))
            elif r * r * (y[IUPH] ** 2 + y[IUTH] ** 2) < 1e40:
                # cross-check against the explicit index contraction where it is numerically meaningful
                with np.errstate(all="ignore"):
                    try:
                        lam_c = np.sort(tidal_tensor(m, r, y[ITH], y[IUV:IUPH + 1], E=y[IEK])["eigenvalues"])
                        cols["tidal_closed_form_reldiff"][i] = float(np.max(np.abs(lam_c - lam) / np.max(np.abs(lam))))
                    except Exception:
                        pass
            out_slope, in_slope = m.null_slopes_ef_time(r)
            cols["lc_out_drdtEF"][i] = out_slope
            cols["lc_in_drdtEF"][i] = in_slope
            cols["worldline_drdtEF"][i] = ur / (uv - ur)
            if r > r_s:
                # f from (r - 2M)/r: exact subtraction, full relative precision of f next to the horizon
                fa = f_accurate(r, getattr(m, "M", 1.0)) if isinstance(m, Schwarzschild) else f
                dtdtau = uv - ur / fa
                cols["dr_dt_schw"][i] = ur / dtdtau
                cols["redshift_1pz_to_infinity"][i] = uv - 2.0 * ur / fa     # = du/dtau (outgoing null coordinate)
                cols["u_ret_geo"][i] = retarded_time(m, v, r)
            # velocity relative to the local E=1 radial free-faller (always < c)
            uff = np.array([ref.uv(r), ref.ur(r), 0.0, 0.0])
            gam = -m.dot(r, y[ITH], y[IUV:IUPH + 1], uff)
            cols["gamma_rel_to_E1_faller"][i] = gam
            cols["v_rel_to_E1_faller"][i] = math.sqrt(max(0.0, 1.0 - 1.0 / (gam * gam)))
            if isinstance(m, Schwarzschild):
                kr = m.kruskal(v - self.v_ref_kruskal, r)
                cols["kruskal_U"][i], cols["kruskal_V"][i] = kr["U"], kr["V"]
                cols["kruskal_T"][i], cols["kruskal_X"][i] = kr["T"], kr["X"]
                cols["penrose_Ut"][i], cols["penrose_Vt"][i] = kr["Ut"], kr["Vt"]
                cols["penrose_T"][i], cols["penrose_X"][i] = kr["Tt"], kr["Xt"]
                cols["ur_analytic_E1"][i] = ref.ur(r)
                cols["uv_analytic_E1"][i] = ref.uv(r)
                cols["ur_reldiff_E1"][i] = (ur - ref.ur(r)) / ref.ur(r)
                cols["uv_reldiff_E1"][i] = (uv - ref.uv(r)) / ref.uv(r)
            reg = self.regime(r)
            cols["regime_code"][i] = {REGIME_VALIDATED: 0, REGIME_EXTREME: 1, REGIME_PLANCK: 2}[reg]
        # received-signal clock of a distant static observer: (u - u_start) GM/c^3 (exterior emission only)
        u_ret = cols["u_ret_geo"]
        if N and math.isfinite(u_ret[0]):
            cols["t_receive_years"][:] = u.t_to_years(1.0) * (u_ret - u_ret[0])
        self.columns = cols
        self.regime_names = regime_names
        self._signal_timeline = None
        return cols

    # ------------------------------------------------------------------
    def signal_timeline(self, eps_min: float = 1e-12, points_per_decade: int = 20, method: str = "exact") -> dict:
        """Distant-observer received-signal table (see slab.signals), cached for the default arguments."""
        default = (eps_min, points_per_decade, method) == (1e-12, 20, "exact")
        if default and getattr(self, "_signal_timeline", None) is not None:
            return self._signal_timeline
        tl = compute_signal_timeline(self, eps_min=eps_min, points_per_decade=points_per_decade, method=method)
        if default:
            self._signal_timeline = tl
        return tl

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        cols = self.columns
        ms = self.milestone_states
        out = {
            "n_steps_total": int(len(cols["r_geo"])),
            "n_rhs_evals_total": int(sum(s.n_rhs_evals for s in self.segments)),
            "n_rejected_total": int(sum(int(s.n_rejected.sum()) for s in self.segments)),
            "max_err_estimate": float(np.nanmax(cols["err_estimate"])),
            "max_abs_E_drift_raw": float(np.nanmax(np.abs(cols["E"] - cols["E"][0]))),
            "max_E_drift_conditioned": float(np.nanmax(np.abs(cols["E_drift_conditioned"]))),
            "max_abs_E_drift_where_well_conditioned": float(np.nanmax(np.abs(cols["E"] - cols["E_killing"])[cols["E_conditioning_scale"] < 10.0])),
            "kruskal_v_reference_geo": float(self.v_ref_kruskal),
            "max_abs_L_drift": float(np.nanmax(np.abs(cols["L"] - cols["L"][0]))),
            "max_abs_norm_residual": float(np.nanmax(np.abs(cols["norm_residual"]))),
            "max_abs_norm_residual_conditioned": float(np.nanmax(np.abs(cols["norm_residual_conditioned"]))),
            "max_abs_norm_residual_where_well_conditioned": float(np.nanmax(np.abs(cols["norm_residual"])[cols["norm_conditioning_scale"] < 10.0])),
            "max_tidal_closed_form_reldiff": float(np.nanmax(cols["tidal_closed_form_reldiff"])),
            "tau_total_years_at_end": float(cols["tau_years"][-1]),
            "tau_since_horizon_years_at_end": float(cols["tau_since_horizon_years"][-1]),
            "segments": [{"index": s.index, "from": s.slug_from, "to": s.slug_to, "mode": s.mode, "steps": int(len(s.x) - 1),
                          "rhs_evals": s.n_rhs_evals, "status": s.status, "wall_time_s": s.wall_time_s,
                          "min_h": float(np.min(s.h[1:])) if len(s.h) > 1 else None,
                          "max_h": float(np.max(s.h[1:])) if len(s.h) > 1 else None} for s in self.segments],
            "milestones": [ms[m.slug] for m in self.milestones if m.slug in ms],
        }
        return out
