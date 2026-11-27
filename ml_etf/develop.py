#!/usr/bin/env python3
"""
Development years only (PLAN.md section 8): run all 36 menu combinations on 2006-2015 with $1,000, retraining every
year, choose one setting per (model, horizon), compute the probability of backtest overfitting, and lock.

    python3 ml_etf/develop.py
      -> ml_etf/dev_results.csv     all 36 combinations (used for choosing, not evidence)
      -> ml_etf/locked.json         chosen settings, N = 36, PBO
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import time  # noqa: E402
from multiprocessing import Pool  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import account as A  # noqa: E402
import features as F  # noqa: E402
import stats as St  # noqa: E402
from models import KINDS, MENU, name  # noqa: E402
from strategy import Strategy, run_decisions  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_YEAR, LAST_YEAR = 2006, 2015
N_TRIALS = 36


def setup():
    p = F.load(os.path.join(HERE, "data", "dev.csv"))
    assert p["dates"][-1] < "2016-01-01"
    years = np.array([int(d[:4]) for d in p["dates"]])
    s0 = int(np.where(years < FIRST_YEAR)[0][-1])
    return p, s0, years


def one(job):
    kind, k, h = job
    p, s0, years = setup()
    S, M = F.inputs(p)
    sel, tim = F.targets(p, h)
    first = F.first_full(S, M)
    T, n = p["O"].shape
    t0 = time.time()
    st = Strategy(kind, MENU[kind][k], h)
    dec = run_decisions(p, S, M, sel, tim, st, s0, T - 2, first)
    W = A.weights_from_choices(T, n, [d["day"] + 1 for d in dec], [d["choice"] for d in dec])
    g = F.cash_growth(p["rate"])
    v, cash, sh, trades, paid = A.run(p["O"], p["C"], g, W, s0 + 1)
    vals = v[s0 + 1:]
    r = np.diff(np.concatenate([[1000.0], vals])) / np.concatenate([[1000.0], vals[:-1]])
    ex = r - (g[s0 + 1:] - 1)
    ex[0] = r[0]                                 # no cash growth on the first day
    return {"kind": kind, "k": k, "h": h, "setting": name(kind, MENU[kind][k]), "end_$": float(vals[-1]),
            "sharpe_above_cash": St.sharpe(ex), "trades": int(trades), "costs_$": float(paid),
            "invested_share": float(np.mean([d["choice"] >= 0 for d in dec])),
            "worst_drop": St.max_drop(vals), "seconds": round(time.time() - t0, 1),
            "excess": ex.tolist(), "trained_at": st.trained_at}


def main():
    p, s0, years = setup()
    print(f"development run: decisions from {p['dates'][s0]} (first fill {p['dates'][s0 + 1]}) "
          f"to {p['dates'][-1]}, {len(p['dates']) - s0 - 1} trading days", flush=True)
    jobs = [(kind, k, h) for kind in ("mlp", "gbm", "ridge") for h in F.HORIZONS for k in range(len(MENU[kind]))]
    assert len(jobs) == N_TRIALS
    res = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(one, jobs):
            res.append(r)
            print(f"  {len(res):>2}/36  h={r['h']:>2}  {r['setting']:<34} ${r['end_$']:>9,.2f}  "
                  f"Sharpe above cash {r['sharpe_above_cash']:+.2f}  trades {r['trades']:>4}  "
                  f"invested {r['invested_share']:.0%}  ({r['seconds']}s)", flush=True)
    res.sort(key=lambda r: (KINDS.index(r["kind"]), r["h"], r["k"]))

    # bug check: every training row's answer was known by its cutoff (purge), recorded at each retrain
    for r in res:
        for tau, last_row, nrows in r["trained_at"]:
            assert last_row + 1 + r["h"] <= tau - F.GAP

    g = F.cash_growth(p["rate"])
    hold = p["C"][s0 + 1:, F.SPY] / (p["O"][s0 + 1, F.SPY] * (1 + A.COST)) * 1000
    choose = {}
    for kind in KINDS:
        for h in F.HORIZONS:
            group = [r for r in res if r["kind"] == kind and r["h"] == h]
            best = max(group, key=lambda r: (r["sharpe_above_cash"], -r["k"]))
            choose[f"{kind}_h{h}"] = best
    R = np.column_stack([r["excess"] for r in res])
    blocks = years[s0 + 1:]
    pbo_all, splits = St.pbo(R, blocks)
    pbo_group = {}
    for key in choose:
        kind, h = key.split("_h")
        cols = [j for j, r in enumerate(res) if r["kind"] == kind and r["h"] == int(h)]
        pbo_group[key] = St.pbo(R[:, cols], blocks)[0]

    locked = {"N_trials": N_TRIALS, "development": f"{p['dates'][s0 + 1]} to {p['dates'][-1]}",
              "pbo_all_36": pbo_all, "pbo_splits": splits, "pbo_within_each_model_horizon": pbo_group,
              "chosen": {key: {"kind": r["kind"], "h": r["h"], "menu_index": r["k"],
                               "setting": MENU[r["kind"]][r["k"]], "label": r["setting"],
                               "dev_end_$": round(r["end_$"], 2), "dev_sharpe_above_cash": round(r["sharpe_above_cash"], 3)}
                         for key, r in choose.items()},
              "dev_hold_spy_end_$": round(float(hold[-1] * (1 - A.COST)), 2)}
    with open(os.path.join(HERE, "locked.json"), "w") as f:
        json.dump(locked, f, indent=2, default=list)
    cols = ["kind", "h", "setting", "end_$", "sharpe_above_cash", "trades", "costs_$", "invested_share", "worst_drop"]
    out = pd.DataFrame([{c: r[c] for c in cols} for r in res])
    out["chosen"] = [choose[f"{r['kind']}_h{r['h']}"] is r for r in res]
    out.to_csv(os.path.join(HERE, "dev_results.csv"), index=False, float_format="%.4f")

    print(f"\nhold SPY over the same development years: $1,000 -> ${locked['dev_hold_spy_end_$']:,.2f}")
    print(f"PBO over all 36: {pbo_all:.2f} ({splits} splits); within each model/horizon: "
          + ", ".join(f"{k} {v:.2f}" for k, v in pbo_group.items()))
    for key, c in locked["chosen"].items():
        print(f"  locked {key:<9} {c['label']:<34} dev ${c['dev_end_$']:,.2f}  Sharpe above cash {c['dev_sharpe_above_cash']:+.2f}")


if __name__ == "__main__":
    main()
