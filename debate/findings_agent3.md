> Pasted unchanged by the coordinator: Agent 3's own file write was blocked, so it returned this text and asked for it to be saved as-is.

# Agent 3 findings - PyPI / npm / HuggingFace / Docker Hub

20 web searches across PyPI, npm, HuggingFace, Docker Hub, plus SourceForge, GitHub and Papers With Code where those sites pointed. Question asked of every find: can you install it and run it with a strategy already inside, and can it trade PEARL (BigONE PEARL-USDT or Coinbase PEARL-USD)?

Bottom line first: nothing on these sites lets you install one package and trade PEARL with a premade strategy that has verified results. No find below has independent, verified live performance. All numbers quoted are the authors' own claims.

## 1. OctoBot - `pip install OctoBot` (also Docker, desktop download, DigitalOcean)
- URL: https://pypi.org/project/OctoBot (2.0.9, Python >=3.10, GPL-3.0); GitHub Drakkar-Software/OctoBot
- What it does: strategies shipped as "tentacles": DCA, Grid, Crypto Basket (set weights, rebalances by rules you set), Market Making, AI/ChatGPT/Ollama, TradingView alerts, technical indicators. Backtesting built in.
- Fully done? Yes - install, add keys, pick strategy, run. Older PyPI pages say tentacles install separately via the launcher; not confirmed whether pip alone brings them.
- Exchanges: "15+" via CCXT (own claim). No full list found. BigONE and Coinbase not confirmed.
- Can it trade PEARL? Probably, if BigONE or Coinbase is supported. Not confirmed.
- Evidence: none independent. Paid cloud tier ~$9.99/month (third-party, unverified).
- Rank: best candidate on these sites. Crypto Basket is the closest premade thing to rebalancing.

## 2. Freqtrade - `pip install freqtrade` (Docker freqtradeorg/freqtrade)
- What it does: framework with backtesting, dry-run, live, Telegram/web UI, hyperopt.
- Fully done? Partly. Strategies are separate .py files: official freqtrade/freqtrade-strategies ("educational purposes only"), community repos pandianmn/freqtrade-strategies, nateemma/strategies, darkvolg/Trading (docs: mostly not maintained by the Freqtrade team).
- Exchanges: CCXT. BigONE untested, Coinbase likely.
- Can it trade PEARL? Yes in principle.
- Evidence: Substack dry-run +4.93% / 67 days (author: not a track record). DEV tutorial 67.9% win rate (backtest). Patreon "291% profit" (backtest). No verified live records.

## 3. Hummingbot - Docker or source (github.com/hummingbot/hummingbot, Apache 2.0)
- What it does: Pure Market Making, Cross-Exchange MM, AMM Arbitrage; V2 Controllers and Scripts. Pure MM has `inventory_target_base`, which skews order sizes back toward a target ratio (built-in rebalancing behaviour).
- Fully done? Yes for market making.
- Exchanges: Coinbase supported; BigONE not listed.
- Can it trade PEARL? Yes on Coinbase PEARL-USD (thin book).
- Evidence: 7-day Binance test +$12.40 gross / +$5.58 net on $200; another test -$16.50. arXiv 2204.13265 is simulation only.

## 4. OpenTrader - `npm install -g opentrader` (github.com/Open-Trader/opentrader)
- What it does: built-in Grid, DCA, RSI (older note: cross-exchange arbitrage); web UI; paper trading; backtesting.
- Fully done? Yes. Needs Node.js 22+.
- Exchanges: "100+ via CCXT" (own claim). BigONE and Coinbase likely, not confirmed.
- Can it trade PEARL? Probably.
- Evidence: none. Beta 1.0.0-beta.25, ~2.8k stars, weekly downloads 51-6.5K. Old note: UI once in a private repo.

## 5. CryptoBots - `pip install cryptobots` (0.2.0)
- Premade EMA crossover and breakout bots, CLI. Fully done. Exchanges not confirmed. PEARL unknown. No evidence. Small, maintenance unknown.

## 6. crypto-balancer - `pip install crypto-balancer` (3.1.1; fork crypto-reflex)
- What it does: threshold rebalancing to target ratios. Threshold = RMS distance from targets (sample 2.0); only trades if the result is better balanced. Dry-run and force options.
- Fully done? Yes.
- Exchanges: Binance only in docs. No CCXT/Coinbase/BigONE found.
- Can it trade PEARL? No as shipped. Needs an exchange change (user approval).
- Evidence: none.
- Similar: portfolio-balancer (Binance), kraken-rebalance-bot (Kraken), koyadovic/binance-rebalancing (Binance), Hodlerhacks Balance Bot (open source per CoinCodeCap, repo not confirmed).

