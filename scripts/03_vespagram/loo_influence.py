from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import (
    infer_nominal_sample_rate_hz,
    load_event_table,
    repo_path,
    sha256_file,
)
from scripts.shared import import_local_module

run_vespagrams = import_local_module(
    "marsquake_run_vespagrams_for_loo",
    "scripts/03_vespagram/run_vespagrams.py",
)
detect_peaks = import_local_module(
    "marsquake_detect_peaks_for_loo",
    "scripts/03_vespagram/detect_peaks.py",
)

ARTIFACT_SCHEMA_VERSION = "paper0-loo-influence-v2"
REGISTERED_EVENT_COUNT = 23
BRANCH_BOUNDARY_S = 632.0

REGISTERED_MODE = "paperfaith"
REGISTERED_INPUT_TYPE = "envelope"
REGISTERED_NORM_VARIANT = "A"
REGISTERED_STACK_METHOD = "nth_root"
REGISTERED_POWER_WINDOW_S = 20.0
REGISTERED_POLARIZATION_OPERATOR = "montalbetti_kanasewich_1970"
REGISTERED_LANE = {
    "input_type": REGISTERED_INPUT_TYPE,
    "mode": REGISTERED_MODE,
    "norm_variant": REGISTERED_NORM_VARIANT,
    "polarization_operator": REGISTERED_POLARIZATION_OPERATOR,
    "power_window_s": REGISTERED_POWER_WINDOW_S,
    "stack_method": REGISTERED_STACK_METHOD,
}

# These are the fixed parameters used by run_vespagrams.run_run.
PRODUCTION_REF_DISTANCE_DEG = 29.0
PRODUCTION_SLOWNESS_MIN_SDEG = -10.0
PRODUCTION_SLOWNESS_MAX_SDEG = 0.0
PRODUCTION_SLOWNESS_STEPS = 100
PRODUCTION_NTH_ROOT_ORDER = 4
PRODUCTION_MIN_STACK_SUPPORT = run_vespagrams.DEFAULT_MIN_STACK_SUPPORT

# The full-precision slowness value identifies the registered -3.64 s/deg grid cell.
EXPECTED_FULL_SET_TIME_S = 663.8
EXPECTED_FULL_SET_SLOWNESS_SDEG = -3.6363636363636367


def validate_registered_lane(
    *,
    mode: str,
    input_type: str,
    norm_variant: str,
    stack_method: str,
    power_window_s: float,
    polarization_operator: str,
) -> None:
    observed = {
        "input_type": input_type,
        "mode": mode,
        "norm_variant": norm_variant,
        "polarization_operator": polarization_operator,
        "power_window_s": float(power_window_s),
        "stack_method": stack_method,
    }
    mismatches = [
        f"{key}={observed[key]!r} (required {expected!r})"
        for key, expected in REGISTERED_LANE.items()
        if observed[key] != expected
    ]
    if mismatches:
        raise ValueError(
            "Registered lane is frozen; refusing CLI override(s): "
            + ", ".join(mismatches)
        )


def validate_output_directory(out_dir: Path) -> Path:
    resolved = Path(out_dir).expanduser().resolve()
    results_root = repo_path("results").resolve()
    if resolved == results_root or results_root in resolved.parents:
        raise ValueError(
            f"--out-dir must not be results/ or a descendant of it: {resolved}"
        )
    return resolved


def exclude_loaded_event(loaded: tuple, hold_out: str | None) -> tuple:
    (
        event_ids,
        traces,
        valid_masks,
        distances,
        distance_errors,
        time_axis,
        provenance_records,
    ) = loaded
    parallel: tuple[Sequence, ...] = (
        traces,
        valid_masks,
        distances,
        distance_errors,
        provenance_records,
    )
    if any(len(values) != len(event_ids) for values in parallel):
        raise ValueError("Loaded event arrays do not have matching lengths")

    if hold_out is None:
        keep = list(range(len(event_ids)))
    else:
        matches = [index for index, event_id in enumerate(event_ids) if event_id == hold_out]
        if not matches:
            raise ValueError(
                f"Held-out event ID {hold_out!r} does not exist in the registered event set"
            )
        if len(matches) != 1:
            raise ValueError(
                f"Held-out event ID {hold_out!r} is not unique in the registered event set"
            )
        keep = [index for index in range(len(event_ids)) if index != matches[0]]

    selected = tuple([[values[index] for index in keep] for values in (event_ids, *parallel)])
    return (*selected[:5], time_axis, selected[5])


