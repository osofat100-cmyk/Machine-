# LLM Trading-Agent Benchmarks on Stock Markets (2024 to Nov 2026): Per-Model Results vs Buy-and-Hold

Conventions used in these notes
- **[T]** = number read from the paper's results table (pulled from the arXiv HTML by a fetch tool and transcribed; StockBench was fetched twice, v1 and v2, and matched). **[S]** = number taken from the paper's text, abstract or a summary, not from a table. **[C]** = number I computed from [T] values (for example a count of models beating the baseline).
- Labels: **O** = open-weight, **C** = closed/API-only, **?** = not sure. **Th** = reasoning/thinking model or mode, **NT** = non-thinking, **Hy** = hybrid model with the mode not stated in the paper. **Papers almost never state these labels.** Unless a row says otherwise, the label is my own classification from general model knowledge. For model names I can't verify (for example GPT-5.6 Luna, Claude Haiku 5.5, GPT-6 Astra), the label is "?".
- CR = cumulative return, SR = Sharpe, SoR = Sortino, MDD = max drawdown, B&H = buy-and-hold.
- Scope is stocks only. Crypto, prediction-market and options results are noted briefly where a paper also covers stocks.

---

## Q1. Benchmark inventory: authors, market, exact test period, live vs backtest, runs, decision frequency

### Takeaway
I found 17 stock-relevant LLM trading benchmarks or evaluations dated Dec 2024 to Nov 2026. Their test windows run from 2 days to 20 years. Almost all report one run, or a median or mean over 3 to 5 runs, with no variance. Live windows are short, from 24 trading days to 217 days. Only three papers run formal significance tests on returns or alpha: FINSABER, the "Beta, Not Alpha" paper, and LiveOption.

### Cited Findings

**Master inventory table**

