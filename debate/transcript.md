# Debate transcript

Each message below was written into this file by the agent named in its heading.

### Agent 5 - round 1
My pick: Freqtrade (github.com/freqtrade/freqtrade, ~57K stars, release 2026.10) running NotAnotherSMAOffsetStrategyHO unchanged. It is Freqle's #1: +117%, 813 trades, 80.7% win rate, profit factor 3.24. Agents 1, 2, 3, 4 and 6 all put Freqtrade in their top three. It has backtest and dry-run built in, so it can be tested before any money moves.

Changes needed (config only, user must approve): exchange = coinbase (or bigone through CCXT), pair = PEARL/USD, stake amount, dry_run = true. The strategy file stays untouched.

Biggest weakness: that +117% is a 2022-2024 backtest on major pairs. The Substack author I cited showed a Freqtrade strategy falling from 105% to 3.65% a year on unseen data. Agent 4 found Risk_Lev3 had a "~-63% worst 3 months" despite a high Freqle score. Expect the same decay on PEARL, so it must pass our sealed one-minute test first.

Why not a rebalancer? Agent 6's anotherRebalancer and Agent 4's crypto_balancer have no published results and small star counts. I trust a maintained engine more.

Question to Agent 1: you wrote "coinbase" = 0 hits in the freqtrade repo. Does that mean Freqtrade cannot connect to Coinbase at all, or only that Coinbase is untested through CCXT?

### Agent 3 - round 1
My pick: **OctoBot, Crypto Basket mode, on Coinbase PEARL-USD.**

Why: of everything the six of us found, it is the only system that comes fully done (pip, Docker or GUI) and already has a rebalancing-style strategy built in. Agent 1 found 57 "coinbase" code hits in its repo, so Coinbase works. Grid and DCA come from a menu too, but the earlier rounds showed grid has zero edge before fees.

Change it needs (user must approve): set the basket to PEARL + USD at about 20/80 with a drift rule. Agent 5 says each preset is "fixed to its coins", so even picking PEARL counts as a change.

Biggest weakness: no verified results at all. Agent 6 found the vendor's own "Lite Bitcoin" went "$1,000 -> ~$886 in 6 months". GNcrypto saw the bot "kept buying above its upper bound". There is also no BigONE support (0 hits), and I can't confirm a basket can hold USD as one of its weights.

Questions:
- Agent 4: you wrote hammertoe/crypto_balancer "Uses CCXT". On PyPI I only saw Binance examples. Did you see CCXT in its code, so it could reach Coinbase or BigONE?
- Agent 6: was "Lite Bitcoin" a DCA or a basket preset, and what did holding BTC do over the same 6 months?

### Agent 6 - round 1
My pick: hammertoe/crypto_balancer (a ready-made threshold rebalancer, pip-installable, CCXT).

Why: the papers I found say prediction bots lose once real costs hit. arXiv 2609.34510 tested 4 AI methods with real money: median -0.56% while the market rose 11.63%. The ai-trading-arena real-money run found fees were 24x the gross result. TensorTrade's own log: +$239 at 0% commission, -$650 at 0.1%. Agent 5's Freqtrade data says the same: 105.03% -> 3.65% yearly on unseen data. PEARL costs us ~1.4% per round trip on BigONE. A rebalancer trades rarely, needs no prediction, and only needs config. Agent 4 lists it as "config only".

Changes (user must approve): exchange name (bigone or coinbase), pair PEARL/USDT or PEARL/USD, targets 20% PEARL / 80% stable, threshold value. Nothing in the code itself.

Biggest weakness: zero track record, one small maintainer, and in a long PEARL uptrend it will sell too early and lose to holding.

Question to Agent 4: you wrote crypto_balancer "Uses CCXT". Agent 3 wrote crypto-balancer is "Binance only in docs. No CCXT/Coinbase/BigONE found." Which is true, and what did you see that shows CCXT?

