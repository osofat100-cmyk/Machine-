"""Way A: ohheycrypto 0.2.0 (pip, own code unchanged) on the sealed test through the price server.

ohheycrypto only talks to Binance through python-binance; fakebinance/binance is a stand-in Client answering from the
price server (limit orders wait until a minute's low/high reaches them, then fill at the next minute's close with the
test's cost). Its trading loop runs once a minute (shipped check_interval 60 s): buy check, sell check, stop-loss check,
then sync. Shipped defaults (stop loss 3%, sell 0.4%, buy 0.2%); only BOT_CRYPTO=PEARL, BOT_FIAT=USDT.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fakebinance"))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.update({"BOT_CRYPTO": "PEARL", "BOT_FIAT": "USDT", "BINANCE_API_KEY": "none", "BINANCE_API_SECRET": "none"})
os.environ.pop("DISCORD_WEBHOOK", None)
import pandas as pd  # noqa: E402
import binance  # noqa: E402
import sealed  # noqa: E402
from ohheycrypto.bot import TradingBot  # noqa: E402
from ohheycrypto.config.settings import Config  # noqa: E402

h = sealed.history_before_oct()
binance.Sim.rows = [{"time": t, "high": a, "low": b, "close": c}
                    for t, a, b, c in zip(h["time"], h["high"], h["low"], h["close"])]
bot = TradingBot(Config())
with sealed.Sealed(int(sys.argv[1]) if len(sys.argv) > 1 else 8863) as s:
    m = s.next()
    binance.exchange_minute(m)
    assert bot.initialize()
    while m is not None:
        bot.execute_buy_order()
        bot.execute_sell_order()
        bot.market.check_stop_loss()
        req = binance.Sim.to_send.pop(0) if binance.Sim.to_send else None
        m = s.next(req[0], qty=req[1]) if req else s.next()
        if m is None:
            break
        binance.exchange_minute(m)
        bot.market.sync()
        bot.wallet.sync()
    acct = s.account
orders = binance.Sim.orders
print(f"ohheycrypto: {len(orders)} limit orders placed, {sum(o['status'] == 'FILLED' for o in orders)} filled, "
      f"{len(acct['trades'])} trades, $1,000 -> ${acct['value']:,.2f} (holding ${acct['holding']:,.2f})")
pd.DataFrame(acct["trades"]).to_csv(os.path.join(HERE, "trades_ohheycrypto.csv"), index=False)
sealed.record("ohheycrypto 0.2.0", "RSI + trend + dynamic thresholds, limit orders (shipped defaults)", "A",
              len(acct["trades"]), acct["value"], "ran",
              "Binance-only; stand-in python-binance Client; loop once a minute")
