"""Re-verify the recorded PKKP Type I/II occupancy concordance for the manuscript.

Registered semantics (frozen 2026-07-25, card P0-T2READ-PKKP):
- statistic: per-threshold-layer full-map occupancy-cell argmax,
  scripts/04_bootstrap/fit_gaussian.py:218-220
  (np.unravel_index(np.argmax(occ)); time[j], slowness[i])
- thresholds: 50/70/85 pct layers as stored in the NPZ
- concordance rule: |dt| <= 5.0 s and |ds| <= 0.5 s/deg

Controls:
- positive: reproduce ALL six recorded cells (Type I frozen + Type II) and the
  recorded dt/ds/concordant flags EXACTLY from the pinned NPZs.
- adverse (shape-preserving, per C3-P2-2): reverse each occupancy layer along
  the time axis WITHOUT reversing the time coordinate vector; the reader must
  execute cleanly and produce readings that do NOT reproduce the recorded
  cells (guards against a reader that ignores axis orientation/metadata).

Fail-closed: any mismatch -> exit 1, no output written.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path("/Users/artuskg/GitRepos/MarsQuake")
RECORDED = REPO / "history/20260725_scout_pass3/t2read_pkkp_argmax.json"
RECORDED_SHA = "921d0ba2badf53f4577f3b9a0f7150739434a746c4a3fc61791e44e1e51ec963"
OUT_DIR = REPO / "history/20260801_pkkp_concordance"
OUT_JSON = OUT_DIR / "pkkp_concordance_verification.json"

DT_TOL_S = 5.0
DS_TOL_SDEG = 0.5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cells(npz_path: Path, reverse_time_data: bool = False):
    """Registered occupancy-cell argmax per threshold layer."""
    z = np.load(npz_path, allow_pickle=False)
    maps = z["occupancy_maps"]
    pcts = [int(v) for v in z["threshold_pcts"]]
    time = z["time_axis"]
    slowness = z["slowness_axis"]
    cells = {}
    for pct, occ in zip(pcts, maps):
        if reverse_time_data:
            occ = occ[:, ::-1]
        i, j = np.unravel_index(np.argmax(occ), occ.shape)
        cells[pct] = (float(time[j]), float(slowness[i]))
    return cells


def main() -> int:
    failures = []

    rec_sha = sha256(RECORDED)
    if rec_sha != RECORDED_SHA:
        print(f"FAIL recorded-artifact SHA {rec_sha} != {RECORDED_SHA}")
        return 1
    recorded = json.loads(RECORDED.read_text())

    input_shas = {}
    for rel, pin in recorded["inputs"].items():
        p = REPO / rel
        got = sha256(p)
        input_shas[rel] = got
        if got != pin:
            failures.append(f"input SHA mismatch {rel}: {got} != {pin}")

    reg = recorded["registered"]
    if reg["dt_tol_s"] != DT_TOL_S or reg["ds_tol_sdeg"] != DS_TOL_SDEG:
        failures.append("registered tolerances differ from frozen constants")

    t1 = read_cells(REPO / "results/bootstrap/type1_pkkp_occupancy.npz")
    t2 = read_cells(REPO / "results/bootstrap/type2_pkkp_distance_stratified_occupancy.npz")

    # Positive control: all six cells, deltas, and flags match the record.
    table = {}
    for pct_str, row in recorded["type2_pkkp"].items():
        pct = int(pct_str)
        rec_t2 = tuple(row["type2_argmax"])
        rec_t1 = tuple(row["type1_frozen"])
        got_t2, got_t1 = t2[pct], t1[pct]
        for name, got, rec in (("type2", got_t2, rec_t2), ("type1", got_t1, rec_t1)):
            if abs(got[0] - rec[0]) > 1e-6 or abs(got[1] - rec[1]) > 1e-6:
                failures.append(f"{name}@{pct}%: {got} != recorded {rec}")
        dt = round(got_t2[0] - got_t1[0], 6)
        ds = round(got_t2[1] - got_t1[1], 3)
        if abs(dt - row["dt"]) > 1e-6 or abs(ds - row["ds"]) > 1e-3:
            failures.append(f"deltas@{pct}%: dt={dt} ds={ds} != recorded {row['dt']}/{row['ds']}")
        concordant = abs(dt) <= DT_TOL_S and abs(ds) <= DS_TOL_SDEG
        if concordant != row["concordant"]:
            failures.append(f"concordance flag@{pct}% mismatch")
        # Nearest recorded reference feature by |dt| (margins are unambiguous:
        # all cells lie within 1.7 s of early_G1 and > 50 s from G2/T).
        refs = reg["reference_features"]
        nearest = min(refs, key=lambda k: abs(got_t2[0] - refs[k][0]))
        if nearest != row["nearest_recorded_feature"]:
            failures.append(f"nearest feature@{pct}%: {nearest} != {row['nearest_recorded_feature']}")
        table[pct] = {
            "type1": got_t1,
            "type2": got_t2,
            "dt_s": dt,
            "ds_sdeg": ds,
            "concordant": concordant,
            "nearest_recorded_feature": nearest,
        }

    # Adverse control: time-reversed layer data with unchanged coordinates
    # must execute and must NOT reproduce the recorded cells.
    adverse_hits = 0
    adv1 = read_cells(REPO / "results/bootstrap/type1_pkkp_occupancy.npz", reverse_time_data=True)
    adv2 = read_cells(REPO / "results/bootstrap/type2_pkkp_distance_stratified_occupancy.npz", reverse_time_data=True)
    for pct in table:
        if abs(adv1[pct][0] - table[pct]["type1"][0]) < 1e-6:
            adverse_hits += 1
        if abs(adv2[pct][0] - table[pct]["type2"][0]) < 1e-6:
            adverse_hits += 1
    if adverse_hits:
        failures.append(f"adverse control vacuous: {adverse_hits}/6 reversed readings reproduced")

    if failures:
        print("CONTROL FAILURES:")
        for f in failures:
            print("  -", f)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "purpose": "Manuscript-facing re-verification of the recorded PKKP Type I/II occupancy stable-early concordance (backlog item (a)); discharges the C3-P2-2 vacuous-adverse-control weakness for this use via a shape-preserving time-reversal adverse control.",
        "recorded_artifact": {"path": str(RECORDED.relative_to(REPO)), "sha256": rec_sha},
        "input_shas": input_shas,
        "registered": reg,
        "statistic_source": "scripts/04_bootstrap/fit_gaussian.py:218-220 (per-threshold occupancy-cell argmax)",
        "positive_control": "all six recorded cells, dt/ds, concordance flags, and nearest-feature labels reproduced exactly",
        "adverse_control": "time-reversed occupancy layers (coordinates unchanged) executed cleanly and reproduced 0/6 recorded readings",
        "adverse_readings": {"type1": adv1, "type2": adv2},
        "concordance_table": table,
    }
    OUT_JSON.write_text(json.dumps(out, indent=1) + "\n")
    print("ALL CONTROLS PASSED")
    for pct, row in sorted(table.items()):
        print(
            f"  {pct}%: TypeI ({row['type1'][0]:.2f}, {row['type1'][1]:.3f})  "
            f"TypeII ({row['type2'][0]:.2f}, {row['type2'][1]:.3f})  "
            f"dt {row['dt_s']:+.2f} s  ds {row['ds_sdeg']:+.3f} s/deg  "
            f"concordant={row['concordant']}  nearest={row['nearest_recorded_feature']}"
        )
    print(f"wrote {OUT_JSON.relative_to(REPO)}")
    print("output sha256:", sha256(OUT_JSON))
    return 0


if __name__ == "__main__":
    sys.exit(main())
