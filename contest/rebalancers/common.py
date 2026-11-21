"""Stand-in exchange for the rebalancer contest (way A, see ../RULES.md).

The price server keeps the money. A program sees only history before 1 Oct plus the minutes handed out so far.
Market orders go with the next request and fill at that minute's close (0.7% cost per side, charged by the server).
A resting limit order "fills" when a later minute's low (buy) or high (sell) touches its price; it is then sent
as an order with the next request and fills at that next minute's close, like every other order in the contest.
The server takes one order per request, so several queued orders go out one minute apart.
"""
import csv
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sealed  # noqa: E402

STEP = 0.0001          # BigONE PEARL/USDT amount and price step (from CCXT)
MIN_COST = 2.0         # BigONE PEARL/USDT smallest order, USDT
OCT1 = 29846880        # 2026-10-01 00:00 in minutes since 1970


class Feed:
    def __init__(self, port):
        h = sealed.history_before_oct()
        ts = ((h["time"] - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(minutes=1)).astype(int).tolist()
        self.T, self.O = ts, h["open"].astype(float).tolist()
        self.H, self.L = h["high"].astype(float).tolist(), h["low"].astype(float).tolist()
        self.C, self.V = h["close"].astype(float).tolist(), h["volume"].astype(float).tolist()
        assert self.T[-1] < OCT1
        self.queue, self.limits, self.filled, self._lid = [], {}, set(), 0
        self.decisions = []
        self.sealed = sealed.Sealed(port).__enter__()
        self.m = self.sealed.next()
        self._add(self.m)

    def _add(self, m):
        self.T.append(m["ts"]); self.O.append(m["open"]); self.H.append(m["high"])
        self.L.append(m["low"]); self.C.append(m["close"]); self.V.append(m["volume"])

    # what the program can see
    @property
    def now(self):
        return self.m["ts"]

    @property
    def price(self):
        return self.m["close"]

    @property
    def cash(self):
        return self.m["cash"]

    @property
    def coins(self):
        return self.m["coins"]

    @property
    def time(self):
        return self.m["time"]

    def candles(self, tf, n, partial=True):
        """Last n candles of tf minutes (aligned to whole tf from 1970), current unfinished one included if partial.
        Returns dict of numpy arrays: ts (candle start, minutes), open, high, low, close, volume."""
        end = len(self.T)
        start = max(0, end - (n + 2) * tf)
        t = np.asarray(self.T[start:end]); g = t // tf
        cut = np.flatnonzero(np.diff(g)) + 1
        idx = np.concatenate([[0], cut])
        last = np.concatenate([cut - 1, [len(t) - 1]])
        o = np.asarray(self.O[start:end])[idx]; c = np.asarray(self.C[start:end])[last]
        hi = np.maximum.reduceat(np.asarray(self.H[start:end]), idx)
        lo = np.minimum.reduceat(np.asarray(self.L[start:end]), idx)
        v = np.add.reduceat(np.asarray(self.V[start:end]), idx)
        ts = g[idx] * tf
        if not partial and (t[-1] % tf) != tf - 1:
            ts, o, hi, lo, c, v = ts[:-1], o[:-1], hi[:-1], lo[:-1], c[:-1], v[:-1]
        k = slice(-n, None)
        return {"ts": ts[k], "open": o[k], "high": hi[k], "low": lo[k], "close": c[k], "volume": v[k]}

    # orders
    def market(self, side, qty, note=""):
        side = side.upper()
        if qty > 0:
            self.queue.append((side, float(qty)))
            self.decisions.append((self.time, side, float(qty), self.price, note))

    def limit(self, side, qty, price, note=""):
        self._lid += 1
        self.limits[self._lid] = {"side": side.upper(), "qty": float(qty), "price": float(price), "note": note}
        return self._lid

    def cancel(self, lid):
        return self.limits.pop(lid, None) is not None

    def step(self):
        if self.queue:
            side, qty = self.queue.pop(0)
            m = self.sealed.next(side, qty=qty)
        else:
            m = self.sealed.next()
        if m is None:
            return False
        self.m = m
        self._add(m)
        for lid, o in list(self.limits.items()):
            if (o["side"] == "BUY" and m["low"] <= o["price"]) or (o["side"] == "SELL" and m["high"] >= o["price"]):
                del self.limits[lid]
                self.filled.add(lid)
                self.queue.append((o["side"], o["qty"]))
                self.decisions.append((m["time"], o["side"], o["qty"], o["price"], f"limit {lid} touched; {o['note']}"))
        return True

    def finish(self):
        while self.step():
            pass
        self.sealed.__exit__(None, None, None)
        return self.sealed.account

    def save(self, path, account):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["decided_utc", "side", "qty", "price_seen", "note"])
            w.writerows(self.decisions)
            w.writerow([])
            w.writerow(["filled_utc", "action", "price", "account_$", "cash", "coins", "source"])
            for t in account["trades"]:
                w.writerow([t["time"], t["action"], t["price"], round(t["value"], 2), round(t["cash"], 2),
                            round(t["coins"], 4), t["source"]])
            w.writerow(["end " + account["last"], "", "", round(account["value"], 2)])
            w.writerow(["just holding", "", "", round(account["holding"], 2)])


def report(name, account):
    print(f"{name}: $1,000 -> ${account['value']:,.2f} after {len(account['trades'])} fills "
          f"(holding ${account['holding']:,.2f})", flush=True)
