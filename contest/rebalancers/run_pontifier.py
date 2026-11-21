#!/usr/bin/env python3
"""pontifier/rebalancer coinbase.py (2015, Python 2), unchanged: places one buy and one sell limit order of
trade_size around the price that keeps `ratio`, polls every poll_delay seconds, cancels the other side when one
fills, repeats.

Runs on Python 3 with three Python-2 shims and stand-ins: the module name ConfigParser (= configparser), open()
accepting str in binary mode (it writes a str to an 'ab' file at start), and `requests` (its Coinbase Exchange
REST calls: accounts, orders, orders/<id>) backed by the price server. Resting orders lock their funds like on an
exchange; a limit fills when a minute's low/high touches it (at the next minute's close). time.sleep(poll_delay)
moves the test forward (2 polls of 30 s per minute).
README: "balance your account manually before starting" (it divides by the coin balance), so 20% PEARL is bought
by hand on 1 Oct 00:00 first. Config: its coinbase.cfg with ratio 0.8 (its formula makes ratio the USD share;
20% PEARL), ratio_spread .002, poll_delay 30 (shipped), trade_size 10 PEARL (shipped .01 is BTC; rule: about 1% of
the account at the 30 Sep price).

    venv/bin/python run_pontifier.py --port 8839
"""
import argparse
import builtins
import configparser
import json
import math
import os
import sys
import types

import common

SRC = os.path.join(common.HERE, "downloads", "pontifier_rebalancer", "coinbase.py")


class Done(Exception):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8839)
    a = ap.parse_args()
    box = os.path.join(common.HERE, "home_pontifier")
    os.makedirs(box, exist_ok=True)
    os.chdir(box)
    with open("coinbase.cfg", "w") as f:
        f.write("[coinbase]\nratio=.8\nratio_spread=.002\ntrade_size=10\noffline_btc=0\noffline_usd=0\n"
                f"poll_delay=30\nlog_file={box}/coinbase_trade_log.txt\nverbose = false\n"
                "api_key=\napi_secret=\napi_passphrase=\n")

    feed = common.Feed(a.port)
    q = math.floor(200 / (feed.price * 1.007) / common.STEP) * common.STEP
    feed.market("BUY", q, "user's own first balancing buy (README), not the program")
    feed.step()
    meta, rejected = {}, []

    def locked():
        c = sum(o["size"] * o["price"] for i, o in meta.items() if o["side"] == "buy" and i in feed.limits)
        k = sum(o["size"] for i, o in meta.items() if o["side"] == "sell" and i in feed.limits)
        return c, k

    class Resp:
        def __init__(self, body):
            self.body = body

        def json(self):
            return self.body

        def iter_content(self, n):
            return [json.dumps(self.body).encode()]

    def get(url, auth=None):
        path = url.split(".com/")[-1]
        if path == "accounts":
            return Resp([{"currency": "USD", "balance": str(feed.cash)}, {"currency": "BTC", "balance": str(feed.coins)}])
        oid = int(path.split("/")[1])
        o = meta[oid]
        return Resp({"id": str(oid), "status": "open" if oid in feed.limits else "done", "side": o["side"],
                     "price": o["price"]})

    def post(url, data=None, auth=None):
        o = json.loads(data)
        size, price = float(o["size"]), float(o["price"])
        c, k = locked()
        if (o["side"] == "buy" and size * price > feed.cash - c + 1e-9) or \
           (o["side"] == "sell" and size > feed.coins - k + 1e-9) or size * price < common.MIN_COST:
            rejected.append((feed.time, o))
            return Resp({"message": "Insufficient funds"})
        oid = feed.limit(o["side"], size, price, f"{o['side']} {size} @ {price}")
        meta[oid] = {"side": o["side"], "size": size, "price": price}
        return Resp({"id": str(oid)})

    def delete(url, auth=None):
        feed.cancel(int(url.split("/")[-1]))
        return Resp({})

    class AuthBase:
        pass

    req = types.ModuleType("requests")
    req.get, req.post, req.delete = get, post, delete
    req.auth = types.SimpleNamespace(AuthBase=AuthBase)
    sys.modules["requests"], sys.modules["requests.auth"] = req, req.auth
    sys.modules["ConfigParser"] = configparser

    def py2_open(file, mode="r", *args, **kw):
        fh = builtins.open(file, mode, *args, **kw)
        if "b" in mode:
            w = fh.write
            fh.write = lambda s: w(s.encode() if isinstance(s, str) else s)
        return fh

    polls = [0]

    def sleep(seconds):
        polls[0] += 1
        if polls[0] % 2 == 0 and not feed.step():
            raise Done

    import time as real_time
    clock = types.SimpleNamespace(sleep=sleep, time=lambda: feed.now * 60,
                                  strftime=lambda fmt, *t: real_time.strftime(fmt, real_time.gmtime(feed.now * 60)))
    src = open(SRC).read()
    ns = {"__name__": "__main__", "open": py2_open, "print": lambda *x, **k: None}
    code = compile(src, SRC, "exec")
    crash = None
    try:
        import time as _t
        sys.modules["time"] = clock
        exec(code, ns)
    except Done:
        pass
    except SystemExit as e:
        crash = f"sys.exit({e.code}) at {feed.time}"
    except Exception as e:
        crash = f"{type(e).__name__}: {e} at {feed.time}"
    finally:
        sys.modules["time"] = _t
    if crash:
        print("program stopped:", crash, flush=True)
    acct = feed.finish()
    label = "ratio 0.8 (= 20% PEARL), trade size 10 PEARL, two resting limits, poll 30 s"
    common.report(f"pontifier/rebalancer coinbase.py [{label}]", acct)
    feed.save(os.path.join(common.HERE, "log_pontifier.csv"), acct)
    note = ("Python 2 program (ConfigParser, str written to binary file) run with shims; first 20% buy done by hand "
            f"as its README says (counted in fills); {len(rejected)} orders rejected for funds/min size. "
            "Other versions: btce.py/mtgox.py target dead exchanges; binance_trade.py crashes at once "
            "(ratio/size/sell_order_id undefined, ['tatus'] typo)")
    if crash:
        note += f"; PROGRAM STOPPED: {crash}"
    common.sealed.record("pontifier/rebalancer (coinbase.py)", label, "A", len(acct["trades"]), acct["value"],
                         "ran", note)


if __name__ == "__main__":
    main()
