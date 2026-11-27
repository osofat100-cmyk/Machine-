# Agent 6 findings - SSRN / Google Scholar / ResearchGate (plus arXiv, GitHub, PyPI links found from them)

20 web searches. Filter: does the paper or project come with code you can download and run?

## Short answer
- No paper, no open-source bot and no premade strategy has verified, profitable live crypto trading over 6+ months.
- SSRN and ResearchGate crypto trading papers almost never link runnable code. The runnable code is on arXiv-linked GitHub repos.
- No PapersWithCode leaderboard exists for crypto trading (the "Algorithmic Trading" task lists 0 benchmarks).
- The only paper that tested methods with real money (arXiv 2609.34510): median live return -0.56% while the market rose 11.63% (2026-08-24 to 2026-09-21).

## A. Papers that come with code

1. Can AI Make Money in Crypto? Measuring the Gap from Backtests to Real Markets (arXiv 2609.34510)
   - Code: https://github.com/Starlien95/Awesome-TradingAI
   - Does: benchmark of ML, RL, LLM and agent trading methods in 3 stages: backtest, exchange paper trading, live trading.
   - Runnable: yes (Python codebase).
   - Live: yes, 4 methods deployed with real money. Median live -0.56% vs market +11.63%. Even the best live method did not beat the market. 3 of 4 earned less live than in paper trading, worst gap 6.38 points. Price difference 0.31 per mille paper -> 1.86 per mille live. Execution latency ~39 s -> ~47 s.
   - Conflict: the README still lists real-money live evaluation as "Coming Soon".
   - PEARL: a research benchmark, not a bot for a user. Fully done as a benchmark, not as a trading system.

