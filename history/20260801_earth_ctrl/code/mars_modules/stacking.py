from __future__ import annotations

import numpy as np
from scipy.signal import hilbert

DEFAULT_MIN_STACK_SUPPORT = 2


def zero_padded_shift(trace, roll_samples):
    """
    Shift a trace by roll_samples, filling vacated positions with zeros.
    Positive roll_samples = shift toward later times (right).
    Negative roll_samples = shift toward earlier times (left).
    Unlike np.roll(), this does NOT wrap around.
    """
    n = len(trace)
    result = np.zeros(n, dtype=np.asarray(trace).dtype)
    if roll_samples == 0:
        result[:] = trace
    elif roll_samples > 0:
        if roll_samples < n:
            result[roll_samples:] = trace[: n - roll_samples]
    else:
        rs = -roll_samples
        if rs < n:
            result[: n - rs] = trace[rs:]
    return result


def _validate_traces_and_masks(traces, valid_masks=None):
    trace_arrays = [np.asarray(trace, dtype=np.float64) for trace in traces]
    if not trace_arrays:
        raise ValueError("At least one trace is required")
    length = trace_arrays[0].shape[0]
    if any(trace.ndim != 1 for trace in trace_arrays):
        raise ValueError("All traces must be 1D arrays")
    if any(trace.shape != (length,) for trace in trace_arrays):
        raise ValueError("All traces must have equal lengths")

    if valid_masks is None:
        mask_arrays = [np.ones(length, dtype=bool) for _ in trace_arrays]
    else:
        mask_arrays = [np.asarray(mask, dtype=bool) for mask in valid_masks]
        if len(mask_arrays) != len(trace_arrays):
            raise ValueError("valid_masks must have the same length as traces")
        if any(mask.ndim != 1 for mask in mask_arrays):
            raise ValueError("All valid masks must be 1D arrays")
        if any(mask.shape != (length,) for mask in mask_arrays):
            raise ValueError("valid mask shape mismatch")
    return trace_arrays, mask_arrays, length


def _validate_distances(distances, n_traces):
    distance_array = np.asarray(distances, dtype=np.float64)
    if distance_array.shape != (n_traces,):
        raise ValueError("distances must have the same length as traces")
    return distance_array


def _support_threshold(min_support):
    threshold = int(min_support)
    if threshold < 1:
        raise ValueError("min_support must be at least 1")
    return threshold


def _roll_for(distance, ref_distance, slowness_sdeg, sampling_rate_hz):
    return int(round(-slowness_sdeg * (distance - ref_distance) * sampling_rate_hz))


def _finalize_stack(accum, support, min_support):
    threshold = _support_threshold(min_support)
    out = np.full(accum.shape, np.nan, dtype=np.float64)
    valid = support >= threshold
    out[valid] = accum[valid] / support[valid]
    return out


def _return_stack(stack, support, return_support):
    if return_support:
        return stack, support.astype(np.int32, copy=False)
    return stack


def zero_padded_shifted_stack_index(distances, ref_distance, slowness_sdeg, sampling_rate_hz):
    distance_delta = np.asarray(distances) - ref_distance
    rolls = np.rint(-slowness_sdeg * distance_delta * sampling_rate_hz).astype(int)
    if rolls.size == 1:
        return int(rolls.item())
    return rolls


def linear_stack(
    traces,
    distances,
    ref_distance,
    slowness_sdeg,
    sampling_rate_hz,
    *,
    valid_masks=None,
    min_support=DEFAULT_MIN_STACK_SUPPORT,
    return_support=False,
):
    trace_arrays, mask_arrays, length = _validate_traces_and_masks(traces, valid_masks)
    distance_array = _validate_distances(distances, len(trace_arrays))
    accum = np.zeros(length, dtype=np.float64)
    support = np.zeros(length, dtype=np.int32)
    for trace, mask, distance in zip(trace_arrays, mask_arrays, distance_array, strict=True):
        roll = _roll_for(distance, ref_distance, slowness_sdeg, sampling_rate_hz)
        shifted = zero_padded_shift(trace, roll)
        shifted_mask = zero_padded_shift(mask, roll).astype(bool)
        accum[shifted_mask] += shifted[shifted_mask]
        support += shifted_mask.astype(np.int32)
    stack = _finalize_stack(accum, support, min_support)
    return _return_stack(stack, support, return_support)


