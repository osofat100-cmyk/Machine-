# Machine-

## PEARL monitor

Live monitor for PEARL on BigONE (reads market data only, places no orders).

    python3 pearl_monitor.py              # PEARL-USDC, every 1s
    python3 pearl_monitor.py --pair PEARL-USDT
    python3 pearl_monitor.py --list       # PEARL pairs BigONE lists

Each tick is logged to `logs/<pair>.csv` for later backtesting. Signals:
UP/DOWN when the fast average moves away from the slow average by more than
the spread.
