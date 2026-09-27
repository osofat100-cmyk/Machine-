"""Packaging / command-line tests: pyproject metadata, requirements.txt in sync, the flag set of the
historic run_simulation.py, project-directory discovery of `slab-sim`, and a stop/resume cycle through
the packaged CLI (`python -m slab.cli`, the code behind the `slab-sim` console command)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab import cli  # noqa: E402

HISTORIC_FLAGS = {"-h", "--help", "--config", "--resume", "--validate-only", "--skip-validation", "--thrust", "--E",
                  "--L", "--r0", "--tag", "--speculative", "--stop-after-milestone", "--out-dir"}


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def _req_name(spec: str) -> str:
    return re.split(r"[<>=!~;\[ ]", spec.strip(), maxsplit=1)[0].lower()


def _env_with_src() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.pop(cli.PROJECT_DIR_ENV, None)
    return env


# ---------------------------------------------------------------------------------------------------
def test_pyproject_metadata():
    pp = _pyproject()
    proj = pp["project"]
    assert proj["name"] == "slab-gr-simulation"
    assert proj["scripts"]["slab-sim"] == "slab.cli:main"
    assert pp["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert pp["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "slab.__version__"
    assert "version" in proj["dynamic"]
    deps = {_req_name(d) for d in proj["dependencies"]}
    assert {"numpy", "scipy", "h5py", "mpmath"} <= deps
    assert "pytest" in {_req_name(d) for d in proj["optional-dependencies"]["test"]}
    # every module the engine imports at run time is declared (sympy is only used by tools/)
    engine_imports = set()
    for p in (ROOT / "src" / "slab").rglob("*.py"):
        engine_imports |= set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", p.read_text(), re.M))
    third_party = engine_imports & {"numpy", "scipy", "h5py", "mpmath", "sympy", "matplotlib", "pandas", "yaml"}
    assert third_party <= deps, f"undeclared runtime dependencies: {third_party - deps}"


def test_requirements_txt_in_sync_with_pyproject():
    proj = _pyproject()["project"]
    declared = list(proj["dependencies"]) + [d for extra in proj["optional-dependencies"].values() for d in extra]
    lines = [ln.strip() for ln in (ROOT / "requirements.txt").read_text().splitlines()]
    reqs = [ln for ln in lines if ln and not ln.startswith("#")]
    assert sorted(reqs) == sorted(declared), "requirements.txt must list exactly pyproject's dependencies + extras"


def test_run_simulation_wrapper_keeps_historic_flags():
    """run_simulation.py is a thin wrapper around slab.cli.main with exactly the historic flag set."""
    out = subprocess.run([sys.executable, str(ROOT / "run_simulation.py"), "--help"], check=True,
                         capture_output=True, text=True, env=_env_with_src()).stdout
    assert out.startswith("usage: run_simulation.py")
    flags = set(re.findall(r"(?<![\w-])(--?[A-Za-z][\w-]*)", out))
    assert flags == HISTORIC_FLAGS
    src = (ROOT / "run_simulation.py").read_text()
    assert "from slab.cli import main" in src and "Simulation(" not in src   # no duplicated pipeline


def test_slab_sim_parser_is_superset():
    ap = cli.build_parser(prog="slab-sim")
    flags = {s for a in ap._actions for s in a.option_strings}
    assert flags == HISTORIC_FLAGS | {"--project-dir", "--version"}
    legacy = {s for a in cli.build_parser(with_project_dir=False)._actions for s in a.option_strings}
    assert legacy == HISTORIC_FLAGS


# ---------------------------------------------------------------------------------------------------
# project-directory discovery
def test_discovery_from_inside_the_repository_matches_run_simulation_root():
    """Run from the repository (project dir, a subdirectory, or the repository root one level up),
    slab-sim uses the same directory run_simulation.py uses (the directory containing it)."""
    for cwd in (ROOT, ROOT / "src" / "slab", ROOT / "tests" / "viewer", ROOT / "renders", ROOT.parent):
        found, how = cli.find_project_dir(cwd=cwd, environ={})
        assert found == ROOT, (cwd, found, how)
    assert cli.source_checkout_dir() == ROOT


def test_discovery_order(tmp_path, monkeypatch):
    cfg = (ROOT / "simulation_config.json").read_text()
    a, b = tmp_path / "a", tmp_path / "b"
    for d in (a, b):
        (d / "deep" / "er").mkdir(parents=True)
        (d / "simulation_config.json").write_text(cfg)
    # explicit beats environment beats cwd
    assert cli.find_project_dir(str(a), cwd=b, environ={cli.PROJECT_DIR_ENV: str(b)}) == (a.resolve(), "--project-dir")
    assert cli.find_project_dir(None, cwd=a, environ={cli.PROJECT_DIR_ENV: str(b)})[0] == b.resolve()
    # cwd and its ancestors
    assert cli.find_project_dir(None, cwd=b / "deep" / "er", environ={})[0] == b.resolve()
    # SLAB_GR_Simulation/ subdirectory (running from a repository root)
    repo = tmp_path / "repo"
    (repo / cli.PROJECT_SUBDIR).mkdir(parents=True)
    (repo / cli.PROJECT_SUBDIR / "simulation_config.json").write_text(cfg)
    assert cli.find_project_dir(None, cwd=repo, environ={})[0] == (repo / cli.PROJECT_SUBDIR).resolve()
    # a simulation_config.json that is not ours (no M_solar) is not a project marker
    other = tmp_path / "other"
    other.mkdir()
    (other / "simulation_config.json").write_text('{"something": 1}')
    assert not cli.is_project_dir(other)
    # nothing found and no source checkout (regular site-packages install) -> clear error
    monkeypatch.setattr(cli, "source_checkout_dir", lambda: None)
    with pytest.raises(cli.ProjectDirError, match="--project-dir"):
        cli.find_project_dir(None, cwd=other, environ={})
    # nothing found near cwd -> the source checkout of the package
    monkeypatch.setattr(cli, "source_checkout_dir", lambda: ROOT)
    assert cli.find_project_dir(None, cwd=other, environ={}) == (ROOT, "source checkout of the installed slab package")


def test_slab_sim_missing_config_is_a_clean_error(tmp_path):
    r = subprocess.run([sys.executable, "-m", "slab.cli", "--project-dir", str(tmp_path / "empty"), "--skip-validation"],
                       capture_output=True, text=True, env=_env_with_src(), cwd=tmp_path)
    assert r.returncode == 2
    assert "configuration file not found" in r.stderr and "Traceback" not in r.stderr


# ---------------------------------------------------------------------------------------------------
def test_slab_sim_project_dir_stop_and_resume(tmp_path):
    """Packaged CLI with --project-dir pointing outside the repository: stop at the horizon, resume with the
    printed hint, finish at r_QG with the Planck message; checkpoints written before the resume are untouched."""
    proj = tmp_path / "my project"
    proj.mkdir()
    cfg = json.loads((ROOT / "simulation_config.json").read_text())
    cfg["rtol"] = 1e-10
    (proj / "simulation_config.json").write_text(json.dumps(cfg))
    base = [sys.executable, "-m", "slab.cli"]
    r1 = subprocess.run(base + ["--project-dir", str(proj), "--skip-validation", "--stop-after-milestone", "horizon"],
                        check=True, capture_output=True, text=True, env=_env_with_src(), cwd=tmp_path)
    assert f"project directory: {proj.resolve()} (--project-dir)" in r1.stdout
    st = json.loads((proj / "simulation_state.json").read_text())
    assert st["status"] == "in_progress" and st["milestone_slug"] == "horizon"
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (proj / "checkpoints").glob("*.json")}
    assert "ckpt_03_horizon_v001.json" in before
    hint = r1.stdout.strip().splitlines()[-1].split("Continue with: ", 1)[1]
    argv = shlex.split(hint)
    assert argv[0] == "slab-sim" and "--resume" in argv and "--skip-validation" in argv
    r2 = subprocess.run(base + argv[1:], check=True, capture_output=True, text=True, env=_env_with_src(), cwd=tmp_path)
    assert "CLASSICAL GENERAL RELATIVITY IS NO LONGER RELIABLE." in r2.stdout
    st = json.loads((proj / "simulation_state.json").read_text())
    assert st["status"] == "complete" and st["milestone_slug"] == "r_QG"
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (proj / "checkpoints").glob("*.json")}
    assert all(after[k] == v for k, v in before.items()), "a checkpoint was overwritten"
    assert "ckpt_14_r_QG_v001.json" in after
    for f in ("data/trajectory.csv", "data/trajectory.h5", "data/trajectory_metadata.json", "renders/trajectory_data.js"):
        assert (proj / f).is_file(), f
    assert not (ROOT / "data" / "scenarios" / "my project").exists()


def test_console_script_entry_point_if_installed():
    """When the package is installed (pip install -e .), the slab-sim entry point targets slab.cli:main."""
    from importlib import metadata
    try:
        dist = metadata.distribution("slab-gr-simulation")
    except metadata.PackageNotFoundError:
        pytest.skip("package not installed (pip install -e .) — entry point not checked")
    eps = [ep for ep in dist.entry_points if ep.group == "console_scripts" and ep.name == "slab-sim"]
    assert len(eps) == 1 and eps[0].value == "slab.cli:main"
    import slab
    assert dist.version == slab.__version__


# ---------------------------------------------------------------------------------------------------
# viewer toolchain (renders/build) and CI
BUILD = ROOT / "renders" / "build"


def test_viewer_build_package_json_and_lockfile():
    pkg = json.loads((BUILD / "package.json").read_text())
    assert pkg["name"] == "slab-viewer-build" and pkg["private"] is True
    pinned = {**pkg["dependencies"], **pkg["devDependencies"]}
    assert set(pinned) == {"esbuild", "three", "playwright-core"}
    for name, ver in pinned.items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", ver), f"{name} must be pinned to an exact version, got {ver!r}"
    s = pkg["scripts"]
    assert "esbuild ../src/main.js --bundle" in s["build"] and "--outfile=../viewer.bundle.js" in s["build"]
    assert "test_*.mjs" in s["test:physics"] and "check_viewer.mjs" in s["test:viewer"] and "causal_check.mjs" in s["test:viewer"]
    assert "test:physics" in s["test"] and "test:viewer" in s["test"]
    lock = json.loads((BUILD / "package-lock.json").read_text())
    assert lock["name"] == pkg["name"] and lock["lockfileVersion"] >= 2
    root = lock["packages"][""]
    assert root["dependencies"] == pkg["dependencies"] and root["devDependencies"] == pkg["devDependencies"]
    for name, ver in pinned.items():
        assert lock["packages"][f"node_modules/{name}"]["version"] == ver
    # all esbuild platform binaries are locked (npm ci must work on any OS/arch, not only linux-x64)
    platforms = [k for k in lock["packages"] if k.startswith("node_modules/@esbuild/")]
    assert len(platforms) >= 20 and "node_modules/@esbuild/linux-x64" in platforms
    # build.sh delegates to the single esbuild definition in package.json
    assert "npm run --silent build" in (BUILD / "build.sh").read_text()


def test_viewer_tests_browser_discovery_order():
    """CHROMIUM_PATH, else /opt/pw-browsers/chromium if it exists, else playwright-core's own chromium."""
    for f in ("check_viewer.mjs", "causal_check.mjs"):
        line = next(ln for ln in (ROOT / "tests" / "viewer" / f).read_text().splitlines() if "executablePath" in ln)
        i_env, i_opt, i_pw = (line.find(t) for t in ("process.env.CHROMIUM_PATH", "fs.existsSync('/opt/pw-browsers/chromium')",
                                                     "chromium.executablePath()"))
        assert 0 <= i_env < i_opt < i_pw, (f, line)


