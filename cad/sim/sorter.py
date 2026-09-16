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

# ---- how long each part of a pick takes -----------------------------
TRACK_T = 1.30
DESCEND_T = 0.75
CLOSE_T = 0.35
LIFT_T = 1.60
DROP_T = 0.65
OPEN_T = 0.30
RETURN_T = 1.70
PHASES = (("TRACK", TRACK_T), ("DESCEND", DESCEND_T), ("CLOSE", CLOSE_T),
          ("LIFT", LIFT_T), ("DROP", DROP_T), ("OPEN", OPEN_T),
          ("RETURN", RETURN_T))
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
GRAVITY = 9810.0                       # mm/s^2, for the drop into the bin
JAW_MARGIN = 24.0                      # how much wider than the box the jaws open
# Closest two boxes are ever spawned. The jaws open to about 190 mm
# around a 140 mm box, so a box needs that much clear belt behind it or
# the gripper would be closing on its neighbour.
MIN_GAP_X = 300.0


def open_gap(size: float) -> float:
    return size + JAW_MARGIN


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
    yaw: float = 0.0                   # how it happens to be turned
    state: str = "belt"                # belt | held | falling | binned | rejected
    claimed_by: int | None = None
    picked_by: int | None = None
    hold_offset: np.ndarray | None = None
    rest: np.ndarray | None = None     # 4x4, where it finished
    fall_from: np.ndarray | None = None
    fall_t0: float = 0.0
    seen_at: float = -1.0

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
        margin = size / 2.0 + 18.0
        y = float(rng.uniform(-(C.BELT_HALF_W - margin),
                              C.BELT_HALF_W - margin))
        reach = C.BIN_INNER - size / 2.0 - 12.0
        out.append(Parcel(pid, size, y, C.BELT_X0, t,
                          drop_dx=float(rng.uniform(-reach, reach)),
                          drop_dy=float(rng.uniform(-reach, reach)),
                          yaw=float(rng.uniform(-np.pi, np.pi))))
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
    belt_ref = task.parcel.belt_point(t)
    hover = np.array([0.0, 0.0, C.HOVER])
    bump = ARC * np.sin(np.pi * s) ** 2
    ph = task.phase

    if ph == "TRACK":
        # To the intercept, which is a *fixed* point inside this arm's
        # own window -- not to wherever the box happens to be now. The
        # box is still upstream at this moment, and an arm that flies
        # out to meet it there is an arm reaching into the territory of
        # the one before it. Which is exactly what it was doing: the
        # closest two arms ever came was a gripper out past its own
        # window boundary, chasing a box that had not arrived yet.
        pos = _swing(arm, task.anchor[:3, 3], task.meet + hover, e)
        gap = open_gap(size)
    elif ph == "DESCEND":
        # One blend from that fixed hover point onto the moving box. At
        # s = 0 it is the hover point with zero velocity, continuous
        # with the end of TRACK; at s = 1 it is the box itself, and
        # because the ease has zero derivative there, moving at exactly
        # belt speed.
        pos = (1 - e) * (task.meet + hover) + e * belt_ref
        gap = open_gap(size)
    elif ph == "CLOSE":
        pos = belt_ref
        gap = float(K.blend([open_gap(size)], [size], s)[0])
    elif ph == "LIFT":
        pos = _swing(arm, belt_ref, task.bin_pt + hover, e, bump)
        gap = size
    elif ph == "DROP":
        pos = (1 - e) * (task.bin_pt + hover) + e * _drop_pt(task, size)
        gap = size
    elif ph == "OPEN":
        pos = _drop_pt(task, size)
        gap = float(K.blend([size], [open_gap(size)], s)[0])
    else:                                            # RETURN
        pos = _swing(arm, task.anchor[:3, 3], st.park_tcp[:3, 3], e, bump)
        gap = open_gap(size)

    lp = arm.to_local(pos)
    jaw = _jaw_local(arm, lp, _square_weight(ph, s), task.jaw_az)
    return arm.base @ K.target_frame(lp, jaw=jaw), gap


