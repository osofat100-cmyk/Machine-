"""A fake `adsk` module, so the Fusion script can be run off Fusion.

This is not an emulator and makes no attempt to be one -- it computes no
geometry. It implements the shape of the API surface the script touches
and records every call, which is enough to catch the things that
actually go wrong when you cannot test: misspelled members, wrong
argument counts, a profile indexed before it exists, a joint asked for
between components that were never created, a loop that silently builds
nothing.

What it cannot tell you is whether Autodesk's real API behaves the way
this mock assumes. That is the honest limit, and it is why the README
says to run the script in Fusion before believing it.
"""

import sys
import types


class Recorder(object):
    """Collects everything the script did, for tests to assert against."""

    def __init__(self):
        self.calls = []
        self.components = []
        self.occurrences = []
        self.parameters = []
        self.features = []
        self.joints = []
        self.sketches = []

    def note(self, what, **kw):
        self.calls.append((what, kw))


REC = Recorder()


# ---------------------------------------------------------------------
# adsk.core
# ---------------------------------------------------------------------
class Point3D(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    @staticmethod
    def create(x, y, z):
        return Point3D(x, y, z)


class Vector3D(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    @staticmethod
    def create(x, y, z):
        return Vector3D(x, y, z)


class Matrix3D(object):
    def __init__(self):
        self.translation = Vector3D(0, 0, 0)
        self.rotation = None

    @staticmethod
    def create():
        return Matrix3D()

    def setToRotation(self, angle, axis, origin):
        self.rotation = (angle, (axis.x, axis.y, axis.z))
        return True

    def transformBy(self, other):
        if other.rotation is not None:
            self.rotation = other.rotation
        return True


class ValueInput(object):
    def __init__(self, value, kind):
        self.value, self.kind = value, kind

    @staticmethod
    def createByReal(v):
        if not isinstance(v, (int, float)):
            raise TypeError("createByReal needs a number, got %r" % type(v))
        return ValueInput(v, "real")

    @staticmethod
    def createByString(s):
        if not isinstance(s, str):
            raise TypeError("createByString needs a string, got %r" % type(s))
        return ValueInput(s, "string")


class _UI(object):
    def __init__(self):
        self.messages = []

    def messageBox(self, text, *a):
        self.messages.append(text)
        return 0


class Application(object):
    _instance = None

    def __init__(self):
        self.userInterface = _UI()
        self.activeProduct = None

    @staticmethod
    def get():
        if Application._instance is None:
            Application._instance = Application()
        return Application._instance


# ---------------------------------------------------------------------
# adsk.fusion -- collections
# ---------------------------------------------------------------------
class _Collection(object):
    def __init__(self, items=None):
        self._items = list(items or [])

    @property
    def count(self):
        return len(self._items)

    def item(self, i):
        # Deliberately strict: indexing a profile that does not exist is
        # exactly the bug this mock is here to catch.
        if i >= len(self._items):
            raise IndexError(
                "profile/item %d requested but only %d exist -- the sketch "
                "did not produce the closed region the script expected"
                % (i, len(self._items))
            )
        return self._items[i]

    def itemByName(self, name):
        for it in self._items:
            if getattr(it, "name", None) == name:
                return it
        return None

    def add(self, *a, **kw):
        obj = _Named("item%d" % len(self._items))
        self._items.append(obj)
        return obj


class _Named(object):
    def __init__(self, name=""):
        self.name = name

    def createForAssemblyContext(self, occurrence):
        """Real Fusion returns a proxy bound to one placement.

        Modelled because the joint code must use it: a bare component
        origin point refers to the component definition, not to a
        particular occurrence of it.
        """
        proxy = _Named(self.name + "@proxy")
        proxy.context = occurrence
        REC.note("createForAssemblyContext", of=self.name)
        return proxy


class _Profile(_Named):
    pass


class _SketchCircles(object):
    def __init__(self, sketch):
        self.sketch = sketch

    def addByCenterRadius(self, center, radius):
        if radius <= 0:
            raise ValueError("circle radius must be positive, got %r" % radius)
        self.sketch._add_profile("circle r=%.4f" % radius)
        REC.note("circle", r=radius, at=(center.x, center.y))
        return _Named("circle")


class _SketchLines(object):
    def __init__(self, sketch):
        self.sketch = sketch

    def addByTwoPoints(self, p1, p2):
        REC.note("line", a=(p1.x, p1.y), b=(p2.x, p2.y))
        self.sketch._line_count += 1
        # A closed loop of >=3 lines yields one profile.
        if self.sketch._line_count >= 3:
            self.sketch._ensure_profile("closed loop")
        return _Named("line")

    def addTwoPointRectangle(self, p1, p2):
        if abs(p1.x - p2.x) < 1e-12 or abs(p1.y - p2.y) < 1e-12:
            raise ValueError(
                "degenerate rectangle: corners (%.4f,%.4f) (%.4f,%.4f)"
                % (p1.x, p1.y, p2.x, p2.y)
            )
        self.sketch._add_profile("rect")
        REC.note("rect", a=(p1.x, p1.y), b=(p2.x, p2.y))
        return _Collection([_Named("line")] * 4)


class _SketchCurves(object):
    def __init__(self, sketch):
        self.sketchCircles = _SketchCircles(sketch)
        self.sketchLines = _SketchLines(sketch)


class _Sketch(object):
    def __init__(self, plane, component):
        self.plane = plane
        self.component = component
        self.sketchCurves = _SketchCurves(self)
        self._profiles = []
        self._line_count = 0
        REC.sketches.append(self)

    def _add_profile(self, label):
        self._profiles.append(_Profile(label))

    def _ensure_profile(self, label):
        if not self._profiles:
            self._add_profile(label)

    @property
    def profiles(self):
        return _Collection(self._profiles)


class _Sketches(object):
    def __init__(self, component):
        self.component = component

    def add(self, plane):
        if plane is None:
            raise ValueError("cannot sketch on a null plane")
        return _Sketch(plane, self.component)


class _ConstructionPlaneInput(object):
    def __init__(self):
        self.base = None
        self.offset = None

    def setByOffset(self, plane, offset):
        self.base, self.offset = plane, offset
        return True


class _ConstructionPlanes(_Collection):
    def createInput(self):
        return _ConstructionPlaneInput()

    def add(self, inp):
        if inp.base is None:
            raise ValueError("construction plane input was never configured")
        p = _Named("offset_plane")
        self._items.append(p)
        return p


class _ExtrudeInput(object):
    def __init__(self, profile, operation):
        if profile is None:
            raise ValueError("extrude needs a profile")
        self.profile = profile
        self.operation = operation
        self.extent = None

    def setDistanceExtent(self, symmetric, distance):
        if not isinstance(distance, ValueInput):
            raise TypeError("setDistanceExtent needs a ValueInput")
        self.extent = ("distance", distance.value)
        return True

    def setSymmetricExtent(self, distance, isFullLength):
        self.extent = ("symmetric", distance.value)
        return True


class _ExtrudeFeatures(object):
    def __init__(self, component):
        self.component = component

    def createInput(self, profile, operation):
        return _ExtrudeInput(profile, operation)

    def add(self, inp):
        if inp.extent is None:
            raise ValueError("extrude added with no extent set")
        kind, value = inp.extent
        if abs(value) < 1e-12:
            raise ValueError("extrude of zero depth")
        f = _Named("extrude")
        f.operation = inp.operation
        f.depth = value
        REC.features.append(("extrude", self.component.name, inp.operation, value))
        return f


class _RevolveInput(object):
    def __init__(self, profile, axis, operation):
        if profile is None:
            raise ValueError("revolve needs a profile")
        if axis is None:
            raise ValueError("revolve needs an axis")
        self.profile, self.axis, self.operation = profile, axis, operation
        self.angle = None

    def setAngleExtent(self, symmetric, angle):
        self.angle = angle.value
        return True


class _RevolveFeatures(object):
    def __init__(self, component):
        self.component = component

    def createInput(self, profile, axis, operation):
        return _RevolveInput(profile, axis, operation)

    def add(self, inp):
        if inp.angle is None:
            raise ValueError("revolve added with no angle set")
        REC.features.append(("revolve", self.component.name, inp.operation, inp.angle))
        return _Named("revolve")


class _Features(object):
    def __init__(self, component):
        self.extrudeFeatures = _ExtrudeFeatures(component)
        self.revolveFeatures = _RevolveFeatures(component)


class _JointInput(object):
    def __init__(self, g1, g2):
        if g1 is None or g2 is None:
            raise ValueError("joint needs two geometries")
        self.g1, self.g2 = g1, g2
        self.motion = None

    def setAsRevoluteJointMotion(self, direction):
        self.motion = ("revolute", direction)
        return True


class _Joints(_Collection):
    def createInput(self, g1, g2):
        return _JointInput(g1, g2)

    def add(self, inp):
        if inp.motion is None:
            raise ValueError("joint added with no motion set")
        REC.joints.append(inp.motion)
        self._items.append(inp)
        return inp


class JointGeometry(object):
    @staticmethod
    def createByPoint(point):
        if point is None:
            raise ValueError("joint geometry needs a point entity")
        return _Named("jointgeo")


class _Lumps(object):
    """A body's connected regions. >1 means the body is in pieces."""

    def __init__(self, n):
        self.count = n


class _Body(object):
    def __init__(self, name, lumps=1):
        self.name = name
        self.lumps = _Lumps(lumps)


class _Component(object):
    def __init__(self, name=""):
        self.name = name
        self.sketches = _Sketches(self)
        self.features = _Features(self)
        self.constructionPlanes = _ConstructionPlanes()
        self.joints = _Joints()
        self.occurrences = None
        self.xYConstructionPlane = _Named("XY")
        self.xZConstructionPlane = _Named("XZ")
        self.yZConstructionPlane = _Named("YZ")
        self.zConstructionAxis = _Named("Zaxis")
        self.xConstructionAxis = _Named("Xaxis")
        self.originConstructionPoint = _Named("origin")
        # One body per component by default. Tests can push a split body
        # in here to exercise the lumps oracle.
        self.bRepBodies = _Collection([_Body("Body1")])
        REC.components.append(self)

    def split_a_body(self, lumps=2):
        """Make this component's body disconnected, for testing."""
        self.bRepBodies = _Collection([_Body("Body1", lumps=lumps)])


class _Occurrence(object):
    def __init__(self, component, transform):
        self.component = component
        self._transform = transform
        REC.occurrences.append(self)

    @property
    def transform(self):
        return self._transform

    @transform.setter
    def transform(self, m):
        if not isinstance(m, Matrix3D):
            raise TypeError("occurrence.transform needs a Matrix3D")
        self._transform = m


class _Occurrences(_Collection):
    def addNewComponent(self, transform):
        occ = _Occurrence(_Component(), transform)
        self._items.append(occ)
        return occ

    def addExistingComponent(self, component, transform):
        occ = _Occurrence(component, transform)
        self._items.append(occ)
        return occ


class _UserParameters(_Collection):
    def add(self, name, value, units, comment):
        if not isinstance(value, ValueInput):
            raise TypeError("user parameter needs a ValueInput")
        p = _Named(name)
        p.value, p.units, p.comment = value.value, units, comment
        self._items.append(p)
        REC.parameters.append((name, value.value, units))
        return p


class _UnitsManager(object):
    defaultLengthUnits = "mm"


class Design(object):
    def __init__(self):
        self.designType = None
        self.rootComponent = _Component("root")
        self.rootComponent.occurrences = _Occurrences()
        self.userParameters = _UserParameters()
        self.unitsManager = _UnitsManager()

    @staticmethod
    def cast(product):
        return product


class DesignTypes(object):
    DirectDesignType = 0
    ParametricDesignType = 1


class FeatureOperations(object):
    JoinFeatureOperation = 0
    CutFeatureOperation = 1
    IntersectFeatureOperation = 2
    NewBodyFeatureOperation = 3
    NewComponentFeatureOperation = 4


class JointDirections(object):
    XAxisJointDirection = 0
    YAxisJointDirection = 1
    ZAxisJointDirection = 2
    CustomJointDirection = 3


# ---------------------------------------------------------------------
# install as `adsk.core` / `adsk.fusion`
# ---------------------------------------------------------------------
def install():
    """Register the fake modules in sys.modules and reset the recorder."""
    global REC
    REC = Recorder()
    # Rebind the recorder the classes above close over.
    for mod in (sys.modules.get("fusion360.tests.mock_adsk"),
                sys.modules.get("mock_adsk"), sys.modules.get(__name__)):
        if mod is not None:
            mod.REC = REC

    core = types.ModuleType("adsk.core")
    for n in ("Point3D", "Vector3D", "Matrix3D", "ValueInput", "Application"):
        setattr(core, n, globals()[n])

    fusion = types.ModuleType("adsk.fusion")
    for n in ("Design", "DesignTypes", "FeatureOperations", "JointDirections",
              "JointGeometry"):
        setattr(fusion, n, globals()[n])

    adsk = types.ModuleType("adsk")
    adsk.core = core
    adsk.fusion = fusion

    sys.modules["adsk"] = adsk
    sys.modules["adsk.core"] = core
    sys.modules["adsk.fusion"] = fusion
    return REC


def new_design():
    d = Design()
    Application.get().activeProduct = d
    return d
