# Machine-

How to build a mechatronics machine with Claude.

---

## Can an agent generate a robot arm in CAD from one prompt?

This repository answers that question, prompted by a MecAgent post
claiming one prompt, 11 parts, 1 assembly, 35 minutes, in SolidWorks
2026.

**Read the answer: [`docs/can-claude-do-this.md`](docs/can-claude-do-this.md)**

![The generated arm](docs/img/arm_iso.png)

Eleven parts, fifteen instances, one assembly. 7.19 kg in 6061-T6,
573 mm reach, built and verified in **10.5 seconds**.

## Two halves

### `cad/` — runs here, right now

A parametric 6-DOF arm on an OpenCascade kernel. No SolidWorks, no
licence, no GUI.

```bash
pip install build123d
cd cad && python3 build.py
```

Exports STEP, STL and hidden-line drawings, and refuses to export
anything that fails its eight verification checks — including a
kinematic chain cross-checked against an independent 4×4-matrix
implementation, agreeing to 2.6e-13 mm.

![Four poses](docs/img/poses.png)

*Only the six joint angles change between these. No geometry is rebuilt.*

### `fusion360/` — run it in Fusion

The same arm built **inside Fusion**, with a real editable timeline, 33
User Parameters, and 5 revolute joints. Load it from *Scripts and
Add-Ins* and hit Run.

Tested off-Fusion against a fake `adsk` module: 20 tests covering the
script's logic and confirming every dimension matches the verified
`cad/` model. See its [README](fusion360/README.md).

### `solidworks_harness/` — needs your Windows machine

A 20-tool agent surface that drives SolidWorks over COM to produce
**native parts with a real feature tree**, which is the thing a STEP
import cannot give you. Windows-only; the COM layer is written against
the documented API but untested — see its
[README](solidworks_harness/README.md) before running it.

## The short version

The gap between "generates plausible CAD" and "generates CAD an engineer
accepts" is almost entirely the verification loop, not the generation.
Writing checks found three real defects in eleven parts. Rendering the
arm and looking at it found a fourth that every automated check had
passed: a gripper whose jaws opened outward.
