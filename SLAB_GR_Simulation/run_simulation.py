#!/usr/bin/env python3
"""Entry point: validate -> simulate -> save -> export render data.

Usage:
  python run_simulation.py                 # full pipeline (validation gate, then simulation)
  python run_simulation.py --resume        # continue from the newest checkpoint in simulation_state.json
  python run_simulation.py --validate-only # run the physics test suite only
  python run_simulation.py --skip-validation --thrust 9.81   # propulsion scenario (writes to data/scenarios/)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from slab.trajectory import Simulation, SimulationConfig, PLANCK_MESSAGE  # noqa: E402
from slab import io as sio  # noqa: E402
from slab.checkpoints import latest_checkpoint, load_checkpoint, dumps  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "simulation_config.json"))
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--skip-validation", action="store_true")
    ap.add_argument("--thrust", type=float, default=None, help="proper acceleration [m/s^2], > 0 inward (scenario run)")
    ap.add_argument("--E", type=float, default=None)
    ap.add_argument("--L", type=float, default=None, help="specific angular momentum in units of GM/c")
    ap.add_argument("--r0", type=float, default=None, help="start radius in units of r_s")
    ap.add_argument("--tag", default=None, help="scenario name; outputs go to data/scenarios/<tag>/")
    ap.add_argument("--speculative", action="store_true", help="also run the speculative toy models (separate outputs)")
    ap.add_argument("--stop-after-milestone", default=None, help="stop (checkpointed) after reaching this milestone slug; continue later with --resume")
    ap.add_argument("--out-dir", default=None, help="project directory for outputs (default: this directory, or data/scenarios/<tag>)")
    args = ap.parse_args()

    cfg = SimulationConfig.from_json(Path(args.config))
    scenario = False
    if args.thrust is not None:
        cfg.thrust_alpha_SI = args.thrust; scenario = True
    if args.E is not None:
        cfg.E = args.E; scenario = True
    if args.L is not None:
        cfg.L_over_M = args.L; scenario = True
    if args.r0 is not None:
        cfg.r0_over_rs = args.r0; scenario = True
    tag = args.tag or (f"E{cfg.E:g}_L{cfg.L_over_M:g}_a{cfg.thrust_alpha_SI:g}_r0{cfg.r0_over_rs:g}" if scenario else None)

    # ---------------- validation gate ----------------
    if not args.skip_validation:
        from slab.validation import run_all_tests
        report = run_all_tests(cfg, ROOT)
        (ROOT / "validation_report.json").write_text(dumps(report))
        print(f"validation: {report['n_passed']}/{report['n_tests']} tests passed -> validation_report.json")
        if not report["all_passed"]:
            print("VALIDATION FAILED — the main simulation is NOT marked validated. See validation_report.json")
            if not scenario:
                return 2
        if args.validate_only:
            return 0

    # ---------------- simulation ----------------
    project_dir = Path(args.out_dir) if args.out_dir else (ROOT if tag is None else ROOT / "data" / "scenarios" / tag)
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "data").mkdir(exist_ok=True)
    sim = Simulation(cfg, project_dir=project_dir)
    print(f"metric: {sim.metric.name}; coordinates: {cfg.coordinate_system}")
    print(f"M = {sim.dq.M_kg:.6e} kg; r_s = {sim.dq.r_s_m:.6e} m = {sim.dq.r_s_ly:,.1f} ly; GM/c^3 = {sim.dq.GM_over_c3_years:,.1f} yr")
    print(f"r_QG = {sim.dq.r_QG_m:.6e} m = {sim.dq.r_QG_over_rs:.6e} r_s")
    if args.resume:
        state = json.loads((project_dir / "simulation_state.json").read_text())
        ck = load_checkpoint(project_dir / state["latest_checkpoint"])
        if ck.get("config_hash") != sim.config_hash:
            print("checkpoint config hash differs from current config; refusing to resume"); return 3
        sim.load_segments()
        if ck["is_final"]:
            print("latest checkpoint is final; nothing to resume (re-exporting outputs)")
        else:
            print(f"resuming from {state['latest_checkpoint']} (milestone {ck['milestone_slug']})")
            sim.run(resume_from=ck, stop_after=args.stop_after_milestone)
    else:
        sim.run(stop_after=args.stop_after_milestone)
    if sim.stopped_early:
        print(f"stopped after milestone '{args.stop_after_milestone}' (checkpointed). Continue with: python run_simulation.py --resume")
        return 0
    sim.postprocess()
    data_dir = project_dir / "data"
    sio.write_csv(sim, data_dir / "trajectory.csv")
    sio.write_json(sim, data_dir / "trajectory_metadata.json")
    sio.write_hdf5(sim, data_dir / "trajectory.h5")
    extra = {}
    if args.speculative:
        from slab.speculative.models import run_speculative_suite
        extra["speculative"] = run_speculative_suite(sim, project_dir / "data" / "speculative")
    render_dir = ROOT / "renders" if (tag is None and args.out_dir is None) else project_dir / "renders"
    render_dir.mkdir(parents=True, exist_ok=True)
    sio.write_render_data(sim, render_dir / "trajectory_data.js", data_dir / "trajectory_render.json", cfg.render_samples, extra)
    s = sim.summary()
    print(f"steps: {s['n_steps_total']}  rhs evals: {s['n_rhs_evals_total']}  max err est: {s['max_err_estimate']:.2e}  "
          f"norm residual: {s['max_abs_norm_residual']:.2e}")
    print(f"proper time since horizon at r_QG: {s['tau_since_horizon_years_at_end']:,.3f} yr")
    print(f"outputs: {data_dir/'trajectory.csv'}, {data_dir/'trajectory.h5'}, {data_dir/'trajectory_metadata.json'}, {render_dir/'trajectory_data.js'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
