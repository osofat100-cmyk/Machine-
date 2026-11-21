# Group 4: grid and DCA bots

Written before any program was run on the test.

## Rule for settings that have no default (fixed before running)
- Grid price range: the 30-day low and high of PEARL/USDT up to 30 Sep 23:59 (data before Oct only):
  low 0.2864, high 1.762. (Computed from data/PEARL-USDT_min1_before_oct.csv, 31 Aug 23:59 - 30 Sep 23:59.)
- Number of grid levels / spacing / order size / DCA amounts: the program's shipped default or README/example config.
- Pair: PEARL/USDT. Start: 1,000 USDT, 0 PEARL on 1 Oct 00:00 (price server account).
- Way A fill rule: a resting limit order at a grid level is sent as a market order on the minute that minute's
  close crosses the level; the server fills it at the next minute's close with the 0.7%/side cost.

## Log
