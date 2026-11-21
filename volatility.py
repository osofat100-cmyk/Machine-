#!/usr/bin/env python3
"""
How much does PEARL move in 1, 5, 10 and 60 minutes, and inside each minute?

    python3 fetch_history.py              # get 1-minute candles first
    python3 volatility.py                 # PEARL-USDT
    python3 volatility.py --pair PEARL-USDC

For each window size it prints:
  normal   = the middle (median) move: half of windows move less, half more
  avg      = the average move (pulled up by the spikes)
  1 in 10  = 90% of windows move less than this
  1 in 100 = 99% of windows move less than this
  biggest spike up / biggest drop
  swing    = high minus low inside the window (how far it travels, not just start to end)
  > cost   = how often the move is bigger than the 1.4% round-trip trading cost
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime

ROUND_TRIP_COST = 1.4  # % : 0.2% fee each way + buy/sell gap, measured on PEARL-USDC


def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            rows.append((datetime.fromisoformat(r["time"].replace("Z", "+00:00")),
                         float(r["open"]), float(r["high"]), float(r["low"]),
                         float(r["close"]), float(r["volume"])))
    return rows


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(p / 100 * len(sorted_vals)))]


def windows(rows, n):
    """Non-overlapping windows of n minutes: (change %, swing %)."""
    out = []
    for i in range(0, len(rows) - n + 1, n):
        w = rows[i:i + n]
        start = w[0][1]
        change = (w[-1][4] / start - 1) * 100
        swing = (max(x[2] for x in w) - min(x[3] for x in w)) / start * 100
        out.append((change, swing))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair", default="PEARL-USDT")
    ap.add_argument("--file", default=None)
    args = ap.parse_args()
    rows = load(args.file or f"data/{args.pair}_min1.csv")
    days = (rows[-1][0] - rows[0][0]).total_seconds() / 86400
    print(f"{args.pair}: {len(rows)} one-minute candles over {days:.1f} days "
          f"({rows[0][0]:%b %d} -> {rows[-1][0]:%b %d}), price {min(r[3] for r in rows):.3f}-{max(r[2] for r in rows):.3f}\n")

    print("START-TO-END MOVE (size, up or down)")
    print(f"{'window':<8}{'normal':>8}{'avg':>8}{'1 in 10':>9}{'1 in 100':>10}{'spike up':>10}{'drop':>9}{'> cost':>9}")
    for n in (1, 5, 10, 60):
        w = windows(rows, n)
        sizes = sorted(abs(c) for c, _ in w)
        print(f"{str(n) + ' min':<8}{pct(sizes, 50):>7.2f}%{sum(sizes) / len(sizes):>7.2f}%"
              f"{pct(sizes, 90):>8.2f}%{pct(sizes, 99):>9.2f}%"
              f"{max(c for c, _ in w):>+9.1f}%{min(c for c, _ in w):>+8.1f}%"
              f"{sum(s > ROUND_TRIP_COST for s in sizes) / len(sizes) * 100:>8.0f}%")

    print("\nSWING INSIDE THE WINDOW (highest minus lowest price)")
    print(f"{'window':<8}{'normal':>8}{'avg':>8}{'1 in 10':>9}{'1 in 100':>10}{'biggest':>10}{'> cost':>9}")
    for n in (1, 5, 10, 60):
        sw = sorted(s for _, s in windows(rows, n))
        print(f"{str(n) + ' min':<8}{pct(sw, 50):>7.2f}%{sum(sw) / len(sw):>7.2f}%"
              f"{pct(sw, 90):>8.2f}%{pct(sw, 99):>9.2f}%{sw[-1]:>9.1f}%"
              f"{sum(s > ROUND_TRIP_COST for s in sw) / len(sw) * 100:>8.0f}%")

    # ---- every minute inside an hour ----
    hours = defaultdict(list)
    for r in rows:
        hours[r[0].replace(minute=0)].append(r)
    full = [h for h in hours.values() if len(h) == 60]
    up = flat = down = flips = 0
    streaks = []
    for h in full:
        last_dir, streak = 0, 0
        for i in range(1, 60):
            d = (h[i][4] > h[i - 1][4]) - (h[i][4] < h[i - 1][4])
            up += d > 0
            down += d < 0
            flat += d == 0
            if d:
                if last_dir and d != last_dir:
                    flips += 1
                    streaks.append(streak)
                    streak = 0
                streak += 1
                last_dir = d
        streaks.append(streak)
    total = up + down + flat
    n = len(full)
    print(f"\nEVERY MINUTE INSIDE AN HOUR (average over {n} full hours)")
    print(f"  minutes that closed higher than the minute before: {up / n:.0f} of 59")
    print(f"  minutes that closed lower:                         {down / n:.0f} of 59")
    print(f"  minutes with no change:                            {flat / n:.0f} of 59")
    print(f"  times the direction flipped (up->down or down->up): {flips / n:.0f} per hour")
    print(f"  longest run of same-direction minutes seen: {max(streaks)}; "
          f"normal run: {sorted(streaks)[len(streaks) // 2]} minute(s)")
    print(f"  after an UP minute, the next minute was DOWN {sum(1 for h in full for i in range(2, 60) if h[i-1][4] > h[i-2][4] and h[i][4] < h[i-1][4]) / max(1, up) * 100:.0f}% of the time")

    # ---- the wildest moments ----
    print("\nBIGGEST SINGLE-MINUTE SPIKES AND HOLES (time is UTC)")
    one = sorted(((r[4] / r[1] - 1) * 100, r[0], (r[2] - r[3]) / r[1] * 100) for r in rows)
    for c, t, s in one[-5:][::-1] + one[:5]:
        print(f"  {t:%b %d %H:%M}  {c:+6.2f}%  (swung {s:.1f}% inside that minute)")


if __name__ == "__main__":
    main()
