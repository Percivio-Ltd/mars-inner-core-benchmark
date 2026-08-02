from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts.shared import (
    ABLATION_BANDPASS_REVISION,
    PAPERSTYLE_ALIGNMENT_REVISION,
    PAPERSTYLE_ALGORITHM_REVISION,
    PAPERSTYLE_NORMALIZATION_REVISION,
    ROTATION_ZNE_REVISION,
    import_local_module,
    sha256_file,
)

NORMALIZATION_WINDOWS = {
    "A": (400.0, 800.0),
    "B": (1100.0, 1500.0),
    "C": (-100.0, 2200.0),
}
NORMALIZATION_ARTIFACT_SCHEMA_VERSION = "paper0-normalized-mask-v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_rotation_products(event_id: str, data_dir: Path) -> dict[str, Any]:
    zne_path = data_dir / f"{event_id}_ZNE.mseed"
    metadata_path = zne_path.with_suffix(".rotation.json")
    missing = [path.name for path in (zne_path, metadata_path) if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing current rotation provenance for {event_id}: {', '.join(missing)}")
    metadata = _read_json(metadata_path)
    if metadata.get("method") != "uvw_to_zne_nominal_seis_vbb":
        raise RuntimeError(f"Stale rotation provenance for {event_id}: method mismatch")
    if metadata.get("algorithm_revision") != ROTATION_ZNE_REVISION:
        raise RuntimeError(f"Stale rotation provenance for {event_id}: algorithm_revision mismatch")
    if metadata.get("output_zne_sha256") != sha256_file(zne_path):
        raise RuntimeError(f"Stale rotation provenance for {event_id}: output ZNE hash mismatch")
    if not metadata.get("deglitch_run_summary_sha256"):
        raise RuntimeError(f"Stale rotation provenance for {event_id}: missing deglitch run summary hash")
    return {
        "path": str(zne_path),
        "sha256": sha256_file(zne_path),
        "metadata_path": str(metadata_path),
        "metadata_sha256": sha256_file(metadata_path),
        "metadata": metadata,
    }


def validate_ablation_bandpass_products(event_id: str, data_dir: Path) -> dict[str, Any]:
    rotation = validate_rotation_products(event_id, data_dir)
    source_path = data_dir / f"{event_id}_ZNE.mseed"
    trace_path = data_dir / f"{event_id}_Z_filt.mseed"
    metadata_path = trace_path.with_suffix(".bandpass.json")
    missing = [path.name for path in (source_path, trace_path, metadata_path) if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing current ablation bandpass provenance for {event_id}: {', '.join(missing)}")
    metadata = _read_json(metadata_path)
    if metadata.get("method") != "zero_phase_bhz_bandpass":
        raise RuntimeError(f"Stale ablation bandpass provenance for {event_id}: method mismatch")
    if metadata.get("algorithm_revision") != ABLATION_BANDPASS_REVISION:
        raise RuntimeError(f"Stale ablation bandpass provenance for {event_id}: algorithm_revision mismatch")
    if metadata.get("source_zne_sha256") != sha256_file(source_path):
        raise RuntimeError(f"Stale ablation bandpass provenance for {event_id}: source ZNE hash mismatch")
    if metadata.get("output_trace_sha256") != sha256_file(trace_path):
        raise RuntimeError(f"Stale ablation bandpass provenance for {event_id}: output trace hash mismatch")
    if not np.allclose(np.asarray(metadata.get("bandpass_hz"), dtype=np.float64), np.array([0.2, 0.8]), rtol=0.0, atol=1e-6):
        raise RuntimeError(f"Stale ablation bandpass provenance for {event_id}: bandpass_hz mismatch")
    return {
        "path": str(trace_path),
        "sha256": sha256_file(trace_path),
        "metadata_path": str(metadata_path),
        "metadata_sha256": sha256_file(metadata_path),
        "metadata": metadata,
        "rotation": rotation,
    }


def validate_paperstyle_polarization_products(event_id: str, data_dir: Path) -> dict[str, Any]:
    rotation = validate_rotation_products(event_id, data_dir)
    align_mod = import_local_module(
        "marsquake_paper0_align_for_provenance",
        "scripts/02_preprocess/align_and_cut.py",
    )
    align_mod.validate_paperstyle_polarization_products(event_id, data_dir)
    trace_path = data_dir / f"{event_id}_Z_polfilt.mseed"
    metadata_path = data_dir / f"{event_id}_Z_polfilt.polarization.json"
    filterbank_path = data_dir / f"{event_id}_mk_filterbank.npz"
    fdpa_path = data_dir / f"{event_id}_fdpa.npz"
    metadata = _read_json(metadata_path)
    return {
        "path": str(trace_path),
        "sha256": sha256_file(trace_path),
        "metadata_path": str(metadata_path),
        "metadata_sha256": sha256_file(metadata_path),
        "metadata": metadata,
        "operator": str(metadata.get("operator", "")),
        "filterbank_path": str(filterbank_path),
        "filterbank_sha256": sha256_file(filterbank_path),
        "fdpa_path": str(fdpa_path),
        "fdpa_sha256": sha256_file(fdpa_path),
        "rotation": rotation,
    }


def validate_alignment_products(event_id: str, data_dir: Path, mode: str) -> dict[str, Any]:
    aligned_path = data_dir / f"{event_id}_aligned_{mode}.mseed"
    aligned_time_path = data_dir / f"{event_id}_{mode}_times.npy"
    alignment_metadata_path = aligned_path.with_suffix(".alignment.json")
    missing = [path.name for path in (aligned_path, aligned_time_path, alignment_metadata_path) if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing current alignment provenance for {event_id}: {', '.join(missing)}")

    metadata = _read_json(alignment_metadata_path)
    if metadata.get("algorithm_revision") != PAPERSTYLE_ALIGNMENT_REVISION:
        raise RuntimeError(f"Stale alignment provenance for {event_id}: algorithm_revision mismatch")
    if metadata.get("mode") != mode:
        raise RuntimeError(f"Stale alignment provenance for {event_id}: mode mismatch")
    if metadata.get("output_trace_sha256") != sha256_file(aligned_path):
        raise RuntimeError(f"Stale alignment provenance for {event_id}: aligned trace hash mismatch")
    if metadata.get("time_axis_sha256") != sha256_file(aligned_time_path):
        raise RuntimeError(f"Stale alignment provenance for {event_id}: time axis hash mismatch")

    valid_mask_path = data_dir / f"{event_id}_{mode}_valid_samples.npy"
    if not metadata.get("valid_sample_mask_sha256"):
        raise RuntimeError(f"Stale alignment provenance for {event_id}: missing valid-sample mask hash")
    if not valid_mask_path.exists():
        raise RuntimeError(f"Missing alignment valid-sample mask for {event_id}: {valid_mask_path.name}")
    if metadata["valid_sample_mask_sha256"] != sha256_file(valid_mask_path):
        raise RuntimeError(f"Stale alignment provenance for {event_id}: valid-sample mask hash mismatch")

    upstream: dict[str, Any]
    if mode == "paperfaith":
        pol = validate_paperstyle_polarization_products(event_id, data_dir)
        upstream = pol
        if metadata.get("paperstyle_algorithm_revision") != PAPERSTYLE_ALGORITHM_REVISION:
            raise RuntimeError(f"Stale alignment provenance for {event_id}: paperstyle_algorithm_revision mismatch")
        expected = {
            "input_trace_sha256": pol["sha256"],
            "polarization_metadata_sha256": pol["metadata_sha256"],
            "filterbank_sha256": pol["filterbank_sha256"],
            "fdpa_sha256": pol["fdpa_sha256"],
        }
        for key, expected_hash in expected.items():
            if metadata.get(key) != expected_hash:
                raise RuntimeError(f"Stale alignment provenance for {event_id}: {key} mismatch")
    elif mode == "ablation":
        bandpass = validate_ablation_bandpass_products(event_id, data_dir)
        upstream = bandpass
        if metadata.get("input_trace_sha256") != bandpass["sha256"]:
            raise RuntimeError(f"Stale alignment provenance for {event_id}: ablation source trace hash mismatch")
    else:
        raise RuntimeError(f"Unknown Paper0 alignment mode for {event_id}: {mode}")

    return {
        "path": str(aligned_path),
        "sha256": sha256_file(aligned_path),
        "time_path": str(aligned_time_path),
        "time_sha256": sha256_file(aligned_time_path),
        "metadata_path": str(alignment_metadata_path),
        "metadata_sha256": sha256_file(alignment_metadata_path),
        "valid_sample_mask_path": str(valid_mask_path) if valid_mask_path.exists() else "",
        "valid_sample_mask_sha256": sha256_file(valid_mask_path) if valid_mask_path.exists() else "",
        "metadata": metadata,
        "upstream": upstream,
    }


def validate_normalized_products(
    event_id: str,
    data_dir: Path,
    mode: str,
    variant: str,
    input_type: str,
) -> dict[str, Any]:
    if variant not in NORMALIZATION_WINDOWS:
        raise RuntimeError(f"Unknown normalization variant for {event_id}: {variant}")
    if input_type not in {"waveform", "envelope"}:
        raise RuntimeError(f"Unknown normalized input type for {event_id}: {input_type}")

    alignment = validate_alignment_products(event_id, data_dir, mode)
    trace_path = data_dir / f"{event_id}_{mode}_{variant}_{input_type}.npy"
    time_path = data_dir / f"{event_id}_{mode}_{variant}_times.npy"
    metadata_path = data_dir / f"{event_id}_{mode}_{variant}.normalization.json"
    missing = [path.name for path in (trace_path, time_path, metadata_path) if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing current normalization provenance for {event_id}: {', '.join(missing)}")

    metadata = _read_json(metadata_path)
    if metadata.get("artifact_schema_version") != NORMALIZATION_ARTIFACT_SCHEMA_VERSION:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: artifact_schema_version mismatch")
    if metadata.get("method") != "zscore_window_and_smoothed_envelope":
        raise RuntimeError(f"Stale normalization provenance for {event_id}: method mismatch")
    if metadata.get("algorithm_revision") != PAPERSTYLE_NORMALIZATION_REVISION:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: algorithm_revision mismatch")
    for key, expected in {"event_id": event_id, "mode": mode, "variant": variant}.items():
        if metadata.get(key) != expected:
            raise RuntimeError(f"Stale normalization provenance for {event_id}: {key} mismatch")
    if not np.allclose(
        np.asarray(metadata.get("normalization_window_s"), dtype=np.float64),
        np.asarray(NORMALIZATION_WINDOWS[variant], dtype=np.float64),
        rtol=0.0,
        atol=1e-6,
    ):
        raise RuntimeError(f"Stale normalization provenance for {event_id}: normalization_window_s mismatch")
    if metadata.get("input_aligned_sha256") != alignment["sha256"]:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: aligned input hash mismatch")
    if metadata.get("input_alignment_metadata_sha256") != alignment["metadata_sha256"]:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: alignment metadata hash mismatch")
    if metadata.get("input_valid_sample_mask_sha256") != alignment["valid_sample_mask_sha256"]:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: valid-sample mask hash mismatch")
    if metadata.get(f"{input_type}_sha256") != sha256_file(trace_path):
        raise RuntimeError(f"Stale normalization provenance for {event_id}: {input_type} hash mismatch")
    mask_path = data_dir / f"{event_id}_{mode}_{variant}_{input_type}_valid_samples.npy"
    mask_hash_key = f"{input_type}_valid_sample_mask_sha256"
    if not mask_path.exists():
        raise RuntimeError(f"Missing normalized valid-sample mask for {event_id}: {mask_path.name}")
    if metadata.get(mask_hash_key) != sha256_file(mask_path):
        raise RuntimeError(f"Stale normalization provenance for {event_id}: {input_type} valid-sample mask hash mismatch")
    trace = np.load(trace_path, allow_pickle=False)
    valid_mask = np.load(mask_path, allow_pickle=False).astype(bool)
    if trace.shape != valid_mask.shape:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: {input_type} valid-sample mask shape mismatch")
    if np.any(np.asarray(trace)[~valid_mask] != 0.0):
        raise RuntimeError(f"Stale normalization provenance for {event_id}: nonzero values outside {input_type} valid-sample mask")
    if metadata.get("time_axis_sha256") != sha256_file(time_path):
        raise RuntimeError(f"Stale normalization provenance for {event_id}: time-axis hash mismatch")
    if int(metadata.get("normalization_valid_sample_count", 0)) <= 0:
        raise RuntimeError(f"Stale normalization provenance for {event_id}: no valid normalization samples recorded")
    return {
        "event_id": event_id,
        "mode": mode,
        "variant": variant,
        "input_type": input_type,
        "trace_path": str(trace_path),
        "trace_sha256": sha256_file(trace_path),
        "valid_sample_mask_path": str(mask_path),
        "valid_sample_mask_sha256": sha256_file(mask_path),
        "valid_sample_count": int(np.count_nonzero(valid_mask)),
        "time_path": str(time_path),
        "time_sha256": sha256_file(time_path),
        "normalization_metadata_path": str(metadata_path),
        "normalization_metadata_sha256": sha256_file(metadata_path),
        "alignment": alignment,
        "normalization_metadata": metadata,
    }
