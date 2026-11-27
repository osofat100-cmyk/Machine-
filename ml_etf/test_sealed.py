#!/usr/bin/env python3
"""
The sealed test, run once (PLAN.md sections 9-11). 4 Jan 2016 - 20 Nov 2026, one day at a time from day_server.py.

The 9 locked strategies and the 3 yardsticks decide after each close using only the development file plus the days
already handed out; their targets go to the server with the next request and fill at that day's open. Afterwards
the fast simulator re-runs every account on the handed-out days (must match the server to the cent), and runs the
coin flips and the fresh-$1,000-per-year view.

    python3 ml_etf/test_sealed.py
      -> ml_etf/sealed_summary.csv, sealed_years.csv, sealed_dm.csv, sealed_curves.csv, sealed_report.md,
         sealed_curves.png, sealed_3d.png, sealed_years.png
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json  # noqa: E402
import pickle  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from multiprocessing import Pool  # noqa: E402

import numpy as np
import pandas as pd

import account as A
import features as F
import stats as St
from sealed_client import Server
from strategy import Strategy, run_decisions

HERE = os.path.dirname(os.path.abspath(__file__))
N_TRIALS = 36
N_COIN = 1000
YARDSTICKS = ["hold_spy", "equal_weight", "momentum"]
OUT = HERE                     # where results go (a scratch folder for the rehearsal)
DEV = os.path.join(HERE, "data", "dev.csv")
SEALED_FILE = None              # None = the server's default, data/sealed/etf_test.csv


def locked_settings():
    path = os.path.join(HERE, "locked.json")
    st = subprocess.run(["git", "status", "--porcelain", path], capture_output=True, text=True, cwd=HERE).stdout
    tracked = subprocess.run(["git", "ls-files", path], capture_output=True, text=True, cwd=HERE).stdout
    assert tracked.strip() and not st.strip(), "locked.json must be committed and unchanged before the sealed test"
    with open(path) as f:
        return json.load(f)


def one_hot(c, n):
    w = [0.0] * n
    if c >= 0:
        w[c] = 1.0
    return w


def momentum_choice(p, t):
    C, g = p["C"], F.cash_growth(p["rate"])
    past = C[t - 21] / C[t - 252] - 1
    spy = C[t, F.SPY] / C[t - 252, F.SPY] - 1
    bill = np.prod(g[t - 251:t + 1]) - 1
    return -1 if spy < bill else int(np.argmax(past))


def walk(locked):
    p = F.load(DEV)
    n = len(F.SYMBOLS)
    s0 = len(p["dates"]) - 1
    strategies = {key: Strategy(c["kind"], c["setting"], c["h"]) for key, c in locked["chosen"].items()}
    last_target = {k: None for k in list(strategies) + YARDSTICKS}
    orders_log = {k: {} for k in last_target}           # day index -> weights sent (filled at that day's open)
    decisions = {k: [] for k in strategies}
    served_values = {k: [] for k in last_target}
    next_date = None
    t0 = time.time()

    with Server(SEALED_FILE) as srv:
        t = s0
        while True:
            # ---- decide after day t's close, using rows 0..t only ----
            S, M = F.inputs(p)
            first = F.first_full(S, M)
            cache = {}
            orders = {}
            nd = next_date if t > s0 else None
            for key, st in strategies.items():
                need_train = t == s0 or int(p["dates"][t][:4]) != st.year
                if need_train:
                    if st.h not in cache:
                        cache[st.h] = F.targets(p, st.h)
                    sel, tim = cache[st.h]
                    year = int(p["dates"][t][:4]) + (1 if t == s0 else 0)   # s0 is the last day of a year
                    st.train(S, M, sel, tim, t, first, year)
                if (t - s0) % st.h == 0:
                    c, ft, fs = st.decide(S, M, t)
                    decisions[key].append({"day": t, "choice": c, "f_tim": ft, "f_sel": fs.tolist()})
                    if c != last_target[key]:
                        orders[key] = one_hot(c, n)
                        last_target[key] = c
            if t == s0:
                orders["hold_spy"] = one_hot(F.SPY, n)
            month_end = t == s0 or (nd is not None and nd[:7] != p["dates"][t][:7])
            if month_end:
                orders["equal_weight"] = [1.0 / n] * n
                c = momentum_choice(p, t)
                if c != last_target["momentum"]:
                    orders["momentum"] = one_hot(c, n)
                    last_target["momentum"] = c
            for k in last_target:
                orders.setdefault(k, None)
            # ---- ask for the next day ----
            out = srv.next(orders)
            if out.get("done"):
                raise RuntimeError("server ended before the walk did")
            d = out["day"]
            for k, w in orders.items():
                if w is not None:
                    orders_log[k][t + 1] = w
            p = F.join(p, {"dates": np.array([d["date"]]), "rate": np.array([d["rate"]]),
                           "O": np.array([d["open"]]), "C": np.array([d["close"]]), "V": np.array([d["volume"]])})
            t += 1
            for k in last_target:
                served_values[k].append(out["values"][k])
            next_date = out["next_date"]
            if t % 250 == 0:
                print(f"  {d['date']}  ({time.time() - t0:.0f}s)", flush=True)
            if next_date is None:
                end = srv.next({})
                assert end["done"]
                break
    return p, s0, decisions, orders_log, served_values, end["accounts"]


def _replay(job):
    """Re-make one strategy's decisions on the finished panel in one go (no day server)."""
    p, kind, setting, h, s0, end = job
    S, M = F.inputs(p)
    sel, tim = F.targets(p, h)
    return run_decisions(p, S, M, sel, tim, Strategy(kind, setting, h), s0, end, F.first_full(S, M))


