#!/usr/bin/env python3
"""Tests for the rigid-body solver, against closed forms rather than eyes.

A physics solver is the easiest thing in a project like this to be wrong
about convincingly: boxes fall, boxes stop, boxes pile up, and it looks
right whether or not any of the numbers are. So none of these compare
against a recorded frame. Each one compares against arithmetic that was
true before the solver existed -- where a body is after a second of free
fall, how high a box rests on a floor, and the exact slope angle at
which Coulomb friction gives up.

Runs under pytest, or standalone with `python3 test_rigid.py`.
"""

from __future__ import annotations

import numpy as np

from sim import rigid as R

UP = np.array([0.0, 0.0, 1.0])
IDENT = np.array([1.0, 0.0, 0.0, 0.0])


def box(half, pos, mass=0.4, quat=IDENT):
    return R.Body(half=np.full(3, half, float) if np.isscalar(half)
                  else np.array(half, float),
                  mass=mass, pos=np.array(pos, float),
                  quat=np.array(quat, float))


def floor_world(**kw) -> R.World:
    w = R.World(**kw)
    w.planes.append(R.Plane(UP.copy(), 0.0))
    return w


def test_free_fall_matches_the_closed_form():
    """z = z0 - g t^2 / 2, to the millimetre, after a full second.

    Semi-implicit Euler with `pos += vel * dt` after the gravity kick
    overshoots by half a step of gravity every step. Over a second at
    240 Hz that is 20 mm -- small enough to look fine on a box falling
    into a bin, and wrong.
    """
    w = R.World()
    b = w.add(box(50.0, (0, 0, 2000.0)))
    for _ in range(60):
        w.advance(1 / 60)
    assert abs(b.pos[2] - (2000.0 - 0.5 * 9810.0)) < 1e-6, b.pos[2]
    assert abs(b.vel[2] + 9810.0) < 1e-6, b.vel[2]


def test_a_box_rests_at_its_own_half_height():
    w = floor_world()
    b = w.add(box(50.0, (0, 0, 400.0)))
    for _ in range(180):
        w.advance(1 / 60)
    # It rests a hair *past* the slop band: that is where the Baumgarte
    # bias exactly cancels one substep of gravity, which is the whole
    # point of leaving a slop band alone in the first place.
    sunk = 50.0 - b.pos[2]
    assert R.SLOP <= sunk <= R.SLOP + 0.05, sunk
    assert b.asleep, "a box on a floor must stop, not hum"


def test_a_stack_does_not_fall_through_itself():
    """The case corner-in-box contact silently gets wrong.

    Two boxes resting face to face have every penetrating corner sitting
    *on* the other's side face rather than strictly inside it, so a
    corner test reports no contact at all and the stack sinks into the
    floor in one piece.
    """
    w = floor_world()
    st = [w.add(box(40.0, (0, 0, 40.0 + i * 81.0))) for i in range(3)]
    for _ in range(240):
        w.advance(1 / 60)
    zs = sorted(b.pos[2] for b in st)
    for i, want in enumerate((40.0, 120.0, 200.0)):
        assert abs(zs[i] - want) < 2.0, zs
    assert all(b.asleep for b in st), [b.pos[2] for b in st]
    assert w.deepest_overlap() <= R.SLOP + 0.25, w.deepest_overlap()


def test_a_box_landing_on_another_box_edge_settles():
    """A box left overhanging the one below it has to stop, not creep.

    The hard case for a stack: the manifold holding it up is asymmetric
    and changes as it tilts, so an under-solved contact tilts it back
    and it rocks. Slowly enough to look like settling, which is the
    problem -- ten millimetres a second reads as "nearly stopped" and is
    not stopping at all.
    """
    w = floor_world()
    low = w.add(box(60.0, (0, 0, 60.0), mass=0.5))
    high = w.add(box(62.0, (100.0, 15.0, 265.0), mass=0.55))
    for _ in range(360):                       # six seconds
        w.advance(1 / 60)
    assert low.asleep and high.asleep, (
        round(R.point_speed(low), 2), round(R.point_speed(high), 2),
        np.round(low.pos, 1), np.round(high.pos, 1))
    assert w.deepest_overlap() <= R.SLOP + 0.35, w.deepest_overlap()


def test_boxes_touching_each_other_all_go_to_sleep():
    """Three boxes side by side, all of them stopped, must all sleep.

    One box on its own always did. Boxes *touching* each other did not,
    and took turns not doing it: each would sleep, be woken by a
    neighbour, and start counting from nothing again, round and round,
    for as long as the clip ran. Nothing moved a millimetre the whole
    time.

    The cause was the order of two things inside a step. The wake test
    asked "is anything touching me moving?" *after* gravity had been
    applied and before the contacts had cancelled it -- and one step of
    gravity at 240 Hz is 41 mm/s, three times the speed this calls
    moving. So every resting box looked fast for the instant the
    question was asked, and woke every sleeping box it was against.

    Dropped a few frames apart, on purpose: boxes that settle on the
    same step all fall asleep together, and with nobody awake there is
    nobody to do the waking. It needs them out of phase, which is what
    arriving one at a time gives you.
    """
    w = floor_world()
    boxes = []
    for i in range(3):
        boxes.append(w.add(box(40.0, (i * 79.0, 0.0, 44.0), mass=0.4)))
        for _ in range(17):                    # out of step with each other
            w.advance(1 / 60)
    for _ in range(300):
        w.advance(1 / 60)
    for b in boxes:
        assert R.point_speed(b) < 1e-6, R.point_speed(b)
    assert all(b.asleep for b in boxes), [b.still for b in boxes]


