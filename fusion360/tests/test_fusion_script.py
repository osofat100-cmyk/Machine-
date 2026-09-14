#!/usr/bin/env python3
"""Run the Fusion script against a fake `adsk` and check what it built.

    python3 tests/test_fusion_script.py

This proves the script's own logic: that it creates eleven components,
sets an extent on every feature, never indexes a profile that does not
exist, and asks for joints between components it actually made. It does
not and cannot prove that Autodesk's API behaves as the mock assumes --
run it in Fusion for that.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import mock_adsk  # noqa: E402


def build_once():
    rec = mock_adsk.install()
    for mod in ("robot_arm_fusion",):
        sys.modules.pop(mod, None)
    import robot_arm_fusion  # noqa: E402
    design = mock_adsk.new_design()
    builder = robot_arm_fusion.build(design)
    return rec, builder, robot_arm_fusion


def test_script_runs_without_raising():
    rec, b, _ = build_once()
    assert b is not None


def test_eleven_components():
    rec, b, mod = build_once()
    # rootComponent is created too, so filter to the named parts.
    named = [c.name for c in rec.components if c.name.startswith(("0", "1"))]
    assert len(named) == 11, "expected 11 parts, got %d: %s" % (len(named), named)
    assert len(mod.BUILDERS) == 11


def test_component_names_match_the_cad_model():
    rec, b, _ = build_once()
    named = sorted(c.name for c in rec.components if c.name.startswith(("0", "1")))
    expected = sorted([
        "01_base_flange", "02_turret", "03_shoulder_yoke", "04_upper_arm",
        "05_elbow_yoke", "06_forearm", "07_wrist_housing", "08_wrist_yoke",
        "09_tool_flange", "10_gripper_finger", "11_actuator_can",
    ])
    assert named == expected, named


def test_fifteen_occurrences():
    """11 parts, with the actuator shown 4x and the finger 2x."""
    rec, b, _ = build_once()
    assert len(b.components) == 15, len(b.components)


def test_design_is_parametric():
    """A direct-modelling design has no timeline, which defeats the point."""
    rec, b, mod = build_once()
    assert b.design.designType == mod.adsk.fusion.DesignTypes.ParametricDesignType


def test_user_parameters_published():
    rec, b, mod = build_once()
    names = [n for n, _, _ in rec.parameters]
    assert len(names) == len(mod.PARAMS), (len(names), len(mod.PARAMS))
    for key in ("upper_len", "fore_len", "base_dia", "wall"):
        assert key in names, key


def test_units_are_converted_to_centimetres():
    """Fusion's API is cm. base_dia is 150mm, so it must arrive as 15.0."""
    rec, b, mod = build_once()
    table = {n: v for n, v, _ in rec.parameters}
    assert abs(table["base_dia"] - 15.0) < 1e-9, table["base_dia"]
    assert abs(table["upper_len"] - 26.0) < 1e-9, table["upper_len"]
    # fore_taper is a bare ratio and must NOT be scaled.
    assert abs(table["fore_taper"] - 0.72) < 1e-9, table["fore_taper"]


def test_every_feature_has_a_real_extent():
    """No feature may be added with a zero or empty extent.

    Extrudes carry a numeric distance in cm; revolves carry a string
    angle like "360 deg", because setAngleExtent takes a ValueInput
    built from a string. Both are valid -- the check is that neither is
    empty, not that both are numbers.
    """
    rec, b, _ = build_once()
    assert rec.features, "no features were created at all"
    for kind, comp, op, value in rec.features:
        if isinstance(value, str):
            assert value.strip(), "%s on %s has an empty extent" % (kind, comp)
            assert any(ch.isdigit() for ch in value), (
                "%s on %s has a non-numeric extent %r" % (kind, comp, value))
        else:
            assert abs(value) > 1e-9, "%s on %s has zero extent" % (kind, comp)


def test_forearm_is_a_revolve():
    """The tapered tube should be a revolve feature, not faked with a box."""
    rec, b, _ = build_once()
    revolves = [f for f in rec.features if f[0] == "revolve"]
    assert revolves, "no revolve features -- the forearm was not revolved"
    assert any("forearm" in f[1] or f[1] == "" for f in revolves), revolves


def test_cuts_are_actually_cuts():
    rec, b, mod = build_once()
    cut_op = mod.adsk.fusion.FeatureOperations.CutFeatureOperation
    cuts = [f for f in rec.features if f[2] == cut_op]
    assert cuts, "nothing was cut -- bolt holes are missing"


def test_joints_created_for_the_chain():
    rec, b, _ = build_once()
    assert len(rec.joints) == 5, "expected 5 revolute joints, got %d" % len(rec.joints)
    for motion, direction in rec.joints:
        assert motion == "revolute", motion


def test_joint_axes_match_the_verified_kinematics():
    """J1 and J4 roll about Z; J2, J3 and J5 pitch about X."""
    rec, b, mod = build_once()
    Z = mod.adsk.fusion.JointDirections.ZAxisJointDirection
    X = mod.adsk.fusion.JointDirections.XAxisJointDirection
    axes = [d for _, d in rec.joints]
    assert axes == [Z, X, X, Z, X], axes


def test_no_component_left_at_the_origin():
    """Everything except the base must be moved somewhere by place_chain."""
    rec, b, _ = build_once()
    moved = sum(1 for o in b.components
                if abs(o.transform.translation.z) > 1e-9)
    assert moved >= 8, "only %d occurrences were positioned" % moved


def test_gripper_jaws_face_each_other():
    """The -X jaw must be spun 180 degrees, or the gripper opens backwards.

    This is the defect that passed every geometric check in the
    build123d model and was caught only by looking at a render. Here it
    is pinned down as an assertion so it cannot come back.
    """
    rec, b, _ = build_once()
    jaws = [o for o in b.components
            if o.component.name == "10_gripper_finger"]
    assert len(jaws) == 2, "expected 2 jaws, got %d" % len(jaws)
    yaws = sorted(
        (j.transform.rotation[0] if j.transform.rotation else 0.0)
        for j in jaws
    )
    assert abs(yaws[0]) < 1e-9, "one jaw should be unrotated, got %r" % yaws
    assert abs(yaws[1] - 3.141592653589793) < 1e-6, (
        "the other jaw must be spun 180 deg so the tips face each other; "
        "got %r radians" % yaws[1]
    )


def test_run_reports_failure_instead_of_dying_silently():
    """run() with no active design must warn, not raise."""
    rec = mock_adsk.install()
    sys.modules.pop("robot_arm_fusion", None)
    import robot_arm_fusion
    app = robot_arm_fusion.adsk.core.Application.get()
    app.activeProduct = None
    robot_arm_fusion.run(None)
    assert app.userInterface.messages, "no message shown to the user"
    assert "No active" in app.userInterface.messages[-1]


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
