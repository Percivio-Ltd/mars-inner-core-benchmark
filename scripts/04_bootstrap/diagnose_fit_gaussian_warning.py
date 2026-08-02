from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import import_local_module, repo_path

fit_mod = import_local_module("marsquake_fit_gaussian_diag", "scripts/04_bootstrap/fit_gaussian.py")


def analyze_projection(label: str, x: np.ndarray, y: np.ndarray) -> dict[str, object]:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    amp0 = float(np.max(y))
    mu0 = float(x[int(np.argmax(y))])
    sigma0 = float(max(1.0, (x[-1] - x[0]) / 10.0))
    p0 = [amp0, mu0, sigma0, 0.0]
    bounds = ([0.0, float(x[0]), 1e-6, -np.inf], [np.inf, float(x[-1]), np.inf, np.inf])
    warning_messages: list[str] = []
    popt_list: list[float] | None = None
    pcov_diag_list: list[float] | None = None
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", OptimizeWarning)
        popt, pcov = curve_fit(fit_mod.gaussian, x, y, p0=p0, bounds=bounds, maxfev=10000)
        popt_list = [float(v) for v in popt]
        pcov_diag_list = [float(v) for v in np.diag(pcov)]
        warning_messages = [str(w.message) for w in caught]

    nonzero = int(np.count_nonzero(y))
    cause = "none"
    if warning_messages:
        if nonzero <= 1 and len(x) <= 4:
            cause = "projection is too sparse: one occupied bin on a 4-point axis leaves covariance underdetermined"
        elif nonzero <= 2:
            cause = "projection is extremely sparse, so amplitude/width/background tradeoffs are poorly constrained"
        else:
            cause = "fit converged but parameter covariance remained ill-conditioned"

    return {
        "label": label,
        "n_points": int(len(x)),
        "nonzero_bins": nonzero,
        "x_min": float(x[0]),
        "x_max": float(x[-1]),
        "initial_guess": {"amp0": amp0, "mu0": mu0, "sigma0": sigma0, "b0": 0.0},
        "fit_params": popt_list,
        "pcov_diag": pcov_diag_list,
        "warning_messages": warning_messages,
        "likely_cause": cause,
    }


def synthetic_repro() -> list[dict[str, object]]:
    slowness = np.linspace(-10.0, 0.0, 4)
    time = np.linspace(0.0, 3.0, 5)
    occ50 = np.zeros((4, 5), dtype=float)
    occ85 = np.zeros((4, 5), dtype=float)
    occ50[1, 2] = 0.8
    occ85[2, 3] = 0.9
    cases = [
        ("synthetic_thr50_time", time, occ50.sum(axis=0)),
        ("synthetic_thr50_slowness", slowness, occ50.sum(axis=1)),
        ("synthetic_thr85_time", time, occ85.sum(axis=0)),
        ("synthetic_thr85_slowness", slowness, occ85.sum(axis=1)),
    ]
    return [analyze_projection(label, x, y) for label, x, y in cases]


def real_data_scan(input_dir: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for name in ("type1_pkikp_occupancy.npz", "type1_pkkp_occupancy.npz"):
        path = input_dir / name
        if not path.exists():
            findings.append({"label": name, "missing": True})
            continue
        payload = np.load(path, allow_pickle=True)
        slowness = np.asarray(payload["slowness_axis"], dtype=np.float64)
        time = np.asarray(payload["time_axis"], dtype=np.float64)
        if "occupancy_maps" in payload.files and "threshold_pcts" in payload.files:
            occ_maps = payload["occupancy_maps"]
            thresholds = [int(v) for v in payload["threshold_pcts"]]
        else:
            occ_maps = payload["occupancy"][None, ...]
            thresholds = [85]
        for thr, occ in zip(thresholds, occ_maps):
            findings.append(analyze_projection(f"{name}:thr{thr}:time", time, occ.sum(axis=0)))
            findings.append(analyze_projection(f"{name}:thr{thr}:slowness", slowness, occ.sum(axis=1)))
    return findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose the scipy OptimizeWarning in fit_gaussian.py")
    parser.add_argument("--input-dir", default=str(repo_path("results/bootstrap")))
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = {
        "synthetic_reproduction": synthetic_repro(),
        "real_data_scan": real_data_scan(Path(args.input_dir)),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
