# PROJECT_STATE.md — chatbot / agent project journal

**The files in this directory are the source of truth. Do not rely on conversational memory.**

## How to continue this project in a new session

1. Read this file, then `README.md`, `physics_notes.md`, `simulation_config.json`, `simulation_state.json`.
2. Python: `python -m pytest tests -q` (~75 tests, ~1 min) must pass before touching physics code;
   `python run_simulation.py --validate-only` must report 11/11.
3. Viewer: `cd renders/build && npm ci` once, then `./build.sh`, `npm run test:physics` (no browser) and
   `npm run test:viewer` (headless Chromium, software GL). Look at `renders/screenshots/`.
4. Continue an interrupted run with `python run_simulation.py --resume` (or `slab-sim --resume`).
5. Next task prompts: `docs/DECLUTTER_PROMPT.md` (screen redesign, next), `docs/UPGRADE_PROMPT.md` (done in
   session 2 except the items listed under "Open items").
6. Update this file after every meaningful change.

## Current implementation status (2026-09-26, end of session 2)

| component | status |
|---|---|
| physics engine (EF geodesics, DP5(4) with PI control and dense output, ln r variable, thrust with split windows, first-integral cross-check) | done, validated |
| accelerated-observer inertial term (`inertial_diff_radial_m_s2`, `radial_total_diff_m_s2`) | done, TEST 9 |
| distant observer's received-signal timeline (`u_ret_geo`, `t_receive_years`, `signal_timeline` table) | done, TEST 10 |
| high-precision (35-digit mpmath) references for scenarios without closed form | done, in TEST 8 |
| validation suite TESTS 0–10 (`src/slab/validation.py`, `validation_report.json`, `docs/validation_report.md`) | 11/11 passing |
| data output (CSV, JSON, HDF5, segment archives, render export) regenerated with the current engine | done; guarded by `test_committed_outputs_match_current_engine` |
| versioned checkpoints + resume | done; interior-agreement and never-overwritten checks in the resume test |
| speculative toy models (Hayward, Bardeen, Dymnikova), first-integral form in core units | done, separated; `tests/test_speculative_models.py` |
| first-person camera: CPU double-precision renderer down to r_QG, star catalogue, log10 g map, optional GPU | done; `test_firstperson.mjs`, `test_firstperson_browser.mjs` |
| viewer: log-τ playback, keyboard/touch controls, PNG export, signal-timeline plot, pixel tests | done; `test_viewer_data.mjs`, `test_pixels_browser.mjs`, `test_controls_browser.mjs` |
| packaging: `pip install -e .` → `slab-sim`; pinned viewer toolchain; GitHub Actions CI | done; CI green on PR #3 |
| citations and constants verified by web search (WebFetch blocked) | done; statuses in `references.md`, `docs/additions/citations.md` |
| UX clutter audit (`tests/viewer/ux_audit.mjs`) + declutter prompt | done; redesign itself is the next task |

## Equations implemented (details and citations in physics_notes.md)

* Schwarzschild in ingoing EF form ds² = −f dv² + 2 dv dr + r² dΩ²; Christoffel symbols (sympy-verified).
* Geodesic equation with 4-acceleration a = −α n/|n|; first integrals E, L; radial-rocket law E(r) = E₀ + α(r₀ − r).
* Analytic E = 1 fall (u^r = −√(2M/r), τ(r_s→0) = 4GM/3c³); cycloid for fall from rest.
* Kruskal and compactified coordinates; light-cone slopes f/(2 − f) and −1.
* Riemann tensor, Kretschmann 48M²/r⁶; exact tidal eigenvalues −(2+3t²), 1+3t², 1 (× M/r³).
* Proper-reference-frame differential acceleration δa = −(E + a aᵀ)ξ.
* Distant observer: t = v − r_*, u = v − 2r_*, 1 + z = du/dτ = u^v − 2u^r/f, late-time 1 + z ∝ e^{u/4M}.
* r_QG = (48 G²M² l_P⁴/c⁴)^{1/6} = 1.3877e-16 m.
* Camera: ξ = E u + a n, E_ph = E + a dₙ, b = L/E_ph, g = 1/E_ph; orbit integral for ψ_∞; b² = 27 boundary.

## Tests passed / failed (2026-09-26)

