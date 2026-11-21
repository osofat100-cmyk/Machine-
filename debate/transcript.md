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
