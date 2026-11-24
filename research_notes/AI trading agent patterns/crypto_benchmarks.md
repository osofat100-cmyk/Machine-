# LLM Trading-Agent Benchmarks on Cryptocurrency Markets (2024 to Nov 2026): Per-Model Results vs Buy-and-Hold

Scope note: crypto only. Stock and real-money arenas are covered elsewhere; overlaps are flagged briefly. Research date 2026-11-24.

Provenance labels used below:
- **[V]** = number copied from a table in the official paper or benchmark page. I read the arXiv HTML render (and one CEUR PDF via pdftotext) with an extraction tool. Spot-check the headline cells against the PDF before publishing, because the extraction tool can mis-transcribe.
- **[D]** = number I derived (usually excess return = model return minus buy-and-hold for the same window). It is not printed in the source.
- **[S]** = number given only in the paper's prose or summary, with no full table.
- Open/closed and thinking labels marked "(my label)" are my classification from public model knowledge. The source paper does not state them. Most papers do not label thinking mode at all.

---

## Q1. Benchmark inventory and methodology (authors, coins, spot/perps, exact dates, live vs backtest, runs, frequency)

### Takeaway
I found 10 crypto trading-return evaluations with per-model or per-system numbers. Three of them (AI-Trader, AMA, OAK Research Season 1) are true multi-LLM, same-window, live or leakage-controlled benchmarks. Most others are single-framework papers that swap a few backbones, or competitions where systems are not identified by LLM. Methods vary a lot: daily vs 4-hourly decisions, spot-only vs up to 10x perps, 1 run vs 5 runs. Cross-paper comparisons should be limited to direction (beat or lost to buy-and-hold) rather than magnitudes.

### Cited Findings

**Master methodology table**

| # | Benchmark / paper | Authors / affiliation | Coins | Spot vs perps/leverage | Test window (exact) | Live vs backtest | Decision freq. | Runs / seeds | B&H baseline given? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **CryptoTrade** arXiv 2407.09546 (v2 dated 17 Aug 2026) | Yuan Li, Bingqiao Luo, Qian Wang, Nuo Chen, Xu Liu, Bingsheng He. National University of Singapore | BTC, ETH, SOL | Spot-style buy/sell/hold, no leverage; $1M start split cash/asset; proportional fee | 2023, per coin: BTC bear 2023-04-12 to 06-16, sideways 06-17 to 08-25, bull 10-01 to 12-01 (ETH/SOL similar; SOL sideways 07-08 to 08-31) | Backtest | Daily | Not stated; ± values are daily-return std, not runs | Yes |
| 2 | **FS-ReasoningAgent** arXiv 2410.12464 (v3, 12 Mar 2025) | Qian Wang, Yuchen Gao, Zhenheng Tang, Bingqiao Luo, Nuo Chen, Bingsheng He. NUS and HKUST | BTC, ETH, SOL | Spot plus cash, no leverage mentioned | Bull 2024-01-24 to 2024-03-13 (all coins). Bear: BTC 2024-05-21 to 07-13, ETH 05-27 to 07-08, SOL 05-21 to 07-11 | Backtest | Daily | Single result per config | Yes |
| 3 | **InvestorBench** arXiv 2412.18174 (crypto task) | Haohang Li, Yupeng Cao, Yangyang Yu et al. (Stevens), Yueru He (Columbia), Guojun Xiong (Harvard), Jimin Huang, Lingfei Qian, Xueqing Peng, Qianqian Xie (The Fin AI) | BTC, ETH | Buy/Sell/Hold, no leverage stated | Warm-up 2023-02-11 to 2023-04-04; **test 2023-04-05 to 2023-11-05** | Backtest | Daily | Temp 0.6; **median of 5 epochs** | Yes |
| 4 | **LLM Multi-Agent Crypto Portfolio** arXiv 2501.00826v3 (16 Jun 2026) | Yichen Luo, Yebo Feng, Jiahua Xu, Paolo Tasca, Yang Liu. UCL, NTU, Exponential Science | Top-15 L1s (BTC, ETH, BNB, XRP, SOL, TRX, ADA, BCH, HYPE, XMR, ZEC, LTC, SUI, AVAX, HBAR) | Long-only portfolio, 0.1% cost per side | Calendar 2025, 52 ISO weeks (27 bull weeks, 15 bear weeks) | Backtest | Weekly rebalance | **1 run**, temp 0.0 | Yes (BTC Hold, MCap Hold) |
| 5 | **Agent Market Arena (AMA)** "When Agents Trade" arXiv 2510.11695v2 | Lingfei Qian, Xueqing Peng, ... Jimin Huang (The Fin AI), plus Stevens, Georgia Tech, Columbia, U Florida (Lopez-Lira), U Montréal, Harvard, U Manchester | BTC, ETH (plus TSLA, BMRN stocks) | BUY/SELL/HOLD, no leverage | **Live 2025-08-01 to 2025-09-30** (init 2025-05-01 to 07-31) | Live (paper) | Daily | Not reported | Yes |
| 6 | **AI-Trader** arXiv 2512.10971v1 | Tianyu Fan, Yuhao Yang, Yangqin Jiang, Yifei Zhang, Yuxuan Chen, Chao Huang. University of Hong Kong | 10 Bitwise-index USDT pairs: BTC, ETH, XRP, SOL, ADA, SUI, LINK, AVAX, LTC, DOT | Not stated | **2025-11-01 to 2025-11-14** | Live/real-time (benchmark framing) | Daily | Not stated | Yes (CD5 index) |
| 7 | **LiveMACE** arXiv 2610.09872v1 | Jun Zhao (NUS, corr.), Leiming Fu and others (Fudan), Hao Xu (U Sydney) | BTC, ETH, SOL, BNB, XRP, DOGE plus 17 US stocks | Hyperliquid data. Crypto leverage allowed in [1,10] by prompt; rule caps total effective leverage at 5x; spot vs perp not stated | **2026-04-13 to 2026-05-13** (~30 days) | Live paper-trading | Every 4 hours | Not stated | **No** |
| 8 | **Agent4Crypto** arXiv 2611.12269v1 | Guangyan Gan (NTU), Jiahao Li (Tsinghua), Jiashun Wang (SUIBE), Lin William Cong (NTU) | BTC, ETH, XRP | Long-only, no shorting/leverage, 0.1% fee, $1M | Test: BTC 2026-04-13 to 06-27; ETH 2026-04-16 to 06-30; XRP 2026-05-06 to 07-20 | Backtest | Daily (trade at open) | 5 LLM runs averaged; baselines seeds 42-46 | Yes |
| 9 | **FinMMEval 2026 Task 3 (CLEF)** overview, CEUR Vol-4283 paper186 | Zhuohan Xie (MBZUAI) et al., incl. The Fin AI, Sofia U, McGill/Mila, Preslav Nakov | BTC (plus TSLA) | Long/flat/short daily; 6 bp fee plus 10 bp slippage; $100k per asset | **BTC 2026-05-11 to 2026-07-04** (55 scoring dates) | Live endpoint competition, 18 teams | Daily | One endpoint per team | **No** (HOLD = 0% only) |
| 10 | **"Can AI Make Money in Crypto?"** arXiv 2609.34510v1 | Xingtong Yu ... Hui Zhang, Yuan Fang. CUHK, USTC, Jilin, RMIT, SMU, Infplane | BTC, ETH, XRP, DOGE, ADA, TRX, LINK, LTC, HBAR, OKB | Longs spot (0.10% fee), shorts perps (0.05%). **10x isolated** in 2025 replay; **2x** in paper trading | Backtest 2025-01-01 to 2025-12-31; paper 2026-06-04 to 2026-09-21; live 2026-08-24 to 2026-09-21 | All three | One decision per closed 4h bar | LLM methods 3 runs averaged in backtest | Yes (BTC) |
| 11 | **OAK Research AI Trading Benchmark, Season 1** (industry leaderboard with published method) | OAK Research | BTC, ETH, SOL, XRP, HYPE, DOGE **perps** | Isolated margin, **up to 10x**; liquidation at 50% margin loss; real hourly funding; Hyperliquid-like fees/slippage; $10k | **2026-07-18 to 2026-10-16** (90 days) | Historical simulation on Hyperliquid data. Each model only enters seasons after its knowledge cutoff | Daily (fill at close) | Page says both "averaged over several independent runs" and "run once"; ± shown | Yes (BTC hold, cash) |

