from __future__ import annotations

import csv
import json
import numpy as np
import pytest
from pathlib import Path

from scripts.shared import import_local_module

compute_mod = import_local_module(
    "marsquake_compute_vespagram_test",
    "scripts/03_vespagram/compute_vespagram.py",
)
detect_peaks = import_local_module(
    "marsquake_detect_peaks_test",
    "scripts/03_vespagram/detect_peaks.py",
)
compute_vespagram = compute_mod.compute_vespagram
detect = detect_peaks.detect
run_detect = detect_peaks.run_detect
parse_combo_from_path = detect_peaks.parse_combo_from_path
stacking = import_local_module(
    "marsquake_stacking_for_vespagram_mask_test",
    "scripts/03_vespagram/stacking.py",
)
run_vespagrams = import_local_module(
    "marsquake_run_vespagrams_operator_test",
    "scripts/03_vespagram/run_vespagrams.py",
)


def _all_valid_masks(traces):
    return [np.ones_like(np.asarray(trace), dtype=bool) for trace in traces]


def _write_current_vespagram_payload(
    path: Path,
    v: np.ndarray,
    s: np.ndarray,
    t: np.ndarray,
    support: np.ndarray | None = None,
    *,
    distance_errors: np.ndarray | None = None,
    extra_payload: dict | None = None,
    omit_payload_fields: tuple[str, ...] = (),
) -> None:
    if support is None:
        support = np.full_like(v, 3, dtype=np.int32)
    payload = {
        "artifact_schema_version": "paper0-vespagram-mask-v1",
        "vespagram": v,
        "support_counts": np.asarray(support, dtype=np.int32),
        "minimum_support": np.asarray(2, dtype=np.int32),
        "slowness_axis": s,
        "time_axis": t,
        "events": np.array(["S0001", "S0002", "S0003"], dtype=str),
        "distances": np.array([29.0, 30.0, 31.0], dtype=float),
        "distance_errors": (
            np.asarray(distance_errors, dtype=float)
            if distance_errors is not None
            else np.array([2.0, 2.0, 2.0], dtype=float)
        ),
        "mode": "paperfaith",
        "input_type": "waveform",
        "norm_variant": "C",
        "power_window_s": 20.0,
        "stack_method": "nth_root",
    }
    if extra_payload:
        payload.update(extra_payload)
    for field in omit_payload_fields:
        payload.pop(field, None)
    np.savez(path, **payload)


def _write_current_provenance_payload(
    path: Path,
    v: np.ndarray,
    s: np.ndarray,
    t: np.ndarray,
    tmp_path: Path,
    *,
    extra_payload: dict | None = None,
) -> None:
    trace = tmp_path / "S0001_trace.npy"
    mask = tmp_path / "S0001_mask.npy"
    time = tmp_path / "S0001_time.npy"
    norm = tmp_path / "S0001.normalization.json"
    align = tmp_path / "S0001.alignment.json"
    rotation = tmp_path / "S0001.rotation.json"
    locked = tmp_path / "alignment_locked_manifest.json"
    for p, content in [
        (trace, b"trace"),
        (mask, b"mask"),
        (time, b"time"),
        (norm, b"{}"),
        (align, b"{}"),
        (rotation, b"{}"),
        (locked, b"{}"),
    ]:
        p.write_bytes(content)
    sha = import_local_module("sha_for_vespagram_test", "scripts/shared.py").sha256_file
    payload = {
        "input_trace_paths": np.asarray([str(trace)], dtype=str),
        "input_trace_sha256": np.asarray([sha(trace)], dtype=str),
        "input_valid_sample_mask_paths": np.asarray([str(mask)], dtype=str),
        "input_valid_sample_mask_sha256": np.asarray([sha(mask)], dtype=str),
        "input_time_paths": np.asarray([str(time)], dtype=str),
        "input_time_sha256": np.asarray([sha(time)], dtype=str),
        "normalization_metadata_paths": np.asarray([str(norm)], dtype=str),
        "normalization_metadata_sha256": np.asarray([sha(norm)], dtype=str),
        "alignment_metadata_paths": np.asarray([str(align)], dtype=str),
        "alignment_metadata_sha256": np.asarray([sha(align)], dtype=str),
        "rotation_metadata_paths": np.asarray([str(rotation)], dtype=str),
        "rotation_metadata_sha256": np.asarray([sha(rotation)], dtype=str),
        "locked_pick_manifest_paths": np.asarray([str(locked)], dtype=str),
        "locked_pick_manifest_sha256": np.asarray([sha(locked)], dtype=str),
        "deglitch_run_summary_sha256": np.asarray(["nonempty-summary-hash"], dtype=str),
        "input_provenance_json": np.asarray(json.dumps([{"event_id": "S0001"}]), dtype=str),
    }
    if extra_payload:
        payload.update(extra_payload)
    _write_current_vespagram_payload(path, v, s, t, extra_payload=payload)