2. FinRL_Crypto (AI4Finance; paper arXiv 2209.05559 "Deep RL for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting")
   - Code: https://github.com/AI4Finance-Foundation/FinRL_Crypto (also Burntt/FinRL_Crypto, the "most implemented" crypto paper on PapersWithCode)
   - Does: deep RL agents (PPO, A2C, DDPG etc.) on Binance 5-minute candles, with a method to reject overfit agents.
   - Runnable: yes, Python.
   - Live: no. Backtest only; claims tested on 10 coins and a crash period (repo's own claim, not verified).
   - Main FinRL (github.com/AI4Finance-Foundation/FinRL, ~12K stars): live trading is "Basic Alpaca support" (stocks); users sent to FinRL-X / FinRL-Trading for live. Third-party review: "not a turnkey trading bot".
   - PEARL: Binance data only, no PEARL. Would need data + exchange changes. Not fully done for PEARL.

3. Dynamic Multi-Pair Trading Strategy in Crypto with Deep RL (arXiv 2606.04574, June 2026)
   - Code: https://github.com/damianlebiedz/pair-trading-with-rl
   - Does: PPO + LSTM pair trading on Binance USD-M futures, 1-hour bars. Train 2024, out-of-sample 2025.
   - Live: no, backtest only.
   - PEARL: futures pairs, needs two correlated coins and shorting. Not usable on PEARL spot.

4. Dynamic Grid Trading Strategy: From Zero Expectation to Market Outperformance (arXiv 2506.11921, June 2025)
   - Code: https://github.com/colachenkc/Dynamic-Grid-Trading
   - Does: grid that recenters on breaks (full capital on upside break, only profits on downside break). Proves a static grid has zero expected value before fees.
   - Live: no. Backtest BTC/ETH Jan 2021 - Jul 2024, by its own authors, 60-70% IRR claimed, fee assumptions unclear.
   - PEARL: logic works on any price series; code is a backtest, not a live bot. Not fully done for live use.

5. CryptoTrade: A Reflective LLM-based Agent for Zero-shot Crypto Trading (arXiv 2407.09546, EMNLP 2024, revised Aug 2026)
   - Paper says "our code and data are available". Repo URL not confirmed in my searches.
   - Does: LLM agent using on-chain + off-chain (news) data.
   - Live: no, backtest.
   - PEARL: needs an LLM API and news/on-chain data. Not fully done for PEARL.

6. Others with code but weak fit
   - Bitcoin vs XRP DRL comparison (arXiv 2505.07660): DQN variants, code on GitHub, backtest only.
   - SYMBA multi-agent RL market simulator (arXiv 2402.10803): simulates a market, not a trading bot.
   - Spot-perpetual basis trading, dynamic collateral (arXiv 2605.05089): notebooks public; needs perpetual futures, PEARL has none.
   - CTREND trend factor (arXiv 2611.01951): partial repo, missing restricted CoinMarketCap inputs.
   - WebCryptoAgent (arXiv 2601.04687): "code will be available" (future tense), check if populated.
   - FinRL Contests 2023-2025 (arXiv 2501.10709): starter kits and team solutions on GitHub; backtests.

7. SSRN / ResearchGate items with NO code found
   - Liu & Kang, "Automated Cryptocurrency Trading Approach Using Ensemble Deep RL: Learn to Understand Candlesticks" (SSRN 4348791; Expert Systems with Applications). BTC/USDT, 30-day bull + 15-day bear test. No code link found.
   - Fang et al., "Cryptocurrency Trading: A Comprehensive Survey" (arXiv 2003.11352, Financial Innovation 2022): surveys 118-146 papers. No code repo.
   - "Cryptocurrency trading: A systematic mapping study" (ResearchGate 380296535): no code.
   - "Cryptocurrencies trading algorithms: A review" (Journal of Forecasting 2022): no code.
   - "Trading Bot for Cryptocurrency Market Based on Smart Price Action Strategies" (ResearchGate/Scribd): design described, no repo.
   - Theseus thesis "Automated cryptocurrency trading system": working bot built, no download.

## B. Premade open-source systems these searches led to

8. Freqtrade - https://github.com/freqtrade/freqtrade
   - ~57K stars, Python, ccxt-based, latest release 2026.10 (30 Oct 2026). Backtest, hyperopt, FreqAI, dry-run, live.
   - Fully done as software: yes. Fully done strategy: no. Sample strategies are for learning.
   - Evidence: nateemma/strategies says most of its strategies are profitable "but nowhere near market returns". A Sept 2026 Substack "+983% in 6 years" strategy: own out-of-sample split CAGR 105.03% -> 3.65%. SampleStrategy on Freqle: -90.1% in a 2021-2025 backtest, profit factor 0.82. NostalgiaForInfinity (most famous community strategy): no published live results; backtests only in commit comments. FrequentHippo Grafana dashboard shows dry/live runs of many strategies (contents not checked).
   - PEARL: ccxt supports BigONE (REST only) and Coinbase, so it can trade PEARL with a config change (exchange + pair). Strategy choice still open.

9. OctoBot - https://github.com/Drakkar-Software/OctoBot
   - ~7K stars, GPL-3.0, built-in Grid, DCA, AI, TradingView strategies, 15+ exchanges.
   - Evidence: vendor's own table: "Lite Bitcoin" $1,000 -> ~$886 in 6 months. GNcrypto 2026 hands-on test on Binance spot: 5 trades, ~$7 PnL, bot kept buying above its upper bound. Testimonial of 1000% in 2021 is anecdote.
   - PEARL: exchange support for BigONE not confirmed.

10. Hummingbot - https://github.com/hummingbot/hummingbot
   - ~19K stars, market making + arbitrage, CEX and DEX.
   - Evidence: no independent audited P&L. Own blog infers success from ~40% of users still running after 1 month (retention, not profit). Short self-reported tests (3 days, 12 hours).

11. Jesse - https://github.com/jesse-ai/jesse
   - ~6.5K stars. Framework only, no proven strategy. Community repos (gabrielweich/jesse-strategies, ysdede/jesse_strategies) have no backtest/live P&L in results. Live plugin closed-source and paid.

12. QuantConnect LEAN - https://github.com/QuantConnect/Lean
   - ~16K stars. Vendor claims 375,000+ live strategies deployed since 2012 (not verified). Old forum reports of crypto live bugs (wrong Bitfinex balances, no crypto futures).

13. Superalgos (~5.7K stars, Apache 2.0): visual builder, no built-in strategies, no performance data found.

14. Dead: Gekko (archived, last push Feb 2020). Zenbot (no recent commits). HaasOnline announced shutdown 9 Jul 2024.

## C. Premade rebalancing bots (closest to "fully done" for one coin + stablecoin)

15. 556isback/anotherRebalancer - https://github.com/556isback/anotherRebalancer
   - MIT, Python, ccxt, weight-difference threshold rebalancing.
   - PEARL: ccxt means BigONE/Coinbase possible. Changes needed: exchange name, PEARL/USDT or PEARL-USD pair, target weights, threshold. No performance data.

16. crypto-reflex (PyPI) - https://pypi.org/project/crypto-reflex
   - Threshold rebalancing with config.ini, Binance, sample uses USDT. PEARL: Binance only as shipped.

17. Saga-Labs/rebalancer - https://github.com/Saga-Labs/rebalancer
   - Node.js, Base chain via CoW Protocol, 3% threshold, $3 min trade, 4-hour checks, tracks vs HODL, Telegram. DeFi only, not BigONE/Coinbase.

18. 0xRozier/rebalancing-bot - https://github.com/0xRozier/rebalancing-bot
   - ±2% bands, ±5% emergency, circuit breaker after 15% drop in 1 hour. DeFi only.

19. miguelvazsilva/binance-portfolio-rebalancing-bot, wallbeach/CRIBot (crypto.com index), timdoubleg/crypto-index-bot (Binance top-10): exchange-locked.

20. Shrimpy (commercial, its own backtests): Bittrex study median +60% vs hold for monthly rebalancing, 85% of portfolios beat hold; self-reported, multi-coin, 2017-2019 era. One outside 50/50 BTC/USD test: 20% threshold -19.26% vs -29.04% without rebalancing (both losses).

## D. Real-money experiments found on GitHub (honest negatives)
- kalambyryura/ai-trading-arena: 7 weeks real money on OKX perps by AI agent teams: -1.65 USDT net on 86 trades, price moves earned +0.07, fees were 24x the gross result, "no edge found".
- thearbajonart/survival-of-the-profitable: 100 rule bots on BTC/ETH/SOL paper money, 10 of 100 made money in both halves and beat random entries (33-day replay).
- yunuhkei/trading-bot: BTC 1m-1h short-term trading "no better than random", even with zero fees.
- wwwlqh/cryptobot: 5,384 real Polymarket up/down trades Jul-Aug 2026 (not spot altcoins).

## E. My ranking for PEARL (premade + fully done + could run on PEARL)
1. Freqtrade - most complete, maintained, ccxt to BigONE/Coinbase. Change needed: config (exchange, pair). Strategy still unproven.
2. 556isback/anotherRebalancer - simplest premade thing that matches a PEARL/stablecoin split. Changes needed: exchange, pair, weights, threshold. No track record.
3. OctoBot - premade grid/DCA ready, but vendor's own example lost money and BigONE support unconfirmed.
Nothing found is "download and profit". Papers with code are research backtests, not ready bots.
