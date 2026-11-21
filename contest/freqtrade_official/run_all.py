"""Backtest every strategy Freqtrade can list, shipped settings, 2 at a time. Logs in logs/, parsed results in results.json."""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

FT = sys.argv[1] if len(sys.argv) > 1 else "venv/bin/freqtrade"
names = [l.strip() for l in open("strategy_list.txt") if l.strip()]
if len(sys.argv) > 2:
    names = sys.argv[2].split(",")


import glob
BASE = "downloads/fts/user_data/strategies"


def folder(name):
    for f in glob.glob(BASE + "/**/*.py", recursive=True):
        if re.search(r"^class\s+" + re.escape(name) + r"\s*\(", open(f).read(), re.M):
            return os.path.dirname(f)
    return BASE


def run(name):
    cmd = [FT, "backtesting", "-c", "config.json", "--strategy", name, "--strategy-path", folder(name),
           "--timerange", "20261001-20261121", "--fee", "0.007", "--export", "none", "--cache", "none"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=5400)
    out = p.stdout + p.stderr
    open(f"logs/{name}.log", "w").write(out)
    row = re.search(r"│\s*" + re.escape(name) + r"\s*│\s*(\d+)\s*│\s*(-?[\d.]+)\s*│\s*(-?[\d.]+)\s*│\s*(-?[\d.]+)\s*│", out)
    if row:
        trades, avg, profit, pct = row.groups()
        return name, {"trades": int(trades), "profit": float(profit), "end": 1000 + float(profit), "error": None}
    err = [l for l in out.splitlines() if "ERROR" in l or "Error" in l or "Exception" in l]
    return name, {"trades": None, "profit": None, "end": None, "error": (err[-1] if err else out[-300:])[-400:]}


os.makedirs("logs", exist_ok=True)
try:
    res = json.load(open("results.json"))
except FileNotFoundError:
    res = {}
with ThreadPoolExecutor(2) as pool:
    for name, r in pool.map(run, names):
        res[name] = r
        json.dump(res, open("results.json", "w"), indent=1)
        print(name, r["trades"], r["end"], (r["error"] or "")[:150], flush=True)
