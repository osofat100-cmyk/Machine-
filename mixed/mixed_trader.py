#!/usr/bin/env python3
"""
Two AIs working together on ONE practice account ($1,000) that may hold any of the 100 coins and ~500 S&P 500 stocks.

  WATCHER (Nemotron Ultra, fast, thinking off): looks at every minute - prices, holdings and the news published
  that minute (headlines arrive at their real, irregular times). It cannot trade. It writes a few plain sentences on
  what is going on and says whether to WAKE the decider.
  DECIDER (GLM-5.3, the thinker): asleep until the watcher wakes it. Then it sees the full picture plus the watcher's
  recent notes, thinks freely, and gives the orders.

Rules: the second golden-rule version - never sell below break-even (enforced), spread the risk over 10 holdings,
keep all money invested, trade rarely; 0.05% cost per buy and per sell. Stock orders only while the US market is
open (14:30-21:00 UTC on weekdays). No fixed GOOD/BAD/NONE labels: both AIs answer in their own sentences; only the
last lines (WAKE / NOTE / ACTIONS) have a fixed form so the program can read them.

Data and money come only from mixed/mixed_server.py (the one program that opens the sealed data); orders fill at
the next minute's open. Answers are saved as they come, so a stopped run resumes where it was.

    KEY=1 python3 mixed/mixed_trader.py
"""
import csv
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
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "crypto"))
os.environ.setdefault("KEY", "1")
import crypto_trader as CT  # noqa: E402  (shared per-key request limit, same files as the other runs)

URL = "https://integrate.api.nvidia.com/v1/chat/completions"
WATCHER = os.environ.get("WATCHER", "nvidia/nemotron-3-ultra-550b-a55b")
DECIDER = os.environ.get("DECIDER", "z-ai/glm-5.3-flash")
TAG = os.environ.get("TAG", "glm_ultra")
W_FILE = os.path.join(HERE, f"watcher_{TAG}.csv")
D_FILE = os.path.join(HERE, f"decider_{TAG}.csv")
STEP = int(os.environ.get("STEP_MIN", "1"))      # 1 = minute updates (mixed_server.py), 60 = hourly (hourly_server.py)
if STEP == 60:
    U, HOUR, BLOCK, DAY, NOTES_N = "hour", 6, 1, 24, 24          # recent window = last 6 hours, in six 1-hour steps
    RECENT, BLOCK_LABEL, SERVER_FILE = "last 6 hours", "1-hour", "hourly_server.py"
else:
    U, HOUR, BLOCK, DAY, NOTES_N = "minute", 60, 10, 1440, 60    # recent window = last hour, in six 10-minute steps
    RECENT, BLOCK_LABEL, SERVER_FILE = "last hour", "10-minute", "mixed_server.py"
WARMUP = HOUR + 1
SLOTS = 10
START_AT = os.environ.get("START_AT", "")        # e.g. "2026-11-22 00:00": the AIs see everything before, trade from then

RULES = (
    "THE ACCOUNT: $1,000 practice money. It can hold coins (the 100 largest cryptocurrencies, symbols ending in -USD, "
    "trading around the clock; in the lists they are written without -USD, e.g. BTC, but order them as BTC-USD) and US stocks (the S&P 500 and the SPY index fund; stock orders only while the US "
    "market is open, 09:30-16:00 New York time, Monday to Friday: 13:30-20:00 UTC until 1 Nov, 14:30-21:00 UTC after). Up to 10 holdings in total, coins and stocks mixed as you "
    "like. Each BUY splits the remaining cash evenly over the empty slots; SELL sells the whole holding. Orders fill "
    f"at the next {U}'s opening price. Every buy costs 0.05% and every sell 0.05%.\n"
    "THE RULES (second golden-rule version):\n"
    "1. GOLDEN RULE: never sell a holding for less than you paid plus costs (its break-even). Below break-even you "
    "hold and wait for it to recover - the system refuses such sells. Above break-even you may sell to take the "
    "profit and buy something that has fallen more than average, then wait for that one to recover.\n"
    "2. SPREAD THE RISK: the money is split over 10 holdings, so one that never recovers only hurts its slice.\n"
    "3. TRADE RARELY: keep all the money invested; every sell plus buy costs 0.10%, so only take a profit when the "
    "gain is clearly bigger than that.\n"
    "4. ALL MONEY INVESTED: hold 10 holdings at all times. If you sell one, buy a replacement in the same answer "
    "(a coin if the stock market is closed).\n")

