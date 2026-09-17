"""Boxes on the belt, and the control system that decides who takes what.

The belt never stops, so every pick is a moving one. An arm claims a box
only when it can prove three things about it: the box is on its half of
the belt, the point where it would meet the box lands inside its own
window, and that point is inside the annulus the arm can actually reach.
A box that nobody can claim in time stays on the belt and gets another
look from the next arm on the same side; past the last window it runs
off the end and is counted as a miss. That is what a real line does, and
it is the only reason the staggered layout is interesting.

**Tracking.** The tool does not wait for the box, and the box does not
wait for the tool. Through `TRACK` the target is the moving box plus a
hover height; through `DESCEND` that hover is eased to zero *while the
target keeps moving*; through `CLOSE` the target is the box exactly. The
useful consequence falls out of the quintic ease rather than being
arranged: the ease has zero derivative at s=1, so at the instant of the
grasp the tool's velocity is the belt's velocity, to numerical precision.
`simulate_cell.py` measures that per frame instead of taking it on trust.

The same trick runs the other way out of the grasp: `LIFT` blends from
the moving box frame to a stationary bin, and the ease's zero derivative
at s=0 means the box leaves the belt at belt speed rather than being
snatched off it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from robot_arm.params import ArmParams

from . import cell as C
from . import kinematics as K
from . import rigid as R

# ---- how long each part of a pick takes -----------------------------
TRACK_T = 1.30
DESCEND_T = 0.75
CLOSE_T = 0.35
LIFT_T = 1.60
DROP_T = 0.65
OPEN_T = 0.30
RETURN_T = 1.70
# The task ends when the box is let go. Going home is *not* part of it:
# an arm that has to finish walking back to its park pose before the
# dispatcher will look at it is an arm standing in its own way, and with
# boxes arriving every second and a half that dead trip is most of a
# cycle. Returning is what an arm does when nothing needs doing, and
# anything needing doing interrupts it -- see `home_pose`.
PHASES = (("TRACK", TRACK_T), ("DESCEND", DESCEND_T), ("CLOSE", CLOSE_T),
          ("LIFT", LIFT_T), ("DROP", DROP_T), ("OPEN", OPEN_T))
CYCLE_T = sum(d for _, d in PHASES)
INTERCEPT_T = TRACK_T + DESCEND_T      # from claim to touchdown

ARC = 120.0                             # how high a carry move bows
# The carry pulls its radius in over the first part of the move and does
# its turret travel over the rest, so the tool is off the belt before it
# starts tracking along it. The return does the same in reverse.
RETREAT = 0.55
SWEEP_FROM = 0.40
# Keep intercepts this far off a window edge. Derived, because a fixed
# margin was wrong: the jaws go on tracking the box for the whole of
# CLOSE, so the box is `CLOSE_T` worth of belt further downstream when
# it is actually gripped than it was at touchdown. A 12 mm margin
# against 40 mm of travel meant a box could be claimed legitimately and
# gripped outside the window.
EDGE = CLOSE_T * C.BELT_SPEED + 15.0
# A filled cardboard parcel: about 250 kg/m^3, so a 100 mm box is a
# quarter of a kilo. Mass is what makes the solver's answers mean
# anything -- it sets how hard a box lands and how much friction the
# jaws need to hold it.
DENSITY = 2.5e-7                       # kg/mm^3
JAW_MARGIN = 24.0                      # how much wider than the box the jaws open
# How much daylight the jaw tips keep under them at the grasp. A claw
# reaches *below* what it grips -- the fingers curl past the pads -- so
# a short box gripped exactly across its middle would drag four tips
# along the belt to get there.
JAW_CLEAR = 10.0
# What an idle arm holds its jaws at. Parked wide open the claw is
# 200 mm across, and that is what two arms came closest with: a
# neighbour's carry passed 38 mm from a jaw that was open only because
# nothing had ever told it to shut.
PARK_GAP = 22.0
# Closest two boxes are ever spawned. The claw opens to about 200 mm
# across around a 140 mm box, so a box needs that much clear belt behind
# it or the claw would come down around its neighbour too.
MIN_GAP_X = 300.0


def open_gap(size: float) -> float:
    return size + JAW_MARGIN


def crush_depth(p: ArmParams) -> float:
    """How far a grip ridge sinks into the box, in mm.

    This is the only distance by which any part of a claw is ever
    allowed to be inside a box, and the box is what yields, not the
    claw. A grip ridge is a cylinder of radius `grab_pad_r` lying
    across a flat face, so an indentation d makes a contact strip of
    half-width sqrt(2*R*d); the board carries the load at its crush
    strength over that strip:

        F = sigma_c * 2*sqrt(2*R*d) * L

    Solved for d. At 260 N over four jaws -- 65 N each -- on a 4 mm
    ridge 22 mm long, double-wall board gives about 1.1 mm. That is
    what "the box gives way to the claw" is worth in millimetres, and
    it is why the claw closing on a box 60 mm wider than it can wrap
    was never going to be explained by the box yielding.
    """
    from math import sqrt
    force = p.grip_force / p.grab_jaws
    strip = force / (C.BOARD_CRUSH * 2.0 * p.grab_jaw_w)
    return strip ** 2 / (2.0 * p.grab_pad_r)


def panel_dish(p: ArmParams, size: float) -> float:
    """How far the whole side panel bows in under a jaw, in mm.

    The other way a box gives way, and the one with something to see.
    A box's side is a plate held at its four folded edges, and a pad
    pressing in the middle of it bends the plate. For a square plate,
    simply supported, with a load in the middle:

        w = 0.0116 * P * a^2 / D

    which goes as the *square* of the panel, so a big box folds and a
    small one barely notices -- 2.0 mm across a 112 mm face against
    0.2 mm across a 38 mm one. Exactly what you see doing it by hand.

    The corners take none of it. That is why this is a fold and not a
    box getting smaller.
    """
    return 0.0116 * (p.grip_force / p.grab_jaws) * size ** 2 / C.BOARD_BEND


# How long the panel takes to come back once the load is off it. Board
# is viscoelastic, so recovery is a rate and not an event: it springs
# most of the way back and then creeps. This is what makes the dent
# outlive the grip -- the jaws come off in a fifth of a second and the
# box is still coming back after they have gone.
RECOVER_TAU = 0.35                     # seconds


# The phases in which the jaws are actually around the box. An arm
# keeps `task.parcel` pointing at its box until the task ends, which is
# long after it let go of it -- through RETURN, where the jaws shut to
# PARK_GAP. Asking "is an arm assigned to this box" instead of "are its
# jaws on it" had a claw parked across the cell crushing a box by
# (size - PARK_GAP)/2, which for a 109 mm box is 43.6 mm: five times
# the deepest fold the board has in it, on a box still riding the belt.
ON_THE_BOX = ("CLOSE", "LIFT", "DROP", "OPEN")


def jaw_demand(pc, states) -> float:
    """How far the jaws have closed past this box's faces, in mm.

    What the claw is *asking* of the board, which is not the same as
    what the board is doing -- see `relax`. Zero unless a claw is
    really around it: `pc.body` means it has been let go, and a box
    that has been let go is not being squeezed by anything.
    """
    if pc.body is not None:
        return 0.0
    for st in states:
        if st.busy and st.task.parcel is pc and st.task.phase in ON_THE_BOX:
            return max(0.0, (pc.size - st.gap) / 2.0)
    return 0.0


def relax(p: ArmParams, pc, demand: float, dt: float) -> None:
    """Advance one box's fold by one frame.

    The two directions are not symmetric, because the two materials
    are not. Going in, the claw is steel and the board is not: it
    yields exactly as far as the jaws have gone, this frame, because
    there is nothing else it can do. Coming out, nothing is pushing
    any more and the panel is on its own clock -- so it lags the jaws
    rather than tracking them, and the dent is still there after the
    claw has let go and moved away.

    What it cannot spring back past is the crush. The dish is a plate
    bent inside its elastic range and it gives the energy back; the
    crush is flutes collapsed under a 4 mm ridge, and board does not
    un-crush. So the permanent set is not a number anyone picked: it
    is `crush_depth`, scaled by how far into the fold this box
    actually got.
    """
    if demand > pc.squeeze:
        pc.squeeze = demand
        pc.peak = max(pc.peak, demand)
        return
    full = panel_dish(p, pc.size) + crush_depth(p)
    kept = crush_depth(p) * min(1.0, pc.peak / full) if full > 0.0 else 0.0
    goal = max(demand, kept)
    pc.squeeze = goal + (pc.squeeze - goal) * np.exp(-dt / RECOVER_TAU)


def grip_gap(p: ArmParams, size: float) -> float:
    """The gap the jaws actually close to on a box of this size.

    Tighter than the box by everything the box gives -- the panel
    bending plus the board crushing under the ridge -- because that is
    what makes the grip a grip. Closing to exactly `size` puts the
    ridges tangent to the faces with no contact force at all, which is
    a claw resting against a box, not holding one.
    """
    return size - 2.0 * (panel_dish(p, size) + crush_depth(p))


# ---------------------------------------------------------------------
@dataclass
class Parcel:
    pid: int
    size: float                        # the measured edge -- the only input
    y: float
    x_at_t0: float
    t0: float
    drop_dx: float = 0.0               # where in the bin it gets let go
    drop_dy: float = 0.0
    state: str = "belt"                # belt | held | falling | binned
    claimed_by: int | None = None
    picked_by: int | None = None
    hold_offset: np.ndarray | None = None
    body: object = None                # rigid.Body, once it has been let go
    prev_pose: np.ndarray | None = None
    prev2: np.ndarray | None = None
    seen_at: float = -1.0
    squeeze: float = 0.0               # mm off each gripped face, now
    peak: float = 0.0                  # the deepest it has ever been folded

    @property
    def mass(self) -> float:
        return DENSITY * self.size ** 3

    @property
    def cls(self) -> C.SizeClass:
        """Which box this one is designated for -- derived, every time,
        from the measurement. Nothing stores the answer."""
        return C.classify(self.size)

    def belt_pose(self, t: float) -> np.ndarray:
        m = np.eye(4)
        m[:3, 3] = self.belt_point(t)
        return m

    def belt_point(self, t: float) -> np.ndarray:
        return np.array([C.belt_x(self.x_at_t0, self.t0, t), self.y,
                         C.grasp_z(self.size)])


def spawn_plan(seconds: float, seed: int = 11, mean_gap: float = 1.15,
               lead: float = 0.0) -> list[Parcel]:
    """Boxes arriving at random times, sizes and lateral positions.

    One constraint keeps it a sorting problem rather than a pile-up: no
    two boxes are ever closer together along the belt than `MIN_GAP_X`.
    Laterally a box may sit anywhere it fits on the belt, because every
    arm works the full width of its own stretch.
    """
    rng = np.random.default_rng(seed)
    out: list[Parcel] = []
    t = lead
    pid = 0
    while t < seconds:
        band = C.CLASSES[int(rng.integers(0, len(C.CLASSES)))]
        size = float(rng.uniform(band.lo, band.hi))
        margin = size / 2.0 + C.BELT_EDGE_MARGIN
        y = float(rng.uniform(-(C.BELT_HALF_W - margin),
                              C.BELT_HALF_W - margin))
        # Release points that clear the walls *however the box is
        # turned*. The wrist carries whatever yaw the turret swing left
        # it with, so the footprint to fit between the walls is the
        # diagonal, not the edge.
        reach = max(0.0, C.BIN_CLEAR - 0.75 * size - 8.0)
        out.append(Parcel(pid, size, y, C.BELT_X0, t,
                          drop_dx=float(rng.uniform(-reach, reach)),
                          drop_dy=float(rng.uniform(-reach, reach))))
        pid += 1
        t += max(MIN_GAP_X / C.BELT_SPEED, float(rng.exponential(mean_gap)))
    return out


# ---------------------------------------------------------------------
@dataclass
class Task:
    """One pick, as a sequence of phases measured in frames.

    Frames rather than seconds on purpose: the whole velocity argument
    rests on the blend parameter reaching exactly 1.0 at a phase
    boundary, and `t - t_start >= duration` does not reliably land there.
    """
    parcel: Parcel
    bin_pt: np.ndarray
    meet: np.ndarray = None            # where the box will be at touchdown
    jaw_az: float = 0.0                # local azimuth of the belt axis
    phase_i: int = 0
    k: int = 0                         # frames elapsed in this phase
    anchor: np.ndarray | None = None   # world tool pose when it began
    gap0: float = PARK_GAP             # jaw opening it started from

    @property
    def phase(self) -> str:
        return PHASES[self.phase_i][0]


@dataclass
class ArmState:
    arm: C.Arm
    joints: np.ndarray
    gap: float
    park_q: np.ndarray                 # joints that hold the park point
    park_tcp: np.ndarray               # world 4x4 at the park point
    task: Task | None = None
    tcp: np.ndarray = None             # world 4x4
    picks: int = 0
    # When this arm last had nothing to do. The dispatcher is a queue,
    # not a scan, and this is its key -- see `run`.
    idle_since: float = 0.0
    # Going home, if it is going home: where it started, how open its
    # jaws were, and how many frames in it is. Cleared the instant it
    # claims something, because the way back is never worth finishing.
    home_from: np.ndarray | None = None
    home_gap: float = PARK_GAP
    home_k: int = 0

    @property
    def phase(self) -> str:
        return self.task.phase if self.task else "IDLE"

    @property
    def busy(self) -> bool:
        return self.task is not None


# How firmly each phase insists on the jaws being square to the belt:
# 1 means "along the belt", 0 means "whatever the wrist does naturally".
#
# The constraint is engaged over the last third of the approach and let
# go over the first third of the carry, rather than across the whole of
# either. Both of those moves sweep the turret a long way, and a jaw
# axis pinned in the world has to be paid for in J6 the whole time; the
# box is only being gripped at the ends, so that is where the alignment
# is worth having.
SQUARE_BAND = 0.35


def _square_weight(phase: str, s: float) -> float:
    if phase == "TRACK":
        return K.ease(max(0.0, (s - (1.0 - SQUARE_BAND)) / SQUARE_BAND))
    if phase in ("DESCEND", "CLOSE"):
        return 1.0
    if phase == "LIFT":
        return 1.0 - K.ease(min(1.0, s / SQUARE_BAND))
    return 0.0


def _jaw_az(arm: C.Arm, grasp_pt: np.ndarray) -> float:
    """The belt axis in the arm's frame, on the branch nearest the pose
    the arm will actually be in when it grips -- decided once, when the
    box is claimed.

    Two things make this worth pinning. A jaw axis is an axis, so it is
    only defined modulo half a turn, and recomputing the branch each
    frame lets it flip sign mid-carry: a 107-degree step in J6 for no
    physical reason. And holding it *fixed* through the grasp, rather
    than as an offset from a wrist that keeps turning, is what makes the
    jaws square to the box for the whole of the close rather than only
    at the instant they touch.
    """
    lp = arm.to_local(grasp_pt)
    nat = np.arctan2(lp[1], lp[0]) + np.pi / 2.0
    return nat + _wrap_half(np.radians(-arm.yaw) - nat)


def _jaw_local(arm: C.Arm, local_pos: np.ndarray, w: float,
               jaw_az: float) -> np.ndarray:
    """Which way the jaws close, in the arm's frame.

    Square to the belt is what a *box* needs: its faces are flat and
    parallel to the belt edges, and the natural wrist -- jaws tangential
    to whatever direction the arm happens to be reaching -- would meet
    them at up to forty degrees off and grip a corner.

    But insisting on it everywhere is what breaks the arm. A jaw axis
    fixed in the world has to be held while the turret sweeps 218
    degrees from belt to bin, and the tool roll J6 has to pay for every
    one of those degrees; it runs out of travel well before the bin.
    Nothing is being gripped on the way there, so the constraint is
    faded in over the approach and faded out over the carry, and J6
    stays inside forty-odd degrees.
    """
    nat = np.arctan2(local_pos[1], local_pos[0]) + np.pi / 2.0
    a = nat + (jaw_az - nat) * w
    return np.array([np.cos(a), np.sin(a), 0.0])


def _wrap_half(a: float) -> float:
    """Bring an angle into (-90, 90] degrees, in radians."""
    return (a + np.pi / 2.0) % np.pi - np.pi / 2.0


def _polar(arm: C.Arm, pt):
    """Radius, azimuth and height in the arm's *own* frame.

    The azimuth is unwrapped into the arm's own travel window rather than
    left in atan2's (-180, 180]. A bin behind the arm sits at -220
    degrees of local azimuth; atan2 reports it as +139, and interpolating
    towards +139 sweeps the turret the wrong way round -- straight into
    the stop it was bolted at 90 degrees to avoid.
    """
    d = arm.to_local(pt)
    c = arm.az_centre
    a = np.arctan2(d[1], d[0])
    a = c + (a - c + np.pi) % (2 * np.pi) - np.pi
    return float(np.hypot(d[0], d[1])), float(a), float(d[2])


def home_pose(st, s: float, p: ArmParams):
    """Where an idle arm is on its way back to park.

    The same motion RETURN used to be, lifted out of the task so that
    nothing waits on it. It has no parcel and asks for no jaw
    alignment -- it is carrying nothing -- and it is abandoned mid-way
    the moment a box is claimed, which is the whole point.
    """
    e = K.ease(s)
    bump = ARC * np.sin(np.pi * s) ** 2
    pos = _swing(st.arm, st.home_from[:3, 3], st.park_tcp[:3, 3], e, bump)
    gap = float(K.blend([st.home_gap], [PARK_GAP], s)[0])
    lp = st.arm.to_local(pos)
    return st.arm.base @ K.target_frame(lp), gap


def _swing(arm: C.Arm, p0, p1, e: float, bump: float = 0.0) -> np.ndarray:
    """Blend two points *around* the arm, not through it.

    A straight line from a box on the belt to a bin behind the arm passes
    within centimetres of the arm's own column -- a radius far inside
    anything it can reach, so the solver is handed a target it cannot
    hold and the whole move collapses. Interpolating in the arm's own
    polar coordinates keeps the radius between the two endpoints, which
    are both known reachable, and turns the carry into what it physically
    is: a turret sweep.
    """
    r0, a0, z0 = _polar(arm, p0)
    r1, a1, z1 = _polar(arm, p1)
    # No wrapping, deliberately. The base is bolted down so that the
    # whole working set falls inside one unwrapped half-turn either side
    # of dead ahead (`cell.turret_plan`), so a straight interpolation
    # between two of those azimuths is already the path that stays off
    # the turret stop. Taking the "short way round" instead would
    # sometimes choose the arc that drives straight into it.
    r, a = r0 + (r1 - r0) * e, a0 + (a1 - a0) * e
    return arm.to_world_point((r * np.cos(a), r * np.sin(a),
                               z0 + (z1 - z0) * e + bump))


def target_pose(st: ArmState, s: float, t: float, p: ArmParams):
    """(world tool pose, jaw gap) for this arm at this instant.

    `s` runs 0 -> 1 across the current phase and lands exactly on 1.0 on
    its last frame. Every blend below uses the quintic ease, whose
    derivative vanishes at both ends -- which is what makes the tool
    arrive at the box moving at belt speed, and leave the belt at belt
    speed, without either being arranged explicitly.
    """
    arm, task = st.arm, st.task
    if task is None:
        return st.park_tcp, st.gap

    e = K.ease(s)
    size = task.parcel.size
    # Where the box would be if it were still riding the belt. After the
    # grasp it is not, but it stays the right frame to peel away *from*:
    # leaving it at e = 0 means leaving at belt speed.
    belt_ref = grasp_at(p, task.parcel.belt_point(t), size)
    hover = np.array([0.0, 0.0, C.HOVER])
    bump = ARC * np.sin(np.pi * s) ** 2
    ph = task.phase

    meet = grasp_at(p, task.meet, size)
    if ph == "TRACK":
        # To the intercept, which is a *fixed* point inside this arm's
        # own window -- not to wherever the box happens to be now. The
        # box is still upstream at this moment, and an arm that flies
        # out to meet it there is an arm reaching into the territory of
        # the one before it. Which is exactly what it was doing: the
        # closest two arms ever came was a gripper out past its own
        # window boundary, chasing a box that had not arrived yet.
        pos = _swing(arm, task.anchor[:3, 3], meet + hover, e)
        # The jaws open on the way out, from wherever the arm was
        # holding them, and are open by the time it is over the box.
        gap = float(K.blend([task.gap0], [open_gap(size)], s)[0])
    elif ph == "DESCEND":
        # One blend from that fixed hover point onto the moving box. At
        # s = 0 it is the hover point with zero velocity, continuous
        # with the end of TRACK; at s = 1 it is the box itself, and
        # because the ease has zero derivative there, moving at exactly
        # belt speed.
        pos = (1 - e) * (meet + hover) + e * belt_ref
        gap = open_gap(size)
    elif ph == "CLOSE":
        pos = belt_ref
        gap = float(K.blend([open_gap(size)], [grip_gap(p, size)], s)[0])
    elif ph == "LIFT":
        pos = _swing(arm, belt_ref, task.bin_pt + hover, e, bump)
        gap = grip_gap(p, size)
    elif ph == "DROP":
        pos = (1 - e) * (task.bin_pt + hover) + e * _drop_pt(p, task, size)
        gap = grip_gap(p, size)
    else:                                            # OPEN
        pos = _drop_pt(p, task, size)
        gap = float(K.blend([grip_gap(p, size)], [open_gap(size)], s)[0])

    lp = arm.to_local(pos)
    jaw = _jaw_local(arm, lp, _square_weight(ph, s), task.jaw_az)
    return arm.base @ K.target_frame(lp, jaw=jaw), gap


def grasp_at(p: ArmParams, pt, size: float) -> np.ndarray:
    """Where the tool centre point goes to put the grip ridges on a box.

    Two corrections, both properties of a claw rather than of the cell.

    The ridges are only at the tool centre point at one stated opening,
    because closing a claw swings its grip along the tool as well as
    in; `pad_offset` is that swing, and the target is raised by it.

    And a claw reaches below what it grips. Gripping a 48 mm box
    exactly across its middle would put four fingertips 5 mm off the
    belt, so the whole grasp lifts until they clear it -- taking the
    box a little above its middle instead, which its 48 mm of side has
    room for.
    """
    z = max(C.BELT_TOP + size / 2.0,
            C.BELT_TOP + K.jaw_tip_drop(p, size) + JAW_CLEAR)
    return np.array([pt[0], pt[1], z + K.pad_offset(p, size)])


def _drop_pt(p: ArmParams, task: Task, size: float) -> np.ndarray:
    """Where the jaws let go: somewhere over the bin, not its dead centre.

    A gripper that always releases over the same point drops a tidy
    column. It releases over the bin, and where in the bin is whatever
    the approach happened to leave it -- drawn once, with the box.
    """
    pc = task.parcel
    return task.bin_pt + (pc.drop_dx, pc.drop_dy,
                          C.BIN_DROP_CLEAR + size / 2.0
                          + K.pad_offset(p, size))


# ---------------------------------------------------------------------
def can_claim(arm: C.Arm, parcel: Parcel, t: float) -> bool:
    """Would this arm meet this box inside its own territory?

    Two conditions, and a box has to satisfy both: the point where the
    tool would touch down lands inside this arm's stretch of belt, at
    any point across its width, and that point -- and the hover above
    it -- are inside the annulus the arm can actually reach. Nothing is
    claimed on optimism.
    """
    if parcel.state != "belt" or parcel.claimed_by is not None:
        return False
    # Nothing is claimed before it has been measured. The cell sorts on
    # what the sensor reads, so an arm that claims a box upstream of the
    # sensor is sorting on what the spawner knew -- which is not the
    # same machine at all. It also pins the layout: the first arm's
    # window has to start downstream of SENSOR_X, and this is what
    # notices when it does not.
    if parcel.seen_at < 0:
        return False
    meet = parcel.belt_point(t + INTERCEPT_T)
    if not (arm.x0 + EDGE <= meet[0] <= arm.x1 - EDGE):
        return False
    if abs(meet[1]) > C.BELT_HALF_W:
        return False
    return arm.can_reach(meet) and arm.can_reach(meet + (0, 0, C.HOVER))


# ---------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------
SENSOR_X = C.BELT_X0 + 260.0           # where a box is first seen and sized
# A box on a belt end starts to fall when its centre of mass passes the
# edge, not before and not after. That instant is the whole rule.
REJECT_AT = C.BELT_X1


@dataclass
class Snap:
    pid: int
    key: str
    pose: np.ndarray
    state: str
    claimed_by: int | None
    size: float = 0.0
    squeeze: float = 0.0               # mm off each gripped face, while held


@dataclass
class Frame:
    t: float
    joints: list
    gaps: list
    phases: list
    targets: list
    tcp: list
    parcels: list
    counts: dict
    physics: dict = field(default_factory=dict)


def _static(half, centre) -> R.Body:
    """Scenery for the solver: infinite mass, never moves, never sleeps."""
    return R.Body(half=np.asarray(half, float), mass=1.0,
                  pos=np.asarray(centre, float),
                  quat=np.array([1.0, 0.0, 0.0, 0.0]), static=True)


def bin_world(centre) -> R.World:
    """One solver per bin: its plinth, its four walls, the shop floor.

    Per bin rather than one world for the cell, because the cost of the
    broad phase is quadratic and boxes three metres apart have nothing
    to say to each other. Walls are finite slabs, so a box that the
    physics throws over a rim lands on the floor outside instead of
    being held in by an infinite plane -- which is the only way "it
    stayed in its bin" can be a measurement rather than a definition.
    """
    w = R.World()
    w.planes.append(R.Plane(np.array([0.0, 0.0, 1.0]), 0.0))
    cx, cy = float(centre[0]), float(centre[1])
    w.add(_static((C.BIN_INNER, C.BIN_INNER, C.BIN_FLOOR_Z / 2.0),
                  (cx, cy, C.BIN_FLOOR_Z / 2.0)))
    for half, c in C.bin_walls(cx, cy):
        w.add(_static(half, c))
    return w


def chute_world() -> R.World:
    """The reject chute, plus the end of the belt to tip off."""
    w = R.World()
    w.planes.append(R.Plane(np.array([0.0, 0.0, 1.0]), 0.0))
    w.add(_static(C.CHUTE_HALF,
                  C.CHUTE_PT + (0.0, 0.0, C.CHUTE_FLOOR_Z / 2.0)))
    for half, c in C.chute_walls():
        w.add(_static(half, c))
    w.add(_static(*C.belt_end()))
    return w


def _twist(prev: np.ndarray, cur: np.ndarray, dt: float):
    """Linear and angular velocity between two poses one frame apart.

    What the gripper was doing at the instant it opened. A box let go
    from a moving tool keeps moving; one let go from a turning tool
    keeps turning. Neither is animated afterwards.
    """
    vel = (cur[:3, 3] - prev[:3, 3]) / dt
    dr = cur[:3, :3] @ prev[:3, :3].T
    axis = 0.5 * np.array([dr[2, 1] - dr[1, 2], dr[0, 2] - dr[2, 0],
                           dr[1, 0] - dr[0, 1]])
    ang = float(np.arccos(np.clip((np.trace(dr) - 1.0) / 2.0, -1.0, 1.0)))
    n = float(np.linalg.norm(axis))
    if n < 1e-9 or ang < 1e-9:
        return vel, np.zeros(3)
    return vel, axis / n * (ang / dt)


def release(world: R.World, pc: Parcel, pose: np.ndarray,
            vel: np.ndarray, omega: np.ndarray, t: float = 0.0) -> R.Body:
    """Hand a box to the solver. After this nothing scripts it."""
    body = R.Body(half=np.full(3, pc.size / 2.0), mass=pc.mass,
                  pos=pose[:3, 3].copy(), quat=R.mat_to_quat(pose[:3, :3]),
                  vel=np.asarray(vel, float).copy(),
                  omega=np.asarray(omega, float).copy(), tag=(pc.pid, t))
    world.add(body)
    pc.body = body
    pc.state = "falling"
    return body


def run(p: ArmParams, seconds: float = 26.0, fps: int = 30, seed: int = 11,
        mean_gap: float = 1.4, lead: float = 40.0, report=print):
    """Simulate the whole cell, frame by frame.

    `lead` seeds the belt with boxes that notionally arrived before the
    clip starts -- a whole transit time of them, so the line opens
    already running rather than waiting half a minute for the first box
    to travel down from the infeed. A 4200 mm belt at 115 mm/s takes
    36.5 s end to end, so the lead has to be at least that or the far
    arms open on empty belt through no fault of their own.
    """
    parcels = spawn_plan(seconds, seed, mean_gap, lead=-lead)
    steps = {name: max(1, int(round(d * fps))) for name, d in PHASES}
    home_steps = max(1, int(round(RETURN_T * fps)))
    states = []
    for a in C.ARMS:
        local_pt = a.to_local(a.park_point)
        goal = K.target_frame(local_pt)           # natural wrist, as TRACK starts
        q, pe, ae = K.solve_ik(p, goal, K.seed_for(local_pt, p))
        if pe > 0.2 or ae > 0.2:
            raise RuntimeError(f"{a.name} cannot hold its park point "
                               f"({pe:.2f} mm, {ae:.2f} deg)")
        states.append(ArmState(a, q.copy(), PARK_GAP,
                               q.copy(), a.base @ K.tcp(p, q)))
    for st in states:
        st.tcp = st.park_tcp.copy()

    # One solver per bin, built on first use, plus one for the chute.
    worlds: dict = {}
    diag = {"ik_pos": [], "ik_ang": [], "grasp_rel": [], "track_err": [],
            "tcp_step": [], "claims": [], "zone_ok": [], "jaw_floor": [],
            "grasps": [], "jaw_square": [], "grasp_pose": [],
            "energy_lift": [], "overlap": [], "grip_z": [],
            "carry_accel": [], "awake_at_end": []}
    counts = {"seen": 0, "picked": 0, "missed": 0,
              **{c.key: 0 for c in C.CLASSES}}
    frames: list[Frame] = []
    n = int(round(seconds * fps))
    dt = 1.0 / fps
    prev = [st.tcp[:3, 3].copy() for st in states]

    for i in range(n):
        t = i * dt

        for pc in parcels:
            if pc.seen_at < 0 and pc.t0 <= t and pc.belt_point(t)[0] >= SENSOR_X:
                pc.seen_at = t
                counts["seen"] += 1

        # --- claiming: any idle arm, its own territory ----------------
        # Every arm may work at the same time as every other. There is
        # no mutual exclusion here and there is not meant to be: two
        # machines that cannot both run are two machines you are paying
        # for and using as one. What keeps them out of each other is the
        # layout -- 800 mm of stagger and 480 mm of standoff, measured
        # at 144 mm of clearance with all five working -- and
        # `check_clearance` is what holds that to it, frame by frame,
        # from the placed triangles rather than from a rule.
        #
        # The order is still longest-idle-first so the machine is
        # deterministic and does not favour a low index.
        for st in sorted(states, key=lambda s: (s.idle_since, s.arm.index)):
            if st.busy:
                continue
            # An arm ahead on the count lets the box run to a quieter
            # one downstream. A box this arm can reach now, every arm
            # downstream of it can reach later -- the same fact the
            # hand-off rests on -- so the line levels itself out
            # instead of the first arm taking everything it sees.
            # Nobody defers forever: the test stops firing the moment
            # the counts level, and the last arm has nothing downstream
            # to defer to at all.
            if any(states[a.index].picks < st.picks
                   for a in C.downstream_of(st.arm)):
                continue
            live = [pc for pc in parcels
                    if pc.t0 <= t and can_claim(st.arm, pc, t)]
            if not live:
                continue
            pc = max(live, key=lambda q: q.belt_point(t)[0])
            pc.claimed_by = st.arm.index
            meet = pc.belt_point(t + INTERCEPT_T)
            # Routed on the measurement, not on anything the spawner knew.
            st.task = Task(pc, st.arm.bins[C.classify(pc.size).key],
                           meet=meet, jaw_az=_jaw_az(st.arm, meet),
                           anchor=st.tcp.copy(), gap0=st.gap)
            st.home_from = None                  # the way back can wait
            diag["claims"].append((round(t, 2), st.arm.name, pc.pid, pc.cls.key))

        # --- drive every arm ------------------------------------------
        for k, st in enumerate(states):
            if st.busy:
                st.task.k += 1
                s = st.task.k / steps[st.task.phase]
                goal, gap = target_pose(st, s, t, p)
                local = np.linalg.inv(st.arm.base) @ goal
                q, pe, ae = K.solve_ik(p, local, st.joints)
                st.joints = q
                diag["ik_pos"].append(pe)
                diag["ik_ang"].append(ae)
            elif st.home_from is not None:
                # On its way home, and it can be interrupted at any
                # frame of it. Nothing depends on it arriving.
                st.home_k += 1
                s_home = min(1.0, st.home_k / max(1, home_steps))
                goal, gap = home_pose(st, s_home, p)
                local = np.linalg.inv(st.arm.base) @ goal
                q, pe, ae = K.solve_ik(p, local, st.joints)
                st.joints = q
                diag["ik_pos"].append(pe)
                diag["ik_ang"].append(ae)
                if s_home >= 1.0:
                    st.home_from = None          # parked; just hold it
            else:
                # Parked. Hold whatever joints it arrived in: snapping to
                # the stored park solution would step the wrist a hundred
                # degrees to reach the same point a different way.
                gap = st.gap
            st.gap = gap
            st.tcp = st.arm.to_world(K.tcp(p, st.joints))

            v = (st.tcp[:3, 3] - prev[k]) / dt
            diag["tcp_step"].append(float(np.linalg.norm(st.tcp[:3, 3] - prev[k])))
            if st.busy and st.task.phase == "CLOSE":
                pc = st.task.parcel
                here = pc.belt_point(t)
                diag["grasp_rel"].append(
                    float(np.linalg.norm(v - (C.BELT_SPEED, 0.0, 0.0))))
                # The claw's axis over the box's centre. Vertically the
                # tool is deliberately *not* on the box -- see
                # `grasp_at` -- so tracking is the horizontal question,
                # and where the grip lands is asked separately.
                diag["track_err"].append(float(np.linalg.norm(
                    st.tcp[:2, 3] - here[:2])))
                # The ridges are `pad_offset` further down the tool than
                # the tool centre point, and the fingertips curl
                # `jaw_tip_drop` past the ridges.
                ridge = st.tcp[2, 3] - K.pad_offset(p, st.gap)
                diag["grip_z"].append(
                    (float(ridge), float(here[2]), float(pc.size)))
                diag["jaw_floor"].append(
                    float(ridge - K.jaw_tip_drop(p, st.gap) - C.BELT_TOP))
            prev[k] = st.tcp[:3, 3].copy()

        # --- boxes nobody took run off the end ------------------------
        for pc in parcels:
            if (pc.state == "belt" and pc.t0 <= t and pc.claimed_by is None
                    and pc.belt_point(t)[0] >= REJECT_AT):
                w = worlds.setdefault("R", chute_world())
                release(w, pc, pc.belt_pose(t),
                        (C.BELT_SPEED, 0.0, 0.0), np.zeros(3), t)
                counts["missed"] += 1

        # --- phase advance --------------------------------------------
        for st in states:
            if not st.busy or st.task.k < steps[st.task.phase]:
                continue
            task, pc = st.task, st.task.parcel
            if task.phase == "CLOSE":
                pc.state = "held"
                pc.hold_offset = np.linalg.inv(st.tcp) @ pc.belt_pose(t)
                here = pc.belt_point(t)
                diag["zone_ok"].append(bool(st.arm.owns(here[0], pc.y)))
                diag["grasps"].append((st.arm.name, pc.pid, pc.cls.key,
                                       float(here[0]), float(here[1])))
                # how square did the jaws actually end up to the belt?
                ax = st.tcp[:3, 0]
                off = np.degrees(np.arctan2(ax[1], ax[0]))
                diag["jaw_square"].append(
                    abs((off + 90.0) % 180.0 - 90.0))
                diag["grasp_pose"].append(
                    (st.arm.index, st.joints.copy(), st.gap, pc.size,
                     C.classify(pc.size).key))
            elif task.phase == "OPEN":
                key = (st.arm.index, C.classify(pc.size).key)
                here = st.tcp @ pc.hold_offset
                w = worlds.get(key)
                if w is None:
                    w = worlds[key] = bin_world(st.arm.bins[key[1]])
                prev_pose = pc.prev_pose if pc.prev_pose is not None else here
                release(w, pc, here, *_twist(prev_pose, here, dt), t=t)
                pc.picked_by = st.arm.index
                st.picks += 1
                counts["picked"] += 1
                counts[pc.cls.key] += 1
            task.phase_i += 1
            task.k = 0
            task.anchor = st.tcp.copy()
            if task.phase_i >= len(PHASES):
                st.task = None
                st.idle_since = t
                # Start home from wherever letting go left it. If a box
                # turns up first, this is simply abandoned.
                st.home_from = st.tcp.copy()
                st.home_gap = st.gap
                st.home_k = 0


        # --- physics ---------------------------------------------------
        # Every released box is integrated here. A world with nothing
        # awake in it costs nothing, so a bin that filled up twenty
        # seconds ago is not re-solved for the rest of the clip.
        live = rest = 0
        for key, w in worlds.items():
            moving = [b for b in w.bodies if not b.static and not b.asleep]
            rest += sum(1 for b in w.bodies if not b.static and b.asleep)
            live += len(moving)
            if not moving:
                continue
            e0 = w.energy()
            w.advance(dt)
            # As a height, not a fraction. Divided by the weight of what
            # is actually moving, an energy gain *is* a distance: how far
            # this pile's centre of mass rose. That can then be held
            # against the overlap the same frame had to push out of,
            # which is the only thing that can lift it -- a statement
            # about the solver rather than a tolerance someone chose.
            weight = 9810.0 * sum(b.mass for b in moving)
            diag["energy_lift"].append(
                ((w.energy() - e0) / weight, w.max_contact, str(key),
                 round(t, 2)))
            diag["overlap"].append(w.max_depth)

        # --- record ---------------------------------------------------
        snaps = []
        for pc in parcels:
            if pc.t0 > t:
                continue
            if pc.state == "belt":
                pose = pc.belt_pose(t)
            elif pc.state == "held":
                holder = next(s for s in states
                              if s.busy and s.task.parcel is pc)
                pose = holder.tcp @ pc.hold_offset
                # Second difference of the carried box's own path: what
                # the jaws have to hold on to, over and above its weight.
                if pc.prev2 is not None:
                    a = (pose[:3, 3] - 2.0 * pc.prev_pose[:3, 3]
                         + pc.prev2[:3, 3]) / (dt * dt)
                    diag["carry_accel"].append(
                        (float(np.linalg.norm(a)), pc.mass, pc.pid,
                         holder.task.phase, round(t, 2)))
                pc.prev2 = pc.prev_pose
            else:
                pose = pc.body.pose()
                pc.state = "binned" if pc.body.asleep else "falling"
            pc.prev_pose = pose.copy()
            # A held box is squeezed by what the board gives; a box that
            # has been let go springs back, because nothing is pressing
            # on it any more.
            relax(p, pc, jaw_demand(pc, states), dt)
            snaps.append(Snap(pc.pid, pc.cls.key, pose.copy(), pc.state,
                              pc.claimed_by, pc.size, pc.squeeze))

        frames.append(Frame(
            t, [s.joints.copy() for s in states], [s.gap for s in states],
            [s.phase for s in states],
            [s.task.parcel.pid if s.busy else None for s in states],
            [s.tcp.copy() for s in states], snaps, dict(counts),
            {"live": live, "rest": rest}))

        if report and i and i % (fps * 5) == 0:
            report(f"  t={t:5.1f}s  seen {counts['seen']:3d}  "
                   f"picked {counts['picked']:3d}  missed {counts['missed']:3d}")

    # Paired with when its *pile* was last disturbed, not when the box
    # itself was let go: a box that settled ten seconds ago and has just
    # had another one land on it is legitimately moving again.
    diag["awake_at_end"] = []
    for w in worlds.values():
        last = max((b.tag[1] for b in w.bodies if not b.static), default=0.0)
        diag["awake_at_end"] += [
            (b.tag[0], last, R.point_speed(b)) for b in w.bodies
            if not b.static and not b.asleep]
    diag["rest_overlap"] = max((w.deepest_overlap() for w in worlds.values()),
                               default=0.0)
    diag["worlds"] = worlds
    return frames, diag
