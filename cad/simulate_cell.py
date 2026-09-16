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

from robot_arm import assembly as A
from robot_arm.params import ArmParams
from robot_arm.verify import Report
from sim import cell as C, cellscene as CS, hud_cell, kinematics as K
from sim import raster as R, render as RD, rigid as RIG, scene as S, sorter as SO

VIEW_DIR = (0.62, -1.0, 0.70)   # a steeper look-down than the
                                # single-arm shot, so the camera
                                # sees into the bins rather than
                                # at the outside of their walls
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
    parcel = R.hex_to_linear(C.PARCEL_COLOUR)
    for sn in fr.parcels:
        # Every box the same colour and the same shape: the only thing
        # that tells the cell where one belongs is how big it is.
        out.append(S.box_mesh((sn.size,) * 3, (0.0, 0.0, 0.0), parcel,
                              m=sn.pose))
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


def check_structure(p: ArmParams, rep: Report) -> None:
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

    # Capability, checked separately from policy: the arm can cross the
    # belt even though it is never sent across it.
    worst, radii, fails = 0.0, [], []
    for arm in C.ARMS:
        for pt in C.full_width_set(arm):
            lp = arm.to_local(pt)
            radii.append(float(np.hypot(lp[0], lp[1])))
            q, pe, ae = K.solve_ik(p, K.target_frame(lp), K.seed_for(lp, p))
            worst = max(worst, pe, ae)
            if pe > 0.2 or ae > 0.2:
                fails.append((arm.name, np.round(pt, 0)))
    rep.add("every arm can reach every point of its own stretch of belt",
            not fails,
            f"solved at {len(radii)} points spanning {min(radii):.0f}"
            f"..{max(radii):.0f} mm of reach, worst residual {worst:.3f}"
            if not fails else f"{fails[:3]}")

    both = [a.name for a in C.ARMS
            if a.owns((a.x0 + a.x1) / 2.0, -a.side * C.BELT_HALF_W * 0.9)
            and a.owns((a.x0 + a.x1) / 2.0, a.side * C.BELT_HALF_W * 0.9)]
    rep.add("...and is sent across it: territory is the full width",
            len(both) == len(C.ARMS),
            "every arm owns both edges of its own stretch")


def check_bands(rep: Report) -> None:
    """The size bands must not touch, or a measurement near a boundary
    could honestly belong to two bins."""
    gaps = [C.CLASSES[i + 1].lo - C.CLASSES[i].hi
            for i in range(len(C.CLASSES) - 1)]
    rep.add("the size bands leave a gap, so no measurement is ambiguous",
            min(gaps) > 0, f"narrowest gap between bands {min(gaps):.0f} mm, "
            f"thresholds at {C.CUTS[0]:.0f} and {C.CUTS[1]:.0f} mm")
    mis = [sz for cls in C.CLASSES
           for sz in np.linspace(cls.lo, cls.hi, 25)
           if C.classify(sz).key != cls.key]
    rep.add("every size in a band classifies into that band", not mis,
            f"{3 * 25} sizes swept" if not mis else f"{mis[:3]}")


def check_designation(p: ArmParams, frames, diag, protos, rep: Report) -> None:
    """Did each box end up in the box it was designated for?

    Not 'in the bin the dispatcher aimed at' -- that would only prove the
    dispatcher agrees with itself. This takes each box where it finally
    came to rest, finds the nearest of all fifteen bins, and requires
    that bin to be the one `cell.classify` designates for the box's
    measured edge.
    """
    wrong, checked, worst = [], 0, 0.0
    all_bins = [(a, key, pt) for a in C.ARMS for key, pt in a.bins.items()]
    for sn in frames[-1].parcels:
        if sn.state != "binned" or sn.claimed_by is None:
            continue
        here = sn.pose[:3, 3]
        arm, key, pt = min(all_bins,
                           key=lambda b: np.linalg.norm(here[:2] - b[2][:2]))
        want = C.classify(sn.size).key
        off = float(np.linalg.norm(here[:2] - pt[:2]))
        worst = max(worst, off)
        checked += 1
        if key != want or off > C.BIN_INNER + sn.size / 2.0:
            wrong.append((sn.pid, round(sn.size, 1), want, key, round(off)))
    rep.add("every box came to rest in the bin its size designates",
            not wrong and checked > 0,
            f"{checked} boxes, worst {worst:.0f} mm from the bin's centre "
            f"(bin half-width {C.BIN_INNER:.0f} mm)" if not wrong
            else f"{wrong[:3]}")

    # and the jaws closed on the width that was measured, not a nominal one
    off = max((abs(gap - size) for _, _, gap, size, _ in diag["grasp_pose"]),
              default=1e9)
    rep.add("the jaws close on the width that was measured", off < 1e-6,
            f"{len(diag['grasp_pose'])} grasps, worst gap error {off:.1e} mm "
            f"across sizes "
            f"{min(sz for *_, sz, _ in diag['grasp_pose']):.0f}"
            f"..{max(sz for *_, sz, _ in diag['grasp_pose']):.0f} mm")

    # measured off the placed triangles, not off the arithmetic
    worst_geo, n = 0.0, 0
    for idx, q, gap, size, key in diag["grasp_pose"][:12]:
        pose = K.posed(p, q, gap)
        worst_geo = max(worst_geo,
                        abs(S.measure_jaw_gap(pose, protos) - size))
        n += 1
    rep.add("the claw really is closed on the box that wide", worst_geo < 0.3,
            f"{n} grasps measured from the placed triangles, worst "
            f"disagreement with the box {worst_geo:.3f} mm")


