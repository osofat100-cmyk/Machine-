# Can I do what that video shows, and how?

*A reply to the MecAgent post: "one prompt, 11 parts, 1 main assembly,
35-minute run" in SolidWorks 2026.*

## Short answer

**The agent part, yes — and it is already built and running in this
repository.** One prompt's worth of intent goes in; eleven parametric
parts and one assembly come out, verified and exported. You can run it
right now on any machine with Python.

**The SolidWorks part, not from here.** SolidWorks is Windows-only COM
software that needs a licence and a running GUI session. This session is
a Linux container. That is not a limit on what I can *write* — the
harness that drives SolidWorks is in `solidworks_harness/` and its
agent-facing half is tested — it is a limit on where it can *execute*.
It has to run on your Windows machine, next to your licence.

Those two halves are worth separating carefully, because the interesting
engineering is almost entirely in the first one.

---

## What the video is actually claiming

Strip out the branding and there are four distinct claims:

| Claim | Difficulty |
|---|---|
| One prompt → many parts and an assembly | Moderate. It is a long agentic loop. |
| Native SolidWorks output with a feature tree | **The hard one.** See below. |
| Parametric and fully editable | Moderate, and partly a consequence of the above. |
| Assembly rotates about its intended axes | Moderate — this is mates, not geometry. |

Their own caveats are the honest and interesting part: *not yet fully
constrained*, with the remaining problems "mainly found in the sketches
used to define the features," and "still far from something truly
manufacturable." Hold onto that. It is the most informative sentence in
the post, and I will come back to why.

---

## The one thing that genuinely cannot be shortcut

There is a fork in the road here that decides the whole shape of the
problem.

A `.SLDPRT` file is an undocumented binary OLE compound document. You
cannot write one directly, and nobody sensible tries. So there are
exactly two ways to produce SolidWorks geometry:

1. **Drive the SolidWorks API.** Have the application itself build the
   part, feature by feature, through COM calls. The result is a native
   file with a real feature tree, because SolidWorks made it.
2. **Generate a neutral solid (STEP/IGES) and import it.** Easy,
   portable, works anywhere — and produces a *dumb solid*. No feature
   tree, no sketches, no design intent. An engineer who opens it can
   move the whole body and nothing else.

Route 2 is what most "AI CAD" amounts to, and the difference is not
cosmetic. A dumb solid is a photograph of a part; a feature tree is the
recipe. **If MecAgent is producing a genuine feature tree, they are on
route 1**, and that is the part of their result that deserves respect.
It means an actual agent loop sitting on the SolidWorks API, which is
exactly what I have written in `solidworks_harness/`.

I want to be plain about this rather than blur it: what I *ran* here is
route 2 with a programmatic model behind it. What I *wrote* for you is
route 1. They are different deliverables and I am not going to pretend
the STEP file is a feature tree.

---

## How the harness works

The architecture is not complicated. Nearly all the difficulty is
concentrated in one place, and it is not where people expect.

```
   prompt
     │
     ▼
 ┌─────────┐   tool calls    ┌──────────────┐   COM    ┌────────────┐
 │  model  │ ──────────────► │   harness    │ ───────► │ SolidWorks │
 │         │ ◄────────────── │ (20 tools)   │ ◄─────── │            │
 └─────────┘   what happened └──────────────┘  state   └────────────┘
                   ▲
                   │
          the return arrow is the whole game
```

### The tool surface

Twenty tools, in `solidworks_harness/swbridge/tools.py`. Roughly what a
first-year CAD course covers:

- **sketching** — `start_sketch`, `sketch_circle`, `sketch_rectangle`,
  `sketch_line`, `finish_sketch`
- **features** — `extrude`, `cut_extrude`, `revolve`, `fillet_edges`,
  `circular_pattern`
- **assembly** — `new_assembly`, `insert_component`, `add_mate`
- **reading back** — `get_feature_tree`, `rebuild_and_check`,
  `check_constraints`, `take_screenshot`, `get_mass_properties`

Three design decisions are doing most of the work:

