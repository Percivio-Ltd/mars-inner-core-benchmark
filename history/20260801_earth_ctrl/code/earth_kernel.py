"""P0-EARTH-CTRL kernel: Mars compute_vespagram with import mechanics adapted (lunar precedent:
"compute_vespagram differs in import mechanics only"). The stacking module is the byte-identical
copy in mars_modules/stacking.py. Function body below is copied verbatim from
scripts/03_vespagram/compute_vespagram.py (SHA in mars_modules/COPY_SHA256.txt); the only change
is the import block."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "mars_modules"))
import stacking as _stacking  # byte-identical copy

linear_stack = _stacking.linear_stack
nth_root_stack = _stacking.nth_root_stack
phase_weighted_stack = _stacking.phase_weighted_stack
DEFAULT_MIN_STACK_SUPPORT = _stacking.DEFAULT_MIN_STACK_SUPPORT


def compute_vespagram(
    traces,
    distances,
    ref_distance,
    sampling_rate_hz,
    time_axis,
    slowness_min,
    slowness_max,
    slowness_steps,
    stack_method="nth_root",
    n=4,
    pw_order=None,
    power_window_s=20.0,
    valid_masks=None,
    min_support=DEFAULT_MIN_STACK_SUPPORT,
):
    if valid_masks is None:
        raise ValueError("valid_masks are required for mask-aware vespagram computation")
    slowness_axis = np.linspace(slowness_min, slowness_max, slowness_steps)
    n_times = len(traces[0])
    time_axis = np.asarray(time_axis, dtype=np.float64)
    if time_axis.shape != (n_times,):
        raise ValueError("time_axis shape must match trace length")
    vespagram = np.full((slowness_steps, n_times), np.nan, dtype=np.float64)
    support_counts = np.zeros((slowness_steps, n_times), dtype=np.int32)

    for si, s in enumerate(slowness_axis):
        if stack_method == "linear":
            beam, support = linear_stack(
                traces,
                distances,
                ref_distance,
                s,
                sampling_rate_hz,
                valid_masks=valid_masks,
                min_support=min_support,
                return_support=True,
            )
        elif stack_method == "nth_root":
            beam, support = nth_root_stack(
                traces,
                distances,
                ref_distance,
                s,
                sampling_rate_hz,
                n=n,
                valid_masks=valid_masks,
                min_support=min_support,
                return_support=True,
            )
        elif stack_method == "pws":
            if pw_order is None and n != 4:
                raise ValueError("For stack_method='pws', use pw_order explicitly; n only applies to nth_root stacking.")
            beam, support = phase_weighted_stack(
                traces,
                distances,
                ref_distance,
                s,
                sampling_rate_hz,
                pw_order=1 if pw_order is None else pw_order,
                valid_masks=valid_masks,
                min_support=min_support,
                return_support=True,
            )
        else:
            raise ValueError(f"Unknown stack method: {stack_method}")
        support_counts[si] = support

        win_samples = max(1, min(n_times, int(round(power_window_s * sampling_rate_hz))))
        hann = np.hanning(win_samples)
        if not np.any(hann):
            hann = np.ones(win_samples, dtype=np.float64)
        supported = (support >= int(min_support)) & np.isfinite(beam)
        raw_power = np.where(supported, beam**2, 0.0)
        weight = np.convolve(supported.astype(np.float64), hann, mode="same")
        numerator = np.convolve(raw_power, hann, mode="same")
        power = np.full(n_times, np.nan, dtype=np.float64)
        valid_power = supported & (weight > 0.0)
        power[valid_power] = numerator[valid_power] / weight[valid_power]
        vespagram[si] = power

    return vespagram, slowness_axis, time_axis, support_counts


# --- envelope helpers, copied verbatim from scripts/02_preprocess/normalize_and_envelope.py ---
from obspy.signal.filter import envelope  # noqa: E402

ENVELOPE_EDGE_EXCLUSION_S = 5.0


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


def normalize_variant(data, valid_mask, time_axis, v0, v1, sr):
    """z-score + smoothed envelope for one normalization window; semantics copied verbatim
    from normalize_and_save (normalize_and_envelope.py:109-130)."""
    n_times = len(data)
    i0, i1 = window_indices(time_axis, v0, v1)
    if i1 <= i0:
        raise ValueError("Empty declared normalization window")
    window_mask = np.zeros(n_times, dtype=bool)
    window_mask[i0:i1] = True
    norm_mask = window_mask & valid_mask
    if not np.any(norm_mask):
        raise ValueError("No valid samples in normalization window")
    seg = data[norm_mask]
    mu = float(np.mean(seg))
    sd = float(np.std(seg))
    if sd <= 0.0:
        raise ValueError("Zero-variance normalization window")
    normed = np.zeros(n_times, dtype=np.float64)
    normed[valid_mask] = (data[valid_mask] - mu) / sd
    smooth_n = max(1, int(round(5.0 * sr)))
    envelope_edge_exclusion_samples = max(0, int(round(ENVELOPE_EDGE_EXCLUSION_S * sr)))
    env_raw = _masked_segment_envelope(normed, valid_mask)
    env_smooth = _smooth_over_valid_support(env_raw, valid_mask, smooth_n)
    envelope_valid_mask = _erode_valid_mask(valid_mask, envelope_edge_exclusion_samples)
    env_smooth[~envelope_valid_mask] = 0.0
    return normed, env_smooth, envelope_valid_mask


# --- local-max check, copied verbatim from scripts/03_vespagram/detect_peaks.py:207-216 ---
def _is_local_maximum(data: np.ndarray, slow_idx: int, time_idx: int) -> bool:
    if slow_idx < 0 or time_idx < 0:
        return False
    if not np.isfinite(data[slow_idx, time_idx]):
        return False
    i0 = max(0, slow_idx - 1)
    i1 = min(data.shape[0], slow_idx + 2)
    j0 = max(0, time_idx - 1)
    j1 = min(data.shape[1], time_idx + 2)
    return bool(data[slow_idx, time_idx] >= np.nanmax(data[i0:i1, j0:j1]))


def box_peak_local_max(vespagram, slowness_axis, time_axis, box):
    """Peak inside a (t,p) box of the non-bootstrap vespagram + 3x3 local-max check.
    box = (t_min, t_max, p_min, p_max). Returns (found, local_max_ok, t, p, power)."""
    m = (
        (slowness_axis[:, None] >= box[2]) & (slowness_axis[:, None] <= box[3])
        & (time_axis[None, :] >= box[0]) & (time_axis[None, :] <= box[1])
    )
    sub = np.where(m & np.isfinite(vespagram), vespagram, -np.inf)
    if not np.any(np.isfinite(sub) & (sub > -np.inf)):
        return False, False, float("nan"), float("nan"), float("nan")
    i, j = np.unravel_index(np.argmax(sub), sub.shape)
    ok = _is_local_maximum(vespagram, int(i), int(j))
    return True, ok, float(time_axis[j]), float(slowness_axis[i]), float(vespagram[i, j])
