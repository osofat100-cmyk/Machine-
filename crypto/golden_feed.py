#!/usr/bin/env python3
"""
Builds the two data files behind the live "Golden Rule Race" page from the saved answer files:
crypto.csv and stocks.csv, one row per decision of every golden-rule run (fast Ultra, thinking off):
    run, version, every, status, time, money, bench
time is the market minute (crypto in UTC, stocks in New York time), money the run's account, bench what $1,000
held in Bitcoin / SPY over the same minutes was worth. status is running, finished or stopped.

    python3 crypto/golden_feed.py OUT_DIR
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSIONS = (("v4a", "First"), ("v4b", "Second"))
STOPPED = {("crypto", "v4a", 1), ("crypto", "v4a", 5), ("crypto", "v4b", 1)}   # weeded out on request


def running():
    """(market, version, every) of the runs whose program is alive right now."""
    out = set()
    for pid in subprocess.run(["pgrep", "-f", r"^python3 (crypto|golden)_trader\.py"], capture_output=True,
                              text=True).stdout.split():
        try:
            env = dict(x.split("=", 1) for x in open(f"/proc/{pid}/environ").read().split("\0") if "=" in x)
            cmd = open(f"/proc/{pid}/cmdline").read()
        except OSError:
            continue
        out.add(("crypto" if "crypto_trader" in cmd else "stocks", env.get("VERSION"), int(env.get("DECIDE_EVERY", 1))))
    return out


def build(market, folder, bench, speeds, total_steps, out_path):
    live = running()
    n = 0
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["run", "version", "every", "status", "time", "money", "bench"])
        for v, name in VERSIONS:
            for k in speeds:
                path = os.path.join(folder, f"answers_1m{'' if k == 1 else f'_every{k}'}_{v}_ultrafast.csv")
                if not os.path.exists(path):
                    continue
                rows = [r for r in csv.DictReader(open(path)) if r.get("time") not in (None, "time")]
                result = os.path.join(folder, f"result_1m{'' if k == 1 else f'_every{k}'}_{v}_ultrafast.json")
                done = os.path.exists(result)
                status = ("finished" if done else "running" if (market, v, k) in live
                          else "stopped" if (market, v, k) in STOPPED else "paused")
                label = f"{name} version, every {k} min"
                for r in rows:
                    w.writerow([label, name, k, status, r["time"], r["value"], r[bench]])
                    n += 1
                if done:                                   # final value at the test's last minute
                    acc = json.load(open(result))
                    last = "2026-11-23 20:59" if market == "crypto" else "2026-11-23 15:59"
                    w.writerow([label, name, k, status, last, f"{acc['ai']['value']:.2f}",
                                f"{acc[bench]['value']:.2f}"])
                    n += 1
    print(out_path, n, "rows")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    build("crypto", os.path.join(ROOT, "crypto"), "btc_hold", (1, 2, 3, 4, 5, 10, 15, 30, 60), 8190,
          os.path.join(out, "crypto.csv"))
    build("stocks", os.path.join(ROOT, "sp500", "golden"), "spy_hold", (1, 2, 3, 4, 5, 10, 15, 30), 8190,
          os.path.join(out, "stocks.csv"))


if __name__ == "__main__":
    main()
