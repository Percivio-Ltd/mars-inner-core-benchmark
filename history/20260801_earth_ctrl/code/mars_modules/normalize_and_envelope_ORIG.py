from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from obspy.signal.filter import envelope
from obspy import read

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import PAPERSTYLE_NORMALIZATION_REVISION, repo_path, sha256_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
NORMALIZATION_ARTIFACT_SCHEMA_VERSION = "paper0-normalized-mask-v1"
ENVELOPE_EDGE_EXCLUSION_S = 5.0


WINDOWS = {
    "A": (400.0, 800.0),
    "B": (1100.0, 1500.0),
    "C": (-100.0, 2200.0),
}


def window_indices(time_axis, t0, t1):
    i0 = np.searchsorted(time_axis, t0, side="left")
    i1 = np.searchsorted(time_axis, t1, side="right")
    return max(0, i0), min(len(time_axis), i1)


def _contiguous_true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    mask = np.asarray(mask, dtype=bool)
    if mask.size == 0:
        return []
    padded = np.concatenate(([False], mask, [False]))
    changes = np.flatnonzero(padded[1:] != padded[:-1])
    return [(int(changes[i]), int(changes[i + 1])) for i in range(0, len(changes), 2)]


def _erode_valid_mask(mask: np.ndarray, margin_samples: int) -> np.ndarray:
    mask = np.asarray(mask, dtype=bool)
    if margin_samples <= 0:
        return mask.copy()
    eroded = np.zeros_like(mask, dtype=bool)
    for lo, hi in _contiguous_true_runs(mask):
        inner_lo = lo + margin_samples
        inner_hi = hi - margin_samples
        if inner_hi > inner_lo:
            eroded[inner_lo:inner_hi] = True
    return eroded


