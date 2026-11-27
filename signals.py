#!/usr/bin/env python3
"""
Search for "90% sure" buy and sell moments in PEARL's history, then trade them.

    python3 signals.py                          # BigONE PEARL-USDT 1-minute candles
    python3 signals.py --move 5                 # "goes up 5% before down 5%"

A BUY moment is "sure" when, after it, the price rose MOVE% before it fell MOVE%.
A SELL moment is "sure" when the price fell MOVE% before it rose MOVE%.
Each rule is two conditions, e.g. "up 4%+ in the last hour AND volume 2x normal".
Rules are found on the first 60% of the data (TRAIN) and checked on the rest (TEST).
"""
import argparse
import numpy as np
import pandas as pd

COST = 0.7  # % per side (1.4% round trip)


def features(df):
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    f = pd.DataFrame(index=df.index)
    for name, n in (("1h", 60), ("4h", 240), ("24h", 1440)):
        f[f"up from {name} low %"] = (c / l.rolling(n).min() - 1) * 100
        f[f"down from {name} high %"] = (1 - c / h.rolling(n).max()) * 100
    for name, n in (("5m", 5), ("15m", 15), ("1h", 60), ("4h", 240), ("24h", 1440)):
        f[f"change last {name} %"] = (c / c.shift(n) - 1) * 100
    f["24h avg vs 7d avg %"] = (c.rolling(1440).mean() / c.rolling(10080).mean() - 1) * 100
    for name, n in (("15m", 15), ("1h", 60)):
        f[f"volume last {name} vs normal (x)"] = v.rolling(n).sum() / (v.rolling(1440).sum() / 1440 * n)
    return f


def outcomes(df, move, horizon=2880):
    """+1 = rose move% first, -1 = fell move% first, 0 = neither within horizon minutes."""
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    n = len(c)
    out = np.zeros(n, dtype=np.int8)
    for i in range(n):
        up, dn = c[i] * (1 + move / 100), c[i] * (1 - move / 100)
        for k in range(i + 1, min(n, i + horizon)):
            if l[k] <= dn:          # if both happen in one minute, count it as a fall
                out[i] = -1
                break
            if h[k] >= up:
                out[i] = 1
                break
    return out


def search(F, y, train, want, min_count):
    """Try every 1- and 2-condition rule; return them sorted by train hit rate."""
    cols, conds = list(F.columns), []
    for col in cols:
        x = F[col].values
        for q in (5, 10, 20, 30, 70, 80, 90, 95):
            t = np.nanpercentile(x[train], q)
            if q < 50:
                conds.append((f"{col} <= {t:.2f}", np.nan_to_num(x, nan=np.inf) <= t))
            else:
                conds.append((f"{col} >= {t:.2f}", np.nan_to_num(x, nan=-np.inf) >= t))
    M = np.array([m for _, m in conds], dtype=np.float32)
    sample = np.zeros(len(y), bool)
    sample[::30] = True                          # one row per 30 min: less double counting
    rows = {}
    for part, mask in (("train", train & sample), ("test", ~train & sample)):
        Mp, yp = M[:, mask], (y[mask] == want).astype(np.float32)
        rows[part] = (Mp @ Mp.T, (Mp * yp) @ Mp.T, yp.mean())
    (cnt, hit, base), (tcnt, thit, tbase) = rows["train"], rows["test"]
    found = []
    for i in range(len(conds)):
        for j in range(i, len(conds)):
            if cnt[i, j] >= min_count and tcnt[i, j] >= 10:
                name = conds[i][0] if i == j else f"{conds[i][0]}  AND  {conds[j][0]}"
                found.append((hit[i, j] / cnt[i, j] * 100, thit[i, j] / tcnt[i, j] * 100,
                              int(cnt[i, j]), int(tcnt[i, j]), name, conds[i][1] & conds[j][1]))
    found.sort(key=lambda r: (-r[0], -r[2]))
    return found, base * 100, tbase * 100


