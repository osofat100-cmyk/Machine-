"""Way B: cryptobots 0.5.3 strategies in their own engine (AutoTrader 1.1.2 backtest, virtual broker).

The strategies need AutoTrader's broker (orders with attached stop-loss / take-profit, order modify), so they cannot
run outside it. Data: contest/other/data/PEARL_USDT_{1m,1h}.csv = 25 Jun-30 Sep history + the sealed minutes walked
from the price server with sealed.export_minutes. Backtest 1 Oct - 20 Nov, $1,000, commission 0.7% per side.

    venv/bin/python run_cryptobots.py emac|grid
"""
import os
import shutil
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))
import sealed  # noqa: E402
from autotrader import AutoTrader  # noqa: E402

PKG = os.path.join(HERE, "venv", "lib", "python3.13", "site-packages", "cryptobots")


def run(name, symbol="PEARL/USDT"):
    cfg = yaml.safe_load(open(os.path.join(PKG, "config", f"{name}.yaml")))
    # Only change: the coin. Spot PEARL/USDT allows long-only (the strategies' own check refuses direction 0 on spot).
    cfg["WATCHLIST"] = [symbol]
    cfg["PARAMETERS"]["direction"] = 1
    sys.path.insert(0, os.path.join(PKG, "strategies"))
    mod = __import__(cfg["MODULE"])
    strat = getattr(mod, cfg["CLASS"])
    ok, why = strat.check_parameters(cfg)
    if not ok:
        return None, f"own check refused config: {why}"
    gran = cfg["INTERVAL"]
    datafile = "PEARL_USDT_1h.csv" if gran == "1h" else "PEARL_USDT_1m.csv"
    home = tempfile.mkdtemp(prefix=f"at_{name}_")
    os.makedirs(os.path.join(home, "price_data"))
    shutil.copy(os.path.join(HERE, "data", datafile), os.path.join(home, "price_data", datafile))
    os.chdir(home)
    at = AutoTrader()
    at.configure(verbosity=int(os.environ.get("VERB", "1")), show_plot=False, home_dir=home, broker="virtual")
    at.add_strategy(config_dict=cfg, strategy=strat)
    at.add_data({symbol: datafile}, data_directory=os.path.join(home, "price_data"))
    at.virtual_account_config(initial_balance=1000, commission=0.7, commission_scheme="percentage", leverage=1)
    at.backtest(start=os.environ.get("START", "11/9/2026"), end="21/11/2026", localize_to_utc=True, warmup_period=os.environ.get("WARMUP", "20d"))
    at.run()
    broker = at._broker if not isinstance(at._broker, dict) else list(at._broker.values())[0]
    nav = float(broker.get_NAV())
    fills = broker.get_trades()
    return (nav, len(fills)), None


if __name__ == "__main__":
    name = sys.argv[1]
    res, err = run(name, *(sys.argv[2:3]))
    print(name, res, err)
