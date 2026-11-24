#!/usr/bin/env python3
"""
STOCK version of crypto/crypto_trader.py with the golden rules: identical rules, prompt, settings and checklist;
only the market changes. An AI runs a $1,000 practice portfolio of the 500 largest US stocks (about the S&P 500),
one 1-minute step at a time during market hours (9:30-16:00 New York), 26 Oct - 23 Nov 2026 (8,190 steps), with
the checklist, a memory notebook, the cost rules and news handed out only at its exact publication minute. It holds
10 stocks with all the money invested. The yardstick is holding SPY over the same steps. "Last 24 hours" becomes
"the last trading day" (390 one-minute steps) and the coin size groups become the stock sectors again.
DECIDE_EVERY=k: the AI sees every 1-minute bar but decides only every k-th minute.

VERSION=v4a: golden rule (never sell below break-even; take profits above it; buy stocks that fell more than average).
VERSION=v4b: golden rule + spread the risk + trade rarely.
The AI is reached through NVIDIA's second address (api.nvcf.nvidia.com), which carries the second key, so these
runs do not share the rate limit with the crypto runs.

Every answer is appended to sp500/golden/answers_1m_every<k>_<version>_<tag>.csv the moment it is given; running
again replays saved answers and continues from where it stopped.

    STEP_MIN=1 VERSION=v4b DECIDE_EVERY=5 MODEL_TAG=ultrafast THINKING=off MAX_TOKENS=1500 python3 sp500/golden_trader.py
"""
import csv
import fcntl
import random
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.environ.get("MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
FUNCTION = os.environ.get("NVCF_FUNCTION", "948fe171-ce7a-4332-8bc0-5e14e90259f9")   # Ultra, second address
API_URL = f"https://api.nvcf.nvidia.com/v2/nvcf/exec/functions/{FUNCTION}"
STATUS_URL = "https://api.nvcf.nvidia.com/v2/nvcf/exec/status/"
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "160"))
NO_THINK = os.environ.get("THINKING") == "off"         # Nemotron: answer without the long reasoning (about 14x faster)
EXTRA = {"chat_template_kwargs": {"enable_thinking": False}} if NO_THINK else {}
STEP = int(os.environ.get("STEP_MIN", "1"))  # 1-minute or 2-minute steps
EVERY = int(os.environ.get("DECIDE_EVERY", "1"))   # sees every 1-minute bar, decides on every EVERY-th one
TAG = f"_{STEP}m" + (f"_every{EVERY}" if EVERY > 1 else "") + (f"_{os.environ['VERSION']}" if os.environ.get("VERSION") else "") \
    + (f"_{os.environ['MODEL_TAG']}" if os.environ.get("MODEL_TAG") else "")
OUT = os.path.join(HERE, "golden")
os.makedirs(OUT, exist_ok=True)
ANSWERS = os.path.join(OUT, f"answers{TAG}.csv")
HOUR = 60 // STEP                             # steps in one hour
DAY = 390 // STEP                             # steps in one trading day (9:30-16:00)
BENCH = "SPY"
V = os.environ.get("VERSION", "")
FULL = V in ("v3", "v4", "v4a", "v4b")                # all money invested, 10 stocks at all times
GOLDEN = V in ("v4", "v4a", "v4b")                    # golden rule: never sell below break-even; buy the dips
GOLDEN_PLUS = V in ("v4", "v4b")                      # second version: + spread the risk, trade rarely
WARMUP = HOUR + 1                             # first hour of the first day: background only

