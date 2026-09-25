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

## Installation

Requirements: Python ≥ 3.11 (tested with 3.11); for the viewer toolchain and its tests Node 22 (tested; `engines` allows ≥ 18).
No GPU is needed anywhere: the headless viewer tests use Chromium's SwiftShader software GL.

```bash
cd SLAB_GR_Simulation
python -m venv .venv && . .venv/bin/activate    # optional but recommended
pip install -e ".[test,tools]"                  # package `slab` (src layout) + console command `slab-sim`
                                                # extras: test = pytest, tools = sympy (tools/derive_ef_curvature.py)
```

Runtime dependencies (declared in `pyproject.toml`): numpy, scipy, h5py, mpmath. `requirements.txt` holds the same
list plus the extras for a no-install setup (`pip install -r requirements.txt`, then use `python run_simulation.py`).

Viewer toolchain (only needed to rebuild `renders/viewer.bundle.js` or run the headless tests; the committed
bundle runs as is):

```bash
cd renders/build && npm ci                      # exact versions from package-lock.json: esbuild, three, playwright-core
npm run browser:install                         # only if no Chromium is available: Chromium pinned to playwright-core's version
```

## Quick start

```bash
slab-sim --speculative                     # validation gate (TESTS 0–8) -> simulation -> data -> render export
python -m pytest tests -q                  # physics/numerics/IO tests incl. CLI checkpoint/resume and packaging checks
# open renders/viewer.html in a browser (works from file://; no network needed)
node tests/viewer/test_null_geodesics.mjs  # first-person ray-tracer physics checks (CPU replica of the shader)
node tests/viewer/check_viewer.mjs         # headless viewer smoke test + screenshots (needs Chromium, see below)
```

`slab-sim` and `python run_simulation.py` run the same pipeline (`src/slab/cli.py`) with the same flags;
`run_simulation.py` needs no installation and always uses its own directory as the project directory.
`slab-sim` finds the project directory (the one holding `simulation_config.json`, `checkpoints/`, `data/`,
`renders/`) in this order: `--project-dir DIR`, the environment variable `SLAB_PROJECT_DIR`, the current directory
or a parent of it (also looking into a `SLAB_GR_Simulation/` subdirectory, so it works from the repository root),
the source checkout of an editable install. Run anywhere inside this repository it therefore uses exactly the
directory `run_simulation.py` uses. It prints the directory it picked; `slab-sim --help` lists all flags.

Useful options: `--resume` (continue from the newest checkpoint in `simulation_state.json`),
`--stop-after-milestone horizon`, `--thrust 9.81` (1 g inward rocket), `--E 0.95 --r0 10`
(fall from rest at finite radius), `--L 3.5` (equatorial plunge with angular momentum),
`--validate-only`, `--out-dir DIR`, `--project-dir DIR` (`slab-sim` only). Scenario runs are written to
`data/scenarios/<tag>/`. After `--stop-after-milestone`, `slab-sim` prints the complete resume command (with the
`--project-dir`, `--out-dir`/`--tag` and `--skip-validation` it needs); `run_simulation.py` keeps its historic hint.

Headless viewer tests find the browser via `CHROMIUM_PATH`, else `/opt/pw-browsers/chromium` if it exists, else
playwright-core's own Chromium (`npm run browser:install`). From `renders/build`: `npm run build` (= `build.sh`),
`npm test` (= `npm run test:physics` for every Node-only `tests/viewer/test_*.mjs`, then `npm run test:viewer` for
the headless browser tests).

## Continuous integration

`.github/workflows/slab-gr-simulation.yml` (repository root) runs on every push and pull request that touches
`SLAB_GR_Simulation/**` (or the workflow itself), and on manual dispatch:

* **Python 3.11 job:** `pip install -e SLAB_GR_Simulation[test,tools]`; `python -m pytest tests -q`;
  `python run_simulation.py --validate-only`; the sympy re-derivation `tools/derive_ef_curvature.py` (fails on any
  mismatch); a `slab-sim` smoke run from the repository root (short `--E 0.95 --r0 10` scenario that must end with
  the Planck-threshold message). The validation report is uploaded as a build artifact.