def extract_global_argmax(
    field: np.ndarray,
    time_axis: np.ndarray,
    slowness_axis: np.ndarray,
    support_counts: np.ndarray,
) -> dict[str, object]:
    values = np.asarray(field, dtype=np.float64)
    time = np.asarray(time_axis, dtype=np.float64)
    slowness = np.asarray(slowness_axis, dtype=np.float64)
    support = np.asarray(support_counts)
    if values.ndim != 2:
        raise ValueError("Vespagram field must be two-dimensional")
    if values.shape != (slowness.size, time.size):
        raise ValueError("Vespagram field shape does not match its grid axes")
    if support.shape != values.shape:
        raise ValueError("Support-count shape does not match the vespagram field")

    peak_result = detect_peaks.find_global_peak(
        values,
        time,
        slowness,
        *detect_peaks.PKIKP_WINDOW,
        support,
        PRODUCTION_MIN_STACK_SUPPORT,
    )
    peak_status = str(peak_result["status"])
    if peak_status != "ok":
        raise RuntimeError(
            "Production PKiKP peak selection failed: "
            f"status={peak_status!r}, "
            f"excluded_reason={peak_result['excluded_reason']!r}"
        )
    return {
        "power": float(peak_result["power"]),
        "slowness_sdeg": float(peak_result["slowness"]),
        "status": peak_status,
        "support_count": int(peak_result["support_count"]),
        "time_s": float(peak_result["time"]),
    }


def classify_branch(time_s: float) -> str:
    return "602-family" if float(time_s) < BRANCH_BOUNDARY_S else "662-family"


def _validate_loaded_inputs(
    event_ids: Sequence[str],
    input_provenance: list[dict],
) -> None:
    if len(event_ids) != REGISTERED_EVENT_COUNT:
        raise RuntimeError(
            "Registered full set must contain exactly "
            f"{REGISTERED_EVENT_COUNT} events; loaded {len(event_ids)}"
        )
    operator, per_event_operators = run_vespagrams._polarization_operator_provenance(
        input_provenance,
        REGISTERED_MODE,
    )
    if (
        operator != REGISTERED_POLARIZATION_OPERATOR
        or len(per_event_operators) != len(event_ids)
        or any(
            value != REGISTERED_POLARIZATION_OPERATOR
            for value in per_event_operators
        )
    ):
        raise RuntimeError(
            "Registered polarization operator mismatch: "
            f"required {REGISTERED_POLARIZATION_OPERATOR!r}, observed {operator!r}"
        )


def _identity_arrays(input_provenance: list[dict]) -> dict[str, np.ndarray]:
    return {
        "input_trace_paths": np.asarray(
            [record["trace_path"] for record in input_provenance],
            dtype=str,
        ),
        "input_trace_sha256": np.asarray(
            [record["trace_sha256"] for record in input_provenance],
            dtype=str,
        ),
        "input_valid_sample_mask_paths": np.asarray(
            [record["valid_sample_mask_path"] for record in input_provenance],
            dtype=str,
        ),
        "input_valid_sample_mask_sha256": np.asarray(
            [record["valid_sample_mask_sha256"] for record in input_provenance],
            dtype=str,
        ),
        "input_time_paths": np.asarray(
            [record["time_path"] for record in input_provenance],
            dtype=str,
        ),
        "input_time_sha256": np.asarray(
            [record["time_sha256"] for record in input_provenance],
            dtype=str,
        ),
        "normalization_metadata_paths": np.asarray(
            [record["normalization_metadata_path"] for record in input_provenance],
            dtype=str,
        ),
        "normalization_metadata_sha256": np.asarray(
            [record["normalization_metadata_sha256"] for record in input_provenance],
            dtype=str,
        ),
        "alignment_metadata_paths": np.asarray(
            [record["alignment"]["metadata_path"] for record in input_provenance],
            dtype=str,
        ),
        "alignment_metadata_sha256": np.asarray(
            [record["alignment"]["metadata_sha256"] for record in input_provenance],
            dtype=str,
        ),
        "rotation_metadata_paths": np.asarray(
            [
                record["alignment"]["upstream"]["rotation"]["metadata_path"]
                for record in input_provenance
            ],
            dtype=str,
        ),
        "rotation_metadata_sha256": np.asarray(
            [
                record["alignment"]["upstream"]["rotation"]["metadata_sha256"]
                for record in input_provenance
            ],
            dtype=str,
        ),
        "deglitch_run_summary_sha256": np.asarray(
            [
                record["alignment"]["upstream"]["rotation"]["metadata"][
                    "deglitch_run_summary_sha256"
                ]
                for record in input_provenance
            ],
            dtype=str,
        ),
    }


