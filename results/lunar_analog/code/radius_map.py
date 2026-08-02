#!/usr/bin/env python
"""PREREG §7 implied-core-radius mapping (leader-only, post-§6/§8).

For each surviving primary-family G2 detection, sweep the core radius within its reference model
family, predict (diff T, diff p) of the detected phase at the config's reference distance/depth, and
report the sigma-weighted best-fit radius with a local-derivative uncertainty.

M1 (vpremoon): CMB depth varies with R_core; mantle profile and core velocity values kept.
M2 (weber2011): outer-core radius R varies holding internal ratios (partial-melt 480/330, IC 240/330).

USAGE:
  python radius_map.py --detections <csv> --out <csv>
Detections CSV needs: config, model, phase, plus fit values (mean/sigma time/slowness) and
ref_distance_deg/ref_depth_km merged from addendum_A_targets.csv.
"""

import argparse
import os
import tempfile

import numpy as np
import pandas as pd
from obspy.taup import TauPyModel
from obspy.taup.taup_create import build_taup_model

RADII = np.arange(100.0, 701.0, 10.0)
MOON_R = 1737.1


def read_nd(path):
    rows, names = [], []
    for line in open(path):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) == 1:
            names.append((len(rows), parts[0]))
        else:
            rows.append([float(x) for x in parts[:4]])
    return rows, names


def write_nd(path, rows, names):
    marks = dict(names)
    with open(path, "w") as f:
        for i, r in enumerate(rows):
            if i in marks:
                f.write(marks[i] + "\n")
            f.write("{:.4f} {:.4f} {:.4f} {:.4f}\n".format(*r))


def scaled_model_m1(base_rows, base_names, r_core):
    """VPREMOON family: move the CMB to depth MOON_R - r_core, keep mantle + core velocity values."""
    cmb_new = MOON_R - r_core
    rows, names = [], []
    core_idx = None
    for i, name in base_names:
        if name == "outer-core":
            core_idx = i
    mantle_bottom = base_rows[core_idx - 1]
    core_rows = [r[:] for r in base_rows[core_idx:]]
    rows = [r[:] for r in base_rows[:core_idx]]
    rows[-1][0] = cmb_new
    old_cmb = core_rows[0][0]
    for r in core_rows:
        # stretch core depths proportionally between new CMB and centre
        frac = (r[0] - old_cmb) / (MOON_R - old_cmb) if MOON_R > old_cmb else 0.0
        r[0] = cmb_new + frac * (MOON_R - cmb_new)
    names = [(i, n) for i, n in base_names if i <= core_idx]
    return rows + core_rows, names


def scaled_model_m2(base_rows, base_names, r_oc):
    """Weber family: scale the 480/330/240 km radii by r_oc/330, keep layer velocities."""
    scale = r_oc / 330.0
    anchors = {1257.1: MOON_R - 480.0 * scale, 1407.1: MOON_R - 330.0 * scale,
               1497.1: MOON_R - 240.0 * scale}
    rows = []
    for r in base_rows:
        d = r[0]
        best = min(anchors, key=lambda a: abs(a - d)) if d >= 1257.1 else None
        if best is not None and abs(best - d) < 0.6:
            rows.append([anchors[best]] + r[1:])
        elif d > 1497.1:
            frac = (d - 1497.1) / (MOON_R - 1497.1)
            new_icb = anchors[1497.1]
            rows.append([new_icb + frac * (MOON_R - new_icb)] + r[1:])
        elif 1257.1 < d < 1407.1:
            frac = (d - 1257.1) / (1407.1 - 1257.1)
            rows.append([anchors[1257.1] + frac * (anchors[1407.1] - anchors[1257.1])] + r[1:])
        elif 1407.1 < d < 1497.1:
            frac = (d - 1407.1) / (1497.1 - 1407.1)
            rows.append([anchors[1407.1] + frac * (anchors[1497.1] - anchors[1407.1])] + r[1:])
        else:
            rows.append(r[:])
    # names re-anchored to the rows nearest the scaled boundaries
    names = []
    for i, n in base_names:
        names.append((i, n))
    return rows, names


def predict(model, phase, depth, dist):
    p = model.get_travel_times(source_depth_in_km=depth, distance_in_degree=dist, phase_list=["P", "p"])
    a = model.get_travel_times(source_depth_in_km=depth, distance_in_degree=dist, phase_list=[phase])
    if not p or not a:
        return None
    return (a[0].time - p[0].time, a[0].ray_param_sec_degree - p[0].ray_param_sec_degree)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--detections", required=True)
    ap.add_argument("--models-dir", default="results/lunar_analog/models")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    det = pd.read_csv(args.detections)
    work = tempfile.mkdtemp(prefix="radius_sweep_")
    base = {m: read_nd(os.path.join(args.models_dir, f"{m}.nd")) for m in ("vpremoon", "weber2011")}

    out_rows = []
    for _, r in det.iterrows():
        fam = r["model"]
        scaler = scaled_model_m1 if fam == "vpremoon" else scaled_model_m2
        misfits, preds = [], []
        for R in RADII:
            nd_path = os.path.join(work, f"{fam}_{int(R)}.nd")
            rows, names = scaler(*base[fam], R)
            try:
                write_nd(nd_path, rows, names)
                npz = build_taup_model(nd_path, output_folder=work, verbose=False)
                model = TauPyModel(model=npz if isinstance(npz, str) else nd_path.replace(".nd", ".npz"))
                pr = predict(model, r["phase"], r["ref_depth_km"], r["ref_distance_deg"])
            except Exception:
                pr = None
            if pr is None:
                misfits.append(np.inf); preds.append((np.nan, np.nan)); continue
            m = ((r["mean_time_s"] - pr[0]) / max(r["sigma_time_s"], 1.0)) ** 2 + \
                ((r["mean_slowness_sdeg"] - pr[1]) / max(r["sigma_slowness_sdeg"], 0.1)) ** 2
            misfits.append(m); preds.append(pr)
        misfits = np.asarray(misfits)
        if not np.isfinite(misfits).any():
            out_rows.append(dict(config=r["config"], model=fam, phase=r["phase"], best_R_km=np.nan))
            continue
        k = int(np.nanargmin(misfits))
        # local dT/dR for sigma_R
        if 0 < k < len(RADII) - 1 and np.isfinite(preds[k - 1][0]) and np.isfinite(preds[k + 1][0]):
            dTdR = (preds[k + 1][0] - preds[k - 1][0]) / (RADII[k + 1] - RADII[k - 1])
        else:
            dTdR = np.nan
        sigma_R = abs(r["sigma_time_s"] / dTdR) if dTdR and np.isfinite(dTdR) and dTdR != 0 else np.nan
        out_rows.append(dict(
            config=r["config"], model=fam, phase=r["phase"],
            best_R_km=float(RADII[k]), sigma_R_km=round(float(sigma_R), 1) if np.isfinite(sigma_R) else np.nan,
            misfit=round(float(misfits[k]), 3),
            pred_T_at_best=round(preds[k][0], 2), obs_T=round(r["mean_time_s"], 2),
            pred_p_at_best=round(preds[k][1], 3), obs_p=round(r["mean_slowness_sdeg"], 3),
            dTdR_s_per_km=round(float(dTdR), 4) if np.isfinite(dTdR) else np.nan,
        ))
    out = pd.DataFrame(out_rows)
    out.to_csv(args.out, index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