W_SYSTEM = (
    f"You are the WATCHER in a two-AI trading team. Every {U} you see the markets, the account and any news "
    f"published that {U}. You cannot trade. Your partner, the DECIDER, is a slower, careful AI that can buy and "
    "sell; it sleeps until you wake it.\n" + RULES +
    f"YOUR JOB EACH {U.upper()}: write 1 to 3 plain sentences about what is actually going on right now (prices, news, the "
    "holdings) - in your own words, no labels. Then decide whether the decider should look now. Wake it when a "
    "buy or sell is probably worth considering: for example a holding is above break-even and its rise is turning "
    "down, important news about a holding or the whole market, empty slots or idle cash, or a rare opportunity. "
    f"Do not wake it for ordinary wiggles or unimportant headlines - most {U}s the answer is no.\n"
    "Every wake costs the team about 5 minutes. The decider writes down what it is waiting for (THE DECIDER'S "
    "CONDITIONS below). Wake it only when one of those conditions has actually been met, or when something new and "
    "important has happened that it has not seen yet. Never wake it again for the same situation it already declined.\n"
    "End with one line: 'WAKE: YES - <short reason>' or 'WAKE: NO'.")

D_SYSTEM = (
    "You are the DECIDER in a two-AI trading team. You sleep until the WATCHER (a fast AI that looks at every "
    f"{U}) wakes you; then you see the full picture and decide.\n" + RULES +
    "Think freely and creatively: write in plain sentences what you see going on, what matters and why, and what "
    "you will do. No fixed labels. Doing nothing is a fine answer.\n"
    "End with exactly these two lines:\n"
    "NOTE: a note to yourself for next time (under 40 words)\n"
    "ACTIONS: 'BUY SYMBOL' or 'SELL SYMBOL' items separated by ';' (use the symbols exactly as shown, e.g. "
    "BTC-USD or NVDA), or NONE")


class Server:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.proc = subprocess.Popen([sys.executable, os.path.join(HERE, SERVER_FILE), "--port", str(self.port)],
                                     stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            self.proc.kill()
            raise RuntimeError(line)
        print(line.strip(), flush=True)
        self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=300)
        return self

    def next(self, orders):
        self.conn.request("POST", "/next", json.dumps({"orders": orders}), {"Content-Type": "application/json"})
        return json.loads(self.conn.getresponse().read())

    def __exit__(self, *exc):
        self.conn.close()
        self.proc.terminate()
        self.proc.wait(timeout=30)


def chat(model, system, user, max_tokens, extra=None, stream=False, temperature=None):
    """One chat request on the shared key limit; streaming for models that queue a long time before answering."""
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens, **(extra or {})}
    if temperature is not None:
        body["temperature"] = temperature
    if stream:
        body["stream"] = True
    hdr = {"Authorization": "Bearer proxy-injected", "Content-Type": "application/json"}
    last = None
    for k in range(1, 9):
        CT.throttle()
        try:
            r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), hdr), timeout=900)
            if not stream:
                return (json.load(r)["choices"][0]["message"].get("content") or "").strip()
            text = []
            for line in r:
                line = line.decode("utf-8", "replace").strip()
                if line.startswith("data:") and "[DONE]" not in line:
                    d = json.loads(line[5:])
                    if d.get("choices"):
                        text.append(d["choices"][0].get("delta", {}).get("content") or "")
            out = "".join(text).strip()
            if out:
                return out
            body["messages"][1]["content"] = user + "\n\nKeep your thinking short and give your answer now."
            body["max_tokens"] = max(max_tokens, 12000)
        except urllib.error.HTTPError as e:
            last = e
            time.sleep(min(120, float(e.headers.get("retry-after") or 15)) if e.code == 429 else min(60, 2 ** k))
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, KeyError, OSError) as e:
            last = e
            time.sleep(min(60, 2 ** k))
    raise RuntimeError(f"AI call kept failing: {last}")


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