def test_friction_lets_go_at_exactly_the_coulomb_angle():
    """A box on a slope slides iff tan(theta) > mu, and nowhere else.

    This is the test that caught friction being applied fresh on each
    of the twelve solver iterations, which multiplies the available
    friction by twelve: the box then sat happily at 35 degrees with
    mu = 0.5, an angle it has no business holding.
    """
    mu = 0.5
    critical = np.degrees(np.arctan(mu))          # 26.57 degrees
    for deg in (10.0, 20.0, 26.0, 35.0, 50.0):
        th = np.radians(deg)
        n = np.array([-np.sin(th), 0.0, np.cos(th)])
        w = floor_world(friction=mu)
        w.planes[0] = R.Plane(n, 0.0)
        # The box's own +z must land on the plane normal, or it balances
        # on an edge at twice the slope and topples at every angle.
        rot = np.array([[np.cos(th), 0, -np.sin(th)], [0, 1, 0],
                        [np.sin(th), 0, np.cos(th)]])
        b = w.add(box(50.0, n * 50.0, quat=R.mat_to_quat(rot)))
        start = b.pos.copy()
        for _ in range(180):
            w.advance(1 / 60)
        moved = float(np.linalg.norm(b.pos - start))
        if deg < critical:
            assert moved < 5.0, f"{deg} deg: crept {moved:.1f} mm"
        else:
            assert moved > 1000.0, f"{deg} deg: stuck after {moved:.1f} mm"


def test_energy_never_goes_up():
    """Contact takes energy out. A solver that puts it in explodes.

    Measured against the energy the drop started with, not against
    what is left: once the box has landed, what is left is the few
    joules of its resting height and any ratio to that is noise.

    What remains is the work done lifting a box back out of an
    overlap, which is real and unavoidable -- the box is being raised
    against gravity. The contact impulses themselves add nothing,
    because the bias that does the lifting is a split impulse.
    """
    w = floor_world()
    w.add(box(50.0, (0, 0, 600.0)))
    start = prev = w.energy()
    worst = 0.0
    for _ in range(240):
        w.advance(1 / 60)
        now = w.energy()
        worst = max(worst, (now - prev) / start)
        prev = now
    assert worst < 0.005, f"gained {worst:.4%} of the drop in one frame"
    assert prev < 0.2 * start


def test_static_bodies_are_scenery():
    """A wall must not be pushed over by what lands on it, and must not
    be woken up either -- a woken wall falls to the floor."""
    w = R.World()
    wall = w.add(R.Body(half=np.array([200.0, 200.0, 20.0]),
                        mass=1.0, pos=np.array([0.0, 0.0, 300.0]),
                        quat=IDENT.copy(), static=True))
    b = w.add(box(50.0, (0, 0, 900.0)))
    for _ in range(180):
        w.advance(1 / 60)
    assert np.allclose(wall.pos, (0, 0, 300.0)), wall.pos
    assert abs(b.pos[2] - 370.0) <= R.SLOP + 0.1, b.pos[2]


def test_a_box_dropped_on_a_corner_does_not_land_flat():
    """The thing the old drop could not do. It interpolated to a
    resting pose it had chosen in advance, so a box always ended up
    axis-aligned; here the pose at rest is wherever the contacts leave
    it, and a box dropped tilted stays tilted or topples."""
    w = floor_world()
    th = np.radians(30.0)
    rot = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0],
                    [0, 0, 1.0]])
    tilt = np.radians(18.0)
    rot = rot @ np.array([[np.cos(tilt), 0, np.sin(tilt)], [0, 1, 0],
                          [-np.sin(tilt), 0, np.cos(tilt)]])
    b = w.add(box(50.0, (0, 0, 260.0), quat=R.mat_to_quat(rot)))
    for _ in range(240):
        w.advance(1 / 60)
    yaw = abs(np.degrees(np.arctan2(b.rot()[1, 0], b.rot()[0, 0])))
    assert b.asleep
    # It settles onto a face -- but not the face it started on, and not
    # at the yaw a tidy arrangement would have picked.
    assert abs(float(b.rot()[:, 2] @ UP)) > 0.98 or \
        abs(float(b.rot()[:, 0] @ UP)) > 0.98, b.rot()
    assert 1.0 < yaw < 89.0, yaw


def test_quaternion_round_trip():
    rng = np.random.default_rng(3)
    for _ in range(50):
        q = rng.normal(size=4)
        q /= np.linalg.norm(q)
        m = R.quat_to_mat(q)
        assert np.allclose(m @ m.T, np.eye(3), atol=1e-9)
        back = R.quat_to_mat(R.mat_to_quat(m))
        assert np.allclose(m, back, atol=1e-9), (m, back)


def main() -> int:
    fails = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  [PASS] {name}")
        except AssertionError as e:
            fails += 1
            print(f"  [FAIL] {name}: {e}")
    print(f"  {'ALL TESTS PASSED' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
