"""Freqtrade data for PEARL/USDT: history before 1 Oct (real opens) + sealed minutes from the price server
(open = previous close, the sealed file has no opens). Saved as 1m and resampled timeframes."""
import sys
import pandas as pd

sys.path.insert(0, "/home/user/Machine-/contest")
import sealed  # noqa: E402

h = sealed.history_before_oct()[["time", "open", "high", "low", "close", "volume"]]
s = pd.read_csv("data/sealed_minutes.csv")
s["time"] = pd.to_datetime(s["time"], utc=True)
s = s[["time", "open", "high", "low", "close", "volume"]]
df = pd.concat([h, s]).rename(columns={"time": "date"})
df = df.drop_duplicates("date").sort_values("date").set_index("date")
for c in ("open", "high", "low", "close", "volume"):
    df[c] = df[c].astype(float)
out = "user_data/data/bigone"
import os
os.makedirs(out, exist_ok=True)
for tf, rule in [("1m", "1min"), ("3m", "3min"), ("5m", "5min"), ("15m", "15min"), ("30m", "30min"), ("1h", "1h"),
                 ("2h", "2h"), ("4h", "4h"), ("1d", "1D")]:
    r = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    r.reset_index().to_feather(f"{out}/PEARL_USDT-{tf}.feather")
    print(tf, len(r), r.index[0], r.index[-1])
