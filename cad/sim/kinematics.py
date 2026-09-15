"""Tool-centre point, inverse kinematics and trajectory blending.

Forward kinematics is *not* reimplemented here. Every frame below is
obtained from `assembly.joint_frames`, the same function the CAD
assembly uses to place solids, so the arm in the video and the arm in the
STEP file cannot disagree about where a joint is.

The inverse solve is damped least squares over the six joints with a
numerical Jacobian. Six unknowns, a six-component pose error, a damping
term that keeps it stable near singularities. It is seeded from the
previous waypoint's answer, which is what keeps the elbow from flipping
configuration halfway through a move.
"""

from __future__ import annotations

import numpy as np

from dataclasses import replace

from robot_arm.assembly import joint_frames
from robot_arm.params import ArmParams

# Generous but real stops; the program below stays well inside them.
LIMITS = np.array([
    (-185.0, 185.0),   # J1 yaw
    (-125.0, 125.0),   # J2 shoulder
    (-155.0, 155.0),   # J3 elbow
    (-185.0, 185.0),   # J4 forearm roll
    (-125.0, 125.0),   # J5 wrist pitch
    (-185.0, 185.0),   # J6 tool roll
])


def _mat(loc) -> np.ndarray:
    from .scene import loc_matrix
    return loc_matrix(loc)


def grasp_offset(p: ArmParams) -> float:
    """Distance from the J6 frame to the point between the jaw serrations.

    The flange stands `tool_thk + tool_spigot_h` off J6; each finger is
    authored as an L rising `finger_len` with a `finger_thk` tip folded
    across the top. The middle of that tip is where a part is actually
    held.
    """
    return p.tool_thk + p.tool_spigot_h + p.finger_len + p.finger_thk / 2


def _inboard(p: ArmParams) -> float:
    """How far a jaw tip reaches past its own shank centreline.

    `parts.gripper_finger` puts the tip block at
    `-finger_w/2 + finger_thk/2` and makes it `finger_w` wide, so the
    gripping face lands `finger_w - finger_thk/2` inboard -- 10 mm, not
    the 11 mm you get by adding the two half-widths. That was the answer
    this function gave until `test_the_jaws_actually_face_each_other`
    measured the placed triangles and disagreed by exactly 2 mm of
    opening; the jaws were standing 1 mm clear of a part they were
    reported as gripping.
    """
    return p.finger_w - p.finger_thk / 2


def jaw_gap(p: ArmParams) -> float:
    """Clear opening between the two jaw tips at the current stroke."""
    return 2.0 * (p.finger_stroke - _inboard(p))


def stroke_for_gap(p: ArmParams, gap: float) -> float:
    return gap / 2.0 + _inboard(p)


def posed(p: ArmParams, joints, gap: float | None = None) -> ArmParams:
    """A copy of the params at this pose, and optionally this jaw opening.

    `ArmParams` is frozen on purpose, so this goes through
    `dataclasses.replace` rather than reaching past the freeze. The jaw
    opening is a *placement* parameter -- `assembly.build_assembly` reads
    `finger_stroke` to position the two jaws -- so changing it moves the
    fingers without rebuilding them, exactly like a joint angle.
    """
    q = p.at_pose(*joints)
    return q if gap is None else replace(q, finger_stroke=stroke_for_gap(p, gap))


def tcp(p: ArmParams, joints) -> np.ndarray:
    """4x4 world pose of the grasp frame at a given joint vector."""
    f = joint_frames(p.at_pose(*joints))
    m = _mat(f.j6)
    return m @ _translation(0.0, 0.0, grasp_offset(p))


