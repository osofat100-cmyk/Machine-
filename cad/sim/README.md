# `sim/` — driving the model and drawing it

Renders the arm running a pick-and-place cycle to video. Entry point is
[`../simulate.py`](../simulate.py).

```bash
cd cad
python3 simulate.py                  # one arm, pick and place -> build/machine.mp4
python3 simulate_cell.py             # five arms on a conveyor -> build/cell.mp4
python3 simulate.py --check-only     # solve and check, render nothing
```

## What is actually on screen

The arm is the CAD model. Not a stand-in, not a re-model: the same
thirteen solids `robot_arm/parts.py` exports to STEP, placed by
`robot_arm/assembly.py`'s own `build_assembly`, at poses
`robot_arm/assembly.py`'s own `joint_frames` resolves. If the STEP file
is wrong, the video is wrong in the same way and at the same joint.

The floor, the two fixtures and the orange block are scenery. They are
boxes generated here, and they are the only things in frame that are not
CAD.

## Modules

| file | what it does |
|---|---|
| `kinematics.py` | tool-centre point, damped-least-squares IK, quintic blending |
| `program.py` | the single-arm motion program, one solved state per frame |
| `cell.py` | the five-arm conveyor layout: territory, reach, turret travel |
| `sorter.py` | boxes on the belt, the dispatcher, conveyor tracking |
| `rigid.py` | the rigid-body solver: contact, friction, sleeping |
| `cellscene.py` | belt, bins, chute, zone markings -- scenery, not CAD |
| `scene.py` | tessellates the thirteen prototypes once; re-places them per frame |
| `raster.py` | z-buffered software rasteriser, and camera fitting |
| `render.py` | shading, ground shadow, static/dynamic compositing |
| `hud.py`, `hud_cell.py` | the telemetry overlays |

## Three decisions worth explaining

**The placements are read out of the assembly, not copied.** `assembly.py`
says driving the pose "is a matter of changing `ArmParams.joints` — no
geometry is rebuilt, only re-placed", so that is what happens.
`scene.placements` calls the real `build_assembly` with the thirteen solids
swapped for unit cubes, purely to read back each instance's `Location`,
then moves cached triangles by those transforms. Rebuilding the solids
 per frame would cost 1.3 s each; more to the point, a re-implementation of
the chain could drift from the one that makes the STEP file, and this one
cannot. `test_simulate.py` compares all nineteen transforms against the
real assembly exactly.

**Z-buffer, not depth sort.** A painter's algorithm gets self-overlap
wrong, and an arm folding back over itself is nothing but self-overlap.
Backfaces are *not* culled: a tessellation that has been through boolean
cuts can carry inconsistently wound faces, so the shading normal is
turned toward the camera instead, which cannot punch holes in a part.

**The camera is fitted, not placed.** Every vertex the arm visits across
the whole program is collected and the camera distance bisected until all
of it lands inside the frame. Framing a robot by eye works right up until
the one pose you were not looking at.

## The cell: five arms, one belt

`cell.py` decides territory and `sorter.py` enforces it. An arm may take
a box only if all three hold: the box's centre is on that arm's half of
the belt **width**, the point where the tool would touch down lands
inside that arm's stretch of belt **length**, and that point is inside
the annulus the arm can actually reach. Windows on a side are 520 mm
apart; windows on opposite sides are offset by 450 mm *and* separated in
y. A box its owner is too busy for stays on the belt for the next arm on
that side.

Three numbers in that layout are derived rather than chosen, and each
one was a bug first:

**The base yaw.** Every arm is bolted down turned about 93 degrees off
the belt. The turret has to swing from the belt in front of it to the
bins behind it -- nearly half a turn -- and square to the belt that
swing straddles J1's stop. The solver clips, the tool lags its target by
tens of millimetres, and the grasp misses: on screen, a robot that just
fumbles. `cell.turret_plan` measures the arc the layout actually spans
and turns the base to centre it, which leaves 54 degrees at both stops.

**Which way round the turret goes.** `atan2` reports a bin behind the
arm at +139 degrees when the continuous answer is -221, and
interpolating towards +139 sweeps the turret the wrong way -- back into
the stop the yaw was chosen to avoid. Azimuths are unwrapped into the
arm's own travel window before anything blends them.

**Which way the jaws close.** A box's faces are square to the belt, so
the jaws should be too, which the natural wrist does not give. But a jaw
axis is an *axis*: half a turn swaps the jaws and grips the same box.
Wrapping that correction modulo 360 instead of 180 commanded a pointless
half-turn straight into J6's stop, and recomputing the branch every
frame let it flip mid-carry -- a 107-degree step in J6 for no physical
reason. The branch is now fixed when the box is claimed, and the
constraint is faded in over the last third of the approach and out over
the first third of the carry, because nothing is being gripped in
between.

None of those are visible in a still. All three were found by checks.

## The boxes fold

`scene.gripped_box_mesh` deforms a box vertex by vertex while a claw is
on it: panels in, corners fixed, because the folded edges are the stiff
part of a box. Two superposed shapes, both vanishing at the creases so
the lid and floor still meet the sides exactly — `sorter.panel_dish`
(the side bending as a plate, going as the square of the panel) and
`sorter.crush_depth` (flutes collapsing under the ridge).

`sorter.relax` advances it a frame at a time and is deliberately
asymmetric: closing, the board yields to wherever the jaws are, because
the claw is steel and it has no choice; opening, it relaxes on its own
time constant and lags them. It can never spring back past the crush,
which is plastic, so a box keeps the pad print.