SYSTEM = (
    "You manage a $1,000 practice portfolio of large US stocks (about the S&P 500). Every few minutes you get the "
    "market, the biggest movers, your holdings and any news published since the last step. The market is open "
    "9:30-16:00 New York time. You may hold up to 10 stocks; each BUY puts 10% of the account into one stock; SELL "
    "sells the whole holding of that stock into cash (US dollars, which do not move with the market).\n"
    "RULES YOU MUST FOLLOW:\n"
    "1. Trading costs money: every BUY costs 0.05% and every SELL another 0.05%, so a round trip costs 0.10%. Only "
    "trade when you expect a move clearly bigger than that. Switching back and forth on small wiggles loses money.\n"
    "2. You can only SELL stocks you own (listed under YOUR HOLDINGS). You cannot BUY a stock you already own.\n"
    + ("3. GOLDEN RULE: never sell a stock for less than you paid plus costs (its BREAK-EVEN price). If a stock you "
       "own dips below its break-even, do not panic: HOLD it until it recovers above break-even. Once a stock is "
       "above its break-even you may SELL it to take the profit, and BUY a stock that has fallen more than average "
       "(see BIGGEST FALLERS last trading day) and wait for that one to recover. Repeat.\n"
       + ("SPREAD THE RISK: your money is split over 10 stocks (about 10% each), so if one stock never recovers only that "
       "slice is affected - holding a dipped stock is an acceptable risk.\n"
       "TRADE RARELY: keep all the money invested, but do not pull money out of stocks often - every sell plus buy "
       "costs 0.10%. Only take a profit when the gain is clearly bigger than that cost. Most decisions should be NONE.\n"
          if GOLDEN_PLUS else "")
       if GOLDEN else
       "3. Sell high, buy low. Do not keep a falling stock just to avoid taking a loss: the price you paid does not "
       "matter, only where the price goes next.\n") +
    "4. Use only symbols shown to you.\n"
    "ADVICE (learned from your earlier runs - follow it):\n"
    "A. Costs: only trade if the move you expect covers the 0.10% round trip AND leaves a profit. If you are not "
    "sure, do nothing. Most minutes the right answer is NONE.\n"
    + ("B. Stocks below break-even cannot be sold (the system will refuse). Stocks above break-even: take the profit "
       "when the rise has clearly turned down from its high, or hold if still rising.\n" if GOLDEN else
       "B. Ride spikes: when a stock you own is rising, keep it. Do not sell just because it went up - it may keep "
       "going, and buying it back later costs more. Sell only when it has clearly turned down from its high since you "
       "bought it (see 'below its high' in YOUR HOLDINGS). Never sell a stock and buy the same stock back soon after.\n") +
    "C. Before any BUY, check YOUR HOLDINGS: never buy a stock you already own.\n"
    "D. News: act on news that changes a company's or the market's outlook (results, guidance, big deals, rate or "
    "tariff decisions, crashes). Ignore headlines that do not matter. Do not trade just because a headline "
    "appeared.\n"
    + ("E. ALL THE MONEY MUST STAY INVESTED. Hold 10 stocks at all times; each BUY splits the remaining cash evenly "
       "over your empty slots. If you SELL a stock, BUY a replacement in the same answer. While you have empty "
       "slots, BUY stocks to fill them.\n" if FULL else "") +
    "Before deciding, answer the checklist. Keep a plan: your notebook shows your last notes.\n"
    "Answer in exactly this form, one line each:\n"
    "MARKET: UP, DOWN or FLAT\n"
    "NEWS: GOOD, BAD or NONE (a few words on what matters)\n"
    "RISK: LOW, MEDIUM or HIGH\n"
    "NOTE: a note to yourself for the next steps (under 25 words)\n"
    "ACTIONS: up to 3 of 'BUY SYMBOL' or 'SELL SYMBOL' separated by ';', or NONE"
    + (" (to fill empty slots you may list more BUYs)" if FULL else ""))


class Server:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.proc = subprocess.Popen([sys.executable, os.path.join(HERE, "market_server.py"), "--port",
                                      str(self.port)], stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            self.proc.kill()
            raise RuntimeError(line)
        print(line.strip(), flush=True)
        self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=300)
        return self

    def next(self, orders):
        self.conn.request("POST", "/next", body=json.dumps({"orders": orders}))
        return json.loads(self.conn.getresponse().read())

    def __exit__(self, *exc):
        self.conn.close()
        self.proc.terminate()
        self.proc.wait(timeout=30)