def _minimal_input_provenance(tmp_path: Path, operator: str) -> list[dict]:
    files = {}
    for name, content in {
        "trace": b"trace",
        "mask": b"mask",
        "time": b"time",
        "normalization": b"{}",
        "alignment": b"{}",
        "rotation": b"{}",
        "locked": b"{}",
    }.items():
        path = tmp_path / f"S0001_{name}"
        path.write_bytes(content)
        files[name] = path
    sha = import_local_module("sha_for_vespagram_operator_test", "scripts/shared.py").sha256_file
    return [
        {
            "trace_path": str(files["trace"]),
            "trace_sha256": sha(files["trace"]),
            "valid_sample_mask_path": str(files["mask"]),
            "valid_sample_mask_sha256": sha(files["mask"]),
            "time_path": str(files["time"]),
            "time_sha256": sha(files["time"]),
            "normalization_metadata_path": str(files["normalization"]),
            "normalization_metadata_sha256": sha(files["normalization"]),
            "alignment": {
                "metadata_path": str(files["alignment"]),
                "metadata_sha256": sha(files["alignment"]),
                "metadata": {
                    "locked_pick_manifest_path": str(files["locked"]),
                    "locked_pick_manifest_sha256": sha(files["locked"]),
                },
                "upstream": {
                    "operator": operator,
                    "metadata": {"operator": operator},
                    "rotation": {
                        "metadata_path": str(files["rotation"]),
                        "metadata_sha256": sha(files["rotation"]),
                        "metadata": {"deglitch_run_summary_sha256": "nonempty-summary-hash"},
                    },
                },
            },
        }
    ]


def test_compute_vespagram_shape_and_axis_contract():
    traces = [
        np.sin(np.linspace(0, 8, 2001)),
        np.zeros(2001),
        np.cos(np.linspace(0, 8, 2001)),
    ]
    distances = [29.0, 30.0, 31.0]
    t = np.linspace(-100, 2200, 2001)

    v, s, t_out, support = compute_vespagram(
        traces=traces,
        valid_masks=_all_valid_masks(traces),
        distances=distances,
        ref_distance=29.0,
        sampling_rate_hz=1.0 / (t[1] - t[0]),
        time_axis=t,
        slowness_min=-10.0,
        slowness_max=0.0,
        slowness_steps=11,
        stack_method="nth_root",
        n=4,
        power_window_s=5.0,
    )

    assert v.shape == (11, len(t))
    assert support.shape == v.shape
    assert np.nanmax(support) == 3
    assert s.shape == (11,)
    assert np.allclose(t_out, t)
    assert np.isfinite(v[support >= 2]).all()


def test_compute_vespagram_requires_valid_masks():
    with pytest.raises(ValueError, match="valid_masks"):
        compute_vespagram(
            traces=[np.zeros(10), np.ones(10)],
            distances=[29.0, 30.0],
            ref_distance=29.0,
            sampling_rate_hz=1.0,
            time_axis=np.arange(10),
            slowness_min=-1.0,
            slowness_max=0.0,
            slowness_steps=3,
            stack_method="linear",
        )