def _write_outputs(
    *,
    out_dir: Path,
    hold_out: str | None,
    field: np.ndarray,
    support_counts: np.ndarray,
    slowness_axis: np.ndarray,
    time_axis: np.ndarray,
    event_ids: list[str],
    distances: list[float],
    distance_errors: list[float],
    input_provenance: list[dict],
    event_table: Path,
    sampling_rate_hz: float,
    global_argmax: dict[str, object],
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "full_set" if hold_out is None else f"hold_out_{hold_out}"
    npz_path = out_dir / f"{stem}.npz"
    json_path = out_dir / f"{stem}.json"

    np.savez(
        npz_path,
        artifact_schema_version=np.asarray(ARTIFACT_SCHEMA_VERSION, dtype=str),
        field=np.asarray(field, dtype=np.float64),
        support_counts=np.asarray(support_counts, dtype=np.int32),
        minimum_support=np.asarray(PRODUCTION_MIN_STACK_SUPPORT, dtype=np.int32),
        peak_result_status=np.asarray(global_argmax["status"], dtype=str),
        peak_window_s=np.asarray(detect_peaks.PKIKP_WINDOW, dtype=np.float64),
        slowness_axis=np.asarray(slowness_axis, dtype=np.float64),
        time_axis=np.asarray(time_axis, dtype=np.float64),
        events=np.asarray(event_ids, dtype=str),
        distances=np.asarray(distances, dtype=np.float64),
        distance_errors=np.asarray(distance_errors, dtype=np.float64),
        held_out_event=np.asarray(hold_out or "", dtype=str),
        lane_json=np.asarray(
            json.dumps(REGISTERED_LANE, sort_keys=True, separators=(",", ":")),
            dtype=str,
        ),
        event_table_path=np.asarray(str(event_table), dtype=str),
        event_table_sha256=np.asarray(sha256_file(event_table), dtype=str),
        ref_distance_deg=np.asarray(PRODUCTION_REF_DISTANCE_DEG, dtype=np.float64),
        sampling_rate_hz=np.asarray(sampling_rate_hz, dtype=np.float64),
        slowness_min_sdeg=np.asarray(
            PRODUCTION_SLOWNESS_MIN_SDEG,
            dtype=np.float64,
        ),
        slowness_max_sdeg=np.asarray(
            PRODUCTION_SLOWNESS_MAX_SDEG,
            dtype=np.float64,
        ),
        slowness_steps=np.asarray(PRODUCTION_SLOWNESS_STEPS, dtype=np.int32),
        nth_root_order=np.asarray(PRODUCTION_NTH_ROOT_ORDER, dtype=np.int32),
        **_identity_arrays(input_provenance),
    )
    summary = {
        "branch": classify_branch(global_argmax["time_s"]),
        "global_argmax": global_argmax,
        "held_out_event": hold_out,
        "lane": REGISTERED_LANE,
        "minimum_support": PRODUCTION_MIN_STACK_SUPPORT,
        "peak_result_status": global_argmax["status"],
        "peak_window_s": [float(value) for value in detect_peaks.PKIKP_WINDOW],
    }
    json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return npz_path, json_path


def run_loo(
    *,
    hold_out: str | None,
    out_dir: Path,
    data_dir: Path,
) -> tuple[dict[str, object], Path, Path]:
    event_table = repo_path("manifest/event_table.csv").resolve()
    events = load_event_table(event_table)

    # Loading the complete set first preserves every production provenance gate,
    # including the held-out event's input checks.
    loaded = run_vespagrams.load_combo_data(
        events,
        REGISTERED_MODE,
        REGISTERED_NORM_VARIANT,
        REGISTERED_INPUT_TYPE,
        Path(data_dir),
    )
    _validate_loaded_inputs(loaded[0], loaded[6])
    (
        event_ids,
        traces,
        valid_masks,
        distances,
        distance_errors,
        time_axis,
        input_provenance,
    ) = exclude_loaded_event(loaded, hold_out)

    expected_selected_count = (
        REGISTERED_EVENT_COUNT if hold_out is None else REGISTERED_EVENT_COUNT - 1
    )
    if len(event_ids) != expected_selected_count:
        raise RuntimeError(
            f"Expected {expected_selected_count} selected events; got {len(event_ids)}"
        )

    sampling_rate_hz = infer_nominal_sample_rate_hz(time_axis)
    field, slowness_axis, returned_time_axis, support_counts = (
        run_vespagrams.compute_vespagram(
            traces=traces,
            valid_masks=valid_masks,
            distances=distances,
            ref_distance=PRODUCTION_REF_DISTANCE_DEG,
            sampling_rate_hz=sampling_rate_hz,
            time_axis=time_axis,
            slowness_min=PRODUCTION_SLOWNESS_MIN_SDEG,
            slowness_max=PRODUCTION_SLOWNESS_MAX_SDEG,
            slowness_steps=PRODUCTION_SLOWNESS_STEPS,
            stack_method=REGISTERED_STACK_METHOD,
            n=PRODUCTION_NTH_ROOT_ORDER,
            power_window_s=REGISTERED_POWER_WINDOW_S,
            min_support=PRODUCTION_MIN_STACK_SUPPORT,
        )
    )
    global_argmax = extract_global_argmax(
        field,
        returned_time_axis,
        slowness_axis,
        support_counts,
    )
    if hold_out is None and (
        global_argmax["time_s"] != EXPECTED_FULL_SET_TIME_S
        or global_argmax["slowness_sdeg"] != EXPECTED_FULL_SET_SLOWNESS_SDEG
    ):
        raise RuntimeError(
            "Full-set positive control failed: expected exact grid cell "
            f"({EXPECTED_FULL_SET_TIME_S:.2f} s, "
            f"{EXPECTED_FULL_SET_SLOWNESS_SDEG:.17g} s/deg), observed "
            f"({global_argmax['time_s']:.17g} s, "
            f"{global_argmax['slowness_sdeg']:.17g} s/deg)"
        )

    npz_path, json_path = _write_outputs(
        out_dir=out_dir,
        hold_out=hold_out,
        field=field,
        support_counts=support_counts,
        slowness_axis=slowness_axis,
        time_axis=returned_time_axis,
        event_ids=event_ids,
        distances=distances,
        distance_errors=distance_errors,
        input_provenance=input_provenance,
        event_table=event_table,
        sampling_rate_hz=sampling_rate_hz,
        global_argmax=global_argmax,
    )
    return global_argmax, npz_path, json_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one registered Paper 0 leave-one-out vespagram restack",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--hold-out", metavar="EVENT_ID")
    selection.add_argument("--full-set", action="store_true")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=repo_path("data/processed"),
    )
    parser.add_argument("--mode", default=REGISTERED_MODE)
    parser.add_argument("--input-type", default=REGISTERED_INPUT_TYPE)
    parser.add_argument("--norm-variant", default=REGISTERED_NORM_VARIANT)
    parser.add_argument("--stack-method", default=REGISTERED_STACK_METHOD)
    parser.add_argument(
        "--power-window-s",
        default=REGISTERED_POWER_WINDOW_S,
        type=float,
    )
    parser.add_argument(
        "--polarization-operator",
        default=REGISTERED_POLARIZATION_OPERATOR,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        validate_registered_lane(
            mode=args.mode,
            input_type=args.input_type,
            norm_variant=args.norm_variant,
            stack_method=args.stack_method,
            power_window_s=args.power_window_s,
            polarization_operator=args.polarization_operator,
        )
        out_dir = validate_output_directory(args.out_dir)
        global_argmax, npz_path, json_path = run_loo(
            hold_out=None if args.full_set else args.hold_out,
            out_dir=out_dir,
            data_dir=args.data_dir,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "branch": classify_branch(global_argmax["time_s"]),
                "global_argmax": global_argmax,
                "json": str(json_path),
                "npz": str(npz_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