def nth_root_stack(
    traces,
    distances,
    ref_distance,
    slowness_sdeg,
    sampling_rate_hz,
    n=4,
    *,
    valid_masks=None,
    min_support=DEFAULT_MIN_STACK_SUPPORT,
    return_support=False,
):
    if n <= 0:
        raise ValueError("n must be positive")
    trace_arrays, mask_arrays, length = _validate_traces_and_masks(traces, valid_masks)
    distance_array = _validate_distances(distances, len(trace_arrays))
    accum = np.zeros(length, dtype=np.float64)
    support = np.zeros(length, dtype=np.int32)
    for trace, mask, distance in zip(trace_arrays, mask_arrays, distance_array, strict=True):
        roll = _roll_for(distance, ref_distance, slowness_sdeg, sampling_rate_hz)
        shifted = zero_padded_shift(trace, roll)
        shifted_mask = zero_padded_shift(mask, roll).astype(bool)
        root = np.sign(shifted) * np.abs(shifted) ** (1.0 / n)
        accum[shifted_mask] += root[shifted_mask]
        support += shifted_mask.astype(np.int32)
    averaged = _finalize_stack(accum, support, min_support)
    stack = np.full_like(averaged, np.nan)
    valid = np.isfinite(averaged)
    stack[valid] = np.sign(averaged[valid]) * np.abs(averaged[valid]) ** n
    return _return_stack(stack, support, return_support)


def phase_weighted_stack(
    traces,
    distances,
    ref_distance,
    slowness_sdeg,
    sampling_rate_hz,
    pw_order=1,
    *,
    valid_masks=None,
    min_support=DEFAULT_MIN_STACK_SUPPORT,
    return_support=False,
):
    trace_arrays, mask_arrays, length = _validate_traces_and_masks(traces, valid_masks)
    distance_array = _validate_distances(distances, len(trace_arrays))
    lin, linear_support = linear_stack(
        trace_arrays,
        distance_array,
        ref_distance,
        slowness_sdeg,
        sampling_rate_hz,
        valid_masks=mask_arrays,
        min_support=min_support,
        return_support=True,
    )
    phase_sum = np.zeros(length, dtype=np.complex128)
    phase_support = np.zeros(length, dtype=np.int32)
    for trace, mask, distance in zip(trace_arrays, mask_arrays, distance_array, strict=True):
        roll = _roll_for(distance, ref_distance, slowness_sdeg, sampling_rate_hz)
        masked_trace = np.where(mask, trace, 0.0)
        analytic = hilbert(masked_trace)
        analytic_shifted = zero_padded_shift(analytic, roll)
        shifted_mask = zero_padded_shift(mask, roll).astype(bool)
        phase_sum[shifted_mask] += np.exp(1j * np.angle(analytic_shifted[shifted_mask]))
        phase_support += shifted_mask.astype(np.int32)
    support = np.minimum(linear_support, phase_support).astype(np.int32)
    threshold = _support_threshold(min_support)
    weight = np.full(length, np.nan, dtype=np.float64)
    valid = support >= threshold
    weight[valid] = np.abs(phase_sum[valid]) / phase_support[valid]
    out = np.full(length, np.nan, dtype=np.float64)
    out[valid] = lin[valid] * weight[valid] ** pw_order
    return _return_stack(out, support, return_support)


def phase_weighted_stack_broken(traces, distances, ref_distance, slowness_sdeg, sampling_rate_hz, pw_order=1):
    """
    Regression-failure variant kept for discrepancy checks:
    phase array is shifted into local variable only and never written to shifted set.
    """
    lin = linear_stack(traces, distances, ref_distance, slowness_sdeg, sampling_rate_hz)
    nsta = len(traces)
    length = len(traces[0])
    shifted_phases = np.zeros((nsta, length), dtype=np.float64)
    for i in range(nsta):
        shift = int(round(-slowness_sdeg * (distances[i] - ref_distance) * sampling_rate_hz))
        analytic = hilbert(np.asarray(traces[i], dtype=np.float64))
        _ = np.roll(analytic, shift)  # noqa: F841
        shifted_phases[i] = np.angle(analytic)
    weight = np.abs(np.sum(np.exp(1j * shifted_phases), axis=0)) / nsta
    return lin * weight ** pw_order
