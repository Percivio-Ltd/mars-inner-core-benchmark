#!/usr/bin/env python3
"""Compute the frozen P0-DECOY-FAM decoy-box family statistics."""

import argparse
import csv
import datetime
import hashlib
import json
import pathlib

import numpy as np


CARD_ID = "P0-DECOY-FAM"
READ_ONLY_REPO = pathlib.Path("/Users/artuskg/GitRepos/MarsQuake")

PKIKP_CSV_NAME = "decoy_boxes_pkikp.csv"
PKKP_CSV_NAME = "decoy_boxes_pkkp.csv"
SUMMARY_NAME = "decoy_family_summary.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute the frozen MarsQuake P0-DECOY-FAM statistic."
    )
    parser.add_argument("--npz", required=True, help="Absolute path to a vespagram NPZ")
    parser.add_argument("--out-dir", required=True, help="Absolute output directory")
    parser.add_argument(
        "--pkkp-threshold",
        required=True,
        type=float,
        help="Recorded PKKP mirror target-box maximum",
    )
    return parser.parse_args()


def ensure_absolute_outside_repo(path, label, must_exist=False):
    if not path.is_absolute():
        raise ValueError(f"{label} must be an absolute path: {path}")
    if path == READ_ONLY_REPO or READ_ONLY_REPO in path.parents:
        raise ValueError(f"{label} must not be under the read-only MarsQuake repo: {path}")
    resolved = path.resolve(strict=must_exist)
    if resolved == READ_ONLY_REPO or READ_ONLY_REPO in resolved.parents:
        raise ValueError(f"{label} must not be under the read-only MarsQuake repo: {path}")
    return resolved


def scalar_metadata(npz_payload, key):
    array = np.asarray(npz_payload[key])
    if array.size != 1:
        raise ValueError(f"NPZ metadata {key!r} must be scalar; got shape {array.shape}")
    value = array.reshape(-1)[0].item()
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"NPZ metadata {key!r} has unsupported scalar type {type(value).__name__}")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def format_float(value):
    return format(float(value), ".17g")


def json_number_or_none(value):
    value = float(value)
    return value if np.isfinite(value) else None


def box_maximum(
    vespagram,
    supported,
    time_axis,
    slowness_axis,
    t_lo,
    t_hi,
    s_lo,
    s_hi,
):
    # Closed cell-center intervals: left search on lo, right search on hi.
    t_i_lo = int(np.searchsorted(time_axis, t_lo, side="left"))
    t_i_hi = int(np.searchsorted(time_axis, t_hi, side="right"))
    s_i_lo = int(np.searchsorted(slowness_axis, s_lo, side="left"))
    s_i_hi = int(np.searchsorted(slowness_axis, s_hi, side="right"))

    interior_supported = supported[s_i_lo:s_i_hi, t_i_lo:t_i_hi]
    n_supported_cells = int(np.count_nonzero(interior_supported))
    if n_supported_cells == 0:
        return float("nan"), 0

    interior_power = vespagram[s_i_lo:s_i_hi, t_i_lo:t_i_hi]
    box_max_power = float(np.max(interior_power[interior_supported]))
    return box_max_power, n_supported_cells


def statistic(numerator, denominator):
    return {
        "numerator": int(numerator),
        "denominator": int(denominator),
        "fraction": float(numerator / denominator),
    }


