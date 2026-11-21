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

## Merging instead of resetting (`merge_lines.py`)

Every setting keeps one account from day one. Line *p* (1%–100%) keeps *p* of the old data each
time the watcher sees a trajectory change. Every hour each line picks a setting. Accuracy = share
of a line's past picks that made money *H* later (5 minutes to 14 days), using only outcomes
already known. Risk = share of money put in per buy, fixed 1%–100% or Kelly. The merged robot
follows, every hour, the middle of the biggest stretch of lines with above-average accuracy.
Checks (`python3 merge_lines.py check`): line 100% equals the never-reset engine pick for pick,
account values match, the risk formula equals a plain account, accuracy uses no future outcomes.

The price file now runs to 20 Nov 22:05, so holding over the test is $1,536 here.

**Accuracy (whole history).** Lines keeping 25–50% of old data were the most accurate: about
57–62% of their picks made money 5–7 days later. Never resetting was about 50%. Within 2 hours of
a pick every line was below 50%: a "buy the crash" pick usually dips further first.

**Results on the unseen period, 1 Oct – 20 Nov, per $1,000 (holding $1,536):**

| Variations | Beat holding | Chosen on Jun–Sep | Its test result |
|---|---|---|---|
| 100 lines × 100 risk levels (10,000) | 180 | keep 43%, risk 77% | $1,077 |
| 100 lines × Kelly × 14 horizons (1,400) | 0 | keep 46%, accuracy after 12 hours | $1,026 |
| Merged robot × 14 horizons × 101 risk (1,414) | 0 | accuracy after 3 days, Kelly | $1,045 |

- The 180 that beat holding are all in one corner (keep 55%+, risk 97%+). There the robot bought
  before October and held, which is holding.
- Kelly put in little money because accuracy was only 50–60%, so results stayed near $1,000.
- Merging did better than resetting on the test (merged $1,045; keep 1% $804; the reset robot
  $652), but not better than holding or never resetting ($1,558).

## Robot 2 with everything connected (`robot2.py`)

One robot now holds all parts: the 100 lines, the trajectory library (similar past trajectories
get extra weight that fades), accuracy judged at all 14 waiting times, the followed line, the
1,440 timing machines, and Kelly risk. The live practice bot runs the same class.

Checks (`python3 robot2.py check`), all pass: with the library off its 100 lines pick exactly what
`merge_lines.py` picked (66,700 of 66,700); accuracy counted live equals accuracy rebuilt
afterwards (444,747 judged picks); the per-minute pick equals a direct calculation; changing
prices after a moment changes nothing before it; stop, save, reload and continue gives the same
result.

$1,000 on 25 Jun 20:38, memory empty, to 20 Nov:

| | 20 Nov | 1 Oct – 20 Nov | from 21 Sep |
|---|---|---|---|
| Kelly risk (what it used) | $1,090 | ×1.00 | +5% |
| 50% per buy | $1,938 | ×1.01 | +21% |
| 100% per buy | $3,279 | ×1.01 | +35% |
| Just holding | $2,749 | ×1.54 | +118% |

Kelly put in 1% on most buys: accuracy pooled over all waiting times stayed close to 50%, which
Kelly treats as no edge.

## Which part of robot 2 helps or hurts (`ablation.py`)

Each run switches one part off; all start 25 Jun with $1,000 and no data.

| Robot 2 | Buys | Nov 20 (100% per buy) | Oct 1 – Nov 20 | From 21 Sep | Nov 20 (Kelly) |
|---|---|---|---|---|---|
| Everything on | 17 | $3,279 | $1,006 | +35% | $1,090 |
| Timing machines off (newest pick every minute) | 19 | $4,356 | $1,166 | +52% | $1,161 |
| Library off | 17 | $5,962 | $1,140 | +48% | $1,325 |
| Accuracy judged after 3 days only | 17 | $3,279 | $1,006 | +35% | $1,274 |
| Library off + timing off | 21 | $7,543 | $1,154 | +50% | $1,362 |
| Just holding | | $2,749 | $1,536 | +118% | |

The library and the timing machines each lowered the result. Judging accuracy at one waiting time
instead of all 14 changed only how much Kelly put in, not when the robot traded.

With both off, the whole-period result was the highest ($7,543), but most of that came before
21 Sep, when the market was too thin to fill $1,000 orders. On the unseen Oct–Nov stretch it made
$1,154 per $1,000: about the same as either part off alone, below the Grayscale-style 50-day rule
($1,251) and below holding ($1,536).

## Compared with public professional methods (`benchmarks.py`)

| Method | Nov 20 | Oct 1 – Nov 20 | Worst drop |
|---|---|---|---|
| Wells Fargo style: 3% in PEARL, rebalanced monthly | $1,080 | $1,011 | 5% |
| Institutional trend-following, 10% risk target | $1,139 | $993 | 4% |
| Grayscale-style 50-day average rule | $4,869 | $1,251 | 48% |
| Robot 2, Kelly risk | $1,090 | $1,002 | 24% |
| Robot 2, 100% per buy | $3,279 | $1,001 | 55% |
| Just holding PEARL | $2,725 | $1,552 | 69% |

## The sealed test: chosen on Jun–Sep only, Oct–Nov handed over one minute at a time

Run on 21 Nov 2026: `python3 fetch_sealed.py`, `python3 choose_before_oct.py`, `python3 test_unseen.py`.

**Chosen using only prices before 1 Oct** (`choose_before_oct.py`, 30 robots, all money per buy,
25 Jun – 30 Sep). The 27 window / low / high combinations were scored as the average of each and
its grid neighbours (safest, not luckiest). Then the 4 part choices were tried at the winner:

| | Chosen | Was (picked after seeing Oct–Nov) |
|---|---|---|
| Window | 2 hours | 4 hours |
| "At the low" | 0.50% | 0.23% |
| "Near the high" | 1.0% | 1.8% |
| Parts | library off, timing on | library off, timing off |
| Money on 30 Sep (from $1,000) | $3,358 | |

**Test prices, sealed** (`data/sealed/`, opened only by `price_server.py`): BigONE PEARL-USDT
1 Oct – 13 Nov 17:59, then Coinbase PEARL-USD 13 Nov 18:00 – 20 Nov 23:59 (Coinbase started
trading PEARL at 17:21 that day; no other exchange had PEARL minute prices before 23 Oct). At the
switch Coinbase was 3.8% above BigONE. The robot and holding both held PEARL then, so both got it.

**The test.** The robot knew 140,122 minutes, the last at 30 Sep 23:59. It started 1 Oct with
$1,000 USDC and asked the server for one minute at a time (73,440 minutes). The server kept the
account and filled each order at the next minute.

| Time | Trade | Price | Account |
|---|---|---|---|
| 21 Oct 16:28 | Buy | 2.2019 | $986.10 |
| 18 Nov 15:59 | Sell | 2.1403 | $958.51 |
| 19 Nov 11:42 | Buy | 2.2581 | $945.18 |
| 20 Nov 23:59 | (still holding) | | **$765.07** |

| $1,000 on 1 Oct → 20 Nov | |
|---|---|
| Robot 2, chosen on Jun–Sep, sealed test | **$765** (−23%) |
| Just holding PEARL | **$1,476** (+48%) |

The server's account and the robot's own count agree to the cent. The robot bought near the
October top, held through the fall to about $1.40, and bought again on 19 Nov before a drop.
