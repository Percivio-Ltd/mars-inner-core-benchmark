#!/usr/bin/env python
"""P0-EARTH-CTRL grading: applies the frozen PREREG §6 grades (G1/G2, lunar-verbatim) to the
real stats + N1 realizations + N2 decoys, with the symmetric box-peak local-max requirement
(DEV-2026-08-01-1) and the G1 Type-III concordance rider. Mirrors
results/lunar_analog/code/apply_criteria.py (grade_row logic verbatim; plumbing parameterized)."""
from __future__ import annotations

import csv
import glob
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/artuskg/marsquake_runs/20260801_earth_ctrl")
RUNS, ANA = ROOT / "runs", ROOT / "analysis"
G1 = dict(dt=25.0, dp=1.2, st=10.0, sp=1.0, occ=0.50)
G2 = dict(dt=50.0, dp=2.0, st=50.0, sp=1.5, occ=0.45)
G1_T3_SIGMA_FACTOR = 1.5
THRESHOLD_PCT = 85
PHASES = ["PcP", "PKiKP", "ScS"]


def grade_row(row, g):
    # verbatim logic from apply_criteria.py:43-53
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


def grade_group(t1_row, t3_row, peak_ok):
    """G2/G1 for one (window) group given type1 row, type3 row, and the box-peak gate."""
    g2_pass, g2_checks, dt, dp = grade_row(t1_row, G2)
    g1_pass, _, _, _ = grade_row(t1_row, G1)
    if g1_pass:
        if t3_row is None:
            g1_pass = False
        else:
            g3 = dict(dt=G1["dt"], dp=G1["dp"], st=G1["st"] * G1_T3_SIGMA_FACTOR,
                      sp=G1["sp"] * G1_T3_SIGMA_FACTOR, occ=0.0)
            g1_pass = grade_row(t3_row, g3)[0]
    g1_pass = bool(g1_pass and peak_ok)
    g2_pass = bool(g2_pass and peak_ok)
    return g1_pass, g2_pass, g2_checks, dt, dp


def load_stats(path_glob):
    frames = [pd.read_csv(p) for p in sorted(glob.glob(str(path_glob)))]
    return pd.concat(frames, ignore_index=True) if frames else None


def rows_for(stats, peaks, group_extra=()):
    stats = stats[stats["threshold_pct"] == THRESHOLD_PCT]
    out = []
    keys = ["phase"] + list(group_extra)
    for key, grp in stats.groupby(keys):
        key = key if isinstance(key, tuple) else (key,)
        t1 = grp[grp["bootstrap_type"] == "type1"]
        t3 = grp[grp["bootstrap_type"] == "type3"]
        if t1.empty:
            continue
        r1 = t1.iloc[0]
        r3 = t3.iloc[0] if not t3.empty else None
        peak_ok = peaks.get(key, False)
        g1, g2, checks, dt, dp = grade_group(r1, r3, peak_ok)
        rec = dict(zip(keys, key))
        rec.update(dt_vs_pred_s=round(dt, 2), dp_vs_pred_sdeg=round(dp, 3),
                   sigma_time_s=round(r1["sigma_time_s"], 2),
                   sigma_slowness_sdeg=round(r1["sigma_slowness_sdeg"], 3),
                   occupancy_argmax=round(r1["occupancy_argmax_value"], 3),
                   degenerate_fit=bool(r1.get("degenerate_fit", False)),
                   box_peak_local_max=bool(peak_ok), G1=g1, G2=g2,
                   outcome=("DETECTED-G1" if g1 else "DETECTED-G2" if g2 else "NOT-DETECTED"))
        for name, val in checks.items():
            rec[f"g2_{name}"] = bool(val)
        out.append(rec)
    return out


