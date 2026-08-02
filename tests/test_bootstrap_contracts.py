from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.shared import import_local_module

compute_mod = import_local_module(
    "marsquake_compute_vespagram_bootstrap_contract_test",
    "scripts/03_vespagram/compute_vespagram.py",
)
DEFAULT_MIN_STACK_SUPPORT = compute_mod.DEFAULT_MIN_STACK_SUPPORT
bootstrap_type1 = import_local_module(
    "marsquake_bootstrap_type1_test",
    "scripts/04_bootstrap/bootstrap_type1.py",
).bootstrap_type1
bootstrap_type3_module = import_local_module(
    "marsquake_bootstrap_type3_test",
    "scripts/04_bootstrap/bootstrap_type3_alignment_jitter.py",
)
bootstrap_type3_p_pick_jitter = bootstrap_type3_module.bootstrap_type3_p_pick_jitter
shift_trace_on_time_axis = bootstrap_type3_module.shift_trace_on_time_axis
fit_bootstrap_maps = import_local_module(
    "marsquake_fit_gaussian_test",
    "scripts/04_bootstrap/fit_gaussian.py",
).fit_bootstrap_maps
fit_gaussian_mod = import_local_module(
    "marsukul_fit_gaussian_quality_test",
    "scripts/04_bootstrap/fit_gaussian.py",
)
TEST_BOOTSTRAP_FIDELITY = "test_fixture_unregistered"


def _fixture_bootstrap_cfg(n_bootstrap: int, **extra):
    return {
        "n_bootstrap": n_bootstrap,
        "bootstrap_fidelity_level": TEST_BOOTSTRAP_FIDELITY,
        **extra,
    }


def _build_traces(ids, npts: int = 100):
    t = np.linspace(0.0, 10.0, npts)
    traces = {}
    for i, eid in enumerate(ids):
        traces[eid] = (np.sin(t + (i * 0.2))).astype(np.float32)
    return traces


def _all_valid_masks(traces):
    return {eid: np.ones_like(trace, dtype=bool) for eid, trace in traces.items()}


def _parse_machine_error(excinfo):
    return json.loads(str(excinfo.value))


def _bootstrap_type2_module():
    return import_local_module(
        "marsquake_bootstrap_type2_test",
        "scripts/04_bootstrap/bootstrap_type2_distance.py",
    )


def test_bootstrap_type1_outputs_occupancy_and_bounds(tmp_path):
    event_ids = [f"S{i:04d}" for i in range(1, 11)]
    distances = [29.0 + 0.2 * i for i in range(len(event_ids))]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    cfg = _fixture_bootstrap_cfg(
        7,
        power_window_s=20.0,
        seed=7,
        threshold_pcts=[50, 70, 85],
        valid_masks=_all_valid_masks(traces),
    )

    bootstrap_type1(event_ids, distances, traces, cfg, t, tmp_path)

    pkikp = np.load(tmp_path / "type1_pkikp_occupancy.npz")
    pkkp = np.load(tmp_path / "type1_pkkp_occupancy.npz")
    assert pkikp["occupancy"].shape == pkkp["occupancy"].shape
    assert pkikp["occupancy"].shape[0] == 100
    assert pkikp["occupancy"].shape[1] == t.size
    assert pkikp["occupancy_maps"].shape == (3, 100, t.size)
    assert np.array_equal(pkikp["threshold_pcts"], np.array([50, 70, 85]))
    assert pkikp["peak_times"].shape == (cfg["n_bootstrap"],)
    assert pkikp["peak_slownesses"].shape == (cfg["n_bootstrap"],)
    assert np.nanmin(pkikp["occupancy"]) >= 0.0
    assert np.nanmax(pkikp["occupancy"]) <= 1.0
    assert int(pkikp["n_bootstrap"]) == cfg["n_bootstrap"]
    assert float(pkikp["sampling_rate_hz"]) == 1.0
    assert "slowness_axis" in pkikp
    assert "time_axis" in pkikp
    assert pkikp["selected_event_indices"].shape == (cfg["n_bootstrap"], int(np.floor(2.0 / 3.0 * len(event_ids))))
    assert "input_provenance_json" in pkikp


