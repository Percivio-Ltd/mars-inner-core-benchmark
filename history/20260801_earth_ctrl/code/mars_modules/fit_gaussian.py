from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

FIT_QUALITY_MAX_RESIDUAL_RMS_FRACTION_OF_PROJECTION_PEAK = 0.10
FIT_QUALITY_MAX_SIGMA_FRACTION_OF_AXIS_SPAN = 0.25
FIT_QUALITY_TRI_ESTIMATOR_TOLERANCE_GRID_CELLS = 3.0
FIT_QUALITY_TRI_ESTIMATOR_TOLERANCE_AXIS_FRACTION = 0.05


def _payload_scalar(payload, key: str, default):
    if key not in payload.files:
        return default
    value = np.asarray(payload[key]).item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def gaussian(x, a, mu, sigma, b):
    return a * np.exp(-(x - mu) ** 2 / (2 * sigma**2)) + b


def fit_projection(x, y):
    if np.sum(y) == 0:
        return {
            "mean": np.nan,
            "sigma": np.nan,
            "fit_converged": False,
            "fallback_used": False,
            "residual_rms": np.nan,
            "projection_nonzero_bins": 0,
        }
    amp0 = np.max(y)
    mu0 = x[int(np.argmax(y))]
    sigma0 = max(1.0, (x[-1] - x[0]) / 10.0)
    p0 = [amp0, mu0, sigma0, 0.0]
    bounds = (
        [0.0, x[0], 1e-6, -np.inf],
        [np.inf, x[-1], np.inf, np.inf],
    )
    try:
        # Small synthetic/regression fixtures can produce very sparse projections
        # (for example one occupied slowness bin on a 4-point axis). In that case
        # scipy may still return a reasonable peak location while warning that the
        # parameter covariance is not identifiable. See
        # `scripts/04_bootstrap/diagnose_fit_gaussian_warning.py`.
        popt, _ = curve_fit(gaussian, x, y, p0=p0, bounds=bounds, maxfev=10000)
        residual = y - gaussian(x, *popt)
        return {
            "mean": float(popt[1]),
            "sigma": float(abs(popt[2])),
            "fit_converged": True,
            "fallback_used": False,
            "residual_rms": float(np.sqrt(np.mean(np.square(residual)))),
            "projection_nonzero_bins": int(np.count_nonzero(y)),
        }
    except (RuntimeError, ValueError):
        return {
            "mean": float(mu0),
            "sigma": float(sigma0),
            "fit_converged": False,
            "fallback_used": True,
            "residual_rms": np.nan,
            "projection_nonzero_bins": int(np.count_nonzero(y)),
        }


def _finite_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def assess_projection_fit_quality(
    *,
    axis_name: str,
    mean: float,
    sigma: float,
    residual_rms: float,
    projection_peak: float,
    axis_min: float,
    axis_max: float,
    grid_spacing: float,
    occupancy_argmax: float,
    weighted_median: float,
    fit_converged: bool,
    fallback_used: bool,
) -> dict:
    axis_span = abs(float(axis_max) - float(axis_min))
    spacing = abs(float(grid_spacing))
    tri_tolerance = max(
        FIT_QUALITY_TRI_ESTIMATOR_TOLERANCE_GRID_CELLS * spacing,
        FIT_QUALITY_TRI_ESTIMATOR_TOLERANCE_AXIS_FRACTION * axis_span,
    )
    limits = {
        "max_residual_rms_fraction_of_projection_peak": FIT_QUALITY_MAX_RESIDUAL_RMS_FRACTION_OF_PROJECTION_PEAK,
        "max_sigma_fraction_of_axis_span": FIT_QUALITY_MAX_SIGMA_FRACTION_OF_AXIS_SPAN,
        "tri_estimator_tolerance_grid_cells": FIT_QUALITY_TRI_ESTIMATOR_TOLERANCE_GRID_CELLS,
        "tri_estimator_tolerance_axis_fraction": FIT_QUALITY_TRI_ESTIMATOR_TOLERANCE_AXIS_FRACTION,
        "tri_estimator_tolerance_axis_units": float(tri_tolerance),
    }
    reasons: list[str] = []
    if not bool(fit_converged):
        reasons.append("optimizer_not_converged")
    if bool(fallback_used):
        reasons.append("optimizer_fallback_used")

    peak = _finite_float(projection_peak)
    residual = _finite_float(residual_rms)
    if peak is None or peak <= 0.0:
        reasons.append("nonpositive_projection_peak")
    elif residual is None:
        reasons.append("residual_rms_unavailable")
    elif residual / peak > FIT_QUALITY_MAX_RESIDUAL_RMS_FRACTION_OF_PROJECTION_PEAK:
        reasons.append("residual_rms_fraction")

    sigma_value = _finite_float(sigma)
    if sigma_value is None or sigma_value <= 0.0:
        reasons.append("sigma_unavailable")
    elif axis_span <= 0.0:
        reasons.append("axis_span_unavailable")
    elif sigma_value > FIT_QUALITY_MAX_SIGMA_FRACTION_OF_AXIS_SPAN * axis_span:
        reasons.append("sigma_exceeds_axis_span_fraction")

    estimates = [
        _finite_float(mean),
        _finite_float(occupancy_argmax),
        _finite_float(weighted_median),
    ]
    if any(value is None for value in estimates):
        reasons.append("tri_estimator_unavailable")
    else:
        spread = max(estimates) - min(estimates)
        if spread > tri_tolerance:
            reasons.append("tri_estimator_inconsistency")

    degenerate = bool(reasons)
    return {
        "axis": axis_name,
        "fit_converged": not degenerate,
        "degenerate_fit": degenerate,
        "reasons": reasons,
        "registered_limits": limits,
    }


