from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Mapping
from pathlib import Path

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.paper0_provenance import validate_normalized_products
from scripts.paper0_bootstrap_fidelity import (
    BOOTSTRAP_FIDELITY_LEVELS,
    DEFAULT_BOOTSTRAP_FIDELITY_LEVEL,
    validate_n_bootstrap_for_fidelity,
)
from scripts.shared import import_local_module, infer_nominal_sample_rate_hz, load_event_table, repo_path

compute_mod = import_local_module("marsquake_compute_vespagram", "scripts/03_vespagram/compute_vespagram.py")
compute_vespagram = compute_mod.compute_vespagram
DEFAULT_MIN_STACK_SUPPORT = compute_mod.DEFAULT_MIN_STACK_SUPPORT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PHASE_WINDOWS = {
    "pkikp": (550.0, 700.0),
    "pkkp": (1200.0, 1500.0),
}
CLUSTER_MIN_DEG = 29.0
CLUSTER_MAX_DEG = 32.0


def _machine_error(status: str, event_ids, reason: str, **extra) -> RuntimeError:
    return RuntimeError(
        json.dumps(
            {
                "status": status,
                "bootstrap_type": "type2_distance_stratified",
                "event_ids": [str(event_id) for event_id in event_ids],
                "reason": reason,
                **extra,
            },
            sort_keys=True,
        )
    )


def _require_valid_masks(config: dict, event_ids):
    if "valid_masks" not in config or config["valid_masks"] is None:
        raise _machine_error(
            "blocked_missing_valid_masks",
            event_ids,
            "valid_masks config is required for mask-aware bootstrap",
            missing_event_ids=[str(event_id) for event_id in event_ids],
        )
    valid_masks = config["valid_masks"]
    if not isinstance(valid_masks, Mapping):
        raise _machine_error(
            "blocked_invalid_valid_masks",
            event_ids,
            "valid_masks must be a mapping from event_id to boolean mask",
            missing_event_ids=[str(event_id) for event_id in event_ids],
        )
    missing = [event_id for event_id in event_ids if event_id not in valid_masks]
    if missing:
        raise _machine_error(
            "blocked_missing_valid_mask_events",
            event_ids,
            "valid_masks must include every selected event_id",
            missing_event_ids=[str(event_id) for event_id in missing],
        )
    return valid_masks


def _distance_bin_labels(distances) -> np.ndarray:
    arr = np.asarray(distances, dtype=np.float64)
    return np.where(
        (arr >= CLUSTER_MIN_DEG) & (arr <= CLUSTER_MAX_DEG),
        "cluster_29_32",
        "outside_29_32",
    )


def _phase_peak_occupancy(vespagram, slowness_axis, time_axis, window_t, threshold_pcts):
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


def _support_at_peak_cell(support_counts: np.ndarray, slowness_axis: np.ndarray, time_axis: np.ndarray, peak_time: float, peak_slow: float) -> int:
    if not np.isfinite(peak_time) or not np.isfinite(peak_slow):
        return 0
    slow_idx = int(np.argmin(np.abs(np.asarray(slowness_axis, dtype=np.float64) - float(peak_slow))))
    time_idx = int(np.argmin(np.abs(np.asarray(time_axis, dtype=np.float64) - float(peak_time))))
    return int(np.asarray(support_counts, dtype=np.int32)[slow_idx, time_idx])


