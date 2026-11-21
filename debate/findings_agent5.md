> Pasted unchanged by the coordinator: Agent 5's own file write was blocked, so it returned this text and asked for it to be saved as-is.

# Agent 5 findings: Freqtrade / Hummingbot / QuantConnect / Backtrader communities

I ran 20 web searches across Freqtrade, Freqle, Hummingbot, QuantConnect, Backtrader, Jesse, OctoBot, Zenbot, TradingView Pine, MQL5, Kaggle, GitHub rebalancers and arXiv/SSRN paper code.

**Main conclusion:** premade, downloadable systems exist, and several can connect to Coinbase PEARL-USD. None has a verified long-term live record. Every number below is a backtest or a short paper-trading run unless stated otherwise.

## 1. Freqtrade and community strategies (strongest platform)
- **Platform:** Python, open source, GPL-3.0, about 57K GitHub stars. https://github.com/freqtrade/freqtrade
- **Official strategy repo:** https://github.com/freqtrade/freqtrade-strategies. Its README says these are starting points, not plug-and-play. They need Freqtrade 2022.4 or newer.
- **Freqle** (https://freqle.org/) indexes 15,184 strategies from 1,627 repos, with 9,580 sandboxed backtests covering 2022–2024. Top of its leaderboard:
  - **NotAnotherSMAOffsetStrategyHO** (davidzr/freqtrade-strategies): +117.0%, 813 trades, 80.7% win rate, profit factor 3.24. It buys dips below a moving average, filtered by the Elliott Wave Oscillator (EWO). Code: https://raw.githubusercontent.com/remiotore/freqtrade/44beaeb6a420cd8e9f2e4ea93e11d6cfa192ee03/strategies/NotAnotherSMAOffsetStrategyHO.py
  - **DS_BNC_EV1E_5m:** +93.8%.
  - **E0V1E** (TheoBrigitte/freqtrade, ssssi/freqtrade_strs): +90.7%. A 5-minute Bollinger squeeze with a 1-hour trend filter. The file calls itself "Live-Validated", but that is its own claim; I found no independent live data. Code: https://raw.githubusercontent.com/TheoBrigitte/freqtrade/d5764d16875707af98ffee939f976dcc9d40662f/strategies/e0v1e/E0V1E.py
  - **heisenberg:** +770.8% over 6,660 trades (backtest).
  - **Risk_Lev3** page: 28.88% maximum drawdown, Sharpe 1.598.
- **Other repos:**
  - BuyMeAnIcecream/freqtrade-strategies calls itself "production-ready" (unverified).
  - TheoBrigitte/freqtrade has strategies plus paper-trading and backtest results.
  - nateemma/strategies says in its README that every model loses on its own.
- **FreqST** (freqst.com) says its shared strategies are no longer maintained and will be archived.
- **How to run:** copy the `.py` file into `user_data/strategies/`, set the pairs, run. A paper-trading mode is built in.
- **Exchanges:** Binance, Coinbase, Kraken, OKX, Bybit, Gate.io and others through the CCXT library. BigONE is in CCXT (REST only) but is not an officially tested Freqtrade exchange.
- **Can it trade PEARL?** Yes on Coinbase PEARL-USD. BigONE is possible but untested.
- **Live evidence:**
  - The backtestsnotsignals Substack "Dual & Reversion Portfolio" paper-trades on Bybit perpetuals. It was at +4.93% in its week-37 report (about 59–67 days). The author says that is "nowhere near a track record".
  - The same author shows strategies collapsing on unseen data: yearly growth 105.03% → 3.65% (Calmar 68.63 → 0.44), and 35.35% → −13.61% on 2024–2026 data.
  - The DEV "67.9% win rate" tutorial and the "+983% in 6 years" post are backtests only.
  - dev.to trendrider: 13 days, 48 trades, breakeven.
  - One guide warns that tuning the stop-loss improves backtests but makes live results worse.
- **Fully done?** The platform is. The strategies download and run as-is, but none is tuned for PEARL; all were tested on major pairs.

## 2. Hummingbot (market making)
- **Platform:** Python, Apache-2.0, about 19.5K stars, last release Oct 2026. https://github.com/hummingbot/hummingbot
- **Built-in scripts** (https://hummingbot.org/strategies/scripts/examples/): simple_pmm (pure market making), simple_xemm (cross-exchange market making), spot_perpetual_arbitrage, twap, simple_vwap, v2_funding_rate_arb. Newer "V2 controllers" include pmm_mister.py.
- **Community:** Chonz-dot/hummingbot-strategies has mm.py (with inventory management) and pmm_mining.py. Its performance table is unverified.
- **Paper trading:** the `create --script-config` wizard sets it up. simple_pmm paper-trades against live Binance data with no API keys.
- **Exchanges:** Binance, Coinbase, KuCoin, Gate.io, Hyperliquid and more.
- **Can it trade PEARL?** Technically yes on Coinbase. But market making on a book only about $50K deep is risky, and holdings get lopsided when the price swings.
- **Evidence:**
  - gncrypto 7-day Binance test with $200 and a 0.3% spread: +$12.40 gross, +$5.58 net. Holdings got lopsided and needed a manual fix.
  - Another test lost $16.50.
  - A HackMD backtest of pure market making at a 0.2% spread: 84.1% win rate, $37,168 profit. It is simulated, and the asset and period are unknown.
  - arXiv 2204.13265 found "positive alpha" in simulation only, not on altcoins.
  - AMBCrypto lists Hummingbot's performance evidence as "None; depends on your strategy".
  - Stoikov et al. on SSRN (pairs trading 6188418, market making 5066176) ran live on Hummingbot. Whether their code is published is unclear.
- **Fully done?** Yes, the scripts run as shipped. The user has to set the spread and order size.

## 3. OctoBot
- **Platform:** Python, open source, about 7K stars, version 2.1.1 (Mar 2026). https://github.com/drakkar-software/octobot and https://octobot.cloud
- **Premade presets:** Smart DCA, "Altcoin Madness" (smart DCA), ChatGPT Crypto Hero AI DCA, grid presets for BTC/ETH/SOL/XRP, crypto baskets, running TradingView alerts as trades, and an AI agent mode (beta, 2026).
- **Setup:** point-and-click interface, paper trading, one-click DigitalOcean install.
- **Exchanges:** Binance, Coinbase, Hyperliquid, KuCoin, Gate.io, 15+ in total.
- **Can it trade PEARL?** Yes on Coinbase. The presets are built for other coins, so switching one to PEARL counts as a change.
- **Evidence:** none verified.
  - No reviews of "Altcoin Madness" exist.
  - OctoBot's Telegram admitted that Cloud backtest stats (for example "Doge Daydream") differed from live results; it says this is fixed.
  - A Gainium review mentions one user making about +2% in a downturn, strategy not named.
- **Fully done?** Yes as a product; each preset is fixed to its coins.

## 4. GitHub rebalancing bots
- **sandybradley/Coinbase-Balancer:** Python, rebalances on a schedule (hourly by default). Written for Coinbase Pro, so it needs porting to the Advanced Trade API. https://github.com/sandybradley/Coinbase-Balancer
- **royaurko/coinbase-trading:** Python 3, CPPI (Constant Proportion Portfolio Insurance) on BTC, has a simulation mode. Old. https://github.com/royaurko/coinbase-trading
- **Saga-Labs/rebalancer:** Node.js, trades on-chain on the Base network through CoW Protocol, tracks itself against holding, sends Telegram alerts. Not usable for PEARL, which has no deep on-chain pool. https://github.com/Saga-Labs/rebalancer
- **0xRozier/rebalancing-bot** (MIT, DeFi, promotional README) and **pontifier/rebalancer** (built for BTC-E, a dead exchange).
- **Cryptohopper marketplace:** RyzeX Portfolio Bot, a paid rebalancer that runs every 24 hours or on a set % change.
- **Hosted services:**
  - Shrimpy is discontinued (bought by Bitcoin IRA in Nov 2023).
  - 3Commas costs $22–99/month, rebalances on a threshold or a schedule, and had an API key breach.
  - Pionex's rebalancing bot works on the Pionex exchange only.
- **Evidence:** none published for any of them.
- **Fully done?** Partly. Coinbase-Balancer needs API changes.

## 5. arXiv / SSRN paper code
- **Dynamic Grid Trading** (arXiv 2506.11921): https://github.com/colachenkc/Dynamic-Grid-Trading. BTC/ETH backtests 2021–2024, claims 60–70% yearly return; fees are not clearly modelled.
- **Short-horizon mean reversion** (arXiv 2608.21888): replication package at https://github.com/nadav2/short-horizon-reversion (public Binance, Coinbase, OKX, Bybit data). A measurement study, not a bot.
- **FS-ReasoningAgent** (arXiv 2410.12464): https://github.com/Persdre/FS-ReasoningAgent (language-model trader).
- **TradingAgents** (arXiv 2412.20138): https://github.com/TauricResearch/TradingAgents (multi-agent language model; outputs change from run to run).
- **AgenticTrading** (arXiv 2512.02227): Open-Finance-Lab, NeurIPS 2025 workshop.
- **"Can AI make money in crypto"** (arXiv 2609.34510): links a list at https://github.com/Starlien95/Awesome-TradingAI.
- **SSRN 5225612:** modular Python backtest code (I only saw it through Scribd).
- **Crone 2021** (arXiv): GitHub code; the author says results may differ from the paper.
- **Fully done?** No. Research code, backtests only, no live trading.

## 6. QuantConnect / LEAN
- The LEAN engine is open source (https://www.lean.io/). About 1,200 community algorithms are in the forum.
- **Crypto:**
  - WarmCryptoCrossover v2: forum post about 9 years old, "not recommended for live".
  - ML Crypto Algo template: QuantConnect staff said it is "not a winning algo".
  - BasicTemplateCryptoAlgorithm.py: only demonstrates order types.
- There is no central crypto strategy library. Coinbase is a supported brokerage, but PEARL data and support are unconfirmed.
- **Fully done?** No, for crypto.

## 7. Jesse
- https://github.com/jesse-ai/jesse, version 3.4.0 on PyPI. The awesome-jesse list is only links. The live-trading plugin is paid.
- No shared-strategy marketplace and no performance data. Unofficial `.exe` copies exist; avoid them.

## 8. Backtrader
- I found no crypto-specific shared strategy library with results.

## 9. Zenbot
- Node.js, mostly unmaintained. Its default strategy, trend_ema, follows moving averages.
- Only 2017 simulations exist (ETH +75% in one week).
- Docker Hub warns: "many people are reporting losses in live trading even if the simulation results and/or paper trading is positive".
- Not usable for PEARL.

## 10. TradingView Pine Script
- **Public library:** a Medium author (Apr 2026) tested UT Bot, MACD+SMA200, Chandelier Exit, Heikin Ashi Trend and SSL Channel on BTCUSDT daily, Jan 2025–Mar 2026. This is one author's test.
- **Strategy Arena:** 7 free strategies, none of which passed its own test on BTCUSDT.
- **GitHub:** Alorse/pinescript-strategies (48 strategies), Tim1l/PineCryptoStrategies.
- These produce signals only. Trading them needs a bridge such as OctoBot or 3Commas. A Coinbase PEARL chart is available.

## 11. MQL5 Market
- Crypto Investor EA ($267, live signal page https://www.mql5.com/en/signals/2393420), Crypto Suite EA ($250, BTC/ETH, hourly), BTC ANCHOR, Pac Man BTC.
- MetaTrader 5 brokers only offer BTC/ETH-type contracts, so these cannot trade PEARL.

## 12. Kaggle
- BTC notebooks: moving-average crossover, momentum, machine-learning backtest, market-making analysis. Educational only, no exchange connection.
- lcsrodriguez/cryptotrading: XGBoost/LSTM models on G-Research competition data.

## 13. Others
- **Gunbot:** paid, runs on your own machine, $59–249 lifetime licence.
- **Krypto-trading-bot** (ctubio, C++, about 3.7K stars): very fast market making, for advanced users.
- **Security:** fake "trading bot" repos with bought stars have stolen keys. Check the code and avoid downloads that are only an `.exe`.

## Ranking

| Rank | System | Fully done | PEARL | Live evidence | Cost |
|---|---|---|---|---|---|
| 1 | Freqtrade + Freqle strategies | Yes (run as-is) | Yes, Coinbase | One ~2-month paper run +4.93%; documented collapse on unseen data | Free |
| 2 | Hummingbot simple_pmm | Yes (settings needed) | Risky, thin book | 7-day +$5.58; another test −$16.50 | Free |
| 3 | OctoBot presets | Yes | Coinbase, coin change needed | None | Free tier |
| 4 | GitHub rebalancers | Partly | Coinbase-Balancer after API port | None | Free |
| 5 | arXiv/SSRN code | No | No | Backtest only | Free |
| 6+ | Zenbot, MQL5, Pine, Kaggle, QuantConnect | No / not for PEARL | No | None | – |

**My position:** Freqtrade is the most complete premade platform that can trade PEARL on Coinbase today, with thousands of downloadable strategies. No premade strategy anywhere has a verified long live record. Any pick should go through the repo's existing sealed one-minute-at-a-time test before we trust it.
