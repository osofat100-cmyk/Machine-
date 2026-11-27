#!/usr/bin/env python3
"""royaurko/coinbase-trading: strategies.cppi_rebalance (CPPI), unchanged, flag='y' (its real-trade path).

Stand-ins: the `trade` module (its Coinbase v1 connection: query, exchange_rate, buy, sell, list_accounts) backed by
the price server, and the module's clock: time.sleep(interval) advances the test by interval/60 minutes.
Choices (no defaults in the program, which asks for them with input()): interval 3600 s (hourly), multiplier 3 (its
default), floor $933.33 so the first target is the debate's 20% PEARL (3 x (1000 - 933.33) = 200). Coinbase only
trades >= $1; BigONE's smallest order is 2 USDT, so smaller buys/sells are refused like an exchange error.

    python run_cppi.py --port 8833
"""
import argparse
import os
import sys
import time as real_time
import types

import common

SRC = os.path.join(common.HERE, "downloads", "royaurko_coinbase-trading")


class Done(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8833)
    ap.add_argument("--interval", type=int, default=3600)
    ap.add_argument("--multiplier", type=float, default=3.0)
    ap.add_argument("--floor", type=float, default=1000 - 200 / 3)
    a = ap.parse_args()
    feed = common.Feed(a.port)
    refused = []

    def exchange_rate(currency="USD"):
        return feed.price

    def query(account_id):
        return feed.coins

    def _order(side, amount, currency):
        qty = amount if currency == "BTC" else amount / feed.price
        if qty * feed.price < common.MIN_COST:
            refused.append((feed.time, side, qty))
            return
        feed.market(side, qty, f"{side} {amount:.4f} {currency}")

    trade = types.ModuleType("trade")
    trade.list_accounts = lambda: ["sealed-account"]
    trade.query = query
    trade.exchange_rate = exchange_rate
    trade.buy = lambda amount, log, account_id, currency="BTC", flag="n": _order("BUY", amount, currency)
    trade.sell = lambda amount, log, account_id, currency="BTC", flag="n": _order("SELL", amount, currency)
    sys.modules["trade"] = trade
    sys.path.insert(0, SRC)
    import strategies  # noqa: E402  (its __main__ block is not run)

    def sleep(seconds):
        for _ in range(max(1, int(seconds // 60))):
            if not feed.step():
                raise Done
    clock = types.SimpleNamespace(sleep=sleep, strftime=real_time.strftime,
                                  localtime=lambda *x: real_time.gmtime(feed.now * 60))
    strategies.time = clock

    crash = None
    with open(os.path.join(common.HERE, "log_cppi_tradelogs.txt"), "wb", 0) as log:
        try:
            strategies.cppi_rebalance(1000.0, a.floor, 0.0, a.interval, log, "sealed-account",
                                      a.multiplier, "USD", "y")
        except Done:
            pass
        except Exception as e:  # the program dies here; the rest of the test runs with no orders
            crash = f"{type(e).__name__}: {e} at {feed.time}"
            print("program crashed:", crash, flush=True)
    acct = feed.finish()
    label = f"CPPI multiplier {a.multiplier:g}, floor ${a.floor:,.2f}, every {a.interval // 60} min"
    common.report(f"royaurko/coinbase-trading [{label}]", acct)
    feed.save(os.path.join(common.HERE, "log_cppi.csv"), acct)
    note = ("floor/interval have no default (asked by input()); floor set so the first target is 20% PEARL; "
            f"{len(refused)} orders under 2 USDT refused")
    if crash:
        note += f"; PROGRAM CRASHED: {crash} - no trades after that"
    common.sealed.record("royaurko/coinbase-trading (CPPI)", label, "A", len(acct["trades"]), acct["value"],
                         "ran", note)


if __name__ == "__main__":
    main()
