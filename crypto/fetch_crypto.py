#!/usr/bin/env python3
"""
Download the crypto test data, saving each piece as it arrives; re-running skips what is saved. Same sources and
rules as the S&P 500 test (sp500/fetch_market.py), with coins instead of stocks.

  - universe: the 100 largest coins by market value from Yahoo's crypto list, leaving out stablecoins (price held
    near $1) and wrapped / staked / bridged copies of other coins (they just follow the original);
  - 1-minute and 2-minute bars, around the clock, from Yahoo (1-minute bars exist for the last ~30 days);
  - Google News headlines for crypto, the economy and the 15 largest coins, day by day. ONLY headlines with a real
    publication time are kept, so each one can be handed out at its exact minute.

    python3 crypto/fetch_crypto.py  -> data/sealed/crypto/{universe.csv, bars_1m/, bars_2m/, news/}
"""
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sealed", "crypto")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) personal-research-script", "Accept": "application/json"}
PLACEHOLDER = {"07:00:00", "08:00:00"}
FIRST_NEWS_DAY, LAST_NEWS_DAY = date(2026, 11, 14), date(2026, 11, 24)
MARKET_QUERIES = ["bitcoin", "ethereum", '"crypto market" OR cryptocurrency', 'crypto regulation OR "SEC" crypto',
                  '"Federal Reserve" OR inflation OR "jobs report"', "stablecoin OR \"crypto ETF\"", "altcoins"]
NOT_REAL_COIN = re.compile(r"wrapped|staked|steth|wsteth|weth|eeth|beth|bep2|aave |bridged|\bcb[a-z]+|usd|tether|dai\b|"
                           r"usde|stable|gold|paxg|xaut", re.I)


COPIES = {"BTCT9486", "LBTC33652", "RETH", "FBTC", "EURC", "SLISBNBX", "TBTC26133", "SOLVBTC", "VBNB", "VBTC", "JLP"}


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
    quotes = []
    for start in (0, 250):
        r = get("https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved",
                params={"scrIds": "all_cryptocurrencies_us", "count": 250, "start": start}).json()
        quotes += r["finance"]["result"][0]["quotes"]
    rows = []
    for q in quotes:
        name = (q.get("shortName") or "").removesuffix(" USD")
        price = q.get("regularMarketPrice") or 0
        if NOT_REAL_COIN.search(name) or NOT_REAL_COIN.search(q["symbol"].removesuffix("-USD")):
            continue
        if 0.97 <= price <= 1.03:                                   # a coin held at $1 is a stablecoin
            continue
        base = q["symbol"].removesuffix("-USD")
        if base in COPIES or re.search(r"BTC|ETH|BNB|EUR", base) and base not in ("BTC", "ETH", "BNB", "ETC", "ETHFI"):
            continue                                                # a token that only tracks another coin
        rows.append({"symbol": q["symbol"], "coin": name, "marketCap": q.get("marketCap", 0)})
    df = pd.DataFrame(rows).drop_duplicates("coin").sort_values("marketCap", ascending=False).head(100)
    df["size"] = ["top 10" if i < 10 else "11-30" if i < 30 else "31-100" for i in range(len(df))]
    os.makedirs(OUT, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"universe: {len(df)} coins, largest {', '.join(df['symbol'].head(12))}", flush=True)
    return df


def bars(symbol, interval):
    folder = os.path.join(OUT, f"bars_{interval}")
    path = os.path.join(folder, f"{symbol}.csv")
    if os.path.exists(path):
        return
    now, frames = int(time.time()), []
    if interval == "1m":                       # Yahoo: 1-minute bars only for the last 30 days, ~7 days a call
        p2 = now
        while p2 > now - int(29.5 * 86400):
            p1 = max(p2 - 6 * 86400, now - int(29.5 * 86400))
            try:
                frames.append(get(f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                                  params={"period1": p1, "period2": p2, "interval": "1m"}).json()["chart"]["result"])
            except RuntimeError:
                pass
            p2 = p1
    else:
        try:
            frames.append(get(f"https://query2.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                              params={"range": "60d", "interval": interval}).json()["chart"]["result"])
        except RuntimeError:
            pass
    js = [j[0] for j in frames if j and j[0].get("timestamp")]
    if not js:
        print(f"  no {interval} bars for {symbol}", flush=True)
        return
    df = pd.concat([pd.DataFrame({"ts": x["timestamp"], **{k: x["indicators"]["quote"][0][k] for k in
                                                         ("open", "high", "low", "close", "volume")}}) for x in js])
    df = df.drop_duplicates("ts").sort_values("ts").dropna(subset=["open", "close"])
    df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d %H:%M")   # UTC, 24/7
    os.makedirs(folder, exist_ok=True)
    df[["time", "open", "high", "low", "close", "volume"]].to_csv(path, index=False, float_format="%.8g")


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
            stamp = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d %H:%M:%S%z")
            if stamp[11:19] in PLACEHOLDER:
                continue                                    # no real time: dropped
            items.append({"title": it.findtext("title"), "published": stamp})
        with open(path, "a") as f:
            f.write(json.dumps({"day": d.isoformat(), "query": q, "items": items}) + "\n")
        time.sleep(1.5)


def main():
    u = universe()
    syms = list(u["symbol"])
    for interval in ("1m", "2m"):
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(lambda s: bars(s, interval), syms))
        have = len(os.listdir(os.path.join(OUT, f"bars_{interval}")))
        btc = pd.read_csv(os.path.join(OUT, f"bars_{interval}", "BTC-USD.csv"))
        print(f"bars {interval}: {have} of {len(syms)} coins; BTC {btc['time'].iloc[0]} .. {btc['time'].iloc[-1]}, "
              f"{len(btc)} steps", flush=True)
    days = [FIRST_NEWS_DAY + timedelta(days=i) for i in range((LAST_NEWS_DAY - FIRST_NEWS_DAY).days + 1)]
    os.makedirs(os.path.join(OUT, "news"), exist_ok=True)
    queries = {f"market_{i}": q for i, q in enumerate(MARKET_QUERIES)}
    queries.update({f"coin_{r.symbol.split('-')[0]}": f'"{r.coin}" crypto' for r in u.head(15).itertuples()})
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda kv: news_query(kv[0], kv[1], days), queries.items()))
    n = sum(len(json.loads(line)["items"]) for name in os.listdir(os.path.join(OUT, "news"))
            for line in open(os.path.join(OUT, "news", name)))
    print(f"news: {len(queries)} queries x {len(days)} days, {n} headlines with exact times", flush=True)


if __name__ == "__main__":
    sys.exit(main())
