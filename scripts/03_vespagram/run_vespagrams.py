from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.paper0_provenance import validate_normalized_products
from scripts.shared import infer_nominal_sample_rate_hz, load_event_table, repo_path
from scripts.shared import import_local_module

compute_mod = import_local_module("marsquake_compute_vespagram", "scripts/03_vespagram/compute_vespagram.py")
compute_vespagram = compute_mod.compute_vespagram
DEFAULT_MIN_STACK_SUPPORT = compute_mod.DEFAULT_MIN_STACK_SUPPORT
VESPAGRAM_ARTIFACT_SCHEMA_VERSION = "paper0-vespagram-mask-v1"
RELEASED_POWER_WINDOW_SAMPLES = 20
RELEASED_POWER_WINDOW_S = 1.0
POWER_WINDOWS_S = (RELEASED_POWER_WINDOW_S, 5.0, 10.0, 20.0)
HEADLINE_NORMALIZATION_VARIANT = "A"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _input_polarization_operator(record: dict) -> str:
    alignment = record.get("alignment", {}) if isinstance(record, dict) else {}
    upstream = alignment.get("upstream", {}) if isinstance(alignment, dict) else {}
    candidates = [
        record.get("polarization_operator") if isinstance(record, dict) else "",
        alignment.get("polarization_operator") if isinstance(alignment, dict) else "",
        alignment.get("metadata", {}).get("polarization_operator") if isinstance(alignment.get("metadata", {}), dict) else "",
        upstream.get("operator") if isinstance(upstream, dict) else "",
        upstream.get("metadata", {}).get("operator") if isinstance(upstream.get("metadata", {}), dict) else "",
    ]
    for value in candidates:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _polarization_operator_provenance(input_provenance: list[dict], mode: str) -> tuple[str, list[str]]:
    operators = [_input_polarization_operator(record) for record in input_provenance]
    fallback = "not_applicable" if mode != "paperfaith" else "unknown"
    operators = [operator or fallback for operator in operators]
    unique = sorted(set(operators))
    if not unique:
        return fallback, []
    if len(unique) == 1:
        return unique[0], operators
    return "mixed", operators


def load_combo_data(rows, mode: str, variant: str, input_type: str, data_dir: Path):
    event_ids: List[str] = []
    traces: List[np.ndarray] = []
    valid_masks: List[np.ndarray] = []
    distances: List[float] = []
    distance_errors: List[float] = []
    time_axes: List[np.ndarray] = []
    provenance_records: list[dict] = []
    missing: List[str] = []

    for row in rows:
        if row["set"] != "vespagram":
            continue
        event_id = row["event_id"]
        path = data_dir / f"{event_id}_{mode}_{variant}_{input_type}.npy"
        if not path.exists():
            missing.append(str(path))
            continue
        time_path = data_dir / f"{event_id}_{mode}_{variant}_times.npy"
        if not time_path.exists():
            missing.append(str(time_path))
            continue
        provenance = validate_normalized_products(event_id, data_dir, mode, variant, input_type)
        traces.append(np.load(path))
        valid_masks.append(np.load(provenance["valid_sample_mask_path"], allow_pickle=False).astype(bool))
        time_axes.append(np.load(time_path).astype(np.float64))
        provenance_records.append(provenance)
        event_ids.append(event_id)
        distances.append(float(row["distance_deg"]))
        distance_errors.append(float(row.get("distance_err") or "nan"))

    if missing:
        raise FileNotFoundError(
            f"Missing {len(missing)} required vespagram inputs for {mode}/{input_type}/{variant}: {missing[:5]}"
        )
    if not traces:
        raise RuntimeError(f"No traces for combo {mode}/{input_type}/{variant}")
    base_time_axis = time_axes[0]
    for event_id, time_axis in zip(event_ids, time_axes, strict=True):
        if time_axis.shape != base_time_axis.shape or not np.allclose(time_axis, base_time_axis, rtol=0.0, atol=1e-9):
            raise ValueError(f"Time-axis mismatch for {mode}/{input_type}/{variant}/{event_id}")
    return event_ids, traces, valid_masks, distances, distance_errors, base_time_axis, provenance_records