def main():
    ANA.mkdir(exist_ok=True)

    # --- real data: 3 phases + 12 decoys (decoys = the N2 null) ---
    stats = pd.read_csv(RUNS / "real" / "stats_real.csv")
    pk = pd.read_csv(RUNS / "real" / "peak_table.csv")
    peaks = {(r["phase"],): bool(r["local_max_neighbor_check"]) for _, r in pk.iterrows()}
    real_rows = rows_for(stats, peaks)
    pd.DataFrame(real_rows).to_csv(ANA / "detection_table.csv", index=False)

    # --- N2 FARs from the decoy rows ---
    dec = [r for r in real_rows if "_decoy" in r["phase"]]
    n2 = []
    for grade in ("G1", "G2"):
        fired = [r for r in dec if r[grade]]
        n2.append(dict(null="N2_decoy", grade=grade, n=len(dec), fires=len(fired),
                       FAR=round(len(fired) / len(dec), 4) if dec else float("nan"),
                       fired_windows=";".join(r["phase"] for r in fired)))
        for ph in PHASES:
            sub = [r for r in dec if r["phase"].startswith(ph + "_")]
            f = [r for r in sub if r[grade]]
            n2.append(dict(null=f"N2_decoy_{ph}", grade=grade, n=len(sub), fires=len(f),
                           FAR=round(len(f) / len(sub), 4) if sub else float("nan"),
                           fired_windows=";".join(r["phase"] for r in f)))

    # --- N1 realizations ---
    n1_stats = load_stats(RUNS / "nulls" / "n1" / "stats_k*.csv")
    n1_rows = []
    if n1_stats is not None:
        n1_peaks = {}
        for p in sorted(glob.glob(str(RUNS / "nulls" / "n1" / "peaks_k*.csv"))):
            for _, r in pd.read_csv(p).iterrows():
                n1_peaks[(r["phase"], r["realization"])] = bool(r["local_max_neighbor_check"])
        n1_rows = rows_for(n1_stats, n1_peaks, group_extra=("realization",))
        pd.DataFrame(n1_rows).to_csv(ANA / "n1_detection_table.csv", index=False)
        realz = sorted({r["realization"] for r in n1_rows})
        for grade in ("G1", "G2"):
            for ph in PHASES:
                f = [r for r in n1_rows if r["phase"] == ph and r[grade]]
                n2.append(dict(null=f"N1_scramble_{ph}", grade=grade, n=len(realz),
                               fires=len(f), FAR=round(len(f) / len(realz), 4) if realz else float("nan"),
                               fired_windows=";".join(str(r["realization"]) for r in f)))
            any_f = [k for k in realz if any(r[grade] and r["realization"] == k
                                            and r["phase"] in PHASES for r in n1_rows)]
            n2.append(dict(null="N1_scramble_anyphase", grade=grade, n=len(realz),
                           fires=len(any_f), FAR=round(len(any_f) / len(realz), 4) if realz else float("nan"),
                           fired_windows=";".join(map(str, any_f))))
    pd.DataFrame(n2).to_csv(ANA / "far_table.csv", index=False)

    # --- per-grade verdicts (PREREG §9 + DEV-1c) ---
    verdicts = []
    far = {(r["null"], r["grade"]): r["FAR"] for r in n2}
    det = {r["phase"]: r for r in real_rows if r["phase"] in PHASES}
    for grade in ("G1", "G2"):
        pcp = det.get("PcP", {})
        detected = bool(pcp.get(grade, False))
        f1 = far.get((f"N1_scramble_PcP", grade), float("nan"))
        f2 = far.get(("N2_decoy_PcP", grade), float("nan"))
        if detected and f1 < 1 / 3 and f2 < 1 / 3:
            v = "RECOVERED-STRONG" if grade == "G1" else "RECOVERED"
        elif detected:
            v = "METHOD-FRAGILE"
        elif not detected and f1 < 1 / 3 and f2 < 1 / 3:
            v = "NOT-RECOVERED"
        else:
            # frozen PREREG section 9: every residual case is INCONCLUSIVE
            v = "INCONCLUSIVE"
        verdicts.append(dict(grade=grade, pcp_detected=detected, FAR_N1_PcP=f1, FAR_N2_PcP=f2,
                             verdict=v))
    pd.DataFrame(verdicts).to_csv(ANA / "verdicts.csv", index=False)
    print(pd.DataFrame(verdicts).to_string(index=False))
    print("grading complete")


if __name__ == "__main__":
    main()
