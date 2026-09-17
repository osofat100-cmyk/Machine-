# Parametric robot arm

A 6-DOF articulated arm: **11 parts, 15 instances, 1 assembly**, built
programmatically on an OpenCascade kernel. No SolidWorks, no licence, no
GUI — it runs anywhere Python does.

## Run it

```bash
pip install build123d
cd cad
python3 build.py                      # verify, then export to build/
python3 poses.py                      # the pose strip
python3 simulate.py                   # one arm running a cycle, to video
python3 simulate_cell.py              # five arms sorting off a conveyor
```

Options:

```bash
python3 build.py --pose 25 -50 80 0 -30 0   # six joint angles, degrees
python3 build.py --out /tmp/arm --no-stl
python3 -c "from robot_arm.verify import run; print(run().render())"
```

Build takes about 10 seconds and writes:

```
build/step/<part>.step     one file per part
build/Robotic_Arm.step     the assembly, with structure and colour
build/stl/<part>.stl       mesh per part
build/arm_iso.svg          hidden-line-removed isometric
build/report.txt           checks + mass properties
```

## Layout

| File | What it is |
|---|---|
| `robot_arm/params.py` | **Every dimension.** One dataclass; nothing downstream hard-codes a number. |
| `robot_arm/parts.py` | The thirteen part builders. |
| `robot_arm/assembly.py` | Kinematic chain and placement. |
| `robot_arm/verify.py` | The checking pass — see below. |
| `build.py` | CLI: verify, export, report. |
| `poses.py` | Renders several poses side by side. |
| `simulate.py` | Runs a pick-and-place cycle and renders it to video. |
| `simulate_cell.py` | Five arms beside a moving conveyor, sorting by size. |
| `sim/` | Kinematics, motion program and software renderer — [README](sim/README.md). |
| `test_robot_arm.py` | Test suite for the model. |
| `test_simulate.py` | Test suite for the simulation and renderer. |
| `test_cell.py` | Test suite for the five-arm cell. |
| `test_rigid.py` | Test suite for the rigid-body solver, against closed forms. |

## The checks are the point

`build.py` refuses to export geometry that fails verification. Eleven
checks run first:

```
[PASS] every part is a single solid -- 13 parts
[PASS] no degenerate (near-zero volume) parts
[PASS] no fillets silently dropped -- 0 dropped
[PASS] joint chain matches independent FK (5 poses) -- max deviation 2.58e-13 mm
[PASS] each joint rotates about its intended axis -- J1/J4/J6 roll about Z, J2/J3/J5 pitch about X
[PASS] all 6 joints are live at a general pose -- 6 DOF
[PASS] the commanded jaw opening is inside the travel -- 52.0 deg commanded, travel 17.0..101.0 deg
[PASS] the jaws are still held by the head across the whole travel -- least overlap with the head 18.7 mm, at 80 deg of a 17..101 deg travel
[PASS] shut is shut, and not through itself -- the claw closes to 7.0 mm and opens to 167.8 mm
[PASS] the claw closes to the width the arithmetic says -- ridge surface measured 45.01 mm from the tool axis over 24 points, arithmetic says 45.01 mm -- a 90.0 mm opening
[PASS] extended reach is self-consistent -- tool at Z=793.4 mm
[PASS] no unintended interference between parts -- no clashes
```

The kinematics check computes the joint chain twice — once by placing
solids, once from scratch with 4×4 matrices — and requires agreement.
Two independent implementations agreeing beats one that merely runs.

These found three real defects during development: a wrist housing that
was two disconnected solids, and two fillets failing silently. A fourth
— a gripper whose jaws opened outward instead of inward — passed every
one of these and was caught only by rendering the arm and looking at it.

The tool checks are newer, and they exist because of a fifth. The
gripper was two fingers placed on the tool face and slid apart: the
stroke had no mechanism to be the stroke *of*, so past a certain
opening the jaws were simply two solids floating near the flange,
attached to nothing, and every other check here passed. It does not
look wrong in a still either — it reads as a gripper that happens to be
open.

## The tool is a reacher grabber's claw

Parts 10, 12 and 13 are the working end of the tool people actually pick
things up with at arm's length: a **reacher grabber**, the
litter-picker's tool. Squeeze the trigger and a rod pulls four jaws
closed on whatever is between them; let go and a spring opens them.

Bolted to a robot flange the pistol grip becomes an actuator housing
(part 12) and the trigger becomes a linear drive. The head (13) bolts
straight onto it, and four jaws (10) pivot in that.

