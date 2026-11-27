# Contest: every premade program the six agents found, on the same sealed test

Goal: run each program the agents found (debate/findings_agent*.md) on PEARL, 1 Oct 00:00 - 20 Nov 23:59 2026,
and compare the end value. Same rules for all of them.

## Money, prices, cost
- $1,000 in USDT at 1 Oct 00:00, 0 PEARL. Spot only, no borrowing, no shorting.
- Test prices come from price_server.py, one minute at a time (contest/sealed.py does this).
  NEVER open data/sealed/ or data/PEARL-USDT_min1.csv (that file also holds Oct-Nov). That would be cheating.
- History the program may know: data/PEARL-USDT_min1_before_oct.csv (25 Jun - 30 Sep) only. Use it for warm-up
  candles and for any training a program does.
- Cost per side: 0.2% fee + max(0.5%, half a price step) = 0.7% on PEARL. The price server charges it.
  Orders fill at the close of the minute after the decision.

## Two ways to run a program (say which one you used)
A. Through the price server (preferred): the program's own decision code decides each minute/candle from the
   candles it has been handed so far; its order goes with the next request. Only the exchange/data connection
   is a stand-in. Example: test_balancer.py.
B. The program's own backtest engine, ONLY when the program cannot run without it (Freqtrade, Jesse, OctoBot ...).
   Get the minutes with sealed.export_minutes() (it walks the server one minute at a time, buying nothing),
   set the engine's fee to 0.7% per side, start with 1,000 USDT, and run the program's own look-ahead check
   if it has one (Freqtrade: lookahead-analysis). Report its end value.

## Not allowed
- Editing the program's own files. If it cannot run unchanged, record "does not run as shipped", the exact error,
  and the smallest change that would fix it. Do NOT make that change (the user decides).
  Allowed: installing it, giving it its config, a stand-in exchange/data feed, pinning an older dependency version.
- Choosing settings by looking at Oct-Nov results. Use the program's shipped defaults/example config. If a setting
  has no default (grid range, levels, pair), choose it from data before 1 Oct with a rule you write down BEFORE the
  run, or use the README's example value.
- Paid services, paid API keys, real orders, real exchange keys.

## Record every program, including the ones that cannot run
Append one line per program/strategy to contest/results.csv with sealed.record(...):
program, strategy, how (A/B/none), trades, end_value, status (ran / does not run as shipped / cannot run here), note.
Put your code and logs in contest/<group>/. Write nothing outside contest/<group>/ except results.csv via record().

Benchmarks on the same test: just holding PEARL $1,475.67; crypto_balancer voted setting $1,095.50; robot 2 $765.
