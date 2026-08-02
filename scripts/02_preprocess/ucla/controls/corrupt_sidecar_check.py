#!/usr/bin/env python3
"""Exercise the harness classification with wrong output-hash evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-mseed", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()

    args.evidence_dir.mkdir(parents=True, exist_ok=False)
    module_path = args.repo_root / "scripts/02_preprocess/deglitch_mps_ucla.py"
    sys.path.insert(0, str(args.repo_root))
    spec = importlib.util.spec_from_file_location("deglitch_mps_ucla_control", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load harness: {module_path}")
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)

    output_path = args.evidence_dir / "S0235b_corrupt_sidecar.mseed"
    work_event_dir = args.evidence_dir / "event_work"
    work_event_dir.mkdir()
    shutil.copy2(args.source_mseed, output_path)
    wrong_hash = "0" * 64
    sidecar_payload = {
        "algorithm": "UCLA_v4 MAIN2SPS+MAIN20SPSJuly26, octave-10.3.0, signal-1.4.7",
        "parameters_sha256": "1" * 64,
        "expected_output_sha256": wrong_hash,
        "verification_status": "ucla_unverified",
    }

    def fake_runner(command, cwd=None):
        del cwd
        ucla_output = Path(command[2])
        shutil.copy2(output_path, ucla_output)
        sidecar = Path(str(ucla_output) + ".ucla.json")
        sidecar.write_text(json.dumps(sidecar_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return harness.CommandResult(command, 0, stdout="corrupt-sidecar control", stderr="")

    metadata = {"commands": []}
    harness._run_ucla_if_configured(
        metadata,
        ["fake-ucla", "{input}", "{output}", "{work_dir}"],
        output_path,
        work_event_dir,
        fake_runner,
    )
    actual_hash = sha256_file(output_path)
    evidence_key, evidence_value, missing = harness._sidecar_verification_evidence(sidecar_payload, actual_hash)
    hash_mismatch = (
        evidence_key == "expected_output_sha256"
        and evidence_value == wrong_hash
        and "expected_output_verification" in missing
    )
    overall = metadata.get("overall_status")
    forbidden = {
        harness.STATUS_MPS_UCLA_VERIFIED,
        harness.STATUS_SIDECAR_ATTESTED_NOT_VERIFIED,
    }
    passed = hash_mismatch and overall == harness.STATUS_UCLA_UNVERIFIED and overall not in forbidden
    evidence = {
        "actual_output_sha256": actual_hash,
        "direct_hash_evidence_check": {
            "evidence_key": evidence_key,
            "evidence_value": evidence_value,
            "missing_verified_evidence": missing,
        },
        "hash_mismatch_detected": hash_mismatch,
        "harness_metadata": metadata,
        "passed": passed,
        "wrong_expected_output_sha256": wrong_hash,
    }
    evidence_path = args.evidence_dir / "classification.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"{'PASS' if passed else 'FAIL'}: overall_status={overall} "
        f"hash_mismatch_detected={hash_mismatch} evidence={evidence_path}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
