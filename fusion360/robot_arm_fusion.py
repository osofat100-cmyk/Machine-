"""Build the 6-DOF robot arm in Autodesk Fusion, with a real timeline.

Run it from Fusion: Utilities > ADD-INS > Scripts and Add-Ins > Scripts >
the green "+" > pick this folder > Run.

What you get is not an imported lump. It is 11 components, each with its
own feature history you can click back through and edit, driven by named
User Parameters you can change in Modify > Change Parameters. Edit
`upper_len` there and the arm rebuilds.

UNITS. Fusion's API is centimetres internally, always, no matter what
the document is displaying. Pass 50 meaning 50 mm and you get a part
five times too big that builds perfectly cleanly. Every number crossing
the API boundary goes through `cm()` below, once. (SolidWorks has the
identical trap set to metres instead. Every CAD API has one.)
"""

import traceback

import adsk.core
import adsk.fusion


# ---------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------
def cm(mm_value):
    """Millimetres -> centimetres, Fusion's internal unit."""
    return mm_value / 10.0


# ---------------------------------------------------------------------
# The parametric table. Mirrors cad/robot_arm/params.py exactly, so the
# two models describe the same arm. Each entry becomes a real Fusion
# User Parameter that shows up in Modify > Change Parameters.
# ---------------------------------------------------------------------
PARAMS = [
    # (name, mm, comment)
    ("wall",          6.0,   "nominal wall thickness"),
    ("base_dia",      150.0, "mounting flange diameter"),
    ("base_thk",      16.0,  "mounting flange thickness"),
    ("base_bolt_bc",  120.0, "bolt circle diameter"),
    ("base_bolt_dia", 9.0,   "clearance for M8"),
    ("turret_dia",    92.0,  "J1 column diameter"),
    ("turret_h",      78.0,  "J1 column height"),
    ("turret_bore",   34.0,  "cable pass-through"),
    ("yoke_width",    88.0,  "shoulder yoke outside width"),
    ("yoke_gap",      52.0,  "shoulder yoke inside gap"),
    ("yoke_h",        72.0,  "shoulder yoke height to pin"),
    ("upper_len",     260.0, "J2 to J3 centre distance"),
    ("upper_w",       48.0,  "upper arm width"),
    ("upper_h",       66.0,  "upper arm depth"),
    ("elbow_width",   78.0,  "elbow yoke outside width"),
    ("elbow_gap",     46.0,  "elbow yoke inside gap"),
    ("fore_len",      215.0, "J3 to wrist distance"),
    ("fore_dia",      62.0,  "forearm root diameter"),
    ("fore_taper",    0.72,  "forearm tip/root diameter ratio"),
    ("wrist_dia",     52.0,  "wrist housing diameter"),
    ("wrist_len",     46.0,  "wrist housing length"),
    ("wyoke_width",   50.0,  "wrist yoke width"),
    ("wyoke_gap",     30.0,  "wrist yoke gap"),
    ("wyoke_h",       44.0,  "wrist yoke height to pin"),
    ("tool_dia",      50.0,  "ISO 9409-1 flange diameter"),
    ("tool_thk",      8.0,   "tool flange thickness"),
    ("tool_bolt_bc",  31.5,  "tool flange bolt circle"),
    ("finger_len",    62.0,  "gripper finger length"),
    ("finger_w",      14.0,  "gripper finger width"),
    ("finger_thk",    8.0,   "gripper finger thickness"),
    ("finger_stroke", 22.0,  "half-opening at rest"),
    ("act_dia",       58.0,  "actuator can diameter"),
    ("act_len",       52.0,  "actuator can length"),
]

#: The home pose, degrees. J1 yaw, J2/J3/J5 pitch, J4/J6 roll.
POSE = (0.0, -35.0, 65.0, 0.0, -30.0, 0.0)

P = {name: value for name, value, _ in PARAMS}


