#!/usr/bin/env python3
"""
HOURLY crypto + stocks test server (same account rules as mixed/mixed_server.py, one step = one hour): the only
program that opens data/sealed/hourly/. Each POST /next hands out ONE new UTC hour, oldest first, from 18 Aug 2026
(a week of history before the 25 Aug start) to 23 Nov 2026 21:00 UTC.

Crypto: hourly bars around the clock; a bar labelled 10:00 covers 10:00-11:00 and is handed out as known at 11:00.
Stocks: hourly bars of the regular session (09:30-16:00 New York). A stock bar is shown only once it has ENDED by the
step's known time. Stock orders fill at the open of the first stock bar that STARTS within the next hour, i.e. after
the decision was made; if none starts then (market closed), stock orders are refused ("stock market closed").
News: crypto and stock headlines, each handed out only once its real publication time has passed.

Account: orders sent with a request fill in the hour that request returns (coins at that hour's open). BUY with
"split" spends the cash evenly over the empty slots (10 slots, coins and stocks together); SELL sells the whole
holding; 0.05% of every amount bought or sold.
"""
import argparse
import csv
import json
import os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(ROOT, "data", "sealed", "hourly")
START = os.environ.get("START", "2026-08-18 00:00")
END = os.environ.get("END", "2026-11-23 21:00")
COST, SLOTS = 0.0005, 10
UTC, NY = ZoneInfo("UTC"), ZoneInfo("America/New_York")
FMT = "%Y-%m-%d %H:%M"


def plus(t, minutes):
    return (datetime.strptime(t, FMT) + timedelta(minutes=minutes)).strftime(FMT)


def ny_utc(t):
    return datetime.strptime(t, FMT).replace(tzinfo=NY).astimezone(UTC).strftime(FMT)


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load():
    cu = read(os.path.join(FOLDER, "universe_crypto.csv"))
    su = read(os.path.join(FOLDER, "universe_stocks.csv"))
    crypto = {}
    for u in cu:
        p = os.path.join(FOLDER, "crypto_1h", f"{u['symbol']}.csv")
        if os.path.exists(p):
            crypto[u["symbol"]] = {r["time"]: (float(r["open"]), float(r["close"])) for r in read(p)}
    grid = [t for t in sorted(crypto["BTC-USD"]) if START <= t < END]
    stocks, bars = {}, {}                      # bars: UTC start -> (UTC end, New York date)
    for sym in ["SPY"] + [u["symbol"] for u in su]:
        p = os.path.join(FOLDER, "stocks_1h", f"{sym}.csv")
        if not os.path.exists(p):
            continue
        rows = {}
        for r in read(p):
            s = ny_utc(r["time"])
            rows[s] = (float(r["open"]), float(r["close"]))
            if sym == "SPY":
                close_ny = r["time"][:10] + " 16:00"
                end_ny = min(plus(r["time"], 60), close_ny)
                bars[s] = (ny_utc(end_ny), r["time"][:10])
        stocks[sym] = rows
    news = []
    for name in sorted(os.listdir(os.path.join(FOLDER, "news"))):
        with open(os.path.join(FOLDER, "news", name)) as f:
            for line in f:
                for it in json.loads(line)["items"]:
                    t = datetime.strptime(it["published"], "%Y-%m-%d %H:%M:%S%z").astimezone(UTC).strftime(FMT)
                    news.append({"time": t, "title": it["title"], "query": name.removesuffix(".jsonl")})
    seen, uniq = set(), []
    for n in sorted(news, key=lambda x: x["time"]):
        if n["title"] not in seen and n["time"] >= START:
            seen.add(n["title"])
            uniq.append(n)
    universe = ([{"symbol": u["symbol"], "kind": "crypto", "group": u.get("size", "")} for u in cu if u["symbol"] in crypto]
                + [{"symbol": u["symbol"], "kind": "stock", "group": u.get("sector", "")} for u in su if u["symbol"] in stocks]
                + [{"symbol": "SPY", "kind": "stock", "group": "index fund"}])
    return universe, crypto, grid, stocks, bars, uniq


