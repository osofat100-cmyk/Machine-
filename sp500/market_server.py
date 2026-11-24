#!/usr/bin/env python3
"""
S&P 500 test server: the ONLY program that opens data/sealed/market/. Each POST /next hands out ONE new 5-minute
step (all ~500 stocks and SPY), oldest first. A bar labelled 10:05 covers 10:05-10:10 and is handed out as known at
10:10. Headlines are handed out only at the exact minute they were published (step end >= publication time);
headlines without a real time were dropped when downloading.

Accounts (created at $1,000 cash the first time a name appears): orders sent with a request fill at the OPEN of the
step that request returns. Order = {"action": "BUY"|"SELL", "symbol": "XYZ"}. BUY spends one slot = 10% of the
account's value at that moment (or what cash is left, if less); SELL sells the whole holding. 0.05% of every amount
bought or sold. A BUY of something already held, a SELL of something not held, or an unknown symbol is refused and
reported back. No cash interest (two months; about 0.6%).

    POST /next {"orders": {"ai": [{"action": "BUY", "symbol": "NVDA"}]}}
      -> {"step": {"time", "known_at", "close": {sym: price}, ...}, "news": [...], "accounts": {...}, "refused": {...}}
"""
import argparse
import csv
import json
import os
from array import array
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "data", "sealed", "market")
COST, SLOT = 0.0005, 0.10
STEP = int(os.environ.get("STEP_MIN", "5"))                     # minutes per step: 5 (bars/) or 2 (bars_2m/)
BARS = "bars" if STEP == 5 else f"bars_{STEP}m"
START = os.environ.get("START", "2026-09-23")            # two months: 23 Sep .. 23 Nov 2026 (or set START)
NY = ZoneInfo("America/New_York")


def load():
    """Prices are kept as one compact array per stock (open, close, volume for every step) instead of a dict per
    step: the same numbers handed out, about a tenth of the memory, so many runs fit side by side."""
    with open(os.path.join(FOLDER, "universe.csv"), newline="") as f:
        uni = list(csv.DictReader(f))
    syms = ["SPY"] + [u["symbol"] for u in uni]
    with open(os.path.join(FOLDER, BARS, "SPY.csv"), newline="") as f:
        full = sorted(r["time"] for r in csv.DictReader(f))
    start = max(START, full[0][:10] if STEP == 1 else START)   # 1-minute bars only exist for the last 30 days
    grid = [t for t in full if t >= start]
    on_grid, before = {t: j for j, t in enumerate(grid)}, set(t for t in full if t < start)
    have, cols = [], {}
    nan = float("nan")
    for s in syms:
        p = os.path.join(FOLDER, BARS, f"{s}.csv")
        if not os.path.exists(p):
            continue
        o, c, v = array("d", [nan]) * len(grid), array("d", [nan]) * len(grid), array("d", [0.0]) * len(grid)
        last_t, last = None, None
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                t = r["time"]
                j = on_grid.get(t)
                if j is not None:
                    o[j], c[j], v[j] = float(r["open"]), float(r["close"]), float(r["volume"] or 0)
                elif t in before and (last_t is None or t > last_t):
                    last_t, last = t, float(r["close"])
        for j in range(len(grid)):
            if c[j] == c[j]:
                last = c[j]
            elif last is not None:                           # no trade in this bar: price unchanged
                o[j], c[j], v[j] = last, last, 0.0
        have.append(s)
        cols[s] = (o, c, v)
    steps = [{"time": t, "known_at": (datetime.strptime(t, "%Y-%m-%d %H:%M") + timedelta(minutes=STEP))
              .strftime("%Y-%m-%d %H:%M")} for t in grid]
    news, seen = [], set()
    for name in sorted(os.listdir(os.path.join(FOLDER, "news"))):
        with open(os.path.join(FOLDER, "news", name)) as f:
            for line in f:
                for it in json.loads(line)["items"]:
                    if it["title"] in seen:
                        continue
                    seen.add(it["title"])
                    t = datetime.strptime(it["published"], "%Y-%m-%d %H:%M:%S%z").astimezone(NY)
                    news.append({"time": t.strftime("%Y-%m-%d %H:%M"), "title": it["title"], "query": name})
    news.sort(key=lambda x: x["time"])
    return uni, steps, news, have, cols


class Exchange:
    def __init__(self):
        self.uni, self.steps, self.news, self.have, self.cols = load()
        self.k, self.n_news, self.acc = -1, 0, {}
        while self.n_news < len(self.news) and self.news[self.n_news]["time"] < self.steps[0]["time"][:10]:
            self.n_news += 1                                 # news from before the test is not replayed

    def next(self, orders):
        if self.k + 1 >= len(self.steps):
            return {"done": True, "accounts": self.acc}
        self.k += 1
        st = dict(self.steps[self.k])
        for key, n in (("open", 0), ("close", 1), ("volume", 2)):
            st[key] = {s: self.cols[s][n][self.k] for s in self.have if self.cols[s][1][self.k] == self.cols[s][1][self.k]}
        refused = {}
        for name, lst in (orders or {}).items():
            a = self.acc.setdefault(name, {"cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
            if any(od.get("split") for od in lst or []):    # version 3: sells first, then split the cash evenly
                lst = sorted(lst, key=lambda od: od.get("action") != "SELL")
            for od in lst or []:
                s, act = od.get("symbol"), od.get("action")
                px = st["open"].get(s)
                if px is None:
                    refused.setdefault(name, []).append({**od, "why": "unknown symbol or no price"})
                    continue
                if act == "SELL":
                    if s not in a["shares"]:
                        refused.setdefault(name, []).append({**od, "why": "not owned"})
                        continue
                    got = a["shares"].pop(s) * px
                    a["cash"] += got * (1 - COST)
                    a["costs"] += got * COST
                    a["trades"] += 1
                elif act == "BUY":
                    if s in a["shares"]:
                        refused.setdefault(name, []).append({**od, "why": "already owned"})
                        continue
                    value = a["cash"] + sum(q * st["open"][x] for x, q in a["shares"].items())
                    if od.get("split"):                       # equal share of the cash over the empty slots
                        spend = a["cash"] / max(1, 10 - len(a["shares"])) / (1 + COST)
                    else:
                        spend = (a["cash"] if od.get("all") else min(SLOT * value, a["cash"])) / (1 + COST)
                    if spend < 1.0:
                        refused.setdefault(name, []).append({**od, "why": "no cash left"})
                        continue
                    a["shares"][s] = spend / px
                    a["cash"] -= spend * (1 + COST)
                    a["costs"] += spend * COST
                    a["trades"] += 1
        for a in self.acc.values():
            a["value"] = a["cash"] + sum(q * st["close"][x] for x, q in a["shares"].items())
        new = []
        while self.n_news < len(self.news) and self.news[self.n_news]["time"] <= st["known_at"]:
            new.append(self.news[self.n_news])
            self.n_news += 1
        return {"step": st, "news": new, "accounts": self.acc, "refused": refused,
                "last_step": self.k + 1 == len(self.steps), "universe": self.uni if self.k == 0 else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    a = ap.parse_args()
    ex = Exchange()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            data = json.dumps(ex.next(json.loads(body or b"{}").get("orders"))).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", a.port), Handler)
    print(f"ready {len(ex.steps)} steps, {len(ex.news)} headlines on port {a.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