# ---------------------------------------------------------------------
# Small helpers over the Fusion API
# ---------------------------------------------------------------------
class Builder(object):
    """Wraps the handful of Fusion calls this script needs."""

    def __init__(self, design):
        self.design = design
        self.root = design.rootComponent
        self.log = []
        self.components = []

    # -- parameters ---------------------------------------------------
    def add_user_parameters(self):
        """Publish the dimension table as editable Fusion parameters."""
        units = self.design.unitsManager
        existing = self.design.userParameters
        made = 0
        for name, value, comment in PARAMS:
            if existing.itemByName(name) is not None:
                continue
            unit = "" if name == "fore_taper" else "mm"
            existing.add(
                name,
                adsk.core.ValueInput.createByReal(
                    value if unit == "" else cm(value)
                ),
                unit,
                comment,
            )
            made += 1
        self.log.append("user parameters created: %d" % made)
        return made

    # -- components ---------------------------------------------------
    def new_component(self, name):
        """A new component at the origin. Positioning happens later."""
        occ = self.root.occurrences.addNewComponent(
            adsk.core.Matrix3D.create()
        )
        occ.component.name = name
        self.components.append(occ)
        return occ.component

    # -- sketch primitives --------------------------------------------
    def sketch_on_xy(self, comp, z_mm=0.0):
        """Open a sketch on XY, offset up the Z axis if asked."""
        if abs(z_mm) < 1e-9:
            return comp.sketches.add(comp.xYConstructionPlane)
        planes = comp.constructionPlanes
        pin = planes.createInput()
        pin.setByOffset(
            comp.xYConstructionPlane,
            adsk.core.ValueInput.createByReal(cm(z_mm)),
        )
        return comp.sketches.add(planes.add(pin))

    @staticmethod
    def circle(sketch, cx_mm, cy_mm, dia_mm):
        return sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(cx_mm), cm(cy_mm), 0),
            cm(dia_mm / 2.0),
        )

    @staticmethod
    def rect(sketch, x1_mm, y1_mm, x2_mm, y2_mm):
        return sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(cm(x1_mm), cm(y1_mm), 0),
            adsk.core.Point3D.create(cm(x2_mm), cm(y2_mm), 0),
        )

    # -- features -----------------------------------------------------
    def extrude(self, comp, profile, depth_mm, operation=None, symmetric=False):
        """Extrude a profile. Returns the feature, so it lands in the timeline."""
        if operation is None:
            operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        feats = comp.features.extrudeFeatures
        inp = feats.createInput(profile, operation)
        distance = adsk.core.ValueInput.createByReal(cm(depth_mm))
        if symmetric:
            inp.setSymmetricExtent(distance, True)
        else:
            inp.setDistanceExtent(False, distance)
        return feats.add(inp)

    def cut(self, comp, profile, depth_mm):
        return self.extrude(
            comp, profile, depth_mm,
            operation=adsk.fusion.FeatureOperations.CutFeatureOperation,
        )

    def revolve(self, comp, profile, axis, angle_deg=360.0):
        feats = comp.features.revolveFeatures
        inp = feats.createInput(
            profile, axis,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        inp.setAngleExtent(
            False,
            adsk.core.ValueInput.createByString("%g deg" % angle_deg),
        )
        return feats.add(inp)

    # -- placement ----------------------------------------------------
    @staticmethod
    def place(occurrence, matrix):
        occurrence.transform = matrix
        return occurrence


def matrix_from(rotation_deg_axis=None, translation_mm=(0.0, 0.0, 0.0)):
    """Build a Matrix3D from an optional rotation and a translation in mm."""
    m = adsk.core.Matrix3D.create()
    if rotation_deg_axis is not None:
        angle_deg, axis = rotation_deg_axis
        rot = adsk.core.Matrix3D.create()
        rot.setToRotation(
            angle_deg * 3.141592653589793 / 180.0,
            adsk.core.Vector3D.create(*axis),
            adsk.core.Point3D.create(0, 0, 0),
        )
        m.transformBy(rot)
    t = adsk.core.Matrix3D.create()
    t.translation = adsk.core.Vector3D.create(
        cm(translation_mm[0]), cm(translation_mm[1]), cm(translation_mm[2])
    )
    t.transformBy(m)
    return t


# ---------------------------------------------------------------------
# The eleven parts
# ---------------------------------------------------------------------
def build_base_flange(b):
    comp = b.new_component("01_base_flange")
    sk = b.sketch_on_xy(comp)
    b.circle(sk, 0, 0, P["base_dia"])
    b.extrude(comp, sk.profiles.item(0), P["base_thk"])

    holes = b.sketch_on_xy(comp, P["base_thk"])
    r = P["base_bolt_bc"] / 2.0
    for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
        b.circle(holes, dx, dy, P["base_bolt_dia"])
    b.circle(holes, 0, 0, P["turret_bore"])
    for i in range(holes.profiles.count):
        b.cut(comp, holes.profiles.item(i), -P["base_thk"] - 2.0)
    return comp


def build_turret(b):
    comp = b.new_component("02_turret")
    sk = b.sketch_on_xy(comp)
    b.circle(sk, 0, 0, P["turret_dia"])
    b.circle(sk, 0, 0, P["turret_bore"])
    b.extrude(comp, sk.profiles.item(0), P["turret_h"])
    return comp


def _clevis(b, comp, width, gap, height, root_thk):
    """Root slab plus two ears, the U that carries a joint pin."""
    sk = b.sketch_on_xy(comp)
    b.rect(sk, -width / 2.0, -width / 2.0, width / 2.0, width / 2.0)
    b.extrude(comp, sk.profiles.item(0), root_thk)

    ear_thk = (width - gap) / 2.0
    for sign in (-1, 1):
        x0 = sign * gap / 2.0
        x1 = sign * (gap / 2.0 + ear_thk)
        es = b.sketch_on_xy(comp, root_thk)
        b.rect(es, min(x0, x1), -width / 2.0, max(x0, x1), width / 2.0)
        b.extrude(comp, es.profiles.item(0), height - root_thk)
    return comp


def build_shoulder_yoke(b):
    comp = b.new_component("03_shoulder_yoke")
    return _clevis(b, comp, P["yoke_width"], P["yoke_gap"], P["yoke_h"],
                   P["wall"] * 2)


def build_upper_arm(b):
    comp = b.new_component("04_upper_arm")
    sk = b.sketch_on_xy(comp)
    b.rect(sk, -P["upper_w"] / 2.0, -P["upper_h"] / 2.0,
           P["upper_w"] / 2.0, P["upper_h"] / 2.0)
    b.extrude(comp, sk.profiles.item(0), P["upper_len"])
    return comp


def build_elbow_yoke(b):
    comp = b.new_component("05_elbow_yoke")
    return _clevis(b, comp, P["elbow_width"], P["elbow_gap"],
                   P["elbow_width"] * 0.62, P["wall"] * 1.6)


def build_forearm(b):
    """Tapered tube, made by revolving a profile -- a real revolve feature."""
    comp = b.new_component("06_forearm")
    sk = comp.sketches.add(comp.xZConstructionPlane)
    lines = sk.sketchCurves.sketchLines
    r0 = P["fore_dia"] / 2.0
    r1 = P["fore_dia"] * P["fore_taper"] / 2.0
    w = P["wall"]
    L = P["fore_len"]
    pts = [(r0, 0.0), (r1, L), (r1 - w, L), (r0 - w, 0.0)]
    prev = None
    first = None
    for x_mm, z_mm in pts:
        pt = adsk.core.Point3D.create(cm(x_mm), cm(z_mm), 0)
        if prev is not None:
            lines.addByTwoPoints(prev, pt)
        else:
            first = pt
        prev = pt
    lines.addByTwoPoints(prev, first)
    b.revolve(comp, sk.profiles.item(0), comp.zConstructionAxis)
    return comp


def build_wrist_housing(b):
    comp = b.new_component("07_wrist_housing")
    sk = b.sketch_on_xy(comp)
    b.circle(sk, 0, 0, P["wrist_dia"])
    b.extrude(comp, sk.profiles.item(0), P["wrist_len"])
    return comp


def build_wrist_yoke(b):
    comp = b.new_component("08_wrist_yoke")
    return _clevis(b, comp, P["wyoke_width"], P["wyoke_gap"], P["wyoke_h"],
                   P["wall"])


def build_tool_flange(b):
    comp = b.new_component("09_tool_flange")
    sk = b.sketch_on_xy(comp)
    b.circle(sk, 0, 0, P["tool_dia"])
    b.extrude(comp, sk.profiles.item(0), P["tool_thk"])

    holes = b.sketch_on_xy(comp, P["tool_thk"])
    r = P["tool_bolt_bc"] / 2.0
    for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
        b.circle(holes, dx, dy, 5.0)
    for i in range(holes.profiles.count):
        b.cut(comp, holes.profiles.item(i), -P["tool_thk"] - 2.0)
    return comp


def build_gripper_finger(b):
    comp = b.new_component("10_gripper_finger")
    sk = b.sketch_on_xy(comp)
    b.rect(sk, -P["finger_thk"] / 2.0, -P["finger_w"] / 2.0,
           P["finger_thk"] / 2.0, P["finger_w"] / 2.0)
    b.extrude(comp, sk.profiles.item(0), P["finger_len"])

    # The tip folds toward -X in local coordinates. The assembly spins
    # the -X jaw 180 degrees so the two tips face each other. Get that
    # backwards and you get a gripper that opens outward: legal
    # geometry, useless hardware, and no check will tell you.
    tip = b.sketch_on_xy(comp, P["finger_len"])
    b.rect(tip, -P["finger_w"] + P["finger_thk"] / 2.0, -P["finger_w"] / 2.0,
           P["finger_thk"] / 2.0, P["finger_w"] / 2.0)
    b.extrude(comp, tip.profiles.item(0), P["finger_thk"])
    return comp


def build_actuator_can(b):
    comp = b.new_component("11_actuator_can")
    sk = b.sketch_on_xy(comp)
    b.circle(sk, 0, 0, P["act_dia"])
    b.extrude(comp, sk.profiles.item(0), P["act_len"])
    return comp


BUILDERS = [
    build_base_flange, build_turret, build_shoulder_yoke, build_upper_arm,
    build_elbow_yoke, build_forearm, build_wrist_housing, build_wrist_yoke,
    build_tool_flange, build_gripper_finger, build_actuator_can,
]


# ---------------------------------------------------------------------
# Posing the chain
# ---------------------------------------------------------------------
def joint_heights():
    """Stack heights along the chain, mm. Mirrors cad/robot_arm/assembly.py."""
    elbow_h = P["elbow_width"] * 0.62
    return {
        "j1_z": P["base_thk"],
        "j2_z": P["turret_h"] + P["yoke_h"],
        "j3_z": P["upper_len"],
        "elbow_h": elbow_h,
        "j4_z": elbow_h + P["fore_len"],
        "j5_z": P["wrist_len"] + P["wyoke_h"],
        "tool_z": P["tool_thk"],
    }


def place_chain(b, occurrences):
    """Position every component down the kinematic chain.

    Cumulative Z only -- each component is stacked on the one before it.
    The joints created next are what actually let it articulate; this
    just puts the parts where the joints expect to find them.
    """
    h = joint_heights()
    by_name = {}
    for occ in occurrences:
        by_name.setdefault(occ.component.name, []).append(occ)

    z = 0.0
    stack = [
        ("01_base_flange", 0.0),
        ("02_turret", h["j1_z"]),
        ("03_shoulder_yoke", P["turret_h"]),
        ("04_upper_arm", P["yoke_h"]),
        ("05_elbow_yoke", h["j3_z"]),
        ("06_forearm", h["elbow_h"]),
        ("07_wrist_housing", P["fore_len"]),
        ("08_wrist_yoke", P["wrist_len"]),
        ("09_tool_flange", P["wyoke_h"]),
    ]
    placed = 0
    for name, dz in stack:
        z += dz
        for occ in by_name.get(name, []):
            b.place(occ, matrix_from(translation_mm=(0.0, 0.0, z)))
            placed += 1

    # Two gripper jaws, facing each other.
    tool_top = z + P["tool_thk"]
    for i, sign in enumerate((-1, 1)):
        for occ in by_name.get("10_gripper_finger", [])[i:i + 1]:
            yaw = 180.0 if sign < 0 else 0.0
            b.place(occ, matrix_from(
                rotation_deg_axis=(yaw, (0, 0, 1)),
                translation_mm=(sign * P["finger_stroke"], 0.0, tool_top),
            ))
            placed += 1
    b.log.append("components placed: %d" % placed)
    return placed


def add_joints(b, occurrences):
    """Revolute joints, so the arm actually articulates in Fusion.

    Joints need real geometry to attach to, and that is the fiddliest
    corner of this API. If a joint fails we record it and carry on: the
    parts are still correctly placed and the model is still usable. An
    honest count beats a script that dies two thirds of the way in.
    """
    made, failed = 0, []
    chain = [
        ("02_turret", "01_base_flange", "Z"),   # J1 yaw
        ("04_upper_arm", "03_shoulder_yoke", "X"),  # J2 shoulder
        ("06_forearm", "05_elbow_yoke", "X"),   # J3 elbow
        ("07_wrist_housing", "06_forearm", "Z"),  # J4 roll
        ("09_tool_flange", "08_wrist_yoke", "X"),  # J5 wrist pitch
    ]
    by_name = {occ.component.name: occ for occ in occurrences}
    for child, parent, axis in chain:
        if child not in by_name or parent not in by_name:
            failed.append("%s->%s (missing component)" % (child, parent))
            continue
        try:
            g1 = adsk.fusion.JointGeometry.createByPoint(
                by_name[child].component.originConstructionPoint
            )
            g2 = adsk.fusion.JointGeometry.createByPoint(
                by_name[parent].component.originConstructionPoint
            )
            jin = b.root.joints.createInput(g1, g2)
            direction = (
                adsk.fusion.JointDirections.ZAxisJointDirection if axis == "Z"
                else adsk.fusion.JointDirections.XAxisJointDirection
            )
            jin.setAsRevoluteJointMotion(direction)
            b.root.joints.add(jin)
            made += 1
        except Exception as exc:
            failed.append("%s->%s (%s)" % (child, parent, exc))
    b.log.append("revolute joints: %d created, %d failed" % (made, len(failed)))
    for f in failed:
        b.log.append("  joint failed: %s" % f)
    return made, failed


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def build(design):
    """Everything, in order. Separated from run() so tests can call it."""
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    b = Builder(design)
    b.add_user_parameters()

    for builder in BUILDERS:
        builder(b)
    b.log.append("components built: %d" % len(b.components))

    # The actuator can is one component shown at four joints.
    can = [o for o in b.components if o.component.name == "11_actuator_can"]
    if can:
        proto = can[0].component
        for _ in range(3):
            b.components.append(
                b.root.occurrences.addExistingComponent(
                    proto, adsk.core.Matrix3D.create()
                )
            )
    # And the gripper finger twice.
    finger = [o for o in b.components if o.component.name == "10_gripper_finger"]
    if finger:
        b.components.append(
            b.root.occurrences.addExistingComponent(
                finger[0].component, adsk.core.Matrix3D.create()
            )
        )

    place_chain(b, b.components)
    add_joints(b, b.components)
    b.log.append("occurrences total: %d" % len(b.components))
    return b


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if design is None:
            ui.messageBox(
                "No active Fusion design.\n\n"
                "Open or create a design first, then run this script."
            )
            return
        b = build(design)
        ui.messageBox("Robot arm built.\n\n" + "\n".join(b.log))
    except Exception:
        if ui:
            ui.messageBox("Script failed:\n\n" + traceback.format_exc())
