# SolidWorks agent harness

Lets a model drive SolidWorks directly, producing native parts with a
real feature tree — not an imported dumb solid.

> **Windows only, and the COM layer is unverified.**
> SolidWorks is COM software with no Linux build and no headless mode.
> It must be installed, licensed and running on the same machine as this
> code. I had no SolidWorks to test against, so the COM calls are
> written against the documented API but not exercised. The
> agent-facing half *is* tested: all 20 tool schemas generate and
> validate. **Run `probe.py` before trusting a build.**

## Setup

```bat
pip install -r requirements.txt
set ANTHROPIC_API_KEY=...

python -m swbridge.probe
```

`probe.py` reports the SolidWorks version and checks the assumption most
likely to be silently wrong: the `GetConstrainedStatus` enum values. If
that table is wrong, the harness reports under-constrained sketches as
fully defined — the worst possible failure, because it is invisible.

## Run

```bat
python -m swbridge.agent_loop ^
    --prompt "A 6-DOF robot arm, 500mm reach, aluminium" ^
    --out C:\work\arm ^
    --effort high
```

## Layout

| File | What it is |
|---|---|
| `swbridge/enums.py` | SolidWorks constants and the mm→m conversion. |
| `swbridge/connection.py` | COM attach, document lifecycle. |
| `swbridge/tools.py` | **The 20-tool surface the model drives.** |
| `swbridge/feedback.py` | Reading state back: tree, errors, constraints, screenshots. |
| `swbridge/agent_loop.py` | The loop and the system prompt. |
| `swbridge/probe.py` | Verifies this harness's assumptions against your install. |

## Three things that matter more than they look

**Millimetres in, metres out.** The SolidWorks API is metres and radians
internally regardless of display units. Pass `50` meaning 50 mm and you
build a fifty-metre part that rebuilds perfectly cleanly. Convert once,
at the boundary, in `enums.mm`.

**Errors return as text, never as exceptions.** An exception ends the
turn; a string the model can read is something it can act on. Every tool
is wrapped to guarantee this.

**`check_constraints` is why this exists.** An under-constrained sketch
is not an error — it rebuilds clean, extrudes fine, and looks finished.
A loop whose only feedback is "did the rebuild succeed" is structurally
blind to it. `finish_sketch` reports constraint status inline so the
model finds out at the moment it closes a sketch, not thirty minutes
later.

## Expect first-contact friction

`FeatureExtrusion3` takes 23 positional arguments and their order has
shifted across releases. Budget time for fixing signatures against your
own version, and read `get_feature_tree` output when something lands
wrong.

See [`../docs/can-claude-do-this.md`](../docs/can-claude-do-this.md) for
the architecture and the reasoning behind it.
