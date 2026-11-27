# Low-cost LLM "analyst" monitor for a small retail stock account: design brief (as of 23 Nov 2026)

Verification note. The "known facts" in the brief were checked against live Anthropic pages on 2026-11-23 and all hold: Claude Haiku 5.5 is $0.10 / $0.50 per million input / output tokens for prompts up to 100,000 tokens (and $0.50 / $2.50 above that), cache reads $0.01/MTok (0.1x), 5-minute cache writes $0.125/MTok (1.25x), 1-hour cache writes $0.20/MTok (2x), Batch API 50% off ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)); `claude-haiku-5-5` appears in the Batch API's supported-model list ([Batch processing docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing)); Claude Code cloud scheduled tasks have a 1-hour minimum interval ([Claude Code scheduling docs](https://code.claude.com/docs/en/scheduled-tasks)). The 1M context window and several Haiku 5.5 API behaviours (no custom temperature, thinking on by default, refusals) were read from Anthropic's bundled Claude API reference in this session rather than a live page; they are marked where used. All dollar figures in the cost tables are my own arithmetic from the cited list prices.

## 1. How do open-source and published systems put an LLM in a trading or monitoring loop, and what are their real results?

### Takeaway
The well-known open-source projects (TradingAgents, virattt/ai-hedge-fund, FinGPT, FinRobot) are research or teaching frameworks: LLM "analysts" read data and produce a rated proposal, while execution is simulated; none publishes an audited live track record. Where LLMs have actually been run forward on live markets (Alpha Arena, LiveTradeBench, StockBench, practitioner logs), most models lost money or failed to beat buy-and-hold, and winners changed from one season to the next.

### Cited Findings

