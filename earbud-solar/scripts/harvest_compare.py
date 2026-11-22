"""Every energy-harvesting type applied to the JBL Endurance Peak 3 earbud.

Geometry comes from JBL's 3D model (ep3_analyze.py); power densities from the sources in README.md.
Runtime = battery / (draw - harvest).  No charging losses are included (none published).
"""
D = 26.95    # mW per bud   = 70 mAh x 3.85 V / 10 h   (JBL spec sheet)
B = 269.5    # mWh per bud
skin, contact, shadow, shadow_best, vol = 46.58, 10.637, 9.20, 11.83, 9.418   # cm2, cm2, cm2, cm2, cm3

rows = [
    ("Sunlight, full sun (100 mW/cm2) x 33.6% flexible tandem", "shadow, mean / best angle", shadow * 33.6, shadow_best * 33.6),
    ("Indoor light 1000 lux: 19-29 uW/cm2 measured cells -> 168 uW/cm2 best 42% cell", "shadow 9.2 cm2", shadow * 0.019, shadow * 0.168),
    ("Body heat thermoelectric: 13.8 (still air) -> 71.8 uW/cm2 (2 m/s air)", "ear-contact rubber <= 10.6 cm2", contact * 0.0138, contact * 0.0718),
    ("Sweat biofuel cell: 68 uW/cm2 (workout) -> 1.2 mW/cm2 (on-body peak)", "ear-contact rubber <= 10.6 cm2", contact * 0.068, contact * 1.2),
    ("Motion electromagnetic: 50 uW/cm3 (leg, running) -> 1.45 mW/cm3 (wrist, running)", "ENTIRE bud volume (impossible bound)", vol * 0.050, vol * 1.45),
    ("Motion triboelectric: 4.65 -> 50.49 uW/cm2", "ENTIRE outer skin (impossible bound)", skin * 0.00465, skin * 0.05049),
    ("Jaw / ear-canal: chin strap ~10 uW; piezo earpiece 44 uJ per cycle = 70 uW", "while chewing", 0.010, 0.070),
    ("Ambient RF: 0.01-0.3 uW/cm2 x ideal 900 MHz dipole aperture 132 cm2", "antenna aperture", 0.01e-3 * 132, 0.3e-3 * 132),
    ("Sound: 90 dB = 0.1 uW/cm2, 100 dB = 1 uW/cm2, 100 % conversion", "ENTIRE outer skin", skin * 0.1e-3, skin * 1e-3),
]
for name, basis, lo, hi in rows:
    rt = lambda p: "indefinite" if p >= D else f"{B / (D - p):.2f} h"
    print(f"{name}\n   {basis}: {lo:.3f}-{hi:.3f} mW = {100*lo/D:.2f}-{100*hi/D:.1f}% of draw, runtime {rt(lo)} - {rt(hi)}")
