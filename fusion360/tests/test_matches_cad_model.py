#!/usr/bin/env python3
"""The Fusion script and the verified build123d model must agree.

Two models of the same arm are only useful if they are the same arm.
The build123d one in `cad/` is the one with eight automated checks and
an independently-computed kinematic chain behind it; this test holds the
Fusion script to those same numbers, so a dimension cannot drift in one
without the other noticing.

Needs build123d installed (pip install build123d). Skips cleanly if not.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(REPO, "cad"))

import mock_adsk  # noqa: E402

mock_adsk.install()
import robot_arm_fusion as F  # noqa: E402

try:
    from robot_arm.params import DEFAULT as CAD
except ImportError:
    CAD = None


#: Fusion parameter name -> build123d ArmParams attribute.
MAPPING = {
    "wall": "wall",
    "base_dia": "base_dia",
    "base_thk": "base_thk",
    "base_bolt_bc": "base_bolt_circle",
    "base_bolt_dia": "base_bolt_dia",
    "turret_dia": "turret_dia",
    "turret_h": "turret_h",
    "turret_bore": "turret_bore",
    "yoke_width": "yoke_width",
    "yoke_gap": "yoke_gap",
    "yoke_h": "yoke_h",
    "upper_len": "upper_len",
    "upper_w": "upper_w",
    "upper_h": "upper_h",
    "elbow_width": "elbow_width",
    "elbow_gap": "elbow_gap",
    "fore_len": "fore_len",
    "fore_dia": "fore_dia",
    "fore_taper": "fore_taper",
    "wrist_dia": "wrist_dia",
    "wrist_len": "wrist_len",
    "wyoke_width": "wyoke_width",
    "wyoke_gap": "wyoke_gap",
    "wyoke_h": "wyoke_h",
    "tool_dia": "tool_dia",
    "tool_thk": "tool_thk",
    "tool_bolt_bc": "tool_bolt_circle",
    "finger_len": "finger_len",
    "finger_w": "finger_w",
    "finger_thk": "finger_thk",
    "finger_stroke": "finger_stroke",
    "act_dia": "act_dia",
    "act_len": "act_len",
}


def test_every_dimension_matches_the_cad_model():
    if CAD is None:
        print("     (skipped: build123d not installed)")
        return
    drift = []
    for fusion_name, cad_attr in MAPPING.items():
        want = getattr(CAD, cad_attr)
        got = F.P[fusion_name]
        if abs(got - want) > 1e-9:
            drift.append("%s: fusion=%g cad=%g" % (fusion_name, got, want))
    assert not drift, "dimensions have drifted apart:\n  " + "\n  ".join(drift)


def test_no_fusion_parameter_is_unmapped():
    """A new parameter must be added to the mapping, not quietly ignored."""
    unmapped = sorted(set(F.P) - set(MAPPING))
    assert not unmapped, "these Fusion params are not cross-checked: %s" % unmapped


def test_part_names_match():
    if CAD is None:
        print("     (skipped: build123d not installed)")
        return
    from robot_arm import parts as CADP
    cad_names = sorted(fn(CAD).label for fn in CADP.BUILDERS)
    mock_adsk.install()
    sys.modules.pop("robot_arm_fusion", None)
    import robot_arm_fusion as F2
    design = mock_adsk.new_design()
    F2.build(design)
    fusion_names = sorted(
        c.name for c in mock_adsk.REC.components if c.name.startswith(("0", "1"))
    )
    assert fusion_names == cad_names, (
        "part lists differ:\n  fusion=%s\n  cad=%s" % (fusion_names, cad_names)
    )


def test_joint_stack_heights_match():
    """The Fusion placement must stack to the same joint heights."""
    if CAD is None:
        print("     (skipped: build123d not installed)")
        return
    h = F.joint_heights()
    assert abs(h["j1_z"] - CAD.base_thk) < 1e-9
    assert abs(h["j2_z"] - (CAD.turret_h + CAD.yoke_h)) < 1e-9
    assert abs(h["j3_z"] - CAD.upper_len) < 1e-9
    assert abs(h["j4_z"] - (CAD.elbow_width * 0.62 + CAD.fore_len)) < 1e-9
    assert abs(h["j5_z"] - (CAD.wrist_len + CAD.wyoke_h)) < 1e-9


def test_home_pose_matches():
    if CAD is None:
        print("     (skipped: build123d not installed)")
        return
    assert tuple(F.POSE) == tuple(CAD.joints), (F.POSE, CAD.joints)


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print("  PASS  %s" % t.__name__)
        except Exception as exc:
            failed += 1
            print("  FAIL  %s: %s" % (t.__name__, exc))
    print("\n%d/%d passed" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_main())
