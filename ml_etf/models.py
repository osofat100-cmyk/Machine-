"""
The three model kinds and the settings menu (PLAN.md section 5). Every model has fit(X, y) and predict(X).
Inputs are standardised with the training rows' mean and standard deviation.
"""
import warnings

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor

MENU = {
    "ridge": [{"alpha": 1.0}, {"alpha": 10.0}, {"alpha": 100.0}, {"alpha": 1000.0}],
    "gbm": [{"max_leaf_nodes": 4, "max_iter": 100}, {"max_leaf_nodes": 4, "max_iter": 300},
            {"max_leaf_nodes": 6, "max_iter": 100}, {"max_leaf_nodes": 6, "max_iter": 300}],
    "mlp": [{"hidden": (16,), "alpha": 1e-3}, {"hidden": (16,), "alpha": 1e-1},
            {"hidden": (32, 16), "alpha": 1e-3}, {"hidden": (32, 16), "alpha": 1e-1}],
}
KINDS = ("ridge", "gbm", "mlp")
SEEDS = range(10)


class Model:
    def __init__(self, kind, setting):
        self.kind, self.setting = kind, dict(setting)

    def fit(self, X, y):
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd[self.sd == 0] = 1.0
        Z = (X - self.mu) / self.sd
        s = self.setting
        if self.kind == "ridge":
            self.m = [Ridge(alpha=s["alpha"]).fit(Z, y)]
            self.yscale = 1.0
        elif self.kind == "gbm":
            self.m = [HistGradientBoostingRegressor(learning_rate=0.05, max_leaf_nodes=s["max_leaf_nodes"],
                                                    max_iter=s["max_iter"], early_stopping=False,
                                                    random_state=0).fit(Z, y)]
            self.yscale = 1.0
        else:
            self.yscale = float(np.std(y)) or 1.0       # MLP trains on y in units of its own spread
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ConvergenceWarning)
                self.m = [MLPRegressor(hidden_layer_sizes=s["hidden"], alpha=s["alpha"], solver="adam",
                                       max_iter=60, batch_size=256, early_stopping=False,
                                       random_state=seed).fit(Z, y / self.yscale) for seed in SEEDS]
        return self

    def predict(self, X):
        Z = (X - self.mu) / self.sd
        return np.mean([m.predict(Z) for m in self.m], axis=0) * self.yscale


def name(kind, setting):
    if kind == "ridge":
        return f"ridge(alpha={setting['alpha']:g})"
    if kind == "gbm":
        return f"gbm(leaves={setting['max_leaf_nodes']},trees={setting['max_iter']})"
    return f"mlp(hidden={setting['hidden']},alpha={setting['alpha']:g})"
