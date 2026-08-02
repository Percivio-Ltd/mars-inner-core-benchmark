#!/usr/bin/env python
"""Generate PREREG Addendum A: model-predicted target phases per configuration.

Deterministic, waveform-free. Reads the frozen velocity models and the catalogue-only trace
inventory (Addendum B), computes per-config reference distance/depth per PREREG_criteria.md §4/§5,
and writes the target-phase table with detection boxes.

USAGE:
  MAMBA_ROOT_PREFIX=/Users/artus/micromamba micromamba run -n mars-ic python \
    results/lunar_analog/code/prereg_targets.py \
    --inventory results/lunar_analog/addendum_B_trace_inventory.csv \
    --models results/lunar_analog/models/vpremoon.nd results/lunar_analog/models/weber2011.nd \
    --out-csv results/lunar_analog/addendum_A_targets.csv \
    --out-md results/lunar_analog/addendum_A_summary.md

Rules implemented (PREREG §4):
  candidate phases: PcP, PKiKP, PKKP, PKPPKP, PKP, ScS
  keep if differential time (phase - P) in [50, 1100] s and differential slowness in [-10.0, -0.5] s/deg
  target box: T_pred +/- 40 s, p_pred +/- 1.5 s/deg
  ref distance: median distance of rows with qc_status == "ok" (fallback: all rows) rounded to 0.5 deg
  ref depth: DM configs median source_depth_km rounded to 25 km; SHQ configs 0 km
  auto-extension flags are reported when p_pred < -9.0 s/deg or T_pred > 1100 s
"""

import argparse
import hashlib
import os
import sys
import tempfile

import numpy as np
import pandas as pd


def md_table(df, cols):
    """Minimal markdown table writer (avoids the optional tabulate dependency)."""
    sub = df[cols].astype(str)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in sub.iterrows():
        lines.append("| " + " | ".join(row.values) + " |")
    return "\n".join(lines)

CANDIDATE_PHASES = ["PcP", "PKiKP", "PKKP", "PKPPKP", "PKP", "ScS"]
DIFF_T_RANGE = (50.0, 1100.0)
DIFF_P_RANGE = (-10.0, -0.5)
BOX_T_HALFWIDTH = 40.0
BOX_P_HALFWIDTH = 1.5


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_model(nd_path, work_dir):
    from obspy.taup.taup_create import build_taup_model
    from obspy.taup import TauPyModel

    npz_path = build_taup_model(nd_path, output_folder=work_dir, verbose=False)
    # build_taup_model returns the output path in recent obspy; fall back to conventional name
    if not isinstance(npz_path, str):
        base = os.path.splitext(os.path.basename(nd_path))[0]
        npz_path = os.path.join(work_dir, base + ".npz")
    return TauPyModel(model=npz_path)


def first_arrival(model, depth_km, dist_deg, phases):
    arrs = model.get_travel_times(
        source_depth_in_km=depth_km, distance_in_degree=dist_deg, phase_list=phases
    )
    return arrs[0] if arrs else None