RPM = int(os.environ.get("RPM", "36"))                 # all stock runs together stay under the key's per-minute limit
RATE_FILE = os.path.join(HERE, "golden", ".requests")


def throttle():
    """Shared by every stock run: wait until fewer than RPM requests were sent in the last 60 seconds."""
    while True:
        with open(RATE_FILE, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            now = time.time()
            sent = [float(x) for x in f.read().split() if now - float(x) < 60]
            try:                                         # the cap can be changed while running: golden/.rpm
                cap = int(open(RATE_FILE.replace(".requests", ".rpm")).read())
            except (OSError, ValueError):
                cap = RPM
            if len(sent) < cap:
                f.seek(0)
                f.truncate()
                f.write(" ".join(f"{x:.3f}" for x in sent + [now]))
                return
            wait = 60 - (now - min(sent)) + random.random()
        time.sleep(wait)


def call(payload):
    """One request through NVIDIA's second address; long jobs come back as 202 and are polled until done."""
    throttle()
    req = urllib.request.Request(API_URL, data=json.dumps({"requestHeader": {}, "requestBody": payload}).encode(),
                                 headers={"Authorization": "Bearer proxy-injected", "Content-Type": "application/json",
                                          "Accept": "application/json"})
    r = urllib.request.urlopen(req, timeout=300)
    j = json.load(r)
    while r.status == 202 or j.get("status") in ("pending-evaluation", "in-progress"):
        time.sleep(1)
        req = urllib.request.Request(STATUS_URL + (j.get("reqId") or r.headers.get("NVCF-REQID")),
                                     headers={"Authorization": "Bearer proxy-injected", "Accept": "application/json"})
        r = urllib.request.urlopen(req, timeout=300)
        j = json.load(r)
    if j.get("status") == "errored":
        raise urllib.error.URLError(f"errored {j.get('errorCode')}")
    return j.get("response", j)


def ask(user):
    payload = {"model": MODEL, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
               "temperature": 0, "max_tokens": MAX_TOKENS, **EXTRA}
    last, limited = None, [0]
    k = 0
    while k < 8:
        k += 1
        try:
            j = call(payload)
            text = (j["choices"][0]["message"].get("content") or "").strip()
            if not text and k < 7:                       # thought too long and never answered: ask again, shorter
                payload = {"model": MODEL, "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user + "\n\nKeep your reasoning short and give the answer form now."}],
                    "temperature": 0, "max_tokens": max(MAX_TOKENS, 6000), **EXTRA}
                continue
            return text
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:                                # over the free per-minute limit: back off, staggered
                limited[0] += 1
                wait = float(e.headers.get("retry-after") or 0) or min(120.0, 15.0 * 2 ** min(limited[0] - 1, 3))
                time.sleep(wait + random.uniform(0, 10))
                if limited[0] < 400:
                    k -= 1                                   # a rate-limit wait does not use up a try
                    continue
            time.sleep(min(60, 2 ** k))
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, KeyError) as e:
            last = e
            time.sleep(min(60, 2 ** k))
    raise RuntimeError(f"AI call kept failing: {last}")


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


def short(sym):
    return sym