def write_vespagram_payload(out_path: Path, vespagram, support_counts, slowness_axis, time_axis, meta: Dict):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    polarization_operator, input_polarization_operators = _polarization_operator_provenance(
        meta["input_provenance"],
        str(meta["mode"]),
    )
    np.savez(
        out_path,
        artifact_schema_version=VESPAGRAM_ARTIFACT_SCHEMA_VERSION,
        vespagram=vespagram,
        support_counts=support_counts.astype(np.int32),
        minimum_support=np.asarray(meta["minimum_support"], dtype=np.int32),
        slowness_axis=slowness_axis,
        time_axis=time_axis,
        events=np.array(meta["event_ids"], dtype=str),
        distances=np.array(meta["distances"], dtype=float),
        distance_errors=np.array(meta["distance_errors"], dtype=float),
        mode=meta["mode"],
        input_type=meta["input_type"],
        norm_variant=meta["norm_variant"],
        polarization_operator=np.asarray(polarization_operator, dtype=str),
        input_polarization_operators=np.asarray(input_polarization_operators, dtype=str),
        power_window_s=meta["power_window_s"],
        stack_method=meta["stack_method"],
        ref_distance=meta["ref_distance"],
        slowness_min=meta["slowness_min"],
        slowness_max=meta["slowness_max"],
        slowness_steps=meta["slowness_steps"],
        sampling_rate_hz=meta["sampling_rate_hz"],
        input_trace_paths=np.asarray([r["trace_path"] for r in meta["input_provenance"]], dtype=str),
        input_trace_sha256=np.asarray([r["trace_sha256"] for r in meta["input_provenance"]], dtype=str),
        input_valid_sample_mask_paths=np.asarray([r["valid_sample_mask_path"] for r in meta["input_provenance"]], dtype=str),
        input_valid_sample_mask_sha256=np.asarray([r["valid_sample_mask_sha256"] for r in meta["input_provenance"]], dtype=str),
        input_time_paths=np.asarray([r["time_path"] for r in meta["input_provenance"]], dtype=str),
        input_time_sha256=np.asarray([r["time_sha256"] for r in meta["input_provenance"]], dtype=str),
        normalization_metadata_paths=np.asarray(
            [r["normalization_metadata_path"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        normalization_metadata_sha256=np.asarray(
            [r["normalization_metadata_sha256"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        alignment_metadata_paths=np.asarray(
            [r["alignment"]["metadata_path"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        alignment_metadata_sha256=np.asarray(
            [r["alignment"]["metadata_sha256"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        rotation_metadata_paths=np.asarray(
            [r["alignment"]["upstream"]["rotation"]["metadata_path"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        rotation_metadata_sha256=np.asarray(
            [r["alignment"]["upstream"]["rotation"]["metadata_sha256"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        locked_pick_manifest_paths=np.asarray(
            [r["alignment"]["metadata"].get("locked_pick_manifest_path", "") for r in meta["input_provenance"]],
            dtype=str,
        ),
        locked_pick_manifest_sha256=np.asarray(
            [r["alignment"]["metadata"].get("locked_pick_manifest_sha256", "") for r in meta["input_provenance"]],
            dtype=str,
        ),
        deglitch_run_summary_sha256=np.asarray(
            [r["alignment"]["upstream"]["rotation"]["metadata"]["deglitch_run_summary_sha256"] for r in meta["input_provenance"]],
            dtype=str,
        ),
        input_provenance_json=np.asarray(json.dumps(meta["input_provenance"], sort_keys=True), dtype=str),
    )


def run_run(
    event_table: Path,
    data_dir: Path,
    results_dir: Path,
    ref_distance: float,
):
    events = load_event_table(event_table)
    results_dir.mkdir(parents=True, exist_ok=True)

    slowness_min = -10.0
    slowness_max = 0.0
    slowness_steps = 100
    power_windows = POWER_WINDOWS_S

    combos: List[Tuple[str, str, str]] = [
        ("paperfaith", "envelope", variant)
        for variant in ("A", "B", "C")
    ] + [
        ("paperfaith", "waveform", "C"),
        ("ablation", "envelope", "C"),
        ("ablation", "waveform", "C"),
    ]

    for mode, input_type, variant in combos:
        event_ids, traces, valid_masks, distances, distance_errors, t, input_provenance = load_combo_data(events, mode, variant, input_type, data_dir)
        sr = infer_nominal_sample_rate_hz(t)

        for method in ["nth_root", "pws"]:
            for win in power_windows:
                vesp, s_axis, _, support_counts = compute_vespagram(
                    traces=traces,
                    valid_masks=valid_masks,
                    distances=distances,
                    ref_distance=ref_distance,
                    sampling_rate_hz=sr,
                    time_axis=t,
                    slowness_min=slowness_min,
                    slowness_max=slowness_max,
                    slowness_steps=slowness_steps,
                    stack_method=method,
                    n=4,
                    pw_order=1 if method == "pws" else None,
                    power_window_s=win,
                    min_support=DEFAULT_MIN_STACK_SUPPORT,
                )
                out = results_dir / mode / input_type / variant / f"{method}_win{int(win)}.npz"
                write_vespagram_payload(
                    out,
                    vespagram=vesp,
                    support_counts=support_counts,
                    slowness_axis=s_axis,
                    time_axis=t,
                    meta={
                        "event_ids": event_ids,
                        "distances": distances,
                        "distance_errors": distance_errors,
                        "mode": mode,
                        "input_type": input_type,
                        "norm_variant": variant,
                        "power_window_s": win,
                        "stack_method": method,
                        "ref_distance": ref_distance,
                        "slowness_min": slowness_min,
                        "slowness_max": slowness_max,
                        "slowness_steps": slowness_steps,
                        "sampling_rate_hz": sr,
                        "minimum_support": DEFAULT_MIN_STACK_SUPPORT,
                        "input_provenance": input_provenance,
                    },
                )

                for label, t0, t1 in [("pkikp", 550, 700), ("pkkp", 1200, 1500)]:
                    t_mask = (t >= t0) & (t <= t1)
                    if not np.any(t_mask):
                        continue
                    win_data = vesp[:, t_mask]
                    if win_data.size == 0:
                        continue
                    finite = win_data[np.isfinite(win_data)]
                    finite_max = float(np.max(finite)) if finite.size else 0.0
                    norm = win_data / finite_max if finite_max > 0 else win_data
                    tag = results_dir / mode / input_type / variant / f"{method}_win{int(win)}_{label}_sub.npz"
                    polarization_operator, input_polarization_operators = _polarization_operator_provenance(
                        input_provenance,
                        mode,
                    )
                    np.savez(
                        tag,
                        artifact_schema_version=VESPAGRAM_ARTIFACT_SCHEMA_VERSION,
                        vespagram=norm,
                        support_counts=support_counts[:, t_mask].astype(np.int32),
                        minimum_support=np.asarray(DEFAULT_MIN_STACK_SUPPORT, dtype=np.int32),
                        slowness_axis=s_axis,
                        time_axis=t[t_mask],
                        events=np.array(event_ids, dtype=str),
                        distances=np.array(distances, dtype=float),
                        distance_errors=np.array(distance_errors, dtype=float),
                        mode=mode,
                        input_type=input_type,
                        norm_variant=variant,
                        polarization_operator=np.asarray(polarization_operator, dtype=str),
                        input_polarization_operators=np.asarray(input_polarization_operators, dtype=str),
                        power_window_s=win,
                        sampling_rate_hz=sr,
                        input_trace_sha256=np.asarray([r["trace_sha256"] for r in input_provenance], dtype=str),
                        input_valid_sample_mask_sha256=np.asarray([r["valid_sample_mask_sha256"] for r in input_provenance], dtype=str),
                        input_time_sha256=np.asarray([r["time_sha256"] for r in input_provenance], dtype=str),
                        rotation_metadata_sha256=np.asarray(
                            [r["alignment"]["upstream"]["rotation"]["metadata_sha256"] for r in input_provenance],
                            dtype=str,
                        ),
                        deglitch_run_summary_sha256=np.asarray(
                            [r["alignment"]["upstream"]["rotation"]["metadata"]["deglitch_run_summary_sha256"] for r in input_provenance],
                            dtype=str,
                        ),
                    )

                logger.info("Saved vespagram combo=%s/%s/%s method=%s win=%s", mode, input_type, variant, method, win)


def parse_args():
    parser = argparse.ArgumentParser(description="Run vespagram runs for Paper 0")
    parser.add_argument("--event-table", default=str(repo_path("manifest/event_table.csv")))
    parser.add_argument("--data-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("results/vespagrams")))
    parser.add_argument("--ref-distance", type=float, default=29.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_run(
        Path(args.event_table),
        Path(args.data_dir),
        Path(args.out_dir),
        args.ref_distance,
    )