def test_bootstrap_type1_is_deterministic_with_seed(tmp_path):
    event_ids = [f"S{i:04d}" for i in range(1, 8)]
    distances = [29.0 + 0.1 * i for i in range(len(event_ids))]
    t = np.linspace(-100.0, 2200.0, 300)
    traces = _build_traces(event_ids, t.size)
    cfg = _fixture_bootstrap_cfg(11, power_window_s=10.0, seed=13, valid_masks=_all_valid_masks(traces))

    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    bootstrap_type1(event_ids, distances, traces, cfg, t, out1)
    bootstrap_type1(event_ids, distances, traces, cfg, t, out2)

    a = np.load(out1 / "type1_pkikp_occupancy.npz")["occupancy"]
    b = np.load(out2 / "type1_pkikp_occupancy.npz")["occupancy"]
    c = np.load(out1 / "type1_pkkp_occupancy.npz")["occupancy"]
    d = np.load(out2 / "type1_pkkp_occupancy.npz")["occupancy"]
    assert np.array_equal(a, b)
    assert np.array_equal(c, d)


def test_bootstrap_type1_requires_minimum_events(tmp_path):
    with np.testing.assert_raises(ValueError):
        bootstrap_type1(
            ["S0001"],
            [29.0],
            {"S0001": np.ones(100)},
            _fixture_bootstrap_cfg(3, power_window_s=20.0),
            np.linspace(-100, 2200, 100),
            tmp_path,
        )


def test_bootstrap_type1_rejects_trace_shape_mismatch(tmp_path):
    event_ids = [f"S{i:04d}" for i in range(1, 5)]
    distances = [29.0 + 0.1 * i for i in range(len(event_ids))]
    t = np.linspace(-100.0, 2200.0, 100)
    traces = _build_traces(event_ids, t.size)
    traces[event_ids[0]] = traces[event_ids[0]][:-1]
    cfg = _fixture_bootstrap_cfg(2, power_window_s=5.0, valid_masks=_all_valid_masks(traces))

    with pytest.raises(ValueError, match="Trace shape mismatch"):
        bootstrap_type1(event_ids, distances, traces, cfg, t, tmp_path)


@pytest.mark.parametrize(
    ("runner", "kwargs"),
    [
        (bootstrap_type1, {}),
        (bootstrap_type3_p_pick_jitter, {"jitter_limit_s": 0.0}),
    ],
)
def test_bootstraps_require_valid_masks_config(tmp_path, runner, kwargs):
    event_ids = ["S0001", "S0002"]
    distances = [29.0, 30.0]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    cfg = _fixture_bootstrap_cfg(1, power_window_s=10.0, **kwargs)

    with pytest.raises(RuntimeError) as excinfo:
        runner(event_ids, distances, traces, cfg, t, tmp_path)

    payload = _parse_machine_error(excinfo)
    assert payload["status"] == "blocked_missing_valid_masks"
    assert payload["missing_event_ids"] == event_ids


def test_bootstrap_type2_outputs_distance_stratified_occupancy_and_bins(tmp_path):
    mod = _bootstrap_type2_module()
    event_ids = [f"S{i:04d}" for i in range(1, 9)]
    distances = [29.1, 29.4, 30.2, 31.7, 33.0, 34.0, 36.0, 38.0]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    cfg = _fixture_bootstrap_cfg(
        6,
        power_window_s=1.0,
        seed=11,
        threshold_pcts=[50, 85],
        valid_masks=_all_valid_masks(traces),
    )

    mod.bootstrap_type2_distance_stratified(event_ids, distances, traces, cfg, t, tmp_path)

    pkikp = np.load(tmp_path / "type2_pkikp_distance_stratified_occupancy.npz")
    pkkp = np.load(tmp_path / "type2_pkkp_distance_stratified_occupancy.npz")
    assert str(pkikp["bootstrap_type"]) == "type2_distance_stratified"
    assert pkikp["occupancy"].shape == pkkp["occupancy"].shape == (100, t.size)
    assert pkikp["occupancy_maps"].shape == (2, 100, t.size)
    assert pkikp["selected_event_indices"].shape[0] == cfg["n_bootstrap"]
    assert pkikp["selected_distance_bin_labels"].shape == pkikp["selected_event_indices"].shape
    selected_labels = set(pkikp["selected_distance_bin_labels"].ravel().astype(str))
    assert selected_labels == {"cluster_29_32", "outside_29_32"}
    assert pkikp["support_at_peaks"].shape == (cfg["n_bootstrap"],)
    assert int(np.nanmin(pkikp["support_at_peaks"])) >= DEFAULT_MIN_STACK_SUPPORT
    assert int(np.nanmax(pkikp["support_at_peaks"])) <= int(pkikp["pick_n"])
    assert int(pkikp["minimum_support"]) == DEFAULT_MIN_STACK_SUPPORT