## 7. DeepAlpha Bot - `pip install deepalpha-bot`
- LSTM + LightGBM, Triple Barrier, SHAP, HMM regimes; 26 USDT perps on Bybit/Bitget/Hyperliquid.
- Can it trade PEARL? No (perps, wrong exchanges).
- Evidence: self-reported 64.9% direction accuracy (not profit). Related stefanoviana/deepalpha claims 84.6%/70.9%, may be a different project. Copy-trading upsell.

## 8. PowerTrader_AI - git clone (garagesteve1155, 736 stars, Apache 2.0; SourceForge mirror)
- kNN/kernel predictor (1h-1w) + tiered DCA (max 2/24h) + trailing profit. Robinhood original; Binance fork (Ibrahim-3d). No CCXT. PEARL: no without porting. Evidence: none.

## 9. Other PyPI / npm / SourceForge
- QTradeX: framework, "100+ exchanges" via CCXT, strategies in companion repo.
- CryptoTradeBot: Kraken spot CLI. ohheycrypto: TA bot, BTC/USDT default. quick-trade: CCXT system, README examples. GeneBot, Pythoncoin, Botic: frameworks. Cryptohopper SDK: client for paid service.
- npm: SockTrader, Bitfox, Clawtrade (Binance/Bybit/OKX), bot18 (2018, dead).
- Jesse: framework only, live plugin paid; "Jesse Bot 2026 AI" SourceForge pages look like marketing.
- Superalgos: visual designer, community strategies only. GoCryptoTrader: engine.
- None premade + PEARL-ready + verified.

## 10. Docker Hub
- freqtradeorg/freqtrade (see #2); pantelis98765/crypto-bot (grid+DCA, Binance/Crypto.com, paper mode); iloveitaly/crypto-index-fund-bot (index basket, rebalance not confirmed); royen99/cryptobot-trader (Coinbase); 5879/spot-trading-bot (Binance); pkumaschow/cryptotrader (Kraken); dodancs/profit-trailer (paid); scionaltera/arbitrader (arbitrage). No rebalancer, no verified results.

## 11. HuggingFace
- Lukeed/Predictor-Models (XGBoost/LSTM/Transformer/GARCH, Feb 2026), cloudqi/crypto_trading_insights, DaProgammer/crypto_radar_brain ("educational only"), duonlabs/apogee-nano-2.4M-base, tahamajs Qwen-GRPO BTC variants, CryptoGAT paper.
- None are trading bots: no exchange connection, no orders, no money management, no PEARL.

## 12. Papers With Code / arXiv code
- FinRL / FinRL_Crypto: research framework (`pip install -e .`), now points to FinRL-X; you train your own agent.
- arXiv 2109.14789, 2505.07660, 2309.00626, 1911.08647, 2505.14050: research code, not ready bots.

## Summary
| # | Name | Install | Premade strategy | PEARL | Evidence |
|---|------|---------|------------------|-------|----------|
| 1 | OctoBot | pip/Docker | DCA, Grid, Basket, MM, AI | Probably | None |
| 2 | Freqtrade | pip/Docker | Separate files | Yes (CCXT) | +4.93%/67d dry-run (self) |
| 3 | Hummingbot | Docker/source | MM, arbitrage | Yes (Coinbase) | +$5.58/7d on $200 (self) |
| 4 | OpenTrader | npm | Grid, DCA, RSI | Probably | None, beta |
| 5 | CryptoBots | pip | EMA, breakout | Unknown | None |
| 6 | crypto-balancer | pip | Threshold rebalance | No (Binance) | None |
| 7 | DeepAlpha | pip | ML ensemble | No (perps) | 64.9% acc (self) |
| 8 | PowerTrader_AI | clone | kNN + DCA | No | None |
| 9 | FinRL | clone | Framework | Custom only | None |
| 10 | HF models | various | Models only | No | None |

## Position
- Most premade and fully done, with PEARL possible: OctoBot (Crypto Basket or Grid/DCA), then OpenTrader (Grid/DCA), then Hummingbot on Coinbase (market making).
- The exact rebalancer (crypto-balancer) is Binance-only, so using it for PEARL needs a change the user has to approve.
- Still open: are BigONE or Coinbase on OctoBot's exchange list, and does OpenTrader's CCXT route work on BigONE? Nothing here has verified results, so any pick should go through the repo's sealed one-minute-at-a-time test first.
