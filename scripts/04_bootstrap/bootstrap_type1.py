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

from scripts.shared import infer_nominal_sample_rate_hz, load_event_table
from scripts.shared import import_local_module
from scripts.paper0_provenance import validate_normalized_products
from scripts.paper0_bootstrap_fidelity import (
    BOOTSTRAP_FIDELITY_LEVELS,
    DEFAULT_BOOTSTRAP_FIDELITY_LEVEL,
    validate_n_bootstrap_for_fidelity,
)

compute_mod = import_local_module("marsquake_compute_vespagram", "scripts/03_vespagram/compute_vespagram.py")
compute_vespagram = compute_mod.compute_vespagram
DEFAULT_MIN_STACK_SUPPORT = compute_mod.DEFAULT_MIN_STACK_SUPPORT

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _blocked_valid_masks_error(status: str, bootstrap_type: str, event_ids, missing_event_ids, reason: str) -> RuntimeError:
    return RuntimeError(
        json.dumps(
            {
                "status": status,
                "bootstrap_type": bootstrap_type,
                "event_ids": [str(event_id) for event_id in event_ids],
                "missing_event_ids": [str(event_id) for event_id in missing_event_ids],
                "reason": reason,
            },
            sort_keys=True,
        )
    )


def _require_valid_masks(config: dict, event_ids):
    if "valid_masks" not in config or config["valid_masks"] is None:
        raise _blocked_valid_masks_error(
            "blocked_missing_valid_masks",
            "type1_event_subset",
            event_ids,
            event_ids,
            "valid_masks config is required for mask-aware bootstrap",
        )
    valid_masks = config["valid_masks"]
    if not isinstance(valid_masks, Mapping):
        raise _blocked_valid_masks_error(
            "blocked_invalid_valid_masks",
            "type1_event_subset",
            event_ids,
            event_ids,
            "valid_masks must be a mapping from event_id to boolean mask",
        )
    missing = [event_id for event_id in event_ids if event_id not in valid_masks]
    if missing:
        raise _blocked_valid_masks_error(
            "blocked_missing_valid_mask_events",
            "type1_event_subset",
            event_ids,
            missing,
            "valid_masks must include every selected event_id",
        )
    return valid_masks


