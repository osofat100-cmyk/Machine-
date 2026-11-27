# Live public AI trading arenas and prediction-market LLM trading benchmarks (2025 to Nov 2026)

Notes compiled 2026-11-24. Labels used throughout:
- **[OFFICIAL]** = from the operator's own site/paper/official account (as rendered by fetch; some via a third party quoting the official page, flagged where so).
- **[PRESS/3P, UNVERIFIED]** = press, blogs, aggregators, competitor sites. Listed for completeness; do not treat as proof.
- Real money vs paper money is stated for every arena.

## Alpha Arena by Nof1 (Season 1 crypto perps, Season 1.5 US stocks, later seasons)

### Takeaway
Alpha Arena is the only well-known arena run with real money on-chain (Hyperliquid), but Nof1 never published an official final per-model table for Season 1 on its pages; the widely cited numbers (Qwen3-Max about +22.3% winner, DeepSeek V3.1 about +4.9%, the four US models all losing, GPT-5 last) come from a founder X chart and press, and two different sets of loser figures circulate. Season 1.5 (US stock tokens, 8 models x 4 competitions) was won by the "Mystery Model" revealed as Grok 4.20 (+12.11% aggregate per the site); no Season 2 had run or published results as of Nov 2026, and the winner changed from a Chinese open-weight model (Qwen) to a US closed model (Grok) between the two seasons.

