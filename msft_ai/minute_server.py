#!/usr/bin/env python3
"""
Minute test server: the ONLY program that opens data/sealed/msft/ for the minute test. Each POST /next hands out ONE
new regular-hours minute (MSFT bar, SPY and QQQ closes), oldest first, plus:
  - headlines that became known by the end of that minute: a headline with a real time stamp from that time on; a
    headline that only carries a date (Google gives midnight) from the first minute of the next trading day;
  - at the first minute of each day, the daily background known before that day (Microsoft's daily trend,
    competitors, economy, latest SEC results) taken only from days before it.
It keeps the practice accounts: an order sent with a request (BUY = all in MSFT, SELL = all cash, HOLD/null = no
change) fills at the OPEN of the minute that request returns. 0.05% of every amount bought or sold. No interest
inside the test (one month; cash interest would be about 0.3%).

    POST /next {"orders": {"pattern": "BUY"}} -> {"minute": {...}, "values": {...}}  or  {"done": true, "accounts": {...}}
"""
import argparse
import csv
import json
import os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.join(os.path.dirname(HERE), "data", "sealed", "msft")
COST = 0.0005
NY = ZoneInfo("America/New_York")
PLACEHOLDER_HOURS = {"07:00:00", "08:00:00"}       # Google's date-only items are stamped at midnight Pacific


def load():
    with open(os.path.join(FOLDER, "minutes.csv"), newline="") as f:
        mins = [{k: (v if k == "time" else float(v)) for k, v in r.items()} for r in csv.DictReader(f)]
    start_day = mins[0]["time"][:10]
    with open(os.path.join(FOLDER, "prices.csv"), newline="") as f:
        daily = [{k: (v if k == "date" else float(v)) for k, v in r.items() if v != ""} for r in csv.DictReader(f)]
    with open(os.path.join(FOLDER, "sec.json")) as f:
        sec = json.load(f)
    news, seen = [], set()
    for name in sorted(os.listdir(os.path.join(FOLDER, "news"))):
        topic = name.replace(".jsonl", "")
        with open(os.path.join(FOLDER, "news", name)) as f:
            for line in f:
                for it in json.loads(line)["items"]:
                    if (topic, it["title"]) in seen:
                        continue
                    seen.add((topic, it["title"]))
                    t = datetime.strptime(it["published"], "%Y-%m-%d %H:%M:%S%z")
                    if it["published"][11:19] in PLACEHOLDER_HOURS:
                        local_day = t.astimezone(ZoneInfo("America/Los_Angeles")).date()
                        known = datetime.combine(local_day + timedelta(days=1), datetime.min.time(), NY)
                    else:
                        known = t.astimezone(NY)
                    if known.strftime("%Y-%m-%d") >= (datetime.fromisoformat(start_day) - timedelta(days=4)).strftime("%Y-%m-%d"):
                        news.append({"topic": topic, "title": it["title"],
                                     "known": known.strftime("%Y-%m-%d %H:%M")})
    news.sort(key=lambda x: x["known"])
    return mins, daily, sec, news


def day_context(day, daily, sec):
    """Background known before `day` (only rows dated before it)."""
    past = [d for d in daily if d["date"] < day]
    if not past:
        return {}
    c = [d["MSFT_close"] for d in past]

    def ch(series, k):
        return round((series[-1] / series[-1 - k] - 1) * 100, 1) if len(series) > k else None
    ctx = {"as_of": past[-1]["date"], "msft_close": c[-1], "msft_change_pct": {"1w": ch(c, 5), "1m": ch(c, 21),
           "3m": ch(c, 63), "1y": ch(c, 252)},
           "competitors_1w_pct": {s: ch([d[f"{s}_close"] for d in past], 5)
                                  for s in ["AAPL", "GOOGL", "AMZN", "META", "NVDA", "ORCL", "CRM"]},
           "vix": past[-1]["VIX"], "ten_year_yield": past[-1]["TNX10Y"], "tbill_3m": past[-1]["TBILL3M"]}
    res = [x for x in sec["quarterly_results"] if x["filed"] < day]
    if res:
        end = max(x["end"] for x in res)
        ctx["latest_quarter"] = {x["item"]: x["value"] for x in res if x["end"] == end}
        ctx["latest_quarter"]["quarter_end"] = end
    return ctx


class Exchange:
    def __init__(self):
        self.mins, self.daily, self.sec, self.news = load()
        self.k, self.n_news, self.acc = -1, 0, {}

    def next(self, orders):
        if self.k + 1 >= len(self.mins):
            return {"done": True, "accounts": self.acc}
        self.k += 1
        m = self.mins[self.k]
        o = m["MSFT_open"]
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
        for a in self.acc.values():
            a["value"] = a["cash"] + a["shares"] * m["MSFT_close"]
        new = []
        while self.n_news < len(self.news) and self.news[self.n_news]["known"] <= m["time"]:
            new.append(self.news[self.n_news])
            self.n_news += 1
        out = {"minute": m, "news": new, "values": {n: a["value"] for n, a in self.acc.items()}}
        if self.k == 0 or self.mins[self.k - 1]["time"][:10] != m["time"][:10]:
            out["day_context"] = day_context(m["time"][:10], self.daily, self.sec)
        out["last_minute"] = self.k + 1 == len(self.mins)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    a = ap.parse_args()
    ex = Exchange()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            out = ex.next(json.loads(body or b"{}").get("orders"))
            data = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", a.port), Handler)
    print(f"ready {len(ex.mins)} minutes on port {a.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