def bootstrap_type1(
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
        raise ValueError("Need at least two events for bootstrap")
    n_bootstrap = int(config["n_bootstrap"])
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be positive")
    fidelity = validate_n_bootstrap_for_fidelity(
        str(config.get("bootstrap_fidelity_level", DEFAULT_BOOTSTRAP_FIDELITY_LEVEL)),
        n_bootstrap,
    )

    pick_n = max(2, int(np.floor(2.0 / 3.0 * n_events)))
    rng = np.random.default_rng(seed=config.get("seed", 0))
    threshold_pcts = [int(v) for v in config.get("threshold_pcts", [85])]
    stack_method = config.get("stack_method", "nth_root")
    nth_root_order = int(config.get("nth_root_order", 4))
    time_axis = np.asarray(time_axis, dtype=np.float64)
    sampling_rate_hz = float(config.get("sampling_rate_hz", infer_nominal_sample_rate_hz(time_axis)))
    valid_masks_dict = _require_valid_masks(config, event_ids)
    minimum_support = int(config.get("minimum_support", DEFAULT_MIN_STACK_SUPPORT))

    sum_pkikp_occ = {thr: None for thr in threshold_pcts}
    sum_pkkp_occ = {thr: None for thr in threshold_pcts}
    pkikp_peaks = []
    pkkp_peaks = []
    selected_event_indices = []

    slowness = None
    t = None
    for _ in range(n_bootstrap):
        idxs = sorted(rng.choice(np.arange(n_events), size=pick_n, replace=False).tolist())
        selected_event_indices.append(idxs)
        sel_ids = [event_ids[i] for i in idxs]
        sel_dist = [distances[i] for i in idxs]
        sel_traces = []
        sel_masks = []
        for eid in sel_ids:
            tr = np.asarray(traces_dict[eid])
            if tr.shape != time_axis.shape:
                raise ValueError(
                    f"Trace shape mismatch for Type I bootstrap input {eid}: "
                    f"trace_shape={tr.shape}, time_axis_shape={time_axis.shape}"
            )
            sel_traces.append(tr)
            mask = np.asarray(valid_masks_dict[eid], dtype=bool)
            if mask.shape != time_axis.shape:
                raise ValueError(
                    f"Valid mask shape mismatch for Type I bootstrap input {eid}: "
                    f"mask_shape={mask.shape}, time_axis_shape={time_axis.shape}"
                )
            sel_masks.append(mask)

        vesp, slowness, t, support_counts = compute_vespagram(
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

        def max_mask(window_t):
            sm = (t >= window_t[0]) & (t <= window_t[1])
            if not np.any(sm):
                return {thr: np.zeros_like(vesp) for thr in threshold_pcts}, float("nan"), float("nan"), float("nan")
            sub = vesp[:, sm]
            finite_sub = np.where(np.isfinite(sub), sub, -np.inf)
            if not np.any(np.isfinite(finite_sub)):
                return {thr: np.zeros_like(vesp) for thr in threshold_pcts}, float("nan"), float("nan"), float("nan")
            i = np.unravel_index(np.argmax(finite_sub), finite_sub.shape)
            p = float(finite_sub[i])
            peak_time = float(t[sm][i[1]])
            peak_slow = float(slowness[i[0]])
            occ = {}
            for thr in threshold_pcts:
                thr_occ = np.zeros_like(vesp)
                thr_occ[:, sm] = sub >= ((thr / 100.0) * p)
                occ[thr] = thr_occ
            return occ, peak_time, peak_slow, p

        occ_pkikp, pkikp_time, pkikp_slow, pkikp_power = max_mask((550, 700))
        occ_pkkp, pkkp_time, pkkp_slow, pkkp_power = max_mask((1200, 1500))
        for thr in threshold_pcts:
            if sum_pkikp_occ[thr] is None:
                sum_pkikp_occ[thr] = np.zeros_like(vesp, dtype=np.float32)
            if sum_pkkp_occ[thr] is None:
                sum_pkkp_occ[thr] = np.zeros_like(vesp, dtype=np.float32)
            sum_pkikp_occ[thr] += occ_pkikp[thr].astype(np.float32)
            sum_pkkp_occ[thr] += occ_pkkp[thr].astype(np.float32)
        pkikp_peaks.append((pkikp_time, pkikp_slow, pkikp_power))
        pkkp_peaks.append((pkkp_time, pkkp_slow, pkkp_power))

    mean_pkikp = np.stack([sum_pkikp_occ[thr] / float(n_bootstrap) for thr in threshold_pcts], axis=0).astype(np.float32)
    mean_pkkp = np.stack([sum_pkkp_occ[thr] / float(n_bootstrap) for thr in threshold_pcts], axis=0).astype(np.float32)
    default_index = threshold_pcts.index(85) if 85 in threshold_pcts else 0
    metadata = {
        "n_bootstrap": np.asarray(n_bootstrap, dtype=np.int32),
        "bootstrap_type": np.asarray("type1_event_subset"),
        "seed": np.asarray(int(config.get("seed", 0)), dtype=np.int64),
        "pick_n": np.asarray(pick_n, dtype=np.int32),
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
        "selected_event_indices": np.asarray(selected_event_indices, dtype=np.int32),
        "input_provenance_json": np.asarray(json.dumps(config.get("input_provenance", []), sort_keys=True), dtype=str),
        "bootstrap_fidelity_level": np.asarray(str(fidelity["level"])),
        "bootstrap_fidelity_description": np.asarray(str(fidelity["description"])),
        "bootstrap_published_equivalent": np.asarray(bool(fidelity["published_equivalent"])),
        "declared_published_n_bootstrap": np.asarray(int(fidelity["published_n_bootstrap"]), dtype=np.int32),
    }

    np.savez_compressed(
        output_dir / "type1_pkikp_occupancy.npz",
        **metadata,
        occupancy=mean_pkikp[default_index],
        occupancy_maps=mean_pkikp,
        threshold_pcts=np.asarray(threshold_pcts, dtype=np.int32),
        peak_times=np.asarray([p[0] for p in pkikp_peaks], dtype=np.float32),
        peak_slownesses=np.asarray([p[1] for p in pkikp_peaks], dtype=np.float32),
        peak_powers=np.asarray([p[2] for p in pkikp_peaks], dtype=np.float32),
        slowness_axis=np.asarray(slowness, dtype=np.float32),
        time_axis=np.asarray(t, dtype=np.float64),
    )
    np.savez_compressed(
        output_dir / "type1_pkkp_occupancy.npz",
        **metadata,
        occupancy=mean_pkkp[default_index],
        occupancy_maps=mean_pkkp,
        threshold_pcts=np.asarray(threshold_pcts, dtype=np.int32),
        peak_times=np.asarray([p[0] for p in pkkp_peaks], dtype=np.float32),
        peak_slownesses=np.asarray([p[1] for p in pkkp_peaks], dtype=np.float32),
        peak_powers=np.asarray([p[2] for p in pkkp_peaks], dtype=np.float32),
        slowness_axis=np.asarray(slowness, dtype=np.float32),
        time_axis=np.asarray(t, dtype=np.float64),
    )
    logger.info("Saved bootstrap occupancy in %s", output_dir)


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap Type I (2/3 event subset)")
    parser.add_argument("--table", default="manifest/event_table.csv")
    parser.add_argument("--vesp-dir", default="data/processed")
    parser.add_argument("--out-dir", default="results/bootstrap")
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


def _load_traces(
    event_table: Path,
    matrix_dir: Path,
    mode: str = "paperfaith",
    variant: str = "C",
    input_type: str = "envelope",
):
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
        raise FileNotFoundError(f"Missing {len(missing)} required Type I bootstrap inputs: {missing[:5]}")
    if time_axis is None:
        raise RuntimeError("No time axis found for bootstrap inputs")
    for event_id, candidate in time_axes:
        if candidate.shape != time_axis.shape or not np.allclose(candidate, time_axis, rtol=0.0, atol=1e-9):
            raise ValueError(f"Time-axis mismatch for Type I bootstrap input {event_id}")
    return event_ids, distances, traces, valid_masks, np.asarray(time_axis), input_provenance


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
    eids, dist, tr, masks, t, provenance = _load_traces(
        Path(args.table),
        Path(args.vesp_dir),
        mode=args.mode,
        variant=args.variant,
        input_type=args.input_type,
    )
    cfg["input_provenance"] = provenance
    cfg["valid_masks"] = masks
    bootstrap_type1(eids, dist, tr, cfg, t, Path(args.out_dir))