def test_bootstrap_type2_fails_closed_on_distance_cluster_pathology(tmp_path):
    mod = _bootstrap_type2_module()
    event_ids = [f"S{i:04d}" for i in range(1, 5)]
    distances = [29.1, 29.4, 30.2, 31.7]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    cfg = _fixture_bootstrap_cfg(
        2,
        power_window_s=1.0,
        valid_masks=_all_valid_masks(traces),
    )

    with pytest.raises(RuntimeError) as excinfo:
        mod.bootstrap_type2_distance_stratified(event_ids, distances, traces, cfg, t, tmp_path)

    payload = _parse_machine_error(excinfo)
    assert payload["status"] == "blocked_distance_cluster_pathology"
    assert payload["bootstrap_type"] == "type2_distance_stratified"


@pytest.mark.parametrize(
    ("runner", "kwargs"),
    [
        (bootstrap_type1, {}),
        (bootstrap_type3_p_pick_jitter, {"jitter_limit_s": 0.0}),
    ],
)
def test_bootstraps_require_valid_mask_for_every_event_id(tmp_path, runner, kwargs):
    event_ids = ["S0001", "S0002"]
    distances = [29.0, 30.0]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    masks = _all_valid_masks(traces)
    masks.pop("S0002")
    cfg = _fixture_bootstrap_cfg(1, power_window_s=10.0, valid_masks=masks, **kwargs)

    with pytest.raises(RuntimeError) as excinfo:
        runner(event_ids, distances, traces, cfg, t, tmp_path)

    payload = _parse_machine_error(excinfo)
    assert payload["status"] == "blocked_missing_valid_mask_events"
    assert payload["missing_event_ids"] == ["S0002"]


def test_bootstrap_type1_applies_configured_minimum_support(tmp_path):
    event_ids = ["S0001", "S0002"]
    distances = [29.0, 29.0]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    base_cfg = _fixture_bootstrap_cfg(
        1,
        power_window_s=1.0,
        seed=0,
        stack_method="linear",
        threshold_pcts=[85],
        valid_masks=_all_valid_masks(traces),
    )

    default_out = tmp_path / "default"
    strict_out = tmp_path / "strict"
    bootstrap_type1(event_ids, distances, traces, base_cfg, t, default_out)
    bootstrap_type1(event_ids, distances, traces, {**base_cfg, "minimum_support": 3}, t, strict_out)

    default_payload = np.load(default_out / "type1_pkikp_occupancy.npz")
    strict_payload = np.load(strict_out / "type1_pkikp_occupancy.npz")
    assert int(default_payload["minimum_support"]) == DEFAULT_MIN_STACK_SUPPORT
    assert int(strict_payload["minimum_support"]) == 3
    assert np.isfinite(default_payload["peak_powers"]).any()
    assert np.isnan(strict_payload["peak_powers"]).all()
    assert np.count_nonzero(default_payload["occupancy"]) > 0
    assert np.count_nonzero(strict_payload["occupancy"]) == 0


def test_shift_trace_on_time_axis_positive_shift_delays_feature():
    time_axis = np.arange(5.0)
    trace = np.zeros(5, dtype=float)
    trace[2] = 1.0

    shifted = shift_trace_on_time_axis(trace, time_axis, 1.0)

    assert int(np.argmax(shifted)) == 3


