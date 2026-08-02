from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from obspy import Stream, Trace

from scripts.shared import (
    PAPERSTYLE_ALIGNMENT_REVISION,
    import_local_module,
    sha256_file,
)

normalize_mod = import_local_module(
    "marsquake_normalize_mask_test",
    "scripts/02_preprocess/normalize_and_envelope.py",
)
normalize_and_save = normalize_mod.normalize_and_save
paper0_provenance = import_local_module(
    "marsquake_paper0_provenance_mask_test",
    "scripts/paper0_provenance.py",
)


def _write_trace(path: Path, data: np.ndarray, sampling_rate_hz: float = 20.0) -> None:
    trace = Trace(data=np.asarray(data, dtype=np.float32))
    trace.stats.sampling_rate = sampling_rate_hz
    path.parent.mkdir(parents=True, exist_ok=True)
    Stream([trace]).write(str(path), format="MSEED")


def _write_alignment_contract(path: Path, event_id: str, mode: str, out_dir: Path, time_axis: np.ndarray, valid_mask: np.ndarray) -> None:
    time_path = out_dir / f"{event_id}_{mode}_times.npy"
    mask_path = out_dir / f"{event_id}_{mode}_valid_samples.npy"
    np.save(time_path, np.asarray(time_axis, dtype=np.float64))
    np.save(mask_path, np.asarray(valid_mask, dtype=bool))
    path.with_suffix(".alignment.json").write_text(
        json.dumps(
            {
                "event_id": event_id,
                "mode": mode,
                "algorithm_revision": PAPERSTYLE_ALIGNMENT_REVISION,
                "output_trace_sha256": sha256_file(path),
                "time_axis_sha256": sha256_file(time_path),
                "valid_sample_mask_sha256": sha256_file(mask_path),
                "sampling_rate_hz": 20.0,
                "npts": int(valid_mask.size),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_normalization_outputs_first_class_masks_and_neutral_invalid_samples(tmp_path):
    event_id = "S0999x"
    mode = "ablation"
    npts = 1200
    time_axis = np.linspace(-100.0, 2200.0, npts)
    valid_mask = np.ones(npts, dtype=bool)
    valid_mask[:100] = False
    valid_mask[1100:] = False

    data = np.zeros(npts, dtype=np.float32)
    data[valid_mask] = 2.0 + np.sin(np.linspace(0.0, 12.0 * np.pi, int(np.count_nonzero(valid_mask))))
    in_path = tmp_path / f"{event_id}_{mode}.mseed"
    _write_trace(in_path, data)
    _write_alignment_contract(in_path, event_id, mode, tmp_path, time_axis, valid_mask)

    normalize_and_save(event_id, mode, in_path, time_axis, tmp_path)

    waveform = np.load(tmp_path / f"{event_id}_{mode}_C_waveform.npy")
    envelope = np.load(tmp_path / f"{event_id}_{mode}_C_envelope.npy")
    waveform_mask = np.load(tmp_path / f"{event_id}_{mode}_C_waveform_valid_samples.npy")
    envelope_mask = np.load(tmp_path / f"{event_id}_{mode}_C_envelope_valid_samples.npy")
    metadata = json.loads((tmp_path / f"{event_id}_{mode}_C.normalization.json").read_text(encoding="utf-8"))

    assert np.array_equal(waveform_mask, valid_mask)
    assert np.all(waveform[~waveform_mask] == 0.0)
    assert np.all(envelope[~envelope_mask] == 0.0)
    assert metadata["artifact_schema_version"] == "paper0-normalized-mask-v1"
    assert metadata["waveform_valid_sample_mask_sha256"] == sha256_file(tmp_path / f"{event_id}_{mode}_C_waveform_valid_samples.npy")
    assert metadata["envelope_valid_sample_mask_sha256"] == sha256_file(tmp_path / f"{event_id}_{mode}_C_envelope_valid_samples.npy")


def test_envelope_edge_exclusion_policy_quantifies_hilbert_boundary_margin(tmp_path):
    event_id = "S0998x"
    mode = "ablation"
    npts = 1200
    time_axis = np.linspace(-100.0, 2200.0, npts)
    valid_mask = np.zeros(npts, dtype=bool)
    valid_mask[100:1100] = True

    data = np.zeros(npts, dtype=np.float32)
    data[valid_mask] = 2.0 + np.cos(np.linspace(0.0, 8.0 * np.pi, int(np.count_nonzero(valid_mask))))
    in_path = tmp_path / f"{event_id}_{mode}.mseed"
    _write_trace(in_path, data)
    _write_alignment_contract(in_path, event_id, mode, tmp_path, time_axis, valid_mask)

    normalize_and_save(event_id, mode, in_path, time_axis, tmp_path)

    envelope_mask = np.load(tmp_path / f"{event_id}_{mode}_C_envelope_valid_samples.npy")
    metadata = json.loads((tmp_path / f"{event_id}_{mode}_C.normalization.json").read_text(encoding="utf-8"))
    expected = np.zeros(npts, dtype=bool)
    expected[200:1000] = True

    assert metadata["envelope_edge_exclusion_s"] == 5.0
    assert metadata["envelope_edge_exclusion_samples"] == 100
    assert np.array_equal(envelope_mask, expected)
    assert np.count_nonzero(valid_mask & ~envelope_mask) == 200


def test_normalization_provenance_rejects_legacy_maskless_outputs(tmp_path, monkeypatch):
    event_id = "S0997x"
    mode = "ablation"
    variant = "C"
    input_type = "waveform"
    npts = 20

    trace_path = tmp_path / f"{event_id}_{mode}_{variant}_{input_type}.npy"
    time_path = tmp_path / f"{event_id}_{mode}_{variant}_times.npy"
    metadata_path = tmp_path / f"{event_id}_{mode}_{variant}.normalization.json"
    np.save(trace_path, np.ones(npts, dtype=np.float32))
    np.save(time_path, np.arange(npts, dtype=np.float64))
    metadata_path.write_text(
        json.dumps(
            {
                "event_id": event_id,
                "mode": mode,
                "variant": variant,
                "method": "zscore_window_and_smoothed_envelope",
                "algorithm_revision": "paper0-zscore-envelope-v2",
                "normalization_window_s": [-100.0, 2200.0],
                "normalization_valid_sample_count": npts,
                "waveform_sha256": sha256_file(trace_path),
                "time_axis_sha256": sha256_file(time_path),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        paper0_provenance,
        "validate_alignment_products",
        lambda event_id_arg, data_dir_arg, mode_arg: {
            "sha256": "aligned-sha",
            "metadata_sha256": "alignment-metadata-sha",
            "valid_sample_mask_sha256": "input-mask-sha",
        },
    )

    with pytest.raises(RuntimeError, match="artifact_schema_version"):
        paper0_provenance.validate_normalized_products(event_id, tmp_path, mode, variant, input_type)
