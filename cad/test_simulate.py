#!/usr/bin/env python3
"""Tests for the simulation and its renderer.

Runs under pytest, or standalone with `python3 test_simulate.py`.

The animation makes a stronger claim than the still renders do: that the
thing moving on screen is the CAD model, driven through poses it can
actually hold. Most of what is below exists to keep that claim honest --
that the placements are the assembly's own, that the mesh is the solid,
that the solver reaches what it was asked for, and that the jaws close
the right way round.

The last two tests check the rasteriser against arithmetic rather than
against geometry, because a renderer that silently draws the far surface
in front of the near one would make every other test here look fine.
"""

from __future__ import annotations

import numpy as np

from robot_arm import assembly as A
from robot_arm import parts as P
from robot_arm import verify
from robot_arm.params import ArmParams
from sim import kinematics as K, program as PG, raster as R, scene as S
import simulate as SIM

DEFAULT = ArmParams()
_PROTOS = None


def protos():
    global _PROTOS
    if _PROTOS is None:
        _PROTOS = S.tessellate_parts(DEFAULT, deflection=0.4, angular=0.3)
    return _PROTOS


# ---------------------------------------------------------------------
# the model is the model
# ---------------------------------------------------------------------
def test_placements_are_the_assemblys_own():
    """The animation swaps the solids out to read placements cheaply. If
    that ever stops matching the real assembly, the video stops being of
    the model, so compare all fifteen transforms exactly."""
    for pose in [(0, 0, 0, 0, 0, 0), DEFAULT.joints, (90, -35, 125, 0, -15, 0)]:
        p = DEFAULT.at_pose(*pose)
        real = A.build_assembly(p)
        stub = S.placements(p)
        assert len(stub) == len(real.children) == 15
        for (key, label, m), child in zip(stub, real.children):
            assert label == child.label
            assert np.array_equal(m, S.loc_matrix(child.location)), label


def test_prototypes_are_authored_at_the_origin():
    """Caching one tessellation per part and re-placing it is only valid
    if the prototypes carry no location of their own."""
    for name, part in P.build_all(DEFAULT).items():
        m = S.loc_matrix(part.location)
        assert np.allclose(m, np.eye(4), atol=1e-9), name


