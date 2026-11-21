"""Hummingbot 20261118 V2 controllers (repo commit 3351ada), way B: Hummingbot's own BacktestingEngineBase.

Runs
  - the three shipped backtest scripts' configs (scripts/backtest_pmm_mister.py, backtest_grid_strike.py,
    backtest_bollinger_v2.py: their build_config() is imported and called with the scripts' default arguments)
  - every other shipped controller that trades one pair, with its own default config
Config changes for this test (allowed: config): connector "binance" (spot), trading pair PEARL-USDT,
total_amount_quote 1000, leverage 1 (spot), trade_cost 0.007 (0.7% per side), resolution 1m (we only have minutes).
Grid bounds for grid_strike: the script's own rule (first close of the window +-2%, limit 1% below the start).

Data stand-in (instead of downloading from the exchange):
  - 1m candles: history_before_oct + the sealed minutes (exported through the price server).
  - every interval is built from those minutes; ONLY finished candles, stamped at their CLOSE time, so a
    1h feature merged onto a 1m row never contains minutes after that row (Hummingbot's own feeds are stamped at
    the open, which would let a backtest see up to an interval ahead).
  - trading rules: BigONE PEARL/USDT (price and amount step 0.0001, smallest order 2 USDT).
Spot stand-in: a SELL PositionExecutor is rejected unless the account already holds that much PEARL (position
holds), as a spot account without the coins rejects it. Shorts are therefore impossible.
Note: the provider only serves candles inside the backtest window, so indicators warm up on Oct candles
(engine behaviour, unchanged).

    venv_hb/bin/python run_hummingbot_v2.py
"""
import asyncio
import importlib
import os
import sys
import time
from decimal import Decimal

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "downloads", "hb_repo"))
sys.path.insert(0, os.path.join(HERE, "downloads", "hb_repo", "scripts"))
import sealed  # noqa: E402

from hummingbot.connector.trading_rule import TradingRule  # noqa: E402
from hummingbot.core.data_type.common import TradeType  # noqa: E402
from hummingbot.strategy_v2.backtesting.backtesting_engine_base import BacktestingEngineBase  # noqa: E402
from hummingbot.strategy_v2.controllers.directional_trading_controller_base import (  # noqa: E402
    DirectionalTradingControllerConfigBase,
)
from hummingbot.strategy_v2.executors.position_executor.data_types import PositionExecutorConfig  # noqa: E402

CONNECTOR, PAIR = "binance", "PEARL-USDT"
START = int(pd.Timestamp("2026-10-01", tz="UTC").timestamp())
END = int(pd.Timestamp("2026-11-21", tz="UTC").timestamp())
RULE = TradingRule(PAIR, min_price_increment=Decimal("0.0001"), min_base_amount_increment=Decimal("0.0001"),
                   min_notional_size=Decimal("2"))
# $100 per quote at the last close before 1 Oct (1.2197), fixed before any run: 100 / 1.2197 = 82 PEARL
ORDER_PEARL = 82
SECONDS = {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "2h": 7200, "4h": 14400,
           "1d": 86400}


def minutes():
    h = sealed.history_before_oct()
    t = pd.read_csv(os.path.join(HERE, "data", "sealed_minutes.csv"))
    df = pd.concat([h.assign(t=pd.to_datetime(h["time"], utc=True)),
                    t.assign(t=pd.to_datetime(t["time"], utc=True))])
    df = df.set_index("t")[["open", "high", "low", "close", "volume"]].astype(float)
    return df[~df.index.duplicated()]


MIN = minutes()


