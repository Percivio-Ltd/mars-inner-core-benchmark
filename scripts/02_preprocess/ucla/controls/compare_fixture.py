#!/usr/bin/env python3
"""Apply the frozen P0-UCLA-EQUIV comparison rule to a runner result."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import loadmat

CHANNELS = ("U", "V", "W")
REFERENCE_COUNTS = (43, 34, 37)
POSITIVE_COUNTS = (43, 34, 36)
REFERENCE_LENGTH = 142840
REFERENCE_DC_SHA256 = "7cc4f0dadc14c5da533e46532d4090954ea1f07f552792769191c29512798647"
REFERENCE_AA_SHA256 = "90c6bf09db4bfbc9ad32b7a276cce83c74394c08b2085e7faa26e4966d122eb7"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cells(value: np.ndarray) -> list[np.ndarray]:
    flat = np.asarray(value).ravel()
    if flat.size != 3:
        raise ValueError(f"expected three MATLAB cells, got {flat.size}")
    return [np.asarray(item) for item in flat]


def rms(value: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(value))))


def classify(counts: tuple[int, int, int], ratios: tuple[float, float, float]) -> str:
    if counts == REFERENCE_COUNTS and all(ratio <= 0.1 for ratio in ratios):
        return "EQUIVALENT"
    if all(abs(got - expected) <= 2 for got, expected in zip(counts, REFERENCE_COUNTS)) and all(
        ratio <= 0.5 for ratio in ratios
    ):
        return "DIVERGENT-MINOR"
    return "NOT-EQUIVALENT"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("positive", "adverse"), required=True)
    parser.add_argument("--run-mat", type=Path, required=True)
    parser.add_argument("--reference-dc", type=Path, required=True)
    parser.add_argument("--reference-aa", type=Path, required=True)
    parser.add_argument("--evidence-json", type=Path, required=True)
    args = parser.parse_args()

    observed_ref_hashes = {
        "dc.mat": sha256_file(args.reference_dc),
        "aaout3.mat": sha256_file(args.reference_aa),
    }
    expected_ref_hashes = {
        "dc.mat": REFERENCE_DC_SHA256,
        "aaout3.mat": REFERENCE_AA_SHA256,
    }
    if observed_ref_hashes != expected_ref_hashes:
        print(f"FAIL: reference SHA-256 mismatch: {observed_ref_hashes}")
        return 2

    run = loadmat(args.run_mat)
    ref_dc_mat = loadmat(args.reference_dc)
    ref_aa_mat = loadmat(args.reference_aa)
    run_dc = [item.ravel().astype(float) for item in cells(run["dc"])]
    run_aa = [np.atleast_2d(item) for item in cells(run["aaout3"])]
    run_data = [item.ravel().astype(float) for item in cells(run["Data"])]
    ref_dc = [item.ravel().astype(float) for item in cells(ref_dc_mat["dc"])]
    ref_aa = [np.atleast_2d(item) for item in cells(ref_aa_mat["aaout3"])]

    if tuple(item.shape[0] for item in ref_aa) != REFERENCE_COUNTS:
        print("FAIL: reference glitch counts do not match the frozen record")
        return 2

    counts: list[int] = []
    ratios: list[float] = []
    rows: list[dict[str, object]] = []
    for index, channel in enumerate(CHANNELS):
        lengths = (run_dc[index].size, run_data[index].size, ref_dc[index].size)
        if lengths != (REFERENCE_LENGTH, REFERENCE_LENGTH, REFERENCE_LENGTH):
            print(f"FAIL: channel {channel} length run/data/ref={lengths}")
            return 2
        delta = run_dc[index] - ref_dc[index]
        correction = run_data[index] - ref_dc[index]
        correction_rms = rms(correction)
        if correction_rms == 0:
            print(f"FAIL: channel {channel} reference correction RMS is zero")
            return 2
        ratio = rms(delta) / correction_rms
        count = int(run_aa[index].shape[0])
        counts.append(count)
        ratios.append(ratio)
        row = {
            "channel": channel,
            "run_count": count,
            "reference_count": REFERENCE_COUNTS[index],
            "port_noise_ratio": ratio,
            "max_abs_dc_delta": float(np.max(np.abs(delta))),
            "rms_dc_delta": rms(delta),
            "rms_reference_correction": correction_rms,
        }
        rows.append(row)
        print(
            f"channel={channel} count={count}/{REFERENCE_COUNTS[index]} "
            f"R_ch={ratio:.6f} max_abs_delta={row['max_abs_dc_delta']:.6f}"
        )

    counts_tuple = tuple(counts)
    ratios_tuple = tuple(ratios)
    classification = classify(counts_tuple, ratios_tuple)
    if args.mode == "positive":
        passed = (
            classification == "DIVERGENT-MINOR"
            and counts_tuple == POSITIVE_COUNTS
            and all(ratio <= 0.1 for ratio in ratios_tuple)
        )
    else:
        passed = classification == "NOT-EQUIVALENT"

    evidence = {
        "classification": classification,
        "control_mode": args.mode,
        "frozen_rule": {
            "equivalent": "counts=(43,34,37) and every R_ch<=0.1",
            "divergent_minor": "every abs(delta_count)<=2 and every R_ch<=0.5",
            "otherwise": "NOT-EQUIVALENT",
        },
        "passed": passed,
        "reference_hashes": observed_ref_hashes,
        "rows": rows,
        "run_results_path": str(args.run_mat.resolve()),
    }
    args.evidence_json.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_json.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"classification={classification}")
    print(f"{'PASS' if passed else 'FAIL'}: evidence={args.evidence_json}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