def ref_params(rows, config):
    qc_ok = rows[rows["qc_status"].astype(str).str.lower() == "ok"]
    use = qc_ok if len(qc_ok) else rows
    ref_dist = round(float(np.median(use["distance_deg"])) * 2.0) / 2.0
    if "SHQ" in config.upper():
        ref_depth = 0.0
    else:
        ref_depth = round(float(np.median(use["source_depth_km"])) / 25.0) * 25.0
    return ref_dist, ref_depth, len(use), len(qc_ok)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--models", nargs="+", required=True, help=".nd files")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    inv = pd.read_csv(args.inventory)
    if "config" not in inv.columns:
        # Final Addendum-B format: boolean membership column per config -> melt to long form.
        member_cols = [c for c in inv.columns
                       if c.split("-")[0] in {"P12", "P14", "P15", "P16", "S12", "S14", "S15", "S16",
                                              "I12", "I14", "I15", "I16"} and c != "config_memberships"]
        frames = []
        for c in member_cols:
            sel = inv[inv[c].astype(str).str.lower().isin(["true", "1", "yes"])].copy()
            sel["config"] = c
            frames.append(sel)
        inv = pd.concat(frames, ignore_index=True)
    needed = {"config", "distance_deg", "source_depth_km", "qc_status"}
    missing = needed - set(inv.columns)
    if missing:
        sys.exit(f"inventory missing columns: {sorted(missing)}")

    inv_hash = sha256(args.inventory)
    model_hashes = {os.path.basename(m): sha256(m) for m in args.models}

    work_dir = tempfile.mkdtemp(prefix="taup_lunar_")
    models = {}
    for nd in args.models:
        name = os.path.splitext(os.path.basename(nd))[0]
        models[name] = build_model(nd, work_dir)

    records = []
    for config, rows in inv.groupby("config"):
        ref_dist, ref_depth, n_used, n_ok = ref_params(rows, config)
        for mname, model in models.items():
            p_arr = first_arrival(model, ref_depth, ref_dist, ["P", "p"])
            if p_arr is None:
                records.append(
                    dict(config=config, model=mname, phase="P", status="NO_P_ARRIVAL",
                         ref_distance_deg=ref_dist, ref_depth_km=ref_depth)
                )
                continue
            for phase in CANDIDATE_PHASES:
                arr = first_arrival(model, ref_depth, ref_dist, [phase])
                if arr is None:
                    records.append(
                        dict(config=config, model=mname, phase=phase, status="phase_absent",
                             ref_distance_deg=ref_dist, ref_depth_km=ref_depth)
                    )
                    continue
                dt = arr.time - p_arr.time
                dp = arr.ray_param_sec_degree - p_arr.ray_param_sec_degree
                in_window = DIFF_T_RANGE[0] <= dt <= DIFF_T_RANGE[1] and DIFF_P_RANGE[0] <= dp <= DIFF_P_RANGE[1]
                records.append(
                    dict(
                        config=config, model=mname, phase=phase,
                        status="target" if in_window else "outside_window",
                        ref_distance_deg=ref_dist, ref_depth_km=ref_depth,
                        n_rows_used=n_used, n_rows_qc_ok=n_ok,
                        t_p_abs_s=round(p_arr.time, 2), t_phase_abs_s=round(arr.time, 2),
                        diff_time_s=round(dt, 2), diff_slowness_sdeg=round(dp, 3),
                        p_slowness_sdeg=round(p_arr.ray_param_sec_degree, 3),
                        phase_slowness_sdeg=round(arr.ray_param_sec_degree, 3),
                        box_t_min=round(dt - BOX_T_HALFWIDTH, 2), box_t_max=round(dt + BOX_T_HALFWIDTH, 2),
                        box_p_min=round(dp - BOX_P_HALFWIDTH, 3), box_p_max=round(dp + BOX_P_HALFWIDTH, 3),
                        flag_extend_slowness=bool(dp < -9.0),
                        flag_extend_cut=bool(dt > 1100.0),
                    )
                )

    df = pd.DataFrame.from_records(records)
    df.to_csv(args.out_csv, index=False)

    targets = df[df["status"] == "target"] if "status" in df else df.iloc[0:0]
    with open(args.out_md, "w") as f:
        f.write("# PREREG Addendum A: model-predicted targets\n\n")
        f.write(f"Generated deterministically by prereg_targets.py (PREREG SHA-referenced inputs).\n\n")
        f.write(f"- inventory: `{args.inventory}` sha256 `{inv_hash}`\n")
        for m, h in model_hashes.items():
            f.write(f"- model: `{m}` sha256 `{h}`\n")
        f.write(f"- candidate phases: {', '.join(CANDIDATE_PHASES)}\n")
        f.write(f"- keep window: diff T in {DIFF_T_RANGE} s, diff p in {DIFF_P_RANGE} s/deg; "
                f"box +/-{BOX_T_HALFWIDTH} s, +/-{BOX_P_HALFWIDTH} s/deg\n\n")
        f.write("## Target table\n\n")
        if len(targets):
            cols = ["config", "model", "phase", "ref_distance_deg", "ref_depth_km",
                    "diff_time_s", "diff_slowness_sdeg", "box_t_min", "box_t_max",
                    "box_p_min", "box_p_max", "flag_extend_slowness", "flag_extend_cut"]
            f.write(md_table(targets, cols))
            f.write("\n")
        else:
            f.write("NO TARGETS in window — report this; it is a result, not an error.\n")
        absent = df[df["status"] == "phase_absent"]
        if len(absent):
            f.write("\n## Phases absent per model (geometry/model does not produce them)\n\n")
            grouped = (absent.groupby(["config", "model"])["phase"]
                       .apply(lambda s: ", ".join(s)).reset_index())
            f.write(md_table(grouped, ["config", "model", "phase"]))
            f.write("\n")
        outside = df[df["status"] == "outside_window"]
        if len(outside):
            f.write("\n## Phases outside the frozen window\n\n")
            cols = ["config", "model", "phase", "diff_time_s", "diff_slowness_sdeg"]
            f.write(md_table(outside, cols))
            f.write("\n")

    print(f"wrote {args.out_csv} ({len(df)} rows; {len(targets)} targets) and {args.out_md}")


if __name__ == "__main__":
    main()