def _translation(x, y, z) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def target_frame(pos, approach=(0.0, 0.0, -1.0), jaw=None) -> np.ndarray:
    """Build a grasp pose: where the jaws meet, which way the tool points,
    and which way the jaws close.

    The pitch joints all turn about their local X, so the arm reaches out
    along its local -Y; the turret must therefore sit 90 degrees round
    from the target's azimuth, and the wrist X axis -- the direction the
    jaws close along -- comes out *tangential*, not radial. Leaving `jaw`
    unset asks for that natural wrist, which keeps the tool roll at zero
    instead of making the solver unwind 90 degrees of J6.
    """
    pos = np.asarray(pos, float)
    z = np.asarray(approach, float)
    z = z / np.linalg.norm(z)
    if jaw is None:
        r = np.array([-pos[1], pos[0], 0.0])      # tangential
        if np.linalg.norm(r) < 1e-6:
            r = np.array([0.0, 1.0, 0.0])
        jaw = r / np.linalg.norm(r)
    x = np.asarray(jaw, float)
    x = x - z * (x @ z)
    x = x / np.linalg.norm(x)
    y = np.cross(z, x)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, pos
    return m


def seed_for(pos, base: ArmParams) -> np.ndarray:
    """A starting guess in the right half of the workspace.

    Damped least squares is a local method: seeded at the home pose it
    will happily walk a 145-degree turret move into a joint stop and stall
    there. Azimuth is the one joint that can be read straight off the
    target, so give it away for free and let the solver do the rest.
    """
    phi = np.degrees(np.arctan2(pos[1], pos[0]))
    q = np.array(base.joints, float)
    q[0] = (phi + 90.0 + 180.0) % 360.0 - 180.0
    return q


def _pose_error(cur: np.ndarray, goal: np.ndarray) -> np.ndarray:
    e = np.empty(6)
    e[:3] = goal[:3, 3] - cur[:3, 3]
    r = goal[:3, :3] @ cur[:3, :3].T
    ang = np.arccos(np.clip((np.trace(r) - 1.0) / 2.0, -1.0, 1.0))
    if ang < 1e-9:
        e[3:] = 0.0
    else:
        axis = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]])
        e[3:] = axis / (2.0 * np.sin(ang)) * ang
    return e


def solve_ik(p: ArmParams, goal: np.ndarray, seed, iters=220,
             tol_mm=0.02, tol_deg=0.02):
    """Damped least squares. Returns (joints, position error, angle error)."""
    q = np.array(seed, float)
    lam = 6.0
    for _ in range(iters):
        cur = tcp(p, q)
        e = _pose_error(cur, goal)
        pos_err = np.linalg.norm(e[:3])
        ang_err = np.degrees(np.linalg.norm(e[3:]))
        if pos_err < tol_mm and ang_err < tol_deg:
            break
        j = np.empty((6, 6))
        for k in range(6):
            dq = np.zeros(6)
            dq[k] = 1e-4
            j[:, k] = (_pose_error(cur, tcp(p, q + dq))) / 1e-4
        # Angular rows are radians, linear rows are millimetres; weight the
        # angular block up so a degree of tilt is not lost next to a
        # millimetre of position.
        w = np.diag([1.0, 1.0, 1.0, 180.0, 180.0, 180.0])
        jw, ew = w @ j, w @ e
        dq = jw.T @ np.linalg.solve(jw @ jw.T + (lam ** 2) * np.eye(6), ew)
        step = np.linalg.norm(dq)
        if step > 8.0:
            dq *= 8.0 / step
        q = np.clip(q + dq, LIMITS[:, 0], LIMITS[:, 1])
    cur = tcp(p, q)
    e = _pose_error(cur, goal)
    return q, float(np.linalg.norm(e[:3])), float(np.degrees(np.linalg.norm(e[3:])))


# --------------------------------------------------------------------
# blending
# --------------------------------------------------------------------
def ease(t: float) -> float:
    """Quintic smoothstep: zero velocity *and* zero acceleration at both
    ends, so the arm starts and stops without a jerk in the motion."""
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def blend(a, b, t: float):
    s = ease(t)
    return np.asarray(a, float) * (1.0 - s) + np.asarray(b, float) * s
