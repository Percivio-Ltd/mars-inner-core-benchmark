#!/usr/bin/env python
"""P0-EARTH-CTRL production pass per countersigned PREREG.
Real data: non-bootstrap A' vespagrams (win 20 grading + win 5 secondary + C' win 20 artifact),
box-peak local-max checks (3 targets + 12 decoys), Type-I and Type-III bootstraps over the 15
frozen windows, stats CSV rows via the byte-identical fit_gaussian machinery."""
from __future__ import annotations

import csv
import json
import sys
import time as _time
from pathlib import Path

import numpy as np

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(CODE / "mars_modules"))
from earth_kernel import compute_vespagram, box_peak_local_max, DEFAULT_MIN_STACK_SUPPORT
from earth_bootstrap import bootstrap_type1_earth, bootstrap_type3_earth
import fit_gaussian as fg  # byte-identical copy

ROOT = Path("/Users/artuskg/marsquake_runs/20260801_earth_ctrl")
PROC, RUNS = ROOT / "data" / "proc", ROOT / "runs"
REF_DIST = 30.0
SR = 20.0
THRESHOLDS = (50, 70, 85)


def load_usable():
    rows = [r for r in csv.DictReader(open(PROC / "qc_table.csv")) if r["qc"] == "ok"]
    rows.sort(key=lambda r: r["event_id"])
    t = np.load(PROC / "time_axis.npy")
    traces, masks, dists, eids = [], [], [], []
    for r in rows:
        traces.append(np.load(PROC / f"{r['event_id']}_A_envelope.npy").astype(np.float64))
        masks.append(np.load(PROC / f"{r['event_id']}_A_envelope_valid.npy").astype(bool))
        dists.append(float(r["distance_deg"]))
        eids.append(r["event_id"])
    return eids, traces, masks, dists, t


def frozen_windows():
    add = json.load(open(ROOT / "addendum_A_targets.json"))
    wins, boxes, preds = {}, {}, {}
    for tg in add["targets"]:
        lbl = tg["phase"]
        wins[lbl] = (tg["box_t_min"], tg["box_t_max"])
        boxes[lbl] = (tg["box_t_min"], tg["box_t_max"], tg["box_p_min"], tg["box_p_max"])
        preds[lbl] = (tg["diff_time_s"], tg["diff_slowness_sdeg"])
    for dc in add["decoys"]:
        if dc["decoy_center_s"] is None:
            continue
        lbl = f"{dc['phase']}_decoy{int(dc['shift_s']):+d}"
        wins[lbl] = (dc["box_t_min"], dc["box_t_max"])
        boxes[lbl] = (dc["box_t_min"], dc["box_t_max"], dc["box_p_min"], dc["box_p_max"])
        preds[lbl] = (dc["decoy_center_s"], preds[dc["phase"]][1])
    return wins, boxes, preds


def stats_rows(config_label, result_by_window, preds, bootstrap_type, extra=None):
    """Mirror of fit_gaussian.fit_bootstrap_maps row construction, parameterized windows."""
    rows = []
    for lbl, res in result_by_window.items():
        slowness = res["slowness_axis"]
        t = res["time_axis"]
        for thr, occ in zip(res["threshold_pcts"], res["occupancy_maps"]):
            tproj = occ.sum(axis=0)
            sproj = occ.sum(axis=1)
            time_fit = fg.fit_projection(t, tproj)
            slow_fit = fg.fit_projection(slowness, sproj)
            argmax_i, argmax_j = np.unravel_index(np.argmax(occ), occ.shape)
            oat = float(t[argmax_j])
            oas = float(slowness[argmax_i])
            wmt = fg.weighted_median(t, tproj)
            wms = fg.weighted_median(slowness, sproj)
            tsp = float(np.nanmedian(np.diff(t)))
            ssp = float(np.nanmedian(np.diff(slowness)))
            tq = fg.assess_projection_fit_quality(
                axis_name="time", mean=time_fit["mean"], sigma=time_fit["sigma"],
                residual_rms=time_fit["residual_rms"],
                projection_peak=float(np.nanmax(tproj)) if tproj.size else float("nan"),
                axis_min=float(t[0]), axis_max=float(t[-1]), grid_spacing=tsp,
                occupancy_argmax=oat, weighted_median=wmt,
                fit_converged=time_fit["fit_converged"], fallback_used=time_fit["fallback_used"])
            sq = fg.assess_projection_fit_quality(
                axis_name="slowness", mean=slow_fit["mean"], sigma=slow_fit["sigma"],
                residual_rms=slow_fit["residual_rms"],
                projection_peak=float(np.nanmax(sproj)) if sproj.size else float("nan"),
                axis_min=float(slowness[0]), axis_max=float(slowness[-1]), grid_spacing=ssp,
                occupancy_argmax=oas, weighted_median=wms,
                fit_converged=slow_fit["fit_converged"], fallback_used=slow_fit["fallback_used"])
            row = dict(
                config=config_label, model="ak135", phase=lbl,
                bootstrap_type=bootstrap_type, threshold_pct=thr, window_type="target_box",
                mean_time_s=time_fit["mean"], sigma_time_s=time_fit["sigma"],
                mean_slowness_sdeg=slow_fit["mean"], sigma_slowness_sdeg=slow_fit["sigma"],
                occupancy_argmax_time_s=oat, occupancy_argmax_slowness_sdeg=oas,
                occupancy_argmax_value=float(occ[argmax_i, argmax_j]),
                weighted_median_time_s=wmt, weighted_median_slowness_sdeg=wms,
                degenerate_fit=bool(tq["degenerate_fit"] or sq["degenerate_fit"]),
                target_time_s=preds[lbl][0], target_slowness_sdeg=preds[lbl][1],
            )
            if extra:
                row.update(extra)
            rows.append(row)
    return rows


