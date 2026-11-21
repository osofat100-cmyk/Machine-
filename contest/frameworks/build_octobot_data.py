"""Write an OctoBot backtesting data file (octobot_work/backtesting/data/) from contest minutes.

Stand-in for OctoBot's ExchangeHistoryCollector: same database rows as its get_ohlcv_history (candle
[open time, o, h, l, c, v], row timestamp = open time + time frame, i.e. the closing time), but the candles come
from history_before_oct (25 Jun - 30 Sep) + the sealed minutes exported through the price server, not from the
exchange. Higher time frames are built from the minutes (finished candles only).

    venv_octo/bin/python build_octobot_data.py
"""
import asyncio
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sealed  # noqa: E402

import octobot_backtesting.collectors.exchanges as exchanges  # noqa: E402
import octobot_commons.enums as commons_enums  # noqa: E402
import octobot_commons.symbols as symbols  # noqa: E402

TFS = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"]
OUT_DIR = os.path.join(HERE, "octobot_work", "backtesting", "data")


def minutes():
    h = sealed.history_before_oct()
    h = h[h["time"] >= pd.Timestamp("2026-06-26", tz="UTC")]  # day-aligned start
    t = pd.read_csv(os.path.join(HERE, "data", "sealed_minutes.csv"))
    df = pd.concat([h.assign(t=pd.to_datetime(h["time"], utc=True)), t.assign(t=pd.to_datetime(t["time"], utc=True))])
    df = df.set_index("t")[["open", "high", "low", "close", "volume"]].astype(float)
    return df[~df.index.duplicated()]


def candles(m, tf):
    sec = commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(tf)] * 60
    c = m.resample(f"{sec}s", origin="epoch").agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                                   "volume": "sum"}).dropna()
    c = c[c.index + pd.Timedelta(seconds=sec) <= m.index[-1] + pd.Timedelta(minutes=1)]
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    opens = ((c.index - epoch) // pd.Timedelta(seconds=1)).astype(int)
    rows = [[int(o), r.open, r.high, r.low, r.close, r.volume] for o, r in zip(opens, c.itertuples())]
    return rows, sec


class ContestCollector(exchanges.AbstractExchangeHistoryCollector):
    def _load_all_available_timeframes(self):
        pass

    async def start(self):
        m = minutes()
        await self._create_description()
        for tf in self.time_frames:
            rows, sec = candles(m, tf.value)
            await self.save_ohlcv(exchange=self.exchange_name, cryptocurrency="PEARL", symbol="PEARL/USDT",
                                  time_frame=tf, candle=rows, timestamp=[r[0] + sec for r in rows], multiple=True)
            print(tf.value, len(rows), "candles", flush=True)
        await self.stop()

    async def stop(self, **kwargs):
        await self.database.stop()
        self.finalize_database()


async def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.chdir(os.path.join(HERE, "octobot_work"))
    start = int(pd.Timestamp("2026-06-26", tz="UTC").timestamp() * 1000)
    end = int(pd.Timestamp("2026-11-21", tz="UTC").timestamp() * 1000)
    c = ContestCollector({}, "bigone", None, None, [symbols.parse_symbol("PEARL/USDT")],
                         [commons_enums.TimeFrames(tf) for tf in TFS], start_timestamp=start, end_timestamp=end)
    await c.initialize()
    await c.start()
    print("file:", c.file_path)


if __name__ == "__main__":
    asyncio.run(main())
