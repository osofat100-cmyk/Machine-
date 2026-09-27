# Packaging, console entry point, pinned viewer toolchain and CI (upgrade-prompt item 9)

Notes for the coordinator, to be merged into `README.md` / `physics_notes.md` / `PROJECT_STATE.md`.
Branch `up/packaging2`.

## What changed

| file | change |
|---|---|
| `pyproject.toml` (new) | setuptools (≥ 64, PEP 660 editable installs) src-layout packaging of package `slab`; distribution name `slab-gr-simulation`; version read from `slab.__version__` (0.1.0); `requires-python >= 3.11`; dependencies numpy ≥ 1.26, scipy ≥ 1.11, h5py ≥ 3.9, mpmath ≥ 1.3 (the minimums of the old requirements.txt); extras `test` = pytest ≥ 7, `tools` = sympy ≥ 1.12 (only `tools/derive_ef_curvature.py` imports sympy); console script `slab-sim = slab.cli:main`; `[tool.pytest.ini_options] testpaths = ["tests"]`. No license field: the repository has no license file and none was invented. |
| `src/slab/cli.py` (new) | The pipeline formerly in `run_simulation.py`, moved verbatim into `run_pipeline()` (same prints, same exit codes 0/2/3, same output locations), plus `find_project_dir()` for `slab-sim`, `build_parser()`, `resume_command()`. `python -m slab.cli` also works. |
| `run_simulation.py` | Thin wrapper: puts `src/` on `sys.path` and calls `slab.cli.main(project_dir=<its own directory>, command="python run_simulation.py")`. Works with no installation. Flags, help text, stdout and outputs are identical to the historic script (verified, see below). |
| `requirements.txt` | Same packages as before (numpy, scipy, h5py, mpmath, sympy, pytest), now annotated with the pyproject section each one belongs to; a test keeps both in sync. |
| `renders/build/package.json` | name `slab-viewer-build`, `private`, exact versions esbuild 0.24.0, three 0.170.0, playwright-core 1.49.1 (the versions that were installed); scripts `build` (the esbuild command), `test` (= `test:physics` + `test:viewer`), `test:physics` (every Node-only `tests/viewer/test_*.mjs`), `test:viewer` (`check_viewer.mjs`, `causal_check.mjs`), `browser:install` (Chromium pinned to the playwright-core version); `engines.node >= 18`. |
| `renders/build/package-lock.json` | Regenerated with npm 10.9.7 (`npm install --package-lock-only` from scratch). The old lock only listed `@esbuild/linux-x64`; the new one locks all 24 esbuild platform packages, so `npm ci` works on any OS/arch. |
| `renders/build/build.sh` | Delegates to `npm run --silent build` (the esbuild command is defined once, in package.json); clear error if `node_modules` is missing. Produces a byte-identical `viewer.bundle.js` (checked with `git diff`). Works with a symlinked `node_modules` (checked). |
| `tests/viewer/check_viewer.mjs`, `tests/viewer/causal_check.mjs` | Only the `executablePath` line: `CHROMIUM_PATH`, else `/opt/pw-browsers/chromium` if it exists, else playwright-core's `chromium.executablePath()`. |
| `.github/workflows/slab-gr-simulation.yml` (new, repository root) | CI, see below. |
| `.gitignore` (repository root) | `*.egg-info/`, `SLAB_GR_Simulation/build/`, `SLAB_GR_Simulation/dist/`, `.venv/`, `venv/`. |
| `README.md` | New sections Installation, Quick start with `slab-sim`, Continuous integration (no badge); Layout lists `pyproject.toml`, `src/slab/cli.py`, `renders/build/`. The hard-coded "26 tests" count was dropped from the quick start because other branches add tests. |
| `tests/test_packaging.py` (new) | 12 tests, see below. (A new file; the ownership list did not name it, but the brief requires tests for everything added.) |

## Project-directory discovery of `slab-sim` (LABELLING CONVENTION: a tooling convention, not physics)

Order (first match wins): `--project-dir DIR` → `$SLAB_PROJECT_DIR` → the current directory or one of its parents
that contains `simulation_config.json` with an `M_solar` key, also checking a `SLAB_GR_Simulation/` subdirectory at
each level (so it works from the repository root) → the source checkout the package was imported from
(`<project>/src/slab/cli.py`, i.e. an editable install) → error naming these options (exit 2). An explicit
directory may be new or empty; `--config` must then point to a configuration file. `slab-sim` prints
`project directory: <path> (<how it was found>)`. Run anywhere inside the repository it gives the directory
that contains `run_simulation.py`, the directory the historic script always used (tested).

