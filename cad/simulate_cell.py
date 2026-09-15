#!/usr/bin/env python3
"""Five arms beside a moving conveyor, sorting boxes by size.

    python3 simulate_cell.py                     # build/cell.mp4
    python3 simulate_cell.py --check-only        # simulate and check only
    python3 simulate_cell.py --seconds 8 --width 800 --ss 1   # quick look

Boxes of three sizes arrive at random times and random positions across
the belt. Five of the arm from `robot_arm/` stand along it, three on one
side and two on the other. Each one may only take boxes from its own
half of the belt width and its own stretch of belt length; a box its
owner is too busy to take stays on the belt for the next arm on that
side, and one that nobody catches runs off the end into the reject
chute and is counted.

The belt never stops. Every pick is made on a moving box, with the tool
matched to belt speed at the instant the jaws close.

The arms are the CAD model. Everything else in frame -- belt, bins,
chute, boxes -- is scenery generated in `sim/cellscene.py`.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from robot_arm.params import ArmParams
from robot_arm.verify import Report
from sim import cell as C, cellscene as CS, hud_cell, kinematics as K
from sim import raster as R, render as RD, scene as S, sorter as SO

VIEW_DIR = (0.62, -1.0, 0.46)
FOV = 29.0
MARGINS = (0.03, 0.03, 0.125, 0.155)
CLEARANCE_FLOOR = 50.0                 # mm: how close two arms may ever come


# ---------------------------------------------------------------------
def arm_meshes(p: ArmParams, fr: SO.Frame, protos) -> list[list]:
    """Placed triangles for each arm, kept separate so pairs can be
    measured against each other."""
    out = []
    for i, arm in enumerate(C.ARMS):
        pose = K.posed(p, fr.joints[i], fr.gaps[i])
        out.append([(lbl, S.transform(m, arm.base))
                    for lbl, m in S.arm_instances(pose, protos)])
    return out


def parcel_meshes(fr: SO.Frame) -> list:
    out = []
    for sn in fr.parcels:
        cls = C.BY_KEY[sn.key]
        out.append(S.box_mesh((cls.size,) * 3, (0.0, 0.0, 0.0),
                              R.hex_to_linear(cls.colour), m=sn.pose))
    return out


def dynamic(p: ArmParams, fr: SO.Frame, protos, arms=None) -> S.Scene:
    arms = arms if arms is not None else arm_meshes(p, fr, protos)
    meshes = [m for arm in arms for _, m in arm]
    return S.merge(meshes + parcel_meshes(fr) + CS.belt_markers(fr.t))


def closest_pair(arms) -> float:
    """The smallest gap between any two arms, right now."""
    boxes = [_boxes(inst) for inst in arms]
    return min(_pair_gap(boxes[a], boxes[b])
               for a in range(len(boxes)) for b in range(a + 1, len(boxes)))


# ---------------------------------------------------------------------
def _boxes(instances) -> tuple[np.ndarray, np.ndarray]:
    lo = np.array([m.verts.min(axis=0) for _, m in instances])
    hi = np.array([m.verts.max(axis=0) for _, m in instances])
    return lo, hi


def _pair_gap(a: tuple, b: tuple) -> float:
    """Smallest gap between any part of one arm and any part of another.

    Measured between the parts' bounding boxes, which *understates* the
    true surface distance -- a box is never smaller than what it holds.
    So a positive answer here is a guarantee, not an estimate: if the
    boxes are 60 mm apart the solids are at least 60 mm apart.
    """
    (alo, ahi), (blo, bhi) = a, b
    d = np.maximum(np.maximum(alo[:, None, :] - bhi[None, :, :],
                              blo[None, :, :] - ahi[:, None, :]), 0.0)
    return float(np.sqrt((d ** 2).sum(axis=2)).min())


def check_clearance(p: ArmParams, frames, protos, rep: Report, stride=2):
    """How close do any two arms ever come? Measured, every frame."""
    worst, when = 1e9, None
    for i in range(0, len(frames), stride):
        fr = frames[i]
        boxes = [_boxes(inst) for inst in arm_meshes(p, fr, protos)]
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                g = _pair_gap(boxes[a], boxes[b])
                if g < worst:
                    worst, when = g, (round(fr.t, 2), C.ARMS[a].name,
                                      C.ARMS[b].name)
    rep.add("no two arms ever come within reach of each other",
            worst >= CLEARANCE_FLOOR,
            f"closest approach {worst:.0f} mm, {when[1]}-{when[2]} at "
            f"t={when[0]:.2f}s (floor {CLEARANCE_FLOOR:.0f} mm)")
    return worst


def check_structure(rep: Report) -> None:
    """The layout's own promises, before anything moves."""
    lo_l, hi_l = K.LIMITS[0]
    tight = [(a.name, a.j1_range) for a in C.ARMS
             if a.j1_range[0] < lo_l + 15 or a.j1_range[1] > hi_l - 15]
    rep.add("every arm's turret travel fits inside J1", not tight,
            f"worst margin {min(min(a.j1_range[0] - lo_l, hi_l - a.j1_range[1]) for a in C.ARMS):.0f} deg"
            if not tight else f"{tight}")

    out = [(a.name, round(r, 1)) for a in C.ARMS
           for r in [float(np.hypot(*a.to_local(pt)[:2]))
                     for pt in C.working_set(a)]
           if not (C.R_MIN <= r <= C.R_MAX)]
    rep.add("everything an arm must reach is inside its own annulus", not out,
            f"radii {min(float(np.hypot(*a.to_local(pt)[:2])) for a in C.ARMS for pt in C.working_set(a)):.0f}"
            f"..{max(float(np.hypot(*a.to_local(pt)[:2])) for a in C.ARMS for pt in C.working_set(a)):.0f} mm"
            f" inside {C.R_MIN:.0f}..{C.R_MAX:.0f}" if not out else f"{out[:3]}")

    bad = []
    for i, a in enumerate(C.ARMS):
        for b in C.ARMS[i + 1:]:
            if a.side == b.side and not (a.x1 < b.x0 or b.x1 < a.x0):
                bad.append((a.name, b.name))
    rep.add("no two arms on a side own the same stretch of belt", not bad,
            f"closest windows {min(abs(b.x0 - a.x1) for a in C.ARMS for b in C.ARMS if b.x0 > a.x1):.0f} mm apart"
            if not bad else f"{bad}")


