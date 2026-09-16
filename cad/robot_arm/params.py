"""Every dimension of the arm, in one place.

This module is the parametric model. Nothing downstream hard-codes a
number: `parts.py` and `assembly.py` read only from an `ArmParams`
instance, so changing a field here regenerates all 11 parts and the
assembly consistently.

Units: millimetres and degrees throughout.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import cos, radians, sin


@dataclass(frozen=True)
class ArmParams:
    # ---- global -----------------------------------------------------
    wall: float = 6.0                 # nominal wall thickness
    clearance: float = 0.4            # running clearance between moving parts
    fillet: float = 3.0               # cosmetic fillet radius

    # ---- part 1: base flange ---------------------------------------
    base_dia: float = 150.0
    base_thk: float = 16.0
    base_bolt_circle: float = 120.0
    base_bolt_dia: float = 9.0        # clearance for M8
    base_bolt_count: int = 4
    base_boss_dia: float = 96.0
    base_boss_h: float = 10.0

    # ---- part 2: J1 turret -----------------------------------------
    turret_dia: float = 92.0
    turret_h: float = 78.0
    turret_bore: float = 34.0         # cable pass-through

    # ---- part 3: shoulder yoke (J2 clevis) --------------------------
    yoke_width: float = 88.0          # outside width across the clevis
    yoke_gap: float = 52.0            # inside gap the arm swings in
    yoke_h: float = 72.0
    yoke_pin_dia: float = 16.0

    # ---- part 4: upper arm (J2 -> J3) -------------------------------
    upper_len: float = 260.0
    upper_w: float = 48.0
    upper_h: float = 66.0
    upper_web: float = 5.0            # I-section web thickness

    # ---- part 5: elbow yoke (J3 clevis) -----------------------------
    elbow_gap: float = 46.0
    elbow_width: float = 78.0
    elbow_pin_dia: float = 14.0

    # ---- part 6: forearm (J3 -> J5, carries J4 roll) ----------------
    fore_len: float = 215.0
    fore_dia: float = 62.0
    fore_taper: float = 0.72          # end diameter as a fraction of fore_dia

    # ---- part 7: wrist housing (J4 roll bearing) --------------------
    wrist_dia: float = 52.0
    wrist_len: float = 46.0

    # ---- part 8: wrist yoke (J5 pitch clevis) -----------------------
    wyoke_gap: float = 30.0
    wyoke_width: float = 50.0
    wyoke_h: float = 44.0
    wyoke_pin_dia: float = 10.0

    # ---- part 9: tool flange (ISO 9409-1-50-4-M6) -------------------
    # The standard's numbers, and the designation is in the name: a
    # 50 mm plate on a 31.5 mm circle, four M6. A tool that cannot be
    # bolted to those is the tool's problem to solve, not the flange's.
    tool_dia: float = 50.0
    tool_thk: float = 8.0
    tool_bolt_circle: float = 31.5
    tool_bolt_dia: float = 5.0        # tapped M6
    tool_bolt_count: int = 4
    tool_spigot_dia: float = 31.5
    tool_spigot_h: float = 6.0

    # ---- the tool: a reacher grabber's claw (parts 10, 12, 13) ------
    # The working end of a reacher grabber, and only that: four jaws
    # that curl shut on whatever is between them, the head they pivot
    # in, and a housing that drives them. Squeeze the trigger on the
    # hand tool and a rod pulls the jaws closed; let go and a spring
    # opens them. Here the pistol grip becomes an actuator housing and
    # the trigger becomes a linear drive.
    #
    # The pole the tool is sold with is not modelled, because it is
    # there to save a person bending down. A robot arm is already the
    # reach; a pole bolted to J6 would be 160 mm of dead length for the
    # wrist to carry and swing, and every clearance in the cell would
    # be paying for it.
    #
    # `grab_open` is the pose, in the same sense `joints` is: how far
    # the jaws are swung open from shut. Nothing is rebuilt when it
    # changes, only re-placed -- the same as every joint angle.
    grab_open: float = 52.0           # degrees at the mounted pose

    # part 12: the housing that replaces the pistol grip
    grab_housing_dia: float = 62.0
    grab_housing_len: float = 46.0

    # The register between the two: a spigot on the housing, a
    # counterbore in the head, so the claw can only go on square and
    # the drive has somewhere to run. On the hand tool this is the
    # socket the pole clamps into.
    grab_spigot_dia: float = 24.0
    grab_spigot_h: float = 12.0

    # part 13: the head the jaws pivot in
    grab_head_dia: float = 64.0
    grab_head_len: float = 40.0
    grab_pivot_r: float = 22.0        # pivot pins, from the tool axis
    grab_pin_dia: float = 6.0
    grab_pin_inset: float = 11.0      # pin centre, back from the head's end
    grab_clevis_wall: float = 6.0     # material either side of a blade

    # part 10: one jaw, instanced `grab_jaws` times round the axis
    grab_jaws: int = 4
    grab_jaw_len: float = 92.0        # along the curl, from the pivot
    grab_jaw_w: float = 22.0
    grab_jaw_thk: float = 9.0
    grab_jaw_curl: float = 52.0       # degrees the finger curls inward
    grab_jaw_segs: int = 3            # straight segments approximating it
    grab_heel: float = 14.0           # heel behind the pivot, carrying
                                      # the pin that runs in the head
    grab_pad_len: float = 36.0
    grab_pad_thk: float = 5.0
    # A half-round ridge standing proud of the pad, and the reason the
    # jaw opening is a number at all. The pad is a flat on a finger that
    # is still curling, so it meets a box's flat side at an angle and
    # touches it on one edge -- and which edge, and how far in it is,
    # changes with the opening. A cylinder touches a plane on a line at
    # exactly its own radius, whatever angle it is presented at.
    grab_pad_r: float = 4.0

    # The travel. Shut is not zero degrees: the pads are 5 mm of rubber
    # on a 9 mm finger, and they meet before the fingers do.
    #
    # These two are the mechanism, not a note beside it. Each jaw
    # carries a pin on its heel that runs in an arc slot cut in the
    # head, and `parts.grabber_head` cuts that slot *from these two
    # numbers* -- so the slot is exactly the travel, the way
    # `grip_slot_len` was exactly the stroke on the gripper this
    # replaced. Widen the range and the slot widens with it; there is
    # no way to command an angle the head does not physically allow.
    grab_open_min: float = 17.0
    grab_open_max: float = 101.0
    grab_slot_w: float = 7.4          # the arc slot, across the arc

    # The opening the tool centre point is defined at. A claw's grip
    # point moves as it curls, so the TCP has to be pinned to one
    # stated opening and everything else measured against it.
    grab_ref_gap: float = 90.0

    # ---- part 11: actuator can (shared, instanced at 4 joints) ------
    act_dia: float = 58.0
    act_len: float = 52.0
    act_boss_dia: float = 26.0
    act_boss_h: float = 6.0

    # ---- ratings: what the hardware can do, not what shape it is ---
    # Not geometry, but no less a property of the machine than the
    # finger length -- and the only numbers that decide whether a box
    # that fits in the jaws can actually be carried by them.
    grip_force: float = 260.0         # N of clamping force at the jaws
    jaw_mu: float = 0.6               # friction pad against cardboard

    # ---- pose: the six joint angles, degrees ------------------------
    joints: tuple[float, float, float, float, float, float] = (
        0.0, -35.0, 65.0, 0.0, -30.0, 0.0
    )

    # ---- derived ----------------------------------------------------
    @property
    def flange_face_z(self) -> float:
        """Tool mounting face, measured from the J6 frame."""
        return self.tool_thk + self.tool_spigot_h

    @property
    def grab_head_z(self) -> float:
        """The claw head's base, measured from the J6 frame.

        The head sits straight on the housing. Nothing between them
        but the register spigot, which is buried in both.
        """
        return self.flange_face_z + self.grab_housing_len

    @property
    def grab_pivot_z(self) -> float:
        """The jaw pivot pins, measured from the J6 frame."""
        return self.grab_head_z + self.grab_head_len - self.grab_pin_inset

    @property
    def grab_curl(self) -> tuple:
        """The jaw's centreline, as a polyline in the jaw's own frame.

        One entry per segment: (angle, (mid_x, mid_z), (end_x, end_z)),
        starting at the pivot pointing along +Z and curling toward -X.

        Three straight segments and a fillet rather than a swept spline,
        because the polyline survives being re-driven and an OCCT sweep
        along a spline does not, reliably.

        `parts.grabber_jaw` builds from this and `kinematics` measures
        from it. That is the whole point of it being here: the old
        gripper wrote out the shape of the jaw tip in one place and the
        arithmetic about where it grips in another, and the two differed
        by 2 mm for as long as nobody measured the triangles.
        """
        step = self.grab_jaw_len / self.grab_jaw_segs
        out, x, z = [], 0.0, 0.0
        for i in range(self.grab_jaw_segs):
            a = radians(self.grab_jaw_curl * (i + 0.5) / self.grab_jaw_segs)
            dx, dz = -sin(a), cos(a)
            mid = (x + dx * step / 2.0, z + dz * step / 2.0)
            x, z = x + dx * step, z + dz * step
            out.append((a, mid, (x, z)))
        return tuple(out)

    @property
    def grab_grip_point(self) -> tuple[float, float]:
        """(x, z) of the grip ridge's *axis*, in the jaw's own frame.

        Half a pad back from the tip along the last segment, then
        `grab_jaw_thk / 2 + grab_pad_thk` inboard of the centreline --
        which is the pad's face, where the ridge sits. What touches a
        box is `grab_pad_r` further in, and always exactly that far in,
        which is the point of the ridge.
        """
        a, _, (ex, ez) = self.grab_curl[-1]
        back = self.grab_pad_len / 2.0
        cx, cz = ex + sin(a) * back, ez - cos(a) * back
        inw = self.grab_jaw_thk / 2.0 + self.grab_pad_thk
        return (cx - cos(a) * inw, cz - sin(a) * inw)

    @property
    def grab_heel_point(self) -> tuple[float, float]:
        """(x, z) of the heel pin, jaw frame: behind and outboard of the
        pivot, so that drawing the collar back curls the jaw shut."""
        return (self.grab_heel * 0.45, -self.grab_heel)

    @property
    def shoulder_z(self) -> float:
        """Height of the J2 axis above the mounting face."""
        return self.base_thk + self.turret_h + self.yoke_h

    @property
    def reach(self) -> float:
        """Nominal maximum reach from the J1 axis to the tool face."""
        return (
            self.upper_len
            + self.fore_len
            + self.wrist_len
            + self.wyoke_h
            + self.tool_thk
        )

    def at_pose(self, *angles: float) -> "ArmParams":
        """Return a copy of these params with a different joint pose."""
        if len(angles) != 6:
            raise ValueError(f"need 6 joint angles, got {len(angles)}")
        return replace(self, joints=tuple(float(a) for a in angles))


DEFAULT = ArmParams()
