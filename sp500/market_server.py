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
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "data", "sealed", "market")
COST, SLOT = 0.0005, 0.10
START = "2026-09-23"                                     # two months: 23 Sep .. 23 Nov 2026
NY = ZoneInfo("America/New_York")


def load():
    with open(os.path.join(FOLDER, "universe.csv"), newline="") as f:
        uni = list(csv.DictReader(f))
    syms = ["SPY"] + [u["symbol"] for u in uni]
    series = {}
    for s in syms:
        p = os.path.join(FOLDER, "bars", f"{s}.csv")
        if os.path.exists(p):
            with open(p, newline="") as f:
                series[s] = {r["time"]: r for r in csv.DictReader(f)}
    grid = sorted(series["SPY"])
    pre = [t for t in grid if t < START]
    grid = [t for t in grid if t >= START]
    steps, last = [], {}
    for s, rows in series.items():
        before = [t for t in pre if t in rows]
        if before:
            last[s] = float(rows[before[-1]]["close"])
    for t in grid:
        o, c, v = {}, {}, {}
        for s, rows in series.items():
            r = rows.get(t)
            if r:
                o[s], c[s], v[s] = float(r["open"]), float(r["close"]), float(r["volume"] or 0)
                last[s] = c[s]
            elif s in last:                                  # no trade in this bar: price unchanged
                o[s], c[s], v[s] = last[s], last[s], 0.0
        known = (datetime.strptime(t, "%Y-%m-%d %H:%M") + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        steps.append({"time": t, "known_at": known, "open": o, "close": c, "volume": v})
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
    return uni, steps, news


class Exchange:
    def __init__(self):
        self.uni, self.steps, self.news = load()
        self.k, self.n_news, self.acc = -1, 0, {}
        while self.n_news < len(self.news) and self.news[self.n_news]["time"] < self.steps[0]["time"][:10]:
            self.n_news += 1                                 # news from before the test is not replayed

    def next(self, orders):
        if self.k + 1 >= len(self.steps):
            return {"done": True, "accounts": self.acc}
        self.k += 1
        st = self.steps[self.k]
        refused = {}
        for name, lst in (orders or {}).items():
            a = self.acc.setdefault(name, {"cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
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
