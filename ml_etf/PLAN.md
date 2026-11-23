# ml_etf — machine learning on SPY + 12 ETFs, practice money (written before any run)

A new program. Nothing from the PEARL bots is reused. Every rule below is fixed before any data is downloaded;
nothing in this file is changed after the sealed test is opened. Any later change is added at the bottom under
"Changes", with the date and the reason, and results from before the change stay reported.

## 1. Data

- Symbols (13): SPY, QQQ, IWM, DIA, XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLB.
- Source: Yahoo chart API, daily bars, all available history; the common start is 22 Dec 1998. The last bar used is
  20 Nov 2026 (the still-forming bar of the download day is dropped).
- Total-return prices: adjusted close C~ = Yahoo adjclose; adjusted open O~ = Open x adjclose / close
  (the same ratio for the whole day, so the dividend is credited across the overnight gap into the ex-date).
- Cash rate: Yahoo ^IRX (13-week T-bill, annual %), forward-filled on days it is missing. A day's cash growth is
  (1 + rate/100)^(1/252), using the previous trading day's rate.
- Checks (must pass before anything else runs): Yahoo raw closes match Nasdaq's within 0.05% on every common day
  of the last 10 years for SPY and 3 other symbols; a sample of 2025-2026 dividends matches Nasdaq's dividend
  history (or the issuer's) to the cent; ^IRX yearly averages for 2022 and 2023 are within 0.15 points of FRED's
  published DGS3MO averages (2.09%, 5.28%); no missing prices after the common start.
- Development file: 22 Dec 1998 - 31 Dec 2015 -> `ml_etf/data/dev.csv` (git-ignored).
- Sealed test file: 4 Jan 2016 - 20 Nov 2026 -> `data/sealed/etf_test.csv` (git-ignored). Only `day_server.py`
  opens it. The test runner sees a test day only after asking the server for it.

## 2. Inputs (features), computed on day t from data up to and including day t's close

Per symbol i, on adjusted closes C~ and volume V:
- r1, r5, r21, r63, r252: C~(t)/C~(t-k) - 1
- vol21, vol63: standard deviation of daily close-to-close returns over 21 / 63 days
- d50, d200: C~(t) / (average of the last 50 / 200 C~) - 1
- volchg: ln(average V over 5 days / average V over 63 days)
- rank21, rank63: rank of r21 / r63 among the 13 symbols, scaled to 0..1
Market inputs, added to every row: SPY's r21, r63, d200, vol21; breadth = share of the 13 above their 200-day
average; dispersion = cross-sectional standard deviation of r21.
Rows with any missing input (the first 252 days) are dropped. Inputs are standardised with mean and standard
deviation from the training rows only.

## 3. Targets — what can actually be traded

A decision made after day t's close fills at day t+1's adjusted open. For horizon h in {1, 5, 21} trading days:
- R_i(t,h) = O~_i(t+1+h) / O~_i(t+1) - 1
- Bill(t,h) = product of the cash growth over the same h days - 1
- Selection target (one row per symbol and day): R_i(t,h) - (1/13) x sum_k R_k(t,h)
- Timing target (one row per day): R_SPY(t,h) - Bill(t,h)

## 4. Purge and gap

A model trained after day tau's close uses only rows t with t + 1 + h <= tau - 5 (in trading days): the whole
answer was known by tau, plus a 5-day gap.

## 5. Models and the settings menu (N)

Each (model, horizon) gets one selection model and one timing model of the same kind and setting.
- Ridge: alpha in {1, 10, 100, 1000}.
- Gradient boosting (HistGradientBoostingRegressor, early_stopping=False, learning_rate 0.05):
  (max_leaf_nodes, max_iter) in {(4, 100), (4, 300), (6, 100), (6, 300)}.
- Neural network (MLPRegressor, early_stopping=False, adam, max_iter 60, batch 256): (hidden, alpha) in
  {((16,), 1e-3), ((16,), 1e-1), ((32, 16), 1e-3), ((32, 16), 1e-1)}; prediction = average of 10 seeds (0..9).
- Menu: 3 models x 3 horizons x 4 settings = 36 combinations. N = 36 for every multiple-testing correction.
  Nothing else is tried; if anything else is ever tried it is added to N here.
- Expanding training window (all purged rows since the start). No other window is tried.

## 6. Trading rule (the same for every model)

Decisions are made after the close every h trading days (decision days are counted from the first day of the run).
1. Timing: invest only if the predicted timing target is above 0.10% (one round-trip cost); else hold cash.
2. Selection: if invested, hold 100% in the symbol with the highest predicted selection target.
3. The order fills at the next day's adjusted open. Long only, no borrowing, all the money.
Models are retrained once a year, after the close of the first trading day of each year, before that day's decision.

## 7. Account (identical in the server and the fast simulator)

$1,000 cash at the start. Each day, before trading: cash grows by the previous day's cash growth. If a new target is
given, at the open: value V = cash + sum of shares x O~; targets T_i = w_i x V; sell everything above target at
O~ x (1 - 0.0005); then buy what is below target, scaled down if needed so that spending at O~ x (1 + 0.0005) never
exceeds cash. Leftover cash stays cash. The day's value is cash + sum of shares x C~.

## 8. Development (choosing settings) — 1999 to 2015 only

For every one of the 36 combinations: run the strategy on the development file from the first trading day of 2006
to 31 Dec 2015 with $1,000, retraining each year as in section 6, using the fast simulator.
- Choice: for each (model, horizon), the setting with the highest Sharpe ratio of daily returns above the cash rate.
  Ties: the setting listed first.
- PBO (probability of backtest overfitting): CSCV with the 10 years 2006-2015 as blocks (252 splits), performance =
  Sharpe above cash, over all 36 combinations; also over the 4 settings of each (model, horizon).
- `ml_etf/locked.json` (chosen settings, N = 36, PBO values) is committed before the sealed file is ever read.

## 9. Sealed test — 4 Jan 2016 to 20 Nov 2026

- One walk through `day_server.py`: each request returns one new day of all 13 symbols; every strategy and
  yardstick sends its target with the request and the server keeps every account. The first targets are decided
  after the close of 31 Dec 2015 from development data and fill at the 4 Jan 2016 open.
- The 9 locked strategies (3 models x 3 horizons), retrained each year on everything seen so far.
- Yardsticks:
  - Hold SPY: 100% SPY at the first open, never changed.
  - Equal weight: 1/13 each, rebalanced at the first open of every month.
  - Momentum (no fitting): after the last close of each month, hold the symbol with the best C~(t-21)/C~(t-252) - 1,
    unless SPY's C~(t)/C~(t-252) - 1 is below the cash growth over the same 252 days, then cash.
  - Coin flip: per strategy, 1,000 runs (seeds 0..999) on the same decision days; at each decision invest with
    probability = that strategy's share of decisions invested, in a symbol chosen uniformly. Run with the fast
    simulator on the bars already handed out.
- Also reported: each calendar year from a fresh $1,000 following the same targets (fast simulator).

## 10. Statistics (all reported for every strategy)

- R2_OS of the timing forecast against the expanding mean of timing targets known at each decision; R2_OS of
  selection forecasts against zero.
- Pesaran-Timmermann test: sign of the timing forecast vs sign of the realised timing target, on decision days
  (non-overlapping).
- Sharpe above cash; information ratio (IR) of daily returns above Hold SPY.
- Deflated Sharpe (DSR) of returns above Hold SPY: N = 36, trial variance V = 1/T (T = number of days),
  skewness and kurtosis from the returns.
- Diebold-Mariano between models for each horizon (timing forecast squared errors, Newey-West with h-1 lags).
- 95% ranges by stationary block bootstrap (mean block 21 days, 2,000 resamples, seed 0) for end value, Sharpe, IR.
- Coin-flip p-value = (1 + k) / (1 + 1000), k = runs ending at or above the strategy.
- Timing skill: mean SPY return above cash over invested periods minus over cash periods.
  Selection skill: mean of (chosen symbol - average of 13) over invested periods.
- Turnover, number of trades, money paid in costs, share of days invested, worst drop.

## 11. Pass mark

A strategy "beats SPY" only if all of these hold:
1. DSR of returns above Hold SPY >= 0.95;
2. the 95% bootstrap range of its IR is above zero;
3. its end value beats the Momentum yardstick;
4. coin-flip p < 0.05.
Otherwise the verdict is "no proven edge", whatever the dollar totals are.

## 12. Checks that must pass before results are shown

- Leak trap: scrambling every day after a retrain date leaves every training row, prediction and trade up to that
  date unchanged (in every development fold and every yearly retrain of the test).
- Purge: no training row's answer window reaches past its cutoff; on pure-noise data a tree model shows no fake
  skill right after a cutoff.
- Money: the fast simulator and the server give the same account values to the cent for every strategy and
  yardstick on the sealed walk.
- Hand-worked examples: adjusted open, a target, a trade with costs, cash interest, each yardstick.
- Statistics checked against an independent library or a published example.
- Independent review for look-ahead and accounting mistakes before results are shown.

## Changes

(none yet)