def fast_values(p, start, orders, T, n, until=None):
    W = np.full((T, n), np.nan)
    for d, w in orders.items():
        if until is None or d <= until:
            W[d] = w
    return W


def rehearsal():
    """Dry run of this whole file on development data only: 2000-2012 as 'known', 2013-2015 served as if sealed.
    Settings: the first menu entry of each model. Results go to a scratch folder and mean nothing."""
    import tempfile
    from models import MENU
    global OUT, DEV, SEALED_FILE
    OUT = tempfile.mkdtemp(prefix="rehearsal_", dir=os.environ.get("REHEARSAL_DIR"))
    df = pd.read_csv(DEV)
    DEV, SEALED_FILE = os.path.join(OUT, "dev.csv"), os.path.join(OUT, "fake_sealed.csv")
    df[df.date < "2013-01-01"].to_csv(DEV, index=False)
    df[df.date >= "2013-01-01"].to_csv(SEALED_FILE, index=False)
    chosen = {f"{k}_h{h}": {"kind": k, "h": h, "setting": MENU[k][0], "label": f"{k} menu 0"}
              for k in ("ridge", "gbm", "mlp") for h in F.HORIZONS}
    return {"chosen": chosen, "pbo_all_36": float("nan")}


def checkpoint_dir():
    """Saved stages live next to the sealed file (git-ignored, never published); the rehearsal keeps its own."""
    d = OUT if SEALED_FILE else os.path.join(os.path.dirname(HERE), "data", "sealed", "checkpoints")
    os.makedirs(d, exist_ok=True)
    return d


