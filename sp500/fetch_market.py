#!/usr/bin/env python3
"""
Download the S&P 500 test data (the last ~60 days), saving each piece as it arrives; re-running skips what is saved.

  - universe: the 500 largest US common stocks by market value from Nasdaq's stock screener (close to the S&P 500
    list; Wikipedia and S&P's own list are not reachable from here), with their sectors;
  - 5-minute bars (regular hours) for those 500 and SPY from Yahoo (the finest step Yahoo keeps for 60 days);
  - Google News headlines, day by day, for the market, the economy and the 15 largest companies. ONLY headlines with
    a real publication time are kept; date-only headlines are dropped, so news can be handed out at its exact minute.

    python3 sp500/fetch_market.py  -> data/sealed/market/{universe.csv, bars/<SYM>.csv, news/<query>.jsonl}
"""
import json
import os
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sealed", "market")
INTERVAL = os.environ.get("INTERVAL", "5m")                    # 5m (default) or 2m; both cover 60 days
BARS = "bars" if INTERVAL == "5m" else f"bars_{INTERVAL}"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) personal-research-script", "Accept": "application/json"}
PLACEHOLDER = {"07:00:00", "08:00:00"}             # Google's date-only items are stamped at midnight Pacific
MARKET_QUERIES = ['"stock market"', '"S&P 500"', '"Wall Street" stocks', '"Federal Reserve"',
                  'inflation OR CPI OR "jobs report"', 'earnings report stock', 'tariffs stocks']


def get(url, **kw):
    for k in range(6):
        try:
            r = requests.get(url, headers=UA, timeout=30, **kw)
            if r.status_code == 200 and b"Sorry..." not in r.content[:2000]:
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * 2 ** k)
    raise RuntimeError(url)


def universe():
    path = os.path.join(OUT, "universe.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    rows = get("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&download=true").json()["data"]["rows"]
    df = pd.DataFrame(rows)
    df = df[(df["country"] == "United States") & df["symbol"].str.fullmatch(r"[A-Z]{1,5}")]
    df = df[~df["name"].str.contains("Preferred|Warrant|Unit|Depositary|Notes|Fund|Trust", case=False, regex=True)
            | df["name"].str.contains("Realty|REIT|Properties", case=False, regex=True)]
    df["marketCap"] = pd.to_numeric(df["marketCap"], errors="coerce")
    df = df.dropna(subset=["marketCap"]).sort_values("marketCap", ascending=False)
    df["company"] = df["name"].str.replace(r" (Class [A-C] )?(Common|Ordinary|Capital) Stock.*$", "", regex=True)
    df = df.drop_duplicates("company")                       # one share class per company (e.g. GOOGL, not GOOG)
    df = df.head(500)[["symbol", "company", "sector", "industry", "marketCap"]]
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"universe: {len(df)} stocks, largest {', '.join(df['symbol'].head(10))}")
    return df


def bars(symbol):
    path = os.path.join(OUT, BARS, f"{symbol}.csv")
    if os.path.exists(path):
        return
    if INTERVAL == "1m":                       # Yahoo: 1-minute bars only for the last 30 days, at most ~7 days a call
        now, frames, p2 = int(time.time()), [], int(time.time())
        while p2 > now - int(29.5 * 86400):
            p1 = max(p2 - 6 * 86400, now - int(29.5 * 86400))
            frames.append(get(f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                              params={"period1": p1, "period2": p2, "interval": "1m",
                                      "includePrePost": "false"}).json()["chart"]["result"])
            p2 = p1
        js = [j[0] for j in frames if j and j[0].get("timestamp")]
    else:
        j = get(f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                params={"range": "60d", "interval": INTERVAL, "includePrePost": "false"}).json()["chart"]["result"]
        js = [j[0]] if j and j[0].get("timestamp") else []
    if not js:
        print(f"  no bars for {symbol}")
        return
    df = pd.concat([pd.DataFrame({"ts": x["timestamp"], **{k: x["indicators"]["quote"][0][k] for k in
                                                         ("open", "high", "low", "close", "volume")}}) for x in js])
    df = df.drop_duplicates("ts").sort_values("ts").dropna(subset=["open", "close"])
    df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert("America/New_York").dt.strftime("%Y-%m-%d %H:%M")
    df = df[(df["time"].str[11:] >= "09:30") & (df["time"].str[11:] < "16:00")]
    df[["time", "open", "high", "low", "close", "volume"]].to_csv(path, index=False, float_format="%.4f")


def news_query(name, q, days):
    path = os.path.join(OUT, "news", f"{name}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path) as f:
            done = {json.loads(line)["day"] for line in f}
    for d in days:
        if d.isoformat() in done:
            continue
        url = (f"https://news.google.com/rss/search?q={quote(q + f' after:{d - timedelta(days=1)} before:{d + timedelta(days=1)}')}"
               "&hl=en-US&gl=US&ceid=US:en")
        root = ET.fromstring(get(url).content)
        items = []
        for it in root.iter("item"):
            raw = it.findtext("pubDate")
            pub = parsedate_to_datetime(raw)
            stamp = pub.strftime("%Y-%m-%d %H:%M:%S%z")
            if stamp[11:19] in PLACEHOLDER:
                continue                                    # no real time: dropped
            items.append({"title": it.findtext("title"), "published": stamp})
        with open(path, "a") as f:
            f.write(json.dumps({"day": d.isoformat(), "query": q, "items": items}) + "\n")
        time.sleep(1.5)


def main():
    u = universe()
    os.makedirs(os.path.join(OUT, BARS), exist_ok=True)
    syms = ["SPY"] + list(u["symbol"])
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(bars, syms))
    have = len(os.listdir(os.path.join(OUT, BARS)))
    spy = pd.read_csv(os.path.join(OUT, BARS, "SPY.csv"))
    print(f"bars: {have} of {len(syms)} symbols; SPY {spy['time'].iloc[0]} .. {spy['time'].iloc[-1]}, {len(spy)} steps", flush=True)
    first = date.fromisoformat(spy["time"].iloc[0][:10]) - timedelta(days=3)
    days = [first + timedelta(days=i) for i in range((date.fromisoformat(spy["time"].iloc[-1][:10]) - first).days + 1)]
    os.makedirs(os.path.join(OUT, "news"), exist_ok=True)
    queries = {f"market_{i}": q for i, q in enumerate(MARKET_QUERIES)}
    queries.update({f"co_{r.symbol}": f'"{r.company.split(" Inc")[0].split(" Corporation")[0].split(",")[0]}"'
                    for r in u.head(15).itertuples()})
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda kv: news_query(kv[0], kv[1], days), queries.items()))
    n = sum(len(json.loads(line)["items"]) for name in os.listdir(os.path.join(OUT, "news"))
            for line in open(os.path.join(OUT, "news", name)))
    print(f"news: {len(queries)} queries x {len(days)} days, {n} headlines with exact times", flush=True)


if __name__ == "__main__":
    main()
