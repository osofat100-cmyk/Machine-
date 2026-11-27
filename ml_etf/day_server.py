#!/usr/bin/env python3
"""
The sealed test server (PLAN.md sections 7 and 9). It is the ONLY program that opens data/sealed/etf_test.csv.

Each POST /next hands out ONE new trading day of all 13 symbols, oldest first, and acts as the exchange:
  - every account (created the first time its name appears, with $1,000 cash) keeps cash and shares here;
  - targets sent with a request fill at the OPEN of the day that request returns: the caller decided after the
    previous day's close;
  - cash grows each day by (1 + previous day's rate / 100)^(1/252); costs are 0.05% of every amount bought or sold.
The answer also gives the date of the next trading day (the exchange calendar is public in advance; no prices).
The account rules are written here separately from account.py, so that the test can check both give the same money.

    python3 ml_etf/day_server.py --port 8811
    POST /next  {"orders": {"name": [13 weights] or null, ...}}
      -> {"day": {"date", "rate", "open": [...], "close": [...], "volume": [...]}, "next_date", "values": {name: $}}
      -> {"done": true, "accounts": {name: {"value", "cash", "shares", "trades", "costs"}}} after the last day
"""
import argparse
import csv
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
SEALED = os.path.join(os.path.dirname(HERE), "data", "sealed", "etf_test.csv")
SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
COST = 0.0005


class Exchange:
    def __init__(self, path):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        self.days = [{"date": r["date"], "rate": float(r["rate"]),
                      "open": [float(r[f"{s}_open"]) for s in SYMBOLS],
                      "close": [float(r[f"{s}_close"]) for s in SYMBOLS],
                      "volume": [float(r[f"{s}_volume"]) for s in SYMBOLS]} for r in rows]
        self.k = -1
        self.accounts = {}

    def trade(self, a, w, o):
        value = a["cash"] + sum(q * p for q, p in zip(a["shares"], o))
        for i in range(len(o)):                                   # sell above target first
            target = w[i] * value
            have = a["shares"][i] * o[i]
            if have > target + 1e-9:
                q = a["shares"][i] - target / o[i]
                a["cash"] += q * o[i] * (1.0 - COST)
                a["costs"] += q * o[i] * COST
                a["shares"][i] -= q
                a["trades"] += 1
        wanted = [w[i] * value - a["shares"][i] * o[i] for i in range(len(o))]
        total = sum(x * (1.0 + COST) for x in wanted if x > 1e-9)
        if total > 0:
            scale = min(1.0, a["cash"] / total)
            for i in range(len(o)):                               # then buy below target, never beyond cash
                if wanted[i] > 1e-9:
                    spend = wanted[i] * scale
                    a["shares"][i] += spend / o[i]
                    a["cash"] -= spend * (1.0 + COST)
                    a["costs"] += spend * COST
                    a["trades"] += 1

    def next(self, orders):
        if self.k + 1 >= len(self.days):
            return {"done": True, "accounts": {n: {k: a[k] for k in ("value", "cash", "shares", "trades", "costs")}
                                               for n, a in self.accounts.items()}}
        self.k += 1
        d = self.days[self.k]
        growth = (1.0 + self.days[self.k - 1]["rate"] / 100.0) ** (1.0 / 252.0) if self.k > 0 else 1.0
        for a in self.accounts.values():
            a["cash"] *= growth
        for name, w in (orders or {}).items():
            if name not in self.accounts:
                self.accounts[name] = {"cash": 1000.0, "shares": [0.0] * len(SYMBOLS), "trades": 0, "costs": 0.0,
                                       "value": 1000.0}
            if w is not None:
                assert len(w) == len(SYMBOLS) and min(w) >= 0 and sum(w) <= 1 + 1e-9, "bad target"
                self.trade(self.accounts[name], w, d["open"])
        for a in self.accounts.values():
            a["value"] = a["cash"] + sum(q * p for q, p in zip(a["shares"], d["close"]))
        nxt = self.days[self.k + 1]["date"] if self.k + 1 < len(self.days) else None
        return {"day": d, "next_date": nxt, "values": {n: a["value"] for n, a in self.accounts.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--file", default=SEALED)
    a = ap.parse_args()
    ex = Exchange(a.file)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        disable_nagle_algorithm = True

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path != "/next":
                out, code = {"error": "only POST /next"}, 404
            else:
                out, code = ex.next(json.loads(body or b"{}").get("orders")), 200
            data = json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", a.port), Handler)
    print(f"ready {len(ex.days)} days on port {a.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
