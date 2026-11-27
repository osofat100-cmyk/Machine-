# Spike robot - plan (written before any run)

New program, no code from the old robots.

## Data
- Training: BigONE PEARL-USDT minutes 25 Jun - 21 Oct 2026 (spikes/data/train.csv).
- Test: the last month, 22 Oct 00:00 - 20 Nov 23:59 (BigONE to 13 Nov 17:59, Coinbase after).
  Only price_server.py opens it and hands it out one minute at a time. The robot never sees a minute before
  it happens.

## What a spike is
A zigzag with size theta: an up-spike starts at a low and is "on" once the price is theta above that low;
it ends when the price falls theta below its highest point. Down-spikes are the mirror image.
For every spike in the training data we keep its full size (low to high, or high to low).

## The odds table
From all training spikes of one theta: "a rise that has already gone r% has this chance of going x% more"
= (spikes at least r+x big) / (spikes at least r big). Same for drops. Small spikes end early, so the
chance of going further is low for middle-sized moves; a move that is already past where small spikes stop
is probably a big spike, and the chance goes back up. That is how the two kinds of spike are told apart.

## Robot (all money in every trade)
- Holding USDT, during a down-spike that has dropped d% from its high:
  BUY when the chance the drop goes x% further is below p_buy.
- Holding PEARL, during an up-spike that has risen r% from its low:
  SELL when the chance the rise goes x% further is below p_sell.
- Optional stop: SELL if the price is s% below the buy price.
- A decision on a minute's close fills at the next minute's close. Cost per side 0.2% fee +
  max(0.5%, half a price step) = 0.7%.

## The settings tried (27,783 robots)
theta 2, 3, 4, 5, 7, 10, 15% | p_buy and p_sell 1, 5, 10, 15 ... 95, 99% | x 2, 4, 8% | stop none, 10%, 20%

## How the winner is chosen (training data only)
1. Odds tables from 25 Jun - 21 Sep. Every robot runs 25 Jun - 21 Sep ("choose") and 22 Sep - 21 Oct ("check").
2. Each robot's score = average over itself and its grid neighbours (one step away in one setting) of
   sqrt(growth on choose x growth on check). Safest, not luckiest. Highest score wins.
3. The winner's odds tables are rebuilt from all training data (25 Jun - 21 Oct). Then the last-month test.
No setting is changed after the test.

## Second search: every 1% (added after the first test, on the user's request)
The first search only tried buy/sell chances 1, 5, 10 ... 95, 99%. The user asked for every 1% from 1 to 100%.
`choose.py --every1` tries 100 x 100 buy/sell chances x 7 spike sizes x 3 x x 3 stops = 630,000 robots,
with the same choose/check months and the same "safest" score. Its winner (winner_1pct.json) is committed
before its last-month test. The last month was already used once (first winner: $815.55); both results are
reported, whichever is better.
