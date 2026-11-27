#!/usr/bin/env python3
"""Acervator-LLC/ACERVATOR: its own Back Test engine, src/simulator/back_test.walk, unchanged (way B in RULES.md:
the program has no way to be driven minute by minute without its Qt app; its back test is the shipped way to run it).

Minutes come from sealed.export_minutes (the server walked one minute at a time, no orders), rolled into 5-minute
[ts, o, h, l, c, v] rows (its native and default bot timeframe; open = previous minute's close). One bot made the
way its own new_bot() makes an operator-defined bot: PEARL/USDT, target_usd 200 (the debate's 20% of $1,000; it has
no default target for PEARL - its asset_target_defaults fallback is $25), every other setting its default, its fee
set to the contest's 0.7% (its default is 0.6%). Venue 'coinbase': its rule table has no row for PEARL on BigONE
(cited_rule_for -> None, "walks nothing"), and on Coinbase cites 'fractional'. The other $800 stays in cash.
End value = 800 + its cash + its coins x last price x (1 - 0.7%), minus 0.7% of the opening $200 buy (its back test
books the opening position without a fee).

    venv_acervator/bin/python run_acervator.py --port 8844
"""
import argparse
import os
import sys

import common

SRC = os.path.join(common.HERE, "downloads", "Acervator-LLC_ACERVATOR")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8844)
    a = ap.parse_args()
    data = os.path.join(common.HERE, "data")
    os.makedirs(data, exist_ok=True)
    df = common.sealed.export_minutes(a.port, os.path.join(data, "acervator_minutes.csv"))
    g = df["ts"] // 5
    rows = []
    for _, part in df.groupby(g, sort=True):
        rows.append([int(part["ts"].iloc[0] // 5 * 5) * 60000, float(part["open"].iloc[0]), float(part["high"].max()),
                     float(part["low"].min()), float(part["close"].iloc[-1]), float(part["volume"].sum())])
    sys.path.insert(0, SRC)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from src.simulator import back_test as bt
    import dataclasses
    bot = dataclasses.replace(bt.new_bot("PEARL/USDT", "coinbase", 200.0), trading_fee_pct=0.7)
    cls, venue, rule = bt.cited_rule_for("PEARL", "coinbase")
    res = bt.walk(bot, bt.candles_from_raw(rows), rule=rule)   # as its run() does
    kap = 0.007
    coins_value = res.end_units * res.end_price * (1 - kap)
    value = 800.0 + res.cash_usd + coins_value - 200.0 * kap
    buys = sum(1 for t in res.trades if t.side != getattr(bt, "SCRUM", "scrum"))
    print(f"ACERVATOR walk: outcome {res.outcome}, {len(rows)} bars, {res.ticks} ticks, {len(res.trades)} trades "
          f"(scrum latched {res.scrum_latched}, fold latched {res.fold_latched}); start {res.start_units:.4f} @ "
          f"{res.start_price}, end {res.end_units:.4f} @ {res.end_price}, cash {res.cash_usd:.2f}, fees "
          f"{res.fees_usd:.2f}, end target {res.end_target_usd:.2f}, refusals {res.order_refusals}")
    print(f"ACERVATOR: $1,000 -> ${value:,.2f}")
    for t in res.trades[:8]:
        print("  ", t)
    common.sealed.record("Acervator-LLC/ACERVATOR (Accumulation scrum/fold bot)",
                         f"target $200 PEARL (+$800 cash), 5m, its defaults, fee 0.7%, venue coinbase rule '{rule}'",
                         "B", len(res.trades) + 1, value, "ran",
                         f"its own back_test.walk; outcome {res.outcome}; {res.ticks} ticks; scrum latched "
                         f"{res.scrum_latched}, fold latched {res.fold_latched}; trades count includes the opening "
                         "buy; needs Python 3.14 per pyproject (ran on 3.13, imports fine, GUI not used); no PEARL "
                         "row for BigONE in its rule table")


if __name__ == "__main__":
    main()