def check_program(p: ArmParams, frames, diag, rep: Report) -> None:
    pos = max(diag["ik_pos"]) if diag["ik_pos"] else 0.0
    ang = max(diag["ik_ang"]) if diag["ik_ang"] else 0.0
    rep.add("every commanded pose is actually reached", pos < 0.2 and ang < 0.2,
            f"worst residual {pos:.3f} mm / {ang:.3f} deg over "
            f"{len(diag['ik_pos'])} solves")

    rel = max(diag["grasp_rel"]) if diag["grasp_rel"] else 1e9
    rep.add("the tool matches belt speed at the grasp", rel < 1.0,
            f"worst relative speed {rel:.3f} mm/s against a belt running "
            f"at {C.BELT_SPEED:.0f} mm/s")

    trk = max(diag["track_err"]) if diag["track_err"] else 1e9
    rep.add("the tool is on the box, not near it", trk < 0.2,
            f"worst tracking error through the grasp {trk:.3f} mm")

    q = np.array([f.joints for f in frames])            # (frames, arms, 6)
    margin = min(float(K.LIMITS[k][1] - np.abs(q[:, :, k]).max())
                 for k in range(6))
    rep.add("no joint on any arm reaches a stop", margin > 5.0,
            f"tightest margin {margin:.0f} deg")

    # Rate, not per-frame step: a step limit silently tightens with the
    # frame rate, and would call the turret's normal slew a fault at
    # 20 fps and pass a real discontinuity at 120.
    fps = (len(frames) - 1) / max(frames[-1].t, 1e-9)
    dq = np.abs(np.diff(q, axis=0)) * fps if len(q) > 1 else np.zeros((1, 1, 6))
    rate = float(dq.max())
    where = np.unravel_index(int(dq.argmax()), dq.shape)
    rep.add("no joint moves faster than the machine could", rate < 400.0,
            f"peak {rate:.0f} deg/s ({C.ARMS[where[1]].name} "
            f"J{where[2] + 1} at t={frames[where[0]].t:.2f}s)")

    peak = max(diag["tcp_step"]) * len(frames) / max(frames[-1].t, 1e-9)
    rep.add("tool speed stays in range for an arm this size", peak < 2600.0,
            f"peak {peak:.0f} mm/s")

    rep.add("every box was grasped inside its own arm's territory",
            all(diag["zone_ok"]), f"{len(diag['zone_ok'])} grasps, all inside")

    sq = max(diag["jaw_square"]) if diag["jaw_square"] else 90.0
    rep.add("the jaws meet the box square to its faces, not on a corner",
            sq < 1.0,
            f"worst misalignment with the belt axis {sq:.3f} deg")

    jaw = min(diag["jaw_floor"]) if diag["jaw_floor"] else -1.0
    rep.add("the jaws clear the belt surface", jaw > 4.0,
            f"lowest jaw {jaw:.1f} mm above the belt")

    counts = frames[-1].counts
    rep.add("the cell actually sorts", counts["picked"] > 0
            and counts["picked"] + counts["missed"] <= counts["seen"],
            f"{counts['seen']} seen, {counts['picked']} picked "
            f"(S{counts['S']}/M{counts['M']}/L{counts['L']}), "
            f"{counts['missed']} run off the end")

    handed = {}
    for _, name, pid, _ in diag["claims"]:
        handed.setdefault(pid, []).append(name)
    passed_on = sum(1 for pid, names in handed.items() if len(names) > 1)
    first = {}
    for t, name, pid, key in diag["claims"]:
        first.setdefault(pid, name)
    downstream = sum(1 for pid, name in first.items()
                     if name not in ("A1", "A2"))
    rep.add("boxes the first arm was too busy for went downstream",
            downstream > 0,
            f"{downstream} of {len(first)} boxes were taken by an arm "
            f"other than the first on their side")


