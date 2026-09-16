"""A small rigid-body solver: boxes, gravity, contact, friction.

The drop into a bin used to work out where a box would end up and then
interpolate to it, which is animation wearing physics as a costume: the
landing pose was an input. Here it is an output. A box is released with
whatever position, orientation and velocity the gripper had, and after
that nothing decides anything -- gravity accelerates it, contacts push
back, friction resists sliding, and where it comes to rest is wherever
the integrator leaves it.

Impulse-based, in the usual sequential form:

* **Semi-implicit Euler** at a fixed substep, because it is stable for
  contact and conserves nothing it should not, integrated
  trapezoidally in position so that free fall is exact to the micron.
* **Contacts** between an oriented box and a plane by testing corners,
  and between two boxes by the separating-axis test with face clipping.
  Corner-in-box alone is not enough and fails in exactly the case that
  matters here: two boxes resting face to face have every penetrating
  corner sitting *on* the other's side face rather than strictly inside
  it, so no contact is ever reported and a stack falls straight through
  itself.
* **Sequential impulses**, with the accumulated normal impulse clamped
  non-negative, and **warm-started** from the previous step. Solving
  from zero every step leaves twelve iterations of Gauss-Seidel short
  of the answer, which a box resting flat hides and a box resting on
  another's edge does not: it rocks, slowly, for ever.
* **Coulomb friction clamped on the accumulated tangential impulse**,
  not on each iteration's contribution. Clamping per iteration lets
  twelve iterations apply twelve times the friction the surface has,
  and a box then sits happily on a slope far past the angle it should
  slide down.
* **A split-impulse Baumgarte bias** to push penetration out. Applied
  to pseudo-velocities that move the bodies for one step and are then
  thrown away, so separating two overlapping boxes cannot leave either
  of them moving faster than it was. In the velocity solve it would
  leave real velocity behind after the overlap was gone -- energy the
  collision never had.
* **Sleeping**, because a pile that never quite stops is a pile that
  jitters for the whole clip and never satisfies "comes to rest".
* **Static bodies** for the bin walls, rather than half-spaces. An
  infinite plane per wall would make "the box stayed in its bin" true
  by construction -- there would be nowhere else for it to go. Four
  finite slabs let a box leave over the rim if the physics sends it
  there, so the check measures something.

Units are millimetres, kilograms and seconds throughout, so forces are
kg mm/s^2 and inertias kg mm^2. Nothing here is in SI metres; mixing the
two is the classic way to get a simulation that looks like syrup.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

GRAVITY = np.array([0.0, 0.0, -9810.0])   # mm/s^2
SLOP = 0.35                                # mm of penetration left alone
BAUMGARTE = 0.22
# How fast penetration may be pushed out, so that a deep impact is
# recovered over a few frames rather than in one visible jump.
BIAS_MAX = 400.0                           # mm/s
# How far apart two surfaces can be and still be given a contact. A
# contact that only exists once the surfaces already overlap is a
# contact that arrives too late: the box lands, the step ends with it
# 7 mm inside the floor, and the only way out is to push it back --
# which is work against gravity, and the one route by which energy ever
# entered this solver. A speculative contact is allowed to slow the box
# to exactly the gap it has left, so the gap closes and nothing
# overlaps. It covers approach speeds up to MARGIN / substep, which at
# 240 Hz is 4.8 m/s -- comfortably past anything dropped from an arm.
MARGIN = 20.0                              # mm
# One sleep threshold, on the speed of the fastest point on the body,
# rather than separate caps on |v| and |omega|. A cap on |omega| alone
# means different things for different boxes -- 0.25 rad/s moves a 48 mm
# box's corner at 10 mm/s and a 140 mm box's at 30 mm/s -- so the same
# number reads as "stopped" for one and "still going" for the other.
SLEEP_SPEED = 14.0                         # mm/s
SLEEP_FRAMES = 12


def quat_to_mat(q: np.ndarray) -> np.ndarray:
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])


def mat_to_quat(m: np.ndarray) -> np.ndarray:
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        q = np.array([0.25 * s, (m[2, 1] - m[1, 2]) / s,
                      (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s])
    else:
        i = int(np.argmax(np.diag(m)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = np.sqrt(m[i, i] - m[j, j] - m[k, k] + 1.0) * 2
        q = np.zeros(4)
        q[0] = (m[k, j] - m[j, k]) / s
        q[i + 1] = 0.25 * s
        q[j + 1] = (m[j, i] + m[i, j]) / s
        q[k + 1] = (m[k, i] + m[i, k]) / s
    return q / np.linalg.norm(q)


def _qmul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    ])


_CORNERS = np.array([[sx, sy, sz] for sx in (-1, 1)
                     for sy in (-1, 1) for sz in (-1, 1)], float)


@dataclass
class Body:
    """An oriented box with mass. `tag` is whatever the caller wants back."""
    half: np.ndarray
    mass: float
    pos: np.ndarray
    quat: np.ndarray
    vel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    omega: np.ndarray = field(default_factory=lambda: np.zeros(3))
    # Pseudo-velocities: they move the body but are thrown away at the
    # end of the step, so pushing penetration out costs nothing.
    pvel: np.ndarray = field(default_factory=lambda: np.zeros(3))
    pomega: np.ndarray = field(default_factory=lambda: np.zeros(3))
    tag: object = None
    group: object = None                  # only bodies in a group collide
    still: int = 0
    static: bool = False                  # scenery: infinite mass, never wakes
    pen: float = 0.0                      # deepest overlap it is in, this step

    @property
    def inv_mass(self) -> float:
        return 0.0 if self.asleep else 1.0 / self.mass

    @property
    def inv_inertia_body(self) -> np.ndarray:
        w, h, d = 2.0 * self.half
        k = self.mass / 12.0
        return 1.0 / np.array([k * (h * h + d * d), k * (w * w + d * d),
                               k * (w * w + h * h)])

    @property
    def asleep(self) -> bool:
        return self.static or self.still >= SLEEP_FRAMES

    def rot(self) -> np.ndarray:
        return quat_to_mat(self.quat)

    def inv_inertia_world(self) -> np.ndarray:
        if self.asleep:
            return np.zeros((3, 3))
        r = self.rot()
        return r @ np.diag(self.inv_inertia_body) @ r.T

    def corners(self) -> np.ndarray:
        return self.pos + (_CORNERS * self.half) @ self.rot().T

    def pose(self) -> np.ndarray:
        m = np.eye(4)
        m[:3, :3] = self.rot()
        m[:3, 3] = self.pos
        return m

    def energy(self, floor: float = 0.0) -> float:
        lin = 0.5 * self.mass * float(self.vel @ self.vel)
        r = self.rot()
        inertia = r @ np.diag(1.0 / self.inv_inertia_body) @ r.T
        rot = 0.5 * float(self.omega @ inertia @ self.omega)
        pot = self.mass * 9810.0 * (self.pos[2] - floor)
        return lin + rot + pot


def point_speed(body: "Body") -> float:
    """How fast the fastest point on the body is moving."""
    return (float(np.linalg.norm(body.vel))
            + float(np.linalg.norm(body.omega))
            * float(np.linalg.norm(body.half)))


def _fast(body: "Body") -> bool:
    return point_speed(body) > SLEEP_SPEED


@dataclass
class Plane:
    """A half-space: points with `n . x < d` are inside the material."""
    normal: np.ndarray
    offset: float
    group: object = None


def _clip(poly: list, normal: np.ndarray, offset: float) -> list:
    """Sutherland-Hodgman: keep the part of `poly` with n.x <= offset."""
    out = []
    for i, cur in enumerate(poly):
        prv = poly[i - 1]
        dc = float(normal @ cur) - offset
        dp = float(normal @ prv) - offset
        if dp <= 0:
            out.append(prv)
        if (dp > 0) != (dc > 0):
            out.append(prv + (cur - prv) * (dp / (dp - dc)))
    return out


def _face(body: "Body", axis: np.ndarray) -> tuple:
    """The face of `body` whose outward normal is closest to `axis`."""
    r = body.rot()
    dots = axis @ r
    i = int(np.argmax(np.abs(dots)))
    sgn = 1.0 if dots[i] >= 0 else -1.0
    n = sgn * r[:, i]
    centre = body.pos + n * body.half[i]
    u, v = (i + 1) % 3, (i + 2) % 3
    du, dv = r[:, u] * body.half[u], r[:, v] * body.half[v]
    quad = [centre - du - dv, centre + du - dv,
            centre + du + dv, centre - du + dv]
    return n, centre, quad, (r[:, u], body.half[u], r[:, v], body.half[v])


def box_box(a: "Body", b: "Body") -> list:
    """Contacts between two oriented boxes: (point, normal, depth).

    Separating-axis test over all fifteen candidate axes, then a clipped
    manifold on the face case. The normal points from `b` toward `a`.

    `depth` is signed: negative means the surfaces are still that far
    apart. Those are speculative contacts -- see `MARGIN`.
    """
    ra, rb = a.rot(), b.rot()
    t = a.pos - b.pos
    axes = [ra[:, i] for i in range(3)] + [rb[:, i] for i in range(3)]
    axes += [np.cross(ra[:, i], rb[:, j]) for i in range(3) for j in range(3)]
    best, best_depth, best_kind = None, np.inf, -1
    for k, ax in enumerate(axes):
        n = float(np.linalg.norm(ax))
        if n < 1e-6:
            continue
        ax = ax / n
        ea = float(np.abs(ax @ ra) @ a.half)
        eb = float(np.abs(ax @ rb) @ b.half)
        overlap = ea + eb - abs(float(ax @ t))
        if overlap <= -MARGIN:
            return []                        # too far apart to matter yet
        # Face axes win ties: an edge-edge answer for what is really a
        # face contact gives one point where there should be four.
        biased = overlap - (1e-3 if k < 6 else 0.0)
        if biased < best_depth:
            best, best_depth, best_kind = (ax if float(ax @ t) >= 0
                                           else -ax), biased, k
    if best is None:
        return []
    depth = best_depth + (1e-3 if best_kind < 6 else 0.0)

    if best_kind >= 6:                       # edge against edge: one point
        return [(0.5 * (a.pos + b.pos), best, depth)]

    # Face case: clip the incident face against the reference face's sides
    if best_kind < 3:
        ref, inc, normal = a, b, -best       # reference face lives on a
    else:
        ref, inc, normal = b, a, best
    rn, rc, _, (u, hu, v, hv) = _face(ref, normal)
    _, _, quad, _ = _face(inc, -rn)
    poly = quad
    for axis, half in ((u, hu), (v, hv)):
        poly = _clip(poly, axis, float(axis @ rc) + half)
        poly = _clip(poly, -axis, -float(axis @ rc) + half)
        if not poly:
            return []
    out = []
    plane_d = float(rn @ rc)
    for p in poly:
        pen = plane_d - float(rn @ p)
        if pen > -MARGIN:
            out.append((p, best, pen))
    return out or [(rc, best, depth)]


@dataclass
class Contact:
    a: Body
    b: Body | None                        # None means the plane is static
    normal: np.ndarray                    # points from b toward a
    point: np.ndarray
    depth: float
    jn: float = 0.0
    jt: np.ndarray = field(default_factory=lambda: np.zeros(3))
    pn: float = 0.0                       # the positional pass's own impulse

    def key(self) -> tuple:
        """Identity of this contact, stable from one step to the next.

        The contact point in `a`'s own frame, quantised -- so a contact
        that is still the same corner on the same pair of bodies is
        recognised as such even though both have moved. That is what
        lets the accumulated impulse be carried over; see
        `World._warm_start`.
        """
        local = self.a.rot().T @ (self.point - self.a.pos)
        return (id(self.a), id(self.b),
                int(round(local[0] / 3.0)), int(round(local[1] / 3.0)),
                int(round(local[2] / 3.0)))


class World:
    def __init__(self, restitution=0.05, friction=0.55, iterations=12,
                 pos_iterations=4):
        self.bodies: list[Body] = []
        self.planes: list[Plane] = []
        self.restitution = restitution
        self.friction = friction
        self.iterations = iterations
        self.pos_iterations = pos_iterations
        # Deepest overlap seen since the last `advance`, taken from the
        # contacts the step already generated. Asking `deepest_overlap`
        # once a frame instead costs a whole extra broad and narrow
        # phase over every body in the world, sleeping ones included --
        # which is more work than the step itself.
        self.max_depth = 0.0
        # Last step's accumulated impulses, keyed by `Contact.key`.
        self.cache: dict = {}

    def add(self, body: Body) -> Body:
        self.bodies.append(body)
        return body

    # -- contact generation ------------------------------------------
    def _plane_contacts(self, out: list) -> None:
        for body in self.bodies:
            if body.asleep:
                continue
            cs = body.corners()
            for pl in self.planes:
                if pl.group is not None and pl.group != body.group:
                    continue
                depth = pl.offset - cs @ pl.normal
                for i in np.nonzero(depth > -MARGIN)[0]:
                    out.append(Contact(body, None, pl.normal.copy(),
                                       cs[i].copy(), float(depth[i])))


    def _body_contacts(self, out: list) -> None:
        n = len(self.bodies)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = self.bodies[i], self.bodies[j]
                if a.group != b.group or (a.asleep and b.asleep):
                    continue
                reach = (float(np.linalg.norm(a.half))
                         + float(np.linalg.norm(b.half)) + MARGIN)
                if np.linalg.norm(a.pos - b.pos) > reach:
                    continue
                for point, normal, depth in box_box(a, b):
                    out.append(Contact(a, b, normal, point, depth))

    # -- solving -----------------------------------------------------
    def _apply(self, c: "Contact", imp: np.ndarray) -> None:
        a, b = c.a, c.b
        a.vel = a.vel + imp * a.inv_mass
        a.omega = a.omega + a.inv_inertia_world() @ np.cross(c.point - a.pos,
                                                             imp)
        if b is not None:
            b.vel = b.vel - imp * b.inv_mass
            b.omega = b.omega - b.inv_inertia_world() @ np.cross(
                c.point - b.pos, imp)

    def _warm_start(self, contacts: list) -> None:
        """Start each contact from the impulse it needed last step.

        Without this every step solves from zero, and twelve iterations
        of Gauss-Seidel do not get all the way there. A box resting flat
        hides it -- the answer is nearly the same every step, so the
        error is a constant sag. A box resting on the *edge* of another
        does not: the manifold that supports it changes as it tilts, the
        under-solved answer tilts it back, and it rocks. One did, in a
        bin, for fourteen seconds, at ten millimetres a second, which is
        slow enough to look like settling and never was.

        Carrying the impulse over is not a nudge toward the answer, it
        *is* the previous answer, and a resting stack's answer barely
        changes. It costs one dictionary lookup per contact.

        Only for contacts that are touching, though -- see below.
        """
        fresh = {}
        for c in contacts:
            # Only contacts that are actually touching. A speculative
            # contact is a prediction about a gap, and warm-starting a
            # prediction hands two bodies that are no longer in contact
            # the impulse they needed when they were -- a push out of
            # nothing. That was the last way energy was getting in: one
            # frame put 2.2 mm of lift into a chute whose deepest
            # overlap that frame was 0.07 mm.
            if c.depth <= -SLOP:
                continue
            prev = self.cache.get(c.key())
            if prev is not None:
                c.jn, c.jt = prev[0], prev[1].copy()
                self._apply(c, c.jn * c.normal + c.jt)
            fresh[c.key()] = c
        self._fresh = fresh

    def _solve(self, contacts: list, dt: float) -> None:
        for _ in range(self.iterations):
            for c in contacts:
                a, b = c.a, c.b
                ra = c.point - a.pos
                ia = a.inv_inertia_world()
                if b is None:
                    rel = a.vel + np.cross(a.omega, ra)
                    inv_m = a.inv_mass
                    ang = np.cross(ia @ np.cross(ra, c.normal), ra)
                else:
                    rb = c.point - b.pos
                    ib = b.inv_inertia_world()
                    rel = (a.vel + np.cross(a.omega, ra)
                           - b.vel - np.cross(b.omega, rb))
                    inv_m = a.inv_mass + b.inv_mass
                    ang = (np.cross(ia @ np.cross(ra, c.normal), ra)
                           + np.cross(ib @ np.cross(rb, c.normal), rb))
                vn = float(rel @ c.normal)
                k = inv_m + float(ang @ c.normal)
                if k <= 0:
                    continue
                # No penetration bias here -- see `_push`. A bias in the
                # velocity solve leaves real velocity behind after the
                # overlap is gone, which is energy the collision never
                # had, and two boxes that land wedged are then squeezed
                # apart a little harder every step for ever.
                #
                # The target is zero closing speed where the surfaces
                # already touch, and *exactly enough to close the
                # remaining gap* where they do not. That is what stops a
                # falling box before it is inside the floor rather than
                # after.
                target = min(0.0, c.depth / dt)
                rest = -self.restitution * vn if vn < -220.0 else 0.0
                dj = (target - vn + rest) / k
                total = max(0.0, c.jn + dj)
                dj, c.jn = total - c.jn, total
                imp = dj * c.normal
                a.vel = a.vel + imp * a.inv_mass
                a.omega = a.omega + ia @ np.cross(ra, imp)
                if b is not None:
                    b.vel = b.vel - imp * b.inv_mass
                    b.omega = b.omega - ib @ np.cross(rb, imp)

                # Coulomb friction, in the tangent plane. The clamp is on
                # the *accumulated* tangential impulse: clamping each
                # iteration separately multiplies the available friction
                # by the iteration count.
                if c.jn <= 0:
                    continue
                if b is None:
                    rel = a.vel + np.cross(a.omega, ra)
                else:
                    rel = (a.vel + np.cross(a.omega, ra)
                           - b.vel - np.cross(b.omega, rb))
                tang = rel - (rel @ c.normal) * c.normal
                tn = float(np.linalg.norm(tang))
                if tn < 1e-9:
                    continue
                td = tang / tn
                if b is None:
                    kt = a.inv_mass + float(
                        np.cross(ia @ np.cross(ra, td), ra) @ td)
                else:
                    kt = inv_m + float(
                        (np.cross(ia @ np.cross(ra, td), ra)
                         + np.cross(ib @ np.cross(rb, td), rb)) @ td)
                if kt <= 0:
                    continue
                want = c.jt + (-tn / kt) * td
                lim = self.friction * c.jn
                mag = float(np.linalg.norm(want))
                if mag > lim:
                    want = want * (lim / mag)
                imp, c.jt = want - c.jt, want
                a.vel = a.vel + imp * a.inv_mass
                a.omega = a.omega + ia @ np.cross(ra, imp)
                if b is not None:
                    b.vel = b.vel - imp * b.inv_mass
                    b.omega = b.omega - ib @ np.cross(rb, imp)

    def _push(self, contacts: list, dt: float) -> None:
        """Push penetration out with pseudo-velocities.

        Same contacts, same effective masses, but the impulses land in
        `pvel`/`pomega`, which move the bodies this step and are then
        discarded. Split this way, separating two overlapping boxes
        cannot make either of them faster.
        """
        for _ in range(self.pos_iterations):
            for c in contacts:
                a, b = c.a, c.b
                bias = min(BAUMGARTE * max(0.0, c.depth - SLOP) / dt,
                           BIAS_MAX)
                if bias <= 0.0 and c.pn <= 0.0:
                    continue
                ra = c.point - a.pos
                ia = a.inv_inertia_world()
                if b is None:
                    rel = a.pvel + np.cross(a.pomega, ra)
                    inv_m = a.inv_mass
                    ang = np.cross(ia @ np.cross(ra, c.normal), ra)
                else:
                    rb = c.point - b.pos
                    ib = b.inv_inertia_world()
                    rel = (a.pvel + np.cross(a.pomega, ra)
                           - b.pvel - np.cross(b.pomega, rb))
                    inv_m = a.inv_mass + b.inv_mass
                    ang = (np.cross(ia @ np.cross(ra, c.normal), ra)
                           + np.cross(ib @ np.cross(rb, c.normal), rb))
                k = inv_m + float(ang @ c.normal)
                if k <= 0:
                    continue
                dj = (bias - float(rel @ c.normal)) / k
                total = max(0.0, c.pn + dj)
                dj, c.pn = total - c.pn, total
                imp = dj * c.normal
                a.pvel = a.pvel + imp * a.inv_mass
                a.pomega = a.pomega + ia @ np.cross(ra, imp)
                if b is not None:
                    b.pvel = b.pvel - imp * b.inv_mass
                    b.pomega = b.pomega - ib @ np.cross(rb, imp)

    def step(self, dt: float) -> None:
        # Snapshot *every* body, not just the awake ones: the contact pass
        # below can wake a sleeper mid-step, and it then arrives at the
        # integrator wanting a velocity it never recorded.
        before = {id(b): b.vel.copy() for b in self.bodies}

        contacts: list[Contact] = []
        self._plane_contacts(contacts)
        self._body_contacts(contacts)
        # Wake a sleeping body only when something moving lands on it.
        # Resetting the counter on every contact means a box resting on
        # the floor is woken by the floor, every step, for ever.
        #
        # Asked *before* gravity is applied, and that is the whole of
        # it. One step of gravity is 41 mm/s at 240 Hz, three times the
        # speed this calls moving, so after the kick every awake body
        # resting quietly on the floor looks fast -- and wakes every
        # sleeping box it happens to be touching. Four boxes in a chute
        # then take turns: each sleeps, is woken by a neighbour that has
        # merely been dropped on by gravity, and starts counting again.
        # Nothing moves a millimetre and nothing ever settles.
        for c in contacts:
            if c.b is None:
                continue
            if c.a.asleep and not c.a.static and not c.b.asleep and _fast(c.b):
                c.a.still = 0
            if c.b.asleep and not c.b.static and not c.a.asleep and _fast(c.a):
                c.b.still = 0

        # Gravity after the wake test, so a body woken by it still gets
        # its kick this step rather than next.
        for body in self.bodies:
            if body.asleep:
                continue
            body.vel = body.vel + GRAVITY * dt
        self.max_depth = max(
            [self.max_depth]
            + [c.depth for c in contacts
               if c.b is None or not (c.a.static or c.b.static)])
        for body in self.bodies:
            body.pen = 0.0
        for c in contacts:
            c.a.pen = max(c.a.pen, c.depth)
            if c.b is not None:
                c.b.pen = max(c.b.pen, c.depth)
        self._warm_start(contacts)
        self._solve(contacts, dt)
        self._push(contacts, dt)
        self.cache = {k: (c.jn, c.jt) for k, c in self._fresh.items()}

        for body in self.bodies:
            if body.asleep:
                continue
            # Trapezoidal in position: with constant acceleration this
            # is exact, where `pos += vel * dt` after the gravity kick
            # overshoots by half a step of gravity every step -- 20 mm
            # over a second at 240 Hz, which looks fine on a box falling
            # into a bin and is wrong.
            body.pos = (body.pos + 0.5 * (before[id(body)] + body.vel) * dt
                        + body.pvel * dt)
            w = body.omega + body.pomega
            body.quat = body.quat + 0.5 * dt * _qmul(
                np.array([0.0, w[0], w[1], w[2]]), body.quat)
            body.quat /= np.linalg.norm(body.quat)
            body.pvel = np.zeros(3)
            body.pomega = np.zeros(3)
            # Settled means two things, and it has to mean both: not
            # moving, and not wedged inside anything. Without the second
            # a body falls asleep mid-correction and the overlap is
            # frozen in for the rest of the clip. Testing the corrective
            # pass's own pseudo-velocity instead does not work: four
            # contacts under one box ask for four slightly different
            # separations, which no rigid body can satisfy at once, so
            # that residual never goes to zero and nothing ever sleeps.
            if point_speed(body) < SLEEP_SPEED and body.pen <= SLOP + 0.5:
                body.still += 1
            else:
                body.still = 0
            if body.asleep:
                body.vel[:] = 0.0
                body.omega[:] = 0.0

    def advance(self, dt: float, substep: float = 1.0 / 240.0) -> None:
        self.max_depth = 0.0
        n = max(1, int(np.ceil(dt / substep)))
        h = dt / n
        for _ in range(n):
            self.step(h)

    def energy(self, floor: float = 0.0) -> float:
        return sum(b.energy(floor) for b in self.bodies if not b.static)

    def deepest_overlap(self) -> float:
        out: list[Contact] = []
        awake = [b.still for b in self.bodies]
        for b in self.bodies:
            if not b.static:
                b.still = 0
        self._plane_contacts(out)
        self._body_contacts(out)
        for b, s in zip(self.bodies, awake):
            b.still = s
        # A box resting against scenery is not overlapping it: only report
        # how far two things that can both move are inside one another.
        return max((c.depth for c in out
                    if c.b is None or not (c.a.static or c.b.static)),
                   default=0.0)  # depth <= 0 means a gap, not an overlap
