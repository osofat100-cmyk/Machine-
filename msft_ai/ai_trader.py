#!/usr/bin/env python3
"""
A free, open AI (Llama 3.2 3B Instruct, run on this machine; its training data ends December 2023) trades Microsoft
with $1,000 of practice money, one day at a time, 2 Jan 2024 .. 20 Nov 2026.

After each close it sees only what day_server.py has handed out so far (prices, competitors, market and economic
gauges, Microsoft's SEC filings and results, headlines) and answers BUY, SELL or HOLD with a one-line reason. The order
fills at the next open. Days of 2022-2023 are handed out first as background history; no decisions are made then.

Every answer is appended to msft_ai/answers.csv (and the full prompt to data/msft_prompts.jsonl) the moment it is
given. If the run stops, starting it again replays the saved answers without asking the AI again, then continues.

    python3 msft_ai/ai_trader.py
"""
import csv
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL = os.path.join(HERE, "models", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
ANSWERS = os.path.join(HERE, "answers.csv")
VALUES = os.path.join(HERE, "values.csv")
LAST_DAY = "2026-11-20"
PROMPTS = os.path.join(ROOT, "data", "msft_prompts.jsonl")
FIRST_DECISION = "2023-12-29"          # decide after this close -> first fill at the 2 Jan 2024 open
COMPETITORS = ["AAPL", "GOOGL", "AMZN", "META", "NVDA", "ORCL", "CRM"]
NAMES = {"AAPL": "Apple", "GOOGL": "Alphabet (Google)", "AMZN": "Amazon", "META": "Meta", "NVDA": "Nvidia",
         "ORCL": "Oracle", "CRM": "Salesforce", "SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq-100 (QQQ)",
         "XLK": "Tech sector (XLK)"}
SYSTEM = (
    "You manage a practice trading account that can hold only one stock, Microsoft (MSFT), or cash. "
    "After each market close you receive the latest information and decide what to do at the next morning's open:\n"
    "BUY = put all the money in MSFT (if already in MSFT, nothing changes)\n"
    "SELL = move all the money to cash, which earns the 3-month T-bill rate (if already in cash, nothing changes)\n"
    "HOLD = keep the current position\n"
    "Each buy or sell costs 0.05% of the amount traded. Your goal is to finish with as much money as possible.\n"
    "Answer with exactly one word, BUY, SELL or HOLD, then ' - ' and one short sentence giving the main reason."
)
GRAMMAR = r'''root ::= ("BUY" | "SELL" | "HOLD") " - " [^\n]{5,160}'''


# ------------------------------------------------------------------------------------------------ server

class Server:
    def __enter__(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.proc = subprocess.Popen([sys.executable, os.path.join(HERE, "day_server.py"), "--port", str(self.port)],
                                     stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline()
        if not line.startswith("ready"):
            self.proc.kill()
            raise RuntimeError(f"day server did not start: {line!r}")
        self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=300)
        return self

    def next(self, orders):
        self.conn.request("POST", "/next", body=json.dumps({"orders": orders}),
                          headers={"Content-Type": "application/json"})
        r = self.conn.getresponse()
        out = json.loads(r.read())
        if r.status != 200:
            raise RuntimeError(out)
        return out

    def __exit__(self, *exc):
        self.conn.close()
        self.proc.terminate()
        self.proc.wait(timeout=30)


# ------------------------------------------------------------------------------------------------ prompt

def pct(a, b):
    return f"{(a / b - 1) * 100:+.1f}%"


def ret(series, k):
    return pct(series[-1], series[-1 - k]) if len(series) > k else "n/a"


def build_prompt(hist, position, value):
    """hist: list of served days, oldest first, the last one being today. Uses nothing else."""
    today = hist[-1]
    P = lambda key: [d["prices"][key] for d in hist if key in d["prices"]]   # noqa: E731
    m = P("MSFT_close")
    vol = P("MSFT_volume")
    d0 = date.fromisoformat(today["date"])
    L = [f"Date: {today['date']} ({d0.strftime('%A')}), after the close.",
         f"Your position: {'all in MSFT' if position else 'all in cash'}. Account value: ${value:,.2f}.", "",
         "MICROSOFT (MSFT)",
         f"Close ${m[-1]:.2f}; change: 1 day {ret(m, 1)}, 1 week {ret(m, 5)}, 1 month {ret(m, 21)}, "
         f"3 months {ret(m, 63)}, 1 year {ret(m, 252)}",
         f"Versus its 50-day average {pct(m[-1], np.mean(m[-50:]))}, 200-day average {pct(m[-1], np.mean(m[-200:]))}; "
         f"52-week high ${max(m[-252:]):.2f}, low ${min(m[-252:]):.2f}",
         f"Volume today versus 20-day average: {pct(vol[-1], np.mean(vol[-20:]))}",
         "Last 10 closes: " + ", ".join(f"{x:.2f}" for x in m[-10:]), "",
         "MARKET AND COMPETITORS (change over 1 day / 1 week / 1 month)"]
    for s in ["SPY", "QQQ", "XLK"] + COMPETITORS:
        c = P(f"{s}_close")
        L.append(f"{NAMES[s]}: {ret(c, 1)} / {ret(c, 5)} / {ret(c, 21)}")
    v, t10, tb, dx, oil = P("VIX"), P("TNX10Y"), P("TBILL3M"), P("DOLLAR"), P("OIL")
    L += ["", "ECONOMY",
          f"VIX fear index {v[-1]:.1f} (1 week ago {v[-6]:.1f}); 10-year Treasury yield {t10[-1]:.2f}% "
          f"(1 month ago {t10[-22]:.2f}%); 3-month T-bill {tb[-1]:.2f}%",
          f"US dollar index 1 month {ret(dx, 21)}; oil 1 month {ret(oil, 21)}", ""]
    # Microsoft's reported results, as filed so far
    res = [x for d in hist for x in d["sec_results"]]
    if res:
        latest_end = max(x["end"] for x in res)
        q = {x["item"]: x for x in res if x["end"] == latest_end}
        prev = {x["item"]: x for x in res if x["end"][:4] == str(int(latest_end[:4]) - 1)
                and x["end"][5:] == latest_end[5:]}
        parts = []
        for item, label in [("revenue", "revenue"), ("net_income", "net income")]:
            if item in q:
                g = f" ({pct(q[item]['value'], prev[item]['value'])} vs a year earlier)" if item in prev else ""
                parts.append(f"{label} ${q[item]['value'] / 1e9:.1f} billion{g}")
        if "eps_diluted" in q:
            parts.append(f"earnings per share ${q['eps_diluted']['value']:.2f}")
        filed = max(x["filed"] for x in q.values())
        L.append(f"MICROSOFT LATEST REPORTED QUARTER (ended {latest_end}, filed {filed}): " + ", ".join(parts))
    recent = [x for d in hist[-5:] for x in d["sec_filings"]]
    if recent:
        L.append("Microsoft SEC filings in the last 5 trading days: "
                 + "; ".join(f"{x['form']} on {x['filed']}" + (f" (items {x['items']})" if x["items"] else "")
                             for x in recent))
    L.append("")
    news = [n for d in reversed(hist[-3:]) for n in d["news"]]
    for topic, title, k in [("microsoft", "HEADLINES ABOUT MICROSOFT", 8), ("msft_stock", "HEADLINES ABOUT MSFT STOCK", 4),
                            ("competitors", "HEADLINES ABOUT COMPETITORS", 5), ("economy", "HEADLINES ABOUT THE ECONOMY", 5)]:
        items = [n for n in news if n["topic"] == topic][:k]
        if items:
            L.append(title + " (last 3 trading days, newest first)")
            L += [f"- {n['date']}: {n['title']}" for n in items]
    L += ["", "Your decision for tomorrow's open (BUY, SELL or HOLD - reason):"]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ main

def load_saved():
    if not os.path.exists(ANSWERS):
        return {}
    with open(ANSWERS, newline="") as f:
        return {r["date"]: r for r in csv.DictReader(f)}


def main():
    saved = load_saved()
    llm = None
    new_file = not os.path.exists(ANSWERS)
    fa = open(ANSWERS, "a", newline="")
    w = csv.writer(fa)
    if new_file:
        w.writerow(["date", "decision", "reason", "position_before", "value", "prompt_tokens", "seconds"])
    os.makedirs(os.path.dirname(PROMPTS), exist_ok=True)
    fp = open(PROMPTS, "a")
    fv = open(VALUES, "w", newline="")                          # re-made in full on every run (replay is exact)
    wv = csv.writer(fv)
    wv.writerow(["date", "ai", "hold_msft"])
    hist, position, orders = [], 0, {}
    t_start = time.time()
    with Server() as srv:
        while True:
            out = srv.next(orders)
            if out.get("done"):
                break
            hist.append(out["day"])
            today = hist[-1]["date"]
            orders = {}
            if today < FIRST_DECISION:
                continue
            if today > FIRST_DECISION:
                wv.writerow([today, f"{out['values']['ai']:.6f}", f"{out['values']['hold_msft']:.6f}"])
                fv.flush()
            if today >= LAST_DAY:
                break
            value = out["values"].get("ai", 1000.0)
            if today == FIRST_DECISION:
                orders["hold_msft"] = "BUY"                     # yardstick: buy at the first open, never sell
            if today in saved:
                decision, reason = saved[today]["decision"], saved[today]["reason"]
            else:
                if llm is None:
                    from llama_cpp import Llama, LlamaGrammar
                    llm = Llama(model_path=MODEL, n_ctx=4096, n_threads=4, seed=0, verbose=False)
                    grammar = LlamaGrammar.from_string(GRAMMAR, verbose=False)
                prompt = build_prompt(hist, position, value)
                t0 = time.time()
                r = llm.create_chat_completion(
                    messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                    temperature=0.0, max_tokens=60, grammar=grammar, seed=0)
                text = r["choices"][0]["message"]["content"].strip()
                decision, _, reason = text.partition(" - ")
                secs = time.time() - t0
                w.writerow([today, decision, reason, position, f"{value:.2f}", r["usage"]["prompt_tokens"], f"{secs:.1f}"])
                fa.flush()
                fp.write(json.dumps({"date": today, "prompt": prompt, "answer": text}) + "\n")
                fp.flush()
                n_done = sum(1 for _ in open(ANSWERS)) - 1
                print(f"{today}  {decision:<4} pos={position} ${value:,.2f}  {secs:.1f}s  "
                      f"[{n_done} answers, {time.time() - t_start:.0f}s]  {reason[:90]}", flush=True)
            orders["ai"] = decision
            if decision == "BUY":
                position = 1
            elif decision == "SELL":
                position = 0
    fa.close()
    fp.close()
    fv.close()
    print("finished", flush=True)


if __name__ == "__main__":
    main()
