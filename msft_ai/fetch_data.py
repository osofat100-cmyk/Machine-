#!/usr/bin/env python3
"""
Download everything the Microsoft AI test uses, saving each piece the moment it arrives (re-running skips what is
already saved).

    python3 msft_ai/fetch_data.py
      -> data/sealed/msft/prices.csv      daily prices 2022-01-03 .. 2026-11-20 (MSFT, competitors, market, economy)
      -> data/sealed/msft/sec.json        Microsoft's SEC filings (date filed) and reported quarterly results
      -> data/sealed/msft/news/*.jsonl    Google News headlines, one file per query, one line per search window

Everything lives under data/sealed/ (git-ignored). Only day_server.py reads it; it hands out one day at a time.
"""
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sealed", "msft")
FIRST, TEST_START, LAST = "2022-01-03", "2024-01-02", "2026-11-20"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) personal-research-script"}

STOCK = "MSFT"
COMPETITORS = ["AAPL", "GOOGL", "AMZN", "META", "NVDA", "ORCL", "CRM"]
MARKET = ["SPY", "QQQ", "XLK"]
ECONOMY = {"^VIX": "VIX", "^TNX": "TNX10Y", "^IRX": "TBILL3M", "DX-Y.NYB": "DOLLAR", "CL=F": "OIL"}

NEWS_QUERIES = {   # name -> (query, window length in days)
    "microsoft": ("Microsoft", 3),
    "msft_stock": ("MSFT stock", 3),
    "competitors": ("Apple OR Alphabet OR Google OR Amazon OR Nvidia OR OpenAI OR Oracle OR Salesforce", 7),
    "economy": ('"Federal Reserve" OR inflation OR "jobs report" OR recession OR tariffs OR "stock market"', 7),
}


def get(url, tries=6, pause=2.0):
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200 and b"Sorry..." not in r.content[:2000]:
                return r
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = str(e)
        time.sleep(pause * 2 ** k)
    raise RuntimeError(f"{url}: {err}")


def yahoo(symbol):
    j = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
            f"?period1=1609459200&period2=9999999999&interval=1d&events=div%2Csplit").json()["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    df = pd.DataFrame({"date": pd.to_datetime(j["timestamp"], unit="s").strftime("%Y-%m-%d"),
                       "open": q["open"], "close": q["close"], "volume": q["volume"]})
    if "adjclose" in j["indicators"]:
        df["adjclose"] = j["indicators"]["adjclose"][0]["adjclose"]
    return df.drop_duplicates("date").set_index("date").sort_index()


def prices():
    path = os.path.join(OUT, "prices.csv")
    if os.path.exists(path):
        print("prices: already saved")
        return
    m = yahoo(STOCK)
    m = m[(m.index >= FIRST) & (m.index <= LAST)].dropna(subset=["open", "close"])
    out = pd.DataFrame(index=m.index)
    # traded prices: dividend-adjusted open/close (a dividend is credited to whoever held overnight into it)
    out["MSFT_open_tr"] = m["open"] * m["adjclose"] / m["close"]
    out["MSFT_close_tr"] = m["adjclose"]
    # shown to the AI: the plain prices of the day (no later adjustments)
    out["MSFT_open"], out["MSFT_close"], out["MSFT_volume"] = m["open"], m["close"], m["volume"]
    for s in COMPETITORS + MARKET:
        d = yahoo(s)
        # split-adjusted closes, shown to the AI only as returns (a split does not change a return)
        out[f"{s}_close"] = d["close"].reindex(out.index).ffill()
        time.sleep(0.5)
    for s, name in ECONOMY.items():
        d = yahoo(s)
        full = d["close"].dropna()
        # value known at each MSFT close: last value on or before that date
        out[name] = full.reindex(sorted(set(full.index) | set(out.index))).ffill().reindex(out.index)
        time.sleep(0.5)
    assert out["MSFT_close"].notna().all() and out["TBILL3M"].notna().all()
    out.index.name = "date"
    os.makedirs(OUT, exist_ok=True)
    out.to_csv(path, float_format="%.6f")
    print(f"prices: {len(out)} days {out.index[0]} .. {out.index[-1]}, {out.shape[1]} columns")


def sec():
    path = os.path.join(OUT, "sec.json")
    if os.path.exists(path):
        print("sec: already saved")
        return
    sub = get("https://data.sec.gov/submissions/CIK0000789019.json").json()
    r = sub["filings"]["recent"]
    filings = [{"form": r["form"][i], "filed": r["filingDate"][i], "accepted": r["acceptanceDateTime"][i],
                "items": r["items"][i], "description": r["primaryDocDescription"][i], "accn": r["accessionNumber"][i]}
               for i in range(len(r["form"])) if r["form"][i] in ("8-K", "10-Q", "10-K")
               and FIRST <= r["filingDate"][i] <= LAST]
    facts = get("https://data.sec.gov/api/xbrl/companyfacts/CIK0000789019.json").json()["facts"]["us-gaap"]
    results = []
    for tag, label in [("RevenueFromContractWithCustomerExcludingAssessedTax", "revenue"),
                       ("NetIncomeLoss", "net_income"), ("EarningsPerShareDiluted", "eps_diluted")]:
        for unit, rows in facts[tag]["units"].items():
            for x in rows:
                if "start" in x and FIRST[:4] <= x["filed"][:4] and x["filed"] <= LAST:
                    days = (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
                    if 80 <= days <= 100:                                     # one quarter
                        results.append({"item": label, "start": x["start"], "end": x["end"], "value": x["val"],
                                        "filed": x["filed"], "form": x["form"], "accn": x["accn"]})
    with open(path, "w") as f:
        json.dump({"filings": filings, "quarterly_results": results}, f)
    print(f"sec: {len(filings)} filings, {len(results)} quarterly figures")


def news():
    os.makedirs(os.path.join(OUT, "news"), exist_ok=True)
    for name, (q, step) in NEWS_QUERIES.items():
        path = os.path.join(OUT, "news", f"{name}.jsonl")
        done = set()
        if os.path.exists(path):
            with open(path) as f:
                done = {json.loads(line)["after"] for line in f}
        d0 = date.fromisoformat(TEST_START) - timedelta(days=14)
        windows = []
        while d0 <= date.fromisoformat(LAST):
            windows.append(d0)
            d0 += timedelta(days=step)
        todo = [w for w in windows if w.isoformat() not in done]
        print(f"news {name}: {len(windows) - len(todo)} of {len(windows)} windows already saved", flush=True)
        for w in todo:
            after, before = w - timedelta(days=1), w + timedelta(days=step)    # Google's after/before are exclusive
            url = (f"https://news.google.com/rss/search?q={quote(q + f' after:{after} before:{before}')}"
                   "&hl=en-US&gl=US&ceid=US:en")
            root = ET.fromstring(get(url, pause=5.0).content)
            items = []
            for it in root.iter("item"):
                pub = parsedate_to_datetime(it.findtext("pubDate"))
                items.append({"title": it.findtext("title"), "source": it.findtext("source"),
                              "published": pub.strftime("%Y-%m-%d %H:%M:%S%z")})
            with open(path, "a") as f:
                f.write(json.dumps({"after": w.isoformat(), "days": step, "query": q, "items": items}) + "\n")
            time.sleep(4.0)
        print(f"news {name}: done", flush=True)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    prices()
    sec()
    news()