def weighted_median(x: np.ndarray, weights: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if weights.size == 0 or float(np.sum(weights)) <= 0.0:
        return float("nan")
    order = np.argsort(x)
    x_sorted = x[order]
    w_sorted = weights[order]
    cutoff = 0.5 * float(np.sum(w_sorted))
    return float(x_sorted[np.searchsorted(np.cumsum(w_sorted), cutoff, side="left")])


def count_connected_components(mask: np.ndarray) -> int:
    mask = np.asarray(mask, dtype=bool)
    seen = np.zeros_like(mask, dtype=bool)
    count = 0
    for start in zip(*np.where(mask)):
        if seen[start]:
            continue
        count += 1
        stack = [start]
        seen[start] = True
        while stack:
            i, j = stack.pop()
            for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ni, nj = i + di, j + dj
                if 0 <= ni < mask.shape[0] and 0 <= nj < mask.shape[1] and mask[ni, nj] and not seen[ni, nj]:
                    seen[ni, nj] = True
                    stack.append((ni, nj))
    return count


def fit_bootstrap_maps(
    input_dir: Path, output_csv: Path, n_bootstrap: int = 200, thresholds=(50, 70, 85)
):
    rows = []
    for phase, name in [("pkikp", "type1_pkikp_occupancy.npz"), ("pkkp", "type1_pkkp_occupancy.npz")]:
        payload = np.load(input_dir / name, allow_pickle=True)
        slowness = payload["slowness_axis"]
        time = payload["time_axis"]
        if "occupancy_maps" in payload.files and "threshold_pcts" in payload.files:
            occupancy_maps = payload["occupancy_maps"]
            payload_thresholds = [int(v) for v in payload["threshold_pcts"]]
        else:
            occupancy_maps = payload["occupancy"][None, ...]
            payload_thresholds = [int(thresholds[-1])]
        payload_n_bootstrap = int(payload["n_bootstrap"]) if "n_bootstrap" in payload.files else int(n_bootstrap)
        fidelity_level = str(_payload_scalar(payload, "bootstrap_fidelity_level", "unregistered_unknown"))
        published_equivalent = bool(_payload_scalar(payload, "bootstrap_published_equivalent", False))
        published_n_bootstrap = int(_payload_scalar(payload, "declared_published_n_bootstrap", 10000))

        for thr, occ in zip(payload_thresholds, occupancy_maps):
            tproj = occ.sum(axis=0)
            sproj = occ.sum(axis=1)
            time_fit = fit_projection(time, tproj)
            slow_fit = fit_projection(slowness, sproj)
            argmax_i, argmax_j = np.unravel_index(np.argmax(occ), occ.shape)
            occupancy_argmax_time = float(time[argmax_j])
            occupancy_argmax_slowness = float(slowness[argmax_i])
            weighted_median_time = weighted_median(time, tproj)
            weighted_median_slowness = weighted_median(slowness, sproj)
            time_spacing = float(np.nanmedian(np.diff(time))) if len(time) > 1 else float("nan")
            slowness_spacing = float(np.nanmedian(np.diff(slowness))) if len(slowness) > 1 else float("nan")
            time_quality = assess_projection_fit_quality(
                axis_name="time",
                mean=time_fit["mean"],
                sigma=time_fit["sigma"],
                residual_rms=time_fit["residual_rms"],
                projection_peak=float(np.nanmax(tproj)) if tproj.size else float("nan"),
                axis_min=float(time[0]),
                axis_max=float(time[-1]),
                grid_spacing=time_spacing,
                occupancy_argmax=occupancy_argmax_time,
                weighted_median=weighted_median_time,
                fit_converged=time_fit["fit_converged"],
                fallback_used=time_fit["fallback_used"],
            )
            slow_quality = assess_projection_fit_quality(
                axis_name="slowness",
                mean=slow_fit["mean"],
                sigma=slow_fit["sigma"],
                residual_rms=slow_fit["residual_rms"],
                projection_peak=float(np.nanmax(sproj)) if sproj.size else float("nan"),
                axis_min=float(slowness[0]),
                axis_max=float(slowness[-1]),
                grid_spacing=slowness_spacing,
                occupancy_argmax=occupancy_argmax_slowness,
                weighted_median=weighted_median_slowness,
                fit_converged=slow_fit["fit_converged"],
                fallback_used=slow_fit["fallback_used"],
            )
            fit_quality_reasons = []
            if time_quality["reasons"]:
                fit_quality_reasons.append("time:" + "|".join(time_quality["reasons"]))
            if slow_quality["reasons"]:
                fit_quality_reasons.append("slowness:" + "|".join(slow_quality["reasons"]))
            degenerate_fit = bool(time_quality["degenerate_fit"] or slow_quality["degenerate_fit"])
            occupied = occ > 0.0
            high_occupancy = occ >= (0.8 * float(np.nanmax(occ))) if np.nanmax(occ) > 0.0 else occupied
            rows.append(
                {
                    "phase": phase,
                    "bootstrap_type": "type1",
                    "mean_time_s": time_fit["mean"],
                    "sigma_time_s": time_fit["sigma"],
                    "mean_slowness_sdeg": slow_fit["mean"],
                    "sigma_slowness_sdeg": slow_fit["sigma"],
                    "time_fit_converged": time_quality["fit_converged"],
                    "slowness_fit_converged": slow_quality["fit_converged"],
                    "fit_fallback_used": bool(time_fit["fallback_used"] or slow_fit["fallback_used"] or degenerate_fit),
                    "degenerate_fit": degenerate_fit,
                    "fit_quality_reasons": ";".join(fit_quality_reasons),
                    "time_fit_residual_rms": time_fit["residual_rms"],
                    "slowness_fit_residual_rms": slow_fit["residual_rms"],
                    "time_projection_nonzero_bins": time_fit["projection_nonzero_bins"],
                    "slowness_projection_nonzero_bins": slow_fit["projection_nonzero_bins"],
                    "occupancy_argmax_time_s": occupancy_argmax_time,
                    "occupancy_argmax_slowness_sdeg": occupancy_argmax_slowness,
                    "occupancy_argmax_value": float(occ[argmax_i, argmax_j]),
                    "weighted_median_time_s": weighted_median_time,
                    "weighted_median_slowness_sdeg": weighted_median_slowness,
                    "occupied_cell_count": int(np.count_nonzero(occupied)),
                    "high_occupancy_component_count": count_connected_components(high_occupancy),
                    "n_bootstrap": payload_n_bootstrap,
                    "bootstrap_fidelity_level": fidelity_level,
                    "bootstrap_published_equivalent": published_equivalent,
                    "declared_published_n_bootstrap": published_n_bootstrap,
                    "threshold_pct": thr,
                }
            )

    df = pd.DataFrame(rows)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    logger.info("Saved %s", output_csv)


def parse_args():
    parser = argparse.ArgumentParser(description="Fit Gaussian to bootstrap occupancy projections")
    parser.add_argument("--input-dir", default="results/bootstrap")
    parser.add_argument("--output-csv", default="results/tables/bootstrap_picks.csv")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    fit_bootstrap_maps(Path(args.input_dir), Path(args.output_csv))
