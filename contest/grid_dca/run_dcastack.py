#!/usr/bin/env python3
"""Way A: DCAStack's own place_market_order (project/services/ccxtHelper.py, unchanged) on the price server.

Run with contest/grid_dca/venv_dca39/bin/python (its 2021 requirements only install on Python 3.9).
App: imported unchanged with SET_DEBUG=true (no Sentry, emails only logged), its Celery tasks run inline
(task_always_eager, no Redis), an in-memory SQLite DB. The web pages, Celery beat and the heartbeat ping to
the author's uptime service are not used.
Schedule, as dcaService.run_dcaSchedule does it: first order when the schedule is saved (1 Oct 00:00,
routes.py runs it at once), then each time the clock passes dca_nextRun, which moves by the interval.
Settings (written before running, NOTES.md): interval "1 Days" (first choice in its form), budget $19
(integer field; floor(1000 / 51 test days)). Exchange: BigONE through a stand-in with ccxt 1.95's BigONE
flags (createMarketOrder yes, createMarketBuyOrderRequiresPrice no, fetchOrder yes); best ask = the minute's close.
"""
import datetime
import os
import sys

os.environ.update({"SET_DEBUG": "true", "MAIL_PORT": "25", "SECRET_KEY": "contest", "DATABASE_URL": "sqlite://"})
sys.path.insert(0, "/home/user/Machine-/contest")
sys.path.insert(0, "/home/user/Machine-/contest/grid_dca/downloads/DCAStackCefi")
import ccxt  # noqa: E402
import sealed  # noqa: E402
from project import celery, create_app  # noqa: E402
from project.services.ccxtHelper import place_market_order  # noqa: E402

COST = 0.007
BUDGET, DAYS = 19, 1


class StandIn:
    has = {"createMarketOrder": True, "fetchOrderTrades": None, "fetchOrder": True}
    options = {}

    def __init__(self):
        self.close, self.cash, self.queue = None, 1000.0, []

    def __str__(self):
        return "bigone"

    def load_markets(self):
        return {"PEARL/USDT": {}}

    def fetch_order_book(self, pair):
        return {"asks": [[self.close, 1e9]], "bids": [[self.close, 1e9]]}

    def createOrder(self, pair, kind, side, amount, price=None):
        assert (pair, kind, side) == ("PEARL/USDT", "market", "buy")
        if amount * self.close * (1 + COST) > self.cash:
            raise ccxt.InsufficientFunds("not enough USDT")
        self.queue.append(amount)
        return {"id": str(len(self.queue))}

    def fetchOrder(self, order_id):
        return {"price": self.close, "amount": self.queue[-1]}


class User:
    email = "contest@example.invalid"


def main():
    celery.conf.task_always_eager = True
    app = create_app()
    ex, sent, refused = StandIn(), 0, 0
    with app.app_context(), sealed.Sealed(8843) as s:
        m = s.next()
        next_run = None
        while m is not None:
            ex.close, ex.cash = m["close"], m["cash"]
            now = datetime.datetime.strptime(m["time"], "%Y-%m-%d %H:%M")
            if next_run is None or now > next_run:
                try:
                    if place_market_order(ex, "PEARL/USDT", BUDGET, User()):
                        next_run = (next_run or now) + datetime.timedelta(days=DAYS)
                except ccxt.InsufficientFunds:
                    refused += 1
                    next_run = datetime.datetime.max
            if ex.queue:
                m = s.next("BUY", qty=ex.queue.pop(0))
                sent += 1
            else:
                m = s.next()
    acct = s.account
    print(f"DCAStack ${BUDGET} every {DAYS} day: {sent} buys, {refused} refused; end ${acct['value']:,.2f} "
          f"(cash {acct['cash']:.2f}, PEARL {acct['coins']:.2f}); holding ${acct['holding']:,.2f}")
    for t in acct["trades"][:3] + acct["trades"][-2:]:
        print(f"    {t['time']} BUY at {t['price']} -> ${t['value']:,.2f}")
    sealed.record("DCAStack/DCAStackCefi", f"${BUDGET} every {DAYS} Days (first form choice; 1000/51 days)", "A", sent,
                  acct["value"], "ran",
                  "way A: its place_market_order unchanged with a BigONE stand-in (ccxt 1.95 flags); app imported "
                  "with SET_DEBUG (no Sentry/email), Celery eager, no Redis/web/beat. Only installs on Python 3.9 "
                  "(celery==4.4.7 etc.). Schedule = dcaService rule (next run += interval). Buys only, never sells.")


if __name__ == "__main__":
    main()
