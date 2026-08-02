"""Registered comparison for P0-ABL-POLOP-PROV (rule frozen before execution).

For every row key in the recorded Card-5 CSV (SHA 0f927fd4...), the enforced
rerun must contain the same key with IDENTICAL (time_s, slowness_sdeg); every
rerun row must carry current_provenance_status=current; zero rows may carry
the M-K operator label. Any coordinate delta => STOP-and-report (exit 2).
"""
import csv
import hashlib
import sys
from pathlib import Path

REPO = Path("/Users/artuskg/GitRepos/MarsQuake")
RECORDED = REPO / "history/20260725_research_pipeline_restock/peak_comparison_operator_ablation.csv"
RECORDED_ALT = REPO / "history/20260725_research_pipeline_restock/ablpolop_peak_comparison_operator_ablation.csv"
RECORDED_SHA = "0f927fd408b4a9390b0a91fcd3b3692991cf24d37b788e02d2f4b3dcf851c344"
NEW = Path("/Users/artuskg/marsquake_runs/20260801T143200Z_ablpolop_prov/peak_comparison_operator_ablation_provenance.csv")

KEY = ("mode", "input_type", "norm_variant", "polarization_operator",
       "stack_method", "power_window_s", "phase", "peak_label")


def load(path):
    with path.open() as fh:
        rows = list(csv.DictReader(fh))
    table = {}
    for r in rows:
        k = tuple(r[c] for c in KEY)
        if k in table:
            print(f"DUPLICATE key in {path.name}: {k}")
            sys.exit(2)
        table[k] = r
    return table


def main():
    rec_path = RECORDED_ALT if RECORDED_ALT.exists() else RECORDED
    sha = hashlib.sha256(rec_path.read_bytes()).hexdigest()
    if sha != RECORDED_SHA:
        print(f"recorded CSV SHA mismatch: {sha}")
        return 2
    rec = load(rec_path)
    new = load(NEW)

    missing = [k for k in rec if k not in new]
    extra = [k for k in new if k not in rec]
    coord_deltas = []
    not_current = []
    mk_rows = []
    for k, r in new.items():
        if r["current_provenance_status"] != "current":
            not_current.append((k, r["current_provenance_status"]))
        if r["polarization_operator"] == "montalbetti_kanasewich_1970":
            mk_rows.append(k)
    for k, r in rec.items():
        if k not in new:
            continue
        n = new[k]
        for col in ("time_s", "slowness_sdeg"):
            a, b = r[col], n[col]
            fa = float(a) if a not in ("", "nan") else None
            fb = float(b) if b not in ("", "nan") else None
            if fa != fb and not (fa is None and fb is None):
                coord_deltas.append((k, col, a, b))

    print(f"recorded rows {len(rec)}  rerun rows {len(new)}")
    print(f"missing keys {len(missing)}  extra keys {len(extra)}")
    print(f"coordinate deltas {len(coord_deltas)}")
    print(f"rows not status=current {len(not_current)}")
    print(f"M-K-labeled rows {len(mk_rows)}")
    for k, col, a, b in coord_deltas[:10]:
        print("  DELTA", k, col, a, "->", b)
    for k, s in not_current[:10]:
        print("  NOT-CURRENT", k, s)
    for k in missing[:5]:
        print("  MISSING", k)
    for k in extra[:5]:
        print("  EXTRA", k)

    if coord_deltas or missing or not_current or mk_rows:
        print("VERDICT: STOP-AND-REPORT")
        return 2
    print("VERDICT: REPRODUCED-AND-ENFORCED (all coordinates identical, all rows current, zero M-K rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
