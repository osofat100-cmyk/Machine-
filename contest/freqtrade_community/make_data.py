"""Freqtrade data for PEARL/USDT: pre-Oct history (warm-up) + sealed minutes fetched one at a time from the server.
The sealed file has no opens, so a sealed minute's open = the previous minute's close."""
import sys
import pandas as pd
from pathlib import Path
sys.path.insert(0, "/home/user/Machine-/contest")
import sealed  # noqa: E402
from freqtrade.data.history import get_datahandler  # noqa: E402
from freqtrade.enums import CandleType  # noqa: E402

h = sealed.history_before_oct()[["time", "open", "high", "low", "close", "volume"]]
s = pd.read_csv("data/sealed_minutes.csv")
s["time"] = pd.to_datetime(s["time"], utc=True)
s.loc[0, "open"] = h["close"].iloc[-1]
s = s[["time", "open", "high", "low", "close", "volume"]]
m = pd.concat([h, s], ignore_index=True).rename(columns={"time": "date"})
m["date"] = pd.to_datetime(m["date"], utc=True)
assert m["date"].is_monotonic_increasing and m["date"].diff().dropna().eq(pd.Timedelta("1min")).all()
dh = get_datahandler(Path("user_data/data/bigone"), "feather")
for tf, rule in [("1m", "1min"), ("3m", "3min"), ("5m", "5min"), ("15m", "15min"), ("30m", "30min"), ("1h", "1h"),
                 ("2h", "2h"), ("4h", "4h"), ("6h", "6h"), ("8h", "8h"), ("12h", "12h"), ("1d", "1D")]:
    r = m.set_index("date").resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna().reset_index()
    dh.ohlcv_store("PEARL/USDT", tf, r, CandleType.SPOT)
    print(tf, len(r), r["date"].iloc[0], r["date"].iloc[-1])
