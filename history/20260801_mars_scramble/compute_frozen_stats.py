#!/usr/bin/env python3
"""Frozen summary statistics for P0-MARS-SCRAMBLE (card at commit a2163d49).

Written BEFORE any null realization existed. Computes exactly the card's
frozen statistics, nothing else:

- FAR_ridge  = fraction of null realizations with full-window supported
               argmax power >= 0.9327 (literal frozen threshold);
- FAR_target = fraction with target-box max power >= 0.7736 (literal);
- empirical exceedance p = (1 + #{null >= real}) / (N + 1) for both REAL
  values, where the real values are the regenerated canonical lane's
  actual argmax power and published_target power (passed on the CLI);
- 5/25/50/75/95% quantiles of both null distributions (numpy.quantile,
  default linear interpolation).

NaN policy (stated pre-outcome): a NaN null value (blocked/no supported
cell) counts as NOT exceeding any threshold and is excluded from
quantiles; NaN counts are reported explicitly.
"""
from __future__ import annotations

import argparse
import csv
import json
import math

import numpy as np

FROZEN_RIDGE_THRESHOLD = 0.9327
FROZEN_TARGET_THRESHOLD = 0.7736
QUANTILES = (0.05, 0.25, 0.50, 0.75, 0.95)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--null-csv", required=True)
    ap.add_argument("--real-ridge", type=float, required=True,
                    help="regenerated canonical PKiKP global argmax power")
    ap.add_argument("--real-target", type=float, required=True,
                    help="regenerated canonical published_target power")
    ap.add_argument("--expect-n", type=int, default=200)
    args = ap.parse_args()

    ridge_vals: list[float] = []
    target_vals: list[float] = []
    with open(args.null_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if int(row["realization"]) == 0:
                continue  # identity control row is not a null realization
            ridge_vals.append(float(row["argmax_power"]))
            target_vals.append(float(row["target_box_max_power"]))

    n = len(ridge_vals)
    if n != args.expect_n:
        raise SystemExit(f"expected N={args.expect_n} null realizations, found {n}")

    ridge = np.asarray(ridge_vals, dtype=np.float64)
    target = np.asarray(target_vals, dtype=np.float64)
    ridge_nan = int(np.sum(~np.isfinite(ridge)))
    target_nan = int(np.sum(~np.isfinite(target)))
    ridge_f = ridge[np.isfinite(ridge)]
    target_f = target[np.isfinite(target)]

    def far(values: np.ndarray, threshold: float) -> float:
        # NaN comparisons are False -> NaN never exceeds.
        with np.errstate(invalid="ignore"):
            return float(np.sum(values >= threshold)) / float(n)

    def exceed_p(values: np.ndarray, real: float) -> float:
        with np.errstate(invalid="ignore"):
            k = int(np.sum(values >= real))
        return (1.0 + k) / (n + 1.0)

    out = {
        "n_null": n,
        "frozen_thresholds": {
            "ridge": FROZEN_RIDGE_THRESHOLD,
            "target": FROZEN_TARGET_THRESHOLD,
        },
        "real_values": {
            "ridge_argmax_power": args.real_ridge,
            "target_box_power": args.real_target,
        },
        "FAR_ridge": far(ridge, FROZEN_RIDGE_THRESHOLD),
        "FAR_target": far(target, FROZEN_TARGET_THRESHOLD),
        "p_ridge": exceed_p(ridge, args.real_ridge),
        "p_target": exceed_p(target, args.real_target),
        "ridge_quantiles": {
            f"q{int(q * 100):02d}": (float(np.quantile(ridge_f, q)) if ridge_f.size else math.nan)
            for q in QUANTILES
        },
        "target_quantiles": {
            f"q{int(q * 100):02d}": (float(np.quantile(target_f, q)) if target_f.size else math.nan)
            for q in QUANTILES
        },
        "nan_counts": {"ridge": ridge_nan, "target": target_nan},
        "ridge_null_max": float(np.max(ridge_f)) if ridge_f.size else math.nan,
        "target_null_max": float(np.max(target_f)) if target_f.size else math.nan,
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
