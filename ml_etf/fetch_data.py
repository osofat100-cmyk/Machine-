#!/usr/bin/env python3
"""
Download the 13 ETFs and the T-bill rate, check them, and write the development file and the sealed test file
(PLAN.md section 1).

    python3 ml_etf/fetch_data.py
      -> ml_etf/data/dev.csv              26 May 2000 - 31 Dec 2015 (the programs may learn from this)
      -> data/sealed/etf_test.csv         4 Jan 2016 - 20 Nov 2026 (only day_server.py opens this)
      -> ml_etf/data_checks.txt           what was checked and the results (committed)

Columns (wide, one row per trading day): date, rate (cash rate, bond-equivalent annual %), then for each symbol SYM_open, SYM_close, SYM_volume,
where SYM_open / SYM_close are total-return (dividend-adjusted) prices.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SYMBOLS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
START, SPLIT, LAST = "2000-05-26", "2016-01-01", "2026-11-20"
DEV = os.path.join(HERE, "data", "dev.csv")
SEALED = os.path.join(ROOT, "data", "sealed", "etf_test.csv")
UA = {"User-Agent": "Mozilla/5.0 (research script)", "Accept": "application/json"}


def get_json(url, tries=5):
    for k in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = str(e)
        time.sleep(2 ** k)
    raise RuntimeError(f"{url}: {err}")


def yahoo(symbol):
    """Daily bars: raw open/close (split-adjusted), adjclose (split + dividend), volume, dividends."""
    sym = symbol.replace("^", "%5E")
    j = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
                 f"?period1=0&period2=9999999999&interval=1d&events=div%2Csplit")["chart"]["result"][0]
    q = j["indicators"]["quote"][0]
    df = pd.DataFrame({"date": pd.to_datetime(j["timestamp"], unit="s").normalize(),
                       "open": q["open"], "close": q["close"], "volume": q["volume"]})
    if "adjclose" in j["indicators"]:
        df["adjclose"] = j["indicators"]["adjclose"][0]["adjclose"]
    divs = {pd.to_datetime(int(k), unit="s").normalize(): v["amount"]
            for k, v in j.get("events", {}).get("dividends", {}).items()}
    return df.drop_duplicates("date").set_index("date").sort_index(), divs


def bey(discount_pct):
    """13-week bill: discount rate d (annual %) -> bond-equivalent yield (annual %) = 365 d / (360 - 91 d)."""
    d = discount_pct / 100.0
    return 100.0 * 365.0 * d / (360.0 - 91.0 * d)


def nasdaq_closes(symbol):
    j = get_json(f"https://api.nasdaq.com/api/quote/{symbol}/historical?assetclass=etf"
                 f"&fromdate=2016-11-01&todate={LAST}&limit=9999")
    rows = j["data"]["tradesTable"]["rows"]
    return pd.Series({pd.Timestamp(r["date"]): float(r["close"].replace("$", "").replace(",", ""))
                      for r in rows}).sort_index()


def nasdaq_dividends(symbol):
    j = get_json(f"https://api.nasdaq.com/api/quote/{symbol}/dividends?assetclass=etf")
    rows = j["data"]["dividends"]["rows"]
    return {pd.Timestamp(r["exOrEffDate"]): float(r["amount"].replace("$", "")) for r in rows
            if r.get("exOrEffDate") and r["exOrEffDate"] != "N/A"}


def main():
    log = []
    say = lambda s: (print(s, flush=True), log.append(s))  # noqa: E731
    raw, divs = {}, {}
    for s in SYMBOLS:
        raw[s], divs[s] = yahoo(s)
        time.sleep(0.5)
    irx, _ = yahoo("^IRX")

    frames = []
    for s in SYMBOLS:
        d = raw[s][(raw[s].index >= START) & (raw[s].index <= LAST)]
        assert d[["open", "close", "adjclose", "volume"]].notna().all().all(), f"{s}: missing values"
        ratio = d["adjclose"] / d["close"]
        frames.append(pd.DataFrame({f"{s}_open": d["open"] * ratio, f"{s}_close": d["adjclose"],
                                    f"{s}_volume": d["volume"].astype(float)}))
    dates = [set(f.index) for f in frames]
    assert all(x == dates[0] for x in dates), "the 13 symbols do not share the same trading days"
    panel = pd.concat(frames, axis=1).sort_index()
    rate = bey(irx["close"]).reindex(panel.index).ffill()
    assert rate.notna().all(), "T-bill rate missing at the start"
    panel.insert(0, "rate", rate)
    say(f"panel: {len(panel):,} days, {panel.index[0].date()} -> {panel.index[-1].date()}, 13 symbols, "
        f"no missing prices; T-bill rate filled forward on {int(irx['close'].reindex(panel.index).isna().sum())} days")

    # check 1: raw closes against Nasdaq (last ~10 years) for SPY and 3 others
    for s in ["SPY", "QQQ", "XLE", "XLU"]:
        n = nasdaq_closes(s)
        common = n.index.intersection(raw[s].index)
        diff = (raw[s].loc[common, "close"] / n.loc[common] - 1).abs()
        big = diff[diff > 0.0005]
        say(f"check closes {s}: {len(common)} common days, {len(big)} above 0.05%, largest gap {diff.max():.4%}"
            + "".join(f"\n    {d.date()}: Yahoo {raw[s].loc[d, 'close']:.4f}, Nasdaq {n.loc[d]:.4f}, {g:.4%}"
                      for d, g in big.items()))
        assert len(common) > 2000 and len(big) <= 0.001 * len(common) and diff.max() < 0.005, \
            f"{s}: Yahoo vs Nasdaq closes differ"
        time.sleep(0.5)

    # check 2: 2025-2026 dividends against Nasdaq (only Nasdaq-listed funds have a history there)
    for s in ["QQQ"]:
        n = nasdaq_dividends(s)
        y = {d: a for d, a in divs[s].items() if pd.Timestamp("2025-01-01") <= d <= pd.Timestamp(LAST)}
        assert y, f"{s}: no Yahoo dividends in 2025-2026"
        for d, a in sorted(y.items()):
            m = n.get(d)
            ok = m is not None and abs(m - a) < 0.005
            say(f"check dividend {s} {d.date()}: Yahoo {a:.4f}, Nasdaq {m if m is not None else 'missing'} "
                f"{'OK' if ok else 'MISMATCH'}")
            assert ok, f"{s} dividend {d.date()} differs"
        time.sleep(0.5)

    # check 3: T-bill rate against FRED's published DGS3MO yearly averages
    for yr, fred in ((2022, 2.09), (2023, 5.28)):
        avg = bey(irx["close"][irx.index.year == yr]).mean()
        say(f"check T-bill {yr}: ^IRX converted to bond-equivalent yield, average {avg:.2f}%, "
            f"FRED DGS3MO {fred:.2f}%")
        assert abs(avg - fred) < 0.15, f"T-bill {yr} differs from FRED"

    # check 4: the adjusted open keeps each day's open-to-close move and credits dividends overnight
    s = "SPY"
    d = raw[s]
    some = [x for x in sorted(divs[s]) if x >= pd.Timestamp("2016-01-01")][:3]
    for x in some:
        i = d.index.get_loc(x)
        prev, today = d.iloc[i - 1], d.iloc[i]
        adj_gap = (today["open"] * today["adjclose"] / today["close"]) / prev["adjclose"] - 1
        raw_gap = (today["open"] + divs[s][x]) / prev["close"] - 1
        say(f"check ex-date {s} {x.date()}: adjusted overnight move {adj_gap:.5%}, "
            f"raw move with the dividend added back {raw_gap:.5%}")
        assert abs(adj_gap - raw_gap) < 2e-4

    os.makedirs(os.path.dirname(DEV), exist_ok=True)
    os.makedirs(os.path.dirname(SEALED), exist_ok=True)
    out = panel.reset_index().rename(columns={"index": "date"})
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    dev, test = out[out["date"] < SPLIT], out[out["date"] >= SPLIT]
    dev.to_csv(DEV, index=False, float_format="%.8g")
    test.to_csv(SEALED, index=False, float_format="%.8g")
    say(f"development file: {len(dev):,} days {dev['date'].iloc[0]} -> {dev['date'].iloc[-1]}")
    say(f"sealed test file: {len(test):,} days (contents not shown)")
    with open(os.path.join(HERE, "data_checks.txt"), "w") as f:
        f.write("\n".join(log) + "\n")


if __name__ == "__main__":
    sys.exit(main())