### Agent 4 - round 1
My pick: Freqtrade running NotAnotherSMAOffsetStrategyHO, the top Freqle strategy (+117%, 813 trades, Agent 5's file).

Why: four of us (Agents 1, 2, 5, 6) rank Freqtrade first. It is the most complete premade system: it was updated today, has a built-in dry-run, and connects to Coinbase through CCXT. Kaggle and Colab have nothing comparable. Every notebook I found is educational with no live trading hooks, and the top Colab results were adverts.

Changes needed (user must approve): config only, meaning exchange coinbase, pair PEARL/USD and stake size. No code edits. It should then go through our sealed one-minute test before any real money.

Biggest weakness: it was tested on major coins in 2022-2024. Agent 5 quotes the same family collapsing out of sample ("105.03% -> 3.65%"). It also trades often, and 813 trades at our ~0.85-1.4% round trip could wipe out the edge.

Questions:
Agent 5, did Freqle's sandbox backtests include fees, and at what rate? If they used 0.1%, the +117% means little at our cost.
Agent 3, you wrote that crypto-balancer is "Binance only in docs", but Agent 2 says hammertoe/crypto_balancer "uses CCXT". Which is right?

### Agent 1 - round 1
My pick: OctoBot in Crypto Basket mode (https://github.com/Drakkar-Software/OctoBot).

Why: it is the most "premade and fully done" system any of us found. pip or Docker install, web GUI, strategies picked from a menu (my file; Agent 3 #1; Agent 4 #3; Agent 5 #3). Coinbase is supported: 57 code hits for "coinbase" in its repo (BigONE: 0). Crypto Basket holds set weights and rebalances (Agent 3), so it trades rarely. That matters most: our cost is ~1.4% per round trip on BigONE. A Freqtrade strategy like NotAnotherSMAOffsetStrategyHO with 813 backtest trades (Agent 5) would pay that cost hundreds of times.

Changes needed (user must approve): basket = PEARL + USD on Coinbase, weights 20/80. Then it goes through our sealed one-minute test before anyone trusts it.

Biggest weakness: zero verified results. Agent 6 found OctoBot's own "Lite Bitcoin" went $1,000 -> ~$886 in 6 months, and a GNcrypto test where it kept buying above its upper bound. BigONE is unconfirmed, so Oct 1 - Nov 13 may need a generic CCXT link.

Agent 3: does Crypto Basket rebalance on a drift threshold or on a timer, and can a stablecoin be one leg?
Agent 4: you say hammertoe/crypto_balancer uses CCXT; Agent 3 says it is Binance-only. Which is right?

### Agent 2 - round 1
My pick: a premade CCXT threshold rebalancer, 556isback/anotherRebalancer (MIT, Python, ccxt, weight-difference threshold). Backup: hammertoe/crypto_balancer.

Why: every paper with code I found is backtest-only on BTC/ETH; none can trade PEARL live. The only real-money numbers anyone found say frequent trading dies on costs: Agent 6's arXiv 2609.34510 (median live -0.56% vs market +11.63%), Agent 6's ai-trading-arena ("fees were 24x the gross result"), Agent 4's TensorTrade ("commission costs currently exceed prediction profits"), Agent 5's Freqtrade strategy falling "105.03% → 3.65%" on unseen data. PEARL costs about 1.4% a round trip on BigONE. A rebalancer trades a few times, predicts nothing, and keeps most money in USDC.

Changes needed (user must approve): exchange name (bigone or coinbase), pair PEARL/USDT or PEARL/USD, target weights, threshold. Nothing else.

Biggest weakness: no track record, tiny repo, and my own search could not open its page (Agents 4 and 6 found it). In a rising market it loses to holding. It must pass our sealed one-minute test first.

Questions:
- Agent 3: you wrote crypto-balancer has "No CCXT/Coinbase/BigONE found", but my search said hammertoe/crypto_balancer "depends on ccxt". Which is right?
- Agent 6: did you see anotherRebalancer's threshold check in its code, or only in its description?

### Agent 2 - round 2
No one asked me a question, so no search this round.

Agent 5 and Agent 4: you pick NotAnotherSMAOffsetStrategyHO at "+117%, 813 trades". Do the math. +117% compounded over 813 trades is about 0.1% gained per trade (ln 2.17 / 813). Our cost is 0.85% (Coinbase) to 1.4% (BigONE) per round trip. Even if Freqle's backtest already paid 0.1% fees, each trade's edge is 8 to 14 times smaller than our cost. Agent 4 said "813 trades at our ~0.85-1.4% round trip could wipe out the edge". It would.

Agent 1 and Agent 3: I agree with the idea of OctoBot Crypto Basket, since it is also rebalancing. But Agent 3 wrote "I can't confirm a basket can hold USD as one of its weights." If it can't, it can't do 20/80.

On the open CCXT question: my own search (ecosyste.ms listing) said hammertoe/crypto_balancer "depends on ccxt". Agent 4 says the same. Agent 3 saw only Binance examples,. Both can be true.

Count: four of us (1, 2, 3, 6) want a rebalancer. I'm moving to Agent 6's pick, hammertoe/crypto_balancer, as primary, because it installs with pip. anotherRebalancer is the backup. The changes stay the same: exchange, pair, 20/80, threshold.

### Agent 4 - round 2
Answer to Agents 1, 2, 3 and 6 on crypto_balancer and CCXT: I was wrong to write "Uses CCXT". My own search result only said it "connects to an exchange" and is pip-installable. It never named CCXT. I checked with two searches this round. "hammertoe crypto_balancer ccxt exchange requirements github" found nothing on the repo. "\"crypto_balancer\" hammertoe README exchange binance ccxt" found https://github.com/hammertoe/crypto_balancer, and its README shows Binance examples only. The summary said it "didn't reveal whether the hammertoe script actually uses CCXT". So Agent 3 is right as far as anyone can see, and Agent 6's pick rests on my unverified line. Agent 2, your "depends on ccxt" needs a source.

Agent 1, you wrote that NotAnotherSMAOffsetStrategyHO "would pay that cost hundreds of times". I agree, and it is the weakness I named myself. 813 trades at ~1.4% is fatal.

So I am changing my pick to OctoBot Crypto Basket on Coinbase PEARL-USD, 20/80. It is maintained, Coinbase is confirmed (57 hits), and it rebalances rarely.

Agent 3: Agent 1 asked you if one leg can be a stablecoin. If it can't, the basket idea fails. What did you see?

### Agent 1 - round 2
Agent 5, your question: 0 hits means untested, not blocked. I re-ran GitHub code search: "coinbase" in freqtrade/freqtrade = 0, but "bitvavo" = 8, so the search works and Coinbase just has no special code. The phrase "not officially supported" sits in freqtrade/exchange/check_exchange.py: it warns and carries on. Web search "freqtrade supported exchanges coinbase advanced ccxt": CCXT's comparison page (https://docs.ccxt.com/docs/comparisons/ccxt-vs-freqtrade) says Freqtrade's SUPPORTED_EXCHANGES is "a tested list" of 15 ids, and other CCXT exchanges that pass its capability check "may be attempted". So Coinbase and BigONE are both possible, both untested.

Agent 4, you wrote "813 trades at our ~0.85-1.4% round trip could wipe out the edge." Agreed, so I can't back that pick: at full stake, 813 round trips at 1.4% leave about 0.001% of the money before any gains.

Agent 3, you wrote "I can't confirm a basket can hold USD as one of its weights." That decides my pick. If Crypto Basket can't hold USD, it can't do 20/80, and I switch to Agent 2's anotherRebalancer (ccxt, seen by Agents 2, 4 and 6).

Agent 6: does anotherRebalancer have a dry-run mode?

### Agent 5 - round 2
Agent 4, answer: yes, fees were in. I searched "Freqle freqtrade strategy league how backtests are run fee pairs timeframe". Freqle league pages (https://freqle.org/strategy/419aaf032f3530f5, https://freqle.org/strategy/7cf7cde9078dade7) show: 33 pairs, spot, 5m, 100 USDT stake, 1000 USDT wallet, 10 open trades, fee 0.1% per side ("exchange lowest tier"). That is 0.2% round trip, against our ~0.85% (Coinbase) to ~1.4% (BigONE).

Rough math (my estimate, assuming flat 100 USDT stakes): +117% = ~1,170 USDT over 813 trades, about +1.44% net per trade, ~1.64% gross. At 1.4% cost that leaves ~0.24% per trade; at 0.85%, ~0.8%. Not wiped out on paper, but thin, and it was earned on 33 deep-book majors, not one thin coin.

Agent 1, you said it "would pay that cost hundreds of times". On one pair it makes roughly 813/33, about 25 trades, not 813. But your core point stands: each trade costs 4-7x what Freqle charged.

Agent 6, your "fees were 24x the gross result" is the warning I can't dismiss.

I keep Freqtrade only if the sealed test runs it AND a rebalancer side by side. Whichever beats holding wins.

### Agent 6 - round 2
Agent 3: I can't say. My source was a table on octobot.cloud: "Lite Bitcoin" $1,000 -> ~$886 over "the past 6 months", type and date not given. I searched `OctoBot "Lite Bitcoin" strategy`: nothing. BTC-hold over that window: unknown.

Agent 2: I had only the description. This round I fetched its code (raw.githubusercontent.com/556isback/anotherRebalancer/main/). The threshold check is real: rebalancer.py line 77 trades only if `diffs[sym] > exchange_api.threshold` and the gap is over $5. But it is NOT config-only:
- weights come from PyPortfolioOpt `min_volatility()` (line ~40); a fixed 20/80 means editing code
- README: "USDT is hard coded", so Coinbase PEARL-USD fails; BigONE PEARL-USDT fits
- README: balances() "you might need to modify" per exchange
So it needs code changes the user must approve. I drop it.

Agent 5 and Agent 4: you wrote "813 trades". At ~1.4% round trip that is over 1,100% of cost on the stake; Agent 4 said this too. That kills NotAnotherSMAOffsetStrategyHO for PEARL.

My pick stays hammertoe/crypto_balancer only if Agent 4 shows CCXT in its code. If not, I move to Agent 1/3's OctoBot Crypto Basket.
