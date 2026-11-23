#!/usr/bin/env python3
"""
Version 2 (after version 1 kept switching on noise): the prompt spells out the 0.10% round-trip cost, shows trades and
costs paid so far and the break-even price, and allows only possible moves (in cash: BUY or HOLD; in MSFT: SELL or HOLD).

Two fast AIs trade Microsoft minute by minute over the last month (26 Oct .. 23 Nov 2026; the first day is background
only). Both use NVIDIA's free Nemotron 3.5 Bolt (about 0.2 s per answer). The next minute is handed out the moment
the AI answers. Orders fill at the next minute's open; 0.05% per trade.

  pattern : looks only at Microsoft's price moving up and down; sees headlines only after a big move
            (15-minute move of 0.75% or more, or 2.5% or more from the previous close).
  thinker : the checklist (long or short term? trend? news good or bad? risk?) plus a memory notebook of its own
            last notes and decisions, with headlines, the market (SPY, QQQ) and the daily background.

Every answer is appended to msft_ai/minute_answers_<style>.csv the moment it is given; running again replays saved
answers (no new AI calls) and continues from where it stopped.

    python3 msft_ai/fast_traders.py pattern
    python3 msft_ai/fast_traders.py thinker
"""
import csv
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "nvidia/nemotron-3.5-bolt-e4b"
BIG_15MIN, BIG_DAY = 0.75, 2.5            # % moves that count as a big spike or drop (pattern AI sees news then)

RULES = (
    "RULES YOU MUST FOLLOW:\n"
    "1. Trading costs money. Every BUY costs 0.05% of the amount and every SELL costs another 0.05%, so buying and "
    "later selling costs 0.10% in total. A trade only makes sense if you expect the price to move clearly more than "
    "0.10% in your favour before you trade back. Switching back and forth on small wiggles loses money.\n"
    "2. You can only SELL shares you own. If you are in cash you own no shares: your only choices are BUY or HOLD. "
    "If you are in MSFT you already own it: your only choices are SELL or HOLD.\n")
SYSTEM_PATTERN = (
    "You trade Microsoft (MSFT) minute by minute with a practice account that is either all in MSFT or all in "
    "cash. Each minute you get the latest one-minute price bars. Decide for the next minute: BUY (be all in MSFT), "
    "SELL (be all in cash) or HOLD (keep the current position). Focus on how the price is moving. Headlines are shown "
    "only when the price has made an unusually big move.\n" + RULES +
    "Answer exactly: BUY, SELL or HOLD, then ' - ' and a few words of reason.")
SYSTEM_THINKER = (
    "You trade Microsoft (MSFT) with a practice account that is either all in MSFT or all in cash. You get new "
    "information every minute and decide for the next minute: BUY (be all in MSFT), SELL (be all in cash) or HOLD "
    "(keep the current position). Before deciding, answer the checklist.\n" + RULES +
    "Keep a plan: your notebook shows your last notes and decisions.\n"
    "Answer in exactly this form, one line each:\n"
    "TERM: LONG or SHORT (is your current view long-term holding or short-term trading?)\n"
    "TREND: UP, DOWN or FLAT (price over the last hour and the day)\n"
    "NEWS: GOOD, BAD or NONE (does recent news matter for Microsoft? a few words)\n"
    "RISK: LOW, MEDIUM or HIGH (is something bad happening or coming?)\n"
    "NOTE: a note to yourself for the next minutes (under 20 words)\n"
    "DECISION: BUY, SELL or HOLD")