* **Node 22 job:** `npm ci` in `renders/build`; `build.sh`; a warning (not a failure) if the committed
  `viewer.bundle.js` differs from the fresh build; `npm run test:physics`; Chromium installed with
  `npx playwright@<playwright-core version> install --with-deps chromium`; `npm run test:viewer` (zero console
  errors required) with SwiftShader software GL, since the runners have no GPU. Screenshots are uploaded as an artifact.

## Layout

```
src/slab/            physics engine (constants, metric, curvature, geodesic, integrators, trajectory, io, validation)
src/slab/cli.py      command-line pipeline behind `slab-sim` and run_simulation.py (project-directory discovery)
src/slab/speculative toy models (NOT established physics)
tools/               symbolic re-derivation of the EF curvature (sympy)
tests/               pytest suite; tests/viewer: headless viewer tests and null-geodesic checks
data/                trajectory.csv, trajectory.h5, trajectory_metadata.json, segments/, speculative/, scenarios/
checkpoints/         versioned checkpoints (never overwritten): ckpt_<index>_<milestone>_v<version>.json
renders/             viewer.html + viewer.bundle.js + trajectory_data.js (+ src/, build/, screenshots/)
renders/build/       viewer toolchain: package.json (slab-viewer-build; exact versions), package-lock.json, build.sh
docs/                viewer architecture and drafts
references/          reference notes
pyproject.toml       packaging (pip install -e .; console command slab-sim; extras test, tools)
run_simulation.py    thin wrapper around slab.cli.main (works without installation)
simulation_config.json / simulation_state.json / validation_report.json
README.md / physics_notes.md / references.md / PROJECT_STATE.md
```

## Method in one paragraph

Geometrized units G = c = M = 1 (r_s = 2). The observer's worldline is integrated from the
second-order geodesic equation (with an optional radial thrust 4-acceleration) in ingoing
Eddington–Finkelstein coordinates, which are regular at r = r_s, with a Dormand–Prince RK5(4)
adaptive integrator whose independent variable is ln r inside the hole (τ outside where a
turning point can occur). The 39-decade range in r (r0/r_QG = 2.1e39) is therefore covered with ~3000 steps,
the step in r and τ shrinking automatically as the curvature K = 48G²M²/(c⁴r⁶) grows, and the
integrator never steps through r = 0. The Killing energy is carried as an independent
well-conditioned variable so that the comoving frame and the tidal tensor remain accurate
deep inside. Kruskal–Szekeres/Penrose coordinates, light-cone orientation, the Kretschmann
scalar, the tidal eigenvalues and the distant-observer quantities are computed analytically
from the state at every step. See `physics_notes.md` for equations and citations and
`validation_report.json` for the automated benchmarks.

## Viewer

Open `renders/viewer.html` (works from `file://`, no network). Tabs: **3D view** (log-radius, linear local,
horizon neighbourhood, deep interior, curvature; third-person orbit camera; exact local light-cone glyph
and (t_EF, r) inset), **Causal / Kruskal diagram** (Kruskal–Szekeres and compactified Penrose-type
diagrams synchronized with the 3D position), **First-person camera** (per-pixel null geodesics on the GPU
in EF coordinates with aberration and frequency shift; synthetic sky; labelled "Qualitative visualization —
trajectory calculations remain relativistic."; disabled and labelled below r = 1e-5 r_s where 32-bit GPU
floats fail), and the separate **SPECULATIVE QUANTUM-GRAVITY TOY MODELS — NOT ESTABLISHED PHYSICS** menu.
Playback runs along log10(r/r_s) (proper time is useless as an axis: 99.9999 % of it is spent outside
0.1 r_s); the dashboard shows all quantities of the brief in real time. Rebuild after editing
`renders/src/*.js` with `renders/build/build.sh` (esbuild + three.js from `renders/build/node_modules`, installed
once with `npm ci`; no network needed afterwards).

## Validation (automated, must pass before the simulation is marked validated)

TEST 0 constants · TEST 1 r_s = 2GM/c² · TEST 2 horizon regularity of the EF chart ·
TEST 3 E = 1 geodesic vs dr/dτ = −c√(r_s/r) · TEST 4 τ(horizon→0) = 4GM/3c³ · TEST 5
Kretschmann by explicit contraction · TEST 6 r_QG numerical root vs closed form vs mpmath ·
TEST 7 conserved quantities · TEST 8 convergence in tolerance + SciPy DOP853 and first-integral
cross-checks. Results: `validation_report.json`.
