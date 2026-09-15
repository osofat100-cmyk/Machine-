"""The sort cell: a moving belt, five arms beside it, and who owns what.

Five of the arm from `robot_arm/` stand along a conveyor, three on one
side and two on the other, staggered so that no two of them are ever
looking at the same stretch of belt. Boxes of three sizes arrive at
random across the belt width; each arm picks from its own territory and
sorts by size into its own three bins.

Territory is the whole design. It is the intersection of three things:

1. **A side.** An arm only takes boxes whose centre is on its half of the
   belt *width*. The two sides never share a box.
2. **A window.** An arm only takes boxes inside its own stretch of belt
   *length*. Windows on the same side are 900 mm apart and 380 mm wide,
   so they do not touch; windows on opposite sides are offset by 450 mm
   and separated in y as well.
3. **Reach.** Every corner of every window has to be somewhere the arm
   can actually put its tool, at both the pick height and the hover
   height. `measure_envelope` derives that annulus from the model by
   solving; `test_cell.py` re-derives it and fails if the numbers below
   have drifted outside it.

Disjoint territory is what *should* keep the arms apart, but a tool
centre point inside a window says nothing about where the elbow is. So
nothing here is trusted on that account: `simulate_cell.py` measures the
real clearance between every pair of arms, from the placed triangles,
at every frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from robot_arm.params import ArmParams

from . import kinematics as K

# The cell runs a longer-reach build of the same arm. Standing off the
# belt far enough to keep its own near edge outside the arm's inner
# limit, and reaching the *far* edge as well, needs more arm than the
# 573 mm default has: the far edge of the belt is 687 mm from the base
# and the default tops out around 550 at hover height. So the links get
# longer. `params.py` is the whole model, so this is one line, and
# `robot_arm.verify` passes on it unchanged -- which is the only reason
# it is safe to do.
CELL_ARM = ArmParams(upper_len=345.0, fore_len=285.0)

# ---- the conveyor ---------------------------------------------------
BELT_X0, BELT_X1 = -1720.0, 1720.0     # mm, boxes travel +X
BELT_HALF_W = 230.0                    # belt is 460 mm wide
BELT_TOP = 120.0                       # top surface above the floor
BELT_SPEED = 115.0                     # mm/s, and it never stops
SLAB_H = 44.0                          # thickness of the belt slab
RAIL_W = 26.0

# ---- the parts on it ------------------------------------------------
# Boxes are not three fixed sizes in three colours. They arrive at any
# size inside their band, and they all look the same: one colour, one
# shape. A cell that sorted a teal box into the teal bin would be
# demonstrating nothing -- the whole job is to *measure* the thing on
# the belt and work out which box it is designated for. The colour is
# on the bins, which are the designations, not on the parts.
PARCEL_COLOUR = "#b9a17c"


@dataclass(frozen=True)
class SizeClass:
    key: str
    name: str
    lo: float                          # band the measured edge must fall in
    hi: float
    colour: str                        # the designated bin's colour

    @property
    def nominal(self) -> float:
        return (self.lo + self.hi) / 2.0


CLASSES = (
    SizeClass("S", "small", 22.0, 30.0, "#48a9a6"),
    SizeClass("M", "medium", 34.0, 42.0, "#d98b39"),
    SizeClass("L", "large", 46.0, 54.0, "#c1554a"),
)
BY_KEY = {c.key: c for c in CLASSES}

# Thresholds sit in the gaps between the bands, so a measurement can
# never be ambiguous -- and `test_cell.py` checks the gaps are really
# there rather than taking the constants' word for it.
CUTS = ((CLASSES[0].hi + CLASSES[1].lo) / 2.0,
        (CLASSES[1].hi + CLASSES[2].lo) / 2.0)


def classify(size: float) -> SizeClass:
    """Which bin a box is designated for, from its measured edge.

    This is the whole job the arms are doing, so it takes a measurement
    and nothing else. Nothing downstream is allowed to ask a box what it
    "is" -- `sorter` routes on the answer to this function.
    """
    if size < CUTS[0]:
        return CLASSES[0]
    return CLASSES[1] if size < CUTS[1] else CLASSES[2]

# ---- the arms -------------------------------------------------------
ARM_OFFSET = 445.0                     # how far the bases stand off the belt
# Staggered at 520 mm, not 450. The arms got longer so that each could
# cross the belt, and a longer arm sweeps a bigger volume: at the old
# spacing two opposite-side arms reaching the centreline from either
# side closed to 73 mm of each other. The gap between facing windows is
# what that clearance is made of, so it is the gap that was widened.
ARM_XS = (-1040.0, -520.0, 0.0, 520.0, 1040.0)
ARM_SIDES = (-1, +1, -1, +1, -1)       # staggered: 3 near side, 2 far side
WINDOW_HALF = 190.0                    # half the length of belt an arm owns

# Verified annulus, in the horizontal plane, measured from the arm's own
# base. Both numbers are inside what `measure_envelope` reports at every
# height the program uses; the test re-measures and holds them to it.
# R_MAX covers the *far* edge of the belt, not just this arm's half --
# see `full_width_set`.
R_MIN, R_MAX = 195.0, 715.0

HOVER = 120.0                          # approach height above a grasp
BIN_R = 395.0                          # bins sit on an arc behind each arm
BIN_ANGLES = (-128.0, -90.0, -52.0)    # small, medium, large
BIN_TOP = 150.0
BIN_INNER = 105.0                      # half-width of a bin's opening


@dataclass(frozen=True)
class Arm:
    name: str
    index: int
    base: np.ndarray                   # 4x4, a pure translation
    side: int                          # -1 or +1, which half of the belt
    x0: float                          # window, along the belt
    x1: float
    bins: dict                         # size key -> world point on the rim
    yaw: float                         # how far round the base is bolted
    j1_range: tuple                    # continuous turret travel it needs
    park_seed: np.ndarray              # a starting guess for the park solve

    @property
    def origin(self) -> np.ndarray:
        return self.base[:3, 3]

    @property
    def rot(self) -> np.ndarray:
        return self.base[:3, :3]

    @property
    def az_centre(self) -> float:
        """Middle of the arm's azimuth travel, in its own frame, radians.

        J1 is the azimuth plus 90 and `turret_plan` centres J1 on zero,
        so this is -90 degrees by construction -- written as arithmetic
        on `j1_range` rather than as the constant, so it follows if the
        layout ever moves.
        """
        return np.radians(sum(self.j1_range) / 2.0 - 90.0)

    def to_local(self, world_pt) -> np.ndarray:
        return self.rot.T @ (np.asarray(world_pt, float) - self.origin)

    def to_local_dir(self, world_dir) -> np.ndarray:
        return self.rot.T @ np.asarray(world_dir, float)

    def to_world_point(self, local_pt) -> np.ndarray:
        return self.origin + self.rot @ np.asarray(local_pt, float)

    def to_world(self, m: np.ndarray) -> np.ndarray:
        return self.base @ m

    @property
    def park_point(self) -> np.ndarray:
        return park_point_for((self.x0 + self.x1) / 2.0, self.side)

    @property
    def _park_doc(self):
        """Where the arm waits: hovering over the middle of its own window.

        Parking in *Cartesian* terms, tool down, matters more than it
        looks. Every target the program commands points straight down
        with the jaws square to the belt; a park pose defined by joint
        angles would have some other tool orientation, and the first
        frame of every pick would open with a step change in commanded
        orientation that the solver then has to chase.
        """
        return np.array([(self.x0 + self.x1) / 2.0,
                         self.side * BELT_HALF_W * 0.55,
                         BELT_TOP + 265.0])

    def owns_side(self, y: float) -> bool:
        return (y < 0.0) if self.side < 0 else (y >= 0.0)

    def in_window(self, x: float) -> bool:
        return self.x0 <= x <= self.x1

    def can_reach(self, world_pt) -> bool:
        d = self.to_local(world_pt)
        r = float(np.hypot(d[0], d[1]))
        return R_MIN <= r <= R_MAX


def park_point_for(xc: float, side: int) -> np.ndarray:
    """Where an arm waits: hovering over the middle of its own window.

    Parking in *Cartesian* terms, tool down, matters more than it looks.
    Every target the program commands points straight down with the jaws
    square to the belt; a park pose defined by joint angles would have
    some other tool orientation, and the first frame of every pick would
    open with a step change in commanded orientation for the solver to
    chase.
    """
    return np.array([xc, side * BELT_HALF_W * 0.55, BELT_TOP + 265.0])


def _bin_points(ax: float, ay: float, side: int) -> dict:
    """Three bins on an arc behind the arm, away from the belt."""
    out = {}
    for cls, ang in zip(CLASSES, BIN_ANGLES):
        a = np.radians(ang if side < 0 else 180.0 - ang)
        out[cls.key] = np.array([ax + BIN_R * np.cos(a),
                                 ay + BIN_R * np.sin(a) * (1 if side < 0 else -1),
                                 BIN_TOP])
    return out


def _park_seed(side: int) -> np.ndarray:
    """A starting guess for the park solve: folded, tool down."""
    return np.array([0.0, -35.0, 125.0, 0.0, -15.0, 0.0])


def _world_points(ax: float, side: int, bins: dict) -> list[np.ndarray]:
    """Every extreme point an arm at (ax, side) is ever asked to reach."""
    x0, x1 = ax - WINDOW_HALF, ax + WINDOW_HALF
    zs = (BELT_TOP + CLASSES[0].lo / 2, BELT_TOP + CLASSES[-1].hi / 2,
          BELT_TOP + CLASSES[-1].hi / 2 + HOVER)
    pts = [np.array([x, y, z]) for z in zs
           for x in (x0, x1) for y in (side * BELT_HALF_W, 0.0)]
    pts += list(bins.values())
    pts += [b + (0.0, 0.0, HOVER) for b in bins.values()]
    pts.append(park_point_for(ax, side))
    return pts


def cover_arcs(angles_deg, tol=1e-6) -> list[tuple[float, float]]:
    """The narrowest arcs containing every one of these directions.

    Angles live on a circle, so "min and max" is meaningless -- a set
    straddling due south reports a 350-degree spread when the real
    spread is ten. Sort them, find the widest empty gap, and the answer
    is everything else.

    Plural because this particular set has a genuine tie: the belt in
    front of the arm and the bins behind it leave two equal gaps, so
    there are two equally narrow arcs covering both, differing in which
    way round the turret travels between them. Both are legal; the
    caller picks.
    """
    a = np.sort(np.mod(np.asarray(angles_deg, float), 360.0))
    gaps = np.diff(np.append(a, a[0] + 360.0))
    best = gaps.max()
    return [(float(a[(i + 1) % len(a)]), float(360.0 - gaps[i]))
            for i in np.flatnonzero(gaps >= best - tol)]


def turret_plan(origin: np.ndarray, pts, face_az: float):
    """How far round to bolt the base, and the J1 travel that then buys.

    J1 comes out 90 degrees round from the direction the arm reaches, so
    the turret travel a layout demands is exactly the arc spanned by
    everything the arm must reach; putting the middle of that arc dead
    ahead of the base leaves the most margin at both stops. Where two
    arcs tie, the base is turned to face the belt -- which is how anyone
    would bolt it down, and makes every arm on a side sit the same way.

    Returns (yaw, J1 low, J1 high) in degrees, the J1 pair as a
    *continuous* interval: a turret that sweeps from +140 to -140 the
    short way passes through 180, and reporting that as two wrapped
    endpoints hides the stop it just drove into.

    Derived, not chosen: move a bin or widen a window and the base turns
    to suit.
    """
    az = [np.degrees(np.arctan2(p[1] - origin[1], p[0] - origin[0]))
          for p in pts]
    best = None
    for arc_start, width in cover_arcs(az):
        yaw = (arc_start + 90.0 + width / 2.0) % 360.0
        off = abs((yaw - face_az + 180.0) % 360.0 - 180.0)
        if best is None or off < best[0]:
            best = (off, yaw, arc_start, width)
    _, yaw, arc_start, width = best
    lo = arc_start + 90.0 - yaw
    lo -= 360.0 * round((lo + width / 2.0) / 360.0)     # nearest to zero
    return yaw, lo, lo + width


def build_arms() -> list[Arm]:
    arms = []
    for i, (ax, side) in enumerate(zip(ARM_XS, ARM_SIDES)):
        ay = side * ARM_OFFSET
        origin = np.array([ax, ay, 0.0])
        bins = _bin_points(ax, ay, side)
        face = 90.0 if side < 0 else 270.0        # square on to the belt
        yaw, j1_lo, j1_hi = turret_plan(
            origin, _world_points(ax, side, bins), face)
        c, sn = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        base = np.eye(4)
        base[:3, :3] = ((c, -sn, 0.0), (sn, c, 0.0), (0.0, 0.0, 1.0))
        base[:3, 3] = origin
        arms.append(Arm(f"A{i + 1}", i, base, side,
                        ax - WINDOW_HALF, ax + WINDOW_HALF, bins, yaw,
                        (j1_lo, j1_hi), _park_seed(side)))
    return arms


ARMS = build_arms()


def owner_of(x: float, y: float) -> Arm | None:
    """Which arm, if any, may take a box whose centre is here."""
    for arm in ARMS:
        if arm.owns_side(y) and arm.in_window(x):
            return arm
    return None


def downstream_of(arm: Arm) -> list[Arm]:
    """Arms on the same side that get a later look at the same box."""
    return [a for a in ARMS if a.side == arm.side and a.x0 > arm.x1]


def grasp_z(size: float) -> float:
    return BELT_TOP + size / 2.0


def belt_x(x0: float, t0: float, t: float) -> float:
    return x0 + BELT_SPEED * (t - t0)


# ---- derivation, used by the tests ---------------------------------
def measure_envelope(p: ArmParams, z: float, lo=90, hi=820, step=20,
                     tol=0.25) -> tuple[float, float]:
    """Solve outward along a ray and report where the tool can be put.

    This is the number the layout is built on, so it is measured rather
    than assumed: the same inverse solver the program runs, asked for a
    tool pointing straight down at a series of radii.
    """
    good = []
    for r in range(lo, hi, step):
        tgt = np.array([0.0, float(r), z])
        q, pe, ae = K.solve_ik(p, K.target_frame(tgt), K.seed_for(tgt, p))
        if pe < tol and ae < tol:
            good.append(float(r))
    if not good:
        raise RuntimeError(f"nothing reachable at z={z}")
    return min(good), max(good)


def working_set(arm: Arm) -> list[np.ndarray]:
    """Every extreme point the arm is ever asked to put its tool at."""
    x = (arm.x0 + arm.x1) / 2.0
    return _world_points(x, arm.side, arm.bins)


def turret_span(arm: Arm) -> tuple[float, float]:
    """The continuous J1 travel this layout demands, in degrees.

    If either end runs past `kinematics.LIMITS`, the solver silently
    clips the turret and the tool lags its target -- which looks, on
    screen, exactly like a robot that misses.
    """
    return arm.j1_range


def window_corners(arm: Arm, z: float) -> list[np.ndarray]:
    """The four hardest points in a window, at a given height."""
    ys = (arm.side * BELT_HALF_W, 0.0)
    return [np.array([x, y, z]) for x in (arm.x0, arm.x1) for y in ys]


def full_width_set(arm: Arm) -> list[np.ndarray]:
    """Every point across the *whole* belt inside this arm's window.

    Capability, not policy. The dispatcher will never send an arm past
    the centreline -- that is what keeps two arms out of each other --
    but an arm that physically could not get there would be a different
    machine, reaching half a belt and calling it a rule. So the arm is
    long enough to cross, and `simulate_cell.py` proves it by solving,
    while the territory rules go on holding it to its own side.
    """
    zs = (BELT_TOP + CLASSES[0].lo / 2, BELT_TOP + CLASSES[-1].hi / 2,
          BELT_TOP + CLASSES[-1].hi / 2 + HOVER)
    return [np.array([x, y, z]) for z in zs for x in (arm.x0, arm.x1)
            for y in (-BELT_HALF_W, 0.0, BELT_HALF_W)]
