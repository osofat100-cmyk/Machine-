# Model Characteristics vs LLM Trading Performance (official papers, 2024 to Nov 2026)

**How to read these notes**
- **[V]** means a verbatim quote, taken from the paper's arXiv HTML. **[S]** means my summary or a figure read from a table. **[C]** means my own arithmetic on the paper's table numbers.
- I pulled the quotes and tables with a fetch tool that summarises pages. Quotes should be near-verbatim, but spot-check any quote before publishing it.
- Each finding is tagged with its market and period.
- Abbreviations: CR = cumulative return, SR = Sharpe ratio (unless a paper says it means Sortino), MDD = max drawdown.

**Papers used (all primary arXiv sources)**

| Paper | Market | Period | Models tested |
|---|---|---|---|
| StockBench, [arXiv 2510.02209](https://arxiv.org/html/2510.02209) | Top-20 DJIA stocks | Mar 3 to Jun 30 2025 (82 trading days) | 14 models |
| LiveTradeBench, [arXiv 2511.03628](https://arxiv.org/html/2511.03628) | US stocks (15 equities/ETFs + cash) and Polymarket (10 markets), live | Aug 18 to Oct 24 2025 (50 trading days) | 21 models |
| InvestorBench, [arXiv 2412.18174](https://arxiv.org/html/2412.18174) | 7 stocks; BTC, ETH; ETF | Stocks 2020-10-01 to 2021-05-06; crypto 2023-04-05 to 2023-11-05 | 13 backbones |
| TraderBench, [arXiv 2603.00285](https://arxiv.org/html/2603.00285) | Crypto and options tracks plus knowledge retrieval | Not stated | 12 or 13 models (the paper is inconsistent) |
| AI-Trader, [arXiv 2512.10971](https://arxiv.org/html/2512.10971) | Nasdaq-100 hourly and SSE-50 daily | Oct 1 to Nov 7 2025 | 6 models |
| AI-Trader (same paper) | 10 crypto assets, daily | Nov 1 to Nov 14 2025 | same 6 models |
| Agent Market Arena (AMA), [arXiv 2510.11695](https://arxiv.org/html/2510.11695) | TSLA, BMRN, BTC, ETH, live | Aug 1 to Sep 30 2025 | 5 backbones x 4 agents |
| The Price of Thought, [arXiv 2609.30705](https://arxiv.org/html/2609.30705v1) (NJIT, Sep 2026) | 100 liquid US stocks | 241 formation dates in 2024 | 3 backbones at different reasoning levels |
| To Trade or Not to Trade, [arXiv 2507.08584](https://arxiv.org/html/2507.08584v1) | AAPL, NVDA, F, MSFT; synthetic S&P 500 backtest | Equities Sep 17 2024 to Apr 24 2025; synthetic 2023 H1 | 7 models |
| FINSABER, [arXiv 2505.07078](https://arxiv.org/html/2505.07078) (KDD '26) | US equities (S&P 500 history) | 2004 to 2024, plus 2022-10 to 2023-04 | GPT-4o vs GPT-4o-mini |
| CLQT, [arXiv 2606.29771](https://arxiv.org/html/2606.29771) | S&P 100-derived universe (~72 stocks) | 2025-06-16 to 2026-06-12, plus 4-week live paper track | 5 models |
| Can AI Make Money in Crypto?, [arXiv 2609.34510](https://arxiv.org/html/2609.34510v1) | 10 coins | Backtest 2025; paper trading Jun to Sep 2026; live Aug to Sep 2026 | DeepSeek, Qwen and agent methods |
| CryptoTrade, [arXiv 2407.09546](https://arxiv.org/html/2407.09546) (EMNLP 2024) | BTC, ETH, SOL | Bull, sideways and bear windows of 2023 | GPT-4 vs GPT-3.5 |

---

## 1. Thinking (reasoning) vs non-thinking models

### Takeaway
Every paper that compares a reasoning model directly with its non-thinking sibling finds no reliable trading advantage from reasoning, in stocks, crypto or prediction markets. The comparisons are:
- Qwen3-235B Think vs Instruct (StockBench, LiveTradeBench)
- DeepSeek-R1 vs V3.1 (LiveTradeBench)
- Qwen3-32B with and without chain-of-thought (TraderBench)
- DeepSeek, GPT and Gemini at different reasoning levels (Price of Thought)

The only weakly positive evidence comes from:
- per-symbol results in "To Trade or Not to Trade", where reasoning models were "often within the top two", though not consistently;
- one crypto result in InvestorBench (o1-preview was best on BTC).

Reasoning models tend to be more volatile.

### Cited Findings

**StockBench (DJIA stocks, Mar to Jun 2025)**
- [V] Section heading: "Reasoning model does not guarantee better performance." The paper says thinking models "do not consistently outperform instruction-tuned counterparts in this trading task." [Source](https://arxiv.org/html/2510.02209)
- [V] "This suggests there is still a gap between reasoning ability and effective decision-making in dynamic, noisy environments." [Source](https://arxiv.org/html/2510.02209)
- [S] Paired results (return / MDD / Sortino / rank). The Thinking variant has a slightly higher return but a deeper drawdown, and the Instruct variant ranks higher on the composite. [Source](https://arxiv.org/html/2510.02209)
  - Qwen3-235B-Instruct: 2.4% / -11.2% / 0.0299 / rank 2
  - Qwen3-235B-Think: 2.5% / -14.9% / 0.0309 / rank 4
- [S] Other results: Qwen3-30B-Think 2.1% (rank 6); OpenAI-o3 1.9%, -13.2%, Sortino 0.0267 (rank 5); non-reasoning Kimi-K2 1.9%, -11.8%, 0.0420 (rank 1). [Source](https://arxiv.org/html/2510.02209)
- [V] Error analysis: "thinking models make fewer arithmetic errors than instruct models," but "they also incur more schema errors." [Source](https://arxiv.org/html/2510.02209)

**LiveTradeBench (US stocks and Polymarket, live, Aug 18 to Oct 24 2025)**
- [V] Section 5.3 heading: "Large reasoning models do not confer trading advantages." The paper says reasoning models (DeepSeek-R1, Qwen3-235B-A22B-Thinking, GPT-o3) show "substantially higher volatility (>>140 in Polymarket)," which it attributes to "over-adjustment during the decision process." [Source](https://arxiv.org/html/2511.03628)
- [S] Paired results, stocks CR / SR and Polymarket CR / SR. [Source](https://arxiv.org/html/2511.03628)

  | Model | Stocks CR | Stocks SR | Polymarket CR | Polymarket SR |
  |---|---|---|---|---|
  | Qwen3-235B-Instruct | 3.52% | 1.32 | -54.24% | -2.97 |
  | Qwen3-235B-Thinking | 1.78% | 0.60 | -57.62% | -1.81 |
  | DeepSeek-V3.1 | 2.46% | 0.86 | -4.68% | -0.07 |
  | DeepSeek-R1 | 2.10% | 0.78 | -13.19% | 0.14 |
  | GPT-o3 | 6.04% | 2.57 | -54.84% | -3.68 |

- [S] GPT-o3 was the 2nd-best stock model, but it had one of the worst Polymarket results. [Source](https://arxiv.org/html/2511.03628)

**TraderBench (crypto and options; period not stated)**
- [S] Turning on chain-of-thought in Qwen3-32B raised Knowledge Retrieval from 14.4 to 40.5 (+26.1). Trading changed by +0.3 in crypto and -0.1 in options. [Source](https://arxiv.org/html/2603.00285)
- [V] "extended thinking helps retrieval (+26 points) but has zero impact on trading." [Source](https://arxiv.org/html/2603.00285)

**The Price of Thought (100 liquid US stocks, 241 dates in 2024, 10 bps one-way cost)**
- Setup [S]:
  - DeepSeek-Flash was tested at none, low, high and maximum reasoning.
  - GPT-5.6 Luna was tested at none vs low.
  - Gemini 3.1 Flash-Lite was tested at minimal vs low.
- [S] Low-vs-baseline differences in bps/day (numerical / identifiable news / masked news). All nine 95% confidence intervals include zero. [Source](https://arxiv.org/html/2609.30705v1)
  - DeepSeek: +6.159 / +0.378 / +1.449
  - GPT: +3.540 / -0.626 / +0.040
  - Gemini: +0.758 / -0.142 / -1.123
- [S] DeepSeek audit over 3 generations. Low vs none: -0.529 / -8.525 / -9.016 bps/day; the masked-news result (CI -16.248 to -1.784) is significant harm. Maximum vs none: -4.875 / -4.053 / -8.246. [Source](https://arxiv.org/html/2609.30705v1)
- [V] "Across all three model families, additional reasoning does not produce a reliable improvement in net portfolio returns." [Source](https://arxiv.org/html/2609.30705v1)
- [V] "For DeepSeek, where we examine the full progression from no reasoning to maximum reasoning, performance is nonmonotonic." [Source](https://arxiv.org/html/2609.30705v1)
- [V] "extra thought changes decisions but does not reliably pay for itself." [Source](https://arxiv.org/html/2609.30705v1)
- [V] "Baseline reasoning is therefore the conservative default unless the target task shows reproducible incremental value." [Source](https://arxiv.org/html/2609.30705v1)

**To Trade or Not to Trade (AAPL, NVDA, F, MSFT, Sep 2024 to Apr 2025; synthetic S&P 500 backtest, 2023 H1)**
- [V] "Models such as R1, Sonnet 3.7, and o3-mini are all reasoning LLMs and are often within the top two trading performances." The paper adds: "However, this is not consistent across symbols." [Source](https://arxiv.org/html/2507.08584v1)
- [V] On the synthetic backtest: "reasoning LLMs do not necessarily result in improved trading performance," and "non-reasoning LLMs can be highly performant such as the Sonnet 3.5v2." [Source](https://arxiv.org/html/2507.08584v1)
- [S] Examples, Sharpe with news only (N) and with news plus metrics (N+M). [Source](https://arxiv.org/html/2507.08584v1)
  - AAPL (N): non-reasoning Llama 3.3 4.56 and 4o-mini 3.70 beat o3-mini 2.67 and R1 2.39. Buy-and-hold was 3.53.
  - NVDA (N+M): Llama 3.3 5.19 was best, Sonnet 3.7 4.03 second, and R1 0.05.

**InvestorBench (stocks 2020-10 to 2021-05; crypto 2023-04 to 2023-11)**
- [S] o1-preview, the only reasoning model tested, had a lower average stock CR than non-reasoning GPT-4 and GPT-4o. [Source](https://arxiv.org/html/2412.18174)
  - Average stock CR / SR: o1-preview 25.057 / 0.592; GPT-4 43.696 / 0.972; GPT-4o 39.031 / 1.041.
- [S] On BTC, o1-preview was the best model (CR 34.060, SR 1.114 vs buy-and-hold 21.821). On ETH it was weak (CR 2.496 vs buy-and-hold 4.528). [Source](https://arxiv.org/html/2412.18174)

**CLQT (S&P 100-derived universe, Jun 2025 to Jun 2026)**
- [S] Models are labelled by reasoning style:
  - gpt-5-mini: "reasoning, effort low"
  - claude-haiku-4.5: "thinking off"
  - deepseek-chat-v3.1: "hybrid→non-thinking"
  - qwen3-235b: "non-thinking"
- [S] The paper has no thinking-vs-non-thinking ablation. The top composite score went to non-thinking deepseek in structured mode: Sharpe 2.99, CumRet +28.6%, APM-CS 72.9. Reasoning gpt-5-mini in structured mode scored 2.62, +22.5%, 67.4. [Source](https://arxiv.org/html/2606.29771)

### Inferences
- [C] Same-base pairs in LiveTradeBench: the thinking variant was worse on stock CR in 2 of 2 pairs and worse on Polymarket CR in 2 of 2 pairs. In StockBench, the Qwen3-235B Think vs Instruct gap is within noise (+0.1 point return, but -3.7 points worse drawdown).
- Across 5 independent papers (StockBench, LiveTradeBench, TraderBench, Price of Thought, To Trade or Not to Trade), reasoning gives no robust edge. The consistent side effects are more variance, more volatility, more schema/format errors, and nonmonotonic return curves.
- **Contradiction:** "To Trade or Not to Trade" reports reasoning models "often within the top two" on real equities, and InvestorBench's o1-preview won BTC. Both are small-sample, per-asset results, and both papers qualify them themselves.

### Gaps
- I found no trading paper that ablates thinking for Kimi, GLM, MiniMax or Nemotron.
- I found no paper that sweeps reasoning effort on crypto. The Price of Thought covers stocks only.
- The Alpha Arena (Nof1) crypto contest is not an official paper, so I excluded it.

---

## 2. Model size (within-family scale)

### Takeaway
The evidence is mixed and depends on the market:
- InvestorBench claims bigger is better in stocks, and its Sharpe numbers partly support this. Its own crypto table contradicts it.
- TraderBench finds scale matters less than tool access.
- FINSABER finds larger models "do not reliably outperform smaller ones".
- StockBench GPT-OSS 120B > 20B is the cleanest "bigger is better" pair, but both models lose to buy-and-hold.

### Cited Findings

**InvestorBench (stocks 2020-10-01 to 2021-05-06)**
- [V] "Model parameter size increment enhances agent financial decision-making quality and robustness." The paper says open-source models above 67B parameters showed higher CR and SR with less variance. [Source](https://arxiv.org/html/2412.18174)
- [V] Crypto (BTC/ETH, 2023-04 to 2023-11): "Large-sized open-source models and proprietary models are needed to effectively capture trading signals." The paper says mid- and small-size open models generally underperformed the market. [Source](https://arxiv.org/html/2412.18174)
- [S] Average stock CR / SR as printed in the paper. [Source](https://arxiv.org/html/2412.18174)

  | Family | Large | Mid | Small |
  |---|---|---|---|
  | Qwen2.5 | 72B: 46.153 / 1.276 | 32B: 20.884 / 0.823 | 7B: 29.515 / 0.722 |
  | Llama-3.1 | 70B: 38.946 / 0.864 | none | 8B: 25.463 / 0.567 |
  | Yi-1.5 | none | 34B: 37.966 / 0.831 | 9B: 22.913 / 0.478 |

  - DeepSeek-67B-Chat was 26.941 / 0.717, below the 15.7B DeepSeek-V2-Lite on CR (28.745 / 0.813).
- [C] Sharpe rises with size in every family. CR is non-monotonic for Qwen (7B beats 32B), and DeepSeek 67B < 15.7B on CR.
- [C] Caveat on the "Avg" column: it does not equal the simple mean of the seven per-stock CRs. Buy-and-hold's per-stock mean is about 28.8 against the printed 34.099, and Qwen2.5-72B's is about 33.1 against 46.153. Treat the averages with caution. [Source](https://arxiv.org/html/2412.18174)
- [S] Crypto size results contradict the paper's own claim. [Source](https://arxiv.org/html/2412.18174)
  - BTC CR, Qwen2.5: 72B 0.549 < 32B 11.566 < 7B 19.477, so bigger was worse.
  - BTC CR, Llama: 70B 20.440 ≈ 8B 20.521.
  - ETH CR, Qwen2.5: 72B 11.984 > 32B 2.823 > 7B -1.339, so bigger was better.
  - ETH CR, Llama: 70B -11.888 vs 8B 4.939, so bigger was worse.

**StockBench (DJIA, Mar to Jun 2025)**
- [S] Same-family pairs, both open-weight:
  - GPT-OSS-120B: -0.9% return, Sortino 0.0156 (rank 13). GPT-OSS-20B: -2.8%, -0.0069 (rank 14, the only negative Sortino).
  - Qwen3-235B-Think 2.5% vs Qwen3-30B-Think 2.1%.

  The bigger model wins both pairs, by small margins. [Source](https://arxiv.org/html/2510.02209)
- [V] StockBench's "Model scale confers robustness" refers to robustness as the portfolio grows. Kimi-K2 showed "greater robustness to portfolio expansion." This is not a clean parameter-count ablation. [Source](https://arxiv.org/html/2510.02209)

**TraderBench (crypto and options)**
- [S] Overall scores by size:
  - Qwen3: 32B 48.4; 8B 44.9; 30B-A3B (MoE, 3B active) 44.7.
  - GPT-OSS: 120B 50.9 vs 20B 50.6, a gap of 0.3.

  [Source](https://arxiv.org/html/2603.00285)
- [V] "For tool-dependent tasks, improving tool access and planning matters more than model scale." Also: "model capability is necessary but not sufficient." [Source](https://arxiv.org/html/2603.00285)

**FINSABER (US equities; KDD '26)**
- [V] "We show that larger models do not reliably outperform smaller ones." [Source](https://arxiv.org/html/2505.07078)
- [S] Sharpe, 2022-10-06 to 2023-04-10 (TSLA / NFLX / AMZN / MSFT). GPT-4o-mini beats GPT-4o on 3 of 4 stocks in both agents. [Source](https://arxiv.org/html/2505.07078)
  - FinMem: 4o-mini 0.927 / 1.704 / 0.297 / -0.554; 4o 0.404 / 0.896 / -0.968 / 0.792.
  - FinAgent: 4o-mini 1.389 / 0.487 / 0.883 / 0.575; 4o 1.203 / 1.169 / 0.328 / 0.364.

**CryptoTrade (BTC, ETH, SOL, 2023)**
- [S] Older/smaller GPT-3.5-turbo vs GPT-4, total return in bull / sideways / bear windows. [Source](https://arxiv.org/html/2407.09546)
  - BTC: 3.5 28.47 / -5.08 / -13.71; GPT-4 26.35 / -4.07 / -11.72.
  - SOL: 3.5 102.45 / -13.05 / -24.08; GPT-4 99.84 / -2.16 / -19.55.
  - So GPT-3.5 was slightly better in bull windows, and GPT-4 was better in sideways and bear windows.
- [S] The paper is inconsistent about whether it tested GPT-4 or GPT-4o. [Source](https://arxiv.org/html/2407.09546)

**LiveTradeBench (US stocks and Polymarket, Aug to Oct 2025)**
- [S] Within-family stock CR. [Source](https://arxiv.org/html/2511.03628)
  - Claude-Opus-4 3.93% vs Claude-Sonnet-4 2.45%: bigger better.
  - Gemini-2.5-Pro 1.95% vs Gemini-2.5-Flash 2.10%: bigger slightly worse.
  - Llama4-Maverick 4.46% vs Llama4-Scout 4.65%: bigger slightly worse.
  - Polymarket: Opus-4 -2.04% vs Sonnet-4 -40.32%; Gemini Pro -35.15% vs Flash -22.40%.
- LiveTradeBench draws no size conclusion. I took the size ordering (Opus > Sonnet, Pro > Flash, Maverick > Scout) from public model descriptions, not from the paper.

### Inferences
- Size helps most clearly in risk-adjusted terms (InvestorBench Sharpe; GPT-OSS 120B > 20B). Even there the gains are small next to the effect of agent design and tool access (TraderBench, AMA).
- In crypto, the same InvestorBench table shows bigger losing on BTC. Treat "bigger trades better" as unproven for crypto.

### Gaps
- I found no paper with a clean size sweep (for example Qwen 7B/14B/32B/72B) under identical prompts, on both stocks and crypto, with significance tests.
- FLAG-Trader (arXiv 2502.11433) appears to reuse the InvestorBench Qwen2.5 numbers. It is not independent, and I did not verify it.
- I found no Nemotron or GLM size comparisons in trading papers.

---

## 3. Open-weight vs closed (proprietary)

### Takeaway
No consistent gap exists:
- InvestorBench (2020-21 stocks) claims proprietary superiority, but its own table has open Qwen2.5-72B at the top of the stock average.
- StockBench (2025) has open-weight models in its top 4 (Kimi-K2, Qwen3-235B, GLM-4.5) and the open GPT-OSS models at the bottom.
- TraderBench finds the proprietary gap comes from knowledge retrieval, not trading.
- AI-Trader's top US/A-share model was open-weight MiniMax-M2, and open DeepSeek-v3.1 was the only model to beat the crypto baseline.

### Cited Findings

**InvestorBench**
- [V] Section heading: "Superior stock trading performance is achieved with proprietary LLMs as agent backbones." Also: "Proprietary models exhibit significantly stronger decision-making capabilities compared to even the largest open-source LLMs." [Source](https://arxiv.org/html/2412.18174)
- [S] Contradicted by its own Table 2: Qwen2.5-72B-Instruct (open) has average stock CR 46.153 and SR 1.276, above GPT-4 (43.696 / 0.972), GPT-4o (39.031 / 1.041) and o1-preview (25.057 / 0.592). [Source](https://arxiv.org/html/2412.18174)
- [V] Finance-tuned models: "domain-specific LLMs did not provide a decisive advantage in sequential stock trading decision-making tasks". Palmyra-Fin-70B had average stock CR -0.453 vs buy-and-hold 34.099. [Source](https://arxiv.org/html/2412.18174)
- [S] ETF track: the paper claims proprietary models significantly outperform, but its ETF table shows Palmyra-Fin-70B with the highest CR (24.759) vs GPT-o1-preview (21.224). [Source](https://arxiv.org/html/2412.18174)

**StockBench (DJIA, Mar to Jun 2025)**
- [S] Ranking from 1 to 14. StockBench draws no explicit open/closed conclusion. [Source](https://arxiv.org/html/2510.02209)

  | Rank | Model | Weights |
  |---|---|---|
  | 1 | Kimi-K2 | open |
  | 2 | Qwen3-235B-Ins | open |
  | 3 | GLM-4.5 | open |
  | 4 | Qwen3-235B-Think | open |
  | 5 | OpenAI-o3 | closed |
  | 6 | Qwen3-30B-Think | open |
  | 7 | Claude-4-Sonnet | closed |
  | 8 | DeepSeek-V3.1 | open |
  | 9 | GPT-5 | closed |
  | 10 | Qwen3-Coder | open |
  | 11 | DeepSeek-V3 | open |
  | 12 | Passive baseline | n/a |
  | 13 | GPT-OSS-120B | open |
  | 14 | GPT-OSS-20B | open |

**TraderBench (crypto and options)**
- [S] Overall score:
  - Proprietary: Gemini-3-Pro 64.3, Grok 4.1 Fast 63.7, GPT-5.2 61.9, GPT-4o 53.3.
  - Open: Kimi-K2.5 54.4, GLM-4.7-Flash 53.9, GPT-OSS-120B 50.9, GPT-OSS-20B 50.6, Qwen3-32B 48.4, Gemma3-27B 47.2.

  [Source](https://arxiv.org/html/2603.00285)
- [V] "the proprietary–open-source gap is driven by knowledge retrieval, not by options or crypto performance." [Source](https://arxiv.org/html/2603.00285)
  - [S] Knowledge Retrieval scores: GPT-OSS-120B 32.5 and 20B 42.4, vs GPT-5.2 50.6 and Grok 61.6.

**AI-Trader (Nasdaq-100 and SSE-50, Oct 1 to Nov 7 2025; crypto, Nov 1 to 14 2025)**
- [S] CR by market. Baselines: QQQ 1.87%, SSE-50 1.65%, CD5 crypto index -14.30%. [Source](https://arxiv.org/html/2512.10971)

  | Model | Weights | US CR | A-share CR | Crypto CR |
  |---|---|---|---|---|
  | MiniMax-M2 | open | 9.56% | 1.31% | -14.80% |
  | DeepSeek-v3.1 | open | 8.39% | -1.23% | -12.18% |
  | Claude-3.7-Sonnet | closed | 3.11% | 0.84% | -15.30% |
  | GPT-5 | closed | 1.56% | -3.53% | -16.41% |
  | Qwen3-Max | closed API | 0.39% | -3.86% | -16.85% |
  | Gemini-2.5-Flash | closed | -0.06% | -1.53% | -18.63% |

- [V] MiniMax-M2 is "the only model that maintains relative advantage in both the U.S. and A-share markets". DeepSeek-v3.1 is "the sole agent outperforming the baseline in the Crypto market". [Source](https://arxiv.org/html/2512.10971)

**LiveTradeBench (stocks and Polymarket, Aug to Oct 2025)**
- [S] Top stock CR: GPT-4.1 6.25%, GPT-o3 6.04%, GPT-5 5.31% (closed), then Qwen2.5-72B 5.15%, Llama4-Scout 4.65%, Llama4-Maverick 4.46% (open). [Source](https://arxiv.org/html/2511.03628)
- [S] Top Polymarket CR: Claude-Sonnet-3.7 20.54%, Grok-4 7.38% (closed), then Qwen2.5-72B 1.63%, Llama3.3-70B 1.58% (open). [Source](https://arxiv.org/html/2511.03628)
- LiveTradeBench draws no open/closed conclusion.

**Can AI Make Money in Crypto? (10 coins; backtest 2025)**
- [S] Direct LLM trading in the 2025 backtest. [Source](https://arxiv.org/html/2609.34510v1)
  - DeepSeek (V4 Flash, open): CR -43.30%, MDD 96.85%.
  - Qwen (3.6 Max Preview, API): CR -68.62%.
  - FinGPT (Llama-2-13B LoRA): -15.15%.
- [V] "none of the evaluated RL-, LLM-, or agent-based methods is profitable over the same period". [Source](https://arxiv.org/html/2609.34510v1)

### Inferences
- [C] Before mid-2025 (InvestorBench, 2020-21 data), proprietary leadership was claimed but not clean. In 2025 live or forward tests (StockBench, AI-Trader), open-weight Chinese models (Kimi-K2, Qwen3-235B, GLM-4.5, MiniMax-M2, DeepSeek-v3.1) match or beat closed frontier models on stock returns.
- In TraderBench, closed models lead on overall score, but only through knowledge retrieval.
- "Open" is not one group. GPT-OSS ranks last in StockBench and lowest in TraderBench retrieval, while Kimi, Qwen and GLM rank at the top.

### Gaps
- No paper tests the open/closed gap statistically, for example with bootstrapped confidence intervals across many runs.
- Qwen3-Max is API-only, which blurs open vs closed for the Qwen family.

---

## 4. General capability (LMArena and similar) vs trading results

### Takeaway
Correlation is near zero or negative where it has been measured:
- LiveTradeBench: Spearman rho with LMArena score is 0.054 (stocks) and -0.38 (Polymarket).
- TraderBench: Pearson r with GDPVal is 0.16 for crypto and 0.36 for trading overall.

Several other papers state in words that general capability does not transfer to trading (AI-Trader, AMA, FINSABER, CryptoBench).

### Cited Findings

**LiveTradeBench (stocks and Polymarket, Aug to Oct 2025)**
- [V] Section heading: "High general LLM capability does not imply strong financial performance." [Source](https://arxiv.org/html/2511.03628)
- [S] Spearman correlation between LMArena score and cumulative return:
  - US stocks: 0.054, which the paper calls "virtually no relationship".
  - Polymarket: "the correlation drops to –0.38".

  [Source](https://arxiv.org/html/2511.03628)
- [V] Section heading: "Trading performance on one market does not generalize to another." [Source](https://arxiv.org/html/2511.03628)
  - [S] GPT-4.1 had the best stock CR (6.25%) but a Polymarket CR of -33.69%.
  - [S] Qwen2.5-72B and Grok-4 were relatively consistent across both markets.

**TraderBench (crypto and options)**
- [S] Pearson correlation with GDPVal (professional tasks across 44 occupations) vs: [Source](https://arxiv.org/html/2603.00285)
  - Trading: r = 0.36
  - Crypto: r = 0.16
  - Knowledge Retrieval: r = 0.62
- [S] The paper concludes that professional output quality and adversarial trading resilience measure different capabilities. [Source](https://arxiv.org/html/2603.00285)

**AI-Trader (US stocks, A-shares and crypto, Oct to Nov 2025)**
- [V] "General intelligence of large language models does not automatically translate into effective trading capability." [Source](https://arxiv.org/html/2512.10971)
- [V] "Risk control capability is the key determinant of an AI agent's cross-market robustness." [Source](https://arxiv.org/html/2512.10971)
- [S] Frontier GPT-5 ranked 4th of 6 in US stocks (1.56% vs QQQ 1.87%). Gemini-2.5-Flash was last in all three markets. [Source](https://arxiv.org/html/2512.10971)

**Agent Market Arena (TSLA, BMRN, BTC, ETH, live Aug to Sep 2025)**
- [V] "model backbones contribute less to outcome variation." [Source](https://arxiv.org/html/2510.11695)
- [V] "modifying the underlying LLM within a fixed agent framework produces only modest changes in profitability". [Source](https://arxiv.org/html/2510.11695)
- [V] Agent design "plays a more decisive role in shaping profitability and stability than merely upgrading to a more powerful model". [Source](https://arxiv.org/html/2510.11695)
- [S] Example: in TradeAgent, the weakest backbone (Gemini-2.0-flash) had the best TSLA CR (21.91%). GPT-4.1 had -38.72%. [Source](https://arxiv.org/html/2510.11695)
- [S] Caveat: HedgeFundAgent's rows are identical across all backbones. The paper does not explain this. [Source](https://arxiv.org/html/2510.11695)

**StockBench (DJIA, Mar to Jun 2025)**
- [S] GPT-5 ranked 9th (0.3% return, below the 0.4% passive baseline). Kimi-K2 ranked 1st. [Source](https://arxiv.org/html/2510.02209)

**CLQT (S&P 100-derived universe, Jun 2025 to Jun 2026)**
- [V] "the capability leader is not the Sharpe leader." [Source](https://arxiv.org/html/2606.29771)
- [V] "Net of realistic costs, agents clear defensive baselines but do not cleanly beat the index." [Source](https://arxiv.org/html/2606.29771)

**Can AI Make Money in Crypto?**
- [V] "strong historical performance does not reliably transfer to prospective trading". [Source](https://arxiv.org/html/2609.34510v1)
- [S] Qwen in three stages:
  - CR: backtest 6.18%, paper trading 10.10%, live 3.72%.
  - Alpha: -0.63%, 15.80%, -28.10%.
  - Sharpe: 1.34, 1.85, 0.34.

  [Source](https://arxiv.org/html/2609.34510v1)

**CryptoBench (expert crypto tasks, not P&L trading)**
- [S, search snippet only] The paper says "raw model capability does not directly translate into effective agentic execution." I did not read the full text. [Source](https://arxiv.org/pdf/2512.00417v5)

### Inferences
- Within one paper and one market, trading rank is close to uncorrelated with general leaderboard rank. Rankings also flip across markets: for example GPT-4.1 and GPT-o3 were near the top in stocks and near the bottom in Polymarket.
- Model selection by LMArena rank is not supported as a proxy for trading skill.

### Gaps
- Only LiveTradeBench computes a correlation with LMArena, and it has 21 models over 50 days with no p-value reported.
- No paper correlates leaderboard rank with crypto P&L specifically. TraderBench's crypto r = 0.16 uses GDPVal, not LMArena.

---

## 5. Model family: does any family rank high repeatedly?

### Takeaway
No family dominates across independent papers. The most recurring "top" placements are open-weight Chinese families:
- **Qwen:** top in StockBench and InvestorBench, consistent in LiveTradeBench, but weak in AI-Trader and in the crypto paper.
- **DeepSeek-V3.1:** best in AI-Trader crypto, 2nd in AI-Trader US, top composite in CLQT; but mid-pack in StockBench and LiveTradeBench.
- **MiniMax-M2 and Kimi-K2:** each top in one paper. Kimi-K2 was among the worst on Polymarket.

Gemini placed low in most return-based tests but tops TraderBench. GPT-5 is mid or low in three of three papers. Rankings flip between papers, which suggests period, market and agent effects dominate.

### Cited Findings

**Qwen**
- StockBench: Qwen3-235B-Ins ranked 2nd and Think 4th; Qwen3-Coder ranked 10th (0.2%). [Source](https://arxiv.org/html/2510.02209)
- InvestorBench: Qwen2.5-72B had the highest average stock CR and SR (46.153 / 1.276). [Source](https://arxiv.org/html/2412.18174)
- LiveTradeBench: Qwen2.5-72B had stock CR 5.15% (4th) and was "relatively consistent" across markets. Qwen3-235B had Polymarket CR -54% to -58%. [Source](https://arxiv.org/html/2511.03628)
- AI-Trader: Qwen3-Max was 5th of 6 in US stocks (0.39%) and last in A-shares (-3.86%). [Source](https://arxiv.org/html/2512.10971)
- Crypto paper: Qwen direct trading had a 2025 backtest CR of -68.62%. [Source](https://arxiv.org/html/2609.34510v1)

**DeepSeek**
- AI-Trader: DeepSeek-v3.1 had US CR 8.39% (2nd) and was the only model to beat the crypto baseline (-12.18% vs -14.30%). [Source](https://arxiv.org/html/2512.10971)
- CLQT: deepseek in structured mode had the top APM-CS (72.9) and the top CumRet (+28.6%). [Source](https://arxiv.org/html/2606.29771)
- StockBench: V3.1 ranked 8th (1.1%) and V3 11th. [Source](https://arxiv.org/html/2510.02209)
- LiveTradeBench: V3.1 had stock CR 2.46% and R1 2.10%, both in the lower half. [Source](https://arxiv.org/html/2511.03628)
- InvestorBench: DeepSeek-67B was 2nd-best on BTC (28.307). [Source](https://arxiv.org/html/2412.18174)

**Kimi**
- StockBench: Kimi-K2 ranked 1st (best Sortino 0.0420). [Source](https://arxiv.org/html/2510.02209)
- LiveTradeBench: Kimi-K2 had stock CR 3.07% (middle) and Polymarket CR -53.44% with SR -5.26, the worst Sharpe. [Source](https://arxiv.org/html/2511.03628)
- TraderBench: Kimi-K2.5 scored 54.4, the best open model. [Source](https://arxiv.org/html/2603.00285)

**GLM**
- StockBench: GLM-4.5 ranked 3rd. [Source](https://arxiv.org/html/2510.02209)
- TraderBench: GLM-4.7-Flash scored 53.9. [Source](https://arxiv.org/html/2603.00285)

**MiniMax**
- AI-Trader: MiniMax-M2 was best in US stocks (9.56%, Sortino 4.42) and in A-shares (1.31%). It was 3rd in crypto (-14.80%). [Source](https://arxiv.org/html/2512.10971)
- CLQT used minimax-m3 only as a judge, so it gives no trading result. [Source](https://arxiv.org/html/2606.29771)

**GPT / OpenAI**
- GPT-5:
  - StockBench: 9th (0.3%). [Source](https://arxiv.org/html/2510.02209)
  - AI-Trader: 4th of 6. [Source](https://arxiv.org/html/2512.10971)
  - LiveTradeBench: 3rd in stocks (5.31%), but -23.96% on Polymarket. [Source](https://arxiv.org/html/2511.03628)
- GPT-4.1 and o3 were 1st and 2nd in LiveTradeBench stocks. [Source](https://arxiv.org/html/2511.03628)
- GPT-OSS was last in StockBench. [Source](https://arxiv.org/html/2510.02209)
- GPT-5.2 scored 61.9 (3rd) in TraderBench. [Source](https://arxiv.org/html/2603.00285)

**Claude**
- LiveTradeBench: Claude-Sonnet-3.7 was best on Polymarket (20.54%, SR 2.38). The other Claude models were mid-pack in stocks (2.45% to 3.93%). [Source](https://arxiv.org/html/2511.03628)
- StockBench: Claude-4-Sonnet ranked 7th. [Source](https://arxiv.org/html/2510.02209)
- AI-Trader: Claude-3.7-Sonnet was 3rd in US stocks. [Source](https://arxiv.org/html/2512.10971)
- CLQT: claude-haiku in structured mode had the highest valid Sharpe (3.21). [Source](https://arxiv.org/html/2606.29771)

**Gemini**
- AI-Trader: Gemini-2.5-Flash was last in all 3 markets. [Source](https://arxiv.org/html/2512.10971)
- LiveTradeBench: Gemini-2.5-Pro and Flash had stock CR 1.95% and 2.10%, near the bottom. [Source](https://arxiv.org/html/2511.03628)
- Agent Market Arena: Gemini-2.0-flash results were mixed, worst in InvestorAgent and best on TSLA in TradeAgent. [Source](https://arxiv.org/html/2510.11695)
- TraderBench: Gemini-3-Pro was #1 overall (64.3). [Source](https://arxiv.org/html/2603.00285)

**Grok**
- LiveTradeBench: Grok-4 had stock CR 4.30% and Polymarket CR 7.38%. It was one of two models consistent across markets and was described as "conservative". [Source](https://arxiv.org/html/2511.03628)
- TraderBench: Grok 4.1 Fast was #2 (63.7). [Source](https://arxiv.org/html/2603.00285)

**Llama**
- LiveTradeBench: Llama4-Scout and Maverick had stock CR 4.65% and 4.46%, in the top 6. [Source](https://arxiv.org/html/2511.03628)
- InvestorBench: Llama-3.1-70B was mid-pack in stocks and negative on ETH (-11.888). [Source](https://arxiv.org/html/2412.18174)
- To Trade or Not to Trade: Llama 3.3 posted top Sharpe on AAPL and NVDA but often failed to finish the trading period. [Source](https://arxiv.org/html/2507.08584v1)

**Nemotron**
- None of the papers reviewed tested Nemotron.

### Inferences
- [C] Families with a top-3 trading placement in two or more independent papers:
  - Qwen: StockBench and InvestorBench.
  - DeepSeek: AI-Trader and CLQT.
  - GPT: LiveTradeBench stocks and TraderBench.
  - Grok: LiveTradeBench Polymarket and TraderBench.
- Families that also land in the bottom half elsewhere: Qwen (AI-Trader), DeepSeek (StockBench, LiveTradeBench) and GPT (StockBench, AI-Trader). So no family is reliably top.
- Grok is the only family with no bottom-half result in the papers here, but it appears in only two of them.
- Gemini and Flash-tier models were repeatedly bottom-ranked in live return tests (AI-Trader, LiveTradeBench). This is the most consistent negative pattern.
- Market-specific flips are large: Kimi-K2 was #1 in DJIA stocks and had the worst Sharpe on Polymarket; GPT-o3 was #2 in stocks and near the bottom on Polymarket. Family effects are smaller than market, period and agent-design effects. AMA states this directly for backbones vs agents.

### Gaps
- Nearly all windows are 2 weeks to 4 months with a single run per model. Few papers report repeated seeds or confidence intervals, except The Price of Thought and CLQT. So family rankings are not statistically established.
- I found no peer-reviewed analysis of the Nof1 Alpha Arena crypto contest (Season 1, Oct 18 to Nov 3 2025; Qwen3-Max reportedly 1st). It was excluded as not an official paper.
- PolyBench ([arXiv 2604.14199](https://arxiv.org/abs/2604.14199), prediction markets, search snippet only) reportedly found only 2 of 7 models profitable (MiMo-V2-Flash 17.6% and Gemini-3-Flash 6.2%), with open MiMo beating proprietary models. I did not verify the full text, and it is out of stocks/crypto scope.
- DeepFund ([arXiv 2503.18313](https://arxiv.org/html/2503.18313)): the HTML version I read had no model results.
