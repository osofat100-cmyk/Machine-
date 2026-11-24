#!/usr/bin/env python3
"""
Why did identical copies end so differently? Looks at 18-19 Nov (when almost all trading happened) for the 11
identical runs (first golden rule, every 60 min), replayed through the test server.

For every trade actually carried out on 18-19 Nov: the AI's own reason at that decision, and how the coin did
afterwards (bought coins: from the fill to the end of the test; sold coins: what holding on would have given).
Also the 10 coins each run was holding at the end of 19 Nov (it was then locked in by the golden rule while the market
fell) and how those coins did to the end.

    python3 crypto/copies_why.py   -> crypto/copies_why.json (+ printed summary)
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flat_ground_replay as F  # noqa: E402
from copies_timing import SPECS  # noqa: E402

BEST = ["copy 6", "original", "copy 5"]
WORST = ["copy 1", "copy 8", "copy 10", "copy 9"]


def main():
    steps, groups, runs, values = F.replay(SPECS)
    tag_of = {n: tag for n, _, _, tag in SPECS}
    end_close = steps[-1]["close"]
    cut = next(i for i, st in enumerate(steps) if st["time"] >= "2026-11-20 00:00")
    report = {}
    for n, _, _, tag in SPECS:
        rows = {r["time"]: r for r in csv.DictReader(open(os.path.join(HERE, f"answers_1m_every60_v4a_{tag}.csv")))
                if r.get("time") and r["time"] != "time"}
        trades = []
        for kidx, sold, bought in runs[n]["trades"]:
            if kidx >= cut:
                break
            dec = steps[kidx - 1]["time"]                       # the decision that sent these orders
            o = steps[kidx]["open"]
            r = rows.get(dec, {})
            trades.append({
                "decided": dec,
                "sold": [{"coin": s, "price": o[s], "after_to_end_pct": 100 * (end_close[s] / o[s] - 1)} for s in sold],
                "bought": [{"coin": b, "price": o[b], "to_end_pct": 100 * (end_close[b] / o[b] - 1),
                            "to_20nov_pct": 100 * (steps[cut]["close"][b] / o[b] - 1)} for b in bought],
                "reason": (r.get("raw") or "")[:600]})
        locked = []                                               # holdings at the end of 19 Nov
        cur, t = set(), 0
        for kidx, sold, bought in runs[n]["trades"]:
            if kidx >= cut:
                break
            cur = (cur - set(sold)) | set(bought)
        c0 = steps[cut]["close"]
        for s in sorted(cur):
            locked.append({"coin": s, "to_end_pct": 100 * (end_close[s] / c0[s] - 1)})
        report[n] = {"end": values[n][-1], "value_end_19nov": values[n][cut], "trades": trades, "locked": locked,
                     "locked_avg_pct": sum(x["to_end_pct"] for x in locked) / max(1, len(locked))}
    json.dump(report, open(os.path.join(HERE, "copies_why.json"), "w"), indent=1)
    for grp, names in (("BEST", BEST), ("WORST", WORST)):
        print(f"===== {grp} =====")
        for n in names:
            d = report[n]
            print(f"--- {n}: end ${d['end']:.2f}; at end of 19 Nov ${d['value_end_19nov']:.2f}; "
                  f"coins held then went {d['locked_avg_pct']:+.1f}% on average to the end")
            print("    held at end of 19 Nov:", ", ".join(f"{x['coin'].replace('-USD','')} {x['to_end_pct']:+.0f}%"
                                                          for x in sorted(d['locked'], key=lambda x: -x['to_end_pct'])))
            for tr in d["trades"]:
                s = ", ".join(f"{x['coin'].replace('-USD','')} (then {x['after_to_end_pct']:+.0f}%)" for x in tr["sold"])
                b = ", ".join(f"{x['coin'].replace('-USD','')} ({x['to_end_pct']:+.0f}%)" for x in tr["bought"])
                print(f"    {tr['decided']}: SOLD {s or '-'} | BOUGHT {b or '-'}")
                print(f"        why: {tr['reason'][:330]}")


if __name__ == "__main__":
    main()
