"""Adaptive explicit Runge–Kutta integrators with per-step error records.

DormandPrince54: the classic RK5(4) pair (Dormand & Prince 1980, J. Comput.
Appl. Math. 6, 19; coefficients as in Hairer, Nørsett & Wanner, "Solving
Ordinary Differential Equations I", 2nd ed., Table 5.2) with FSAL, the PI
step-size controller of Hairer's DOPRI5 (fac = err^-(1/5 - 0.75 beta) *
err_prev^beta, beta = 0.04), a user-supplied maximum-step function, and exact
termination at a target value of a monotonic monitor function (used to stop
precisely at each milestone radius).  Every accepted step records the step
size and the normalized embedded error estimate, which are saved with the
trajectory.

Dense output (optional): Hairer's 4th-order continuous extension of DOPRI5
(coefficients d1, d3..d7 of the DOPRI5 code of Hairer & Wanner; Hairer,
Nørsett & Wanner I, §II.6).  With theta = (x - x_old)/h, theta1 = 1 - theta,
    y(x) = r1 + theta (r2 + theta1 (r3 + theta (r4 + theta1 r5)))
    r1 = y_old, r2 = y_new - y_old, r3 = h k1 - r2, r4 = r2 - h k7 - r3,
    r5 = h (d1 k1 + d3 k3 + d4 k4 + d5 k5 + d6 k6 + d7 k7),
which reproduces y_old, y_new, h k1 and h k7 exactly at the step end points and
satisfies all order-4 conditions for every theta (verified symbolically with
exact rationals by tools/verify_dopri5_dense_output.py and tests).
``integrate(..., t_eval=..., dense_output=True)`` gives SciPy-like access.

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
# Hairer's DOPRI5 dense-output coefficients (4th-order continuous extension; stages 2 has d2 = 0)
_D_RAT = {1: (-12715105075, 11282082432), 3: (87487479700, 32700410799), 4: (-10690763975, 1880347072),
          5: (701980252875, 199316789632), 6: (-1453857185, 822651844), 7: (69997945, 29380423)}
_D = np.zeros(7)
for _i, (_p, _q) in _D_RAT.items():
    _D[_i - 1] = _p / _q


def dense_coefficients(y_old: np.ndarray, y_new: np.ndarray, K: np.ndarray, hd: float) -> np.ndarray:
    """rcont[0..4] of Hairer's DOPRI5 continuous extension for one step (see module docstring)."""
    r = np.empty((5, y_old.size))
    r[0] = y_old
    r[1] = y_new - y_old
    r[2] = hd * K[0] - r[1]
    r[3] = r[1] - hd * K[6] - r[2]
    r[4] = hd * (_D @ K)
    return r


def dense_eval(rcont: np.ndarray, x_old: float, hd: float, x: float) -> np.ndarray:
    th = (x - x_old) / hd
    th1 = 1.0 - th
    return rcont[0] + th * (rcont[1] + th1 * (rcont[2] + th * (rcont[3] + th1 * rcont[4])))