def test_compute_vespagram_rejects_unknown_method():
    with pytest.raises(ValueError, match="Unknown stack method"):
        compute_vespagram(
            traces=[np.zeros(10)],
            valid_masks=[np.ones(10, dtype=bool)],
            distances=[29.0],
            ref_distance=29.0,
            sampling_rate_hz=1.0,
            time_axis=np.arange(10),
            slowness_min=-10.0,
            slowness_max=0.0,
            slowness_steps=3,
            stack_method="not_a_method",
        )


def test_compute_vespagram_pws_defaults_to_order_one():
    traces = [np.sin(np.linspace(0, 6, 501)), np.cos(np.linspace(0, 6, 501))]
    distances = [29.0, 30.0]
    t = np.linspace(-10, 10, 501)

    masks = _all_valid_masks(traces)
    default_v, default_s, default_t, default_support = compute_vespagram(
        traces=traces,
        valid_masks=masks,
        distances=distances,
        ref_distance=29.0,
        sampling_rate_hz=1.0 / (t[1] - t[0]),
        time_axis=t,
        slowness_min=-2.0,
        slowness_max=0.0,
        slowness_steps=5,
        stack_method="pws",
        power_window_s=1.0,
    )
    explicit_v, explicit_s, explicit_t, explicit_support = compute_vespagram(
        traces=traces,
        valid_masks=masks,
        distances=distances,
        ref_distance=29.0,
        sampling_rate_hz=1.0 / (t[1] - t[0]),
        time_axis=t,
        slowness_min=-2.0,
        slowness_max=0.0,
        slowness_steps=5,
        stack_method="pws",
        pw_order=1,
        power_window_s=1.0,
    )

    assert np.allclose(default_v, explicit_v, equal_nan=True)
    assert np.allclose(default_s, explicit_s)
    assert np.allclose(default_t, explicit_t)
    assert np.array_equal(default_support, explicit_support)


def test_compute_vespagram_rejects_using_n_for_pws_order():
    with pytest.raises(ValueError, match="pw_order explicitly"):
        compute_vespagram(
            traces=[np.zeros(10), np.ones(10)],
            valid_masks=[np.ones(10, dtype=bool), np.ones(10, dtype=bool)],
            distances=[29.0, 30.0],
            ref_distance=29.0,
            sampling_rate_hz=1.0,
            time_axis=np.arange(10),
            slowness_min=-1.0,
            slowness_max=0.0,
            slowness_steps=3,
            stack_method="pws",
            n=2,
        )


def test_compute_vespagram_support_map_flags_shifted_padding():
    traces = [np.ones(8, dtype=float), np.ones(8, dtype=float)]
    masks = [
        np.ones(8, dtype=bool),
        np.array([True, True, True, True, False, False, False, False]),
    ]

    v, s, t, support = compute_vespagram(
        traces=traces,
        valid_masks=masks,
        distances=[29.0, 31.0],
        ref_distance=29.0,
        sampling_rate_hz=1.0,
        time_axis=np.arange(8, dtype=float),
        slowness_min=-1.0,
        slowness_max=-1.0,
        slowness_steps=1,
        stack_method="linear",
        power_window_s=1.0,
    )

    # The far trace rolls right by two samples; its valid mask rolls with it.
    assert np.array_equal(support[0], np.array([1, 1, 2, 2, 2, 2, 1, 1]))
    assert np.isnan(v[0, 0])
    assert np.isfinite(v[0, 2])


