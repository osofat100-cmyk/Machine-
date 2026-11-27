"""Way A: cryptobots 0.5.3 strategies (own code unchanged) on the sealed test through the price server.

Settings: the shipped config/<name>.yaml. Changes, all config: WATCHLIST -> PEARL/USDT (spot), direction -> 1
(long only; the strategies' own check refuses 0 on spot, and the test does not allow shorting).

    venv/bin/python run_cryptobots_a.py emac|grid [port]
"""
import os
import sys
import tempfile

import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import sealed  # noqa: E402
from autotrader_standin import StandInBroker  # noqa: E402

PKG = os.path.join(HERE, "venv", "lib", "python3.13", "site-packages", "cryptobots")
SYMBOL = "PEARL/USDT"


def main(name, port):
    cfg = yaml.safe_load(open(os.path.join(PKG, "config", f"{name}.yaml")))
    cfg["WATCHLIST"] = [SYMBOL]
    cfg["PARAMETERS"]["direction"] = 1
    sys.path.insert(0, os.path.join(PKG, "strategies"))
    strat_cls = getattr(__import__(cfg["MODULE"]), cfg["CLASS"])
    ok, why = strat_cls.check_parameters(cfg)
    assert ok, why
    params = dict(cfg["PARAMETERS"], granularity=cfg["INTERVAL"])
    every = int(pd.Timedelta(cfg["INTERVAL"]) / pd.Timedelta("1m"))

    h = sealed.history_before_oct()
    hist = pd.DataFrame({"Date": h["time"], "Open": h["open"], "High": h["high"], "Low": h["low"],
                         "Close": h["close"], "Volume": h["volume"]})
    broker = StandInBroker(hist, SYMBOL)
    os.chdir(tempfile.mkdtemp(prefix=f"cb_{name}_"))           # grid writes a log file in the working directory
    strat, n = None, 0
    with sealed.Sealed(port) as s:
        m = s.next()
        while m is not None:
            broker.on_minute(m)
            if strat is None:
                strat = strat_cls(params, SYMBOL, broker, logger_kwargs={})
            if (m["ts"] + 1) % every == 0:                      # a candle of the strategy's interval just closed
                broker.place(strat.generate_signal(pd.Timestamp(m["time"], tz="UTC")))
                n += 1
            req = broker.next_request()
            m = s.next(req[0], qty=req[1]) if req else s.next()
        acct = s.account
    print(f"cryptobots {name}: {n:,} decisions, {len(acct['trades'])} trades, $1,000 -> ${acct['value']:,.2f} "
          f"(holding ${acct['holding']:,.2f})")
    pd.DataFrame(acct["trades"]).to_csv(os.path.join(HERE, f"trades_cryptobots_{name}.csv"), index=False)
    return acct


if __name__ == "__main__":
    name = sys.argv[1]
    acct = main(name, int(sys.argv[2]) if len(sys.argv) > 2 else 8861)
    note = {"emac": "EMA 10/40 cross, 200 trend filter, 10% of NAV per trade, ATR*3 stop, 1h; long-only spot",
            "grid": "1% spacing, 15% stop, max investment 3000 (shipped; account has 1000), long-only spot"}[name]
    sealed.record("cryptobots 0.5.3", name, "A", len(acct["trades"]), acct["value"], "ran", note)
