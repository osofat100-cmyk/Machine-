#!/usr/bin/env python3
"""Entry point: validate -> simulate -> save -> export render data.

Usage:
  python run_simulation.py                 # full pipeline (validation gate, then simulation)
  python run_simulation.py --resume        # continue from the newest checkpoint in simulation_state.json
  python run_simulation.py --validate-only # run the physics test suite only
  python run_simulation.py --skip-validation --thrust 9.81   # propulsion scenario (writes to data/scenarios/)

Thin wrapper around :func:`slab.cli.main` (the same pipeline as the ``slab-sim`` console command
installed by ``pip install -e .``).  It needs no installation: it puts ``src/`` on ``sys.path`` and always
uses the directory of this file as the project directory (config, checkpoints/, data/, renders/).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from slab.cli import main as _cli_main  # noqa: E402


def main() -> int:
    return _cli_main(project_dir=ROOT, command="python run_simulation.py")


if __name__ == "__main__":
    sys.exit(main())
