"""Inertial (Rindler-type) differential term in the accelerated observer's proper reference frame."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab import constants as C  # noqa: E402
from slab.accelerated import (inertial_diff_along_thrust_SI, inertial_relative_accel, rindler_flat_check, hovering_check,  # noqa: E402
                              thrust_energy_closed_form, crossover_radius_geo)
from slab.metric import Schwarzschild  # noqa: E402
from slab.curvature import tidal_tensor  # noqa: E402
from slab.geodesic import initial_state_radial, IUV, IEK  # noqa: E402
from slab.trajectory import Simulation, SimulationConfig  # noqa: E402


def test_inertial_term_magnitude_sign_and_geometry():
    val = inertial_diff_along_thrust_SI(9.81, 2.0)
    assert val < 0.0                                               # approach (compression) along the thrust axis
    assert math.isclose(val, -9.81**2 * 2.0 / C.c**2, rel_tol=1e-15)
    assert 2.1e-15 < abs(val) < 2.2e-15                           # a^2 L/c^2 ~ 2.14e-15 m/s^2 for 1 g, 2 m
    assert inertial_diff_along_thrust_SI(0.0, 2.0) == 0.0
    a = np.array([0.0, 0.0, 3.0])
    ahead, behind, side = inertial_relative_accel(a, [0, 0, 0.5]), inertial_relative_accel(a, [0, 0, -0.5]), inertial_relative_accel(a, [0.5, 0, 0])
    assert np.allclose(ahead, [0, 0, -4.5]) and np.allclose(behind, [0, 0, 4.5])   # both towards the observer
    assert np.allclose(side, 0.0)                                                     # no transverse inertial term


def test_rindler_flat_space_exact():
    d = rindler_flat_check(a=1.0, L=0.1, tau_max=1.5, n_eval=151)
    assert d["observer_vs_exact_hyperbola_max_abs"] < 1e-9
    assert d["separation_vs_L_over_cosh_max_rel"] < 1e-8
    assert math.isclose(d["measured_diff_accel_at_0"], -0.1, rel_tol=1e-6)         # -a^2 L = -1 * 0.1
    assert math.isclose(d["measured_origin_accel_at_0"], -1.0, rel_tol=1e-6)       # -a


@pytest.mark.parametrize("r0,expect_sign", [(4.0, +1.0), (2.2, -1.0)])
def test_hovering_observer_inertial_plus_tidal(r0, expect_sign):
    """Static observer held by the engine: net relative acceleration -(lambda + a^2) L; at 2 r_s the tidal
    stretching wins (separation), at 1.1 r_s the inertial term wins (approach) - the tidal-only
    prediction has the wrong sign there."""
    h = hovering_check(r0, L=1e-3)
    assert h["observer_hover_max_abs_dr"] < 1e-10
    assert math.isclose(h["measured_diff_accel"], h["exact_lapse_diff_accel"], rel_tol=1e-5)
    assert math.isclose(h["measured_diff_accel"], h["predicted_-(lambda+a2)L"], rel_tol=2e-2)
    assert np.sign(h["measured_diff_accel"]) == expect_sign
    assert np.sign(h["tidal_only_prediction_-lambdaL"]) == +1.0


@pytest.mark.parametrize("L", [0.0, 3.0])
def test_thrust_axis_is_radial_tidal_eigendirection(L):
    """E_1j = 0 for j != 1 in the conditioned tetrad (e_1 = n = thrust axis): the inertial and tidal radial terms add."""
    m = Schwarzschild()
    for r in (10.0, 3.0, 1.0, 1e-3):
        y = initial_state_radial(m, r, 1.0, L)
        Eij = tidal_tensor(m, r, math.pi / 2, y[IUV:IUV + 4], E=y[IEK])["E_ij"]
        assert np.max(np.abs(Eij[0, 1:])) <= 1e-12 * np.max(np.abs(Eij))


def test_thrust_columns_window_and_energy_law():
    """Thrust window 10 r_s -> 0: inertial column 0 above 10 r_s, -a^2 L/c^2 below; total = stretch + inertial;
    carried Killing energy follows the exact law E = E(10 r_s) + alpha (20 - r) inside the window."""
    cfg = SimulationConfig(thrust_alpha_SI=9.81, r0_over_rs=30.0, thrust_r_on_max_over_rs=10.0, rtol=1e-11)
    sim = Simulation(cfg, verbose=False)
    sim.run()
    c = sim.postprocess()
    on = c["r_over_rs"] <= 10.0
    exp_val = inertial_diff_along_thrust_SI(9.81, cfg.body_length_m)
    assert np.all(c["inertial_diff_radial_m_s2"][~on] == 0.0)
    assert np.allclose(c["inertial_diff_radial_m_s2"][on], exp_val, rtol=1e-12, atol=0)
    assert np.array_equal(c["radial_total_diff_m_s2"], c["radial_stretch_m_s2"] + c["inertial_diff_radial_m_s2"])
    # inside the window E(r) = E(first on-step) + alpha (r_first - r); before it the geodesic keeps E = 1
    rr = c["r_geo"][on]
    E = c["E_killing"][on]
    alpha = sim.thrust.alpha
    assert np.allclose(E - E[0], alpha * (rr[0] - rr), rtol=1e-8, atol=1e-6)
    assert np.all(c["E_killing"][~on] == 1.0)
    # the crossover radius where tidal = inertial for 1 g lies deep inside (2.1e-4 r_s)
    assert 2.0e-4 < crossover_radius_geo(alpha) / 2.0 < 2.3e-4
    assert math.isclose(float(thrust_energy_closed_form(1.0, alpha, 20.0, 19.0)), 1.0 + alpha, rel_tol=1e-15)