`slab-sim` has two extra flags, `--project-dir` and `--version`. `run_simulation.py` has exactly the historic flag set.
After `--stop-after-milestone`, `slab-sim` prints a complete resume command (`--project-dir`, `--out-dir` or the scenario
`--tag`, `--skip-validation`); `run_simulation.py` prints its historic hint `python run_simulation.py --resume`
unchanged. The resume itself still restores the configuration from the checkpoint, as before.

The only intentional behaviour difference of `run_simulation.py`: a `--config` path that does not exist now gives
a clean argparse error (exit 2) instead of a Python traceback (exit 1). Every valid invocation behaves the same.

## Equations

No new or changed equations. No physics code was touched: the pipeline body moved unchanged from
`run_simulation.py` to `src/slab/cli.py`. The hard rules are untouched: the run still stops at r_QG and prints
the Planck-threshold message (printed by `Simulation.run`; asserted in `test_slab_sim_project_dir_stop_and_resume`
and in the CI smoke step), speculative models still run only with `--speculative` into their own outputs, and
checkpoints are still never overwritten (asserted by hashing the pre-resume checkpoints in the new test).

## CI (`.github/workflows/slab-gr-simulation.yml`)

Triggers: `push` and `pull_request` with `paths: SLAB_GR_Simulation/**` and the workflow file itself; `workflow_dispatch`.
`permissions: contents: read`; one run per ref at a time (`concurrency`, cancel in progress). Runners: `ubuntu-24.04`.

* **python** (Python 3.11, pip cache keyed on `pyproject.toml`): `pip install -e ".[test,tools]"` →
  `python -m pytest tests -q` → `python run_simulation.py --validate-only` → `python tools/derive_ef_curvature.py`
  (the step fails unless it prints `ALL RIEMANN COMPONENTS MATCH CODE: True` and no `False`; the script itself always
  exits 0) → from the repository root: `slab-sim --version` and a short scenario
  `slab-sim --skip-validation --E 0.95 --r0 10 --out-dir $RUNNER_TEMP/scenario`, which must find the project
  directory, print the Planck-threshold message and write `trajectory.h5` → upload `validation_report.json`.
* **viewer** (Node 22, npm cache keyed on the lockfile, working directory `SLAB_GR_Simulation/renders/build`):
  `npm ci` → `./build.sh` → a warning annotation (not a failure) if the committed `viewer.bundle.js` differs from the
  fresh build → `npm run test:physics` → `npx --yes "playwright@${PW_VERSION}" install --with-deps chromium` with
  `PW_VERSION` read from the installed playwright-core → `npm run test:viewer` (the scripts already pass
  `--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`: software GL, no GPU) → upload `renders/screenshots/`.

**GitHub Actions could not be run from this environment.** What was checked instead:
* YAML parses with `yaml.safe_load` (PyYAML 6.0.1); `actionlint` 1.7.12 with shellcheck enabled (`actionlint-py`
  and `shellcheck-py` from PyPI in a scratch venv) reports 0 findings; `shellcheck build.sh` is clean.
* Every step of the python job was replayed locally in a fresh, isolated venv (no system site-packages; numpy 2.4.6,
  scipy 1.17.1, h5py 3.16.0, mpmath 1.3.0, sympy 1.14.0, pytest 9.1.1 from PyPI), with `RUNNER_TEMP` and
  `GITHUB_WORKSPACE` set by hand. All steps passed.
* The viewer job was replayed locally except the Chromium download: `npx --yes playwright@1.49.1 install chromium`
  resolved the pinned version correctly ("Chromium 131.0.6778.33 (playwright build v1148)"), but the download host is
  blocked by this sandbox's proxy (HTTP 403). The third browser-discovery branch (`chromium.executablePath()`) was
  tested anyway. In a private mount namespace (`unshare -m`), `/opt/pw-browsers` was hidden and
  `PLAYWRIGHT_BROWSERS_PATH` pointed at a directory where `chromium-1148` was bind-mounted from the local Chromium.
  `npm test` then passed with zero console errors. The `CHROMIUM_PATH` branch was checked with a bogus path (launch fails and names
  it) and a valid one (passes).

## Verification of external facts

* setuptools ≥ 64 is needed for PEP 660 editable installs: PEP 660 hooks were added in setuptools v64.0.0, as the
  setuptools GitHub PR #3488 and the setuptools "Development Mode" documentation state (found by web search; the changelog
  page itself was not fetched). The editable install was also tested locally with setuptools from PyPI (build isolation).
* Playwright 1.49 ships Chromium 131.0.6778.33 (build v1148): the installer printed this locally, and the Playwright release
  notes page says the same (found by web search).
* Whether `playwright@1.49.1 install --with-deps chromium` works on the `ubuntu-24.04` runner image: INSUFFICIENT DATA TO
  VERIFY here (not runnable). Playwright's documentation lists Ubuntu 24.04 as supported, but no source checked here
  names the first release that supported it. If it fails, switch `runs-on` to `ubuntu-22.04`.