**The pole is not modelled, on purpose.** It is there to save a person
bending down, and a robot arm is already the reach. Bolted to J6 it
would be dead length for the wrist to carry and swing, spent holding
the frame above the box rather than reaching out to it — and every
clearance in the cell would be paying for it.

The mechanism is the same lesson one level on. Each jaw carries a pin on
its heel, and that pin runs in an **arc slot** cut in the head. The slot
is swept from `grab_open_min` to `grab_open_max` — the same two numbers
everything else asks for the travel — so the head cannot allow an angle
the model forbids, nor forbid one the model allows.

Two things a claw needs that a parallel gripper does not:

- **The grip does not sit still as it closes.** Parallel jaws
  translate, so the grasp point is a fixed distance down the tool at any
  opening. A claw's jaws rotate, so the grip swings along the tool as
  well as in. The tool centre point is pinned to one stated opening and
  everything else is measured against it (`kinematics.pad_offset`).
- **Each pad is a half-round ridge, not a flat.** The pad sits on a
  finger that is still curling, so a flat would meet a box's flat side
  at an angle and touch it on one edge — and which edge, and how far in
  it is, would change with the opening. A cylinder touches a plane on a
  line at exactly its own radius, whatever angle it is presented at,
  which is what makes the opening a number at all.

## Watching it move

```bash
python3 simulate.py                   # build/machine.mp4, about 6 minutes
python3 simulate.py --check-only      # solve and check, render nothing
```

A pick-and-place cycle: approach, descend on a straight line, close on a
70 mm part, transfer, place, retract, park. A 70 mm part and not a 32 mm
one because a claw wraps what it grips: its fingertips reach about 18 mm
below the grip, and a 32 mm cube on a flat bench has only 16 mm of
height under its middle, so four tips would close into the bench to get
to it. `check_clearance` said so -- eighty intrusions, the first of them
a jaw inside a pedestal. The arm on screen is this
model — the same thirteen solids, placed by `assembly.build_assembly`,
driven by an inverse solve that runs once per frame on the straight-line
moves. There is no GPU in the loop and no OpenGL; `sim/` rasterises it
with numpy.

Thirteen more checks run before a single frame is drawn, and the run
refuses to render if any fails:

```
[PASS] every commanded pose is actually reached -- worst residual 0.020 mm / 0.012 deg over 139 solves
[PASS] straight-line moves run straight -- worst deviation from the commanded line 0.019 mm
[PASS] joint motion is continuous -- largest change in one frame 2.99 deg
[PASS] no joint reaches a stop -- widest excursion 145.0 deg
[PASS] the payload is rigidly held, not re-scripted, while gripped -- tool-to-part transform varies by 1.2e-13 mm over 161 frames, caught 17 um off axis
[PASS] the payload is actually picked up -- lifted to z = 261 mm
[PASS] the payload ends up on the second fixture -- 0.001 mm from the commanded place point
[PASS] the jaws are commanded onto the part exactly -- commanded gap 70.0 mm against a 70 mm part
[PASS] the tool never drives into the fixture -- lowest tool centre point z = 136.0 mm
[PASS] nothing but the recessed J1 drive goes below the mounting face -- lowest moving vertex z = 0.00 mm
[PASS] the arm never enters a fixture -- clear at every sampled frame
[PASS] the jaws close on the part, not through it -- jaw faces measured 70.01 mm apart on a 70 mm part, with the jaws 43.3 deg open
[PASS] no self-collision at any commanded pose -- 7 distinct poses checked with robot_arm.verify
```

The last one is the model's own `verify.check_interference`, re-run at
every pose the program commands. A pose that clashes is a pose the
machine cannot hold, and animating it would be drawing a lie smoothly.

One of them is there because the others are not enough. `jaw_gap` is
arithmetic *about* `parts.grabber_jaw`, and arithmetic about geometry
can be wrong while the geometry is right — this one was, by 2 mm, and the
jaws stood a millimetre clear of a part they were reported as gripping.
Nothing in the render looked wrong. So the check that matters measures
the placed triangles, and `scene.measure_jaw_gap` is the one place that
does it for everything that asks.

## Five of them on a conveyor

```bash
python3 simulate_cell.py              # build/cell.mp4, about 40 minutes
python3 simulate_cell.py --check-only
```

Five arms beside a belt that never stops: three on one side, two on the
other, staggered 800 mm apart. Boxes of three sizes arrive at random
times and random positions across the belt. Every box is the same colour
and the same shape, at any size inside its band, so where one goes is
decided by measuring it and nothing else.

