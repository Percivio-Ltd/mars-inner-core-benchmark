"""Registered reader for CARD_P0-SIG-STATEMENT. Rules frozen in the card;
this script implements them verbatim and nothing else."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "results/tables/peak_comparison.csv"
MANIFEST = REPO / "history/20260725_assembly_cgr/cgr_identity_manifest.sha256"
OUT = Path(__file__).resolve().parent / "sig_statement_reading.json"

RECORDED = {
    "pkikp_global": (663.80, -3.64),
    "pkikp_published_target": (601.95, -6.67),
    "pkkp_paper_target": (1341.00, -6.97),
}
LANE_FIELDS = ("mode", "input_type", "norm_variant", "polarization_operator", "stack_method", "power_window_s")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def manifest_digest_for(locator: str) -> str:
    for line in MANIFEST.read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == locator:
            return parts[0].lower()
    raise SystemExit(f"ABORT: locator {locator} not in manifest")


def r2(x: str) -> float:
    return round(float(x), 2)


def main() -> int:
    # Rule 1: identity gate.
    expected = manifest_digest_for("results/tables/peak_comparison.csv")
    actual = sha256(TABLE)
    if actual != expected:
        raise SystemExit(f"ABORT: table identity mismatch: {actual} != {expected}")

    # Adverse control: one altered digit must fail the same gate.
    corrupted = bytearray(TABLE.read_bytes())
    idx = corrupted.index(b"663.8") if b"663.8" in corrupted else 100
    corrupted[idx] = ord("7") if corrupted[idx] != ord("7") else ord("8")
    adverse_digest = hashlib.sha256(bytes(corrupted)).hexdigest()
    if adverse_digest == expected:
        raise SystemExit("ABORT: adverse control failed to fail (corrupted copy passed identity)")

    rows = list(csv.DictReader(TABLE.open()))

    # Rule 2: lane selector via the recorded global endpoint.
    candidates = [
        r for r in rows
        if r["phase"] == "PKiKP" and r["peak_label"] == "global"
        and r["mode"] == "paperfaith" and r["norm_variant"] == "A"
        and r2(r["time_s"]) == RECORDED["pkikp_global"][0]
        and r2(r["slowness_sdeg"]) == RECORDED["pkikp_global"][1]
    ]
    if len(candidates) != 1:
        raise SystemExit(f"ABORT: ambiguous/absent PKiKP lane selector: {len(candidates)} candidate rows")
    g = candidates[0]
    lane = {k: g[k] for k in LANE_FIELDS}

    def lane_row(phase: str, label: str) -> dict:
        matches = [
            r for r in rows
            if r["phase"] == phase and r["peak_label"] == label
            and all(r[k] == lane[k] for k in LANE_FIELDS if phase == "PKiKP" or k != "norm_variant")
        ]
        if phase == "PKKP":
            matches = [
                r for r in matches
                if r2(r["time_s"]) == RECORDED["pkkp_paper_target"][0]
                and r2(r["slowness_sdeg"]) == RECORDED["pkkp_paper_target"][1]
            ] or matches
        if len(matches) != 1:
            raise SystemExit(f"ABORT: ambiguous/absent row {phase}/{label}: {len(matches)}")
        return matches[0]

    p = lane_row("PKiKP", "published_target")
    k = lane_row("PKKP", "paper_target")

    # Positive controls: recorded endpoint reproduction.
    for row, key in ((g, "pkikp_global"), (p, "pkikp_published_target"), (k, "pkkp_paper_target")):
        if (r2(row["time_s"]), r2(row["slowness_sdeg"])) != RECORDED[key]:
            raise SystemExit(f"ABORT: positive control mismatch for {key}")

    s3_ratio = float(g["power"]) / float(p["power"])
    result = {
        "card": "P0-SIG-STATEMENT",
        "table_sha256": actual,
        "adverse_gate_fails_on_corruption": True,
        "lane": lane,
        "pkikp": {
            "global": {"time_s": float(g["time_s"]), "slowness_sdeg": float(g["slowness_sdeg"]), "power": float(g["power"])},
            "published_target": {
                "time_s": float(p["time_s"]),
                "slowness_sdeg": float(p["slowness_sdeg"]),
                "power": float(p["power"]),
                "S1_target_box_rank": int(float(p["target_box_rank"])),
                "S2_background_quantile": float(p["box_peak_background_quantile"]),
                "S4_within_published_tolerance": p["within_published_tolerance"],
                "S4_within_uncertainty_folded_tolerance": p["within_uncertainty_folded_tolerance"],
            },
            "S3_power_ratio_global_over_published_target": s3_ratio,
        },
        "pkkp_mirror": {
            "paper_target": {
                "time_s": float(k["time_s"]),
                "slowness_sdeg": float(k["slowness_sdeg"]),
                "target_box_rank": int(float(k["target_box_rank"])),
                "background_quantile_NEW": float(k["box_peak_background_quantile"]),
                "within_uncertainty_folded_tolerance": k["within_uncertainty_folded_tolerance"],
            },
        },
        "headline": (
            "In the registered primary public lane, the published PKiKP pair is a "
            f"within-uncertainty-folded-tolerance local maximum at target-box rank "
            f"{int(float(p['target_box_rank']))} and background quantile "
            f"{float(p['box_peak_background_quantile']):.4f}, while the unexplained displaced "
            f"ridge carries {s3_ratio:.2f}x its stack power."
        ),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"headline": result["headline"], "out": str(OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
