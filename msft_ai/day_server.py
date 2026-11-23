#!/usr/bin/env python3
"""
The Microsoft test server. It is the ONLY program that opens data/sealed/msft/. Each POST /next hands out ONE new
trading day (3 Jan 2022 .. 20 Nov 2026), oldest first:
  - prices of that day (Microsoft, competitors, market, economic gauges);
  - headlines whose date is after the previous served day and on or before this day (weekend news comes with Monday);
  - Microsoft SEC filings and reported quarterly figures filed after the previous served day, on or before this day.
It also keeps the practice accounts. An order sent with a request ("BUY" = all money in MSFT, "SELL" = all cash,
"HOLD"/null = no change) fills at the OPEN of the day that request returns (the trader decided after the previous
close). Costs 0.05% of every amount bought or sold. Cash grows each day by (1 + previous day's T-bill yield)^(1/252).

    POST /next {"orders": {"ai": "BUY"}}  ->  {"day": {...}, "values": {"ai": 1000.0, ...}}   or  {"done": true, ...}
"""
import argparse
import csv
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
SEALED = os.path.join(os.path.dirname(HERE), "data", "sealed", "msft")
COST = 0.0005
NY = ZoneInfo("America/New_York")


def bey(discount_pct):
    """13-week bill discount rate (annual %) -> bond-equivalent yield (annual %)."""
    d = discount_pct / 100.0
    return 100.0 * 365.0 * d / (360.0 - 91.0 * d)


def load(folder):
    with open(os.path.join(folder, "prices.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    days = [{"date": r["date"], "prices": {k: float(v) for k, v in r.items() if k != "date" and v != ""},
             "news": [], "sec_filings": [], "sec_results": []} for r in rows]
    dates = [d["date"] for d in days]

    def slot(day_str):
        """Index of the first served day on or after day_str (None if after the last day)."""
        import bisect
        i = bisect.bisect_left(dates, day_str)
        return i if i < len(dates) else None

    seen = set()
    for name in sorted(os.listdir(os.path.join(folder, "news"))):
        topic = name.replace(".jsonl", "")
        with open(os.path.join(folder, "news", name)) as f:
            for line in f:
                for it in json.loads(line)["items"]:
                    when = datetime.strptime(it["published"], "%Y-%m-%d %H:%M:%S%z").astimezone(NY)
                    key = (topic, it["title"])
                    i = slot(when.strftime("%Y-%m-%d"))
                    if key in seen or i is None:
                        continue
                    seen.add(key)
                    days[i]["news"].append({"topic": topic, "title": it["title"], "source": it["source"],
                                            "date": when.strftime("%Y-%m-%d")})
    with open(os.path.join(folder, "sec.json")) as f:
        sec = json.load(f)
    for x in sec["filings"]:
        i = slot(x["filed"])
        if i is not None:
            days[i]["sec_filings"].append(x)
    for x in sec["quarterly_results"]:
        i = slot(x["filed"])
        if i is not None:
            days[i]["sec_results"].append(x)
    for d in days:
        d["news"].sort(key=lambda x: x["date"], reverse=True)
    return days


class Exchange:
    def __init__(self, folder):
        self.days = load(folder)
        self.k = -1
        self.acc = {}

    def next(self, orders):
        if self.k + 1 >= len(self.days):
            return {"done": True, "accounts": self.acc}
        self.k += 1
        d = self.days[self.k]
        if self.k > 0:
            g = (1.0 + bey(self.days[self.k - 1]["prices"]["TBILL3M"]) / 100.0) ** (1.0 / 252.0)
            for a in self.acc.values():
                a["cash"] *= g
        o = d["prices"]["MSFT_open_tr"]
        for name, order in (orders or {}).items():
            a = self.acc.setdefault(name, {"cash": 1000.0, "shares": 0.0, "trades": 0, "costs": 0.0})
            if order == "BUY" and a["cash"] > 0:
                spend = a["cash"] / (1.0 + COST)
                a["shares"] += spend / o
                a["costs"] += spend * COST
                a["cash"] = 0.0
                a["trades"] += 1
            elif order == "SELL" and a["shares"] > 0:
                got = a["shares"] * o
                a["cash"] += got * (1.0 - COST)
                a["costs"] += got * COST
                a["shares"] = 0.0
                a["trades"] += 1
            elif order not in (None, "HOLD", "BUY", "SELL"):
                raise ValueError(f"bad order {order!r}")
        c = d["prices"]["MSFT_close_tr"]
        for a in self.acc.values():
            a["value"] = a["cash"] + a["shares"] * c
        return {"day": d, "values": {n: a["value"] for n, a in self.acc.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--folder", default=SEALED)
    a = ap.parse_args()
    ex = Exchange(a.folder)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            try:
                out, code = ex.next(json.loads(body or b"{}").get("orders")), 200
            except Exception as e:   # noqa: BLE001
                out, code = {"error": str(e)}, 400
            data = json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    print(f"ready {len(ex.days)} days on port {a.port}", flush=True)
    HTTPServer(("127.0.0.1", a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
