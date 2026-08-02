from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

BRANCH_REGISTRY_SCHEMA_VERSION = "branch-registry-v1"
REQUIRED_FIELDS = (
    "branch",
    "lane",
    "endpoint",
    "preprocessing_chain_id",
    "target_box",
    "event_set_hash",
    "coordinate_source",
    "code_commit",
    "result_status",
    "allowed_claim_level",
)
REGISTERED_BRANCHES = ("alpha", "beta", "gamma", "pi")
BRANCH_ALPHA, BRANCH_BETA, BRANCH_GAMMA, BRANCH_PI = REGISTERED_BRANCHES
REGISTERED_RESULT_STATUSES = ("accepted", "exploratory", "blocked", "stale")
REGISTERED_CLAIM_LEVELS = {
    "L1_reproducibility": 1,
    "L2_detection": 2,
    "L3_phase_identity": 3,
    "L4_interior_structure": 4,
}
LANE_BRANCHES = {
    "paper1": ("alpha", "beta", "gamma", "pi"),
    "paper2": ("alpha", "beta", "gamma"),
    "paper3": ("alpha", "pi", "gamma"),
    "paper5": ("alpha", "pi", "gamma"),
    "paper5_measurement": ("alpha", "pi"),
    "paper6": ("alpha", "pi"),
}

ENDPOINT_TARGET_BOXES = {
    "pkikp_global": {"t_min_s": 550.0, "t_max_s": 700.0, "s_min_sdeg": -10.0, "s_max_sdeg": 0.0},
    "pkikp_published_target": {"t_min_s": 584.0, "t_max_s": 624.0, "s_min_sdeg": -7.1, "s_max_sdeg": -5.9},
    "pkkp_global": {"t_min_s": 1200.0, "t_max_s": 1500.0, "s_min_sdeg": -10.0, "s_max_sdeg": 0.0},
    "pkkp_paper_target": {"t_min_s": 1320.0, "t_max_s": 1360.0, "s_min_sdeg": -8.0, "s_max_sdeg": -6.0},
}
ENDPOINT_ROLES = {
    "pkikp_global": "public_data_displaced_PKIKP_ridge_characterization",
    "pkikp_published_target": "primary_published_PKIKP_claim",
    "pkkp_global": "registered_PKKP_search_window_context",
    "pkkp_paper_target": "primary_published_PKKP_claim",
}
PAPER0_FREEZE_DEFAULT_VARIANT = "C"
ENDPOINT_ROW_KEY_SUFFIXES = {
    "pkikp_global": ("PKiKP", "global"),
    "pkikp_published_target": ("PKiKP", "published_target"),
    "pkkp_global": ("PKKP", "peak_1"),
    "pkkp_paper_target": ("PKKP", "paper_target"),
}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def paperfaith_nth_root_win20_chain_id(variant: str) -> str:
    return f"paperfaith/envelope/{variant}/nth_root/win20"


def paper0_freeze_endpoint_row_keys(variant: str = PAPER0_FREEZE_DEFAULT_VARIANT) -> dict[str, tuple[str, ...]]:
    return {
        endpoint: ("paperfaith", "envelope", str(variant), "nth_root", "20.0", phase, peak_label)
        for endpoint, (phase, peak_label) in ENDPOINT_ROW_KEY_SUFFIXES.items()
    }


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_error(key: str, errors: list[dict[str, Any]]) -> RuntimeError:
    return RuntimeError(json.dumps({key: errors}, indent=2, sort_keys=True))


def _validate_hash_like(value: object) -> bool:
    text = str(value)
    if not text.startswith("sha256:"):
        return False
    suffix = text.removeprefix("sha256:")
    return len(suffix) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in suffix)


def _validate_present_hash_like(value: object) -> bool:
    text = str(value)
    if not _validate_hash_like(text):
        return False
    return text.removeprefix("sha256:") != "0" * 64


def branch_labels_for_lane(lane: str) -> tuple[str, ...]:
    try:
        return LANE_BRANCHES[lane]
    except KeyError as exc:
        raise KeyError(f"Unknown branch-registry lane: {lane}") from exc


def validate_branch_label(branch: object, *, lane: str | None = None) -> str:
    label = str(branch)
    allowed = branch_labels_for_lane(lane) if lane is not None else REGISTERED_BRANCHES
    if label not in allowed:
        raise ValueError(f"branch must be one of {list(allowed)}, got {branch!r}")
    return label


