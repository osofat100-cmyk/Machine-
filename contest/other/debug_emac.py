import os, sys
sys.argv = ["x", "emac", "PEARL/USDT:USDT"]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "venv/lib/python3.13/site-packages/cryptobots/strategies"))
import emac
orig = emac.Emac.generate_signal
calls = {"n": 0}
def wrapped(self, dt):
    calls["n"] += 1
    n = 2 * self.trend_ema_period
    d = self.exchange.get_candles(self.instrument, granularity=self.granularity, count=n)
    if calls["n"] in (1, 50, 500) :
        print("call", calls["n"], dt, "candles", len(d), "pos", self.current_position(), flush=True)
        if len(d) >= n:
            c, a, t = self.generate_features(d); print(" cross last", c.iloc[-5:].tolist(), "trend", t, flush=True)
    return orig(self, dt)
emac.Emac.generate_signal = wrapped
exec(open(os.path.join(HERE, "run_cryptobots.py")).read())