**Keep it small.** SolidWorks exposes something like two thousand API
calls. Wrapping them all would be worse, not better — the model would
burn its attention choosing between eight kinds of extrude instead of
thinking about the part.

**Millimetres in, metres out.** The SolidWorks API is metres and radians
internally no matter what the document's display units say. Pass `50`
meaning 50 mm and you get a fifty-metre part that rebuilds perfectly
cleanly. Convert once, at the boundary (`enums.mm`), and never let a raw
number reach a COM call.

**Errors come back as text, never as exceptions.** An exception ends the
turn. A returned string — *"fillet of 3mm on 12 edges failed, the radius
is probably larger than the adjacent geometry allows, try smaller"* — is
something the model can read and act on. Every tool is wrapped to
guarantee this.

### The return arrow

Generating geometry is the easy half. Being told you got it wrong, in
terms specific enough to repair, is the half that decides whether the
output is worth anything. Four channels, in ascending order of
usefulness:

1. `get_feature_tree` — what exists
2. `rebuild_and_check` — what SolidWorks thinks is broken
3. `check_constraints` — **what is under-defined**
4. `take_screenshot` — what it actually looks like

---

## Why "not yet fully constrained" happens

This is the most instructive thing in their post, and it is not a
mystery — it falls directly out of the feedback loop above.

**An under-constrained sketch is not an error.** It rebuilds clean. It
extrudes. It looks completely finished. SolidWorks will never volunteer
a complaint, because nothing is wrong in the sense that a rebuild
understands. It is merely *fragile*: change any nearby dimension and the
geometry moves in ways nobody intended.

So a loop whose only feedback is "did the rebuild succeed" is
structurally blind to it, and will converge happily on models that are
under-defined everywhere. The fix is to ask a different question, and
SolidWorks will answer it: `ISketch::GetConstrainedStatus` reports, per
sketch, whether it is fully defined. In the harness that is
`check_constraints`, and `finish_sketch` reports the status inline so
the model learns about a loose sketch *at the moment it closes it*
rather than 30 minutes later.

That is the difference between an agent that produces a demo and one
that produces a model an engineer will accept. The failure mode it
guards against — clean rebuild, loose sketches — is precisely the one
they describe.

The same argument covers the screenshot tool. A great many defects are
geometrically legal and obviously wrong on sight, and no rebuild check
will ever catch them. I hit exactly one while building this, and it is
worth reporting: my gripper came out with **both jaws folding outward,
away from each other**. Every solid check passed. Eleven single
watertight solids, zero interference, kinematics exact to 2.6e-13 mm.
The gripper simply could not grip. I found it by rendering the arm and
looking at it. That is the entire argument for putting an eye in the
loop, and it cost me one commit to learn.

---

## What I actually built and ran

In `cad/` — a parametric 6-DOF arm, generated programmatically on an
OpenCascade kernel (build123d / OCCT 7.9.3), which runs here on Linux
with no SolidWorks and no licence.

Eleven parts, fifteen instances, one assembly:

| # | Part | Notes |
|---|---|---|
| 1 | base flange | 150 mm, 4 × M8 on a 120 bolt circle |
| 2 | J1 turret | waisted column, cable bore |
| 3 | shoulder yoke | J2 clevis |
| 4 | upper arm | I-section, 260 mm between bores |
| 5 | elbow yoke | J3 clevis |
| 6 | forearm | tapered tube, 215 mm |
| 7 | wrist housing | J4 roll bearing |
| 8 | wrist yoke | J5 pitch clevis |
| 9 | tool flange | ISO 9409-1-50-4-M6 |
| 10 | gripper finger | ×2 |
| 11 | actuator can | ×4, one part at four joints |

Total 7.19 kg in 6061-T6, 573 mm nominal reach, whole build in **10.5
seconds**.

### It is checked, not just generated

`cad/robot_arm/verify.py` re-derives what the model should be and
complains when the solids disagree:

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

The kinematics check is the one I would point at. The joint chain is
computed twice — once by the geometry kernel placing solids, once from
scratch with 4×4 matrices — and the two must agree. Two independent
implementations agreeing is worth far more than one that merely runs.

