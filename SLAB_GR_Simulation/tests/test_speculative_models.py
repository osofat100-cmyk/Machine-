"""Tests of the SPECULATIVE toy models (Hayward, Bardeen, Dymnikova). These check the implementation of the
published metric functions and of the toy integration; they do NOT validate the models as physics."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import sympy as sp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab.speculative.models import Hayward, Bardeen, Dymnikova, run_model  # noqa: E402
from slab.curvature import kretschmann_closed_form  # noqa: E402
from slab.trajectory import Simulation, SimulationConfig  # noqa: E402

MU = 1e52                      # M / l in core units, as used by run_speculative_suite
r, M, g = sp.symbols("r M g", positive=True)
SYMBOLIC = {
    "hayward": (lambda: Hayward(M=MU), 1 - 2 * M * r**2 / (r**3 + 2 * M)),
    "bardeen": (lambda: Bardeen(M=MU, g=(2 * MU) ** (1 / 3)), 1 - 2 * M * r**2 / (r**2 + g**2) ** sp.Rational(3, 2)),
    "dymnikova": (lambda: Dymnikova(M=MU), 1 - (2 * M / r) * (1 - sp.exp(-r**3 / (2 * M)))),
}


@pytest.mark.parametrize("name", list(SYMBOLIC))
def test_derivatives_match_sympy(name):
    make, fexpr = SYMBOLIC[name]
    model = make()
    subs = {M: sp.Float(MU, 200), g: sp.Float((2 * MU) ** (1 / 3), 200)}
    f1, f2 = sp.diff(fexpr, r), sp.diff(fexpr, r, 2)
    for rv in (1e-3, 0.3, 1.0, 3.0, 1e3, 1e10, 1e30):
        vals = {k: float(e.subs(subs).subs(r, sp.Float(rv, 200)).evalf(150)) for k, e in (("f", fexpr), ("df", f1), ("d2f", f2))}  # 150 digits: 1 - exp(-5e-62) must not cancel
        for k, got in (("f", model.f(rv)), ("df", model.df(rv)), ("d2f", model.d2f(rv))):
            ref = vals[k]
            assert math.isclose(got, ref, rel_tol=1e-9, abs_tol=1e-12 * max(1.0, abs(ref))), (name, k, rv, got, ref)


@pytest.mark.parametrize("name", list(SYMBOLIC))
def test_de_sitter_core_and_curvature_limit(name):
    model = SYMBOLIC[name][0]()
    for rv in (1e-4, 1e-3):
        assert math.isclose(model.f(rv), 1 - rv**2, rel_tol=1e-9, abs_tol=1e-12)      # f = 1 - r^2/l^2 + O(r^4)
    assert math.isclose(kretschmann_closed_form(model, 1e-4), 24.0, rel_tol=1e-6)      # de Sitter: K = 24 / l^4


def test_toy_integration_in_the_core():
    """E = 1 radial infall: in the de Sitter core u^r = -r/l, so the proper time between two core radii is
    l ln(r1/r2).  (The exported tau is accumulated from the horizon, ~(4/3) mu ~ 1e52 core lengths, so it
    cannot resolve core-scale intervals in double precision; the check uses the exported u^r instead.)"""
    sim = Simulation(SimulationConfig(), verbose=False)
    out = run_model(Hayward(M=MU), sim, 1e-2, ell_m=1.0)
    assert out["status"] == "reached_x_end"
    rr = np.array(out["r_geo"]) * MU                        # back to core units
    ur = np.array(out["u_r"])
    core = rr < 0.05
    assert np.allclose(ur[core], -rr[core], rtol=5e-3)
    i1, i2 = int(np.argmin(abs(rr - 0.04))), len(rr) - 1
    lnr = np.log(rr[i2:i1 - 1:-1] if i1 > 0 else rr[::-1])
    dtau = np.trapezoid(rr[i2:i1 - 1:-1] / np.abs(ur[i2:i1 - 1:-1]), lnr)       # tau = int dr/|u^r| = int r dlnr/|u^r|
    assert math.isclose(dtau, math.log(rr[i1] / rr[i2]), rel_tol=5e-3)
    assert out["max_norm_residual_conditioned"] < 1e-9
    assert out["inner_horizon_r_m"] is not None and abs(Hayward(M=MU).f(out["inner_horizon_r_m"])) < 1e-9