def bootstrap_type2_distance_stratified(
    event_ids,
    distances,
    traces_dict,
    config: dict,
    time_axis: np.ndarray,
    output_dir: Path,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    n_events = len(event_ids)
    if n_events < 2:
        raise ValueError("Need at least two events for Type II distance-stratified bootstrap")
    n_bootstrap = int(config["n_bootstrap"])
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be positive")
    fidelity = validate_n_bootstrap_for_fidelity(
        str(config.get("bootstrap_fidelity_level", DEFAULT_BOOTSTRAP_FIDELITY_LEVEL)),
        n_bootstrap,
    )

    time_axis = np.asarray(time_axis, dtype=np.float64)
    labels = _distance_bin_labels(distances)
    cluster_indices = np.flatnonzero(labels == "cluster_29_32")
    outside_indices = np.flatnonzero(labels == "outside_29_32")
    if cluster_indices.size == 0 or outside_indices.size == 0:
        raise _machine_error(
            "blocked_distance_cluster_pathology",
            event_ids,
            "Type II requires both 29-32 degree cluster events and outside-cluster events",
            cluster_event_count=int(cluster_indices.size),
            outside_event_count=int(outside_indices.size),
        )

    pick_n = max(2, int(np.floor(2.0 / 3.0 * n_events)))
    cluster_pick_n = max(1, pick_n // 2)
    outside_pick_n = pick_n - cluster_pick_n
    if cluster_pick_n > cluster_indices.size or outside_pick_n > outside_indices.size:
        raise _machine_error(
            "blocked_distance_cluster_pathology",
            event_ids,
            "not enough events in one Type II distance stratum for the requested subset size",
            cluster_event_count=int(cluster_indices.size),
            outside_event_count=int(outside_indices.size),
            cluster_pick_n=int(cluster_pick_n),
            outside_pick_n=int(outside_pick_n),
        )

    rng = np.random.default_rng(seed=config.get("seed", 0))
    threshold_pcts = [int(v) for v in config.get("threshold_pcts", [85])]
    stack_method = config.get("stack_method", "nth_root")
    nth_root_order = int(config.get("nth_root_order", 4))
    sampling_rate_hz = float(config.get("sampling_rate_hz", infer_nominal_sample_rate_hz(time_axis)))
    valid_masks_dict = _require_valid_masks(config, event_ids)
    minimum_support = int(config.get("minimum_support", DEFAULT_MIN_STACK_SUPPORT))

    occupancy_by_phase = {phase: {thr: [] for thr in threshold_pcts} for phase in PHASE_WINDOWS}
    peaks_by_phase = {phase: [] for phase in PHASE_WINDOWS}
    support_at_peaks_by_phase = {phase: [] for phase in PHASE_WINDOWS}
    selected_event_indices = []
    selected_distance_bin_labels = []
    slowness_axis = None
    t = None

    for _ in range(n_bootstrap):
        cluster_pick = rng.choice(cluster_indices, size=cluster_pick_n, replace=False)
        outside_pick = rng.choice(outside_indices, size=outside_pick_n, replace=False)
        idxs = sorted(np.concatenate([cluster_pick, outside_pick]).astype(int).tolist())
        selected_event_indices.append(idxs)
        selected_distance_bin_labels.append(labels[idxs].astype(str).tolist())

        sel_ids = [event_ids[i] for i in idxs]
        sel_dist = [float(distances[i]) for i in idxs]
        sel_traces = []
        sel_masks = []
        for eid in sel_ids:
            trace = np.asarray(traces_dict[eid])
            if trace.shape != time_axis.shape:
                raise ValueError(
                    f"Trace shape mismatch for Type II bootstrap input {eid}: "
                    f"trace_shape={trace.shape}, time_axis_shape={time_axis.shape}"
                )
            mask = np.asarray(valid_masks_dict[eid], dtype=bool)
            if mask.shape != time_axis.shape:
                raise ValueError(
                    f"Valid mask shape mismatch for Type II bootstrap input {eid}: "
                    f"mask_shape={mask.shape}, time_axis_shape={time_axis.shape}"
                )
            sel_traces.append(trace)
            sel_masks.append(mask)

        vesp, slowness_axis, t, support_counts = compute_vespagram(
            sel_traces,
            sel_dist,
            ref_distance=29.0,
            sampling_rate_hz=sampling_rate_hz,
            time_axis=time_axis,
            slowness_min=-10.0,
            slowness_max=0.0,
            slowness_steps=100,
            stack_method=stack_method,
            n=nth_root_order,
            power_window_s=config["power_window_s"],
            valid_masks=sel_masks,
            min_support=minimum_support,
        )

        for phase, window_t in PHASE_WINDOWS.items():
            occupancy, peak_time, peak_slow, peak_power = _phase_peak_occupancy(
                vesp,
                slowness_axis,
                t,
                window_t,
                threshold_pcts,
            )
            for threshold_pct in threshold_pcts:
                occupancy_by_phase[phase][threshold_pct].append(occupancy[threshold_pct])
            peaks_by_phase[phase].append((peak_time, peak_slow, peak_power))
            support_at_peaks_by_phase[phase].append(
                _support_at_peak_cell(support_counts, slowness_axis, t, peak_time, peak_slow)
            )

    metadata = {
        "n_bootstrap": np.asarray(n_bootstrap, dtype=np.int32),
        "bootstrap_type": np.asarray("type2_distance_stratified"),
        "seed": np.asarray(int(config.get("seed", 0)), dtype=np.int64),
        "pick_n": np.asarray(pick_n, dtype=np.int32),
        "cluster_pick_n": np.asarray(cluster_pick_n, dtype=np.int32),
        "outside_pick_n": np.asarray(outside_pick_n, dtype=np.int32),
        "cluster_distance_range_deg": np.asarray([CLUSTER_MIN_DEG, CLUSTER_MAX_DEG], dtype=np.float32),
        "sampling_rate_hz": np.asarray(sampling_rate_hz, dtype=np.float64),
        "stack_method": np.asarray(stack_method),
        "nth_root_order": np.asarray(nth_root_order, dtype=np.int32),
        "power_window_s": np.asarray(float(config["power_window_s"]), dtype=np.float64),
        "mode": np.asarray(str(config.get("mode", ""))),
        "variant": np.asarray(str(config.get("variant", ""))),
        "input_type": np.asarray(str(config.get("input_type", ""))),
        "minimum_support": np.asarray(minimum_support, dtype=np.int32),
        "event_ids": np.asarray(event_ids, dtype=str),
        "distances": np.asarray(distances, dtype=np.float64),
        "distance_bin_labels": labels.astype(str),
        "selected_event_indices": np.asarray(selected_event_indices, dtype=np.int32),
        "selected_distance_bin_labels": np.asarray(selected_distance_bin_labels, dtype=str),
        "input_provenance_json": np.asarray(json.dumps(config.get("input_provenance", []), sort_keys=True), dtype=str),
        "bootstrap_fidelity_level": np.asarray(str(fidelity["level"])),
        "bootstrap_fidelity_description": np.asarray(str(fidelity["description"])),
        "bootstrap_published_equivalent": np.asarray(bool(fidelity["published_equivalent"])),
        "declared_published_n_bootstrap": np.asarray(int(fidelity["published_n_bootstrap"]), dtype=np.int32),
    }

    default_index = threshold_pcts.index(85) if 85 in threshold_pcts else 0
    for phase in PHASE_WINDOWS:
        occupancy_maps = np.stack(
            [np.mean(occupancy_by_phase[phase][thr], axis=0) for thr in threshold_pcts],
            axis=0,
        ).astype(np.float32)
        peaks = peaks_by_phase[phase]
        np.savez_compressed(
            output_dir / f"type2_{phase}_distance_stratified_occupancy.npz",
            **metadata,
            occupancy=occupancy_maps[default_index],
            occupancy_maps=occupancy_maps,
            threshold_pcts=np.asarray(threshold_pcts, dtype=np.int32),
            peak_times=np.asarray([p[0] for p in peaks], dtype=np.float32),
            peak_slownesses=np.asarray([p[1] for p in peaks], dtype=np.float32),
            peak_powers=np.asarray([p[2] for p in peaks], dtype=np.float32),
            support_at_peaks=np.asarray(support_at_peaks_by_phase[phase], dtype=np.int32),
            slowness_axis=np.asarray(slowness_axis, dtype=np.float32),
            time_axis=np.asarray(t, dtype=np.float64),
        )
    logger.info("Saved Type II distance-stratified bootstrap in %s", output_dir)


def _load_traces(event_table: Path, matrix_dir: Path, mode: str, variant: str, input_type: str):
    rows = load_event_table(event_table)
    event_ids = []
    distances = []
    traces = {}
    valid_masks = {}
    time_axis = None
    time_axes = []
    input_provenance = []
    missing = []
    for row in rows:
        if row.get("set") != "vespagram":
            continue
        event_id = row["event_id"]
        trace_path = matrix_dir / f"{event_id}_{mode}_{variant}_{input_type}.npy"
        if not trace_path.exists():
            missing.append(str(trace_path))
            continue
        provenance = validate_normalized_products(event_id, matrix_dir, mode, variant, input_type)
        traces[event_id] = np.load(trace_path)
        valid_masks[event_id] = np.load(provenance["valid_sample_mask_path"], allow_pickle=False).astype(bool)
        event_ids.append(event_id)
        distances.append(float(row["distance_deg"]))
        input_provenance.append(provenance)
        t_candidate = matrix_dir / f"{event_id}_{mode}_{variant}_times.npy"
        if not t_candidate.exists():
            missing.append(str(t_candidate))
            continue
        time_candidate = np.load(t_candidate).astype(np.float64)
        time_axes.append((event_id, time_candidate))
        if time_axis is None:
            time_axis = time_candidate
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} required Type II bootstrap inputs: {missing[:5]}")
    if time_axis is None:
        raise RuntimeError("No time axis found for Type II bootstrap inputs")
    for event_id, candidate in time_axes:
        if candidate.shape != time_axis.shape or not np.allclose(candidate, time_axis, rtol=0.0, atol=1e-9):
            raise ValueError(f"Time-axis mismatch for Type II bootstrap input {event_id}")
    return event_ids, distances, traces, valid_masks, np.asarray(time_axis), input_provenance


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap Type II (distance-stratified event subset)")
    parser.add_argument("--table", default=str(repo_path("manifest/event_table.csv")))
    parser.add_argument("--vesp-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("results/bootstrap")))
    parser.add_argument("--mode", default="paperfaith")
    parser.add_argument("--variant", default="A")
    parser.add_argument("--input-type", default="envelope")
    parser.add_argument("--n-bootstrap", type=int, default=200)
    parser.add_argument(
        "--bootstrap-fidelity-level",
        choices=sorted(BOOTSTRAP_FIDELITY_LEVELS),
        default=DEFAULT_BOOTSTRAP_FIDELITY_LEVEL,
    )
    parser.add_argument("--power-window-s", type=float, default=20.0)
    parser.add_argument("--stack-method", default="nth_root")
    parser.add_argument("--nth-root-order", type=int, default=4)
    parser.add_argument("--threshold-pcts", default="50,70,85")
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg = {
        "n_bootstrap": args.n_bootstrap,
        "power_window_s": args.power_window_s,
        "stack_method": args.stack_method,
        "nth_root_order": args.nth_root_order,
        "threshold_pcts": [int(v.strip()) for v in args.threshold_pcts.split(",") if v.strip()],
        "seed": args.seed,
        "mode": args.mode,
        "variant": args.variant,
        "input_type": args.input_type,
        "bootstrap_fidelity_level": args.bootstrap_fidelity_level,
    }
    eids, dist, tr, masks, t_axis, provenance = _load_traces(
        Path(args.table),
        Path(args.vesp_dir),
        mode=args.mode,
        variant=args.variant,
        input_type=args.input_type,
    )
    cfg["input_provenance"] = provenance
    cfg["valid_masks"] = masks
    bootstrap_type2_distance_stratified(eids, dist, tr, cfg, t_axis, Path(args.out_dir))
