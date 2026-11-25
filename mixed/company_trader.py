#!/usr/bin/env python3
"""
A trading COMPANY of Claude Haiku agents (low effort) on exactly the same test as the two-Ultra hourly run:
same hourly data (25 Aug - 23 Nov 2026, coins and stocks), same market view, same news timing, same rules (golden
rule: buy only below the 24-hour average, sell on a spike, never sell below break-even; 10 holdings; all money
invested; trade rarely; 0.05% per buy and per sell), same benchmarks (holding Bitcoin, holding SPY).

The differences: the AIs are Claude Haiku at low effort, run headless through Claude Code on this session's
subscription (no API key, no tools - they only read text and answer), and the work is split like a trading firm:

  every hour  3 RESEARCHERS, each covering one slice of the market (crypto majors, small coins, US stocks), read
              their slice and the news and report; any of them can call a meeting.
  meetings    SHORT-TERM PM (golden-rule dips and spikes, hours) and LONG-TERM PM (days and weeks: which assets and
              sectors deserve money, the coin/stock mix) propose trades with evidence
              -> RISK OFFICER approves or vetoes each item -> CEO makes the final call (may drop items, cannot add
              any) and writes the company's conditions for the researchers -> TRADER writes the orders.
              The program then enforces the rules exactly as in the Ultra run.
  every day   STRATEGY ANALYST reviews the previous day's record and writes a memo management reads.

If the subscription's usage limit is reached, the company waits and retries; it never gives up. Every answer is
saved as it comes, so a stopped run resumes where it was.

    TAG=company_haiku START_AT="2026-08-25 00:00" python3 mixed/company_trader.py
"""
import csv
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("STEP_MIN", "60")
sys.path.insert(0, HERE)
import mixed_trader as MT  # noqa: E402  (same view, rules, server and order checks as the Ultra runs)

TAG = os.environ.get("TAG", "company_haiku")
START_AT = os.environ.get("START_AT", "2026-08-25 00:00")
MODEL = os.environ.get("COMPANY_MODEL", "haiku")
EFFORT = os.environ.get("COMPANY_EFFORT", "low")
H_FILE = os.path.join(HERE, f"company_{TAG}_hours.csv")
M_FILE = os.path.join(HERE, f"company_{TAG}_meetings.csv")
A_FILE = os.path.join(HERE, f"company_{TAG}_memos.csv")
U_FILE = os.path.join(HERE, f"company_{TAG}_usage.json")
U = MT.U                                   # "hour"
SLOTS = MT.SLOTS

COMPANY = (
    "THE COMPANY: a small trading company run by AIs, managing one practice account. Researchers watch the market "
    "every hour, each covering one slice. When something is worth acting on, management meets: a short-term "
    "portfolio manager and a long-term portfolio manager propose trades with evidence, the risk officer approves or "
    "vetoes each item, the CEO makes the final call, and the trader places the orders. Everyone follows the rules "
    "below; the system also refuses any order that breaks them.\n")
RULES = COMPANY + MT.RULES

R_SYSTEM = (
    "You are a RESEARCHER at the company, covering {cover}. Every hour you see the market for your coverage, the "
    "account and the news. You cannot trade.\n" + RULES +
    "YOUR JOB EACH HOUR: write 1 to 3 plain sentences on what is actually happening in your coverage that matters "
    "to the company - dips worth buying under the golden rule, holdings spiking clearly above break-even, important "
    "news. Then decide whether management should meet now. Call a meeting only when a buy or sell is probably worth "
    "considering in your coverage, there are empty slots, or there is important news about a holding or the whole "
    "market. Management writes down what it is waiting for (MANAGEMENT'S CONDITIONS); call a meeting when one of "
    "those is met or when something new and important happened that it has not seen. Most hours the answer is no.\n"
    "End with one line: 'FLAG: YES - <short reason>' or 'FLAG: NO'.")

ITEMS = ("items like 'BUY SYMBOL' or 'SELL SYMBOL' separated by ';' (symbols exactly as in the lists; coins end in "
         "-USD, e.g. BTC-USD; stocks e.g. NVDA), or NONE")