def sweep_pkikp(
    csv_path,
    vespagram,
    supported,
    time_axis,
    slowness_axis,
    t_ridge,
    s_ridge,
):
    fieldnames = [
        "t_center",
        "s_center",
        "t_lo",
        "t_hi",
        "s_lo",
        "s_hi",
        "box_max_power",
        "n_supported_cells",
        "overlaps_target_box",
        "contains_ridge_cell",
        "ge_target",
        "ge_ridge",
    ]
    counts = {
        "total": 0,
        "overlaps_target_box": 0,
        "contains_ridge_cell": 0,
        "nan": 0,
        "ge_target_incl": 0,
        "ge_target_excl": 0,
        "target_excl_denominator": 0,
        "ge_ridge_incl": 0,
        "ge_ridge_excl": 0,
        "ridge_excl_denominator": 0,
    }

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fieldnames)

        for i in range(371):
            t_center = float(250 + 5 * i)
            t_lo = t_center - 20.0
            t_hi = t_center + 20.0
            for k in range(89):
                s_center = (-94 + k) / 10.0
                s_lo = s_center - 0.6
                s_hi = s_center + 0.6
                box_max_power, n_supported_cells = box_maximum(
                    vespagram,
                    supported,
                    time_axis,
                    slowness_axis,
                    t_lo,
                    t_hi,
                    s_lo,
                    s_hi,
                )

                # Frozen closed-rectangle overlap with T.
                overlaps_target_box = (
                    (t_center - 20.0 <= 624.0)
                    and (t_center + 20.0 >= 584.0)
                    and (s_center - 0.6 <= -5.9)
                    and (s_center + 0.6 >= -7.1)
                )
                contains_ridge_cell = (
                    abs(t_center - t_ridge) <= 20.0
                    and abs(s_center - s_ridge) <= 0.6
                )
                ge_target = box_max_power >= 0.7736
                ge_ridge = box_max_power >= 0.9327

                counts["total"] += 1
                counts["overlaps_target_box"] += int(overlaps_target_box)
                counts["contains_ridge_cell"] += int(contains_ridge_cell)
                counts["nan"] += int(np.isnan(box_max_power))
                counts["ge_target_incl"] += int(ge_target)
                counts["ge_ridge_incl"] += int(ge_ridge)
                if not overlaps_target_box:
                    counts["target_excl_denominator"] += 1
                    counts["ge_target_excl"] += int(ge_target)
                if not contains_ridge_cell:
                    counts["ridge_excl_denominator"] += 1
                    counts["ge_ridge_excl"] += int(ge_ridge)

                writer.writerow(
                    [
                        format_float(t_center),
                        format_float(s_center),
                        format_float(t_lo),
                        format_float(t_hi),
                        format_float(s_lo),
                        format_float(s_hi),
                        format_float(box_max_power),
                        str(n_supported_cells),
                        str(overlaps_target_box),
                        str(contains_ridge_cell),
                        str(ge_target),
                        str(ge_ridge),
                    ]
                )

    if counts["total"] != 33019:
        raise AssertionError(f"PKiKP box count is {counts['total']}, expected 33019")
    return counts


def sweep_pkkp(
    csv_path,
    vespagram,
    supported,
    time_axis,
    slowness_axis,
    pkkp_threshold,
):
    fieldnames = [
        "t_center",
        "s_center",
        "t_lo",
        "t_hi",
        "s_lo",
        "s_hi",
        "box_max_power",
        "n_supported_cells",
        "overlaps_pkkp_target_box",
        "ge_pkkp",
    ]
    counts = {
        "total": 0,
        "overlaps_pkkp_target_box": 0,
        "nan": 0,
        "ge_pkkp_incl": 0,
        "ge_pkkp_excl": 0,
        "pkkp_excl_denominator": 0,
    }

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(fieldnames)

        for i in range(371):
            t_center = float(250 + 5 * i)
            t_lo = t_center - 20.0
            t_hi = t_center + 20.0
            for k in range(81):
                s_center = (-90 + k) / 10.0
                s_lo = s_center - 1.0
                s_hi = s_center + 1.0
                box_max_power, n_supported_cells = box_maximum(
                    vespagram,
                    supported,
                    time_axis,
                    slowness_axis,
                    t_lo,
                    t_hi,
                    s_lo,
                    s_hi,
                )

                # Frozen closed-rectangle overlap with K.
                overlaps_pkkp_target_box = (
                    (t_center - 20.0 <= 1360.0)
                    and (t_center + 20.0 >= 1320.0)
                    and (s_center - 1.0 <= -6.0)
                    and (s_center + 1.0 >= -8.0)
                )
                ge_pkkp = box_max_power >= pkkp_threshold

                counts["total"] += 1
                counts["overlaps_pkkp_target_box"] += int(overlaps_pkkp_target_box)
                counts["nan"] += int(np.isnan(box_max_power))
                counts["ge_pkkp_incl"] += int(ge_pkkp)
                if not overlaps_pkkp_target_box:
                    counts["pkkp_excl_denominator"] += 1
                    counts["ge_pkkp_excl"] += int(ge_pkkp)

                writer.writerow(
                    [
                        format_float(t_center),
                        format_float(s_center),
                        format_float(t_lo),
                        format_float(t_hi),
                        format_float(s_lo),
                        format_float(s_hi),
                        format_float(box_max_power),
                        str(n_supported_cells),
                        str(overlaps_pkkp_target_box),
                        str(ge_pkkp),
                    ]
                )

    if counts["total"] != 30051:
        raise AssertionError(f"PKKP box count is {counts['total']}, expected 30051")
    return counts


