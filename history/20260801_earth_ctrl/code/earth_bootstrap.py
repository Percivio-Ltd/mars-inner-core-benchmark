"""P0-EARTH-CTRL bootstrap port (D-ADAPT-E4): Type-I and Type-III algorithms copied from
scripts/04_bootstrap/bootstrap_type1.py and bootstrap_type3_alignment_jitter.py with ONLY:
  - windows parameterized (dict label -> (t0, t1)) instead of hardcoded pkikp/pkkp;
  - ref_distance parameterized (30.0 here) instead of hardcoded 29.0;
  - repo provenance/fidelity imports dropped (isolated custody; import mechanics);
  - occupancy maps returned/saved per window label.
RNG call order is preserved exactly: type1 draws one rng.choice per iteration; type3 draws one
rng.uniform(size=n_events) per iteration. Window-max/occupancy logic is verbatim (_phase_peak_
occupancy from type3, identical to type1's max_mask)."""
from __future__ import annotations

import numpy as np

from earth_kernel import compute_vespagram, DEFAULT_MIN_STACK_SUPPORT

SLOWNESS_MIN, SLOWNESS_MAX, SLOWNESS_STEPS = -10.0, 0.0, 100


def _phase_peak_occupancy(vespagram, slowness_axis, time_axis, window_t, threshold_pcts):
    # verbatim from bootstrap_type3_alignment_jitter.py:113-141
    mask = (time_axis >= window_t[0]) & (time_axis <= window_t[1])
    if not np.any(mask):
        empty = {thr: np.zeros_like(vespagram, dtype=bool) for thr in threshold_pcts}
        return empty, float("nan"), float("nan"), float("nan")
    sub = vespagram[:, mask]
    finite_sub = np.where(np.isfinite(sub), sub, -np.inf)
    if not np.any(np.isfinite(finite_sub)):
        empty = {thr: np.zeros_like(vespagram, dtype=bool) for thr in threshold_pcts}
        return empty, float("nan"), float("nan"), float("nan")
    peak_idx = np.unravel_index(np.argmax(finite_sub), finite_sub.shape)
    peak_power = float(finite_sub[peak_idx])
    peak_time = float(time_axis[mask][peak_idx[1]])
    peak_slow = float(slowness_axis[peak_idx[0]])
    occupancy = {}
    for threshold_pct in threshold_pcts:
        thresholded = np.zeros_like(vespagram, dtype=bool)
        thresholded[:, mask] = sub >= ((threshold_pct / 100.0) * peak_power)
        occupancy[threshold_pct] = thresholded
    return occupancy, peak_time, peak_slow, peak_power


def shift_trace_on_time_axis(trace, time_axis, shift_s):
    # verbatim from bootstrap_type3_alignment_jitter.py:84-90
    return np.interp(time_axis - float(shift_s), time_axis, trace, left=0.0, right=0.0)


def shift_mask_on_time_axis(valid_mask, time_axis, shift_s):
    # verbatim from bootstrap_type3_alignment_jitter.py:93-100
    shifted = np.interp(time_axis - float(shift_s), time_axis, valid_mask.astype(float), left=0.0, right=0.0)
    return shifted >= 1.0


