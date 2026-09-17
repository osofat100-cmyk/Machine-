"""The main assembly: 12 parts, 16 instances, one kinematic chain.

The chain is built as a running product of `Location`s, one per joint.
`Pos(...) * Rot(...)` rotates about the *translated* origin, so each
joint frame is expressed relative to the previous one exactly as a
Denavit-Hartenberg chain would be.

Driving the pose is therefore a matter of changing `ArmParams.joints` --
no geometry is rebuilt, only re-placed. That is the property the video
is demonstrating when the arm sweeps: the mates, not the solids, are
what the angles touch.
"""

from __future__ import annotations

from dataclasses import dataclass

from build123d import Color, Compound, Location, Part, Pos, Rot

from . import parts as P
from .params import ArmParams

# Elbow-yoke stand-off: the pin sits this far above the yoke root face.
_ELBOW_H = lambda p: p.elbow_width * 0.62  # noqa: E731


@dataclass(frozen=True)
class Frames:
    """World-space frame of every joint, in chain order."""
    base: Location
    j1: Location
    j2: Location
    j3: Location
    j4: Location
    j5: Location
    j6: Location
    tool: Location


def joint_frames(p: ArmParams) -> Frames:
    """Forward kinematics. Pure transforms -- no geometry involved."""
    j1, j2, j3, j4, j5, j6 = p.joints

    base = Location()
    # J1: yaw about the vertical, at the top of the base flange.
    f1 = base * Pos(0, 0, p.base_thk) * Rot(0, 0, j1)
    # J2: shoulder pitch about X, at the top of the shoulder yoke's ears.
    f2 = f1 * Pos(0, 0, p.turret_h + p.yoke_h) * Rot(j2, 0, 0)
    # J3: elbow pitch about X, at the far end of the upper arm.
    f3 = f2 * Pos(0, 0, p.upper_len) * Rot(j3, 0, 0)
    # J4: forearm roll about the link axis.
    f4 = f3 * Pos(0, 0, _ELBOW_H(p) + p.fore_len) * Rot(0, 0, j4)
    # J5: wrist pitch about X, at the top of the wrist yoke's ears.
    f5 = f4 * Pos(0, 0, p.wrist_len + p.wyoke_h) * Rot(j5, 0, 0)
    # J6: tool roll about the flange axis.
    f6 = f5 * Rot(0, 0, j6)
    # The tool mounting face itself.
    tool = f6 * Pos(0, 0, p.flange_face_z)
    return Frames(base, f1, f2, f3, f4, f5, f6, tool)


_COLORS = {
    "01_base_flange": "#4a5568",
    "02_turret": "#2d3748",
    "03_shoulder_yoke": "#4a5568",
    "04_upper_arm": "#e2a03f",
    "05_elbow_yoke": "#4a5568",
    "06_forearm": "#e2a03f",
    "07_wrist_housing": "#2d3748",
    "08_wrist_yoke": "#4a5568",
    "09_tool_flange": "#718096",
    "10_grabber_jaw": "#a0aec0",
    "11_actuator_can": "#1a202c",
    "12_grabber_housing": "#2d3748",
    "13_grabber_head": "#39414f",
}


def _instance(proto: Part, label: str, loc: Location) -> Part:
    """Place a copy of a prototype part without disturbing the original."""
    inst = proto.moved(loc)
    inst.label = label
    base = label.split(".")[0]
    if base in _COLORS:
        inst.color = Color(_COLORS[base])
    return inst


def build_assembly(p: ArmParams | None = None) -> Compound:
    """Build the whole arm at the pose in `p.joints`."""
    p = p or ArmParams()
    lib = P.build_all(p)
    f = joint_frames(p)
    eh = _ELBOW_H(p)

    items: list[Part] = []
    add = lambda k, lbl, loc: items.append(_instance(lib[k], lbl, loc))  # noqa: E731

    # --- column ---------------------------------------------------
    add("01_base_flange", "01_base_flange", f.base)
    add("02_turret", "02_turret", f.j1)
    add("03_shoulder_yoke", "03_shoulder_yoke", f.j1 * Pos(0, 0, p.turret_h))

    # --- upper arm: J2 bore at the frame origin, extends along +Z ----
    add("04_upper_arm", "04_upper_arm", f.j2)

    # --- elbow: yoke pin coincident with J3, root facing the forearm --
    # Flipped 180 degrees about X so its +Z (root -> pin) points back at J3.
    add("05_elbow_yoke", "05_elbow_yoke", f.j3 * Pos(0, 0, eh) * Rot(180, 0, 0))
    add("06_forearm", "06_forearm", f.j3 * Pos(0, 0, eh))

    # --- wrist ------------------------------------------------------
    add("07_wrist_housing", "07_wrist_housing", f.j4)
    add("08_wrist_yoke", "08_wrist_yoke", f.j4 * Pos(0, 0, p.wrist_len))

    # --- tool -------------------------------------------------------
    add("09_tool_flange", "09_tool_flange", f.j6)
    # The tool is a reacher grabber's claw: the housing that replaces
    # its pistol grip, the head bolted straight onto it, and
    # `grab_jaws` jaws swinging in that.
    add("12_grabber_housing", "12_grabber_housing",
        f.j6 * Pos(0, 0, p.flange_face_z))
    add("13_grabber_head", "13_grabber_head",
        f.j6 * Pos(0, 0, p.grab_head_z))
    for i in range(p.grab_jaws):
        # Each jaw is authored at its own pivot, pointing along +Z with
        # +X outboard. Placing it is: spin to its station round the
        # axis, out to the pivot radius, then rotate by the opening --
        # which is why `grab_open` is a pose and not a shape. Nothing
        # is rebuilt when it changes, exactly as with a joint angle.
        add(
            "10_grabber_jaw",
            f"10_grabber_jaw.{i + 1}",
            f.j6
            * Rot(0, 0, 360.0 * i / p.grab_jaws)
            * Pos(p.grab_pivot_r, 0, p.grab_pivot_z)
            * Rot(0, p.grab_open, 0),
        )

    # --- actuators: one part, four placements ------------------------
    act_drops = {
        "J1": f.j1 * Pos(0, 0, -p.act_len + p.wall),
        "J2": f.j2 * Pos(p.yoke_width / 2 + p.act_len, 0, 0) * Rot(0, -90, 0),
        "J3": f.j3 * Pos(p.elbow_width / 2 + p.act_len, 0, 0) * Rot(0, -90, 0),
        "J5": f.j5 * Pos(p.wyoke_width / 2 + p.act_len, 0, 0) * Rot(0, -90, 0),
    }
    for i, (joint, loc) in enumerate(act_drops.items(), start=1):
        add("11_actuator_can", f"11_actuator_can.{joint}", loc)

    asm = Compound(children=items)
    asm.label = "Robotic_Arm_Main_Assembly"
    return asm


def instance_count(p: ArmParams | None = None) -> tuple[int, int]:
    """(distinct parts, placed instances) in the assembly."""
    asm = build_assembly(p)
    labels = [c.label for c in asm.children]
    distinct = {lbl.split(".")[0] for lbl in labels}
    return len(distinct), len(labels)
