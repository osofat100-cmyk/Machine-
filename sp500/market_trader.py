#!/usr/bin/env python3
"""
A fast AI (NVIDIA's free Nemotron 3.5 Bolt) runs a $1,000 practice portfolio of the ~500 largest US stocks for the
last ~2 months, one 5-minute step at a time, with the checklist, a memory notebook, the cost rules and news that is
handed out only at its exact publication minute. It may hold up to 10 stocks (10% slots) plus cash, and may make up
to 3 buys or sells per step. The yardstick is holding SPY over the same steps.

Every answer is appended to sp500/answers.csv the moment it is given; running again replays saved answers and
continues from where it stopped.

    python3 sp500/market_trader.py
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
MODEL = "nvidia/nemotron-3.5-bolt-e4b"
ANSWERS = os.path.join(HERE, "answers.csv")
WARMUP = 13                                   # first hour of the first day: background only

SYSTEM = (
    "You manage a $1,000 practice portfolio of large US stocks (about the S&P 500). Every 5 minutes you get the "
    "market, the biggest movers, your holdings and any news published since the last step. You may hold up to 10 "
    "stocks; each BUY puts 10% of the account into one stock; SELL sells the whole holding of that stock into cash "
    "(US dollars, which do not move with the market).\n"
    "RULES YOU MUST FOLLOW:\n"
    "1. Trading costs money: every BUY costs 0.05% and every SELL another 0.05%, so a round trip costs 0.10%. Only "
    "trade when you expect a move clearly bigger than that. Switching back and forth on small wiggles loses money.\n"
    "2. You can only SELL stocks you own (listed under YOUR HOLDINGS). You cannot BUY a stock you already own.\n"
    "3. Sell high, buy low. Do not keep a falling stock just to avoid taking a loss: the price you paid does not "
    "matter, only where the price goes next.\n"
    "4. Use only symbols shown to you.\n"
    "Before deciding, answer the checklist. Keep a plan: your notebook shows your last notes.\n"
    "Answer in exactly this form, one line each:\n"
    "MARKET: UP, DOWN or FLAT\n"
    "NEWS: GOOD, BAD or NONE (a few words on what matters)\n"
    "RISK: LOW, MEDIUM or HIGH\n"
    "NOTE: a note to yourself for the next steps (under 25 words)\n"
    "ACTIONS: up to 3 of 'BUY SYMBOL' or 'SELL SYMBOL' separated by ';', or NONE")


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


def ask(user):
    body = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": SYSTEM},
                                                    {"role": "user", "content": user}],
                       "temperature": 0, "max_tokens": 160}).encode()
    last = None
    for k in range(8):
        try:
            req = urllib.request.Request("https://integrate.api.nvidia.com/v1/chat/completions", data=body,
                                         headers={"Authorization": "Bearer proxy-injected",
                                                  "Content-Type": "application/json"})
            j = json.load(urllib.request.urlopen(req, timeout=90))
            return (j["choices"][0]["message"].get("content") or "").strip()
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last = e
            time.sleep(min(60, 2 ** k))
    raise RuntimeError(f"AI call kept failing: {last}")


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0


def build_prompt(hist, sector_of, acc, entries, news_seen, new_news, notes, refused_now=()):
    st = hist[-1]
    c = st["close"]
    day = [h for h in hist if h["time"][:10] == st["time"][:10]]
    hour = hist[-12] if len(hist) >= 12 else hist[0]
    first = day[0]
    L = [f"Time: {st['known_at']} New York (the 5-minute bar from {st['time'][11:]} has just closed)."]
    s = "SPY"
    L.append(f"MARKET (SPY ${c[s]:.2f}): 5 min {pct(c[s], hist[-2]['close'][s]):+.2f}%, 1 hour "
             f"{pct(c[s], hour['close'][s]):+.2f}%, today {pct(c[s], first['open'][s]):+.2f}%")
    by_sector = defaultdict(list)
    for sym, sec in sector_of.items():
        if sym in c and sym in first["open"]:
            by_sector[sec].append(pct(c[sym], first["open"][sym]))
    L.append("SECTORS today: " + ", ".join(f"{sec} {sum(v) / len(v):+.2f}%" for sec, v in
                                            sorted(by_sector.items(), key=lambda x: -sum(x[1]) / len(x[1])) if sec))
    moves = sorted(((pct(c[x], hour["close"][x]), x) for x in sector_of if x in c and x in hour["close"]))
    L.append("BIGGEST RISERS last hour: " + ", ".join(f"{x} {m:+.2f}% ({sector_of[x]})" for m, x in reversed(moves[-8:])))
    L.append("BIGGEST FALLERS last hour: " + ", ".join(f"{x} {m:+.2f}% ({sector_of[x]})" for m, x in moves[:8]))
    held = acc.get("shares", {})
    L.append(f"YOUR ACCOUNT: ${acc.get('value', 1000.0):,.2f}; cash ${acc.get('cash', 1000.0):,.2f}; trades so far "
             f"{acc.get('trades', 0)}, costs paid ${acc.get('costs', 0.0):.2f}; free slots {10 - len(held)}.")
    if held:
        L.append("YOUR HOLDINGS (you may SELL only these):")
        for sym, q in held.items():
            e = entries.get(sym)
            L.append(f"- {sym} ({sector_of.get(sym, '')}): ${q * c[sym]:,.2f}, now ${c[sym]:.2f}"
                     + (f", bought at ${e:.2f}, {pct(c[sym] * 0.9995, e * 1.0005):+.2f}% after costs" if e else "")
                     + f", 1 hour {pct(c[sym], hour['close'].get(sym, c[sym])):+.2f}%")
    else:
        L.append("YOUR HOLDINGS: none (all cash) - you cannot SELL anything.")
    if new_news:
        L.append("NEWS PUBLISHED SINCE THE LAST STEP:")
        L += [f"- {n['time'][11:]} {n['title']}" for n in new_news[-10:]]
    else:
        L.append("No new news since the last step. Earlier today:")
        L += [f"- {n['time'][11:]} {n['title']}" for n in news_seen[-5:] if n["time"][:10] == st["time"][:10]]
    if refused_now:
        L.append("YOUR LAST ORDERS THAT WERE REFUSED: " + "; ".join(f"{o['action']} {o['symbol']} ({o['why']})"
                                                                     for o in refused_now))
    if notes:
        L.append("YOUR NOTEBOOK:")
        L += [f"- {t}: {nt}" for t, nt in notes[-6:]]
    return "\n".join(L)


def parse(text, universe):
    f = {ln.split(":", 1)[0].strip().upper(): ln.split(":", 1)[1].strip() for ln in text.splitlines() if ":" in ln}
    acts = []
    for part in re.split(r"[;,]", f.get("ACTIONS", "")):
        m = re.match(r"\s*(BUY|SELL)\s+\$?([A-Za-z.]{1,6})", part.strip(), re.I)
        if m and len(acts) < 3:
            sym = m.group(2).upper().replace(".", "")
            acts.append({"action": m.group(1).upper(), "symbol": sym})
    return f, acts


def main():
    saved = []
    if os.path.exists(ANSWERS):
        with open(ANSWERS, newline="") as fh:
            saved = list(csv.DictReader(fh))
    fields = ["time", "actions", "refused", "market", "news", "risk", "note", "value", "spy_hold", "new_news",
              "seconds", "raw"]
    fa = open(ANSWERS, "a", newline="")
    w = csv.DictWriter(fa, fieldnames=fields)
    if not saved:
        w.writeheader()
    hist, news_seen, notes, entries, orders, n, t0 = [], [], [], {}, {}, 0, time.time()
    sector_of, spy_sent, pending = {}, False, []
    with Server() as srv:
        while True:
            out = srv.next(orders)
            if out.get("done"):
                break
            if out.get("universe"):
                sector_of = {u["symbol"]: u["sector"] for u in out["universe"]}
            st = out["step"]
            hist.append(st)
            hist = hist[-80:]
            new_news = out["news"]
            news_seen += new_news
            acc = out["accounts"].get("ai", {"value": 1000.0, "cash": 1000.0, "shares": {}, "trades": 0, "costs": 0.0})
            refused_now = out["refused"].get("ai", [])
            for od in pending:                               # remember buy prices of fills that went through
                if od["action"] == "BUY" and od["symbol"] in acc.get("shares", {}) and od["symbol"] not in entries:
                    entries[od["symbol"]] = st["open"][od["symbol"]]
                if od["action"] == "SELL" and od["symbol"] not in acc.get("shares", {}):
                    entries.pop(od["symbol"], None)
            if refused_now and n > len(saved):
                with open(os.path.join(HERE, "refused.csv"), "a") as fr:
                    for od in refused_now:
                        fr.write(f"{st['time']},{od['action']},{od['symbol']},{od['why']}\n")
            orders, pending = {}, []
            if len(hist) <= WARMUP or out["last_step"]:
                continue
            if not spy_sent:
                orders["spy_hold"] = [{"action": "BUY", "symbol": "SPY", "all": True}]   # all money into SPY, never sold
                spy_sent = True
            if n < len(saved):
                r = saved[n]
                assert r["time"] == st["time"], f"saved answers out of step at {st['time']}"
                acts = json.loads(r["actions"])
                note = r["note"]
            else:
                prompt = build_prompt(hist, sector_of, acc, entries, news_seen, new_news, notes, refused_now)
                t1 = time.time()
                text = ask(prompt)
                secs = time.time() - t1
                f, acts = parse(text, sector_of)
                note = f.get("NOTE", "")[:200]
                spy_v = out["accounts"].get("spy_hold", {}).get("value", 1000.0)
                w.writerow({"time": st["time"], "actions": json.dumps(acts), "refused": "", "market": f.get("MARKET", ""),
                            "news": f.get("NEWS", "")[:200], "risk": f.get("RISK", ""), "note": note,
                            "value": f"{acc.get('value', 1000.0):.2f}", "spy_hold": f"{spy_v:.2f}",
                            "new_news": len(new_news), "seconds": f"{secs:.2f}", "raw": text.replace("\n", " / ")[:600]})
                fa.flush()
                if n % 100 == 0:
                    print(f"{st['time']} value ${acc.get('value', 1000.0):,.2f} vs SPY ${spy_v:,.2f} | holds "
                          f"{','.join(acc.get('shares', {})) or 'cash'} | {json.dumps(acts)} | {secs:.2f}s "
                          f"[{n} answers, {time.time() - t0:.0f}s]", flush=True)
            notes.append((st["known_at"][5:], note))
            orders["ai"] = acts
            pending = acts
            n += 1
        final = out
    fa.close()
    with open(os.path.join(HERE, "result.json"), "w") as fh:
        json.dump(final.get("accounts", {}), fh, indent=1)
    print("finished:", json.dumps({k: round(v.get("value", 0), 2) for k, v in final.get("accounts", {}).items()}),
          flush=True)


if __name__ == "__main__":
    main()
