# AI traders mostly just ride the market

Across more than 30 official sources from 2024 to November 2026 (peer-reviewed and arXiv papers, benchmarks with published tables, and live arenas), the pattern that holds most firmly is that **the direction of the market, not the choice of model, decides whether an AI trader "beats" buy-and-hold**. LLM agents hold much less of the market than a buy-and-hold investor, with market exposure (beta) of 0.01 to 0.70 in the largest look-ahead-free test. So they trail in rallies (0 of 24 agents beat Tesla's +46.9% run; 0 of 6 models beat SPY in the 2026 rally; 11 of 12 trailed Bitcoin's +23.3%) and look clever in sell-offs (6 of 6 beat SPY in 2022) ([rta-bench-1](https://arxiv.org/html/2611.19530); [Agent Market Arena](https://arxiv.org/html/2510.11695); [OAK Research](https://oakresearch.io/en/ai/trading-benchmark)). No source shows statistically real skill: **0 of 91 runs had significant alpha** in the 2026 study, and two 20-year agents had none (all p > 0.34) ([rta-bench-1](https://arxiv.org/html/2611.19530); [FINSABER](https://arxiv.org/html/2505.07078v5)). Run-to-run luck (5.2 points between two runs of the same model) is close to the gap between the best and worst model (8.7 points), and rankings reshuffle every season. Thinking mode, model size, open vs closed weights, model family and general-intelligence leaderboard rank do not reliably predict trading results. Three things do change results: prompt rules and agent design, leverage, and how honestly the test is run. For someone running free tests on NVIDIA-hosted open models, this means the test design matters far more than the model. No official paper has tested Nemotron at all, and Kimi models range from first place (StockBench 2025) to last (−24.2% against a +36.9% index in KTD-Fin).

## Eight patterns hold and ten do not

The two tables below are the short answer. "Buy-and-hold" (B&H) means buying the index or coin at the start and doing nothing. "Beat" means a higher return than B&H over the same dates. Open/closed and thinking labels are mostly the researchers' own classification, because most papers do not state them.

**Patterns that hold** (seen across several independent sources, markets and periods)

| # | Pattern | Proof (numbers) |
|---|---|---|
| 1 | Most AI traders do not beat buy-and-hold, and none has proven skill | 0 of 91 runs had significant alpha; mean alpha −2.3% a year (95% CI −4.7% to +0.1%) ([rta-bench-1](https://arxiv.org/html/2611.19530)). FinMem and FinAgent alpha all p > 0.34 over 2004–2024 ([FINSABER](https://arxiv.org/html/2505.07078v5)). 1 of 12 models beat holding BTC ([OAK](https://oakresearch.io/en/ai/trading-benchmark)). Over 11 seasons only Gemini 4 Argon (+13.0%) roughly matched SPY (+12.6%) ([TradeRank](https://traderank.ai/)) |
| 2 | They hold less of the market, so they lag in rising markets | TSLA +46.88%: 0 of 24 agent setups beat it ([AMA](https://arxiv.org/html/2510.11695)). 2026 rally: 0 of 6 beat SPY +12.1% ([rta-bench-1](https://arxiv.org/html/2611.19530)). Crypto bull Jan–Mar 2024: 0 of 24 setups beat B&H ([FS-ReasoningAgent](https://arxiv.org/html/2410.12464)) |
| 3 | In falling markets they often "win", but by losing less, not by skill | 2022 bear: 6 of 6 beat SPY −18.6% ([rta-bench-1](https://arxiv.org/html/2611.19530)). BMRN −6.89%: 20 of 24 beat ([AMA](https://arxiv.org/html/2510.11695)). Mar–Apr 2025: 7 of 9 beat the S&P 500 (−6.91%) with beta 0.35–0.94 ([DeepFund](https://arxiv.org/html/2505.11065v2)) |
| 4 | Luck from run to run is about as big as the gap between models | Two runs of one model ended 5.2 points apart on average; best vs worst model 8.7 points ([rta-bench-1](https://arxiv.org/html/2611.19530)). OAK winner's edge over BTC was about $603, but its run spread was ±$3,498 ([OAK](https://oakresearch.io/en/ai/trading-benchmark)) |
| 5 | Rankings do not carry over between seasons or benchmarks | Across 72 model-seasons, "rank still does not detectably carry over"; the top family won again only 1 time in 10 ([TradeRank](https://traderank.ai/)). Same months of 2025: DeepSeek-V3.1 placed 8th of 13, 16th of 21 and 2nd of 6 in three benchmarks ([StockBench](https://arxiv.org/html/2510.02209v2); [LiveTradeBench](https://arxiv.org/html/2511.03628); [AI-Trader](https://arxiv.org/html/2512.10971)) |
| 6 | Prompt rules and agent design move results more than swapping the model | One cash rule cut stock holdings by 30.3 points in all 6 pairs and max drawdown by 9.4 points ([rta-bench-1](https://arxiv.org/html/2611.19530)). "Agent architecture proved to be the dominant factor" ([AMA](https://arxiv.org/html/2510.11695)) |
| 7 | High leverage causes the big blow-ups | DeepSeek V4 Pro −62.8% at up to 10x, while BTC rose 23.3% ([OAK](https://oakresearch.io/en/ai/trading-benchmark)). At 10x in 2025, DeepSeek −43.3% (max drawdown 96.85%) and Qwen −68.6% against BTC −7.6% ([Can AI Make Money in Crypto?](https://arxiv.org/html/2609.34510v1)) |
| 8 | Backtests on old data and paper trading flatter results; real money is worse | Returns decayed 50–72% after the model's training cutoff ([Profit Mirage](https://arxiv.org/html/2510.07920)). Qwen alpha went from +15.8 points in paper trading to −28.1 live ([Can AI Make Money in Crypto?](https://arxiv.org/html/2609.34510v1)). All 6 real-money Kalshi accounts lost 16–31% ([Prediction Arena](https://arxiv.org/html/2604.07355)) |

**Beliefs that do not hold** (contradicted, or no better than mixed, in the sources)

| # | Belief | Verdict and proof |
|---|---|---|
| 1 | Closed (paid) models trade better than open models | **Does not hold.** Open models topped StockBench (Kimi-K2), AI-Trader US and crypto (MiniMax-M2, DeepSeek-v3.1) and OAK (GLM-5.3, +29.4%). Open models also hold the worst results: DeepSeek V4 Pro −62.8% ([OAK](https://oakresearch.io/en/ai/trading-benchmark)) and Kimi-K2.6 −24.2% vs CSI300 +36.9% ([KTD-Fin](https://arxiv.org/html/2605.28359v1)). Open models spread wider; they are not better or worse on average |
| 2 | Bigger models trade better | **Does not hold reliably.** "Larger models do not reliably outperform smaller ones" ([FINSABER](https://arxiv.org/html/2505.07078v5)). On BTC, Qwen2.5-72B made +0.55% vs +19.48% for the 7B ([InvestorBench](https://arxiv.org/html/2412.18174)). There is a weak edge for size on risk-adjusted stock returns only |
| 3 | Thinking (reasoning) mode makes better trades | **Does not hold.** 5 stock papers and the crypto tests find no reliable gain; all 9 confidence intervals include zero ([Price of Thought](https://arxiv.org/html/2609.30705v1)); thinking changed crypto trading by +0.3 points ([TraderBench](https://arxiv.org/html/2603.00285)) |
| 4 | Smarter models (higher on general leaderboards) trade better | **Does not hold.** LMArena score vs return: rank correlation 0.054 on stocks and −0.38 on Polymarket ([LiveTradeBench](https://arxiv.org/html/2511.03628)); "the capability leader is not the Sharpe leader" ([CLQT](https://arxiv.org/html/2606.29771)) |
| 5 | One model family (or "Chinese models") is the best trader | **Does not hold.** Every family with a top-3 finish also has a bottom-half finish elsewhere. Alpha Arena's Season 1 Chinese winner was replaced by xAI's Grok 4.20 in Season 1.5 ([founder post via ForkLog](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/)) |
| 6 | Feeding the AI news gives it an edge | **Not proven.** Removing headlines changed return by −0.3 points (95% CI −3.4 to +2.7); agents "bought the stocks with the most positive news" but earned as much without it ([rta-bench-1](https://arxiv.org/abs/2611.19530)) |
| 7 | Trading more often makes more money | **Not proven.** No official paper varies decision frequency for the same model. The overtrading evidence (Gemini 2.5 Pro paying over 13% of capital in fees in Alpha Arena) is secondary and unverified |
| 8 | Finance-tuned models trade better | **Does not hold.** Palmyra-Fin-70B averaged −0.45% vs B&H +34.10% on stocks; "domain-specific LLMs did not provide a decisive advantage" ([InvestorBench](https://arxiv.org/html/2412.18174)) |
| 9 | Higher forecast accuracy or confidence means profit | **Does not hold.** Gemini-3-Flash had the best accuracy (75%) but much lower profit than MiMo (62.1%); five of seven models lost money "despite uniformly high stated confidence" ([PolyBench](https://arxiv.org/html/2604.14199)) |
| 10 | A model that does well on stocks will do well on crypto or other markets | **Mixed, so not reliable.** Stock and Polymarket Sharpe ratios were nearly uncorrelated ([LiveTradeBench](https://arxiv.org/html/2511.03628)); BTC vs TSLA returns correlated at r = 0.06 across 18 teams ([FinMMEval](https://ceur-ws.org/Vol-4283/paper186.pdf)). One counterexample: in AI-Trader the six models kept almost the same order in US stocks and crypto ([AI-Trader](https://arxiv.org/html/2512.10971)) |

## Rising markets beat the AI; falling markets flatter it

The single most useful fact for reading any AI trading result is how much of the market the agent holds. Beta measures this: 1.0 moves with the index, and 0.3 is mostly cash. Where researchers measured it, LLM agents sat well below 1. In the 2026 look-ahead-free study the betas were **0.01 to 0.70**, and market and style exposure explained a **median 78% of return** ([rta-bench-1](https://arxiv.org/html/2611.19530)). In live trading in March–April 2025 the betas were 0.35 to 0.94 ([DeepFund](https://arxiv.org/html/2505.11065v2)). On Chinese A-shares, 9 of 10 models had negative stock-selection alpha once returns were split into factor and style parts, so their wins came from exposure ([KTD-Fin](https://arxiv.org/html/2605.28359v1)). An agent that holds a third of the market will lose to the index when prices rise and beat it when they fall. The table bears this out in both markets and across years.

| Market | Window | Market move (B&H) | AI traders that beat B&H | Source |
|---|---|---|---|---|
| **Stocks, rising** | 2026 rally (Jan 2–Nov 11) | SPY +12.1% | 0 of 6 | [rta-bench-1](https://arxiv.org/html/2611.19530) |
| Stocks, rising | 2020 crash and rebound | SPY +17.2%, equal-weight +40.1% | 1 of 6 vs SPY, 0 of 6 vs equal-weight | [rta-bench-1](https://arxiv.org/html/2611.19530) |
| Stocks, rising | TSLA, Aug–Sep 2025 (live) | +46.88% | 0 of 24 | [AMA](https://arxiv.org/html/2510.11695) |
| Stocks, rising | A-shares, Oct–Nov 2025 (live) | SSE-50 +1.65% | 0 of 6 | [AI-Trader](https://arxiv.org/html/2512.10971) |
| Stocks, rising | A-shares 2024 (strategy code) | Equal-weight +17.1% | 0 of 9 best setups | [Quant-Arena](https://arxiv.org/html/2610.30113) |
| Stocks, rising | CSI300, Jan 2024–Apr 2026 | +36.92% | 5 of 10 on return, but 9 of 10 negative selection alpha | [KTD-Fin](https://arxiv.org/html/2605.28359v1) |
| Stocks, mild rise | Nasdaq-100, Oct–Nov 2025 (live, hourly) | QQQ +1.87% | 3 of 6 | [AI-Trader](https://arxiv.org/html/2512.10971) |
| Stocks, flat | DJIA-20, Mar–Jun 2025 | +0.4% | 8 of 13 | [StockBench](https://arxiv.org/html/2510.02209v2) |
| **Stocks, falling** | 2022 bear | SPY −18.6% | 6 of 6 | [rta-bench-1](https://arxiv.org/html/2611.19530) |
| Stocks, falling | Mar–Apr 2025 tariff sell-off (live) | S&P 500 −6.91% | 7 of 9 | [DeepFund](https://arxiv.org/html/2505.11065v2) |
| Stocks, falling | BMRN, Aug–Sep 2025 (live) | −6.89% | 20 of 24 | [AMA](https://arxiv.org/html/2510.11695) |
| **Crypto, rising** | Jul–Oct 2026 perps (post-cutoff simulation) | BTC +23.3% | 1 of 12 (with lower Sharpe than BTC) | [OAK](https://oakresearch.io/en/ai/trading-benchmark) |
| Crypto, rising | Jan–Mar 2024 backtest | BTC/ETH/SOL +77% to +80% | 0 of 24 setups | [FS-ReasoningAgent](https://arxiv.org/html/2410.12464) |
| Crypto, rising | Oct–Dec 2023 backtest | BTC +39.7%, SOL +176.7% | 1 of 6 coin-model cells | [CryptoTrade](https://arxiv.org/html/2407.09546v2) |
| Crypto, rising | ETH, Aug–Sep 2025 (live) | +18.56% | Only 1 agent, whose rows are identical for every model | [AMA](https://arxiv.org/html/2510.11695) |
| **Crypto, falling** | Nov 1–14 2025 (live) | CD5 index −14.30% | 1 of 6 (all lost 12–19%) | [AI-Trader](https://arxiv.org/html/2512.10971) |
| Crypto, falling | Apr–Jul 2026 backtest | BTC −15.2%, ETH −31.8%, XRP −22.4% | All active strategies lost less | [Agent4Crypto](https://arxiv.org/html/2611.12269) |
| Crypto, falling | Apr–Jun 2023 backtest | BTC −15.6%, SOL −36.1% | 4 of 6 cells | [CryptoTrade](https://arxiv.org/html/2407.09546v2) |
| Crypto, falling | 2025 full year, 10x leverage | BTC −7.63% | 0 LLM methods | [Can AI Make Money in Crypto?](https://arxiv.org/html/2609.34510v1) |
| Crypto, falling | TradeRank Season 11 (live, paper) | BTC −18.18%, S&P 500 −3.91% | 22 of 22 beat BTC; 12 of 22 beat the S&P | [TradeRank](https://traderank.ai/) |

The rising-market half of the pattern has no real exception: **no LLM beat a rising market convincingly and on a risk-adjusted basis in any source**. The one up-market win on a post-cutoff test, GLM-5.3 at +29.4% vs BTC +23.3%, came with a Sharpe of 1.40 against BTC's 2.39 and a run spread larger than the edge ([OAK](https://oakresearch.io/en/ai/trading-benchmark)). The falling-market half has two exceptions, and they matter, because "the AI protects me in a crash" is not guaranteed. Over 2004–2024, LLM agents were "overly conservative in bull markets" and "overly aggressive in bear markets": FinMem's bear-market Sharpe was −0.97 against −0.28 for buy-and-hold, while simple rule strategies stayed positive in every regime ([FINSABER](https://arxiv.org/html/2505.07078)). StockBench found the reverse of the usual split in 2025: all agents trailed buy-and-hold in the January–April downturn and beat it in the May–August upturn, and GPT-OSS-120B went from last to first between the two ([StockBench](https://arxiv.org/html/2510.02209v2)). The fair summary is that agents usually hold less market, but when and how much they cut exposure varies by agent. Leverage turns a falling market into a wipe-out rather than a cushion.

Stocks and crypto differ mainly in size of swings and use of leverage, not in which model wins. Crypto tests often allow perpetual futures at up to 10x, which produced every blow-up in the record. Stock tests were spot-only and lost at most a few tens of percent. Because no model or family led in both markets across benchmarks (pattern 10 above), the practical lesson is to test each market separately and always against that market's own buy-and-hold for the same dates.

## Luck, rules and leverage matter more than the model

**Luck is large.** In the only study with repeated seeds across three market regimes, two runs of the same model ended **5.2 points apart** on average, while the best and worst models of 2026 were **8.7 points apart**. The author concludes: "A single run's return cannot tell an LLM trading agent's skill from its luck" ([rta-bench-1](https://arxiv.org/html/2611.19530)). StockBench ran three seeds and saw return variance range more than a hundredfold between models (0.074 to 10.19 × 10⁻⁴), with model means spanning only −2.8% to +2.5%, so many ranking gaps sit inside the noise ([StockBench](https://arxiv.org/html/2510.02209v2)). Most other leaderboards, including Alpha Arena, AMA and LiveTradeBench, report one run per model. Runs with very few trades swing the most: Llama 3.2 3B made 1 to 20 decisions per run and its returns ranged from −7.9% to +21.4% ([rta-bench-1](https://arxiv.org/html/2611.19530)).

**Rankings reshuffle.** TradeRank, the only arena with many seasons (Seasons 0 to 11, about four weeks each, since January 2026; paper money, no slippage), found that rank "does not detectably carry over" across 72 model-seasons and that the top model's family won again just once in 10 tries. Across 117 model-seasons only 46 made money and the median lost 1.00% ([TradeRank](https://traderank.ai/)). Its season winners rotate across MiniMax, Gemini, Kimi, Inkling and Jev, and the Season 3 winner lost money (−0.63%). The real-money Prediction Arena leaderboard "substantially reshuffled" between its two phases ([Prediction Arena](https://arxiv.org/html/2604.07355)).

**Rules change behavior reliably, mostly by changing risk.** Telling a GPT-based agent to keep 30% cash when risk-off cut its stock share by **30.3 points in all six paired runs** and its maximum drawdown by **9.4 points** ([rta-bench-1](https://arxiv.org/html/2611.19530)). That buys a smaller loss in bad markets at the cost of a smaller gain in good ones; it does not add stock-picking skill. Agents follow rules unevenly: one live audit found 97.56% adherence when the agent chose not to trade, but only **62.63%** on constraints attached to actual orders ([FIDES-Live](https://arxiv.org/abs/2610.36476)). In LiveMACE, hard-rule pass rates ran from 0.613 (Qwen3-Max) to 0.888 (Gemini-3.1-Pro) and did not line up with returns ([LiveMACE](https://arxiv.org/html/2610.09872)).

**Agent design beats backbone choice.** In live trading of TSLA, BMRN, BTC and ETH (Aug–Sep 2025), the authors found that "modifying the underlying LLM within a fixed agent framework produces only modest changes in profitability", and that the framework mattered more ([AMA](https://arxiv.org/html/2510.11695)). In a weekly 15-coin portfolio over 2025, every backbone's single-agent average was negative or flat (GPT-4o −23.0%, GPT-5 −9.0%, Claude Sonnet 4.5 +0.1%), and every multi-agent average was positive (+31.0%, +12.2%, +43.9%). That is one run in a year when BTC fell 3.36% ([LLM Multi-Agent Crypto Portfolio](https://arxiv.org/html/2501.00826v3)). Moving from a simple ReAct loop to a multi-agent setup changed return by +2.45, +3.72 and +2.57 points for three models but −4.39 for Qwen3-Max ([LiveMACE](https://arxiv.org/html/2610.09872)). Design helps on average but not for every model, so it has to be tested per model too. Strong claims for reflection and risk modules in early framework papers (FinCon, TradingAgents) came from short tests on dates the models had already seen in training. They shrink sharply in longer, leak-free retests: FinMem's reported TSLA return of 61.78% re-ran at 19.94% ([FINSABER](https://arxiv.org/html/2505.07078)).

**Leverage drives the disasters.** On OAK's 90-day perps simulation (up to 10x), DeepSeek V4 Pro lost 62.8% with 1.8 liquidations on average, and Mistral Large 4 had 2 liquidations, while BTC rose 23.3% ([OAK](https://oakresearch.io/en/ai/trading-benchmark)). In a 2025 replay at 10x, direct DeepSeek and Qwen traders lost 43.3% and 68.6% against BTC's −7.63% ([Can AI Make Money in Crypto?](https://arxiv.org/html/2609.34510v1)). Spot-only crypto tests in the same years show small losses instead.

**News and trading frequency have no proven effect.** In the only news test that blocks look-ahead (headlines appear only after their publication minute), removing news changed return by **−0.3 points** (CI −3.4 to +2.7), giving another stock's news −2.2 points, and calendar-shifted news −1.4 points. All intervals include zero ([rta-bench-1](https://arxiv.org/html/2611.19530)). StockBench's no-news runs moved Kimi-K2 from 1.9% to 1.4% and left GPT-OSS-120B unchanged, gaps inside its seed noise ([StockBench](https://arxiv.org/html/2510.02209v2)). Before the training cutoff, apparent news skill can be memory: agents gave nearly the same outputs even when news and prices were altered ([Profit Mirage](https://arxiv.org/html/2510.07920v1)). No official paper varies decision frequency for one model, so "trade more often" is untested. Trading costs, though, show up wherever they are modeled. Larger order sizes cut returns through slippage ([PolyBench](https://arxiv.org/html/2604.14199)), and a reproduction of TradingAgents found its Sharpe fell from 0.43 to 0.22 after costs ([critical review](https://arxiv.org/html/2611.24133)).

**The testing method can create fake skill.** Moving the same agents from memorized 2021 dates to post-cutoff 2024 dates, with similar market returns, cut total return by **50% to 72%** and Sharpe by 51% to 62% ([Profit Mirage](https://arxiv.org/html/2510.07920)). Standard models lost 15 to 22 points of alpha the same way ([Look-Ahead-Bench](https://arxiv.org/html/2601.13770)). GPT-5.6 Luna "remembers" 2022 stock moves (rank correlation 0.69, falling to 0.25 after its cutoff) but "does not use what it remembers in this task" ([rta-bench-1](https://arxiv.org/html/2611.19530)). Paper results then fall again live: Qwen's alpha went from +15.80 points in paper trading to **−28.10** in real trading over the same month ([Can AI Make Money in Crypto?](https://arxiv.org/html/2609.34510v1)). A November 2026 review of 18 papers found that none fully met basic standards on timing, model memory, stock universe, costs and selection, and that 8 of 10 real-price papers tested for less than a year ([critical review](https://arxiv.org/html/2611.24133)).

## Open, big, thinking or famous: none reliably wins

**Open vs closed.** Open-weight models won often in 2025 and 2026: the top four of StockBench (Kimi-K2, Qwen3-235B Instruct, GLM-4.5, Qwen3-235B Think) ([StockBench](https://arxiv.org/html/2510.02209v2)), AI-Trader's US winner MiniMax-M2 (+9.56% vs QQQ +1.87%) and its only crypto winner DeepSeek-v3.1 ([AI-Trader](https://arxiv.org/html/2512.10971)), OAK's GLM-5.3 ([OAK](https://oakresearch.io/en/ai/trading-benchmark)), and the real-money Kalshi leader GLM-4.7, which still lost 16.0% ([Prediction Arena](https://arxiv.org/html/2604.07355)). Open models also fill the bottom: GPT-OSS-20B and 120B were last in StockBench, and in KTD-Fin the open Chinese models were the three lowest (deepseek-v4-pro +1.39%, glm-5.1 −3.55%, kimi-k2.6 −24.23% vs CSI300 +36.92%) ([KTD-Fin](https://arxiv.org/html/2605.28359v1)). TraderBench found that closed models' lead in its overall score "is driven by knowledge retrieval, not by options or crypto performance" ([TraderBench](https://arxiv.org/html/2603.00285)). InvestorBench claimed proprietary superiority, but its own table put open Qwen2.5-72B first on stocks (46.15% vs GPT-4 43.70%) ([InvestorBench](https://arxiv.org/html/2412.18174)). Free open models are not at a disadvantage, but they produce a wider spread of outcomes.

**Model size.** InvestorBench's Sharpe ratios rise with size in every stock family (Qwen2.5 7B 0.722 → 72B 1.276; Llama-3.1 8B 0.567 → 70B 0.864), but returns do not (Qwen 7B 29.5% beat 32B 20.9%), and its own crypto table reverses the claim on BTC ([InvestorBench](https://arxiv.org/html/2412.18174)). GPT-4o-mini beat GPT-4o on 3 of 4 stocks in both FinMem and FinAgent ([FINSABER](https://arxiv.org/html/2505.07078)). GPT-OSS-120B beat 20B by small margins in StockBench (−0.9% vs −2.8%) and by 0.3 points in TraderBench, which concluded that "improving tool access and planning matters more than model scale" ([TraderBench](https://arxiv.org/html/2603.00285)). Bigger helps a little with smoothness on stocks, and not reliably with returns.

**Thinking vs non-thinking.** This is the most consistent negative result. The same-model pairs:

| Pair (same base model) | Market, window | Thinking | Non-thinking | Source |
|---|---|---|---|---|
| Qwen3-235B Think vs Instruct | DJIA-20 stocks, Mar–Jun 2025 | 2.5%, drawdown −14.9%, rank 4 | 2.4%, drawdown −11.2%, rank 2 | [StockBench](https://arxiv.org/html/2510.02209v2) |
| Qwen3-235B Thinking vs Instruct | 15 US stocks, Aug–Oct 2025 (live) | 1.78% (last of 21) | 3.52% | [LiveTradeBench](https://arxiv.org/html/2511.03628) |
| DeepSeek-R1 vs V3.1 | Same | 2.10% | 2.46% | [LiveTradeBench](https://arxiv.org/html/2511.03628) |
| Qwen3-32B with vs without chain-of-thought | Crypto and options tracks | +0.3 crypto, −0.1 options | baseline | [TraderBench](https://arxiv.org/html/2603.00285) |
| DeepSeek, GPT, Gemini at low reasoning vs none | 100 US stocks, 2024, after costs | 9 of 9 differences inside zero | baseline | [Price of Thought](https://arxiv.org/html/2609.30705v1) |
| o1-mini vs GPT-4o (same framework) | BTC/ETH/SOL, H1 2024 | Not systematically better | — | [FS-ReasoningAgent](https://arxiv.org/html/2410.12464) |

LiveTradeBench's heading says it plainly: "Large reasoning models do not confer trading advantages". It found reasoning models far more volatile on Polymarket, which it puts down to "over-adjustment" ([LiveTradeBench](https://arxiv.org/html/2511.03628)). On DeepSeek, low reasoning significantly hurt one condition and the full none-to-maximum curve was "nonmonotonic"; the authors call baseline reasoning "the conservative default" ([Price of Thought](https://arxiv.org/html/2609.30705v1)). The only positive signs are small and per-asset: reasoning models were "often within the top two" on some single stocks, "however, this is not consistent across symbols" ([To Trade or Not to Trade](https://arxiv.org/html/2507.08584v1)), and o1-preview won BTC in a 2023 backtest while placing 10th of 13 on stocks ([InvestorBench](https://arxiv.org/html/2412.18174)). Thinking models made fewer arithmetic errors but more format errors ([StockBench](https://arxiv.org/html/2510.02209v2)).

**General intelligence.** Leaderboard rank barely predicts trading: Spearman 0.054 on stocks, −0.38 on Polymarket ([LiveTradeBench](https://arxiv.org/html/2511.03628)), and Pearson 0.16 between GDPVal and crypto trading ([TraderBench](https://arxiv.org/html/2603.00285)). GPT-5 ranked 9th of 13 in StockBench (0.3%, below the 0.4% passive baseline) and 4th of 6 in AI-Trader US.

**Model family, including the models available free on NVIDIA.** No family is reliably on top. Each family that reaches the top three somewhere also lands in the bottom half somewhere else:

| Family | Best showing | Worst showing |
|---|---|---|
| **Kimi** | Kimi-K2 1st of 13, StockBench 2025 ([StockBench](https://arxiv.org/html/2510.02209v2)); TradeRank S6 winner Kimi K2.7 Code +2.14% ([TradeRank](https://traderank.ai/)) | Kimi-K2.6 −24.23% vs CSI300 +36.92%, last of 10 ([KTD-Fin](https://arxiv.org/html/2605.28359v1)); Kimi K3 +2.7% vs BTC +23.3% ([OAK](https://oakresearch.io/en/ai/trading-benchmark)); Kimi-K2 −53.44% on Polymarket, worst Sharpe ([LiveTradeBench](https://arxiv.org/html/2511.03628)); Kimi K3.1 Pro −12.2% over 9 seasons ([TradeRank](https://traderank.ai/)) |
| **DeepSeek** | Only crypto winner, AI-Trader Nov 2025; top of LiveMACE (+5.77%) ([AI-Trader](https://arxiv.org/html/2512.10971); [LiveMACE](https://arxiv.org/html/2610.09872)) | DeepSeek V4 Pro −62.8%, last on OAK; V3.1 16th of 21 on LiveTradeBench |
| **Qwen** | Qwen2.5-72B 1st, InvestorBench stocks; qwen3.6-plus +85.29% on CSI300 ([KTD-Fin](https://arxiv.org/html/2605.28359v1)) | Qwen3.8 Max −25.7%, 11th of 12 on OAK; Qwen3-Max last in AI-Trader A-shares |
| **GLM** | GLM-5.3 +29.4%, OAK winner; GLM-4.7 Kalshi leader | GLM-5.1 −3.55% vs +36.92% (KTD-Fin); GLM-5.3 −7.8% vs +17.1% ([Quant-Arena](https://arxiv.org/html/2610.30113)) |
| **GPT** | GPT-4.1 and o3 1st and 2nd, LiveTradeBench stocks | GPT-OSS last in StockBench; GPT-5 below the index in StockBench and AI-Trader |
| **Gemini** | Gemini 4 Argon best all-time on TradeRank (+13.0%) | Gemini-2.5-Flash last in all three AI-Trader markets |

**Nemotron has no official trading result.** None of the papers tested any Nemotron model. The only data point is a third-party blog reporting that Nemotron 3.5 Lightning won TradeRank Season 9 with +13.69% ([Bitrue](https://www.bitrue.com/blog/top-ai-trading-agents)). It is not confirmed on TradeRank's own page and would be one four-week paper-money season even if accurate. A Nemotron Ultra experiment is therefore new evidence, not a replication.

## Per-model scorecards against buy-and-hold

These are the per-model tables with a same-period baseline, grouped by market and ordered by date. Returns are cumulative over the window unless noted. "O" marks open-weight models; the label is the researchers' own. Papers that publish no baseline (LiveTradeBench, LiveMACE) are left out of the "beat" counts.

### Stocks, 2025: flat US market, then live US and China

StockBench, top-20 Dow stocks, March 3 to June 30 2025, mean of 3 seeds; equal-weight buy-and-hold **+0.4%**, drawdown −15.2% ([StockBench](https://arxiv.org/html/2510.02209v2)):

| Model | Return | Max drawdown | vs B&H |
|---|---|---|---|
| Kimi-K2 (O) — rank 1 | 1.9% | −11.8% | +1.5 |
| Qwen3-235B Instruct (O) | 2.4% | −11.2% | +2.0 |
| GLM-4.5 (O) | 2.3% | −13.7% | +1.9 |
| Qwen3-235B Think (O) | 2.5% | −14.9% | +2.1 |
| OpenAI o3 | 1.9% | −13.2% | +1.5 |
| Qwen3-30B Think (O) | 2.1% | −13.5% | +1.7 |
| Claude 4 Sonnet | 2.2% | −14.2% | +1.8 |
| DeepSeek-V3.1 (O) | 1.1% | −14.1% | +0.7 |
| GPT-5 | 0.3% | −13.1% | −0.1 |
| Qwen3-Coder (O) | 0.2% | −13.9% | −0.2 |
| DeepSeek-V3 (O) | 0.2% | −14.1% | −0.2 |
| GPT-OSS-120B (O) | −0.9% | −14.0% | −1.3 |
| GPT-OSS-20B (O) | −2.8% | −14.4% | −3.2 |

Eight of 13 beat a flat market and all 13 had smaller drawdowns than holding. The biggest gap is 2.1 points over four months.

AI-Trader, live, October 1 to November 7 2025 (US hourly, A-shares daily), and crypto November 1–14 2025 ([AI-Trader](https://arxiv.org/html/2512.10971)):

| Model | US (QQQ +1.87%) | A-shares (SSE-50 +1.65%) | Crypto (CD5 −14.30%) |
|---|---|---|---|
| MiniMax-M2 (O) | **+9.56%** | +1.31% | −14.80% |
| DeepSeek-v3.1 (O) | +8.39% | −1.23% | **−12.18%** |
| Claude 3.7 Sonnet | +3.11% | +0.84% | −15.30% |
| GPT-5 | +1.56% | −3.53% | −16.41% |
| Qwen3-Max | +0.39% | −3.86% | −16.85% |
| Gemini 2.5 Flash | −0.06% | −1.53% | −18.63% |
| Beat B&H | 3 of 6 | 0 of 6 | 1 of 6 |

Every agent also had a deeper drawdown than its index in both stock markets. LiveTradeBench (15 US stocks, August 18 to October 24 2025, live) had all 21 models positive, from GPT-4.1 at +6.25% down to Qwen3-235B Thinking at +1.78%, but published no index return to compare against ([LiveTradeBench](https://arxiv.org/html/2511.03628)).

### Stocks across three regimes, and China 2024–2026

The 2026 look-ahead-free study, 56 large US stocks, mean of blind runs (return / beta) ([rta-bench-1](https://arxiv.org/html/2611.19530)):

| Model | 2020 crash and rebound | 2022 bear | 2026 rally |
|---|---|---|---|
| Claude Sonnet 4.6 (1 run) | **+25.4% / 0.34** | +0.4% / 0.55 | **+8.1% / 0.59** |
| Claude Haiku 4.5 (1 run) | +16.9% / 0.50 | −5.3% / 0.58 | +7.2% / 0.59 |
| Gemini 3.5 Flash | +13.7% / 0.47 | −8.4% / 0.46 | +6.3% / 0.70 |
| Llama 3.2 3B (O) | +10.6% / 0.19 | −1.6% / 0.25 | −0.6% / 0.19 |
| Claude Haiku 5.5 (1 run) | +7.4% / 0.23 | **+1.4% / 0.01** | +2.4% / 0.23 |
| GPT-5.6 Luna | +0.9% / 0.30 | −3.7% / 0.29 | +7.8% / 0.35 |
| **SPY** | **+17.2%** | **−18.6%** | **+12.1%** |
| Trend-following rule | +67.4% | −5.9% | +19.0% |
| Beat SPY | 1 of 6 | 6 of 6 | 0 of 6 |

A second table in the same paper gives slightly different averages for the multi-run models (for example GPT-5.6 Luna +5.4% in 2026); the beat counts are the same either way. A plain trend-following rule beat every model in both up years.

KTD-Fin, China CSI300 stocks, January 2024 to April 2026, blinded backtest; CSI300 buy-and-hold **+36.92%** ([KTD-Fin](https://arxiv.org/html/2605.28359v1)):

| Model | Return | Sharpe | Max drawdown | Stock-selection alpha |
|---|---|---|---|---|
| qwen3.6-plus | +85.29% | 1.13 | −24.49% | −0.7 |
| gpt-5.5 | +61.26% | 0.98 | −24.63% | −14.9 |
| doubao-seed-2.0 | +61.01% | 1.15 | −15.62% | −4.7 |
| claude-opus-4-7 | +58.80% | 0.98 | −26.69% | **+0.2** |
| minimax-m2.7 (O) | +56.31% | 0.89 | −29.43% | −7.4 |
| gemini-3.1-pro | +8.25% | 0.29 | −49.67% | −38.5 |
| deepseek-v4-pro (O) | +1.39% | 0.19 | −42.35% | −43.0 |
| glm-5.1 (O) | −3.55% | 0.10 | −44.88% | −61.9 |
| kimi-k2.6 (O) | −24.23% | −0.34 | −45.49% | −77.8 |
| Simple ML model (Qlib SFM) | +86.58% | 2.02 | −7.41% | — |

Half the models beat the index, but only one had positive stock-selection alpha, and a plain machine-learning baseline beat every LLM with nearly double the best Sharpe.

### Crypto, 2026: rising Bitcoin, leveraged perps

OAK Research Season 1, BTC/ETH/SOL/XRP/HYPE/DOGE perps up to 10x, July 18 to October 16 2026; each model only trades dates after its knowledge cutoff; $10,000 start ([OAK](https://oakresearch.io/en/ai/trading-benchmark)):

| Model | Return | vs BTC (+23.3%) | Sharpe | Max drawdown | Liquidations |
|---|---|---|---|---|---|
| GLM-5.3 (O) | **+29.4%** | **+6.0** | 1.40 | −15.1% | 0 |
| *Buy & hold BTC* | *+23.3%* | — | *2.39* | *−7.2%* | — |
| Gemini 4 Argon | +20.4% | −3.0 | 1.63 | −14.4% | 0.2 |
| Claude Opus 5.5 | +15.9% | −7.4 | 1.73 | −8.7% | 0 |
| GPT-6.1 Sol | +15.3% | −8.1 | 1.50 | −12.2% | 0 |
| Grok 4.7 | +10.4% | −13.0 | 0.80 | −9.8% | 0 |
| MiMo V2.6 Pro (O) | +8.8% | −14.6 | 0.71 | −13.5% | 0 |
| MiniMax M3 (O) | +5.6% | −17.7 | 0.91 | −6.5% | 0 |
| Kimi K3 (O) | +2.7% | −20.7 | 0.47 | −23.1% | 0.2 |
| Mistral Large 4 (O) | −12.8% | −36.1 | −1.27 | −23.9% | 2 |
| Muse Spark 1.3 | −16.5% | −39.9 | −0.65 | −30.9% | 1 |
| Qwen3.8 Max | −25.7% | −49.1 | −1.55 | −32.1% | 0 |
| DeepSeek V4 Pro (O) | −62.8% | −86.1 | −1.26 | −67.8% | 1.8 |

No model matched BTC's Sharpe. OAK is an industry research firm rather than a peer-reviewed venue, and it does not clearly define its "±" spread or run count. Closed frontier models clustered mid-table with moderate drawdowns. Open models filled both the top slot and the bottom slots.

Older crypto tests point the same way. On 2023 data, which the models had likely seen in training, only DeepSeek-67B beat buy-and-hold on both BTC (+28.3% vs +21.8%) and ETH (+9.5% vs +4.5%) ([InvestorBench](https://arxiv.org/html/2412.18174)). A single GPT-5.4 framework beat falling coins in April–July 2026 by 20 to 27 points, while still losing money on ETH and XRP ([Agent4Crypto](https://arxiv.org/html/2611.12269)).

### Live arenas, including the only real-money results

**Prediction Arena** is the only peer-reviewed-style source with real money: funded $10,000 Kalshi accounts, January 12 to March 9 2026. Every model lost: GLM-4.7 (O) −16.0%, Grok-4.20 checkpoint −20.0%, GPT-5.2 −20.5%, Claude Opus 4.5 −25.9%, Gemini 3 Pro −30.5%, Grok 4.1 Fast reasoning −30.8%. On Polymarket the same models came out between −2.68% and 0.00% ([Prediction Arena](https://arxiv.org/html/2604.07355)). Grok-4.20 had the best settlement win rate (51.9%) and still lost a fifth of its money. Research volume showed no link to results.

**TradeRank** (paper money, 10 cryptos and 50 US large caps, daily decisions) is the longest-running arena. Over the same 11-season span, SPY buy-and-hold made **+12.6%** and BTC lost **−18.3%**. All-time model results: Gemini 4 Argon +13.0%, Qwen3.8 Max −0.1%, Kimi K3.1 Pro −12.2%, Grok 4.7 −13.6%, GPT-6.1 Terra Pro −16.4%, DeepSeek V4.1 Flash −23.8%, Claude Haiku 5.5 −24.7% ([TradeRank](https://traderank.ai/)). Some models ran fewer seasons (9 or 10), but the shape is clear: only one model matched SPY, four of the seven listed finished between SPY and Bitcoin, and two did worse than Bitcoin. That spread fits a mixed, partly-cash stock-and-crypto book rather than skill.

**Alpha Arena** (Nof1) is the best-known real-money contest ($10,000 per model on Hyperliquid), but Nof1 never posted an official per-model table for Season 1 (October 18 to November 3 2025, crypto perps). The widely repeated figures, Qwen3-Max about +22% and DeepSeek V3.1 about +5% with GPT-5, Gemini 2.5 Pro, Grok 4 and Claude Sonnet 4.5 all losing, come from a founder chart relayed by third parties, and two conflicting sets of loser numbers circulate. They are not proof. Nof1's own write-up warns that one season cannot crown a best model. In Season 1.5 (US stock tokens, November 19 to December 3 2025, four rule variants per model), the founder announced Grok 4.20 as the winner at about +12% on average and profitable in all four variants ([founder post via ForkLog](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/)). Caixin reported it was the only profitable model ([Caixin](https://www.caixinglobal.com/2025-12-15/cover-story-trading-by-algorithm-who-is-responsible-when-ai-calls-the-shots-102393319.html)). The Season 1 winner did not repeat, and no Season 2 results had been published by November 2026.

## Conclusion

The evidence moves the question from "which AI trades best?" to "how much market does this AI hold, and was the test honest?". Every model trait people argue about (open vs closed, size, thinking, family, leaderboard rank) produces gaps smaller than one model's run-to-run luck, while market direction, cash and leverage rules, and test leakage each move results by tens of points. One consequence is easy to miss: a cautious AI that sits mostly in cash will appear to "win" in any falling month and "lose" in any rising one, so a single good or bad month says almost nothing. Another is that free open models are not handicapped. They have won major benchmarks, and their real risk is a wider spread of outcomes, including the worst blow-ups when leverage is on.

For free experiments with Nemotron Ultra or Kimi, the sources support a specific setup. Run each model at least three times with identical inputs, because one run cannot separate skill from luck. Test thinking mode off and on, starting with off, since no source found that reasoning pays for itself. Score every run against buy-and-hold of the same asset over the same dates, and report the model's average market exposure next to its return. Keep leverage at 1x unless the experiment is specifically about leverage. Trade forward on live prices, never only on past data the model may remember, and span both an up stretch and a down stretch before drawing conclusions. Adding a news feed, more frequent decisions or a bigger model should each be treated as an experiment to prove, not an upgrade to assume. Under those rules, a Nemotron result would add genuinely new evidence, because no official trading benchmark has yet measured it.
