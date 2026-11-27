#!/usr/bin/env python3
"""
3D graphs of the every-1% search (training months only): buy chance x sell chance -> money,
at the winner's spike size, x and stop.

    python3 spikes/graph.py   -> spikes/graph_1pct.png
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    d = np.load(os.path.join(HERE, "choose_1pct.npz"))
    with open(os.path.join(HERE, "winner_1pct.json")) as f:
        w = json.load(f)
    ti = list(d["thetas"]).index(w["theta"])
    xi = int(np.argmin(np.abs(d["xs"] - w["x"])))
    ki = int(np.argmin(np.abs(d["stops"] - w["stop"])))
    ps = d["ps"] * 100
    B, S = np.meshgrid(ps, ps, indexing="ij")
    panels = [("choose", "Choose months 25 Jun - 21 Sep ($)", 1463),
              ("check", "Check month 22 Sep - 21 Oct ($)", 2422),
              ("score", "Score (safest, used to pick the winner)", None)]
    fig = plt.figure(figsize=(21, 8.5))
    for n, (key, title, hold) in enumerate(panels, 1):
        z = d[key][ti, :, :, xi, ki]
        ax = fig.add_subplot(1, 3, n, projection="3d")
        ax.plot_surface(B, S, z, cmap="viridis", linewidth=0, antialiased=True, alpha=0.95)
        if hold:
            ax.plot_surface(B, S, np.full_like(z, hold), color="red", alpha=0.25)
        bi = int(round(w["p_buy"] * 100)) - 1
        si = int(round(w["p_sell"] * 100)) - 1
        ax.scatter([ps[bi]], [ps[si]], [z[bi, si]], color="red", s=60, depthshade=False)
        ax.set_xlabel("buy when chance drop continues < (%)")
        ax.set_ylabel("sell when chance rise continues < (%)")
        ax.set_title(title + ("\nred sheet = just holding" if hold else "\nred dot = winner"), fontsize=11)
        ax.view_init(elev=28, azim=-130)
        print(f"{key}: winner {z[bi, si]:,.2f}, max {np.nanmax(z):,.2f}, min {np.nanmin(z):,.2f}")
    fig.suptitle(f"Spike robot, every 1% from 1 to 100 (10,000 buy/sell pairs per panel) at spike size "
                 f"{w['theta']:.0%}, x {w['x']:.0%}, stop {w['stop']:.0%}  |  winner: buy {w['p_buy']:.0%}, "
                 f"sell {w['p_sell']:.0%}", fontsize=13, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(HERE, "graph_1pct.png"), dpi=110)
    print("saved spikes/graph_1pct.png")


if __name__ == "__main__":
    main()
