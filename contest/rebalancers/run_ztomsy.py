#!/usr/bin/env python3
"""ztomsy/rebalancer (build 190710), unchanged, with its shipped _settings.py values except the white list.

Its Runner.run_balancer is an endless wall-clock loop with a curses screen, so this program builds the Runner the
way Runner.__init__ does (minus the loop, the screen and InfluxDB) and then runs the loop body - the same calls in
the same order - once a minute (LOOP_INTERVAL is 40-60 s). Its own RestClient methods run unchanged; only the ccxt
object under them is a stand-in backed by the price server: limit orders rest and lock their funds like on an
exchange, and fill when a minute's low/high touches them (at the next minute's close).
Settings: PORTFOLIO_WHITE_LIST ['PEARL', 'USDT'] (shipped list has no PEARL), everything else as shipped:
base USDT, WEIGHT_BOUNDS (0, 0.95), TARGET_RETURN 0.05, REBALANCING_PRECISION 0.01, TIME_FRAMES ['1h'],
DRY_RUN True in the file means no orders at all, so it is run as DRY_RUN False.
PyPortfolioOpt 0.5.5 (its requirement is >=0.3.1; 1.x removed the gamma= argument it passes).

    venv_ztomsy/bin/python run_ztomsy.py --port 8837
"""
import argparse
import logging
import os
import sys
import time
import types

import common

SRC = os.path.join(common.HERE, "downloads", "ztomsy_rebalancer")
PAIR = "PEARL/USDT"


class StubCCXT:
    """The ccxt.binance object RestClient talks to."""
    id = "binance"

    def __init__(self, feed):
        self.feed, self.orders = feed, {}

    def describe(self):
        return {"id": "binance"}

    def fetch_bids_asks(self):
        p = self.feed.price
        return {PAIR: {"symbol": PAIR, "ask": p, "bid": p}}

    def fetch_ohlcv(self, symbol, timeframe="1h", limit=200):
        tf = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}[timeframe]
        c = self.feed.candles(tf, limit)
        return [[int(t) * 60000, o, h, l, cl, v] for t, o, h, l, cl, v in
                zip(c["ts"], c["open"], c["high"], c["low"], c["close"], c["volume"])]

    def _locked(self):
        cash = sum(o["amount"] * o["price"] for i, o in self.orders.items()
                   if o["side"] == "BUY" and i in self.feed.limits)
        coins = sum(o["amount"] for i, o in self.orders.items() if o["side"] == "SELL" and i in self.feed.limits)
        return cash, coins

    def fetch_balance(self):
        lc, lq = self._locked()
        f = self.feed
        return {"info": {"balances": [{"asset": "PEARL", "free": str(f.coins - lq), "locked": str(lq)},
                                      {"asset": "USDT", "free": str(f.cash - lc), "locked": str(lc)}]}}

    def create_order(self, symbol, type, side, amount, price=None):
        side = side.upper()
        lc, lq = self._locked()
        if side == "BUY" and amount * price > self.feed.cash - lc + 1e-9:
            raise Exception("InsufficientFunds")
        if side == "SELL" and amount > self.feed.coins - lq + 1e-9:
            raise Exception("InsufficientFunds")
        lid = self.feed.limit(side, amount, price, f"{type} {side} {amount} @ {price}")
        self.orders[lid] = {"side": side, "amount": amount, "price": price}
        return {"id": lid, "symbol": symbol, "status": "open", "side": side, "amount": amount, "price": price,
                "filled": 0}

    def fetch_order(self, oid, symbol):
        o = self.orders[oid]
        done = oid not in self.feed.limits
        return {"id": oid, "symbol": symbol, "status": "closed" if done else "open", "side": o["side"],
                "amount": o["amount"], "price": o["price"], "filled": o["amount"] if done else 0}

    def cancel_order(self, oid, symbol=None, params=None):
        self.feed.cancel(oid)