def test_padding_can_create_legacy_coherent_peak_but_mask_aware_path_excludes_it():
    sr = 1.0
    ref_distance = 29.0
    slowness = -2.0
    distances = [29.0, 30.0, 31.0]
    target_idx = 80
    npts = 140
    traces = []
    masks = []

    for distance in distances:
        roll = int(round(-slowness * (distance - ref_distance) * sr))
        source_idx = target_idx - roll
        trace = np.zeros(npts, dtype=float)
        mask = np.ones(npts, dtype=bool)
        # This value represents old normalized padding: zero-padded samples
        # converted into a constant nonzero value after unmasked z-scoring.
        trace[source_idx] = 6.0
        mask[source_idx] = False
        traces.append(trace)
        masks.append(mask)

    legacy_stack = np.zeros(npts, dtype=float)
    for trace, distance in zip(traces, distances, strict=True):
        roll = int(round(-slowness * (distance - ref_distance) * sr))
        legacy_stack += stacking.zero_padded_shift(trace, roll)
    legacy_stack /= len(traces)
    legacy_power_at_target = legacy_stack[target_idx] ** 2

    v, s, t, support = compute_vespagram(
        traces=traces,
        valid_masks=masks,
        distances=distances,
        ref_distance=ref_distance,
        sampling_rate_hz=sr,
        time_axis=np.arange(npts, dtype=float),
        slowness_min=slowness,
        slowness_max=slowness,
        slowness_steps=1,
        stack_method="linear",
        power_window_s=1.0,
    )

    assert legacy_power_at_target == pytest.approx(36.0)
    assert support[0, target_idx] == 0
    assert np.isnan(v[0, target_idx])
    assert s[0] == pytest.approx(slowness)
    assert t[target_idx] == pytest.approx(float(target_idx))


def test_detect_peak_labels_and_values(tmp_path):
    s = np.linspace(-10, 0, 41)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    # Put deterministic peaks for each expected report slot
    v[np.argmin(np.abs(s + 6.5)), np.argmin(np.abs(t - 604.0))] = 2.0
    v[np.argmin(np.abs(s + 8.0)), np.argmin(np.abs(t - 1290.0))] = 4.0
    v[np.argmin(np.abs(s + 6.0)), np.argmin(np.abs(t - 1341.0))] = 3.0
    v[np.argmin(np.abs(s + 7.0)), np.argmin(np.abs(t - 1338.0))] = 3.5

    out = tmp_path / "detect_case.npz"
    _write_current_vespagram_payload(out, v, s, t)

    rows, meta = detect(out)
    assert len(rows) == 5
    assert meta["mode"] == "paperfaith"
    assert meta["input_type"] == "waveform"
    assert meta["norm_variant"] == "C"
    assert meta["power_window_s"] == "20.0"
    assert set((phase, label) for phase, label, _, _, _ in rows) == {
        ("PKiKP", "global"),
        ("PKiKP", "published_target"),
        ("PKKP", "peak_1"),
        ("PKKP", "peak_2"),
        ("PKKP", "paper_target"),
    }

    peak_2 = [r for r in rows if r[0] == "PKKP" and r[1] == "peak_2"][0]
    assert peak_2[2] > 1200
    pkkp_target_diag = meta["diagnostics"][("PKKP", "paper_target")]
    assert pkkp_target_diag["local_max_neighbor_check"] is True
    assert pkkp_target_diag["target_box_rank"] >= 1
    pkikp_target_diag = meta["diagnostics"][("PKiKP", "published_target")]
    assert pkikp_target_diag["published_target_box"] == "PKIKP_PUBLISHED"
    assert pkikp_target_diag["box_supported_cell_fraction"] > 0.0


def test_detect_distinguishes_pkikp_global_from_published_target_box(tmp_path):
    s = np.linspace(-10, 0, 101)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    v[np.argmin(np.abs(s + 4.0)), np.argmin(np.abs(t - 666.0))] = 10.0
    v[np.argmin(np.abs(s + 6.5)), np.argmin(np.abs(t - 607.0))] = 4.0

    out = tmp_path / "pkikp_target_case.npz"
    _write_current_vespagram_payload(out, v, s, t, distance_errors=np.array([2.0, 2.0, 2.0]))

    rows, meta = detect(out)
    pkikp_global = [r for r in rows if r[0] == "PKiKP" and r[1] == "global"][0]
    pkikp_target = [r for r in rows if r[0] == "PKiKP" and r[1] == "published_target"][0]
    target_diag = meta["diagnostics"][("PKiKP", "published_target")]

    assert pkikp_global[2] == pytest.approx(666.0)
    assert pkikp_target[2] == pytest.approx(607.0)
    assert target_diag["target_box_rank"] > 1
    assert target_diag["box_occupancy_in_band"] > 0.0