def compute_controls(
    vespagram,
    supported,
    time_axis,
    slowness_axis,
    t_ridge,
    s_ridge,
    power_ridge,
    pkkp_threshold,
):
    p1_value, p1_supported = box_maximum(
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        584.0,
        624.0,
        -7.1,
        -5.9,
    )
    p1_pass = not np.isnan(p1_value) and round(p1_value, 4) == 0.7736

    p2_value, p2_supported = box_maximum(
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        t_ridge - 20.0,
        t_ridge + 20.0,
        s_ridge - 0.6,
        s_ridge + 0.6,
    )
    p2_pass = (
        not np.isnan(p2_value)
        and round(p2_value, 4) == 0.9327
        and p2_value == power_ridge
    )

    a1_value, a1_supported = box_maximum(
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        -90.0,
        -50.0,
        -7.1,
        -5.9,
    )
    a1_pass = np.isnan(a1_value) or a1_value < 0.7736

    s1_value, s1_supported = box_maximum(
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        1320.0,
        1360.0,
        -8.0,
        -6.0,
    )
    s1_pass = (
        not np.isnan(s1_value)
        and round(s1_value, 10) == round(pkkp_threshold, 10)
    )

    controls = {
        "P1_positive": {
            "classification": "frozen_card_control",
            "center": [604.0, -6.5],
            "observed_box_max_power": json_number_or_none(p1_value),
            "observed_box_max_power_text": format_float(p1_value),
            "n_supported_cells": p1_supported,
            "expected_round_4": 0.7736,
            "pass": bool(p1_pass),
        },
        "P2_positive": {
            "classification": "frozen_card_control",
            "center_exact_ridge_cell": [t_ridge, s_ridge],
            "observed_box_max_power": json_number_or_none(p2_value),
            "observed_box_max_power_text": format_float(p2_value),
            "n_supported_cells": p2_supported,
            "expected_round_4": 0.9327,
            "expected_exact_power_ridge": power_ridge,
            "exactly_equals_power_ridge": bool(p2_value == power_ridge),
            "pass": bool(p2_pass),
        },
        "A1_adverse": {
            "classification": "frozen_card_control",
            "center": [-70.0, -6.5],
            "observed_box_max_power": json_number_or_none(a1_value),
            "observed_box_max_power_text": format_float(a1_value),
            "n_supported_cells": a1_supported,
            "expected": "less than 0.7736, or NaN",
            "pass": bool(a1_pass),
        },
        "S1_supplementary": {
            "classification": "supplementary_not_frozen_card_control",
            "center": [1340.0, -7.0],
            "observed_box_max_power": json_number_or_none(s1_value),
            "observed_box_max_power_text": format_float(s1_value),
            "n_supported_cells": s1_supported,
            "pkkp_threshold": pkkp_threshold,
            "pkkp_threshold_text": format_float(pkkp_threshold),
            "comparison": "round(observed, 10) == round(pkkp_threshold, 10)",
            "pass": bool(s1_pass),
        },
    }
    return controls


def print_summary(gate, controls, box_counts, family_statistics):
    observed = gate["observed_exact_cell"]
    print(
        "gate: "
        f"{'PASS' if gate['pass'] else 'FAIL'} "
        f"t={format_float(observed['time_s'])} "
        f"s={format_float(observed['slowness_s_per_deg'])} "
        f"power={format_float(observed['power'])} "
        f"support={observed['support_count']}"
    )
    for name in ("P1_positive", "P2_positive", "A1_adverse", "S1_supplementary"):
        control = controls[name]
        print(
            f"{name}: {'PASS' if control['pass'] else 'FAIL'} "
            f"max={control['observed_box_max_power_text']} "
            f"supported={control['n_supported_cells']}"
        )
    pkikp = box_counts["pkikp"]
    pkkp = box_counts["pkkp"]
    print(
        "PKiKP boxes: "
        f"total={pkikp['total']} target_overlap={pkikp['overlaps_target_box']} "
        f"ridge_contains={pkikp['contains_ridge_cell']} nan={pkikp['nan']}"
    )
    print(
        "PKKP boxes: "
        f"total={pkkp['total']} target_overlap={pkkp['overlaps_pkkp_target_box']} "
        f"nan={pkkp['nan']}"
    )
    for name in (
        "F_decoy_target_incl",
        "F_decoy_target_excl",
        "F_decoy_ridge_incl",
        "F_decoy_ridge_excl",
        "F_decoy_pkkp_incl",
        "F_decoy_pkkp_excl",
    ):
        item = family_statistics[name]
        print(
            f"{name}: {item['numerator']}/{item['denominator']} "
            f"= {format_float(item['fraction'])}"
        )