def main():
    RUNS.mkdir(exist_ok=True)
    (RUNS / "real").mkdir(exist_ok=True)
    eids, traces, masks, dists, t = load_usable()
    wins, boxes, preds = frozen_windows()
    print(f"traces={len(eids)} windows={len(wins)}")

    # Type-II trigger check (diagnostic only)
    d = np.asarray(dists)
    frac = max(np.mean((d >= lo) & (d < lo + 3.0)) for lo in np.arange(25.0, 33.1, 0.5))
    print(f"type2 trigger max 3-deg bin fraction = {frac:.3f} (trigger if > 0.5)")

    t0 = _time.time()
    vesp20, s_axis, _, sup20 = compute_vespagram(
        traces, dists, ref_distance=REF_DIST, sampling_rate_hz=SR, time_axis=t,
        slowness_min=-10.0, slowness_max=0.0, slowness_steps=100,
        stack_method="nth_root", n=4, power_window_s=20.0, valid_masks=masks,
        min_support=DEFAULT_MIN_STACK_SUPPORT)
    print(f"one vespagram: {_time.time()-t0:.2f}s")
    vesp5 = compute_vespagram(
        traces, dists, ref_distance=REF_DIST, sampling_rate_hz=SR, time_axis=t,
        slowness_min=-10.0, slowness_max=0.0, slowness_steps=100,
        stack_method="nth_root", n=4, power_window_s=5.0, valid_masks=masks,
        min_support=DEFAULT_MIN_STACK_SUPPORT)[0]
    np.savez_compressed(RUNS / "real" / "vespagram_A.npz", vespagram_win20=vesp20,
                        vespagram_win5=vesp5, support_counts=sup20.astype(np.int32),
                        slowness_axis=s_axis, time_axis=t, events=np.array(eids, dtype=str),
                        distances=np.array(dists), ref_distance=REF_DIST,
                        type2_max_bin_fraction=frac)

    # C' secondary artifact
    tracesC = [np.load(PROC / f"{e}_C_envelope.npy").astype(np.float64) for e in eids]
    masksC = [np.load(PROC / f"{e}_C_envelope_valid.npy").astype(bool) for e in eids]
    vespC = compute_vespagram(
        tracesC, dists, ref_distance=REF_DIST, sampling_rate_hz=SR, time_axis=t,
        slowness_min=-10.0, slowness_max=0.0, slowness_steps=100,
        stack_method="nth_root", n=4, power_window_s=20.0, valid_masks=masksC,
        min_support=DEFAULT_MIN_STACK_SUPPORT)[0]
    np.savez_compressed(RUNS / "real" / "vespagram_C.npz", vespagram_win20=vespC,
                        slowness_axis=s_axis, time_axis=t)

    # box peaks (A', win 20)
    peak_rows = []
    for lbl, box in boxes.items():
        found, ok, pt, ps, pp = box_peak_local_max(vesp20, s_axis, t, box)
        peak_rows.append(dict(config="ANMO", phase=lbl, peak_found=found,
                              local_max_neighbor_check=ok, peak_time_s=pt,
                              peak_slowness_sdeg=ps, peak_power=pp))
    with open(RUNS / "real" / "peak_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(peak_rows[0].keys()))
        w.writeheader()
        [w.writerow(r) for r in peak_rows]

    # bootstraps
    t0 = _time.time()
    r1 = bootstrap_type1_earth(traces, masks, dists, t, wins, ref_distance=REF_DIST,
                               sampling_rate_hz=SR, n_bootstrap=200, seed=0,
                               threshold_pcts=THRESHOLDS, power_window_s=20.0)
    print(f"type1 pass: {(_time.time()-t0)/60:.1f} min")
    t0 = _time.time()
    r3 = bootstrap_type3_earth(traces, masks, dists, t, wins, ref_distance=REF_DIST,
                               sampling_rate_hz=SR, n_bootstrap=200, seed=0,
                               threshold_pcts=THRESHOLDS, power_window_s=20.0)
    print(f"type3 pass: {(_time.time()-t0)/60:.1f} min")

    np.savez_compressed(RUNS / "real" / "type1_occupancy.npz",
                        **{f"{lbl}_maps": r1[lbl]["occupancy_maps"] for lbl in r1},
                        threshold_pcts=np.asarray(THRESHOLDS, dtype=np.int32),
                        slowness_axis=s_axis, time_axis=t, seed=0, n_bootstrap=200)
    np.savez_compressed(RUNS / "real" / "type3_occupancy.npz",
                        **{f"{lbl}_maps": r3[lbl]["occupancy_maps"] for lbl in r3},
                        threshold_pcts=np.asarray(THRESHOLDS, dtype=np.int32),
                        slowness_axis=s_axis, time_axis=t, seed=0, n_bootstrap=200)

    rows = stats_rows("ANMO", r1, preds, "type1") + stats_rows("ANMO", r3, preds, "type3")
    with open(RUNS / "real" / "stats_real.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        [w.writerow(r) for r in rows]
    print("real pass complete")


if __name__ == "__main__":
    main()
