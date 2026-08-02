#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import numpy as np


REPO_ROOT = "/Users/artuskg/GitRepos/MarsQuake"
sys.path.insert(0, REPO_ROOT)

from scripts.shared import (  # noqa: E402
    import_local_module,
    infer_nominal_sample_rate_hz,
    load_event_table,
)


compute_mod = import_local_module(
    "marsquake_compute_vespagram",
    "scripts/03_vespagram/compute_vespagram.py",
)
detect_mod = import_local_module(
    "marsquake_detect_peaks",
    "scripts/03_vespagram/detect_peaks.py",
)
vesp_mod = import_local_module(
    "marsquake_run_vespagrams",
    "scripts/03_vespagram/run_vespagrams.py",
)
stack_mod = import_local_module(
    "marsquake_stacking",
    "scripts/03_vespagram/stacking.py",
)


DEFAULT_DATA_DIR = Path("/Users/artuskg/marsquake_runs/20260801_mars_scramble")
DEFAULT_EVENT_TABLE = Path("/Users/artuskg/GitRepos/MarsQuake/manifest/event_table.csv")
SEED_BASE = 20260801
EVENT_COUNT = 23

REF_DISTANCE = 29.0
SLOWNESS_MIN = -10.0
SLOWNESS_MAX = 0.0
SLOWNESS_STEPS = 100
STACK_METHOD = "nth_root"
NTH_ROOT_N = 4
POWER_WINDOW_S = 20.0

OUTPUT_COLUMNS = (
    "realization",
    "seed",
    "permutation",
    "argmax_time_s",
    "argmax_slowness_sdeg",
    "argmax_power",
    "argmax_support",
    "argmax_status",
    "target_box_max_power",
    "target_box_time_s",
    "target_box_slowness_sdeg",
    "target_box_support",
    "target_box_status",
)


def parse_realizations(spec: str) -> list[int]:
    """Parse the frozen realization selection syntax while preserving order."""
    realizations: list[int] = []
    tokens = spec.split(",")
    if not tokens or any(not token.strip() for token in tokens):
        raise argparse.ArgumentTypeError("realizations must be a nonempty comma-separated list")

    for raw_token in tokens:
        token = raw_token.strip()
        if token == "identity":
            realizations.append(0)
            continue

        range_match = re.fullmatch(r"([0-9]+)-([0-9]+)", token)
        if range_match is not None:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            if start < 1 or end < 1 or start > end:
                raise argparse.ArgumentTypeError(
                    f"invalid realization range {token!r}: require 1 <= A <= B"
                )
            realizations.extend(range(start, end + 1))
            continue

        if re.fullmatch(r"[0-9]+", token) is not None:
            realization = int(token)
            if realization >= 1:
                realizations.append(realization)
                continue

        raise argparse.ArgumentTypeError(
            f"invalid realization token {token!r}: use identity, A-B, or an integer >= 1"
        )

    return realizations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the frozen Mars PKiKP event-distance scramble null."
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--event-table", type=Path, default=DEFAULT_EVENT_TABLE)
    parser.add_argument("--out-csv", type=Path, required=True)
    parser.add_argument(
        "--realizations",
        type=parse_realizations,
        default=parse_realizations("identity,1-200"),
        help='comma-separated tokens: "identity", "A-B", or an integer >= 1',
    )
    parser.add_argument("--dump-grid-prefix", type=Path)
    parser.add_argument("--dump-shifts-prefix", type=Path)
    return parser.parse_args(argv)