def _drop_pt(task: Task, size: float) -> np.ndarray:
    """Where the jaws let go: somewhere over the bin, not its dead centre.

    A gripper that always releases over the same point drops a tidy
    column. It releases over the bin, and where in the bin is whatever
    the approach happened to leave it -- drawn once, with the box.
    """
    pc = task.parcel
    return task.bin_pt + (pc.drop_dx, pc.drop_dy, 40.0 + size / 2.0)


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
    meet = parcel.belt_point(t + INTERCEPT_T)
    if not (arm.x0 + EDGE <= meet[0] <= arm.x1 - EDGE):
        return False
    if abs(meet[1]) > C.BELT_HALF_W:
        return False
    return arm.can_reach(meet) and arm.can_reach(meet + (0, 0, C.HOVER))


# ---------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------
BIN_FLOOR = 55.0
SENSOR_X = C.BELT_X0 + 260.0           # where a box is first seen and sized
REJECT_AT = C.BELT_X1 - 70.0
REJECT_PT = np.array([C.BELT_X1 + 140.0, 0.0, 0.0])
CHUTE_FLOOR = 40.0                     # top of the reject chute's own slab


@dataclass
class Snap:
    pid: int
    key: str
    pose: np.ndarray
    state: str
    claimed_by: int | None
    size: float = 0.0


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


def _yaw_matrix(a: float) -> np.ndarray:
    m = np.eye(4)
    c, sn = np.cos(a), np.sin(a)
    m[:3, :3] = ((c, -sn, 0.0), (sn, c, 0.0), (0.0, 0.0, 1.0))
    return m


def _support(settled: list, x: float, y: float, size: float,
             floor: float) -> float:
    """The height a box dropped at (x, y) will come to rest on.

    The floor of the bin, or the top of whatever is already lying there
    under it. Footprints are compared as squares, which is close enough
    for boxes turned a few degrees and a great deal simpler than asking
    a physics engine -- what this has to get right is that a box lands
    *on* the pile rather than inside it, and that it lands where it was
    dropped rather than where a tidy arrangement wanted it.
    """
    top = floor
    for ox, oy, osize, otop in settled:
        if (abs(x - ox) < (size + osize) / 2.0
                and abs(y - oy) < (size + osize) / 2.0):
            top = max(top, otop)
    return top


def _land(pc: Parcel, at: np.ndarray, settled: list, floor: float):
    """Register where this box will come to rest, and what it rests on."""
    x, y = float(at[0]), float(at[1])
    base = _support(settled, x, y, pc.size, floor)
    settled.append((x, y, pc.size, base + pc.size))
    m = _yaw_matrix(pc.yaw)
    m[:3, 3] = (x, y, base + pc.size / 2.0)
    return m


def _fall(pc: Parcel, t: float):
    """Free fall from where it was let go to where it lands."""
    z0, z1 = pc.fall_from[2, 3], pc.rest[2, 3]
    drop = max(z0 - z1, 0.0)
    tf = float(np.sqrt(2.0 * drop / GRAVITY)) if drop > 0 else 0.0
    s = 1.0 if tf <= 0 else min(1.0, (t - pc.fall_t0) / tf)
    # Orientation swings from however the gripper held it to however it
    # ends up lying, over the same fall.
    m = pc.rest.copy()
    m[:3, 3] = pc.fall_from[:3, 3] * (1 - s) + pc.rest[:3, 3] * s
    m[2, 3] = z0 - drop * s * s
    if s < 1.0:
        blend = s * s
        m[:3, :3] = (pc.fall_from[:3, :3] * (1 - blend)
                     + pc.rest[:3, :3] * blend)
    return m, s >= 1.0