def build_prompt(hist, sector_of, acc, entries, news_seen, new_news, notes, refused_now=(), highs=None):
    st = hist[-1]
    c = st["close"]
    hour = hist[-HOUR] if len(hist) >= HOUR else hist[0]
    first = hist[-DAY] if len(hist) >= DAY else hist[0]                # one trading day ago (or the earliest seen)
    day = [h for h in hist if h["time"][:10] == st["time"][:10]]
    today = day[0] if day else hist[0]
    L = [f"Time: {st['known_at']} New York (the {STEP}-minute bar from {st['time'][11:]} has just closed)."]
    s = BENCH
    k = min(len(hist), STEP * EVERY + 1)
    L.append(f"MARKET (SPY ${c[s]:,.2f}): {STEP * EVERY} min {pct(c[s], hist[-k]['close'][s]):+.2f}%, 1 hour "
             f"{pct(c[s], hour['close'][s]):+.2f}%, today {pct(c[s], today['open'][s]):+.2f}%")
    by_sector = defaultdict(list)
    for sym, sec in sector_of.items():
        if sym in c and sym in today["open"]:
            by_sector[sec].append(pct(c[sym], today["open"][sym]))
    L.append("SECTORS today: " + ", ".join(f"{sec} {sum(v) / len(v):+.2f}%" for sec, v in
                                                         sorted(by_sector.items(), key=lambda x: -sum(x[1]) / len(x[1])) if sec))
    moves = sorted(((pct(c[x], hour["close"][x]), x) for x in sector_of if x in c and x in hour["close"]))
    L.append("BIGGEST RISERS last hour: " + ", ".join(f"{short(x)} {m:+.2f}% ({sector_of[x]})" for m, x in reversed(moves[-8:])))
    L.append("BIGGEST FALLERS last hour: " + ", ".join(f"{short(x)} {m:+.2f}% ({sector_of[x]})" for m, x in moves[:8]))
    if GOLDEN:
        d24 = sorted(((pct(c[x], first["open"][x]), x) for x in sector_of if x in c and x in first["open"]))
        avg24 = sum(m for m, _ in d24) / len(d24)
        L.append(f"BIGGEST FALLERS last trading day (average stock {avg24:+.2f}%): "
                 + ", ".join(f"{short(x)} {m:+.2f}%" for m, x in d24[:10]))
    held = acc.get("shares", {})
    L.append(f"YOUR ACCOUNT: ${acc.get('value', 1000.0):,.2f}; cash ${acc.get('cash', 1000.0):,.2f}; trades so far "
             f"{acc.get('trades', 0)}, costs paid ${acc.get('costs', 0.0):.2f}; free slots {10 - len(held)}.")
    if held:
        L.append("YOUR HOLDINGS (you may SELL only these):")
        for sym, q in held.items():
            e = entries.get(sym)
            L.append(f"- {short(sym)} ({sector_of.get(sym, '')}): ${q * c[sym]:,.2f}, now ${c[sym]:.6g}"
                     + (f", bought at ${e:.6g}, {pct(c[sym] * 0.9995, e * 1.0005):+.2f}% after costs" if e else "")
                     + ((f", break-even ${e * 1.0005 / 0.9995:.6g} - " + ("CAN SELL" if c[sym] * 0.9995 >= e * 1.0005
                                                                          else "BELOW BREAK-EVEN, HOLD"))
                        if GOLDEN and e else "")
                     + (f", high since bought ${highs[sym]:.6g}, now {pct(c[sym], highs[sym]):+.2f}% below its high"
                        if highs and sym in highs else "")
                     + f", 1 hour {pct(c[sym], hour['close'].get(sym, c[sym])):+.2f}%")
    else:
        L.append("YOUR HOLDINGS: none (all cash) - you cannot SELL anything.")
    if new_news:
        L.append("NEWS PUBLISHED SINCE THE LAST STEP:")
        L += [f"- {n['time'][11:]} {n['title']}" for n in new_news[-10:]]
    else:
        L.append("No new news since the last step. Earlier in the last trading day:")
        L += [f"- {n['time'][5:]} {n['title']}" for n in news_seen[-5:] if n["time"] >= first["time"]]
    if refused_now:
        L.append("YOUR LAST ORDERS THAT WERE REFUSED: " + "; ".join(f"{o['action']} {short(o['symbol'])} ({o['why']})"
                                                                     for o in refused_now))
    if notes:
        L.append("YOUR NOTEBOOK:")
        L += [f"- {t}: {nt}" for t, nt in notes[-6:]]
    return "\n".join(L)