def validate_sha256_digest(
    value: object,
    *,
    field: str = "sha256",
    prefixed: bool = False,
    present: bool = False,
    lowercase: bool = False,
) -> str:
    text = str(value)
    if prefixed:
        ok = _validate_present_hash_like(text) if present else _validate_hash_like(text)
        if not ok:
            raise ValueError(f"{field} must be a sha256-prefixed digest")
        return text
    if len(text) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise ValueError(f"{field} must be a 64-hex sha256")
    if lowercase and text != text.lower():
        raise ValueError(f"{field} must be a lowercase 64-hex SHA-256 digest")
    if present and text == "0" * 64:
        raise ValueError(f"{field} must be a present 64-hex sha256")
    return text


def require_single_label(values: Iterable[object], *, field: str, allowed: Iterable[str] | None = None) -> str:
    raw = list(values)
    missing = [value for value in raw if value in (None, "")]
    labels = [str(value) for value in raw if value not in (None, "")]
    unique = sorted(set(labels))
    if missing or len(labels) == 0 or len(unique) != 1:
        raise ValueError(f"{field} mixing or missing labels: {unique}")
    label = unique[0]
    if allowed is not None and label not in tuple(allowed):
        raise ValueError(f"{field} must be one of {list(allowed)}, got {label!r}")
    return label


