"""
Checks from PLAN.md section 12 that do not need the sealed file. Run from ml_etf/:  python3 -m pytest -q tests
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import account as A  # noqa: E402
import features as F  # noqa: E402
import stats as St  # noqa: E402
from models import MENU  # noqa: E402
from strategy import Strategy, run_decisions  # noqa: E402

N = len(F.SYMBOLS)


def synthetic(T=900, seed=1, drift=0.0):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, 0.01, size=(T, N))
    C = 100 * np.exp(np.cumsum(r, axis=0))
    O = C * np.exp(rng.normal(0, 0.003, size=(T, N)))
    V = rng.uniform(1e6, 2e6, size=(T, N))
    dates = np.array([f"{2000 + d // 252}-{1 + (d % 252) // 21:02d}-{1 + d % 21:02d}" for d in range(T)])
    return {"dates": dates, "rate": np.full(T, 2.0), "O": O, "C": C, "V": V}


# ---------- hand-worked examples ----------

def test_cash_growth_and_targets_by_hand():
    p = synthetic(60)
    g = F.cash_growth(p["rate"])
    assert g[0] == 1.0 and g[5] == pytest.approx(1.02 ** (1 / 252))
    sel, tim = F.targets(p, 5)
    t = 10
    R = p["O"][t + 6] / p["O"][t + 1] - 1
    bill = 1.02 ** (5 / 252) - 1
    assert sel[t] == pytest.approx(R - R.mean())
    assert tim[t] == pytest.approx(R[0] - bill)
    assert np.isnan(tim[60 - 6]) and not np.isnan(tim[60 - 7])


def test_inputs_by_hand():
    p = synthetic(300)
    S, M = F.inputs(p)
    t, i = 280, 3
    C = p["C"][:, i]
    assert S[t, i, F.SYM_FEATURES.index("r21")] == pytest.approx(C[t] / C[t - 21] - 1)
    assert S[t, i, F.SYM_FEATURES.index("d200")] == pytest.approx(C[t] / C[t - 199:t + 1].mean() - 1)
    r = np.diff(C[t - 21:t + 1]) / C[t - 21:t]
    assert S[t, i, F.SYM_FEATURES.index("vol21")] == pytest.approx(r.std(ddof=1))
    assert np.isnan(S[250, 0, F.SYM_FEATURES.index("r252")]) and not np.isnan(S[252, 0, F.SYM_FEATURES.index("r252")])


def test_trade_with_costs_and_interest_by_hand():
    T = 4
    O = np.full((T, N), 100.0)
    C = np.full((T, N), 100.0)
    O[1, 0], C[1, 0], O[2, 0], O[2, 1], C[2, 1], C[3, 1] = 110, 110, 120, 50, 50, 55
    g = np.array([1.0, 1.0, 1.0, 1.01])
    W = np.full((T, N), np.nan)
    W[0] = 0.0
    W[0, 0] = 1.0            # day 0: all into SPY
    W[2] = 0.0
    W[2, 1] = 0.5            # day 2: half QQQ, half cash
    v, cash, sh, trades, paid = A.run(O, C, g, W, 0)
    sh0 = 1000 / (100 * 1.0005)
    assert v[1] == pytest.approx(sh0 * 110)
    V2 = sh0 * 120
    cash2 = sh0 * 120 * 0.9995                     # sell all SPY
    q = 0.5 * V2 / 50                              # buy half the pre-trade value of QQQ
    cash2 -= 0.5 * V2 * 1.0005
    assert v[2] == pytest.approx(cash2 + q * 50)
    assert v[3] == pytest.approx(cash2 * 1.01 + q * 55)
    assert trades == 3


def test_purge_rule():
    for h in F.HORIZONS:
        days = F.train_days(1000, h, 252)
        assert days[-1] + 1 + h <= 1000 - F.GAP and days[-1] + 1 + h + 1 > 1000 - F.GAP


# ---------- look-ahead trap ----------

@pytest.mark.parametrize("kind", ["ridge", "gbm"])
@pytest.mark.parametrize("h", [1, 21])
def test_scrambling_the_future_changes_nothing(kind, h):
    p = synthetic(800, seed=3)
    tau = 600
    q = {k: v.copy() for k, v in p.items()}
    rng = np.random.default_rng(9)
    for k in ("O", "C", "V", "rate"):
        q[k][tau + 1:] = rng.permutation(q[k][tau + 1:])
        q[k][tau + 1:] *= 1.3
    out = []
    for panel in (p, q):
        S, M = F.inputs(panel)
        sel, tim = F.targets(panel, h)
        first = F.first_full(S, M)
        days = F.train_days(tau, h, first)
        X = F.selection_X(S, M, days)
        y = sel[days].reshape(-1)
        st = Strategy(kind, MENU[kind][0], h)
        dec = run_decisions(panel, S, M, sel, tim, st, tau, tau, first)
        out.append((X, y, F.timing_X(S, M, days), tim[days], dec[0]["choice"], dec[0]["f_tim"]))
    a, b = out
    for x, z in zip(a[:4], b[:4]):
        np.testing.assert_array_equal(x, z)
    assert a[4] == b[4] and a[5] == b[5]


# ---------- the purge removes fake skill on pure noise ----------

def test_no_fake_skill_on_noise_after_purge():
    """The review's example: on pure-noise prices, a 1-nearest-neighbour model trained right up to the cutoff (no
    purge) predicts the first 21-day answer through overlapping answers; with the purge it cannot."""
    from sklearn.neighbors import KNeighborsRegressor
    p = synthetic(3000, seed=5)
    h = 21
    S, M = F.inputs(p)
    sel, tim = F.targets(p, h)
    first = F.first_full(S, M)
    out = {"no purge": ([], []), "purge": ([], [])}
    for tau in range(700, 2950, 25):
        for kind in out:
            days = np.arange(first, tau) if kind == "no purge" else F.train_days(tau, h, first)
            days = days[~np.isnan(tim[days])]
            X = F.timing_X(S, M, days)
            mu, sd = X.mean(0), X.std(0)
            m = KNeighborsRegressor(n_neighbors=1).fit((X - mu) / sd, tim[days])
            out[kind][0].append(m.predict((F.timing_X(S, M, tau) - mu) / sd)[0])
            out[kind][1].append(tim[tau])
    c = {k: np.corrcoef(*v)[0, 1] for k, v in out.items()}
    print(f"\nnoise data, 1-nearest-neighbour, h=21: correlation of forecast and answer: "
          f"no purge {c['no purge']:.2f}, purge {c['purge']:.2f}")
    assert c["no purge"] > 0.6
    assert abs(c["purge"]) < 0.3


# ---------- statistics against independent sources ----------

def test_pesaran_timmermann_matches_statsmodels():
    from statsmodels.stats.diagnostic import pesaran_timmermann as pt_sm
    rng = np.random.default_rng(0)
    a = rng.random(300) < 0.55
    f = np.where(rng.random(300) < 0.6, a, ~a)
    hit, s, p = St.pesaran_timmermann(a, f)
    ref = pt_sm(a.astype(int), f.astype(int))
    ref_s = getattr(ref, "statistic", ref[0] if isinstance(ref, tuple) else None)
    assert s == pytest.approx(float(ref_s), rel=1e-6)


def test_diebold_mariano_variance_matches_statsmodels_hac():
    import statsmodels.api as sm
    rng = np.random.default_rng(1)
    e1, e2 = rng.normal(size=500), rng.normal(size=500) * 1.1
    d = e1 ** 2 - e2 ** 2
    lags = 4
    fit = sm.OLS(d, np.ones(len(d))).fit(cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": False})
    ref_t = float(fit.tvalues[0])
    s, _ = St.diebold_mariano(e1, e2, lags)
    assert s == pytest.approx(ref_t, rel=1e-6)


def test_expected_max_sharpe_bracket():
    # the review's figure: the bracket equals 1.52 for N = 9
    assert St.expected_max_sharpe(9, 1.0) == pytest.approx(1.52, abs=0.01)


def test_psr_is_one_half_at_its_own_sharpe():
    r = np.random.default_rng(2).normal(0.0005, 0.01, 2500)
    sr = r.mean() / r.std(ddof=1)
    assert St.psr(r, sr) == pytest.approx(0.5)


def test_pbo_on_noise_is_about_half_and_low_for_a_real_winner():
    rng = np.random.default_rng(4)
    blocks = np.repeat(np.arange(10), 252)
    noise = rng.normal(0, 0.01, size=(2520, 20))
    pbs = [St.pbo(np.random.default_rng(k).normal(0, 0.01, size=(2520, 20)), blocks)[0] for k in range(4, 14)]
    pb, n = St.pbo(noise, blocks)
    assert n == 252 and 0.35 < np.mean(pbs) < 0.65
    good = noise.copy()
    good[:, 7] += 0.002
    assert St.pbo(good, blocks)[0] < 0.1


def test_bootstrap_range_covers_the_mean():
    x = np.random.default_rng(5).normal(1.0, 1.0, 1000)
    lo, hi = St.bootstrap(np.mean, x, reps=300)
    assert lo < 1.0 < hi and hi - lo < 0.3


def test_weights_from_choices_sends_only_changes():
    W = A.weights_from_choices(10, N, [1, 3, 5, 7], [2, 2, -1, 4])
    assert np.isnan(W[3, 0]) and W[1, 2] == 1 and (W[5] == 0).all() and W[7, 4] == 1