* Python < 3.11: INSUFFICIENT DATA TO VERIFY (only 3.11 is available and tested), hence `requires-python >= 3.11`
  (`tests/test_packaging.py` itself uses `tomllib`, which is 3.11+).

## Tests added (`tests/test_packaging.py`, 12 tests, all pass)

1. `test_pyproject_metadata`: name, entry point `slab-sim = slab.cli:main`, src layout, dynamic version. Also checks that
   every third-party module imported by `src/slab` is a declared dependency.
2. `test_requirements_txt_in_sync_with_pyproject`: `requirements.txt` equals the pyproject dependencies plus the extras.
3. `test_run_simulation_wrapper_keeps_historic_flags`: `run_simulation.py --help` lists exactly the historic flags. The
   wrapper contains no second copy of the pipeline.
4. `test_slab_sim_parser_is_superset`: slab-sim = historic flags + `--project-dir`, `--version`.
5. `test_discovery_from_inside_the_repository_matches_run_simulation_root`: discovery from the project directory,
   from `src/slab`, `tests/viewer` and `renders`, and from the repository root, all give the directory of
   `run_simulation.py`.
6. `test_discovery_order`: explicit > env > cwd/ancestors > `SLAB_GR_Simulation/` subdirectory > source checkout;
   a foreign `simulation_config.json` without `M_solar` is ignored; the error message when nothing is found.
7. `test_slab_sim_missing_config_is_a_clean_error`: exit 2, no traceback.
8. `test_slab_sim_project_dir_stop_and_resume`: `python -m slab.cli --project-dir "<dir with a space>"` stops at the
   horizon. The printed resume command is then executed as printed and must print the Planck-threshold message and reach
   `status: complete` at r_QG. It must also leave the pre-resume checkpoints byte-identical (never overwritten) and write
   CSV/HDF5/JSON/render export.
9. `test_console_script_entry_point_if_installed`: entry-point metadata (skipped when the package is not installed).
10. `test_viewer_build_package_json_and_lockfile`: name, exact versions, scripts, lock root matches package.json,
    locked versions match, all esbuild platform binaries locked, `build.sh` delegates to `npm run build`.
11. `test_viewer_tests_browser_discovery_order`: the executablePath line in both browser tests has the order
    CHROMIUM_PATH → /opt/pw-browsers/chromium → `chromium.executablePath()`.
12. `test_ci_workflow_structure`: the workflow triggers, Python 3.11 / Node 22, the required commands, pinned Playwright
    install. Skipped without PyYAML or outside this repository.

Equivalence of the wrapper with the historic script (manual check, scratch directory): the old `run_simulation.py`
(from `git show HEAD`) and the new wrapper were run side by side on the same `src/`. The runs were
`--help`, `--skip-validation --thrust 9.81 --stop-after-milestone horizon`, the same with `--resume`, and
`--E 0.95 --r0 10 --L 1 --tag t1 --speculative`. Results: help text and stdout identical (after masking wall
times and directory names); the same file sets; CSV byte-identical. All 74 JSON/NPZ/HDF5/CSV outputs were identical
after removing timestamp and wall-time fields.

## Known limitations

* GitHub Actions itself was not run (see above). The Chromium download in CI is the one untested step.
* The npm `build` script uses POSIX `sh` syntax (`NODE_PATH="$PWD/node_modules" esbuild ...`), so it does not run
  under Windows `cmd`. esbuild has no CLI flag for node paths, and `build.sh` was already bash-only.
* `test:physics` runs every `tests/viewer/test_*.mjs`. By convention these must be Node-only, because CI runs them before
  Chromium is installed. Browser tests have to be added to `test:viewer` by name.
* A regular (non-editable) `pip install .` has no source checkout to fall back to: `slab-sim` then needs to run inside a
  project directory, or be given `--project-dir` or `SLAB_PROJECT_DIR`. The default `simulation_config.json` is deliberately
  not shipped as package data, so it has one source of truth.
* `src/slab/trajectory.py` still writes `"how_to_resume": "python run_simulation.py --resume ..."` into
  `simulation_state.json`. That file is not owned by this branch, and the text is still correct.
* The viewer job relies on the committed `renders/trajectory_data.js`, because it does not run the simulation. The
  bundle-freshness check only warns, since branches are told not to commit the bundle.
* Test 9 also passes in a plain checkout after any `pip install -e`, because `src/slab_gr_simulation.egg-info`
  is on `sys.path` (it is git-ignored).
* Found, not fixed (not owned by this branch): in `tests/viewer/test_null_geodesics.mjs`, check (f) (exact
  impact-parameter classification) sits after `process.exit(...)` and never runs.
