"""Hummingbot scripts/simple_pmm.py (repo commit 3351ada), way A: through the price server, one minute at a time.

SimplePMM's own on_tick / create_proposal / adjust_proposal_to_budget / place_orders / cancel_all_orders run
unchanged on a stand-in bot object, with Hummingbot's real BudgetChecker against a stand-in account. Stand-ins:
  - price: the minute's close (mid price; we have no order book)
  - clock: one tick per minute (its order_refresh_time is 15 s, so it re-quotes every tick)
  - fills (market-maker rule for the contest): a quote placed after minute t fills only if minute t+1's low reaches
    the bid (high reaches the ask); the order then goes to the price server with the next request and fills at
    minute t+2's close at 0.7%. Only one order can go per minute, so a second fill waits a minute.
Config: shipped defaults (bid/ask spread 0.1%, refresh 15 s, mid price) except trading_pair PEARL-USDT and
order_amount: the shipped 0.01 is ETH-sized, so the rule fixed before the run is $100 per quote at the last close
before 1 Oct (1.2197): 82 PEARL.

    venv_hb/bin/python run_simple_pmm.py
"""
import os
import sys
from collections import deque
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "downloads", "hb_repo", "scripts"))
import sealed  # noqa: E402
from simple_pmm import SimplePMM, SimplePMMConfig  # noqa: E402

from hummingbot.connector.budget_checker import BudgetChecker  # noqa: E402
from hummingbot.core.data_type.common import PriceType, TradeType  # noqa: E402

PAIR = "PEARL-USDT"


class Account:
    name = "binance"

    def __init__(self):
        self.bal = {"USDT": Decimal(0), "PEARL": Decimal(0)}
        self.price = Decimal(1)

    def get_available_balance(self, token):
        return self.bal.get(token, Decimal(0))

    get_balance = get_available_balance

    def get_price(self, pair, is_buy):
        return self.price

    def quantize_order_amount(self, pair, amount):
        return (amount // Decimal("0.0001")) * Decimal("0.0001")


class Connector:
    def __init__(self, account):
        self.account = account
        self.budget_checker = BudgetChecker(account)

    def get_price_by_type(self, pair, price_type):
        return self.account.price


class Order:
    def __init__(self, oid, side, amount, price):
        self.client_order_id, self.side, self.amount, self.price, self.trading_pair = oid, side, amount, price, PAIR


class Bot:
    """Stands in for the StrategyV2Base plumbing; every strategy method is SimplePMM's own."""

    on_tick = SimplePMM.on_tick
    create_proposal = SimplePMM.create_proposal
    adjust_proposal_to_budget = SimplePMM.adjust_proposal_to_budget
    place_orders = SimplePMM.place_orders
    place_order = SimplePMM.place_order
    cancel_all_orders = SimplePMM.cancel_all_orders
    create_timestamp = 0

    def __init__(self, config, connector):
        self.config = config
        self.connectors = {config.exchange: connector}
        self.price_source = PriceType.LastTrade if config.price_type == "last" else PriceType.MidPrice
        self.current_timestamp = 0
        self.orders, self.n = {}, 0

    def get_active_orders(self, connector_name):
        return list(self.orders.values())

    def cancel(self, connector_name, trading_pair, order_id):
        self.orders.pop(order_id, None)

    def _add(self, side, amount, price):
        if amount <= 0:
            return
        self.n += 1
        self.orders[str(self.n)] = Order(str(self.n), side, amount, price)

    def buy(self, connector_name, trading_pair, amount, order_type, price):
        self._add(TradeType.BUY, amount, price)

    def sell(self, connector_name, trading_pair, amount, order_type, price):
        self._add(TradeType.SELL, amount, price)


def main():
    config = SimplePMMConfig(trading_pair=PAIR, order_amount=Decimal(82))
    account = Account()
    bot = Bot(config, Connector(account))
    queue, kap = deque(), Decimal("0.007")
    with sealed.Sealed(8851) as s:
        m = s.next()
        while m is not None:
            hi, lo, close = Decimal(str(m["high"])), Decimal(str(m["low"])), Decimal(str(m["close"]))
            for o in list(bot.orders.values()):  # quotes placed after the previous minute
                if (o.side == TradeType.BUY and lo <= o.price) or (o.side == TradeType.SELL and hi >= o.price):
                    queue.append(o)
                    del bot.orders[o.client_order_id]
            cash, coins = Decimal(str(m["cash"])), Decimal(str(m["coins"]))
            for q in queue:  # fills not yet executed still use the money
                if q.side == TradeType.BUY:
                    cash -= q.amount * close * (1 + kap)
                    coins += q.amount
                else:
                    coins -= q.amount
                    cash += q.amount * close * (1 - kap)
            account.bal = {"USDT": max(cash, Decimal(0)), "PEARL": max(coins, Decimal(0))}
            account.price = close
            bot.current_timestamp = m["ts"] * 60
            bot.on_tick()
            if queue:
                q = queue.popleft()
                m = s.next("BUY" if q.side == TradeType.BUY else "SELL", qty=float(q.amount))
            else:
                m = s.next()
    acct = s.account
    print(f"simple_pmm: $1,000 -> ${acct['value']:,.2f} after {len(acct['trades'])} fills "
          f"(cash {acct['cash']:.2f}, PEARL {acct['coins']:.4f}); holding ${acct['holding']:,.2f}")
    sealed.record("Hummingbot 20261118 scripts/simple_pmm.py", "shipped defaults, 82 PEARL per quote", "A",
                  len(acct["trades"]), acct["value"], "ran",
                  "own on_tick/proposal/BudgetChecker; quote fills if next minute's high/low reaches it, executed at "
                  "the minute after that's close via the server")


if __name__ == "__main__":
    main()
