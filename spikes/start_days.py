#!/usr/bin/env python3
"""
Every training start day, 25 Jun ... 20 Nov (149 variations). Variation d = the raw data from day d to 20 Nov,
fed into the main program unchanged:
  - all 29,700 buy/sell pairs (buy after 1..99% fall, sell after 1..300% rise) on that data
  - averaged with story size 85 -> the buy/sell number, and its money on that data
  - also the single best pair before averaging
Data: spikes/data/train.csv (25 Jun - 21 Oct) + the last month taken from price_server.py one minute at a time.

    python3 spikes/start_days.py   -> spikes/start_days.csv, spikes/start_days_graph.png
"""
import os
import time

import numpy as np
import pandas as pd

from all_stories import walk_minutes
from dip_top import COST, XS, YS, grid
from stories import pick

HERE = os.path.dirname(os.path.abspath(__file__))
STORY = 85


def main():
    train = pd.read_csv(os.path.join(HERE, "data/train.csv"))
    t_test, c_test, _ = walk_minutes(8799)
    days = np.array([t[:10] for t in train["time"].str.replace("T", " ").tolist() + t_test])
    close = np.concatenate([train["close"].to_numpy(np.float64), c_test])
    first = sorted(set(days))
    print(f"{len(first)} variations: {first[0]} -> 20 Nov, ..., {first[-1]} -> 20 Nov", flush=True)

    rows, t0 = [], time.time()
    for n, d in enumerate(first):
        c = close[np.searchsorted(days, d):]
        v, trades = grid(c, XS, YS)
        i, j, _ = pick(v, STORY)
        bi, bj = np.unravel_index(np.argmax(v), v.shape)
        rows.append({"start_day": d, "minutes": len(c),
                     "averaged_buy_%": int(round(XS[i] * 100)), "averaged_sell_%": int(round(YS[j] * 100)),
                     "averaged_$": round(v[i, j], 2), "averaged_trades": int(trades[i, j]),
                     "best_pair": f"{XS[bi]:.0%}/{YS[bj]:.0%}", "best_pair_$": round(v[bi, bj], 2),
                     "holding_$": round(c[-1] / c[0] * 1000 * (1 - COST) / (1 + COST), 2)})
        if n % 10 == 0 or n == len(first) - 1:
            r = rows[-1]
            print(f"  {d}: averaged {r['averaged_buy_%']}%/{r['averaged_sell_%']}% ${r['averaged_$']:,.2f} "
                  f"({r['averaged_trades']} trades) | best pair {r['best_pair']} ${r['best_pair_$']:,.2f} | "
                  f"holding ${r['holding_$']:,.2f}  ({time.time() - t0:.0f}s)", flush=True)
    r = pd.DataFrame(rows)
    a = r[r.start_day == "2026-06-25"].iloc[0]
    assert a["best_pair_$"] > 0 and len(r) == len(first)
    r.to_csv(os.path.join(HERE, "start_days.csv"), index=False)
    print("\nbest 10 variations by averaged $:")
    print(r.sort_values("averaged_$", ascending=False).head(10).to_string(index=False))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = pd.to_datetime(r["start_day"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(17, 10), sharex=True)
    a1.plot(x, r["averaged_$"], lw=2, label="averaged buy/sell number (story size 85)")
    a1.plot(x, r["best_pair_$"], lw=1, alpha=0.7, label="single best pair (no averaging)")
    a1.plot(x, r["holding_$"], color="grey", ls=":", lw=2, label="just holding PEARL")
    a1.axhline(1000, color="black", ls="--", lw=0.8)
    a1.set_yscale("log")
    a1.set_ylabel("\\$ on 20 Nov (start \\$1,000 on the start day)")
    a1.set_title(f"{len(r)} variations: raw data from each start day to 20 Nov")
    a1.legend()
    a1.grid(alpha=0.3, which="both")
    a2.plot(x, r["averaged_buy_%"], label="averaged: buy after this % fall")
    a2.plot(x, r["averaged_sell_%"] / 3, label="averaged: sell after this % rise (divided by 3)")
    a2.set_xlabel("training start day")
    a2.legend()
    a2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "start_days_graph.png"), dpi=110)
    print("saved spikes/start_days_graph.png")


if __name__ == "__main__":
    main()