**Each arm works the whole width of its own stretch of belt** -- near
edge to far edge. That is why the cell runs a 783 mm build of the arm
rather than the 573 mm default: the far edge is 701 mm from a base,
reach falls off with height, and the claw spends 153 mm of the arm's
own reach holding the wrist above the box rather than out towards it.
Territory used to be a stretch *and* the near half of it, which made
the arms look like they could only get halfway across, and made the
extra reach pointless.

A box its owner is too busy for stays on the belt for the next arm along;
one nobody catches rides to the end and falls off it.

### All five work at once, and the layout is why

Reaching across is what makes two arms able to touch, and the cell used
to answer that with an **interlock**: an arm whose neighbour was
mid-pick stood still. It worked, and it was the wrong answer. Two
machines that cannot both run are two machines you are paying for and
using as one -- a third of the line idle at any moment to keep the rest
safe is not a safety system, it is a smaller cell.

Worse, it hid a scheduling bug for a whole render. Adjacency is a path,
`A1-A2-A3-A4-A5`, so the largest set that could work at once was either
`{A1, A3, A5}` or `{A2, A4}`, and a claim loop that scanned arms in
index order picked the same one of those every frame forever. Measured:
`A1:4 A2:0 A3:4 A4:0 A5:4`, with the two zeros having moved **0.00
degrees**. Every check passed, because "no two adjacent arms work at
once" is satisfied perfectly by two arms doing nothing at all.

So the interlock is gone and the collision is fixed where it lives, in
the layout. Same 26 s, same seed, every arm free to work:

| | closest two arms | picked |
|---|---|---|
| 650 mm stagger, 445 mm standoff | **18 mm** — fails a 50 mm floor | 13 |
| 800 mm stagger, 480 mm standoff | **145 mm** | 14 |

Adjacent arms sit on opposite sides of the belt, so standing the bases
back separates them *across* the belt as well as along it — and 480 +
230 = 710 mm to the far edge is still inside the 735 mm the envelope is
verified to. The belt grows to ±2100 to carry the wider stagger.

It grows for a second reason too, which is a bug this turned up: a box
may not be claimed before the sensor has measured it, and `can_claim`
never asked. The cell sorts on what the sensor reads, so an arm claiming
upstream of the sensor is sorting on what the *spawner* knew — a
different machine, and one whose "the sorting is a measurement" claim
would be false. Two candidate layouts put the first arm's window
upstream of the sensor and nothing objected. It objects now.

What is left of the dispatcher is longest-idle ordering, for
determinism, and one rule that levels the line: an arm ahead on the
count lets a box run to a quieter arm downstream, since a box it can
reach now, every arm downstream can reach later. Result: **5 of 5 arms
working at once**, `A1:3 A2:3 A3:3 A4:2 A5:3`, and 14 of 23 boxes picked
against 9 with the interlock.

The two checks that hold it: **"every arm can be working at the same
time"**, and `check_clearance`, which is now the *only* thing promising
two arms never touch — measured between placed triangles every other
frame rather than asserted by a rule.

### The boxes fold

A claw cannot be inside the box it is holding, so either the box gives
way or the claw does. Boxes are cardboard, so the box gives way — and it
gives way the way a cardboard box does, which is not by getting smaller.
The folded edges are the stiff part, so the corners do not move at all
and the **panels** go in. Each face is a grid of vertices, displaced by
two shapes that both vanish at the creases:

| | | |
|---|---|---|
| **dish** | the side bending as a plate held at its four edges | `0.0116·P·a²/D` |
| **crush** | the flutes collapsing under the 4 mm ridge itself | `F = σc·2√(2Rd)·L` |

Dish goes as the *square* of the panel, so a 112 mm box gives 7.88 mm
and a 38 mm box gives 0.93 — big boxes crunch and small ones barely
notice, which is what you feel doing it by hand. `grip_gap` is therefore
`size − 2(dish + crush)`: the jaws close past the nominal face by
everything the box gives and nothing more. Closing to exactly `size`,
as this once did, puts the ridges tangent to the faces with no contact
force at all — a claw resting against a box rather than holding one.

**Going in and coming out are not symmetric, because the materials are
not.** Closing, the claw is steel and the board is not, so it yields as
far as the jaws have gone, that frame. Opening, nothing is pushing any
more and the panel is on its own clock — a relaxation at
`RECOVER_TAU = 0.35 s` — so it *lags* the jaws rather than tracking
them, and the dent is still there after the claw has let go and swung
away. Traced on a 109 mm box: four frames to crush, 8.59 mm held through
the carry, released still 5 mm folded, and creeping back for a second
and a half while it falls.