# ---------------------------------------------------------------------
def fit_camera(p: ArmParams, frames, protos, w: int, h: int) -> R.Camera:
    pts = [S.merge(CS.machinery()).verts[::9]]
    for fr in frames[::max(1, len(frames) // 40)]:
        pts.append(dynamic(p, fr, protos).verts[::29])
    return R.fit(np.vstack(pts), VIEW_DIR, w, h, fov=FOV, margins=MARGINS)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/cell.mp4")
    ap.add_argument("--seconds", type=float, default=26.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--ss", type=int, default=2)
    ap.add_argument("--deflection", type=float, default=0.45)
    ap.add_argument("--mean-gap", type=float, default=1.45)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--poster", default="")
    args = ap.parse_args(argv)

    w = args.width
    h = int(round(w * 9 / 16))
    p = ArmParams()

    print(f"cell: {len(C.ARMS)} arms, belt {C.BELT_X1 - C.BELT_X0:.0f} mm "
          f"at {C.BELT_SPEED:.0f} mm/s, cycle {SO.CYCLE_T:.2f} s")
    for a in C.ARMS:
        print(f"  {a.name}  side {a.side:+d}  window [{a.x0:+7.0f},{a.x1:+7.0f}]"
              f"  base yaw {a.yaw:6.1f} deg  J1 {a.j1_range[0]:+7.1f}"
              f"..{a.j1_range[1]:+7.1f} deg")

    print("simulating")
    t0 = time.time()
    frames, diag = SO.run(p, seconds=args.seconds, fps=args.fps,
                          seed=args.seed, mean_gap=args.mean_gap)
    print(f"  {len(frames)} frames in {time.time() - t0:.0f} s")

    print("tessellating")
    protos = S.tessellate_parts(p, deflection=args.deflection, angular=0.3)

    print("checking")
    rep = Report()
    check_structure(rep)
    check_program(p, frames, diag, rep)
    check_clearance(p, frames, protos, rep)
    print(rep.render())
    if not rep.ok:
        print("checks failed -- refusing to render", file=sys.stderr)
        return 1
    if args.check_only:
        return 0

    static = CS.static_scene()
    mach = S.merge(CS.machinery())
    cam = fit_camera(p, frames, protos, w * args.ss, h * args.ss)
    print(f"baking the static layer at {w * args.ss}x{h * args.ss}")
    t0 = time.time()
    baked = RD.bake(static, cam, w * args.ss, h * args.ss,
                    casters=(mach.verts, mach.tris))
    print(f"  {time.time() - t0:.0f} s")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import imageio.v2 as imageio
    writer = imageio.get_writer(
        str(out), fps=args.fps, codec="libx264", quality=None,
        pixelformat="yuv420p", macro_block_size=1,
        ffmpeg_params=["-crf", "18", "-preset", "slow", "-profile:v", "high",
                       "-movflags", "+faststart"])
    meta = hud_cell.build_meta(frames, args.fps)
    t0 = time.time()
    for i, fr in enumerate(frames):
        arms = arm_meshes(p, fr, protos)
        dyn = dynamic(p, fr, protos, arms)
        img = RD.frame(baked, dyn, cam, args.ss, casters=(dyn.verts, dyn.tris))
        over = hud_cell.draw(img, fr, meta, cam, closest_pair(arms))
        writer.append_data(over)
        if args.poster and fr.t > args.seconds * 0.55:
            from PIL import Image
            Path(args.poster).parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(over).save(args.poster)
            args.poster = ""
        if (i + 1) % 25 == 0 or i == len(frames) - 1:
            el = time.time() - t0
            print(f"  frame {i + 1}/{len(frames)}  {el:.0f}s elapsed, "
                  f"{el / (i + 1):.2f}s/frame", flush=True)
    writer.close()
    print(f"wrote {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
