# Declutter prompt — make the SLAB simulation screen simple to use and understand

Written after the session-2 upgrade, for Claude Opus 5.5 or a comparable coding agent. Copy everything
below the line into a new session opened on this repository.

---

You are continuing **SLAB_GR_Simulation** (directory `SLAB_GR_Simulation/`). The physics engine, its data
and its validation are finished and verified; **do not change them**. This task is only about the
screen (`renders/`): make it uncluttered, easy to operate, and understandable by a curious
non-physicist within one minute, while keeping every number, diagram and label an expert needs one
click away.

Read first, in this order: `PROJECT_STATE.md`, `README.md`, `docs/viewer_architecture.md`, the modules
in `renders/src/`, `tests/viewer/ux_audit.mjs`, its last report `tests/viewer/ux_audit_report.json`,
and the screenshots in `renders/screenshots/ux/`. Run `python -m pytest tests -q`, the node tests in
`tests/viewer/`, and `node tests/viewer/ux_audit.mjs` before you change anything, and record the
baseline numbers.

## Hard rules (unchanged, plus three UI rules)

1. No change to `src/slab/`, to the exported data, or to any validated number. If the screen needs a
   presentation-only field, compute it in the viewer from existing columns.
2. Required labels stay on screen whenever their condition applies, **exactly once per view**, with
   the quoted text unchanged: "LOGARITHMIC VISUALIZATION — NOT TO SCALE" whenever a picture maps radius
   logarithmically; "Qualitative visualization — trajectory calculations remain relativistic." on the
   first-person view; the three-line Planck-threshold message at r_QG; "SPECULATIVE MODEL — NOT
   experimentally established." on every speculative screen, whose menu keeps the name "SPECULATIVE
   QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS". Nothing beyond r_QG is presented as fact.
3. **The user has no GPU.** Every default screen must work with WebGL unavailable. Anything that needs
   WebGL becomes an optional "Advanced 3D" view, loaded only on request, with a clear message when it
   cannot start.
4. Every plain-language sentence shown to a newcomer lives in one reviewed copy deck,
   `renders/src/copy.js`, and each entry names the export column or the `physics_notes.md` section it
   rests on. No new physics claims. Where a statement only holds in part of the journey (for example
   "speed relative to a hovering observer", which does not exist inside the horizon), the copy says so.
5. Expert detail is hidden, never deleted: every number the current dashboard shows remains reachable
   in a Details drawer, and all data downloads stay available.

## Who the screen is for

* **Newcomer (default):** wants the story. Where am I? Have I crossed the horizon? How long is left on
  my own watch? What do I feel? Is this well-tested physics? What happens next?
* **Student or expert (one click away):** wants every column, the diagrams, units, error estimates and
  the data files.

## Baseline clutter (measured by `tests/viewer/ux_audit.mjs`)

BASELINE_TABLE_PLACEHOLDER

## Design to implement

1. **One screen, three zones.** A top status line with one plain sentence and the physics-status
   badge; one main picture in the centre; a journey bar with Play at the bottom. A compact "vital
   signs" panel sits beside the picture on wide screens and becomes a bottom sheet on phones.
2. **Journey bar replaces the slider, the speed menu and the axis menu.** It shows the milestones as
   named chapters (Start, Photon sphere, Event horizon, 1 light-year, 1 AU, 1 km, 1 m, Atom, Nucleus,
   End of known physics), the observer's position, one big Play/Pause button, and three speed
   buttons. The playback-axis choice moves into Settings.
3. **Four picture choices instead of four crowded tabs:**
   * **Journey** (default, no WebGL): a clean 2D side view. Prefer true proportions around the
     observer with a scale bar in human units ("this bar = 1 km"); where a whole-journey overview needs
     a logarithmic map, show it small inside the journey bar with the required label.
   * **What you see:** the CPU first-person camera with only three controls (look toward the hole,
     look outward, drag to look) and a one-line caption; the rest moves to Settings.
   * **Spacetime map:** the Kruskal diagram, the Penrose diagram and the received-signal timeline,
     one at a time behind a three-way toggle, each with a two-sentence explainer.
   * **Beyond known physics:** the speculative page, visually separated from the three above (its own
     colour and position), opened through a short confirmation that says what it is.
   * **Advanced 3D** (WebGL, optional): the current 3D view, reached from Settings, loaded on demand
     as a separate bundle so the default page does not load three.js.
