#!/usr/bin/env python3
"""Tests. Runs under pytest, or standalone with `python3 test_robot_arm.py`.

The interesting tests are the ones that would have caught the defects
found while building this: a part silently becoming two disconnected
solids, a fillet failing without complaint, and a kinematic chain that
disagrees with the arithmetic it is supposed to implement.
"""

from __future__ import annotations

import sys

import numpy as np

from robot_arm.assembly import build_assembly, instance_count, joint_frames
from robot_arm.params import ArmParams
from robot_arm import parts as P
from robot_arm import verify

DEFAULT = ArmParams()


def test_fourteen_parts():
    assert len(P.BUILDERS) == 14
    assert len(P.build_all(DEFAULT)) == 14


def test_assembly_shape():
    distinct, instances = instance_count(DEFAULT)
    assert distinct == 14
    assert instances == 20  # claw jaws x4, actuator x4


def test_every_part_is_one_watertight_solid():
    """The wrist housing was briefly two disjoint solids. Never again."""
    for name, part in P.build_all(DEFAULT).items():
        assert len(part.solids()) == 1, f"{name} is not a single solid"
        assert part.volume > 1.0, f"{name} is degenerate"


def test_no_fillet_is_dropped_silently():
    P._safe_fillet.dropped = 0
    P.build_all(DEFAULT)
    assert P._safe_fillet.dropped == 0


def test_kinematics_matches_independent_fk():
    """Two implementations of the joint chain must agree."""
    for pose in [(0, 0, 0, 0, 0, 0),
                 (90, -45, 90, 30, -60, 15),
                 (-120, 20, -75, -90, 45, -30)]:
        p = DEFAULT.at_pose(*pose)
        got = joint_frames(p).tool.position
        want = verify.fk_reference(p)[:3, 3]
        assert np.allclose([got.X, got.Y, got.Z], want, atol=1e-9), pose


def test_joints_turn_about_intended_axes():
    expected = ("Z", "X", "X", "Z", "X", "Z")
    for i, axis in enumerate(expected):
        angles = [0.0] * 6
        angles[i] = 25.0
        got = verify.fk_reference(DEFAULT.at_pose(*angles))[:3, :3]
        want = (verify._rz(25.0) if axis == "Z" else verify._rx(25.0))[:3, :3]
        assert np.allclose(got, want, atol=1e-9), f"J{i + 1} is not about {axis}"


def test_model_is_re_drivable():
    """A parametric model that only works at its default numbers isn't one."""
    for kw in (dict(upper_len=420.0, fore_len=350.0),
               dict(upper_len=150.0, fore_len=120.0, base_dia=110.0),
               dict(wall=9.0, upper_w=60.0, upper_h=80.0),
               dict(wall=4.0, fillet=1.5)):
        rep = verify.run(ArmParams(**kw))
        assert rep.ok, f"{kw} failed:\n{rep.render()}"


def test_full_verification_passes():
    rep = verify.run(DEFAULT)
    assert rep.ok, "\n" + rep.render()


def test_pose_is_rejected_when_malformed():
    try:
        DEFAULT.at_pose(1, 2, 3)
    except ValueError:
        return
    raise AssertionError("at_pose accepted the wrong number of angles")


def _main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
