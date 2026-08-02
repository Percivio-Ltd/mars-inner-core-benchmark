from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.shared import repo_path


AMENDMENT_REFERENCE = "Paper0.md registered amendment 2026-07-31"
MAX_OFFENDING_PATHS = 20

# Registered by the Paper0.md amendment row dated 2026-07-31 and the operator
# decision in history/20260731_repair2_decision/DECISION_repair2_nonresident_archives.md.
NONRESIDENT_PINNED_ARCHIVES = {
    "data/models/khan2023/Core.zip": "45bc822d90e56ade754ad9deaa08866aecf3d63818ced56c4a1be4200000390f",
    "data/models/khan2023/LSL_Models.zip": "40b2041c81c9db09a849c82bf3456dc4f31569af484d47f2a8c394f55a1711f3",
    "data/models/khan2023/LSL_Models_TauP.zip": "c54ba3ddeb5cb01a6ee24fba164c0475b1127166c4e65afd725a9cc071c3b0f4",
}


class InputAuditError(RuntimeError):
    returncode = 1

    def __init__(self, diagnosis: dict[str, Any]):
        self.diagnosis = diagnosis
        super().__init__(json.dumps(diagnosis, sort_keys=True))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _target_path(repo_root: Path, manifest_path: object) -> Path | None:
    if not isinstance(manifest_path, str) or not manifest_path:
        return None
    relative = Path(manifest_path)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    return repo_root / relative


def _class_record(path: str, pinned_sha256: str) -> dict[str, Any]:
    return {
        "path": path,
        "pinned_sha256": pinned_sha256,
        "manifest_entry_count": 0,
        "manifest_pin_status": "not_checked",
        "resident": False,
        "resident_digest_status": "not_checked",
        "status": "not_checked",
    }


def _diagnosis(
    *,
    manifest_path: Path,
    counts: dict[str, int],
    class_records: list[dict[str, Any]],
    violations: list[dict[str, Any]],
) -> dict[str, Any]:
    categories = sorted({str(item["reason_category"]) for item in violations})
    offending_paths = sorted({str(item["path"]) for item in violations})
    reason_category = categories[0] if len(categories) == 1 else "multiple_input_audit_failures"
    return {
        "status": "failed",
        "reason_category": reason_category,
        "reason_categories": categories,
        "offending_paths": offending_paths[:MAX_OFFENDING_PATHS],
        "offending_path_count": len(offending_paths),
        "listed_path_limit": MAX_OFFENDING_PATHS,
        "violation_count": len(violations),
        "violations": sorted(
            violations,
            key=lambda item: (str(item["path"]), str(item["reason_category"])),
        )[:MAX_OFFENDING_PATHS],
        "counts": counts,
        "pinned_archive_class": class_records,
        "manifest_path": str(manifest_path),
        "amendment_reference": AMENDMENT_REFERENCE,
    }


def _raise_manifest_failure(manifest_path: Path, reason_category: str, detail: str) -> NoReturn:
    class_records = [
        _class_record(path, digest)
        for path, digest in NONRESIDENT_PINNED_ARCHIVES.items()
    ]
    violation = {
        "path": str(manifest_path),
        "reason_category": reason_category,
        "detail": detail,
    }
    raise InputAuditError(
        _diagnosis(
            manifest_path=manifest_path,
            counts={
                "manifest_entries_with_path_and_sha256": 0,
                "verified_resident_entries": 0,
                "verified_required_resident_entries": 0,
                "pinned_archive_class_paths": len(NONRESIDENT_PINNED_ARCHIVES),
                "verified_resident_class_archives": 0,
                "nonresident_class_archives": 0,
            },
            class_records=class_records,
            violations=[violation],
        )
    )


