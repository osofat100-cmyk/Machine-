# Agent 1 - GitHub / GitLab findings

20+ GitHub searches (repository search sorted by stars, plus code search inside repos).
Star/fork counts and last-update dates are from the GitHub search API on 21 Nov 2026.
Note: I could only use GitHub's search API (repo pages and READMEs were not readable from this session), so "what it does" comes from repo descriptions and file names found by code search, not from running the code.

## Tier 1 - big frameworks (fully done, maintained, 1000+ stars)

### 1. Freqtrade - https://github.com/freqtrade/freqtrade
- Stars 57,121 | forks 11,790 | updated 21 Nov 2026 (active today)
- What: complete Python crypto bot: backtesting, hyperopt (parameter search), dry-run (paper) and live trading, Telegram/web UI, Docker.
- Premade strategies: official collection https://github.com/freqtrade/freqtrade-strategies (5,673 stars) - Strategy001-005, TWAPStrategy, HourBasedStrategy, AlmgrenChrissStrategy, etc. Most popular community strategy: NostalgiaForInfinity https://github.com/iterativv/NostalgiaForInfinity (3,546 stars, updated 20 Nov 2026). Other strategy packs: MoniGoMani (1,028), ssssi/freqtrade_strs (653), nateemma/strategies (444), PeetCrypto/freqtrade-stuff (337), paulcpk/freqtrade-strategies-that-work (331), werkkrew (325).
- Can it trade PEARL? Uses CCXT for exchanges (18 CCXT hits in freqtrade/exchange). Code search: "bigone" = 0 hits, "coinbase" = 0 hits in the freqtrade repo. So BigONE/Coinbase are NOT among its tested exchanges; might connect through generic CCXT, untested.
- No rebalancing strategy: code search "rebalance" in freqtrade-strategies = 0 hits.
- Fully done? Yes - install, config file, run.
- Evidence it works: none verified. Strategy repos show backtests only. (From earlier research rounds: best independent live report was a blogger's dry-run +4.93% over 67 days, self-reported.)
- Setup: medium (config JSON, API keys, pair list, pick strategy).

### 2. Hummingbot - https://github.com/hummingbot/hummingbot
- Stars 21,331 | forks 5,168 | updated 21 Nov 2026
- What: market-making and arbitrage bot (places buy and sell limit orders around the price), Python, Docker.
- Can it trade PEARL? "coinbase" = 26 code hits (has a Coinbase connector). "bigone" = 0 hits (no BigONE). Uses its own connectors, not plain CCXT.
- Fully done? Yes.
- Evidence: no verified live record. (Earlier rounds: GNCrypto 7-day $200 test +$5.58 net; another test -$16.50.)
- Setup: medium-high (market making needs spread/inventory settings).

### 3. OctoBot - https://github.com/Drakkar-Software/OctoBot
- Stars 6,968 | forks 1,326 | updated 21 Nov 2026
- What: open-source bot with a web GUI; premade Grid, DCA, AI and TradingView-signal strategies; "Binance, Hyperliquid and 15+ exchanges". Exchange layer is CCXT (ccxt_adapter.py, ccxt_websocket_connector.py, configurable_default_ccxt_rest tentacle found by code search).
- Related: OctoBot-Market-Making https://github.com/Drakkar-Software/OctoBot-Market-Making (43 stars), OctoBot-Trading library (136 stars).
- Can it trade PEARL? "coinbase" = 57 code hits (Coinbase supported). "bigone" = 0 hits. There is a "configurable_default_ccxt_rest" exchange option, which may let any CCXT exchange (incl. BigONE) connect - untested.
- Fully done? Yes - web GUI, Docker, pip. Grid and DCA are pick-from-menu.
- Evidence: none verified.
- Setup: LOW - easiest of the big bots because of the GUI.

### 4. Superalgos - https://github.com/Superalgos/Superalgos
- Stars 5,813 | forks 5,992 | updated 20 Nov 2026
- What: visual (drag-and-drop) bot designer with charts, data mining, backtesting, paper trading, multi-server deployment. Node.js.
- Can it trade PEARL? Not checked/unknown.
- Fully done? Yes, but complex.
- Evidence: none found.
- Setup: high.

### 5. Jesse - https://github.com/jesse-ai/jesse
- Stars 8,827 | forks 1,294 | updated 21 Nov 2026
- What: Python backtesting framework. Live trading plugin is paid/closed (from earlier rounds).
- Can it trade PEARL? Backtest yes (any data); live needs paid plugin; exchange list not checked.
- Fully done? Backtesting yes; live behind paywall.
- Evidence: none.
- Setup: medium.

### Other large repos seen (less relevant)
- CCXT https://github.com/ccxt/ccxt - 44,944 stars. Library, not a bot. The ONLY project that supports BigONE (59 code hits for "bigone").
- Crypto-Signal https://github.com/CryptoSignal/Crypto-Signal - 5,660 stars. Signals/technical analysis only, does not trade.
- blankly https://github.com/blankly-finance/blankly - 2,485 stars. Multi-exchange algo platform (Coinbase listed in description). Build-your-own, no premade strategy.
- pycryptobot https://github.com/whittlem/pycryptobot - 2,061 stars. Coinbase/Binance/Kucoin bot (MACD/EMA signals). No CCXT, no BigONE.
- intelligent-trading-bot https://github.com/asavinov/intelligent-trading-bot - 1,907 stars. ML signal bot.
- algotrading https://github.com/ivopetiz/algotrading - 1,720 stars. Framework.
- algobot https://github.com/ZENALC/algobot - 952 stars. GUI bot, Binance.
- Gekko https://github.com/askmike/gekko - 10,180 stars. DEAD (archived ~2018). Gekko-Strategies (1,445 stars) also old.
- Zenbot - dead.

## Tier 2 - small but on-topic

### 6. Cryptotrademate - https://github.com/Cryptotrademate/cryptotrademate-trading-bot
- 13 stars | 4 forks | updated Jun 2026
- What: Grid + DCA bot, Python + CCXT, Telegram control, "Binance, Coinbase and more".
- PEARL? Coinbase claimed; BigONE possible via CCXT, untested.
- Fully done? Appears so. Evidence: none.

### 7. DCAStack - https://github.com/DCAStack/DCAStackCefi
- 59 stars | 10 forks
- What: automated DCA for centralized exchanges, web app (forms, dashboard found by code search).
- PEARL? Exchange list unknown. Evidence: none.

### 8. ACERVATOR - https://github.com/Acervator-LLC/ACERVATOR
- 4 stars | 0 forks
- What: "accumulation trading platform... harvests volatility by selling the excess and buying back the dip, across 19 venues", PySide6 desktop app. Claims "6,200+ real trades". Docs folder has "the reserve for a dip", "how far price must move" pages.
- This is the closest thing to a premade volatility-harvesting / rebalancing-style bot I found.
- PEARL? Unknown which 19 venues. Evidence: only its own claim; 4 stars.

### 9. pegahcarter/rebalance - https://github.com/pegahcarter/rebalance
- 18 stars | 9 forks | updated Sep 2026
- What: "Rebalance & backtest your cryptocurrency portfolio". Small Python utility.
- PEARL? Unknown. Evidence: none.

### 10. crypto-index-fund-bot - https://github.com/iloveitaly/crypto-index-fund-bot
- 62 stars | 9 forks
- What: "Build your own crypto index fund" (buys a market-cap index, rebalances). Has bot/market_buy.py.
- PEARL? Unknown (index of top coins, not single-coin). Evidence: none.

### Other small rebalancing/grid/DCA repos (all 0-30 stars)
- RetGal/BalanceR (8 stars) - rebalance bot with Mayer Multiple, German.
- timdoubleg/crypto-index-bot (3) - Binance top-10 rebalance.
- knightlightst/rebalancer (42) - WBTC/WETH rebalance on Uniswap (DEX, not PEARL).
- jordantete/grid_trading_bot (154 stars) - grid bot with backtesting.
- btschwertfeger/infinity-grid (26) - multi-exchange infinity grid.
- princeniu/AS-Grid (40) - futures grid (Binance/OKX/Gate).
- wpeok45/volatility_harvesting (1) - spot volatility-harvesting bot.
- lussifa/Shannon-s-Demon (1) - "a trading idea", not a bot.
- Kraken/Binance/Crypto.com DCA bots: adocquin/kraken-dca (43), CyberPunkMetalHead/binance-dca (55), piebotai/bot (36).
- Fundless (9) - index-fund bot with web UI.

## Searches that found nothing
- "threshold rebalancing crypto": 0 repos.
- "volatility pumping rebalance": 0. "constant proportion portfolio insurance crypto": 0.
- "freqtrade strategy rebalance": 0. "crypto portfolio rebalance ccxt": 0. "shrimpy crypto rebalance": 0.
- "kelly criterion crypto trading": 0. "dynamic grid trading crypto": 0 (the DGT paper code colachenkc/Dynamic-Grid-Trading did not show up in this search).

## Bottom line from GitHub
1. BigONE: no bot names it. Only the CCXT library supports it. Any bot on BigONE = CCXT, untested.
2. Coinbase: OctoBot (57 hits) and Hummingbot (26 hits) support it. Freqtrade: 0 hits.
3. A premade threshold-rebalancing bot does not exist in any major framework. Closest: ACERVATOR (4 stars), pegahcarter/rebalance (18), crypto-index-fund-bot (62).
4. Best premade, fully done candidates for PEARL: OctoBot (GUI, Grid/DCA from a menu, Coinbase, CCXT), then Freqtrade (biggest, many strategies, would need its CCXT connection to BigONE/Coinbase tested), then Hummingbot (market making on Coinbase).
5. No repository has verified live trading results.