4. **Vital signs: at most four numbers by default,** three significant figures, human-scale units,
   each with a one-line meaning and an (i) tooltip:
   * distance to the centre (units switch automatically: light-years, AU, km, m, atom and nucleus sizes);
   * time on your own watch: since the start, and the classical estimate of what is left (labelled
     "classical estimate");
   * stretch across your 2 m body in Earth gravities (radial tidal acceleration / 9.80665 m/s²), with
     the exact value in the tooltip;
   * "Can you still get out?": outside the horizon "Yes, with enough rocket thrust"; inside "No: every
     possible path leads to smaller r".
   The physics-status badge uses words as well as colour: "Well-tested physics", "Standard physics,
   untested at this curvature", "Physics breaks down here", "Speculation".
5. **Explain panel:** one caption per chapter (at most two sentences) plus a "Why?" link to a short
   explainer; glossary tooltips for event horizon, tidal force, proper time, Planck curvature,
   Kruskal diagram and redshift.
6. **Details drawer (closed by default):** the full current dashboard, grouped into collapsible
   sections (Position and time, Curvature, Tidal forces, Distant observer, Numerics), with the data
   download links and a unit toggle (SI or GM/c² units).
7. **Guided tour:** on first visit a small card with three sentences and two buttons, "Take the
   guided tour" and "Explore freely". The tour plays chapter by chapter and pauses on each caption.
   Remember the choice in localStorage inside try/catch; the page must work without storage.
8. **Visual rules:** no overlapping panels; at most one floating element per corner of the picture;
   no duplicated banners; body text at least 14 px and labels at least 12 px; at most three font
   sizes; regime colours always paired with words; generous spacing; readable contrast in the dark
   theme. In the Advanced 3D view show labels only for the two nearest shells and remove the axes helper.
9. **Screen sizes:** the default screen fits 1366×768 without scrolling; it also works at 1920×1080
   and at 390×844 (phone: single column, bottom sheet, no horizontal scrolling, thumb-reachable controls).
10. **Performance without a GPU:** the default view draws a frame in under 16 ms on the CPU at
    1366×768; hidden views do not render; the first-person camera keeps its progressive CPU rendering.
11. **Accessibility:** existing keyboard shortcuts keep working and are listed behind "?"; visible
    focus; aria labels on controls; an aria-live status line that announces only chapter changes;
    prefers-reduced-motion respected; text alternatives for every canvas.

## Acceptance tests (automate them)

Turn `tests/viewer/ux_audit.mjs` into an asserting test, `tests/viewer/test_ux.mjs`, run at 1366×768
and 390×844 in the default state (Details closed) and at each chapter:

* zero overlapping floating panels and no horizontal overflow;
* at most 10 numbers and at most 150 words visible;
* zero text blocks smaller than 12 px;
* each required label present exactly once wherever its condition applies, and absent elsewhere;
* every picture except Advanced 3D works with WebGL disabled (launch Chromium with WebGL off) and
  shows a clear message for Advanced 3D;
* first render within 2 s headless; no console errors;
* all existing viewer tests still pass (update their selectors and the `window.SLAB_APP` API only
  where the redesign requires it).

Also check by hand that a newcomer can answer the five questions above from the default screen alone,
and save before/after screenshots of every chapter at both sizes to `renders/screenshots/ux/`.

## Deliverables

The redesigned viewer; `renders/src/copy.js`; `tests/viewer/test_ux.mjs`; a short illustrated user guide
`docs/ui_guide.md`; a "How to use the screen" section in `README.md`; an updated
`docs/viewer_architecture.md`; a before/after table of the audit numbers; and `PROJECT_STATE.md` updated
with status, files changed, tests passed or failed, known issues and the next task. Rebuild the bundle,
rerun every test suite, and do not touch the physics engine.