def _read_manifest(manifest_path: Path) -> tuple[dict[str, Any], list[Any], str]:
    try:
        manifest_bytes = manifest_path.read_bytes()
        payload = json.loads(manifest_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _raise_manifest_failure(
            manifest_path,
            "manifest_missing_unreadable_or_invalid_json",
            f"Input manifest could not be read as JSON: {exc}",
        )
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        _raise_manifest_failure(
            manifest_path,
            "manifest_schema_invalid",
            "Input manifest must be a JSON object with an items list",
        )
    return payload, payload["items"], hashlib.sha256(manifest_bytes).hexdigest()


def audit_paper0_inputs(manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    """Verify all manifest path/digest pairs without changing repository state."""

    manifest_path = Path(manifest_path)
    repo_root = Path(repo_root)
    _payload, items, manifest_sha256 = _read_manifest(manifest_path)
    target_entries = [
        item
        for item in items
        if isinstance(item, dict) and "path" in item and "sha256" in item
    ]
    violations: list[dict[str, Any]] = []
    class_records: list[dict[str, Any]] = []
    verified_required_resident_entries = 0
    verified_resident_class_archives = 0
    nonresident_class_archives = 0

    for class_path, pinned_sha256 in NONRESIDENT_PINNED_ARCHIVES.items():
        record = _class_record(class_path, pinned_sha256)
        matching_entries = [
            item
            for item in items
            if isinstance(item, dict) and item.get("path") == class_path
        ]
        record["manifest_entry_count"] = len(matching_entries)
        if not matching_entries:
            record["manifest_pin_status"] = "missing"
            violations.append(
                {
                    "path": class_path,
                    "reason_category": "pinned_archive_manifest_entry_missing",
                    "expected_sha256": pinned_sha256,
                }
            )
        else:
            drifted = [item.get("sha256") for item in matching_entries if item.get("sha256") != pinned_sha256]
            if drifted:
                record["manifest_pin_status"] = "drifted"
                violations.append(
                    {
                        "path": class_path,
                        "reason_category": "pinned_archive_manifest_pin_drift",
                        "expected_sha256": pinned_sha256,
                        "manifest_sha256_values": drifted,
                    }
                )
            else:
                record["manifest_pin_status"] = "matched"

        archive_path = repo_root / class_path
        record["resident"] = archive_path.is_file()
        if record["resident"]:
            try:
                actual_sha256 = _sha256_file(archive_path)
            except OSError as exc:
                record["resident_digest_status"] = "unreadable"
                violations.append(
                    {
                        "path": class_path,
                        "reason_category": "pinned_archive_resident_unreadable",
                        "expected_sha256": pinned_sha256,
                        "detail": str(exc),
                    }
                )
            else:
                if actual_sha256 == pinned_sha256:
                    record["resident_digest_status"] = "matched"
                    verified_resident_class_archives += 1
                else:
                    record["resident_digest_status"] = "mismatched"
                    violations.append(
                        {
                            "path": class_path,
                            "reason_category": "pinned_archive_resident_digest_mismatch",
                            "expected_sha256": pinned_sha256,
                            "actual_sha256": actual_sha256,
                        }
                    )
        elif archive_path.exists():
            record["resident_digest_status"] = "not_a_regular_file"
            violations.append(
                {
                    "path": class_path,
                    "reason_category": "pinned_archive_resident_unreadable",
                    "expected_sha256": pinned_sha256,
                    "detail": "Path exists but is not a regular file",
                }
            )
        else:
            record["resident_digest_status"] = "not_required_absent"
            nonresident_class_archives += 1
        record["status"] = (
            "passed"
            if record["manifest_pin_status"] == "matched"
            and record["resident_digest_status"] in {"matched", "not_required_absent"}
            else "failed"
        )
        class_records.append(record)

    for index, item in enumerate(target_entries):
        item_path = item["path"]
        if item_path in NONRESIDENT_PINNED_ARCHIVES:
            continue
        target_path = _target_path(repo_root, item_path)
        display_path = str(item_path) if isinstance(item_path, str) else f"<manifest item {index}>"
        if target_path is None:
            violations.append(
                {
                    "path": display_path,
                    "reason_category": "manifest_target_path_invalid",
                    "detail": "Manifest target path must be a nonempty repository-relative path without '..'",
                }
            )
            continue
        if not target_path.is_file():
            violations.append(
                {
                    "path": display_path,
                    "reason_category": "resident_input_missing",
                    "expected_sha256": item["sha256"],
                }
            )
            continue
        try:
            actual_sha256 = _sha256_file(target_path)
        except OSError as exc:
            violations.append(
                {
                    "path": display_path,
                    "reason_category": "resident_input_unreadable",
                    "expected_sha256": item["sha256"],
                    "detail": str(exc),
                }
            )
            continue
        if actual_sha256 != item["sha256"]:
            violations.append(
                {
                    "path": display_path,
                    "reason_category": "resident_digest_mismatch_transplant_or_tamper",
                    "expected_sha256": item["sha256"],
                    "actual_sha256": actual_sha256,
                }
            )
            continue
        verified_required_resident_entries += 1

    counts = {
        "manifest_entries_with_path_and_sha256": len(target_entries),
        "verified_resident_entries": verified_required_resident_entries + verified_resident_class_archives,
        "verified_required_resident_entries": verified_required_resident_entries,
        "pinned_archive_class_paths": len(NONRESIDENT_PINNED_ARCHIVES),
        "verified_resident_class_archives": verified_resident_class_archives,
        "nonresident_class_archives": nonresident_class_archives,
    }
    if violations:
        raise InputAuditError(
            _diagnosis(
                manifest_path=manifest_path,
                counts=counts,
                class_records=class_records,
                violations=violations,
            )
        )

    return {
        "status": "passed",
        "counts": counts,
        "pinned_archive_class": class_records,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "amendment_reference": AMENDMENT_REFERENCE,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify all Paper 0 manifest-backed inputs under the registered 2026-07-31 rule."
    )
    parser.add_argument("--manifest", default=str(repo_path("manifest/data_manifest.json")))
    parser.add_argument("--repo-root", default=str(repo_path(".")))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit_paper0_inputs(Path(args.manifest), Path(args.repo_root))
    except InputAuditError as exc:
        print(json.dumps(exc.diagnosis, indent=2, sort_keys=True), file=sys.stderr)
        return exc.returncode
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
