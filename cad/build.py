#!/usr/bin/env python3
"""Build the arm: verify, then export.

    python3 build.py                 # default pose -> build/
    python3 build.py --pose 25 -50 80 0 -30 0
    python3 build.py --out /tmp/arm --no-stl

Outputs
    build/step/<part>.step      one file per part
    build/Robotic_Arm.step      the assembly, with structure and colour
    build/stl/<part>.stl        mesh per part
    build/arm_iso.svg           hidden-line-removed isometric drawing
    build/report.txt            verification results + mass properties
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from build123d import export_step, export_stl
from build123d.exporters import ExportSVG, LineType

from robot_arm.assembly import build_assembly, joint_frames
from robot_arm.params import ArmParams
from robot_arm import parts as P
from robot_arm import verify


def export_drawing(asm, path: Path, size: float = 900.0) -> None:
    """Hidden-line-removed isometric, the way a drawing sheet shows it."""
    visible, hidden = asm.project_to_viewport(
        viewport_origin=(-600, -900, 700),
        viewport_up=(0, 0, 1),
        look_at=(0, 0, 380),
    )
    svg = ExportSVG(scale=1.0, margin=12)
    svg.add_layer("hidden", line_color=(160, 160, 160),
                  line_weight=0.15, line_type=LineType.ISO_DOT)
    svg.add_layer("visible", line_color=(20, 20, 20), line_weight=0.4)
    svg.add_shape(hidden, layer="hidden")
    svg.add_shape(visible, layer="visible")
    svg.write(str(path))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="build", help="output directory")
    ap.add_argument("--pose", nargs=6, type=float, metavar="DEG",
                    help="six joint angles in degrees")
    ap.add_argument("--no-stl", action="store_true")
    ap.add_argument("--no-svg", action="store_true")
    ap.add_argument("--skip-verify", action="store_true")
    args = ap.parse_args(argv)

    p = ArmParams()
    if args.pose:
        p = p.at_pose(*args.pose)

    out = Path(args.out)
    (out / "step").mkdir(parents=True, exist_ok=True)
    if not args.no_stl:
        (out / "stl").mkdir(parents=True, exist_ok=True)

    log: list[str] = []
    def say(msg: str) -> None:
        print(msg)
        log.append(msg)

    say(f"pose  J1..J6 = {tuple(p.joints)}")
    t0 = time.time()

    # ---- verify before exporting; do not ship geometry that fails ----
    if not args.skip_verify:
        rep = verify.run(p)
        say("verification:")
        say(rep.render())
        if not rep.ok:
            say("REFUSING TO EXPORT: verification failed")
            (out / "report.txt").write_text("\n".join(log) + "\n")
            return 1

    # ---- parts -------------------------------------------------------
    lib = P.build_all(p)
    for name, part in lib.items():
        export_step(part, str(out / "step" / f"{name}.step"))
        if not args.no_stl:
            export_stl(part, str(out / "stl" / f"{name}.stl"))
    say(f"exported {len(lib)} parts")

    # ---- assembly ----------------------------------------------------
    asm = build_assembly(p)
    export_step(asm, str(out / "Robotic_Arm.step"))
    say(f"exported assembly: {len(asm.children)} instances "
        f"of {len({c.label.split('.')[0] for c in asm.children})} parts")

    if not args.no_svg:
        export_drawing(asm, out / "arm_iso.svg")
        say("exported drawing: arm_iso.svg")

    # ---- mass properties --------------------------------------------
    DENSITY = 2.70e-6  # kg/mm^3, aluminium 6061
    total = 0.0
    say("")
    say("mass properties (6061-T6 @ 2.70 g/cm3):")
    for name, part in sorted(lib.items()):
        n = sum(1 for c in asm.children if c.label.split(".")[0] == name)
        m = part.volume * DENSITY
        total += m * n
        say(f"  {name:<20} x{n}  {part.volume:9.0f} mm3  {m * 1000:7.1f} g each")
    say(f"  {'TOTAL':<20}      {'':>9}      {total * 1000:7.1f} g")

    f = joint_frames(p)
    tp = f.tool.position
    bb = asm.bounding_box()
    say("")
    say(f"tool centre point: ({tp.X:.1f}, {tp.Y:.1f}, {tp.Z:.1f}) mm")
    say(f"envelope: {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")
    say(f"nominal reach: {p.reach:.0f} mm")
    say(f"build time: {time.time() - t0:.1f} s")

    (out / "report.txt").write_text("\n".join(log) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
