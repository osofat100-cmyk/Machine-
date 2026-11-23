# Practical plumbing for a small US retail automated stock-trading bot (brokers, costs, data, frameworks, hosting)

Research date: 2026-11-23. Unless a different date is given, every fact below was read from the linked page on 2026-11-23. Method notes that affect reliability:
- Pages were read through an automated fetch-and-summarise tool, so numbers are as that tool reported them; anything marked "verify" should be re-checked on the live page before money depends on it.
- Several primary pages refused automated access (HTTP 403/404): most interactivebrokers.com pricing/docs pages, developer.schwab.com, docs.tradier.com rate-limit and FAQ pages, vultr.com pricing, Hetzner's price-adjustment page. Facts about those come from search-result extracts or secondary sources and are flagged.
- Package release dates were pulled directly from the PyPI JSON API on 2026-11-23 (primary). The GitHub API was not reachable from this session, so commit/issue counts are mostly missing.
- No sign-ups, API keys or orders were used.

## 1. Broker APIs open to US retail for automated stock/ETF trading

### Takeaway
Alpaca is the only broker found that gives a no-deposit, email-only paper-trading API with $0 commission, $1 fractional orders and 24/5 trading; its free data is IEX-only and its paper fills ignore fees, slippage, queue position and dividends. Every other option either needs a funded live account before paper trading (IBKR, Tradier), has no real paper API (Schwab, Public, Robinhood), or has a limited sandbox (tastytrade, E*TRADE, Webull), and the $25,000 pattern-day-trader minimum was abolished by rule in 2026 but is only gone at brokers that have implemented the change.

### Cited Findings