class DenseOutput:
    """Piecewise continuous extension y(x) over all accepted steps (4th order, C^1 at step joins).

    NOTE: components modified by an ``after_step`` projection (e.g. the passive r copy in ln r mode)
    are interpolated from the *raw* Runge–Kutta step, i.e. before projection; callers must
    recompute such components (the trajectory driver sets r = exp(x))."""

    def __init__(self, x_old: np.ndarray, hd: np.ndarray, rcont: np.ndarray):
        self.x_old = np.asarray(x_old, dtype=float)
        self.hd = np.asarray(hd, dtype=float)
        self.rcont = rcont
        self.direction = 1.0 if (len(self.hd) == 0 or self.hd[0] > 0) else -1.0
        # breakpoints in increasing order of direction*x for searchsorted
        self._key = self.direction * self.x_old
        self.x_min = float(min(self.x_old[0], self.x_old[-1] + self.hd[-1])) if len(self.hd) else math.nan
        self.x_max = float(max(self.x_old[0], self.x_old[-1] + self.hd[-1])) if len(self.hd) else math.nan

    def __call__(self, x):
        xa = np.atleast_1d(np.asarray(x, dtype=float))
        idx = np.searchsorted(self._key, self.direction * xa, side="right") - 1
        idx = np.clip(idx, 0, len(self.hd) - 1)
        out = np.array([dense_eval(self.rcont[i], self.x_old[i], self.hd[i], xv) for i, xv in zip(idx, xa)])
        return out[0] if np.ndim(x) == 0 else out


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
    x_eval: Optional[np.ndarray] = None     # t_eval points actually reached (in integration order)
    y_eval: Optional[np.ndarray] = None     # dense-output states at x_eval, shape (n_eval, n_state)
    dense: Optional[DenseOutput] = None     # continuous extension over all accepted steps (dense_output=True)


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
    beta: float = 0.04          # PI controller weight (Hairer DOPRI5: expo1 = 1/5 - 0.75*beta)
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
                  t_eval: Optional[np.ndarray] = None, dense_output: bool = False,
                  ) -> IntegrationResult:
        """Integrate y' = fun(x, y) from x0 to x_end.

        event(x, y): monotonic scalar that changes sign exactly once; the
        integration stops at the step where it crosses zero, with the final
        step shrunk iteratively (secant on the step length) so that the end
        point satisfies event = 0 to integrator accuracy.
        after_step(x, y) -> y: optional projection applied to each accepted state
        (used to resynchronize r = exp(x) in ln r mode).
        t_eval: optional points (any order) at which the solution is returned through Hairer's
        continuous extension (res.x_eval, res.y_eval; only the points actually reached, in
        integration order).  dense_output=True also returns res.dense, callable on the whole range.
        Neither option changes the accepted steps (the step sequence is identical with and without).
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
        want_dense = dense_output or t_eval is not None
        d_x: List[float] = []
        d_h: List[float] = []
        d_r: List[np.ndarray] = []
        if t_eval is not None:
            te = np.asarray(t_eval, dtype=float).ravel()
            te = te[np.argsort(direction * te, kind="stable")]
        else:
            te = np.empty(0)
        te_pos = 0
        xe: List[float] = []
        ye: List[np.ndarray] = []
        if te.size:
            # points at (or behind) the start are served by the initial state
            while te_pos < te.size and direction * (te[te_pos] - x) <= 0.0:
                if te[te_pos] == x:
                    xe.append(float(te[te_pos])); ye.append(y.copy())
                te_pos += 1

        def _serve(x_a: float, hd_a: float, rc: np.ndarray, x_b: float):
            nonlocal te_pos
            if dense_output:
                d_x.append(x_a); d_h.append(hd_a); d_r.append(rc)
            while te_pos < te.size and direction * (te[te_pos] - x_b) <= 0.0:
                xe.append(float(te[te_pos]))
                ye.append(dense_eval(rc, x_a, hd_a, te[te_pos]) if te[te_pos] != x_b else rc[0] + rc[1])
                te_pos += 1

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
        err_old = 1e-4          # PI controller memory (Hairer: facold)
        expo1 = 0.2 - 0.75 * self.beta
        K = np.empty((7, n))
        for _ in range(self.max_steps):
            if direction * (x - x_end) >= 0.0:
                break
            h = min(h, abs(x_end - x))
            if h < self.min_step:
                status = "step_size_underflow"
                break
            hd = direction * h
            # make the step exactly representable: x + hd is rounded, and a mismatch between the step used in
            # the stages and the recorded x_new accumulates as a phase error in the independent variable
            # (visible e.g. in ln r mode where Delta x ~ 1e-8 at x ~ 5 carries 1e-7 relative quantization)
            x_try = x + hd
            if abs(x_try - x) > h:
                x_try = float(np.nextafter(x_try, x))     # never round the step UP (a rejected step must shrink)
            hd_exact = x_try - x
            if hd_exact != 0.0:
                hd = hd_exact
                h = abs(hd)
            else:
                status = "step_size_underflow"      # x + h == x: no progress possible in double precision
                break
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
                y_raw = y_new
                k1_new = K[6].copy()  # FSAL (copy: K[6] is reused by the next attempt / event location)
                if after_step is not None:
                    y_new = after_step(x_new, y_new)
                    k1_new = fun(x_new, y_new)
                    nfev += 1
                # --- event handling: shrink the step to land on event == 0 ---
                if event is not None:
                    ev_new = event(x_new, y_new)
                    if ev_prev is not None and (ev_prev * ev_new < 0.0 or ev_new == 0.0):
                        x_new, y_new, nf, ok, h_ev, y_raw_ev, K_ev = self._locate_event(fun, event, x, y, k1, hd, ev_prev, after_step)
                        nfev += nf
                        k1_new = fun(x_new, y_new)
                        nfev += 1
                        if want_dense:
                            _serve(x, h_ev, dense_coefficients(y, y_raw_ev, K_ev, h_ev), x_new)
                        terminated = True
                        status = "event"
                        h_used = abs(x_new - x)
                        xs.append(x_new); ys.append(y_new.copy()); hs.append(h_used); errs.append(err); rejs.append(n_rej_here)
                        n_acc += 1
                        min_h = min(min_h, h_used); max_h = max(max_h, h_used); max_err = max(max_err, err)
                        x, y, k1 = x_new, y_new, k1_new
                        break
                    ev_prev = ev_new
                if want_dense:
                    _serve(x, hd, dense_coefficients(y, y_raw, K, hd), x_new)
                xs.append(x_new); ys.append(y_new.copy()); hs.append(h); errs.append(err); rejs.append(n_rej_here)
                n_acc += 1
                min_h = min(min_h, h); max_h = max(max_h, h); max_err = max(max_err, err)
                x, y, k1 = x_new, y_new, k1_new
                n_rej_here = 0
                if err == 0.0:
                    fac = self.fac_max
                else:
                    # PI step control (Hairer, Nørsett & Wanner II.4; DOPRI5 code): fac = err^-expo1 * err_old^beta
                    fac = min(self.fac_max, max(self.fac_min, self.safety * err ** (-expo1) * err_old ** self.beta))
                err_old = max(err, 1e-4)
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
            x_eval=np.array(xe) if t_eval is not None else None,
            y_eval=(np.array(ye) if ye else np.empty((0, n))) if t_eval is not None else None,
            dense=DenseOutput(np.array(d_x), np.array(d_h), np.array(d_r)) if (dense_output and d_x) else None,
        )

    def _rk_step(self, fun, x, y, k1, hd):
        """One Dormand–Prince step; returns (y_new, number of RHS evaluations, stage matrix K)."""
        n = y.size
        K = np.empty((7, n))
        K[0] = k1
        for i in range(1, 7):
            yi = y + hd * sum(_A[i][j] * K[j] for j in range(i))
            K[i] = fun(x + _C[i] * hd, yi)
        return y + hd * (_B5 @ K), 6, K

    def _locate_event(self, fun, event, x, y, k1, hd, ev_prev, after_step):
        """Secant/bisection on the step length so that event(x+h, y(h)) = 0.

        Returns (x_end, y_end, n_rhs_evals, ok, h_used, y_end_raw, K): the last three describe the
        final (shrunk) Runge–Kutta step, used for its dense output."""
        nf = 0
        h_lo, e_lo = 0.0, ev_prev
        h_hi = hd
        y_hi, n, K_hi = self._rk_step(fun, x, y, k1, h_hi); nf += n
        y_raw_hi = y_hi
        if after_step is not None:
            y_hi = after_step(x + h_hi, y_hi)
        e_hi = event(x + h_hi, y_hi)
        h_best, y_best, y_raw_best, K_best = h_hi, y_hi, y_raw_hi, K_hi
        for _ in range(60):
            if e_hi == e_lo:
                break
            h_try = h_hi - e_hi * (h_hi - h_lo) / (e_hi - e_lo)
            # keep inside bracket
            lo, hi = sorted((h_lo, h_hi))
            if not (lo < h_try < hi):
                h_try = 0.5 * (h_lo + h_hi)
            y_try, n, K_try = self._rk_step(fun, x, y, k1, h_try); nf += n
            y_raw_try = y_try
            if after_step is not None:
                y_try = after_step(x + h_try, y_try)
            e_try = event(x + h_try, y_try)
            h_best, y_best, y_raw_best, K_best = h_try, y_try, y_raw_try, K_try
            if e_try == 0.0:
                break
            if e_try * e_lo < 0.0:
                h_hi, e_hi, y_hi = h_try, e_try, y_try
            else:
                h_lo, e_lo = h_try, e_try
            if abs(h_hi - h_lo) <= 1e-15 * abs(hd) + 1e-300:
                break
        return x + h_best, y_best, nf, True, h_best, y_raw_best, K_best


def integrate_scipy_dop853(fun, x0, y0, x_end, rtol=1e-13, atol=1e-16, max_step=math.inf, events=None):
    """Independent cross-check with SciPy's DOP853 (Hairer's 8(5,3) Dormand–Prince)."""
    from scipy.integrate import solve_ivp

    sol = solve_ivp(fun, (x0, x_end), y0, method="DOP853", rtol=rtol, atol=atol, max_step=max_step,
                    events=events, dense_output=False)
    return sol
