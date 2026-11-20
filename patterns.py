#!/usr/bin/env python3
"""
Research: when does a PEARL rise or drop keep going, and how do fast spikes behave?

    python3 patterns.py data/coinbase_trades.csv        # trade-by-trade (seconds)
    python3 patterns.py data/gate_trades.csv
    python3 patterns.py data/PEARL-USDT_min1.csv        # BigONE 1-minute candles

PART 1 - MOVES. The price is split into up-moves and down-moves. A move ends
when the price turns back by REVERSAL % from its high (or low); smaller dips
are treated as noise inside the move. For each size X it shows: once a move
has gone X%, how often it went at least 1.6% further.

PART 2 - SPIKES. A spike is a rise (or drop) of SPIKE % within WINDOW seconds.
For each spike it measures what happened next.
"""
import argparse
import csv
import statistics as st
from datetime import datetime, timezone

EXTRA = 1.6  # % further the move must go to be worth trading (cost is 1.4%)


def load(path):
    """List of (unix_seconds, price), oldest first."""
    out = []
    with open(path) as f:
        r = csv.DictReader(f)
        price_col = "price" if "price" in r.fieldnames else "close"
        for row in r:
            t = datetime.fromisoformat(row["time"].replace("Z", "+00:00")).timestamp()
            out.append((t, float(row[price_col])))
    out.sort()
    return out


def moves(series, reversal):
    """Split prices into alternating up/down moves. Returns (direction, size %, seconds)."""
    out = []
    d = 0
    lo = hi = series[0][1]
    lo_t = hi_t = series[0][0]
    for t, p in series:
        if p > hi:
            hi, hi_t = p, t
        if p < lo:
            lo, lo_t = p, t
        if d >= 0 and p <= hi * (1 - reversal / 100):      # up-move ended at hi
            if d == 1:
                out.append((1, (hi / lo - 1) * 100, hi_t - lo_t))
            d, lo, lo_t = -1, p, t
        elif d <= 0 and p >= lo * (1 + reversal / 100):    # down-move ended at lo
            if d == -1:
                out.append((-1, (1 - lo / hi) * 100, lo_t - hi_t))
            d, hi, hi_t = 1, p, t
    return out


def keep_going_table(sizes, steps):
    rows = []
    for x in steps:
        reached = [s for s in sizes if s >= x]
        if len(reached) < 5:
            break
        further = sum(s >= x + EXTRA for s in reached)
        rows.append((x, len(reached), further / len(reached) * 100,
                     st.median(s - x for s in reached)))
    return rows


def spikes(series, size, window, horizon=3600, stop=3.0):
    """Find spikes and what happened after each. Returns list of dicts."""
    out, j, cooldown_until = [], 0, 0
    n = len(series)
    for i in range(n):
        t, p = series[i]
        while series[j][0] < t - window:
            j += 1
        if t < cooldown_until:
            continue
        lo = min(q for _, q in series[j:i + 1])
        hi = max(q for _, q in series[j:i + 1])
        direction = 0
        if p >= lo * (1 + size / 100):
            direction = 1
        elif p <= hi * (1 - size / 100):
            direction = -1
        if not direction:
            continue
        # what happens next
        k, best, worst, first = i + 1, p, p, None
        later = {}
        while k < n and series[k][0] <= t + horizon:
            q = series[k][1]
            best, worst = max(best, q), min(worst, q)
            if first is None:
                if q >= p * (1 + EXTRA / 100):
                    first = "up"
                elif q <= p * (1 - EXTRA / 100):
                    first = "down"
            for m in (60, 300, 900, 3600):
                if m not in later and series[k][0] >= t + m:
                    later[m] = (q / p - 1) * 100
            k += 1
        out.append({"dir": direction, "t": t, "first": first,
                    "max_up": (best / p - 1) * 100, "max_down": (1 - worst / p) * 100, "later": later})
        cooldown_until = t + 1800  # one spike per 30 minutes
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--reversal", type=float, nargs="+", default=[1.5, 3, 5])
    ap.add_argument("--spike", type=float, nargs="+", default=[2, 3, 5])
    ap.add_argument("--window", type=int, nargs="+", default=[60, 300])
    a = ap.parse_args()

    s = load(a.file)
    days = (s[-1][0] - s[0][0]) / 86400
    print(f"{a.file}: {len(s)} prices over {days:.1f} days, "
          f"{datetime.fromtimestamp(s[0][0], timezone.utc):%b %d} -> {datetime.fromtimestamp(s[-1][0], timezone.utc):%b %d}")

    print("\nPART 1 - MOVES")
    for r in a.reversal:
        m = moves(s, r)
        for d, name in ((1, "UP"), (-1, "DOWN")):
            sizes = [x[1] for x in m if x[0] == d]
            mins = [x[2] / 60 for x in m if x[0] == d]
            if not sizes:
                continue
            print(f"\n {name}-moves (a move ends when price turns back {r}%): {len(sizes)} moves, "
                  f"{len(sizes) / days:.1f} per day")
            print(f"   normal size {st.median(sizes):.1f}%  avg {st.mean(sizes):.1f}%  "
                  f"1 in 10 bigger than {sorted(sizes)[int(len(sizes) * .9)]:.1f}%  biggest {max(sizes):.1f}%  "
                  f"normal length {st.median(mins):.0f} min")
            print(f"   once it has gone X%   moves   went {EXTRA}%+ further   normal extra")
            for x, cnt, pct, extra in keep_going_table(sizes, [r] + [x for x in (2, 3, 4, 5, 6, 8, 10, 15, 20) if x > r]):
                print(f"   {x:>9}%       {cnt:>7}   {pct:>12.0f}%        {extra:>6.1f}%")

    print("\nPART 2 - SPIKES (what happened after; one spike counted per 30 min)")
    for w in a.window:
        for sz in a.spike:
            ev = spikes(s, sz, w)
            for d, name in ((1, "UP"), (-1, "DOWN")):
                e = [x for x in ev if x["dir"] == d]
                if len(e) < 3:
                    continue
                cont = sum(x["first"] == ("up" if d == 1 else "down") for x in e) / len(e) * 100
                rev = sum(x["first"] == ("down" if d == 1 else "up") for x in e) / len(e) * 100
                print(f"\n {name} spike {sz}% within {w // 60} min: {len(e)} times")
                print(f"   kept going {EXTRA}% more first: {cont:.0f}%   turned back {EXTRA}% first: {rev:.0f}%")
                print("   avg change after:  " + "  ".join(
                    f"{m // 60}min {st.mean(x['later'][m] for x in e if m in x['later']):+.1f}%"
                    for m in (60, 300, 900, 3600) if any(m in x["later"] for x in e)))
                print(f"   in the next hour: normal best {st.median(x['max_up'] for x in e):+.1f}%, "
                      f"normal worst {-st.median(x['max_down'] for x in e):+.1f}%")


if __name__ == "__main__":
    main()