Open-source frameworks (what the LLM decides vs. what code does)
- TradingAgents: LLM roles are an analyst team (Fundamentals, Sentiment, News, Technical) running in parallel, bullish and bearish researchers who debate, a Trader that sets "the timing and magnitude of trades", a risk-management team, and a Portfolio Manager that "approves/rejects the transaction proposal"; an approved order "will be sent to the simulated exchange and executed" (no real orders). Data comes from SEC EDGAR, Yahoo Finance, Alpha Vantage, FRED, Polymarket, StockTwits and Reddit. The README says it "is designed for research purposes" and "is not intended as financial, investment, or trading advice", and advises that for more repeatable output you "name a non-reasoning model in your config". — [TradingAgents README](https://raw.githubusercontent.com/TauricResearch/TradingAgents/main/README.md)
- TradingAgents' paper results are a backtest only, on three stocks (AAPL, GOOGL, AMZN) over a few months of 2024, with daily decisions; the authors report that it outperformed all their baselines on cumulative return, Sharpe ratio and drawdown, and list live deployment as future work. Search summaries of different paper versions give conflicting windows (January–March 2024 vs. June–November 2024); I did not resolve which is final. — [arXiv 2412.20138](https://arxiv.org/abs/2412.20138v1)
- Community commenters on the paper's Hugging Face page ask whether results were checked with real capital and point out that the model was pretrained on the window it "predicts" (unreviewed user opinions). — [Hugging Face paper page](https://huggingface.co/papers/2412.20138)
- The TradingAgents PyPI package (v0.7.0) ships a backtest harness that scores realised returns and reports Sharpe, hit-rate and drawdown against buy-and-hold, HOLD, SMA and random benchmarks: a tool, not evidence of live performance. — [PyPI tradingagents 0.7.0](https://pypi.org/project/tradingagents/0.7.0/)
- virattt/ai-hedge-fund: "Note: the system does not actually make any trades"; "This project is for educational purposes only and is not intended for real trading or investment"; it has a paper-trading mode with "fake money" where "an approval step shows the exact decision about to execute before anything trades", and a backtest mode that replays a fund "against its benchmark". Supported LLM providers: Anthropic, OpenAI, DeepSeek, Google, xAI, Kimi. Data comes from the paid Financial Datasets API. — [ai-hedge-fund README](https://raw.githubusercontent.com/virattt/ai-hedge-fund/main/README.md)
- FinGPT is a set of fine-tuned open models (for example `fingpt-sentiment_llama2-13b_lora` and `fingpt-forecaster_dow30_llama2-7b_lora`) for sentiment scoring and a stock "Forecaster"; its README tells users to consult a professional before trading. No live results were found. — [FinGPT GitHub](https://github.com/ai4finance-foundation/fingpt); [FinGPT on Hugging Face](https://huggingface.co/FinGPT)
- FinRobot is "an open-source AI agent platform supporting multiple financially specialized AI agents, each powered by LLM", including a Market Forecaster application; the paper reports no live trading. — [FinRobot paper, arXiv 2405.14767](https://arxiv.org/abs/2405.14767v1)
- A practitioner build published on Alpaca's site shows the cleanest split: five LLM research agents (Momentum, Macro, StatArb, Contrarian, Exotic) each return a structured proposal and an LLM critic checks structure against a governance file; a human approves, rejects or revises each proposal; everything else is deterministic Python: data ingestion and indicators, a Risk Guard (10% max single position, 30% max sector, 1.0x leverage, halts at 5% daily / 10% weekly / 15% total drawdown), bracket (OCO) stop-loss and take-profit orders, and a position monitor running pure price checks every 15 minutes. "Risk checks run as deterministic code, unit-tested, with no model in the loop." — [Alpaca Learn: multi-agent AI trading system](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)
- That system's results are paper-only and tiny: $100K paper account, 18 March–5 April, 82 proposals, 26 approved (32%), about 48% win rate on 25 closed trades, per-agent P&L from +$1,046 (Macro, 7 trades) to −$232 (Contrarian, 8 trades); the author calls them limited simulated results with no slippage or liquidity modelling. — [Alpaca Learn: multi-agent AI trading system](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)

Forward-tested and live results
- Alpha Arena Season 1 (Nof1, crypto perpetuals on Hyperliquid, $10,000 real money per model, ended early November 2025, about 17 days): final balances reported as Qwen3 Max $12,231, DeepSeek $10,489, Claude Sonnet 4.5 $5,799, Gemini 2.5 Pro $5,445, Grok $4,208, GPT-5 $4,126, so two of six finished above their start. — [ForkLog](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/); a Benzinga headline gives GPT's loss as 63%, so the losers' exact figures differ by source — [Benzinga](https://fr.benzinga.com/quote/cryptocurrency/25/11/48651974/chatgpt-lost-63-trying-to-trade-crypto-but-one-china-ai-made-a-healthy-profit)
- During Season 1, Gemini 2.5 Pro reportedly traded frequently and erratically, flipping between bearish and bullish at a loss. — [Decrypt](https://decrypt.co/345006/ai-crypto-trading-showdown-deepseek-grok-winning-gemini-implodes)
- Alpha Arena Season 1.5 (US stocks, about two weeks from late November 2025, four modes: New Baseline, Monk Mode, Situational Awareness, Max Leverage): the winner, an initially anonymous model later named as Grok 4.20, averaged about +12% and was profitable in all four modes; as of 8 December 2025 it was the only profitable model. — [ForkLog](https://forklog.com/en/ai-model-grok-4-2-triumphs-in-trading-tournament/)
- Third-party write-ups of Season 1.5 report 6 of 32 entries positive, returns from +34.59% to −96.15% within one mode, and that Season 1's winner (Qwen 3 Max) lost in all four Season 1.5 competitions; one notes no published prompts, leverage limits, buy-and-hold benchmark or significance test. I did not verify these against Nof1's own leaderboard. — [aihola](https://aihola.com/article/grok-wins-alpha-arena-trading); [OneDayAdvisor](https://www.onedayadvisor.com/2025/12/nof1ai-alpha-arena-review-season-15.html?m=0)
- LiveTradeBench (UIUC, November 2025) is a live environment, not a backtest: it streams real-time prices and news to avoid "offline backtesting and information leakage", and ran 21 LLMs for 50 days on US stocks and Polymarket. Its headline finding: "high LMArena scores do not imply superior trading outcomes". — [arXiv 2511.03628](https://arxiv.org/abs/2511.03628)
- StockBench (October 2025, revised March 2026): agents get daily prices, fundamentals and news and make buy/sell/hold decisions over multi-month periods; "most models struggle to outperform the simple buy-and-hold baseline", though some show higher returns and better risk management. — [arXiv 2510.02209](https://arxiv.org/abs/2510.02209)
- AI-Trader (HKU) is a fully automated live benchmark over US stocks, A-shares and crypto; it reports excess returns come more readily in the liquid US market. I did not read its buy-and-hold figures. — [arXiv 2512.10971](https://www.arxiv.org/pdf/2512.10971)
- FINSABER (accepted to KDD 2026 per the arXiv listing): re-testing published LLM timing strategies over 2004–2024 and 100+ symbols, "previously reported LLM advantages deteriorate significantly"; LLM strategies were too conservative in bull markets and took disproportionate losses in bear markets. — [arXiv 2505.07078](https://arxiv.org/abs/2505.07078v5)
- A May 2026 news article summarised the public AI investing contests as "unflattering" for the bots and quoted an expert saying most public experiments are too short and too noisy for firm conclusions. — [ThinkAdvisor](https://www.thinkadvisor.com/2026/05/06/why-ai-bots-arent-ready-to-replace-your-fund-manager/)
- A practitioner's 26-day log of an AI-agent-run bot on Hyperliquid ($100 account, crypto): trading P&L was −$7.71 over 14 trades; the account's gain came from unrelated fee income. A 30-minute cron check "missed all 32 signals in one week" and was replaced by a WebSocket monitor; four code bugs turned a stop-loss into a plain limit order; seven review rounds found 19 bugs; tests passed only because mocks matched the code's assumptions. — [DEV Community post](https://dev.to/xqliu/26-days-of-ai-trading-14-trades-3-system-rewrites-and-one-expensive-lesson-4ai9)

Strongest academic evidence for a narrow LLM job (news classification)
- Lopez-Lira and Tang ask an LLM to judge news headlines dated after the model's knowledge cutoff. GPT-4 scores capture the initial market reaction (about 90% portfolio-day hit rate for that non-tradable first move) and also predict the later drift, more strongly for small stocks and negative news; ability rises with model size; and "strategy returns decline as LLM adoption rises". — [arXiv 2304.07619 (v6, October 2025)](https://arxiv.org/abs/2304.07619)

### Inferences
- The recurring division of labour is: LLM reads text and returns a labelled opinion; code fetches data, computes every number, sizes positions, enforces limits and places orders. No reviewed project lets the LLM send orders directly to a real broker by default.
- The only use with peer-level evidence is classifying fresh news text, at a daily horizon, with the edge concentrated in small stocks and shrinking as adoption rises. I found no evidence that showing a cheap LLM price bars every few minutes adds anything a rule cannot do.
- Multi-agent frameworks multiply calls per decision (four analysts, two debaters, trader, risk team, manager), so they are a poor fit for a few-minute, low-cost loop; a single structured classification call is the cheap pattern.
- Contest leaderboards are weak evidence either way: two weeks, one run per model, and the Season 1 winner lost in every Season 1.5 mode.

### Gaps
- OpenBB's agent tooling: no usable source surfaced; not covered.
- No audited, long-running live track record was found for any open-source LLM trading system.
- Nof1's official leaderboard was not fetched; Alpha Arena figures come from press and third-party reviews that disagree on details. A widely repeated quote from Nof1's founder that it is not yet feasible to hand money to an LLM to trade on its own appeared in search summaries but I could not locate the primary article.
- A "90-day AI trading experiment" retrospective (reported in a search snippet as a $550 paper loss, 50% win rate, 60+ lessons) returned HTTP 404 when fetched, so it is unverified.

## 2. What is a sound architecture for a small account, what do practitioners recommend, and what goes wrong?

### Takeaway
The pattern that practitioners converge on is "code does everything measurable, the LLM only labels text": deterministic polling, triggers, numbers, risk limits and order logic, with the LLM returning a small schema-checked JSON verdict that can at most filter or veto a rule-based signal. Reported failures are mostly plumbing (missed polls, broken stops, mock-only tests, ignored fees) and over-trading, not exotic AI problems.

### Cited Findings
- Deterministic risk layer with no model in it (position cap, sector cap, leverage cap, drawdown halts), broker-side bracket orders for stops, and a price-only position monitor every 15 minutes; LLM agents return structured proposals; a human gate approves each one. — [Alpaca Learn: multi-agent AI trading system](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)
- Timer-only polling loses events: a 30-minute cron missed all 32 signals in a week; the fix was an event-driven WebSocket monitor. — [DEV Community post](https://dev.to/xqliu/26-days-of-ai-trading-14-trades-3-system-rewrites-and-one-expensive-lesson-4ai9)
- Other practitioner builds surfaced by search follow the same shape: a deterministic "turbulence" check that runs before the LLM and can force a sell, and an LLM that returns only APPROVE/REJECT plus a size factor after code has checked balance, daily loss and a circuit breaker. These come from search snippets; the posts were not read in full and I could not confirm which post made which statement. Candidate sources: — [DEV Community post](https://dev.to/nulllimit/we-built-an-ai-trading-bot-in-2-weeks-heres-what-actually-happened-3cf5); [Medium post](https://medium.com/@kojott/teaching-an-ai-to-trade-system-prompt-engineering-and-performance-monitoring-9d55258cca06); [CEUR workshop paper](https://ceur-ws.org/Vol-4283/paper201.pdf)
- Free push inputs exist, so the "event" half needs no polling of the LLM: Alpaca streams news over WebSocket at `wss://stream.data.alpaca.markets/v1beta1/news`. — [Alpaca docs: real-time news](https://docs.alpaca.markets/docs/streaming-real-time-news)
- Alpaca's free Basic data plan gives real-time IEX quotes, 200 historical API calls per minute and 30 WebSocket symbols, enough for code to poll a small watchlist every minute at no cost. — [Alpaca docs: Market Data API](https://docs.alpaca.markets/docs/about-market-data-api)
- Structured output is a first-class API feature (`output_config.format` with schema enforcement), so the JSON verdict can be constrained rather than parsed from prose. — [Anthropic structured outputs docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) (feature described in Anthropic's bundled API reference; live page not fetched)
- Claude Haiku 5.5 rejects non-default `temperature`, `top_p` and `top_k`; Anthropic's guidance for classification is to remove `temperature=0` and "constrain the output with structured outputs or an enum-valued tool". Thinking is on by default, counts toward `max_tokens`, and can be reduced with `output_config.effort: "low"`. — [Anthropic migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) (read via Anthropic's bundled API reference)
- Haiku 5.5 on the entry (Start) tier allows 4,000 requests, 2,000,000 input tokens and 400,000 output tokens per minute, so one call every 1–15 minutes is nowhere near a rate limit. — [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits)
- LLM strategies in long backtests were too cautious in rising markets and had weak risk control in falling ones, an argument for keeping risk control in code. — [arXiv 2505.07078](https://arxiv.org/abs/2505.07078v5)
- Hidden cost and realism problems reported by practitioners: "Any backtest without real transaction costs is fiction" (fees cut one backtest from about +94% to +35%); "100% coverage means nothing if your mocks don't match reality". — [DEV Community post](https://dev.to/xqliu/26-days-of-ai-trading-14-trades-3-system-rewrites-and-one-expensive-lesson-4ai9)
- A live Polymarket bot write-up reports a clear gap between paper-traded and live-executed results (4 wins / 11 losses, −$15.47 in its first live session) and blames backtest overfitting (search-snippet level). — [Medium post](https://medium.com/@gwrx2005/ai-augmented-arbitrage-in-short-duration-prediction-markets-live-trading-analysis-of-polymarkets-8ce1b8c5f362)

### Inferences
Proposed pipeline (my synthesis, not a published standard):
1. Poller (code, free): 1-minute bars and quotes for up to 30 symbols over Alpaca's free WebSocket; keep rolling indicators in memory.
2. Triggers (code): a slow timer (for example every 15 minutes in regular hours) plus events: move beyond k x ATR, volume spike, new watchlist headline, new 8-K on EDGAR, earnings date, scheduled macro release. De-duplicate and rate-limit triggers.
3. Context builder (code): compute every number in Python and pass it as fields; put stable instructions and schema first (cache-friendly), then fresh data; wrap headline text as untrusted quoted data with an ID.
4. One LLM call (Haiku 5.5, low effort, structured output), for example: `event_type` (enum), `direction` (up / down / none), `confidence` (0–1), `horizon` (enum), `headline_ids` used, `reason` (short). The LLM is never asked for prices, sizes or orders.
5. Validator (code): schema and enum check; reject if it cites an unknown headline ID or the call is stale; on any failure treat the verdict as "no opinion".
6. Rule gate (code): the rule-based bot's own signal must already want the trade; the LLM can only confirm, down-weight or veto. Then position caps, max trades per day, daily-loss halt, market-hours check, limit orders only.
7. Paper broker (Alpaca paper account), then the log.
8. Log everything per call: timestamp, trigger, input snapshot, prompt hash, model ID, raw output, tokens, cost, latency, the rule signal, and the action with and without the LLM.
- "Filter, not driver" also makes the system testable: the bot can run in shadow mode where the LLM verdict is logged but not acted on (see section 8).
- For a $1,000 account the human approval gate used in the Alpaca example is cheap insurance during the paper phase.

### Gaps
- There is no authoritative standard for LLM-in-the-loop trading architecture; the practitioner sources are individual blog posts with small samples.
- I found no published measurement of how often cheap models return schema-invalid or self-contradictory verdicts in this kind of loop.

## 3. Worked cost model at Claude Haiku 5.5 prices, and comparison with other cheap models

### Takeaway
At Haiku 5.5 list prices a light call (3,000 in + 300 out) costs $0.00045 and a heavy one (20,000 in + 800 out) $0.0024, so a sensible schedule costs cents to a few dollars a month; only "heavy call every minute around the clock" becomes material ($105/month, about $1,260/year, more than the whole account). Prompt caching saves roughly 40% at 1- and 5-minute cadence but costs slightly more than no caching at 15-minute cadence unless the 1-hour cache is used.

### Cited Findings
- Prices used: Haiku 5.5 input $0.10/MTok, output $0.50/MTok, 5-minute cache write $0.125/MTok, 1-hour cache write $0.20/MTok, cache read $0.01/MTok, for prompts up to 100,000 tokens; above that every rate is 5x ($0.50 / $2.50 / $0.05 read) and the whole request is repriced. — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Per-call cost (computed): light = 3,000 x $0.10/M + 300 x $0.50/M = $0.00045. Heavy = 20,000 x $0.10/M + 800 x $0.50/M = $0.0024. With a warm cache, assuming a 2,000-token stable prefix on the light call and 10,000 on the heavy call: $0.00027 and $0.0015 (40% and 37.5% lower). — prices from [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)

Light call (3,000 in + 300 out). Month = 30.42 days for 24/7 and 21 trading days otherwise; year = 365 or 252 days.

| Schedule | Interval | Calls/day | Uncached $/day | $/month | $/year | Warm-cache $/day | $/month | $/year |
|---|---|---|---|---|---|---|---|---|
| (a) 24/7 | 1 min | 1,440 | 0.648 | 19.71 | 236.52 | 0.389 | 11.83 | 141.91 |
| (a) 24/7 | 5 min | 288 | 0.130 | 3.94 | 47.30 | 0.078 | 2.37 | 28.38 |
| (a) 24/7 | 15 min | 96 | 0.043 | 1.31 | 15.77 | 0.026 | 0.79 | 9.46 |
| (b) regular hours, 6.5 h | 1 min | 390 | 0.176 | 3.69 | 44.23 | 0.105 | 2.21 | 26.54 |
| (b) regular hours | 5 min | 78 | 0.035 | 0.74 | 8.85 | 0.021 | 0.44 | 5.31 |
| (b) regular hours | 15 min | 26 | 0.012 | 0.25 | 2.95 | 0.007 | 0.15 | 1.77 |
| (c) 04:00–20:00 ET, 16 h | 1 min | 960 | 0.432 | 9.07 | 108.86 | 0.259 | 5.44 | 65.32 |
| (c) 04:00–20:00 ET | 5 min | 192 | 0.086 | 1.81 | 21.77 | 0.052 | 1.09 | 13.06 |
| (c) 04:00–20:00 ET | 15 min | 64 | 0.029 | 0.60 | 7.26 | 0.017 | 0.36 | 4.35 |

Heavy call (20,000 in + 800 out, news included).

| Schedule | Interval | Calls/day | Uncached $/day | $/month | $/year | Warm-cache $/day | $/month | $/year |
|---|---|---|---|---|---|---|---|---|
| (a) 24/7 | 1 min | 1,440 | 3.456 | 105.12 | 1,261.44 | 2.160 | 65.70 | 788.40 |
| (a) 24/7 | 5 min | 288 | 0.691 | 21.02 | 252.29 | 0.432 | 13.14 | 157.68 |
| (a) 24/7 | 15 min | 96 | 0.230 | 7.01 | 84.10 | 0.144 | 4.38 | 52.56 |
| (b) regular hours, 6.5 h | 1 min | 390 | 0.936 | 19.66 | 235.87 | 0.585 | 12.28 | 147.42 |
| (b) regular hours | 5 min | 78 | 0.187 | 3.93 | 47.17 | 0.117 | 2.46 | 29.48 |
| (b) regular hours | 15 min | 26 | 0.062 | 1.31 | 15.72 | 0.039 | 0.82 | 9.83 |
| (c) 04:00–20:00 ET, 16 h | 1 min | 960 | 2.304 | 48.38 | 580.61 | 1.440 | 30.24 | 362.88 |
| (c) 04:00–20:00 ET | 5 min | 192 | 0.461 | 9.68 | 116.12 | 0.288 | 6.05 | 72.58 |
| (c) 04:00–20:00 ET | 15 min | 64 | 0.154 | 3.23 | 38.71 | 0.096 | 2.02 | 24.19 |

Both tables are computed from the list prices at [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing); the pre/post-market window (04:00–20:00 ET) follows the session times in section 5.

Caching rules that change the tables
- Default cache lifetime is 5 minutes; a 1-hour option costs a 2x write; a cache read "also refreshes" the entry. Caching pays back after one read on the 5-minute cache and after two reads on the 1-hour cache. — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- A call made exactly five minutes after the previous one can arrive after a 5-minute cache has expired; Claude Code's own scheduler starts 5-minute jobs 15 seconds early for that reason. — [Claude Code scheduling docs](https://code.claude.com/docs/en/scheduled-tasks)
- Computed consequence at 15-minute cadence: with the default 5-minute cache every call pays the 1.25x write and never gets a read, so the light call costs $0.00050 and the heavy call $0.00265, about 10% more than not caching at all. With the 1-hour cache, one 2x write per session start ($0.00065 light, $0.0034 heavy) is followed by reads that keep it alive, giving the warm-cache figures above. — prices from [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- The minimum cacheable prefix on Haiku 5.5 is 512 tokens; shorter prefixes silently do not cache. — [Anthropic prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) (value read from Anthropic's bundled API reference, which itself says to check the docs before relying on it)
- Cache reads do not count toward the input-tokens-per-minute rate limit. — [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits)

Other cost facts
- Haiku 5.5 thinks by default and thinking tokens are billed as output and count toward `max_tokens`; current Claude models also produce roughly 30% more tokens for the same text than older ones, so measure real token counts rather than estimating from word counts. — [Anthropic migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) (via bundled reference); [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Batch API: 50% off (Haiku 5.5 $0.05 / $0.25 per MTok), but asynchronous: "most batches completing within 1 hour", results guaranteed only within 24 hours, after which unprocessed requests expire. — [Batch processing docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing); [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Entry (Start) tier has a $500 monthly spend cap, and you can set a lower cap of your own in the Console; at your own cap, requests fail with HTTP 400 `invalid_request_error`. — [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits)

Other cheap models, official list prices per million tokens (input / cached input / output)
- OpenAI: gpt-5-nano $0.05 / $0.005 / $0.40; gpt-5.4-nano $0.20 / $0.02 / $1.25; gpt-5-mini $0.25 / $0.025 / $2.00; gpt-4o-mini $0.15 / $0.075 / $0.60. — [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- Google: gemini-2.5-flash-lite $0.10 in / $0.40 out (cache $0.01); gemini-3.1-flash-lite $0.25 / $1.50; gemini-3.5-flash-lite $0.30 / $2.50; each also shows a "free of charge" tier whose rate limits the page does not state. — [Gemini API pricing](https://aistudio.google.com/docs/pricing)
- DeepSeek: third-party comparison sites quote about $0.14 / $0.28 or $0.28 / $0.42 depending on model; not checked against DeepSeek's own page. — [Spheron comparison](https://www.spheron.network/blog/llm-api-pricing-comparison-gpt-claude-gemini-deepseek-2026/)
- Other Claude models for scale: Haiku 4.5 $1 / $5; Sonnet 5.5 $2 / $10; Opus 5.5 $4 / $20. — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)

Same workload on other models (computed, uncached list prices, same token counts assumed):

| Model (in / out per MTok) | Light call | Heavy call | 5-min 24/7 light $/mo | 5-min 24/7 heavy $/mo | 5-min regular hours light $/mo | heavy $/mo |
|---|---|---|---|---|---|---|
| GPT-5 nano ($0.05 / $0.40) | $0.00027 | $0.00132 | 2.37 | 11.56 | 0.44 | 2.16 |
| Gemini 2.5 Flash-Lite ($0.10 / $0.40) | $0.00042 | $0.00232 | 3.68 | 20.32 | 0.69 | 3.80 |
| Claude Haiku 5.5 ($0.10 / $0.50) | $0.00045 | $0.00240 | 3.94 | 21.02 | 0.74 | 3.93 |
| gpt-5.4-nano ($0.20 / $1.25) | $0.00098 | $0.00500 | 8.54 | 43.80 | 1.60 | 8.19 |
| Gemini 3.1 Flash-Lite ($0.25 / $1.50) | $0.00120 | $0.00620 | 10.51 | 54.31 | 1.97 | 10.16 |
| gpt-5-mini ($0.25 / $2.00) | $0.00135 | $0.00660 | 11.83 | 57.82 | 2.21 | 10.81 |
| Gemini 3.5 Flash-Lite ($0.30 / $2.50) | $0.00165 | $0.00800 | 14.45 | 70.08 | 2.70 | 13.10 |
| Claude Haiku 4.5 ($1 / $5) | $0.00450 | $0.02400 | 39.42 | 210.24 | 7.37 | 39.31 |
| Claude Sonnet 5.5 ($2 / $10) | $0.00900 | $0.04800 | 78.84 | 420.48 | 14.74 | 78.62 |
| Claude Opus 5.5 ($4 / $20) | $0.01800 | $0.09600 | 157.68 | 840.96 | 29.48 | 157.25 |

Prices from [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing), [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) and [Gemini API pricing](https://aistudio.google.com/docs/pricing).

### Inferences
- Against a $1,000 account, LLM cost is a return hurdle: 5-minute 24/7 light calls are about $47/year (4.7% of the account); 15-minute regular-hours light calls are about $3/year (0.3%); heavy calls every minute around the clock would cost 126% of the account per year.
- A hybrid schedule is cheapest per unit of information: 26 light timer calls (every 15 minutes in regular hours) plus about 23 heavy event or digest calls per trading day comes to roughly $0.067/day, $1.40/month, $17/year uncached.
- At this scale hosting, not the model, is the larger bill: a small paid VPS at about €5.49/month (section 6) costs more than every 5-minute schedule in the light table.
- Cheap models differ by at most about 2x among the cheapest three (GPT-5 nano, Gemini 2.5 Flash-Lite, Haiku 5.5), which is cents per month here; model choice should rest on measured verdict quality, not price.
- Keep prompts well under 100,000 tokens: a 150,000-token Haiku 5.5 prompt costs about $0.077 per call versus about $0.010 at 99,000 tokens.
- The Batch API fits nightly jobs (re-scoring the day's log, an overnight news digest, evaluation runs) at $0.000225 per light call, but not a few-minute loop.

### Gaps
- Token sizes are assumptions; real prompts should be measured with the token-counting endpoint. Thinking tokens could raise output above 300 / 800 (doubling output adds $0.00015 to the light call and $0.0004 to the heavy call).
- Competitor token counts for the same text differ by tokenizer, and reasoning-token behaviour differs by model; the comparison table holds token counts equal, which is only approximate.
- Gemini free-tier rate limits and data-use terms, and DeepSeek's official prices, were not verified.

## 4. Free or cheap inputs: news, filings and calendars, with limits and licence terms

### Takeaway
A small bot can get prices, a push news stream and all SEC filings for free: Alpaca (IEX quotes plus Benzinga-sourced news over WebSocket) and SEC EDGAR (no key, 10 requests per second) cover most needs. Finnhub and Massive (formerly Polygon) free tiers are usable but tightly rate-limited, and their free news coverage and licence terms could not be confirmed.

### Cited Findings
- Alpaca Basic (free) plan: real-time equities coverage from IEX only, 200 historical API calls per minute, 30 WebSocket symbols, and a restriction on the most recent 15 minutes of historical (all-exchange) data; Algo Trader Plus is $99/month for all US exchanges, 10,000 calls per minute and unlimited symbols. — [Alpaca docs: Market Data API](https://docs.alpaca.markets/docs/about-market-data-api)
- Alpaca's general API throttle is 200 requests per minute per account. — [Alpaca support](https://alpaca.markets/support/usage-limit-api-calls)
- Alpaca news is "provided directly by Benzinga", available by REST and by WebSocket stream; at launch (2022) it was free with 200 calls per minute on free plans, with a warning that pricing or limits might change after beta; Alpaca said real-time streaming carries 600–900 articles or headlines a day. — [Alpaca news launch post](https://alpaca.markets/blog/introducing-news-api-for-real-time-fiancial-news); [Alpaca docs: real-time news](https://docs.alpaca.markets/docs/streaming-real-time-news)
- Alpaca lists news as included with its Trading API, and lists fundamentals, corporate filings, economic announcements and sentiment indicators as "coming soon". — [Alpaca data page](https://alpaca.markets/data)
- Finnhub's pricing page lists 60 API calls per minute on the free tier (paid tiers 300–900 per minute); a third-party review says the free tier is non-commercial. — [Finnhub pricing](https://finnhub.io/pricing); [DEV Community comparison](https://dev.to/nexgendata/best-free-stock-market-apis-and-data-tools-in-2026-a-developers-honest-comparison-1926)
- Massive (Polygon.io renamed on 30 October 2025): the free Basic plan is reported as 5 API calls per minute with end-of-day and 15-minute-delayed data; Massive's own comparison page (vendor marketing) says its free plan includes daily and minute bars and that Finnhub's free plan returns 403 on stock candles. — [Massive vs Finnhub](https://massive.com/compare/massive-vs-finnhub); [DEV Community comparison](https://dev.to/nexgendata/best-free-stock-market-apis-and-data-tools-in-2026-a-developers-honest-comparison-1926)
- SEC EDGAR: free, no API key; "no more than 10 requests per second" per user, and the SEC may block IPs that exceed it; automated tools must declare a User-Agent (sample format: company name plus contact email). — [SEC developer resources](https://www.sec.gov/about/developer-resources); [SEC: accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- EDGAR offers JSON APIs on data.sec.gov (submissions by company, extracted XBRL data), RSS feeds for Company Search and Latest Filings, and daily and quarterly index files; indexes for the current day update nightly from about 10:00 p.m. ET. — [SEC developer resources](https://www.sec.gov/about/developer-resources); [SEC: accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
- EDGAR full-text search covers "all EDGAR filings submitted electronically since 2001" including exhibits, filterable by form type and date, with exact phrases, OR, NOT and NEAR() operators; natural-language queries are not supported. — [SEC full-text search FAQ](https://www.sec.gov/edgar/search/efts-faq.html)
- FRED (macro data): free key, about 120 requests per minute per key according to several third-party guides; secondary daily caps are quoted inconsistently and were not confirmed on the official site. — [FRED rate-limit profile](https://apis.io/rate-limits/fred/fred-rate-limits/); [DEV Community guide](https://dev.to/pickuma/fred-api-guide-using-federal-reserve-economic-data-in-your-python-projects-4e2m)
- As a worked example of a free stack, TradingAgents uses SEC EDGAR (no key), Yahoo Finance, Alpha Vantage, FRED, and StockTwits/Reddit for social sentiment. — [TradingAgents README](https://raw.githubusercontent.com/TauricResearch/TradingAgents/main/README.md)

### Inferences
- Minimum viable free feed set: Alpaca WebSocket (prices for up to 30 symbols, plus news) as the push source, EDGAR Latest Filings RSS or per-company submissions JSON polled every minute or so for 8-Ks (well under 10 requests per second), and a hand-maintained earnings and macro calendar.
- IEX-only quotes are a single venue; fine for paper-testing a few-minute analyst, but volume and exact prints will differ from the consolidated tape.
- Headline-only feeds keep prompts small (the light-call budget); full article bodies and filings are what push a call into the heavy budget.

### Gaps
- Current Alpaca news rate limit and redistribution terms for the Benzinga content were not found on a current page (the 200 per minute figure dates from the 2022 launch).
- Whether Finnhub's free tier still includes company news, earnings calendar and economic calendar is unresolved: sources conflict and Finnhub's docs pages did not render for the fetch tool.
- Whether Massive's free plan includes its news endpoint was not confirmed.
- Press-release RSS feeds (GlobeNewswire, PR Newswire, Business Wire), free earnings calendars and official economic-release calendars were not researched to a citable standard.
- Licence terms were only verified at the level stated above; none of the vendors' full terms of service were read.

## 5. What "24/7" means for stocks, and what is worth analysing when the market is closed

### Takeaway
US stocks are not a 24/7 market: there is the 6.5-hour regular session, pre-market and after-hours trading, and an overnight session that makes it roughly 24 hours on five days, with nothing at weekends. From 6 December 2026 Nasdaq and NYSE Arca themselves move to 23 hours a day, five days a week, but overnight volume is still under 1% of the total and overnight orders are limit-only.

### Cited Findings
- Alpaca's Trading API supports 24/5 trading from 8:00 p.m. ET Sunday to 8:00 p.m. ET Friday; the overnight session is 8:00 p.m.–4:00 a.m. ET; API accounts are enabled by default; overnight supports limit orders only, with DAY or GTC time-in-force and `extended_hours` set to true (orders without it queue for the next session); fractional shares are supported; paper accounts can be used to test it. — [Alpaca docs: 24/5 trading](https://docs.alpaca.markets/docs/245-trading); [Alpaca tutorial](https://alpaca.markets/learn/how-to-trade-us-stocks-24_5-overnight-with-python-and-alpaca)
- Alpaca's overnight market data comes from the Blue Ocean ATS (BOATS) feed or an "Overnight" feed depending on the market-data plan. — [Alpaca docs: 24/5 trading](https://docs.alpaca.markets/docs/245-trading)
- "Beginning December 6, 2026, both the Nasdaq Stock Market and NYSE Arca are expected to extend trading hours to 23 hours per day, five days per week", adding an overnight session Sunday–Thursday 9 p.m.–4 a.m. ET and merging today's pre-market, regular and post-market sessions into one running 9 p.m. Sunday to 8 p.m. Friday; only exchange-member broker-dealers trade directly, so retail investors go through a member firm. — [Harvard Law School Forum on Corporate Governance, 21 Oct 2026](https://corpgov.law.harvard.edu/2026/10/21/nyse-arca-and-nasdaq-to-launch-extended-trading-what-companies-should-consider/)
- SEC approvals of overnight sessions: Nasdaq 10 April 2026, NYSE Arca 21 May 2026, Cboe EDGX 29 May 2026, MEMX 9 September 2026; the consolidated tapes, exchanges and FINRA trade reporting go live on the 23/5 schedule on 6 December 2026. Before that, overnight trading ran off-exchange on venues such as Blue Ocean ATS. In August 2026 overnight trading was about 0.9% of US share volume, up 359% from a year earlier. — [Databento: 23/5 trading in US equities](https://databento.com/blog/us-equities-overnight-trading)
- Off-hours orders are limit orders, not market orders, and that is not expected to change under the exchange expansions. — [Kiplinger](https://www.kiplinger.com/investing/well-soon-be-able-to-buy-and-sell-stocks-24-7-but-should-we)
- Broker overnight offerings can be restricted to large names: Schwab's 24/5 list covers S&P 500, Nasdaq-100 and Dow 30 stocks plus more than 600 ETFs. — [Schwab](https://international.schwab.com/story/how-does-extended-hours-trading-work)
- EDGAR filings that begin submission after 5:30 p.m. ET are generally disseminated the next business day, so the official filing flow mostly stops overnight. — [SEC: accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)

### Inferences
- "24/7 every few minutes" is not a good fit for stocks: for about 16 hours a weekday and all weekend there is either no trading or a thin, limit-only market. A sensible schedule is frequent calls in regular hours, sparse or event-only calls in pre/post-market, and one or two digest calls overnight and at weekends.
- Useful closed-market work for the analyst: summarising after-close and pre-open company news for the watchlist, flagging tomorrow's scheduled events, and scoring the day's logged calls (which can use the half-price Batch API).
- With under 1% of volume overnight, paper fills there will be especially unrealistic; treating overnight as "analyse only, do not trade" is the conservative default.
- The 6 December 2026 switch changes session labels and tape hours within two weeks of this brief; code that hard-codes 04:00–20:00 ET session boundaries should read the broker's calendar and clock instead.

### Gaps
- Whether Alpaca's free (IEX) plan includes any overnight quotes was not resolved from the docs.
- Index futures hours and their use as an overnight signal were not researched to a citable source.
- No source was gathered on the share of earnings releases that occur outside regular hours.
- How retail brokers, including Alpaca, will expose the new exchange overnight sessions after 6 December 2026 was not found.

## 6. Where to run an always-on loop, and how to keep it reliable

### Takeaway
An every-few-minutes analyst cannot run on Claude Code cloud scheduled tasks (1-hour minimum) and should not run on GitHub Actions cron (5-minute minimum, delays and silently dropped runs); it needs a small always-on Python process on a cheap VPS, a free-tier cloud VM or a home machine, with a heartbeat monitor so silent death is noticed.

### Cited Findings
- Claude Code scheduling options: cloud tasks have a minimum interval of 1 hour and run without your machine; Desktop tasks allow 1 minute when Claude sets them (1 hour in the forms) but need your machine on; `/loop` allows 1 minute but is session-scoped, only fires while Claude Code is running and idle, does not catch up missed runs, and recurring tasks expire after 7 days. — [Claude Code scheduling docs](https://code.claude.com/docs/en/scheduled-tasks)
- GitHub Actions: "The shortest interval you can run scheduled workflows is once every 5 minutes"; the schedule event "can be delayed during periods of high loads", some queued jobs may be dropped under heavy load, runs happen only on the default branch, and "in a public repository, scheduled workflows are automatically disabled when no repository activity has occurred in 60 days". — [GitHub Actions docs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- Practitioner reports put typical GitHub cron delays at 5–30 minutes, with dropped runs producing no failure signal. — [HackerNoon](https://hackernoon.com/your-github-actions-cron-job-can-disappear-without-failing); [DEV Community](https://dev.to/ksivamuthu/github-actions-scheduled-workflows-understanding-the-limitations-and-possible-solutions-5hm5)
- Hetzner Cloud lists shared-vCPU servers from €5.49/month excluding VAT (Regular Performance line); its Cost-Optimized line (from €5.99/month) is shown as "currently not available". — [Hetzner Cloud](https://www.hetzner.com/cloud/)
- Third-party trackers say Hetzner raised cloud prices during 2026 (older articles quote €3.79–4.35/month for 2 vCPU / 4 GB) and has carried a limited-availability notice since 26 June 2026. — [Better Stack review](https://betterstack.com/community/guides/web-servers/hetzner-cloud-review/); [Findstack price tracker](https://findstack.com/resources/vps-price-tracker)
- Google Cloud free tier: one non-preemptible e2-micro VM per month in us-west1, us-central1 or us-east1, 30 GB-months of standard disk and 1 GB of outbound transfer per month. — [Google Cloud free tier](https://docs.cloud.google.com/free/docs/free-cloud-features)
- Oracle Cloud Always Free ARM instances: older guides cite 4 OCPU / 24 GB; one benchmark article says the allowance was halved to 2 OCPU / 12 GB around 10 June 2026 without announcement, and a developer guide says provisioning can take weeks of retries and idle free instances have been reclaimed (anecdotal, not confirmed by Oracle). — [Bitdoze](https://www.bitdoze.com/hetzner-oracle-arm-performance/); [DeployWise](https://deploywise.dev/blog/cheap-vps-for-developers)
- Heartbeat monitoring: Healthchecks.io's free Hobbyist plan monitors up to 20 jobs with 100 log entries each; paid plans start at $5/month. — [Healthchecks.io pricing](https://healthchecks.io/pricing/)
- The Anthropic Python SDK retries connection errors and HTTP 408, 409, 429 and 5xx responses twice by default with backoff, and has a 10-minute default timeout that can be shortened per client or per request. — [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (behaviour as described in Anthropic's bundled API reference)
- A fixed-interval poll can miss the thing it exists to catch: a 30-minute cron missed every signal in a week. — [DEV Community post](https://dev.to/xqliu/26-days-of-ai-trading-14-trades-3-system-rewrites-and-one-expensive-lesson-4ai9)

### Inferences
- Recommended shape: one long-running Python process (WebSocket listener plus an internal scheduler) under systemd with `Restart=always`, or the same in a container; cron every minute is a workable fallback for a stateless version. This is standard Linux practice rather than something a cited source measured.
- Reliability checklist: ping a heartbeat URL each cycle and alert when pings stop; alert separately on "process alive but no market data for N minutes" and "LLM call failures above N in a row"; write state to disk (SQLite) so a restart resumes; keep clocks on UTC internally and convert to US Eastern for session logic; set a short per-call timeout (for example 30 seconds) so one hung request cannot stall the loop.
- A home computer or Raspberry Pi removes the VPS bill but adds home-internet and power-cut risk; during paper trading that risk only costs data, so it is a reasonable start, with the heartbeat showing how often it actually drops.
- GitHub Actions remains fine for non-urgent daily jobs (nightly scoring report), not for the loop itself.
- The API key should live in an environment variable or secrets file on the host, in a dedicated workspace with its own low spend limit (section 7).

### Gaps
- No sourced figures were gathered for Raspberry Pi hardware or electricity cost, or for home-connection uptime.
- VPS prices beyond Hetzner (for example DigitalOcean, Vultr, OVH) were not checked on official pages; the third-party pages found are largely affiliate content.
- Oracle's official free-tier allowance and reclamation policy were not verified.

## 7. Guardrails and failure modes

### Takeaway
The dangerous failures are ordinary ones made faster by automation: wrong or invented numbers, poisoned input text, an unavailable or refusing model, a loop that spends without limit, and code bugs in the safety path itself. Each has a code-side control, and the non-negotiable one is that the LLM's output is only ever a validated label that deterministic checks can ignore.

### Cited Findings
- Hallucination and inconsistency: a practitioner article published by a broker warns that "LLM-based systems can produce inconsistent or inaccurate outputs" and that human review and risk controls "reduce but do not eliminate these risks". — [Alpaca Learn: multi-agent AI trading system](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)
- Nondeterminism: Haiku 5.5 does not accept `temperature=0` (non-default sampling parameters return HTTP 400), so repeatability has to come from structured outputs or enum-valued fields rather than sampling settings. — [Anthropic migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) (via bundled reference)
- Prompt injection and poisoned news, measured: an attacker who alters headlines on a single day, with no access to the trading system, used invisible Unicode homoglyphs (breaking stock-name matching) and hidden-text clauses (flipping sentiment); over a 14-month simulation this cut annual returns "by up to 17.7 percentage points". The setup combined an LSTM price forecast with LLM sentiment from FinBERT, FinGPT, FinLLaMA and six general-purpose LLMs; it is a preprint. — [arXiv 2601.13082](https://arxiv.org/abs/2601.13082)
- In the same study FinBERT reportedly misread homoglyph headlines 99% of the time and hidden-text headlines 67% of the time, and the attack transferred to nine other models (search-summary level, not checked in the full text); a security database entry notes the findings "have not been independently verified". — [arXiv 2601.13082 (HTML)](https://arxiv.org/html/2601.13082); [promptfoo vulnerability database](https://promptfoo.dev/lm-security-db/vuln/invisible-headline-trading-loss-b17a1c27/)
- Fabricated news can be worse than classic injection: one 2026 study reports a 14% attack success rate for prompt injection but 62% for fabricated news against LLM trading agents, and that removing credibility cues (a named source, a "BREAKING" tag) cut success from 100% to 0% (abstract-level reading). — [arXiv 2610.26438](https://arxiv.org/pdf/2610.26438)
- Multi-agent trading systems have their own poisoning surface across roles. — [arXiv 2608.24069](https://arxiv.org/pdf/2608.24069)
- Refusals: Haiku 5.5 runs safety classifiers that can decline a request with a normal HTTP 200 and `stop_reason: "refusal"`; there is no server-side fallback for this model, so client code must check `stop_reason` before reading content. — [Anthropic migration guide](https://platform.claude.com/docs/en/about-claude/models/migration-guide) (via bundled reference)
- Spend limits: the Start tier has a $500 monthly cap; you can set your own lower organisation or workspace limit, after which requests return HTTP 400; when the tier cap is hit, requests return HTTP 429 with no `retry-after` header and retries keep failing until the next month; a spend limit on the default workspace may not count some usage. — [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits)
- Rate limits are generous enough to hurt: Haiku 5.5 on the Start tier allows 4,000 requests, 2,000,000 input tokens and 400,000 output tokens per minute. — [Anthropic rate limits](https://platform.claude.com/docs/en/api/rate-limits)
- Long-prompt repricing: a Haiku 5.5 request over 100,000 prompt tokens is billed at 5x rates for the whole request, even when part of it is a cache hit. — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Guardrail code can itself be wrong: four bugs turned one bot's stop-loss into an ordinary limit order, and its tests passed only against mocks. — [DEV Community post](https://dev.to/xqliu/26-days-of-ai-trading-14-trades-3-system-rewrites-and-one-expensive-lesson-4ai9)
- Unconstrained LLM traders over-trade and blow up: Gemini 2.5 Pro flipped positions erratically in Alpha Arena Season 1, and Season 1.5 entries ranged down to −96.15%. — [Decrypt](https://decrypt.co/345006/ai-crypto-trading-showdown-deepseek-grok-winning-gemini-implodes); [aihola](https://aihola.com/article/grok-wins-alpha-arena-trading)
- A concrete deterministic limit set from a published build: 10% max single position, 30% max sector, 1.0x leverage, halts at 5% daily, 10% weekly and 15% total drawdown, plus broker-side bracket orders. — [Alpaca Learn: multi-agent AI trading system](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca)

### Inferences
- Runaway-spend bound (computed from the limits and prices above): a bug that loops at full Start-tier throughput could burn about 2,000,000 x $0.10/M + 400,000 x $0.50/M = $0.40 per minute, about $24 per hour, reaching the $500 tier cap in under a day. Controls, in order: a Console spend limit of a few dollars a month on a dedicated workspace; a code-side daily budget (count calls and tokens from each response's `usage`, stop calling when the day's allowance is spent); a minimum gap between calls; a hard cap on prompt size before sending.
- Number hygiene: never ask the model for a price, percentage or size; compute them in code and pass them in. Reject any verdict whose cited headline IDs are not in the input.
- Input hygiene against the measured attacks: normalise Unicode (NFKC) and drop non-printing characters, strip HTML to visible text, map tickers by exchange symbol rather than by name in the text, keep the source name as a separate trusted field, and require a second independent source or a matching price/volume reaction before any headline can influence an order.
- Treat every non-answer the same way: API error, timeout, refusal, schema failure or stale response all become "no opinion", and the rule-based bot behaves as if the LLM did not exist. The system must be safe with the LLM unplugged.
- Kill switch: a file or environment flag checked every cycle that stops new orders, plus the broker's own "cancel all orders" call; keep protective stops at the broker so they survive a crash of the bot.
- Test guardrails against the real paper API (place and cancel real paper bracket orders), not only against mocks.
- Pin and log the exact model ID on every call, since a model change silently changes behaviour and invalidates comparisons.

### Gaps
- No public data was found on how often Haiku-class models refuse or misfire on ordinary financial-news classification.
- The injection papers were read at abstract or summary level; defences listed above are my inferences from the attack descriptions, not measured mitigations.
- Anthropic outage frequency and typical latency for Haiku 5.5 were not researched.

## 8. How to measure whether the analyst adds anything

### Takeaway
LLM backtests on past dates are not trustworthy because the model may already know what happened; the only clean evidence is forward testing after the model's knowledge cutoff, with every call logged at the time and scored later. The right comparison is the same rule-based bot with and without the LLM filter on the same events, alongside buy-and-hold.

### Cited Findings
- Glasserman and Lin identify two biases when GPT-style models score news inside their training window: look-ahead bias (the model may know how the stock moved afterwards) and a "distraction effect" (general knowledge of the named company interferes with reading the text). Anonymising company names improved in-sample performance, most for large companies; out of sample look-ahead bias is not a concern, and they suggest anonymisation for live use and de-biased backtests. — [arXiv 2309.17322](https://arxiv.org/abs/2309.17322)
- A statistical test for the problem finds that memorisation substantially inflates the apparent predictive power of LLM forecasts (search-summary level). — [arXiv 2512.23847](https://arxiv.org/pdf/2512.23847v1)
- Look-Ahead-Bench measures the bias as "alpha decay" across market regimes and reports significant look-ahead bias in standard LLMs compared with point-in-time models trained only on data up to a fixed date. — [arXiv 2601.13770](https://arxiv.org/abs/2601.13770)
- A 2026 paper calls it "parametric look-ahead bias" (the bias lives in the weights); its correction lowers in-sample backtest returns on memorised dates while leaving out-of-sample 2025 results essentially unchanged (search-summary level). — [arXiv 2605.24564](https://arxiv.org/abs/2605.24564)
- Effective model knowledge can also end months before the vendor's stated cutoff, and LLM trading agents can profit from leaked outcomes (related-work summary). — [arXiv 2611.07464](https://arxiv.org/pdf/2611.07464)
- Broader and longer tests erase most reported LLM edges: over 2004–2024 and 100+ symbols, advantages "deteriorate significantly", which the authors attribute to short windows, few stocks, survivorship and data-snooping bias in earlier work. — [arXiv 2505.07078](https://arxiv.org/abs/2505.07078v5)
- Clean designs test forward: LiveTradeBench streams live prices and news specifically to avoid "offline backtesting and information leakage"; Lopez-Lira and Tang restricted their test to headlines after the model's cutoff. — [arXiv 2511.03628](https://arxiv.org/abs/2511.03628); [arXiv 2304.07619](https://arxiv.org/abs/2304.07619)
- Buy-and-hold is a hard baseline: most LLM agents in StockBench did not beat it. — [arXiv 2510.02209](https://arxiv.org/abs/2510.02209)
- Benchmarks used by an open-source harness: buy-and-hold, always-HOLD, a simple moving-average rule and random decisions. — [PyPI tradingagents 0.7.0](https://pypi.org/project/tradingagents/0.7.0/)
- Small samples mislead: a published paper-trading run had 25 closed trades and about a 48% win rate, and its author declined to draw conclusions; a commentator on the public contests says most are too short and too noisy. — [Alpaca Learn: multi-agent AI trading system](https://alpaca.markets/learn/building-a-multi-agent-ai-trading-system-on-alpaca); [ThinkAdvisor](https://www.thinkadvisor.com/2026/05/06/why-ai-bots-arent-ready-to-replace-your-fund-manager/)
- Paper results overstate live results: fees cut one backtest from about +94% to +35%, and a live prediction-market bot saw a clear paper-to-live gap. — [DEV Community post](https://dev.to/xqliu/26-days-of-ai-trading-14-trades-3-system-rewrites-and-one-expensive-lesson-4ai9); [Medium post](https://medium.com/@gwrx2005/ai-augmented-arbitrage-in-short-duration-prediction-markets-live-trading-analysis-of-polymarkets-8ce1b8c5f362)
- Alpaca's own 24/5 tutorial runs against a paper-trading client, so the same order code can be exercised with no real money. — [Alpaca tutorial](https://alpaca.markets/learn/how-to-trade-us-stocks-24_5-overnight-with-python-and-alpaca)

### Inferences
Proposed measurement protocol (my synthesis):
1. Forward only. Count nothing dated before the model's knowledge cutoff or before the day the prompt and schema were frozen. Any change to prompt, schema or model starts a new test period.
2. Log at call time, score later. Each log row holds the input snapshot, the verdict (direction, confidence, horizon), the rule bot's own signal and the reference price. A separate nightly job fills in what happened after 15 minutes, 1 hour and 1 day, net of an assumed cost per trade.
3. Shadow A/B on identical events. Run the rule bot as usual and record, for every signal, what the LLM filter would have done. Compare three equity curves over the same period: bot alone, bot plus LLM filter, and buy-and-hold of the same symbols (and SPY).
4. Random-veto control. If the LLM vetoes 30% of signals, also compute the result of vetoing a random 30%, repeated many times. A filter only "adds something" if it beats that distribution; otherwise the gain is just reduced exposure.
5. Score the verdicts directly, independent of P&L: hit rate of direction against a coin-flip, and whether higher stated confidence actually goes with higher accuracy (calibration, for example a Brier score).
6. Decide the pass mark before starting: the metric, the minimum number of scored events and the test length. With a handful of trades per day, months are needed before a difference is distinguishable from noise.
7. Include the LLM bill and realistic fees and spread in the "with LLM" curve.
8. Optional realism check from Glasserman and Lin: run a second, anonymised prompt (company name and ticker masked) on the same headlines; if the anonymised version does as well, the model is reading the text rather than leaning on what it knows about the company.
- This matches the reader's history: bots that failed on unseen data need a test in which unseen data is the only data, and the logging-first design makes the LLM's contribution falsifiable at a cost of a few dollars a month.

### Gaps
- Claude Haiku 5.5's stated knowledge cutoff was not looked up; it must be checked on Anthropic's models page before fixing the start date of a forward test.
- I found no published study that forward-tests a cheap model as a veto filter on top of a rule-based stock bot, so the size of any benefit is unknown.
- No source gave a worked sample-size calculation for this setting; the "months, not weeks" statement is my judgement.
- Several bias papers (2512.23847, 2605.24564, 2611.07464) were read only through search summaries; their numbers should be checked before being quoted.
