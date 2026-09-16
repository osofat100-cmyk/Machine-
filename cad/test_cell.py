#!/usr/bin/env python3
"""Tests for the five-arm sort cell.

Runs under pytest, or standalone with `python3 test_cell.py`.

The cell makes four promises that are not obvious from looking at it:
every arm can reach everything it is asked to reach, no two arms ever
own the same box, no two arms ever come near each other, and the tool is
travelling at belt speed when the jaws close. The first three are
properties of the *layout*, so they are re-derived here from the numbers
in `cell.py` rather than read back out of it; the fourth needs the thing
run, so a short run is what these tests use.
"""

from __future__ import annotations

import numpy as np

from robot_arm.params import ArmParams
from sim import cell as C, kinematics as K, sorter as SO
import simulate_cell as SIM

DEFAULT = C.CELL_ARM
_RUN = None
_PROTOS = None


def run():
    global _RUN
    if _RUN is None:
        _RUN = SO.run(DEFAULT, seconds=11.0, fps=15, mean_gap=1.45,
                      report=None)
    return _RUN


def protos():
    global _PROTOS
    if _PROTOS is None:
        from sim import scene as S
        _PROTOS = S.tessellate_parts(DEFAULT, deflection=0.6, angular=0.4)
    return _PROTOS


# ---------------------------------------------------------------------
# the layout
# ---------------------------------------------------------------------
def test_windows_on_a_side_never_overlap():
    for i, a in enumerate(C.ARMS):
        for b in C.ARMS[i + 1:]:
            if a.side != b.side:
                continue
            assert a.x1 < b.x0 or b.x1 < a.x0, (a.name, b.name)


def test_a_box_belongs_to_at_most_one_arm():
    """Side and window between them must partition the belt."""
    for x in np.linspace(C.BELT_X0, C.BELT_X1, 220):
        for y in np.linspace(-C.BELT_HALF_W, C.BELT_HALF_W, 25):
            owners = [a for a in C.ARMS if a.owns(x, y)]
            assert len(owners) <= 1, (x, y, [o.name for o in owners])


def test_the_reach_annulus_is_inside_what_the_model_can_do():
    """R_MIN/R_MAX are constants; the model decides whether they are
    honest ones. Re-measure and hold them to it."""
    for z in (C.BELT_TOP + C.CLASSES[0].lo / 2,
              C.BELT_TOP + C.CLASSES[-1].hi / 2,
              C.BELT_TOP + C.CLASSES[-1].hi / 2 + C.HOVER):
        lo, hi = C.measure_envelope(DEFAULT, z)
        assert lo <= C.R_MIN, (z, lo, C.R_MIN)
        assert hi >= C.R_MAX, (z, hi, C.R_MAX)


def test_every_point_an_arm_must_reach_is_inside_the_annulus():
    for arm in C.ARMS:
        for pt in C.working_set(arm):
            r = float(np.hypot(*arm.to_local(pt)[:2]))
            assert C.R_MIN <= r <= C.R_MAX, (arm.name, np.round(pt, 0), r)


def test_every_point_an_arm_must_reach_actually_solves():
    """The annulus is a summary. This is the thing itself: ask the
    solver for a tool pointing down at every corner and every bin."""
    worst = 0.0
    for arm in C.ARMS:
        for pt in C.working_set(arm):
            lp = arm.to_local(pt)
            q, pe, ae = K.solve_ik(DEFAULT, K.target_frame(lp),
                                   K.seed_for(lp, DEFAULT))
            worst = max(worst, pe, ae)
            assert pe < 0.2 and ae < 0.2, (arm.name, np.round(pt, 0), pe, ae)
    assert worst < 0.2


def test_turret_travel_fits_with_margin():
    lo_l, hi_l = K.LIMITS[0]
    for arm in C.ARMS:
        lo, hi = C.turret_span(arm)
        assert lo > lo_l + 15.0 and hi < hi_l - 15.0, (arm.name, lo, hi)


