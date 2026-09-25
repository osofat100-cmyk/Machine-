# SLAB_GR_Simulation

Numerical general-relativity simulation of an indestructible observer falling radially into a
hypothetical, non-rotating, uncharged **Stupendously LArge Black hole (SLAB)** of mass
**M = 10^18 M☉**, followed from r = 100 r_s, through the event horizon, down to the radius
r_QG where the Kretschmann curvature reaches the Planck curvature 1/l_P^4 — the point where
classical GR stops being trustworthy and the validated simulation **stops**.

This is a physics simulation first; the interactive 3D viewer renders precomputed, validated
trajectories and never integrates the observer's motion itself.

| quantity | value (computed at run time from CODATA constants) |
|---|---|
| M | 1.98847e48 kg |
| r_s = 2GM/c² | 2.95334e21 m = 312,168 ly |
| GM/c³ | 156,084 yr |
| proper time horizon → r = 0 (E = 1 radial geodesic) | 4GM/(3c³) = 208,112 yr |
| r_QG (K = 1/l_P⁴) | 1.3877e-16 m = 4.70e-38 r_s |

## Two strictly separated regimes

* **REGIME A — classical GR (validated):** exact Schwarzschild solution, integrated in
  horizon-regular ingoing Eddington–Finkelstein coordinates. Everything in `data/`,
  `checkpoints/` and the main viewer tabs.
* **REGIME B — unknown quantum-gravity region:** at r_QG the program prints
  `PLANCK-CURVATURE THRESHOLD REACHED. CLASSICAL GENERAL RELATIVITY IS NO LONGER RELIABLE.
  NO EXPERIMENTALLY VERIFIED THEORY DETERMINES THE CONTINUATION.` and stops. The optional toy
  models under the menu **"SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS"**
  (`src/slab/speculative/`, `data/speculative/`) are kept visually and numerically separate and
  carry the permanent banner "SPECULATIVE MODEL — NOT experimentally established."

## Quick start

```bash
cd SLAB_GR_Simulation
pip install -r requirements.txt            # numpy scipy h5py mpmath sympy pytest
python run_simulation.py --speculative     # validation gate (TESTS 0–8) -> simulation -> data -> render export
python -m pytest tests -q                  # physics tests + CLI checkpoint/resume test
# open renders/viewer.html in a browser (works from file://; no network needed)
node tests/viewer/check_viewer.mjs         # headless viewer smoke test + screenshots (optional)
```

Useful options: `--resume` (continue from the newest checkpoint in `simulation_state.json`),
`--stop-after-milestone horizon`, `--thrust 9.81` (1 g inward rocket), `--E 0.95 --r0 10`
(fall from rest at finite radius), `--L 3.5` (equatorial plunge with angular momentum),
`--validate-only`. Scenario runs are written to `data/scenarios/<tag>/`.

## Layout

```
src/slab/            physics engine (constants, metric, curvature, geodesic, integrators, trajectory, io, validation)
src/slab/speculative toy models (NOT established physics)
tools/               symbolic re-derivation of the EF curvature (sympy)
tests/               pytest suite; tests/viewer: headless viewer tests and null-geodesic checks
data/                trajectory.csv, trajectory.h5, trajectory_metadata.json, segments/, speculative/, scenarios/
checkpoints/         versioned checkpoints (never overwritten): ckpt_<index>_<milestone>_v<version>.json
renders/             viewer.html + viewer.bundle.js + trajectory_data.js (+ src/, build/, screenshots/)
docs/                viewer architecture and drafts
references/          reference notes
simulation_config.json / simulation_state.json / validation_report.json
README.md / physics_notes.md / references.md / PROJECT_STATE.md
```

## Method in one paragraph

Geometrized units G = c = M = 1 (r_s = 2). The observer's worldline is integrated from the
second-order geodesic equation (with an optional radial thrust 4-acceleration) in ingoing
Eddington–Finkelstein coordinates, which are regular at r = r_s, with a Dormand–Prince RK5(4)
adaptive integrator whose independent variable is ln r inside the hole (τ outside where a
turning point can occur). The 10^41-decade range in r is therefore covered with ~3000 steps,
the step in r and τ shrinking automatically as the curvature K = 48G²M²/(c⁴r⁶) grows, and the
integrator never steps through r = 0. The Killing energy is carried as an independent
well-conditioned variable so that the comoving frame and the tidal tensor remain accurate
deep inside. Kruskal–Szekeres/Penrose coordinates, light-cone orientation, the Kretschmann
scalar, the tidal eigenvalues and the distant-observer quantities are computed analytically
from the state at every step. See `physics_notes.md` for equations and citations and
`validation_report.json` for the automated benchmarks.

## Validation (automated, must pass before the simulation is marked validated)

TEST 0 constants · TEST 1 r_s = 2GM/c² · TEST 2 horizon regularity of the EF chart ·
TEST 3 E = 1 geodesic vs dr/dτ = −c√(r_s/r) · TEST 4 τ(horizon→0) = 4GM/3c³ · TEST 5
Kretschmann by explicit contraction · TEST 6 r_QG numerical root vs closed form vs mpmath ·
TEST 7 conserved quantities · TEST 8 convergence in tolerance + SciPy DOP853 and first-integral
cross-checks. Results: `validation_report.json`.
