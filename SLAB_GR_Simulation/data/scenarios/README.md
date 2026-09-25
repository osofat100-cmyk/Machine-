# Scenario runs (all classical GR, same validated engine)

| tag | E | L [GM/c] | thrust [m/s²] | r0/r_s | τ(r0→r_s) [yr] | E at horizon | τ(r_s→r_QG) [yr] | steps | max conditioned norm residual |
|---|---|---|---|---|---|---|---|---|---|
| plunge_L3.5 | 1.0 | 3.5 | 0.0 | 100.0 | 2.171987e+08 | 1.000000e+00 | 1.068599e+05 | 11967 | 5.4e-13 |
| rest_at_10rs | 0.9486832980505138 | 0.0 | 0.0 | 10.0 | 1.529160e+07 | 9.486833e-01 | 2.147133e+05 | 3544 | 1.5e-11 |
| thrust_1g | 1.0 | 0.0 | 9.81 | 100.0 | 1.731121e+01 | 3.191363e+07 | 9.732587e-03 | 4090 | 6.5e-12 |

Reference (E = 1, L = 0, no thrust): τ(r_s→r_QG) = 4GM/(3c³) = 208,112 yr.  Inward thrust makes the interior proper time SHORTER (the geodesic maximizes it; Lewis & Kwan 2007), angular momentum also shortens it.  Run new scenarios with `python run_simulation.py --skip-validation --thrust <m/s^2> | --L <GM/c> | --E <E> --r0 <r/r_s> [--tag name]`.
