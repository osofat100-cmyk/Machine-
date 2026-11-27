# Quant trading team: what the research supports, and a plan for our practice-money company

Status: research complete. Labels: CONFIRMED = primary source; SECONDARY = third-party; INFERRED = our reconstruction.

## 1. What the research settled

- **Structure (SECONDARY/INFERRED):** no firm publishes an org chart. The common pattern is trading desks or products, each with a mix of traders, quant researchers and software engineers. Jane Street and Citadel post near-identical starting pay for these roles, which suggests no single role is the boss of the others.
- **Governance (CONFIRMED, US):** broker-dealers need pre-trade risk controls under the firm's own control (SEC Rule 15c3-5); written supervision (FINRA 3110); annual supervisory testing (3120); CEO certification (3130).
- **Algorithm release (CONFIRMED, UK FCA review, Aug 2025):** algorithms often need approval from several business areas before deployment; good firms document each deployment stage with senior approval; weak firms had unclear ownership of who runs each algorithm. No public source names one approver.
- **Headcount (CONFIRMED only from firm sites):** Jane Street "more than 3,000"; Two Sigma about 1,700 (250+ PhDs); D.E. Shaw "more than 3,000" (company page). Wells Fargo about 205,000 and JPMorgan about 318,500 (filings). Crypto firms: no official figures. Aggregator figures (Form ADV counts, Wintermute, GSR, Jump) could not be verified and are not used.
- **Crypto firms (CONFIRMED from Jump careers page):** AI/ML, technology, trading and signals teams. Wintermute and GSR departments were not on their sites.
- **Evidence of skill (our own work and the literature):** no published study shows a model with real skill after luck is removed. Thinking mode did not help. Buy-low / sell-on-spike rules did (our 3-month hourly run).

## 2. Plan for the practice-money company

Scope: practice money only, $1,000 per account, no real orders. Runs while the session is active or on scheduled check-ins.

Roles (mapped to the research):
| Role | Who | Job | Authority |
|---|---|---|---|
| CEO | Ultra | Sets goal and risk budget; breaks ties | Final say on the budget, not on single trades |
| Risk officer | Ultra | Checks each proposal against limits: golden rule, 10-slot cap, maximum loss, buy-low rule | Can veto any trade |
| Portfolio manager A | Ultra | Proposes buy-the-dip trades with evidence | Proposes |
| Portfolio manager B | Ultra | Proposes sell-the-spike trades with evidence | Proposes |
| Researchers (x3) | Ultra | Each watches one sector (majors, small coins, stock sectors) and reports changes | Reports only |
| Trader | GLM (woken on demand) | Places orders | Acts only if risk approves and at least one PM proposed it |

Process (adapted from FCA: documented approval at each step):
1. Researchers report; PMs propose trades with evidence.
2. Risk checks the proposal against written limits. Veto ends it.
3. The trader acts only with risk approval and one PM proposal.
4. Every decision and approval is saved to the record.
5. Monthly review: risk reviews the record and retires any rule that loses money repeatedly.

Tests before trusting it: run it on the same 3 months as the current hourly runs, and compare with holding Bitcoin, holding SPY and the current two-Ultra run. A company only counts as better if it beats the current run by more than the luck spread between identical runs (about $30 over 3 months from the copies test).

## 3. Open items

- Who approves releases at real firms: not public. Our design uses one approver (risk) plus one PM, which is our choice, not a finding.
- Real headcount for crypto firms and Form ADV counts: not verified.
- Wells Fargo and JPMorgan desk structure: not disclosed.
