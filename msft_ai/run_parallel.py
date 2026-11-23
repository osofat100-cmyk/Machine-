#!/usr/bin/env python3
"""
Run the AI over 2 Jan 2024 .. 20 Nov 2026 in sections side by side, then join the real path.

Each section is run from cash and from Microsoft (the first section only from cash, where the account starts).
All cash-start runs go first; the Microsoft-start runs follow and reuse every answer already saved for the same
(day, position), so once the two runs of a section reach the same position they cost nothing more.

    python3 msft_ai/run_parallel.py --workers 4 --sections 8
"""
import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from ai_trader import FIRST_DECISION, LAST_DAY, Server

HERE = os.path.dirname(os.path.abspath(__file__))


def decision_days():
    days = []
    with Server() as s:
        while True:
            out = s.next({})
            if out.get("done"):
                break
            d = out["day"]["date"]
            if d >= LAST_DAY:
                break
            if d >= FIRST_DECISION:
                days.append(d)
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--sections", type=int, default=8)
    a = ap.parse_args()
    threads = max(1, 4 // a.workers)
    days = decision_days()
    k = a.sections
    bounds = [(days[i * len(days) // k], days[(i + 1) * len(days) // k - 1]) for i in range(k)]
    jobs = [(s, e, 0) for s, e in bounds] + [(s, e, 1) for s, e in bounds[1:]]
    print(f"{len(days)} decision days in {k} sections, {len(jobs)} runs, {a.workers} at a time x {threads} threads",
          flush=True)
    from ai_trader import CACHE, FIELDS, append_line, csv_line
    if not os.path.exists(CACHE):
        append_line(CACHE, csv_line(FIELDS))
    t0 = time.time()

    def run(j):
        s, e, p = j
        cmd = [sys.executable, os.path.join(HERE, "ai_trader.py"), "--job", s, e, str(p), "--threads", str(threads)]
        return subprocess.run(cmd, cwd=HERE).returncode

    with ThreadPoolExecutor(a.workers) as ex:
        codes = list(ex.map(run, jobs))
    if any(codes):
        raise SystemExit(f"some sections failed: {codes}")
    print(f"all sections done in {time.time() - t0:.0f}s", flush=True)
    subprocess.run([sys.executable, os.path.join(HERE, "ai_trader.py"), "--replay"], cwd=HERE, check=True)


if __name__ == "__main__":
    main()
