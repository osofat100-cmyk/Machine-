"""Dense output (Hairer's DOPRI5 continuous extension) of slab.integrators.DormandPrince54."""
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab.integrators import DormandPrince54  # noqa: E402
from slab.metric import Schwarzschild  # noqa: E402
from slab.geodesic import rhs_lnr, RadialInfallE1, IV, IUV, IUR, ITAU  # noqa: E402


def test_dense_coefficients_symbolic_derive_check():
    """Exact rational check: end points, Hermite derivatives, all order-4 conditions for every theta."""
    spec = importlib.util.spec_from_file_location("verify_dd", ROOT / "tools" / "verify_dopri5_dense_output.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.verify()
    assert all(res.values()), [k for k, v in res.items() if not v]


def _osc(x, y):
    return np.array([y[1], -y[0]])


def test_dense_reproduces_step_end_points_and_t_eval_does_not_change_steps():
    I = DormandPrince54(rtol=1e-9, atol=1e-12)
    y0 = np.array([0.0, 1.0])
    plain = I.integrate(_osc, 0.0, y0, 12.0)
    te = np.linspace(0.0, 12.0, 97)
    res = I.integrate(_osc, 0.0, y0, 12.0, t_eval=te[::-1], dense_output=True)   # unsorted t_eval is accepted
    assert np.array_equal(plain.y, res.y) and np.array_equal(plain.x, res.x)
    # interpolant at every accepted step end point = the step result (exact up to rounding)
    assert np.max(np.abs(res.dense(res.x) - res.y)) < 4e-16 * np.max(np.abs(res.y)) * 10
    assert np.allclose(res.x_eval, te) and res.y_eval.shape == (97, 2)
    assert np.max(np.abs(res.y_eval[:, 0] - np.sin(te))) < 1e-8


def test_dense_output_order_four():
    """One step of y' = y from the exact state: interpolation error at theta = 1/2 scales as h^5."""
    errs = []
    for h in (0.2, 0.1, 0.05):
        I = DormandPrince54(rtol=1.0, atol=1.0, max_step=h)
        res = I.integrate(lambda x, y: y.copy(), 0.0, np.array([1.0]), h, h0=h, dense_output=True)
        assert res.n_accepted == 1
        errs.append(abs(res.dense(0.5 * h)[0] - math.exp(0.5 * h)))
    r1, r2 = errs[0] / errs[1], errs[1] / errs[2]
    assert 24.0 < r1 < 40.0 and 24.0 < r2 < 40.0, (errs, r1, r2)      # 2^5 = 32


def test_dense_output_vs_analytic_E1_geodesic_off_grid():
    """E = 1 radial infall in ln r mode (the engine's own RHS), evaluated at off-grid radii from 100 r_s to 1e-30 r_s."""
    m = Schwarzschild()
    ref = RadialInfallE1()
    r0 = 200.0
    y0 = np.array([0.0, r0, math.pi / 2, 0.0, ref.uv(r0), ref.ur(r0), 0.0, 0.0, 0.0, 1.0])
    atol = np.array([0.0, 0.0, 1e-14, 1e-14, 0.0, 0.0, 1e-14, 1e-14, 0.0, 1e-14])
    I = DormandPrince54(rtol=1e-12, atol=atol, max_step=0.05)
    rng = np.random.default_rng(1)
    x_eval = np.sort(rng.uniform(math.log(2e-30), math.log(r0), 400))[::-1]
    res = I.integrate(lambda x, y: rhs_lnr(m, x, y), math.log(r0), y0, math.log(2e-30), t_eval=x_eval, dense_output=True)
    assert len(res.x_eval) == 400
    on_grid = np.isin(res.x_eval, res.x)
    assert not on_grid.any()                      # genuinely off-grid points
    r = np.exp(res.x_eval)
    ur_err = np.max(np.abs(res.y_eval[:, IUR] / np.array([ref.ur(x) for x in r]) - 1.0))
    uv_err = np.max(np.abs(res.y_eval[:, IUV] / np.array([ref.uv(x) for x in r]) - 1.0))
    tau_err = np.max(np.abs(res.y_eval[:, ITAU] / np.array([ref.tau_between(r0, x) for x in r]) - 1.0))
    v_an = np.array([ref.v_between(r0, x) for x in r])
    v_err = np.max(np.abs(res.y_eval[:, IV] - v_an) / np.maximum(1.0, np.abs(v_an)))
    assert ur_err < 1e-9 and uv_err < 1e-9 and tau_err < 1e-9 and v_err < 1e-9, (ur_err, uv_err, tau_err, v_err)
    # the callable dense solution agrees with t_eval
    assert np.allclose(res.dense(res.x_eval[:20]), res.y_eval[:20], rtol=0, atol=0)


def test_dense_output_with_event_and_backward_integration():
    I = DormandPrince54(rtol=1e-10, atol=1e-12)
    te = np.linspace(0.0, 10.0, 101)
    res = I.integrate(_osc, 10.0, np.array([math.sin(10.0), math.cos(10.0)]), 0.0, t_eval=te,
                      event=lambda x, y: x - 4.5, dense_output=True)
    assert res.terminated_by_event and abs(res.x[-1] - 4.5) < 1e-12
    assert res.x_eval[0] == 10.0 and res.x_eval[-1] >= 4.5 - 1e-12 and np.all(np.diff(res.x_eval) < 0)
    assert np.max(np.abs(res.y_eval[:, 0] - np.sin(res.x_eval))) < 1e-9
    # the event-shortened final step has its own continuous extension
    xm = 0.5 * (res.x[-2] + res.x[-1])
    assert abs(res.dense(xm)[0] - math.sin(xm)) < 1e-9