def test_bootstrap_type3_p_pick_jitter_outputs_bounds_and_metadata(tmp_path):
    event_ids = [f"S{i:04d}" for i in range(1, 8)]
    distances = [29.0 + 0.1 * i for i in range(len(event_ids))]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    cfg = _fixture_bootstrap_cfg(
        5,
        jitter_limit_s=10.0,
        power_window_s=20.0,
        seed=17,
        threshold_pcts=[50, 85],
        valid_masks=_all_valid_masks(traces),
    )

    bootstrap_type3_p_pick_jitter(event_ids, distances, traces, cfg, t, tmp_path)

    pkikp = np.load(tmp_path / "type3_pkikp_p_pick_jitter.npz")
    pkkp = np.load(tmp_path / "type3_pkkp_p_pick_jitter.npz")
    assert pkikp["occupancy"].shape == pkkp["occupancy"].shape
    assert pkikp["occupancy"].shape == (100, t.size)
    assert pkikp["occupancy_maps"].shape == (2, 100, t.size)
    assert np.array_equal(pkikp["threshold_pcts"], np.array([50, 85]))
    assert pkikp["peak_times"].shape == (cfg["n_bootstrap"],)
    assert pkikp["jitter_seconds"].shape == (cfg["n_bootstrap"], len(event_ids))
    assert np.nanmin(pkikp["jitter_seconds"]) >= -cfg["jitter_limit_s"]
    assert np.nanmax(pkikp["jitter_seconds"]) <= cfg["jitter_limit_s"]
    assert str(pkikp["bootstrap_type"]) == "type3_p_pick_jitter"
    assert list(pkikp["event_ids"]) == event_ids
    assert "base_peak_time_s" in pkikp
    assert "base_peak_slowness_sdeg" in pkikp
    assert "input_provenance_json" in pkikp
    assert "mode" in pkikp


def test_bootstrap_type3_rejects_trace_shape_mismatch(tmp_path):
    event_ids = [f"S{i:04d}" for i in range(1, 5)]
    distances = [29.0 + 0.1 * i for i in range(len(event_ids))]
    t = np.linspace(-100.0, 2200.0, 100)
    traces = _build_traces(event_ids, t.size)
    traces[event_ids[-1]] = traces[event_ids[-1]][:-1]
    cfg = _fixture_bootstrap_cfg(2, power_window_s=5.0, valid_masks=_all_valid_masks(traces))

    with pytest.raises(ValueError, match="Trace shape mismatch"):
        bootstrap_type3_p_pick_jitter(
            event_ids,
            distances,
            traces,
            cfg,
            t,
            tmp_path,
        )


def test_bootstrap_type3_applies_configured_minimum_support(tmp_path):
    event_ids = ["S0001", "S0002"]
    distances = [29.0, 29.0]
    t = np.linspace(-100.0, 2200.0, 2301)
    traces = _build_traces(event_ids, t.size)
    base_cfg = _fixture_bootstrap_cfg(
        1,
        jitter_limit_s=0.0,
        power_window_s=1.0,
        seed=0,
        stack_method="linear",
        threshold_pcts=[85],
        valid_masks=_all_valid_masks(traces),
    )

    default_out = tmp_path / "default"
    strict_out = tmp_path / "strict"
    bootstrap_type3_p_pick_jitter(event_ids, distances, traces, base_cfg, t, default_out)
    bootstrap_type3_p_pick_jitter(event_ids, distances, traces, {**base_cfg, "minimum_support": 3}, t, strict_out)

    default_payload = np.load(default_out / "type3_pkikp_p_pick_jitter.npz")
    strict_payload = np.load(strict_out / "type3_pkikp_p_pick_jitter.npz")
    assert int(default_payload["minimum_support"]) == DEFAULT_MIN_STACK_SUPPORT
    assert int(strict_payload["minimum_support"]) == 3
    assert np.isfinite(default_payload["base_peak_power"])
    assert np.isnan(strict_payload["base_peak_power"])
    assert np.isfinite(default_payload["peak_powers"]).any()
    assert np.isnan(strict_payload["peak_powers"]).all()
    assert np.count_nonzero(default_payload["occupancy"]) > 0
    assert np.count_nonzero(strict_payload["occupancy"]) == 0


