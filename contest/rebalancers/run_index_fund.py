#!/usr/bin/env python3
"""iloveitaly/crypto-index-fund-bot, bot/ package unchanged: commands.BuyCommand.execute(user) once an hour (its
Celery task "check all accounts every hour"), with its own Binance adapter bot/supported_exchanges/binance.py.

Stand-ins: python-binance's `binance.client.Client` (account, tickers, exchange info, market orders) backed by the
price server, `coinbasepro` (only lists products; none here), and the CoinMarketCap listing it downloads (seeded into
its own cache, utils._cached_result, the way its code caches it): one coin, PEARL - the only coin its exchange
offers here, so the market-cap index is 100% PEARL. Its cache lasts for the process; each hourly run is a fresh
cache, like a new task. Pair PEARLUSD on its "Binance US"; cash is labelled USD. BigONE steps (0.0001).
User = its defaults (purchase_min 10, purchase_max 25, market buys, never sells) with livemode True (otherwise it
only sends Binance test orders).

    venv_index/bin/python run_index_fund.py --port 8843
"""
import argparse
import os
import sys
import time
import types
from decimal import Decimal

import common

SRC = os.path.join(common.HERE, "downloads", "iloveitaly_crypto-index-fund-bot")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8843)
    a = ap.parse_args()
    feed = common.Feed(a.port)
    oid = [0]

    class BinanceAPIException(Exception):
        pass

    class Client:
        SIDE_BUY, SIDE_SELL = "BUY", "SELL"
        ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT = "MARKET", "LIMIT"

        def __init__(self, *args, **kwargs):
            pass

        def get_account(self):
            return {"balances": [{"asset": "PEARL", "free": f"{feed.coins:.8f}", "locked": "0"},
                                 {"asset": "USD", "free": f"{feed.cash:.8f}", "locked": "0"}]}

        def get_all_tickers(self):
            return [{"symbol": "PEARLUSD", "price": f"{feed.price:.4f}"}]

        def get_exchange_info(self):
            return {"symbols": [{"symbol": "PEARLUSD", "baseAsset": "PEARL", "quoteAsset": "USD", "status": "TRADING",
                                 "quoteAssetPrecision": 8,
                                 "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.0001"},
                                             {"filterType": "LOT_SIZE", "stepSize": "0.0001"}]}]}

        def get_open_orders(self):
            return []

        def _market(self, side, symbol, quoteOrderQty, **kw):
            qty = float(quoteOrderQty) / feed.price
            if float(quoteOrderQty) < common.MIN_COST:
                raise BinanceAPIException("MIN_NOTIONAL")
            feed.market(side, qty, f"market {side} quoteOrderQty {quoteOrderQty}")
            oid[0] += 1
            return {"origQty": f"{qty:.8f}", "price": "0.0000", "transactTime": feed.now * 60000,
                    "timeInForce": "GTC", "side": side, "orderId": oid[0], "status": "FILLED", "symbol": symbol}

        def order_market_buy(self, **kw):
            return self._market("BUY", **kw)

        def order_market_sell(self, **kw):
            return self._market("SELL", **kw)

        def cancel_order(self, **kw):
            return {}

    binance = types.ModuleType("binance")
    binance.client = types.SimpleNamespace(Client=Client)
    binance.exceptions = types.SimpleNamespace(BinanceAPIException=BinanceAPIException)
    sys.modules.update({"binance": binance, "binance.client": binance.client, "binance.exceptions": binance.exceptions})
    sys.modules["coinbasepro"] = types.SimpleNamespace(PublicClient=lambda: types.SimpleNamespace(get_products=lambda: []))
    os.environ.setdefault("LOG_LEVEL", "ERROR")
    sys.path.insert(0, SRC)
    from bot import utils
    from bot.commands import BuyCommand
    from bot.user import User

    def cmc():
        q = {"price": Decimal(str(feed.price)), "market_cap": Decimal(str(feed.price)) * Decimal(100_000_000),
             "percent_change_7d": 0.0, "percent_change_30d": 0.0}
        return {"data": [{"symbol": "PEARL", "tags": [], "quote": {"USD": q}}]}

    user = User()
    user.binance_api_key, user.binance_secret_key, user.livemode = "stand-in", "stand-in", True
    runs, start = 0, feed.now
    while True:
        if (feed.now - start) % 60 == 0 and not feed.queue:
            runs += 1
            utils._cached_result.clear()
            utils._cached_result["coinmarketcap_data"] = cmc()
            BuyCommand.execute(user)
        if not feed.step():
            break
    acct = feed.finish()
    label = "market-cap index of what its exchange offers (= 100% PEARL), buys $10-25 per hourly run, never sells"
    common.report(f"crypto-index-fund-bot [{label}] {runs} runs", acct)
    feed.save(os.path.join(common.HERE, "log_index_fund.csv"), acct)
    common.sealed.record("iloveitaly/crypto-index-fund-bot", label, "A", len(acct["trades"]), acct["value"], "ran",
                         "its defaults (purchase 10-25 USD per run, market buys) + livemode on; Binance US only in "
                         "real life and needs a CoinMarketCap key - here the listing is a stand-in with PEARL only; "
                         "it never sells, so once the cash is spent it is buy-and-hold")


if __name__ == "__main__":
    main()