#### Rule change that matters for a $1,000 account (pattern day trader rule)
- The SEC approved (April 14, 2026) FINRA's amendment of Rule 4210 that removes the "pattern day trader" definition, the $25,000 minimum equity requirement and "day trading buying power", replacing them with intraday margin standards — [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10); [Schwab summary](https://www.schwab.com/learn/story/sec-approves-scrapping-25000-day-trader-minimum)
- Effective date June 4, 2026, with a phase-in period ending October 20, 2027; members that need more time may phase in implementation — [FINRA Regulatory Notice 26-10](https://www.finra.org/rules-guidance/notices/26-10)
- Until a given broker implements the new standards, the $25,000 requirement still applies at that broker; Schwab said it planned to stop counting day trades from June 8, 2026 — [SoFi](https://www.sofi.com/learn/content/pattern-day-trading-rules/); [Schwab](https://www.schwab.com/learn/story/sec-approves-scrapping-25000-day-trader-minimum)
- Alpaca's fractional-trading doc still says fractional day trades "count toward your day trade count" (page not dated; may predate the rule change) — [Alpaca fractional trading docs](https://docs.alpaca.markets/docs/fractional-trading)

#### Comparison table (stocks/ETFs only)

| Broker | Commission (US stocks/ETFs) | Paper/sandbox | Fractional via API | Data included | Rate limit | Extended / overnight |
|---|---|---|---|---|---|---|
| Alpaca | $0 for self-directed API accounts; SEC/FINRA fees passed through | Yes, paper-only account with just an email, $100k default | Yes, from $1, 2,000+ symbols | Free: IEX real-time; $99/mo for all exchanges | 200 requests/min per account (live and paper) | Pre/post and overnight (24/5), limit orders only overnight |
| Interactive Brokers (Pro) | Fixed $0.005/share, $1.00 minimum per order; Tiered $0.0005–$0.0035/share | Yes, but only after the live account is funded | Unclear/conflicting (see below) | Free non-consolidated Cboe One + IEX streaming; NBBO bundle $10/mo | 50 orders/second (TWS API) | Not researched |
| Tradier | Lite $0/mo plan: $0.35 per stock trade; Pro $10/mo: $0 | Sandbox = paper account for account holders, delayed data, no streaming | Not found | Not found | Not found (docs page 404) | Not found |
| Charles Schwab | Not confirmed from a primary page | No sandbox found; thinkorswim paperMoney is not exposed via API (secondary) | Not found | Quotes via API (details not confirmed) | 120 requests/min (unofficial wrapper docs) | Not found |
| tastytrade | $0 to open and close | Yes, sandbox resets every 24h; fills at quote mid | Fractional supported at $0 (pricing page; API support not confirmed) | Sandbox REST market data returns HTTP 502 | Not found | Not found |
| Public.com | "Free to use" API; stock commission not stated in FAQ | None mentioned | Yes, $5 minimum, regular hours only | Quotes and bars; real-time status not stated | 10 requests/second per account | 4am–8pm ET and 24/5 session |
| Webull | Not found | Sandbox with separate keys (third-party guide); QuantConnect says no paper via API | Yes for stocks | Level 1 US stock streaming free; more needs an OpenAPI subscription | 600 order requests per 60s | Extended hours and overnight session |
| E*TRADE | Not found | Sandbox with separate keys | Not found | Not found | "Strict" (third party), number not found | Not found |
| Robinhood | n/a | None mentioned | n/a | n/a | n/a | n/a — no documented public stock REST API; crypto API and (since May 2026) agent/MCP access only |

Row sources are itemised below.

#### Alpaca
- "Commission-Free trading means that there are no commission charges" for self-directed individual cash brokerage accounts trading US-listed securities through an API; "Relevant SEC and FINRA fees may apply" (article dated August 2023, still live) — [Alpaca commission and clearing fees](https://alpaca.markets/support/commission-clearing-fees)
- "Anyone globally can create an Alpaca Paper Only Account" with only an email address; paper accounts start with $100k; paper has its own API key and base URL — [Alpaca paper trading docs](https://docs.alpaca.markets/docs/paper-trading)
- Paper-only accounts receive IEX market data only — [Alpaca paper trading docs](https://docs.alpaca.markets/docs/paper-trading)
- Paper fill model: orders fill only when marketable against real-time quotes; order size is not checked against quoted size; eligible orders get a partial fill of random size 10% of the time — [Alpaca paper trading docs](https://docs.alpaca.markets/docs/paper-trading)
- Paper trading explicitly does not account for market impact, information leakage, latency slippage, order queue position for non-marketable limit orders, price improvement, regulatory fees, or dividends; borrow fees are "coming soon" for paper — [Alpaca paper trading docs](https://docs.alpaca.markets/docs/paper-trading)
- Fractional shares: "as little as $1 worth of shares for over 2,000 US equities"; market, limit, stop and stop-limit orders with time-in-force `day`; no short sales; use either `qty` or `notional`; executed by Alpaca "on a principal or riskless principal basis" — [Alpaca fractional trading docs](https://docs.alpaca.markets/docs/fractional-trading)
- Fractional trading covers pre-market (4:00–9:30am ET), post-market (4:00–8:00pm ET) and overnight (8:00pm–4:00am ET) for eligible symbols — [Alpaca fractional trading docs](https://docs.alpaca.markets/docs/fractional-trading)
- 24/5 trading runs 8:00pm ET Sunday to 8:00pm ET Friday; Trading API accounts are enabled by default; only limit orders with `day` or `gtc` time-in-force are accepted overnight; eligible assets carry an `overnight_tradable` attribute — [Alpaca 24/5 trading docs](https://docs.alpaca.markets/docs/245-trading); launch for the Trading API was reported February 2026 — [Crowdfund Insider](https://www.crowdfundinsider.com/2026/02/259268-alpaca-introduces-24-5-trades-for-trading-api-providing-almost-round-the-clock-access/)
- Market data plans: Basic is free with IEX-only real-time, 30 websocket symbols, 200 historical calls/min, history since 2016 with a restriction on the latest 15 minutes; Algo Trader Plus is $99/month with all US exchanges, unlimited websocket symbols, 10,000 calls/min — [Alpaca market data docs](https://docs.alpaca.markets/docs/about-market-data-api)
- Trading API limit is 200 requests per minute per account, on both live and paper; exceeding it returns HTTP 429 — [Alpaca support: usage limit](https://alpaca.markets/support/usage-limit-api-calls); a data subscription does not raise it (Alpaca staff forum reply) — [Alpaca forum](https://forum.alpaca.markets/t/is-there-a-way-to-increase-the-200-min-api-call-limit-for-the-trading-endpoint/18110)
- Alpaca routes to wholesalers and is paid for order flow. In April 2026, non-directed S&P 500 stock orders went 35.3% to Citadel Securities, 33.0% to Jane Street, 27.0% to Virtu and 4.7% to GTS; net payment received on market orders was about 73–95 cents per hundred shares for S&P 500 stocks and about 13–19 cents per hundred shares for non-S&P 500 stocks — [Alpaca SEC Rule 606 report, Q2 2026](https://files.alpaca.markets/disclosures/library/SEC+606a1+-+2026Q2.pdf)
- Under the Virtu arrangement, marketable orders filled in the core session earn Alpaca "12% of the spread per share, capped at 5 cents per share"; extended-hours fills outside the core session earn no payment — [Alpaca SEC Rule 606 report, Q2 2026](https://files.alpaca.markets/disclosures/library/SEC+606a1+-+2026Q2.pdf)
- FINRA's March 2025 action found Alpaca failed to disclose specific details of its payment-for-order-flow arrangements in its Rule 606(a)(1) report (as summarised in search results; document not read in full) — [FINRA SD-2436 Alpaca](https://finra.org/sites/default/files/2025-03/SD-2436-Alpaca-03-06-2025.pdf)
- 2026 incidents on Alpaca's status page (dates as summarised by search, not individually verified): Jan 12 elevated error rates; Mar 12 orders intermittently not filled; May 22 partial Trading API outage of about five minutes; Jun 11 orders rejected by a venue after a disconnection; Jul 31 overnight trading paused after a venue notional limit was exceeded; Nov 12 options orders wrongly marked rejected/cancelled. There is also an incident titled "Investigating Issue with Double Executions" — [Alpaca status page](https://status.alpaca.markets/); [overnight incident](https://status.alpaca.markets/incidents/8qc854324l85); [double executions incident](https://status.alpaca.markets/incidents/wy443l1k5rrz)
- Official Python SDK `alpaca-py` latest release 0.45.0 on 2026-11-05 (5 releases in 2026) — [PyPI alpaca-py](https://pypi.org/project/alpaca-py/)

#### Interactive Brokers
- IBKR Pro Fixed: USD 0.005 per share, minimum USD 1.00 per order; Tiered: USD 0.0005–0.0035 per share; IBKR Lite: commission-free for US exchange-listed stocks/ETFs (from search extract of IBKR's page; the page itself returned 403) — [IBKR commissions](https://investors.interactivebrokers.com/en/pricing/commissions-home.php)
- "Clients with fully open and funded accounts may use our Web API and our TWS API immediately, without any onboarding or approval process" — [IBKR third-party FAQ](https://www.interactivebrokers.com/docs/third-party-integrations/general-third-party-frequently-asked-questions)
- The Client Portal (Web) API "supports only IBKR Pro accounts" (search extract; that doc page may be an older version) — [IBKR Web API v1 requirements](https://www.interactivebrokers.com/docs/web-api/web-api-v-1-0-documentation/requirements-limitations/introduction)
- A paper trading account "will not be opened until your account has been funded"; paper accounts have separate credentials — [IBKR paper account FAQ](https://www.interactivebrokers.com/support/faq/content/37128282); [IBKR Web API paper docs](https://www.interactivebrokers.com/docs/web-api/authentication/paper)
- The TWS API requires the user to first log in to TWS or IB Gateway (desktop applications); the TWS API order rate limit is 50 orders per second — [IBKR API solutions](https://investors.interactivebrokers.com/en/trading/ib-api.php)
- Market data: free real-time streaming for US-listed stocks/ETFs from Cboe One and IEX, which is non-consolidated and does not show the NBBO; snapshot quotes cost USD 0.01 each with a USD 1.00 monthly waiver; the "US Securities Snapshot and Futures Value Bundle" is USD 10/month with a USD 30 commission waiver threshold; 100 concurrent market-data lines by default — [IBKR market data pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php)
- An IBKR docs page was quoted in search results as saying "Interactive Brokers APIs do not support fractional or cash quantity trading with exception to Cryptocurrencies and Forex trading" (page returned 403 when fetched directly, so unverified and undated) — [IBKR order types notes and limitations](https://www.interactivebrokers.com/docs/general/order-types/notes-limitations/introduction)
- Community Python clients: `ib_insync` last released 2023-07-02; its successor `ib_async` last released 2025-12-08 (no 2026 release) — [PyPI ib_insync](https://pypi.org/project/ib_insync/); [PyPI ib_async](https://pypi.org/project/ib_async/)

#### Tradier
- Plans: Lite $0/month, Pro $10/month, Pro Plus $35/month; API access included on all; stocks cost $0.35 per trade on Lite and $0.00 on Pro/Pro Plus (verify: this is how the pricing page read on 2026-11-23) — [Tradier pricing](https://tradier.com/individuals/pricing)
- Account minimum $0; inactivity fee $50/year for accounts with fewer than 2 trades per year; SEC fee $0.00002060 per $1 sold; TAF shown as $0.00 for 10/1/2026–12/31/2026; a "trade reporting & processing" fee of $0.000054 per equivalent share — [Tradier pricing](https://tradier.com/individuals/pricing)
- "The sandbox is a paper trading account to test your integration with our API, including working with delayed market data and paper trades"; "we do not offer a delayed streaming endpoint for paper trading"; paper accounts are created by brokerage account holders in Tradier Dash (search extract; page returned 404 on direct fetch) — [Tradier docs FAQ](https://docs.tradier.com/docs/faq)

#### Charles Schwab Trader API
- The "Trader API – Individual" product is for a personal-use application on your own self-directed account and needs a developer account plus a separately reviewed access request (secondary guides; developer.schwab.com returned 403) — [Unofficial guide (Medium)](https://medium.com/@carstensavage/the-unofficial-guide-to-charles-schwabs-trader-apis-14c1f5bc1d57)
- The refresh token expires after 7 days and cannot be extended, so an unattended bot needs a manual re-login weekly — [schwab-api client README](https://unpkg.com/@sudowealth/schwab-api@2.1.1/README.md); [Unofficial guide (Medium)](https://medium.com/@carstensavage/the-unofficial-guide-to-charles-schwabs-trader-apis-14c1f5bc1d57)
- Schwab's public Trader API pages list only Production products and none mention paperMoney (third-party guide, lower quality) — [QuantVPS Schwab API guide](https://www.quantvps.com/blog/schwab-api-thinkorswim-guide)
- Community Python client `schwab-py` latest release 1.6.0 on 2026-11-15 — [PyPI schwab-py](https://pypi.org/project/schwab-py/)

#### tastytrade
- Stocks and ETFs: $0 opening and $0 closing commission; fractional shares listed at $0; exchange, clearing and regulatory fees still apply — [tastytrade pricing](https://tastytrade.com/pricing/)
- Sandbox: base URL `api.cert.tastyworks.com`; "resets every 24 hours, clearing trades, transactions and positions while leaving users and accounts intact"; separate OAuth credentials from production — [tastytrade sandbox docs](https://developer.tastytrade.com/docs/sandbox)
- Sandbox fills are simulated at the quote mid price rounded to the tick (up for a buy, down for a sell); larger orders fill in steps one tick worse each; REST `/market-data` and `/market-metrics` return HTTP 502 in the sandbox; the docs suggest reading market data from production and sending orders to the sandbox — [tastytrade sandbox docs](https://developer.tastytrade.com/docs/sandbox)
- A community SDK's docs say the official sandbox "only supports a few underlyings" with no control over fills (version-12 docs, may be outdated) — [tastyware SDK paper docs](https://tastyworks-api.readthedocs.io/en/v12.4.0/paper.html); QuantConnect's docs say the tastytrade API does not support paper trading — [QuantConnect tastytrade docs](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages/tastytrade)

#### Public.com
- The Individual API is for "personal, non-commercial use" (program terms dated February 2026); access is requested and approved by email; Public says the API "is free to use", but the terms let Public charge additional trading fees or change rebates for API trades — [Public API](https://public.com/api); [Public Individual API Program terms](https://public.com/documents/individual-api-program)
- Rate limit 10 requests per second per account; fractional and dollar orders for market and limit orders with a $5 minimum and $250,000 maximum in regular hours; extended-hours orders must be whole shares; sessions: `EXTENDED` (4:00am–8:00pm ET) and `TWENTY_FOUR_HOURS` (24/5); order types include market, limit, stop, stop-limit, MOC/LOC, bracket/OCO/OTO — [Public API FAQ](https://public.com/api/docs/faq)
- The FAQ mentions no paper-trading or sandbox environment — [Public API FAQ](https://public.com/api/docs/faq)
- Official Python SDK `publicdotcom-py` first released 2025-10-17; latest 0.2.1 on 2026-11-19 — [PyPI publicdotcom-py](https://pypi.org/project/publicdotcom-py/)

#### Webull OpenAPI
- Trading API covers US stocks, options, futures, crypto and event contracts; fractional shares supported for stocks; extended-hours and overnight sessions for stocks — [Webull Trading API overview](https://developer.webull.com/apis/docs/trade-api/overview)
- Rate limits: place/replace/cancel 600 per 60s; account balance and positions 2 per 2s; order history/detail 2 per 2s; instruments 60 per 60s — [Webull Trading API overview](https://developer.webull.com/apis/docs/trade-api/overview)
- Level 1 streaming quotes for US stocks are advertised at no charge; other data needs a subscription "specifically enabled for OpenAPI", separate from app subscriptions; the sandbox gives 15-minute delayed data by default — [Webull OpenAPI](https://www.webull.com/open-api); [Webull Market Data API overview](https://developer.webull.com/apis/docs/market-data-api/overview/)
- Paper trading: Webull announced "OpenAPI multi-asset simulation" — [Barchart press release](https://www.barchart.com/story/news/3382513/webull-unveils-enhanced-paper-trading-experience-with-professional-grade-and-openapi-multi-asset-simulation); a third-party guide says sandbox keys are auto-approved within minutes — [QuantVPS Webull guide](https://www.quantvps.com/blog/webull-api-guide); contradicted by QuantConnect's statement that the Webull API does not support paper trading — [QuantConnect Webull docs](https://www.quantconnect.com/docs/v2//cloud-platform/live-trading/brokerages/webull)
- Official Python SDK first released 2025-09-06; latest 3.1.1 on 2026-11-23 (30 releases in 2026) — [PyPI webull-openapi-python-sdk](https://pypi.org/project/webull-openapi-python-sdk/)

#### E*TRADE
- Separate keys are required for sandbox and production; an Individual Key works with any of your E*TRADE accounts — [E*TRADE developer getting started](https://developer.etrade.com/getting-started)
- "By default the access token expires at midnight US Eastern time", after which OAuth must be repeated or the token renewed — [E*TRADE authorization API docs](https://apisb.etrade.com/docs/api/authorization/get_access_token.html)
- A third-party R client says the token is inactivated after two hours without API calls — [etrader R package docs](https://rdrr.io/cran/etrader/man/etrd_auth_manage_token.html); an aggregator says E*TRADE "enforces quite a strict rate-limit per connection" — [SnapTrade E*TRADE FAQ](https://support.snaptrade.com/E-Trade-830ffc2d25154ae3aa536d9859de7386)

#### Robinhood
- The official, documented Robinhood API is the Crypto Trading API (US crypto customers) — [Robinhood Crypto Trading API](https://robinhood.com/us/en/support/articles/crypto-api/)
- Community libraries for stocks rely on reverse-engineered private endpoints: "Robinhood does not publish official API documentation for stocks/options" — [pyhood endpoint reference](https://jamestford.github.io/pyhood/api-endpoints/)
- On May 27, 2026 Robinhood announced "Agentic Trading": AI agents connect through Robinhood's Trading MCP server to a separate agentic account funded by the user; the beta supports equities only; no public REST API, fees, order limits or paper mode are described in the announcement — [Robinhood newsroom](https://robinhood.com/us/en/newsroom/robinhood-is-now-open-to-agents/)

### Inferences
- For a $1,000 Python user who wants to start in paper trading with no deposit, Alpaca is the path of least resistance: it is the only one of the nine where the sources show an email-only paper account, a $1 minimum order and an official, actively released Python SDK. This is a fit judgement, not a claim that Alpaca executes better.
- Alpaca paper results will be optimistic compared with live trading: fills ignore quoted size, queue position, fees and latency, and a paper-only account sees only IEX quotes (a single exchange), so resting limit orders and anything relying on tight spreads will look better on paper than live.
- Per-order minimum commissions punish small orders: IBKR Pro Fixed's $1.00 minimum is 1% of a $100 order per side, and Tradier Lite's $0.35 is 0.35% of a $100 order per side, versus $0 at Alpaca, tastytrade and Tradier Pro (which costs $10/month, i.e. 1% of a $1,000 account per month).
- Schwab (7-day token) and E*TRADE (midnight token expiry) need a human login step at least weekly/daily, which makes them poor choices for an unattended bot.
- With the pattern-day-trader rule replaced, a sub-$25,000 margin account may be able to day trade, but only once the specific broker has implemented the new intraday margin standards; this must be confirmed per broker before designing an intraday strategy.

### Gaps
- Alpaca's account minimum, cash-versus-margin thresholds, whether it has implemented the new intraday margin rule, and its current regulatory-fee page (the old URL returned 404) were not confirmed.
- IBKR: whether IBKR Lite can use the TWS API, whether fractional orders work through the API (one doc extract says no; not verified), account minimum, paper-fill realism, and pacing rules could not be read because IBKR pages returned 403.
- Tradier: numeric rate limits, fractional support, extended-hours rules and real-time data source for account holders were not found (docs pages returned 404).
- Schwab: no primary-source confirmation of commissions, rate limits, fractional support or the absence of a sandbox (developer portal returned 403).
- Stock commissions at Public and Webull through the API, and E*TRADE's commissions, fractional support and numeric rate limits, were not found.
- Account-restriction or account-closure complaints: no reliable sources found for any broker; only Alpaca's own status-page incidents were located. Outage history for the other brokers was not researched.
- Robinhood's agentic account: fees, limits and whether a non-AI script may use the MCP server are not documented in the announcement.

## 2. The real cost of a round trip in liquid US stocks/ETFs for small orders

### Takeaway
For small orders in large, liquid US stocks the all-in round-trip cost is a few hundredths of a percent (about 0.05% for S&P 500 stocks, well under 0.01% for SPY/QQQ at quoted spreads), roughly 30 to several hundred times cheaper than a 1.4% crypto round trip; the smallest third of US stocks cost close to 1% per round trip, which is in the same range as the crypto figure.

### Cited Findings

#### Regulatory fees (sell side only)
- SEC Section 31 fee: $20.60 per million dollars of sales, effective April 4, 2026; it stays until 60 days after the SEC's fiscal-2027 appropriation is enacted — [SEC fee rate advisory 2026-2](https://www.sec.gov/rules-regulations/fee-rate-advisories/2026-2). Tradier's pricing page shows the same rate ($0.00002060 per $1 sold) — [Tradier pricing](https://tradier.com/individuals/pricing)
- FINRA Trading Activity Fee (TAF) scheduled rate for 2026: $0.000195 per share sold, maximum $9.79 per trade (2024–2025: $0.000166, max $8.30) — [FINRA fee adjustment schedule](https://www.finra.org/rules-guidance/rule-filings/sr-finra-2024-019/fee-adjustment-schedule)
- FINRA filed SR-FINRA-2026-021 to "temporarily pause assessment of the Trading Activity Fee" for transactions from October 1, 2026 through December 31, 2026; the filing's documents include a "Notice of Filing and Immediate Effectiveness" — [FINRA SR-FINRA-2026-021](https://www.finra.org/rules-guidance/rule-filings/sr-finra-2026-021). Tradier's pricing page shows TAF as $0.00 for 10/1/2026–12/31/2026, consistent with the pause being in effect — [Tradier pricing](https://tradier.com/individuals/pricing)
- A companion filing (SR-FINRA-2026-020) would keep FINRA fees at 2026 rates from January 1, 2027 through December 31, 2028 instead of the previously scheduled increases — [FINRA SR-FINRA-2026-020](https://www.finra.org/rules-guidance/rule-filings/sr-finra-2026-020)

#### Bid-ask spreads
- SPY and QQQ quoted spreads: Trackinsight shows 1-year average spreads of about 0.26 bps (SPY) and 0.34 bps (QQQ) — [Trackinsight SPY vs QQQ](https://www.trackinsight.com/en/compare-etfs/SPY,QQQ); ETF Central lists 0.002% (SPY) and 0.004% (QQQ) — [ETF Central](https://www.etfcentral.com/compare-etfs/SPY-vs-QQQ); State Street lists SPY's 30-day average spread as 0.0051% — [SSGA](https://www.ssga.com/us/en/intermediary/insights/optimizing-trade-execution-etfs-of-all-levels-of-liquidity). The sources differ in method and date; none gives a November 2026 median.
- Trading the whole S&P 500 "incurs spread costs of just over 4.5 bps" — [Nasdaq](https://www.nasdaq.com/articles/sampling-sp-500-minimize-spreads)
- Academic study of all SEC Rule 605 reports, January 2019–March 2022 (Dyhrberg, Shkilko and Werner, "The Retail Execution Quality Landscape", July 4, 2023), volume-weighted, for marketable orders executed by wholesalers (where retail orders go) — [NBER conference paper](https://conference.nber.org/conf_papers/f187847/f187847.pdf):

| Stock group (avg. price) | Quoted spread | Effective spread retail paid | Orders price-improved |
|---|---|---|---|
| S&P 500 ($146) | 8.28 bps | 4.62 bps | 75% |
| Non-S&P 500, largest third ($56) | 24.16 bps | 15.96 bps | 69% |
| Non-S&P 500, middle third ($15) | 58.72 bps | 42.84 bps | 64% |
| Non-S&P 500, smallest third ($8) | 118.46 bps | 93.63 bps | 63% |
| All 3,241 ETFs ($42) | 27.95 bps | 17.97 bps | 75% |

- In that study the effective spread is "twice the signed difference between the traded price and the midpoint", i.e. it already represents the cost of buying and then selling — [NBER conference paper](https://conference.nber.org/conf_papers/f187847/f187847.pdf)
- Older SEC staff data (2013): 25% of small-cap stocks (under $1bn) had mean quoted spreads of 15 cents or more — [SEC small cap liquidity study](https://www.sec.gov/files/marketstructure/research/small_cap_liquidity.pdf)

#### Payment for order flow and price improvement
- "A portion of the spread is retained by the wholesaler, another portion goes to the retail broker as payment for order flow (PFOF), and yet another portion is passed on to the retail trader as price improvement" — [NBER conference paper](https://conference.nber.org/conf_papers/f187847/f187847.pdf)
- The average retail order received price improvement of 24% of the quoted spread; in S&P 500 stocks, 44%; on exchanges the figures were 3% and 6%. Retail orders at wholesalers paid 76% of the quoted spread on average — [NBER conference paper](https://conference.nber.org/conf_papers/f187847/f187847.pdf)
- Critics argue wholesaler price improvement "tends to be de minimis"; the paper disputes this — [NBER conference paper](https://conference.nber.org/conf_papers/f187847/f187847.pdf)
- Alpaca's own payment example: 12% of the spread per share on marketable core-session orders routed to Virtu, capped at 5 cents per share — [Alpaca SEC Rule 606 report, Q2 2026](https://files.alpaca.markets/disclosures/library/SEC+606a1+-+2026Q2.pdf)
- Amended SEC Rule 605 (adopted March 2024) had a compliance date of August 1, 2026, with a further price-improvement statistic due November 1, 2026, so richer execution-quality reports should now be appearing (dates as reported by an advocacy source) — [Robinhood policy blog, Sep 28, 2026](https://robinhood.com/us/en/policy/blog/rule-605-and-the-limits-of-efficacy/)
- Alpaca paper trading does not simulate price improvement or regulatory fees — [Alpaca paper trading docs](https://docs.alpaca.markets/docs/paper-trading)

### Inferences
- Worked example, $1,000 bought then sold at a $0-commission PFOF broker (arithmetic on the cited figures; the spread data is 2019–early 2022 and broker rounding of fees to whole cents is not included):
  - S&P 500 stock: spread cost about 4.6 bps = $0.46; SEC fee on the $1,000 sale = $0.02; TAF $0 until Dec 31, 2026 (otherwise a fraction of a cent on a few shares). Total about $0.48, or 0.05%.
  - SPY/QQQ at quoted spreads of roughly 0.2–0.5 bps: about $0.02–$0.05 of spread plus $0.02 SEC fee, i.e. about 0.004–0.007%.
  - Smallest-third stocks: about $9.36 of spread, or 0.94%.
  - A 1.4% round trip on $1,000 is $14.00. So the same trade is about 30 times cheaper in an S&P 500 stock, on the order of 200–300 times cheaper in SPY/QQQ, about 3 times cheaper in mid-sized non-index stocks (0.43%), and only about 1.5 times cheaper in the smallest stocks.
- The spread is therefore not the binding cost for a small account in liquid names; per-order commissions (where charged), data subscriptions and hosting, which are fixed dollar amounts, weigh far more on $1,000. A $10/month fee is 1% of the account every month.
- A strategy that only survives on paper because fills happen at the quote with no slippage will lose its edge live in small caps, where the real spread is 50–100+ bps.
- Overnight and extended-hours spreads are wider than regular-session spreads, and Alpaca's routing earns no payment there; the figures above are regular-hours figures only.

### Gaps
- No current (2026) primary measurement of spreads for individual mega-caps (e.g. AAPL, NVDA) or for small caps in basis points was found; the best cross-sectional numbers are 2019–March 2022.
- No source isolated execution quality for very small or fractional orders, or for API-routed retail flow specifically.
- No reliable source was found on overnight-session (8pm–4am ET) spreads.
- The Consolidated Audit Trail (CAT) fee and whether any of these brokers pass it through was not researched.
- Whether a fiscal-2027 Section 31 rate has been announced was not found; $20.60 per million was the latest advisory located.

## 3. Historical and live market data a small trader can get free or cheaply

### Takeaway
Free data is enough to start: Alpaca gives minute bars back to 2016 with a free account, and yfinance gives daily history but only 7 days of 1-minute bars; the gaps are full-market (SIP) real-time quotes ($99–$199/month) and survivorship-bias-free history with delisted stocks, which costs from roughly $79–$500 one-off or about $199/month.

### Cited Findings

| Source | Free tier | Cheapest paid | Notes |
|---|---|---|---|
| Alpaca | IEX real-time, history since 2016, 200 calls/min, 30 websocket symbols | $99/mo for all exchanges, 10,000 calls/min | Default bar adjustment is `raw` |
| Massive (formerly Polygon.io) | 5 calls/min, 2 years, end-of-day | Starter $29/mo; Advanced $199/mo real-time, 20+ years | Developer tier $79/mo per secondary source |
| Tiingo | 50 requests/hr, 1,000/day, 500 symbols/mo | Power $30/mo | Intraday is IEX-only |
| Alpha Vantage | 25 requests/day | $49.99/mo (75 requests/min) | Real-time US data reportedly from $99.99/mo |
| Twelve Data | 800 credits/day, 8/min | Conflicting ($99 vs $229/mo "Pro") | |
| Databento | $125 signup credit | Standard $199/mo incl. full OHLCV-1m history | Live data needs a subscription |
| FirstRate Data | Samples | About $500 one-off (secondary) | 16,322 tickers incl. 7,000+ delisted, from 2000 |
| Stooq | Free daily; short intraday | n/a | CAPTCHA and undisclosed daily limit |
| yfinance | Free, unofficial | n/a | 1-minute data: last 7 days only |

- Alpaca Basic (free): IEX-only real-time, 30 websocket symbols, 200 historical calls/min, history since 2016 with a limit on the most recent 15 minutes; Algo Trader Plus $99/month: all US exchanges, no restriction, 10,000 calls/min. Sources are the CTA and UTP consolidated streams for the paid plan — [Alpaca market data docs](https://docs.alpaca.markets/docs/about-market-data-api)
- Alpaca historical bars default to `adjustment=raw`; options are raw, split, dividend, spin-off and all; a November 2, 2026 changelog made the parameter an enum array — [Alpaca stock bars reference](https://docs.alpaca.markets/us/reference/stockbars); [Alpaca changelog 2026-11-02](https://docs.alpaca.markets/in-giftcity/changelog/2026-11-02-adjustment-8f7882f)
- User reports of Alpaca adjustment errors: adjustment values returning identical data, wrong or missing split ratios (some tied to spin-offs), and a suspect dividend adjustment for an ex-date in February 2026 — [Alpaca forum: adjustment not working](https://forum.alpaca.markets/t/v2-api-bars-request-adjustment-not-working/12893); [Alpaca forum: incorrect split ratios](https://forum.alpaca.markets/t/incorrect-historical-data-of-stock-split-ratios/17839); [Alpaca forum: dividend adjustment](https://forum.alpaca.markets/t/bad-data-incorrect-price-adjustment-for-cash-dividend/18614) (user reports, lower quality)
- Massive: Stocks Advanced is $199/month for individuals with real-time data and "20+ years of history" — [Massive pricing](https://massive.com/pricing). Basic is free at 5 calls/min with 2 years of end-of-day history; Starter is $29/month; paid plans have unlimited API calls (prices checked October 23, 2026 on Massive's own comparison page) — [Massive vs Tiingo](https://massive.com/compare/massive-vs-tiingo)
- Polygon.io rebranded to Massive.com effective October 30, 2025, with existing keys and the api.polygon.io base still supported; a Developer plan at $79/month is cited by third parties only — [apis.io Massive profile](https://apis.io/finops/massive-com/polygon-finops/) (secondary)
- Tiingo: free tier 50 requests/hour, 1,000/day, 1 GB/month; Power $30/month with 10,000/hour and 100,000/day; intraday feed is IEX-sourced — [Tiingo IEX API](https://api.tiingo.com/products/iex-api); 500 unique symbols per month on free — [Massive vs Tiingo](https://massive.com/compare/massive-vs-tiingo)
- Alpha Vantage: free tier is 25 requests per day; premium runs from $49.99/month (75 requests/min) to $249.99/month (1,200 requests/min) — [Alpha Vantage premium](https://alphavantage.co/premium); [Macroption limits summary](https://www.macroption.com/alpha-vantage-api-limits/) (secondary)
- Twelve Data: free Basic plan has 800 API credits per day and 8 per minute; paid pricing conflicts across Twelve Data's own pages ($229/month vs "from $99/month" for Pro) — [Twelve Data pricing](https://twelvedata.com/pricing)
- Databento: $125 in free credits at signup (expire after 6 months); Standard plan launched at $199/month in January 2025 with "unlimited access to the entire history of OHLCV-1s/-1m" for US equities; live data requires a subscription; historical data can also be bought per use with no subscription — [Databento pricing plan changes](https://databento.com/blog/upcoming-changes-to-pricing-plans-in-january-2025); [Databento usage pricing FAQ](https://databento.com/docs/faqs/usage-pricing-and-data-credits)
- FirstRate Data: 1-minute to daily bars for 16,322 US tickers including 7,000+ delisted, January 2000 to October 2026; one month of updates included, then $59.95/month — [FirstRate stock data](https://firstratedata.com/stock-data); the roughly $500 one-off price is a competitor's figure — [MarketParquet comparison](https://marketparquet.com/vs/firstrate) (lower quality)
- MarketParquet advertises a 26-year US archive for $79 one-off plus $15/month for updates (vendor claim, not independently verified) — [MarketParquet](https://marketparquet.com/historical-market-data)
- Stooq: an API key obtained via CAPTCHA is required as of early 2026 and an undisclosed daily hit limit applies; intraday depth reported as about 7–9 months hourly and 15 days–1 month for 5-minute bars; bulk files need a manual CAPTCHA (all third-party) — [apis.io Stooq](https://apis.io/apis/stooq/stooq-q-api/); [QuantStart](https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data); [squihd project](https://github.com/ryanbranch/squihd)
- yfinance intraday limits: 1-minute data covers at most 7 days (within the last 30); 60m/1h up to 730 days; other intraday intervals up to 60 days — [yfinance wiki](https://github.com/ranaroussi/yfinance/wiki/Ticker)
- yfinance users hit `YFRateLimitError` ("Too Many Requests"), sometimes for more than 24 hours; Yahoo publishes no limits — [yfinance discussion 2431](https://github.com/ranaroussi/yfinance/discussions/2431); [yfinance issue 2422](https://github.com/ranaroussi/yfinance/issues/2422)
- yfinance remains actively released: version 1.8.0 on 2026-11-03, 12 releases in 2026 — [PyPI yfinance](https://pypi.org/project/yfinance/)
- Yahoo "can change or shut off its APIs at any time, and bars commercial use without permission" (competitor's characterisation) — [Massive vs yfinance](https://massive.com/compare/massive-vs-yfinance) (lower quality)
- Survivorship-bias-free options: EODHD lists 60,191 delisted US symbols as of September 2026 — [EODHD delisted data](https://eodhd.com/financial-apis/review-delisted-stock-companies-data); Norgate's cheapest survivorship-bias-free tier is quoted at $630/year in an undated forum post — [QuantConnect forum](https://www.quantconnect.com/forum/discussion/21226/would-you-pay-for-cheap-point-in-time-s-amp-p-500-data-survivorship-bias-free/) (lower quality)
- QuantConnect's free tier includes minute, hour and daily equity data with corporate fundamentals inside its cloud backtester — [QuantConnect pricing](https://www.quantconnect.com/pricing)
- IBKR clients get free non-consolidated real-time US stock data (Cboe One and IEX) — [IBKR market data pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php)

### Inferences
- A workable zero-cost stack for paper trading liquid ETFs is Alpaca free data (minute bars since 2016, IEX real-time) for both backtest and live signals, with yfinance only as a cross-check for daily adjusted prices.
- IEX is one exchange with a small share of volume, so IEX-only bars will show lower volume and occasionally different highs/lows than consolidated bars; a strategy tuned on SIP history and run live on IEX quotes (or the reverse) is being tested on different data than it trades on.
- Because Alpaca's default is unadjusted prices, a backtest that forgets the adjustment parameter will see splits as crashes; given the forum reports of wrong ratios, adjusted series should be spot-checked against a second source around known split and dividend dates.
- Any free source that lists only currently trading tickers (yfinance, a broker's active-asset list) produces survivorship bias in stock-picking backtests; this matters much less for a bot that trades a fixed handful of large ETFs.

### Gaps
- Exact wording of Alpaca's 15-minute restriction on the free plan (the fetched summary was ambiguous) and how far back minute bars go per symbol were not confirmed beyond "since 2016".
- Massive's current Developer plan price and the history depth and delay of each tier could not be read from the official pricing page (it rendered only the Advanced plan).
- Tiingo's intraday history depth, Alpha Vantage's intraday depth per plan, and Twelve Data's true paid prices were not confirmed.
- Yahoo's actual terms-of-use text on personal versus commercial use was not retrieved.
- Stooq's limits come only from third parties; nothing on Sharadar was found; Norgate and EODHD current prices were not confirmed.
- Whether Alpaca, Massive or Tiingo return delisted symbols in historical queries was not verified.

## 4. Open-source Python frameworks for backtesting and live/paper trading of stocks

### Takeaway
As of November 2026 every framework on the list except backtrader is still being released (backtrader's last PyPI release was April 2023); Lumibot and QuantConnect LEAN are the two that run the same strategy code in backtest and against US stock brokers including Alpaca, while vectorbt, bt, Backtesting.py and zipline-reloaded are backtest-only and NautilusTrader's only stock broker adapter is Interactive Brokers.

### Cited Findings

Release data pulled from the PyPI JSON API on 2026-11-23:

| Framework | Latest release | Releases in 2026 | Licence (PyPI) | Live/paper stock brokers | Status |
|---|---|---|---|---|---|
| backtrader | 1.9.78.123, 2023-04-19 | 0 | GPLv3+ | Interactive Brokers (IbPy), Oanda, Visual Chart | Unmaintained on PyPI |
| vectorbt (open source) | 1.2.1, 2026-11-11 | 8 | not listed | None (research/backtest) | Maintained |
| zipline-reloaded | 3.2.1, 2026-10-25 | 2 | not listed | None documented | Maintained |
| QuantConnect LEAN (`lean` CLI) | 1.0.234, 2026-11-18 | 11 | not listed | IBKR, Alpaca, Tradier, Schwab, tastytrade, Public, Webull, TradeStation and more | Maintained |
| NautilusTrader | 1.231.0, 2026-08-02 | 17 | LGPL-3.0-or-later | Interactive Brokers only | Maintained |
| Lumibot | 4.6.95, 2026-11-22 | 201 | GPL-3.0 | Alpaca, IBKR (REST and legacy TWS), Tradier, Schwab, Tradovate | Maintained |
| bt | 1.4.1, 2026-10-10 | 10 | MIT | None (backtest) | Maintained |
| Backtesting.py | 0.6.6, 2026-07-22 | 1 | AGPL-3.0 | None (backtest) | Maintained, slow cadence |
| Freqtrade | 2026.10, 2026-10-30 | 11 | GPLv3 | Crypto only | Maintained |
| Hummingbot | 20261118, 2026-11-18 | 32 | Apache 2.0 | Crypto venues | Maintained |

Sources: [backtrader](https://pypi.org/project/backtrader/), [vectorbt](https://pypi.org/project/vectorbt/), [zipline-reloaded](https://pypi.org/project/zipline-reloaded/), [lean](https://pypi.org/project/lean/), [nautilus_trader](https://pypi.org/project/nautilus_trader/), [lumibot](https://pypi.org/project/lumibot/), [bt](https://pypi.org/project/bt/), [backtesting](https://pypi.org/project/backtesting/), [freqtrade](https://pypi.org/project/freqtrade/), [hummingbot](https://pypi.org/project/hummingbot/)

- backtrader: 23.8k GitHub stars, 64 open pull requests; README lists live support for Interactive Brokers (via IbPy), Visual Chart and Oanda, and states Python >= 3.2 — [backtrader GitHub](https://github.com/mementum/backtrader). The Alpaca bridge `alpaca-backtrader-api` was last released 2022-01-02 — [PyPI alpaca-backtrader-api](https://pypi.org/project/alpaca-backtrader-api/)
- backtrader look-ahead defaults: market orders execute "with the 1st tick of the next bar (namely the open price)"; cheat-on-close and cheat-on-open both default to False; slippage is zero unless set; orders fill completely regardless of bar volume unless a filler is set — [backtrader broker docs](https://www.backtrader.com/docu/broker/)
- Backtesting.py: new orders execute on the next candle's open, or the current candle's close if `trade_on_close=True`; inside `next()` only data up to the current bar is visible — [Backtesting.py API docs](https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html)
- zipline-reloaded: described as "Stream-based: Process each event individually, avoids look-ahead bias"; open orders are filled after `handle_data()` finishes, subject to commission, a slippage model and a volume check; the tutorial covers backtesting only and its default bundle is the old Quandl WIKI data — [zipline-reloaded tutorial](https://zipline.ml4trading.io/beginner-tutorial.html)
- vectorbt (open source) is described in its README as "the open-source community edition of VectorBT PRO" — [vectorbt README](https://raw.githubusercontent.com/polakowo/vectorbt/master/README.md). VectorBT PRO costs $25/month, $225/year or $500 lifetime, delivered as access to a private GitHub repository, for "personal, non-commercial use only" — [VectorBT PRO membership](https://vectorbt.pro/become-a-member)
- Lumibot: "Same strategy for backtesting and trading: keep your strategy class; change the data source and broker runner"; assets include stocks, options, futures, forex, crypto and prediction markets; README shows an Alpaca paper-trading setup; backtest data from Yahoo, ThetaData and Polygon — [Lumibot README](https://raw.githubusercontent.com/Lumiwealth/lumibot/dev/README.md)
- Lumibot broker guides: Alpaca, Charles Schwab, Interactive Brokers (Client Portal REST and legacy TWS), Tradier, Tradovate, TopstepX, plus Kalshi, Polymarket and 100+ crypto exchanges via CCXT — [Lumibot brokers](https://lumibot.lumiwealth.com/brokers.all.html)
- QuantConnect cloud live-trading brokerages for US equities: QuantConnect Paper Trading, Interactive Brokers, TradeStation, tastytrade, Public, Alpaca, Charles Schwab, Clear Street, Webull, Tradier (plus crypto and institutional connections) — [QuantConnect brokerages](https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/brokerages)
- QuantConnect Free tier excludes paper trading, live trading (0 live nodes), brokerage integrations, API access and LEAN-CLI local coding; it includes unlimited cloud backtesting on minute/hour/daily data. Researcher is $84/month and allows up to 2 live nodes — [QuantConnect pricing](https://www.quantconnect.com/pricing)
- NautilusTrader integrations: 21 adapters, of which the only brokerage is Interactive Brokers (stable); Databento is a stable data adapter; the rest are crypto exchanges, betting and prediction markets; no Alpaca, Tradier or Schwab adapter is listed — [NautilusTrader integrations](https://nautilustrader.io/docs/latest/integrations/). PyPI describes it as a "Rust-native trading engine with deterministic event-driven architecture", Python >= 3.12 — [PyPI nautilus_trader](https://pypi.org/project/nautilus_trader/)
- Freqtrade's PyPI summary is "Freqtrade - Crypto Trading Bot" — [PyPI freqtrade](https://pypi.org/project/freqtrade/)
- Hummingbot describes itself as for "crypto trading bots across 50+ exchanges" (centralised and decentralised); no stock broker such as Alpaca or Interactive Brokers is listed; Kalshi (a prediction market) does appear — [Hummingbot exchanges](https://hummingbot.org/exchanges/)

### Inferences
- For someone moving a practice bot from crypto to US stocks with Alpaca paper trading, Lumibot is the most direct open-source fit on the evidence here: native Alpaca support, the same class for backtest and live, and very frequent releases. The release count (201 in 2026) also signals fast-moving code, so pinning a version is prudent.
- LEAN supports the widest set of US brokers, but on QuantConnect's cloud any paper or live deployment needs a paid tier, so it is not a free path to paper trading.
- backtrader still works as a backtester but should be treated as frozen: no release since April 2023, an Alpaca bridge frozen since January 2022, and reliance on the old IbPy library.
- Next-bar-open execution is the default protection against look-ahead in backtrader and Backtesting.py; the dangerous switches are `cheat-on-close`/`cheat-on-open` and `trade_on_close=True`. None of these defaults protect against leaks created in the user's own indicator code (for example using the full series to normalise).
- Freqtrade is still crypto-only; Hummingbot is still crypto-focused with no stock brokers, though it has added a prediction market.
- Licence note for anyone who might later share or sell a bot: Lumibot and backtrader are GPL, Backtesting.py is AGPL, bt is MIT.

### Gaps
- GitHub commit, issue and star counts could not be pulled (GitHub API not reachable); only backtrader's repository page was read.
- No source was gathered on the look-ahead protections or fill models of vectorbt, bt, NautilusTrader, Lumibot's price data handling, or LEAN (a QuantConnect forum post about fills at the current bar's close was old and not verified).
- Whether zipline-reloaded has any maintained live-trading bridge was not found.
- LEAN's open-source licence and whether it can paper trade locally against Alpaca without a paid QuantConnect tier were not confirmed.
- vectorbt's and zipline-reloaded's licence fields are blank on PyPI and were not checked elsewhere.

## 5. Cheap always-on hosting for a small bot

### Takeaway
A small bot can run for about $0–$6 a month: a $4–$6 VPS is the simplest reliable choice, free cloud tiers exist but carry reclaim or capacity risks, and GitHub Actions is only suitable for coarse schedules because the minimum interval is 5 minutes and runs can be delayed or dropped.

### Cited Findings

| Option | Cost | Key limits |
|---|---|---|
| DigitalOcean Basic Droplet | $4/mo (512 MiB) or $6/mo (1 GiB) | Per-second billing with monthly cap |
| Google Cloud Free Tier | $0 | One e2-micro, three US regions, 30 GB disk, 1 GB egress/month |
| Oracle Cloud Always Free | $0 | Idle instances can be reclaimed; capacity errors |
| AWS (new accounts) | Credits only | Free plan ends after 6 months or when credits run out |
| GitHub Actions schedule | $0 on public repos | 5-minute minimum, delays, possible dropped runs |
| QuantConnect cloud | $84/mo tier needed for any live or paper node | Free tier has 0 live nodes |
| Raspberry Pi 5 at home | Board $77.50+ (2GB) plus about 3 W of power | Home internet and power reliability |

- DigitalOcean Basic Droplets: $4/month (512 MiB RAM, 1 vCPU, 10 GiB SSD, 500 GiB transfer), $6/month (1 GiB, 25 GiB SSD), $12/month (2 GiB); per-second billing from January 1, 2026 with a monthly cap — [DigitalOcean Droplet pricing](https://www.digitalocean.com/pricing/droplets)
- Hetzner raised prices in 2026: increases of up to 37% from April 1, 2026 — [Tom's Hardware](https://www.tomshardware.com/tech-industry/hetzner-to-raise-prices-by-up-to-37-percent-from-april-1); secondary trackers report the entry CX22 going from EUR 3.29 to EUR 4.49, its CX23 replacement rising to EUR 5.49 after a June 15 increase, and limited availability — [Findstack](https://findstack.com/resources/hetzner-price-increase-2026); [Bitdoze](https://www.bitdoze.com/hetzner-cloud-cost-optimized-plans/) (secondary, figures conflict between sources)
- Google Cloud Free Tier: one non-preemptible e2-micro VM per month in us-west1, us-central1 or us-east1, 30 GB-months of standard persistent disk, 1 GB outbound transfer per month from North America; limits do not roll over; Google may change the offer with 30 days' notice. New users also get a $300 credit valid 90 days — [Google Cloud free features](https://docs.cloud.google.com/free/docs/free-cloud-features)
- Oracle Cloud Always Free: Ampere A1 instances get the first 3,000 OCPU-hours and 18,000 GB-hours per month free (equal to 4 OCPUs and 24 GB running continuously); Oracle may reclaim instances it deems idle, including when 95th-percentile CPU use over 7 days is under 20% — [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm)
- 2026 blog reports say Oracle halved the free ARM allowance to about 2 OCPUs/12 GB without notice; this was not confirmed against Oracle's documentation, which still showed the larger allowance — [Korben](https://korben.info/en/oracle-quietly-cuts-free-arm-offer-in-half.html) (secondary, unconfirmed)
- AWS: accounts created on or after July 15, 2025 get $100 in credits at signup plus up to $100 more for trying services, replacing the old 12-month free tier; the free plan ends at the earlier of 6 months or credit exhaustion — [AWS announcement](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan); [AWS Free Tier FAQs](https://aws.amazon.com/free/faqs/)
- GitHub Actions `schedule`: "The shortest interval you can run scheduled workflows is once every 5 minutes"; the event "can be delayed during periods of high loads", high-load times "include the start of every hour", and "if the load is sufficiently high enough, some queued jobs may be dropped" — [GitHub Actions docs: events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- Scheduled workflows run only from the default branch; in public repositories they are "automatically disabled when no repository activity has occurred in 60 days"; schedules default to UTC but an IANA timezone such as `America/New_York` can now be set — [GitHub Actions docs: events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- GitHub Actions minutes are free on standard runners for public repositories; GitHub Free accounts have historically had 2,000 minutes/month for private repositories — [GitHub Actions billing docs](https://docs.github.com/en/billing/concepts/product-billing/github-actions). Third-party posts say that on October 28, 2026 the allowance became a dollar-based pool ($12/month on Free); not confirmed on GitHub's own pages — [dev.to](https://dev.to/kalemi/github-actions-pricing-changes-in-2026-4g0j) (secondary)
- GitHub announced in December 2025 lower hosted-runner rates from January 1, 2026 and a $0.002/minute platform charge for self-hosted runners in private repositories from March 1, 2026 (whether the latter took effect was not verified) — [GitHub changelog](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/)
- QuantConnect: Free tier has 0 live trading nodes and no paper trading; Researcher tier is $84/month with up to 2 live nodes; node prices are not shown in the fetched pricing text — [QuantConnect pricing](https://www.quantconnect.com/pricing). A third-party review puts the smallest live node (L-MICRO) at $24/month — [newtrading.io review](https://www.newtrading.io/?p=13451) (secondary, unverified)
- Raspberry Pi prices rose repeatedly in 2026 on memory costs: the Pi 5 4GB went from $60 to $70 (February) to $85 (April), and a later report lists the 2GB at $77.50 and the 4GB at $110 (October 2026) — [Tom's Hardware](https://www.tomshardware.com/raspberry-pi/raspberry-pi-5-price-increases-drastically-as-ai-shortage-bites-16gb-version-now-usd205-second-price-increase-in-three-months-over-70-percent-more-expensive-than-original-msrp); [Phoronix](https://www.phoronix.com/news/Raspberry-Pi-5-2GB-Price-77.50); [Raspberry Pi news](https://raspberrypi.com/news/more-memory-driven-price-rises)
- Power draw: Pi 5 idles headless at roughly 2.5–3 W; Pi Zero 2 W at roughly 0.6 W — [raspberry.tips comparison](https://raspberry.tips/en/raspberrypi-tutorials/raspberry-pi-power-consumption-update-2026-all-models-compared); [CNX Software](https://www.cnx-software.com/2021/12/09/raspberry-pi-zero-2-w-power-consumption/) (blog measurements, approximate)

### Inferences
- A bot that only acts on 5-minute-or-slower bars during US market hours needs very little: any 512 MiB–1 GiB Linux box running a Python loop or cron job is enough, so the $4–$6 DigitalOcean tiers or the free Google e2-micro cover it. $6/month is 0.6% of a $1,000 account per month, i.e. more than the trading costs of dozens of round trips in liquid ETFs.
- GitHub Actions is workable only for strategies that tolerate minutes of timing error (for example one rebalance per day or per hour, scheduled off the top of the hour); it is not suitable for anything that must act within a minute, and it cannot hold a websocket open. A public repository is free but exposes strategy code (keys must be in secrets); a private one is limited by the monthly allowance.
- A Pi 5 at about 3 W uses roughly 26 kWh a year, which is a few dollars of electricity at typical US residential rates (rate assumed, not sourced); after the 2026 price rises the board plus power supply, case and storage costs about as much as 1.5–2 years of a $4–$6 VPS, and it adds home power and internet as failure points.
- Oracle's free ARM tier is the most generous on paper but the least dependable for an always-on bot: an idle, low-CPU bot is exactly the profile its reclaim policy targets, and the reported 2026 allowance cut is unresolved.
- QuantConnect cloud is the most expensive route for a $1,000 account ($84/month minimum for any paper or live deployment, before node costs).

### Gaps
- Current official Hetzner and Vultr entry prices could not be read (pages returned 403/404); Hetzner figures are from conflicting secondary trackers.
- QuantConnect live-node prices were not available from the official page text.
- GitHub's own statement of the current free private-repo allowance after the reported October 2026 change, and how per-run minute rounding applies, were not confirmed.
- No sourced US electricity rate was gathered, so the Pi running-cost figure is only an order-of-magnitude estimate.
- Broker-hosted options other than QuantConnect (for example any hosted runner from Alpaca or Lumibot's commercial hosting) were not researched.
