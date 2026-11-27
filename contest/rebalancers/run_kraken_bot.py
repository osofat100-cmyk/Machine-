#!/usr/bin/env python3
"""kraken-rebalance-bot 1.0.0 (PyPI), rebalance/bot.py unchanged: RebalanceBot.__check_balances keeps a fixed dollar
value of the coin (target_quantity) and buys/sells back to it when it leaves +-margin.

Stand-in for its exchange SDK (`kraken.spot` Market/Trade/User) backed by the price server, and for the module's
time.sleep. With use_build_in_scheduler it runs schedule.every().day.at(t) for each of `times`; the first check is
the first listed time after the start (06:00 on 1 Oct). Any exception ends the program (the CLI logs it and exits).
Config = README example scaled to the debate's 20% of $1,000: target_quantity 200 (example 500), quote_to_maintain
80 (example 200, same ratio), margin 0.035, times 06:00 and 18:00, demo false.

    venv/bin/python run_kraken_bot.py --port 8838
"""
import argparse
import math
import os
import sys
import types

import common

SRC = os.path.join(common.HERE, "downloads", "pypi_kraken-rebalance-bot", "kraken_rebalance_bot-1.0.0-py3-none-any_x")
CONFIG = {"base_currency": ["PEARL"], "quote_currency": ["USDT"], "target_quantity": [200],
          "quote_to_maintain": [80], "margin": [0.035], "times": ["06:00", "18:00"],
          "use_build_in_scheduler": True, "demo": False}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8838)
    a = ap.parse_args()
    feed = common.Feed(a.port)
    refused = []

    class Market:
        def get_ticker(self, pair):
            return {pair: {"c": [str(feed.price), "1.00000000"]}}

    class User:
        def __init__(self, key=None, secret=None):
            pass

        def get_balance(self, currency):
            v = feed.coins if currency == "PEARL" else feed.cash
            return {"currency": currency, "balance": v, "available_balance": v}

    class Trade:
        def __init__(self, key=None, secret=None):
            pass

        def truncate(self, amount, amount_type, pair):
            return f"{math.floor(float(amount) / common.STEP + 1e-9) * common.STEP:.4f}"

        def create_order(self, ordertype, side, pair, volume):
            q = float(volume)
            if q * feed.price < common.MIN_COST:
                refused.append((feed.time, side, q))
                raise Exception("EOrder:Order minimum not met")
            feed.market(side, q, f"{ordertype} {side} {volume} {pair}")
            return {"txid": [str(len(feed.decisions))]}

    sys.modules["kraken"] = types.ModuleType("kraken")
    sys.modules["kraken.spot"] = types.SimpleNamespace(Market=Market, Trade=Trade, User=User)
    sys.path.insert(0, SRC)
    import rebalance.bot as botmod
    botmod.time = types.SimpleNamespace(sleep=lambda s: None)
    bot = botmod.RebalanceBot(key="k", secret="s", config=dict(CONFIG))
    check = bot._RebalanceBot__check_balances

    slots = {int(t[:2]) * 60 + int(t[3:]) for t in CONFIG["times"]}
    start, crash, runs = feed.now, None, 0
    while True:
        if feed.now != start and feed.now % 1440 in slots:
            runs += 1
            try:
                check()
            except Exception as e:
                crash = f"{type(e).__name__}: {e} at {feed.time}"
                print("program stopped:", crash, flush=True)
                break
        if not feed.step():
            break
    acct = feed.finish()
    label = "hold $200 of PEARL +-3.5%, keep $80 USDT, checks 06:00 and 18:00"
    common.report(f"kraken-rebalance-bot [{label}] {runs} checks", acct)
    feed.save(os.path.join(common.HERE, "log_kraken_bot.csv"), acct)
    note = ("README example config scaled to 20% of $1,000; Kraken only in real life (PEARL not checked there)")
    if crash:
        note += (f"; PROGRAM STOPPED: {crash} - the sell branch reads ticker[symbol][\"c\"[0]] (= [\"c\"], a list), "
                 "so float() fails on the first sell")
    common.sealed.record("kraken-rebalance-bot 1.0.0", label, "A", len(acct["trades"]), acct["value"], "ran", note)


if __name__ == "__main__":
    main()