def run(p: ArmParams, seconds: float = 26.0, fps: int = 30, seed: int = 11,
        mean_gap: float = 1.4, lead: float = 30.0, report=print):
    """Simulate the whole cell, frame by frame.

    `lead` seeds the belt with boxes that notionally arrived before the
    clip starts -- a whole transit time of them, so the line opens
    already running rather than waiting half a minute for the first box
    to travel down from the infeed.
    """
    parcels = spawn_plan(seconds, seed, mean_gap, lead=-lead)
    steps = {name: max(1, int(round(d * fps))) for name, d in PHASES}
    states = []
    for a in C.ARMS:
        local_pt = a.to_local(a.park_point)
        goal = K.target_frame(local_pt)           # natural wrist, as TRACK starts
        q, pe, ae = K.solve_ik(p, goal, K.seed_for(local_pt, p))
        if pe > 0.2 or ae > 0.2:
            raise RuntimeError(f"{a.name} cannot hold its park point "
                               f"({pe:.2f} mm, {ae:.2f} deg)")
        states.append(ArmState(a, q.copy(), open_gap(C.CLASSES[-1].hi),
                               q.copy(), a.base @ K.tcp(p, q)))
    for st in states:
        st.tcp = st.park_tcp.copy()

    fill: dict = {}          # bin -> boxes already lying in it
    diag = {"ik_pos": [], "ik_ang": [], "grasp_rel": [], "track_err": [],
            "tcp_step": [], "claims": [], "zone_ok": [], "jaw_floor": [],
            "grasps": [], "jaw_square": [], "grasp_pose": [],
            "both_busy": []}
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

        # --- claiming: only an idle arm, only its own territory -------
        # Recomputed inside the loop, not snapshotted before it: two
        # neighbours claiming in the same frame would both have seen an
        # idle neighbour and both gone.
        for st in states:
            if st.busy:
                continue
            busy = {s2.arm.index for s2 in states if s2.busy}
            # Interlock: an arm whose neighbour is mid-pick stays put.
            # Their reaches overlap now that each works the full width,
            # so nothing about the territory rules keeps them apart in
            # *time* -- this does. Non-adjacent arms are unaffected, so
            # three of the five can still be working at once.
            if any(n.index in busy for n in C.neighbours(st.arm)):
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
                           anchor=st.tcp.copy())
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
            else:
                # Hold whatever joints the arm finished RETURN in. They
                # already hold the park pose; snapping to the stored park
                # solution instead would step the wrist a hundred degrees
                # to reach the same point a different way.
                gap = st.gap
            st.gap = gap
            st.tcp = st.arm.to_world(K.tcp(p, st.joints))

            v = (st.tcp[:3, 3] - prev[k]) / dt
            diag["tcp_step"].append(float(np.linalg.norm(st.tcp[:3, 3] - prev[k])))
            if st.busy and st.task.phase == "CLOSE":
                diag["grasp_rel"].append(
                    float(np.linalg.norm(v - (C.BELT_SPEED, 0.0, 0.0))))
                diag["track_err"].append(float(np.linalg.norm(
                    st.tcp[:3, 3] - st.task.parcel.belt_point(t))))
                diag["jaw_floor"].append(
                    float(st.tcp[2, 3] - p.finger_thk / 2.0 - C.BELT_TOP))
            prev[k] = st.tcp[:3, 3].copy()

        # --- boxes nobody took run off the end ------------------------
        for pc in parcels:
            if (pc.state == "belt" and pc.t0 <= t and pc.claimed_by is None
                    and pc.belt_point(t)[0] >= REJECT_AT):
                pc.state = "falling"
                pc.fall_from = pc.belt_pose(t)
                pc.fall_t0 = t
                pc.rest = _land(pc, REJECT_PT + (pc.drop_dx, pc.drop_dy, 0.0),
                                fill.setdefault("R", []), CHUTE_FLOOR)
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
                pc.state = "falling"
                pc.fall_from = st.tcp @ pc.hold_offset
                pc.fall_t0 = t
                pc.rest = _land(pc, pc.fall_from[:3, 3],
                                fill.setdefault(key, []), BIN_FLOOR)
                pc.picked_by = st.arm.index
                st.picks += 1
                counts["picked"] += 1
                counts[pc.cls.key] += 1
            task.phase_i += 1
            task.k = 0
            task.anchor = st.tcp.copy()
            if task.phase_i >= len(PHASES):
                st.task = None

        for st in states:
            for n in C.neighbours(st.arm):
                if st.busy and states[n.index].busy:
                    diag["both_busy"].append((round(t, 2), st.arm.name, n.name))

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
            elif pc.state == "falling":
                pose, landed = _fall(pc, t)
                if landed:
                    pc.state = "binned"
            else:
                pose = pc.rest
            snaps.append(Snap(pc.pid, pc.cls.key, pose.copy(), pc.state,
                              pc.claimed_by, pc.size))

        frames.append(Frame(
            t, [s.joints.copy() for s in states], [s.gap for s in states],
            [s.phase for s in states],
            [s.task.parcel.pid if s.busy else None for s in states],
            [s.tcp.copy() for s in states], snaps, dict(counts)))

        if report and i and i % (fps * 5) == 0:
            report(f"  t={t:5.1f}s  seen {counts['seen']:3d}  "
                   f"picked {counts['picked']:3d}  missed {counts['missed']:3d}")

    return frames, diag
