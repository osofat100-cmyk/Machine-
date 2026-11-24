#!/usr/bin/env python3
"""
Three numbers for every finished crypto golden-rule run (practice $1,000, 18 Nov 05:31 -> 23 Nov 21:00 UTC):

1. Exponential (continuous) growth rate  k = ln(end / 1000) / hours.  Also shown per day and as the
   equivalent compound % per day, exp(24k) - 1.
2. Money without trading costs: end value + the fees the run actually paid (0.05% per buy and per sell).
   The fee money would also have stayed invested, but over this test that changes the result by cents.
3. "Flat ground" gain: what the run would have made if the market had not moved at all.
   Method (the standard one, often called Jensen's alpha / a market-model regression):
   - Take every run's value and the value of $1,000 held in Bitcoin at the same minutes: the hourly :31 marks,
     where every run makes a decision, plus the final minute.
   - Turn both into hourly log returns  r = ln(value_now / value_before).
   - Fit  r_run = alpha + beta * r_bitcoin + noise  by least squares.
     beta  = how strongly the run moves with the market (1 = exactly like Bitcoin, 0 = not at all).
     alpha = the run's average gain per hour that is NOT explained by the market.
   - Because the fit has an intercept, the whole test splits exactly into two parts:
       ln(end / 1000) = alpha * N  +  beta * ln(Bitcoin end / Bitcoin start)
     The first part is the flat-ground gain; the second is the part that came from the market moving.
   - t = alpha / its standard error (Newey-West, so a run of good or bad hours in a row is not over-counted).
     As a rough guide, |t| above 2 means the flat-ground gain is unlikely to be luck.

    python3 crypto/golden_flat_ground.py
"""
import csv
import json
import math
import os

import numpy as np
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
HOURS = 135.5                      # 18 Nov 05:31 -> 23 Nov 21:00 UTC


def series(rows, acc):
    """Value and Bitcoin-hold value at every hourly :31 mark, plus the final minute."""
    marks = [(float(r["value"]), float(r["btc_hold"])) for r in rows if r["time"].endswith(":31")]
    marks.append((acc["ai"]["value"], acc["btc_hold"]["value"]))
    return np.array(marks)


def main():
    out = []
    for v, name in (("v4a", "First"), ("v4b", "Second")):
        for k in (2, 3, 4, 5, 10, 15, 30, 60):
            res = os.path.join(HERE, f"result_1m_every{k}_{v}_ultrafast.json")
            if not os.path.exists(res):
                continue
            acc = json.load(open(res))
            rows = [r for r in csv.DictReader(open(os.path.join(HERE, f"answers_1m_every{k}_{v}_ultrafast.csv")))
                    if r.get("time") and r["time"] != "time" and r["value"]]
            s = series(rows, acc)
            ra, rb = np.diff(np.log(s[:, 0])), np.diff(np.log(s[:, 1]))
            fit = sm.OLS(ra, sm.add_constant(rb)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
            alpha, beta = fit.params
            n = len(ra)
            end = acc["ai"]["value"]
            k_hour = math.log(end / 1000) / HOURS
            out.append({
                "run": f"{name} every {k}", "end": end, "trades": acc["ai"]["trades"], "fees": acc["ai"]["costs"],
                "k_hour_pct": 100 * k_hour, "k_day_pct": 100 * 24 * k_hour, "compound_day_pct": 100 * (math.exp(24 * k_hour) - 1),
                "no_fee_end": end + acc["ai"]["costs"],
                "beta": beta, "alpha_hour_pct": 100 * alpha, "alpha_t": fit.tvalues[0],
                "flat_ground_dollars": 1000 * (math.exp(alpha * n) - 1),
                "market_part_dollars": 1000 * (math.exp(beta * math.log(s[-1, 1] / s[0, 1])) - 1),
                "r2": fit.rsquared})
    btc = json.load(open(os.path.join(HERE, "result_1m_every60_v4a_ultrafast.json")))["btc_hold"]["value"]
    kb = math.log(btc / 1000) / HOURS
    out.sort(key=lambda d: -d["flat_ground_dollars"])
    print(f"Bitcoin hold: end {btc:.2f}  k/hour {100*kb:+.4f}%  k/day {2400*kb:+.3f}%  compound/day {100*(math.exp(24*kb)-1):+.3f}%")
    for d in out:
        print(f"{d['run']:16s} end {d['end']:8.2f}  k/h {d['k_hour_pct']:+.4f}%  k/day {d['k_day_pct']:+.3f}%  "
              f"comp/day {d['compound_day_pct']:+.3f}%  fees {d['fees']:.2f}  no-fee {d['no_fee_end']:8.2f}  "
              f"beta {d['beta']:.2f}  alpha/h {d['alpha_hour_pct']:+.4f}%  t {d['alpha_t']:+.2f}  "
              f"flat {d['flat_ground_dollars']:+7.2f}  market {d['market_part_dollars']:+7.2f}  R2 {d['r2']:.2f}")
    json.dump(out, open(os.path.join(HERE, "golden_flat_ground.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
