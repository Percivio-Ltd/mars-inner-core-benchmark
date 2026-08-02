"""Build the CARD_P0-LOO-INFLUENCE result table and verdict from sweep JSONs.

Mechanical reader of the runner's per-run JSON summaries; applies only the
card's frozen M1/M2 definitions and records artifact identities. No analytic
choice is made here.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

BRANCH_BOUNDARY_S = 632.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_run(json_path: Path) -> dict:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    argmax = data["global_argmax"]
    if data["branch"] not in {"602-family", "662-family"}:
        raise SystemExit(f"ABORT: unknown branch in {json_path}: {data['branch']}")
    expected_branch = (
        "602-family" if float(argmax["time_s"]) < BRANCH_BOUNDARY_S else "662-family"
    )
    if data["branch"] != expected_branch:
        raise SystemExit(f"ABORT: branch/time inconsistency in {json_path}")
    if argmax.get("status") != "ok":
        raise SystemExit(f"ABORT: non-ok peak status in {json_path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep-dir", required=True, type=Path)
    parser.add_argument("--full-set-json", required=True, type=Path)
    parser.add_argument("--repeat-json", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--s3-prefix", required=True)
    args = parser.parse_args()

    full = load_run(args.full_set_json)
    if full["held_out_event"] is not None:
        raise SystemExit("ABORT: full-set JSON has a held-out event")
    full_argmax = full["global_argmax"]
    full_branch = full["branch"]

    run_paths = sorted(args.sweep_dir.glob("hold_out_*.json"))
    if len(run_paths) != 23:
        raise SystemExit(f"ABORT: expected 23 hold-out JSONs, found {len(run_paths)}")

    rows = []
    for json_path in run_paths:
        data = load_run(json_path)
        event = data["held_out_event"]
        if not event or f"hold_out_{event}.json" != json_path.name:
            raise SystemExit(f"ABORT: held-out identity mismatch in {json_path}")
        npz_path = json_path.with_suffix(".npz")
        argmax = data["global_argmax"]
        rows.append(
            {
                "held_out_event": event,
                "time_s": argmax["time_s"],
                "slowness_sdeg": argmax["slowness_sdeg"],
                "power": argmax["power"],
                "support_count": argmax["support_count"],
                "branch": data["branch"],
                "abs_dt_vs_full_s": abs(float(argmax["time_s"]) - float(full_argmax["time_s"])),
                "abs_ds_vs_full_sdeg": abs(
                    float(argmax["slowness_sdeg"]) - float(full_argmax["slowness_sdeg"])
                ),
                "branch_flip": data["branch"] != full_branch,
                "json_sha256": sha256_file(json_path),
                "npz_sha256": sha256_file(npz_path),
                "s3_npz_uri": f"{args.s3_prefix}/{npz_path.name}",
                "s3_json_uri": f"{args.s3_prefix}/{json_path.name}",
            }
        )

    repeat = load_run(args.repeat_json)
    repeat_event = repeat["held_out_event"]
    primary_json = args.sweep_dir / f"hold_out_{repeat_event}.json"
    primary_npz = args.sweep_dir / f"hold_out_{repeat_event}.npz"
    determinism = {
        "held_out_event": repeat_event,
        "json_sha256_identical": sha256_file(args.repeat_json) == sha256_file(primary_json),
        "npz_sha256_identical": sha256_file(args.repeat_json.with_suffix(".npz"))
        == sha256_file(primary_npz),
    }
    if not (determinism["json_sha256_identical"] and determinism["npz_sha256_identical"]):
        raise SystemExit("ABORT: determinism control failed (non-identical repeat)")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    table_path = args.out_dir / "loo_table.csv"
    with table_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    flips = [r["held_out_event"] for r in rows if r["branch_flip"]]
    verdict = {
        "card": "P0-LOO-INFLUENCE",
        "branch_boundary_s": BRANCH_BOUNDARY_S,
        "determinism_control": determinism,
        "full_set": {
            "branch": full_branch,
            "global_argmax": full_argmax,
            "json_sha256": sha256_file(args.full_set_json),
            "npz_sha256": sha256_file(args.full_set_json.with_suffix(".npz")),
            "s3_npz_uri": f"{args.s3_prefix}/full_set.npz",
            "s3_json_uri": f"{args.s3_prefix}/full_set.json",
        },
        "m1_material": bool(flips),
        "m1_flip_count": len(flips),
        "m1_flipping_events": flips,
        "n_hold_out_runs": len(rows),
        "positive_control_full_set_reproduced": (
            full_argmax["time_s"] == 663.8
            and full_argmax["slowness_sdeg"] == -3.6363636363636367
        ),
    }
    verdict_path = args.out_dir / "loo_verdict.json"
    verdict_path.write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"flips": flips, "table": str(table_path), "verdict": str(verdict_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