def test_the_mesh_is_the_solid():
    """A tessellation can be wrong in ways that still render: dropped
    faces, inverted triangles. Compare the mesh's own signed volume with
    the exact volume OCCT reports for the solid."""
    lib = P.build_all(DEFAULT)
    for name, mesh in protos().items():
        v = mesh.verts[mesh.tris]
        vol = abs(np.einsum("ij,ij->i",
                            v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6.0)
        exact = lib[name].volume
        assert abs(vol - exact) / exact < 0.02, (name, vol, exact)


def test_forward_kinematics_is_not_reimplemented():
    """`sim` must agree with the 4x4 chain `verify` derives independently."""
    for pose in [(0, 0, 0, 0, 0, 0), (35, 21, 80, 0, 79, 0),
                 (145, 21, 80, 0, 79, 0), (90, -35, 125, 0, -15, 0)]:
        p = DEFAULT.at_pose(*pose)
        want = verify.fk_reference(p)          # the tool mounting face
        got = K.tcp(p, pose).copy()            # the point between the jaws
        got[:3, 3] -= got[:3, 2] * (p.finger_len + p.finger_thk / 2)
        assert np.allclose(got, want, atol=1e-6), pose


# ---------------------------------------------------------------------
# the solver reaches what it is asked for
# ---------------------------------------------------------------------
def test_ik_round_trip():
    rng = np.random.default_rng(7)
    for _ in range(12):
        az = rng.uniform(-70, 70)
        r = rng.uniform(340, 500)
        z = rng.uniform(130, 420)
        goal = K.target_frame(PG._at(az, r, z))
        q, pe, ae = K.solve_ik(DEFAULT, goal, K.seed_for(goal[:3, 3], DEFAULT))
        assert pe < 0.2 and ae < 0.2, (az, r, z, pe, ae)
        assert (q >= K.LIMITS[:, 0]).all() and (q <= K.LIMITS[:, 1]).all()


def test_natural_wrist_leaves_the_rolls_alone():
    """Default jaw direction should not cost 90 degrees of tool roll."""
    goal = K.target_frame(PG.PICK)
    q, _, _ = K.solve_ik(DEFAULT, goal, K.seed_for(PG.PICK, DEFAULT))
    assert abs(q[3]) < 1.0 and abs(q[5]) < 1.0, q


def test_jaw_gap_round_trips_through_the_stroke():
    for gap in (18.0, 24.0, 32.0, 54.0):
        p = DEFAULT
        q = K.posed(p, p.joints, gap)
        assert abs(K.jaw_gap(q) - gap) < 1e-9


def test_the_jaws_actually_face_each_other():
    """The one defect in this repo's history that passed every solid
    check and was caught only by looking at a render: a gripper whose
    jaws fold outward. Measure the opening off the placed triangles and
    make it agree with the arithmetic the program grips by."""
    gap = 32.0
    p = K.posed(DEFAULT, (35, 21, 80, 0, 79, 0), gap)
    j6 = np.linalg.inv(S.loc_matrix(A.joint_frames(p).j6))
    tips = []
    for label, mesh in S.arm_instances(p, protos()):
        if not label.startswith("10_gripper_finger"):
            continue
        local = (j6[:3, :3] @ mesh.verts.T).T + j6[:3, 3]
        lo = p.tool_thk + p.tool_spigot_h + p.finger_len
        band = local[(local[:, 2] > lo - 0.5) & (local[:, 2] < lo + p.finger_thk + 0.5)]
        assert len(band), label
        tips.append((band[:, 0].min(), band[:, 0].max()))
    tips.sort()
    measured = tips[1][0] - tips[0][1]
    assert measured > 0, "the jaws overlap -- they are not a gripper"
    assert abs(measured - K.jaw_gap(p)) < 0.02, (measured, K.jaw_gap(p))


# ---------------------------------------------------------------------
# the program
# ---------------------------------------------------------------------
def test_program_passes_its_own_checks():
    p = ArmParams()
    moves = PG.cycle()
    states, diag = PG.expand(p, moves, fps=20, report=lambda *a: None)
    track = SIM.payload_track(p, states)
    rep = SIM.check(p, states, diag, track)
    SIM.check_clearance(p, states, protos(), rep, stride=6)
    assert rep.ok, rep.render()


def test_lin_moves_are_straight_not_merely_endpoint_correct():
    p = ArmParams()
    states, diag = PG.expand(p, PG.cycle(), fps=20, report=lambda *a: None)
    assert diag["lin_dev"], "no straight-line move in the program"
    assert max(diag["lin_dev"]) < 0.5


def test_camera_frames_every_pose():
    p = ArmParams()
    states, _ = PG.expand(p, PG.cycle(), fps=20, report=lambda *a: None)
    track = SIM.payload_track(p, states)
    w, h = 640, 360
    cam = SIM.frame_camera(p, states, protos(), w, h, track)
    for i in range(0, len(states), 5):
        st = states[i]
        pose = K.posed(p, st.joints, st.gap)
        for m in S.arm_meshes(pose, protos()):
            sx, sy, zc = R.project(m.verts, cam, w, h)
            assert zc.min() > cam.near
            assert sx.min() > 0 and sx.max() < w, (st.phase, sx.min(), sx.max())
            assert sy.min() > 0 and sy.max() < h, (st.phase, sy.min(), sy.max())


# ---------------------------------------------------------------------
# the renderer, checked against arithmetic
# ---------------------------------------------------------------------
def _quad(y, half=100.0):
    """A square in the XZ plane, square-on to a camera down -Y."""
    v = np.array([[-half, y, -half], [half, y, -half],
                  [half, y, half], [-half, y, half]], float)
    return v, np.array([[0, 1, 2], [0, 2, 3]])


def test_rasteriser_draws_the_near_surface():
    """Two overlapping quads, the second one farther away. The near one
    must win every shared pixel -- a painter's-algorithm renderer fed in
    the wrong order gets this backwards, and a folded arm is nothing but
    shared pixels."""
    cam = R.look(eye=(0, -1000, 0), target=(0, 0, 0), up=(0, 0, 1), fov=40)
    near_v, t = _quad(0.0)
    far_v, _ = _quad(400.0)          # same size, further down the view axis
    verts = np.vstack([near_v, far_v])
    tris = np.vstack([t, t + 4])
    tribuf, hit, _ = R.depth_pass(verts, tris, cam, 160, 120)
    assert hit.size > 0
    assert set(np.unique(tribuf[hit])) == {0, 1}, "the far quad showed through"

    # and with the order reversed, the answer must not change
    verts2 = np.vstack([far_v, near_v])
    tribuf2, hit2, _ = R.depth_pass(verts2, tris, cam, 160, 120)
    assert set(np.unique(tribuf2[hit2])) == {2, 3}


def test_rasteriser_covers_the_area_it_should():
    """A square of known size, square to the camera, must cover the
    number of pixels the pinhole projection says it does."""
    w, h, dist, half = 400, 400, 1000.0, 100.0
    cam = R.look(eye=(0, -dist, 0), target=(0, 0, 0), up=(0, 0, 1), fov=40)
    verts, tris = _quad(0.0, half)
    _, hit, _ = R.depth_pass(verts, tris, cam, w, h)
    f = (h / 2) / np.tan(np.radians(40) / 2)
    want = (2 * half * f / dist) ** 2
    assert abs(hit.size - want) / want < 0.02, (hit.size, want)


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
