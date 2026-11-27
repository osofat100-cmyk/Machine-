#!/usr/bin/env python3
"""Writes mixed/chat_glm_ultra.md: every time Ultra woke GLM - Ultra's message and GLM's answer, in order."""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
w = {r["time"]: r for r in csv.DictReader(open(os.path.join(HERE, "watcher_glm_ultra.csv")))}
d = list(csv.DictReader(open(os.path.join(HERE, "decider_glm_ultra.csv"))))
L = ["# Ultra and GLM: every wake-up so far", "",
     "Each time Ultra (the watcher) woke GLM (the decider): what Ultra said, then GLM's answer. Times are market time (UTC).",
     "", "**What GLM is shown each time it wakes:** the time and whether the stock market is open; Bitcoin and SPY moves; "
     "coins by size; coins rising and falling most in the last hour; coins fallen most in 24 hours; stock sectors and the "
     "stocks up and down most since the last close; the account and every holding (price paid, gain or loss after costs, "
     "break-even status, distance from its high); why Ultra woke it; Ultra's last 10 notes; the headlines since its last "
     "decision; refused orders; and its own notebook.", ""]
for i, r in enumerate(d, 1):
    wr = w.get(r["time"], {})
    acts = json.loads(r["actions"])
    L += [f"## {i}. {r['time']} (account ${r['value']})", "",
          f"**Ultra:** {wr.get('text', '').replace(' / ', ' ').strip()}", "",
          f"**GLM** (answered in {float(r['seconds']) / 60:.1f} min):", "",
          r["raw"].replace(" /  / ", "\n\n").replace(" / ", "\n"), "",
          "**Orders:** " + ("; ".join(f"{a['action']} {a['symbol']}" for a in acts) or "none (hold)"), ""]
open(os.path.join(HERE, "chat_glm_ultra.md"), "w").write("\n".join(L))
print(len(d), "wake-ups written")
