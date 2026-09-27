#!/usr/bin/env python3
"""Write data/scenarios/README.md summarizing every scenario run (from their trajectory_metadata.json)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rows = []
    for meta in sorted((ROOT / "data" / "scenarios").glob("*/data/trajectory_metadata.json")):
        d = json.loads(meta.read_text())
        cfg = d["metadata"]["config"]
        ms = {m["slug"]: m for m in d["summary"]["milestones"]}
        h, q = ms.get("horizon", {}), ms.get("r_QG", {})
        rows.append({
            "tag": meta.parents[1].name,
            "E": cfg["E"], "L": cfg["L_over_M"], "thrust": cfg["thrust_alpha_SI"], "r0": cfg["r0_over_rs"],
            "tau_r0_to_horizon_yr": h.get("tau_total_years"),
            "E_at_horizon": h.get("E_killing"),
            "tau_horizon_to_rQG_yr": (q.get("tau_total_years", 0) - h.get("tau_total_years", 0)) if h and q else None,
            "steps": d["summary"]["n_steps_total"],
            "norm_resid_cond": d["summary"].get("max_abs_norm_residual_conditioned"),
        })
    out = ["# Scenario runs (all classical GR, same validated engine)\n",
           "| tag | E | L [GM/c] | thrust [m/s²] | r0/r_s | τ(r0→r_s) [yr] | E at horizon | τ(r_s→r_QG) [yr] | steps | max conditioned norm residual |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['tag']} | {r['E']} | {r['L']} | {r['thrust']} | {r['r0']} | {r['tau_r0_to_horizon_yr']:.6e} | {r['E_at_horizon']:.6e} | "
                   f"{r['tau_horizon_to_rQG_yr']:.6e} | {r['steps']} | {r['norm_resid_cond']:.1e} |")
    out.append("\nReference (E = 1, L = 0, no thrust): τ(r_s→r_QG) = 4GM/(3c³) = 208,112 yr.  "
               "Inward thrust (the only kind implemented) makes the interior proper time SHORTER; from the horizon no observer can have more than piGM/c^3, reached on the E = 0 free-fall path, and suitably directed thrust can lengthen the time of an observer who entered from outside only up to that maximum (Lewis & Kwan 2007), "
               "angular momentum also shortens it.  Run new scenarios with `python run_simulation.py --skip-validation --thrust <m/s^2> | --L <GM/c> | --E <E> --r0 <r/r_s> [--tag name]`.\n")
    (ROOT / "data" / "scenarios" / "README.md").write_text("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