class Exchange:
    def __init__(self):
        self.universe, self.crypto, self.grid, self.stocks, self.bars, self.news = load()
        self.starts = sorted(self.bars)
        self.k, self.j, self.n_news, self.acc = -1, 0, 0, {}
        self.c_last, self.s_close, self.prev_close, self.day = {}, {}, {}, None
        for s, rows in self.crypto.items():                    # last known coin prices before the first step
            before = [t for t in rows if t < self.grid[0]]
            if before:
                self.c_last[s] = rows[max(before)][1]
        self._show_stocks(self.grid[0])

    def _show_stocks(self, known):
        """Apply every stock bar that has ENDED by `known` (UTC)."""
        while self.j < len(self.starts) and self.bars[self.starts[self.j]][0] <= known:
            s0 = self.starts[self.j]
            d = self.bars[s0][1]
            if d != self.day:
                if self.s_close:
                    self.prev_close = dict(self.s_close)
                self.day = d
            for sym, rows in self.stocks.items():
                if s0 in rows:
                    self.s_close[sym] = rows[s0][1]
            self.j += 1

    def _bar_starting(self, t0, t1):
        for s0 in self.starts:
            if t0 <= s0 < t1:
                return s0
            if s0 >= t1:
                return None
        return None

    def next(self, orders):
        if self.k + 1 >= len(self.grid):
            return {"done": True, "accounts": self.acc}
        self.k += 1
        t = self.grid[self.k]
        known = plus(t, 60)
        opn, close = {}, {}
        for s, rows in self.crypto.items():
            r = rows.get(t)
            if r:
                opn[s], close[s] = r
                self.c_last[s] = r[1]
            elif s in self.c_last:
                opn[s] = close[s] = self.c_last[s]
        fill_bar = self._bar_starting(t, known)                 # a stock bar starting after the decision, this hour
        s_open = {sym: rows[fill_bar][0] for sym, rows in self.stocks.items() if fill_bar and fill_bar in rows}
        refused = {}
        for name, lst in (orders or {}).items():
            a = self.acc.setdefault(name, {"cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
            for od in sorted(lst or [], key=lambda o: o.get("action") != "SELL"):
                s, act = od.get("symbol"), od.get("action")
                if s in self.stocks:
                    px = s_open.get(s)
                    if px is None:
                        refused.setdefault(name, []).append({**od, "why": "stock market closed"})
                        continue
                else:
                    px = opn.get(s)
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
                    if od.get("dollars") is not None:          # a chosen amount (never more than the cash there is)
                        spend = min(float(od["dollars"]), a["cash"]) / (1 + COST)
                    elif od.get("of"):                         # an even share of the cash that is left
                        spend = a["cash"] / max(1, int(od["of"])) / (1 + COST)
                    else:
                        spend = (a["cash"] if od.get("all") else a["cash"] / max(1, SLOTS - len(a["shares"]))) / (1 + COST)
                    if spend < 1.0:
                        refused.setdefault(name, []).append({**od, "why": "no cash left"})
                        continue
                    a["shares"][s] = spend / px
                    a["cash"] -= spend * (1 + COST)
                    a["costs"] += spend * COST
                    a["trades"] += 1
        new_prev = self.prev_close
        self._show_stocks(known)
        close.update(self.s_close)
        for a in self.acc.values():
            a["value"] = a["cash"] + sum(q * close[x] for x, q in a["shares"].items())
        new = []
        while self.n_news < len(self.news) and self.news[self.n_news]["time"] <= known:
            new.append(self.news[self.n_news])
            self.n_news += 1
        nxt = self._bar_starting(known, plus(known, 60))        # can orders placed now fill in the next hour?
        opn.update(s_open)
        step = {"time": t, "known_at": known, "open": opn, "close": close, "stock_market_open": nxt is not None,
                "stock_prev_close": self.prev_close if (self.k == 0 or self.prev_close is not new_prev) else None}
        return {"step": step, "news": new, "accounts": self.acc, "refused": refused,
                "last_step": self.k + 1 == len(self.grid), "universe": self.universe if self.k == 0 else None}


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
    print(f"ready {len(ex.grid)} hours, {len(ex.universe)} symbols, {len(ex.news)} headlines on port {a.port}",
          flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
