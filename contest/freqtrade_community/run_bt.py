"""Run a list of Freqtrade strategies on the sealed test (way B) and write summary rows.

    venv/bin/python run_bt.py jobs.json summary.csv [--parallel 2] [--timeout 900]

jobs.json: [{"label", "repo", "file", "class"}]. Each job gets its own strategy folder holding the strategy file and
its sibling files (for helper imports), minus siblings that define a class with the same name.
Shipped strategy settings are not touched; config.json sets wallet 1000, stake unlimited, 1 open trade, spot.
"""
import argparse
import ast
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
FT = os.path.join(HERE, "venv", "bin", "freqtrade")
FT_OLD = os.path.join(HERE, "venv_np1", "bin", "freqtrade")
OLD_HINT = re.compile(r"numpy|NAN|Impossible to load Strategy|ImportError|AttributeError|ModuleNotFoundError|pandas_ta")
NETWORK = re.compile(r"\b(requests\.|urllib|socket\.|subprocess|os\.system|http\.client|aiohttp|websocket)")
FIELDS = ["label", "repo", "class", "file", "timeframe", "status", "trades", "end_value", "start", "end", "freqtrade", "note"]


def classes_in(path):
    try:
        tree = ast.parse(open(path, errors="ignore").read())
    except SyntaxError:
        return set()
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def run_one(job, timeout, ft):
    label = job["label"]
    work = os.path.join(HERE, "runs", re.sub(r"[^A-Za-z0-9_.-]", "_", label))
    shutil.rmtree(work, ignore_errors=True)
    sdir, rdir = os.path.join(work, "strategy"), os.path.join(work, "results")
    os.makedirs(sdir)
    os.makedirs(rdir)
    src = os.path.abspath(job["file"])
    for f in glob.glob(os.path.join(os.path.dirname(src), "*.py")):
        if os.path.abspath(f) != src and job["class"] in classes_in(f):
            continue
        os.symlink(os.path.abspath(f), os.path.join(sdir, os.path.basename(f)))
    row = {"label": label, "repo": job["repo"], "class": job["class"], "file": job["file"]}
    text = open(src, errors="ignore").read()
    if NETWORK.search(text):
        row.update(status="skipped", note="strategy file makes network/system calls: " + NETWORK.search(text).group(0))
        return row
    cmd = [ft, "backtesting", "-c", os.path.join(HERE, "config.json"), "--userdir", os.path.join(HERE, "user_data"),
           "--strategy", job["class"], "--strategy-path", sdir, "--timerange", "20261001-20261121",
           "--fee", "0.007", "--cache", "none", "--export", "trades"]
    cmd += ["--backtest-directory", rdir] if ft == FT else ["--export-filename", os.path.join(rdir, "result.json")]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=timeout)
        log = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        log = (e.stdout or b"").decode(errors="ignore") if isinstance(e.stdout, bytes) else (e.stdout or "")
        row.update(status="failed", note=f"timeout after {timeout}s")
        open(os.path.join(work, "log.txt"), "w").write(log)
        return row
    open(os.path.join(work, "log.txt"), "w").write(log)
    zips = sorted(glob.glob(os.path.join(rdir, "*.zip")) + glob.glob(os.path.join(rdir, "*.json")))
    zips = [z for z in zips if not z.endswith(".meta.json") and "last_result" not in z]
    if p.returncode != 0 or not zips:
        err = [ln for ln in log.splitlines() if "ERROR" in ln or "Error" in ln or "Exception" in ln]
        row.update(status="failed", note=(err[-1] if err else log.strip().splitlines()[-1] if log.strip() else "no output")[-300:])
        return row
    st = read_stats(zips[-1])["strategy"][job["class"]]
    row.update(status="ran", trades=st["total_trades"], end_value=round(st["final_balance"], 2),
               start=st["backtest_start"], end=st["backtest_end"], timeframe=st.get("timeframe"),
               note=f"{time.time() - t0:.0f}s")
    if not str(st["backtest_start"]).startswith("2026-10-01 00:"):
        row["note"] += "; started late (not enough warm-up candles before 1 Oct)"
    return row


def read_stats(path):
    if path.endswith(".zip"):
        import zipfile
        z = zipfile.ZipFile(path)
        for n in z.namelist():
            if n.endswith(".json") and not n.endswith("_config.json"):
                d = json.loads(z.read(n))
                if "strategy" in d:
                    return d
    return json.load(open(path))


def run(job, timeout):
    row = run_one(job, timeout, FT)
    row["freqtrade"] = "2026.10"
    if row["status"] == "failed" and OLD_HINT.search(row.get("note") or "") and "Short strategies" not in row["note"]:
        first = row["note"]
        row = run_one(job, timeout, FT_OLD)
        row["freqtrade"] = "2024.10 (numpy 1.26)"
        row["note"] = (row.get("note") or "") + f" | on 2026.10: {first[:150]}"
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("summary")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    jobs = json.load(open(a.jobs))
    done = set()
    if os.path.exists(a.summary):
        done = {r["label"] for r in csv.DictReader(open(a.summary))}
    new = not os.path.exists(a.summary)
    with open(a.summary, "a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        with ThreadPoolExecutor(a.parallel) as ex:
            for row in ex.map(lambda j: run(j, a.timeout), [j for j in jobs if j["label"] not in done]):
                w.writerow(row)
                f.flush()
                print(row["status"], row["label"], row.get("trades"), row.get("end_value"), (row.get("note") or "")[:120],
                      flush=True)


if __name__ == "__main__":
    main()