def test_fit_bootstrap_maps_uses_threshold_specific_mean_maps(tmp_path):
    slowness = np.linspace(-10.0, 0.0, 9)
    time = np.linspace(0.0, 3.0, 5)
    occ50 = np.zeros((9, 5), dtype=float)
    occ85 = np.zeros((9, 5), dtype=float)
    occ50[2, 2] = 0.3
    occ50[3, 2] = 0.8
    occ50[4, 2] = 0.3
    occ85[4, 3] = 0.35
    occ85[5, 3] = 0.9
    occ85[6, 3] = 0.35

    for name in ("type1_pkikp_occupancy.npz", "type1_pkkp_occupancy.npz"):
        np.savez(
            tmp_path / name,
            occupancy=occ85,
            occupancy_maps=np.stack([occ50, occ85], axis=0),
            threshold_pcts=np.array([50, 85], dtype=np.int32),
            n_bootstrap=np.array(123, dtype=np.int32),
            slowness_axis=slowness,
            time_axis=time,
        )

    out_csv = tmp_path / "bootstrap_picks.csv"
    fit_bootstrap_maps(tmp_path, out_csv)

    df = pd.read_csv(out_csv)
    assert set(df["threshold_pct"]) == {50, 85}
    assert len(df) == 4
    assert set(df["n_bootstrap"]) == {123}


def test_bootstrap_fit_quality_rejects_observed_pkikp_degenerate_slowness():
    result = fit_gaussian_mod.assess_projection_fit_quality(
        axis_name="slowness",
        mean=-0.00358113047202732,
        sigma=0.4135851428833738,
        residual_rms=18.85574722290039,
        projection_peak=102.739990234375,
        axis_min=-10.0,
        axis_max=0.0,
        grid_spacing=10.0 / 99.0,
        occupancy_argmax=-3.7373738288879395,
        weighted_median=-3.535353422164917,
        fit_converged=True,
        fallback_used=False,
    )

    assert result["fit_converged"] is False
    assert result["degenerate_fit"] is True
    assert "residual_rms_fraction" in result["reasons"]
    assert "tri_estimator_inconsistency" in result["reasons"]
    assert result["registered_limits"]["max_residual_rms_fraction_of_projection_peak"] == pytest.approx(0.10)
    assert result["registered_limits"]["tri_estimator_tolerance_grid_cells"] == pytest.approx(3.0)


def test_fit_bootstrap_maps_flags_degenerate_fit_without_erasing_robust_estimators(tmp_path):
    slowness = np.linspace(-10.0, 0.0, 100)
    time = np.linspace(550.0, 700.0, 3001)
    occ85 = np.zeros((100, 3001), dtype=np.float64)
    argmax_slow_idx = int(np.argmin(np.abs(slowness + 3.7373738288879395)))
    median_slow_idx = int(np.argmin(np.abs(slowness + 3.535353422164917)))
    argmax_time_idx = int(np.argmin(np.abs(time - 664.0)))
    median_time_idx = int(np.argmin(np.abs(time - 638.6)))
    occ85[argmax_slow_idx, argmax_time_idx] = 1.0
    occ85[median_slow_idx, median_time_idx] = 0.9
    occ85[80, argmax_time_idx] = 1.0

    for name in ("type1_pkikp_occupancy.npz", "type1_pkkp_occupancy.npz"):
        np.savez(
            tmp_path / name,
            occupancy=occ85,
            occupancy_maps=np.expand_dims(occ85, axis=0),
            threshold_pcts=np.array([85], dtype=np.int32),
            n_bootstrap=np.array(200, dtype=np.int32),
            slowness_axis=slowness,
            time_axis=time,
        )

    output_csv = tmp_path / "bootstrap_picks.csv"
    fit_bootstrap_maps(tmp_path, output_csv)

    rows = pd.read_csv(output_csv)
    pkikp = rows[rows["phase"] == "pkikp"].iloc[0]
    assert bool(pkikp["degenerate_fit"]) is True
    assert bool(pkikp["slowness_fit_converged"]) is False
    assert "residual_rms_fraction" in pkikp["fit_quality_reasons"]
    assert pkikp["occupancy_argmax_slowness_sdeg"] == pytest.approx(slowness[argmax_slow_idx])
    assert pkikp["weighted_median_slowness_sdeg"] == pytest.approx(slowness[median_slow_idx])