class Server:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.proc = subprocess.Popen([sys.executable, os.path.join(HERE, "minute_server.py"), "--port",
                                      str(self.port)], stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            self.proc.kill()
            raise RuntimeError(line)
        self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        return self

    def next(self, orders):
        self.conn.request("POST", "/next", body=json.dumps({"orders": orders}))
        return json.loads(self.conn.getresponse().read())

    def __exit__(self, *exc):
        self.conn.close()
        self.proc.terminate()
        self.proc.wait(timeout=30)


def ask(system, user, max_tokens):
    body = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": system},
                                                    {"role": "user", "content": user}],
                       "temperature": 0, "max_tokens": max_tokens}).encode()
    for k in range(8):
        try:
            req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=body,
                                         headers={"Authorization": "Bearer proxy-injected",
                                                  "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(req, timeout=60))
            return (j["choices"][0]["message"].get("content") or "").strip(), j.get("usage", {})
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last = e
            time.sleep(min(60, 2 ** k))
    raise RuntimeError(f"AI call kept failing: {last}")


def pct(a, b):
    return (a / b - 1) * 100


def price_block(bars, prev_close, position, entry, book, value):
    c = [b["MSFT_close"] for b in bars]
    today = [b for b in bars if b["time"][:10] == bars[-1]["time"][:10]]
    if position and entry:
        even = entry * (1.0005 / 0.9995)                  # price that only just covers the buy and the sell cost
        held = (f"You OWN MSFT, bought at ${entry:.2f}. Break-even after costs: ${even:.2f}. "
                f"If you sold now: {pct(c[-1] * 0.9995, entry * 1.0005):+.2f}% after costs.")
    else:
        held = "You are in CASH and own no MSFT shares."
    L = [f"Time: {bars[-1]['time']} New York. {held}",
         f"Account ${value:,.2f}. Trades so far: {book.get('trades', 0)}, trading costs paid so far: "
         f"${book.get('costs', 0.0):.2f}.",
         f"MSFT ${c[-1]:.2f}; change: 1 min {pct(c[-1], c[-2]):+.2f}%, 5 min {pct(c[-1], c[-6]):+.2f}%, "
         f"15 min {pct(c[-1], c[-16]):+.2f}%, 60 min {pct(c[-1], c[-61]):+.2f}%, today {pct(c[-1], today[0]['MSFT_open']):+.2f}%"
         + (f", since yesterday's close {pct(c[-1], prev_close):+.2f}%" if prev_close else ""),
         f"Today's high ${max(b['MSFT_high'] for b in today):.2f}, low ${min(b['MSFT_low'] for b in today):.2f}",
         "Last 15 minutes (close, volume): " + ", ".join(f"{b['MSFT_close']:.2f}/{int(b['MSFT_volume'] / 1000)}k"
                                                         for b in bars[-15:])]
    return L


def run(style):
    path = os.path.join(HERE, f"minute_answers_{style}.csv")
    saved = []
    if os.path.exists(path):
        with open(path, newline="") as f:
            saved = list(csv.DictReader(f))
    fields = ["time", "decision", "reason", "note", "position_before", "news_shown", "seconds", "invalid", "raw"]
    fa = open(path, "a", newline="")
    w = csv.DictWriter(fa, fieldnames=fields)
    if not saved:
        w.writeheader()
    system = SYSTEM_PATTERN if style == "pattern" else SYSTEM_THINKER
    bars, news, ctx, notes = [], [], {}, []
    position, entry, prev_close, orders, n, t0, hold_sent = 0, None, None, {}, 0, time.time(), False
    with Server() as srv:
        while True:
            out = srv.next(orders)
            if out.get("done"):
                break
            m = out["minute"]
            if bars and bars[-1]["time"][:10] != m["time"][:10]:
                prev_close = bars[-1]["MSFT_close"]
            bars.append(m)
            news += out["news"]
            ctx = out.get("day_context", ctx)
            orders = {}
            if out["last_minute"] or prev_close is None or len(bars) < 61:
                continue                                   # first day is background only
            if not hold_sent:
                orders["hold_msft"] = "BUY"                # yardstick: buy at the first trading minute, never sell
                hold_sent = True
            L = price_block(bars, prev_close, position, entry, out.get("books", {}).get(style, {}),
                            out["values"].get(style, 1000.0))
            c = [b["MSFT_close"] for b in bars]
            big = abs(pct(c[-1], c[-16])) >= BIG_15MIN or abs(pct(c[-1], prev_close)) >= BIG_DAY
            shown = 0
            if style == "pattern":
                if big:
                    recent = [x for x in news if x["topic"] in ("microsoft", "msft_stock")][-6:]
                    L += ["BIG MOVE - latest headlines about Microsoft:"] + [f"- {x['known']}: {x['title']}" for x in reversed(recent)]
                    shown = len(recent)
                max_tokens = 30
            else:
                s, q = [b["SPY_close"] for b in bars], [b["QQQ_close"] for b in bars]
                L += [f"Market: S&P 500 (SPY) 15 min {pct(s[-1], s[-16]):+.2f}%, today {pct(s[-1], [b for b in bars if b['time'][:10] == m['time'][:10]][0]['SPY_close']):+.2f}%; "
                      f"Nasdaq-100 (QQQ) 15 min {pct(q[-1], q[-16]):+.2f}%"]
                if ctx:
                    L.append("Background (up to yesterday): " + json.dumps({k: v for k, v in ctx.items() if k != "as_of"}))
                recent = news[-8:]
                L += ["Latest headlines (newest first):"] + [f"- {x['known']} [{x['topic']}]: {x['title']}" for x in reversed(recent)]
                shown = len(recent)
                if notes:
                    L += ["Your notebook (oldest first):"] + [f"- {t} {d}: {nt}" for t, d, nt in notes[-6:]]
                max_tokens = 120
            L.append("You are in CASH: answer BUY or HOLD (you cannot sell shares you do not own)." if not position
                     else "You OWN MSFT: answer SELL or HOLD (buying again does nothing).")
            key_i = n
            if key_i < len(saved):
                r = saved[key_i]
                assert r["time"] == m["time"], f"saved answers out of step at {m['time']}"
                decision, reason, note = r["decision"], r["reason"], r["note"]
            else:
                t1 = time.time()
                text, usage = ask(system, "\n".join(L), max_tokens)
                secs = time.time() - t1
                decision, reason, note = "HOLD", "", ""
                if style == "pattern":
                    word = text.split(" - ")[0].strip().upper().split()[0] if text else ""
                    decision = word if word in ("BUY", "SELL", "HOLD") else "HOLD"
                    reason = text.partition(" - ")[2][:200]
                else:
                    fields_out = {ln.split(":", 1)[0].strip().upper(): ln.split(":", 1)[1].strip()
                                  for ln in text.splitlines() if ":" in ln}
                    d = fields_out.get("DECISION", "").upper().split()
                    decision = d[0] if d and d[0] in ("BUY", "SELL", "HOLD") else "HOLD"
                    note = fields_out.get("NOTE", "")[:200]
                    reason = " | ".join(f"{k} {fields_out.get(k, '')}" for k in ("TERM", "TREND", "NEWS", "RISK"))[:300]
                invalid = (decision == "SELL" and not position) or (decision == "BUY" and position)
                if invalid:
                    decision = "HOLD"                           # an impossible move counts as HOLD; logged
                w.writerow({"time": m["time"], "decision": decision, "reason": reason, "note": note, "invalid": int(invalid),
                            "position_before": position, "news_shown": shown, "seconds": f"{secs:.2f}",
                            "raw": text.replace("\n", " / ")[:500]})
                fa.flush()
                if n % 100 == 0:
                    v = out["values"].get(style, 1000.0)
                    print(f"{style} {m['time']} {decision:<4} pos={position} value ${v:,.2f} "
                          f"hold ${out['values'].get('hold_msft', 1000.0):,.2f} {secs:.2f}s [{n} answers, "
                          f"{time.time() - t0:.0f}s] {reason[:70]}", flush=True)
            n += 1
            if style == "thinker":
                notes.append((m["time"][11:], decision, note))
            orders[style] = decision
            if decision == "BUY" and not position:
                position, entry = 1, c[-1]
            elif decision == "SELL" and position:
                position, entry = 0, None
        final = srv.next(orders) if not out.get("done") else out
    fa.close()
    with open(os.path.join(HERE, f"minute_result_{style}.json"), "w") as f:
        json.dump(final.get("accounts", {}), f, indent=1)
    print(f"{style} finished: {n} answers; accounts {json.dumps(final.get('accounts', {}))}", flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
