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
| `robot_arm/parts.py` | The twelve part builders. |
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

## The checks are the point

`build.py` refuses to export geometry that fails verification. Eleven
checks run first:

```
[PASS] every part is a single solid -- 12 parts
[PASS] no degenerate (near-zero volume) parts
[PASS] no fillets silently dropped -- 0 dropped
[PASS] joint chain matches independent FK (5 poses) -- max deviation 2.58e-13 mm
[PASS] each joint rotates about its intended axis -- J1/J4/J6 roll about Z, J2/J3/J5 pitch about X
[PASS] all 6 joints are live at a general pose -- 6 DOF
[PASS] the slot is long enough for both jaws at full stroke -- jaw outer face reaches 54.0 mm, slot half-length 55.0 mm
[PASS] the commanded stroke is inside the travel the slot allows -- 22.0 mm commanded of 50.0 mm available
[PASS] the jaws are still held by the body at every stroke -- least engagement 13.0 mm of a 13.0 mm slot
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

The three gripper checks are newer, and they exist because of a fifth.
The gripper was two fingers placed on the tool face and slid apart:
`finger_stroke` had no mechanism to be the stroke *of*, so past a
certain opening the jaws were simply two solids floating near the
flange, attached to nothing, and every other check here passed. It does
not look wrong in a still either — it reads as a gripper that happens to
be open. So part 12 is the body they run in, and the slot is both the
mechanism and the limit.

## Watching it move

```bash
python3 simulate.py                   # build/machine.mp4, about 6 minutes
python3 simulate.py --check-only      # solve and check, render nothing
```

A pick-and-place cycle: approach, descend on a straight line, close on a
32 mm part, transfer, place, retract, park. The arm on screen is this
model — the same eleven solids, placed by `assembly.build_assembly`,
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
[PASS] the jaws are commanded onto the part exactly -- commanded gap 32.0 mm against a 32 mm part
[PASS] the tool never drives into the fixture -- lowest tool centre point z = 136.0 mm
[PASS] nothing but the recessed J1 drive goes below the mounting face -- lowest moving vertex z = 0.00 mm
[PASS] the arm never enters a fixture -- clear at every sampled frame
[PASS] the jaws close on the part, not through it -- jaw faces measured 32.00 mm apart on a 32 mm part, at stroke 26.0 mm
[PASS] no self-collision at any commanded pose -- 7 distinct poses checked with robot_arm.verify
```

The last one is the model's own `verify.check_interference`, re-run at
every pose the program commands. A pose that clashes is a pose the
machine cannot hold, and animating it would be drawing a lie smoothly.

The twelfth is there because the eleventh is not enough. `jaw_gap` is
arithmetic *about* `parts.gripper_finger`, and arithmetic about geometry
can be wrong while the geometry is right — this one was, by 2 mm, and the
jaws stood a millimetre clear of a part they were reported as gripping.
Nothing in the render looked wrong. So the check that matters measures
the placed triangles.

## Five of them on a conveyor

```bash
python3 simulate_cell.py              # build/cell.mp4, about 40 minutes
python3 simulate_cell.py --check-only
```

Five arms beside a belt that never stops: three on one side, two on the
other, staggered 650 mm apart. Boxes of three sizes arrive at random
times and random positions across the belt. Every box is the same colour
and the same shape, at any size inside its band, so where one goes is
decided by measuring it and nothing else.

**Each arm works the whole width of its own stretch of belt** -- near
edge to far edge. That is why the cell runs a 783 mm build of the arm
rather than the 573 mm default: the far edge is 701 mm from a base, and
reach falls off with height. Territory used to be a stretch *and* the
near half of it, which made the arms look like they could only get
halfway across, and made the extra reach pointless.

Reaching across is what makes two arms able to touch. The 270 mm between
windows is a gap between the points their *tools* visit, not between the
machines: measured, neighbours came within 3 mm of each other, while
every non-adjacent pair stayed a clear 235 mm off. So the cell
interlocks on adjacency -- two arms that can reach the same air are
never both in a pick -- which still lets three of the five work at once.

A box its owner is too busy for stays on the belt for the next arm along;
one nobody catches runs off the end into the reject chute and is counted.
Boxes dropped into a bin fall and land on whatever is already in it.

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
