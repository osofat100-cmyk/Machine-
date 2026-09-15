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
python3 simulate.py                   # the arm running a cycle, to video
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
| `robot_arm/parts.py` | The eleven part builders. |
| `robot_arm/assembly.py` | Kinematic chain and placement. |
| `robot_arm/verify.py` | The checking pass — see below. |
| `build.py` | CLI: verify, export, report. |
| `poses.py` | Renders several poses side by side. |
| `simulate.py` | Runs a pick-and-place cycle and renders it to video. |
| `sim/` | Kinematics, motion program and software renderer — [README](sim/README.md). |
| `test_robot_arm.py` | Test suite for the model. |
| `test_simulate.py` | Test suite for the simulation and renderer. |

## The checks are the point

`build.py` refuses to export geometry that fails verification. Eight
checks run first:

```
[PASS] every part is a single solid -- 11 parts
[PASS] no degenerate (near-zero volume) parts
[PASS] no fillets silently dropped -- 0 dropped
[PASS] joint chain matches independent FK (5 poses) -- max deviation 2.58e-13 mm
[PASS] each joint rotates about its intended axis -- J1/J4/J6 roll about Z, J2/J3/J5 pitch about X
[PASS] all 6 joints are live at a general pose -- 6 DOF
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