def saved(name, make):
    """Load a finished stage from disk, or run it and save it at once, so a stop never loses finished work."""
    path = os.path.join(checkpoint_dir(), name + ".pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            print(f"  loaded saved stage: {name}", flush=True)
            return pickle.load(f)
    out = make()
    with open(path + ".tmp", "wb") as f:
        pickle.dump(out, f)
    os.replace(path + ".tmp", path)
    print(f"  saved stage: {name}", flush=True)
    return out


def main():
    import sys
    locked = rehearsal() if "--rehearse" in sys.argv else locked_settings()
    print(f"output folder: {OUT}", flush=True)
    print("sealed test: locked settings " + ", ".join(f"{k}={v['label']}" for k, v in locked["chosen"].items()),
          flush=True)
    p, s0, decisions, orders_log, served, accounts = saved("walk", lambda: walk(locked))
    # the account curves and every decision, written as plain files as soon as the walk is done
    curves0 = pd.DataFrame({k: served[k] for k in served}, index=p["dates"][s0 + 1:])
    curves0.index.name = "date"
    curves0.to_csv(os.path.join(OUT, "sealed_curves.csv"), float_format="%.2f")
    with open(os.path.join(OUT, "sealed_decisions.json"), "w") as f:
        json.dump({k: [{"date": p["dates"][x["day"]], "day": int(x["day"]), "choice": int(x["choice"]),
                        "f_tim": float(x["f_tim"])} for x in v] for k, v in decisions.items()}, f)
    T, n = p["O"].shape
    start = s0 + 1
    g = F.cash_growth(p["rate"])
    dates = p["dates"][start:]
    print(f"walk done: {dates[0]} -> {dates[-1]}, {len(dates)} days", flush=True)

    # ---- check: fast simulator equals the server for every account ----
    sim = {}
    for k, orders in orders_log.items():
        W = fast_values(p, start, orders, T, n)
        v, cash, sh, trades, paid = A.run(p["O"], p["C"], g, W, start)
        sim[k] = v[start:]
        gap = np.max(np.abs(sim[k] - np.array(served[k])))
        assert gap < 0.005, f"{k}: fast simulator and server differ by ${gap:.4f}"
        assert trades == accounts[k]["trades"] and abs(paid - accounts[k]["costs"]) < 0.005
    print("check: fast simulator equals the server to the cent for all 12 accounts", flush=True)

    # ---- check: decisions made day by day equal decisions re-made on the finished panel (no look-ahead) ----
    end = T - 2
    jobs = [(p, c["kind"], c["setting"], c["h"], s0, end) for c in locked["chosen"].values()]
    todo = [(key, job) for key, job in zip(locked["chosen"], jobs)
            if not os.path.exists(os.path.join(checkpoint_dir(), f"replay_{key}.pkl"))]
    if todo:
        with Pool(4) as pool:
            for key, rep in zip([k for k, _ in todo], pool.imap(_replay, [j for _, j in todo])):
                saved(f"replay_{key}", lambda: rep)
    replays = [saved(f"replay_{key}", None) for key in locked["chosen"]]
    for key, rep in zip(locked["chosen"], replays):
        live = decisions[key]
        assert [x["day"] for x in live] == [x["day"] for x in rep], key
        assert [x["choice"] for x in live] == [x["choice"] for x in rep], f"{key}: choices differ"
        gap = max(abs(a["f_tim"] - b["f_tim"]) for a, b in zip(live, rep))
        assert gap < 1e-9, f"{key}: timing forecasts differ by {gap}"
    print("check: day-by-day decisions equal the decisions re-made on the finished panel", flush=True)

    # ---- realised targets (after the walk, on the full panel) ----
    real = {h: F.targets(p, h) for h in F.HORIZONS}
    S, M = F.inputs(p)
    first = F.first_full(S, M)

    def daily(values):
        v = np.asarray(values)
        return np.diff(np.concatenate([[1000.0], v])) / np.concatenate([[1000.0], v[:-1]])

    cash_r = g[start:] - 1
    cash_r[0] = 0.0
    hold_r = daily(served["hold_spy"])
    names = list(decisions) + YARDSTICKS
    rows, years_rows = [], []
    year_of = np.array([int(x[:4]) for x in p["dates"]])
    rng_boot = np.random.default_rng(0)
    boot_idx = [St.stationary_bootstrap_index(len(dates), 21, rng_boot) for _ in range(2000)]

    def brange(fn, data):
        vals = np.array([fn(data[ix]) for ix in boot_idx])
        return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))

    coin_ends = {}
    for k in names:
        vals = np.array(served[k])
        r = daily(vals)
        ex = r - cash_r
        act = r - hold_r
        row = {"strategy": k, "end_$": vals[-1], "sharpe_above_cash": St.sharpe(ex),
               "ir_vs_spy": St.sharpe(act) if k != "hold_spy" else 0.0, "worst_drop": St.max_drop(vals),
               "trades": accounts[k]["trades"], "costs_$": accounts[k]["costs"]}
        data = np.column_stack([r, cash_r, hold_r])
        row["end_$_range"] = brange(lambda x: 1000 * np.prod(1 + x[:, 0]), data)
        row["sharpe_range"] = brange(lambda x: St.sharpe(x[:, 0] - x[:, 1]), data)
        if k != "hold_spy":
            row["ir_range"] = brange(lambda x: St.sharpe(x[:, 0] - x[:, 2]), data)
            row["dsr_vs_spy"] = St.dsr(act, N_TRIALS)
        if k in decisions:
            dec = decisions[k]
            h = locked["chosen"][k]["h"]
            sel_r, tim_r = real[h]
            done = [x for x in dec if x["day"] + 1 + h < T]
            inv = [x for x in done if x["choice"] >= 0]
            out_ = [x for x in done if x["choice"] < 0]
            y = np.array([tim_r[x["day"]] for x in done])
            f = np.array([x["f_tim"] for x in done])
            csum = np.nancumsum(np.where(np.isnan(tim_r), 0, tim_r))
            bench = []
            for x in done:
                last = x["day"] - 1 - h
                bench.append((csum[last] - (csum[first - 1] if first > 0 else 0)) / (last - first + 1))
            row["r2_os_timing"] = St.r2_os(y, f, np.array(bench))
            fs = np.concatenate([x["f_sel"] for x in done])
            ys = np.concatenate([sel_r[x["day"]] for x in done])
            row["r2_os_selection"] = St.r2_os(ys, fs, np.zeros_like(ys))
            hit, pts, ptp = St.pesaran_timmermann(y > 0, f > 0)
            row.update({"pt_hit_rate": hit, "pt_stat": pts, "pt_p": ptp,
                        "invested_share": float(np.mean([x["choice"] >= 0 for x in dec])),
                        "timing_skill": (np.mean([tim_r[x["day"]] for x in inv]) if inv else np.nan)
                        - (np.mean([tim_r[x["day"]] for x in out_]) if out_ else 0.0),
                        "selection_skill": np.mean([sel_r[x["day"]][x["choice"]] for x in inv]) if inv else np.nan})
            # coin flips: same decision days, same share invested
            pinv = row["invested_share"]
            days = [x["day"] + 1 for x in dec]

            def coins():
                ends = np.empty(N_COIN)
                for seed in range(N_COIN):
                    rng = np.random.default_rng(seed)
                    ch = [int(rng.integers(n)) if rng.random() < pinv else -1 for _ in days]
                    W = A.weights_from_choices(T, n, days, ch)
                    ends[seed] = A.run(p["O"], p["C"], g, W, start)[0][-1]
                return ends
            ends = saved(f"coins_{k}", coins)
            coin_ends[k] = ends
            row["coin_p"] = (1 + np.sum(ends >= vals[-1])) / (1 + N_COIN)
            row["coin_median_$"] = float(np.median(ends))
        rows.append(row)
        # fresh $1,000 each calendar year
        orders = orders_log[k]
        for yr in sorted(set(year_of[start:])):
            ys_ = int(np.where(year_of == yr)[0][0])
            ye = int(np.where(year_of == yr)[0][-1])
            W = fast_values(p, start, orders, T, n)
            if np.isnan(W[ys_, 0]):
                prior = [d for d in orders if d < ys_]
                if prior:
                    W[ys_] = orders[max(prior)]
            v = A.run(p["O"], p["C"], g, W, ys_)[0]
            years_rows.append({"strategy": k, "year": yr, "end_$": v[ye]})

    summ = pd.DataFrame(rows)
    mom_end = summ.loc[summ.strategy == "momentum", "end_$"].iloc[0]
    passes = []
    for _, r in summ.iterrows():
        if r["strategy"] in decisions:
            ok = [r["dsr_vs_spy"] >= 0.95, r["ir_range"][0] > 0, r["end_$"] > mom_end, r["coin_p"] < 0.05]
            passes.append("yes" if all(ok) else "no")
            summ.loc[_, "pass_dsr"], summ.loc[_, "pass_ir"], summ.loc[_, "pass_momentum"], summ.loc[_, "pass_coin"] = ok
        else:
            passes.append("-")
    summ["beats_spy"] = passes
    summ.to_csv(os.path.join(OUT, "sealed_summary.csv"), index=False, float_format="%.6g")
    yrs = pd.DataFrame(years_rows).pivot(index="year", columns="strategy", values="end_$")[names]
    yrs.to_csv(os.path.join(OUT, "sealed_years.csv"), float_format="%.2f")
    curves = pd.DataFrame({k: served[k] for k in names}, index=dates)
    curves.index.name = "date"
    curves.to_csv(os.path.join(OUT, "sealed_curves.csv"), float_format="%.2f")

    # Diebold-Mariano between models for each horizon
    dm = []
    for h in F.HORIZONS:
        keys = [k for k in decisions if locked["chosen"][k]["h"] == h]
        tim_r = real[h][1]
        err = {}
        for k in keys:
            done = [x for x in decisions[k] if x["day"] + 1 + h < T]
            err[k] = np.array([x["f_tim"] - tim_r[x["day"]] for x in done])
        for a in range(len(keys)):
            for b in range(a + 1, len(keys)):
                s, pv = St.diebold_mariano(err[keys[a]], err[keys[b]], max(h - 1, 0))
                dm.append({"horizon": h, "model_a": keys[a], "model_b": keys[b], "dm_stat": s, "p_value": pv,
                           "note": "positive = model b forecasts better"})
    pd.DataFrame(dm).to_csv(os.path.join(OUT, "sealed_dm.csv"), index=False, float_format="%.4f")
    with open(os.path.join(OUT, "sealed_decisions.json"), "w") as f:
        json.dump({k: [{kk: vv for kk, vv in x.items() if kk != "f_sel"} | {"date": p["dates"][x["day"]]}
                       for x in v] for k, v in decisions.items()}, f)
    graphs(curves, yrs, names, decisions)
    report(summ, yrs, dm, locked, dates)
    print(summ[["strategy", "end_$", "sharpe_above_cash", "ir_vs_spy", "worst_drop", "trades"]].to_string(index=False))


