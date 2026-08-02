#!/usr/bin/env python
"""Leader-side application of the frozen PREREG §6 detection criteria (G1/G2).

Reads per-config bootstrap stats (real sweep or null realizations) plus the peak table, applies the
two frozen grades, and writes a detection table. Criteria are FROZEN in PREREG_criteria.md §6
(SHA ab5f8034...e119, DEV log through DEV-2026-07-06-5); this script only mechanizes them.

USAGE (real sweep):
  python results/lunar_analog/code/apply_criteria.py \
    --runs-root results/lunar_analog/runs --out results/lunar_analog/analysis/detection_table.csv
USAGE (nulls; stats CSVs carry a `realization` column and live under runs/nulls/<type>/<config>/):
  python results/lunar_analog/code/apply_criteria.py --nulls \
    --runs-root results/lunar_analog/runs/nulls --out results/lunar_analog/analysis/null_far_table.csv
"""

import argparse
import glob
import os

import numpy as np
import pandas as pd

G1 = dict(dt=25.0, dp=1.2, st=10.0, sp=1.0, occ=0.50)
G2 = dict(dt=50.0, dp=2.0, st=50.0, sp=1.5, occ=0.45)
G1_T3_SIGMA_FACTOR = 1.5
THRESHOLD_PCT = 85


def load_stats(runs_root, nulls):
    pattern = (os.path.join(runs_root, "*", "*", "stats_*.csv") if nulls
               else os.path.join(runs_root, "*", "stats_*.csv"))
    frames = []
    for path in sorted(glob.glob(pattern)):
        df = pd.read_csv(path)
        if nulls:
            df["null_type"] = path.split(os.sep)[-3]
        frames.append(df)
    if not frames:
        raise SystemExit(f"no stats CSVs under {runs_root}")
    return pd.concat(frames, ignore_index=True)


def grade_row(row, g):
    dt = abs(row["mean_time_s"] - row["target_time_s"])
    dp = abs(row["mean_slowness_sdeg"] - row["target_slowness_sdeg"])
    checks = dict(
        loc_time=dt <= g["dt"],
        loc_slow=dp <= g["dp"],
        tight_time=row["sigma_time_s"] <= g["st"],
        tight_slow=row["sigma_slowness_sdeg"] <= g["sp"],
        occupancy=row["occupancy_argmax_value"] >= g["occ"],
    )
    return all(checks.values()), checks, dt, dp


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nulls", action="store_true")
    ap.add_argument("--peak-table", default=None,
                    help="peak_table.csv for the box-peak local-max requirement (real sweep only)")
    args = ap.parse_args()

    stats = load_stats(args.runs_root, args.nulls)
    stats = stats[(stats["threshold_pct"] == THRESHOLD_PCT)
                  & (stats["window_type"] == "target_box")].copy()

    peaks = None
    if args.peak_table and not args.nulls:
        pt = pd.read_csv(args.peak_table)
        pt = pt[(pt["peak_label"] == "target_box") & (pt["power_window_s"] == 20.0)]
        # box peak must exist as a local max in the matching A-variant vespagram
        pt = pt[pt["norm_variant"].isin(["A_vpremoon", "A_weber2011"])]
        pt["model"] = pt["norm_variant"].str.replace("A_", "", regex=False)
        peaks = pt.set_index(["config", "model", "phase"])["local_max_neighbor_check"].to_dict()

    group_cols = ["config", "model", "phase"]
    if args.nulls:
        group_cols = ["null_type"] + group_cols + [c for c in ("realization",) if c in stats.columns]

    records = []
    for key, grp in stats.groupby(group_cols):
        t1 = grp[grp["bootstrap_type"] == "type1"]
        t3 = grp[grp["bootstrap_type"] == "type3"]
        if t1.empty:
            continue
        r1 = t1.iloc[0]
        g2_pass, g2_checks, dt, dp = grade_row(r1, G2)
        g1_pass, g1_checks, _, _ = grade_row(r1, G1)
        # G1 additionally requires the Type-III map to satisfy G1 location bounds w/ 1.5x sigma
        if g1_pass:
            if t3.empty:
                g1_pass = False
            else:
                r3 = t3.iloc[0]
                g3 = dict(dt=G1["dt"], dp=G1["dp"],
                          st=G1["st"] * G1_T3_SIGMA_FACTOR, sp=G1["sp"] * G1_T3_SIGMA_FACTOR,
                          occ=0.0)
                g1_pass = grade_row(r3, g3)[0]
        # box-peak local-max requirement (real sweep only; nulls carry their own stats-level peaks)
        local_max_ok = True
        if peaks is not None:
            kk = key if not args.nulls else key[1:4]
            local_max_ok = bool(peaks.get(tuple(kk[:3]), False))
            g1_pass = g1_pass and local_max_ok
            g2_pass = g2_pass and local_max_ok

        rec = dict(zip(group_cols, key if isinstance(key, tuple) else (key,)))
        rec.update(
            dt_vs_pred_s=round(dt, 2), dp_vs_pred_sdeg=round(dp, 3),
            sigma_time_s=round(r1["sigma_time_s"], 2),
            sigma_slowness_sdeg=round(r1["sigma_slowness_sdeg"], 3),
            occupancy_argmax=round(r1["occupancy_argmax_value"], 3),
            degenerate_fit=bool(r1.get("degenerate_fit", False)),
            box_peak_local_max=local_max_ok,
            G1=bool(g1_pass), G2=bool(g2_pass),
            outcome=("DETECTED-G1" if g1_pass else
                     "DETECTED-G2" if g2_pass else "NOT-DETECTED"),
        )
        for name, val in g2_checks.items():
            rec[f"g2_{name}"] = bool(val)
        records.append(rec)

    out = pd.DataFrame.from_records(records)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    out.to_csv(args.out, index=False)

    if args.nulls and len(out):
        far = (out.groupby(["null_type"])
               .agg(realizations=("G2", "size"), g2_detections=("G2", "sum"),
                    g1_detections=("G1", "sum")).reset_index())
        far["FAR_G2"] = far["g2_detections"] / far["realizations"]
        far["FAR_G1"] = far["g1_detections"] / far["realizations"]
        far_path = args.out.replace(".csv", "_summary.csv")
        far.to_csv(far_path, index=False)
        print(far.to_string(index=False))
    print(f"wrote {args.out} ({len(out)} rows)")


if __name__ == "__main__":
    main()
