#!/usr/bin/env python3
"""
The test's price server: the ONLY program that opens the sealed test prices
(data/sealed/PEARL_oct1_nov20.csv, made by fetch_sealed.py).

It hands them out one minute at a time, oldest first, and it is also the exchange:
  - it keeps the practice account itself ($1,000 USDC at the start)
  - an order sent with a request fills at the close of the minute that request returns,
    i.e. the minute after the decision, at cost 0.2% fee + max(0.5%, half a price step)
    (the same cost rule as every other test)
  - after the last minute it also reports buying on the first minute and holding to the end

    python3 price_server.py [--port 8765]

    GET /next?order=BUY&share=1.0      order: BUY, SELL or NONE
      -> {"ts": minutes since 1970, "time", "high", "low", "close", "source", "value"}
      -> {"done": true, "account": {...}} after the last minute
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd

from engine import FEE, HALF_GAP, decimals

SEALED = "data/sealed/PEARL_oct1_nov20.csv"


class Exchange:
    def __init__(self, path):
        df = pd.read_csv(path, parse_dates=["time"])
        self.time = df["time"].dt.strftime("%Y-%m-%d %H:%M").tolist()
        self.ts = df["time"].values.astype("datetime64[m]").astype(np.int64).tolist()
        self.hi, self.lo, self.cl = (df[c].astype(float).tolist() for c in ("high", "low", "close"))
        self.src = df["source"].tolist()
        self.k = -1
        self.seen = [-10 ** 9] * 10
        self.cash, self.coins = 1000.0, 0.0
        self.trades = []
        self.hold0 = None
        self.kap = FEE + HALF_GAP

    def cost(self, k):
        for d in range(max(decimals(self.cl[k]), decimals(self.hi[k]), decimals(self.lo[k])) + 1):
            self.seen[d] = k
        dec = max(d for d in range(10) if self.seen[d] > k - 1440)
        return FEE + max(HALF_GAP, 0.5 * 10.0 ** -dec / self.cl[k])

    def next(self, order, share):
        if self.k + 1 >= len(self.cl):
            return {"done": True, "account": self.summary()}
        self.k += 1
        k, c = self.k, self.cl[self.k]
        kap = self.cost(k)
        if self.hold0 is None:
            self.hold0 = 1000.0 / (c * (1 + kap))
        note = None
        if order == "BUY" and self.coins == 0 and self.cash > 0:
            put = min(1.0, max(0.0, share)) * self.cash
            self.coins = put / (c * (1 + kap))
            self.cash -= put
            note = "BUY"
        elif order == "SELL" and self.coins > 0:
            self.cash += self.coins * c * (1 - kap)
            self.coins = 0.0
            note = "SELL"
        value = self.cash + self.coins * c * (1 - kap)
        if note:
            self.trades.append({"time": self.time[k], "action": note, "price": c, "value": value,
                                "source": self.src[k]})
        self.kap = kap
        return {"ts": self.ts[k], "time": self.time[k], "high": self.hi[k], "low": self.lo[k], "close": c,
                "source": self.src[k], "value": value}

    def summary(self):
        k = self.k
        c, kap = self.cl[k], self.kap
        return {"first": self.time[0], "last": self.time[k], "minutes": k + 1,
                "value": self.cash + self.coins * c * (1 - kap), "cash": self.cash, "coins": self.coins,
                "holding": self.hold0 * c * (1 - kap), "trades": self.trades}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    ex = Exchange(SEALED)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            u = urlparse(self.path)
            if u.path != "/next":
                body, code = b'{"error": "only /next"}', 404
            else:
                q = parse_qs(u.query)
                order = q.get("order", ["NONE"])[0].upper()
                share = float(q.get("share", ["1"])[0])
                body, code = json.dumps(ex.next(order, share)).encode(), 200
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    print(f"price server: {len(ex.cl):,} sealed minutes, serving one at a time on 127.0.0.1:{a.port}", flush=True)
    HTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