def graphs(curves, yrs, names, decisions):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = pd.to_datetime(curves.index)
    fig, ax = plt.subplots(figsize=(16, 8.5))
    for k in names:
        style = {"hold_spy": dict(color="black", lw=2.5), "equal_weight": dict(color="grey", lw=2, ls="--"),
                 "momentum": dict(color="tab:brown", lw=2, ls=":")}.get(k, dict(lw=1.2))
        ax.plot(x, curves[k], label=f"{k} (\\${curves[k].iloc[-1]:,.0f})", **style)
    ax.axhline(1000, color="black", lw=0.6, ls="--")
    ax.set_yscale("log")
    ax.set_ylabel(f"\\$ (start \\$1,000 on {curves.index[0]}, log scale)")
    ax.set_title(f"Sealed test {curves.index[0]} to {curves.index[-1]}: 9 machine-learning strategies vs holding SPY "
                 "and the yardsticks")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "sealed_curves.png"), dpi=110)

    keys = list(decisions)
    Z = np.array([[yrs.loc[y, k] / 1000 - 1 for y in yrs.index] for k in keys]) * 100
    Zs = np.array([yrs.loc[y, "hold_spy"] / 1000 - 1 for y in yrs.index]) * 100
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_subplot(projection="3d")
    X, Y = np.meshgrid(np.arange(len(yrs.index)), np.arange(len(keys)))
    ax.plot_surface(X, Y, Z - Zs[None, :], cmap="viridis", linewidth=0.3, edgecolor="k", alpha=0.9)
    ax.plot_surface(X, Y, np.zeros_like(Z), color="red", alpha=0.18)
    ax.set_xticks(range(len(yrs.index)))
    ax.set_xticklabels(yrs.index, fontsize=7)
    ax.set_yticks(range(len(keys)))
    ax.set_yticklabels(keys, fontsize=7)
    ax.set_zlabel("year's return minus holding SPY (% points)")
    ax.set_title("Each strategy, each year, against holding SPY (red sheet = same as SPY)")
    ax.view_init(elev=28, azim=-60)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "sealed_3d.png"), dpi=110)

    fig, ax = plt.subplots(figsize=(17, 7))
    width = 0.8 / len(names)
    for j, k in enumerate(names):
        ax.bar(np.arange(len(yrs.index)) + j * width, yrs[k] / 1000 - 1, width,
               color="black" if k == "hold_spy" else None, label=k)
    ax.set_xticks(np.arange(len(yrs.index)) + 0.4)
    ax.set_xticklabels(yrs.index)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("return that year, fresh \\$1,000")
    ax.legend(fontsize=7, ncol=4)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "sealed_years.png"), dpi=110)


