# PEARL trading plan

Research done 2026-11-20 on BigONE data: 5 months of hourly prices (PEARL-USDT,
since 2026-06-25) and 30 days of 1-minute prices. Re-run `backtest.py` to refresh.

## What the data says

1. **Each trade is expensive.** Buying $1000 of PEARL-USDC and selling it straight
   back cost about 1.4% at the live order book (0.2% fee each way, plus the gap
   between buy and sell prices). The price has to move more than that before a
   trade makes anything.
2. **Second-by-second trading cannot cover that cost.** In 1-minute data, only
   about 2% of minutes move more than 1%. A fast rule on 1-minute candles lost
   74% in the test.
3. **PEARL trends.** It went from about $0.31 (end of August) to about $1.95.
   Just holding turned $1000 into about $2,930 over the 5 months, but with a
   74% drop along the way.
4. **One slow rule held up:** hold PEARL while the 24-hour average is above the
   7-day average, otherwise hold dollars. $1000 became about $4,400 with 10
   trades and a worst drop of 42%. It made less than holding during rallies and
   lost much less during falls.
5. **Chasing spikes did not work.** After a big-volume hour that jumped 3% or
   more, the price was lower 4 hours later in 9 of 12 cases.
6. **Busiest hours** are 13:00-16:00 UTC (biggest moves and volume).

## What moves the price (from news)

- Late September rally: the "AI mining" story and social media attention.
- November rally: a mining upgrade (FP8) and a reported Coinbase spot listing.
- Risks named in coverage: the team and its shareholders reportedly hold about
  a quarter of circulating supply, and critics question whether the AI work is
  really in demand.

News can't be predicted by the program. The trend rule reacts after a news move
has started; it does not need to know the reason.

## The plan

1. **Now:** run `paper_trader.py` (fake money) and `pearl_monitor.py` for 2-4 weeks.
2. **Review:** compare the practice account with just holding. Add and test your
   own rules in `backtest.py`.
3. **Only then:** real money, small size, with an API key that can trade but
   cannot withdraw.

## Limits of this research

- 5 months is short and contains one very large rally. The rule made only 10
  trades, and 3 of them were winners; most of the profit came from a few big ones.
- Other slow settings (12/96, 48/168) also did well; fast ones (6/24) lost
  money. That pattern is more trustworthy than any single number.
- Past results do not promise future results. This token can fall as fast as it rose.