def _validate_target_box(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    keys = {"t_min_s", "t_max_s", "s_min_sdeg", "s_max_sdeg"}
    if set(value) != keys:
        return False
    try:
        t_min = float(value["t_min_s"])
        t_max = float(value["t_max_s"])
        s_min = float(value["s_min_sdeg"])
        s_max = float(value["s_max_sdeg"])
    except (TypeError, ValueError):
        return False
    return t_min < t_max and s_min < s_max


def validate_registry_row(row: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    for field in REQUIRED_FIELDS:
        if field not in row:
            errors.append({"field": field, "error": "missing_required_field"})
    if errors:
        raise _json_error("branch_registry_row_errors", errors)

    normalized = dict(row)
    if normalized.get("schema_version", BRANCH_REGISTRY_SCHEMA_VERSION) != BRANCH_REGISTRY_SCHEMA_VERSION:
        errors.append(
            {
                "field": "schema_version",
                "expected": BRANCH_REGISTRY_SCHEMA_VERSION,
                "actual": normalized.get("schema_version"),
            }
        )
    if normalized["branch"] not in REGISTERED_BRANCHES:
        errors.append({"field": "branch", "expected": list(REGISTERED_BRANCHES), "actual": normalized["branch"]})
    if normalized["result_status"] not in REGISTERED_RESULT_STATUSES:
        errors.append(
            {"field": "result_status", "expected": list(REGISTERED_RESULT_STATUSES), "actual": normalized["result_status"]}
        )
    if normalized["allowed_claim_level"] not in REGISTERED_CLAIM_LEVELS:
        errors.append(
            {
                "field": "allowed_claim_level",
                "expected": list(REGISTERED_CLAIM_LEVELS),
                "actual": normalized["allowed_claim_level"],
            }
        )
    if not _validate_target_box(normalized["target_box"]):
        errors.append({"field": "target_box", "error": "expected_registered_numeric_box"})
    if not _validate_hash_like(normalized["event_set_hash"]):
        errors.append({"field": "event_set_hash", "error": "expected_sha256_prefixed_hash"})
    if not str(normalized["lane"]).strip():
        errors.append({"field": "lane", "error": "expected_non_empty_string"})
    if not str(normalized["endpoint"]).strip():
        errors.append({"field": "endpoint", "error": "expected_non_empty_string"})
    if not str(normalized["preprocessing_chain_id"]).strip():
        errors.append({"field": "preprocessing_chain_id", "error": "expected_non_empty_string"})
    if not str(normalized["coordinate_source"]).strip():
        errors.append({"field": "coordinate_source", "error": "expected_non_empty_string"})
    if not str(normalized["code_commit"]).strip():
        errors.append({"field": "code_commit", "error": "expected_non_empty_string"})
    locked_pick_sha = normalized.get("locked_pick_manifest_sha256")
    if normalized["result_status"] == "accepted":
        if not _validate_present_hash_like(locked_pick_sha):
            errors.append({"field": "locked_pick_manifest_sha256", "error": "expected_present_sha256_for_accepted_result"})
    elif locked_pick_sha not in (None, "") and not _validate_present_hash_like(locked_pick_sha):
        errors.append({"field": "locked_pick_manifest_sha256", "error": "expected_sha256_prefixed_hash_or_absent"})
    if errors:
        raise _json_error("branch_registry_row_errors", errors)
    return normalized


def validate_registry_consistency(
    rows: Iterable[dict[str, Any]],
    *,
    required_same: tuple[str, ...] = ("branch", "lane", "code_commit"),
) -> list[dict[str, Any]]:
    normalized = [validate_registry_row(dict(row)) for row in rows]
    if not normalized:
        raise _json_error("branch_registry_mixing_errors", [{"field": "rows", "error": "missing_registry_rows"}])
    errors: list[dict[str, Any]] = []
    for field in required_same:
        values = sorted({str(row.get(field, "")) for row in normalized})
        if len(values) != 1:
            errors.append({"field": field, "expected": values[0], "actual": values})
    if errors:
        raise _json_error("branch_registry_mixing_errors", errors)
    return normalized


def claim_level_rank(level: str) -> int:
    if level not in REGISTERED_CLAIM_LEVELS:
        raise KeyError(f"Unknown registered claim level: {level}")
    return REGISTERED_CLAIM_LEVELS[level]


def assert_claim_allowed(row: dict[str, Any], requested_claim_level: str) -> None:
    normalized = validate_registry_row(row)
    allowed = str(normalized["allowed_claim_level"])
    if claim_level_rank(requested_claim_level) > claim_level_rank(allowed):
        raise RuntimeError(
            json.dumps(
                {
                    "claim_level_exceeds_registry": {
                        "endpoint": normalized["endpoint"],
                        "allowed_claim_level": allowed,
                        "requested_claim_level": requested_claim_level,
                    }
                },
                indent=2,
                sort_keys=True,
            )
        )


def read_registry(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise _json_error("branch_registry_row_errors", [{"field": "rows", "error": "expected_list"}])
    return [validate_registry_row(dict(row)) for row in rows]


def write_registry(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    normalized = [validate_registry_row(dict(row)) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        {"schema_version": BRANCH_REGISTRY_SCHEMA_VERSION, "rows": normalized},
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(text + "\n", encoding="utf-8")


def _read_peak_rows(freeze_dir: Path) -> dict[tuple[str, ...], dict[str, str]]:
    path = freeze_dir / "peak_comparison.csv"
    rows: dict[tuple[str, ...], dict[str, str]] = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (
                row.get("mode", ""),
                row.get("input_type", ""),
                row.get("norm_variant", ""),
                row.get("stack_method", ""),
                row.get("power_window_s", ""),
                row.get("phase", ""),
                row.get("peak_label", ""),
            )
            rows[key] = row
    return rows


def build_paper0_freeze_registry_rows(
    freeze_dir: Path,
    *,
    branch: str,
    lane: str,
    result_status: str,
    freeze_recorded_commit: str,
    event_set_hash: str,
    baseline_variant: str = PAPER0_FREEZE_DEFAULT_VARIANT,
    preprocessing_chain_id: str | None = None,
    locked_pick_manifest_sha256: str | None = None,
    locked_pick_manifest_provenance: str = "MQS V14 locked pick manifest",
) -> list[dict[str, Any]]:
    freeze_dir = Path(freeze_dir)
    manifest_path = freeze_dir / "FREEZE_SHA256SUMS"
    commit_path = freeze_dir / "FREEZE_COMMIT"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    artifact_commit = commit_path.read_text(encoding="utf-8").strip().split()[0] if commit_path.exists() else ""
    peak_rows = _read_peak_rows(freeze_dir)
    chain_id = preprocessing_chain_id or paperfaith_nth_root_win20_chain_id(str(baseline_variant))
    rows: list[dict[str, Any]] = []
    for endpoint, key in paper0_freeze_endpoint_row_keys(str(baseline_variant)).items():
        peak_row = peak_rows.get(key, {})
        row: dict[str, Any] = {
            "schema_version": BRANCH_REGISTRY_SCHEMA_VERSION,
            "branch": branch,
            "lane": lane,
            "endpoint": endpoint,
            "preprocessing_chain_id": chain_id,
            "target_box": ENDPOINT_TARGET_BOXES[endpoint],
            "event_set_hash": event_set_hash,
            "coordinate_source": "registered Paper 0/Paper 1 endpoint taxonomy",
            "code_commit": artifact_commit or freeze_recorded_commit,
            "result_status": result_status,
            "allowed_claim_level": "L2_detection",
            "endpoint_role": ENDPOINT_ROLES[endpoint],
            "freeze_manifest_sha256": f"sha256:{_sha256_text(manifest_text)}",
            "freeze_recorded_commit": freeze_recorded_commit,
            "artifact_commit": artifact_commit,
            "deglitch_attestation": "frozen manifest records accepted deglitch state",
            "provenance_status": "current" if result_status == "accepted" else result_status,
            "locked_pick_manifest_sha256": locked_pick_manifest_sha256,
            "locked_pick_manifest_provenance": locked_pick_manifest_provenance,
        }
        if peak_row:
            row.update(
                {
                    "peak_time_s": float(peak_row["time_s"]),
                    "peak_slowness_sdeg": float(peak_row["slowness_sdeg"]),
                    "peak_power": float(peak_row["power"]),
                }
            )
        rows.append(validate_registry_row(row))
    return rows