def main():
    args = parse_args()
    npz_argument = pathlib.Path(args.npz)
    out_dir_argument = pathlib.Path(args.out_dir)
    npz_path = ensure_absolute_outside_repo(npz_argument, "--npz", must_exist=True)
    out_dir = ensure_absolute_outside_repo(out_dir_argument, "--out-dir")
    if not npz_path.is_file():
        raise ValueError(f"--npz is not a file: {npz_path}")
    if not np.isfinite(args.pkkp_threshold):
        raise ValueError("--pkkp-threshold must be finite")
    pkkp_threshold = float(args.pkkp_threshold)

    out_dir.mkdir(parents=True, exist_ok=True)
    pkikp_csv_path = out_dir / PKIKP_CSV_NAME
    pkkp_csv_path = out_dir / PKKP_CSV_NAME
    summary_path = out_dir / SUMMARY_NAME
    for output_path in (pkikp_csv_path, pkkp_csv_path, summary_path):
        ensure_absolute_outside_repo(output_path, "output path")

    metadata_keys = (
        "mode",
        "input_type",
        "norm_variant",
        "stack_method",
        "power_window_s",
        "polarization_operator",
        "minimum_support",
    )
    required_keys = (
        "vespagram",
        "support_counts",
        "slowness_axis",
        "time_axis",
    ) + metadata_keys

    npz_sha256 = sha256_file(npz_path)
    with np.load(npz_path, allow_pickle=False) as npz_payload:
        missing = [key for key in required_keys if key not in npz_payload.files]
        if missing:
            raise ValueError(f"NPZ is missing required keys: {', '.join(missing)}")
        vespagram = np.asarray(npz_payload["vespagram"])
        support_counts = np.asarray(npz_payload["support_counts"])
        slowness_axis = np.asarray(npz_payload["slowness_axis"])
        time_axis = np.asarray(npz_payload["time_axis"])
        metadata = {key: scalar_metadata(npz_payload, key) for key in metadata_keys}

    if vespagram.ndim != 2:
        raise ValueError(f"vespagram must be two-dimensional; got shape {vespagram.shape}")
    if not np.issubdtype(vespagram.dtype, np.floating):
        raise ValueError(f"vespagram must have floating dtype; got {vespagram.dtype}")
    if support_counts.shape != vespagram.shape:
        raise ValueError(
            "support_counts shape must match vespagram shape; "
            f"got {support_counts.shape} and {vespagram.shape}"
        )
    if not np.issubdtype(support_counts.dtype, np.integer):
        raise ValueError(f"support_counts must have integer dtype; got {support_counts.dtype}")
    if time_axis.ndim != 1 or slowness_axis.ndim != 1:
        raise ValueError("time_axis and slowness_axis must be one-dimensional")
    if vespagram.shape != (slowness_axis.size, time_axis.size):
        raise ValueError(
            "vespagram shape must be (len(slowness_axis), len(time_axis)); "
            f"got {vespagram.shape}"
        )
    if time_axis.size == 0 or slowness_axis.size == 0:
        raise ValueError("time_axis and slowness_axis must be nonempty")
    if not np.all(np.isfinite(time_axis)) or not np.all(np.diff(time_axis) > 0):
        raise ValueError("time_axis must be finite and strictly ascending")
    if not np.all(np.isfinite(slowness_axis)) or not np.all(np.diff(slowness_axis) > 0):
        raise ValueError("slowness_axis must be finite and strictly ascending")

    minimum_support_raw = metadata["minimum_support"]
    minimum_support = int(minimum_support_raw)
    if minimum_support != minimum_support_raw:
        raise ValueError("minimum_support metadata must be an integer scalar")
    metadata["minimum_support"] = minimum_support

    # This is the exact supported-power surface used by detect_peaks.py.
    supported = np.isfinite(vespagram) & (support_counts >= int(minimum_support))

    # Frozen in-script gate: this assertion occurs before every box/control sweep.
    gate_time_columns = (time_axis >= 550.0) & (time_axis <= 700.0)
    gate_mask = supported & gate_time_columns[np.newaxis, :]
    if not np.any(gate_mask):
        raise AssertionError("Gate window [550.0, 700.0] contains no supported cells")
    gate_surface = np.where(gate_mask, vespagram, -np.inf)
    gate_flat_index = int(np.argmax(gate_surface))
    ridge_s_index, ridge_t_index = np.unravel_index(gate_flat_index, vespagram.shape)
    t_ridge = float(time_axis[ridge_t_index])
    s_ridge = float(slowness_axis[ridge_s_index])
    power_ridge = float(vespagram[ridge_s_index, ridge_t_index])
    ridge_support_count = int(support_counts[ridge_s_index, ridge_t_index])
    gate_pass = (
        round(t_ridge, 2) == 663.80
        and round(s_ridge, 4) == -3.6364
        and round(power_ridge, 4) == 0.9327
        and ridge_support_count == 23
    )
    if not gate_pass:
        raise AssertionError(
            "Frozen gate failed: observed exact cell "
            f"(t={format_float(t_ridge)}, s={format_float(s_ridge)}, "
            f"power={format_float(power_ridge)}, support={ridge_support_count})"
        )

    gate = {
        "time_window_closed_s": [550.0, 700.0],
        "expected_tuple": [663.80, -3.6364, 0.9327, 23],
        "expected_tuple_fields": [
            "round(time_s, 2)",
            "round(slowness_s_per_deg, 4)",
            "round(power, 4)",
            "support_count",
        ],
        "observed_exact_cell": {
            "time_s": t_ridge,
            "slowness_s_per_deg": s_ridge,
            "power": power_ridge,
            "support_count": ridge_support_count,
            "slowness_index": int(ridge_s_index),
            "time_index": int(ridge_t_index),
        },
        "pass": bool(gate_pass),
    }

    controls = compute_controls(
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        t_ridge,
        s_ridge,
        power_ridge,
        pkkp_threshold,
    )
    pkikp_counts = sweep_pkikp(
        pkikp_csv_path,
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        t_ridge,
        s_ridge,
    )
    pkkp_counts = sweep_pkkp(
        pkkp_csv_path,
        vespagram,
        supported,
        time_axis,
        slowness_axis,
        pkkp_threshold,
    )

    family_statistics = {
        "F_decoy_target_incl": statistic(
            pkikp_counts["ge_target_incl"], pkikp_counts["total"]
        ),
        "F_decoy_target_excl": statistic(
            pkikp_counts["ge_target_excl"],
            pkikp_counts["target_excl_denominator"],
        ),
        "F_decoy_ridge_incl": statistic(
            pkikp_counts["ge_ridge_incl"], pkikp_counts["total"]
        ),
        "F_decoy_ridge_excl": statistic(
            pkikp_counts["ge_ridge_excl"],
            pkikp_counts["ridge_excl_denominator"],
        ),
        "F_decoy_pkkp_incl": statistic(
            pkkp_counts["ge_pkkp_incl"], pkkp_counts["total"]
        ),
        "F_decoy_pkkp_excl": statistic(
            pkkp_counts["ge_pkkp_excl"],
            pkkp_counts["pkkp_excl_denominator"],
        ),
    }

    box_counts = {
        "pkikp": {
            "total": pkikp_counts["total"],
            "overlaps_target_box": pkikp_counts["overlaps_target_box"],
            "contains_ridge_cell": pkikp_counts["contains_ridge_cell"],
            "nan": pkikp_counts["nan"],
        },
        "pkkp": {
            "total": pkkp_counts["total"],
            "overlaps_pkkp_target_box": pkkp_counts["overlaps_pkkp_target_box"],
            "nan": pkkp_counts["nan"],
        },
    }
    summary = {
        "card_id": CARD_ID,
        "utc_timestamp": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "npz": {
            "path": str(npz_path),
            "sha256": npz_sha256,
        },
        "npz_metadata": metadata,
        "grid": {
            "shape": [int(vespagram.shape[0]), int(vespagram.shape[1])],
            "slowness_axis_span": [
                float(slowness_axis[0]),
                float(slowness_axis[-1]),
            ],
            "time_axis_span_s": [float(time_axis[0]), float(time_axis[-1])],
        },
        "gate": gate,
        "thresholds": {
            "pkikp_target": 0.7736,
            "pkikp_ridge": 0.9327,
            "pkkp": pkkp_threshold,
        },
        "box_counts": box_counts,
        "family_statistics": family_statistics,
        "controls": controls,
        "csv_sha256": {
            PKIKP_CSV_NAME: sha256_file(pkikp_csv_path),
            PKKP_CSV_NAME: sha256_file(pkkp_csv_path),
        },
    }
    with summary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")

    print_summary(gate, controls, box_counts, family_statistics)

    failed_frozen_controls = [
        name
        for name in ("P1_positive", "P2_positive", "A1_adverse")
        if not controls[name]["pass"]
    ]
    if failed_frozen_controls:
        raise AssertionError(
            "Frozen controls failed after summary JSON was written: "
            + ", ".join(failed_frozen_controls)
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
