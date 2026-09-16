#!/usr/bin/env python3
"""Render the arm at several poses, side by side, as one drawing.

Evidence for the claim that the joints turn about the axes they are
supposed to: only `ArmParams.joints` changes between these frames. No
geometry is rebuilt -- the same fourteen solids are re-placed by the
kinematic chain.

    python3 poses.py --out build/poses.svg
"""

from __future__ import annotations

import argparse
from pathlib import Path

from build123d import Compound, Pos
from build123d.exporters import ExportSVG, LineType

from robot_arm.assembly import build_assembly
from robot_arm.params import ArmParams

POSES = [
    ("home",      (0, 0, 0, 0, 0, 0)),
    ("reach",     (0, -55, 35, 0, 20, 0)),
    ("folded",    (0, -30, 125, 0, -40, 0)),
    ("yaw 60",    (60, -35, 65, 0, -30, 0)),
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/poses.svg")
    ap.add_argument("--pitch", type=float, default=460.0,
                    help="mm between frames")
    args = ap.parse_args(argv)

    base = ArmParams()
    frames = []
    for i, (name, angles) in enumerate(POSES):
        asm = build_assembly(base.at_pose(*angles))
        frames.append(Compound(children=[
            c.moved(Pos(i * args.pitch, 0, 0)) for c in asm.children
        ]))
        print(f"  posed {name:<8} {angles}")

    strip = Compound(children=frames)
    visible, hidden = strip.project_to_viewport(
        viewport_origin=(0, -3000, 700),
        viewport_up=(0, 0, 1),
        look_at=(args.pitch * (len(POSES) - 1) / 2, 0, 380),
    )
    svg = ExportSVG(scale=1.0, margin=14)
    svg.add_layer("hidden", line_color=(175, 175, 175),
                  line_weight=0.12, line_type=LineType.ISO_DOT)
    svg.add_layer("visible", line_color=(20, 20, 20), line_weight=0.38)
    svg.add_shape(hidden, layer="hidden")
    svg.add_shape(visible, layer="visible")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    svg.write(str(out))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
