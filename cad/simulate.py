#!/usr/bin/env python3
"""Simulate the arm running a pick-and-place cycle, and render it to video.

    python3 simulate.py                          # build/machine.mp4
    python3 simulate.py --width 640 --ss 1       # a quick low-res look
    python3 simulate.py --check-only             # solve + check, no render

What this is, precisely: the fourteen solids from `robot_arm/parts.py`,
placed by `robot_arm/assembly.py`'s own kinematic chain, at a pose the
inverse solver produces once per frame, rasterised by `sim/`. The video
is therefore a view of the CAD model, not a drawing of one -- if the STEP
file is wrong, so is the video, in the same way.

The run checks itself before it writes anything, in the same spirit as
`build.py`: a frame is only worth rendering if the pose it holds is the
pose that was asked for.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

from robot_arm import assembly as A
from robot_arm import parts as PARTS
from robot_arm.params import ArmParams
from robot_arm.verify import Report
from sim import hud, kinematics as K, program as PG, raster as R, render as RD
from sim import scene as S

# ---- the cell -------------------------------------------------------
PEDESTAL_BODY = "#2f3644"
PEDESTAL_TOP = "#4a5364"
PAYLOAD = "#d1642f"
FLOOR = "#2f3640"

# The viewing direction is a taste decision; the distance is not -- see
# `raster.fit`, which is handed every vertex the arm visits.
VIEW_DIR = (1.0, -0.30, 0.44)
FOV = 30.0


def frame_camera(p: ArmParams, states, protos, w: int, h: int, track):
    """Fit the camera to the whole program, not to one pose."""
    pts = []
    for i in range(0, len(states), 6):
        pose = K.posed(p, states[i].joints, states[i].gap)
        for m in S.arm_meshes(pose, protos):
            pts += _corners(m.verts.min(axis=0), m.verts.max(axis=0))
        c = track[i][:3, 3]
        pts += _corners(c - PG.BLOCK, c + PG.BLOCK)
    for c in (PG.PICK, PG.PLACE):
        pts += _corners([c[0] - 68, c[1] - 68, 0.0],
                        [c[0] + 68, c[1] + 68, PG.PEDESTAL_H])
    return R.fit(np.array(pts, float), VIEW_DIR, w, h, fov=FOV)


def _corners(lo, hi):
    """All eight corners of a box.

    Two opposite corners are not enough: which corner projects furthest
    left depends on where the camera is, and the one that overflows the
    frame is reliably the one you left out.
    """
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return [np.array([lo[0] if i & 1 else hi[0],
                      lo[1] if i & 2 else hi[1],
                      lo[2] if i & 4 else hi[2]]) for i in range(8)]


def cell_scene() -> S.Scene:
    """Floor and fixtures -- scenery, not CAD. The arm is the model."""
    body, top = R.hex_to_linear(PEDESTAL_BODY), R.hex_to_linear(PEDESTAL_TOP)
    meshes = [S.floor_mesh(half=2400.0, n=40, color=R.hex_to_linear(FLOOR))]
    for c in (PG.PICK, PG.PLACE):
        meshes += [
            S.box_mesh((112, 112, PG.PEDESTAL_H - 10), (c[0], c[1], (PG.PEDESTAL_H - 10) / 2), body),
            S.box_mesh((136, 136, 10), (c[0], c[1], PG.PEDESTAL_H - 5), top),
        ]
    return S.merge(meshes)


def payload_start(p: ArmParams) -> np.ndarray:
    """The block sits square to the jaws, which close tangentially."""
    a = np.radians(PG.PICK_AZ + 90.0)
    m = np.eye(4)
    m[:3, :3] = np.array([[np.cos(a), -np.sin(a), 0],
                          [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    m[:3, 3] = PG.PICK
    return m


def payload_track(p: ArmParams, states: list[PG.State]) -> list[np.ndarray]:
    """Where the block is, frame by frame.

    While the jaws are shut the block is rigidly attached to the tool: its
    pose is the tool pose times a fixed offset captured at the instant of
    the grasp. Released, it stays where it was let go. Nothing about its
    position is scripted -- it is carried by the kinematics.
    """
    out: list[np.ndarray] = []
    here = payload_start(p)
    offset = None
    for st in states:
        if st.holding:
            if offset is None:
                offset = np.linalg.inv(st.tcp) @ here
            here = st.tcp @ offset
        out.append(here.copy())
    return out


# ---------------------------------------------------------------------
def check(p: ArmParams, states, diag, track) -> Report:
    rep = Report()

    pos = max(diag["ik_pos_err"]) if diag["ik_pos_err"] else 0.0
    ang = max(diag["ik_ang_err"]) if diag["ik_ang_err"] else 0.0
    rep.add("every commanded pose is actually reached", pos < 0.2 and ang < 0.2,
            f"worst residual {pos:.3f} mm / {ang:.3f} deg over "
            f"{len(diag['ik_pos_err'])} solves")

    dev = max(diag["lin_dev"]) if diag["lin_dev"] else 0.0
    rep.add("straight-line moves run straight", dev < 0.5,
            f"worst deviation from the commanded line {dev:.3f} mm")

    q = np.array([s.joints for s in states])
    step = np.abs(np.diff(q, axis=0)).max() if len(q) > 1 else 0.0
    rep.add("joint motion is continuous", step < 6.0,
            f"largest change in one frame {step:.2f} deg")

    lim = K.LIMITS
    inside = bool((q >= lim[:, 0] - 1e-6).all() and (q <= lim[:, 1] + 1e-6).all())
    rep.add("no joint reaches a stop", inside,
            f"widest excursion {np.abs(q).max():.1f} deg")

    # While held, the block must be rigid in the tool frame. Note what
    # this does *not* assert: that the block is exactly on the tool axis.
    # It is caught wherever the jaws close on it, which is the tool point
    # plus whatever the IK left on the table -- a real gripper picks a
    # part up where the part is, not where the program wished it were.
    held_t = [np.linalg.inv(st.tcp) @ m
              for st, m in zip(states, track) if st.holding]
    slip = 0.0
    if held_t:
        ref = held_t[0]
        slip = max(float(np.abs(t - ref).max()) for t in held_t)
    grip_off = float(np.linalg.norm(ref[:3, 3])) if held_t else 0.0
    rep.add("the payload is rigidly held, not re-scripted, while gripped",
            slip < 1e-9,
            f"tool-to-part transform varies by {slip:.1e} mm over "
            f"{len(held_t)} frames, caught {grip_off * 1000:.0f} um off axis")

    held = [i for i, s in enumerate(states) if s.holding]
    lifted = max(track[i][2, 3] for i in held) if held else 0.0
    rep.add("the payload is actually picked up", lifted > PG.PEDESTAL_H + 100.0,
            f"lifted to z = {lifted:.0f} mm")

    placed = track[-1][:3, 3]
    want = PG.PLACE
    err = float(np.linalg.norm(placed - want))
    rep.add("the payload ends up on the second fixture", err < 1.0,
            f"{err:.3f} mm from the commanded place point")

    closed = min(s.gap for s in states)
    rep.add("the jaws are commanded onto the part exactly",
            abs(closed - PG.BLOCK) < 1e-6,
            f"commanded gap {closed:.1f} mm against a {PG.BLOCK:.0f} mm part")

    lowest = min(s.tcp[2, 3] for s in states)
    rep.add("the tool never drives into the fixture",
            lowest >= PG.PEDESTAL_H + PG.BLOCK / 2 - 0.5,
            f"lowest tool centre point z = {lowest:.1f} mm")

    return rep


def _fixture_boxes():
    """Half-extents of the two pedestals, inflated by a millimetre."""
    for c in (PG.PICK, PG.PLACE):
        yield (np.array([c[0], c[1], PG.PEDESTAL_H / 2]),
               np.array([69.0, 69.0, PG.PEDESTAL_H / 2 + 1.0]))


def check_clearance(p: ArmParams, states, protos, rep: Report, stride=4) -> None:
    """Sweep the real triangles, not a proxy: does any part of the arm
    ever end up inside a fixture, or below the surface it is bolted to?"""
    worst_floor, hits = 1e9, []
    for i in range(0, len(states), stride):
        st = states[i]
        pose = K.posed(p, st.joints, st.gap)
        for label, mesh in S.arm_instances(pose, protos):
            v = mesh.verts
            # The J1 drive is recessed *through* the mounting face by
            # design -- see the -act_len offset in assembly.build_assembly.
            if not label.startswith("11_actuator_can.J1"):
                worst_floor = min(worst_floor, float(v[:, 2].min()))
            for c, half in _fixture_boxes():
                if (np.abs(v - c) < half).all(axis=1).any():
                    hits.append((round(st.t, 2), label))
    rep.add("nothing but the recessed J1 drive goes below the mounting face",
            worst_floor >= -1e-6, f"lowest moving vertex z = {worst_floor:.2f} mm")
    rep.add("the arm never enters a fixture", not hits,
            "clear at every sampled frame" if not hits
            else f"{len(hits)} intrusions, first {hits[0]}")


def check_grip(p: ArmParams, states, protos, rep: Report) -> None:
    """Measure the jaw opening off the placed triangles at the moment of
    the grasp, and hold it against the part.

    The arithmetic in `kinematics.jaw_gap` is a summary of geometry that
    lives in `parts.grabber_jaw`; a summary can be wrong. This one was,
    by 2 mm, and the jaws stood a millimetre clear of a part the program
    reported as gripped. So the check that matters measures the triangles.
    """
    grip = next((st for st in states if st.holding), None)
    if grip is None:
        rep.add("the jaws close on the part, not through it", False,
                "the program never grips anything")
        return
    pose = K.posed(p, grip.joints, grip.gap)
    measured = S.measure_jaw_gap(pose, protos)
    rep.add("the jaws close on the part, not through it",
            abs(measured - PG.BLOCK) < 0.05,
            f"jaw faces measured {measured:.2f} mm apart on a "
            f"{PG.BLOCK:.0f} mm part, with the jaws {pose.grab_open:.1f} deg open")


def check_self_collision(p: ArmParams, states, moves, rep: Report,
                         fps: int = 30) -> None:
    """Run the repo's own interference check at every commanded pose."""
    from robot_arm import verify
    seen, bad = set(), []
    idx, n = [], 0
    for mv in moves:
        n += max(1, int(round(mv.seconds * fps)))
        idx.append(min(n, len(states)) - 1)
    for i in idx:
        key = tuple(np.round(states[i].joints, 3))
        if key in seen:
            continue
        seen.add(key)
        sub = Report()
        verify.check_interference(p.at_pose(*key), sub)
        if not sub.ok:
            bad.append((states[i].phase, sub.checks[-1][2]))
    rep.add("no self-collision at any commanded pose", not bad,
            f"{len(seen)} distinct poses checked with robot_arm.verify"
            if not bad else f"{bad}")