def trade(df, buy, sell, move, exit_mode):
    """exit_mode 'signal': sell on the sell rule.  'target': sell at +move% or -move%."""
    c, h, l = df["close"].values, df["high"].values, df["low"].values
    t = df.index
    cash, coins, holding, entry, entry_i = 1000.0, 0.0, False, 0.0, 0
    log = []
    for i in range(len(c) - 1):
        if not holding and buy[i]:
            px = c[i + 1] * (1 + COST / 100)
            coins, cash, holding, entry, entry_i = cash / px, 0.0, True, c[i + 1], i + 1
        elif holding:
            done = sell[i] if exit_mode == "signal" else (
                l[i] <= entry * (1 - move / 100) or h[i] >= entry * (1 + move / 100))
            if done:
                px = c[i + 1] if exit_mode == "signal" else (
                    entry * (1 - move / 100) if l[i] <= entry * (1 - move / 100) else entry * (1 + move / 100))
                cash, coins, holding = coins * px * (1 - COST / 100), 0.0, False
                log.append((t[entry_i], t[i], (px / entry - 1) * 100))
    final = cash + coins * c[-1] * (1 - COST / 100)
    return final, log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="data/PEARL-USDT_min1.csv")
    ap.add_argument("--move", type=float, default=3.0)
    ap.add_argument("--min-count", type=int, default=40)
    a = ap.parse_args()

    df = pd.read_csv(a.file, parse_dates=["time"]).set_index("time")
    F = features(df)
    y = outcomes(df, a.move)
    ok = F.notna().all(axis=1).values
    df, F, y = df[ok], F[ok], y[ok]
    split = int(len(df) * 0.6)
    train = np.arange(len(df)) < split
    print(f"{a.file}: {len(df)} minutes. TRAIN {df.index[0]:%b %d} - {df.index[split]:%b %d}, "
          f"TEST {df.index[split]:%b %d} - {df.index[-1]:%b %d}")

    best = {}
    for want, name in ((1, "BUY"), (-1, "SELL")):
        found, base, tbase = search(F, y, train, want, a.min_count)
        word = "rose" if want == 1 else "fell"
        print(f"\n{name} rules: after the moment, price {word} {a.move}% first. "
              f"Any random moment: TRAIN {base:.0f}%, TEST {tbase:.0f}%")
        print(f"   {'TRAIN':>6} {'TEST':>6} {'times':>11}   rule")
        for tr, te, n, tn, rule, _ in found[:8]:
            print(f"   {tr:>5.0f}% {te:>5.0f}%  {n:>4}/{tn:<4}   {rule}")
        top = [r for r in found if r[0] >= 90] or found[:1]
        best[name] = top[0]
        print(f"   rules at 90%+ on TRAIN: {len([r for r in found if r[0] >= 90])}; "
              f"their average on TEST: {np.mean([r[1] for r in top]):.0f}%")

    hold = 1000 * df["close"].iloc[-1] / df["close"].iloc[0] * (1 - COST / 100) ** 2
    print(f"\nTRADING the top BUY rule and top SELL rule (1.4% cost). Just holding: ${hold:.0f}")
    print(f"   BUY:  {best['BUY'][4]}\n   SELL: {best['SELL'][4]}")
    for mode, text in (("signal", "sell on the SELL rule"), ("target", f"sell at +{a.move}% or -{a.move}%")):
        for part, rng in (("TRAIN", slice(0, split)), ("TEST", slice(split, None)), ("ALL", slice(None))):
            final, log = trade(df[rng], best["BUY"][5][rng], best["SELL"][5][rng], a.move, mode)
            if not log:
                print(f"   {text:<24} {part:<5}: no trades")
                continue
            held = [(s - b).total_seconds() / 3600 for b, s, _ in log]
            gaps = [(log[k][0] - log[k - 1][1]).total_seconds() / 3600 for k in range(1, len(log))]
            print(f"   {text:<24} {part:<5}: $1000 -> ${final:>6.0f}  trades {len(log):>3}  "
                  f"wins {sum(r > 1.4 for _, _, r in log) / len(log) * 100:>3.0f}%  "
                  f"held normal {np.median(held):>5.1f}h  "
                  f"wait between trades normal {np.median(gaps) if gaps else 0:>5.1f}h")


if __name__ == "__main__":
    main()
