"""OctoBot 2.1.1 + official tentacles 2.1.1, way B: OctoBot's own backtesting engine (IndependentBacktesting).

Data: octobot_work/backtesting/data/pearl_contest.data (build_octobot_data.py: history before 1 Oct for warm-up +
sealed minutes exported through the price server). Backtest window 1 Oct 00:00 - 21 Nov 00:00.

Every shipped profile that trades on its own (no external signal, AI key or second exchange) is copied to
user/profiles/contest_<id> with config changes only:
  pair PEARL/USDT, exchange bigone, simulator portfolio 1,000 USDT and 0 PEARL, maker and taker fee 0.7%.
Coin-specific settings (rule fixed before any run, P = 1.2197 = last close before 1 Oct):
  - grid_trading / trailing_grid_trading: the shipped values are BTC dollar amounts; use the vendor's own percent
    defaults from the staggered_orders profile (spread 6%, increment 3%) at P; order counts and flags as shipped.
  - staggered_orders_trading: spread/increment % as shipped; the shipped BTC range is 2x wide (30,000-60,000);
    the same 2x range centred on P: P/sqrt(2) .. P*sqrt(2).
  - everything else as shipped.

    venv_octo/bin/python run_octobot.py [profile ...]
"""
import asyncio
import copy
import json
import math
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "octobot_work")
sys.path.insert(0, os.path.dirname(HERE))
import sealed  # noqa: E402

PROFILES = ["simple_dca", "smart_dca", "daily_trading", "dip_analyser", "index_trading", "grid_trading",
            "trailing_grid_trading", "staggered_orders_trading", "market_making"]
P = 1.2197
START = 1790812800  # 2026-10-01 00:00 UTC
END = 1795219200    # 2026-11-21 00:00 UTC
DATA_FILE = "pearl_contest.data"
EXTRA_NOTES = {"simple_dca": "OctoBot logs: Time based trigger is not supporting backtesting for now (so only the first buy happens)"}


def make_profile(pid):
    src = os.path.join(WORK, "user", "profiles", pid)
    dst = os.path.join(WORK, "user", "profiles", f"contest_{pid}")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    path = os.path.join(dst, "profile.json")
    prof = json.load(open(path))
    c = prof["config"]
    c["crypto-currencies"] = {"PEARL": {"enabled": True, "pairs": ["PEARL/USDT"]}}
    c["exchanges"] = {"bigone": {"enabled": True, "exchange-type": "spot"}}
    c["trader-simulator"]["starting-portfolio"] = {"USDT": 1000, "PEARL": 0}
    c["trader-simulator"]["fees"] = {"maker": 0.7, "taker": 0.7}
    c["trading"]["reference-market"] = "USDT"
    prof["profile"].update({"id": f"contest_{pid}", "name": f"contest {pid}", "read_only": False})
    json.dump(prof, open(path, "w"), indent=4)
    spec = os.path.join(dst, "specific_config")
    for fname in os.listdir(spec):
        fpath = os.path.join(spec, fname)
        d = json.load(open(fpath))
        if "pair_settings" in d:
            base = copy.deepcopy(d["pair_settings"][0])
            base["pair"] = "PEARL/USDT"
            if fname == "GridTradingMode.json":
                base["flat_spread"] = round(P * 0.06, 6)
                base["flat_increment"] = round(P * 0.03, 6)
            if fname == "StaggeredOrdersTradingMode.json":
                base["lower_bound"] = round(P / math.sqrt(2), 6)
                base["upper_bound"] = round(P * math.sqrt(2), 6)
            d["pair_settings"] = [base]
            json.dump(d, open(fpath, "w"), indent=4)
    return f"contest_{pid}"


async def run(pid):
    import octobot.api.backtesting as bt_api
    import octobot.configuration_manager as configuration_manager
    import octobot.constants as constants
    import octobot_commons.configuration as configuration
    import octobot_commons.constants as commons_constants
    import octobot_tentacles_manager.api as tentacles_api

    profile_id = make_profile(pid)
    config = configuration.Configuration(configuration.get_user_config(), commons_constants.USER_PROFILES_FOLDER,
                                         constants.CONFIG_FILE_SCHEMA, constants.PROFILE_FILE_SCHEMA)
    if config.is_config_file_empty_or_missing():
        configuration_manager.init_config()
    config.read(should_raise=False, fill_missing_fields=True)
    config.select_profile(profile_id)
    tentacles_setup = tentacles_api.get_tentacles_setup_config(config.get_tentacles_config_path())
    ib = bt_api.create_independent_backtesting(
        config.config, tentacles_setup, [DATA_FILE], os.path.join("backtesting", "data"),
        start_timestamp=START, end_timestamp=END, enable_logs=False, stop_when_finished=False,
        enforce_total_databases_max_size_after_run=False, enable_storage=False)
    t0 = time.time()
    await bt_api.initialize_and_run_independent_backtesting(ib, log_errors=True)
    await bt_api.join_independent_backtesting(ib, timeout=None)
    report = await bt_api.get_independent_backtesting_report(ib)
    import octobot_trading.api as trading_api
    trades = []
    for eid in bt_api.get_independent_backtesting_exchange_manager_ids(ib):
        em = trading_api.get_exchange_manager_from_exchange_id(eid)
        trades += [(t.executed_time, t.side.value, float(t.executed_quantity), float(t.executed_price))
                   for t in trading_api.get_trade_history(em)]
    report["contest_trades"] = sorted(trades)
    await bt_api.stop_independent_backtesting(ib, memory_check=False)
    return report, time.time() - t0


def summarize(report):
    bot = report.get("bot_report", report)
    end = bot.get("end_portfolio") or {}
    trades = bot.get("trades", None)
    return bot, end, trades


async def main():
    os.chdir(WORK)
    sys.path.append(WORK)
    import tentacles  # noqa: F401  (registers the installed trading modes / evaluators, as OctoBot's start does)
    only = sys.argv[1:] or PROFILES
    for pid in only:
        try:
            report, sec = await run(pid)
            with open(os.path.join(HERE, f"octobot_{pid}_report.json"), "w") as f:
                json.dump(report, f, indent=2, default=str)
            bot = report["bot_report"]
            prof = float(list(bot["profitability"].values())[0])
            trades = report["contest_trades"]
            end = 1000 * (1 + prof / 100)
            first = time.strftime("%Y-%m-%d %H:%M", time.gmtime(trades[0][0])) if trades else "-"
            note = (f"OctoBot engine; end portfolio {json.dumps(bot['end_portfolio'])}; first trade {first} UTC; "
                    f"errors {report.get('errors_count')}")
            print(f"{pid:<26} trades {len(trades):>5}  end ${end:,.2f}  ({sec:.0f}s)  {note}", flush=True)
            assert not trades or trades[0][0] >= START, "trade before the test window"
            sealed.record("OctoBot 2.1.1 (official tentacles)", f"{pid} profile", "B", len(trades), end, "ran",
                          note + (f"; {EXTRA_NOTES[pid]}" if pid in EXTRA_NOTES else ""))
        except Exception as e:
            import traceback
            traceback.print_exc()
            err = f"{type(e).__name__}: {e}".replace("\n", " ")[:300]
            print(pid, "ERROR", err, flush=True)
            sealed.record("OctoBot 2.1.1 (official tentacles)", f"{pid} profile", "B", "", None,
                          "does not run as shipped", err)


if __name__ == "__main__":
    asyncio.run(main())