def assert_frozen_constants() -> dict:
    assert compute_mod.DEFAULT_MIN_STACK_SUPPORT == 2, (
        "authority mismatch: compute_mod.DEFAULT_MIN_STACK_SUPPORT must equal 2"
    )
    assert detect_mod.PKIKP_WINDOW == (550.0, 700.0), (
        "authority mismatch: detect_mod.PKIKP_WINDOW must equal (550.0, 700.0)"
    )

    box = detect_mod.PKIKP_PUBLISHED_TARGET_BOX
    assert box["t_min"] == 584.0, "authority mismatch: target-box t_min must equal 584.0"
    assert box["t_max"] == 624.0, "authority mismatch: target-box t_max must equal 624.0"
    assert box["s_min"] == -7.1, "authority mismatch: target-box s_min must equal -7.1"
    assert box["s_max"] == -5.9, "authority mismatch: target-box s_max must equal -5.9"

    assert (
        REF_DISTANCE,
        SLOWNESS_MIN,
        SLOWNESS_MAX,
        SLOWNESS_STEPS,
        STACK_METHOD,
        NTH_ROOT_N,
        POWER_WINDOW_S,
    ) == (29.0, -10.0, 0.0, 100, "nth_root", 4, 20.0), (
        "frozen stack constants do not match the registered card"
    )
    return box


def permutation_for(realization: int) -> tuple[str | int, np.ndarray]:
    identity = np.arange(EVENT_COUNT)
    if realization == 0:
        return "", identity

    seed = SEED_BASE + realization
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(EVENT_COUNT)
    while np.array_equal(permutation, identity):
        permutation = rng.permutation(EVENT_COUNT)
    return seed, permutation


def format_float(value: object) -> str:
    number = float(value)
    if not np.isfinite(number):
        return "nan"
    return format(number, ".17g")


def dump_shift_table(
    prefix: Path,
    realization: int,
    event_ids: list[str],
    assigned_distances: np.ndarray,
    slowness_axis: np.ndarray,
    sampling_rate_hz: float,
) -> None:
    assert len(slowness_axis) == SLOWNESS_STEPS, (
        f"authority mismatch: expected {SLOWNESS_STEPS} slowness values, "
        f"got {len(slowness_axis)}"
    )
    rolls_by_slowness = []
    for slowness in slowness_axis:
        rolls = stack_mod.zero_padded_shifted_stack_index(
            assigned_distances,
            REF_DISTANCE,
            slowness,
            sampling_rate_hz,
        )
        rolls = np.asarray(rolls)
        assert rolls.shape == (EVENT_COUNT,), (
            "authority mismatch: shifted-stack index returned an unexpected shape"
        )
        rolls_by_slowness.append(rolls)

    path = Path(f"{prefix}_r{realization:03d}_shifts.csv")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["trace_index", "event_id", "assigned_distance_deg"]
            + [f"roll_s{k:03d}" for k in range(SLOWNESS_STEPS)]
        )
        for trace_index, event_id in enumerate(event_ids):
            writer.writerow(
                [
                    trace_index,
                    event_id,
                    format_float(assigned_distances[trace_index]),
                    *[
                        int(rolls_by_slowness[k][trace_index])
                        for k in range(SLOWNESS_STEPS)
                    ],
                ]
            )