def bootstrap_type1_earth(traces, masks, distances, time_axis, windows, *, ref_distance,
                          sampling_rate_hz, n_bootstrap=200, seed=0,
                          threshold_pcts=(50, 70, 85), power_window_s=20.0):
    """traces/masks: lists aligned with distances. windows: {label: (t0, t1)}.
    Returns {label: {"occupancy_maps": (n_thr, S, T) float32 means, "threshold_pcts": [...],
                     "peaks": [(t, p, power)]}}."""
    n_events = len(traces)
    if n_events < 2:
        raise ValueError("Need at least two events for bootstrap")
    pick_n = max(2, int(np.floor(2.0 / 3.0 * n_events)))  # bootstrap_type1.py:97
    rng = np.random.default_rng(seed=seed)
    threshold_pcts = [int(v) for v in threshold_pcts]
    sums = {lbl: {thr: None for thr in threshold_pcts} for lbl in windows}
    peaks = {lbl: [] for lbl in windows}
    selected = []
    for _ in range(n_bootstrap):
        idxs = sorted(rng.choice(np.arange(n_events), size=pick_n, replace=False).tolist())
        selected.append(idxs)
        sel_traces = [traces[i] for i in idxs]
        sel_masks = [masks[i] for i in idxs]
        sel_dist = [distances[i] for i in idxs]
        vesp, slowness, t, _sc = compute_vespagram(
            sel_traces, sel_dist, ref_distance=ref_distance,
            sampling_rate_hz=sampling_rate_hz, time_axis=time_axis,
            slowness_min=SLOWNESS_MIN, slowness_max=SLOWNESS_MAX, slowness_steps=SLOWNESS_STEPS,
            stack_method="nth_root", n=4, power_window_s=power_window_s,
            valid_masks=sel_masks, min_support=DEFAULT_MIN_STACK_SUPPORT,
        )
        for lbl, window_t in windows.items():
            occ, pt, ps, pp = _phase_peak_occupancy(vesp, slowness, t, window_t, threshold_pcts)
            for thr in threshold_pcts:
                if sums[lbl][thr] is None:
                    sums[lbl][thr] = np.zeros_like(vesp, dtype=np.float32)
                sums[lbl][thr] += occ[thr].astype(np.float32)
            peaks[lbl].append((pt, ps, pp))
    out = {}
    for lbl in windows:
        maps = np.stack([sums[lbl][thr] / float(n_bootstrap) for thr in threshold_pcts], axis=0)
        out[lbl] = {"occupancy_maps": maps.astype(np.float32), "threshold_pcts": threshold_pcts,
                    "peaks": peaks[lbl], "slowness_axis": np.linspace(SLOWNESS_MIN, SLOWNESS_MAX, SLOWNESS_STEPS),
                    "time_axis": np.asarray(time_axis, dtype=np.float64),
                    "n_bootstrap": n_bootstrap, "seed": seed, "pick_n": pick_n,
                    "selected_event_indices": selected}
    return out


def bootstrap_type3_earth(traces, masks, distances, time_axis, windows, *, ref_distance,
                          sampling_rate_hz, n_bootstrap=200, seed=0, jitter_limit_s=10.0,
                          threshold_pcts=(50, 70, 85), power_window_s=20.0):
    """Same contract as type1; jitters ALL events per iteration (no subsampling)."""
    n_events = len(traces)
    if n_events < 2:
        raise ValueError("Need at least two events for Type III alignment jitter")
    rng = np.random.default_rng(seed=seed)
    threshold_pcts = [int(v) for v in threshold_pcts]
    sums = {lbl: {thr: None for thr in threshold_pcts} for lbl in windows}
    peaks = {lbl: [] for lbl in windows}
    all_jitters = []
    for _ in range(n_bootstrap):
        jitters = rng.uniform(-jitter_limit_s, jitter_limit_s, size=n_events)
        all_jitters.append(jitters.astype(np.float32))
        jittered_traces = [shift_trace_on_time_axis(np.asarray(tr), time_axis, j)
                           for tr, j in zip(traces, jitters)]
        jittered_masks = [shift_mask_on_time_axis(np.asarray(mk, dtype=bool), time_axis, j)
                          for mk, j in zip(masks, jitters)]
        vesp, slowness, t, _sc = compute_vespagram(
            jittered_traces, distances, ref_distance=ref_distance,
            sampling_rate_hz=sampling_rate_hz, time_axis=time_axis,
            slowness_min=SLOWNESS_MIN, slowness_max=SLOWNESS_MAX, slowness_steps=SLOWNESS_STEPS,
            stack_method="nth_root", n=4, power_window_s=power_window_s,
            valid_masks=jittered_masks, min_support=DEFAULT_MIN_STACK_SUPPORT,
        )
        for lbl, window_t in windows.items():
            occ, pt, ps, pp = _phase_peak_occupancy(vesp, slowness, t, window_t, threshold_pcts)
            for thr in threshold_pcts:
                if sums[lbl][thr] is None:
                    sums[lbl][thr] = np.zeros_like(vesp, dtype=np.float32)
                sums[lbl][thr] += occ[thr].astype(np.float32)
            peaks[lbl].append((pt, ps, pp))
    out = {}
    for lbl in windows:
        maps = np.stack([sums[lbl][thr] / float(n_bootstrap) for thr in threshold_pcts], axis=0)
        out[lbl] = {"occupancy_maps": maps.astype(np.float32), "threshold_pcts": threshold_pcts,
                    "peaks": peaks[lbl], "slowness_axis": np.linspace(SLOWNESS_MIN, SLOWNESS_MAX, SLOWNESS_STEPS),
                    "time_axis": np.asarray(time_axis, dtype=np.float64),
                    "n_bootstrap": n_bootstrap, "seed": seed,
                    "jitter_seconds": np.stack(all_jitters, axis=0)}
    return out