def parse(text, universe, limit=3):
    f = {ln.split(":", 1)[0].strip().upper(): ln.split(":", 1)[1].strip() for ln in text.splitlines() if ":" in ln}
    acts = []
    for part in re.split(r"[;,]", f.get("ACTIONS", "")):
        m = re.match(r"\s*(BUY|SELL)\s+\$?([A-Za-z]{1,5})\b", part.strip(), re.I)
        if m and len(acts) < limit:
            sym = m.group(2).upper()
            acts.append({"action": m.group(1).upper(), "symbol": sym})
    return f, acts


def main():
    saved = []
    if os.path.exists(ANSWERS):
        with open(ANSWERS, newline="") as fh:
            saved = [r for r in csv.DictReader(fh) if r.get("time") != "time"]   # skip a repeated title line
    fields = ["time", "actions", "refused", "market", "news", "risk", "note", "value", "spy_hold", "new_news",
              "seconds", "raw", "forced"]
    fa = open(ANSWERS, "a", newline="")
    w = csv.DictWriter(fa, fieldnames=fields)
    if not saved:
        w.writeheader()
    hist, news_seen, notes, entries, orders, n, t0 = [], [], [], {}, {}, 0, time.time()
    sector_of, spy_sent, pending, highs = {}, False, [], {}
    step_i, news_buffer = 0, []
    with Server() as srv:
        while True:
            out = srv.next(orders)
            if out.get("done"):
                break
            if out.get("universe"):
                sector_of = {u["symbol"]: u["sector"] for u in out["universe"]}
            st = out["step"]
            hist.append(st)
            hist = hist[-(DAY + HOUR):]
            new_news = out["news"]
            news_seen += new_news
            news_buffer += new_news                          # news from skipped minutes waits for the next decision
            acc = out["accounts"].get("ai", {"value": 1000.0, "cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
            refused_now = out["refused"].get("ai", [])
            for sym in list(highs):
                if sym in acc.get("shares", {}):
                    highs[sym] = max(highs[sym], st["close"].get(sym, highs[sym]))
                else:
                    highs.pop(sym)
            for od in pending:                               # remember buy prices of fills that went through
                if od["action"] == "BUY" and od["symbol"] in acc.get("shares", {}) and od["symbol"] not in highs:
                    highs[od["symbol"]] = max(st["open"][od["symbol"]], st["close"][od["symbol"]])
                if od["action"] == "BUY" and od["symbol"] in acc.get("shares", {}) and od["symbol"] not in entries:
                    entries[od["symbol"]] = st["open"][od["symbol"]]
                if od["action"] == "SELL" and od["symbol"] not in acc.get("shares", {}):
                    entries.pop(od["symbol"], None)
            if refused_now and n > len(saved):
                with open(os.path.join(OUT, f"refused{TAG}.csv"), "a") as fr:
                    for od in refused_now:
                        fr.write(f"{st['time']},{od['action']},{od['symbol']},{od['why']}\n")
            orders, pending = {}, []
            if len(hist) <= WARMUP or out["last_step"]:
                continue
            step_i += 1
            if (step_i - 1) % EVERY:                         # not a decision minute: just watch
                continue
            new_news, news_buffer = news_buffer, []
            if not spy_sent:
                orders["spy_hold"] = [{"action": "BUY", "symbol": BENCH, "all": True}]   # all money into SPY, never sold
                spy_sent = True
            if n < len(saved):
                r = saved[n]
                assert r["time"] == st["time"], f"saved answers out of step at {st['time']}"
                acts = json.loads(r["actions"])
                note = r["note"]
            else:
                prompt = build_prompt(hist, sector_of, acc, entries, news_seen, new_news, notes, refused_now, highs)
                t1 = time.time()
                text = ask(prompt)
                secs = time.time() - t1
                f, acts = parse(text, sector_of, limit=10 if FULL else 3)
                forced = ""
                if FULL:                                     # enforce: no empty slots left after this step
                    owned_now = set(acc.get("shares", {}))
                    for _ in range(2):
                        clean = []
                        for a_ in acts:
                            ok = a_["symbol"] in sector_of and (
                                (a_["action"] == "SELL" and a_["symbol"] in owned_now) or
                                (a_["action"] == "BUY" and a_["symbol"] not in owned_now
                                 and a_["symbol"] not in [c_["symbol"] for c_ in clean]))
                            if ok:
                                clean.append(a_)
                        acts = clean
                        after = (owned_now - {a_["symbol"] for a_ in acts if a_["action"] == "SELL"}) | \
                            {a_["symbol"] for a_ in acts if a_["action"] == "BUY"}
                        empty = 10 - len(after)
                        if empty <= 0:
                            break
                        extra = ask(prompt + f"\n\nYOUR ANSWER WAS: {text.replace(chr(10), ' / ')}\n"
                                    f"That leaves {empty} empty slot(s) and cash uninvested. All the money must stay "
                                    f"invested. You already own or are buying: {', '.join(sorted(after)) or 'nothing'}. "
                                    f"Name exactly {empty} other stocks to BUY now from the symbols shown. Answer only "
                                    f"one line: ACTIONS: BUY X; BUY Y; ...")
                        _, more = parse(extra if "ACTIONS" in extra.upper() else "ACTIONS: " + extra, sector_of, limit=10)
                        acts += [m_ for m_ in more if m_["action"] == "BUY"]
                        forced += extra.replace("\n", " / ")[:300] + " | "
                note = f.get("NOTE", "")[:200]
                spy_v = out["accounts"].get("spy_hold", {}).get("value", 1000.0)
                w.writerow({"time": st["time"], "actions": json.dumps(acts), "refused": "", "market": f.get("MARKET", ""),
                            "news": f.get("NEWS", "")[:200], "risk": f.get("RISK", ""), "note": note,
                            "value": f"{acc.get('value', 1000.0):.2f}", "spy_hold": f"{spy_v:.2f}",
                            "new_news": len(new_news), "seconds": f"{time.time() - t1:.2f}", "raw": text.replace("\n", " / ")[:600],
                            "forced": forced})
                fa.flush()
                if n % 100 == 0:
                    print(f"{st['time']} value ${acc.get('value', 1000.0):,.2f} vs SPY ${spy_v:,.2f} | holds "
                          f"{','.join(short(x) for x in acc.get('shares', {})) or 'cash'} | {json.dumps(acts)} | {secs:.2f}s "
                          f"[{n} answers, {time.time() - t0:.0f}s]", flush=True)
            notes.append((st["known_at"][5:], note))
            owned = set(acc.get("shares", {}))
            blocked = [a for a in acts if (a["action"] == "BUY") == (a["symbol"] in owned)]
            if GOLDEN:                                       # never sell below break-even (price paid plus costs)
                blocked += [a for a in acts if a["action"] == "SELL" and a["symbol"] in owned and a not in blocked
                            and a["symbol"] in entries
                            and st["close"][a["symbol"]] * 0.9995 < entries[a["symbol"]] * 1.0005]
            if blocked and n >= len(saved):
                with open(os.path.join(OUT, f"refused{TAG}.csv"), "a") as fr:
                    for od in blocked:
                        fr.write(f"{st['time']},{od['action']},{od['symbol']},blocked before sending (already owned / not owned)\n")
            acts = [a for a in acts if a not in blocked]
            if FULL:
                acts = [dict(a, split=True) if a["action"] == "BUY" else a for a in acts]
            orders["ai"] = acts
            pending = acts
            n += 1
        final = out
    fa.close()
    with open(os.path.join(OUT, f"result{TAG}.json"), "w") as fh:
        json.dump(final.get("accounts", {}), fh, indent=1)
    print("finished:", json.dumps({k: round(v.get("value", 0), 2) for k, v in final.get("accounts", {}).items()}),
          flush=True)


if __name__ == "__main__":
    main()