def candles(interval):
    s = SECONDS[interval]
    c = MIN.resample(f"{s}s", origin="epoch").agg({"open": "first", "high": "max", "low": "min", "close": "last",
                                                   "volume": "sum"}).dropna()
    c = c[c.index + pd.Timedelta(seconds=s) <= MIN.index[-1] + pd.Timedelta(minutes=1)]
    epoch = pd.Timestamp("1970-01-01", tz="UTC")
    out = pd.DataFrame({"timestamp": ((c.index - epoch) // pd.Timedelta(seconds=1) + s).astype(float)})
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = c[col].values
    out["quote_asset_volume"] = out["volume"] * out["close"]
    out["n_trades"] = 0.0
    out["taker_buy_base_volume"] = 0.0
    out["taker_buy_quote_volume"] = 0.0
    return out.reset_index(drop=True)


class SpotEngine(BacktestingEngineBase):
    """Spot stand-in: a sell may only open if the account already holds that much PEARL."""
    rejected = 0

    def simulate_executor(self, config, df, trade_cost):
        if isinstance(config, PositionExecutorConfig) and config.side == TradeType.SELL:
            held = sum(max(Decimal(0), ph.net_amount_base) for ph in self.active_position_holds.values())
            selling = sum(sim.config.amount for sim in self.active_executor_simulations
                          if isinstance(sim.config, PositionExecutorConfig) and sim.config.side == TradeType.SELL)
            if config.amount > held - selling:
                self.rejected += 1
                return None
        return super().simulate_executor(config, df, trade_cost)


async def run(name, config):
    engine = SpotEngine()
    p = engine.backtesting_data_provider
    p.trading_rules[CONNECTOR] = {PAIR: RULE}
    for interval in SECONDS:
        p.candles_feeds[f"{CONNECTOR}_{PAIR}_{interval}"] = candles(interval)
    t0 = time.time()
    res = await engine.run_backtesting(config, START, END, backtesting_resolution="1m", trade_cost=0.007)
    r = res["results"]
    shorts = max([x["short_amount"] for x in res["position_held_timeseries"]] or [0.0])
    filled = [e for e in res["executors"] if e.filled_amount_quote > 0]
    raw = 1000 + float(r["net_pnl_quote"])
    end = max(0.0, raw)  # the engine keeps sizing from the fixed 1,000 budget; below 0 = account wiped out
    note = (f"engine fills; {len(res['executors'])} executors, {engine.rejected} sells rejected (no PEARL held, spot); "
            f"close types {dict(r['close_types'])}")
    if raw < 0:
        note += f"; engine total {raw:,.2f} (losses larger than the account: wiped out, recorded as 0)"
    if shorts > 0:
        note += f"; position went short up to {shorts:.2f} USDT"
    print(f"{name:<34} filled executors {len(filled):>5}  end ${end:,.2f}  ({time.time() - t0:.0f}s)  {note}",
          flush=True)
    return len(filled), end, note


def configs():
    import backtest_bollinger_v2 as bb2
    import backtest_grid_strike as gs
    import backtest_pmm_mister as pm
    ref = float(MIN.loc[pd.Timestamp("2026-10-01", tz="UTC"), "close"])
    half = 0.04 / 2
    start, end = round(ref * (1 - half), 6), round(ref * (1 + half), 6)
    yield ("pmm_mister (backtest script config)", lambda: pm.build_config(CONNECTOR, PAIR, 1000))
    yield ("grid_strike (backtest script config)", lambda: gs.build_config(
        CONNECTOR, PAIR, 1000, start, end, round(start * 0.99, 6), "BUY", 0.001, 2, 1))
    yield ("bollinger_v2 (backtest script config)", lambda: bb2.build_config(
        CONNECTOR, PAIR, 1000, *BB2_ARGS))
    for module, name in (("market_making", "pmm_simple"), ("market_making", "pmm_dynamic"),
                         ("market_making", "dman_maker_v2"), ("generic", "pmm_v1"),
                         ("directional_trading", "bollinger_v1"), ("directional_trading", "supertrend_v1"),
                         ("directional_trading", "macd_bb_v1"), ("directional_trading", "dman_v3"),
                         ("directional_trading", "bollingrid")):
        def make(module=module, name=name):
            data = {"id": f"contest_{name}", "controller_name": name, "controller_type": module}
            cls = BacktestingEngineBase.get_controller_config_instance_from_dict(dict(data), "controllers").__class__
            # pass the controller's own defaults in explicitly so its validators parse them
            # (a blank amounts_pct = "distribute equally", as its prompt says)
            for k, f in cls.model_fields.items():
                if k in data or f.is_required():
                    continue
                if f.default is None and k.endswith("amounts_pct"):
                    data[k] = ""
                elif f.default is not None and type(f.default).__name__ not in ("PydanticUndefinedType",):
                    data[k] = f.default
            data.update({"connector_name": CONNECTOR, "trading_pair": PAIR, "total_amount_quote": 1000})
            if "leverage" in cls.model_fields:
                data["leverage"] = 1
            if "candles_connector" in cls.model_fields:
                data.update({"candles_connector": CONNECTOR, "candles_trading_pair": PAIR})
            if name == "pmm_v1":
                data["order_amount"] = ORDER_PEARL  # shipped 1 is BTC-sized; same $100 rule as simple_pmm
            return BacktestingEngineBase.get_controller_config_instance_from_dict(data, "controllers")
        yield (f"{name} (default config)", make)


# backtest_bollinger_v2.py argparse defaults (lines 124-133), leverage 20 -> 1 for spot
BB2_ARGS = ("3m", 100, 2.0, 0.0, 1.0, 1, 0.03, 0.02, 2700, 300)


async def main():
    for name, make in configs():
        try:
            trades, end, note = await run(name, make())
            sealed.record("Hummingbot 20261118 V2 controller", name, "B", trades, end, "ran", note)
        except Exception as e:
            err = f"{type(e).__name__}: {e}".replace("\n", " ")[:300]
            print(f"{name:<34} ERROR {err}", flush=True)
            sealed.record("Hummingbot 20261118 V2 controller", name, "B", "", None, "does not run as shipped", err)


if __name__ == "__main__":
    asyncio.run(main())
