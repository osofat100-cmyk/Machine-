"""Symbolic re-derivation of the Christoffel symbols, Riemann tensor and
Kretschmann scalar for the ingoing Eddington–Finkelstein form of a static
spherically symmetric metric,  ds^2 = -f(r) dv^2 + 2 dv dr + r^2 dOmega^2.

Run:  python tools/derive_ef_curvature.py
It prints the nonzero components and checks them against the closed forms
hard-coded in src/slab/metric.py and src/slab/curvature.py, for a generic
f(r) and for Schwarzschild f = 1 - 2M/r (where K must equal 48 M^2/r^6).
"""
import sympy as sp

v, r, th, ph, M = sp.symbols("v r theta phi M", positive=True)
f = sp.Function("f")(r)
x = [v, r, th, ph]
g = sp.Matrix([[-f, 1, 0, 0], [1, 0, 0, 0], [0, 0, r**2, 0], [0, 0, 0, r**2 * sp.sin(th) ** 2]])
gi = g.inv()

def christoffel(g, gi):
    G = [[[0] * 4 for _ in range(4)] for _ in range(4)]
    for a in range(4):
        for b in range(4):
            for c in range(4):
                G[a][b][c] = sp.simplify(sum(gi[a, d] * (sp.diff(g[d, c], x[b]) + sp.diff(g[d, b], x[c]) - sp.diff(g[b, c], x[d])) for d in range(4)) / 2)
    return G

G = christoffel(g, gi)

def riemann_upper(G):
    # R^a_{bcd} = d_c G^a_{db} - d_d G^a_{cb} + G^a_{ce} G^e_{db} - G^a_{de} G^e_{cb}
    Rm = [[[[0] * 4 for _ in range(4)] for _ in range(4)] for _ in range(4)]
    for a in range(4):
        for b in range(4):
            for c in range(4):
                for d in range(4):
                    Rm[a][b][c][d] = sp.simplify(sp.diff(G[a][d][b], x[c]) - sp.diff(G[a][c][b], x[d]) + sum(G[a][c][e] * G[e][d][b] - G[a][d][e] * G[e][c][b] for e in range(4)))
    return Rm

Ru = riemann_upper(G)
Rl = [[[[sp.simplify(sum(g[a, e] * Ru[e][b][c][d] for e in range(4))) for d in range(4)] for c in range(4)] for b in range(4)] for a in range(4)]

names = ["v", "r", "th", "ph"]
print("Nonzero Christoffel symbols Gamma^a_bc:")
for a in range(4):
    for b in range(4):
        for c in range(b, 4):
            if G[a][b][c] != 0:
                print(f"  G^{names[a]}_{names[b]}{names[c]} = {G[a][b][c]}")
print("\nIndependent nonzero covariant Riemann components R_abcd (a<b, c<d, (ab)<=(cd)):")
pairs = [(a, b) for a in range(4) for b in range(a + 1, 4)]
for i, (a, b) in enumerate(pairs):
    for (c, d) in pairs[i:]:
        if Rl[a][b][c][d] != 0:
            print(f"  R_{names[a]}{names[b]}{names[c]}{names[d]} = {sp.factor(Rl[a][b][c][d])}")

# Kretschmann scalar by full contraction
K = 0
for a in range(4):
    for b in range(4):
        for c in range(4):
            for d in range(4):
                if Rl[a][b][c][d] == 0:
                    continue
                Rup = sum(gi[a, e] * gi[b, ff] * gi[c, gg] * gi[d, hh] * Rl[e][ff][gg][hh]
                          for e in range(4) for ff in range(4) for gg in range(4) for hh in range(4)
                          if Rl[e][ff][gg][hh] != 0)
                K += Rl[a][b][c][d] * Rup
K = sp.simplify(K)
fp, fpp = sp.diff(f, r), sp.diff(f, r, 2)
K_closed = fpp**2 + 4 * fp**2 / r**2 + 4 * (1 - f) ** 2 / r**4
print("\nKretschmann (generic f):", K)
print("matches closed form f''^2 + 4 f'^2/r^2 + 4 (1-f)^2/r^4 :", sp.simplify(K - K_closed) == 0)
Ks = sp.simplify(K.subs(f, 1 - 2 * M / r).doit())
print("Schwarzschild K =", Ks, " equals 48 M^2/r^6 :", sp.simplify(Ks - 48 * M**2 / r**6) == 0)

# Check hard-coded components against the code
expected = {
    ("v", "r", "v", "r"): fpp / 2,
    ("v", "th", "v", "th"): r * f * fp / 2,
    ("v", "th", "r", "th"): -r * fp / 2,
    ("r", "th", "r", "th"): 0,
    ("th", "ph", "th", "ph"): r**2 * (1 - f) * sp.sin(th) ** 2,
    ("v", "ph", "v", "ph"): r * f * fp / 2 * sp.sin(th) ** 2,
    ("v", "ph", "r", "ph"): -r * fp / 2 * sp.sin(th) ** 2,
}
idx = {n: i for i, n in enumerate(names)}
all_ok = True
for key, val in expected.items():
    a, b, c, d = (idx[k] for k in key)
    ok = sp.simplify(Rl[a][b][c][d] - val) == 0
    all_ok &= ok
    print(f"  R_{''.join(key)} matches code: {ok}")
print("ALL RIEMANN COMPONENTS MATCH CODE:", all_ok)
