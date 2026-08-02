#!/usr/bin/env python
"""P0-EARTH-CTRL Addendum A generator: frozen ak135 targets, collision list, decoy placement.

Model-only (obspy built-in ak135). No waveform contact. Run BEFORE any data download;
outputs are pasted into PREREG.md and SHA-256 logged.

Frozen conventions (PREREG §4/§8):
  reference distance 30.0 deg, reference depth 33.0 km (a-priori, mirrors Mars fixed ref 29.0)
  targets: PcP, PKiKP, ScS; boxes T_pred +/- 40 s, p_pred +/- 1.5 s/deg (lunar addendum-A convention)
  collision list: fixed phase set below, first arrival each, at the reference geometry
  decoys per phase: shifts {-300,-150,+150,+300} s; center domain [60, 1160] s;
    candidate k: c = c0 + 75*d*k (d=sign(shift), k=0..40), reflected at domain bounds
    (c<60 -> 120-c; c>1160 -> 2320-c, re-reflected if needed); first candidate with
    |c - t_collision| >= 60 for all collision times AND |c - c_placed_same_phase| >= 100
    AND |c - t_target_same_phase| >= 60 is placed; else decoy dropped (min 2/phase else report).
"""
import hashlib
import json
import numpy as np
from obspy.taup import TauPyModel

REF_DIST = 30.0
REF_DEPTH = 33.0
TARGET_PHASES = ["PcP", "PKiKP", "ScS"]
COLLISION_PHASES = ["P", "pP", "sP", "PP", "PPP", "PcP", "pPcP", "sPcP", "S", "sS", "SS",
                    "ScP", "PcS", "ScS", "SKS", "PKiKP", "SKiKP", "PKP", "PKKP", "PS", "SP"]
BOX_T = 40.0
BOX_P = 1.5
SHIFTS = [-300.0, -150.0, 150.0, 300.0]
C_MIN, C_MAX = 60.0, 1160.0
COLL_CLEAR = 60.0
DECOY_SEP = 100.0
STEP = 75.0
MAX_K = 40

def reflect(c):
    for _ in range(8):
        if c < C_MIN:
            c = 2 * C_MIN - c
        elif c > C_MAX:
            c = 2 * C_MAX - c
        else:
            return c
    return None

def main():
    m = TauPyModel(model="ak135")
    p_arr = m.get_travel_times(source_depth_in_km=REF_DEPTH, distance_in_degree=REF_DIST,
                               phase_list=["P", "p"])[0]
    t_p, s_p = p_arr.time, p_arr.ray_param_sec_degree

    targets = {}
    rows = []
    for ph in TARGET_PHASES:
        arrs = m.get_travel_times(source_depth_in_km=REF_DEPTH, distance_in_degree=REF_DIST,
                                  phase_list=[ph])
        a = arrs[0]
        dt, dp = a.time - t_p, a.ray_param_sec_degree - s_p
        targets[ph] = (dt, dp)
        rows.append(dict(phase=ph, ref_distance_deg=REF_DIST, ref_depth_km=REF_DEPTH,
                         t_p_abs_s=round(t_p, 2), t_phase_abs_s=round(a.time, 2),
                         diff_time_s=round(dt, 2), diff_slowness_sdeg=round(dp, 3),
                         box_t_min=round(dt - BOX_T, 2), box_t_max=round(dt + BOX_T, 2),
                         box_p_min=round(dp - BOX_P, 3), box_p_max=round(dp + BOX_P, 3)))

    coll = {}
    for ph in COLLISION_PHASES:
        arrs = m.get_travel_times(source_depth_in_km=REF_DEPTH, distance_in_degree=REF_DIST,
                                  phase_list=[ph])
        if arrs:
            coll[ph] = round(arrs[0].time - t_p, 2)
    coll_times = sorted(coll.values())

    decoys = []
    for ph in TARGET_PHASES:
        dt, dp = targets[ph]
        placed = []
        for shift in SHIFTS:
            d = 1.0 if shift > 0 else -1.0
            c0 = dt + shift
            chosen, k_used = None, None
            for k in range(MAX_K + 1):
                c = reflect(c0 + STEP * d * k)
                if c is None:
                    continue
                if any(abs(c - tc) < COLL_CLEAR for tc in coll_times):
                    continue
                if abs(c - dt) < COLL_CLEAR:
                    continue
                if any(abs(c - pc) < DECOY_SEP for pc in placed):
                    continue
                chosen, k_used = c, k
                break
            if chosen is not None:
                placed.append(chosen)
                decoys.append(dict(phase=ph, shift_s=shift, decoy_center_s=round(chosen, 2),
                                   walk_steps=k_used,
                                   box_t_min=round(chosen - BOX_T, 2), box_t_max=round(chosen + BOX_T, 2),
                                   box_p_min=round(dp - BOX_P, 3), box_p_max=round(dp + BOX_P, 3)))
            else:
                decoys.append(dict(phase=ph, shift_s=shift, decoy_center_s=None, walk_steps=None,
                                   box_t_min=None, box_t_max=None, box_p_min=None, box_p_max=None))

    out = dict(reference=dict(distance_deg=REF_DIST, depth_km=REF_DEPTH,
                              t_p_abs_s=round(t_p, 2), p_slowness_sdeg=round(s_p, 3)),
               model="ak135 (obspy built-in)",
               targets=rows, collision_times_rel_p=coll, decoys=decoys)
    path = "/Users/artuskg/marsquake_runs/20260801_earth_ctrl/addendum_A_targets.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    print(json.dumps(out, indent=2, sort_keys=True))
    print("SHA256", digest)

if __name__ == "__main__":
    main()
