# Group 4: grid and DCA bots

Written before any program was run on the test.

## Rule for settings that have no default (fixed before running)
- Grid price range: the 30-day low and high of PEARL/USDT up to 30 Sep 23:59 (data before Oct only):
  low 0.2864, high 1.762. (Computed from data/PEARL-USDT_min1_before_oct.csv, 31 Aug 23:59 - 30 Sep 23:59.)
- Number of grid levels / spacing / order size / DCA amounts: the program's shipped default or README/example config.
- Pair: PEARL/USDT. Start: 1,000 USDT, 0 PEARL on 1 Oct 00:00 (price server account).
- Way A fill rule: a resting limit order at a grid level is sent as a market order on the minute that minute's
  close crosses the level; the server fills it at the next minute's close with the 0.7%/side cost.

## Log
- Dynamic-Grid-Trading: read all 441 lines. Ran its own backtest (src.dgt_backtest) on Sep 2026 data (pre-Oct, only the
  date range in a copy of config.py changed) -> TypeError at the first downward break. Recorded "does not run as shipped".
- grid_trading_bot 0.2.0: 11k lines, async; live mode runs on wall-clock (ticker feed, reconciliation, health checks), so way A
  would mean rewriting it -> way B with its own engine. Read backtest_grid_strategy.py, backtest_exchange_service.py.
  Config = shipped config/config.json with pair PEARL/USDT, exchange bigone, fee 0.007, $1,000, period, data file,
  backtest_min_cost 2.0 and the pre-written range. hedged_grid (shipped type) $1,159.24, 8 trades; simple_grid $1,064.76, 3 trades.
- Cryptotrademate: read all 226 lines. Way A with strategies.py unchanged. GridBot places 5 buy limits of 1 PEARL (amount
  hard-coded) and never sells: $1,001.22. DCABot fires all 10 buys at once with 100 = PEARL amount: buy-and-hold, $1,469.81.
- DCAStack: requirements only install on Python 3.9 (uv). Way A with ccxtHelper.place_market_order unchanged. $19/day: $1,143.12.
- PowerTrader_AI: KuCoin data + Robinhood orders only; no PEARL on either. Recorded "cannot run here".
- OpenTrader settings (written before running):
  - grid: config.sample.json5 -> gridLevels 20; range = pre-written rule 0.2864-1.762; quantityPerGrid: the sample's
    0.005 is a BTC amount, so rule = split $1,000 evenly over the 20 lines at the start price 1.2214 (Oct 1 00:00 close,
    the moment the bot starts): 1000 / 20 / 1.2214 = 40.93 PEARL. Timeframe 1m (README: smaller is more accurate).
  - rsi: schema defaults high 70, low 30, periods 14, persistence 1; timeframe 1h (README backtest example `-t 1h`);
    quantity: the default 0.0001 is meaningless for PEARL, rule = one full stake at the start price:
    1000 / 1.2214 = 818.7 -> 818 PEARL (the price server caps a buy at the cash it has, a sell at the coins it has).
  - dca: no example config anywhere in the repo, and its backtester refuses DCA trades -> not run.
  - Way A with its own code: strategy templates + createStrategyRunner + MarketSimulator/MemoryStore/MemoryExchange
    unchanged, copying Backtesting.run's loop; candles come one at a time from the price server and each fill its
    simulator makes is sent to the server (market: placed after candle i, server fills at i+1 close = same as its
    simulator; limit: sent on the candle its simulator fills it, server fills at the next close). The price server
    keeps the real account, so a sell of PEARL it does not hold sells nothing (OpenTrader's grid assumes the coins for
    grid lines above the price are already held and has no balance check).
- OpenTrader grid: first try deadlocked (Node fetch opened a 2nd connection; the price server serves one at a time) ->
  fixed by one kept-alive http.Agent connection. Result $1,145.46, 115 orders, 108 filled, 7 sells with no PEARL held.
- OpenTrader dca: backtester throws "Trade with type DCA is not supported in backtesting". Not run.
- Gunbot (paid), Pionex (hosted): not run.
- pantelis98765/crypto-bot: Docker Hub image only (no public source; README says <your-repo>), Binance + Crypto.com only,
  needs Postgres. No docker daemon here; registry API pull refused twice: TOOMANYREQUESTS (unauthenticated rate limit).
- pantelis98765/crypto-bot: 3rd pull refused (TOOMANYREQUESTS). Recorded 'cannot run here'.
