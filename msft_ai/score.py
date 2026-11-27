#!/usr/bin/env python3
"""
Score the AI trader (PLAN.md): AI vs holding Microsoft, holding SPY (close to close) and 1,000 random-timing
shuffles that keep the AI's number of switches and days in Microsoft. Prices are read by walking the day server
again (nothing else opens the sealed folder).

    python3 msft_ai/score.py   -> msft_ai/report.md, results.csv, years.csv, curves.png
"""
import csv
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_etf"))
import stats as St  # noqa: E402  (shared statistics: sharpe, max_drop, stationary bootstrap)

from ai_trader import FIRST_DECISION, LAST_DAY, Server  # noqa: E402
from day_server import COST, bey  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
N_SHUFFLE = 1000


def walk_prices():
    rows = []
    with Server() as s:
        while True:
            out = s.next({})
            if out.get("done"):
                break
            d = out["day"]
            if d["date"] >= FIRST_DECISION:
                p = d["prices"]
                rows.append({"date": d["date"], "o": p["MSFT_open_tr"], "c": p["MSFT_close_tr"],
                             "spy": p["SPY_close"], "bill": p["TBILL3M"]})
            if d["date"] >= LAST_DAY:
                break
    return pd.DataFrame(rows).set_index("date")


def simulate(px, pos_after):
    """pos_after[k] = position chosen after close of day k (k = 0 is FIRST_DECISION). Fills at open of day k+1.
    Returns account value at each close from day 1 on (same rules as day_server.py)."""
    o, c, bill = px["o"].values, px["c"].values, px["bill"].values
    cash, sh, vals, trades = 1000.0, 0.0, [], 0
    for k in range(1, len(px)):
        if k > 1:
            cash *= (1.0 + bey(bill[k - 1]) / 100.0) ** (1.0 / 252.0)
        want = pos_after[k - 1]
        if want == 1 and cash > 0:
            sh += cash / (1.0 + COST) / o[k]
            cash = 0.0
            trades += 1
        elif want == 0 and sh > 0:
            cash += sh * o[k] * (1.0 - COST)
            sh = 0.0
            trades += 1
        vals.append(cash + sh * c[k])
    return np.array(vals), trades


def runs(pos):
    out, cur, n = [], pos[0], 0
    for x in pos:
        if x == cur:
            n += 1
        else:
            out.append((cur, n))
            cur, n = x, 1
    out.append((cur, n))
    return out


def shuffled(pos, rng):
    r = runs(pos)
    ins = [n for s, n in r if s == 1]
    outs = [n for s, n in r if s == 0]
    rng.shuffle(ins)
    rng.shuffle(outs)
    seq, i, j = [], 0, 0
    for s, _ in r:                                     # same alternation, shuffled lengths
        if s == 1:
            seq += [1] * ins[i]
            i += 1
        else:
            seq += [0] * outs[j]
            j += 1
    return np.array(seq)