def check_physics(p: ArmParams, frames, diag, rep: Report) -> None:
    """The invariants the rigid-body solver has to satisfy.

    These are the checks that make "it is a physics simulation" a
    testable claim rather than a description. The old drop chose where
    a box would end up and eased it there, and every one of these would
    have passed trivially -- boxes cannot interpenetrate if their
    resting places were laid out on a grid, and energy cannot grow if
    nothing is integrated. They are only worth running because the
    landing pose is now an output.
    """
    over = diag.get("rest_overlap", 0.0)
    live = max(diag["overlap"]) if diag["overlap"] else 0.0
    rep.add("no box comes to rest inside another box",
            over <= RIG.SLOP + 0.3,
            f"deepest box-into-box overlap at rest {over:.2f} mm "
            f"(solver leaves {RIG.SLOP:.2f} mm of slop alone); "
            f"worst during impact {live:.2f} mm")

    end_t = frames[-1].t
    # A box let go in the last second and a half is *meant* to still be
    # moving; anything older has had time to settle and has to have.
    stuck = [(pid, round(v, 1)) for pid, last, v in diag["awake_at_end"]
             if end_t - last > 1.5]
    rep.add("every box that was let go comes to rest", not stuck,
            f"{len(diag['awake_at_end'])} still moving at the last frame, "
            f"every one of them in a pile something landed on within "
            f"1.5 s of it" if not stuck
            else f"still moving long after its pile settled: {stuck[:4]}")

    # Energy in, expressed as the height it would have lifted the pile,
    # against the overlap that frame was pushing out of. Contact impulses
    # cannot add any at all -- the penetration bias is a split impulse --
    # so the only way in is the work of raising a box out of something it
    # is inside, and that cannot exceed how far inside it was.
    slack = [(lift - depth, lift, depth, key, when)
             for lift, depth, key, when in diag["energy_lift"]]
    worst = max(slack) if slack else (0.0, 0.0, 0.0, "", 0.0)
    rep.add("no frame lifts a box further than the overlap it was in",
            worst[0] < 0.4,
            f"worst frame put in {worst[1]:.2f} mm of lift against a "
            f"{worst[2]:.2f} mm overlap ({worst[3]} at t={worst[4]:.2f}s) "
            f"-- {worst[0]:+.2f} mm of slack")

    out = []
    for sn in frames[-1].parcels:
        if sn.state != "binned" or sn.claimed_by is None:
            continue
        pt = C.ARMS[sn.claimed_by].bins[sn.key]
        d = np.abs(sn.pose[:2, 3] - pt[:2])
        if d.max() > C.BIN_CLEAR or sn.pose[2, 3] < C.BIN_FLOOR_Z:
            out.append((sn.pid, round(float(d.max())), round(sn.pose[2, 3])))
    rep.add("no box ends up on a rim, or on the floor beside a bin",
            not out,
            f"every box at rest is between its bin's walls "
            f"(clear half-width {C.BIN_CLEAR:.0f} mm, walls are finite "
            f"slabs so leaving is possible)" if not out
            else f"outside: {out[:4]}")

    # What the claw has to hold on to. `grab_jaws` pads, each pressing
    # at `grip_force` and each able to resist `jaw_mu` times that in
    # shear, against the box's weight plus whatever the carry is doing
    # to it. Friction only: a claw also wraps, and that would help, but
    # a number that leans on form closure is a number that stops being
    # true the moment a box is a little rounder than expected.
    pads = p.grab_jaws * p.jaw_mu
    need = [(m * (9810.0 + a) / pads / 1000.0, a, m, pid, ph)
            for a, m, pid, ph, _ in diag["carry_accel"]]
    worst = max(need) if need else (0.0, 0.0, 0.0, -1, "")
    rep.add("the claw can hold the box through the carry",
            worst[0] < p.grip_force,
            f"worst case needs {worst[0]:.1f} N per jaw against "
            f"{p.grip_force:.0f} N available -- a {worst[2] * 1000:.0f} g box "
            f"at {worst[1] / 9810.0:.2f} g during {worst[4]}, "
            f"{p.grab_jaws} pads at mu {p.jaw_mu}")


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
    rep.add("the claw stays centred on the box, not near it", trk < 0.2,
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

    bad_zone = sum(1 for ok in diag["zone_ok"] if not ok)
    rep.add("every box was grasped inside its own arm's territory",
            bool(diag["zone_ok"]) and not bad_zone,
            f"{len(diag['zone_ok'])} grasps, all inside" if not bad_zone
            else f"{bad_zone} of {len(diag['zone_ok'])} grasps outside")

    # Once every arm works the full width of its own stretch, two
    # adjacent arms can reach the same air -- the 140 mm between their
    # windows is a gap between the points their *tools* visit, not
    # between the machines. Measured, neighbours came within 3 mm of
    # each other; everything further apart stayed a clear 235 mm off.
    # So the cell interlocks on adjacency, and this is the invariant
    # that replaces the territory rule the half-belt version relied on.
    concurrent = max((sum(1 for p_ in fr.phases if p_ != "IDLE")
                      for fr in frames), default=0)
    rep.add("two arms that can reach the same air are never both working",
            not diag["both_busy"],
            f"never a neighbouring pair; {concurrent} of {len(C.ARMS)} arms "
            f"working at once at the busiest" if not diag["both_busy"]
            else f"{len(diag['both_busy'])} frames, first {diag['both_busy'][0]}")

    sq = max(diag["jaw_square"]) if diag["jaw_square"] else 90.0
    rep.add("the jaws meet the box square to its faces, not on a corner",
            sq < 1.0,
            f"worst misalignment with the belt axis {sq:.3f} deg")

    shut = max((K.opening_for_gap(p, g) for _, _, g, _, _
                in diag["grasp_pose"]), default=0.0)
    widest = max((K.opening_for_gap(p, SO.open_gap(sz)) for _, _, _, sz, _
                  in diag["grasp_pose"]), default=0.0)
    rep.add("the jaws never swing past the travel the head allows",
            widest <= p.grab_open_max and shut >= p.grab_open_min,
            f"widest {widest:.1f} deg, tightest {shut:.1f} deg, of a "
            f"{p.grab_open_min:.0f}..{p.grab_open_max:.0f} deg travel")

    jaw = min(diag["jaw_floor"]) if diag["jaw_floor"] else -1.0
    rep.add("the fingertips clear the belt surface", jaw > 4.0,
            f"lowest fingertip {jaw:.1f} mm above the belt -- a claw"
            f" reaches below what it grips, so this is the number that"
            f" decides how low it can take a short box")

    # Where the grip actually lands on the box. The ridges have to be on
    # a side face: above the top and the claw has hold of nothing, below
    # the bottom and it has hold of the belt.
    off = [(r - b, sz) for r, b, sz in diag["grip_z"]]
    worst = max((abs(d) - sz / 2.0 for d, sz in off), default=-1.0)
    rep.add("the grip lands on the box's side, not over or under it",
            worst < 0.0,
            f"worst ridge position {worst:.1f} mm outside a side face "
            f"(negative is inside it), over {len(off)} frames")

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
    ap.add_argument("--mean-gap", type=float, default=1.4)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--poster", default="")
    args = ap.parse_args(argv)

    w = args.width
    h = int(round(w * 9 / 16))
    p = C.CELL_ARM

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
    check_structure(p, rep)
    check_bands(rep)
    check_program(p, frames, diag, rep)
    check_designation(p, frames, diag, protos, rep)
    check_physics(p, frames, diag, rep)
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
