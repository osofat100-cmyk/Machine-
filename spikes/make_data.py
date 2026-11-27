#!/usr/bin/env python3
"""
Split the prices: training months for the spike robot, and the sealed last month for the price server.

    python3 spikes/make_data.py
      -> spikes/data/train.csv                   25 Jun - 21 Oct (BigONE PEARL-USDT), what the robot may learn from
      -> data/sealed/PEARL_last_month.csv        22 Oct - 20 Nov, only price_server.py opens it
"""
import os

import pandas as pd

CUT = pd.Timestamp("2026-10-22", tz="UTC")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    hist = pd.read_csv(os.path.join(ROOT, "data/PEARL-USDT_min1.csv"), parse_dates=["time"])
    train = hist[hist["time"] < CUT][["time", "high", "low", "close", "volume"]]
    os.makedirs(os.path.join(ROOT, "spikes/data"), exist_ok=True)
    train.to_csv(os.path.join(ROOT, "spikes/data/train.csv"), index=False, date_format="%Y-%m-%dT%H:%M:%SZ")

    sealed = pd.read_csv(os.path.join(ROOT, "data/sealed/PEARL_oct1_nov20.csv"), parse_dates=["time"])
    last = sealed[sealed["time"] >= CUT]
    last.to_csv(os.path.join(ROOT, "data/sealed/PEARL_last_month.csv"), index=False,
                date_format="%Y-%m-%dT%H:%M:%SZ")
    assert train["time"].iloc[-1] < CUT <= last["time"].iloc[0]
    print(f"training {len(train):,} minutes {train['time'].iloc[0]} -> {train['time'].iloc[-1]}")
    print(f"sealed last month {len(last):,} minutes (not shown)")


if __name__ == "__main__":
    main()
