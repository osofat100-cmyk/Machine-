"""The eleven parts.

Each builder takes an `ArmParams` and returns a build123d `Part`.

Framing convention — every part is authored so that its *mounting face*
sits on the local XY plane at Z=0 and its primary axis runs along +Z.
`assembly.py` relies on this, so a part that breaks the convention will
place wrongly even though it is geometrically valid. This is the
code-CAD equivalent of choosing mate references consistently.
"""

from __future__ import annotations

from build123d import (
    Align, Axis, Box, Cone, Cylinder, GeomType, Part, Plane, Pos, Rot,
    chamfer, fillet,
)

from .params import ArmParams

# Parts are built bottom-up from Z=0 rather than centred, so that a
# mounting face lands on the origin plane.
_UP = (Align.CENTER, Align.CENTER, Align.MIN)


def _safe_fillet(part: Part, edges, radius: float) -> Part:
    """Apply a cosmetic fillet, tolerating a radius the geometry rejects.

    A parametric model is only useful if it survives being re-driven. A
    fillet that is legal at the default dimensions can become illegal
    when a length is halved, and OCCT raises rather than clamping. We
    degrade to the un-filleted solid instead of failing the build, and
    `verify.py` reports how many fillets were dropped.
    """
    try:
        edges = list(edges)
    except TypeError:
        return part
    if not edges or radius <= 0:
        return part
    try:
        return fillet(edges, radius)
    except Exception:
        _safe_fillet.dropped += 1
        return part


_safe_fillet.dropped = 0


def _bolt_ring(radius: float, hole_dia: float, count: int, depth: float,
               z: float = 0.0) -> Part:
    """A ring of `count` through-holes on a bolt circle, as a cutting tool."""
    tool = None
    from math import cos, radians, sin
    for i in range(count):
        a = radians(360.0 * i / count + 45.0)
        peg = Pos(radius * cos(a), radius * sin(a), z) * Cylinder(
            hole_dia / 2, depth, align=_UP
        )
        tool = peg if tool is None else tool + peg
    return tool


def _clevis(width: float, gap: float, height: float, pin_dia: float,
            root_thk: float, fillet_r: float) -> Part:
    """A U-shaped yoke: a root slab with two ears carrying a coaxial pin bore.

    The pin axis lies along X at height `height` above the root face.
    """
    ear_thk = (width - gap) / 2.0
    if ear_thk <= 0:
        raise ValueError("clevis gap must be narrower than its width")

    root = Box(width, width, root_thk, align=_UP)
    part = root
    for sign in (-1, 1):
        ear = Pos(sign * (gap + ear_thk) / 2, 0, 0) * Box(
            ear_thk, width, height, align=_UP
        )
        part = part + ear

    # Round the top of each ear, then bore the pin through both.
    part = _safe_fillet(
        part,
        part.edges().filter_by(Axis.Y).group_by(Axis.Z)[-1],
        min(fillet_r * 2, width / 6),
    )
    bore = Pos(0, 0, height) * Rot(0, 90, 0) * Cylinder(
        pin_dia / 2, width * 1.2
    )
    return part - bore


# --------------------------------------------------------------------
# 1 / 11
# --------------------------------------------------------------------
def base_flange(p: ArmParams) -> Part:
    """Bolted-down mounting flange. Mounting face is the underside, Z=0."""
    part = Cylinder(p.base_dia / 2, p.base_thk, align=_UP)
    part = part + Pos(0, 0, p.base_thk) * Cylinder(
        p.base_boss_dia / 2, p.base_boss_h, align=_UP
    )
    part = part - _bolt_ring(
        p.base_bolt_circle / 2, p.base_bolt_dia, p.base_bolt_count,
        p.base_thk * 3, z=-p.base_thk,
    )
    part = part - Pos(0, 0, -1) * Cylinder(
        p.turret_bore / 2, p.base_thk + p.base_boss_h + 2, align=_UP
    )
    part = _safe_fillet(
        part,
        part.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[0],
        p.fillet / 2,
    )
    part.label = "01_base_flange"
    return part


# --------------------------------------------------------------------
# 2 / 11
# --------------------------------------------------------------------
def turret(p: ArmParams) -> Part:
    """J1 rotating column. Sits on the base boss, carries the shoulder."""
    part = Cylinder(p.turret_dia / 2, p.turret_h, align=_UP)
    # Waist the column so it reads as a casting rather than a plain tube.
    waist = Pos(0, 0, p.turret_h * 0.35) * Cone(
        p.turret_dia / 2 + 1, p.turret_dia / 2 - 7, p.turret_h * 0.4,
        align=_UP,
    )
    part = part - (
        Pos(0, 0, p.turret_h * 0.35) * Cylinder(
            p.turret_dia, p.turret_h * 0.4, align=_UP
        ) - waist
    )
    part = part - Pos(0, 0, -1) * Cylinder(
        p.turret_bore / 2, p.turret_h + 2, align=_UP
    )
    # Counterbore for the J1 actuator can, entering from below.
    part = part - Pos(0, 0, -1) * Cylinder(
        p.act_boss_dia / 2 + p.clearance, p.wall + 1, align=_UP
    )
    part.label = "02_turret"
    return part


