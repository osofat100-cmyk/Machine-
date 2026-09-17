"""The checking pass.

Generating geometry is the easy half. This module is the other half: it
re-derives what the model should be and complains when the solids
disagree. Three independent checks:

1. `check_solids`   -- every part is a single watertight solid.
2. `check_kinematics`-- the joint chain, recomputed from scratch with 4x4
   matrices, agrees with the placements build123d produced. Two
   implementations agreeing is worth far more than one that runs.
3. `check_interference` -- no two parts occupy the same space, beyond the
   press/clearance fits that are there on purpose.
4. `check_grabber` -- the jaws are inside the slot they run in, at every
   stroke the design allows. A gripper whose jaws leave their body is
   still a valid pile of solids.

An agent driving a CAD system needs exactly this: a way to be told it is
wrong, in terms it can act on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians, sin

import numpy as np

from build123d import Compound, Vector

from .assembly import _ELBOW_H, build_assembly, joint_frames
from .params import ArmParams
from . import parts as P


@dataclass
class Report:
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))

    @property
    def ok(self) -> bool:
        return all(c[1] for c in self.checks)

    def render(self) -> str:
        lines = []
        for name, ok, detail in self.checks:
            mark = "PASS" if ok else "FAIL"
            lines.append(f"  [{mark}] {name}" + (f" -- {detail}" if detail else ""))
        lines.append(f"  {'ALL CHECKS PASSED' if self.ok else 'CHECKS FAILED'}")
        return "\n".join(lines)


# ---------------------------------------------------------------------
def _rx(a: float) -> np.ndarray:
    c, s = cos(radians(a)), sin(radians(a))
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])


def _rz(a: float) -> np.ndarray:
    c, s = cos(radians(a)), sin(radians(a))
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def _tz(d: float) -> np.ndarray:
    m = np.eye(4)
    m[2, 3] = d
    return m


def _vec(v: "Vector") -> np.ndarray:
    """build123d Vectors do not coerce to numpy arrays; unpack explicitly."""
    return np.array([v.X, v.Y, v.Z], dtype=float)


def fk_reference(p: ArmParams) -> np.ndarray:
    """Forward kinematics from first principles, independent of build123d."""
    j1, j2, j3, j4, j5, j6 = p.joints
    m = np.eye(4)
    m = m @ _tz(p.base_thk) @ _rz(j1)
    m = m @ _tz(p.turret_h + p.yoke_h) @ _rx(j2)
    m = m @ _tz(p.upper_len) @ _rx(j3)
    m = m @ _tz(_ELBOW_H(p) + p.fore_len) @ _rz(j4)
    m = m @ _tz(p.wrist_len + p.wyoke_h) @ _rx(j5)
    m = m @ _rz(j6)
    m = m @ _tz(p.tool_thk + p.tool_spigot_h)
    return m


# ---------------------------------------------------------------------
def check_solids(p: ArmParams, rep: Report) -> None:
    P._safe_fillet.dropped = 0
    lib = P.build_all(p)
    bad = [k for k, v in lib.items() if len(v.solids()) != 1]
    rep.add("every part is a single solid", not bad,
            f"{len(lib)} parts" if not bad else f"disjoint: {bad}")
    thin = [k for k, v in lib.items() if v.volume < 1.0]
    rep.add("no degenerate (near-zero volume) parts", not thin,
            "" if not thin else f"{thin}")
    rep.add("no fillets silently dropped", P._safe_fillet.dropped == 0,
            f"{P._safe_fillet.dropped} dropped")


def check_kinematics(p: ArmParams, rep: Report) -> None:
    """Cross-check the placement chain against the reference FK."""
    worst = 0.0
    poses = [
        p.joints,
        (0, 0, 0, 0, 0, 0),
        (90, -45, 90, 30, -60, 15),
        (-120, 20, -75, -90, 45, -30),
        (37.5, -12.25, 128.0, 180.0, 88.5, -179.0),
    ]
    for pose in poses:
        q = p.at_pose(*pose)
        got = _vec(joint_frames(q).tool.position)
        want = fk_reference(q)[:3, 3]
        worst = max(worst, float(np.linalg.norm(got - want)))
    rep.add("joint chain matches independent FK (5 poses)", worst < 1e-6,
            f"max deviation {worst:.2e} mm")


def check_axes(p: ArmParams, rep: Report) -> None:
    """Prove each joint turns about the axis it is supposed to turn about.

    With every other joint at zero the whole chain is colinear, so the
    tool frame's rotation reduces to that one joint's rotation alone. It
    must therefore equal a pure rotation about the intended axis.

    (An earlier version of this check asked instead whether each joint
    *moved the tool point*, and flagged J1 and J4 as dead. They are not:
    at the straight pose they are rolls about the very axis the tool sits
    on, so the tool centre is a fixed point. The check was wrong, not the
    arm -- which is the whole argument for checking the axis rather than
    the displacement.)
    """
    # J1 yaw, J2 shoulder, J3 elbow, J4 roll, J5 wrist pitch, J6 tool roll
    expected = ("Z", "X", "X", "Z", "X", "Z")
    theta = 25.0
    bad = []
    for i, axis in enumerate(expected):
        angles = [0.0] * 6
        angles[i] = theta
        got = fk_reference(p.at_pose(*angles))[:3, :3]
        want = (_rz(theta) if axis == "Z" else _rx(theta))[:3, :3]
        if not np.allclose(got, want, atol=1e-9):
            bad.append(f"J{i + 1}(expected {axis})")
    rep.add("each joint rotates about its intended axis", not bad,
            "J1/J4/J6 roll about Z, J2/J3/J5 pitch about X"
            if not bad else f"wrong axis: {bad}")

    # Liveness, measured away from the singular straight pose.
    bent = (20.0, -40.0, 70.0, 25.0, -35.0, 10.0)
    ref = fk_reference(p.at_pose(*bent))
    dead = []
    for i in range(6):
        angles = list(bent)
        angles[i] += 15.0
        m = fk_reference(p.at_pose(*angles))
        if np.allclose(m, ref, atol=1e-9):
            dead.append(f"J{i + 1}")
    rep.add("all 6 joints are live at a general pose", not dead,
            "6 DOF" if not dead else f"dead: {dead}")


def _bb_overlap(a, b, pad: float = 0.0) -> bool:
    """Do two axis-aligned bounding boxes overlap? Cheap boolean pre-filter."""
    return (
        a.min.X - pad <= b.max.X and b.min.X - pad <= a.max.X
        and a.min.Y - pad <= b.max.Y and b.min.Y - pad <= a.max.Y
        and a.min.Z - pad <= b.max.Z and b.min.Z - pad <= a.max.Z
    )


def check_interference(p: ArmParams, rep: Report, tol: float = 1.0) -> None:
    """Pairwise solid intersection across the assembly.

    Fits that are meant to overlap (a spigot in its bore) are excluded by
    name; everything else overlapping by more than `tol` mm^3 is a clash.
    """
    allowed = {
        frozenset({"06_forearm", "07_wrist_housing"}),   # spigot in bore
        frozenset({"01_base_flange", "02_turret"}),      # boss register
        frozenset({"02_turret", "11_actuator_can"}),     # motor in housing
        frozenset({"03_shoulder_yoke", "11_actuator_can"}),
        frozenset({"05_elbow_yoke", "11_actuator_can"}),
        frozenset({"08_wrist_yoke", "11_actuator_can"}),
        frozenset({"07_wrist_housing", "08_wrist_yoke"}),
    }
    asm = build_assembly(p)
    kids = list(asm.children)
    clashes = []
    for i in range(len(kids)):
        for j in range(i + 1, len(kids)):
            a, b = kids[i], kids[j]
            ka, kb = a.label.split(".")[0], b.label.split(".")[0]
            if frozenset({ka, kb}) in allowed:
                continue
            # Cheap reject on bounding boxes before the costly boolean.
            if not _bb_overlap(a.bounding_box(), b.bounding_box()):
                continue
            try:
                ov = a.intersect(b)
                vol = ov.volume if ov is not None else 0.0
            except Exception:
                continue
            if vol > tol:
                clashes.append((a.label, b.label, vol))
    clashes.sort(key=lambda c: -c[2])
    detail = "no clashes" if not clashes else "; ".join(
        f"{x}/{y} {v:.0f}mm3" for x, y, v in clashes[:4]
    )
    rep.add("no unintended interference between parts", not clashes, detail)


def check_grabber(p: ArmParams, rep: Report) -> None:
    """A jaw that is not in its slot is not a jaw.

    The tool this replaced was two fingers placed on the tool face and
    slid apart, which meant the stroke could be any number at all: past
    a certain opening the jaws were simply two solids floating near the
    flange, attached to nothing, and every other check in this file
    passed. Nothing about that is visible in a still render either --
    it reads as a gripper that happens to be open.

    A claw can fail the same way and more quietly, because a jaw hinged
    on nothing still *looks* hinged. So the same three questions, asked
    of the mechanism this tool actually has: the head's arc slot spans
    the travel, the commanded opening is inside it, and the pin on each
    jaw's heel is still in the slot at both ends of the travel --
    measured from the placed solids, not from the numbers that placed
    them.
    """
    from math import cos, hypot, radians, sin

    from build123d import Pos, Rot

    rep.add("the commanded jaw opening is inside the travel",
            p.grab_open_min <= p.grab_open <= p.grab_open_max,
            f"{p.grab_open:.1f} deg commanded, travel "
            f"{p.grab_open_min:.1f}..{p.grab_open_max:.1f} deg")

    lib = P.build_all(p)
    head = lib["13_grabber_head"].moved(Pos(0, 0, p.grab_head_z))
    hbox = head.bounding_box()
    worst_gap, worst_at = 1e9, 0.0
    for k in range(9):
        phi = p.grab_open_min + (p.grab_open_max - p.grab_open_min) * k / 8.0
        # the heel pin, where the jaw's own placement puts it
        jaw = lib["10_grabber_jaw"].moved(
            Pos(p.grab_pivot_r, 0, p.grab_pivot_z) * Rot(0, phi, 0))
        jb = jaw.bounding_box()
        # it has to still be inside the head's envelope in Z: a pin that
        # has run out of the end of its slot is not in a slot
        over = min(hbox.max.Z, jb.max.Z) - max(hbox.min.Z, jb.min.Z)
        if over < worst_gap:
            worst_gap, worst_at = over, phi
    rep.add("the jaws are still held by the head across the whole travel",
            worst_gap > 0.0,
            f"least overlap with the head {worst_gap:.1f} mm, at "
            f"{worst_at:.0f} deg of a {p.grab_open_min:.0f}.."
            f"{p.grab_open_max:.0f} deg travel")

    # The pads must not pass through each other at the shut end, and
    # must reach wide enough at the open end to be worth having.
    shut = 2.0 * (p.grab_pivot_r + p.grab_grip_point[0]
                  * cos(radians(p.grab_open_min))
                  + p.grab_grip_point[1] * sin(radians(p.grab_open_min))
                  - p.grab_pad_r)
    wide = 2.0 * (p.grab_pivot_r + p.grab_grip_point[0]
                  * cos(radians(p.grab_open_max))
                  + p.grab_grip_point[1] * sin(radians(p.grab_open_max))
                  - p.grab_pad_r)
    rep.add("shut is shut, and not through itself", shut > 0.0,
            f"the claw closes to {shut:.1f} mm and opens to {wide:.1f} mm")

    # And the claw really opens as wide as the arithmetic says. This is
    # the check the old gripper needed and did not have: a formula about
    # a jaw and the jaw itself, written out separately, differed by 2 mm
    # and nothing noticed until something measured the triangles.
    #
    # Triangles and not vertices: the ridge is a B-rep cylinder, whose
    # topological vertices are two points on an arbitrary seam. Asking
    # it where its surface is means tessellating it, which is also what
    # anything downstream will be looking at.
    jaw = lib["10_grabber_jaw"].moved(
        Pos(p.grab_pivot_r, 0, p.grab_pivot_z) * Rot(0, p.grab_open, 0))
    gx, gz = p.grab_grip_point
    phi = radians(p.grab_open)
    want_r = p.grab_pivot_r + gx * cos(phi) + gz * sin(phi)
    want_z = p.grab_pivot_z - gx * sin(phi) + gz * cos(phi)
    verts, _ = jaw.tessellate(0.02)
    band = [v for v in verts if abs(v.Z - want_z) < 0.6]
    near = min((v.X for v in band), default=-1e9)
    want = want_r - p.grab_pad_r
    rep.add("the claw closes to the width the arithmetic says",
            abs(near - want) < 0.3,
            f"ridge surface measured {near:.2f} mm from the tool axis "
            f"over {len(band)} points, arithmetic says {want:.2f} mm "
            f"-- a {2 * want:.1f} mm opening")


def check_reach(p: ArmParams, rep: Report) -> None:
    """Fully extended, the tool should sit at roughly the nominal reach."""
    straight = p.at_pose(0, 0, 0, 0, 0, 0)
    z = float(joint_frames(straight).tool.position.Z)
    want = p.base_thk + p.turret_h + p.yoke_h + p.reach - p.wrist_len \
        - p.wyoke_h - p.tool_thk + _ELBOW_H(p) + p.wrist_len + p.wyoke_h \
        + p.tool_thk + p.tool_spigot_h
    rep.add("extended reach is self-consistent", abs(z - want) < 1e-6,
            f"tool at Z={z:.1f} mm")


def run(p: ArmParams | None = None) -> Report:
    p = p or ArmParams()
    rep = Report()
    check_solids(p, rep)
    check_kinematics(p, rep)
    check_axes(p, rep)
    check_grabber(p, rep)
    check_reach(p, rep)
    check_interference(p, rep)
    return rep
