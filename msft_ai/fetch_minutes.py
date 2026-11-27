#!/usr/bin/env python3
"""
Download the last ~30 days of 1-minute bars (regular hours) for MSFT, SPY and QQQ from Yahoo (the most Yahoo gives).

    python3 msft_ai/fetch_minutes.py   -> data/sealed/msft/minutes.csv   (only minute_server.py reads it)
"""
import os
import time

import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sealed", "msft", "minutes.csv")
UA = {"User-Agent": "Mozilla/5.0 personal-research-script"}


def bars(symbol):
    now = int(time.time())
    frames = []
    p2 = now
    while True:
        p1 = max(p2 - 6 * 86400, now - int(29.5 * 86400))
        j = requests.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
                         params={"period1": p1, "period2": p2, "interval": "1m", "includePrePost": "false"},
                         headers=UA, timeout=30).json()["chart"]["result"]
        if j and j[0].get("timestamp"):
            q = j[0]["indicators"]["quote"][0]
            frames.append(pd.DataFrame({"ts": j[0]["timestamp"], "open": q["open"], "high": q["high"],
                                        "low": q["low"], "close": q["close"], "volume": q["volume"]}))
        if p1 <= now - int(29.5 * 86400):
            break
        p2 = p1
        time.sleep(0.5)
    df = pd.concat(frames).drop_duplicates("ts").sort_values("ts")
    df["time"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert("America/New_York")
    df = df[(df["time"].dt.strftime("%H:%M") >= "09:30") & (df["time"].dt.strftime("%H:%M") < "16:00")]
    return df.set_index("ts")


def main():
    m = bars("MSFT").dropna(subset=["open", "close"])
    out = pd.DataFrame({"time": m["time"].dt.strftime("%Y-%m-%d %H:%M"),
                        "MSFT_open": m["open"], "MSFT_high": m["high"], "MSFT_low": m["low"],
                        "MSFT_close": m["close"], "MSFT_volume": m["volume"].fillna(0)})
    for s in ["SPY", "QQQ"]:
        d = bars(s)
        out[f"{s}_close"] = d["close"].reindex(out.index).ffill()
    out = out.dropna()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False, float_format="%.4f")
    days = out["time"].str[:10]
    print(f"{len(out)} minutes, {days.nunique()} days {days.iloc[0]} .. {days.iloc[-1]}")
    print(days.value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