### Cited Findings
**Season 1 rules / methodology**
- Six models: GPT-5, Gemini 2.5 Pro, Claude Sonnet 4.5, Grok 4, DeepSeek V3.1, Qwen3-Max; same system prompt, same user-prompt template, same numeric data, default sampling, no news, no fine-tuning; all at highest reasoning setting except Qwen3-Max (as summarized from Nof1's 27 Oct 2025 writeup "Exploring the Limits of Large Language Models as Quant Traders") — [Moby guide summarizing Nof1 writeup](https://moby.win/learn/alpha-arena/) [3P summarizing OFFICIAL]
- "No person placed orders"; outputs were long/short/hold/close with a reason, 0-1 confidence, size, leverage and exit plan; decisions roughly every 2-3 minutes; $10,000 real money each on Hyperliquid; assets BTC, ETH, SOL, BNB, DOGE, XRP perps; season ran through 3 Nov 2025, 5:00 pm ET — [Moby](https://moby.win/learn/alpha-arena/) [3P summarizing OFFICIAL]
- Nof1's writeup itself does not publish a final ranking or ending balances and says a single run should not crown a permanent best trading model — [Moby](https://moby.win/learn/alpha-arena/) [3P summarizing OFFICIAL]
- Behavioral profiles from the official writeup (early run, not final results): Qwen3-Max largest sizes, highest confidence, tightest exits; Gemini 2.5 Pro most trades and frequent shorting; Grok 4 fewest trades, loose exits; Claude Sonnet 4.5 rarely shorts; GPT-5 lowest confidence, which Nof1 says did not track results — [Moby](https://moby.win/learn/alpha-arena/) [3P summarizing OFFICIAL]
- Dates: 18 Oct to 3 Nov 2025 per TradeRank (competitor site) — [TradeRank vs Alpha Arena](https://www.traderank.ai/traderank-vs-alpha-arena) [3P]; 17 days per press — [GNcrypto](https://www.gncrypto.news/news/qwen-wins-alpha-arena-season-1-with-22-percent-returns/) [PRESS]

**Season 1 per-model final returns ($10,000 start, real money)** — no official Nof1 table found; two conflicting sets circulate:
- Set A (attributed to the Nof1 founder's end-of-season chart on X): Qwen 3 Max +22.32% ($12,231.82); DeepSeek V3.1 +4.89% ($10,489.08); Claude Sonnet 4.5 -30.81% ($6,918.88); Grok 4 -45.30% ($5,469.66); Gemini 2.5 Pro -56.71% ($4,329.31); GPT-5 -62.66% ($3,733.54) — [Thortradecopier, citing founder X chart](https://thortradecopier.com/blog/can-chatgpt-trade-for-you) [3P, UNVERIFIED]; Qwen $12,231.82 / 22.32% also in [GNcrypto](https://www.gncrypto.news/news/qwen-wins-alpha-arena-season-1-with-22-percent-returns/) [PRESS]
- Set B: Qwen 3 Max +22.31%, DeepSeek V3.1 +4.89%, Claude Sonnet 4.5 -42.01%, Gemini 2.5 Pro -45.55%, Grok 4 -57.92%, GPT-5 -58.74% — [TradeRank alternatives page](https://www.traderank.ai/blog/alpha-arena-alternatives-2026) [3P competitor, UNVERIFIED]. Contradicts Set A on the order of the four losers (Gemini vs Grok) and magnitudes. Both agree: Qwen 1st, DeepSeek 2nd, only those two profitable, GPT-5 last.
- Chinese press: "China models all profitable, US models all lost; GPT-5 lost over 62%" — [ifeng](https://tech.ifeng.com/c/8o0WDHlWzBm) [PRESS]; DeepSeek reportedly peaked around +125% mid-competition before drawing down — reported in search summaries of press [PRESS, UNVERIFIED; no primary found]
- A mid-season SCMP piece reported DeepSeek leading earlier in the run ("DeepSeek outperforms AI rivals in 'real money, real market' crypto showdown") — [SCMP](https://www.scmp.com/tech/tech-trends/article/3329784/deepseek-outperforms-ai-rivals-real-money-real-market-crypto-showdown) [PRESS]; i.e., the leader changed within the season.

**Verifiability (wallets)**
- SCMP: all models' trades were accessible through their respective Hyperliquid wallet addresses — [SCMP](https://www.scmp.com/tech/tech-trends/article/3331425/alibabas-ai-model-outperforms-us-rivals-crypto-trading-showdown) [PRESS]
- Manifold market resolving on Alpha Arena points to hypurrscan.io to verify wallets on-chain (addresses not listed there) — [Manifold](https://manifold.markets/Mo17/what-ai-model-wins-the-alpha-arena) [3P]
- One address surfaced: 0xc20ac4dc4188660cbf555448af52694ca62b0734 for DeepSeek Chat V3.1 (via a DataWallet guide citing Coinglass) — search-result snippet of [DataWallet](https://www.datawallet.com/crypto/alpha-arena-nof1-ai-explained) [3P, UNVERIFIED: page returned 404 on fetch; not checked on hypurrscan]
- Moby's summary of the FAQ: trades are public and positions visible on-chain, but no official wallet-verification procedure is described — [Moby](https://moby.win/learn/alpha-arena/) [3P summarizing OFFICIAL]

**Season 1.5 (US equities)**
- Launched 20 Nov 2025: live trading of US equity tokens on Hyperliquid (trade.xyz) instead of crypto, 8 models, two new entrants Kimi 2 and a stealth "mystery model" — [BlockFlow on X](https://x.com/BlockFlow_News/status/1991387204099375354) [3P]; [Bitget news](https://www.bitget.com/news/detail/12560605072931) [PRESS]; HyperX launched copy-trading of all 8 models — [HyperX on X](https://x.com/hyperx_trade/status/1991714578494054591) [3P]
- Dates 19 Nov to 3 Dec 2025 — [TradeRank vs Alpha Arena](https://www.traderank.ai/traderank-vs-alpha-arena) [3P]. Live board banner (as summarized): "ended on December 3, 2025, at 5:00 p.m. EST", models no longer running — [Moby](https://moby.win/learn/alpha-arena/) [3P quoting OFFICIAL]
- Four parallel competitions (statistical-rigor change): New Baseline (news + memory/self-learning), Monk Mode (capital preservation), Situational Awareness (models see rivals' rankings), Max Leverage (high leverage required) — [ForkLog](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/) [PRESS]. 8 models x 4 = 32 accounts — [Thortradecopier](https://thortradecopier.com/blog/can-chatgpt-trade-for-you) [3P]
- Official site (as summarized): winner Mystery Model "a 12.11% aggregate return in two weeks", "$4,844 in total across competitions"; tickers included NVDA, MSFT, AMZN, GOOGL, PLTR, TSLA, NDX; only the winner's figures published in the summary — [Moby](https://moby.win/learn/alpha-arena/) [3P quoting OFFICIAL]
- Founder X post (Jay Azhang, 5 Dec 2025): "Mystery Model (a.k.a GROK 4.20)" winner, up 12% on average, profitable in all four competitions; GPT-5.1 2nd, Gemini 3 3rd — [ForkLog embedding @jay_azhang post](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/) [OFFICIAL founder post via PRESS]
- Averages over four competitions (leaderboard captured Sept 2026): Grok 4.20 +10.17%, GPT-5.1 -12.09%, Gemini 3 Pro -45.06%, Claude Sonnet 4.5 -50.93%; Qwen 3 Max by competition -6.79%, -20.24%, -41.37%, -82.06%; best single account Grok 4.20 +34.59%, worst Grok 4 -96.15% (both in Situational Awareness) — [Thortradecopier](https://thortradecopier.com/blog/can-chatgpt-trade-for-you) [3P, UNVERIFIED]. It notes an internal inconsistency: site says $4,844 (12.11%) but the four rows sum to about $4,066 (10.16%).
- Caixin: only Grok-4.20 turned a profit by the 3 Dec end — [Caixin Global](https://www.caixinglobal.com/2025-12-15/cover-story-trading-by-algorithm-who-is-responsible-when-ai-calls-the-shots-102393319.html) [PRESS]. Other reported winner figures: +12.11% / $10,000 to $12,193 (AIbase) and 22.38% (MEXC headline) — conflicting, per search summary [PRESS, UNVERIFIED].

**Later seasons**
- As of 12 Nov 2026 alphaarena.ai still showed Season 1.5 with models no longer running; no Season 2 roster or results published; nof1 raised $15M in May 2026 and plans a consumer product; a CoinDesk report mentioned a "Season Two" — [TradeRank vs Alpha Arena](https://www.traderank.ai/traderank-vs-alpha-arena) [3P competitor]
- nof1.ai home page now describes an AI research lab for financial markets and only links to alphaarena.ai; no leaderboard, wallets or season list on it (fetched 2026-11-24) — [nof1.ai](https://nof1.ai/) [OFFICIAL]; nof1.ai/leaderboard returns 404 — [nof1.ai/leaderboard](https://nof1.ai/leaderboard) [OFFICIAL, 404]

### Inferences
- Winner did not persist: Season 1 winner Qwen3-Max (Chinese, closed-weights API model) finished with losses in every Season 1.5 competition (-6.79% to -82.06%, if the 3P capture is right); Season 1 last-place OpenAI family placed 2nd in 1.5 (GPT-5.1) but still lost money on average. Samples are tiny (one 17-day run, one 2-week run), so no skill claim is supportable; Nof1 itself warned against that.
- "Chinese models won" headlines rest on one season and two models; DeepSeek V3.1 is open-weight, Qwen3-Max is not open-weight, so Season 1 was not a clean open-vs-closed result.
- Real money plus on-chain wallets make Alpha Arena the most verifiable in principle, but in practice the per-model final numbers available today are from the founder's chart and third-party captures, not a downloadable official dataset.

### Gaps
- alphaarena.ai returned HTTP 429; could not read the official leaderboard, blog, or wallet list directly. No official per-model Season 1 final table was found; Set A vs Set B conflict unresolved.
- Wallet addresses for 5 of 6 Season 1 models and all Season 1.5 accounts not found; the one DeepSeek address was not checked on a Hyperliquid explorer.
- Full Season 1.5 per-model, per-competition table (all 8 models incl. Kimi 2, DeepSeek, Grok 4) not found from a primary source; Season 1.5 starting capital per account not confirmed officially.
- No primary evidence of any Season 2 run in 2026.

## Other live arenas with published methodology (TradeRank, Prediction Arena, academic live leaderboards) and rank persistence

### Takeaway
TradeRank.ai is the only arena found with many seasons (Seasons 0-11 since Jan 2026, ~4 weeks each), and it is paper money; its own published analysis says rank does not detectably carry over season to season, and its winners rotate across families (MiniMax, Gemini, Kimi, Inkling, Jev, Nemotron...). Academic live benchmarks (Prediction Arena, LiveTradeBench) likewise find reshuffling between phases and near-zero cross-market rank correlation.

### Cited Findings
**TradeRank.ai** (paper money)
- Methodology: $10,000 simulated per model against live prices; 10 major cryptos + 50 large-cap US equities; BTC and SPY benchmarks; daily decisions at 16:00 UTC; 15-minute sweep auto-closes positions whose invalidation price is hit; each position needs a thesis and invalidation_price; equity actions only when US market open; inputs are 4h/daily/weekly candles with 14-period RSI and a deterministic liquidity/momentum screen — [TradeRank home](https://traderank.ai/) [OFFICIAL]
- Prompts, per-decision reasoning and trade logs published; headline numbers downloadable as JSON; simulated fills omit slippage, partial fills, market impact, borrow/funding cost; seasons about four weeks — [TradeRank vs Alpha Arena](https://www.traderank.ai/traderank-vs-alpha-arena); [TradeRank alternatives](https://www.traderank.ai/blog/alpha-arena-alternatives-2026) [OFFICIAL]
- Season winners stated on site: S3 MiniMax M2.5 -0.63% (winner lost money); S4 MiniMax M2.7 +6.94%; S5 Gemini 3.5 Flash +13.76%; S6 Kimi K2.7 Code +2.14%; S8 Inkling +12.82%; S10 Jev +11.99%; S0, S1, S2, S7 (provisional), S9 winners not shown on the fetched page — [TradeRank home](https://traderank.ai/) [OFFICIAL]
- Season 9 top 5 (3P): Nemotron 3.5 Lightning (NVIDIA) +13.69%, Qwen3.8 Max 0902 +9.47%, Inkling +8.16%, Mistral Medium 3.5 +7.35%, GLM-5.3 +4.03%; Season 8 winner Inkling +12.86% (site says +12.82%) — [Bitrue blog, 14 Oct 2026](https://www.bitrue.com/blog/top-ai-trading-agents) [3P, UNVERIFIED; minor mismatch with site]
- Season 11 (live, as of 24 Nov 2026, 22 models): no model in profit; leader Grok 4.7 +0.00%, then Gemini 4 Argon -0.04%, GPT-6.1 Terra Pro -0.13%; last Mistral Large 4 -15.37%; 12/22 beat S&P 500 (-3.91%), 22/22 beat Bitcoin (-18.18%) — [TradeRank home](https://traderank.ai/) [OFFICIAL]
- All-time cumulative: best Gemini 4 Argon +13.0% over 11 seasons; Grok 4.7 -13.6% (11), GPT-6.1 Terra Pro -16.4% (11), Claude Haiku 5.5 -24.7% (10), DeepSeek V4.1 Flash 1017 -23.8% (9), Kimi K3.1 Pro -12.2% (9), Qwen3.8 Max 0902 -0.1% (9); SPY buy-and-hold +12.6% and BTC buy-and-hold -18.3% over the same span — [TradeRank home](https://traderank.ai/) [OFFICIAL]
- Persistence: site cites its Sept 2026 article "across 72 model-seasons, rank still does not detectably carry over"; Nov 2026 article: the family of a season's top model came first again once in 10 tries; across 117 model-seasons (S0-S10) 46 made money, median lost 1.00%, 45 beat S&P 500 — [TradeRank home](https://traderank.ai/) [OFFICIAL]
- Profitable share conflicts: 46/117 = 39.3% (site home), "38.9% of model-seasons profitable, 78 models, 3,131 trades" as of 8 Nov 2026 — [TradeRank alternatives](https://www.traderank.ai/blog/alpha-arena-alternatives-2026); 46.2% across 9 seasons — [Bitrue](https://www.bitrue.com/blog/top-ai-trading-agents) [3P]

**Prediction Arena** (arXiv 2604.07355; real money cohort 1) — see next section for full tables. Persistence: Cohort 1 leaderboard "substantially reshuffled" from Phase 1 (12 Jan-14 Feb) to Phase 2 (15 Feb-9 Mar 2026): glm-4.7 moved 2nd to 1st, grok-4-20-checkpoint 1st to 2nd; settlement accuracy "remained the strongest longitudinal predictor"; whether provider characteristics carry across generations "cannot be concluded" — [arXiv 2604.07355 HTML](https://arxiv.org/html/2604.07355) [OFFICIAL]

**LiveTradeBench** (arXiv 2511.03628, UIUC; live data, apparently simulated accounts) — Sharpe correlation between stocks and Polymarket "close to zero"; Spearman of LMArena score vs return 0.054 (stocks) and -0.38 (Polymarket) — [arXiv 2511.03628 HTML](https://arxiv.org/html/2511.03628) [OFFICIAL]. Full tables in next section.

**Other live arenas named (no results verified)**
- BingX AI Arena: real $10,000 per model, crypto perps, copy-trading — [TradeRank alternatives](https://www.traderank.ai/blog/alpha-arena-alternatives-2026) [3P]; [BingX blog](https://bingx.com/en/blog/article/bingx-ai-arena-ranking-the-six-llm-traders-after-a-big-week) [operator blog, not fetched]
- RockAlpha/RockFlow (US stocks, six models in Classic arena, limited methodology); Strategy Arena (virtual, 75 strategies) — [TradeRank alternatives](https://www.traderank.ai/blog/alpha-arena-alternatives-2026) [3P]
- LLMTrader: seasons ranked by Sharpe, ties by absolute return, results kept public — [LLMTrader docs](https://llmtrader-docs.pages.dev/seasons/how-seasons-work) [OFFICIAL docs, results not fetched]
- PilotAI "Alpha Games" daily public competition among its AI portfolio models (Aug 2025) — [investingLive](https://investinglive.com/Education/pilotai-launches-alpha-games-a-public-daily-competition-among-its-ai-portfolio-models-20250814) [PRESS, not fetched]

### Inferences
- Every multi-period source found (TradeRank 11 seasons, Prediction Arena 2 phases, LiveTradeBench 2 markets, Alpha Arena 2 seasons) shows rank instability; no model or family repeatedly wins. The only repeat winner family on TradeRank is MiniMax (S3, S4), and S3's "win" was a loss.
- TradeRank's all-time numbers say most models trailed SPY buy-and-hold (+12.6%); only Gemini 4 Argon (+13.0%) roughly matched it over 11 seasons.
- TradeRank is a competitor of Alpha Arena and paper-only with no slippage; its claims about Alpha Arena should be read in that light.

### Gaps
- TradeRank S0, S1, S2, S7, S9 winners from the official site not obtained (S9 only via Bitrue); full per-model per-season tables and the persistence articles themselves (statistical method) not fetched (traderank.ai/seasons 404).
- No academic live leaderboard with more than two periods found besides TradeRank (which is not peer-reviewed).

## Prediction markets: PolyBench, LiveTradeBench (Polymarket), Prediction Arena — per-model results, open vs closed

### Takeaway
Only Prediction Arena Cohort 1 used real money (Kalshi + Polymarket); every real-money model lost on Kalshi (-16.0% to -30.8% over 57 days) and roughly broke even to slightly negative on Polymarket, with the open-weight GLM-4.7 topping Kalshi. PolyBench (simulated, one week of snapshots) was led by open-weight MiMo-V2-Flash, and LiveTradeBench's Polymarket track (simulated $500 accounts) was led by Claude-Sonnet-3.7; no model leads across these benchmarks.

### Cited Findings
**Prediction Arena** — Zhang, Liu, Johansson, Yitayew, Ohly, Li; submitted 28 Mar 2026 — [arXiv abs](https://arxiv.org/abs/2604.07355) [OFFICIAL]
- Cohort 1: real capital, live Kalshi accounts funded $10,000 each, 12 Jan-9 Mar 2026 (57 days), Polymarket live 9 Feb-9 Mar; decisions every 15-45 minutes. Cohort 2: paper ($10,000 simulated) from 6 Mar, 3 days; paper trades have no real counterparty so not comparable — [arXiv HTML](https://arxiv.org/html/2604.07355) [OFFICIAL]
- Kalshi Cohort 1 (real money), final value / total return / settlement win rate / trades: 1 glm-4.7 [open-weight, Zhipu] $8,398 / -16.0% / 30.9% / 361; 2 grok-4-20-checkpoint [closed] $7,999 / -20.0% / 51.9% / 424; 3 gpt-5.2 [closed] $7,950 / -20.5% / 48.0% / 452; 4 claude-opus-4-5-20251101 [closed] $7,409 / -25.9% / 41.0% / 886; 5 gemini-3-pro-preview [closed] $6,950 / -30.5% / 28.8% / 664; 6 grok-4-1-fast-reasoning [closed] $6,925 / -30.8% / 15.4% / 129 — [arXiv HTML](https://arxiv.org/html/2604.07355) [OFFICIAL; open/closed labels are mine]
- Polymarket (Cohort 1 real, Cohort 2 paper), return / settled win rate / trades: grok-4-20-checkpoint -1.85% / 71.4% / 18; gemini-3-pro-preview -1.81% / 14.3% / 155; gpt-5.2 -0.42% / 43.5% / 127; glm-4.7 -0.09% / 10.5% / 95; claude-opus-4-5 -2.68% / 33.3% / 86; grok-4-1-fast-reasoning 0.00% / 0 trades; Cohort 2: gemini-3.1-pro-preview +6.02% / 50.0% / 76; glm-5 [open] +0.30% / 4; gpt-5.4 -0.02% / 1; claude-opus-4-6 -10.06% / 33.3% / 59. Cohort 1 average about -1.1% on Polymarket vs -22.6% on Kalshi — [arXiv HTML](https://arxiv.org/html/2604.07355); [abs](https://arxiv.org/abs/2604.07355) [OFFICIAL]
- Kalshi Cohort 2 (paper, 3 days): GPT-5.4 +1.22% ($10,121.96, 5 trades); Claude Opus 4.6 -0.11% (46); GLM-5 -4.09% (12); Gemini 3.1 Pro Preview 0.00% (0 trades) — [arXiv HTML](https://arxiv.org/html/2604.07355) [OFFICIAL]
- Drivers: initial prediction accuracy and ability to capitalize on correct predictions; research volume shows no correlation with outcomes — [arXiv abs](https://arxiv.org/abs/2604.07355) [OFFICIAL]
- Verifiability: real broker accounts, but no public account/wallet IDs found in the fetched paper text [gap].

**PolyBench** — Cheng, Liu, Long; submitted 3 Apr 2026; q-fin.CP — [arXiv abs](https://arxiv.org/abs/2604.14199) [OFFICIAL]
- Simulated: point-in-time snapshots of 38,666 binary Polymarket markets across 4,997 events with CLOB order-book state + real-time news, collected 6-12 Feb 2026; 7 LLMs, 36,165 predictions; order-book sweep execution sim (top 5 levels); budget per BUY = confidence x base lot $10; confidence < 0.6 discarded; CWR = net profit / invested — [arXiv HTML](https://arxiv.org/html/2604.14199) [OFFICIAL]
- Per-model (accuracy / CWR / APY / Sharpe): MiMo-V2-Flash [open] 62.1% / +17.6% / 4067.3% / 0.02; Gemini-3-Flash [closed] 75.0% / +6.2% / 1486.5% / 0.01; Trinity-Large [open] 42.7% / -9.2% / -4527.8% / -0.02; DeepSeek-V3.2 [open] 53.5% / -11.4% / -5571.8% / -0.03; Grok-4.1-Fast [closed] 59.1% / -12.1% / -5820.4% / -0.17; GPT-OSS-120B [open] 58.0% / -17.8% / -7075.8% / -0.22; MiniMax-M2.5 [open] 42.6% / -25.2% / -9537.2% / -0.22 — [arXiv HTML](https://arxiv.org/html/2604.14199) [OFFICIAL; open/closed partly inferred from table grouping]
- Only two of seven profitable; the rest "incur losses despite uniformly high stated confidence"; larger lot sizes (up to $1,000) reduce returns via slippage — [arXiv abs](https://arxiv.org/abs/2604.14199); [HTML](https://arxiv.org/html/2604.14199) [OFFICIAL]

**LiveTradeBench** — Haofei Yu, Fenghai Li, Jiaxuan You (UIUC); 5 Nov 2025 — [arXiv HTML](https://arxiv.org/html/2511.03628) [OFFICIAL]
- Live data 18 Aug-24 Oct 2025 (50 trading days); 21 LLMs; US stocks (15 tickers + cash, $1,000 start) and Polymarket (10 binary markets, $500 start); prices from yfinance and Polymarket endpoints; appears daily decisions; real vs paper not explicitly stated in the fetched text but accounts look simulated — [arXiv HTML](https://arxiv.org/html/2511.03628) [OFFICIAL]
- Polymarket top (CR% / Sharpe / MDD%): Claude-Sonnet-3.7 [closed] +20.54 / 2.38 / 10.65; Grok-4 [closed] +7.38 / 1.01; Qwen2.5-72B-Instruct [open] +1.63 / 0.43; Llama3.3-70B [open] +1.58 / 0.40; bottom: Kimi-K2-Instruct [open] -53.44 / -5.26; GPT-o3 [closed] -54.84 / -3.68; Qwen3-235B-Thinking [open] -57.62; GPT-5 -23.96 — [arXiv HTML](https://arxiv.org/html/2511.03628) [OFFICIAL]
- Stocks top by Sharpe: GPT-4.1 +6.25% (SR 2.64), GPT-o3 +6.04%, GPT-5 +5.31%, Qwen2.5-72B +5.15%; bottom Qwen3-235B-Thinking +1.78% (SR 0.60); all 21 positive in stocks in this window — [arXiv HTML](https://arxiv.org/html/2511.03628) [OFFICIAL]
- GPT-o3 was 2nd in stocks and 20th of 21 on Polymarket; Sharpe correlation across markets near zero; LMArena score vs return Spearman 0.054 (stocks), -0.38 (Polymarket) — [arXiv HTML](https://arxiv.org/html/2511.03628) [OFFICIAL]

**Related (forecasting, not trading; not researched in depth)**: Prophet Arena (U. Chicago, arXiv 2510.17638) forecasts Kalshi/Polymarket events; Foresight Arena on-chain — mentioned in [search summary / arXiv PDF](https://arxiv.org/pdf/2510.17638v2) [not fetched]. Kalshi runs a market on "best AI model" (LMArena-based, not trading) — [Kalshi](https://kalshi.com/best-ai-model).

### Inferences
- Open vs closed: open-weight models led two of three prediction-market benchmarks (GLM-4.7 on real-money Kalshi, though still -16%; MiMo-V2-Flash in PolyBench), while closed Claude-Sonnet-3.7 led LiveTradeBench Polymarket. Open models also occupy most of the bottom of PolyBench and LiveTradeBench. No family-level pattern survives across benchmarks.
- Accuracy is not profit: Gemini-3-Flash had the highest PolyBench accuracy (75%) but much lower CWR than MiMo; grok-4-20-checkpoint had the best settlement win rate on Kalshi (51.9%) and Polymarket (71.4%) but still lost money.
- Real-money results are uniformly worse than simulated ones (all six real Kalshi accounts lost 16-31%; positive results come mostly from paper/simulated settings or 3-day windows).
- Across Alpha Arena (Qwen, then Grok 4.20), Prediction Arena (GLM-4.7), PolyBench (MiMo), LiveTradeBench (GPT-4.1 stocks / Claude-Sonnet-3.7 Polymarket) and TradeRank (rotating), no single model repeatedly wins. The xAI Grok 4.20 checkpoint is the most recurrent strong performer (Alpha Arena 1.5 winner; Prediction Arena Kalshi #2 and best win rates), but it still lost money in Prediction Arena.

### Gaps
- Prediction Arena: no public live leaderboard or account IDs found; no later cohorts (post-March 2026) found.
- PolyBench: no starting bankroll; open/closed labels partly inferred; one-week window only.
- LiveTradeBench: explicit confirmation of paper vs real accounts not found in fetched text; no later live updates checked.
