# PROJECT_STATE.md — chatbot / agent project journal

**The files in this directory are the source of truth. Do not rely on conversational memory.**

## How to continue this project in a new session

1. Read this file, then `README.md`, `physics_notes.md`, `simulation_config.json`, `simulation_state.json`.
2. `python -m pytest tests -q` must pass (≈15 s) before touching physics code.
3. To continue an interrupted run: `python run_simulation.py --resume` (reads `simulation_state.json`,
   loads the newest checkpoint in `checkpoints/`, reloads finished segments from `data/segments/`).
4. Viewer: edit `renders/src/*.js`, rebuild with `renders/build/build.sh`, test with
   `node tests/viewer/check_viewer.mjs`, look at `renders/screenshots/`.
5. Update this file after every meaningful change.

## Current implementation status (2026-09-25)

| component | status |
|---|---|
| physics engine (EF geodesics, DP5(4), ln r variable, thrust, first-integral cross-check) | done, validated |
| validation suite TESTS 0–8 (`src/slab/validation.py`, `validation_report.json`) | all passing |
| data output (CSV, JSON, HDF5, segment archives, render export) | done |
| versioned checkpoints + resume (`--stop-after-milestone`, `--resume`) | done, tested (`tests/test_physics.py::test_cli_stop_and_resume_matches_full_run`) |
| speculative toy models (Hayward, Bardeen, Dymnikova) | done, separated, banner |
| viewer skeleton (dashboard, playback, data layer, headless test) | done |
| viewer modules: 3D scene + light cones, causal diagram, first-person ray tracer, speculative menu | IN PROGRESS (see below) |
| docs: physics_notes.md, references.md | IN PROGRESS |

## Equations implemented (see physics_notes.md for details and citations)

* Schwarzschild in ingoing EF form: ds² = −f dv² + 2 dv dr + r² dΩ², f = 1 − 2M/r.
* Christoffel symbols of that metric (hand-derived, sympy-verified in `tools/derive_ef_curvature.py`).
* Second-order geodesic equation with optional 4-acceleration a = −α n, n = (u^v, E, 0, 0).
* First integrals E = f u^v − u^r, L = r² sin²θ u^φ; g(u,u) = −1.
* Analytic E = 1 radial solution: u^r = −√(2M/r), u^v = x/(1+x), v(r) = −4M B(x), τ(r) = −(4M/3)x³ (x = √(r/2M)).
* Riemann tensor in EF coordinates; Kretschmann K = f''² + 4f'²/r² + 4(1−f)²/r⁴ = 48M²/r⁶.
* Tidal tensor E_ij = R_{μανβ} e_i^μ u^α e_j^ν u^β in the comoving frame. Outputs use the EXACT
  closed form for an arbitrary 4-velocity with transverse rapidity t² = r²[(u^θ)² + sin²θ (u^φ)²]:
  λ = (−(2+3t²), 1+3t², 1) × M/r³ (radial, transverse ⊥ motion, transverse ∥ motion); reduces to
  (−2M/r³, M/r³, M/r³) for radial motion. Cross-checked against the explicit contraction of the
  EF Riemann tensor, a static-frame Lorentz boost and a numeric 4×4 frame matrix
  (`tests/test_physics.py::test_tidal_exact_eigenvalues_vs_independent_methods`).
* Kruskal map U = −(r/2M−1) e^{r/2M} e^{−v/4M}, V = e^{v/4M}; compactified (atan) coordinates.
* Light cones: dr/dt_EF = f/(2−f) (outgoing), −1 (ingoing).
* Distant observer: t = v − r_*, dr/dt, 1+z = u^v − 2u^r/f.
* r_QG = (48 G² M² l_P⁴ / c⁴)^{1/6}.

## Tests passed / failed

* `validation_report.json`: 9/9 tests passed (all checks), see file for numbers.
* pytest: see latest run in this journal's log below.

## Known numerical issues / caveats

* E = f u^v − u^r evaluated from the 4-velocity suffers catastrophic cancellation for r ≪ M
  (both terms ~ √(2M/r) ~ 1e19 at r_QG); the engine therefore carries the Killing energy as a
  separate state component (E_killing) and reports the conditioned drift. This is a
  property of the (u^v, u^r) representation, not an integration error (TEST 7).
* Kruskal coordinates overflow double precision for |v − v_horizon| ≳ 2800 M; the export
  stores null there and the compactified coordinates always.
* Proper time deep inside is a converging series; τ_total is stored as a double
  (resolution 1e-16 relative) — the per-segment increments (`dtau_segment_geo` in the
  milestone table) keep full relative precision at every scale.
* The τ-mode integrator (fall from rest / L ≠ 0 outside) had an FSAL aliasing bug in the
  event-located final step (fixed 2026-09-25; regression covered by the cycloid check in
  `tests/test_physics.py`).
* g(u,u) + 1 is likewise cancellation-limited for L ≠ 0 deep inside (u^φ = L/r² ~ 1e74 at r_QG);
  `norm_residual_conditioned` is the meaningful diagnostic.
* Equatorial motion: cos(π/2) = 6e-17 in floating point seeds a spurious u^θ through the source
  term sinθ cosθ (u^φ)²; the RHS snaps |cos θ| < 1e-14 to 0 so the plane is preserved exactly.
* The explicit index contraction of the coordinate-basis Riemann tensor overflows/cancels for
  L ≠ 0 deep inside (terms ~1e333); it is kept only as a cross-check where conditioned.
* `tau_to_center_est` is exact only for the E = 1 radial geodesic (asymptotic estimate otherwise; labelled).

## Files changed in the last session

Initial creation of the whole project (see git log): src/slab/*, src/slab/speculative/*, tools/*,
tests/*, run_simulation.py, simulation_config.json, data/*, checkpoints/*, renders/* (skeleton),
docs/*, README.md, PROJECT_STATE.md, requirements.txt.

Scenario runs available in `data/scenarios/` (see its README.md): thrust_1g (1 g inward rocket:
reaches the horizon after 17.3 proper years with E ≈ 3.2e7 and spends only 0.0097 yr inside),
plunge_L3.5 (equatorial plunge with L = 3.5 GM/c: interior proper time 1.07e5 yr),
rest_at_10rs (fall from rest at 10 r_s, matches the cycloid solution to 2e-12).

## Next technical task

1. Integrate the viewer modules (scene3d/lightcone, causal, firstperson, speculative) from the
   implementation agents; rebuild; run `node tests/viewer/check_viewer.mjs`; review screenshots.
2. Apply confirmed findings of the adversarial physics review; re-run validation.
3. Finalize `physics_notes.md` and `references.md` from `docs/drafts/`.
4. Commit, push, open PR.

## Last successful checkpoint

`checkpoints/ckpt_14_r_QG_v001.json` (final milestone of the validated run; see `simulation_state.json`).