Two bugs the frame-by-frame trace caught that no aggregate check could:
a box that went from square to fully crushed in one frame, and — worse —
a claw parked across the cell crushing a box by 43 mm because
`task.parcel` still pointed at a box it had dropped a second earlier.

## The tool is a reacher grabber's claw

Parts 10, 12 and 13 are the working end of the tool people pick things
up with at arm's length. Bolted to a robot flange the pistol grip
becomes an actuator housing and the trigger becomes a linear drive; the
head bolts straight onto it and four jaws pivot in that.

The pole is not modelled. It exists to save a person bending down, and
the arm is already the reach -- on J6 it would only be length to carry
and swing.

Two things a claw needs that a parallel gripper does not, and both of
them are why `kinematics` grew rather than shrank:

* **The grip does not sit still as it closes.** Parallel jaws
  translate, so the grasp point is a fixed distance down the tool at
  every opening. A claw's jaws rotate, so the grip swings *along* the
  tool as well as in -- 20 mm of it across the size range here. The tool
  centre point is pinned to one stated opening (`grab_ref_gap`) and
  `pad_offset` is how far the grip is from it at any other, which is
  what the sorter raises its targets by.
* **Each pad is a half-round ridge.** The pad sits on a finger that is
  still curling, so a flat face meets a box's flat side at an angle and
  touches it on one edge -- and which edge, and how far in it is,
  changes with the opening. A cylinder touches a plane on a line at
  exactly its own radius whatever angle it is presented at, so the
  opening is a number again and `opening_for_gap` inverts in closed
  form.

And one thing the cell pays for: pointing any tool straight down costs
horizontal reach, because its length is spent on standoff rather than
on stretch. This one costs 153 mm of it. `CELL_ARM` is re-driven longer
to buy that back, which is one line in `cell.py` and the whole point of
the model being parametric.

A claw also reaches *below* what it grips -- the fingers curl past the
pads -- so `sorter.grasp_at` lifts the whole grasp until the fingertips
clear the belt, taking a short box a few millimetres above its middle
rather than dragging four tips along the belt to get to it.

## The drop is solved, not drawn

Everything up to the moment the jaws open is a motion program. After it,
nothing is. A released box becomes a rigid body with the position,
orientation, velocity and angular velocity the gripper had at that
instant, and `rigid.py` integrates it: gravity, contact against the bin
walls and against whatever is already lying in the bin, Coulomb
friction, and sleep when it stops.

This replaced a function that worked out where a box would end up and
then eased it there. It read as physics and was not: the landing pose
was an input, boxes settled onto a grid, and no box ever knocked another
one. The tell was that every box came to rest square to the bin.

The parts that are easy to get wrong, and what pins them down:

* **Position integration is trapezoidal.** `pos += vel * dt` after the
  gravity kick overshoots by half a step of gravity every step — 20 mm
  over a second at 240 Hz, which looks fine and is wrong.
  `test_free_fall_matches_the_closed_form` holds it to 1 µm.
* **Contact is SAT with face clipping**, not corner-in-box. Two boxes
  resting face to face have every penetrating corner sitting *on* the
  other's side face rather than inside it, so a corner test reports no
  contact and a stack sinks through itself.
* **Contacts are speculative**, generated up to 20 mm before the
  surfaces touch and allowed to slow a box to exactly the gap it has
  left. A contact that waits for overlap arrives too late: the box
  lands, the step ends with it 7 mm inside the floor, and pushing it
  back out is work against gravity — which was the one route by which
  energy ever entered the solver.
* **The penetration bias is a split impulse**, on pseudo-velocities that
  move the bodies for one step and are then thrown away, so separating
  two overlapping boxes cannot leave either of them faster than it was.
* **Friction clamps the accumulated tangential impulse**, not each
  iteration's contribution. Clamping per iteration gives twelve
  iterations twelve times the friction the surface has, and a box then
  sits at 35° with µ = 0.5. The test sweeps the slope and requires the
  box to let go on the right side of `atan(µ)`.
* **Bin walls are finite slabs, not half-spaces**, so "the box stayed in
  its bin" is a measurement. With a plane per wall there is nowhere else
  a box could go.

It found two things, too, neither of them in the solver.

**The bins were shorter than the boxes.** 170 mm deep, and a box that
landed on the edge of the one already in the bin slid off it and came to
rest balanced on the rim. That is what a shallow tray does; the tray is
230 mm deep now, and the jaws open 30 mm above the rim.

**An idle arm sat with its jaws wide open.** Each jaw stands 105 mm out
from the tool axis at full stroke, and that is what two arms came
closest with — a neighbour's carry passing 38 mm from a jaw that was
open only because nothing had ever told it to shut. The jaws now open
on the way out and close on the way home. Closest approach: 95 mm.

## Tracking a belt that never stops

Through `TRACK` the target is the moving box plus a hover height;
through `DESCEND` that hover eases to zero *while the target keeps
moving*; through `CLOSE` the target is the box exactly. The quintic ease
has zero derivative at the end, so the tool arrives at the box moving at
belt speed -- measured at 0.04 mm/s against a belt running at 115 mm/s.
The same property run backwards lets the box leave the belt at belt
speed instead of being snatched off it.

## Speed

A frame is about 44,000 triangles at 2560×1440, and the expensive part is
not the arm — it is the ground plane, a few triangles each covering a
quarter of the screen. So the floor and fixtures are shaded once into a
cached layer with its own depth buffer, and each frame rasterises only
what moves, compositing against that depth. That, rectangular
bounding-box buckets for scan conversion, and a sort-based depth resolve
in place of `np.maximum.at`, together take a frame from 9.4 s to 0.8 s.

No GPU, no OpenGL, no display: numpy and Pillow.
