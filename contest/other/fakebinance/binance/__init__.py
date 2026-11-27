"""Stand-in for python-binance's Client (way A). Answers from the contest price server, see run_ohheycrypto.py."""
import pandas as pd

from .exceptions import BinanceAPIException  # noqa: F401


class Sim:
    rows = []          # minute dicts: time (Timestamp), high, low, close
    cash, coins = 1000.0, 0.0
    orders = []        # binance-style order dicts
    to_send = []       # (side, qty) for the price server
    next_id = 1
    daily, daily_for = [], None


class Client:
    KLINE_INTERVAL_1DAY = "1d"
    SIDE_BUY, SIDE_SELL = "BUY", "SELL"
    ORDER_TYPE_LIMIT = "LIMIT"
    TIME_IN_FORCE_GTC = "GTC"

    def __init__(self, *a, **k):
        pass

    def _now(self):
        return Sim.rows[-1]

    def get_ticker(self, symbol=None):
        last = Sim.rows[-1]
        day = [r for r in Sim.rows[-1440:]]
        return {"symbol": symbol, "lastPrice": str(last["close"]), "askPrice": str(last["close"]),
                "bidPrice": str(last["close"]), "highPrice": str(max(r["high"] for r in day)),
                "lowPrice": str(min(r["low"] for r in day))}

    def get_historical_klines(self, symbol, interval, start_str=None, *a, **k):
        assert interval == "1d"
        days = (pd.Timestamp.today().normalize() - pd.Timestamp(start_str)).days   # the bot asks "today - N days"
        day = Sim.rows[-1]["time"].normalize()
        if Sim.daily_for != day:                     # completed days, rebuilt once per day
            df = pd.DataFrame(Sim.rows).set_index("time")
            d = df[df.index < day].resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
            Sim.daily = [[int(t.timestamp() * 1000), r.close, r.high, r.low, r.close, 0] for t, r in d.iterrows()]
            Sim.daily_for = day
        today = [r for r in Sim.rows[-1440:] if r["time"] >= day]          # today's candle is partial, like Binance
        part = [int(day.timestamp() * 1000), today[0]["close"], max(r["high"] for r in today),
                min(r["low"] for r in today), today[-1]["close"], 0]
        first = int((day - pd.Timedelta(days=days)).timestamp() * 1000)
        return [k for k in Sim.daily if k[0] >= first] + [part]

    def get_all_orders(self, symbol=None, limit=100):
        return [dict(o) for o in Sim.orders[-limit:]]

    def _locked(self):
        b = sum(float(o["price"]) * float(o["origQty"]) for o in Sim.orders if o["status"] == "NEW" and o["side"] == "BUY")
        s = sum(float(o["origQty"]) for o in Sim.orders if o["status"] == "NEW" and o["side"] == "SELL")
        return b, s

    def get_asset_balance(self, asset=None):
        b, s = self._locked()
        free = max(0.0, Sim.cash - b) if asset == "USDT" else max(0.0, Sim.coins - s)
        return {"asset": asset, "free": str(free)}

    def get_account(self):
        return {"balances": [{"asset": a, "free": self.get_asset_balance(a)["free"]} for a in ("USDT", "PEARL")]}

    def get_trade_fee(self, symbol=None):
        return [{"symbol": symbol, "makerCommission": "0.002", "takerCommission": "0.002"}]

    def create_order(self, symbol, side, type, timeInForce, price, quantity):
        o = {"symbol": symbol, "orderId": Sim.next_id, "price": float(price), "origQty": float(quantity),
             "status": "NEW", "type": type, "side": side, "updateTime": 0}
        Sim.next_id += 1
        Sim.orders.append(o)
        return dict(o)

    def cancel_order(self, symbol=None, orderId=None):
        for o in Sim.orders:
            if o["orderId"] == orderId and o["status"] == "NEW":
                o["status"] = "CANCELED"
        return {}


def exchange_minute(m):
    """Exchange side for one minute: a waiting limit order whose price was reached is filled (sent to the server)."""
    Sim.rows.append({"time": pd.Timestamp(m["time"], tz="UTC"), "high": m["high"], "low": m["low"], "close": m["close"]})
    Sim.cash, Sim.coins = m["cash"], m["coins"]
    for o in Sim.orders:
        if o["status"] != "NEW":
            continue
        if (o["side"] == "BUY" and m["low"] <= o["price"]) or (o["side"] == "SELL" and m["high"] >= o["price"]):
            o["status"] = "FILLED"
            Sim.to_send.append((o["side"], o["origQty"]))
