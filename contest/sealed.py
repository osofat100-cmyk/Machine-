"""Shared helpers for the contest. See RULES.md."""
import csv
import fcntl
import http.client
import json
import os
import subprocess
import sys
import time

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEFORE_OCT = os.path.join(ROOT, "data", "PEARL-USDT_min1_before_oct.csv")
RESULTS = os.path.join(ROOT, "contest", "results.csv")
FIELDS = ["program", "strategy", "how", "trades", "end_value", "status", "note"]


def history_before_oct():
    """25 Jun - 30 Sep minutes (time, open, high, low, close, volume). The only history a program may know."""
    df = pd.read_csv(BEFORE_OCT, parse_dates=["time"])
    assert df["time"].iloc[-1] < pd.Timestamp("2026-10-01", tz="UTC")
    return df


class Sealed:
    """One test run: starts price_server.py on `port`, hands out minutes one at a time.

        with Sealed(8801) as s:
            m = s.next()                      # first minute, no order
            while not s.done:
                m = s.next("BUY", qty=10.0)   # or s.next("SELL", qty=...), s.next() for nothing
        s.account                             # final account from the server
    m: {"ts", "time", "open"(=previous close; the sealed file has no opens), "high", "low", "close", "volume",
        "source", "value", "cash", "coins"}
    """

    def __init__(self, port):
        self.port, self.done, self.account, self._prev = port, False, None, None

    def __enter__(self):
        self.server = subprocess.Popen([sys.executable, os.path.join(ROOT, "price_server.py"), "--port",
                                        str(self.port)], cwd=ROOT, stdout=subprocess.DEVNULL)
        for _ in range(200):
            try:
                self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
                self.conn.connect()
                return self
            except OSError:
                time.sleep(0.2)
        raise RuntimeError("price server did not start")

    def __exit__(self, *exc):
        self.server.terminate()
        self.server.wait()

    def next(self, order="NONE", qty=None, share=None):
        q = f"/next?order={order}"
        if qty is not None:
            q += f"&qty={qty}"
        if share is not None:
            q += f"&share={share}"
        self.conn.request("GET", q)
        m = json.loads(self.conn.getresponse().read())
        if m.get("done"):
            self.done, self.account = True, m["account"]
            return None
        m["open"] = self._prev if self._prev is not None else m["close"]
        self._prev = m["close"]
        return m


def export_minutes(port, path):
    """Way B only: walk the server one minute at a time (no orders) and save the minutes for an engine."""
    rows = []
    with Sealed(port) as s:
        while True:
            m = s.next()
            if m is None:
                break
            rows.append({k: m[k] for k in ("ts", "time", "open", "high", "low", "close", "volume", "source")})
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df


def record(program, strategy, how, trades, end_value, status, note=""):
    new = not os.path.exists(RESULTS)
    with open(RESULTS, "a", newline="") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        w = csv.DictWriter(f, FIELDS)
        if new or f.tell() == 0:
            w.writeheader()
        w.writerow({"program": program, "strategy": strategy, "how": how, "trades": trades,
                    "end_value": "" if end_value is None else round(float(end_value), 2),
                    "status": status, "note": note})
        fcntl.flock(f, fcntl.LOCK_UN)
