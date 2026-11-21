"""Freqtrade's own look-ahead check for every strategy that ended above a bar (default $1,095.50).

    venv/bin/python run_lookahead.py summary_a.csv [summary_b.csv ...] --out lookahead.csv [--bar 1095.5]
"""
import argparse
import csv
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = {"2026.10": os.path.join(HERE, "venv", "bin", "freqtrade"),
       "2024.10 (numpy 1.26)": os.path.join(HERE, "venv_np1", "bin", "freqtrade")}


def check(row):
    sdir = os.path.join(HERE, "runs", re.sub(r"[^A-Za-z0-9_.-]", "_", row["label"]), "strategy")
    out = os.path.join(HERE, "runs", re.sub(r"[^A-Za-z0-9_.-]", "_", row["label"]), "lookahead.csv")
    cmd = [BIN[row["freqtrade"]], "lookahead-analysis", "-c", os.path.join(HERE, "config.json"),
           "--userdir", os.path.join(HERE, "user_data"), "--strategy", row["class"], "--strategy-path", sdir,
           "--timerange", "20261001-20261121", "--fee", "0.007", "--lookahead-analysis-exportfilename", out]
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=3600)
        log = p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return {**row, "lookahead": "check timed out"}
    verdict = "unknown"
    if os.path.exists(out):
        for r in csv.DictReader(open(out)):
            if r.get("strategy") == row["class"]:
                bias = r.get("has_bias", "")
                biased = r.get("biased_entry_signals", ""), r.get("biased_exit_signals", ""), r.get("biased_indicators", "")
                verdict = (f"BIASED (entry {biased[0]}, exit {biased[1]}, indicators {biased[2]})"
                           if str(bias).lower() == "true" else "no bias found") if bias != "" else "unknown"
                if r.get("total_signals"):
                    verdict += f", {r.get('total_signals')} signals checked"
    else:
        err = [ln for ln in log.splitlines() if "ERROR" in ln or "too few" in ln.lower() or "not enough" in ln.lower()]
        verdict = "check failed: " + (err[-1][-200:] if err else log.strip().splitlines()[-1][-200:])
    return {**row, "lookahead": verdict}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summaries", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bar", type=float, default=1095.5)
    a = ap.parse_args()
    rows = [r for s in a.summaries for r in csv.DictReader(open(s))
            if r["status"] == "ran" and r["end_value"] and float(r["end_value"]) > a.bar]
    with ThreadPoolExecutor(2) as ex:
        res = list(ex.map(check, rows))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, ["label", "class", "freqtrade", "end_value", "trades", "lookahead"], extrasaction="ignore")
        w.writeheader()
        for r in res:
            w.writerow(r)
            print(r["end_value"], r["label"], "->", r["lookahead"], flush=True)


if __name__ == "__main__":
    main()