The axis check is the direct analogue of their "rotates correctly around
its intended axes": with every other joint at zero, each joint's tool
frame must equal a pure rotation about its intended axis, exactly.

These checks earned their place. Writing them surfaced three real
defects I would otherwise have shipped: a wrist housing that was
**two disconnected solids** (the spigot floated 4 mm clear of its bore),
and two fillets failing silently. All three are fixed, and the checks
are why I know that.

### And it is genuinely parametric

Every dimension lives in one dataclass. Re-driving the model across
seven quite different parameter sets — reach from 368 mm to 868 mm, wall
from 4 mm to 9 mm — rebuilds and re-passes every check, every time:

```
OK  default        6.5s  reach=573.0mm
OK  long-reach     6.4s  reach=868.0mm
OK  compact        5.9s  reach=368.0mm
OK  heavy-wall     6.8s  reach=573.0mm
OK  thin-wall      6.2s  reach=573.0mm
OK  big-base       6.9s  reach=573.0mm
OK  wide-gripper   6.2s  reach=573.0mm
```

That is a stronger parametric claim than a feature tree with
under-defined sketches, and I want to be fair about why: it is also an
*easier* one. Code has no sketch-solver to under-constrain. The
constraint problem they are wrestling with is a cost of route 1 — the
price of producing something a mechanical engineer can open and edit in
the tool they actually use.

---

## Honest comparison

| | MecAgent (their claims) | What runs in `cad/` | What's in `solidworks_harness/` |
|---|---|---|---|
| Output | native SolidWorks + feature tree | STEP / STL / SVG | native SolidWorks + feature tree |
| Editable in SolidWorks GUI | yes, feature by feature | imported as a dumb solid | yes |
| Parametric | yes, not fully constrained | yes, fully re-drivable | depends on the run |
| Verified | rebuild + visual | 8 automated checks | rebuild + constraints + visual |
| Runtime | ~35 min | 10.5 s | comparable to theirs |
| Runs here | — | **yes** | no — needs Windows |

The row that matters is "editable in the GUI." Everything else I can
match or beat; that one is theirs, and it is the one an engineer cares
about.

---

## What it would take to run the SolidWorks path

On a Windows machine with SolidWorks installed:

```bat
pip install anthropic pywin32
python -m swbridge.probe          :: check the harness's assumptions first
python -m swbridge.agent_loop ^
    --prompt "A 6-DOF robot arm, 500mm reach, aluminium" ^
    --out C:\work\arm
```

Two warnings I would rather give up front than have you discover.

**The COM half is unverified.** I have no SolidWorks to test against, so
I will not claim it works. What *is* tested is the agent-facing half:
all 20 tool schemas generate and validate. The COM calls are written
against the documented API, and `probe.py` exists specifically to check
the assumptions I could not — in particular the `GetConstrainedStatus`
enum values, where a wrong constant would silently report loose sketches
as fine. **Run `probe.py` first.** Expect to fix some argument
signatures on first contact; `FeatureExtrusion3` alone takes 23
positional arguments and their order has shifted across releases.

**A 35-minute run is a real cost.** Hundreds of tool calls with a
growing transcript. Enable prompt caching, and be aware that a screenshot
every few steps is the single largest consumer of context.

---

## What I'd tell you if you're deciding whether to chase this

The gap between "generates plausible CAD" and "generates CAD an engineer
accepts" is almost entirely the verification loop, not the generation.
Generation is the part that looks impressive in a video. Checking is the
part that decides whether anyone can use the output.

MecAgent's own caveat says exactly this, in their own words: the
geometry arrives, the constraints do not. If you build in this space,
build the return arrow first. I found three real defects in eleven parts
by writing checks, and a fourth — the gripper that opened backwards — by
rendering the thing and looking at it. That ratio is not unusual, and it
is not going to change.

---

*Generated artifacts, drawings, and the full source are in this
repository. Start with `cad/README.md` to run it.*
