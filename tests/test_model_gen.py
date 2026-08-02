from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest
from obspy.taup import TauPyModel

from scripts.shared import import_local_module, repo_path

model_gen_module = import_local_module(
    "marsquake_generate_nd_model_test",
    "scripts/05_model_gen/generate_nd_model.py",
)
generate_nd_model = model_gen_module.generate_nd_model


def _write_minimal_nd(path: Path):
    text = """mantle
0.0 4.5 2.6 3.3
1589.5 5.0 2.9 3.8
outer-core
1589.5 5.0 0.0 4.0
2789.5 5.8 0.0 5.1
inner-core
2789.5 7.0 4.0 6.5
3389.5 7.8 4.5 6.5
"""
    path.write_text(text, encoding="utf-8")


def _read_sections_for_model(path: Path):
    sections = {"mantle": [], "outer-core": [], "inner-core": []}
    current = "mantle"
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ln in {"mantle", "outer-core", "inner-core"}:
            current = ln
            sections[current] = []
            continue
        sections[current].append([float(x) for x in ln.split()[:4]])
    return {k: np.array(v) for k, v in sections.items()}


def _released_interp_line():
    rel = "references/original_paper/Mars_IC-main/MCMC_inversion-main/MCMC_inversion_M_vesp.py"
    try:
        return import_local_module("marsquake_released_m_vesp_test", rel).interp_line
    except Exception:
        # Source: references/original_paper/Mars_IC-main/MCMC_inversion-main/
        # MCMC_inversion_M_vesp.py:24-34, identical in MCMC_inversion_M_pick.py.
        # The release imports optional runtime packages at module import time, so
        # this literal body is the fallback when direct import is unavailable.
        def draw_curve(p1, p2, n=10):
            a = (p2[1] - p1[1]) / (np.cosh(p2[0]) - np.cosh(p1[0]))
            b = p1[1] - a * np.cosh(p1[0])
            x = np.linspace(p1[0], p2[0], n)
            y = a * np.cosh(x) + b
            return x, y

        def interp_line(p1, p2, n):
            names = ["depth", "vp", "vs", "density"]
            _data = []
            with np.errstate(divide="ignore", invalid="ignore"):
                for i in range(1, len(names)):
                    _x, _y = draw_curve([p1[i], p1[0]], [p2[i], p2[0]], n=n)
                    if i == 1:
                        _data.append(_y)
                    _data.append(_x)
            return np.vstack(_data).T

        return interp_line


def _eq6_coefficients(depth1: float, depth2: float, vp1: float, vp2: float):
    K = (depth2 - depth1) / (np.cosh(vp2) - np.cosh(vp1))
    b = depth1 - K * np.cosh(vp1)
    return K, b


def _generate_reference_model(tmp_path: Path, *, r_ic=600.0, dvp_icb=0.30):
    base = tmp_path / "base.nd"
    _write_minimal_nd(base)
    out_nd, out_npz = generate_nd_model(
        R_OC=1800.0,
        Vp_CMB=5.0,
        Vp_OC_ICB=5.8,
        R_IC=r_ic,
        dVp_ICB=dvp_icb,
        base_model_path=base,
        out_dir=tmp_path,
        tag="ref",
    )
    return Path(out_nd), Path(out_npz)


def test_released_interp_line_equals_printed_eq6_on_outer_core_nodes():
    interp_line = _released_interp_line()
    p1 = [1589.5, 5.0, 0.0, 6.8]
    p2 = [2789.5, 5.8, 0.0, 6.8]
    rows = interp_line(p1, p2, n=15)

    expected_vp = np.linspace(5.0, 5.8, 15)
    K, b = _eq6_coefficients(1589.5, 2789.5, 5.0, 5.8)
    expected_depth = K * np.cosh(expected_vp) + b
    vp_from_printed_eq6 = np.arccosh((rows[:, 0] - b) / K)

    np.testing.assert_allclose(rows[:, 1], expected_vp, rtol=0, atol=1e-12)
    np.testing.assert_allclose(rows[:, 0], expected_depth, rtol=0, atol=1e-9)
    np.testing.assert_allclose(vp_from_printed_eq6, rows[:, 1], rtol=0, atol=1e-12)


