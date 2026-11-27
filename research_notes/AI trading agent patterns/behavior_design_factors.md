# Behavior, Design and Evaluation Factors Behind LLM Trading-Agent Results (2024 to Nov 2026)

Conventions: "VERBATIM" means a short quote copied from the paper (the fetch tool capped quotes at about 125 characters, so long abstracts are summarized). "SUMMARY" means my paraphrase of what the paper says. Numbers come from the paper's own tables or text as extracted from the arXiv HTML pages, unless marked "secondary". Each finding names the market and test period.

Main sources read in full or in part:
- arXiv 2611.19530, "LLM Trading Agents Earn Beta, Not Alpha: A Look-Ahead-Free Benchmark" (rta-bench-1), submitted 14 Nov 2026. The abs page shows author "Jackson Wang"; the submission history shows "Mengxiao Wang". The paper covers US large caps, with periods 2020 crash/rebound, 2022 bear and 2026 rally (2 Jan to 11 Nov 2026), and tests 6 models in 91 runs.
- arXiv 2610.36476, FIDES-Live (Tian, Ding, Wu, Chan), 27 Oct 2026.
- arXiv 2601.13770, Look-Ahead-Bench (Benhenda), 20 Jan 2026.
- arXiv 2510.07920, "Profit Mirage: Revisiting Information Leakage in LLM-based Financial Agents" (Li et al.), 9 Oct 2025.
- arXiv 2505.07078, FINSABER, "Can LLM-based Financial Investing Strategies Outperform the Market in Long Run?" (Li, Kim, Cucuringu, Ma). v1 May 2025, v6 26 Jun 2026.
- arXiv 2510.02209, StockBench.
- arXiv 2510.11695, "When Agents Trade: Live Multi-Market Trading Benchmark for LLM Agents" (Agent Market Arena).
- arXiv 2512.10971, AI-Trader (HKUDS).
- arXiv 2412.20138, TradingAgents.
- arXiv 2407.06567, FinCon (NeurIPS 2024).
- Alpha Arena Season 1 (Nof1). No official methodology page could be fetched (nof1.ai/blog/TechPost1 returned 404), so all Alpha Arena numbers here are secondary.

---

## 1. Trading frequency, turnover and overtrading

### Takeaway
No official paper found isolates decision frequency (minute vs hour vs day) as a controlled variable for LLM agents. The strongest overtrading evidence is Alpha Arena Season 1 (crypto perps, Oct–Nov 2025), where the most active model lost heavily to fees, but those numbers come only from secondary sources. Official papers give indirect evidence. In rta-bench-1, runs with very few decisions had the widest spread of outcomes. AI-Trader ran each market at one frequency, so frequency is confounded with market.

