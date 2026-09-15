"""Every dimension of the arm, in one place.

This module is the parametric model. Nothing downstream hard-codes a
number: `parts.py` and `assembly.py` read only from an `ArmParams`
instance, so changing a field here regenerates all 11 parts and the
assembly consistently.

Units: millimetres and degrees throughout.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace


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
    tool_dia: float = 50.0
    tool_thk: float = 8.0
    tool_bolt_circle: float = 31.5
    tool_bolt_dia: float = 5.0        # tapped M6
    tool_bolt_count: int = 4
    tool_spigot_dia: float = 31.5
    tool_spigot_h: float = 6.0

    # ---- part 10: gripper finger ------------------------------------
    finger_len: float = 62.0
    finger_w: float = 14.0
    finger_thk: float = 8.0
    finger_stroke: float = 22.0       # half-opening at the mounted pose

    # ---- part 12: gripper body (the rail the jaws run on) -----------
    # Without this the jaws were placed straight onto the tool face and
    # simply translated apart, so at any real opening they hung in free
    # space attached to nothing, and `finger_stroke` had no limit at all
    # because there was no mechanism for it to be a limit of. The body
    # is that mechanism: a housing with a slot, and the jaws travel in
    # the slot.
    grip_body_h: float = 24.0
    grip_body_w: float = 28.0         # across the jaw axis
    grip_slot_depth: float = 13.0     # how far a jaw stays engaged
    grip_wall: float = 10.0           # material beyond the slot ends
    grip_stroke_max: float = 50.0     # the travel the slot actually allows

    # ---- part 11: actuator can (shared, instanced at 4 joints) ------
    act_dia: float = 58.0
    act_len: float = 52.0
    act_boss_dia: float = 26.0
    act_boss_h: float = 6.0

    # ---- pose: the six joint angles, degrees ------------------------
    joints: tuple[float, float, float, float, float, float] = (
        0.0, -35.0, 65.0, 0.0, -30.0, 0.0
    )

    # ---- derived ----------------------------------------------------
    @property
    def grip_slot_len(self) -> float:
        """Length of the slot the two jaws run in.

        Derived from the travel, not chosen next to it: the slot has to
        be exactly long enough for both jaws at full stroke, so that
        `grip_stroke_max` is a statement about the hardware rather than
        a number that happens to sit nearby.
        """
        return 2.0 * self.grip_stroke_max + self.finger_thk + 2.0

    @property
    def grip_body_len(self) -> float:
        return self.grip_slot_len + 2.0 * self.grip_wall

    @property
    def flange_face_z(self) -> float:
        """Tool mounting face, measured from the J6 frame."""
        return self.tool_thk + self.tool_spigot_h

    @property
    def finger_mount_z(self) -> float:
        """Where a jaw's own origin sits, measured from the J6 frame.

        The jaw rises into the slot rather than sitting on the face, so
        its first `grip_slot_depth` of shank is inside the body at every
        stroke. Everything downstream -- the tool centre point, the
        checks, the animation -- reads this rather than re-deriving it.
        """
        return self.flange_face_z + self.grip_body_h - self.grip_slot_depth

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
