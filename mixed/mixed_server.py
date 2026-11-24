#!/usr/bin/env python3
"""
Crypto + stocks test server: ONE account that can hold the 100 coins and the ~500 S&P 500 stocks together.
It is a server program, so it may open the sealed folders: it loads them with the two existing servers' own loaders
(crypto/crypto_server.py and sp500/market_server.py, 1-minute bars) and hands out ONE minute at a time, oldest first.

Clock: UTC minutes of the crypto test (8,190 minutes up to 23 Nov 2026 21:00 UTC; crypto trades around the clock).
Stocks: each minute carries the latest stock minute-bar known by then. The stock market is open 09:30-16:00 New York
(14:30-21:00 UTC in November), Monday to Friday; outside those hours stock prices stand still and stock orders are
refused ("stock market closed").

News: crypto and stock headlines are handed out only at the exact minute they were published (step end >=
publication time), so they arrive at irregular times, as in real life.

Account rules (same as the other tests): orders sent with a request fill at the OPEN of the minute that request
returns. BUY with "split" spends the cash evenly over the empty slots (10 slots in all, coins and stocks together);
SELL sells the whole holding. 0.05% of every amount bought or sold. Buying something already held, selling something
not held, or an unknown symbol is refused and reported back.

    POST /next {"orders": {"ai": [{"action": "BUY", "symbol": "NVDA", "split": true}]}}
      -> {"step": {...}, "news": [...], "accounts": {...}, "refused": {...}}
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["STEP_MIN"] = "1"
os.environ.setdefault("START", "2026-11-16")          # stock bars from Monday 16 Nov (history before the test)
sys.path.insert(0, os.path.join(ROOT, "crypto"))
sys.path.insert(0, os.path.join(ROOT, "sp500"))
import crypto_server  # noqa: E402
import market_server  # noqa: E402

COST, SLOTS = 0.0005, 10
UTC, NY = ZoneInfo("UTC"), ZoneInfo("America/New_York")


def ny_to_utc(t):
    return datetime.strptime(t, "%Y-%m-%d %H:%M").replace(tzinfo=NY).astimezone(UTC).strftime("%Y-%m-%d %H:%M")


class Exchange:
    def __init__(self):
        c_uni, self.c_steps, c_news = crypto_server.load()
        s_uni, s_steps, s_news, have, cols = market_server.load()
        self.universe = ([{"symbol": u["symbol"], "kind": "crypto", "group": u.get("size", "")} for u in c_uni] +
                         [{"symbol": u["symbol"], "kind": "stock", "group": u.get("sector", "")} for u in s_uni
                          if u["symbol"] in have] + [{"symbol": "SPY", "kind": "stock", "group": "index fund"}])
        self.s_time = [ny_to_utc(st["time"]) for st in s_steps]      # stock bar start, UTC
        self.s_cols, self.s_have = cols, [s for s in have]
        self.s_ny = [st["time"] for st in s_steps]
        start = self.c_steps[0]["time"]
        news = [n for n in c_news if n["time"] >= start] + \
               [dict(n, time=ny_to_utc(n["time"])) for n in s_news if ny_to_utc(n["time"]) >= start]
        self.news = sorted(news, key=lambda n: n["time"])
        self.k, self.j, self.n_news, self.acc = -1, -1, 0, {}
        self.s_close, self.prev_close, self.day = {}, {}, None
        while self.j + 1 < len(self.s_time) and self.s_time[self.j + 1] < start:
            self._advance_stock()

    def _advance_stock(self):
        self.j += 1
        d = self.s_ny[self.j][:10]
        if d != self.day:                                        # a new trading day: yesterday's close is the base
            if self.s_close:
                self.prev_close = dict(self.s_close)
            self.day = d
        for s in self.s_have:
            c = self.s_cols[s][1][self.j]
            if c == c:
                self.s_close[s] = c

    def next(self, orders):
        if self.k + 1 >= len(self.c_steps):
            return {"done": True, "accounts": self.acc}
        self.k += 1
        st = self.c_steps[self.k]
        t = st["time"]
        bar = None                                               # a stock bar that starts this very minute?
        if self.j + 1 < len(self.s_time) and self.s_time[self.j + 1] <= t:
            while self.j + 1 < len(self.s_time) and self.s_time[self.j + 1] <= t:
                self._advance_stock()
            if self.s_time[self.j] == t:
                bar = self.j
        s_open = {s: self.s_cols[s][0][bar] for s in self.s_have if self.s_cols[s][0][bar] == self.s_cols[s][0][bar]} \
            if bar is not None else {}
        opn = dict(st["open"], **s_open)
        close = dict(st["close"], **self.s_close)
        refused = {}
        for name, lst in (orders or {}).items():
            a = self.acc.setdefault(name, {"cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
            lst = sorted(lst or [], key=lambda od: od.get("action") != "SELL")    # sells first, then buys
            for od in lst:
                s, act = od.get("symbol"), od.get("action")
                is_stock = not str(s).endswith("-USD")
                if is_stock and s in self.s_close and s not in s_open:
                    refused.setdefault(name, []).append({**od, "why": "stock market closed"})
                    continue
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
                    if od.get("all"):
                        spend = a["cash"] / (1 + COST)
                    else:
                        spend = a["cash"] / max(1, SLOTS - len(a["shares"])) / (1 + COST)
                    if spend < 1.0:
                        refused.setdefault(name, []).append({**od, "why": "no cash left"})
                        continue
                    a["shares"][s] = spend / px
                    a["cash"] -= spend * (1 + COST)
                    a["costs"] += spend * COST
                    a["trades"] += 1
        for a in self.acc.values():
            a["value"] = a["cash"] + sum(q * close[x] for x, q in a["shares"].items())
        new = []
        while self.n_news < len(self.news) and self.news[self.n_news]["time"] <= st["known_at"]:
            new.append(self.news[self.n_news])
            self.n_news += 1
        step = {"time": t, "known_at": st["known_at"], "open": opn, "close": close,
                "stock_market_open": bar is not None, "stock_prev_close": self.prev_close if self.k == 0 or
                (bar is not None and self.s_ny[bar][11:] == "09:30") else None}
        return {"step": step, "news": new, "accounts": self.acc, "refused": refused,
                "last_step": self.k + 1 == len(self.c_steps), "universe": self.universe if self.k == 0 else None}


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
    print(f"ready {len(ex.c_steps)} minutes, {len(ex.universe)} symbols, {len(ex.news)} headlines on port {a.port}",
          flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