| # | Benchmark (arXiv) | Authors / affiliation | Market / universe | Test period (exact) | Live or backtest | Runs per model | Decision freq. | Baseline |
|---|---|---|---|---|---|---|---|---|
| 1 | InvestorBench (2412.18174; ACL 2025) | Li, Cao, Yu, … Xie: Stevens Inst. of Tech., Columbia, Harvard, The Fin AI | US single stocks: MSFT, JNJ, UVV, HON, TSLA, AAPL, NIO (also BTC/ETH, ETF) | Warm-up 2020-07-01 to 09-30. **Test 2020-10-01 to 2021-05-06** | Backtest | 5 epochs, median reported. Temp 0.6 | Daily | B&H per stock — [InvestorBench](https://arxiv.org/html/2412.18174v1) |
| 2 | FinCon (2407.06567; NeurIPS 2024) | Stevens, Harvard, The Fin AI | 8 US single stocks + 2 three-stock portfolios | Train 2022-01-03 to 10-04. **Test 2022-10-05 to 2023-06-10** | Backtest | Median of 5 epochs. Wilcoxon test | Daily | B&H, FinMem, FinAgent, DRL — [FinCon](https://arxiv.org/html/2407.06567) |
| 3 | FINSABER (2505.07078 v5, Feb 2026; KDD '26) | W. W. Li, H. Kim, M. Cucuringu, T. Ma: Edinburgh, Sungkyunkwan, UCLA/Oxford | US equities, survivorship-free S&P 500 history. "Selected-4" (TSLA, NFLX, AMZN, MSFT) + composites of 63 to 91 symbols | **2004-01-01 to 2024-01-01**. Original-claim window 2022-10-06 to 2023-04-10 | Backtest (rolling) | Not stated in the text I read | Daily timing | B&H — [FINSABER v5](https://arxiv.org/html/2505.07078v5) |
| 4 | TradingAgents (2412.20138) | Xiao, Sun, Luo, Wang (Tauric Research named in comments) | US stocks | Not obtained | Backtest | Not obtained | Daily | B&H and rules — [TradingAgents abs](https://arxiv.org/abs/2412.20138) |
| 5 | DeepFund, "Time Travel is Cheating" (2505.11065; NeurIPS 2025 D&B) | C. Li, … N. Tang, Y. Luo: HKUST (Guangzhou), Paradoox AI | US: AAPL, AXP, BAC, KO, CVX (Berkshire top 5) | **Live 2025-03-17 to 2025-04-17 (24 trading days)**. Extension through Q2 2025 (to 2025-06-29) | Live | Not reported | Daily | S&P 500 and per-model "CRbnh" — [DeepFund](https://arxiv.org/html/2505.11065v2) |
| 6 | StockBench (2510.02209 v1 Oct 2025, v2 2 Mar 2026) | Y. Chen, Z. Yao, … L. Hou, J. Li: Tsinghua, BUPT | US: top-20 DJIA stocks by weight | **2025-03-03 to 2025-06-30 (82 trading days)** | Backtest on post-cutoff data ("contamination-free") | **3 seeds, mean reported, no variance in main table** | Daily at open. $100k start | Equal-weight B&H — [StockBench v2](https://arxiv.org/html/2510.02209v2) |
| 7 | Agent Market Arena, "When Agents Trade" (2510.11695 v2) | L. Qian, … J. Huang, S. Ananiadou: The Fin AI, Stevens, Columbia, Harvard, U. Florida, U. Montréal, Manchester, et al. | TSLA, BMRN (also BTC, ETH) | Warm-up 2025-05-01 to 07-31. **Live 2025-08-01 to 2025-09-30** | Live | 1 per agent×backbone | Daily BUY/SELL/HOLD | B&H per asset — [AMA](https://arxiv.org/html/2510.11695) |
| 8 | Profit Mirage / FinLake-Bench (2510.07920) | X. Li, Y. Zeng, X. Xing, J. Xu, X. Xu: SCUT, ByteDance, Pazhou Lab | AAPL, NVDA, TSLA, BYD (002594.SZ), Tencent (0700.HK), BTC | Pre-cutoff Q2–Q3 2021 vs post-cutoff Q3–Q4 2024. **Main eval 2024-07-01 to 2025-06-30** | Backtest | Not reported | Daily | Market B&H — [Profit Mirage](https://arxiv.org/html/2510.07920) |
| 9 | LiveTradeBench (2511.03628) | H. Yu, F. Li, J. You: UIUC | US: 15 stocks/ETFs (AAPL, MSFT, NVDA, META, JPM, V, XOM, CAT, TSLA, PG, KO, AMZN, WMT, JNJ, UNH) + cash (also Polymarket) | **Live 2025-08-18 to 2025-10-24 (50 trading days)** | Live | Single live run (no repeat count stated) | Daily (implied) | **None reported** — [LiveTradeBench](https://arxiv.org/html/2511.03628) |
| 10 | AI-Trader (2512.10971) | T. Fan, Y. Yang, Y. Jiang, Y. Zhang, Y. Chen, C. Huang: HKU | Nasdaq-100 (US) and SSE-50 (A-share) (also 10 crypto) | **US and A-share 2025-10-01 to 2025-11-07**. Crypto 2025-11-01 to 11-14 | Live | Not stated | **US hourly, A-share daily** | QQQ, SSE-50 index — [AI-Trader](https://arxiv.org/html/2512.10971) |
| 11 | TraderBench (2603.00285; ICLR 2026 listing) | X. Yuan, H. Xu, S. Xu, C. Zou, J. Xiong | Knowledge, analysis, **options** and **crypto** trading (no cash-equity trading section) | Historical with adversarial transforms | Backtest | n/a | n/a | n/a — [TraderBench](https://arxiv.org/html/2603.00285v1) |
| 12 | KTD-Fin, "From Knowing to Doing" (2605.28359) | T. Zhu, … Z. Bai: Tsinghua, StepFun, SJTU, Adelaide, FinStep | China A-share **CSI300** constituents, price-only inputs. Qlib simulator with T+1 and price limits | **Long window 2024-01-01 to 2026-04-10 (548 trading days)**. 10 short windows from 2024-04-01. W10 = 2026-02-02 to 04-10 | Backtest | Multiple seeds, median per cell (count unclear; limitations section says 3 for the long window) | Daily | CSI300 B&H +36.92% and 18 Qlib ML models — [KTD-Fin](https://arxiv.org/html/2605.28359v1) |
| 13 | FinMMEval 2026 Task 3 (shared task on AMA). Results from the Fin-Analyst system paper (2607.12233) | Organizers: Xie, Qian, … Nakov. Participant: Rashid, Hong, Ding, Hossain (U. North Texas) | TSLA (also BTC) | Offline 2025-08-01 to 2026-05-10. **Live from 2026-05-11. TSLA 33 trading days to 2026-06-26** | Live | 1 | Daily | B&H — [Fin-Analyst](https://arxiv.org/html/2607.12233) |
| 14 | LiveOption (2609.33470) | H. Luo, … C. Liu: CityU HK, CUHK-SZ, SUFE | **Options**: SPY 0DTE, overlays on 5 large caps (AMD, GOOG, NVDA, TSLA, +1), earnings bets on 24 names | Full year **2025**, replayed | Replay (called "live") | ~90–102 episodes per task per model | Episode | Matched B&H (overlay) — [LiveOption](https://arxiv.org/html/2609.33470) |
| 15 | LiveMACE / LiveMACEBench (2610.09872) | J. Zhao, … Q. Zhang, X. Huang: NUS, Fudan, U. Sydney | 17 US stocks (Alpaca SIP) **plus** 6 crypto (Hyperliquid) | **Live paper trading 2026-04-13 to 2026-05-13 (~30 days)** | Live | 1 trajectory per model × config | Every 4 hours | **None** — [LiveMACE](https://arxiv.org/html/2610.09872) |
| 16 | Quant-Arena (2610.30113) | H. Qian, … C. Xiao: Navers Lab, Einsia.AI | A-share, 3,042 stocks. The LLM **writes strategy code** rather than trading directly | Feedback 2022–2023. **Sealed OOS 2024** | Backtest | 38 iterative + 38 one-shot configs across effort levels | Strategy-level | Equal-weight market 2024 ARR 17.1% — [Quant-Arena](https://arxiv.org/html/2610.30113) |
| 17 | FIDES-Live (2610.36476) | A. Tian, A. Ding, S. Wu, A. Chan: DGrid AI | Mainly crypto. **Equity pilot**: SPY, QQQ, IWM, EFA, TLT, GLD, XLF, XLE, then AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA | Equity pilot **2026-09-28 to 09-29**. Crypto 2026-09-30 to 10-07 | Live paper | 2 equity runs (5 and 26 rounds) | 5 or 15 min | Cash only — [FIDES-Live](https://arxiv.org/html/2610.36476) |
| 18 | "LLM Trading Agents Earn Beta, Not Alpha" / rta-bench-1 (2611.19530, 14 Nov 2026) | Jackson Wang (affiliation not listed) | 56 large US stocks in 11 sectors, plus ETFs and T-bills | **2026 rally: 2026-01-02 to 2026-11-11 (217 days)**. 2022 bear (251 days). 2020 crash and rebound (253 days). Exact 2020/2022 dates not stated | Look-ahead-free backtest: each headline is released only after its publication minute | **91 runs total**. Seeds 0–2 for GPT-5.6 Luna, Gemini 3.5 Flash and Llama 3.2 3B. Seed 0 for the Claude models | Every 5th close, fill at next open | SPY, equal weight, 5 rule strategies, same-day same-sector random picks — [Beta Not Alpha](https://arxiv.org/html/2611.19530) |

Adjacent papers (not stock benchmarks with per-model returns)
- "What LLM Trading Agents Actually Do in Production" (2609.05663, DXRG) is **crypto only**: memecoins on Base and Hyperliquid perps, Feb–Aug 2026. Its finding is "neither fleet shows a directional edge". The model league showed no significant separation (Holm min p = 0.46) — [2609.05663](https://arxiv.org/html/2609.05663).
- Critical review "Evaluating LLM Trading Agents" (2611.24133, RMIT, 18 Nov 2026) coded 18 papers. **No paper fully met the timing, model-memory, universe, cost or selection criteria.** 8 of 10 real-price papers had a longest continuous evaluation under 365 days. It cites a TradingAgents reproduction with "a portfolio Sharpe ratio of 0.43 before costs but only 0.22 after costs" [S] — [Critical review](https://arxiv.org/html/2611.24133).
- Agentic Quantitative Trading survey (2608.31041) lists 15 benchmarks, including AlphaEval 2508.13174 (A-share and US, strategy construction) and StockAgent 2407.18957 (simulated). It reports no numeric B&H comparisons — [Survey](https://arxiv.org/html/2608.31041v1).
- **FINCOSMOS: not found.** A search for the name returned no matching paper.

### Inferences
- A "benchmark" here covers four quite different designs. (a) Direct daily trading of a few names: InvestorBench, AMA, DeepFund, StockBench, LiveTradeBench, AI-Trader. (b) Cross-sectional portfolio with factor attribution: KTD-Fin, "Beta Not Alpha". (c) LLM writing strategy code: Quant-Arena. (d) Options: LiveOption, TraderBench. Only (a) and (b) are comparable "LLM trades stocks vs B&H" evidence.
- InvestorBench (2020–21), FinCon (2022–23) and FINSABER (2004–24) test periods fall inside the backbones' training data. Profit Mirage shows that post-cutoff returns decay by 50–72%, so pre-2024 results probably overstate skill.

### Gaps
- TradingAgents: test period, tickers and numeric table not obtained (only the abstract was fetched).
- FinCon B&H rows and FinMem standalone results (2023) not extracted.
- "Beta Not Alpha": exact 2020 and 2022 start and end dates not stated in the extracted text.
- DeepFund: definition of the "CRbnh" column not extracted.
- LiveMACE: whether "Final Return" is a combined stock+crypto portfolio or stock-only is unclear.

---

## Q2. Per-model results tables (return, Sharpe/Sortino, MDD) vs the same-period baseline

### Takeaway
On every benchmark with a baseline, the best LLM's margin over buy-and-hold is small and fragile: about +2 percentage points over 4 months, or a multi-point lead in a single 5-week or 2-month live window. A large share of models trail B&H in rising markets. LLM agents systematically run **beta below 1**. They beat B&H in falling or flat windows (BMRN, DeepFund Mar–Apr 2025, the 2022 bear) and lose in strong rallies (TSLA Aug–Sep 2025, the 2026 rally, the A-share Oct 2025 rally, A-share 2024).

### Cited Findings

#### 2.1 StockBench — DJIA-20, 2025-03-03 to 06-30, mean of 3 seeds [T] — [StockBench v2](https://arxiv.org/html/2510.02209v2)
| Rank | Model | Label | Final return % | MDD % | Sortino | Beats B&H 0.4%? [C] |
|---|---|---|---|---|---|---|
| 1 | Kimi-K2 | O, NT | 1.9 | −11.8 | 0.0420 | Yes |
| 2 | Qwen3-235B-Ins | O, NT (paper: Instruct) | 2.4 | −11.2 | 0.0299 | Yes |
| 3 | GLM-4.5 | O, Hy | 2.3 | −13.7 | 0.0295 | Yes |
| 4 | Qwen3-235B-Think | O, Th (paper label) | 2.5 | −14.9 | 0.0309 | Yes |
| 5 | OpenAI-O3 | C, Th | 1.9 | −13.2 | 0.0267 | Yes |
| 6 | Qwen3-30B-Think | O, Th (paper label) | 2.1 | −13.5 | 0.0255 | Yes |
| 7 | Claude-4-Sonnet | C, Hy | 2.2 | −14.2 | 0.0245 | Yes |
| 8 | DeepSeek-V3.1 | O, Hy | 1.1 | −14.1 | 0.0210 | Yes |
| 9 | GPT-5 | C, Th | 0.3 | −13.1 | 0.0132 | No |
| 10 | Qwen3-Coder | O, NT | 0.2 | −13.9 | 0.0137 | No |
| 11 | DeepSeek-V3 | O, NT | 0.2 | −14.1 | 0.0144 | No |
| 12 | **Passive B&H (equal weight)** | — | **0.4** | **−15.2** | **0.0155** | — |
| 13 | GPT-OSS-120B | O, Th | −0.9 | −14.0 | 0.0156 | No |
| 14 | GPT-OSS-20B | O, Th | −2.8 | −14.4 | −0.0069 | No |
- [C] 8 of 13 LLMs beat B&H on return. **All 13 had a smaller MDD than B&H.** The best excess return was +2.1 pp (Qwen3-235B-Think).
- [S] Sub-period split: all agents **underperform B&H in the downturn (Jan–Apr 2025) and outperform in the upturn (May–Aug 2025)**. GPT-OSS-120B moves from last to first between the two. Values appear only in a figure.

#### 2.2 DeepFund — live, 5 US stocks, 2025-03-17 to 04-17 (24 trading days) [T] — [DeepFund](https://arxiv.org/html/2505.11065v2)
| Model | Label | CR % | CRbnh % | SR | MDD % | WR % | β | α | Beats S&P (−6.91)? [C] | Beats own CRbnh? [C] |
|---|---|---|---|---|---|---|---|---|---|---|
| Grok 3 mini Beta | C, Th | **+1.1** | −3.09 | 0.51 | 5.5 | 61 | 0.42 | 0.2 | Yes | Yes |
| Gemini 2.5 Flash | C, Hy | −1.9 | −1.58 | −1.37 | 6.4 | 61 | 0.35 | 0.0 | Yes | No |
| Claude 3.7 Sonnet | C, Hy | −3.7 | −2.94 | −1.45 | 10.1 | 70 | 0.64 | 0.0 | Yes | No |
| Llama 4 Scout | O, NT | −4.3 | −3.62 | −2.42 | 8.9 | 61 | 0.36 | −0.1 | Yes | No |
| DeepSeek-V3 | O, NT | −5.7 | −5.6 | −1.39 | 14.5 | 57 | 0.94 | 0.0 | Yes | No |
| GPT-4.1 | C, NT | −5.9 | −4.41 | −1.87 | 12.8 | 52 | 0.77 | 0.0 | Yes | No |
| Qwen2.5-Max | C, NT | −6.7 | −4.86 | −3.12 | 10.7 | 65 | 0.48 | −0.2 | Yes | No |
| GLM-4-Air | ?, NT | −7.5 | −3.90 | −2.31 | 13.2 | 57 | 0.78 | −0.1 | No | No |
| Doubao-1.5-pro | C, NT | −8.1 | −5.37 | −2.35 | 13.6 | 65 | 0.84 | −0.1 | No | No |
| **S&P 500** | — | **−6.91** | NA | 0.3 | 13.7 | NA | 1.00 | 0.0 | — | — |
- Q2 2025 extension, weekly average total asset value, final row 2025-06-29 ($100k start) [T]: Grok 3 106,262. Llama 4 102,859. DeepSeek V3 102,851. GPT-4.1 101,443. Claude 3.7 101,234. Doubao 1.5 100,866. Gemini 2.5 99,763. GLM 4 97,671. Qwen Max 96,383.
- [C] 7 of 9 beat the S&P 500 in a falling month, through low beta (0.35–0.94). Only 1 of 9 beat its own "CRbnh" column.

#### 2.3 Agent Market Arena — live, 2025-08-01 to 09-30, stocks [T] — [AMA](https://arxiv.org/html/2510.11695)
| Agent | Backbone (label) | TSLA CR % | TSLA SR | TSLA MDD % | BMRN CR % | BMRN SR | BMRN MDD % |
|---|---|---|---|---|---|---|---|
| **Buy & Hold** | — | **46.88** | **6.00** | 6.34 | **−6.89** | −1.37 | 15.03 |
| InvestorAgent | GPT-4o (C, NT) | 33.01 | 5.37 | 6.34 | −5.33 | −0.98 | 14.36 |
| InvestorAgent | GPT-4.1 (C, NT) | 40.83 | **6.47** | 4.38 | 3.79 | 0.98 | 7.35 |
| InvestorAgent | Gemini-2.0-flash (C, NT) | 10.57 | 1.60 | 8.50 | −13.88 | −2.92 | 19.57 |
| InvestorAgent | Claude-3.5-haiku (C, NT) | 11.55 | 2.30 | 8.35 | −8.35 | −1.97 | 15.24 |
| InvestorAgent | Claude-sonnet-4 (C, Hy) | 28.91 | 3.76 | 8.41 | −6.89 | −1.36 | 15.12 |
| InvestorAgent | Vote | 29.13 | 3.83 | 8.37 | −5.47 | −1.06 | 13.64 |
| TradeAgent | GPT-4o | −4.25 | −3.38 | 5.73 | −1.95 | −1.11 | 7.81 |
| TradeAgent | GPT-4.1 | −38.72 | −5.38 | 38.72 | 4.84 | 1.15 | 6.20 |
| TradeAgent | Gemini-2.0-flash | 21.91 | 3.82 | 6.41 | −0.31 | 0.04 | 9.46 |
| TradeAgent | Claude-3.5-haiku | −6.62 | −1.64 | 11.05 | −9.45 | 3.01 | 13.85 |
| TradeAgent | Claude-sonnet-4 | −5.43 | −0.91 | 12.89 | 14.57 | 3.76 | 3.81 |
| TradeAgent | Vote | −0.36 | 0.02 | 9.03 | 1.22 | 0.48 | 6.70 |
| HedgeFundAgent | all 5 backbones + Vote (identical rows) | −29.15 | −4.39 | 29.15 | 23.70 | 4.83 | 5.59 |
| DeepFundAgent | GPT-4o | 13.89 | 1.98 | 7.61 | 3.72 | 0.92 | 8.92 |
| DeepFundAgent | GPT-4.1 | −5.52 | −0.69 | 19.22 | 4.86 | 1.64 | 3.49 |
| DeepFundAgent | Gemini-2.0-flash | −8.04 | −3.88 | 8.04 | 3.59 | 0.89 | 6.57 |
| DeepFundAgent | Claude-3.5-haiku | −15.43 | −2.04 | 28.48 | −1.12 | −0.10 | 12.25 |
| DeepFundAgent | Claude-sonnet-4 | −6.96 | −0.90 | 12.99 | 5.48 | 1.31 | 8.52 |
| DeepFundAgent | Vote | 8.61 | 1.39 | 10.14 | 9.45 | 1.96 | 6.42 |
- [C] **TSLA (+46.9% rally): 0 of 24 agent×backbone combinations beat B&H on CR.** BMRN (−6.9%): 20 of 24 beat B&H.
- Data-quality flag: all six HedgeFundAgent rows are identical, which suggests a pipeline issue. The paper attributes it to robustness [S].
- Crypto, briefly: ETH B&H 18.56% vs HedgeFundAgent 39.66%. BTC B&H 0.66% vs TradeAgent-Gemini 5.02% [T].
- Survey summary: in AMA, agent architecture explains more variation than the LLM backbone [S] — [Survey](https://arxiv.org/html/2608.31041v1).

#### 2.4 LiveTradeBench — live, 15 US stocks/ETFs, 2025-08-18 to 10-24 [T] — [LiveTradeBench](https://arxiv.org/html/2511.03628)
| Model | Label | CR % | SR | MDD % | Win rate % |
|---|---|---|---|---|---|
| GPT-4.1 | C, NT | **6.25** | **2.64** | 1.92 | 65.31 |
| GPT-o3 | C, Th | 6.04 | 2.57 | 2.27 | 61.22 |
| GPT-5 | C, Th | 5.31 | 2.19 | 2.53 | 65.31 |
| Qwen2.5-72B-Instruct | O, NT | 5.15 | 2.18 | 2.22 | 65.31 |
| Llama4-Scout | O, NT | 4.65 | 1.99 | 2.62 | 59.18 |
| Llama4-Maverick | O, NT | 4.46 | 1.65 | 2.45 | 53.06 |
| Grok-4 | C, Th | 4.30 | 1.75 | 1.92 | 59.18 |
| Claude-Opus-4 | C, Hy | 3.93 | 1.72 | 2.11 | 63.27 |
| Claude-Opus-4.1 | C, Hy | 3.73 | 1.51 | 1.84 | 63.27 |
| Claude-Sonnet-3.7 | C, Hy | 3.63 | 1.45 | 2.65 | 59.18 |
| GPT-4o | C, NT | 3.55 | 1.39 | 2.43 | 55.10 |
| Qwen3-235B-A22B-Instruct | O, NT | 3.52 | 1.32 | 2.04 | 61.22 |
| Grok-3 | C, NT | 3.22 | 1.26 | 2.13 | 65.31 |
| Kimi-K2-Instruct | O, NT | 3.07 | 1.15 | 3.32 | 53.06 |
| Llama3.3-70B-Instruct-Turbo | O, NT | 2.72 | 0.88 | 3.54 | 61.22 |
| DeepSeek-V3.1 | O, Hy | 2.46 | 0.86 | 2.45 | 59.18 |
| Claude-Sonnet-4 | C, Hy | 2.45 | 0.72 | 3.23 | 53.06 |
| Gemini-2.5-Flash | C, Hy | 2.10 | 0.72 | 3.10 | 55.10 |
| DeepSeek-R1 | O, Th | 2.10 | 0.78 | 2.20 | 61.22 |
| Gemini-2.5-Pro | C, Th | 1.95 | 0.61 | 2.85 | 50.00 |
| Qwen3-235B-A22B-Thinking | O, Th | 1.78 | 0.60 | 2.32 | 59.18 |
- **No buy-and-hold, SPY or equal-weight baseline is reported** (checked both halves of the HTML). All 21 models had a positive return (1.78–6.25%) [C]. The paper also says the stock and Polymarket Sharpe ratios are nearly uncorrelated [S] — [Survey](https://arxiv.org/html/2608.31041v1).

#### 2.5 AI-Trader — live, 2025-10-01 to 11-07 [T] — [AI-Trader](https://arxiv.org/html/2512.10971)
| Model | Label | US CR % (hourly) | US Sortino | US MDD % | A-share CR % (daily) | A-share Sortino | A-share MDD % |
|---|---|---|---|---|---|---|---|
| MiniMax-M2 | O, Th | **9.56** | **4.42** | −4.92 | **1.31** | 1.00 | −2.15 |
| DeepSeek-v3.1 | O, Hy | 8.39 | 3.73 | −8.58 | −1.23 | −0.18 | −5.88 |
| Claude-3.7-Sonnet | C, Hy | 3.11 | 1.13 | −8.13 | 0.84 | 0.29 | −4.49 |
| GPT-5 | C, Th | 1.56 | 0.70 | −10.55 | −3.53 | −1.54 | −3.78 |
| Qwen3-Max | C, NT | 0.39 | 0.32 | −9.39 | −3.86 | −1.40 | −5.49 |
| Gemini-2.5-Flash | C, Hy | −0.06 | 0.09 | −7.73 | −1.53 | −0.29 | −4.81 |
| **Baseline** | — | **QQQ 1.87** (Sortino 1.51, MDD −3.94) | | | **SSE-50 1.65** (Sortino 2.19, MDD −2.01) | | |
- [C] US: 3 of 6 beat QQQ. **A-share: 0 of 6 beat the SSE-50.** Every agent had a deeper MDD than its index in both markets.
- Crypto, 2025-11-01 to 11-14: CD5 −14.30%. Only DeepSeek-v3.1 (−12.18%) beat it [T].

#### 2.6 KTD-Fin — CSI300 A-share backtest, 2024-01-01 to 2026-04-10, blinded, median over seeds [T] — [KTD-Fin](https://arxiv.org/html/2605.28359v1)
| Model | Label | Total return | Excess vs CSI300 B&H | Sharpe | MDD | Barra selection α (Table 5) | α rank |
|---|---|---|---|---|---|---|---|
| qwen3.6-plus | C?, ? | **+85.29%** | +48.37% | 1.13 | −24.49% | −0.7 | 2 |
| gpt-5.5 | C, ? | +61.26% | +24.34% | 0.98 | −24.63% | −14.9 | 6 |
| doubao-seed-2.0 | C, ? | +61.01% | +24.09% | 1.15 | −15.62% | −4.7 | 3 |
| claude-opus-4-7 | C, ? | +58.80% | +21.88% | 0.98 | −26.69% | **+0.2** | 1 |
| minimax-m2.7 | O?, ? | +56.31% | +19.39% | 0.89 | −29.43% | −7.4 | 4 |
| step-3.5-flash (anchor) | O?, ? | +21.86% | −15.06% | 0.49 | −28.99% | −13.7 | 5 |
| gemini-3.1-pro | C, ? | +8.25% | −28.67% | 0.29 | −49.67% | −38.5 | 7 |
| deepseek-v4-pro | O?, ? | +1.39% | −35.53% | 0.19 | −42.35% | −43.0 | 8 |
| glm-5.1 | O?, ? | −3.55% | −40.47% | 0.10 | −44.88% | −61.9 | 9 |
| kimi-k2.6 | O?, ? | −24.23% | −61.15% | −0.34 | −45.49% | −77.8 | 10 |
| **CSI300 B&H** | — | **+36.92%** | 0 | — | — | — | — |
| SFM (Qlib ML baseline) | — | +86.58% | +49.66% | 2.02 | −7.41% | — | — |
| LightGBM (Qlib) | — | +66.22% | +29.30% | 1.29 | −15.59% | — | — |
- [C] 5 of 10 LLMs beat CSI300 B&H on total return. **9 of 10 have negative Barra selection alpha**, so their excess return came from common-factor and style exposure (+29.6 to +42.5 pp common, +11.8 to +29.2 pp style) [T]. A plain Qlib SFM model beat every LLM with a much higher Sharpe (2.02 vs at most 1.15).

#### 2.7 LiveMACE — live, 17 US stocks + 6 crypto, 2026-04-13 to 05-13, 4-hour decisions [T] — [LiveMACE](https://arxiv.org/html/2610.09872)
| Model | Label | Final return | MDD | Rule-following (HPR / RSS / RAS) |
|---|---|---|---|---|
| DeepSeek-V3.2 | O, Hy | **+5.765%** | 4.270% | 0.877 / 0.847 / 0.623 |
| GPT-5.4 | C, Th | +5.738% | 5.169% | 0.682 / 0.634 / 0.677 |
| Qwen3-Max | C, NT | +4.418% | 5.674% | 0.613 / 0.612 / 0.511 |
| Gemini-3.1-Pro | C, Th | +3.503% | 4.927% | 0.888 / 0.872 / 0.882 |
| Grok-4.20 | C, ? | +3.085% | 5.165% | 0.834 / 0.751 / 0.775 |
- **No B&H baseline and no Sharpe.** The paper says return rankings shifted often over the window, while capability metrics were more stable [S].

#### 2.8 "LLM Trading Agents Earn Beta, Not Alpha" — 56 US large caps, blind runs (Table III) [T] — [2611.19530](https://arxiv.org/html/2611.19530)
| Model | Label | 2026 rally ret % / β / 4-factor α (%/yr) | 2022 bear ret % / β / α | 2020 crash ret % / β / α |
|---|---|---|---|---|
| GPT-5.6 Luna (6 runs per period) | C, ? | +7.8 / 0.35 / +3.5 | −3.7 / 0.29 / −3.0 | +0.9 / 0.30 / −8.4 |
| Gemini 3.5 Flash (4 runs) | C, ? | +6.3 / 0.70 / −1.6 | −8.4 / 0.46 / −8.9 | +13.7 / 0.47 / −9.2 |
| Claude Haiku 4.5 (1 run) | C, Hy | +7.2 / 0.59 / −1.2 | −5.3 / 0.58 / −1.0 | +16.9 / 0.50 / −2.3 |
| Claude Sonnet 4.6 (1 run) | C, Hy | **+8.1** / 0.59 / +1.8 | +0.4 / 0.55 / −0.5 | **+25.4** / 0.34 / +3.6 |
| Claude Haiku 5.5 (1 run) | C, ? | +2.4 / 0.23 / −3.2 | **+1.4** / 0.01 / −0.0 | +7.4 / 0.23 / −2.6 |
| Llama 3.2 3B (3 runs) | O, NT | −0.6 / 0.19 / −8.7 | −1.6 / 0.25 / +2.7 | +10.6 / 0.19 / +7.7 |
| Trend following (rule) | — | +19.0 | −5.9 | +67.4 |
| RSI(2) reversion | — | +4.9 | −8.6 | +6.3 |
| Positive-headlines rule | — | +2.0 | −16.3 | +23.4 |
| **SPY** | — | **+12.1** (DD 8.9) | **−18.6** (DD 24.5) | **+17.2** (DD 33.7) |
| **Equal weight** | — | **+11.4** | **−12.4** | **+40.1** |
- [C] 2026 rally: **0 of 6 models beat SPY or equal weight.** 2022 bear: 6 of 6 beat both. 2020: 1 of 6 beat SPY (Sonnet 4.6) and 0 of 6 beat equal weight. Betas were 0.01–0.70 throughout.
- [S] Seed-only differences averaged 5.2 points of return. Market and style exposure accounted for a median 78% of return. A single cash rule in the prompt cut a GPT agent's stock share by 30.3 points in all 6 pairs.

#### 2.9 Quant-Arena — A-share sealed 2024. The LLM designs a strategy rather than trading [T] — [Quant-Arena](https://arxiv.org/html/2610.30113)
| Model (best iterative config) | Effort | ARR % | Excess vs EW market (pp) | Sharpe | MDD % |
|---|---|---|---|---|---|
| GPT-6 Astra | xhigh | 10.7 | −6.3 | 0.86 | −6.8 |
| GPT-6 Sol | xhigh | 8.6 | −8.4 | 1.89 | −2.8 |
| GPT-5.6 Terra | max | 8.4 | −8.7 | 0.42 | −28.8 |
| Claude Opus 5.5 | medium | 4.4 | −12.7 | 0.29 | −32.7 |
| Gemini 3.8 Flash | medium | −2.9 | −19.9 | 0.06 | −33.8 |
| DeepSeek V4.1 Flash | low | −5.7 | −22.7 | −0.06 | −30.3 |
| GLM-5.3 | max | −7.8 | −24.9 | −0.18 | −27.8 |
| Kimi K3 | low | −8.5 | −25.6 | −0.10 | −36.4 |
| Claude Sonnet 5.5 | max | −12.2 | −29.2 | −0.23 | −36.1 |
| **Equal-weight market** | — | **17.1** | 0 | — | — |
- Internal inconsistency: the abstract says no model beats the market. The fetch tool reported a table row for GPT-6 Sol at medium effort with ARR 18.4% (+1.4 pp), and the text calls it the only config that beats the market [S/T, unverified]. Einsia's own non-LLM "Kepler-1" scored much higher (Sharpe 2.98).

#### 2.10 InvestorBench — single stocks, 2020-10-01 to 2021-05-06, median of 5 [T] — [InvestorBench](https://arxiv.org/html/2412.18174v1)
Average across the 7 stocks (paper's "Average" column):
| Model | Label (paper: proprietary/open) | Avg CR % | Avg SR | Avg MDD % | Beats B&H avg 34.10? [C] |
|---|---|---|---|---|---|
| Qwen2.5-72B | O, NT | **46.15** | **1.276** | 19.52 | Yes |
| GPT-4 | C, NT | 43.70 | 0.972 | 27.34 | Yes |
| GPT-4o | C, NT | 39.03 | 1.041 | 21.23 | Yes |
| Llama-3.1-70B | O, NT | 38.95 | 0.864 | 30.74 | Yes |
| Yi-1.5-34B | O, NT | 37.97 | 0.831 | 34.32 | Yes |
| Qwen2.5-7B | O, NT | 29.52 | 0.722 | 34.35 | No |
| DeepSeek-V2-Lite | O, NT | 28.75 | 0.813 | 40.44 | No |
| DeepSeek-67B | O, NT | 26.94 | 0.717 | 30.03 | No |
| Llama-3.1-8B | O, NT | 25.46 | 0.567 | 37.22 | No |
| GPT-o1-preview | C, Th | 25.06 | 0.592 | 34.64 | No |
| Yi-1.5-9B | O, NT | 22.91 | 0.478 | 36.95 | No |
| Qwen2.5-32B | O, NT | 20.88 | 0.823 | 22.54 | No |
| Palmyra-Fin-70B | O (finance-tuned) | −0.45 | 0.031 | 36.56 | No |
| **Buy & Hold** | — | **34.10** | 0.732 | 34.95 | — |
- The paper's text says proprietary models lead. Its own average column shows open Qwen2.5-72B on top [T vs S conflict]. The reasoning model o1-preview ranked 10th of 13 on average CR.

#### 2.11 FINSABER — 2004–2024, Sharpe / annual return % / MDD % [T] — [FINSABER v5](https://arxiv.org/html/2505.07078v5)
| Universe | Buy & Hold | FinMem (GPT-4o-mini / GPT-4o) | FinAgent |
|---|---|---|---|
| TSLA | 0.630 / 37.77 / −50.84 | 0.641 / 42.15 / −34.23 | 0.206 / 38.59 / −36.93 |
| NFLX | 0.622 / 23.92 / −48.12 | 0.293 / 12.57 / −27.72 | −0.419 / 22.54 / −20.47 |
| AMZN | 0.551 / 16.00 / −36.84 | 0.188 / 5.70 / −28.30 | 0.364 / 12.70 / −25.52 |
| MSFT | 0.461 / 11.24 / −25.46 | 0.203 / 4.57 / −19.27 | 0.285 / 11.12 / −18.60 |
| Random Five (91 symbols) | 0.315 / 6.69 / −35.13 | −0.253 / −0.09 / −24.24 | 0.094 / 4.48 / −28.06 |
| Momentum (84) | 0.384 / 9.92 / −32.60 | 0.025 / 3.65 / −23.34 | 0.104 / **13.95** / −20.68 |
| Volatility effect (63) | 0.703 / 7.90 / −14.15 | −0.228 / 4.06 / −10.86 | 0.241 / 4.95 / −10.27 |
| FinCon selection (80) | 0.389 / 6.94 / −30.94 | −0.292 / −1.69 / −20.81 | −0.076 / 5.17 / −15.56 |
- Regime Sharpe [S]: B&H 0.61 bull / 0.48 sideways / −0.28 bear. FinAgent 0.12 bull / −0.38 bear. FinMem −0.19 bull / −0.97 bear. In the paper's words, LLM strategies are "overly conservative in bull markets … overly aggressive in bear markets" [S] — [FINSABER v1](https://arxiv.org/html/2505.07078v1).

#### 2.12 Profit Mirage — post-cutoff 2024-07-01 to 2025-06-30, GPT-4o agents [T, abridged] — [Profit Mirage](https://arxiv.org/html/2510.07920)
| Asset | Market B&H TR / SR | TradingAgents TR / SR | FactFin (authors' method) TR / SR |
|---|---|---|---|
| AAPL | −3.36% / 0.05 | 12.89% / 0.55 | 36.70% / 1.22 |
| NVDA | 27.81% / 0.72 | 59.28% / 1.17 | 71.34% / 1.29 |
| TSLA | 57.88% / 0.98 | 106.01% / 1.47 | 165.01% / 1.83 |
| BYD | 32.43% / 0.96 | 43.33% / 1.26 | 84.24% / 2.09 |
| Tencent | 36.82% / 1.12 | 42.77% / 1.38 | 81.37% / 2.31 |
- [S] From pre-cutoff (Q2–Q3 2021) to post-cutoff (Q3–Q4 2024), with similar market returns (+13.79% vs +13.35%), **total return decayed 50.18% (TradingAgents) to 71.85% (FinMem)** and **Sharpe decayed 51.48% (QuantAgent) to 62.23% (FinCON)**. No significance tests. The authors are promoting their own method.

#### 2.13 Other stock-relevant results
- **FinCon** (GPT-4-Turbo; test 2022-10-05 to 2023-06-10), CR % / SR [S, summary]: TSLA 82.87 / 1.97, MSFT 31.63 / 1.54, AMZN 24.85 / 0.90, NIO 17.46 / 0.34, COIN 57.05 / 0.83, Portfolio 1 113.84 / 3.27 — [FinCon](https://arxiv.org/html/2407.06567). B&H rows not extracted.
- **FinMMEval 2026 Task 3** (AMA live, TSLA 2026-05-11 to 06-26): the winner Fin-Analyst, a hybrid of LLM specialists and rules, returned **+13.51% vs TSLA B&H −14.7%** (+28.33 pp, SR 4.10, 33 days). Its own offline backtest (2025-08-01 to 2026-05-10) **lost to B&H**: +25.6% vs +37.9%, below a random policy at +41.7% [T] — [Fin-Analyst](https://arxiv.org/html/2607.12233). Its gain came mostly from short days (+15.17 pp) [T].
- **LiveOption** (2025, options): hedging overlays had **negative ΔReturn vs matched B&H for all 8 models** (−3.05 to −13.65 pp). Covered calls were positive only for DeepSeek-V4-Flash (+0.34 pp). The information ratio was negative in all 16 model×mandate cells [T/S] — [LiveOption](https://arxiv.org/html/2609.33470).
- **FIDES-Live equity pilot** (2026-09-28/29): aggregate figures only (297/309 valid decisions). No per-model returns [S] — [FIDES-Live](https://arxiv.org/html/2610.36476).
- **FinBen**: GPT-4 trading summary at 28.19% CR and 1.51 Sharpe (95% CI), no baseline in the quoted text [S, quoted in review] — [Critical review](https://arxiv.org/html/2611.24133).

### Inferences
- **Low beta explains most "wins".** Wherever beta or exposure is measured (DeepFund β 0.35–0.94; "Beta Not Alpha" β 0.01–0.70; KTD-Fin Barra attribution), LLM agents hold less market exposure than B&H. That makes them look good in down windows (BMRN, Mar–Apr 2025, 2022) and bad in rallies (TSLA Aug–Sep 2025, 2026, A-share Oct 2025, A-share 2024). A "win vs B&H" is mostly a statement about the market regime of the test window.
- **Thinking vs non-thinking, same family, same window.** Qwen3-235B Think vs Instruct: StockBench 2.5% vs 2.4% (Instruct ranked higher), LiveTradeBench 1.78% vs 3.52%. DeepSeek-R1 2.10% vs V3.1 2.46% (LTB). o3 6.04% vs GPT-4.1 6.25% (LTB). o1-preview ranked 10th of 13 in InvestorBench. TraderBench reports extended thinking improves tool-use planning "but has no measurable effect on trading" [S] — [TraderBench](https://arxiv.org/pdf/2603.00285). Reasoning shows no consistent advantage in any source.
- **Open vs closed is not consistent.** Open-weight models top StockBench (top 3), AI-Trader US (MiniMax-M2, DeepSeek-V3.1) and InvestorBench (Qwen2.5-72B). Closed OpenAI models top LiveTradeBench. In KTD-Fin the open-weight Chinese models (deepseek-v4-pro, glm-5.1, kimi-k2.6) are at the bottom and closed models near the top. The same model ranks very differently across benchmarks: DeepSeek-V3.1 was 8th of 13 in StockBench, 16th of 21 in LTB and 2nd of 6 in AI-Trader US. GPT-5 was below B&H in StockBench, 3rd in LTB, and below QQQ and SSE-50 in AI-Trader.
- **Size shows weak, non-monotonic effects.** InvestorBench avg CR: Qwen2.5 7B 29.5 / 32B 20.9 / 72B 46.2. Llama-3.1 8B 25.5 / 70B 39.0. Yi 9B 22.9 / 34B 38.0. StockBench: GPT-OSS 20B −2.8 vs 120B −0.9. Qwen3 30B-Think 2.1 vs 235B-Think 2.5. Larger is usually a little better, but noise (5.2-pt seed spread in "Beta Not Alpha") swamps gaps of this size.

### Gaps
- LiveTradeBench publishes no baseline. SPY or 15-stock equal-weight returns for 2025-08-18 to 10-24 are not in the paper, and I did not compute them, so "did LLMs beat B&H" can't be answered from that source.
- LiveMACE: no baseline, so B&H for 2026-04-13 to 05-13 is unknown from the source.
- KTD-Fin short-window results (W1–W10), including the post-cutoff W10 (Feb–Apr 2026), were not extracted.
- "Beta Not Alpha" Tables IV–XII (risk, Sharpe, MDD, named runs) and per-run t-stats in Appendix B were not extracted.
- The full FinMMEval 2026 Task 3 leaderboard (other teams and backbones) was not obtained.
- The S&P 500 return for Q2 2025, to compare against DeepFund's extension, is not in the source.

---

## Q3. Winners, and did any model beat buy-and-hold with statistical significance?

### Takeaway
**No source shows any LLM beating buy-and-hold or the market with statistical significance on stocks.** The three papers with formal tests all come out negative or null: FINSABER (alpha p > 0.34), "Beta Not Alpha" (0 of 91 runs with significant alpha, max |t| = 1.79), and LiveOption (no CI above zero; IR negative in every overlay cell). Every other "winner" is a point estimate from one window, usually one run.

### Cited Findings

| Benchmark | Period | Winner (return) | Beat B&H? | Significance tested? |
|---|---|---|---|---|
| InvestorBench | Oct 2020–May 2021 | Qwen2.5-72B, avg CR 46.15% vs B&H 34.10% [T] | Yes, 5 of 13 on average | No — [InvestorBench](https://arxiv.org/html/2412.18174v1) |
| FINSABER | 2004–2024 | B&H beats FinMem/FinAgent on Sharpe nearly everywhere (exception: FinMem TSLA 0.641 vs 0.630) [T] | Mostly no | **Yes: neither LLM agent has significant alpha (all p > 0.34).** Paired t-tests vs B&H give small p in the composite setup, inconsistent in selected-4 [S] — [FINSABER](https://arxiv.org/html/2505.07078v5) |
| DeepFund | Mar 17–Apr 17 2025 | Grok 3 mini Beta +1.1% (only positive) [T] | Beat S&P (−6.91%) via low β. 1 of 9 beat own CRbnh | No — [DeepFund](https://arxiv.org/html/2505.11065v2) |
| StockBench | Mar 3–Jun 30 2025 | Kimi-K2 (composite rank 1). Highest return Qwen3-235B-Think 2.5% vs B&H 0.4% [T] | 8 of 13 on return | No. 3 seeds, no variance — [StockBench](https://arxiv.org/html/2510.02209v2) |
| AMA (stocks) | Aug 1–Sep 30 2025 | TSLA: B&H 46.88% beats all; best agent InvestorAgent-GPT-4.1 40.83% (best SR 6.47 vs 6.00). BMRN: HedgeFundAgent 23.70% vs −6.89% [T] | TSLA 0 of 24; BMRN 20 of 24 | No — [AMA](https://arxiv.org/html/2510.11695) |
| LiveTradeBench | Aug 18–Oct 24 2025 | GPT-4.1, 6.25%, SR 2.64 [T] | No baseline | No — [LTB](https://arxiv.org/html/2511.03628) |
| AI-Trader | Oct 1–Nov 7 2025 | US: MiniMax-M2 9.56% vs QQQ 1.87%. A-share: none beat SSE-50 1.65% [T] | US 3 of 6; A-share 0 of 6 | No — [AI-Trader](https://arxiv.org/html/2512.10971) |
| Profit Mirage | Jul 2024–Jun 2025 | FactFin, the authors' own method [T] | Yes, but by the authors' own method | No — [Profit Mirage](https://arxiv.org/html/2510.07920) |
| KTD-Fin | Jan 2024–Apr 2026 | qwen3.6-plus +85.29% vs CSI300 +36.92%. Only Claude Opus 4.7 has positive selection alpha (+0.2) [T] | 5 of 10 on return. 9 of 10 negative selection α | Wilcoxon protocol specified, results not reported in extracted text — [KTD-Fin](https://arxiv.org/html/2605.28359v1) |
| Quant-Arena | 2024 (A-share) | GPT-6 Astra (score 51.29), ARR 10.7% vs EW 17.1% [T] | No (one medium-effort config claimed +1.4 pp) | No — [Quant-Arena](https://arxiv.org/html/2610.30113) |
| LiveMACE | Apr 13–May 13 2026 | DeepSeek-V3.2 +5.765%, just ahead of GPT-5.4 +5.738% [T] | No baseline | No — [LiveMACE](https://arxiv.org/html/2610.09872) |
| FinMMEval 2026 T3 (TSLA) | May 11–Jun 26 2026 | Fin-Analyst +13.51% vs B&H −14.7% [T] | Yes (falling stock, short-biased) | No — [Fin-Analyst](https://arxiv.org/html/2607.12233) |
| LiveOption | 2025 | No winner. Only MiniMax-M3's earnings CI excludes zero, and it is **negative** (−1.81%) [T] | Overlay: all IR negative | **Yes: bootstrap CIs with Holm correction; nothing positive is significant** — [LiveOption](https://arxiv.org/html/2609.33470) |
| Beta, Not Alpha | 2026 / 2022 / 2020 | Sonnet 4.6 best in 2026 (+8.1%) and 2020 (+25.4%). Haiku 5.5 best in 2022 (+1.4%) [T] | 2026: 0 of 6 beat SPY | **Yes: no four-factor alpha significant across 91 runs. Max abs t = 1.79. Mean α −2.3%/yr, 95% CI [−4.7%, +0.1%]** [S] — [2611.19530](https://arxiv.org/html/2611.19530) |

### Inferences
- When a paper adds factor or attribution controls (KTD-Fin, "Beta Not Alpha", FINSABER), the LLM edge disappears. Raw return wins in KTD-Fin come from market and style exposure, not stock selection.
- Several "winners" are tied to one regime. The single-name live wins (AMA BMRN, FinMMEval TSLA) came from being flat or short in falling stocks. On the same benchmark AMA, nobody beat TSLA B&H in a rally.

### Gaps
- KTD-Fin's Wilcoxon test results were not in the extracted text.
- FinCon claims a Wilcoxon test, but I did not extract its p-values.

---

## Q4. Results grouped by time period (for same-month comparison)

### Takeaway
The densest overlapping coverage is **Aug–Nov 2025**: AMA, LiveTradeBench and AI-Trader. The same models rank very differently across them in overlapping months, which points to benchmark design and noise rather than stable model skill. **2026** results (KTD-Fin tail, LiveMACE, FinMMEval, the 2026 rally in "Beta Not Alpha") use newer models but show the same pattern: in a rising market, no significant alpha and underperformance of SPY.

### Cited Findings

**Pre-2024 test windows (inside model training data; contamination likely)**
| Period | Benchmark | Market move (B&H) | LLM outcome |
|---|---|---|---|
| 2004–2024 | FINSABER | B&H Sharpe 0.46–0.70 | LLM Sharpe below B&H in 7 of 8 universes [C from T] — [FINSABER](https://arxiv.org/html/2505.07078v5) |
| 2020 (253 days) | Beta Not Alpha | SPY +17.2%, EW +40.1% | 1 of 6 beat SPY, 0 of 6 beat EW — [2611.19530](https://arxiv.org/html/2611.19530) |
| Oct 2020–May 2021 | InvestorBench | Avg B&H +34.1% | 5 of 13 beat — [InvestorBench](https://arxiv.org/html/2412.18174v1) |
| 2022 (251 days) | Beta Not Alpha | SPY −18.6%, EW −12.4% | 6 of 6 beat (all lost less) — [2611.19530](https://arxiv.org/html/2611.19530) |
| Oct 2022–Jun 2023 | FinCon | B&H not extracted | FinCon TSLA CR 82.9% [S] — [FinCon](https://arxiv.org/html/2407.06567) |
| 2022–23 feedback / 2024 sealed | Quant-Arena (A-share) | EW +17.1% (2024) | 0 of 9 best configs beat — [Quant-Arena](https://arxiv.org/html/2610.30113) |

**2024 to mid-2025 (backtests on mostly post-cutoff data)**
| Period | Benchmark | Market (B&H) | LLM outcome |
|---|---|---|---|
| Jul 2024–Jun 2025 | Profit Mirage | AAPL −3.4%, NVDA +27.8%, TSLA +57.9% | Agents beat B&H in the authors' table. Separately, returns decay 50–72% after the cutoff — [Profit Mirage](https://arxiv.org/html/2510.07920) |
| Jan 2024–Apr 2026 | KTD-Fin (CSI300) | +36.92% | 5 of 10 beat, 9 of 10 negative selection α — [KTD-Fin](https://arxiv.org/html/2605.28359v1) |
| 2025 full year | LiveOption (options) | Matched B&H | All hedging overlays below B&H — [LiveOption](https://arxiv.org/html/2609.33470) |

**H1 2025**
| Period | Benchmark | Market (B&H) | Best model | Beat B&H |
|---|---|---|---|---|
| Mar 17–Apr 17 2025 (tariff sell-off) | DeepFund live | S&P 500 −6.91% | Grok 3 mini +1.1% | 7 of 9 vs S&P; 1 of 9 vs own CRbnh — [DeepFund](https://arxiv.org/html/2505.11065v2) |
| Mar 3–Jun 30 2025 | StockBench | EW DJIA-20 +0.4% | Qwen3-235B-Think +2.5% (Kimi-K2 rank 1) | 8 of 13 — [StockBench](https://arxiv.org/html/2510.02209v2) |
| Apr–Jun 2025 | DeepFund Q2 extension | not given | Grok 3 to $106,262 | n/a — [DeepFund](https://arxiv.org/html/2505.11065v2) |

**H2 2025 (overlapping live benchmarks)**
| Period | Benchmark | Market (B&H) | Best model | Beat B&H |
|---|---|---|---|---|
| Aug 1–Sep 30 2025 | AMA | TSLA +46.88%, BMRN −6.89% | TSLA InvestorAgent-GPT-4.1 40.83%. BMRN HedgeFundAgent 23.70% | TSLA 0 of 24, BMRN 20 of 24 — [AMA](https://arxiv.org/html/2510.11695) |
| Aug 18–Oct 24 2025 | LiveTradeBench | none reported | GPT-4.1 6.25% | n/a — [LTB](https://arxiv.org/html/2511.03628) |
| Oct 1–Nov 7 2025 | AI-Trader US (hourly) | QQQ +1.87% | MiniMax-M2 9.56% | 3 of 6 — [AI-Trader](https://arxiv.org/html/2512.10971) |
| Oct 1–Nov 7 2025 | AI-Trader A-share | SSE-50 +1.65% | MiniMax-M2 1.31% | 0 of 6 — [AI-Trader](https://arxiv.org/html/2512.10971) |

Cross-benchmark tracking of the same model in overlapping 2025 windows [C from T above]
| Model | StockBench (Mar–Jun) | DeepFund (Mar–Apr) | AMA TSLA/BMRN InvestorAgent (Aug–Sep) | LTB (Aug–Oct) | AI-Trader US / A (Oct–Nov) |
|---|---|---|---|---|---|
| GPT-4.1 | — | −5.9% (6th of 9) | 40.83% / 3.79% (best TSLA agent) | 6.25% (1st of 21) | — |
| GPT-5 | 0.3% (9th of 13, below B&H) | — | — | 5.31% (3rd) | 1.56% (below QQQ) / −3.53% |
| o3 | 1.9% (5th) | — | — | 6.04% (2nd) | — |
| DeepSeek-V3.1 | 1.1% (8th) | — | — | 2.46% (16th) | 8.39% (2nd) / −1.23% |
| Claude Sonnet 4 | 2.2% (7th) | — | 28.91% / −6.89% | 2.45% (17th) | — |
| Claude 3.7 Sonnet | — | −3.7% (3rd) | — | 3.63% (10th) | 3.11% (3rd) / 0.84% |
| Kimi-K2 | 1.9% (rank 1) | — | — | 3.07% (14th) | — |
| Qwen3-235B Instruct / Think | 2.4% / 2.5% | — | — | 3.52% / 1.78% | — |
| Gemini 2.5 Flash | — | −1.9% (2nd) | — | 2.10% (18th) | −0.06% (last) / −1.53% |

**2026**
| Period | Benchmark | Market (B&H) | Best model | Beat B&H |
|---|---|---|---|---|
| Feb 2–Apr 10 2026 | KTD-Fin W10 (post-cutoff for the anchor model) | not extracted | not extracted | — — [KTD-Fin](https://arxiv.org/html/2605.28359v1) |
| Jan 2–Nov 11 2026 | Beta Not Alpha | SPY +12.1%, EW +11.4% | Sonnet 4.6 +8.1% | 0 of 6 — [2611.19530](https://arxiv.org/html/2611.19530) |
| Apr 13–May 13 2026 | LiveMACE (stocks+crypto) | none | DeepSeek-V3.2 +5.765% | n/a — [LiveMACE](https://arxiv.org/html/2610.09872) |
| May 11–Jun 26 2026 | FinMMEval T3 TSLA (AMA) | TSLA −14.7% | Fin-Analyst +13.51% | Yes (one system) — [Fin-Analyst](https://arxiv.org/html/2607.12233) |
| Sep 28–29 2026 | FIDES-Live equity pilot | cash only | n/a | n/a — [FIDES-Live](https://arxiv.org/html/2610.36476) |

### Inferences
- In the same months (Aug–Oct 2025), GPT-4.1 was 1st of 21 on LTB, while DeepSeek-V3.1 was 16th of 21 on LTB but 2nd of 6 on AI-Trader US one month later. Rankings are not stable across benchmarks covering about the same market.
- The most reliable cross-period signal is direction-dependence. Below-market beta wins in down windows and loses in up windows, and this holds in every period group above. A balanced comparison should pair each benchmark's result with its market move, not compare raw returns across benchmarks.
- Model generations change across period groups: GPT-4.x/Claude 3.x in 2025, GPT-5.x/Claude 4.6–5.5/Gemini 3.x in 2026. No single model appears in both an H1 2025 and a 2026 stock benchmark in my extraction, so a "same model over time" comparison is not possible.

### Gaps
- No 2026 benchmark I found reports an index baseline and named per-model results for overlapping months, apart from "Beta Not Alpha" (2026 rally) and FinMMEval TSLA (one system). LiveMACE has no baseline.
- H1 2026 has no direct-trading US stock benchmark with a B&H baseline, other than the long "Beta Not Alpha" 2026 window.
- Any LiveTradeBench, AI-Trader or AMA continuation into 2026 (their websites may run ongoing leaderboards, e.g. ai4trade.ai) was not checked. Website leaderboards would need their methodology confirmed before use as evidence.
