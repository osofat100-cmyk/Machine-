# Handoff

Everything needed to pick this up in a desktop Claude Code session with
Fusion 360 installed. Written to be read cold — no prior conversation
required.

---

## What this is

It started as a question about [a MecAgent
post](https://www.instagram.com/mecagent_off/): they claimed one prompt
produced **11 parts + 1 assembly** in SolidWorks 2026 in a 35-minute
run, parametric and editable, "not yet fully constrained."

The question was: *can you do the same, and how?*

This repository is the answer, built rather than described. It contains
a 6-DOF robot arm — **11 parts, 15 instances, 1 assembly** — generated
three different ways, plus the machinery for checking that generated CAD
is not quietly wrong.

---

## The one idea worth keeping

**Generating geometry is the easy half. Knowing it's wrong is the hard
half.**

Writing verification found three real defects in eleven parts. A fourth
passed *every* automated check and was caught only by rendering the arm
and looking at it — a gripper whose two jaws both folded outward.
Geometrically flawless. Could not grip.

That failure mode then happened **again, independently**, on a different
kernel: a Fusion forearm whose two plates never touched, so the join had
nothing to merge and silently left two loose lumps. Every step reported
OK. Only counting solids exposed it.

Two independent hits on the same failure mode is why the checks in here
are not decoration.

---

## What's in the box

| Folder | What | Runs where | State |
|---|---|---|---|
| `cad/` | Parametric arm on an OpenCascade kernel (build123d) | Anywhere Python runs | **Verified, works** |
| `fusion360/` | The same arm built inside Fusion, real timeline | Needs Fusion | **Never run in Fusion** |
| `solidworks_harness/` | 20-tool agent surface driving SolidWorks over COM | Needs Windows + SolidWorks | **COM layer unverified** |
| `docs/` | The full written answer | — | — |

### `cad/` — this one definitely works

```bash
pip install build123d
cd cad
python3 build.py          # verify, then export (~10 s)
python3 test_robot_arm.py # 9 tests
```

13 parts, 7.97 kg in 6061-T6, 573 mm of arm plus a reacher grabber's
claw. Exports STEP, STL and hidden-line drawings. **Refuses to export
anything failing its 12 checks.** The kinematic chain is computed twice — once by placing
solids, once from scratch with 4×4 matrices — and the two must agree to
2.6e-13 mm.

Its output is STEP, which imports everywhere **as a dumb solid**: no
feature tree, no sketches. That limitation is why the other two folders
exist.

### `fusion360/` — the recommended path, and the open task

Builds the same arm *inside* Fusion, so the history is genuine: 11
components each with their own timeline, 33 named User Parameters
(change `upper_len`, the arm rebuilds), 5 revolute joints.

```bash
cd fusion360
python3 tests/test_fusion_script.py       # 23 tests
python3 tests/test_matches_cad_model.py   # 5 tests
```

Those run **without Fusion**, against a hand-written fake `adsk` module
in `tests/mock_adsk.py` that records every API call.

- **Proven:** 11 components, every feature given a real extent, no
  profile indexed before it exists, joints only between components that
  exist, gripper jaws facing each other, mm→cm conversion correct, and
  all 33 dimensions matching `cad/robot_arm/params.py`.
- **Not proven:** that Autodesk's API behaves as the mock assumes.

### `solidworks_harness/` — reference only

Windows-only. Agent-facing half is tested (20 tool schemas validate);
the COM layer is written from documentation and unverified. `probe.py`
checks the assumptions that couldn't be tested — chiefly the
`GetConstrainedStatus` enum, where a wrong constant would silently
report loose sketches as fully defined.

**Recommendation: don't buy SolidWorks for this.** Fusion gives the same
editable history, has a far nicer Python API, runs on macOS, and is free
for personal use. Kept only as reference.

---

## THE OPEN TASK

**Run `fusion360/robot_arm_fusion.py` in Fusion. It has never been run
there.**

That is the single remaining unknown in this project.

### How to run it

1. Fusion → `File > New... > **Part Design**`
   **Not** Electronics Design. If the default new document is an
   Electronics Design, `adsk.fusion.Design.cast(app.activeProduct)`
   returns None and the script correctly refuses. This has already
   caught someone out.
2. `Utilities > ADD-INS > Scripts and Add-Ins > Scripts` tab
3. Green `+` → select the `fusion360` folder → Run

The script **does not stop at the first error.** Each step is wrapped:
failures are recorded (step name, exception, raising line) and the rest
still builds, so one run reports every problem instead of just the
first. It then asks Fusion what actually landed and writes everything to
`fusion360/fusion_run_report.txt`.

Expected on success:
```
distinct components : 11
occurrences         : 15
solid bodies        : 11 or more
joints              : 5
user parameters     : 33
all counts as expected, no split bodies
```

### What will probably break, in order

1. **Profile indexing.** `sketch.profiles.item(0)` assumes the sketch
   yielded the expected closed region. `build_base_flange` and
   `build_tool_flange` cut several holes from one sketch; `_clevis`
   builds a U. Real Fusion may order or split profiles differently.
2. **Offset construction planes.** `Builder.sketch_on_xy(comp, z_mm)`
   uses `createInput()` / `setByOffset()`.
3. **`build_forearm`.** Four-point closed polygon on XZ, revolved about
   `zConstructionAxis`.
4. **Cut direction.** Hole cuts pass a negative depth to cut downward
   from an offset plane.

Joints *were* the top prediction, and the likely cause was found and
fixed by reading the docs rather than waiting for the failure: a bare
`component.originConstructionPoint` refers to the component definition,
not a placement, so `_joint_point()` now calls
`createForAssemblyContext(occurrence)` first. That fix is committed and
its tests pass, but it is **still unverified against real Fusion** —
like everything else in `fusion360/`.

### Rules when fixing

- **Never change a dimension.** `tests/test_matches_cad_model.py`
  asserts all 33 match `cad/robot_arm/params.py`. If you change a
  number that test fails, and it should — the two models describe the
  same arm deliberately.
- **Keep 11 components and 5 joints.** If joints genuinely cannot be
  scripted, say so plainly and leave the components correctly placed.
  Don't fake counts and don't simplify the arm to make it build.
- **Update the mock** whenever you fix a call because reality differed,
  with a comment on what you observed. Otherwise the tests keep passing
  against a fiction.
- **Look at the tool by eye.** The claw's four jaws must curl inward.
  No automated check catches a claw that opens the wrong way; that's
  the whole lesson above.

---

## Git state

Branch: `claude/replication-question-s6j2xl` → **PR #1**, open draft,
mergeable, no conflicts. The repo has **no CI**, so nothing runs these
tests on push — all figures here come from running them locally.

```
(head)   Bind joint geometry to placements, not component definitions
055505d  Detect bodies that look solid but are in pieces
dc5430e  Make the Fusion script survive its first contact with Fusion
e4ee1fe  Add Fusion 360 path: same arm, real timeline, tested off-Fusion
71ec4d3  Answer "can you generate CAD from one prompt", with working code
```

The working tree is clean — everything described here is committed and
pushed.

Clone: `git clone https://github.com/osofat100-cmyk/Machine-.git`
then `git checkout claude/replication-question-s6j2xl`

---

## Current test state

```
8/8   verification checks   (cad/build.py)
9/9   tests                 (cad/test_robot_arm.py)
23/23 tests                 (fusion360/tests/test_fusion_script.py)
5/5   tests                 (fusion360/tests/test_matches_cad_model.py)
20/20 tool schemas valid    (solidworks_harness/)
7/7   parameter variants rebuild and re-verify
```

---

## A note on a previous attempt

A desktop session was asked to run the Fusion script and instead
**wrote its own, different, simpler arm** — 4 bodies named `ARM_BASE`,
`LINK_UPPER`, `LINK_FORE`, `GRIPPER`, no joints, no User Parameters,
339 mm reach. It built successfully and its verifier caught the
split-lump defect described above, which is where that finding came
from. Good work, but not this arm.

If you open the script and see `combineFeatures` or `modelToSketchSpace`,
you have the wrong file — this one uses neither. The right file is 671
lines and defines components named `01_base_flange` through
`11_actuator_can`.
