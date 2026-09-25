"""pytest wrapper around the automated validation suite plus unit tests of the building blocks.
Run:  cd SLAB_GR_Simulation && python -m pytest tests -q
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab import constants as C  # noqa: E402
from slab.constants import DerivedQuantities  # noqa: E402
from slab.metric import Schwarzschild  # noqa: E402
from slab.curvature import kretschmann_by_contraction, kretschmann_schwarzschild, tidal_tensor  # noqa: E402
from slab.geodesic import initial_state_radial, rhs_tau, norm, energy, RadialInfallE1, Thrust, IUV, IUR, IEK  # noqa: E402
from slab.trajectory import Simulation, SimulationConfig  # noqa: E402


@pytest.fixture(scope="module")
def report():
    from slab.validation import run_all_tests
    cfg = SimulationConfig.from_json(ROOT / "simulation_config.json")
    return run_all_tests(cfg, ROOT)


def test_validation_suite_all_pass(report):
    failed = [t["id"] for t in report["tests"] if not t["passed"]]
    assert report["all_passed"], f"failed: {failed}"


@pytest.mark.parametrize("tid", ["TEST 0", "TEST 1", "TEST 2", "TEST 3", "TEST 4", "TEST 5", "TEST 6", "TEST 7", "TEST 8", "TEST 9", "TEST 10"])
def test_each(report, tid):
    t = next(x for x in report["tests"] if x["id"] == tid)
    bad = [c["label"] for c in t["checks"] if not c["passed"]]
    assert t["passed"], bad


def test_schwarzschild_radius_formula():
    dq = DerivedQuantities(1e18)
    assert math.isclose(dq.r_s_m, 2 * C.G * dq.M_kg / C.c**2, rel_tol=1e-15)
    assert math.isclose(dq.r_s_m, 2.95334e21, rel_tol=1e-5)


def test_kretschmann_contraction_at_horizon():
    m = Schwarzschild()
    assert math.isclose(kretschmann_by_contraction(m, 2.0), kretschmann_schwarzschild(1.0, 2.0), rel_tol=1e-13)


def test_geodesic_equation_matches_analytic_derivative():
    m = Schwarzschild()
    ref = RadialInfallE1()
    for r in [10.0, 2.0, 0.3]:
        y = initial_state_radial(m, r, 1.0)
        d = rhs_tau(m, y)
        # d(u^r)/dtau = -M/r^2 along the E=1 geodesic
        assert math.isclose(d[IUR], -1.0 / r**2, rel_tol=1e-12)
        assert math.isclose(y[IUV], ref.uv(r), rel_tol=1e-14)


@pytest.mark.parametrize("L", [0.0, 3.0])
def test_thrust_four_acceleration_orthogonal_and_unit(L):
    from slab.geodesic import four_acceleration
    m = Schwarzschild()
    for r in (5.0, 2.0, 0.7):
        y = initial_state_radial(m, r, 1.0, L)
        a = four_acceleration(m, y, Thrust(alpha=0.3))
        u = y[IUV:IUV + 4]
        assert abs(m.dot(r, y[2], u, a)) < 1e-12 * max(1.0, abs(a).max() * abs(u).max())   # a . u = 0
        assert math.isclose(m.dot(r, y[2], a, a), 0.09, rel_tol=1e-12)  # |a|^2 = alpha^2 (also for L != 0)
        # RHS with thrust equals geodesic RHS plus a (both formulations consistent)
        d0, d1 = rhs_tau(m, y), rhs_tau(m, y, Thrust(alpha=0.3))
        assert np.allclose(d1[IUV:IUV + 4] - d0[IUV:IUV + 4], a, rtol=1e-12, atol=1e-15)


def test_thrust_energy_evolution_consistent():
    """Integrate a short thrust segment and check E_k (integrated) vs f u^v - u^r (from velocity)."""
    cfg = SimulationConfig(thrust_alpha_SI=1e-3, r0_over_rs=20.0, rtol=1e-12)
    sim = Simulation(cfg, verbose=False)
    y = sim.initial_state()
    res, mode = sim.integrate_segment(y, 6.0)
    yend = res.y[-1]
    assert abs(energy(m := sim.metric, yend) - yend[IEK]) < 1e-8
    assert abs(norm(m, yend) + 1) < 1e-9
    assert yend[IEK] > 1.0  # inward thrust from rest at infinity increases Killing energy while falling outside


def test_tidal_eigenvalues_deep_inside():
    m = Schwarzschild()
    ref = RadialInfallE1()
    r = 1e-30
    u = np.array([ref.uv(r), ref.ur(r), 0.0, 0.0])
    lam = tidal_tensor(m, r, math.pi / 2, u, E=1.0)["eigenvalues"]
    assert math.isclose(lam[0], -2 / r**3, rel_tol=1e-9)
    assert math.isclose(lam[2], 1 / r**3, rel_tol=1e-9)


def test_never_steps_through_r_zero():
    cfg = SimulationConfig(rtol=1e-10)
    sim = Simulation(cfg, verbose=False)
    sim.run()
    for seg in sim.segments:
        assert np.all(seg.y[:, 1] > 0)
    assert math.isclose(sim.segments[-1].y[-1, 1], sim.milestones[-1].r_geo, rel_tol=1e-12)


def test_cli_stop_and_resume_matches_full_run(tmp_path):
    """Run the CLI to the horizon, resume from the checkpoint to r_QG, compare with a single run."""
    import subprocess, json, shutil
    cfg = json.loads((ROOT / "simulation_config.json").read_text())
    cfg["rtol"] = 1e-10
    cfgp = tmp_path / "cfg.json"
    cfgp.write_text(json.dumps(cfg))
    base = [sys.executable, str(ROOT / "run_simulation.py"), "--config", str(cfgp), "--skip-validation", "--out-dir", str(tmp_path / "proj")]
    subprocess.run(base + ["--stop-after-milestone", "horizon"], check=True, capture_output=True)
    st = json.loads((tmp_path / "proj" / "simulation_state.json").read_text())
    assert st["status"] == "in_progress" and st["milestone_slug"] == "horizon"
    subprocess.run(base + ["--resume"], check=True, capture_output=True)
    st = json.loads((tmp_path / "proj" / "simulation_state.json").read_text())
    assert st["status"] == "complete" and st["milestone_slug"] == "r_QG"
    meta_resumed = json.loads((tmp_path / "proj" / "data" / "trajectory_metadata.json").read_text())
    subprocess.run(base[:-2] + ["--out-dir", str(tmp_path / "full")], check=True, capture_output=True)
    meta_full = json.loads((tmp_path / "full" / "data" / "trajectory_metadata.json").read_text())
    a = meta_resumed["milestone_states"]["r_QG"]["tau_total_geo"]
    b = meta_full["milestone_states"]["r_QG"]["tau_total_geo"]
    assert math.isclose(a, b, rel_tol=1e-12)
    # checkpoints are versioned, never overwritten: the resumed run re-wrote none of the first run's files
    ck = sorted(p.name for p in (tmp_path / "proj" / "checkpoints").glob("*.json"))
    assert "ckpt_03_horizon_v001.json" in ck and "ckpt_14_r_QG_v001.json" in ck
    # HDF5 readable and complete
    import h5py
    with h5py.File(tmp_path / "proj" / "data" / "trajectory.h5") as h:
        keys = set(h["trajectory"].keys())
        for k in ("tau_s", "r_m", "u_v", "u_r", "a_v", "K_SI_log10", "tidal_lambda1_geo", "lc_out_drdtEF", "step_h", "err_estimate", "kruskal_T"):
            assert k in keys
        assert len(h["segments_raw"].keys()) == 14


def _static_frame_tidal_eigenvalues(r, uv, ur, uph):
    """Independent route (valid for r > 2M): tidal tensor from the Schwarzschild Riemann tensor in
    the STATIC orthonormal frame, contracted with the observer's boosted 4-velocity.
    Static-frame components (M = 1): R_trtr = -2/r^3, R_tθtθ = R_tφtφ = 1/r^3, R_θφθφ = 2/r^3,
    R_rθrθ = R_rφrφ = -1/r^3 (hats omitted).  Returns the three nonzero eigenvalues of E^a_b."""
    f = 1 - 2 / r
    ut = uv - ur / f                       # Schwarzschild coordinate time component (v = t + r_*)
    uhat = np.array([math.sqrt(f) * ut, ur / math.sqrt(f), 0.0, r * uph])   # (t, r, θ, φ) orthonormal
    assert math.isclose(-uhat[0] ** 2 + uhat[1] ** 2 + uhat[3] ** 2, -1.0, abs_tol=1e-10)
    Rm = np.zeros((4, 4, 4, 4))

    def put(a, b, c, d, val):
        for (i, j, k, l, s) in ((a, b, c, d, 1), (b, a, c, d, -1), (a, b, d, c, -1), (b, a, d, c, 1),
                                (c, d, a, b, 1), (d, c, a, b, -1), (c, d, b, a, -1), (d, c, b, a, 1)):
            Rm[i, j, k, l] = s * val
    put(0, 1, 0, 1, -2 / r**3); put(0, 2, 0, 2, 1 / r**3); put(0, 3, 0, 3, 1 / r**3)
    put(2, 3, 2, 3, 2 / r**3); put(1, 2, 1, 2, -1 / r**3); put(1, 3, 1, 3, -1 / r**3)
    E = np.einsum("acbd,c,d->ab", Rm, uhat, uhat)
    eta = np.diag([-1.0, 1.0, 1.0, 1.0])
    w = np.linalg.eigvals(eta @ E).real
    w = np.sort(w)
    # remove the zero eigenvalue (E u = 0)
    i0 = int(np.argmin(np.abs(w)))
    return np.delete(w, i0)


@pytest.mark.parametrize("L", [0.0, 2.5, 3.9])
def test_tidal_exact_eigenvalues_vs_independent_methods(L):
    from slab.curvature import tidal_eigenvalues_exact, tidal_eigenvalues_frame_matrix
    m = Schwarzschild()
    for r in (30.0, 8.0, 3.2, 2.2, 2.0, 1.0, 0.1, 1e-3, 1e-10, 1e-30):
        y = initial_state_radial(m, r, 1.0, L)
        lam = tidal_eigenvalues_exact(m, r, math.pi / 2, y[IUV:IUV + 4])
        s2 = (L / r) ** 2
        assert np.allclose(lam, np.sort([-(2 + 3 * s2) / r**3, (1 + 3 * s2) / r**3, 1 / r**3]), rtol=1e-12)
        assert abs(lam.sum()) < 1e-12 * np.max(np.abs(lam))          # vacuum: traceless
        # numeric 4x4 frame-matrix route (independent of the closed form) where its eigen-solver is well conditioned
        if L == 0.0 or r >= 0.1:
            lam_m = tidal_eigenvalues_frame_matrix(m, r, math.pi / 2, y[IUV:IUV + 4])
            assert np.allclose(lam, lam_m, rtol=1e-7), (L, r, lam, lam_m)
        if L == 0.0 or r >= 1.0:   # explicit index contraction of the EF Riemann tensor (well conditioned here)
            lam_c = np.sort(tidal_tensor(m, r, math.pi / 2, y[IUV:IUV + 4], E=y[IEK])["eigenvalues"])
            assert np.allclose(lam, lam_c, rtol=1e-8), (L, r, lam, lam_c)
        if r > 2.0:                # static orthonormal frame + Lorentz boost (exterior only)
            ref = np.sort(_static_frame_tidal_eigenvalues(r, y[IUV], y[IUV + 1], y[IUV + 3]))
            assert np.allclose(lam, ref, rtol=1e-9), (L, r, lam, ref)


@pytest.mark.parametrize("L", [0.0, 2.5, 3.9])
def test_tidal_tensor_orbital_motion_vs_static_frame_boost(L):
    """EF-tetrad tidal eigenvalues vs an independent static-frame computation, for radial (L=0)
    and orbital-plunge (L != 0) 4-velocities at several exterior radii."""
    m = Schwarzschild()
    for r in (30.0, 8.0, 3.2, 2.2):
        y = initial_state_radial(m, r, 1.0, L)
        lam = tidal_tensor(m, r, math.pi / 2, y[IUV:IUV + 4], E=y[IEK])["eigenvalues"]
        ref = _static_frame_tidal_eigenvalues(r, y[IUV], y[IUV + 1], y[IUV + 3])
        assert np.allclose(np.sort(lam), np.sort(ref), rtol=1e-9, atol=1e-14), (r, lam, ref)
        if L == 0.0:
            assert np.allclose(np.sort(lam), [-2 / r**3, 1 / r**3, 1 / r**3], rtol=1e-12)
        else:
            # with angular momentum the radial stretching is enhanced: lambda_min < -2M/r^3
            assert lam[0] < -2 / r**3


def test_angular_momentum_plunge_conservation():
    cfg = SimulationConfig(L_over_M=3.5, r0_over_rs=20.0, rtol=1e-11)
    sim = Simulation(cfg, verbose=False)
    sim.run()
    sim.postprocess()
    s = sim.summary()
    assert [seg.mode for seg in sim.segments][:3] == ["tau", "tau", "tau"]   # exterior integrated in tau (turning points possible)
    assert s["max_abs_L_drift"] < 1e-8                       # relative 3e-9 over ~3000 steps of a stiff spiral
    assert s["max_abs_norm_residual_conditioned"] < 1e-9     # raw residual is round-off of ~L^2/r^2 ~ 1e75 terms at r_QG
    assert s["max_abs_norm_residual_where_well_conditioned"] < 1e-9
    assert s["max_abs_E_drift_where_well_conditioned"] < 1e-8
    assert sim.columns["u_phi"][-1] > 0.0
    assert np.all(sim.columns["u_theta"] == 0.0)              # equatorial plane preserved exactly
    assert np.all(np.abs(sim.columns["r_geo"] * 0 + 1) == 1)
    lam = sim.columns["tidal_lambda1_geo"]
    assert np.all(np.isfinite(lam)) and lam[-1] < -2 / sim.columns["r_geo"][-1] ** 3
