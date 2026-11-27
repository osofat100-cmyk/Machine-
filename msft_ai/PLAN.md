# Microsoft AI trader: plan (fixed before any AI answer is seen)

## Question
Can a free, open AI model trade Microsoft better than simply holding it, if it gets one day at a time and the
same kinds of information a person would use: prices, competitors, the market, the economy, Microsoft's reported
results and the news?

## AI
- Meta Llama 3.2 3B Instruct, Q4_K_M quantised (bartowski GGUF), run on this machine with llama.cpp. Free, no key.
- Its training data ends December 2023 (Meta's model card). The test starts 2 January 2024, so it cannot remember
  what happened next. Before the run it is asked about 2024-2026 events to check this (`probe_memory.py`).
- Temperature 0, fixed seed: the same inputs always give the same answer.
- Answer forced to the form `BUY|SELL|HOLD - one short reason`.

## Information each day (`ai_trader.py build_prompt`)
Only what `day_server.py` has handed out so far:
- **Microsoft:** close; 1-day, 1-week, 1-month, 3-month and 1-year change; distance from its 50- and 200-day
  averages; 52-week high and low; volume against its 20-day average; last 10 closes.
- **Market:** SPY, QQQ and the tech sector XLK over 1 day, 1 week and 1 month.
- **Competitors:** Apple, Alphabet, Amazon, Meta, Nvidia, Oracle and Salesforce over 1 day, 1 week and 1 month.
- **Economy:** VIX, the 10-year Treasury yield, the 3-month T-bill, the US dollar index and oil.
- **Results:** Microsoft's latest reported quarter as filed with the SEC (revenue, net income and EPS, with
  year-on-year growth), plus SEC filings in the last 5 days.
- **Headlines** from Google News for the last 3 trading days, newest first:
  - up to 8 about Microsoft;
  - up to 4 about MSFT stock;
  - up to 5 about competitors;
  - up to 5 about the economy.

  A headline dated day D reaches the AI after D's close, at the earliest. Weekend headlines arrive with Monday.

## Trading
- **Positions:** all money in Microsoft or all in cash. Cash earns the 3-month T-bill.
- **Timing:** the decision is made after the close; the order fills at the next open, using a dividend-adjusted
  open.
- **Costs:** 0.05% of every amount bought or sold.
- **Account:** starts with $1,000. The first fill is on 2 January 2024 and the last day is 20 November 2026.
- **History only:** the days 2022–2023 are handed out first as background, so averages and 1-year changes exist.
  The AI makes no decisions on them.

## Yardsticks
- **Hold Microsoft:** buy at the 2 January 2024 open and never sell. This is the main comparison.
- **Hold SPY:** close-to-close, for context.
- **Random timing:** 1,000 shuffles that keep exactly the AI's number of switches and its share of days in
  Microsoft, but shuffle the order of its in and out periods.

## Pass mark (all must hold), decided now
1. The AI's end value beats holding Microsoft.
2. Its 95% block-bootstrap range of the information ratio against holding Microsoft is above zero. Blocks
   average 21 days; there are 2,000 resamples.
3. It beats the random-timing shuffles with p < 0.05, where p = (1 + number of shuffles ending at or above the
   AI) / 1001.

Otherwise the verdict is **no proven edge**.

## Saving
- Every answer is appended to `answers.csv`, and every full prompt to `data/msft_prompts.jsonl`, at the moment
  the answer is given.
- Daily account values go to `values.csv`.
- A restart replays the saved answers without asking the AI again, then continues where it stopped.

## Known limits
- Google News search today may return a different set of headlines than a reader saw on the day. Counts vary from
  1 to 100 per search.
- Economic releases (CPI, jobs) arrive as headlines and market moves, not as official numbers. The FRED site is
  blocked here.
- A 3B model is small; it was chosen because it runs at a usable speed on 4 CPU cores with no key or cost.
