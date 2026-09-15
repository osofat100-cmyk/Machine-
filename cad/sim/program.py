"""The motion program, and the timeline it expands into.

A pick-and-place cycle, written the way a cell program is written: in
Cartesian terms, with the approach and retract moves declared as straight
lines and the long transfer left as a joint move. Nothing here hard-codes
a joint angle except the home pose.

Two move types, both of which a real controller has:

* ``PTP`` -- interpolate the six joints. Fast, and the tool sweeps an arc.
* ``LIN`` -- interpolate the *tool pose*, and solve the joints every frame
  so the tool runs dead straight. This is what you want going into and
  out of a grasp, and it is the move that exercises the IK once per frame
  rather than once per waypoint.

Both are blended with a quintic ease, so every move starts and ends at
zero velocity and zero acceleration.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from robot_arm.params import ArmParams

from . import kinematics as K

# The parked pose: folded, clear of the floor, and checked for
# self-interference by the repo's own `verify.check_interference`. A
# robot that parks bolt upright is a robot you have to frame the shot
# around; this one tucks.
PARK = np.array([90.0, -35.0, 125.0, 0.0, -15.0, 0.0])

# ---- the cell -------------------------------------------------------
PICK_AZ, PLACE_AZ = -55.0, 55.0      # degrees about the turret axis
REACH = 440.0                        # mm from the turret axis
PEDESTAL_H = 120.0
BLOCK = 32.0                         # cube edge; the jaws close on this
CLEAR = 125.0                        # approach/retract height above the grip


def _at(az_deg: float, r: float, z: float) -> np.ndarray:
    a = np.radians(az_deg)
    return np.array([r * np.cos(a), r * np.sin(a), z])


PICK = _at(PICK_AZ, REACH, PEDESTAL_H + BLOCK / 2)
PLACE = _at(PLACE_AZ, REACH, PEDESTAL_H + BLOCK / 2)
PICK_OVER = PICK + (0, 0, CLEAR)
PLACE_OVER = PLACE + (0, 0, CLEAR)


@dataclass
class Move:
    name: str
    kind: str                    # "ptp" | "lin" | "hold"
    seconds: float
    goal: object = None          # joints (ptp) or 4x4 tool pose (lin)
    gap: float | None = None     # jaw opening to arrive at, mm
    grip: bool | None = None     # take / release the payload at the end


@dataclass
class State:
    t: float
    joints: np.ndarray
    gap: float
    holding: bool
    phase: str
    tcp: np.ndarray              # 4x4


def cycle(open_gap: float = BLOCK + 22.0, closed_gap: float = BLOCK) -> list[Move]:
    return [
        Move("PARK",      "hold", 0.55, PARK,                 open_gap),
        Move("APPROACH",  "ptp",  2.10, K.target_frame(PICK_OVER),  open_gap),
        Move("DESCEND",   "lin",  1.15, K.target_frame(PICK),       open_gap),
        Move("GRIP",      "hold", 0.75, None,             closed_gap, grip=True),
        Move("LIFT",      "lin",  1.15, K.target_frame(PICK_OVER),  closed_gap),
        Move("TRANSFER",  "ptp",  2.30, K.target_frame(PLACE_OVER), closed_gap),
        Move("PLACE",     "lin",  1.20, K.target_frame(PLACE),      closed_gap),
        Move("RELEASE",   "hold", 0.75, None,               open_gap, grip=False),
        Move("RETRACT",   "lin",  1.10, K.target_frame(PLACE_OVER), open_gap),
        Move("RETURN",    "ptp",  2.20, PARK,                       open_gap),
        Move("IDLE",      "hold", 0.55, None,                       open_gap),
    ]


def expand(p: ArmParams, moves: list[Move], fps: int = 30,
           report=print) -> tuple[list[State], dict]:
    """Solve the program into one State per frame.

    Also returns the diagnostics the checks in `test_simulate.py` run on:
    the IK residual at every solve, and the straightness of every LIN
    move. A frame is only worth rendering if the pose it holds is the
    pose that was asked for.
    """
    states: list[State] = []
    diag = {"ik_pos_err": [], "ik_ang_err": [], "lin_dev": []}
    q = PARK.copy()
    gap = moves[0].gap or 46.0
    holding = False
    t = 0.0
    dt = 1.0 / fps

    for mv in moves:
        n = max(1, int(round(mv.seconds * fps)))
        q0, gap0 = q.copy(), gap

        if mv.kind == "ptp" and mv.goal is not None:
            goal = mv.goal
            if isinstance(goal, np.ndarray) and goal.shape == (4, 4):
                qt, pe, ae = K.solve_ik(p, goal, K.seed_for(goal[:3, 3], p))
                diag["ik_pos_err"].append(pe)
                diag["ik_ang_err"].append(ae)
            else:
                qt = np.asarray(goal, float)
            report(f"  {mv.name:<9} PTP  -> J {np.round(qt, 1)}")
        elif mv.kind == "lin":
            start = K.tcp(p, q)
            goal = mv.goal
            report(f"  {mv.name:<9} LIN  -> {np.round(goal[:3, 3], 1)}")

        for i in range(1, n + 1):
            s = i / n
            if mv.kind == "ptp" and mv.goal is not None:
                q = K.blend(q0, qt, s)
            elif mv.kind == "lin":
                tgt = goal.copy()
                tgt[:3, 3] = K.blend(start[:3, 3], goal[:3, 3], s)
                q, pe, ae = K.solve_ik(p, tgt, q)
                diag["ik_pos_err"].append(pe)
                diag["ik_ang_err"].append(ae)
                got = K.tcp(p, q)[:3, 3]
                line = _dist_to_segment(got, start[:3, 3], goal[:3, 3])
                diag["lin_dev"].append(line)
            if mv.gap is not None:
                gap = float(K.blend([gap0], [mv.gap], s)[0])
            t += dt
            if mv.grip is not None and i == n:
                holding = mv.grip
            states.append(State(t, q.copy(), gap, holding, mv.name,
                                K.tcp(p, q)))
    return states, diag


def _dist_to_segment(pt, a, b) -> float:
    ab = b - a
    denom = float(ab @ ab)
    if denom < 1e-12:
        return float(np.linalg.norm(pt - a))
    u = np.clip(((pt - a) @ ab) / denom, 0.0, 1.0)
    return float(np.linalg.norm(pt - (a + u * ab)))
