#!/usr/bin/env python3
"""Way A: Cryptotrademate's GridBot and DCABot (strategies.py, unchanged) on the price server.

The Telegram wrapper (bot.py) is not used: it only parses the command and calls these two classes.
Commands, one each, sent on 1 Oct 00:00 (README examples; grid range from the pre-written rule in NOTES.md):
    /grid PEARL/USDT 5 0.2864 1.762      (README: /grid BTC/USDT 5 25000 30000)
    /dca  PEARL/USDT 10 1000             (README: /dca BTC/USDT 10 1000)
Stand-in exchange (replaces exchanges.ExchangeConnector):
  - market order: refused if the account can't pay (like a real exchange), else sent with the next request
  - limit buy: rests; sent as a market order on the minute the close is at or below its price, filled at the next
    close (the price server's rule)
"""
import sys

sys.path.insert(0, "/home/user/Machine-/contest")
sys.path.insert(0, "/home/user/Machine-/contest/grid_dca/downloads/cryptotrademate-trading-bot")
import sealed  # noqa: E402
from strategies import DCABot, GridBot  # noqa: E402

COST = 0.007


class StandIn:
    def __init__(self):
        self.cash, self.coins, self.close = 1000.0, 0.0, None
        self.queue, self.resting, self.refused = [], [], []

    def create_order(self, symbol, order_type, side, amount, price=None):
        assert symbol == "PEARL/USDT"
        reserved = sum(q * self.close * (1 + COST) for s, q in self.queue if s == "BUY")
        reserved += sum(q * p for s, q, p in self.resting if s == "buy")
        if side == "buy" and amount * (price or self.close) * (1 + COST) > self.cash - reserved:
            self.refused.append((order_type, side, amount, price))
            raise Exception("Failed to create order: insufficient balance")
        if order_type == "market":
            self.queue.append((side.upper(), amount))
        else:
            self.resting.append((side, amount, price))
        return {"id": len(self.queue) + len(self.resting)}


def run(name, start, port):
    ex = StandIn()
    trades = 0
    with sealed.Sealed(port) as s:
        m = s.next()
        ex.close, ex.cash, ex.coins = m["close"], m["cash"], m["coins"]
        try:
            start(ex)
        except Exception as e:
            print(f"  {name}: stopped placing orders: {e}")
        while True:
            for o in list(ex.resting):
                side, amount, price = o
                if side == "buy" and m["close"] <= price:
                    ex.resting.remove(o)
                    ex.queue.append(("BUY", amount))
            if ex.queue:
                side, qty = ex.queue.pop(0)
                m = s.next(side, qty=qty)
                trades += 1
            else:
                m = s.next()
            if m is None:
                break
            ex.close, ex.cash, ex.coins = m["close"], m["cash"], m["coins"]
    acct = s.account
    print(f"{name}: {trades} orders sent, {len(acct['trades'])} filled, {len(ex.refused)} refused, "
          f"{len(ex.resting)} still resting; end ${acct['value']:,.2f} (cash {acct['cash']:.2f}, "
          f"PEARL {acct['coins']:.4f}); holding ${acct['holding']:,.2f}")
    for t in acct["trades"][:12]:
        print(f"    {t['time']} {t['action']} at {t['price']} -> ${t['value']:,.2f}")
    return len(acct["trades"]), acct["value"], ex


if __name__ == "__main__":
    note = ("way A: strategies.py unchanged, stand-in exchange on the price server. Telegram bot.py not used "
            "(hard-wired to Binance + Telegram token). ")
    n, v, ex = run("GridBot", lambda e: GridBot(e, "PEARL/USDT", 5, 0.2864, 1.762).execute_grid(), 8841)
    sealed.record("Cryptotrademate/cryptotrademate-trading-bot", "/grid PEARL/USDT 5 0.2864 1.762 (README example, "
                  "pre-written range)", "A", n, v, "ran", note + "GridBot only places 5 buy limits of 1 PEARL each "
                  "(amount = 1 hard-coded, 'Adjust amount') and never sells; the rest stays in USDT.")
    n, v, ex = run("DCABot", lambda e: DCABot(e, "PEARL/USDT", 10, 1000).execute_dca(), 8842)
    sealed.record("Cryptotrademate/cryptotrademate-trading-bot", "/dca PEARL/USDT 10 1000 (README example)", "A", n, v,
                  "ran", note + "DCABot sends all 10 market buys at once (no time between them) and passes "
                  "total/intervals = 100 as a PEARL amount, not dollars; buys stop at the first one the account "
                  f"cannot pay ({len(ex.refused)} refused). Ends almost all in PEARL, so it is buy-and-hold.")