def test_generate_nd_model_outer_core_matches_released_interp_line_and_eq6(tmp_path):
    out_nd, _ = _generate_reference_model(tmp_path)
    oc = _read_sections_for_model(out_nd)["outer-core"]

    interp_line = _released_interp_line()
    released_rows = interp_line([1589.5, 5.0, 0.0, 6.8], [2789.5, 5.8, 0.0, 6.8], n=15)
    K, b = _eq6_coefficients(1589.5, 2789.5, 5.0, 5.8)
    vp_from_printed_eq6 = np.arccosh((oc[:, 0] - b) / K)

    assert oc.shape == (15, 4)
    np.testing.assert_allclose(oc[:, 0], released_rows[:, 0], rtol=0, atol=6e-4)
    np.testing.assert_allclose(oc[:, 1], released_rows[:, 1], rtol=0, atol=6e-5)
    np.testing.assert_allclose(vp_from_printed_eq6, oc[:, 1], rtol=0, atol=6e-4)


def test_generate_nd_model_inner_core_uses_same_velocity_sampled_family(tmp_path):
    out_nd, _ = _generate_reference_model(tmp_path)
    ic = _read_sections_for_model(out_nd)["inner-core"]

    vp_icb = 5.8 * 1.30
    vp_gradient = (5.8 - 5.0) / (1800.0 - 600.0)
    vp_center = vp_icb + vp_gradient * 600.0
    expected_vp = np.linspace(vp_icb, vp_center, 5)
    K, b = _eq6_coefficients(2789.5, 3389.5, vp_icb, vp_center)
    expected_depth = K * np.cosh(expected_vp) + b

    assert ic.shape == (5, 4)
    np.testing.assert_allclose(ic[:, 0], expected_depth, rtol=0, atol=6e-4)
    np.testing.assert_allclose(ic[:, 1], expected_vp, rtol=0, atol=6e-5)


def test_generate_nd_model_output_sections_boundaries_and_non_degenerate_nodes(tmp_path):
    out_nd, _ = _generate_reference_model(tmp_path, r_ic=900.0, dvp_icb=0.10)
    sections = _read_sections_for_model(out_nd)

    assert len(sections["outer-core"]) == 15
    assert len(sections["inner-core"]) == 5

    depth_CMB = 3389.5 - 1800.0
    depth_ICB = 3389.5 - 900.0
    oc = sections["outer-core"]
    ic = sections["inner-core"]

    assert np.isclose(oc[0, 0], depth_CMB, atol=6e-4)
    assert np.isclose(oc[-1, 0], depth_ICB, atol=6e-4)
    assert np.isclose(ic[0, 0], depth_ICB, atol=6e-4)
    assert np.isclose(ic[-1, 0], 3389.5, atol=6e-4)
    assert np.allclose(oc[:, 2], 0.0, atol=1e-12)
    assert np.sum(np.isclose(oc[:, 1], oc[0, 1], atol=1e-12)) == 1
    assert np.all(np.diff(oc[:, 0]) > 0.0)
    assert np.all(np.diff(oc[:, 1]) > 0.0)


def test_generate_nd_model_core_velocities_are_physically_sane(tmp_path):
    out_nd, _ = _generate_reference_model(tmp_path)
    sections = _read_sections_for_model(out_nd)
    oc = sections["outer-core"]
    ic = sections["inner-core"]

    np.testing.assert_allclose(oc[:, 1], np.linspace(5.0, 5.8, 15), rtol=0, atol=6e-5)
    assert np.all((4.5 <= oc[:, 1]) & (oc[:, 1] <= 6.5))
    assert np.all((7.0 <= ic[:, 1]) & (ic[:, 1] <= 8.5))
    assert np.all(ic[:, 2] > 0.0)
    assert np.all(ic[:, 2] < ic[:, 1])