Sources: [CryptoTrade](https://arxiv.org/html/2407.09546v2); [FS-ReasoningAgent](https://arxiv.org/html/2410.12464); [InvestorBench](https://arxiv.org/html/2412.18174); [Multi-agent portfolio](https://arxiv.org/html/2501.00826v3); [AMA](https://arxiv.org/html/2510.11695); [AI-Trader](https://arxiv.org/html/2512.10971); [LiveMACE](https://arxiv.org/html/2610.09872); [Agent4Crypto](https://arxiv.org/html/2611.12269); [FinMMEval Task 3 overview](https://ceur-ws.org/Vol-4283/paper186.pdf); [Can AI Make Money in Crypto?](https://arxiv.org/html/2609.34510v1); [OAK Research benchmark](https://oakresearch.io/en/ai/trading-benchmark)

**Crypto-adjacent benchmarks with no trading returns (for context only):**
- **CryptoBench** (arXiv 2512.00417, v5 May 2026; Jiacheng Guo, ..., Mengdi Wang). 50 expert-written questions per month in four categories (simple/complex retrieval, simple/complex prediction). The metric is a 0-3 LLM-judged rubric, not trading P&L. The window is Oct 12 to Nov 11 (year not stated in the text) — [CryptoBench](https://arxiv.org/html/2512.00417v5)
- **LATTICE** (arXiv 2604.26235, 29 Apr 2026; Aaron Chan et al., Sahara AI / USC). Scores six crypto copilots (Elsa, Gina, June, Minara, Sorin, Surf) on 1,200 queries with an LLM judge (GPT-5.2). No returns, Sharpe, or buy-and-hold — [LATTICE](https://arxiv.org/html/2604.26235)
- **TraderBench** (arXiv 2603.00285; Xiaochuang Yuan (Amazon) et al.). The crypto track reports only a composite score (35% return, 30% Sharpe, 20% win rate, 15% MDD penalty) over baseline/noisy/meta/adversarial transforms of historical data. Coins and period are not specified, and there is no buy-and-hold — [TraderBench](https://arxiv.org/html/2603.00285)
- **DXAP / DX Terminal Pro production fleets** (arXiv 2609.05663). Real-world fleets: 500-599 agents on Hyperliquid perps, Jun-Aug 2026, plus 3,505 real-ETH vaults on Base memecoins. Models are not named and there are no per-model returns. The fleet win rate was 41% vs 50% for matched Hyperliquid retail. This overlaps with the real-money arena research — [arXiv 2609.05663](https://arxiv.org/abs/2609.05663)

### Inferences
- Only AMA, AI-Trader, LiveMACE, FinMMEval and OAK avoid training-data leakage by design: they run live, or (OAK) gate each model to post-cutoff seasons. CryptoTrade, FS-ReasoningAgent and InvestorBench backtest on 2023 to H1-2024 data with GPT-4/4o/o1-class models whose training data likely covers those prices. Their "beat B&H" results carry contamination risk. The papers themselves do not quantify this.
- Leverage differs by orders of magnitude: spot-only (CryptoTrade, InvestorBench, AMA, Agent4Crypto) vs 10x (OAK; 2025 replay in 2609.34510). Drawdowns and blow-ups such as DeepSeek V4 Pro -62.8% on OAK, or DeepSeek -43% / Qwen -69% in the 2609.34510 2025 replay, are largely leverage artifacts. They should not be compared with spot-only results.

### Gaps
- CryptoTrade's EMNLP 2024 venue is not stated on the arXiv v2 page I read. I did not verify it in the ACL Anthology.
- AI-Trader: spot vs leverage, starting capital and run count are not stated.
- LiveMACE: no per-market (crypto-only) split and no buy-and-hold in the paper. The GitHub README (RaymondVoldemortFu/LiveMACE) also gives no per-market numbers; raw logs may exist in `backend/` or `docs/evaluation/` but I did not open them — [LiveMACE GitHub](https://github.com/RaymondVoldemortFu/LiveMACE)
- I did not open LiveTradeBench (arXiv 2511.03628), so I have not confirmed whether it includes crypto. It is cited for "reasoning models don't outperform" — [LiveTradeBench](https://arxiv.org/html/2511.03628). I also did not open Market-Bench (2512.12264; strategy-code accuracy, not returns), PortBench (2605.27887), AI Trading tech-analysis (2607.15414), Bitcoin multi-agent (2510.08068, DeepSeek-R1 single backbone), or CSTrader (2606.31461; virtual game-item market, not crypto).
- I did not find the AMA public leaderboard URL or any post-September-2025 AMA standings with newer models.

---

## Q2. Per-model result tables (return, Sharpe/Sortino, MDD, buy-and-hold for same period; open/closed; thinking)

### Takeaway
Here are the full per-model tables, in chronological order of test window. Across every multi-model live or post-cutoff benchmark, most LLMs failed to beat buy-and-hold. In AI-Trader 1 of 6 beat the index. In OAK S1 1 of 12 beat BTC. In AMA BTC only 2-3 of 24 agent-backbone cells beat a +0.66% B&H, and on ETH almost none beat +18.56%.

### Cited Findings

#### 2.1 CryptoTrade (2023 backtest, daily, spot) — Total return % [V], Sharpe [V]
Source: [CryptoTrade arXiv 2407.09546v2](https://arxiv.org/html/2407.09546v2), Tables 2-4. Backbones: GPT-4 and GPT-3.5-turbo (closed, non-thinking; my label). MDD is not reported. GPT-4o is mentioned in the text and ablation but is not in the main tables.

| Coin / regime | B&H return | CryptoTrade GPT-4 | CryptoTrade GPT-3.5-turbo | GPT-4 excess vs B&H [D] | GPT-3.5 excess [D] |
|---|---|---|---|---|---|
| BTC bull (2023-10-01 to 12-01) | 39.66 (SR 0.25) | 26.35 (0.23) | 28.47 (0.23) | -13.31 | -11.19 |
| BTC sideways | -0.83 (0.00) | -4.07 (-0.04) | -5.08 (-0.06) | -3.24 | -4.25 |
| BTC bear (2023-04-12 to 06-16) | -15.61 (-0.11) | -11.72 (-0.11) | -13.71 (-0.12) | +3.89 | +1.90 |
| ETH bull | 22.59 (0.14) | 25.72 (0.17) | 18.91 (0.15) | +3.13 | -3.68 |
| ETH sideways | -1.91 (-0.00) | 0.72 (0.02) | -5.02 (-0.04) | +2.63 | -3.11 |
| ETH bear | -12.24 (-0.07) | -13.72 (-0.10) | -14.40 (-0.10) | -1.48 | -2.16 |
| SOL bull | 176.72 (0.30) | 99.84 (0.27) | 102.45 (0.28) | -76.88 | -74.27 |
| SOL sideways | -3.23 (0.00) | -2.16 (0.00) | -13.05 (-0.15) | +1.07 | -9.82 |
| SOL bear | -36.08 (-0.18) | -19.55 (-0.13) | -24.08 (-0.10) | +16.53 | +12.00 |

The paper also notes a data inconsistency: its ablation Table 5 (labelled ETH bull) reports 28.47, which matches the BTC bull GPT-3.5 cell instead — [CryptoTrade](https://arxiv.org/html/2407.09546v2)

#### 2.2 FS-ReasoningAgent vs CryptoTrade, multi-backbone (H1 2024 backtest, daily) — Return % [V] (Sharpe in parentheses)
Source: [arXiv 2410.12464](https://arxiv.org/html/2410.12464). Backbones: GPT-3.5-turbo, GPT-4, GPT-4o (closed, non-thinking), o1-mini (closed, **reasoning**) (my labels).

| Strategy | BTC bull | BTC bear | ETH bull | ETH bear | SOL bull | SOL bear |
|---|---|---|---|---|---|---|
| **Buy & Hold** | **79.63 (0.53)** | **-19.15 (-0.21)** | **78.72 (0.53)** | **-23.63 (-0.28)** | **77.35 (0.36)** | **-24.08 (-0.11)** |
| CryptoTrade GPT-3.5-turbo | 70.25 (0.44) | -18.08 (-0.21) | 74.83 (0.53) | -22.35 (-0.30) | 66.64 (0.34) | -23.56 (-0.12) |
| CryptoTrade GPT-4 | 66.83 (0.39) | -21.11 (-0.26) | 74.41 (0.53) | -23.06 (-0.29) | 32.59 (0.23) | -21.51 (-0.11) |
| CryptoTrade GPT-4o | 68.35 (0.43) | -20.21 (-0.24) | 74.23 (0.53) | -24.13 (-0.30) | 48.41 (0.33) | -24.63 (-0.13) |
| CryptoTrade o1-mini (reasoning) | 70.83 (0.44) | -19.89 (-0.25) | 75.01 (0.53) | -23.68 (-0.29) | 42.48 (0.29) | -21.95 (-0.13) |
| FS-Reasoning GPT-3.5-turbo | 73.55 (0.23) | -19.15 (-0.23) | 71.09 (0.52) | -22.33 (-0.30) | 68.03 (0.34) | -24.67 (-0.14) |
| FS-Reasoning GPT-4 | 77.47 (0.46) | -15.23 (-0.25) | 76.67 (0.54) | -23.41 (-0.31) | 64.35 (0.33) | -25.33 (-0.16) |
| FS-Reasoning GPT-4o | 74.27 (0.45) | -13.94 (-0.33) | 76.74 (0.54) | -21.64 (-0.31) | 69.67 (0.35) | -14.52 (-0.09) |
| FS-Reasoning o1-mini (reasoning) | 76.19 (0.46) | -15.91 (-0.35) | 77.28 (0.54) | -21.88 (-0.32) | 76.71 (0.36) | -19.40 (-0.11) |

- **No LLM configuration beat B&H in any bull window** [D: all 24 bull cells < B&H]. In bear windows, FS-Reasoning GPT-4o lost less than B&H on all three coins: BTC +5.21pp, ETH +1.99pp, SOL +9.56pp [D].
- Paper's statement: "stronger LLMs (o1-mini, GPT-4o) do not always outperform weaker LLMs (GPT-4, GPT-3.5-turbo)" — [arXiv 2410.12464](https://arxiv.org/html/2410.12464)
- Oddity worth noting: some FS-Reasoning bear rows report a higher return than B&H but a lower Sharpe (e.g., BTC bear GPT-4o -13.94 / SR -0.33 vs B&H -19.15 / -0.21). The source does not explain this — [arXiv 2410.12464](https://arxiv.org/html/2410.12464)

#### 2.3 InvestorBench crypto (test 2023-04-05 to 2023-11-05, daily, median of 5 runs) — CR %, SR, AV %, MDD % [V]
Source: [InvestorBench arXiv 2412.18174](https://arxiv.org/html/2412.18174) Table 3. Type and size labels come from the paper's Table 1. Thinking: o1-preview is a reasoning model (my label); all others are non-thinking.

| Model | Type (paper) | Size | BTC CR | BTC SR | BTC MDD | ETH CR | ETH SR | ETH MDD | BTC excess [D] | ETH excess [D] |
|---|---|---|---|---|---|---|---|---|---|---|
| **Buy & Hold** | baseline | – | **21.821** | 0.683 | 20.796 | **4.528** | 0.146 | 29.889 | – | – |
| GPT-o1-preview | Proprietary (reasoning) | N/A | **34.060** | **1.114** | 17.075 | 2.496 | 0.085 | 27.692 | **+12.24** | -2.03 |
| GPT-4 | Proprietary | N/A | 22.396 | 0.828 | 17.206 | 1.516 | 0.051 | 32.541 | +0.58 | -3.01 |
| GPT-4o | Proprietary | N/A | 14.330 | 0.532 | 17.278 | 4.666 | 0.190 | 22.539 | -7.49 | +0.14 |
| Palmyra-Fin-70B | Financial domain (open; my label) | 70B | -20.812 | -1.212 | 27.782 | 4.795 | 0.240 | 16.405 | -42.63 | +0.27 |
| Qwen2.5-72B-Instruct | Open-source | 72B | 0.549 | 0.325 | 0.897 | **11.984** | 0.584 | 27.642 | -21.27 | **+7.46** |
| Llama-3.1-70B-Instruct | Open-source | 70B | 20.440 | 0.758 | 17.813 | -11.888 | -0.410 | 36.416 | -1.38 | -16.42 |
| DeepSeek-67B-Chat | Open-source | 67B | 28.307 | 0.891 | 17.944 | 9.480 | 0.309 | 26.261 | **+6.49** | **+4.95** |
| Yi-1.5-34B-Chat | Open-source | 34B | 13.620 | 0.434 | 22.790 | 6.325 | 0.227 | 25.707 | -8.20 | +1.80 |
| Qwen2.5-32B-Instruct | Open-source | 32B | 11.566 | 0.869 | 7.984 | 2.823 | 0.194 | 7.883 | -10.26 | -1.71 |
| DeepSeek-V2-Lite | Open-source | 15.7B | 4.804 | 0.153 | 20.562 | -9.504 | -0.311 | 21.270 | -17.02 | -14.03 |
| Yi-1.5-9B-Chat | Open-source | 9B | 7.953 | 0.253 | 26.545 | -3.684 | -0.119 | 35.417 | -13.87 | -8.21 |
| Llama-3.1-8B-Instruct | Open-source | 8B | 20.521 | 0.646 | 21.104 | 4.939 | 0.163 | 29.466 | -1.30 | +0.41 |
| Qwen-2.5-Instruct-7B | Open-source | 7B | 19.477 | 0.612 | 20.796 | -1.339 | -0.075 | -16.053 (sic) | -2.34 | -5.87 |
| *Avg proprietary* | | | 23.595 | 0.825 | 17.186 | 2.893 | 0.109 | 27.591 | +1.77 | -1.64 |
| *Avg open-source* | | | 14.137 | 0.549 | 17.382 | 1.015 | 0.062 | 21.557 | -7.68 | -3.51 |

- Paper's claim: mid- and small-sized open-source models generally underperform the market baseline on CR/SR in crypto, and large open-source or proprietary models are needed to capture news/sentiment signals. The paper offers no statistical test — [InvestorBench](https://arxiv.org/html/2412.18174)
- Only **DeepSeek-67B-Chat** beat B&H on both coins [D]. Qwen2.5-32B had the best risk profile (BTC SR 0.869 > B&H 0.683, MDD 7.98%) but a lower return [V].

#### 2.4 LLM Multi-Agent Crypto Portfolio (calendar 2025, weekly, 15 L1s, 1 run)
Source: [arXiv 2501.00826v3](https://arxiv.org/html/2501.00826v3). A full table exists only for GPT-4o; GPT-5 and Claude Sonnet 4.5 have prose-only figures [S].

| Item | Cum % | SR | MDD % | Provenance |
|---|---|---|---|---|
| BTC Hold (passive) | -3.36 | 0.091 | -29.73 | [V] |
| MCap Hold (passive) | -4.54 | 0.095 | -31.31 | [V] |
| GPT-4o single-agent zero-shot | -26.00 | -0.309 | -39.29 | [V] |
| GPT-4o single-agent CoT | -8.81 | 0.013 | -34.48 | [V] |
| GPT-4o Hierarchical (Skill), best GPT-4o | +133.52 | 1.502 | -39.33 | [V] |
| GPT-4o Debate (Skill) | +110.00 | 1.310 | -44.60 | [V] |
| GPT-4o mean over 16 configs / multi-agent avg / single-agent avg | +17.5 / +31.0 / -23.0 | – | – | [S] |
| GPT-5 (closed, reasoning; my label) mean 16 configs / MA avg / SA avg | +6.9 / +12.2 / -9.0 | – | – | [S] |
| GPT-5 best: Hierarchical (CoT) | +39.7 | – | – | [S] |
| Claude Sonnet 4.5 (closed; thinking mode not stated) mean / MA avg / SA avg | +33.0 / +43.9 / +0.1 | – | – | [S] |
| Claude Sonnet 4.5 best: Debate (Skill) | +121.3 | – | – | [S] |
| Non-LLM: TimesNet / Informer | +83.40 / +74.89 | 1.212 / 1.236 | -32.09 / -26.37 | [V] |

- Inference from the table: in a falling year (BTC -3.36%), architecture explained more than backbone. Every single-agent average was negative or flat, every multi-agent average was positive, and GPT-5 (reasoning) had the lowest mean of the three backbones [D from S].

#### 2.5 Agent Market Arena, crypto (LIVE 2025-08-01 to 2025-09-30, daily) — CR %, SR, MDD % [V]
Source: [AMA arXiv 2510.11695v2](https://arxiv.org/html/2510.11695) Table 1. All backbones are closed: GPT-4o, GPT-4.1, Gemini-2.0-flash, Claude-3.5-haiku, Claude-sonnet-4 (non-thinking; my label). There are no open-weight models.

**Buy & Hold:** BTC CR **0.66** (SR 0.28, MDD 11.95); ETH CR **18.56** (SR 1.77, MDD 20.23) [V]

| Agent | Backbone | BTC CR | BTC SR | BTC MDD | ETH CR | ETH SR | ETH MDD |
|---|---|---|---|---|---|---|---|
| InvestorAgent | GPT-4o | -1.22 | -0.25 | 8.79 | -1.98 | 0.06 | 22.13 |
| InvestorAgent | GPT-4.1 | -3.34 | -0.90 | 9.92 | 1.35 | 0.41 | 23.76 |
| InvestorAgent | Gemini-2.0-flash | -2.78 | -0.76 | 10.20 | -6.39 | -0.28 | 32.27 |
| InvestorAgent | Claude-3.5-haiku | -7.06 | -1.31 | 15.18 | 5.05 | 0.76 | 22.98 |
| InvestorAgent | Claude-sonnet-4 | -6.48 | -1.42 | 12.62 | 5.56 | 0.83 | 27.17 |
| InvestorAgent | Vote | -2.19 | -0.49 | 9.68 | -1.97 | 0.09 | 28.80 |
| TradeAgent | GPT-4o | -5.05 | -4.09 | 5.05 | -6.23 | -1.05 | 15.95 |
| TradeAgent | GPT-4.1 | -5.65 | -1.07 | 9.76 | -11.42 | -0.72 | 24.75 |
| TradeAgent | **Gemini-2.0-flash** | **5.02** | **1.33** | 5.83 | 9.78 | 1.32 | 16.01 |
| TradeAgent | Claude-3.5-haiku | -14.51 | -3.77 | 16.37 | -12.93 | -1.40 | 15.21 |
| TradeAgent | Claude-sonnet-4 | -13.02 | -3.03 | 15.02 | -12.35 | -1.71 | 20.50 |
| TradeAgent | Vote | -7.28 | -1.78 | 11.53 | -9.89 | -1.35 | 14.57 |
| HedgeFundAgent | all 5 backbones and Vote (identical rows) | -9.09 | -1.76 | 11.14 | **39.66** | **3.21** | 14.63 |
| DeepFundAgent | GPT-4o | -0.30 | 0.04 | 7.98 | 18.03 | 1.74 | 21.86 |
| DeepFundAgent | GPT-4.1 | 0.44 | 2.45 | 0.00 | 2.89 | 0.57 | 26.08 |
| DeepFundAgent | Gemini-2.0-flash | 0.00 | 0.00 | 0.00 | -13.11 | -1.87 | 22.20 |
| DeepFundAgent | Claude-3.5-haiku | 1.67 | 0.50 | 7.91 | 10.74 | 1.21 | 23.11 |
| DeepFundAgent | Claude-sonnet-4 | -8.24 | -2.24 | 10.18 | 8.20 | 1.11 | 18.58 |
| DeepFundAgent | Vote | -0.54 | -2.45 | 0.54 | 4.91 | 0.75 | 13.00 |

- Beat BTC B&H (+0.66): TradeAgent/Gemini-2.0-flash (+4.36pp) and DeepFundAgent/Claude-3.5-haiku (+1.01pp) [D]. Beat ETH B&H (+18.56): only HedgeFundAgent (+21.10pp), whose rows are identical for every backbone [D].
- The identical HedgeFundAgent rows across all backbones look like a pipeline artifact, not a model effect. The paper attributes them to hierarchical coordination reducing variance, and states that agent design matters more than backbone choice — [AMA](https://arxiv.org/html/2510.11695)

#### 2.6 AI-Trader crypto (2025-11-01 to 2025-11-14, daily, 10 coins) — CR, Sortino, Vol, MDD [V]
Source: [AI-Trader arXiv 2512.10971v1](https://arxiv.org/html/2512.10971) Table 1. The paper reports Sortino, not Sharpe. Open/thinking labels are mine.

| Model | Open/closed (my label) | Thinking (my label) | CR | Sortino | Vol | MDD | Excess vs CD5 [D] | No-trade share / avg trades [V] |
|---|---|---|---|---|---|---|---|---|
| **DeepSeek-v3.1** | Open-weight | Hybrid; mode used not stated | **-12.18** | -2.85 | 28.55 | -14.02 | **+2.12** | 0.44 / 2.00 |
| MiniMax-M2 | Open-weight | Reasoning (interleaved thinking) | -14.80 | -4.30 | 41.20 | -16.56 | -0.50 | 0.44 / 1.56 |
| Claude-3.7-Sonnet | Closed | Hybrid; mode not stated | -15.30 | -2.27 | 32.20 | -16.93 | -1.00 | 0.00 / 5.00 |
| GPT-5 | Closed | Reasoning | -16.41 | -4.38 | 40.95 | -17.98 | -2.11 | 0.78 / 0.78 |
| Qwen3-Max | Closed (API-only) | Non-thinking (presumed) | -16.85 | -6.54 | 59.90 | -18.03 | -2.55 | 0.44 / 1.33 |
| Gemini-2.5-Flash | Closed | Thinking-capable; mode not stated | -18.63 | -5.55 | 46.22 | -20.15 | -4.33 | 0.67 / 1.67 |
| **CD5 index baseline** | – | – | **-14.30** | -12.71 | 54.93 | -15.71 | – | – |

- The paper states DeepSeek-v3.1 is the only agent that beat the baseline in crypto — [AI-Trader](https://arxiv.org/html/2512.10971)
- Overlap with stocks, same paper: US NASDAQ-100 hourly, Oct 1 to Nov 7 2025, QQQ +1.87. Results: MiniMax-M2 +9.56, DeepSeek-v3.1 +8.39, Claude-3.7 +3.11, GPT-5 +1.56, Qwen3-Max +0.39, Gemini-2.5-Flash -0.06 — [AI-Trader](https://arxiv.org/html/2512.10971)

#### 2.7 LiveMACE (LIVE 2026-04-13 to 2026-05-13, every 4h; crypto and equities pooled) — [V]
Source: [LiveMACE arXiv 2610.09872v1](https://arxiv.org/html/2610.09872) Table 2. **There is no crypto-only split, no Sharpe/Sortino, and no buy-and-hold.** $10k start.

| Model | Open/closed (my label) | Final return | MDD | Hard-rule pass rate |
|---|---|---|---|---|
| DeepSeek-V3.2 | Open-weight | **+5.765%** | 4.270% | 0.877 |
| GPT-5.4 | Closed | +5.738% | 5.169% | 0.682 |
| Qwen3-Max | Closed (API) | +4.418% | 5.674% | 0.613 |
| Gemini-3.1-Pro | Closed | +3.503% | 4.927% | 0.888 |
| Grok-4.20 | Closed | +3.085% | 5.165% | 0.834 |

- Switching from ReAct to Multi-Agent changed return by GPT-5.4 +2.45pp, DeepSeek-V3.2 +3.72pp, Gemini-3.1-Pro +2.57pp, Qwen3-Max -4.39pp — [LiveMACE](https://arxiv.org/html/2610.09872) Table 3.

#### 2.8 Agent4Crypto (backtest Apr-Jul 2026, daily, long-only, 5 runs) — Total return % / Sharpe [V]
Source: [Agent4Crypto arXiv 2611.12269v1](https://arxiv.org/html/2611.12269) Table 2. Single backbone **GPT-5.4** (closed) for both LLM methods, so there is no cross-model comparison. MDD is not reported.

| Strategy | BTC TR (SR) | ETH TR (SR) | XRP TR (SR) |
|---|---|---|---|
| **Buy & Hold** | **-15.24 (-0.10)** | **-31.81 (-0.19)** | **-22.37 (-0.13)** |
| CryptoTrade (GPT-5.4) | -5.12 (-0.06) | -16.29 (-0.24) | -16.08 (-0.19) |
| **Agent4Crypto (GPT-5.4)** | **+6.66 (0.10)** | **-4.77 (-0.08)** | **-2.36 (-0.04)** |
| Best non-LLM per coin: SLMA (BTC) / SMA (ETH) / PatchTST (XRP) | +3.78 / -10.78 / -5.78 | | |
| PPO (RL) | -5.75 | -25.45 | -11.18 |

- Excess vs B&H [D]: Agent4Crypto +21.90pp (BTC), +27.04pp (ETH), +20.01pp (XRP); CryptoTrade-GPT-5.4 +10.12 / +15.52 / +6.29. In this falling market, every active strategy except LSTM on BTC lost less than B&H [D].

#### 2.9 FinMMEval 2026 Task 3 — BTC live (2026-05-11 to 2026-07-04, daily long/flat/short, 6bp fee + 10bp slippage) [V]
Source: [FinMMEval Task 3 overview, CEUR Vol-4283 paper186](https://ceur-ws.org/Vol-4283/paper186.pdf) Table 2. Teams are not identified by LLM backbone.

| Rank (mean) | Team | BTC CR % | TSLA CR % |
|---|---|---|---|
| 1 | Infraglyph | -0.68 | 10.34 |
| 2 | Calibrated Signals | 0.48 | 7.76 |
| 3 | **NLP-DE** | **9.97 (best BTC)** | -1.91 |
| 4 | Fin-Analyst | -5.45 | 13.33 |
| 5 | pjmathematician | 2.05 | 0.84 |
| 6 | The Lab Rats | 4.26 | -3.14 |
| 7 | CLaC | 3.50 | -2.75 |
| 8 | Enjamul Islam Khan | 0.00 | 0.00 |
| 9 | Amongus | 2.38 | -2.42 |
| 10 | TrustMe | -3.62 | 3.44 |
| 11 | Gentlemen | -5.51 | 5.21 |
| 12 | AI_TLfanclub | -1.60 | -0.88 |
| 13 | AAA | -2.50 | -0.93 |
| 14 | A | -6.27 | -3.79 |
| 15 | TCLabs | -9.70 | -1.43 |
| 16 | Club GAIA - ESCOM | -4.40 | -7.07 |
| 17 | DS@GT ARC | -12.55 | -2.57 |
| 18 | TextSentinels | -11.51 | -6.20 |

- The organizers provide **only a HOLD (0%) baseline**, and they state that "positive CR does not establish outperformance of passive market exposure". BTC vs TSLA returns correlated at Pearson r = 0.06 across the 18 systems — [FinMMEval overview](https://ceur-ws.org/Vol-4283/paper186.pdf)
- BTC B&H: the Fin-Analyst participant paper reports BTC B&H "about -26.3%" over its live window (data to 2026-06-29). It also reports its own BTC -5.30% as "+17.63% vs B&H", which implies a B&H of about -22.9% [D]. The two figures are internally inconsistent. Fin-Analyst's BTC component used **no LLM** (a rule-based three-signal vote); gpt-4o-mini handled TSLA only — [Fin-Analyst arXiv 2607.12233](https://arxiv.org/html/2607.12233)
- Offline backtest in the same paper (2025-08-01 to 2026-05-10): BTC B&H -0.315 (-31.5%), rule-based BTC +0.228 [V] — [Fin-Analyst](https://arxiv.org/html/2607.12233)

#### 2.10 "Can AI Make Money in Crypto?" (2609.34510) — direct-LLM traders vs BTC B&H [V]
Source: [arXiv 2609.34510v1](https://arxiv.org/html/2609.34510v1). DeepSeek = V4 Flash (Pro in part of the 2025 run), open-weight (my label). Qwen = 3.6 Max Preview, closed/API (my label). FinMem used qwen3-max; FinAgent and TradingAgents used DeepSeek V4 Flash.

Historical replay 2025-01-01 to 2025-12-31 (10x leverage for direct models):

| Method | Cum ret % | Alpha % | Sharpe | Max DD % | Vol % |
|---|---|---|---|---|---|
| **Buy&Hold BTC** | **-7.63** | 0.00 | -0.18 | 33.01 | 41.74 |
| DeepSeek (direct) | -43.30 | 278.44 (sic) | -0.22 | 96.85 | 261.12 |
| Qwen (direct) | -68.62 | 38.38 | -0.62 | 82.85 | 188.58 |
| FinGPT (Llama-2-13B LoRA, open) | -15.15 | -7.03 | 0.03 | 45.13 | 60.08 |
| FinMem (qwen3-max) | -20.76 | -19.30 | -0.78 | 41.08 | 29.95 |
| FinAgent (DeepSeek V4 Flash) | -41.06 | -48.14 | -1.61 | 45.51 | 32.78 |
| TradingAgents (DeepSeek V4 Flash) | -9.16 | -3.36 | -0.25 | 31.79 | 38.02 |

Backtest (BT) vs paper trading (PT), same window 2026-06-04 to 2026-09-21 (2x leverage), cells BT / PT:

| Method | Cum ret % | Alpha % | Sharpe | Max DD % |
|---|---|---|---|---|
| Buy&Hold BTC | 30.35 / ? (row garbled in extraction) | – | – | – |
| DeepSeek | 7.35 / 9.53 | 1.61 / -0.91 | 1.43 / 1.32 | 3.31 / 8.83 |
| Qwen | 11.35 / **37.77** | 15.66 / 53.15 | 1.18 / 2.94 | 8.49 / 11.83 |
| FinGPT | 20.04 / 16.85 | 14.15 / 3.51 | 1.90 / 1.62 | 9.41 / 8.97 |
| FinMem | -6.63 / 5.28 | -20.98 / -2.93 | -0.51 / 0.74 | 20.43 / 15.10 |
| FinAgent | 0.20 / 1.73 | -10.08 / -15.28 | -0.21 / 0.43 | 15.31 / 7.88 |

Live trading 2026-08-24 to 2026-09-21: Qwen BT 6.18 / PT 10.10 / **LT 3.72**, alpha -0.63 / 15.80 / **-28.10**, Sharpe 1.34 / 1.85 / 0.34. The B&H row for that window is garbled in extraction; its first value is 11.63 — [arXiv 2609.34510](https://arxiv.org/html/2609.34510v1)
- The search snippet summarizing the paper said all four highlighted methods had negative alpha in live trading and only Qwen kept a positive Sharpe, with a backtest-to-paper gap of up to 26.42pp for Qwen. That gap is consistent with 37.77 - 11.35 = 26.42 [D].

#### 2.11 OAK Research AI Trading Benchmark, Season 1 (2026-07-18 to 2026-10-16, perps up to 10x, daily) [V]
Source: [OAK Research](https://oakresearch.io/en/ai/trading-benchmark), page last modified 2026-10-17. Open-weight labels come from the page; closed labels are mine. The page gives no thinking labels.

| # | Model | Open? | Return | vs BTC (+23.3%) | Sharpe | Max DD | Liquidations | Final equity (±) |
|---|---|---|---|---|---|---|---|---|
| 1 | **GLM-5.3 (Z.ai)** | Open weights | **+29.4%** | **+6.0%** | 1.40 | -15.1% | 0 | $12,936 ± $3,498 |
| – | **Buy & hold BTC** | baseline | **+23.3%** | 0 | **2.39** | -7.2% | 0 | $12,333 |
| 2 | Gemini 4 Argon (Google) | closed | +20.4% | -3.0% | 1.63 | -14.4% | 0.2 | $12,036 ± $652 |
| 3 | Claude Opus 5.5 (Anthropic) | closed | +15.9% | -7.4% | 1.73 | -8.7% | 0 | $11,593 ± $626 |
| 4 | GPT-6.1 Sol (OpenAI) | closed | +15.3% | -8.1% | 1.50 | -12.2% | 0 | $11,525 ± $574 |
| 5 | Grok 4.7 (xAI) | closed | +10.4% | -13.0% | 0.80 | -9.8% | 0 | $11,037 ± $1,647 |
| 6 | MiMo V2.6 Pro (Xiaomi) | Open weights | +8.8% | -14.6% | 0.71 | -13.5% | 0 | $10,875 ± $2,002 |
| 7 | MiniMax M3 | Open weights | +5.6% | -17.7% | 0.91 | -6.5% | 0 | $10,564 ± $460 |
| 8 | Kimi K3 (Moonshot) | Open weights | +2.7% | -20.7% | 0.47 | -23.1% | 0.2 | $10,268 ± $1,613 |
| – | Cash | baseline | 0.0% | -23.3% | 0.00 | 0.0% | 0 | $10,000 |
| 9 | Mistral Large 4 | Open weights | -12.8% | -36.1% | -1.27 | -23.9% | 2 | $8,721 ± $1,291 |
| 10 | Muse Spark 1.3 (Meta) | closed (my label) | -16.5% | -39.9% | -0.65 | -30.9% | 1 | $8,348 ± $1,255 |
| 11 | Qwen3.8 Max (Alibaba) | closed (my label) | -25.7% | -49.1% | -1.55 | -32.1% | 0 | $7,426 ± $1,280 |
| 12 | DeepSeek V4 Pro | Open weights | -62.8% | -86.1% | -1.26 | -67.8% | 1.8 | $3,723 ± $2,665 |

- No model matched BTC's Sharpe (2.39) or its drawdown (-7.2%) except MiniMax M3, whose MDD was -6.5% but whose return was far lower [D]. GLM-5.3's +6.0pp edge comes with ±$3,498 dispersion, which is larger than the edge itself [D].
- Disclosure: OAK Research is an industry crypto research outfit, not peer-reviewed. It is included because it publishes methodology and a full table. The "±" values and the run count are not clearly defined on the page — [OAK Research](https://oakresearch.io/en/ai/trading-benchmark)

#### 2.12 Non-return model scores (context only)
- TraderBench crypto composite [V]: Gemma3-27B 51.7, GPT-5.2 47.4, Kimi-K2.5 46.8, Gemini-3-Pro 46.6, GPT-4o 44.9, GLM-4.7-Flash 33.5, Grok 4.1 Fast 33.2, GPT-OSS-120B 33.1, Qwen3-8B 33.1, Qwen3-32B 32.8, Qwen3-30B-A3B 32.7, GPT-OSS-20B 32.6. Qwen3-32B with thinking shows no meaningful change. The abstract says extended thinking "helps retrieval (+26 points) but has zero impact on trading (+0.3 crypto...)". The paper is internally inconsistent: it says 13 models in one place and 12 in another — [TraderBench](https://arxiv.org/html/2603.00285)
- CryptoBench direct-LLM scores [V] (SR/CR/SP/CP = simple/complex retrieval/prediction): Grok-4 (Web) 54.9/45.1/35.2/28.6; GPT-5 58.8/32.4/6.3/5.9; GPT-OSS-120B 40.5/24.7/11.3/8.9; DeepSeek R1 28.4/15.2/8.6/6.1. The paper calls this a "retrieval-prediction imbalance" — [CryptoBench](https://arxiv.org/html/2512.00417v5)

### Inferences
- Thinking vs non-thinking is almost never controlled. The only explicit reasoning vs non-reasoning comparisons on crypto returns are: o1-mini vs GPT-4/4o/3.5 (FS-Reasoning, 2024), where o1-mini was not systematically better; o1-preview vs GPT-4/4o (InvestorBench, 2023 backtest), where o1-preview was best on BTC but below B&H on ETH; GPT-5 vs GPT-4o vs Claude Sonnet 4.5 (2501.00826, 2025), where GPT-5 had the lowest mean; and the Qwen3-32B thinking ablation (TraderBench), which showed no effect. Together these weakly suggest that reasoning mode does not reliably improve crypto trading returns.
- Open-weight models win often enough that "closed > open" does not hold in crypto. Open-weight winners: DeepSeek-v3.1 (AI-Trader Nov 2025), DeepSeek-V3.2 (LiveMACE Apr-May 2026, pooled), GLM-5.3 (OAK Jul-Oct 2026), DeepSeek-67B (InvestorBench 2023, both coins). Open-weight models also produced the worst blow-ups: DeepSeek V4 Pro -62.8% and Mistral Large 4 with 2 liquidations on OAK. Open-weight results look higher-variance rather than better or worse on average.
- Model size: InvestorBench shows no monotonic size trend. The 8B Llama beat or nearly matched the 70B Llama on both coins, and Qwen-72B BTC (+0.55) was far below Qwen-7B (+19.48).

### Gaps
- There are no Sortino values except in AI-Trader. There are no per-model MDDs in CryptoTrade, FS-Reasoning or Agent4Crypto.
- LiveMACE has no crypto-only split, so its crypto-specific ranking is unknown.
- The FinMMEval teams' LLM backbones are documented only in 13 separate working notes, which I did not read individually except Fin-Analyst. The best BTC team, NLP-DE, has an unidentified model.
- In 2609.34510, the Buy&Hold rows of Tables 2 and 4 are garbled in the HTML extraction. Read the PDF to confirm BTC B&H for 2026-06-04 to 09-21 (30.35% appears to be the BT value).
- GPT-5 and Claude Sonnet 4.5 Sharpe/MDD in 2501.00826 are not tabulated.

---

## Q3. Who won, did anything beat buy-and-hold convincingly, and rising vs falling markets

### Takeaway
No LLM beat buy-and-hold convincingly in a rising crypto market in any source. In rising windows LLM agents mostly under-participate and lag B&H. Typical gaps: -1pp to -77pp in 2023-24 bull backtests, and 11 of 12 models lagging BTC's +23.3% in OAK S1. In falling markets many agents "beat" B&H simply by holding cash or de-risking. Examples: all strategies in Agent4Crypto (Apr-Jul 2026), FS-Reasoning GPT-4o in 2024 bears, and DeepSeek-v3.1 in AI-Trader (Nov 2025). That is a lower-beta effect, not demonstrated skill. Single runs, short windows and leverage make most of the margins statistically weak.

### Cited Findings

**Winner and B&H scorecard (derived [D] from the Q2 tables)**

| Benchmark (window) | Market direction (B&H) | Best model by return | Beat B&H? | # models / cells beating B&H |
|---|---|---|---|---|
| CryptoTrade (2023 bull) | Up: BTC +39.66, ETH +22.59, SOL +176.72 | GPT-4 on ETH +25.72 | Only ETH GPT-4 (+3.1pp) | 1 of 6 cells |
| CryptoTrade (2023 bear) | Down: BTC -15.61, ETH -12.24, SOL -36.08 | GPT-4 on SOL -19.55 | BTC and SOL yes, ETH no | 4 of 6 cells |
| InvestorBench (Apr-Nov 2023) | Up: BTC +21.8, ETH +4.5 | o1-preview BTC +34.06; Qwen2.5-72B ETH +11.98 | BTC: 3 of 13; ETH: 6 of 13 | Only DeepSeek-67B beat both |
| FS-Reasoning (Jan-Mar 2024 bull) | Up ~ +77 to +80% | FS GPT-4 BTC 77.47; FS o1-mini ETH 77.28 / SOL 76.71 | **No** | 0 of 24 |
| FS-Reasoning (May-Jul 2024 bear) | Down -19 to -24% | FS GPT-4o (SOL -14.52) | Mostly yes for FS variants | – |
| Multi-agent portfolio (2025) | Down: BTC -3.36 | GPT-4o Hier.(Skill) +133.52 | Yes, for multi-agent configs; single-agent configs mostly no | 1 run only |
| 2609.34510 replay (2025) | Down: BTC -7.63 | TradingAgents -9.16 | **No LLM method** | 0 |
| AMA live (Aug-Sep 2025) | BTC flat +0.66; ETH up +18.56 | ETH HedgeFundAgent +39.66 (backbone-invariant); BTC TradeAgent-Gemini-2.0-flash +5.02 | Rarely | BTC 2-3 of 24; ETH 1 agent |
| AI-Trader (Nov 1-14 2025) | Down: CD5 -14.30 | DeepSeek-v3.1 -12.18 | Yes, by 2.1pp | 1 of 6 |
| LiveMACE (Apr 13-May 13 2026) | Unknown (no B&H) | DeepSeek-V3.2 +5.77 ≈ GPT-5.4 +5.74 | Unknown | – |
| Agent4Crypto (Apr-Jul 2026) | Down: BTC -15.2, ETH -31.8, XRP -22.4 | Agent4Crypto (GPT-5.4) BTC +6.66 | Yes, all coins | Single backbone |
| FinMMEval BTC (May 11-Jul 4 2026) | Down (participant-reported B&H ~ -23% to -26%) | NLP-DE +9.97 | Probably most teams lost less than B&H; organizers decline to claim it | 18 teams |
| 2609.34510 paper/live (Jun-Sep 2026) | Up (BT B&H window +30.35; Aug 24-Sep 21 window +11.63) | Qwen PT +37.77 | Live Qwen: alpha -28.10 | Negative live alpha |
| OAK S1 (Jul 18-Oct 16 2026) | Up: BTC +23.3 | GLM-5.3 +29.4 | Yes (+6.0pp) but with ± $3.5k dispersion; lower Sharpe 1.40 vs 2.39 | 1 of 12 |

Supporting statements from sources:
- AI-Trader: DeepSeek-v3.1 is the only agent that outperformed the CD5 baseline in crypto — [AI-Trader](https://arxiv.org/html/2512.10971)
- OAK S1 headline: "1 of 12 models beat holding BTC (+23.3%)" — [OAK Research](https://oakresearch.io/en/ai/trading-benchmark)
- AMA: agent architecture outweighs LLM backbone choice — [AMA](https://arxiv.org/html/2510.11695)
- FinMMEval: "positive CR does not establish outperformance of passive market exposure", and no single architecture or model family dominates — [FinMMEval overview](https://ceur-ws.org/Vol-4283/paper186.pdf)
- 2609.34510 documents a backtest-to-live collapse: Qwen alpha went from +15.80 (paper) to -28.10 (live) over 2026-08-24 to 09-21 — [arXiv 2609.34510](https://arxiv.org/html/2609.34510v1)
- The production fleet trading Hyperliquid perps (Jun-Aug 2026) showed no directional edge and trailed a matched retail benchmark (41% vs 50% roundtrip win rate) — [arXiv 2609.05663](https://arxiv.org/abs/2609.05663)

### Inferences
- The regime asymmetry is the most robust pattern across sources. Up-markets mean LLMs lag B&H; down-markets mean LLMs often beat it. This is consistent with LLM agents sitting partly in cash. AI-Trader shows a 44-78% no-trade share for most models [V], and MDDs are usually lower than B&H in AMA BTC rows. Any "beat B&H" claim from a falling-market window, including Agent4Crypto, AI-Trader and FinMMEval, should be read as "lower beta" unless risk-adjusted alpha is shown.
- The only up-market LLM win vs B&H on a live or leakage-controlled benchmark is GLM-5.3 on OAK S1. It came with high run dispersion and a lower Sharpe than BTC. I found no convincing outperformance that holds up on a risk-adjusted basis.
- The InvestorBench and CryptoTrade "wins" are on 2023 data with models trained after it, so contamination is plausible. The 2024-2026 live or post-cutoff results (AMA, AI-Trader, OAK, 2609.34510 live) are uniformly weaker.

### Gaps
- No source reports statistical significance (bootstrap, multiple seeds with CIs) for beating B&H, except OAK's undefined ±.
- I found no rising-market live crypto benchmark with many models other than OAK S1 and AMA ETH.

---

## Q4. Results grouped by time period (for same-month comparison)

### Takeaway
Within any one calendar window, the only same-window, multi-model comparisons are AMA (Aug-Sep 2025), AI-Trader (Nov 1-14 2025), LiveMACE (Apr-May 2026) and OAK S1 (Jul-Oct 2026). Several 2026 windows overlap (Apr-Jul 2026: LiveMACE, Agent4Crypto, FinMMEval, 2609.34510 paper trading). They differ in coins and leverage, but all point to a falling crypto market in roughly May-July 2026 and a rising one in roughly Jul-Oct 2026.

### Cited Findings

| Window | Source | Crypto B&H in window | Model results (return; [V] unless noted) |
|---|---|---|---|
| 2023-04 to 2023-06 (bear) | CryptoTrade | BTC -15.61, ETH -12.24, SOL -36.08 | GPT-4: -11.72 / -13.72 / -19.55; GPT-3.5: -13.71 / -14.40 / -24.08 — [CryptoTrade](https://arxiv.org/html/2407.09546v2) |
| 2023-06 to 2023-08 (sideways) | CryptoTrade | BTC -0.83, ETH -1.91, SOL -3.23 | GPT-4: -4.07 / +0.72 / -2.16; GPT-3.5: -5.08 / -5.02 / -13.05 |
| 2023-04-05 to 2023-11-05 | InvestorBench | BTC +21.82, ETH +4.53 | o1-preview 34.06 / 2.50; GPT-4 22.40 / 1.52; GPT-4o 14.33 / 4.67; DeepSeek-67B 28.31 / 9.48; Qwen2.5-72B 0.55 / 11.98; Llama-3.1-70B 20.44 / -11.89 — [InvestorBench](https://arxiv.org/html/2412.18174) |
| 2023-10-01 to 2023-12-01 (bull) | CryptoTrade | BTC +39.66, ETH +22.59, SOL +176.72 | GPT-4: 26.35 / 25.72 / 99.84; GPT-3.5: 28.47 / 18.91 / 102.45 |
| 2024-01-24 to 2024-03-13 (bull) | FS-Reasoning | BTC +79.63, ETH +78.72, SOL +77.35 | Best: BTC FS GPT-4 77.47; ETH FS o1-mini 77.28; SOL FS o1-mini 76.71 (all < B&H) — [FS-Reasoning](https://arxiv.org/html/2410.12464) |
| 2024-05 to 2024-07 (bear) | FS-Reasoning | BTC -19.15, ETH -23.63, SOL -24.08 | FS GPT-4o: -13.94 / -21.64 / -14.52 |
| 2025 full year | 2501.00826 (weekly, 15 L1s) | BTC hold -3.36, MCap hold -4.54 | GPT-4o mean +17.5 [S]; GPT-5 mean +6.9 [S]; Claude Sonnet 4.5 mean +33.0 [S] — [2501.00826](https://arxiv.org/html/2501.00826v3) |
| 2025 full year | 2609.34510 replay (10x) | BTC -7.63 | DeepSeek -43.30; Qwen -68.62; TradingAgents -9.16 — [2609.34510](https://arxiv.org/html/2609.34510v1) |
| **2025-08-01 to 2025-09-30 (live)** | AMA | BTC +0.66, ETH +18.56 | BTC best TradeAgent/Gemini-2.0-flash +5.02; ETH best HedgeFundAgent +39.66 (all backbones); many Claude rows -6 to -15 on BTC — [AMA](https://arxiv.org/html/2510.11695) |
| 2025-08-01 to 2026-05-10 (offline) | Fin-Analyst | BTC -31.5 | Rule-based BTC (no LLM) +22.8 — [Fin-Analyst](https://arxiv.org/html/2607.12233) |
| **2025-11-01 to 2025-11-14** | AI-Trader (10 coins) | CD5 -14.30 | DeepSeek-v3.1 -12.18; MiniMax-M2 -14.80; Claude-3.7 -15.30; GPT-5 -16.41; Qwen3-Max -16.85; Gemini-2.5-Flash -18.63 — [AI-Trader](https://arxiv.org/html/2512.10971) |
| **2026-04-13 to 2026-05-13 (live)** | LiveMACE (6 crypto + 17 stocks pooled) | not given | DeepSeek-V3.2 +5.77; GPT-5.4 +5.74; Qwen3-Max +4.42; Gemini-3.1-Pro +3.50; Grok-4.20 +3.09 — [LiveMACE](https://arxiv.org/html/2610.09872) |
| 2026-04-13 to 2026-07-20 (backtest) | Agent4Crypto (GPT-5.4) | BTC -15.24, ETH -31.81, XRP -22.37 | Agent4Crypto +6.66 / -4.77 / -2.36; CryptoTrade-GPT-5.4 -5.12 / -16.29 / -16.08 — [Agent4Crypto](https://arxiv.org/html/2611.12269) |
| **2026-05-11 to 2026-07-04 (live)** | FinMMEval BTC, 18 teams | not given by organizers (participant: ~ -23 to -26%) | Range -12.55 to +9.97; median ~ -1.1 [D] — [FinMMEval](https://ceur-ws.org/Vol-4283/paper186.pdf) |
| 2026-06-04 to 2026-09-21 (paper, 2x) | 2609.34510 | BT-window B&H +30.35 (extraction-ambiguous) | Qwen PT +37.77; DeepSeek PT +9.53; FinGPT PT +16.85 — [2609.34510](https://arxiv.org/html/2609.34510v1) |
| 2026-08-24 to 2026-09-21 (live) | 2609.34510 | ~ +11.63 (ambiguous) | Qwen live +3.72, alpha -28.10 |
| **2026-07-18 to 2026-10-16** | OAK S1 (6 perps, ≤10x) | BTC +23.3 | GLM-5.3 +29.4; Gemini 4 Argon +20.4; Claude Opus 5.5 +15.9; GPT-6.1 Sol +15.3; ... DeepSeek V4 Pro -62.8 — [OAK](https://oakresearch.io/en/ai/trading-benchmark) |

### Inferences
- DeepSeek models top three separate same-window comparisons: AI-Trader Nov 2025, LiveMACE Apr-May 2026, and InvestorBench 2023 (both coins). A DeepSeek model is also the worst on OAK S1 (V4 Pro, leveraged perps) and in the 2609.34510 2025 replay. The family-level signal is "behaviour depends on the harness and leverage", not "DeepSeek is good at trading".
- Qwen3-Max appears in AI-Trader (5th of 6) and LiveMACE (3rd of 5, worst hard-rule pass rate 0.613). Qwen3.8 Max was 11th of 12 on OAK. Qwen 3.6 Max Preview was the best paper trader in 2609.34510 but had negative live alpha. Qwen is mid-to-low in every multi-model crypto ranking.
- Frontier closed models (GPT-5.x, Gemini, Claude Opus, Grok) cluster mid-table with moderate drawdowns in OAK S1 and LiveMACE. They neither top the board nor blow up. Their Sharpe values on OAK (1.50-1.73) are below BTC's 2.39.

### Gaps
- I found no multi-model crypto benchmark covering Dec 2025 to Mar 2026, or late Oct to Nov 2026 (OAK Season 2, if any, was not found).
- For the May-Jul 2026 overlap, the BTC B&H comes only from participant papers and differing windows (Agent4Crypto -15.24% for Apr 13-Jun 27; Fin-Analyst ~ -26.3% for May 11-Jun 29). No organizer-published same-window B&H exists for FinMMEval or LiveMACE.