# --------------------------------------------------------------------
# 3 / 11
# --------------------------------------------------------------------
def shoulder_yoke(p: ArmParams) -> Part:
    """J2 clevis. Bolts to the turret; the upper arm swings in its gap."""
    part = _clevis(
        p.yoke_width, p.yoke_gap, p.yoke_h, p.yoke_pin_dia,
        root_thk=p.wall * 2, fillet_r=p.fillet,
    )
    part = part - _bolt_ring(
        p.turret_dia / 2 - p.wall * 1.6, p.base_bolt_dia * 0.7, 4,
        p.wall * 4, z=-1,
    )
    part.label = "03_shoulder_yoke"
    return part


# --------------------------------------------------------------------
# 4 / 11
# --------------------------------------------------------------------
def upper_arm(p: ArmParams) -> Part:
    """J2 -> J3 link, an I-section beam with a bearing boss at each end.

    Authored along +Z: the J2 bore is at Z=0, the J3 bore at Z=upper_len.
    """
    L, w, h = p.upper_len, p.upper_w, p.upper_h
    beam = Box(w, h, L, align=_UP)
    # Mill the I-section pockets out of both flanks.
    pocket_d = (w - p.upper_web) / 2
    for sign in (-1, 1):
        pocket = Pos(sign * (w / 2 - pocket_d / 2), 0, L / 2) * Box(
            pocket_d, h - p.wall * 2, L - w * 2.2
        )
        beam = beam - pocket

    # Break the four long outer corners while the beam is still a plain
    # prism. Two constraints, both learned from OCCT refusing the naive
    # version: fillet before the bosses land (they consume part of these
    # edges), and take only the outer corners -- the eight corners of the
    # I-section pockets sit too close to the 5 mm web to take this radius.
    corners = [
        e for e in beam.edges().filter_by(Axis.Z)
        if abs(abs(e.center().X) - w / 2) < 1e-6
        and abs(abs(e.center().Y) - h / 2) < 1e-6
    ]
    beam = _safe_fillet(beam, corners, p.fillet)

    # Bearing bosses, coaxial with each joint pin (pin axis along X).
    boss = Cylinder(h / 2, w, rotation=(0, 90, 0))
    beam = beam + boss + Pos(0, 0, L) * boss
    for z in (0.0, L):
        beam = beam - Pos(0, 0, z) * Rot(0, 90, 0) * Cylinder(
            p.yoke_pin_dia / 2, w * 2
        )
    beam.label = "04_upper_arm"
    return beam


# --------------------------------------------------------------------
# 5 / 11
# --------------------------------------------------------------------
def elbow_yoke(p: ArmParams) -> Part:
    """J3 clevis carrying the forearm."""
    part = _clevis(
        p.elbow_width, p.elbow_gap, p.elbow_width * 0.62, p.elbow_pin_dia,
        root_thk=p.wall * 1.6, fillet_r=p.fillet,
    )
    part = part - Pos(0, 0, -1) * Cylinder(
        p.fore_dia / 2 - p.wall, p.wall * 3, align=_UP
    )
    part.label = "05_elbow_yoke"
    return part


# --------------------------------------------------------------------
# 6 / 11
# --------------------------------------------------------------------
def forearm(p: ArmParams) -> Part:
    """J3 -> J5 link. Tapered tube, hollow for the J4 drive shaft."""
    d0 = p.fore_dia / 2
    d1 = p.fore_dia * p.fore_taper / 2
    part = Cone(d0, d1, p.fore_len, align=_UP)
    part = part - Pos(0, 0, -1) * Cone(
        d0 - p.wall, d1 - p.wall, p.fore_len + 2, align=_UP
    )
    # Flanged foot that bolts into the elbow yoke.
    part = part + Cylinder(d0 + p.wall, p.wall, align=_UP)
    part = part - _bolt_ring(d0, p.tool_bolt_dia, 4, p.wall * 3, z=-1)
    # Blend the flange rim only. Selecting a whole Z-group here would
    # also catch the bolt-hole mouths, which cannot take this radius.
    rim = [
        e for e in part.edges().filter_by(GeomType.CIRCLE)
        if abs(e.radius - (d0 + p.wall)) < 1e-6
    ]
    part = _safe_fillet(part, rim, p.fillet / 2)
    part.label = "06_forearm"
    return part


