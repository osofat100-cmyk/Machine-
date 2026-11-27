"""Way A stand-in for an AutoTrader broker, for cryptobots strategies (and any AutoTrader Strategy).

AutoTrader's own backtest engine hands strategies the LAST candles of the whole data file at every step (look-ahead),
so it cannot be used. This stand-in gives the strategy only candles up to now, built from the history before 1 Oct plus
the minutes the price server has handed out so far.

Order handling (what the exchange would do; every fill goes through the price server at the next minute's close):
  market order -> sent with the next request
  limit order  -> waits; when a minute's low (buy) / high (sell) reaches the limit, sent with the next request
  modify       -> moves the related waiting order to the new price/size
  stop_loss / take_profit on an order -> after it fills, a waiting sell (long) at that price, like a broker's
                 attached stop / take-profit; one cancels the other
"""
import itertools
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd

AGG = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}


class StandInBroker:
    def __init__(self, history, instrument, price_step=1e-4, amount_step=1e-4):
        self.instrument = instrument
        self.base = instrument.split("/")[0]
        self.api = SimpleNamespace(markets={instrument: {
            "base": self.base, "type": "swap" if ":" in instrument else "spot",
            "precision": {"price": price_step, "amount": amount_step}}})
        self.rows = history.to_dict("records")   # Date, Open, High, Low, Close, Volume (minutes)
        self.cash, self.coins, self.close = 1000.0, 0.0, None
        self.waiting = {}                          # id -> dict(order, kind, side, price, size)
        self.ids = itertools.count(1)
        self.to_send = []                          # (side, qty, children) for the next request
        self._cache = {}

    # ---------- what the strategy calls ----------
    def get_candles(self, instrument, granularity="1m", count=500, **kw):
        key = (granularity, len(self.rows))
        if key not in self._cache:
            df = pd.DataFrame(self.rows[-(count + 2) * max(1, int(pd.Timedelta(granularity) / pd.Timedelta("1m"))):])
            df = df.set_index("Date")
            if granularity != "1m":
                df = df.resample(granularity).agg(AGG).dropna()
                last_full = self.rows[-1]["Date"] + pd.Timedelta("1m")
                df = df[df.index + pd.Timedelta(granularity) <= last_full]   # completed candles only
            self._cache = {key: df}
        return self._cache[key].iloc[-count:]

    def get_NAV(self, *a, **k):
        return self.cash + self.coins * self.close

    def get_balance(self, *a, instrument=None, **k):
        if instrument in (None, "USDT"):
            return self.cash
        return self.coins

    def get_positions(self, instrument=None, **k):
        if self.coins <= 0:
            return {}
        return {self.instrument: SimpleNamespace(net_position=self.coins, instrument=self.instrument)}

    def get_orderbook(self, instrument=None, **k):
        return SimpleNamespace(midprice=self.close)

    def get_orders(self, instrument=None, **k):
        return {i: w["order"] for i, w in self.waiting.items() if w["kind"] == "limit"}

    def place(self, orders):
        if orders is None:
            return
        if not isinstance(orders, (list, tuple)):
            orders = [orders]
        for o in orders:
            if o is None or o.direction is None:
                continue
            kind = (o.order_type or "market").lower()
            side = "BUY" if o.direction > 0 else "SELL"
            size = float(o.size) if o.size is not None else 0.0
            kids = [("tp", float(o.take_profit)) if o.take_profit else None,
                    ("sl", float(o.stop_loss)) if o.stop_loss else None]
            kids = [k for k in kids if k]
            if kind == "modify":
                for rid in o.related_orders or []:
                    if rid in self.waiting:
                        w = self.waiting[rid]
                        w["price"] = float(o.order_limit_price)
                        w["size"] = size or w["size"]
                        w["kids"] = kids
                        w["order"].order_limit_price = o.order_limit_price
                        w["order"].size = o.size
                continue
            if kind == "limit":
                oid = next(self.ids)
                o.id = oid
                self.waiting[oid] = {"order": o, "kind": "limit", "side": side, "price": float(o.order_limit_price),
                                     "size": size, "kids": kids, "group": None}
            else:
                self.to_send.append((side, size, kids))

    # ---------- the exchange side, once per minute ----------
    def on_minute(self, m):
        """m is the minute just handed out. Returns (side, qty) to send with the next request or None."""
        self.rows.append({"Date": pd.Timestamp(m["time"], tz="UTC"), "Open": m["open"], "High": m["high"],
                          "Low": m["low"], "Close": m["close"], "Volume": m["volume"]})
        self.cash, self.coins, self.close = m["cash"], m["coins"], m["close"]
        for oid, w in list(self.waiting.items()):
            hit = (w["side"] == "BUY" and m["low"] <= w["price"]) or (w["side"] == "SELL" and m["high"] >= w["price"])
            if w["kind"] == "sl":
                hit = m["low"] <= w["price"]
            if hit and oid in self.waiting:
                del self.waiting[oid]
                if w.get("group") is not None:          # one cancels the other
                    for j, v in list(self.waiting.items()):
                        if v.get("group") == w["group"]:
                            del self.waiting[j]
                self.to_send.append((w["side"], w["size"], w.get("kids", [])))

    def next_request(self):
        if not self.to_send:
            return None
        side, qty, kids = self.to_send.pop(0)
        if side == "SELL":
            qty = min(qty, self.coins)
        if qty <= 0:
            return None
        if side == "BUY" and kids:                    # attached take-profit / stop-loss for the long just bought
            g = next(self.ids)
            for kind, price in kids:
                self.waiting[next(self.ids)] = {"order": None, "kind": kind, "side": "SELL", "price": price,
                                                "size": qty, "kids": [], "group": g}
        return side, qty