def write_results_atomically(path: Path, rows: list[dict[str, object]]) -> None:
    temporary_path = Path(f"{path}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary_path, path)


def progress_line(realization: int, argmax: dict, target_box_peak: dict) -> str:
    return (
        f"r{realization} argmax=("
        f"{float(argmax['time']):.3f},"
        f"{float(argmax['slowness']):.3f},"
        f"{float(argmax['power']):.6g},"
        f"{int(argmax['support_count'])}) "
        f"box={float(target_box_peak['power']):.6g}"
    )


def run(args: argparse.Namespace) -> None:
    box = assert_frozen_constants()
    minimum_support = compute_mod.DEFAULT_MIN_STACK_SUPPORT
    full_window = detect_mod.PKIKP_WINDOW

    events = load_event_table(Path(args.event_table))
    (
        event_ids,
        traces,
        valid_masks,
        distances,
        _distance_errors,
        time_axis,
        _provenance_records,
    ) = vesp_mod.load_combo_data(
        events,
        "paperfaith",
        "A",
        "envelope",
        Path(args.data_dir),
    )

    assert len(event_ids) == EVENT_COUNT, (
        f"input mismatch: expected {EVENT_COUNT} vespagram events, got {len(event_ids)}"
    )
    sampling_rate_hz = infer_nominal_sample_rate_hz(time_axis)
    assert sampling_rate_hz == 20.0, (
        f"input mismatch: expected 20.0 Hz nominal sample rate, got {sampling_rate_hz!r}"
    )
    base = np.asarray(distances, dtype=np.float64)
    assert base.shape == (EVENT_COUNT,), (
        f"input mismatch: expected {EVENT_COUNT} distances, got shape {base.shape}"
    )

    result_rows: list[dict[str, object]] = []
    for realization in args.realizations:
        seed, permutation = permutation_for(realization)
        assigned_distances = base[permutation]

        vespagram, slowness_axis, grid_time_axis, support_counts = (
            compute_mod.compute_vespagram(
                traces=traces,
                valid_masks=valid_masks,
                distances=assigned_distances,
                ref_distance=REF_DISTANCE,
                sampling_rate_hz=sampling_rate_hz,
                time_axis=time_axis,
                slowness_min=SLOWNESS_MIN,
                slowness_max=SLOWNESS_MAX,
                slowness_steps=SLOWNESS_STEPS,
                stack_method=STACK_METHOD,
                n=NTH_ROOT_N,
                pw_order=None,
                power_window_s=POWER_WINDOW_S,
                min_support=minimum_support,
            )
        )

        argmax = detect_mod.find_global_peak(
            vespagram,
            grid_time_axis,
            slowness_axis,
            full_window[0],
            full_window[1],
            support_counts,
            minimum_support,
        )
        target_box_mask = detect_mod.neighborhood_mask(
            slowness_axis,
            grid_time_axis,
            box["s_min"],
            box["s_max"],
            box["t_min"],
            box["t_max"],
        )
        target_box_peak = detect_mod._find_peak_in_mask(
            vespagram,
            grid_time_axis,
            slowness_axis,
            target_box_mask,
            support_counts,
            minimum_support,
        )

        if args.dump_grid_prefix is not None:
            np.save(
                Path(f"{args.dump_grid_prefix}_r{realization:03d}_vesp.npy"),
                vespagram,
            )
            np.save(
                Path(f"{args.dump_grid_prefix}_r{realization:03d}_support.npy"),
                support_counts,
            )

        if args.dump_shifts_prefix is not None:
            dump_shift_table(
                args.dump_shifts_prefix,
                realization,
                event_ids,
                assigned_distances,
                slowness_axis,
                sampling_rate_hz,
            )

        result_rows.append(
            {
                "realization": realization,
                "seed": seed,
                "permutation": json.dumps(
                    permutation.tolist(),
                    separators=(",", ":"),
                ),
                "argmax_time_s": format_float(argmax["time"]),
                "argmax_slowness_sdeg": format_float(argmax["slowness"]),
                "argmax_power": format_float(argmax["power"]),
                "argmax_support": int(argmax["support_count"]),
                "argmax_status": str(argmax["status"]),
                "target_box_max_power": format_float(target_box_peak["power"]),
                "target_box_time_s": format_float(target_box_peak["time"]),
                "target_box_slowness_sdeg": format_float(
                    target_box_peak["slowness"]
                ),
                "target_box_support": int(target_box_peak["support_count"]),
                "target_box_status": str(target_box_peak["status"]),
            }
        )
        print(progress_line(realization, argmax, target_box_peak), flush=True)

    write_results_atomically(args.out_csv, result_rows)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        detail = str(exc) or "no additional detail"
        print(
            f"scramble_runner.py: {type(exc).__name__}: {detail}",
            file=sys.stderr,
            flush=True,
        )
        exit_code = 1
    raise SystemExit(exit_code)
