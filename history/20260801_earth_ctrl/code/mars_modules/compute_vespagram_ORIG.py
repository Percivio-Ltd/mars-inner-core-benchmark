from __future__ import annotations

import numpy as np

from scripts.shared import import_local_module

_stacking = import_local_module("marsquake_stacking", "scripts/03_vespagram/stacking.py")
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
