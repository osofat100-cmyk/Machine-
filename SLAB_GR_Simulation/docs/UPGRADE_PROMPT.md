# Upgrade prompt for the next session (written for Claude Opus 5.5 or a comparable coding agent)

Copy the block below into a new session opened on this repository. It states what exists, what is
verified, what was cut short, and what to improve, in priority order.

---

You are continuing **SLAB_GR_Simulation** (directory `SLAB_GR_Simulation/` of this repository), a
validated numerical general-relativity simulation of an indestructible observer falling radially into a
10^18 M☉ Schwarzschild black hole, from 100 r_s through the horizon to the Planck-curvature radius r_QG,
plus an interactive 3D viewer. **Read `PROJECT_STATE.md`, `README.md`, `physics_notes.md`,
`validation_report.json` and `docs/viewer_architecture.md` first; the files are the source of truth.**
Run `python -m pytest tests -q` (26 tests, ~1 min) and `node tests/viewer/test_null_geodesics.mjs`
before changing anything; keep both green after every change and update `PROJECT_STATE.md`.

Hard rules that must survive any upgrade: the validated classical-GR integration stops at r_QG and prints
the Planck-threshold message; nothing beyond r_QG is presented as fact; speculative toy models stay under
the menu "SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS" with the banner
"SPECULATIVE MODEL — NOT experimentally established."; every visual simplification stays labelled
("LOGARITHMIC VISUALIZATION — NOT TO SCALE", "Qualitative visualization — trajectory calculations
remain relativistic."); checkpoints are never overwritten; anything unverifiable is marked
"INSUFFICIENT DATA TO VERIFY".

## What exists and is verified
* Physics engine (`src/slab`): ingoing Eddington–Finkelstein geodesics (second-order form + first-integral
  cross-check), Dormand–Prince 5(4) with PI control and ln r as independent variable inside, thrust mode,
  exact tidal eigenvalues for arbitrary 4-velocity, Kruskal/Penrose maps, light-cone slopes, Kretschmann,
  regime labels, versioned checkpoints/resume, CSV/JSON/HDF5 output. Validation TESTS 0–8 all pass
  (τ(r_s→r_QG) = 4GM/3c³ to 2e-13; u^r to 2e-11; DOP853 and first-integral cross-checks agree).
* Viewer (`renders/`): dashboard, log/linear/horizon/deep/curvature 3D views with exact light-cone glyph,
  Kruskal + Penrose diagrams, GPU first-person null-geodesic camera (CPU replica tested), speculative menu.
  Headless test `node tests/viewer/check_viewer.mjs` passes with zero console errors.

## Known gaps to close (priority order)
1. **Citations were never verified online** (the build environment had no web egress). Verify every entry of
   `references.md` and every citation in `physics_notes.md` (DOIs, volumes, pages, section numbers) and
   replace the "NOT RE-VERIFIED ONLINE" flags; fetch the CODATA 2022 values from NIST and confirm G, ħ, l_P;
   confirm the solar-mass value and cite its primary source; fetch the NASA Goddard visualization pages and
   cite them precisely.
2. **First-person camera limits.** The GPU tracer uses 32-bit floats, so it is disabled (labelled) below
   r = 1e-5 r_s. Implement a double-precision CPU/WebGPU path or a rescaled formulation (work in units of the
   observer's current r with M/r as a parameter, or split the ray integration at r = 2M) so that the view can
   be rendered down to r_QG; render the observer's view near the singularity (expected: the exterior sky
   compressed into a shrinking cone around the outward direction; document with references, e.g. Hamilton &
   Polhemus 2010). Add a real-GPU quality mode with progressive refinement; add the option of a physically
   motivated background (star catalogue or NASA all-sky image with attribution) instead of the synthetic grid;
   render the frequency-shift map itself (false colour with a labelled scale) in addition to the qualitative tint.
3. **Adversarial review not completed.** A 6-lens automated review produced 33 findings but most verification
   agents were cut off by a usage limit; 20 of them were triaged and fixed by hand (see PROJECT_STATE.md).
   Re-run an independent review of `src/slab` (equations, numerics, IO) and of the viewer physics
   (`renders/src/lightcone.js`, `causal.js`, `firstperson_core.js`), verify each finding by derivation or
   numerical reproduction, and fix what survives.
4. **Accelerated-observer tidal terms.** For the thrust mode the displayed tidal accelerations are the curvature
   part only; add the inertial (Rindler-type) differential terms of the deviation equation for accelerated
   worldlines and document them.
5. **Radiation/Doppler for the distant-observer panel.** Add the received-signal timeline (Schwarzschild t of
   emission vs reception, redshift factor as a function of reception time) as a plot in the causal tab.
6. **Kerr / Reissner–Nordström generalization** (optional): the engine is written for
   ds² = −f dv² + 2 dv dr + r² dΩ²; extending to Kerr requires new coordinates (ingoing Kerr) and a new light-cone
   and ray tracer. Only do this with new validation tests (e.g. ISCO radii, Carter constant conservation).
7. **Numerics polish.** Optional: quad-precision reference run (mpmath) of the full trajectory for the
   convergence table; dense output for the Dormand–Prince pair; a proper event function interface.
8. **Viewer polish.** Playback along proper time with a log-warped time axis; keyboard/touch controls; screenshot
   export; tests that assert rendered pixel content (e.g. the shadow radius in the first-person view at r = 5 r_s
   against the analytic value, the cone tilt at the horizon), not only "no console errors".
9. **Packaging.** `pip install -e .` packaging with a console entry point; a GitHub Actions workflow running the
   Python tests and the headless viewer test (Chromium + SwiftShader).

When you finish, regenerate `validation_report.json`, `docs/validation_report.md`, the render export
(`python run_simulation.py --speculative`), rebuild the viewer (`renders/build/build.sh`), rerun both test
suites, and update `PROJECT_STATE.md` with: implementation status, equations implemented, tests passed/failed,
known numerical issues, files changed, next technical task, and last successful checkpoint.