class View:
    """Builds the text both AIs read, from what the server has handed out so far."""

    def __init__(self):
        self.kind, self.group, self.hist, self.prev_close = {}, {}, [], {}
        self.first_c, self.first_s, self.snaps = None, None, []   # start of the data and each UTC midnight
        self.first_t = None

    def add(self, out):
        if out.get("universe"):
            for u in out["universe"]:
                self.kind[u["symbol"]], self.group[u["symbol"]] = u["kind"], u["group"]
        st = out["step"]
        if st.get("stock_prev_close"):
            self.prev_close = st["stock_prev_close"]
            if self.first_s is None:
                self.first_s = dict(st["stock_prev_close"])
        if self.first_c is None:
            self.first_c, self.first_t = dict(st["open"]), st["time"]
        if st["time"].endswith("00:00"):
            self.snaps.append((st["time"][:10], {k: v for k, v in st["close"].items()}))
        self.hist.append(st)
        self.hist = self.hist[-(DAY + HOUR):]

    def lines(self, acc, entries, highs, n_move):
        st = self.hist[-1]
        c = st["close"]
        hr = self.hist[-HOUR] if len(self.hist) >= HOUR else self.hist[0]
        day = self.hist[-DAY] if len(self.hist) >= DAY else self.hist[0]
        mins = self.hist[-2] if len(self.hist) >= 2 else st
        coins = [s for s, k in self.kind.items() if k == "crypto" and s in c]
        stocks = [s for s, k in self.kind.items() if k == "stock" and s in c]
        open_ = st["stock_market_open"]
        L = [f"Time: {st['known_at']} UTC. US stock market: {'OPEN' if open_ else 'CLOSED (stock orders refused)'}."]
        b = "BTC-USD"
        L.append(f"Bitcoin ${c[b]:,.2f}: last {U} {pct(c[b], mins['close'][b]):+.2f}%, {RECENT} "
                 f"{pct(c[b], hr['close'][b]):+.2f}%, 24 hours {pct(c[b], day['open'][b]):+.2f}%.")
        if "SPY" in c and "SPY" in self.prev_close:
            L.append(f"SPY (S&P 500 fund) ${c['SPY']:,.2f}: {pct(c['SPY'], self.prev_close['SPY']):+.2f}% since the last "
                     f"session's close" + (f", {RECENT} {pct(c['SPY'], hr['close'].get('SPY', c['SPY'])):+.2f}%" if open_ else "")
                     + ".")
        by = defaultdict(list)
        for s in coins:
            if s in day["open"]:
                by[self.group[s]].append(pct(c[s], day["open"][s]))
        L.append("Coins by size, last 24 hours: " + ", ".join(f"{g} {sum(v) / len(v):+.2f}%" for g, v in
                                                             sorted(by.items(), key=lambda x: -sum(x[1]) / len(x[1]))))
        mv = sorted((pct(c[s], hr["close"][s]), s) for s in coins if s in hr["close"])
        L.append(f"Coins rising most, {RECENT}: " + ", ".join(f"{s} {m:+.2f}%" for m, s in reversed(mv[-n_move:])))
        L.append(f"Coins falling most, {RECENT}: " + ", ".join(f"{s} {m:+.2f}%" for m, s in mv[:n_move]))
        d24 = sorted((pct(c[s], day["open"][s]), s) for s in coins if s in day["open"])
        L.append(f"Coins fallen most, last 24 hours (average coin {sum(m for m, _ in d24) / len(d24):+.2f}%): "
                 + ", ".join(f"{s} {m:+.2f}%" for m, s in d24[:n_move]))
        if self.prev_close:
            sd = sorted((pct(c[s], self.prev_close[s]), s) for s in stocks if s in self.prev_close and s != "SPY")
            bys = defaultdict(list)
            for m, s in sd:
                bys[self.group[s]].append(m)
            L.append(("Stock sectors" if open_ else "Stock sectors (market closed; last session)") + " vs previous close: "
                     + ", ".join(f"{g} {sum(v) / len(v):+.2f}%" for g, v in sorted(bys.items(), key=lambda x: -sum(x[1]) / len(x[1]))))
            L.append("Stocks up most vs previous close: " + ", ".join(f"{s} {m:+.2f}%" for m, s in reversed(sd[-n_move:])))
            L.append(f"Stocks down most vs previous close (average stock {sum(m for m, _ in sd) / len(sd):+.2f}%): "
                     + ", ".join(f"{s} {m:+.2f}%" for m, s in sd[:n_move]))
            if open_:
                sh = sorted((pct(c[s], hr["close"][s]), s) for s in stocks if s in hr["close"] and s != "SPY")
                L.append(f"Stocks moving most, {RECENT}: " + ", ".join(f"{s} {m:+.2f}%" for m, s in reversed(sh[-4:]))
                         + " | " + ", ".join(f"{s} {m:+.2f}%" for m, s in sh[:4]))
        ago = self.hist[-HOUR - 1] if len(self.hist) > HOUR else self.hist[0]
        blocks = [self.hist[max(0, len(self.hist) - 1 - HOUR + BLOCK * k)] for k in range(7)]

        def trend(s):
            out = ""
            for a, b in zip(blocks, blocks[1:]):
                m = pct(b["close"].get(s, 0), a["close"].get(s, 0)) if a["close"].get(s) else 0.0
                out += "↑" if m > 0.05 else "↓" if m < -0.05 else "→"
            return out

        if len(self.snaps) >= 1:
            L.append("THE DAYS SO FAR (UTC days; change over each day):")
            snaps = self.snaps[-14:]                       # at most the last 14 days
            pts = ([(self.first_t[5:], self.first_c)] if len(self.snaps) <= 14 else []) + \
                [(d[5:], snap) for d, snap in snaps] + [("now", c)]
            cs = [x for x in coins if x in self.first_c]
            for (d0, a), (d1, b) in zip(pts, pts[1:]):
                avg = sum(pct(b[x], a[x]) for x in cs if x in a and x in b) / len(cs)
                spy = f", SPY {pct(b['SPY'], a['SPY']):+.2f}%" if "SPY" in a and "SPY" in b and a["SPY"] != b["SPY"] else ""
                L.append(f"- {d0} to {d1}: Bitcoin {pct(b[ 'BTC-USD'], a['BTC-USD']):+.2f}%, average coin {avg:+.2f}%{spy}")
        L.append(f"EVERY COIN - price, last {U} %, {RECENT} %, 24 hours %, since {self.first_t[5:10]} %, then the "
                 f"{RECENT} in six {BLOCK_LABEL} steps (↑ rising, ↓ falling, → flat); grouped by size:")
        for g in sorted({self.group[s] for s in coins}):
            L.append(f"  {g}: " + "; ".join(
                f"{s.removesuffix('-USD')} {c[s]:.5g} {pct(c[s], mins['close'].get(s, c[s])):+.2f} "
                f"{pct(c[s], ago['close'].get(s, c[s])):+.1f} {pct(c[s], day['open'].get(s, c[s])):+.1f} "
                f"{pct(c[s], self.first_c.get(s, c[s])):+.1f} {trend(s)}"
                for s in coins if self.group[s] == g))
        if self.prev_close:
            L.append(f"EVERY STOCK - price, % since the last close, % since the first close in the data" + (
                f", last {U} %, {RECENT} %, then the {RECENT} in six {BLOCK_LABEL} steps" if open_ else
                " (market closed: prices are the last session's)") + "; grouped by sector:")
            for g in sorted({self.group[s] for s in stocks}):
                L.append(f"  {g}: " + "; ".join(
                    f"{s} {c[s]:.5g} {pct(c[s], self.prev_close.get(s, c[s])):+.1f} "
                    f"{pct(c[s], (self.first_s or {}).get(s, c[s])):+.1f}"
                    + (f" {pct(c[s], mins['close'].get(s, c[s])):+.2f} {pct(c[s], ago['close'].get(s, c[s])):+.1f} "
                       f"{trend(s)}" if open_ else "")
                    for s in stocks if self.group[s] == g))
        held = acc.get("shares", {})
        L.append(f"ACCOUNT: ${acc.get('value', 1000.0):,.2f}; cash ${acc.get('cash', 1000.0):,.2f}; trades so far "
                 f"{acc.get('trades', 0)}, costs paid ${acc.get('costs', 0.0):.2f}; empty slots {SLOTS - len(held)}.")
        if held:
            L.append("HOLDINGS (only these can be sold):")
            for s, q in held.items():
                e = entries.get(s)
                ok = e and c[s] * 0.9995 >= e * 1.0005
                L.append(f"- {s} ({self.kind.get(s)}, {self.group.get(s)}): ${q * c[s]:,.2f}, now ${c[s]:.6g}"
                         + (f", bought at ${e:.6g}, {pct(c[s] * 0.9995, e * 1.0005):+.2f}% after costs, "
                            + ("above break-even (CAN SELL)" if ok else "below break-even (HOLD)") if e else "")
                         + (f", {pct(c[s], highs[s]):+.2f}% from its high since bought" if s in highs else "")
                         + f", {RECENT} {pct(c[s], hr['close'].get(s, c[s])):+.2f}%")
        else:
            L.append("HOLDINGS: none, all cash.")
        return L


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("time") != "time"]


