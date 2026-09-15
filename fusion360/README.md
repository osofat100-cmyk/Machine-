# The arm, in Fusion 360

Builds the same 11-part robot arm **inside Fusion**, with a real
timeline you can click back through and edit — not an imported lump.

## Run it

1. Open Fusion and create a new design (or open an empty one).
2. **Utilities → ADD-INS → Scripts and Add-Ins → Scripts** tab
3. Click the green **+** next to "My Scripts", pick this `fusion360`
   folder
4. Select `robot_arm_fusion` → **Run**

Takes a few seconds. A dialog reports what was built, and a full report
is written to `fusion360/fusion_run_report.txt`.

**If something fails, the script does not stop.** It records which step
broke and what the error was, builds everything else, then reports the
lot — so one API mismatch tells you about all of them instead of just
the first. It also counts what actually landed in the document
(components, bodies, joints, parameters) rather than assuming.

Send back `fusion_run_report.txt` if anything is marked FAIL; it names
the exact call that didn't match.

## What you get

- **11 components**, each with its own feature history
- **33 User Parameters** under *Modify → Change Parameters* — change
  `upper_len` from 260 to 420 and the arm rebuilds
- **5 revolute joints**, so the arm articulates: drag it
- Real sketches, extrudes, cuts and revolves in the timeline

This is the thing a STEP import can't give you. Fusion is doing the
modelling, so the history is genuine.

## The one trap worth knowing

**Fusion's API is centimetres.** Always, regardless of what your
document displays. Pass `50` meaning 50 mm and you get a part five times
too big that builds perfectly cleanly and looks fine until you measure
it. Everything here goes through `cm()` exactly once, at the boundary.

Every CAD API has this trap. SolidWorks' is set to metres.

## Tests

```bash
cd fusion360
python3 tests/test_fusion_script.py       # 18 tests
python3 tests/test_matches_cad_model.py   # 5 tests
```

These run **without Fusion**, against a fake `adsk` module in
`tests/mock_adsk.py` that records every API call the script makes.

**What that proves:** the script's own logic — 11 components, every
feature gets a real extent, no profile indexed before it exists, joints
requested only between components that were created, the gripper jaws
facing each other, mm→cm conversion correct, and every one of the 33
dimensions matching the verified `cad/` model.

**What it can't prove:** that Autodesk's real API behaves the way the
mock assumes. Run it in Fusion before believing it. If something fails
there it will be a signature detail, not the logic.

## Files

| File | What it is |
|---|---|
| `robot_arm_fusion.py` | The script you run in Fusion. |
| `tests/mock_adsk.py` | Fake `adsk` module — records calls, off Fusion. |
| `tests/test_fusion_script.py` | Does the script build what it claims? |
| `tests/test_matches_cad_model.py` | Does it match the verified `cad/` model? |

## Going further: the Fusion MCP

Autodesk ships an official **Fusion MCP** that connects an AI client to
a *live* Fusion session — run scripts, read errors, reach the API docs.
That's the agentic workflow: the model builds, looks at what happened,
and fixes it, instead of firing one script and hoping.

This script is the deterministic counterpart — same arm, every time, no
API calls, no cost. Both are useful; they're not competing.