### Cited Findings
- **Alpha Arena Season 1 (crypto perpetuals on Hyperliquid, 17 Oct to 3 Nov 2025; 6 models, $10,000 each). All figures secondary.**
  - Qwen3 Max won with a final account value of $12,231.82 (about +22%). More than half of the models finished in loss. — [gncrypto.news](https://www.gncrypto.news/news/qwen-wins-alpha-arena-season-1-with-22-percent-returns/); [forklog](https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/)
  - Gemini 2.5 Pro made about 238–240 trades (about 15 per day) and "burned over 13% of its capital in transaction fees alone". Qwen3 Max made about 43 trades and DeepSeek about 41. Qwen3 Max paid the highest total fees ($1,654) but still won. These counts come from a single less-established blog and are not corroborated by Nof1. — [aurpay.net](https://aurpay.net/?p=23782); [iweaver.ai](https://iweaver.ai/blog/alpha-arena-ai-trading-season-1-results)
  - GPT-5's loss is reported inconsistently: −62.66% in one source, about −75% with $498 in fees in another. Decrypt reported losses of more than 28% at an earlier date. — [aurpay.net](https://aurpay.net/?p=23782); [decrypt](https://decrypt.co/345006/ai-crypto-trading-showdown-deepseek-grok-winning-gemini-implodes)
  - Nof1 described the contest as mid-to-low frequency, with decisions spaced minutes to a few hours apart. According to secondary coverage, Nof1 said one season cannot crown a permanent best model and early successes may be luck. — [datawallet explainer](https://www.datawallet.com/crypto/alpha-arena-nof1-ai-explained); [buildix summary of Nof1 writeup](https://www.buildix.trade/blog/nof1-alpha-arena-lessons-ai-trading-byok-strategy-advisor-2026)
- **rta-bench-1 (arXiv 2611.19530; US large caps; 2020, 2022, 2026).**
  - The agent decides after every 5th close, so roughly weekly on daily bars. The main study had 4,394 steps and 9,101 buys and sells in total. The paper does not report turnover. — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
  - Decisions per run varied widely by model: Haiku 4.5 204–240; GPT-5.6 Luna 138–212; Sonnet 4.6 152–170; Gemini 3.5 Flash 78–153; Haiku 5.5 4–66; Llama 3.2 3B 1–20. Llama's blind-run returns ranged from −7.9% to +21.4%, so runs with few decisions swing widely. The paper reports no correlation between decision count and return; the swing reading is my interpretation of its Tables XIII and XIV. — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
  - Minute and 5-minute bars appear only in an intraday news analysis (the last 15 and 58 trading days of 2026, ten stocks). — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
- **AI-Trader (arXiv 2512.10971).** US NASDAQ-100 traded hourly (1 Oct to 7 Nov 2025), A-shares SSE-50 daily over the same dates, and 10 crypto pairs daily (1–14 Nov 2025). The paper makes no hourly-vs-daily comparison, so frequency is confounded with market.
  - US (hourly): MiniMax-M2 +9.56%, DeepSeek-v3.1 +8.39%, Claude-3.7-Sonnet +3.11%, GPT-5 +1.56%, Qwen3-Max +0.39%, Gemini-2.5-Flash −0.06%, against QQQ +1.87%.
  - A-shares (daily): no agent beat the SSE-50 (+1.65%).
  - Crypto (daily): only DeepSeek beat the CD5 Index (−12.18% vs −14.30%).
  - VERBATIM: "general intelligence does not automatically translate to effective trading capability". — [arXiv 2512.10971](https://arxiv.org/html/2512.10971)
- **Agent Market Arena (arXiv 2510.11695; TSLA, BMRN, BTC, ETH; live 1 Aug to 30 Sep 2025).** All agents make one BUY/SELL/HOLD decision per day, and no trade count is reported. SUMMARY: InvestorAgent is described as "proactive and risk-taking in trading frequency" with only moderate profitability. — [arXiv 2510.11695](https://arxiv.org/html/2510.11695v2)
- **HKU Business School "Agentic Trader" (live FX, from April 2026; 10 agents; one decision per hour).** Its reported finding is that higher trading frequency did not necessarily bring higher returns. This is a university report, not a peer-reviewed paper, and I saw it only as a search snippet. — [HKUBS FX Trading](https://www.hkubs.hku.hk/aimodelrankings_en/abstract/FX_Trading.html)

### Inferences
- The best-documented overtrading case (Gemini 2.5 Pro in Alpha Arena) is anecdotal. It covers one 17-day run, unreplicated, with secondary numbers. It is consistent with fee drag, but it is not a controlled frequency experiment.
- Benchmarks mostly fix cadence at daily or weekly, so "trade more often" has rarely been tested inside the LLM literature.

### Gaps
- No official paper found that varies decision interval (for example 1 min / 1 h / 1 day) for the same LLM and reports return. No paper found that regresses turnover on return for LLM agents.
- No official Nof1 trade-count or fee table was retrievable (the blog URL returned 404).

---

## 2. News: with vs without (ablations)

### Takeaway
In the only look-ahead-checked news ablation found (rta-bench-1, 2026), removing headlines changed returns by −0.3 points, and the 95% CI included zero. The agents did act on news, buying the most positively covered stocks, but that did not earn money. StockBench (2025) found a small return drop without news for one model and no change for another. Neither result shows a robust news edge.

### Cited Findings
- **rta-bench-1 (arXiv 2611.19530; US stocks, 2026 rally 2 Jan to 11 Nov 2026; headlines shown only after their publication minute).**
  - Return difference vs baseline, in points with 95% CI: no news −0.3 [−3.4, +2.7]; another stock's news −2.2 [−5.3, +1.1]; calendar-date news −1.4 [−4.4, +1.9]. All intervals include zero.
  - Mean five-day return per decision changed by +0.09, +0.15 and +0.05 points respectively.
  - VERBATIM (abstract): the agents "bought the stocks with the most positive news". SUMMARY: in ablations they earned as much without their headlines. — [arXiv 2611.19530](https://arxiv.org/abs/2611.19530); [HTML](https://arxiv.org/html/2611.19530)
- **StockBench (arXiv 2510.02209; top 20 DJIA stocks; 3 Mar to 30 Jun 2025, 82 trading days; 3 seeds per model).** Return % by input set (Full / without news / without news and fundamentals):
  - Kimi-K2: 1.9 / 1.4 / 0.6
  - GPT-OSS-120B: −1.2 / −1.2 / −3.4
  - The differences are small relative to the seed variance reported in its appendix (see section 4). — [arXiv 2510.02209](https://arxiv.org/html/2510.02209v2)
- **Profit Mirage (arXiv 2510.07920)** measures whether agents respond to inputs or to memory. For counterfactually perturbed inputs (10 large-cap US stocks, Jan 2022 to Jun 2023), it reports Prediction Consistency (PC) and Consistency Index (CI); lower is better for both.
  - FinMem: PC 0.8213, CI 0.8743
  - FinAgent: 0.7245 / 0.7781
  - QuantAgent: 0.7789 / 0.8362
  - FinCON: 0.7136 / 0.7522
  - TradingAgents: 0.6903 / 0.7016
  - VERBATIM: "High PC and CI across methods confirm reliance on memorized patterns over input-driven forecasting." — [arXiv 2510.07920](https://arxiv.org/html/2510.07920v1)

### Inferences
- When the period is pre-cutoff, an agent's apparent "news skill" may be memory of the outcome. Profit Mirage shows high output consistency even when the news and price inputs are altered. When look-ahead is removed (rta-bench-1), the news effect is not distinguishable from zero.

### Gaps
- No other look-ahead-free news ablation with CIs was found for crypto agents.

---

## 3. Prompt rules, risk limits, frameworks, memory and reflection

### Takeaway
Explicit rules change behavior reliably. One cash rule cut equity exposure by 30.3 points and maximum drawdown by 9.4 points (rta-bench-1). Framework design moved results more than the choice of LLM backbone in Agent Market Arena (2025). The large gains that original framework papers reported for risk control and reflection (FinCon, TradingAgents) came from short, pre-cutoff, single-period tests with few or no repeats. They shrink sharply under longer or leakage-free tests (FINSABER, Profit Mirage).

### Cited Findings
- **Cash rule (arXiv 2611.19530; US stocks; GPT-5.6 Luna).** VERBATIM: "a single cash rule in the prompt cut a GPT-based agent's share in stocks by 30.3 points in all six pairs." The rule required 30% cash when risk-off. It also cut maximum drawdown by 9.4 points. — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
- **FIDES-Live (arXiv 2610.36476; 7,299 crypto account-rounds plus a 310-round equity pilot; real market data, local paper execution; 10 inference routes).** Behavioral concordance (how far agents do what they say):
  - Crypto decision validity: 97.35%
  - Structured reporting accuracy (scorable responses): 90.81%
  - Commitment adherence overall: 94.36%, but only 62.63% on constraints attached to non-empty order proposals, against 97.56% on valid empty proposals
  - SUMMARY: the authors caution that the results do not establish long-run trading skill, faithful explanations, or causal benefit of audit feedback. — [arXiv 2610.36476](https://arxiv.org/abs/2610.36476)
- **Agent Market Arena (arXiv 2510.11695; TSLA, BMRN, BTC, ETH; live Aug to Sep 2025; 4 frameworks × 5 backbones).** Cumulative return ranges across backbones, with Buy & Hold for comparison (TSLA 46.88; BMRN −6.89; BTC 0.66; ETH 18.56):
  - InvestorAgent: TSLA 10.57 to 40.83; BMRN −13.88 to 3.79; BTC −7.06 to −1.22; ETH −6.39 to 5.56
  - TradeAgent (multi-agent): TSLA −38.72 to 21.91; BMRN −9.45 to 14.57; BTC −14.51 to 5.02; ETH −12.93 to 9.78
  - DeepFundAgent (memory): TSLA −15.43 to 13.89; BMRN −1.12 to 5.48; BTC −8.24 to 1.67; ETH 0.00 to 18.03
  - HedgeFundAgent: identical across all backbones (TSLA −29.15, BMRN 23.70, BTC −9.09, ETH 39.66), which may indicate a pipeline issue
  - VERBATIM: "agent architecture proved to be the dominant factor shaping behavior". SUMMARY: the abstract says backbones contribute less to outcome variation than frameworks.
  - DeepFundAgent (memory-based) was the most conservative and most consistent. — [arXiv 2510.11695](https://arxiv.org/html/2510.11695v2)
- **FinCon ablations (arXiv 2407.06567; US stocks; test 5 Oct 2022 to 10 Jun 2023; median of 5 repeated epochs).** CR % / SR, with vs without each component:
  - Within-episode CVaR risk control: GOOG 25.08 / 1.052 vs −1.46 / −0.006; NIO 17.46 vs −52.89; portfolio (TSLA, MSFT, PFE) 113.84 / 3.269 vs 14.70 / 1.142
  - Over-episode belief updates (verbal reflection, CVRF): GOOG 25.08 vs −11.94; NIO 17.46 vs 8.20; portfolio 113.84 vs 28.43
  - The paper's text and tables do not fully agree on which ablation hurts more (NIO). — [arXiv 2407.06567](https://arxiv.org/html/2407.06567)
- **TradingAgents (arXiv 2412.20138; AAPL, GOOGL, AMZN; 1 Jan to 29 Mar 2024).** CR / SR: AAPL 26.62% / 8.21 vs Buy & Hold −5.23%; GOOGL 24.36% / 6.39 vs 7.78%; AMZN 23.21% / 5.60 vs 17.1%.
  - No component ablations and no seed counts are reported.
  - VERBATIM: "We benchmarked TradingAgents over 3 months due to intensive LLM and tool use". SUMMARY: the paper says the Sharpe ratio exceeds the expected empirical range because the period had few pullbacks. — [arXiv 2412.20138](https://arxiv.org/html/2412.20138)
- **FINSABER re-tests of FinMem and FinAgent (arXiv 2505.07078; US stocks).**
  - Original window 6 Oct 2022 to 10 Apr 2023, SPR / CR %: FinMem reported TSLA 2.679 / 61.78, but the re-run with GPT-4o-mini gave 0.927 / 19.94 (GPT-4o: 0.404 / 5.31). MSFT: reported 1.440 / 23.26, re-run −0.554 / −7.10.
  - Over 2004–2024, annualized return: FinMem underperforms Buy & Hold on NFLX (12.57 vs 23.92), AMZN (5.70 vs 16.00) and MSFT (4.57 vs 11.24).
  - On survivorship-free composite universes (historical S&P 500 including delisted names), FinMem's Sharpe is negative on 3 of 4 selectors, for example Random Five −0.253 vs Buy & Hold 0.315.
  - VERBATIM: "LLM-derived alpha is likely a methodological artefact of narrow, biased evaluations." SUMMARY: the authors recommend trend detection and regime-aware risk controls over more framework complexity. — [arXiv 2505.07078](https://arxiv.org/html/2505.07078)
- **Profit Mirage FactFin (arXiv 2510.07920; Jul 2024 to Jun 2025; post-cutoff).** Counterfactual training gave average gains over the best baseline of TR +31.91%, SR +22.74% and MDD −9.23%, across AAPL, NVDA, TSLA, BYD, Tencent and Bitcoin. The authors' own method, so treat it as self-reported. — [arXiv 2510.07920](https://arxiv.org/html/2510.07920v1)
- **AI-Trader (arXiv 2512.10971).** VERBATIM: "risk control capability determines cross-market robustness". In crypto, DeepSeek-v3.1 peaked at about 41% cash during the drawdown and was the only agent to beat the index. — [arXiv 2512.10971](https://arxiv.org/html/2512.10971)

### Inferences
- Rules and risk limits mainly change exposure (beta) and drawdown, not stock-picking skill. That is consistent with rta-bench-1's finding that about 78% of return is exposure.
- Agents follow abstain/empty-order rules well (97.56%) but follow constraints much less when they actually place orders (62.63%). FIDES-Live does not link adherence to P&L.

### Gaps
- No look-ahead-free, multi-seed ablation of memory or reflection (FinMem, FinCon style) was found. FinCon's ablations are pre-cutoff for GPT-4-class models.

---

## 4. Run-to-run variance (seeds and luck)

### Takeaway
Seed noise is about the same size as model differences. In rta-bench-1, two seeds of the same model ended 5.2 points apart on average, while the best and worst models of 2026 were 8.7 points apart. Most framework papers report single runs or medians without CIs.

### Cited Findings
- **rta-bench-1 (arXiv 2611.19530; US; 2026).** Two seeds of the same model ended 5.2 points apart on average; the best and worst models of 2026 were 8.7 points apart.
  - VERBATIM: "A single run's return cannot tell an LLM trading agent's skill from its luck."
  - The three Claude models have only one seed per period (a limitation the paper notes). Gemini, GPT and Llama have 3 seeds.
  - Mean alpha was −2.3% a year (95% CI −4.7% to 0.1%). The largest |t| for alpha was 1.79. — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
- **StockBench (arXiv 2510.02209; DJIA top 20; Mar to Jun 2025; 3 seeds).** Return variance (×10⁻⁴) ranged from 0.074 (DeepSeek-V3) to 10.19 (GPT-OSS-120B); Kimi-K2 1.866 and Qwen3-235B-Think 0.321. Models' mean returns ranged from −2.8% to +2.5%, so many differences fall inside seed noise. GPT-OSS-120B's full-input return also differs between tables (−0.9% vs −1.2%). — [arXiv 2510.02209](https://arxiv.org/html/2510.02209v2)
- **FinCon** reports the median of 5 epochs, with no dispersion in the extracted text. **TradingAgents** reports no seeds. — [FinCon](https://arxiv.org/html/2407.06567); [TradingAgents](https://arxiv.org/html/2412.20138)
- **Agent Market Arena (2025).** Backbone ranges within one framework are themselves wide; TradeAgent on TSLA ran from −38.72% to +21.91%. — [arXiv 2510.11695](https://arxiv.org/html/2510.11695v2)
- **FIDES-Live** reports behavioral concordance (section 3) but no run-to-run return variance. — [arXiv 2610.36476](https://arxiv.org/abs/2610.36476)
- **Alpha Arena** was a single run per model. According to secondary coverage, Nof1 cautioned that a single season does not identify a best model. — [buildix summary](https://www.buildix.trade/blog/nof1-alpha-arena-lessons-ai-trading-byok-strategy-advisor-2026)

### Inferences
- With a seed gap of 5.2 against a model gap of 8.7, leaderboards built from one run per model (Alpha Arena, many papers) cannot separate models reliably.

### Gaps
- No paper found with bootstrapped CIs on live crypto agent returns across many seeds.

---

## 5. Market regime (bull vs bear)

### Takeaway
Regime dominates. FINSABER (2004–2024) finds LLM agents too conservative in bull markets and too aggressive in bear markets. StockBench (2025) finds all agents trail buy-and-hold in a downturn and beat it in an upturn. rta-bench-1 shows the same models swing from positive in 2020 and 2026 to negative in 2022.

### Cited Findings
- **FINSABER (arXiv 2505.07078; US; 2004–2024; regimes defined by S&P 500 annual return: bull ≥ +20%, bear ≤ −20%).** Average annual Sharpe:
  - Buy & Hold: bull 0.61, sideways 0.48, bear −0.28
  - FinAgent: bull 0.12, bear −0.38
  - FinMem: bull −0.19, bear −0.97
  - Rule-based ATR Band, Turn of the Month and ARIMA had positive Sharpe in every regime.
  - VERBATIM: "overly conservative in bull markets, underperforming passive benchmarks" and "overly aggressive in bear markets, incurring heavy losses". — [arXiv 2505.07078](https://arxiv.org/html/2505.07078)
- **StockBench (DJIA; downturn Jan to Apr 2025, upturn May to Aug 2025).** SUMMARY: all LLM agents underperform the passive baseline in the downturn and outperform it in the upturn. GPT-OSS-120B moves from bottom-ranked to top-ranked, while Kimi-K2 stays relatively stable. Numbers appear only in a figure. — [arXiv 2510.02209](https://arxiv.org/html/2510.02209v2)
- **rta-bench-1.** The three periods:
  - 2020 crash and rebound: 253 trading days, SPY +17.2%, max drawdown 33.7%
  - 2022 bear: 251 trading days, SPY −18.6%, max drawdown 24.5%
  - 2026 rally: 217 trading days, SPY +12.1%, max drawdown 8.9%

  Blind-run mean returns, 2020 / 2022 / 2026:

  | Model | 2020 | 2022 | 2026 |
  |---|---|---|---|
  | Haiku 4.5 | +16.9 | −5.3 | +7.2 |
  | Haiku 5.5 | +7.4 | +1.4 | +2.4 |
  | Sonnet 4.6 | +25.4 | +0.4 | +8.1 |
  | Gemini 3.5 Flash | +11.3 | −8.4 | +5.2 |
  | GPT-5.6 Luna | +2.3 | −2.5 | +5.4 |
  | Llama 3.2 3B | +10.6 | −1.5 | +2.3 |

  Named-ticker runs in 2022 were worse: GPT-5.6 Luna −9.4, Haiku 4.5 −9.5, Llama −8.8, Gemini −6.4. Exposures explain a median 78% of return (median R² 0.66). — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
- **AI-Trader (Oct to Nov 2025).** Crypto fell (CD5 −14.30%) and every agent lost 12–19%. In the rising US market several agents beat QQQ. VERBATIM: agents achieve excess returns "more readily in highly liquid markets than policy-driven environments". — [arXiv 2512.10971](https://arxiv.org/html/2512.10971)

### Inferences
- Because returns are mostly beta, a test window's direction largely decides whether an agent "wins". Results from a single regime do not generalize.

### Gaps
- No crypto-specific multi-year bull vs bear study of LLM agents was found.

---

## 6. Evaluation pitfalls: look-ahead, memorization, short windows, survivorship

### Takeaway
Moving from memorized to post-cutoff periods removes roughly half to all of the reported edge:
- Profit Mirage: total-return decay of 50–72%.
- Look-Ahead-Bench: alpha decay of 15–22 points for standard LLMs.
- FINSABER: reported LLM advantages vanish over 20 years and survivorship-free universes.

Short windows (TradingAgents, 3 months) produce implausible Sharpe ratios. Even look-ahead-free rta-bench-1 admits survivorship in its universe.

### Cited Findings
- **Look-Ahead-Bench (arXiv 2601.13770; AAPL, MSFT, GOOGL, NVDA, TSLA).** P1 = 1 Apr to 30 Sep 2021 (in-training, Buy & Hold +25.32%); P2 = 1 Jul to 31 Dec 2024 (Buy & Hold +24.75%). Alpha is return minus buy-and-hold, in points:

  | Model | P1 alpha | P2 alpha | Decay |
  |---|---|---|---|
  | Llama 3.1 8B | +13.81 | −3.42 | −17.23 |
  | Llama 3.1 70B | +19.27 | +4.02 | −15.25 |
  | DeepSeek 3.2 | +20.73 | −1.04 | −21.77 |
  | Pitinf-Small | | | +0.31 |
  | Pitinf-Medium | | | +0.85 |
  | Pitinf-Large | | | +1.30 |
  | Momentum (3M), rule baseline | +7.96 | +5.75 | |

  - VERBATIM: standard models "suffer from severe alpha decay when moved from memorized training windows". The paper calls itself a proof-of-concept (5 stocks, 6-month windows). The Pitinf models come from the author's affiliated vendor (PiT-Inference). — [arXiv 2601.13770](https://arxiv.org/html/2601.13770)
- **Profit Mirage (arXiv 2510.07920; NASDAQ-100; GPT-4o, cutoff Oct 2023; backtest Q2–Q3 2021 vs post-cutoff Q3–Q4 2024, market +13.79% vs +13.35%).**
  - Total-return decay ranged from 50.18% (TradingAgents) to 71.85% (FinMem). Sharpe decay ranged from 51.48% (QuantAgent) to 62.23% (FinCON); TradingAgents 55.68%.
  - Memorization QA on Jan 2022 to Jun 2023: accuracy 85.37% on price inquiries, 92.94% on event impacts, 89.83% on market performance, 90.23% on trend prediction.
  - Fine-tuning raised in-distribution accuracy (Qwen2.5-7B 51.61% to 72.16%) but cut generalization by 21.53%.
  - VERBATIM: "all methods show a significant drop in the period after the base model (i.e., GPT-4o) is released." SUMMARY (abstract): almost every published LLM agent fails to beat a random baseline after the cutoff; random-baseline numbers are not given in the text. — [arXiv 2510.07920](https://arxiv.org/html/2510.07920v1)
- **rta-bench-1 memory probe.** GPT-5.6 Luna's rank correlation with actual 2022 moves was 0.69 (0.51–0.80), against 0.25 after its cutoff. Sonnet 4.6 scored 0.52, Haiku 4.5 0.24 and Llama 3B 0.06.
  - VERBATIM: "The model remembers the period but does not use what it remembers in this task."
  - Limitation, VERBATIM: "The stock list is today's 56 largest US companies, so every period carries survivorship."
  - Decisions "did no better than random stocks of the same sector". — [arXiv 2611.19530](https://arxiv.org/html/2611.19530)
- **FINSABER.** Survivorship bias, meaning a universe of only currently active stocks, is cited as distorting annual returns by 0.1–0.9%. FINSABER uses historical S&P 500 constituents including delisted names. It concedes that look-ahead from pretraining is not fully eliminated. VERBATIM: "the perceived superiority of LLM-based methods deteriorates under more robust and broader long-term testing." — [arXiv 2505.07078](https://arxiv.org/html/2505.07078)
- **Short windows.** TradingAgents was tested over 3 months (Q1 2024), with Sharpe 5.60–8.21 that the authors acknowledge exceeds the expected range. Agent Market Arena covered 2 months on 4 assets. StockBench covered 82 days. AI-Trader covered 2–5 weeks. Alpha Arena covered 17 days. — [TradingAgents](https://arxiv.org/html/2412.20138); [AMA](https://arxiv.org/html/2510.11695v2); [StockBench](https://arxiv.org/html/2510.02209v2); [AI-Trader](https://arxiv.org/html/2512.10971)
- **Related (title and abstract only, not read in full).** "Summoning the Oracle to Slay It" (arXiv 2605.24564) names "parametric look-ahead bias" stored in the weights and proposes an inference-time decoding fix (FinCAD). — [arXiv 2605.24564](https://arxiv.org/pdf/2605.24564.pdf)

### Inferences
- Across three independent setups (Profit Mirage, Look-Ahead-Bench, rta-bench-1), the pre-cutoff advantage of LLM agents shrinks by half or more, or disappears, out of sample. Point-in-time models (Pitinf) and live or after-cutoff windows are the main remedies; survivorship-free universes are still rare.

### Gaps
- Profit Mirage's absolute pre/post returns and random-baseline values appear only in figures and were not extractable.
- I did not read the full text of arXiv 2605.24564 (FinCAD).
- FIDES-Live's time period was not stated on the abstract page.
