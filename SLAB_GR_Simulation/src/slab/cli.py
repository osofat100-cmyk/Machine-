"""Command-line interface: validate -> simulate -> save -> export render data.

Two entry points run the SAME pipeline (:func:`main`):

* ``slab-sim`` — console script declared in ``pyproject.toml`` (``pip install -e .``);
* ``python run_simulation.py`` — thin wrapper kept for backwards compatibility; it passes its own
  directory as the project directory, exactly as the stand-alone script did before packaging.

The *project directory* holds ``simulation_config.json`` (default configuration), ``checkpoints/``,
``data/``, ``renders/``, ``simulation_state.json`` and ``validation_report.json``.  ``slab-sim``
locates it in this order (first match wins):

1. ``--project-dir DIR``;
2. the environment variable ``SLAB_PROJECT_DIR``;
3. the current working directory or one of its ancestors that contains a project marker
   (``simulation_config.json`` with an ``M_solar`` entry), also looking into an
   ``SLAB_GR_Simulation/`` subdirectory at each level (so it works from the repository root);
4. the source checkout the ``slab`` package was imported from (``<project>/src/slab/cli.py``,
   i.e. an editable install);

otherwise it stops with an error that names these options.  Run from inside the repository,
steps 3 and 4 both give the directory that contains ``run_simulation.py`` — the same directory the
old script used.

Hard rule preserved: the validated classical-GR integration stops at r_QG and prints the
Planck-threshold message (printed by :meth:`slab.trajectory.Simulation.run`); speculative toy models
run only with ``--speculative`` and write to their own, separately labelled outputs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import sys
from pathlib import Path
from typing import Optional, Sequence, Tuple

PROJECT_MARKER = "simulation_config.json"
PROJECT_DIR_ENV = "SLAB_PROJECT_DIR"
PROJECT_SUBDIR = "SLAB_GR_Simulation"
DEFAULT_COMMAND = "slab-sim"


class ProjectDirError(RuntimeError):
    """No project directory could be located."""


# ----------------------------------------------------------------------------------------------
# project-directory discovery
# ----------------------------------------------------------------------------------------------
def is_project_dir(path: Path) -> bool:
    """True if ``path`` contains a SLAB project configuration (``simulation_config.json`` with ``M_solar``)."""
    cfg = Path(path) / PROJECT_MARKER
    if not cfg.is_file():
        return False
    try:
        d = json.loads(cfg.read_text())
    except (OSError, ValueError):
        return False
    return isinstance(d, dict) and "M_solar" in d


def source_checkout_dir() -> Optional[Path]:
    """Project directory of the source tree this module was imported from, or None.

    For an editable install (or ``sys.path`` pointing at ``<project>/src``) this file is
    ``<project>/src/slab/cli.py``.  For a regular (non-editable) install into site-packages there is
    no project directory next to the code and None is returned.
    """
    here = Path(__file__).resolve()
    if here.parent.name != "slab" or here.parents[1].name != "src":
        return None
    cand = here.parents[2]
    return cand if is_project_dir(cand) else None


def find_project_dir(explicit: Optional[str] = None, cwd: Optional[Path] = None,
                     environ: Optional[dict] = None) -> Tuple[Path, str]:
    """Locate the project directory; returns ``(absolute path, how it was found)``.

    See the module docstring for the search order.  An explicit directory (``--project-dir`` or
    ``$SLAB_PROJECT_DIR``) is accepted as given (it may be new/empty; ``--config`` then has to point
    at a configuration file); discovered directories must contain the project marker.
    """
    if explicit:
        return Path(explicit).expanduser().resolve(), "--project-dir"
    env = os.environ if environ is None else environ
    if env.get(PROJECT_DIR_ENV):
        return Path(env[PROJECT_DIR_ENV]).expanduser().resolve(), f"${PROJECT_DIR_ENV}"
    start = (Path.cwd() if cwd is None else Path(cwd)).resolve()
    for d in (start, *start.parents):
        if is_project_dir(d):
            return d, "current directory" if d == start else "parent of the current directory"
        if is_project_dir(d / PROJECT_SUBDIR):
            return (d / PROJECT_SUBDIR), f"{PROJECT_SUBDIR}/ below the current directory or a parent"
    src = source_checkout_dir()
    if src is not None:
        return src, "source checkout of the installed slab package"
    raise ProjectDirError(
        "no SLAB_GR_Simulation project directory found: run slab-sim inside the project (the directory "
        f"containing {PROJECT_MARKER}), pass --project-dir DIR, or set {PROJECT_DIR_ENV}=DIR")


# ----------------------------------------------------------------------------------------------
# argument parser
# ----------------------------------------------------------------------------------------------
def build_parser(prog: Optional[str] = None, with_project_dir: bool = True) -> argparse.ArgumentParser:
    """The command-line flags.  ``with_project_dir=False`` gives exactly the flag set of the historic
    ``run_simulation.py`` (which always uses its own directory as the project directory)."""
    if with_project_dir:
        from . import __version__
        ap = argparse.ArgumentParser(
            prog=prog,
            description="SLAB_GR_Simulation: validation gate (TESTS 0-8) -> classical-GR simulation down to r_QG "
                        "-> CSV/JSON/HDF5 data -> render export for the viewer.",
            epilog=f"Project directory search order: --project-dir, ${PROJECT_DIR_ENV}, the current directory or a "
                   f"parent containing {PROJECT_MARKER} (or its {PROJECT_SUBDIR}/ subdirectory), the source checkout "
                   "of the installed package.")
    else:
        ap = argparse.ArgumentParser(prog=prog)
    ap.add_argument("--config", default=None,
                    help=f"configuration JSON (default: <project dir>/{PROJECT_MARKER})" if with_project_dir else None)
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
    ap.add_argument("--out-dir", default=None,
                    help="project directory for outputs (default: "
                         + ("the project directory" if with_project_dir else "this directory") + ", or data/scenarios/<tag>)")
    if with_project_dir:
        ap.add_argument("--project-dir", default=None,
                        help="project directory holding simulation_config.json, checkpoints/, data/, renders/ "
                             "(default: discovered, see below)")
        ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


# ----------------------------------------------------------------------------------------------
# pipeline
# ----------------------------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None, *, project_dir: Optional[Path] = None,
         command: str = DEFAULT_COMMAND) -> int:
    """Run the pipeline; returns the process exit code.

    ``project_dir`` fixes the project directory (used by ``run_simulation.py``: no ``--project-dir``
    flag, no discovery, identical flags and output); ``command`` is the command quoted in the
    "continue with ... --resume" hint.
    """
    fixed = project_dir is not None
    ap = build_parser(with_project_dir=not fixed)
    args = ap.parse_args(argv)
    if fixed:
        root, how = Path(project_dir).resolve(), None
    else:
        try:
            root, how = find_project_dir(args.project_dir)
        except ProjectDirError as exc:
            ap.error(str(exc))
    config_path = Path(args.config) if args.config else root / PROJECT_MARKER
    if not config_path.is_file():
        ap.error(f"configuration file not found: {config_path} (pass --config FILE"
                 + ("" if fixed else " or --project-dir DIR") + ")")
    if how is not None:
        print(f"project directory: {root} ({how})")
    return run_pipeline(args, root, config_path, command, full_resume_hint=not fixed)


def resume_command(command: str, args: argparse.Namespace, root: Path, tag: Optional[str]) -> str:
    """Command line that continues a run stopped with --stop-after-milestone: the same project directory
    (when given explicitly) and the same output directory (--out-dir, or the scenario --tag); the
    configuration itself is restored from the checkpoint."""
    parts = [command]
    if getattr(args, "project_dir", None):
        parts += ["--project-dir", shlex.quote(str(root))]
    if args.out_dir:
        parts += ["--out-dir", shlex.quote(args.out_dir)]
    elif tag is not None:
        parts += ["--tag", shlex.quote(tag)]
    if args.skip_validation:
        parts.append("--skip-validation")
    return " ".join(parts + ["--resume"])


def run_pipeline(args: argparse.Namespace, ROOT: Path, config_path: Path, command: str = DEFAULT_COMMAND,
                 full_resume_hint: bool = True) -> int:
    """The validate -> simulate -> save -> export pipeline (formerly the body of run_simulation.py).

    ``full_resume_hint=False`` keeps the historic hint text of run_simulation.py ("<command> --resume")."""
    from .trajectory import Simulation, SimulationConfig
    from . import io as sio
    from .checkpoints import load_checkpoint, dumps

    cfg = SimulationConfig.from_json(config_path)
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
        from .validation import run_all_tests
        report = run_all_tests(cfg, ROOT)
        ROOT.mkdir(parents=True, exist_ok=True)
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
            # the checkpoint carries its full configuration: use it (no need to re-type CLI overrides)
            cfg = SimulationConfig(**{k: (math.inf if v == "inf" else v) for k, v in ck["config"].items() if k in SimulationConfig.__dataclass_fields__})
            sim = Simulation(cfg, project_dir=project_dir)
            if ck.get("config_hash") != sim.config_hash:
                print("checkpoint config hash differs from the configuration it stores; refusing to resume"); return 3
            print("configuration restored from the checkpoint")
        sim.load_segments()
        if ck["is_final"]:
            print("latest checkpoint is final; nothing to resume (re-exporting outputs)")
        else:
            print(f"resuming from {state['latest_checkpoint']} (milestone {ck['milestone_slug']})")
            sim.run(resume_from=ck, stop_after=args.stop_after_milestone)
    else:
        sim.run(stop_after=args.stop_after_milestone)
    if sim.stopped_early:
        hint = resume_command(command, args, ROOT, tag) if full_resume_hint else f"{command} --resume"
        print(f"stopped after milestone '{args.stop_after_milestone}' (checkpointed). Continue with: {hint}")
        return 0
    sim.postprocess()
    data_dir = project_dir / "data"
    sio.write_csv(sim, data_dir / "trajectory.csv")
    sio.write_json(sim, data_dir / "trajectory_metadata.json")
    sio.write_hdf5(sim, data_dir / "trajectory.h5")
    extra = {}
    if args.speculative:
        from .speculative.models import run_speculative_suite
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


if __name__ == "__main__":  # python -m slab.cli
    sys.exit(main())
