"""Adaptive explicit Runge–Kutta integrators with per-step error records.

DormandPrince54: the classic RK5(4) pair (Dormand & Prince 1980, J. Comput.
Appl. Math. 6, 19; coefficients as in Hairer, Nørsett & Wanner, "Solving
Ordinary Differential Equations I", 2nd ed., Table 5.2) with FSAL, PI-type
step-size control, a user-supplied maximum-step function, and exact
termination at a target value of a monotonic monitor function (used to stop
precisely at each milestone radius).  Every accepted step records the step
size and the normalized embedded error estimate, which are saved with the
trajectory.

An independent cross-check integrator (scipy DOP853, 8th order) is wrapped
in :func:`integrate_scipy_dop853` for the convergence test.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

# Dormand–Prince 5(4) Butcher tableau
_C = np.array([0.0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1.0, 1.0])
_A = [
    [],
    [1 / 5],
    [3 / 40, 9 / 40],
    [44 / 45, -56 / 15, 32 / 9],
    [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
    [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656],
    [35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84],
]
_B5 = np.array([35 / 384, 0.0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0.0])
_B4 = np.array([5179 / 57600, 0.0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40])
_E = _B5 - _B4


@dataclass
class StepRecord:
    x: float
    h: float
    err: float          # normalized error estimate of the accepted step (<= 1)
    n_rejected: int     # rejected attempts before this accepted step
    y: np.ndarray


@dataclass
class IntegrationResult:
    x: np.ndarray
    y: np.ndarray               # shape (n_steps+1, n_state)
    h: np.ndarray               # step used to reach each row (0 for the initial row)
    err: np.ndarray             # normalized error estimate for each accepted step
    n_rejected: np.ndarray
    n_rhs_evals: int
    n_accepted: int
    n_rejected_total: int
    terminated_by_event: bool
    status: str
    max_err: float = 0.0
    min_h: float = math.inf
    max_h: float = 0.0


@dataclass
class DormandPrince54:
    rtol: float = 1e-12
    atol: np.ndarray | float = 1e-14
    max_step: float = math.inf
    max_step_fn: Optional[Callable[[float, np.ndarray], float]] = None
    min_step: float = 1e-300
    safety: float = 0.9
    fac_min: float = 0.2
    fac_max: float = 5.0
    max_steps: int = 2_000_000

    def _scale(self, y0: np.ndarray, y1: np.ndarray) -> np.ndarray:
        atol = np.broadcast_to(np.asarray(self.atol, dtype=float), y0.shape)
        return atol + self.rtol * np.maximum(np.abs(y0), np.abs(y1))

    def _err_norm(self, delta: np.ndarray, scale: np.ndarray) -> float:
        with np.errstate(divide="ignore", invalid="ignore"):
            q = np.where(scale > 0.0, delta / scale, np.where(delta == 0.0, 0.0, np.inf))
        return float(math.sqrt(np.mean(q * q)))

    def integrate(self, fun: Callable[[float, np.ndarray], np.ndarray], x0: float, y0: np.ndarray,
                  x_end: float, h0: Optional[float] = None,
                  event: Optional[Callable[[float, np.ndarray], float]] = None,
                  after_step: Optional[Callable[[float, np.ndarray], np.ndarray]] = None,
                  ) -> IntegrationResult:
        """Integrate y' = fun(x, y) from x0 to x_end.

        event(x, y): monotonic scalar that changes sign exactly once; the
        integration stops at the step where it crosses zero, with the final
        step shrunk iteratively (secant on the step length) so that the end
        point satisfies event = 0 to integrator accuracy.
        after_step(x, y) -> y: optional projection applied to each accepted state
        (used to resynchronize r = exp(x) in ln r mode).
        """
        direction = 1.0 if x_end >= x0 else -1.0
        x = float(x0)
        y = np.array(y0, dtype=float)
        n = y.size
        xs: List[float] = [x]
        ys: List[np.ndarray] = [y.copy()]
        hs: List[float] = [0.0]
        errs: List[float] = [0.0]
        rejs: List[int] = [0]
        nfev = 0
        n_acc = 0
        n_rej_total = 0
        max_err = 0.0
        min_h, max_h = math.inf, 0.0
        terminated = False
        status = "reached_x_end"

        k1 = fun(x, y)
        nfev += 1
        ev_prev = event(x, y) if event is not None else None

        # initial step guess (Hairer et al. I.4)
        if h0 is None:
            sc = self._scale(y, y)
            # components with relative-only control that start at exactly zero have no scale yet:
            sc = np.where(sc > 0.0, sc, self.rtol * np.maximum(np.abs(k1), 1.0))
            d0 = self._err_norm(y, sc)
            d1 = self._err_norm(k1, sc)
            h = 1e-6 if (d0 < 1e-5 or d1 < 1e-5) else 0.01 * d0 / d1
            h = min(h, abs(x_end - x0))
        else:
            h = abs(h0)
        h = min(h, self.max_step)
        if self.max_step_fn is not None:
            h = min(h, self.max_step_fn(x, y))

        n_rej_here = 0
        K = np.empty((7, n))
        for _ in range(self.max_steps):
            if direction * (x - x_end) >= 0.0:
                break
            h = min(h, abs(x_end - x))
            if h < self.min_step:
                status = "step_size_underflow"
                break
            hd = direction * h
            K[0] = k1
            for i in range(1, 7):
                yi = y + hd * sum(_A[i][j] * K[j] for j in range(i))
                K[i] = fun(x + _C[i] * hd, yi)
            nfev += 6
            y_new = y + hd * (_B5 @ K)
            delta = hd * (_E @ K)
            sc = self._scale(y, y_new)
            err = self._err_norm(delta, sc)
            if err <= 1.0 or h <= self.min_step * 1.0001:
                x_new = x + hd
                k1_new = K[6]  # FSAL
                if after_step is not None:
                    y_new = after_step(x_new, y_new)
                    k1_new = fun(x_new, y_new)
                    nfev += 1
                # --- event handling: shrink the step to land on event == 0 ---
                if event is not None:
                    ev_new = event(x_new, y_new)
                    if ev_prev is not None and (ev_prev * ev_new < 0.0 or ev_new == 0.0):
                        x_new, y_new, nf, ok = self._locate_event(fun, event, x, y, k1, hd, ev_prev, after_step)
                        nfev += nf
                        k1_new = fun(x_new, y_new)
                        nfev += 1
                        terminated = True
                        status = "event"
                        h_used = abs(x_new - x)
                        xs.append(x_new); ys.append(y_new.copy()); hs.append(h_used); errs.append(err); rejs.append(n_rej_here)
                        n_acc += 1
                        min_h = min(min_h, h_used); max_h = max(max_h, h_used); max_err = max(max_err, err)
                        x, y, k1 = x_new, y_new, k1_new
                        break
                    ev_prev = ev_new
                xs.append(x_new); ys.append(y_new.copy()); hs.append(h); errs.append(err); rejs.append(n_rej_here)
                n_acc += 1
                min_h = min(min_h, h); max_h = max(max_h, h); max_err = max(max_err, err)
                x, y, k1 = x_new, y_new, k1_new
                n_rej_here = 0
                fac = self.fac_max if err == 0.0 else min(self.fac_max, max(self.fac_min, self.safety * err ** (-0.2)))
                h = h * fac
            else:
                n_rej_here += 1
                n_rej_total += 1
                fac = max(self.fac_min, self.safety * err ** (-0.2))
                h = h * fac
            h = min(h, self.max_step)
            if self.max_step_fn is not None:
                h = min(h, self.max_step_fn(x, y))
        else:
            status = "max_steps_exceeded"

        return IntegrationResult(
            x=np.array(xs), y=np.array(ys), h=np.array(hs), err=np.array(errs), n_rejected=np.array(rejs),
            n_rhs_evals=nfev, n_accepted=n_acc, n_rejected_total=n_rej_total,
            terminated_by_event=terminated, status=status, max_err=max_err, min_h=min_h, max_h=max_h,
        )

    def _rk_step(self, fun, x, y, k1, hd):
        n = y.size
        K = np.empty((7, n))
        K[0] = k1
        for i in range(1, 7):
            yi = y + hd * sum(_A[i][j] * K[j] for j in range(i))
            K[i] = fun(x + _C[i] * hd, yi)
        return y + hd * (_B5 @ K), 6

    def _locate_event(self, fun, event, x, y, k1, hd, ev_prev, after_step):
        """Secant/bisection on the step length so that event(x+h, y(h)) = 0."""
        nf = 0
        h_lo, e_lo = 0.0, ev_prev
        h_hi = hd
        y_hi, n = self._rk_step(fun, x, y, k1, h_hi); nf += n
        if after_step is not None:
            y_hi = after_step(x + h_hi, y_hi)
        e_hi = event(x + h_hi, y_hi)
        h_best, y_best = h_hi, y_hi
        for _ in range(60):
            if e_hi == e_lo:
                break
            h_try = h_hi - e_hi * (h_hi - h_lo) / (e_hi - e_lo)
            # keep inside bracket
            lo, hi = sorted((h_lo, h_hi))
            if not (lo < h_try < hi):
                h_try = 0.5 * (h_lo + h_hi)
            y_try, n = self._rk_step(fun, x, y, k1, h_try); nf += n
            if after_step is not None:
                y_try = after_step(x + h_try, y_try)
            e_try = event(x + h_try, y_try)
            h_best, y_best = h_try, y_try
            if e_try == 0.0:
                break
            if e_try * e_lo < 0.0:
                h_hi, e_hi, y_hi = h_try, e_try, y_try
            else:
                h_lo, e_lo = h_try, e_try
            if abs(h_hi - h_lo) <= 1e-15 * abs(hd) + 1e-300:
                break
        return x + h_best, y_best, nf, True


def integrate_scipy_dop853(fun, x0, y0, x_end, rtol=1e-13, atol=1e-16, max_step=math.inf, events=None):
    """Independent cross-check with SciPy's DOP853 (Hairer's 8(5,3) Dormand–Prince)."""
    from scipy.integrate import solve_ivp

    sol = solve_ivp(fun, (x0, x_end), y0, method="DOP853", rtol=rtol, atol=atol, max_step=max_step,
                    events=events, dense_output=False)
    return sol
