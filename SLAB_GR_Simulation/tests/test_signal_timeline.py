"""Distant-observer received-signal timeline and the new export columns / files."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from slab.metric import Schwarzschild  # noqa: E402
from slab.geodesic import RadialInfallE1  # noqa: E402
from slab.signals import (compute_signal_timeline, one_plus_z_E1_closed_form, late_time_slopes, retarded_time,  # noqa: E402
                          f_accurate)
from slab.trajectory import Simulation, SimulationConfig  # noqa: E402
from slab import io as sio  # noqa: E402

CONTRACT_KEYS = ("note", "eps", "r_over_rs", "t_receive_years", "one_plus_z", "tau_years", "t_schw_years", "late_time_efold_years")


@pytest.fixture(scope="module")
def sim_e1():
    sim = Simulation(SimulationConfig(rtol=1e-11), verbose=False)
    sim.run()
    sim.postprocess()
    return sim


def test_retarded_time_and_f_accurate():
    m = Schwarzschild()
    assert math.isnan(retarded_time(m, 0.0, 2.0)) and math.isnan(retarded_time(m, 0.0, 1.0))
    assert math.isclose(retarded_time(m, 5.0, 10.0), 5.0 - 2.0 * (10.0 + 2.0 * math.log(4.0)), rel_tol=1e-15)
    r = 2.0 * (1.0 + 1e-12)
    assert abs(f_accurate(r) / ((r / 2.0 - 1.0) / (r / 2.0)) - 1.0) < 1e-15      # 1 - 2/r would be off by ~1e-4 here


def test_timeline_E1_closed_forms(sim_e1):
    tl = sim_e1.signal_timeline()
    for k in CONTRACT_KEYS:
        assert k in tl
    eps = np.array(tl["eps"])
    assert eps[0] == pytest.approx(99.0) and eps[-1] < 1.1e-12 and np.all(np.diff(eps) < 0)
    r = np.array(tl["r_over_rs"]) * 2.0
    assert np.max(np.abs(np.array(tl["one_plus_z"]) / one_plus_z_E1_closed_form(r) - 1.0)) < 1e-9
    ref, m = RadialInfallE1(), Schwarzschild()
    u_cf = np.array([ref.v_between(r[0], x) - 2.0 * (m.tortoise(x) - m.tortoise(r[0])) for x in r])
    assert np.max(np.abs(np.array(tl["t_receive_geo"]) - u_cf) / np.maximum(1.0, np.abs(u_cf))) < 1e-9
    assert tl["t_receive_years"][0] == 0.0 and tl["tau_years"][0] == 0.0 and tl["t_schw_years"][0] == 0.0
    assert tl["late_time_efold_years"] == pytest.approx(4.0 * sim_e1.dq.GM_over_c3_years, rel=1e-12)
    # dense-output route agrees with the per-radius exact integration
    tld = compute_signal_timeline(sim_e1, method="dense")
    assert np.max(np.abs(np.array(tld["one_plus_z"]) / np.array(tl["one_plus_z"]) - 1.0)) < 1e-9


def test_late_time_exponential_redshift_fall_from_rest():
    """E < 1 fall from rest at 10 r_s (tau mode, turning point at the start): the late-time law is universal."""
    E = math.sqrt(1.0 - 2.0 / 20.0)
    sim = Simulation(SimulationConfig(E=E, r0_over_rs=10.0, rtol=1e-11), verbose=False)
    tl = compute_signal_timeline(sim, points_per_decade=10)
    assert tl["one_plus_z"][0] == pytest.approx(1.0 / math.sqrt(0.9), rel=1e-12)   # at rest: gravitational redshift only
    s = late_time_slopes(tl, 1e-8)
    assert abs(s["dln1pz_du_times_4M"] - 1.0) < 1e-2
    assert abs(s["t_receive_per_decade_geo"] / (4.0 * math.log(10.0)) - 1.0) < 1e-2
    assert s["tau_increment_over_range_geo"] < 1e-6 * s["t_receive_increment_over_range_geo"]
    assert np.all(np.diff(tl["t_receive_geo"]) > 0) and np.all(np.diff(tl["tau_geo"]) > 0)


def test_start_inside_horizon_gives_empty_timeline():
    sim = Simulation(SimulationConfig(r0_over_rs=0.5), verbose=False)
    tl = sim.signal_timeline()
    assert tl["eps"] == [] and "EMPTY" in tl["note"]


def test_outputs_contain_new_columns_and_timeline(sim_e1, tmp_path):
    import h5py
    c = sim_e1.columns
    inside = c["r_geo"] <= 2.0
    for k in ("u_ret_geo", "t_receive_years", "inertial_diff_radial_m_s2", "radial_total_diff_m_s2"):
        assert k in c and k in sio.COLUMN_DESCRIPTIONS
    assert np.all(np.isnan(c["u_ret_geo"][inside])) and np.all(np.isfinite(c["t_receive_years"][~inside]))
    assert c["t_receive_years"][0] == 0.0 and np.all(np.diff(c["t_receive_years"][~inside]) > 0)
    assert np.all(c["inertial_diff_radial_m_s2"] == 0.0) and np.array_equal(c["radial_total_diff_m_s2"], c["radial_stretch_m_s2"])
    d = tmp_path / "data"
    d.mkdir()
    sio.write_csv(sim_e1, d / "trajectory.csv")
    sio.write_hdf5(sim_e1, d / "trajectory.h5")
    sio.write_json(sim_e1, d / "trajectory_metadata.json")
    sio.write_render_data(sim_e1, tmp_path / "trajectory_data.js", d / "trajectory_render.json", 500)
    lines = (d / "signal_timeline.csv").read_text().splitlines()
    header = next(l for l in lines if not l.startswith("#"))
    assert header.split(",")[:6] == ["eps", "r_over_rs", "t_receive_years", "one_plus_z", "tau_years", "t_schw_years"]
    assert len([l for l in lines if not l.startswith("#")]) == len(sim_e1.signal_timeline()["eps"]) + 1
    assert "t_receive_years" in (d / "trajectory.csv").read_text().splitlines()[2]
    with h5py.File(d / "trajectory.h5") as h:
        assert "signal_timeline" in h and len(h["signal_timeline/eps"]) == len(sim_e1.signal_timeline()["eps"])
        for k in ("u_ret_geo", "t_receive_years", "inertial_diff_radial_m_s2", "radial_total_diff_m_s2"):
            assert k in h["trajectory"]
    meta = json.loads((d / "trajectory_metadata.json").read_text())
    assert meta["signal_timeline_summary"]["n_points"] == len(sim_e1.signal_timeline()["eps"])
    js = (tmp_path / "trajectory_data.js").read_text()
    payload = json.loads(js.split("window.SLAB_DATA = ", 1)[1].rstrip().rstrip(";"))
    st = payload["signal_timeline"]
    assert set(CONTRACT_KEYS) <= set(st) and len(st["eps"]) == len(st["one_plus_z"]) > 200
    smp = payload["samples"]
    lr = np.array(smp["log10_r_over_rs"])
    tr = smp["t_receive_years"]
    assert all(tr[i] is None for i in np.where(lr < 0)[0]) and all(tr[i] is not None for i in np.where(lr > 1e-9)[0])
    assert all(v == 0.0 for v in smp["inertial_diff_radial_m_s2"])