* pytest: all pass (1 skipped: entry-point check runs only when the package is installed).
* `run_simulation.py --validate-only`: 11/11. Informational rows are rendered as "info".
* `npm test` in renders/build: all Node and browser suites pass, zero console errors.
* GitHub Actions (PR #3): Python and Node jobs green on the latest pushed commit.

## Known numerical issues / caveats

* E(u) = f u^v − u^r and g(u,u) cancel catastrophically deep inside; the engine carries E_k separately and
  reports conditioned residuals.
* τ_total is a double (~1333 GM/c³): interior increments are exact per segment (`dtau_segment_geo`), not in
  τ_total's last digits. The same limits the toy models' exported τ inside their cores.
* The render export resamples engine steps linearly (in log r); the viewer evaluates steep functions
  (1 + z, light-cone slopes) at the displayed r instead of interpolating them.
* The first-person GPU mode (float32) is limited to r > 1e-5 r_s; the CPU default has no such limit.
* The ring of blueshifted sky near r_QG is far narrower than a pixel (documented in the camera notes).

## Review of session 2 (27 findings; verification agents were cut off by a usage limit, so each finding
was re-checked by hand before fixing)

Fixed: ln r segments that fail now raise instead of being recorded as reached; dense output refuses to
extrapolate; an event hit exactly at a step end is accepted without bisection; tautological validation
checks replaced (inertial column now checked against |a| recomputed from the exported 4-acceleration;
r_QG eigenvalue against the numeric frame matrix) or marked informational; informational rows no longer
render as "ok"; the benchmark is pinned to the configuration file and r0 = 100 r_s (CLI overrides no
longer leak into it) and scenario runs write their report to their own directory; unknown
`--stop-after-milestone` names and `--resume` without state are rejected with a message;
`checkpoint_list()` returns the newest version per milestone; every output column documented (test);
stale committed outputs regenerated and guarded by a test; resume test checks interior agreement,
unchanged checkpoints and all HDF5 columns; toy models: wording ("not validated"), root-found radii,
recorded parameters, a meaningful normalization diagnostic, new tests; docs (test counts, camera text,
inertial term, signal timeline, L ≠ 0 remaining-time asymptote, 99.997 %, fall-from-rest example,
Regime A sentence, ~3500 steps, 39 decades).

## Files changed in session 2

Engine: `src/slab/{accelerated,signals,reference,cli}.py` (new), `integrators.py`, `trajectory.py`, `io.py`,
`validation.py`, `geodesic.py`, `constants.py` (sources, l_P uncertainty), `speculative/models.py`,
`metric.py`, `curvature.py` (docstrings). Viewer: `renders/src/firstperson*.js`, `starcatalog.js`, `data/*`,
`main.js`, `data.js`, `dashboard.js`, `causal.js`, `scene3d.js`, `lightcone.js`, `speculative.js`, `viewer.html`.
Tests: `tests/test_{accelerated_frame,dense_output,signal_timeline,packaging,citations,speculative_models}.py`,
`tests/test_physics.py`, `tests/viewer/*`. Packaging/CI: `pyproject.toml`, `run_simulation.py`,
`renders/build/{package.json,package-lock.json,build.sh}`, `/.github/workflows/slab-gr-simulation.yml`.
Docs: `physics_notes.md` (§6, §10, §11, §13, §14 updated; §15 camera, §16 viewer added), `README.md`,
`references.md`, `docs/additions/*.md` (detailed notes of each workstream), `docs/viewer_architecture.md`,
`docs/DECLUTTER_PROMPT.md`, this file. Outputs regenerated: `data/**`, `checkpoints/*_v002.json` and (after the review fixes) `*_v003.json`,
`renders/trajectory_data.js`, `renders/viewer.bundle.js`, `validation_report.json`, screenshots.

## Open items (not done in session 2)

1. Screen redesign for newcomers — see `docs/DECLUTTER_PROMPT.md` (the next task; its baseline table was measured on commit `deea531`).
2. Kerr / Reissner–Nordström generalization (optional in the upgrade prompt; not started).
3. An independent review of the camera code by a second agent was cut off by a usage limit; the
   camera's own test suite (shadow radius vs analytic, EF integration vs quadrature to r_QG,
   classifier vs integration) passes.
4. MTW section/equation numbers remain unverified (search could not confirm them); see `references.md`.

## Last successful checkpoint

`checkpoints/ckpt_14_r_QG_v003.json` (final milestone of the regenerated validated run; see `simulation_state.json`).
