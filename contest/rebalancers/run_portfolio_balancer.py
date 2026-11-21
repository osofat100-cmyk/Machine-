#!/usr/bin/env python3
"""portfolio-balancer 0.1.18 (PyPI), main.py unchanged: PortfolioBalancer.balance_portfolio() keeps a "virtual
portfolio" ledger in ~/.portfolio_balancer/portfolio.csv and trades the ledger's difference to balance_ratio.

It is a one-shot command (meant for cron); here a fresh PortfolioBalancer runs every hour, as a cron line would.
HOME points at a sandbox folder holding its config.toml and portfolio.csv. Stand-in `ccxt` module (its exchange
connection): getattr(ccxt, 'bigone') gives an object backed by the price server.
No defaults exist for balance_ratio or trigger_ratio: balance_ratio 0.2 (debate), trigger_ratio 0.05 (the usual
5%). The ledger has to be written by the user before the first run:
  --start cash   ledger = what the account really holds on 1 Oct: 0 PEARL, 1000 USDT
  --start split  the user first buys 20% PEARL by hand on 1 Oct 00:00, ledger = that split

    venv/bin/python run_portfolio_balancer.py --start cash --port 8839
"""
import argparse
import math
import os
import shutil
import sys
import types

import common

SRC = os.path.join(common.HERE, "downloads", "pypi_portfolio-balancer", "portfolio_balancer-0.1.18-py3-none-any_x")
CONFIG = """[portfolio]
exchange = "bigone"
currency1 = "PEARL"
currency2 = "USDT"
base_currency = "USDT"

[bigone]
api_key = ""
api_secret = ""
balance_ratio = 0.2
trigger_ratio = 0.05
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", choices=["cash", "split"], required=True)
    ap.add_argument("--port", type=int, default=8839)
    a = ap.parse_args()
    home = os.path.join(common.HERE, f"home_portfolio_balancer_{a.start}")
    shutil.rmtree(home, ignore_errors=True)
    os.makedirs(os.path.join(home, ".portfolio_balancer"))
    os.environ["HOME"] = home
    feed = common.Feed(a.port)
    if a.start == "cash":
        cur1, cur2 = 0.0, 1000.0
    else:
        cur1 = math.floor(200 / (feed.price * 1.007) / common.STEP) * common.STEP
        feed.market("BUY", cur1, "user's own first buy of 20% (not the program)")
        feed.step()
        cur1, cur2 = feed.coins, feed.cash
    with open(os.path.join(home, ".portfolio_balancer", "config.toml"), "w") as f:
        f.write(CONFIG)
    with open(os.path.join(home, ".portfolio_balancer", "portfolio.csv"), "w") as f:
        f.write("date,currency1,currency2,base_currency,details,fx_rate,portfolio_value,performance\n")
        f.write(f"20261001000000,{cur1},{cur2},USDT,start,{feed.price},{cur1 * feed.price + cur2},0\n")

    class InsufficientFunds(Exception):
        pass

    class StandIn:
        def __init__(self, params):
            pass

        def fetch_ticker(self, symbol):
            return {"symbol": symbol, "close": feed.price}

        def _order(self, side, symbol, amount):
            q = math.floor(float(amount) / common.STEP + 1e-9) * common.STEP
            if q * feed.price < common.MIN_COST:
                raise InsufficientFunds("below the 2 USDT minimum")
            feed.market(side, q, f"market {side} {amount} {symbol}")
            return {"symbol": symbol, "side": side, "amount": q}

        def create_market_buy_order(self, symbol, amount):
            return self._order("BUY", symbol, amount)

        def create_market_sell_order(self, symbol, amount):
            return self._order("SELL", symbol, amount)

    sys.modules["ccxt"] = types.SimpleNamespace(bigone=StandIn, InsufficientFunds=InsufficientFunds)
    sys.path.insert(0, SRC)
    import importlib.metadata as md
    md_version = md.version
    md.version = lambda name: "0.1.18" if name == "portfolio-balancer" else md_version(name)
    from portfolio_balancer.main import PortfolioBalancer
    args = types.SimpleNamespace(verbose=False, show_history=False, check=False, dry_run=False,
                                 report_transaction=False, exchange="binance", portfolio="portfolio.csv")
    runs, start = 0, feed.now
    while True:
        if (feed.now - start) % 60 == 0 and not feed.queue:
            runs += 1
            PortfolioBalancer(args).exec()
        if not feed.step():
            break
    acct = feed.finish()
    label = f"balance_ratio 0.2, trigger_ratio 0.05, hourly, ledger start = {a.start}"
    common.report(f"portfolio-balancer [{label}] {runs} runs", acct)
    feed.save(os.path.join(common.HERE, f"log_portfolio_balancer_{a.start}.csv"), acct)
    note = ("ledger only (never reads the account; after a trade it books exactly the target, no fees); its trigger "
            "abs_diff = |value gap| x coins held / total value mixes units, so with 0 coins it can never trigger")
    if a.start == "split":
        note += "; the first 20% buy was done by hand (counted in fills), the program only rebalanced after"
    common.sealed.record("portfolio-balancer 0.1.18", label, "A", len(acct["trades"]), acct["value"], "ran", note)


if __name__ == "__main__":
    main()