def _masked_segment_envelope(values: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    env = np.zeros_like(values, dtype=np.float64)
    for lo, hi in _contiguous_true_runs(valid_mask):
        segment = values[lo:hi]
        if segment.size == 1:
            env[lo:hi] = np.abs(segment)
        elif segment.size > 1:
            env[lo:hi] = envelope(segment)
    return env


def _smooth_over_valid_support(values: np.ndarray, valid_mask: np.ndarray, smooth_n: int) -> np.ndarray:
    kernel_n = max(1, min(values.size, int(smooth_n)))
    kernel = np.ones(kernel_n, dtype=np.float64)
    numerator = np.convolve(np.where(valid_mask, values, 0.0), kernel, mode="same")
    denominator = np.convolve(valid_mask.astype(np.float64), kernel, mode="same")
    smoothed = np.zeros_like(values, dtype=np.float64)
    supported = denominator > 0.0
    smoothed[supported] = numerator[supported] / denominator[supported]
    return smoothed


def normalize_and_save(event_id: str, mode: str, input_path: Path, time_axis: np.ndarray, out_dir: Path):
    st = read(str(input_path))
    tr = st[0]
    data = np.asarray(tr.data, dtype=np.float64)
    if data.size == 0:
        raise ValueError(f"Empty aligned trace for {event_id}: {input_path}")
    sr = float(tr.stats.sampling_rate)
    n_times = len(data)
    if np.asarray(time_axis).shape == (n_times,):
        t = np.asarray(time_axis, dtype=np.float64)
    else:
        raise ValueError(f"Missing or mismatched alignment time axis for {event_id} {mode}")

    alignment_metadata = input_path.with_suffix(".alignment.json")
    if not alignment_metadata.exists():
        raise FileNotFoundError(f"Missing alignment metadata for normalization: {alignment_metadata}")
    valid_mask_path = out_dir / f"{event_id}_{mode}_valid_samples.npy"
    if not valid_mask_path.exists():
        raise FileNotFoundError(f"Missing alignment valid-sample mask for normalization: {valid_mask_path}")
    valid_mask = np.load(valid_mask_path).astype(bool)
    if valid_mask.shape != data.shape:
        raise ValueError(
            f"Valid-sample mask shape mismatch for {event_id} {mode}: "
            f"mask_shape={valid_mask.shape}, trace_shape={data.shape}"
        )
    if not np.any(valid_mask):
        raise ValueError(f"No valid samples available for normalization: {event_id} {mode}")

    for variant, (v0, v1) in WINDOWS.items():
        i0, i1 = window_indices(t, v0, v1)
        if i1 <= i0:
            raise ValueError(f"Empty declared normalization window for {event_id} variant {variant}")
        window_mask = np.zeros(n_times, dtype=bool)
        window_mask[i0:i1] = True
        norm_mask = window_mask & valid_mask
        if not np.any(norm_mask):
            raise ValueError(f"No valid samples in normalization window for {event_id} variant {variant}")
        seg = data[norm_mask]
        mu = float(np.mean(seg))
        sd = float(np.std(seg))
        if sd <= 0.0:
            raise ValueError(f"Zero-variance normalization window for {event_id} variant {variant}")
        normed = np.zeros(n_times, dtype=np.float64)
        normed[valid_mask] = (data[valid_mask] - mu) / sd
        smooth_n = max(1, int(round(5.0 * sr)))
        envelope_edge_exclusion_samples = max(0, int(round(ENVELOPE_EDGE_EXCLUSION_S * sr)))
        env_raw = _masked_segment_envelope(normed, valid_mask)
        env_smooth = _smooth_over_valid_support(env_raw, valid_mask, smooth_n)
        envelope_valid_mask = _erode_valid_mask(valid_mask, envelope_edge_exclusion_samples)
        env_smooth[~envelope_valid_mask] = 0.0

        mode_prefix = mode
        wv = out_dir / f"{event_id}_{mode_prefix}_{variant}_waveform.npy"
        ev = out_dir / f"{event_id}_{mode_prefix}_{variant}_envelope.npy"
        waveform_mask_path = out_dir / f"{event_id}_{mode_prefix}_{variant}_waveform_valid_samples.npy"
        envelope_mask_path = out_dir / f"{event_id}_{mode_prefix}_{variant}_envelope_valid_samples.npy"
        np.save(wv, normed.astype(np.float32))
        np.save(ev, env_smooth.astype(np.float32))
        np.save(waveform_mask_path, valid_mask.astype(bool))
        np.save(envelope_mask_path, envelope_valid_mask.astype(bool))
        time_path = out_dir / f"{event_id}_{mode_prefix}_{variant}_times.npy"
        np.save(time_path, t.astype(np.float64))
        metadata = {
            "artifact_schema_version": NORMALIZATION_ARTIFACT_SCHEMA_VERSION,
            "event_id": event_id,
            "mode": mode,
            "variant": variant,
            "method": "zscore_window_and_smoothed_envelope",
            "algorithm_revision": PAPERSTYLE_NORMALIZATION_REVISION,
            "input_aligned_trace": str(input_path),
            "input_aligned_sha256": sha256_file(input_path),
            "input_alignment_metadata_sha256": sha256_file(alignment_metadata),
            "input_valid_sample_mask": str(valid_mask_path),
            "input_valid_sample_mask_sha256": sha256_file(valid_mask_path),
            "waveform_sha256": sha256_file(wv),
            "envelope_sha256": sha256_file(ev),
            "waveform_valid_sample_mask": str(waveform_mask_path),
            "waveform_valid_sample_mask_sha256": sha256_file(waveform_mask_path),
            "envelope_valid_sample_mask": str(envelope_mask_path),
            "envelope_valid_sample_mask_sha256": sha256_file(envelope_mask_path),
            "time_axis_sha256": sha256_file(time_path),
            "normalization_window_s": [float(v0), float(v1)],
            "normalization_window_indices": [int(i0), int(i1)],
            "normalization_valid_sample_count": int(np.count_nonzero(norm_mask)),
            "trace_valid_sample_count": int(np.count_nonzero(valid_mask)),
            "waveform_valid_sample_count": int(np.count_nonzero(valid_mask)),
            "envelope_valid_sample_count": int(np.count_nonzero(envelope_valid_mask)),
            "invalid_sample_fill_value": 0.0,
            "envelope_hilbert_policy": "valid_contiguous_segments_then_masked_smoothing_and_edge_exclusion",
            "envelope_edge_exclusion_s": float(ENVELOPE_EDGE_EXCLUSION_S),
            "envelope_edge_exclusion_samples": int(envelope_edge_exclusion_samples),
            "sampling_rate_hz": sr,
            "npts": int(n_times),
        }
        (out_dir / f"{event_id}_{mode_prefix}_{variant}.normalization.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )

        logger.info("Wrote normalized outputs for %s (%s, %s)", event_id, mode, variant)


def parse_args():
    parser = argparse.ArgumentParser(description="Normalize + envelope generation")
    parser.add_argument("--in-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    for event_id_file in sorted(in_dir.glob("S*_aligned_*.mseed")):
        name = event_id_file.stem
        event_id, mode = name.split("_")[0], name.split("_")[2]
        time_axis = np.load(in_dir / f"{event_id}_{mode}_times.npy")
        normalize_and_save(event_id, mode, event_id_file, time_axis, out_dir)
