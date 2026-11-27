"""The server and the fast simulator must give the same money (PLAN.md section 12). Uses a made-up price file, never
the sealed one."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import account as A  # noqa: E402
import features as F  # noqa: E402
from sealed_client import Server  # noqa: E402


def test_server_equals_fast_simulator(tmp_path):
    rng = np.random.default_rng(7)
    T, n = 300, len(F.SYMBOLS)
    C = 50 * np.exp(np.cumsum(rng.normal(0, 0.012, (T, n)), axis=0))
    O = C * np.exp(rng.normal(0, 0.004, (T, n)))
    df = pd.DataFrame({"date": pd.bdate_range("2030-01-01", periods=T).strftime("%Y-%m-%d"),
                       "rate": rng.uniform(0, 6, T)})
    for i, s in enumerate(F.SYMBOLS):
        df[f"{s}_open"], df[f"{s}_close"], df[f"{s}_volume"] = O[:, i], C[:, i], 1e6
    path = tmp_path / "synthetic.csv"
    df.to_csv(path, index=False)

    plans = {"switcher": {}, "equal": {}, "cashy": {}}
    for d in range(0, T, 7):
        w = np.zeros(n)
        c = rng.integers(-1, n)
        if c >= 0:
            w[c] = 1.0
        plans["switcher"][d] = w.tolist()
    for d in range(0, T, 21):
        plans["equal"][d] = [1.0 / n] * n
    for d in range(0, T, 3):
        w = np.zeros(n)
        w[rng.integers(n)] = rng.uniform(0, 1)
        plans["cashy"][d] = w.tolist()

    served = {k: [] for k in plans}
    with Server(str(path)) as s:
        for d in range(T):
            out = s.next({k: plans[k].get(d) for k in plans})
            for k in plans:
                served[k].append(out["values"][k])
        end = s.next({})
        assert end["done"]
    p = F.arrays(df)
    g = F.cash_growth(p["rate"])
    for k, plan in plans.items():
        W = np.full((T, n), np.nan)
        for d, w in plan.items():
            W[d] = w
        v, cash, sh, trades, paid = A.run(p["O"], p["C"], g, W, 0)
        np.testing.assert_allclose(v, served[k], atol=0.005, rtol=0)
        assert trades == end["accounts"][k]["trades"]
        assert abs(paid - end["accounts"][k]["costs"]) < 0.005