def test_the_base_yaw_is_derived_not_chosen():
    """Rebuild each arm's yaw from its world points and require the same
    answer -- the layout is supposed to follow the geometry."""
    for arm in C.ARMS:
        xc = (arm.x0 + arm.x1) / 2.0
        face = 90.0 if arm.side < 0 else 270.0
        yaw, lo, hi = C.turret_plan(
            arm.origin, C._world_points(xc, arm.side, arm.bins), face)
        assert abs((yaw - arm.yaw + 180) % 360 - 180) < 1e-9, arm.name
        assert np.allclose((lo, hi), arm.j1_range)


def test_cover_arc_handles_a_straddling_set():
    """Angles on a circle: the naive min/max reports 350 degrees for a
    set that spans ten."""
    (start, width), = C.cover_arcs([-5.0, 0.0, 5.0])
    assert abs(width - 10.0) < 1e-9
    assert abs((start + 5.0) % 360.0) < 1e-9
    assert len(C.cover_arcs([0.0, 90.0, 180.0, 270.0])) == 4


def test_boxes_are_classified_by_what_is_measured():
    """The bands must partition their range, and nothing may route on a
    class that was decided anywhere but here."""
    for cls in C.CLASSES:
        for sz in np.linspace(cls.lo, cls.hi, 40):
            assert C.classify(sz).key == cls.key, (sz, cls.key)
    for a, b in zip(C.CLASSES, C.CLASSES[1:]):
        assert b.lo > a.hi, (a.key, b.key)
    pc = SO.Parcel(0, C.CLASSES[2].nominal, 0.0, 0.0, 0.0)
    assert pc.cls.key == "L"


def test_the_jaws_stay_in_their_slot():
    """The gripper used to be two fingers on the tool face, slid apart,
    with no body and so no limit: past a certain opening they were two
    solids floating near the flange. `verify.check_gripper` is what
    makes that impossible; this is that it runs."""
    from robot_arm.verify import Report, check_gripper
    rep = Report()
    check_gripper(DEFAULT, rep)
    assert rep.ok, rep.render()
    assert DEFAULT.finger_mount_z > DEFAULT.flange_face_z


def test_an_arm_works_the_full_width_of_its_own_stretch():
    """Both edges, not just the near one -- and it can actually solve
    for a tool pose at each."""
    for arm in C.ARMS:
        for sgn in (-1, 1):
            far = np.array([(arm.x0 + arm.x1) / 2.0,
                            sgn * C.BELT_HALF_W, C.BELT_TOP + 20.0])
            lp = arm.to_local(far)
            q, pe, ae = K.solve_ik(DEFAULT, K.target_frame(lp),
                                   K.seed_for(lp, DEFAULT))
            assert pe < 0.2 and ae < 0.2, (arm.name, sgn, pe, ae)
            assert arm.owns(far[0], far[1]), (arm.name, sgn)


def test_a_jaw_axis_is_an_axis():
    """Half a turn swaps the jaws and grips the same box, so the wrap
    that matters is 180, not 360."""
    assert abs(SO._wrap_half(np.pi)) < 1e-12
    assert abs(SO._wrap_half(np.radians(179.0)) - np.radians(-1.0)) < 1e-9


# ---------------------------------------------------------------------
# the dispatcher
# ---------------------------------------------------------------------
def test_an_arm_only_claims_from_its_own_half_and_window():
    for arm in C.ARMS:
        for y in (-140.0, 140.0):
            for x0 in np.linspace(C.BELT_X0, C.BELT_X1 - 400.0, 40):
                pc = SO.Parcel(0, C.CLASSES[1].nominal, y, x0, 0.0)
                if not SO.can_claim(arm, pc, 0.0):
                    continue
                meet = pc.belt_point(SO.INTERCEPT_T)
                assert arm.in_window(meet[0]), (arm.name, meet[0])
                assert arm.owns(meet[0], y), (arm.name, meet[0], y)
                assert arm.can_reach(meet)


def test_boxes_are_never_spawned_on_top_of_each_other():
    ps = SO.spawn_plan(40.0, seed=3, mean_gap=0.9)
    xs = sorted(p.t0 * C.BELT_SPEED for p in ps)
    assert min(np.diff(xs)) >= SO.MIN_GAP_X - 1e-6


