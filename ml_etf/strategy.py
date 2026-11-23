"""
One strategy = one model kind + one setting + one horizon h (PLAN.md section 6).

Decisions are made after the close every h trading days, counted from the run's first decision day s0. Training
happens at s0 (the model then belongs to the year of s0 + 1) and again after the close of the first trading day of
every later year, before that day's decision. A decision after day t's close fills at day t+1's open.
"""
import numpy as np

import features as F
from models import Model

THRESHOLD = 0.001          # invest only if the predicted SPY excess return beats one round-trip cost (0.10%)


class Strategy:
    def __init__(self, kind, setting, h):
        self.kind, self.setting, self.h = kind, setting, h
        self.year = None
        self.trained_at = []

    def train(self, S, M, sel, tim, tau, first, year):
        days = F.train_days(tau, self.h, first)
        Xs = F.selection_X(S, M, days)
        ys = sel[days].reshape(-1)
        Xt = F.timing_X(S, M, days)
        yt = tim[days]
        assert not np.isnan(ys).any() and not np.isnan(yt).any(), "a training answer is not known yet"
        self.sel_model = Model(self.kind, self.setting).fit(Xs, ys)
        self.tim_model = Model(self.kind, self.setting).fit(Xt, yt)
        self.year = year
        self.trained_at.append((int(tau), int(days[-1]), len(days)))

    def decide(self, S, M, t):
        """-> (choice, timing forecast, selection forecasts): choice = symbol index, or -1 for cash."""
        f_tim = float(self.tim_model.predict(F.timing_X(S, M, t))[0])
        f_sel = self.sel_model.predict(F.selection_X(S, M, t))
        choice = int(np.argmax(f_sel)) if f_tim > THRESHOLD else -1
        return choice, f_tim, f_sel


def year_of(dates, t):
    return int(str(dates[t])[:4])


def run_decisions(p, S, M, sel, tim, strat, s0, end, first):
    """Walk days s0..end on a panel that already holds them (development, or the sealed days already handed out).
    -> list of decisions {day, choice, f_tim, f_sel}."""
    dates = p["dates"]
    out = []
    for t in range(s0, end + 1):
        if t == s0:
            strat.train(S, M, sel, tim, t, first, year_of(dates, t + 1) if t + 1 < len(dates) else year_of(dates, t) + 1)
        elif year_of(dates, t) != strat.year:
            strat.train(S, M, sel, tim, t, first, year_of(dates, t))
        if (t - s0) % strat.h == 0:
            c, ft, fs = strat.decide(S, M, t)
            out.append({"day": t, "choice": c, "f_tim": ft, "f_sel": fs})
    return out
