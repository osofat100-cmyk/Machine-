import os, sys
sys.argv = ["x", "emac", "PEARL/USDT:USDT"]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "venv/lib/python3.13/site-packages/cryptobots/strategies"))
import emac
orig = emac.Emac.generate_signal
st = {"n": 0, "x": []}
def wrapped(self, dt):
    st["n"] += 1
    d = self.exchange.get_candles(self.instrument, granularity=self.granularity, count=2 * self.trend_ema_period)
    if st["n"] in (1,2,3,100,1000): print("last idx", d.index[-1], len(d), d["Close"].iloc[-1], flush=True)
    if len(d) >= 400:
        c, a, t = self.generate_features(d)
        if c.iloc[-1] != 0: st["x"].append((str(dt), float(c.iloc[-1]), float(t), str(d.index[-1])))
    out = orig(self, dt)
    if out: print("ORDERS", dt, out, flush=True)
    return out
emac.Emac.generate_signal = wrapped
exec(open(os.path.join(HERE, "run_cryptobots.py")).read())
print("calls", st["n"], "crossovers", st["x"][:20])
