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
eleven solids `robot_arm/parts.py` exports to STEP, placed by
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
| `cellscene.py` | belt, bins, chute, zone markings -- scenery, not CAD |
| `scene.py` | tessellates the eleven prototypes once; re-places them per frame |
| `raster.py` | z-buffered software rasteriser, and camera fitting |
| `render.py` | shading, ground shadow, static/dynamic compositing |
| `hud.py`, `hud_cell.py` | the telemetry overlays |

## Three decisions worth explaining

**The placements are read out of the assembly, not copied.** `assembly.py`
says driving the pose "is a matter of changing `ArmParams.joints` — no
geometry is rebuilt, only re-placed", so that is what happens.
`scene.placements` calls the real `build_assembly` with the eleven solids
swapped for unit cubes, purely to read back each instance's `Location`,
then moves cached triangles by those transforms. Rebuilding the solids
 per frame would cost 1.3 s each; more to the point, a re-implementation of
the chain could drift from the one that makes the STEP file, and this one
cannot. `test_simulate.py` compares all fifteen transforms against the
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