class UI:
    def __init__(self):
        self.index_data, self.portfolio_data, self.spark_data = [], [], {}

    def print_ui(self, *a, **k): pass
    def push_data(self, *a, **k): pass
    def reload_ui(self, *a, **k): pass
    def teardown(self, *a, **k): return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8837)
    a = ap.parse_args()
    sys.modules["influxdb"] = types.SimpleNamespace(InfluxDBClient=object)
    sys.path.insert(0, SRC)
    from binance.restclient import RestClient
    from payload.runner import Runner
    from payload.portfolioOpt import PortfolioOpt
    from yat.assetlist.StaticAssetList import StaticAssetList

    feed = common.Feed(a.port)
    logger = logging.getLogger("Rebalancer")
    logging.basicConfig(level=logging.ERROR)

    ex = RestClient.__new__(RestClient)
    ex.logger, ex.dry_run, ex.exchange_name, ex.marketonly = logger, False, "binance", False
    ex.exchange = StubCCXT(feed)
    ex.possible_timeframes = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
    ex.markets = {PAIR: {"base": "PEARL", "quote": "USDT", "active": True,
                         "limits": {"amount": {"min": None, "max": None}, "cost": {"min": common.MIN_COST, "max": None},
                                    "price": {"min": None, "max": None}}}}
    ex.all_tickers, ex.confirm_trade_collector, ex._order_index, ex._ex_index = None, [], 0, 0
    ex.order_history, ex._candlesticks, ex._trades, ex.balances = {}, {}, {}, []

    r = Runner.__new__(Runner)
    r.logger, r.file_watcher, r.last_fetch_time = logger, None, int(time.time())
    r.dry_run, r.loop_interval, r.market_only = False, (40, 60), False
    r.ui, r.db, r.data_provider_list, r.exchange = UI(), None, ["binance"], ex
    r.portfolio_base_asset, r.portfolio_weight_bounds = "USDT", (0.0, 0.95)
    r.portfolio_manager = StaticAssetList(logger, ex, ["PEARL", "USDT"], ["USDSB"], r.portfolio_weight_bounds)
    r.portfolio_manager.refresh_assetlist()
    r.portfolio_base_markets = r.portfolio_manager.build_portfolio_assets_markets(r.portfolio_base_asset)
    r.portfolio_assets, r.portfolio = r.portfolio_manager.whitelist, r.portfolio_manager.portfolio
    r.rebalancing_precision, r.portfolio_base_amount = 0.01, 0
    r.portfolio_target_return, r.portfolio_target_risk, r.portfolio_time_frames = 0.05, None, ["1h"]
    r.portfolio_ohlcv, r.portfolio_current_weights, r.portfolio_recommended_weights = {}, {}, {}
    r.portfolio_difference, r.quote_collector, r.run_step, r.balances = {}, [], 0, {}
    ex.process_tickers()

    crash, runs, weights = None, 0, []
    while crash is None:
        try:
            # body of Runner.run_balancer, in its order
            r.exchange.fetch_processed_orders()
            r.exchange.cancel_processed_orders()
            r._update_db_with_succeed_trades(r.exchange.order_history)
            r.exchange.order_history.clear()
            r.exchange.process_tickers()
            r.portfolio_ohlcv.clear()
            r.portfolio_ohlcv = r.exchange.process_ohlcv(markets=r.portfolio_base_markets,
                                                         time_frames=r.portfolio_time_frames, limit=200)
            r.exchange.fetch_balances()
            r.balances = {x: y for x, y in r.exchange.balances.items() if x in r.portfolio_assets}
            r._count_portfolio_base_amount()
            r._update_portfolio_current_weights()
            r._update_index_data()
            r._update_pctchange_sparkline()
            r._update_portfolio_data()
            r.portfolio_recommended_weights, p_list = PortfolioOpt().generate_report(
                ohlcv_data=r.portfolio_ohlcv, time_frames=r.portfolio_time_frames,
                weight_bounds=r.portfolio_weight_bounds, base_asset=r.portfolio_base_asset,
                exp_return_periods=200, risk_model_periods=200,
                target_return=r.portfolio_target_return, target_risk=r.portfolio_target_risk)
            r._compare_weights(r.portfolio_current_weights, r.portfolio_recommended_weights)
            r._update_portfolio_data()
            r._generate_quotes()
            if len(r.quote_collector) != 0:
                r._proceed_orders()
            r.run_step += 1
            runs += 1
            if runs % 1440 == 1:
                weights.append((feed.time, dict(r.portfolio_recommended_weights)))
        except Exception as e:   # run.py logs "Stop main loop" and exits
            crash = f"{type(e).__name__}: {e} at {feed.time}"
            print("program stopped:", crash, flush=True)
            break
        if not feed.step():
            break
    acct = feed.finish()
    label = "efficient_return(0.05) on 200 x 1h, bounds 0-0.95, precision 0.01, every minute"
    common.report(f"ztomsy/rebalancer [{label}] {runs} runs", acct)
    print("weights (daily samples):", weights[:3], weights[-2:])
    feed.save(os.path.join(common.HERE, "log_ztomsy.csv"), acct)
    note = ("shipped settings, white list PEARL+USDT, DRY_RUN off; PyPortfolioOpt 0.5.5. BUG: every order fails - "
            "RestClient.check_order_limits adds 'cost' to the order dict and create_order passes it to "
            "ccxt create_order(**order_dict), which raises TypeError (checked with real ccxt 4.5.93); "
            "also cancel_processed_orders never cancels (only re-fetches)")
    if crash:
        note += f"; PROGRAM STOPPED: {crash}"
    common.sealed.record("ztomsy/rebalancer", label, "A", len(acct["trades"]), acct["value"], "ran", note)


if __name__ == "__main__":
    main()