# ---------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build/machine.mp4")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--ss", type=int, default=2, help="supersampling factor")
    ap.add_argument("--deflection", type=float, default=0.3,
                    help="tessellation chord tolerance, mm")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="skip the per-pose solid interference check")
    ap.add_argument("--poster", default="", help="also write a still here")
    ap.add_argument("--every", type=int, default=1,
                    help="render every Nth frame; playback stays real-time")
    args = ap.parse_args(argv)

    w = args.width
    h = int(round(w * 9 / 16))
    p = ArmParams()

    print("solving the program")
    moves = PG.cycle()
    states, diag = PG.expand(p, moves, fps=args.fps)
    track = payload_track(p, states)
    duration = len(states) / args.fps
    print(f"  {len(states)} frames, {duration:.2f} s at {args.fps} fps")

    print(f"tessellating the {len(PARTS.BUILDERS)} parts")
    protos = S.tessellate_parts(p, deflection=args.deflection)
    n_proto = sum(len(m.tris) for m in protos.values())
    print(f"  {n_proto} triangles across {len(protos)} prototypes")

    print("checking")
    rep = check(p, states, diag, track)
    check_clearance(p, states, protos, rep)
    check_grip(p, states, protos, rep)
    if not args.fast:
        check_self_collision(p, states, moves, rep, fps=args.fps)
    print(rep.render())
    if not rep.ok:
        print("checks failed -- refusing to render", file=sys.stderr)
        return 1
    if args.check_only:
        return 0

    static = cell_scene()
    cam = frame_camera(p, states, protos, w * args.ss, h * args.ss, track)
    print(f"  camera at {np.round(cam.eye, 0)} looking at "
          f"{np.round(cam.target, 0)}, {FOV:.0f} deg")
    print(f"baking the static layer at {w * args.ss}x{h * args.ss}")
    t0 = time.time()
    baked = RD.bake(static, cam, w * args.ss, h * args.ss,
                    casters=(static.verts, static.tris))
    print(f"  {time.time() - t0:.1f} s")

    from robot_arm.assembly import instance_count
    _distinct, _instances = instance_count(p)
    segs, t = [], 0.0
    for mv in moves:
        n = max(1, int(round(mv.seconds * args.fps)))
        segs.append((t, t + n / args.fps, mv.name))
        t += n / args.fps
    meta = {
        "title": "6-DOF arm — pick and place",
        "subtitle": "11 parts / 15 instances, posed by robot_arm.assembly "
                    "— github.com/osofat100-cmyk/Machine-",
        "limits": K.LIMITS,
        "duration": duration,
        "segments": segs,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import imageio.v2 as imageio
    writer = imageio.get_writer(
        str(out), fps=args.fps / args.every, codec="libx264", quality=None,
        pixelformat="yuv420p", macro_block_size=1,
        ffmpeg_params=["-crf", "17", "-preset", "slow", "-profile:v", "high",
                       "-movflags", "+faststart"])

    payload_col = R.hex_to_linear(PAYLOAD)
    trail: list[np.ndarray] = []
    t0 = time.time()
    n_done = 0
    for i, st in enumerate(states):
        if i % args.every:
            continue
        pose = K.posed(p, st.joints, st.gap)
        block = S.box_mesh((PG.BLOCK,) * 3, (0, 0, 0), payload_col,
                           m=track[i])
        dyn = S.merge(S.arm_meshes(pose, protos) + [block])
        img = RD.frame(baked, dyn, cam, args.ss, casters=(dyn.verts, dyn.tris))
        trail.append(st.tcp[:3, 3].copy())
        over = hud.draw(img, st, meta, cam, trail[-90:])
        writer.append_data(over)
        n_done += 1
        if args.poster and st.phase == "TRANSFER":
            from PIL import Image
            Path(args.poster).parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(over).save(args.poster)
            args.poster = ""
        if n_done % 25 == 0 or i == len(states) - 1:
            el = time.time() - t0
            print(f"  frame {i + 1}/{len(states)}  {el:.0f}s elapsed, "
                  f"{el / n_done:.2f}s/frame", flush=True)
    writer.close()
    print(f"wrote {out}  ({out.stat().st_size / 1e6:.1f} MB, "
          f"{n_done} frames, {n_proto} triangles per part set)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