def test_detect_parse_combo_extracts_window_from_method_filename(tmp_path):
    root = tmp_path / "results"
    method = root / "paperfaith" / "waveform" / "C" / "pws_nth_root_win20.npz"
    assert parse_combo_from_path(method, root) == (
        "paperfaith",
        "waveform",
        "C",
        "pws_nth_root",
        "20.0",
    )


def test_detect_parse_combo_with_fallback_for_unusual_method_name(tmp_path):
    root = tmp_path / "results"
    method = root / "paperfaith" / "waveform" / "C" / "pws_nth_root_20.npz"
    assert parse_combo_from_path(method, root) == (
        "paperfaith",
        "waveform",
        "C",
        "pws_nth_root",
        "20.0",
    )


def test_detect_run_emits_path_derived_meta_when_payload_missing(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    v[2, 1000] = 1.2

    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "C"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    np.savez(
        in_file,
        vespagram=v,
        slowness_axis=s,
        time_axis=t,
    )

    out_csv = tmp_path / "peak_comparison.csv"
    with pytest.raises(RuntimeError, match="blocked_missing_support_map"):
        run_detect(tmp_path / "results", out_csv)


def test_detect_run_emit_expected_schema(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    v[2, 1000] = 1.2

    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "C"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    _write_current_vespagram_payload(in_file, v, s, t)

    out_csv = tmp_path / "peak_comparison.csv"
    run_detect(tmp_path / "results", out_csv)

    with out_csv.open("r", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    expected = [
        "mode",
        "input_type",
        "norm_variant",
        "stack_method",
        "power_window_s",
        "phase",
        "peak_label",
        "time_s",
        "slowness_sdeg",
        "power",
        "support_count",
        "minimum_support",
        "status",
        "excluded_reason",
        "paper_time_s",
        "paper_slowness_sdeg",
        "dt_vs_paper_s",
        "ds_vs_paper_sdeg",
        "within_published_tolerance",
        "grid_coordinate_miss_norm",
        "median_distance_error_deg",
        "distance_uncertainty_moveout_s",
        "uncertainty_folded_time_tolerance_s",
        "within_uncertainty_folded_tolerance",
        "local_max_neighbor_check",
        "box_peak_background_quantile",
        "target_box_rank",
        "box_occupancy_in_band",
        "box_supported_cell_fraction",
        "normalization_lane",
        "current_provenance_status",
    ]
    assert set(expected).issubset(rows[0].keys())
    assert rows[0]["mode"] == "paperfaith"
    assert rows[0]["input_type"] == "waveform"
    assert rows[0]["norm_variant"] == "C"
    assert rows[0]["stack_method"] == "nth_root"
    assert rows[0]["power_window_s"] == "20.0"
    assert rows[0]["minimum_support"] == "2"


@pytest.mark.parametrize(
    ("field", "payload_value"),
    [
        ("mode", "ablation"),
        ("input_type", "envelope"),
        ("norm_variant", "A"),
        ("stack_method", "pws"),
        ("power_window_s", 5),
    ],
)
def test_detect_run_rejects_payload_path_lane_identity_mismatch(
    tmp_path,
    field,
    payload_value,
):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "C"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    _write_current_vespagram_payload(
        in_file,
        v,
        s,
        t,
        extra_payload={field: payload_value},
    )

    with pytest.raises(RuntimeError) as excinfo:
        run_detect(tmp_path / "results", tmp_path / "peak_comparison.csv")

    payload = json.loads(str(excinfo.value))
    assert payload["status"] == "blocked_lane_identity_mismatch"
    assert payload["path"] == str(in_file)
    assert f"field {field}" in payload["reason"]
    assert "payload value=" in payload["reason"]
    assert "path value=" in payload["reason"]


@pytest.mark.parametrize("field", detect_peaks.LANE_IDENTITY_FIELDS)
def test_detect_run_requires_each_payload_lane_identity_field_under_current_provenance(
    tmp_path,
    field,
):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "C"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    _write_current_provenance_payload(in_file, v, s, t, tmp_path)
    with np.load(in_file, allow_pickle=False) as current:
        payload = {key: current[key] for key in current.files if key != field}
    np.savez(in_file, **payload)

    with pytest.raises(RuntimeError) as excinfo:
        run_detect(
            tmp_path / "results",
            tmp_path / "peak_comparison.csv",
            require_current_provenance=True,
        )

    failure = json.loads(str(excinfo.value))
    assert failure["status"] == "blocked_missing_current_provenance"
    assert f"field {field}" in failure["reason"]


@pytest.mark.parametrize("field", detect_peaks.LANE_IDENTITY_FIELDS)
def test_detect_run_uses_path_fallback_for_missing_payload_lane_identity_when_not_strict(
    tmp_path,
    field,
):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "C"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    _write_current_vespagram_payload(
        in_file,
        v,
        s,
        t,
        omit_payload_fields=(field,),
    )

    out_csv = tmp_path / "peak_comparison.csv"
    run_detect(tmp_path / "results", out_csv)

    rows = list(csv.DictReader(out_csv.open("r", encoding="utf-8")))
    expected = {
        "mode": "paperfaith",
        "input_type": "waveform",
        "norm_variant": "C",
        "stack_method": "nth_root",
        "power_window_s": "20.0",
    }
    assert rows[0][field] == expected[field]


def test_detect_run_accepts_numeric_string_equivalent_power_window(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "C"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    _write_current_vespagram_payload(
        in_file,
        v,
        s,
        t,
        extra_payload={"power_window_s": "20.0"},
    )

    out_csv = tmp_path / "peak_comparison.csv"
    run_detect(tmp_path / "results", out_csv)

    rows = list(csv.DictReader(out_csv.open("r", encoding="utf-8")))
    assert rows[0]["power_window_s"] == "20.0"


def test_default_mk_operator_surfaces_from_vespagram_payload_to_detect_csv(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    v[2, 604] = 2.0
    support = np.full_like(v, 3, dtype=np.int32)

    payload_dir = tmp_path / "results" / "paperfaith" / "envelope" / "A"
    in_file = payload_dir / "nth_root_win20.npz"
    operator = "montalbetti_kanasewich_1970"
    run_vespagrams.write_vespagram_payload(
        in_file,
        vespagram=v,
        support_counts=support,
        slowness_axis=s,
        time_axis=t,
        meta={
            "event_ids": ["S0001"],
            "distances": [29.0],
            "distance_errors": [2.0],
            "mode": "paperfaith",
            "input_type": "envelope",
            "norm_variant": "A",
            "power_window_s": 20.0,
            "stack_method": "nth_root",
            "ref_distance": 29.0,
            "slowness_min": -10.0,
            "slowness_max": 0.0,
            "slowness_steps": 5,
            "sampling_rate_hz": 1.0,
            "minimum_support": 2,
            "input_provenance": _minimal_input_provenance(tmp_path, operator),
        },
    )

    with np.load(in_file, allow_pickle=False) as payload:
        assert payload["polarization_operator"].item() == operator
        assert payload["input_polarization_operators"].tolist() == [operator]

    out_csv = tmp_path / "peak_comparison.csv"
    run_detect(tmp_path / "results", out_csv)

    rows = list(csv.DictReader(out_csv.open("r", encoding="utf-8")))
    assert rows
    assert rows[0]["polarization_operator"] == operator


def test_detect_uncertainty_folded_consistency_keeps_grid_miss_separate(tmp_path):
    s = np.linspace(-10, 0, 101)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    v[np.argmin(np.abs(s + 6.5)), np.argmin(np.abs(t - 607.0))] = 3.0

    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "A"
    payload_dir.mkdir(parents=True)
    in_file = payload_dir / "nth_root_win20.npz"
    _write_current_vespagram_payload(
        in_file,
        v,
        s,
        t,
        distance_errors=np.array([2.0, 2.0, 2.0]),
        extra_payload={"norm_variant": "A"},
    )

    out_csv = tmp_path / "peak_comparison.csv"
    run_detect(tmp_path / "results", out_csv)

    rows = list(csv.DictReader(out_csv.open("r", encoding="utf-8")))
    pkikp_target = [row for row in rows if row["phase"] == "PKiKP" and row["peak_label"] == "published_target"][0]
    assert pkikp_target["within_published_tolerance"] == "False"
    assert pkikp_target["within_uncertainty_folded_tolerance"] == "True"
    assert float(pkikp_target["distance_uncertainty_moveout_s"]) == pytest.approx(13.0)
    assert pkikp_target["normalization_lane"] == "headline_targeted_window_eq1"


def test_detect_require_current_provenance_refuses_missing_hash_chain(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "A"
    payload_dir.mkdir(parents=True)
    _write_current_vespagram_payload(payload_dir / "nth_root_win20.npz", v, s, t)

    with pytest.raises(RuntimeError) as excinfo:
        run_detect(tmp_path / "results", tmp_path / "peak_comparison.csv", require_current_provenance=True)

    payload = json.loads(str(excinfo.value))
    assert payload["status"] == "blocked_missing_current_provenance"


def test_detect_require_current_provenance_accepts_hash_chain(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    payload_dir = tmp_path / "results" / "paperfaith" / "waveform" / "A"
    payload_dir.mkdir(parents=True)
    _write_current_provenance_payload(
        payload_dir / "nth_root_win20.npz",
        v,
        s,
        t,
        tmp_path,
        extra_payload={"norm_variant": "A"},
    )

    out_csv = tmp_path / "peak_comparison.csv"
    run_detect(tmp_path / "results", out_csv, require_current_provenance=True)

    rows = list(csv.DictReader(out_csv.open("r", encoding="utf-8")))
    assert rows[0]["current_provenance_status"] == "current"


def test_vespagram_sweep_registers_released_one_second_power_window_and_headline_variant():
    run_mod = import_local_module(
        "marsquake_run_vespagrams_contract_test",
        "scripts/03_vespagram/run_vespagrams.py",
    )

    assert run_mod.RELEASED_POWER_WINDOW_SAMPLES == 20
    assert run_mod.RELEASED_POWER_WINDOW_S == pytest.approx(1.0)
    assert run_mod.POWER_WINDOWS_S == (1.0, 5.0, 10.0, 20.0)
    assert run_mod.HEADLINE_NORMALIZATION_VARIANT == "A"


def test_detect_refuses_low_support_target_cells_with_machine_reason(tmp_path):
    s = np.linspace(-10, 0, 5)
    t = np.linspace(0, 2200, 2201)
    v = np.zeros((len(s), len(t)))
    support = np.zeros_like(v, dtype=np.int32)
    target_i = 2
    target_j = 604
    v[target_i, target_j] = 10.0
    support[target_i, target_j] = 1

    in_file = tmp_path / "low_support.npz"
    _write_current_vespagram_payload(in_file, v, s, t, support=support)

    rows, meta = detect(in_file)
    pkikp = [row for row in rows if row[0] == "PKiKP" and row[1] == "global"][0]
    diag = meta["diagnostics"][("PKiKP", "global")]
    assert pkikp[2] != pytest.approx(604.0)
    assert diag["status"] == "blocked_low_support"
    assert diag["excluded_reason"] == "no_finite_cells_meeting_minimum_support"