What it never comes back past is the crush. The dish is elastic and
gives its energy back; the flutes do not un-collapse. So the permanent
set is not a number anyone chose — it is `crush_depth`, and every box in
a bin carries the pad print of the claw that put it there.

The check is **"no part of the claw is inside the box it is holding"**,
measured from every triangle of every jaw against the box as it is while
folded, and bounded by what the board gives rather than by a tolerance.
The check it replaced watched only the ridges, and the ridges were
tangent the whole time the fingertips were 65 mm deep in a large box.

### The drop is solved, not drawn

Everything up to the moment the jaws open is a motion program. After it,
nothing is. A released box becomes a rigid body carrying the position,
orientation, velocity and angular velocity the gripper had at that
instant, and `sim/rigid.py` integrates it: gravity, contact against the
bin walls and against whatever is already lying in the bin, Coulomb
friction, and sleep once it stops. A box nobody claimed is let go at the
instant its centre of mass crosses the end of the belt, which is exactly
when a box on a belt end starts to tip, and it pivots on the edge on the
way into the chute.

This replaced a function that worked out where a box would end up and
then eased it there. It read as physics and was not: the landing pose
was an input, boxes settled onto a grid, and no box ever knocked
another. The tell was that every box came to rest square to the bin.

`test_rigid.py` checks the solver against arithmetic that was true
before it existed -- where a body is after a second of free fall, how
high a box rests on a floor, and the exact slope angle at which Coulomb
friction gives up -- because a solver is easy to be wrong about
convincingly. Boxes fall, boxes stop, boxes pile up, and it looks right
whether or not any of the numbers are.

Twenty-four checks run before a frame is drawn. The ones worth reading:

```
[PASS] every arm can reach every point of its own stretch of belt -- solved at 125 points spanning 287..701 mm of reach, worst residual 0.020
[PASS] ...and is sent across it: territory is the full width -- every arm owns both edges of its own stretch
[PASS] the size bands leave a gap, so no measurement is ambiguous -- narrowest gap between bands 16 mm, thresholds at 72 and 109 mm
[PASS] the tool matches belt speed at the grasp -- worst relative speed 0.032 mm/s against a belt running at 115 mm/s
[PASS] two arms that can reach the same air are never both working -- never a neighbouring pair; 3 of 5 arms working at once at the busiest
[PASS] the jaws never open past the travel the slot allows -- widest 95.5 mm of 110.0 mm available
[PASS] every box came to rest in the bin its size designates
[PASS] the jaw faces really are that far apart -- measured from the placed triangles, worst disagreement with the box 0.000 mm
[PASS] no two arms ever come within reach of each other -- closest approach 100 mm (floor 50 mm)
```

The last one is the point of the layout. Disjoint territory constrains
where each arm puts its *tool*; it says nothing about where the elbow
is. So the clearance is measured from the placed triangles, every frame,
between every pair of arms -- and between bounding boxes rather than
surfaces, which understates the gap, so a pass is a guarantee rather
than an estimate.

It is also what caught two holes in the dispatcher. The approach used to
fly out to wherever the box was *now*, which is upstream, in the
previous arm's stretch of belt; it now goes to the intercept, a fixed
point inside the arm's own window. And the claim margin was a fixed
12 mm against 40 mm of belt travel during the close, so a box could be
claimed legitimately and gripped outside the window -- the margin is now
derived from `CLOSE_T` and the belt speed.

## Parametric means re-drivable

Change a field in `params.py` and everything follows. Seven variants,
all passing every check:

```
OK  default        reach=573.0mm      OK  thin-wall      wall=4mm
OK  long-reach     reach=868.0mm      OK  big-base       220mm, 6 bolts
OK  compact        reach=368.0mm      OK  wide-gripper   34mm stroke
OK  heavy-wall     wall=9mm
```

```python
from robot_arm.params import ArmParams
from robot_arm.assembly import build_assembly

arm = build_assembly(ArmParams(upper_len=420.0, fore_len=350.0))
```

## About the output format

STEP is a neutral solid format. It imports into SolidWorks, CATIA, Fusion
and everything else — **as a dumb solid**, with no feature tree and no
sketches. That is a real limitation, not a detail: see
[`../docs/can-claude-do-this.md`](../docs/can-claude-do-this.md) for why
it matters and what the alternative costs.
