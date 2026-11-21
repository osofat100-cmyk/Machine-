# Agent 4 findings - Kaggle / Colab (plus GitHub, PyPI, Papers With Code, arXiv where Kaggle searches led there)

20 extended web searches. Filter used: is it a COMPLETE trading system (gets prices, decides buy/sell, backtests, can place real orders)? A price-prediction model with no buy/sell logic does not count.

## 1. Freqtrade + Freqle strategy library
- URL: https://github.com/freqtrade/freqtrade (57.1k stars), strategies https://github.com/freqtrade/freqtrade-strategies, index https://freqle.org/
- What it does: open-source Python bot. Data download, strategy logic, backtesting, dry-run (paper), live trading via CCXT, Telegram/web UI control. Latest release 2026.10 (30 Oct 2026, PyPI).
- Premade strategies: official repo has Strategy001-005, Diamond, Supertrend, Bandtastic and more. The repo itself says they are "provided as-is", "mostly a starting point", backtest them on your own exchange and pairs first.
- Freqle indexes ~15,000 community strategies, ranks them with sandbox backtests + lookahead and robustness checks. Top entries: NotAnotherSMAOffsetStrategyHO +117% (score 95.0), DS_BNC_EV1E_5m +93.8% (score 94.9). Per-strategy pages show ugly months, e.g. Risk_Lev3 has a ~-38% month and ~-63% worst 3 months despite a high score.
- Evidence: backtest only. No independent live-verified result found. Best live-ish report (from earlier round): +4.93% over 67 days dry-run, author said "nowhere near a track record". A GitHub showcase claims B434BestFT +511% with -1.7% drawdown, code not published, nobody verified.
- Can it trade PEARL: yes in principle. BigONE is in CCXT (REST only, no WebSockets); Coinbase is supported. Fine for 1-minute or slower strategies.
- Fully done: the bot yes. A strategy tuned for PEARL no - any Freqle strategy was built on other pairs.

## 2. Hummingbot (market making)
- URL: https://github.com/hummingbot/hummingbot , docs https://hummingbot.org/docs/
- What it does: open-source market-making client. Built-in strategies: simple_pmm (pure market making), simple_xemm (cross-exchange market making), v2_funding_rate_arb, v2_directional_rsi. Docker install. Mirror updated Sep 2026.
- Evidence: one 7-day $200 Binance test +$12.40 gross -> +$5.58 net; another test lost $16.50. An academic paper claimed positive alpha in simulation only. No long live record.
- Can it trade PEARL: Coinbase connector exists. BigONE connector not confirmed. Market making on a thin book (~$50K depth on Coinbase) with our cost is risky.
- Fully done: yes, the strategies run as shipped. Not a rebalancer.

## 3. OctoBot
- URL: https://github.com/Drakkar-Software/OctoBot , https://www.octobot.cloud/ , PyPI octobot 2.1.1 (29 Mar 2026), GPL-3.0
- What it does: GUI bot with grid, DCA, AI, TradingView-signal, crypto basket, market-making modes. Backtesting, paper and live, 15+ exchanges.
- Evidence: none. Only vendor marketing ("excels in its performance").
- Can it trade PEARL: maybe via its CCXT layer; BigONE support not confirmed.
- Fully done: yes, built-in strategies usable as-is.

## 4. Ready-made rebalancing bots on GitHub (closest to the earlier debate's pick)
- hammertoe/crypto_balancer https://github.com/hammertoe/crypto_balancer - pip-installable script, connects to an exchange, trades back to set ratios when drift passes a threshold. Uses CCXT.
- miguelvazsilva/binance-portfolio-rebalancing-bot https://github.com/miguelvazsilva/binance-portfolio-rebalancing-bot - threshold rebalancer, Binance only.
- ztomsy/rebalancer https://github.com/ztomsy/rebalancer - rebalancer with dry-run, backtesting, portfolio optimization.
- Saga-Labs/rebalancer https://github.com/Saga-Labs/rebalancer - Node.js, CoW Protocol on Base, tracks performance vs HODL, Telegram alerts, configurable threshold. On-chain only, not CEX.
- 556isback/anotherRebalancer https://github.com/556isback/anotherRebalancer - dynamic weights, threshold param, optional PyPortfolioOpt.
- timdoubleg/crypto-index-bot https://github.com/timdoubleg/crypto-index-bot - top-10 market-cap index on Binance (not for a single coin).
- Shannon's demon: only a GitHub topic tag found, no dedicated maintained repo.
- Evidence: no published live results for any of them. Several repos are old; activity unchecked.
- Can it trade PEARL: crypto_balancer and ztomsy (CCXT) probably yes with a config change (pair PEARL/USDT or PEARL/USD, target 20/80, threshold). Binance-only ones no.
- Fully done: yes as code; needs config only (which pair, which ratio, which threshold).

## 5. Jesse
- URL: https://github.com/jesse-ai/jesse (8.8k stars), https://jesse.trade/
- What it does: Python framework, backtesting with no look-ahead, Monte Carlo, optimization, live trading (live plugin was paid/closed in earlier reports).
- Premade strategies: no. A review says "there aren't pre-built templates you can just plug and play"; only an example golden-cross strategy.
- Evidence: none.
- Fully done: framework yes, strategy no. Fails the premade rule unless we accept the example strategy.

