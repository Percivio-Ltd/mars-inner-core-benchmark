#!/usr/bin/env python
"""P0-EARTH-CTRL N1 event-scramble null per countersigned PREREG §8.
Realization k (k=0..24): rng = default_rng(100+k); permuted distance labels; full machinery =
non-bootstrap A' vespagram (win 20) with box-peak local-max per target box, Type-I (200, seed 0),
Type-III (200, seed 0) over the 3 phase windows. Shardable: run_n1.py K0 K1 processes [K0, K1)."""
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
from run_real import load_usable, frozen_windows, stats_rows

ROOT = Path("/Users/artuskg/marsquake_runs/20260801_earth_ctrl")
RUNS = ROOT / "runs"
REF_DIST, SR = 30.0, 20.0
THRESHOLDS = (50, 70, 85)


def main(k0, k1):
    out_dir = RUNS / "nulls" / "n1"
    out_dir.mkdir(parents=True, exist_ok=True)
    eids, traces, masks, dists, t = load_usable()
    wins_all, boxes_all, preds = frozen_windows()
    phase_wins = {k: v for k, v in wins_all.items() if "_decoy" not in k}
    phase_boxes = {k: v for k, v in boxes_all.items() if "_decoy" not in k}
    dists = np.asarray(dists, dtype=float)

    for k in range(k0, k1):
        t_start = _time.time()
        rng = np.random.default_rng(100 + k)
        perm = rng.permutation(len(dists))
        pd_ = list(dists[perm])
        vesp, s_axis, _, _sup = compute_vespagram(
            traces, pd_, ref_distance=REF_DIST, sampling_rate_hz=SR, time_axis=t,
            slowness_min=-10.0, slowness_max=0.0, slowness_steps=100,
            stack_method="nth_root", n=4, power_window_s=20.0, valid_masks=masks,
            min_support=DEFAULT_MIN_STACK_SUPPORT)
        peak_rows = []
        for lbl, box in phase_boxes.items():
            found, ok, pt, ps, pp = box_peak_local_max(vesp, s_axis, t, box)
            peak_rows.append(dict(realization=k, phase=lbl, peak_found=found,
                                  local_max_neighbor_check=ok, peak_time_s=pt,
                                  peak_slowness_sdeg=ps, peak_power=pp))
        r1 = bootstrap_type1_earth(traces, masks, pd_, t, phase_wins, ref_distance=REF_DIST,
                                   sampling_rate_hz=SR, n_bootstrap=200, seed=0,
                                   threshold_pcts=THRESHOLDS, power_window_s=20.0)
        r3 = bootstrap_type3_earth(traces, masks, pd_, t, phase_wins, ref_distance=REF_DIST,
                                   sampling_rate_hz=SR, n_bootstrap=200, seed=0,
                                   threshold_pcts=THRESHOLDS, power_window_s=20.0)
        rows = (stats_rows("ANMO", r1, preds, "type1", extra=dict(realization=k))
                + stats_rows("ANMO", r3, preds, "type3", extra=dict(realization=k)))
        with open(out_dir / f"stats_k{k:02d}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            [w.writerow(r) for r in rows]
        with open(out_dir / f"peaks_k{k:02d}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(peak_rows[0].keys()))
            w.writeheader()
            [w.writerow(r) for r in peak_rows]
        (out_dir / f"perm_k{k:02d}.json").write_text(json.dumps(
            dict(realization=k, seed=100 + k, perm=perm.tolist())))
        print(f"k={k} done in {(_time.time()-t_start)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