PS_SYSTEM = (
    "You are the SHORT-TERM PORTFOLIO MANAGER. You trade the golden rule over hours: buy coins or stocks that are in "
    "a clear dip (below their 24-hour average, the bigger the dip the better, preferably steadying rather than "
    "crashing) and sell holdings that spike clearly above break-even. If there are empty slots you must propose dip "
    "buys to fill them (coins only while the stock market is closed).\n" + RULES +
    "Read the researchers' reports and the numbers, think it through in plain sentences, and propose specific trades "
    "with the evidence. Doing nothing is a fine answer when nothing is clear. End with exactly these lines:\n"
    "PROPOSAL: " + ITEMS + "\nNOTE: what you are waiting for next (under 30 words)")
PL_SYSTEM = (
    "You are the LONG-TERM PORTFOLIO MANAGER. You think in days and weeks: which coins, stocks and sectors deserve "
    "the company's money, the mix between coins and stocks, and avoiding holdings that may never recover. You may "
    "propose your own trades (same rules) or say which of today's ideas fit the bigger picture.\n" + RULES +
    "Think it through in plain sentences and propose specific trades with the evidence, or none. End with exactly "
    "these lines:\nPROPOSAL: " + ITEMS + "\nNOTE: your longer-term view in one line (under 30 words)")
RK_SYSTEM = (
    "You are the RISK OFFICER. You check every proposed trade against the rules and the evidence: is a sell really "
    "above break-even and a spike; is a buy really below its 24-hour average and a dip rather than a crash; is a stock "
    "order placed while the market is open; does the company stay at 10 holdings with all money invested; is too much "
    "money going into one sector or one story. Approve what holds up and veto what does not, saying why in a few "
    "words. You need a sound reason, not certainty - blocking every trade is also a failure.\n" + RULES +
    "End with exactly these lines:\nAPPROVED: " + ITEMS + "\nVETOED: items with a short reason each, or NONE")
CEO_SYSTEM = (
    "You are the CEO. You read the researchers' reports, both portfolio managers' proposals and the risk officer's "
    "decision, and you make the final call. You may keep or drop any trade the risk officer approved, but you cannot "
    "add a trade the risk officer did not approve. Keep the company disciplined: buy low, sell on spikes, never "
    "panic, trade rarely, keep all money invested.\n" + RULES +
    "Explain your call in a few plain sentences. End with exactly these lines:\nFINAL: " + ITEMS + "\n"
    "NOTE: the company's conditions for the researchers - what we are waiting for before meeting again (under 40 "
    "words)")
TR_SYSTEM = (
    "You are the TRADER. You turn the CEO's final decision into orders. Use the symbols exactly as shown (coins end "
    "in -USD), SELL only what the company holds, BUY only what it does not hold, stock orders only while the stock "
    "market is open, and no more buys than the empty slots after the sells. Do not add anything the CEO did not "
    "decide.\nEnd with exactly one line: ACTIONS: " + ITEMS)
AN_SYSTEM = (
    "You are the STRATEGY ANALYST. Once a day you review the company's record for the previous day - what the "
    "researchers flagged, what management proposed, approved and traded, and how the account did against simply "
    "holding Bitcoin and simply holding SPY - and you write a short memo for management with up to 3 concrete "
    "suggestions that stay inside the rules (for example a clearer spike or dip threshold, a sector to favour or "
    "avoid, a habit that is costing money).\n" + RULES +
    "Write the memo in plain sentences, under 150 words, starting with 'MEMO:'.")
COVERAGE = [("crypto majors (the top 10 and the 11-30 coins)", "crypto", {"top 10", "11-30"}),
            ("small coins (the 31-100 coins)", "crypto", {"31-100"}),
            ("US stocks (every sector and SPY)", "stock", None)]

usage = {"model": MODEL, "effort": EFFORT, "calls": 0, "cost_usd_at_list_price": 0.0, "input_tokens": 0,
         "cached_input_tokens": 0, "output_tokens": 0, "limit_waits": 0, "errors": 0, "by_role": {}}
