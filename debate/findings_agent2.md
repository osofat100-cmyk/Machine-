> Pasted unchanged by the coordinator: Agent 2's own file write was blocked, so it returned this text and asked for it to be saved as-is.

# Agent 2 findings - Papers With Code / arXiv (plus GitHub, PyPI, Zenodo, Kaggle, SSRN, QuantConnect cross-checks)

19 web searches. Filter: does it come with working code you can download and run? A paper without code was dropped.

**Limit:** I read search results, READMEs and listings. I did not clone or run any repo. "Runnable" means the project says it installs and runs, not that I ran it.

**Papers With Code:** paperswithcode.com now redirects to Hugging Face "Trending Papers". Its crypto search page returned general finance work (for example TradingAgents), not a list of crypto code.

## Ranked list (working code + could trade PEARL + evidence)

### 1. Freqtrade (best overall framework)
- **Code:** https://github.com/freqtrade/freqtrade
- **What it is:** a free, open-source Python crypto bot. It has backtesting, plotting, money management, hyperopt (machine-learning tuning of a strategy's settings), dry-run and live trading.
- **Fully done?** Yes as software: install with pip or Docker, set the config, run. But it is a framework, so you still have to pick or write the strategy.
- **Live trading?** Yes, on exchanges reached through CCXT (Binance, Kraken, Bybit and others).
- **Could it trade PEARL?** Probably, if Coinbase Advanced or BigONE is supported. I have not confirmed this.
- **Evidence:** I found no audited live record.
  - Substack author (DualMomentumCSM v2 + BBReversionV3, dry-run on Kraken): about +6.48%, worst drop about -3.11%, mostly unrealised. The same author's combined backtest showed +257%, but that is a backtest.
  - Earlier round: a self-reported dry run made +4.93% over 67 days. Its author said 67 days is not a track record.
  - DEV Community tutorial: 67.9% win rate and +127% a year, from a backtest only.
  - Gainium review: in 2026 the community was testing 17+ strategies; one "Simple-RSI" claimed 131% profit, self-reported.
  - Guides say live results usually come in 10-20% below backtests.

### 2. Hummingbot (best for market making)
- **Code:** https://github.com/hummingbot/hummingbot
- **What it is:** an open-source market-making and arbitrage bot that ships with premade strategies (V2).
- **Fully done?** Yes as software, with premade strategies. You still have to fill in their settings.
- **Live trading?** Yes, on many exchanges.
- **Could it trade PEARL?** Possibly, if it has a BigONE or Coinbase connector. I have not confirmed this.
- **Evidence:**
  - GNcrypto live test (Binance spot, $200, 0.3% spread): +$12.40 before fees, +$5.58 after. A second test lost $16.50.
  - Hummingbot's own blog: the CTO's strategy made +50% in 3 days during a Bot Battle. That is the project's own marketing and is not audited.
  - Beta Bot Battle (48 hours, 100 USDT start): the winner made about +134.72 USDT, and several entrants lost.
  - Bots run on users' own machines, so the project cannot see their results. About 40% of new users are still running a bot after one month.
- **Caveat:** PEARL's Coinbase order book is thin (about $50K within 2% of the price). Market making on a thin coin that moves in trends risks getting stuck holding coins as the price falls.

### 3. FinRL / FinRL_Crypto (best academic reinforcement-learning framework)
- **Papers:** arXiv 2111.09395, 2211.03107, 2112.06753 and 2209.05559
- **Code:** AI4Finance-Foundation/FinRL, FinRL_Crypto and FinRL-Meta on GitHub
- **What it is:** reinforcement-learning trading agents (PPO, A2C, DDPG, TD3, SAC). FinRL_Crypto targets Binance and is built to reduce backtest overfitting.
- **Fully done?** Partly. It is research code, and the README sends production users to FinRL-X. The classic version's live trading is a basic Alpaca link only.
- **Could it trade PEARL?** Only after work on the data feed, training and the exchange connection.
- **Evidence:** the papers' backtests beat buy-and-hold. I found no live crypto record.

### 4. CryptoTrade (EMNLP 2024, arXiv 2407.09546)
- **Code:** https://github.com/Xtra-Computing/CryptoTrade (last push December 2024)
- **What it is:** several LLM agents (market analyst, news analyst, trader, reflection) decide trades.
- **Live trading?** No, it only backtests. It also needs a paid LLM API.
- **Could it trade PEARL?** No.
- **Related:** FS-ReasoningAgent (arXiv 2410.12464, code at github.com/Persdre/FS-ReasoningAgent) also only backtests.

### 5. crypto-reflex / crypto_balancer (best premade threshold rebalancer)
- **Code:** PyPI `crypto-reflex`, GitHub draczer01/Crypto_Reflex. A related tool is hammertoe/crypto_balancer, which uses CCXT.
- **What it is:** you set target percentages and a threshold % in config.ini, and it buys or sells to get back to target. It does a dry run unless you pass `--trade`, and it comes with a cron example.
- **Fully done?** Yes, as a small tool.
- **Could it trade PEARL?** Only if its exchange setting accepts Coinbase or BigONE. The examples show Binance only.
- **Evidence:** none; it is a tool, not a strategy. The last release is about 2 years old, it has one maintainer and about 21 downloads a month.
- **Other premade rebalancers I saw:**
  - kraken-rebalance-bot: Kraken only, and PEARL is not on Kraken.
  - pionex_py: Pionex only.
  - koyadovic/binance-rebalancing: Binance only.
  - timdoubleg/crypto-index-bot: Binance only.
  - miguelvazsilva bot: has hardcoded email credentials in its code, so don't reuse it.
  - Saga-Labs and 0xRozier: on-chain bots, not for an exchange like BigONE or Coinbase.

### 6. jordantete/grid_trading_bot
- **Code:** https://github.com/jordantete/grid_trading_bot (MIT licence, about 50 stars). It does backtest, paper and live trading on any CCXT exchange.
- **Evidence:** none published. Also, grid trading has zero expected value before fees (arXiv 2506.11921) and negative after fees.

### 7. Dynamic Grid Trading (arXiv 2506.11921)
- **Code:** https://github.com/colachenkc/Dynamic-Grid-Trading. SOTAVerified marks code as available; I could not open the repo itself.
- **What it is:** backtest code only, no live trading.
- **Evidence:** the authors report 60-70% a year on BTC and ETH from January 2021 to July 2024. That is their own result, not repeated by anyone else, and the fee rate is unclear.

### 8. Multi-pair reinforcement-learning trading (arXiv 2606.04574 / SSRN 6825378)
- **Code:** https://github.com/damianlebiedz/pair-trading-with-rl
- **What it is:** a full replication package, backtest only.
- **Could it trade PEARL?** No. Pairs trading needs a partner coin that moves with PEARL.

### 9. AI-Trader (HKUDS, arXiv 2512.10971)
- **Code:** https://github.com/HKUDS/AI-Trader, which has a crypto module.
- **What it is:** a live benchmark where LLM agents trade. It needs paid OpenAI, Alpha Vantage and Jina keys.
- **Evidence:** in a related live contest (17 October to 3 November), only 2 AI models ended with positive returns.

### 10. Other academic code (backtest only)
- PGPortfolio (arXiv 1706.10059): uses old TensorFlow 1.x.
- XDRL-for-finance (arXiv 2407.14486).
- BTC/XRP DQN comparison (arXiv 2505.07660).
- SYMBA (arXiv 2402.10803).
- Orchestration Framework (arXiv 2512.02227): +8.39% on BTC over 17 days.
- SSRN 5048674 volatility forecasting.
- Zenodo replication packages.
- arXiv 2609.34510 says its code is public, but I could not find the repo.

### Frameworks with no strategy included
- **Jesse:** MIT licence, about 8,000 stars, does backtest, paper and live trading. I found no live results.
- **QuantConnect LEAN:** only a crypto template file; no complete premade crypto strategy.
- **vectorbt / backtrader:** backtesting libraries only.
- **Kaggle:** the notebooks are 3-7 years old, BTC only, and none is a complete runnable bot.

## Bottom line
1. **Premade software that works today and could trade PEARL:** Freqtrade, Hummingbot, crypto-reflex and grid_trading_bot. All four are tools. None comes with a strategy proven profitable on a small coin.
2. **Academic papers with code:** all only backtest, mostly on BTC and ETH, and none is ready to trade PEARL live.
3. **No system I found has an audited live track record.**
4. **Closest fit for "premade, fully done":** crypto-reflex (a threshold rebalancer) or Hummingbot's premade market-making strategy. For either one, support for Coinbase or BigONE still has to be confirmed.