def parse_actions(text, kind):
    line = ""
    for ln in text.splitlines():
        if ln.strip().upper().startswith("ACTIONS"):
            line = ln.split(":", 1)[1] if ":" in ln else ""
    acts = []
    for part in re.split(r"[;,]", line):
        m = re.match(r"[\s*'\"`]*(BUY|SELL)\s+\$?([A-Za-z0-9.\-]{1,20})", part.strip(), re.I)
        if not m:
            continue
        s = m.group(2).upper().rstrip(".")
        if s not in kind and s + "-USD" in kind:
            s += "-USD"
        if s in kind:
            acts.append({"action": m.group(1).upper(), "symbol": s})
    return acts


def main():
    w_saved, d_saved = load(W_FILE), load(D_FILE)
    d_by_time = {r["time"]: r for r in d_saved}
    wf, df = open(W_FILE, "a", newline=""), open(D_FILE, "a", newline="")
    ww = csv.DictWriter(wf, ["time", "wake", "text", "seconds", "value", "btc_hold", "spy_hold", "new_news"])
    dw = csv.DictWriter(df, ["time", "actions", "blocked", "note", "seconds", "value", "raw", "forced"])
    if not w_saved:
        ww.writeheader()
    if not d_saved:
        dw.writeheader()
    view = View()
    entries, highs, pending, orders = {}, {}, [], {}
    w_notes, d_notes, news_since_wake, recent_news = [], [], [], []
    i_w, n_wake, t0, btc_sent, spy_sent, last_dec = 0, 0, time.time(), False, False, "none yet"
    with Server() as srv:
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
            news_since_wake += out["news"]
            recent_news = (recent_news + out["news"])[-400:]
            news_since_wake = news_since_wake[-60:]
            if len(view.hist) <= WARMUP or out["last_step"] or st["time"] < START_AT:
                continue
            if not btc_sent:
                orders["btc_hold"] = [{"action": "BUY", "symbol": "BTC-USD", "all": True}]
                btc_sent = True
            if not spy_sent and st["stock_market_open"]:
                orders["spy_hold"] = [{"action": "BUY", "symbol": "SPY", "all": True}]
                spy_sent = True
            accs = out["accounts"]
            # ---- the watcher, every minute ----
            base = view.lines(acc, entries, highs, 5)
            if i_w < len(w_saved):
                r = w_saved[i_w]
                assert r["time"] == st["time"], f"saved watcher answers out of step at {st['time']}"
                wtext, wake = r["text"], r["wake"] == "1"
            else:
                hour_news = [n for n in recent_news if n["time"] >= view.hist[-HOUR - 1]["known_at"]][-80:]
                L = base + [f"HEADLINES FROM THE {RECENT.upper()} (UTC time; newest last; * = published this {U}):"] + \
                    ([f"- {n['time'][11:]}{' *' if n in out['news'] else ''} {n['title']}" for n in hour_news]
                     or ["- none"])
                if refused:
                    L.append(f"ORDERS REFUSED LAST {U.upper()}: " + "; ".join(f"{o['action']} {o['symbol']} ({o['why']})" for o in refused))
                L.append(f"THE DECIDER'S LAST DECISION: {last_dec}")
                if d_notes:
                    L.append(f"THE DECIDER'S CONDITIONS (what it is waiting for, in its own words): {d_notes[-1][1]}")
                if w_notes:
                    L.append(f"YOUR LAST {NOTES_N} NOTES (oldest first):")
                    L += [f"- {t[6:] if STEP == 1 else t}: {x[:160]}" for t, x in w_notes[-NOTES_N:]]
                if i_w == 0:
                    L.append(f"This is the first {U} of the test: the account is all cash, so the decider must invest it."
                             + (" Everything above (the days so far, 24-hour and since-start moves, headlines) is "
                                "what happened before you started." if START_AT else ""))
                t1 = time.time()
                wtext = chat(WATCHER, W_SYSTEM, "\n".join(L), 400, {"chat_template_kwargs": {"enable_thinking": False}},
                             temperature=0)
                m = re.search(r"WAKE\s*:\s*(YES|NO)", wtext, re.I)
                wake = bool(m and m.group(1).upper() == "YES") or i_w == 0
                ww.writerow({"time": st["time"], "wake": int(wake), "text": wtext.replace("\n", " / ")[:900],
                             "seconds": f"{time.time() - t1:.2f}", "value": f"{acc.get('value', 1000.0):.2f}",
                             "btc_hold": f"{accs.get('btc_hold', {}).get('value', 1000.0):.2f}",
                             "spy_hold": f"{accs.get('spy_hold', {}).get('value', 1000.0):.2f}", "new_news": len(out["news"])})
                wf.flush()
            i_w += 1
            said = re.sub(r"\s*/?\s*WAKE\s*:.*$", "", wtext.replace("\n", " / "), flags=re.I | re.S).strip()
            w_notes.append((st["known_at"][5:], said[:300]))
            if i_w % 120 == 0:
                print(f"{st['time']} ${acc.get('value', 1000.0):,.2f} | BTC ${accs.get('btc_hold', {}).get('value', 1000.0):,.2f} "
                      f"SPY ${accs.get('spy_hold', {}).get('value', 1000.0):,.2f} | holds {','.join(held) or 'cash'} | "
                      f"watcher answers {i_w}, wakes {n_wake} [{time.time() - t0:.0f}s]", flush=True)
            if not wake:
                continue
            # ---- the decider, only when woken ----
            n_wake += 1
            if st["time"] in d_by_time:
                r = d_by_time[st["time"]]
                acts, note = json.loads(r["actions"]), r["note"]
            else:
                L = view.lines(acc, entries, highs, 10)
                L.append("WHY THE WATCHER WOKE YOU: " + (re.search(r"WAKE\s*:\s*YES\s*[-:]?\s*(.*)", wtext, re.I | re.S)
                                                         or re.search(r"(.*)", "")).group(1)[:300])
                L.append("THE WATCHER'S NOTES SINCE YOU LAST DECIDED (newest last):")
                L += [f"- {t}: {x}" for t, x in w_notes[-10:]]
                L.append("HEADLINES SINCE YOU LAST DECIDED (newest last, with UTC time):")
                L += [f"- {n['time'][5:]} {n['title']}" for n in news_since_wake[-40:]] or ["- none"]
                if refused:
                    L.append(f"ORDERS REFUSED LAST {U.upper()}: " + "; ".join(f"{o['action']} {o['symbol']} ({o['why']})" for o in refused))
                if d_notes:
                    L.append("YOUR NOTEBOOK (your earlier notes):")
                    L += [f"- {t}: {x}" for t, x in d_notes[-6:]]
                prompt = "\n".join(L)
                t1 = time.time()
                text = chat(DECIDER, D_SYSTEM, prompt, 8000, stream=True)
                acts = parse_actions(text, view.kind)
                forced = ""
                tradable = lambda a: view.kind.get(a["symbol"]) == "crypto" or st["stock_market_open"]
                for _ in range(2):                           # keep all money invested: fill empty slots
                    after = (set(held) - {a["symbol"] for a in acts if a["action"] == "SELL" and tradable(a)}) | \
                        {a["symbol"] for a in acts if a["action"] == "BUY" and tradable(a)}
                    empty = SLOTS - len(after)
                    if empty <= 0:
                        break
                    allowed = "coins or stocks" if st["stock_market_open"] else "coins only (the stock market is closed)"
                    extra = chat(DECIDER, D_SYSTEM, prompt + f"\n\nYOUR ANSWER WAS:\n{text}\n\nThat leaves {empty} empty "
                                 f"slot(s) and cash uninvested. All money must stay invested. You already own or are "
                                 f"buying: {', '.join(sorted(after)) or 'nothing'}. Name exactly {empty} other {allowed} "
                                 f"to BUY now from the symbols shown. Answer with one line: ACTIONS: BUY X; BUY Y; ...",
                                 4000, stream=True)
                    acts += [a for a in parse_actions(extra if "ACTIONS" in extra.upper() else "ACTIONS: " + extra,
                                                      view.kind) if a["action"] == "BUY"]
                    forced += extra.replace("\n", " / ")[:300] + " | "
                note = ""
                for ln in text.splitlines():
                    if ln.strip().upper().startswith("NOTE"):
                        note = ln.split(":", 1)[-1].strip()[:300]
                dw.writerow({"time": st["time"], "actions": json.dumps(acts), "blocked": "", "note": note,
                             "seconds": f"{time.time() - t1:.1f}", "value": f"{acc.get('value', 1000.0):.2f}",
                             "raw": text.replace("\n", " / ")[:3000], "forced": forced})
                df.flush()
                print(f"  DECIDER {st['time']}: {json.dumps(acts)} | {note[:120]}", flush=True)
            d_notes.append((st["known_at"][5:], note))
            news_since_wake = []
            # rules the program enforces before sending
            ok, seen = [], set()
            for a in acts:
                s = a["symbol"]
                bad = (a["action"] == "BUY" and (s in held or s in seen)) or (a["action"] == "SELL" and s not in held)
                bad = bad or (view.kind.get(s) == "stock" and not st["stock_market_open"])
                bad = bad or (a["action"] == "SELL" and s in entries and st["close"][s] * 0.9995 < entries[s] * 1.0005)
                if not bad:
                    ok.append(dict(a, split=True) if a["action"] == "BUY" else a)
                    seen.add(s)
            sells = [a["symbol"] for a in ok if a["action"] == "SELL"]
            free = SLOTS - len(held) + len(sells)
            ok = [a for a in ok if a["action"] == "SELL"] + [a for a in ok if a["action"] == "BUY"][:max(0, free)]
            last_dec = (f"{st['known_at']} UTC: " + ("; ".join(f"{a['action']} {a['symbol']}" for a in ok) or "no trades")
                        + (f" - note: {note[:150]}" if note else ""))
            orders["ai"] = ok
            pending = ok
        final = out
    wf.close()
    df.close()
    with open(os.path.join(HERE, f"result_{TAG}.json"), "w") as fh:
        json.dump(final.get("accounts", {}), fh, indent=1)
    print("finished:", json.dumps({k: round(v.get("value", 0), 2) for k, v in final.get("accounts", {}).items()}),
          f"watcher answers {i_w}, decider woken {n_wake} times", flush=True)


if __name__ == "__main__":
    main()
