#!/usr/bin/env python3
"""koyadovic/binance-rebalancing, core.domain.services.rebalance unchanged (with its activity logging module), run
like its README's crontab line: `0 * * * * bin/rebalance.sh` = `python rebalance.py --yes` once an hour.

Its README says another exchange is added by implementing AbstractExchange; here BinanceExchange itself is
subclassed and only its client calls are replaced (balance, 5-minute average price, market orders by quote amount,
exchange info), so its get_exchange_valid_operations / execute_operations / exchange_pair_exist run unchanged.
Exchange info for PEARLUSDT uses BigONE's rules: tick 0.0001, smallest order 2 USDT. `binance` (python-binance)
is a stand-in module: no client is ever made. Market orders fill at the next minute's close.
Settings = README example "Only bitcoin but leaving 50% in fiat", with PEARL and the debate's 20%:
crypto_assets ['PEARL'], fiat_asset 'USDT', fiat_decimals 2, fiat_untouched 1 * 5, exposure 0.2, EqualDistribution.

    venv/bin/python run_koyadovic.py --port 8842
"""
import argparse
import contextlib
import io
import os
import sys
import types

import common

SRC = os.path.join(common.HERE, "downloads", "koyadovic_binance-rebalancing")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8842)
    a = ap.parse_args()
    box = os.path.join(common.HERE, "home_koyadovic")
    os.makedirs(box, exist_ok=True)
    sys.modules["binance"] = types.SimpleNamespace(Client=type("Client", (), {"KLINE_INTERVAL_1HOUR": "1h"}))
    sys.path.insert(0, SRC)
    from core.domain import services
    from core.domain.distribution import EqualDistribution
    from core.domain.interfaces import AbstractExchange, AbstractUserInterface, AbstractDebugPlatform
    from core.infrastructure.exchange_binance import BinanceExchange
    from core.infrastructure.debug_platform_logging import LoggingDebugPlatform
    from core.infrastructure.user_interface_text import TextUserInterface
    from shared.domain.dependencies import dependency_dispatcher
    os.chdir(box)
    from activity.bootstrap import init_activity_module

    feed = common.Feed(a.port)

    class SealedBinance(BinanceExchange):
        def get_asset_balance(self, asset):
            return feed.coins if asset == "PEARL" else feed.cash

        def get_asset_price(self, base_asset, quote_asset, **kwargs):
            c = feed.C[-5:]
            return sum(c) / len(c)

        def place_buy_order(self, base_asset, quote_asset, quote_amount, **kwargs):
            feed.market("BUY", float(f"{quote_amount:.8f}") / feed.price, f"market buy quoteOrderQty {quote_amount:.8f}")

        def place_sell_order(self, base_asset, quote_asset, quote_amount, **kwargs):
            feed.market("SELL", float(f"{quote_amount:.8f}") / feed.price, f"market sell quoteOrderQty {quote_amount:.8f}")

        def _get_exchange_info(self):
            return {"PEARLUSDT": {"symbol": "PEARLUSDT", "filters": [
                {"filterType": "PRICE_FILTER", "minPrice": "0.0001", "maxPrice": "100000", "tickSize": "0.0001"},
                {"filterType": "MIN_NOTIONAL", "minNotional": str(common.MIN_COST), "applyToMarket": True}]}}

    dependency_dispatcher.register_implementation(AbstractExchange, SealedBinance())
    dependency_dispatcher.register_implementation(AbstractDebugPlatform, LoggingDebugPlatform())
    dependency_dispatcher.register_implementation(AbstractUserInterface, TextUserInterface())
    init_activity_module()

    runs = 0
    while True:
        if feed.now % 60 == 0 and not feed.queue:
            runs += 1
            with contextlib.redirect_stdout(io.StringIO()):
                services.rebalance(crypto_assets=["PEARL"], fiat_asset="USDT", fiat_decimals=2, fiat_untouched=5.0,
                                   exposure=0.2, with_confirmation=False,
                                   distribution=EqualDistribution(crypto_assets=["PEARL"]))
        if not feed.step():
            break
    acct = feed.finish()
    label = "PEARL x exposure 0.2 (20%), fiat USDT, fiat_untouched 5, hourly, trades to exact target"
    common.report(f"koyadovic/binance-rebalancing [{label}] {runs} runs", acct)
    feed.save(os.path.join(common.HERE, "log_koyadovic.csv"), acct)
    common.sealed.record("koyadovic/binance-rebalancing", label, "A", len(acct["trades"]), acct["value"], "ran",
                         "README example settings with PEARL and exposure 0.2; README crontab hourly; no drift "
                         "threshold - it trades back to target every hour when the gap is at least the 2 USDT "
                         "minimum; BinanceExchange subclassed with only client calls replaced (README's extension "
                         "point); Binance only in real life")


if __name__ == "__main__":
    main()
