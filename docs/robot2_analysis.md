# Robot 2: checks, fixes and test results

Run on 20 Nov 2026 on BigONE PEARL-USDT minute prices, 25 Jun – 20 Nov 2026.
Re-run with `python3 checks.py`, `python3 traj_sweep.py`, `python3 robustness.py 14`.

## What robot 2 is now

One program, `engine.py`, does everything in the plan (`docs/machine_math.tex`): settings
landscape in 0.1% steps, smoothing, the pick, 1,440 update-interval machines, the safest
interval, the trajectory watcher, the library and the borrowed data. The tests and the live
practice bot (`live_machine.py`) both run this same code.

## Structural checks (`checks.py`): all pass

| Check | What it proves |
|---|---|
| Cost | A buy and a sell at the same price turn $1,000 into $986.10 |
| Book | 300 random settings match a separate, simple simulation to the cent |
| Watcher | The engine finds the same 15 trajectories as `trajectories.py` |
| Library | 760 setting/trajectory results match a simple simulation of just that stretch |
| No future | Scrambling all prices after a moment changes nothing the robot did before it |
| Restart | Saving, reloading and continuing gives the same result as running straight through |

## Problems found and fixed

1. **Ties.** When many settings were tied for best, the pick was whichever came first in
   memory (for example sell 0.1% instead of sell 42%). It now takes the middle of the tied area.
   This alone moved the never-reset robot's result from $2,919 to $3,804.
2. **Cost with coarse prices.** Until 10 Jul BigONE priced PEARL in whole cents, about 2% of the
   price per step. The simulation counted a one-cent bounce as profit: the setting buy 0.1% /
   sell 0.1% "made" +72% in ten days of falling prices. Cost now includes half a price step.
3. **Smoothing at the bottom edge.** A lucky setting in the 0.1% / 0.1% corner kept about 27%
   of its height after smoothing, because the edge was repeated. The bottom edge now averages
   only real neighbours.
4. **Test and live were different programs.** The old live bot kept a stale setting where the
   tested robot dropped it. Both now run `engine.py`.

## Two facts about the data

- **Cent prices until 10 Jul** (above).
- **Thin market until about 21 Sep.** PEARL traded about $15–35k a day; a typical minute traded
  $5–13. All 17 of the never-reset robot's fills before 21 Sep were orders (about $1,260) larger
  than everything the market traded in that minute, and 8 of 17 were larger than the whole hour
  around it. Money "made" before late September could not have been made at that size. That
  covers most of every large number so far ($13,419, $11,069, the 3D hill).

## Trajectory resets: the plan's test

16 sensitivity levels, robot starts 25 Jun with $1,000 and no data. The level is chosen on
25 Jun – 30 Sep only, then checked on 1 Oct – 20 Nov.

| | To 30 Sep (choosing) | 1 Oct – 20 Nov (unseen), per $1,000 |
|---|---|---|
| Chosen level (14): robot 2 with resets | $2,638 | **$652** |
| Robot 2, never resets | $2,980 | $1,591 |
| Just holding PEARL | $1,765 | $1,578 |

- 14 of the 16 levels lost money on the unseen period. The best (40, which resets least) made
  $1,376, still below holding.
- The never-reset robot made no trades in the unseen period. It bought on 27 Sep and held, so
  its $1,591 is the holding result.
- Why resets lost: after a reset the robot moved to settings with a small sell % (10–15%). The
  rule sells on a bounce from the 4-hour low, whatever it paid, so in October it bought dips
  and sold lower (bought $2.20 on 21 Oct, sold $1.80 on 28 Oct).

See `traj_sweep.png` and `data/traj_sweep.csv`.

## How fragile it is (`robustness.py`)

Each run changes one thing. Unseen period, per $1,000 (holding: $1,578):

| Change | Result |
|---|---|
| As built (level 14) | $652 |
| Fills at the worst price of the minute | $627 |
| Cost 1.2% per side | $1,318 |
| 2-hour / 8-hour window instead of 4 | $892 / $898 |
| "At the low" 0.10% / 0.50% | $656 / $693 |
| "Near the high" 1.0% / 3.0% | $906 / $743 |
| Start 11 Jul / 1 Aug / 1 Sep | $1,291 / $996 / $952 |
| Update every minute (no interval choice) | $1,145 |
| Borrow the whole library | $1,160 |

All 13 stayed below holding. On the choosing period the 4-hour window gave $2,638 while 2 and
8 hours gave $1,604 and $1,206, so the 4-hour window is a narrow, hindsight-picked spot.

## Live practice bot

`live_machine.py` builds the robot from the whole downloaded history, then follows live BigONE
minutes and trades practice money at the real PEARL-USDC order book. Tested: build, live
minutes, save and restart, and a buy then sell at the real book ($1,000 → $980.73, a 1.9%
round trip, above the 1.4% the tests assume).

## What this does and does not show

- The engine is structurally sound: it does what the plan says, with no look-ahead.
- On the only stretch that is both liquid and unseen (1 Oct – 20 Nov), no version beat holding.
- That stretch is 7 weeks of one coin, and it was looked at earlier when the rule was first
  found, so it is not a perfectly clean test either.