def test_a_box_the_first_arm_is_busy_for_goes_downstream():
    _, diag = run()
    first = {}
    for _, name, pid, _ in diag["claims"]:
        first.setdefault(pid, name)
    assert any(n not in ("A1", "A2") for n in first.values()), first


def test_every_grasp_happens_inside_its_own_territory():
    _, diag = run()
    assert diag["zone_ok"] and all(diag["zone_ok"])
    for name, pid, key, x, y in diag["grasps"]:
        arm = next(a for a in C.ARMS if a.name == name)
        assert arm.owns(x, y), (name, x, y)


def test_boxes_land_on_what_is_already_in_the_bin():
    """They fall and pile. They used to be placed on a 3x3 grid, which
    looked exactly like what it was."""
    frames, _ = run()
    per_bin = {}
    for sn in frames[-1].parcels:
        if sn.state != "binned" or sn.claimed_by is None:
            continue
        per_bin.setdefault((sn.claimed_by, sn.key), []).append(sn)
    assert per_bin, "nothing was binned"
    for boxes in per_bin.values():
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                da = a.pose[:3, 3] - b.pose[:3, 3]
                span = (a.size + b.size) / 2.0
                if abs(da[0]) < span and abs(da[1]) < span:
                    assert abs(da[2]) >= span - 1e-6, (a.pid, b.pid, da)
    yaws = [float(np.arctan2(sn.pose[1, 0], sn.pose[0, 0]))
            for boxes in per_bin.values() for sn in boxes]
    if len(yaws) > 2:
        assert np.std(yaws) > 0.1, "every box landed at the same angle"


def test_each_box_ends_up_in_the_bin_for_its_size():
    frames, _ = run()
    for sn in frames[-1].parcels:
        if sn.state != "binned" or sn.claimed_by is None:
            continue
        arm = C.ARMS[sn.claimed_by]
        want = arm.bins[sn.key]
        if np.linalg.norm(sn.pose[:2, 3] - want[:2]) > 200.0:
            continue                       # ran off the end, not binned here
        assert np.linalg.norm(sn.pose[:2, 3] - want[:2]) < 120.0, sn.pid


# ---------------------------------------------------------------------
# the moving pick
# ---------------------------------------------------------------------
def test_the_tool_matches_belt_speed_at_the_grasp():
    """The claim the whole design rests on. Not asserted anywhere in the
    motion -- it falls out of the quintic ease having zero derivative at
    the end of the approach -- so it is worth measuring."""
    _, diag = run()
    assert diag["grasp_rel"]
    assert max(diag["grasp_rel"]) < 1.0, max(diag["grasp_rel"])


def test_the_tool_is_on_the_box_through_the_close():
    _, diag = run()
    assert max(diag["track_err"]) < 0.2


def test_the_jaws_are_square_to_the_box():
    _, diag = run()
    assert max(diag["jaw_square"]) < 1.0, max(diag["jaw_square"])


def test_every_commanded_pose_is_reached():
    _, diag = run()
    assert max(diag["ik_pos"]) < 0.2 and max(diag["ik_ang"]) < 0.2


def test_no_joint_reaches_a_stop():
    frames, _ = run()
    q = np.array([f.joints for f in frames])
    for k in range(6):
        assert np.abs(q[:, :, k]).max() < K.LIMITS[k][1] - 5.0, k


# ---------------------------------------------------------------------
# the thing the whole layout exists for
# ---------------------------------------------------------------------
def test_no_two_arms_ever_come_near_each_other():
    """Disjoint territory constrains the *tool*. It says nothing about
    where the elbow is, so measure the placed triangles."""
    from robot_arm.verify import Report
    frames, _ = run()
    rep = Report()
    worst = SIM.check_clearance(DEFAULT, frames, protos(), rep, stride=3)
    assert rep.ok, rep.render()
    assert worst >= SIM.CLEARANCE_FLOOR, worst


def main() -> int:
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  [PASS] {name}")
        except AssertionError as e:
            fails += 1
            print(f"  [FAIL] {name}: {e}")
    print(f"  {'ALL TESTS PASSED' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