def test_model_generation_and_boundaries_are_taup_loadable(tmp_path):
    out_nd, out_npz = _generate_reference_model(tmp_path)

    lines = [ln.strip() for ln in out_nd.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert "outer-core" in lines and "inner-core" in lines
    first = lines[0]
    assert first.split()[0].replace(".", "", 1).replace("-", "", 1).isdigit(), first

    model = TauPyModel(model=str(out_npz))
    phases = model.get_travel_times(
        source_depth_in_km=33,
        distance_in_degree=29.0,
        phase_list=["P", "PKiKP", "PKIKKIKP", "PKPPKP"],
    )
    phase_names = {tr.phase.name for tr in phases}
    assert "P" in phase_names
    assert any(
        [tr.time for tr in phases if tr.phase.name == phase and np.isfinite(tr.time)]
        for phase in ["PKIKKIKP", "PKPPKP", "PKiKP"]
    )


def test_generate_nd_model_monotonic_depths_are_non_decreasing(tmp_path):
    out_nd, _ = _generate_reference_model(tmp_path)
    sections = _read_sections_for_model(out_nd)

    for layer_name, rows in sections.items():
        assert rows.size > 0, layer_name
        assert np.all(np.diff(rows[:, 0]) >= -1e-12), f"{layer_name} depths are not monotonic: {rows[:, 0]}"


def test_generate_nd_model_is_deterministic_when_reloaded(tmp_path):
    base = tmp_path / "base.nd"
    _write_minimal_nd(base)
    out_nd_a, _ = generate_nd_model(
        R_OC=1800.0,
        Vp_CMB=5.0,
        Vp_OC_ICB=5.8,
        R_IC=600.0,
        dVp_ICB=0.30,
        base_model_path=base,
        out_dir=tmp_path,
        tag="same",
    )
    out_nd_b, _ = generate_nd_model(
        R_OC=1800.0,
        Vp_CMB=5.0,
        Vp_OC_ICB=5.8,
        R_IC=600.0,
        dVp_ICB=0.30,
        base_model_path=base,
        out_dir=tmp_path,
        tag="same",
    )

    assert Path(out_nd_a).read_text(encoding="utf-8") == Path(out_nd_b).read_text(encoding="utf-8")


def test_generate_nd_model_rejects_invalid_core_radius_order(tmp_path):
    base = tmp_path / "base.nd"
    _write_minimal_nd(base)

    with pytest.raises(ValueError):
        generate_nd_model(
            R_OC=900.0,
            Vp_CMB=5.0,
            Vp_OC_ICB=5.8,
            R_IC=1200.0,
            dVp_ICB=0.30,
            base_model_path=base,
            out_dir=tmp_path,
        )


def test_generate_nd_model_rejects_base_rows_with_vs_greater_than_vp(tmp_path):
    base = tmp_path / "bad_base.nd"
    base.write_text(
        "\n".join(
            [
                "mantle",
                "0.0 2.0 3.0 3.3",
                "outer-core",
                "2000.0 5.0 0.0 4.0",
                "inner-core",
                "3000.0 7.0 4.0 6.5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        generate_nd_model(
            R_OC=1800.0,
            Vp_CMB=5.0,
            Vp_OC_ICB=5.8,
            R_IC=600.0,
            dVp_ICB=0.30,
            base_model_path=base,
            out_dir=tmp_path,
        )


def test_cosh_family_has_single_authoritative_production_source():
    allowed_reference_transcriptions = {
        "scripts/10_paper3/released_reference.py",
    }
    hits = []
    root = repo_path("")
    for path in repo_path("scripts").rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in path.parts or rel in allowed_reference_transcriptions:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"np\.(?:arc)?cosh\s*\(", text):
            hits.append(rel)

    assert hits == ["scripts/core_profile.py"]


def test_model_generator_fidelity_artifact_schema_documents_zero_diff(tmp_path):
    profile_core = import_local_module("marsquake_core_profile_artifact_test", "scripts/core_profile.py")
    artifact = model_gen_module.model_generator_fidelity_report()
    ok, status, detail = profile_core.validate_model_generator_fidelity_payload(artifact)
    encoded = json.dumps(artifact, sort_keys=True)

    assert ok is True, detail
    assert status == "ok"
    assert "released-eq6-vp-cosh-20260704" in encoded
    assert artifact["n_outer_core_nodes"] == 15
    assert artifact["max_abs_depth_diff_released_km"] <= 1e-9
    assert artifact["max_abs_vp_diff_released_km_s"] <= 1e-12
    assert artifact["max_abs_vp_diff_printed_eq6_km_s"] <= 1e-12

    path = tmp_path / "model_generator_fidelity.json"
    model_gen_module.write_model_generator_fidelity_report(path)
    ok, status, detail = profile_core.check_model_generator_fidelity_artifact(path)
    assert ok is True, detail
    assert status == "ok"

    stale = json.loads(path.read_text(encoding="utf-8"))
    stale["scripts_core_profile.py_sha256"] = "stale"
    path.write_text(json.dumps(stale), encoding="utf-8")
    ok, status, detail = profile_core.check_model_generator_fidelity_artifact(path)
    assert ok is False
    assert status == "blocked_model_generator_fidelity_failed"
    assert detail["hash_key"] == "scripts_core_profile.py_sha256"
