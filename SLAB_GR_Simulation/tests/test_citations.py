"""Checks for the citation / constant verification pass of 2026-09-25 (docs/additions/citations.md).

* the primary constants are exactly the CODATA 2022 / SI / IAU values recorded in references.md;
* the l_P standard uncertainty is the CODATA one (1.8e-40 m, relative 1.1e-5), not the old 1.8e-41;
* the documented relations for the solar mass hold (brief value = IAU GM_sun / CODATA-2014 G);
* no "not re-verified" flag survives, every bibliography entry carries a status, and every DOI in
  references.md / constants.py is listed in the verification table of docs/additions/citations.md;
* the corrected propulsion note of physics_notes.md §6: the longest proper time from the horizon to
  r = 0 is pi*M (E = 0 geodesic), 4M/3 for E = 1, and the free-fall remaining time falls with E > 0.

Run:  cd SLAB_GR_Simulation && python -m pytest tests -q
"""
import math
import re
import sys
from pathlib import Path

import pytest
from scipy.integrate import quad

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab import constants as C  # noqa: E402

REFS = (ROOT / "references.md").read_text(encoding="utf-8")
NOTES = (ROOT / "physics_notes.md").read_text(encoding="utf-8")
REFS_README = (ROOT / "references" / "README.md").read_text(encoding="utf-8")
CITATIONS = (ROOT / "docs" / "additions" / "citations.md").read_text(encoding="utf-8")

STATUS_RE = re.compile(r"VERIFIED VIA WEB SEARCH|PARTIALLY VERIFIED|INSUFFICIENT DATA TO VERIFY|"
                       r"\*\*VERIFIED \(2026-09-25\)\*\*")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;]+")


def _dois(text):
    return {m.rstrip(".)*") for m in DOI_RE.findall(text)}


def test_primary_constants_are_codata_2022_and_exact_si_iau_values():
    P = C.PRIMARY_CONSTANTS
    # CODATA 2022 (= CODATA 2018 for these three): value and standard uncertainty
    assert P["G"]["value"] == 6.67430e-11 and P["G"]["uncertainty"] == 1.5e-15
    assert P["l_P"]["value"] == 1.616255e-35 and P["l_P"]["uncertainty"] == 1.8e-40
    hbar_exact = 6.62607015e-34 / (2.0 * math.pi)
    assert P["hbar"]["value"] == 1.054571817e-34      # the 10 digits printed by CODATA (1.054 571 817...)
    assert 0.0 < (hbar_exact - P["hbar"]["value"]) / hbar_exact < 1e-9
    # relative standard uncertainties as published (2.2e-5 and 1.1e-5)
    assert round(P["G"]["uncertainty"] / P["G"]["value"], 6) == 2.2e-5
    assert round(P["l_P"]["uncertainty"] / P["l_P"]["value"], 6) == 1.1e-5
    # exact definitions (SI 2019, IAU 2012 B2, Julian year / light-year)
    assert C.c == 299792458.0
    assert C.AU == 149597870700.0
    assert C.YEAR == 365.25 * 86400.0 == 31557600.0
    assert C.LIGHT_YEAR == 9460730472580800.0
    for key, entry in P.items():
        assert "CODATA 2018 recommended value;" not in entry["source"], key


def test_planck_length_consistent_within_codata_uncertainty():
    lp = math.sqrt(C.hbar * C.G / C.c**3)
    assert abs(lp - C.l_P) < C.PRIMARY_CONSTANTS["l_P"]["uncertainty"]


def test_propagated_uncertainties_use_corrected_lP_uncertainty():
    ru = C.DerivedQuantities(1e18).relative_uncertainties()
    assert ru["l_P"] == pytest.approx(1.1137e-5, rel=1e-3)
    assert ru["K_planck (∝ l_P^-4)"] == pytest.approx(4.0 * ru["l_P"], rel=1e-12)


def test_solar_mass_relations_documented_in_references():
    gm_sun_iau2015 = 1.3271244e20          # IAU 2015 B3 nominal (GM)_sun, exact [m^3 s^-2]
    g_codata2014 = 6.67408e-11             # CODATA 2014
    # the brief's value is (GM)_sun / G_2014 = 1.988475e30 kg to its quoted digits
    assert abs(gm_sun_iau2015 / g_codata2014 - C.M_sun) / C.M_sun < 5e-6
    # with CODATA 2022 G it is 1.98841e30 kg: 3.0e-5 lower (the documented discrepancy)
    rel = (C.M_sun - gm_sun_iau2015 / C.G) / C.M_sun
    assert 2.9e-5 < rel < 3.1e-5
    assert rel < C.PRIMARY_CONSTANTS["M_sun"]["uncertainty"] / C.M_sun


def test_no_unverified_flags_remain():
    for name, text in (("references.md", REFS), ("physics_notes.md", NOTES), ("references/README.md", REFS_README)):
        assert "NOT RE-VERIFIED ONLINE" not in text.upper(), name
        assert "[citation from memory" not in text, name
    for key, entry in C.PRIMARY_CONSTANTS.items():
        assert "NOT RE-VERIFIED" not in entry["verification"].upper(), key
        assert re.search(r"VERIFIED|EXACT", entry["verification"]), key
    assert "NOT RE-VERIFIED" not in (C.__doc__ or "").upper()


def test_every_bibliography_entry_has_a_status():
    sections = re.split(r"^## ", REFS, flags=re.M)[1:]
    checked = 0
    for sec in sections:
        number = sec.split(".", 1)[0].strip()
        if number == "7":                      # the project's own data files: not citations
            continue
        entries, cur = [], None
        for line in sec.splitlines():
            if line.startswith("* "):
                cur = [line]
                entries.append(cur)
            elif line.startswith("#"):
                cur = None
            elif cur is not None:
                cur.append(line)
        for e in entries:
            text = "\n".join(e)
            if text.startswith("* Scope statement"):
                continue
            assert STATUS_RE.search(text), f"no verification status in references.md entry: {e[0][:90]}"
            checked += 1
    assert checked >= 35


def test_every_doi_is_in_the_verification_table():
    dois = _dois(REFS) | _dois(" ".join(e["source"] for e in C.PRIMARY_CONSTANTS.values()))
    assert len(dois) >= 20
    table = CITATIONS.split("## Verification table", 1)[1]
    missing = sorted(d for d in dois if d not in table)
    assert not missing, f"DOIs without a verification-table row: {missing}"


def _remaining_proper_time_from_horizon(E: float) -> float:
    """tau(r = 2M -> 0) of a radial free fall with Killing energy E (M = 1), using r = 2 sin^2(t):
    dr / sqrt(E^2 + 2/r - 1) = 4 sin^2(t) cos(t) / sqrt(E^2 sin^2(t) + cos^2(t)) dt, t in (0, pi/2)."""
    val, _ = quad(lambda t: 4.0 * math.sin(t) ** 2 * math.cos(t) / math.sqrt(E * E * math.sin(t) ** 2 + math.cos(t) ** 2),
                  0.0, 0.5 * math.pi, epsabs=0.0, epsrel=1e-13, limit=200)
    return val


def test_maximal_interior_proper_time_is_pi_M_and_falls_with_E():
    assert _remaining_proper_time_from_horizon(0.0) == pytest.approx(math.pi, rel=1e-12)
    assert _remaining_proper_time_from_horizon(1.0) == pytest.approx(4.0 / 3.0, rel=1e-12)
    values = [_remaining_proper_time_from_horizon(E) for E in (0.0, 0.25, 0.5, 1.0, 2.0, 10.0)]
    assert all(a > b for a, b in zip(values, values[1:]))
