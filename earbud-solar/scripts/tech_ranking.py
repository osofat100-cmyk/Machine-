"""Rank solar technologies by the power they could deliver on the real earbud and case surfaces.

Every parameter below is a sourced figure (see README section 6); None = not published, so that
limit is not applied and the result is an UPPER bound for that technology.
Power = exact mean (or best-angle) shadow x share of the sunlit skin the tech can cover
        x 100 mW/cm^2 (standard test sun) x efficiency.
Silicon tile strain limit 0.024 % comes from Yamada (JSAP Rev. 2022): a <=3-inch (76 mm) 180 um mono-Si
cell followed a 1 m sphere uncracked -> eps = L^2 K / 24 = 76^2 / 1e6 / 24 = 0.024 % (a 6-inch cell cracked).
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from coverage_power import load, coverable, lit_area
from exterior import fib_dirs

EXACT = {"earbud": dict(mean=9.20, best=11.83, draw=26.95), "case": dict(mean=38.11, best=48.86)}
TECH = [  # name, efficiency, r_min mm, tile/patch mm, strain, note
    ("Flexible perovskite/Si tandem tiles (LONGi, NREL-cert.)", 0.3335, 15.0, 10.0, 0.00024, "1 cm2 cell, bends to 15 mm; Si strain limit from Yamada"),
    ("Corrugated IBC silicon (KAUST sphere)", 0.1893, 18.5, None, None, "formed onto an 18.5 mm-radius sphere; not certified"),
    ("Stretchable GaAs micro-cells (Rogers, dual-junction)", 0.19 * 0.67, 1.5, 10.0, 0.60, "19 % cells x 67 % fill; 60 % biaxial stretch; wraps 1.5 mm"),
    ("Spray-coated perovskite, sprayed on the part", 0.232, None, None, None, "23.2 % on a doubly-curved part (its curvature not stated)"),
    ("  same, only curvature actually demonstrated (R 64.4 mm lens)", 0.125, 64.4, None, None, "12.5 % on a 64.4 mm-radius lens"),
    ("Stretchable perovskite skin (PolyU)", 0.2144, None, 10.0, 0.40, "40 % stretch; bend radius not published"),
    ("Stretchable organic PV", 0.10, None, 10.0, 1.00, ">10 % at 100 % strain; bend radius not published"),
    ("Flexible CIGS (Empa, Fraunhofer-confirmed)", 0.222, 3.0, None, None, "3 mm bend is Ascent's (unverified); stretch limit not published"),
    ("Flexible a-Si (PowerFilm)", 0.06, 25.4, None, None, "<1 inch bend; stretch limit not published"),
    ("Exeger Powerfoyle (dye cell)", None, 60.0, None, None, "efficiency not published; min 15 cm2 per cell"),
    ("Rigid mono-Si tiles (ANYSOLAR)", 0.25, 200.0, None, None, "rigid: only flat spots (200 mm = flat at this curvature resolution)"),
]

dirs = fib_dirs(150)   # 150 directions; coverable share is a ratio against the full skin over the same directions
out = {}
for part, res in (("earbud", 0.2), ("case", 0.3)):
    V, va, k1, k2, lab = load(os.path.join(sys.argv[1], f"curvature_{part}.npz"))
    full = lit_area(V, np.ones(len(V), bool), dirs, res)
    rows = []
    for name, eta, r, L, eps, note in TECH:
        m = coverable(k1, k2, r, L, eps if eps is not None else 0)
        lit = lit_area(V, m, dirs, res)
        share = float(va[m].sum() / va.sum())
        fmean, fbest = float(lit.mean() / full.mean()), float(lit.max() / full.max())
        pm = EXACT[part]["mean"] * fmean * 100 * eta if eta else None
        pb = EXACT[part]["best"] * fbest * 100 * eta if eta else None
        rows.append(dict(tech=name, eff=eta, skin_share=share, lit_share_mean=fmean, power_mean_mW=pm, power_best_mW=pb, note=note))
    out[part] = rows
    print(f"\n== {part}")
    for r_ in rows:
        p = "n/a (eff. not published)" if r_["eff"] is None else f"{r_['power_mean_mW']:7.1f} mW avg / {r_['power_best_mW']:7.1f} best"
        extra = ""
        if part == "earbud" and r_["eff"]:
            extra = f" | {r_['power_mean_mW']/EXACT['earbud']['draw']:5.2f}x draw"
        print(f"{r_['tech'][:58]:58s} covers {100*r_['skin_share']:5.1f}% skin, {100*r_['lit_share_mean']:5.1f}% of sunlit area -> {p}{extra}")
json.dump(out, open(os.path.join(sys.argv[1], "tech_ranking.json"), "w"), indent=1)