def main():
    with open(os.path.join(HERE, "answers.csv"), newline="") as f:
        ans = {r["date"]: r for r in csv.DictReader(f)}
    served = pd.read_csv(os.path.join(HERE, "values.csv")).set_index("date")
    px = walk_prices()
    dates = list(px.index)
    assert dates[-1] == LAST_DAY and len(served) == len(dates) - 1, "the AI run is not finished"
    pos, p = [], 0
    for d in dates[:-1]:
        dec = ans[d]["decision"]
        p = 1 if dec == "BUY" else 0 if dec == "SELL" else p
        pos.append(p)
    pos = np.array(pos)
    ai, trades = simulate(px, pos)
    gap = np.max(np.abs(ai - served["ai"].values))
    assert gap < 0.005, f"simulator and server differ by ${gap:.4f}"
    hold, _ = simulate(px, np.ones(len(pos), int))
    assert np.max(np.abs(hold - served["hold_msft"].values)) < 0.005
    spy = 1000.0 * px["spy"].values[1:] / px["spy"].values[0]
    days = dates[1:]

    def daily(v):
        v = np.asarray(v)
        return np.concatenate([[v[0] / 1000.0 - 1], v[1:] / v[:-1] - 1])

    r_ai, r_hold, r_spy = daily(ai), daily(hold), daily(spy)
    rng = np.random.default_rng(0)
    shuf_ends = np.array([simulate(px, shuffled(pos, rng))[0][-1] for _ in range(N_SHUFFLE)])
    coin_p = (1 + np.sum(shuf_ends >= ai[-1])) / (1 + N_SHUFFLE)
    rb = np.random.default_rng(1)
    idx = [St.stationary_bootstrap_index(len(days), 21, rb) for _ in range(2000)]
    act = r_ai - r_hold
    ir_boot = np.array([St.sharpe(act[ix]) for ix in idx])
    end_boot = np.array([1000 * np.prod(1 + r_ai[ix]) for ix in idx])
    ir_lo, ir_hi = np.percentile(ir_boot, [2.5, 97.5])
    passes = [ai[-1] > hold[-1], ir_lo > 0, coin_p < 0.05]

    res = pd.DataFrame([
        {"who": "AI (Llama 3.2 3B)", "end_$": ai[-1], "worst_drop": St.max_drop(ai), "trades": trades,
         "days_in_msft": f"{pos.mean():.0%}"},
        {"who": "Hold Microsoft", "end_$": hold[-1], "worst_drop": St.max_drop(hold), "trades": 1, "days_in_msft": "100%"},
        {"who": "Hold SPY (close to close)", "end_$": spy[-1], "worst_drop": St.max_drop(spy), "trades": 1,
         "days_in_msft": "0%"},
        {"who": "Random timing, median of 1,000", "end_$": float(np.median(shuf_ends)), "worst_drop": np.nan,
         "trades": trades, "days_in_msft": f"{pos.mean():.0%}"}])
    res.to_csv(os.path.join(HERE, "results.csv"), index=False, float_format="%.2f")

    curves = pd.DataFrame({"ai": ai, "hold_msft": hold, "hold_spy": spy}, index=days)
    yrs = []
    for y in sorted({d[:4] for d in days}):
        sel = [i for i, d in enumerate(days) if d[:4] == y]
        row = {"year": y}
        for k, v in [("ai", ai), ("hold_msft", hold), ("hold_spy", spy)]:
            start = v[sel[0] - 1] if sel[0] > 0 else 1000.0
            row[k] = f"{(v[sel[-1]] / start - 1) * 100:+.1f}%"
        yrs.append(row)
    pd.DataFrame(yrs).to_csv(os.path.join(HERE, "years.csv"), index=False)

    # how good were the calls: Microsoft's next-month move after each kind of answer
    fwd = px["o"].shift(-22) / px["o"].shift(-1) - 1
    calls = {}
    for kind in ("BUY", "SELL", "HOLD"):
        ds = [d for d in dates[:-1] if ans[d]["decision"] == kind]
        f = fwd.reindex(ds).dropna()
        calls[kind] = (len(ds), f.mean() * 100 if len(f) else float("nan"))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(15, 7))
    x = pd.to_datetime(curves.index)
    ax.fill_between(x, 0, 1, where=pos[:len(x)] == 1, transform=ax.get_xaxis_transform(), color="tab:blue",
                    alpha=0.08, step="post", label="AI holding Microsoft")
    ax.plot(x, curves["ai"], color="tab:blue", lw=2, label=f"AI (${ai[-1]:,.0f})")
    ax.plot(x, curves["hold_msft"], color="black", lw=2, label=f"Hold Microsoft (${hold[-1]:,.0f})")
    ax.plot(x, curves["hold_spy"], color="grey", lw=1.5, ls="--", label=f"Hold SPY (${spy[-1]:,.0f})")
    ax.axhline(1000, color="black", lw=0.5, ls=":")
    ax.set_ylabel("$ (start $1,000)")
    ax.set_title(f"Free open AI trading Microsoft one day at a time, {days[0]} to {days[-1]}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "curves.png"), dpi=110)

    n = {k: sum(1 for d in dates[:-1] if ans[d]["decision"] == k) for k in ("BUY", "SELL", "HOLD")}
    L = [f"# Free open AI trading Microsoft: {days[0]} to {days[-1]} ({len(days)} trading days)", "",
         "AI: Meta Llama 3.2 3B Instruct on this machine (training data ends Dec 2023; memory check in "
         "probe_memory.txt). One day at a time; fills at the next open; 0.05% per trade; cash earns the T-bill.", "",
         "| | $1,000 became | Worst drop | Trades | Days in Microsoft |", "|---|---|---|---|---|"]
    for _, r in res.iterrows():
        wd = "-" if pd.isna(r["worst_drop"]) else f"{r['worst_drop']:.0%}"
        L.append(f"| {r['who']} | ${r['end_$']:,.2f} | {wd} | {r['trades']} | {r['days_in_msft']} |")
    L += ["", f"AI 95% range (block bootstrap): ${np.percentile(end_boot, 2.5):,.0f} - ${np.percentile(end_boot, 97.5):,.0f}",
          f"Information ratio vs holding Microsoft: {St.sharpe(act):+.2f} (95% range {ir_lo:+.2f} to {ir_hi:+.2f})",
          f"Random-timing p-value: {coin_p:.3f} (share of 1,000 shuffles ending at or above the AI: "
          f"{np.mean(shuf_ends >= ai[-1]):.1%})", "",
          f"Answers: BUY {n['BUY']}, SELL {n['SELL']}, HOLD {n['HOLD']}",
          "Microsoft's next-month move after each answer: "
          + ", ".join(f"{k} {v[1]:+.2f}% (n={v[0]})" for k, v in calls.items()), "",
          "Pass mark (PLAN.md): beats holding Microsoft "
          f"{'yes' if passes[0] else 'no'}; information-ratio range above zero {'yes' if passes[1] else 'no'}; "
          f"beats random timing p<0.05 {'yes' if passes[2] else 'no'}.",
          f"**Verdict: {'the AI beat holding Microsoft' if all(passes) else 'no proven edge'}.**", "",
          "Each year (return of each account over the calendar year):", "", "| Year | AI | Hold MSFT | Hold SPY |",
          "|---|---|---|---|"]
    L += [f"| {y['year']} | {y['ai']} | {y['hold_msft']} | {y['hold_spy']} |" for y in yrs]
    with open(os.path.join(HERE, "report.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