lock = threading.Lock()


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def claude(role, system, prompt):
    """One headless Claude call: no tools, no files, just text in and text out. Waits through usage limits."""
    env = dict(os.environ, CLAUDE_EFFORT=EFFORT)
    wait = 30
    while True:
        msg = ""
        try:
            r = subprocess.run(["claude", "-p", "--model", MODEL, "--effort", EFFORT, "--tools", "",
                                "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "",
                                "--output-format", "json", "--system-prompt", system],
                               input=prompt, capture_output=True, text=True, timeout=900, env=env)
            out = r.stdout.strip()
            j = json.loads(out[out.index("{"):]) if "{" in out else {}
            text = (j.get("result") or "").strip()
            if r.returncode == 0 and j and not j.get("is_error") and text:
                u = j.get("usage", {})
                with lock:
                    usage["calls"] += 1
                    usage["cost_usd_at_list_price"] += float(j.get("total_cost_usd") or 0)
                    usage["input_tokens"] += (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                    usage["cached_input_tokens"] += u.get("cache_read_input_tokens") or 0
                    usage["output_tokens"] += u.get("output_tokens") or 0
                    usage["by_role"][role] = usage["by_role"].get(role, 0) + 1
                return text
            msg = (text or out or r.stderr)[-500:]
        except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as e:
            msg = str(e)[:500]
        limited = bool(re.search(r"limit|quota|429|overloaded|rate", msg, re.I))
        with lock:
            usage["limit_waits" if limited else "errors"] += 1
        delay = 300 if limited else wait
        log(f"{role}: call failed ({'usage limit' if limited else 'error'}): {msg[:200]!r} - retrying in {delay}s")
        time.sleep(delay)
        wait = min(600, wait * 2)


def parse_items(text, key, kind):
    """Read the last line starting with KEY: and return its BUY/SELL items (same reader as the Ultra runs)."""
    line = ""
    for ln in text.splitlines():
        s = ln.strip().lstrip("*").strip()
        if s.upper().startswith(key):
            line = s.split(":", 1)[1] if ":" in s else ""
    return MT.parse_actions("ACTIONS:" + line, kind)


def last_line(text, key, n=300):
    v = ""
    for ln in text.splitlines():
        s = ln.strip().lstrip("*").strip()
        if s.upper().startswith(key):
            v = s.split(":", 1)[-1].strip()
    return v[:n]


def slice_view(lines, kind, groups):
    """The common lines plus only this researcher's rows of the EVERY COIN / EVERY STOCK tables."""
    out, section, header, shown = [], None, "", False
    for ln in lines:
        if ln.startswith("EVERY COIN"):
            section, header, shown = "crypto", ln, False
            continue
        if ln.startswith("EVERY STOCK"):
            section, header, shown = "stock", ln, False
            continue
        if section and ln.startswith("  "):
            g = ln.strip().split(":")[0]
            if section == kind and (groups is None or g in groups):
                if not shown:
                    out.append(header)
                    shown = True
                out.append(ln)
            continue
        section = None
        out.append(ln)
    return out


def load(path):
    return MT.load(path)


def writer(path, fields):
    new = not os.path.exists(path)
    f = open(path, "a", newline="")
    w = csv.DictWriter(f, fields)
    if new:
        w.writeheader()
    return f, w


def items_str(items):
    return "; ".join(f"{a['action']} {a['symbol']}" for a in items) or "NONE"


def main():
    h_saved, m_saved, a_saved = load(H_FILE), load(M_FILE), load(A_FILE)
    m_by_time = {r["time"]: r for r in m_saved}
    a_by_time = {r["time"]: r for r in a_saved}
    hf, hw = writer(H_FILE, ["time", "value", "btc_hold", "spy_hold", "flags", "meeting", "r1", "r2", "r3", "seconds"])
    mf, mw = writer(M_FILE, ["time", "value", "pm_short", "pm_long", "risk", "ceo", "trader", "proposals", "approved",
                             "final", "trader_actions", "executed", "ceo_note", "seconds"])
    af, aw = writer(A_FILE, ["time", "memo"])
    view = MT.View()
    entries, highs, pending, orders = {}, {}, [], {}
    r_notes = [[], [], []]
    ceo_notes, memo, last_dec = [], "", "none yet"
    news_since_meeting, recent_news, day_log = [], [], []
    i_h, n_meet, t0, btc_sent, spy_sent = 0, 0, time.time(), False, False
    with MT.Server() as srv:
        while True:
            out = srv.next(orders)
            if out.get("done"):
                break
            view.add(out)
            st = out["step"]
            acc = out["accounts"].get("ai", {"value": 1000.0, "cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
            held = acc.get("shares", {})
            for s in list(highs):
                if s in held:
                    highs[s] = max(highs[s], st["close"][s])
                else:
                    highs.pop(s)
            for od in pending:
                if od["action"] == "BUY" and od["symbol"] in held and od["symbol"] not in entries:
                    entries[od["symbol"]] = st["open"][od["symbol"]]
                    highs[od["symbol"]] = max(st["open"][od["symbol"]], st["close"][od["symbol"]])
                if od["action"] == "SELL" and od["symbol"] not in held:
                    entries.pop(od["symbol"], None)
            refused = out["refused"].get("ai", [])
            orders, pending = {}, []
            news_since_meeting = (news_since_meeting + out["news"])[-60:]
            recent_news = (recent_news + out["news"])[-400:]
            if len(view.hist) <= MT.WARMUP or out["last_step"] or st["time"] < START_AT:
                continue
            if not btc_sent:
                orders["btc_hold"] = [{"action": "BUY", "symbol": "BTC-USD", "all": True}]
                btc_sent = True
            if not spy_sent and st["stock_market_open"]:
                orders["spy_hold"] = [{"action": "BUY", "symbol": "SPY", "all": True}]
                spy_sent = True
            accs = out["accounts"]
            t1 = time.time()
            # ---- the strategy analyst, once a day ----
            if st["time"].endswith("00:00") and day_log:
                if st["time"] in a_by_time:
                    memo = a_by_time[st["time"]]["memo"]
                else:
                    L = view.lines(acc, entries, highs, 5)[:12] + ["THE PREVIOUS DAY'S RECORD:"] + day_log[-40:]
                    memo = claude("analyst", AN_SYSTEM, "\n".join(L))[:1500]
                    aw.writerow({"time": st["time"], "memo": memo.replace("\n", " / ")})
                    af.flush()
                day_log = []
            # ---- the researchers, every hour ----
            base = view.lines(acc, entries, highs, 5)
            if i_h < len(h_saved):
                r = h_saved[i_h]
                assert r["time"] == st["time"], f"saved hours out of step at {st['time']}"
                reports = [r["r1"], r["r2"], r["r3"]]
                flags = [c == "Y" for c in r["flags"]]
            else:
                hour_news = [n for n in recent_news if n["time"] >= view.hist[-MT.HOUR - 1]["known_at"]][-60:]
                common = ([f"HEADLINES FROM THE {MT.RECENT.upper()} (UTC; newest last; * = this {U}):"] +
                          ([f"- {n['time'][11:]}{' *' if n in out['news'] else ''} {n['title']}" for n in hour_news]
                           or ["- none"]) +
                          [f"THE COMPANY'S LAST DECISION: {last_dec}"] +
                          ([f"MANAGEMENT'S CONDITIONS (the CEO's latest note): {ceo_notes[-1][1]}"] if ceo_notes else []) +
                          ([f"ORDERS REFUSED LAST {U.upper()}: " + "; ".join(f"{o['action']} {o['symbol']} ({o['why']})"
                                                                            for o in refused)] if refused else []))
                if i_h == 0:
                    common.append("This is the first hour: the account is all cash, so management must meet and invest it.")

                def research(k):
                    cover, kind, groups = COVERAGE[k]
                    L = slice_view(base, kind, groups) + common + (
                        ["YOUR LAST REPORTS:"] + [f"- {t}: {x[:200]}" for t, x in r_notes[k][-6:]] if r_notes[k] else [])
                    return claude(f"researcher_{k + 1}", R_SYSTEM.format(cover=cover), "\n".join(L))
                with ThreadPoolExecutor(3) as ex:
                    reports = list(ex.map(research, range(3)))
                flags = [bool(re.search(r"FLAG\s*:\s*\**\s*YES", x, re.I)) for x in reports]
            for k in range(3):
                said = re.sub(r"\s*/?\s*\**FLAG\s*:.*$", "", reports[k].replace("\n", " / "), flags=re.I | re.S).strip()
                r_notes[k].append((st["known_at"][5:], said[:400]))
            meet = any(flags) or i_h == 0 or (SLOTS - len(held)) > 0
            # ---- the management meeting ----
            if meet:
                n_meet += 1
                if st["time"] in m_by_time:
                    m = m_by_time[st["time"]]
                    acts, ceo_note = json.loads(m["trader_actions"]), m["ceo_note"]
                    final_items = json.loads(m["final"])
                else:
                    full = view.lines(acc, entries, highs, 10)
                    ctx = (["RESEARCHERS' REPORTS THIS HOUR:"] +
                           [f"- {COVERAGE[k][0]}: {reports[k].replace(chr(10), ' / ')[:900]}" for k in range(3)] +
                           ["HEADLINES SINCE THE LAST MEETING (newest last, UTC):"] +
                           ([f"- {n['time'][5:]} {n['title']}" for n in news_since_meeting[-40:]] or ["- none"]) +
                           (["COMPANY NOTEBOOK (the CEO's earlier notes):"] + [f"- {t}: {x}" for t, x in ceo_notes[-6:]]
                            if ceo_notes else []) +
                           ([f"STRATEGY ANALYST'S LATEST MEMO: {memo}"] if memo else []) +
                           ([f"ORDERS REFUSED LAST {U.upper()}: " + "; ".join(f"{o['action']} {o['symbol']} ({o['why']})"
                                                                             for o in refused)] if refused else []))
                    prompt = "\n".join(full + ctx)
                    with ThreadPoolExecutor(2) as ex:
                        f1 = ex.submit(claude, "pm_short", PS_SYSTEM, prompt)
                        f2 = ex.submit(claude, "pm_long", PL_SYSTEM, prompt)
                        pm_s, pm_l = f1.result(), f2.result()
                    proposals, seen = [], set()
                    for a in parse_items(pm_s, "PROPOSAL", view.kind) + parse_items(pm_l, "PROPOSAL", view.kind):
                        if (a["action"], a["symbol"]) not in seen:
                            seen.add((a["action"], a["symbol"]))
                            proposals.append(a)
                    pms = (f"SHORT-TERM PM:\n{pm_s}\n\nLONG-TERM PM:\n{pm_l}\n\n"
                           f"ALL PROPOSED ITEMS: {items_str(proposals)}")
                    if proposals:
                        risk = claude("risk", RK_SYSTEM, prompt + "\n\nTHE PROPOSALS:\n" + pms)
                        approved = [a for a in parse_items(risk, "APPROVED", view.kind)
                                    if (a["action"], a["symbol"]) in seen]
                    else:
                        risk, approved = "No trades were proposed.", []
                    ok_set = {(a["action"], a["symbol"]) for a in approved}
                    ceo = claude("ceo", CEO_SYSTEM, prompt + "\n\nTHE PROPOSALS:\n" + pms + "\n\nTHE RISK OFFICER:\n" + risk +
                                 f"\n\nRISK-APPROVED ITEMS (the only ones you may keep): {items_str(approved)}")
                    final_items = [a for a in parse_items(ceo, "FINAL", view.kind) if (a["action"], a["symbol"]) in ok_set]
                    ceo_note = last_line(ceo, "NOTE")
                    if final_items:
                        tr_prompt = "\n".join(
                            [ln for ln in full if not ln.startswith("  ") and not ln.startswith("EVERY ")] +
                            [f"\nTHE CEO'S FINAL DECISION: {items_str(final_items)}",
                             f"Stock market open for orders next {U}: {'YES' if st['stock_market_open'] else 'NO'}",
                             f"Empty slots now: {SLOTS - len(held)}"])
                        trader = claude("trader", TR_SYSTEM, tr_prompt)
                        fset = {(a["action"], a["symbol"]) for a in final_items}
                        acts = [a for a in parse_items(trader, "ACTIONS", view.kind) if (a["action"], a["symbol"]) in fset]
                    else:
                        trader, acts = "No orders.", []
                    mw.writerow({"time": st["time"], "value": f"{acc.get('value', 1000.0):.2f}",
                                 "pm_short": pm_s.replace("\n", " / ")[:2500], "pm_long": pm_l.replace("\n", " / ")[:2500],
                                 "risk": risk.replace("\n", " / ")[:2500], "ceo": ceo.replace("\n", " / ")[:2500],
                                 "trader": trader.replace("\n", " / ")[:600], "proposals": json.dumps(proposals),
                                 "approved": json.dumps(approved), "final": json.dumps(final_items),
                                 "trader_actions": json.dumps(acts), "executed": "", "ceo_note": ceo_note,
                                 "seconds": f"{time.time() - t1:.1f}"})
                    mf.flush()
                    log(f"MEETING {st['time']}: proposed {items_str(proposals)} | approved {items_str(approved)} | "
                        f"final {items_str(final_items)} | orders {items_str(acts)}")
                ceo_notes.append((st["known_at"][5:], ceo_note))
                news_since_meeting = []
                # the rules the program enforces before sending (same checks as the Ultra runs)
                ok, seen2 = [], set()
                for a in acts:
                    s = a["symbol"]
                    bad = (a["action"] == "BUY" and (s in held or s in seen2)) or (a["action"] == "SELL" and s not in held)
                    bad = bad or (view.kind.get(s) == "stock" and not st["stock_market_open"])
                    bad = bad or (a["action"] == "SELL" and s in entries and st["close"][s] * 0.9995 < entries[s] * 1.0005)
                    bad = bad or (a["action"] == "BUY" and (view.avg24(s) is None or st["close"][s] >= view.avg24(s)))
                    if not bad:
                        ok.append(dict(a, split=True) if a["action"] == "BUY" else a)
                        seen2.add(s)
                free = SLOTS - len(held) + len([a for a in ok if a["action"] == "SELL"])
                ok = [a for a in ok if a["action"] == "SELL"] + [a for a in ok if a["action"] == "BUY"][:max(0, free)]
                last_dec = (f"{st['known_at']} UTC: " + ("; ".join(f"{a['action']} {a['symbol']}" for a in ok) or "no trades")
                            + (f" - CEO's note: {ceo_note[:150]}" if ceo_note else ""))
                day_log.append(f"- {st['time'][5:]} meeting: final {items_str(final_items)}; sent {items_str(ok)}; "
                               f"CEO note: {ceo_note[:150]}; account ${acc.get('value', 1000.0):,.2f}")
                orders["ai"] = ok
                pending = ok
            if i_h >= len(h_saved):
                hw.writerow({"time": st["time"], "value": f"{acc.get('value', 1000.0):.2f}",
                             "btc_hold": f"{accs.get('btc_hold', {}).get('value', 1000.0):.2f}",
                             "spy_hold": f"{accs.get('spy_hold', {}).get('value', 1000.0):.2f}",
                             "flags": "".join("Y" if f else "N" for f in flags), "meeting": int(meet),
                             "r1": reports[0].replace("\n", " / ")[:900], "r2": reports[1].replace("\n", " / ")[:900],
                             "r3": reports[2].replace("\n", " / ")[:900], "seconds": f"{time.time() - t1:.1f}"})
                hf.flush()
                with lock:
                    json.dump(usage, open(U_FILE, "w"), indent=1)
            i_h += 1
            if i_h % 24 == 0:
                day_log.append(f"- {st['time'][5:]} account ${acc.get('value', 1000.0):,.2f}, holding Bitcoin "
                               f"${accs.get('btc_hold', {}).get('value', 1000.0):,.2f}, holding SPY "
                               f"${accs.get('spy_hold', {}).get('value', 1000.0):,.2f}")
                log(f"{st['time']} ${acc.get('value', 1000.0):,.2f} | BTC ${accs.get('btc_hold', {}).get('value', 1000.0):,.2f} "
                    f"SPY ${accs.get('spy_hold', {}).get('value', 1000.0):,.2f} | holds {','.join(held) or 'cash'} | "
                    f"hours {i_h}, meetings {n_meet}, calls {usage['calls']}, list-price ${usage['cost_usd_at_list_price']:.2f} "
                    f"[{time.time() - t0:.0f}s]")
        final = out
    hf.close()
    mf.close()
    af.close()
    with open(os.path.join(HERE, f"result_company_{TAG}.json"), "w") as fh:
        json.dump(final.get("accounts", {}), fh, indent=1)
    with lock:
        json.dump(usage, open(U_FILE, "w"), indent=1)
    log("finished: " + json.dumps({k: round(v.get("value", 0), 2) for k, v in final.get("accounts", {}).items()}) +
        f" | hours {i_h}, meetings {n_meet}, calls {usage['calls']}")


if __name__ == "__main__":
    main()
