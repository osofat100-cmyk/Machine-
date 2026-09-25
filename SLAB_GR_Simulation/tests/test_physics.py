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


@pytest.mark.parametrize("tid", ["TEST 0", "TEST 1", "TEST 2", "TEST 3", "TEST 4", "TEST 5", "TEST 6", "TEST 7", "TEST 8"])
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


def test_thrust_preserves_normalization_in_continuous_equations():
    m = Schwarzschild()
    y = initial_state_radial(m, 5.0, 1.0)
    d = rhs_tau(m, y, Thrust(alpha=0.3))
    # d/dtau [g(u,u)] = 2 g(u, du/dtau) must vanish (a orthogonal to u)
    du = d[IUV:IUV + 4]
    u = y[IUV:IUV + 4]
    assert abs(m.dot(y[1], y[2], u, du)) < 1e-12


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