def test_ci_workflow_structure():
    wf = ROOT.parent / ".github" / "workflows" / "slab-gr-simulation.yml"
    if not wf.is_file():
        pytest.skip("not inside the repository that holds .github/workflows/slab-gr-simulation.yml")
    yaml = pytest.importorskip("yaml")
    d = yaml.safe_load(wf.read_text())
    on = d.get("on", d.get(True))            # YAML 1.1 reads the bare key `on` as boolean True
    for ev in ("push", "pull_request"):
        assert "SLAB_GR_Simulation/**" in on[ev]["paths"]
    py, node = d["jobs"]["python"], d["jobs"]["viewer"]

    def runs(job):
        return "\n".join(st.get("run", "") for st in job["steps"])

    def uses(job, action):
        return next(st for st in job["steps"] if st.get("uses", "").startswith(action))

    assert str(uses(py, "actions/setup-python")["with"]["python-version"]) == "3.11"
    assert 'pip install -e ".[test' in runs(py) and "python -m pytest tests" in runs(py)
    assert "python run_simulation.py --validate-only" in runs(py) and "slab-sim" in runs(py)
    assert str(uses(node, "actions/setup-node")["with"]["node-version"]) == "22"
    r = runs(node)
    assert "npm ci" in r and "./build.sh" in r and "npm run test:physics" in r and "npm run test:viewer" in r
    assert "require('playwright-core/package.json').version" in r
    assert 'npx --yes "playwright@${PW_VERSION}" install --with-deps chromium' in r