# --------------------------------------------------------------------
# 7 / 11
# --------------------------------------------------------------------
def wrist_housing(p: ArmParams) -> Part:
    """J4 roll bearing housing, spigotted into the forearm nose."""
    part = Cylinder(p.wrist_dia / 2, p.wrist_len, align=_UP)
    # Bore from the web upward, not straight through: the base web is what
    # ties the spigot to the housing. Boring through leaves the spigot
    # floating inside the bore as a second, disconnected solid.
    part = part - Pos(0, 0, p.wall) * Cylinder(
        p.wrist_dia / 2 - p.wall, p.wrist_len, align=_UP
    )
    # Spigot that registers in the forearm bore, hanging below the web.
    spig = Cylinder(
        p.fore_dia * p.fore_taper / 2 - p.wall - p.clearance, p.wall * 1.5,
        align=(Align.CENTER, Align.CENTER, Align.MAX),
    )
    part = part + spig
    # Cable pass-through, small enough to leave the web intact.
    part = part - Pos(0, 0, -p.wall * 2) * Cylinder(
        p.turret_bore / 4, p.wrist_len, align=_UP
    )
    part = _safe_fillet(
        part,
        part.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1],
        p.fillet / 2,
    )
    part.label = "07_wrist_housing"
    return part


# --------------------------------------------------------------------
# 8 / 11
# --------------------------------------------------------------------
def wrist_yoke(p: ArmParams) -> Part:
    """J5 pitch clevis, between the wrist housing and the tool flange."""
    part = _clevis(
        p.wyoke_width, p.wyoke_gap, p.wyoke_h, p.wyoke_pin_dia,
        root_thk=p.wall, fillet_r=p.fillet / 2,
    )
    part.label = "08_wrist_yoke"
    return part


# --------------------------------------------------------------------
# 9 / 11
# --------------------------------------------------------------------
def tool_flange(p: ArmParams) -> Part:
    """ISO 9409-1 style tool plate: spigot, bolt ring, central bore."""
    part = Cylinder(p.tool_dia / 2, p.tool_thk, align=_UP)
    part = part + Pos(0, 0, p.tool_thk) * Cylinder(
        p.tool_spigot_dia / 2, p.tool_spigot_h, align=_UP
    )
    part = part - _bolt_ring(
        p.tool_bolt_circle / 2, p.tool_bolt_dia, p.tool_bolt_count,
        p.tool_thk * 4, z=-1,
    )
    part = part - Pos(0, 0, -1) * Cylinder(
        p.tool_bolt_dia * 1.6, p.tool_thk + p.tool_spigot_h + 2, align=_UP
    )
    part = _safe_fillet(
        part,
        part.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1],
        1.0,
    )
    part.label = "09_tool_flange"
    return part


# --------------------------------------------------------------------
# 10 / 11  (instanced twice in the assembly)
# --------------------------------------------------------------------
def gripper_finger(p: ArmParams) -> Part:
    """One jaw of a two-finger parallel gripper.

    Authored as an L: a shank up +Z, then a tip folding in toward -X.
    """
    shank = Box(p.finger_thk, p.finger_w, p.finger_len, align=_UP)
    tip = Pos(-p.finger_w / 2 + p.finger_thk / 2, 0, p.finger_len) * Box(
        p.finger_w, p.finger_w, p.finger_thk, align=_UP
    )
    part = shank + tip
    part = _safe_fillet(part, part.edges().filter_by(Axis.Y), p.finger_thk / 3)
    # Serrations on the gripping face.
    for i in range(3):
        z = p.finger_len + p.finger_thk / 2
        notch = Pos(-p.finger_w / 2 + p.finger_thk / 2 - 2 + i * 3.0, 0, z) * Rot(
            0, 45, 0
        ) * Box(1.2, p.finger_w + 2, 1.2)
        part = part - notch
    part = part - Pos(0, 0, p.finger_len * 0.25) * Rot(0, 90, 0) * Cylinder(
        p.tool_bolt_dia / 2, p.finger_thk * 3
    )
    part.label = "10_gripper_finger"
    return part


# --------------------------------------------------------------------
# 11 / 11  (instanced at J1, J2, J3, J5)
# --------------------------------------------------------------------
def actuator_can(p: ArmParams) -> Part:
    """Servo-gearbox body. One part, reused at four joints."""
    part = Cylinder(p.act_dia / 2, p.act_len, align=_UP)
    part = part + Pos(0, 0, p.act_len) * Cylinder(
        p.act_boss_dia / 2, p.act_boss_h, align=_UP
    )
    # Cooling flutes.
    from math import cos, radians, sin
    for i in range(8):
        a = radians(360.0 * i / 8)
        r = p.act_dia / 2
        flute = Pos(r * cos(a), r * sin(a), p.act_len * 0.2) * Cylinder(
            2.2, p.act_len * 0.6, align=_UP
        )
        part = part - flute
    part = _safe_fillet(
        part,
        part.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1],
        1.5,
    )
    part.label = "11_actuator_can"
    return part


#: Build order, and the single source of truth for "how many parts".
BUILDERS = (
    base_flange,
    turret,
    shoulder_yoke,
    upper_arm,
    elbow_yoke,
    forearm,
    wrist_housing,
    wrist_yoke,
    tool_flange,
    gripper_finger,
    actuator_can,
)


def build_all(p: ArmParams) -> dict[str, Part]:
    """Build every part once, keyed by label."""
    out: dict[str, Part] = {}
    for fn in BUILDERS:
        part = fn(p)
        out[part.label] = part
    return out