def report(summ, yrs, dm, locked, dates):
    L = [f"# Sealed test result: {dates[0]} to {dates[-1]} ({len(dates)} trading days)", "",
         "Settings were locked on the development years (2006-2015) and committed before this test.",
         f"N = {N_TRIALS} combinations tried. PBO (development) over all 36: {locked['pbo_all_36']:.2f}.", "",
         "| Strategy | $1,000 became | 95% range | Sharpe above cash | IR vs SPY | DSR | Worst drop | Trades | "
         "Coin-flip p | Beats SPY? |", "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in summ.iterrows():
        rng = r["end_$_range"]
        L.append(f"| {r['strategy']} | ${r['end_$']:,.2f} | ${rng[0]:,.0f}-${rng[1]:,.0f} | {r['sharpe_above_cash']:.2f} | "
                 f"{r['ir_vs_spy']:.2f} | {r.get('dsr_vs_spy', float('nan')):.2f} | {r['worst_drop']:.0%} | "
                 f"{r['trades']} | {r.get('coin_p', float('nan')):.3f} | "
                 f"{r['beats_spy']} |")
    L += ["", "Forecast quality (strategies only):", "",
          "| Strategy | R2_OS timing | R2_OS selection | Direction hit rate | PT p | Timing skill | Selection skill | Invested |",
          "|---|---|---|---|---|---|---|---|"]
    for _, r in summ.iterrows():
        if "r2_os_timing" in r and not pd.isna(r.get("r2_os_timing")):
            L.append(f"| {r['strategy']} | {r['r2_os_timing']:.4f} | {r['r2_os_selection']:.4f} | {r['pt_hit_rate']:.1%} | "
                     f"{r['pt_p']:.3f} | {r['timing_skill']:+.4f} | {r['selection_skill']:+.4f} | {r['invested_share']:.0%} |")
    with open(os.path.join(OUT, "sealed_report.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