## 6. cryptobots (PyPI)
- URL: https://pypi.org/project/cryptobots
- What it does: package with pre-built breakout bot and EMA-crossover bot; page shows backtests on ETH.
- Evidence: backtest only, small unknown project.
- Can it trade PEARL: unknown exchange support.

## 7. FinRL_Crypto / FinRL-X / TensorTrade (reinforcement learning)
- FinRL_Crypto https://github.com/AI4Finance-Foundation/FinRL_Crypto - PPO/A2C/DDPG/TD3/SAC on Binance data, built around reducing backtest overfitting (paper arXiv 2209.05559, Gort et al.).
- FinRL-Trading / FinRL-X https://github.com/AI4Finance-Foundation/FinRL-Trading - backtest + Alpaca paper trading.
- inoue0406/CryptoBot-FinRL https://github.com/inoue0406/CryptoBot-FinRL - multi-crypto Binance script.
- TensorTrade https://github.com/tensortrade-org/tensortrade v1.0.4 (Feb 2026). Its own experiment log (BTC/USD, PPO, 16 Sep-16 Oct 2025): EVERY configuration lost money, best -$748; README: +$239 at 0% commission but -$650 at 0.1% commission vs -$355 buy-and-hold; "commission costs currently exceed prediction profits".
- Can it trade PEARL: no - would need retraining on PEARL, which is not premade.
- Fully done: research code. Not ready for live use.

## 8. Kaggle notebooks
- Building an Bitcoin Trading Strategy https://www.kaggle.com/code/yanmaksi/building-an-bitcoin-trading-strategy - has bot code + trade analysis, private dataset.
- PPO Reinforcement Learning Trading Agent https://www.kaggle.com/code/mahdikhodarahimi/ppo-reinforcement-learning-trading-agent
- Bitcoin Value-Based RL (DQN/DDQN/Dueling) https://www.kaggle.com/code/alincijov/bitcoin-value-based-reinforcement-learning
- Deep RL for Trading (crypto hourly 2017-2023) https://www.kaggle.com/code/franoisgeorgesjulien/deep-reinforcement-learning-for-trading
- Automated Portfolio Rebalancing https://www.kaggle.com/code/pranshujayswal/automated-portfolio-rebalancing - rebalancing vs buy-and-hold, not crypto data.
- ML BTC Prediction & Trading Strategy Backtest https://www.kaggle.com/code/albertoburchi/ml-btc-prediction-trading-strategy-backtest
- Momentum Trading Strategy https://www.kaggle.com/code/mburakergenc/applying-evaluating-a-momentum-trading-strategy
- Backtesting of Moving Averages https://www.kaggle.com/code/stacknishant/backtesting-of-moving-averages-on-price-series
- Crypto-portfolio Optimization series (G-Research data) https://www.kaggle.com/code/federicominutoli/crypto-portfolio-optimization-training-test-split
- Evidence: all backtests on BTC/ETH or other data; snippets only, contents not fully checked.
- Can it trade PEARL / fully done: no. None has live-trading hooks; all are educational. None meets "premade and fully done".

## 9. Kaggle competitions
- G-Research Crypto Forecasting: top 3 all LightGBM; 1st (Meme Lord Capital) code not found; 2nd (Maddux) refused to publish code; 3rd per-coin LightGBM. https://www.gresearch.com/news/wrapping-up-the-g-research-crypto-forecasting-competition/
- DRW Crypto Market Prediction (2025): 1st place MLP + autoencoder ensemble, writeup only https://www.kaggle.com/competitions/drw-crypto-market-prediction/writeups/drw-solution-1st
- These are forecasting scores (correlation), no buy/sell logic, anonymized features. Not trading systems. Cannot trade PEARL.

## 10. Google Colab
- Top Colab results were promotional "review" pages for AI trading platforms (Bellaro Forge GPT, Kestrel Fundast, Eisen Peak, Xavelytrium) - marketing, not code. Treat as spam.
- Real ones: Alpaca crypto-trading-basic.ipynb (Alpaca broker only), FinRL tutorials (stocks). kamsec/crypto-bot https://github.com/kamsec/crypto-bot - Binance LSTM bot trained in Colab, Python 3.7, old.
- Can trade PEARL: no.

## 11. PLUTUS Open Source (arXiv 2505.14050)
- https://github.com/algotrade-plutus - reproducibility standard + reference strategies ProtoSmartBeta, ProtoMarketMaker. Third-party summary: out-of-sample results "honestly negative". Vietnamese stock-market focus.

## Dead / do not use
- Zenbot: archived, last commit Feb 2022, last release 2018.
- Gekko: discontinued (archived 2020), last release Dec 2018; sites selling "Gekko" are suspect.

## My bottom line
Only three things are premade, fully done AND could plausibly point at PEARL today:
1. A CCXT rebalancing bot (hammertoe/crypto_balancer or ztomsy/rebalancer) - config only.
2. Freqtrade with a stock strategy from its repo/Freqle - config only, but strategies were built on other pairs; backtest-only evidence.
3. Hummingbot pure market making on Coinbase - runs as shipped, risky on a thin book.
No system anywhere in my search has verified live profits. Kaggle/Colab contain no complete live trading system.
