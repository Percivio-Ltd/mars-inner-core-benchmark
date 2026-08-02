from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.paper0_bootstrap_fidelity import (
    BOOTSTRAP_FIDELITY_LEVELS,
    DEFAULT_BOOTSTRAP_FIDELITY_LEVEL,
    fidelity_metadata,
    n_bootstrap_for_level,
)
from scripts.paper0_input_audit import (
    AMENDMENT_REFERENCE as INPUT_AUDIT_AMENDMENT_REFERENCE,
    InputAuditError,
    audit_paper0_inputs,
)
from scripts.shared import repo_path


AK_DATASET_PID = "doi:10.18715/IPGP.2021.kpmqrnz8"
KHAN_DATASET_PID = "doi:10.18715/IPGP.2023.llxn7e6d"
PRODUCTION_INPUT_MANIFEST = repo_path("manifest/data_manifest.json")
PRODUCTION_REPO_ROOT = repo_path(".")

DERIVED_PATHS = [
    repo_path("data/deglitched"),
    repo_path("data/processed"),
    repo_path("results/bootstrap"),
    repo_path("results/figures"),
    repo_path("results/tables"),
    repo_path("results/validation"),
    repo_path("results/vespagrams"),
]

VERIFIED_DEGLITCH_STATUS = "mps_ucla_verified"
DEGLITCH_STATUS_VOCABULARY = (
    "succeeded_mps_only",
    "ucla_unverified",
    VERIFIED_DEGLITCH_STATUS,
)
DEFAULT_ALLOWED_DEGLITCH_STATUSES = (VERIFIED_DEGLITCH_STATUS,)
DEGLITCH_STATUS_RANK = {status: idx for idx, status in enumerate(DEGLITCH_STATUS_VOCABULARY)}
DEGLITCH_ATTESTATION_KEYS = (
    "status",
    "detail",
    "summary_path",
    "summary_sha256",
    "status_counts",
    "verified_only_gate",
    "unverified_statuses",
    "attestation_level",
    "accepted_partial_lane_by_design",
    "n_events",
)
INCREMENTAL_VALIDATION_CHECKS = (
    "inventory",
    "preprocessing",
    "alignment",
    "benchmark",
    "bootstrap",
    "type2_distance_stratified",
    "type3_alignment_jitter",
    "deglitch",
    "model",
)


class DeterminedValidationError(RuntimeError):
    returncode = 2


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_deglitch_statuses(statuses: list[str] | tuple[str, ...] | None) -> list[str]:
    selected = list(dict.fromkeys(statuses or DEFAULT_ALLOWED_DEGLITCH_STATUSES))
    unknown = sorted(set(selected).difference(DEGLITCH_STATUS_VOCABULARY))
    if unknown:
        expected = ", ".join(DEGLITCH_STATUS_VOCABULARY)
        raise ValueError(f"Unknown deglitch status: {', '.join(unknown)}; expected one of: {expected}")
    return selected


def _weakest_deglitch_status(statuses: list[str] | tuple[str, ...] | set[str]) -> str:
    if not statuses:
        return "unverified"
    return min(statuses, key=lambda status: (DEGLITCH_STATUS_RANK.get(status, -1), status))


def _unverified_deglitch_statuses(statuses: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return sorted(str(status) for status in statuses if str(status) != VERIFIED_DEGLITCH_STATUS)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path("."), text=True).strip()
    except subprocess.SubprocessError:
        return "unknown"


def _git_status_sha() -> str:
    try:
        status = subprocess.check_output(["git", "status", "--short", "--untracked-files=no"], cwd=repo_path("."), text=True)
    except subprocess.SubprocessError:
        status = "unknown"
    return _sha256_text(status)


def _run_production_input_audit() -> dict[str, Any]:
    return audit_paper0_inputs(PRODUCTION_INPUT_MANIFEST, PRODUCTION_REPO_ROOT)


def _clear_derived_outputs() -> None:
    for path in DERIVED_PATHS:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        path.mkdir(parents=True, exist_ok=True)
    for placeholder in (
        repo_path("results/bootstrap/.gitkeep"),
        repo_path("results/figures/.gitkeep"),
        repo_path("results/tables/.gitkeep"),
        repo_path("results/vespagrams/.gitkeep"),
    ):
        placeholder.touch()


def _clear_incremental_validation_state(args: argparse.Namespace) -> None:
    path = _validation_out_dir(args) / "incremental_validation"
    if path.exists():
        shutil.rmtree(path)


def _command(label: str, *args: str) -> dict[str, Any]:
    return {"label": label, "args": [sys.executable, *args]}


def _manifest_root(data_manifest_path: Path) -> Path:
    if data_manifest_path.parent.name == "manifest":
        return data_manifest_path.parent.parent
    return repo_path(".")


def _relpath(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_data_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_items_by_path(data_manifest_path: Path) -> dict[str, list[dict[str, Any]]]:
    payload = _load_data_manifest(data_manifest_path)
    by_path: dict[str, list[dict[str, Any]]] = {}
    for item in payload.get("items", []):
        item_path = item.get("path")
        if item_path:
            by_path.setdefault(str(item_path), []).append(item)
    return by_path


def _event_ids(event_table_path: Path) -> list[str]:
    with event_table_path.open("r", encoding="utf-8", newline="") as f:
        return [row["event_id"] for row in csv.DictReader(f)]


def _empty_audit(label: str) -> dict[str, Any]:
    return {
        "label": label,
        "valid": False,
        "checked_paths": [],
        "missing_paths": [],
        "stale_paths": [],
        "missing_checksums": [],
        "missing_manifest_entries": [],
        "summary": {
            "checked": 0,
            "valid": 0,
            "missing": 0,
            "stale": 0,
            "missing_checksums": 0,
            "missing_manifest_entries": 0,
        },
    }


def _finalize_audit(audit: dict[str, Any], valid_count: int) -> dict[str, Any]:
    for key in ("checked_paths", "missing_paths", "stale_paths", "missing_checksums", "missing_manifest_entries"):
        audit[key] = sorted(dict.fromkeys(audit[key]))
    audit["summary"] = {
        "checked": len(audit["checked_paths"]),
        "valid": valid_count,
        "missing": len(audit["missing_paths"]),
        "stale": len(audit["stale_paths"]),
        "missing_checksums": len(audit["missing_checksums"]),
        "missing_manifest_entries": len(audit["missing_manifest_entries"]),
    }
    audit["valid"] = (
        audit["summary"]["checked"] > 0
        and audit["summary"]["valid"] == audit["summary"]["checked"]
        and audit["summary"]["missing_manifest_entries"] == 0
        and audit["summary"]["missing_checksums"] == 0
        and audit["summary"]["missing"] == 0
        and audit["summary"]["stale"] == 0
    )
    return audit


def _audit_expected_paths(label: str, data_manifest_path: Path, expected_paths: list[str], root: Path) -> dict[str, Any]:
    audit = _empty_audit(label)
    entries_by_path = _manifest_items_by_path(data_manifest_path)
    valid_count = 0
    for rel in expected_paths:
        audit["checked_paths"].append(rel)
        entries = entries_by_path.get(rel, [])
        best = next((entry for entry in reversed(entries) if entry.get("sha256")), entries[-1] if entries else None)
        path = root / rel
        if best is None:
            audit["missing_manifest_entries"].append(rel)
            if not path.exists():
                audit["missing_paths"].append(rel)
            continue
        expected_sha = best.get("sha256")
        if not expected_sha:
            audit["missing_checksums"].append(rel)
            continue
        if not path.exists():
            audit["missing_paths"].append(rel)
            continue
        if _sha256_file(path) != expected_sha:
            audit["stale_paths"].append(rel)
            continue
        valid_count += 1
    return _finalize_audit(audit, valid_count)


def _audit_waveforms(args: argparse.Namespace) -> dict[str, Any]:
    data_manifest = Path(args.data_manifest)
    root = _manifest_root(data_manifest)
    event_table = Path(args.event_table)
    if not event_table.exists():
        audit = _empty_audit("download_waveforms")
        audit["missing_paths"].append(_relpath(event_table, root))
        return _finalize_audit(audit, 0)
    out_dir = Path(args.raw_dir)
    expected = [_relpath(out_dir / f"{event_id}.mseed", root) for event_id in _event_ids(event_table)]
    return _audit_expected_paths("download_waveforms", data_manifest, expected, root)


def _audit_mqs_catalog(args: argparse.Namespace) -> dict[str, Any]:
    data_manifest = Path(args.data_manifest)
    root = _manifest_root(data_manifest)
    return _audit_expected_paths("download_mqs_catalog", data_manifest, [_relpath(Path(args.mqs_catalog), root)], root)


def _audit_dataset_manifest_stage(
    label: str,
    data_manifest_path: Path,
    dataset_pid: str,
    required_marker_type: str,
) -> dict[str, Any]:
    root = _manifest_root(data_manifest_path)
    payload = _load_data_manifest(data_manifest_path)
    items = payload.get("items", [])
    expected = sorted(
        {
            str(item["path"])
            for item in items
            if item.get("dataset_pid") == dataset_pid and item.get("path") and item.get("sha256")
        }
    )
    audit = _audit_expected_paths(label, data_manifest_path, expected, root) if expected else _empty_audit(label)
    if not any(item.get("dataset_pid") == dataset_pid and item.get("type") == required_marker_type for item in items):
        audit["missing_manifest_entries"].append(f"{dataset_pid}:{required_marker_type}")
    if not expected:
        audit["missing_manifest_entries"].append(f"{dataset_pid}:file_entries")
    return _finalize_audit(audit, audit["summary"]["valid"])


def _audit_ak_models(args: argparse.Namespace) -> dict[str, Any]:
    return _audit_dataset_manifest_stage(
        "download_ak_models",
        Path(args.data_manifest),
        AK_DATASET_PID,
        "model_archive",
    )


def _audit_khan_models(args: argparse.Namespace) -> dict[str, Any]:
    return _audit_dataset_manifest_stage(
        "download_khan_models",
        Path(args.data_manifest),
        KHAN_DATASET_PID,
        "model_mapping",
    )


def build_download_stage_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        {
            "label": "download_waveforms",
            "kind": "download",
            "args": [
                sys.executable,
                "scripts/01_download/download_waveforms.py",
                "--event-table",
                args.event_table,
                "--manifest",
                args.data_manifest,
                "--out-dir",
                args.raw_dir,
            ],
            "audit": _audit_waveforms,
        },
        {
            "label": "download_ak_models",
            "kind": "download",
            "args": [
                sys.executable,
                "scripts/01_download/download_ak_models.py",
                "--manifest",
                args.data_manifest,
                "--out-dir",
                args.ak_out_dir,
            ],
            "audit": _audit_ak_models,
        },
        {
            "label": "download_khan_models",
            "kind": "download",
            "args": [
                sys.executable,
                "scripts/01_download/download_khan_models.py",
                "--manifest",
                args.data_manifest,
                "--out-dir",
                args.khan_out_dir,
            ],
            "audit": _audit_khan_models,
        },
        {
            "label": "download_mqs_catalog",
            "kind": "download",
            "args": [
                sys.executable,
                "scripts/01_download/download_mqs_catalog.py",
                "--manifest",
                args.data_manifest,
                "--out-file",
                args.mqs_catalog,
            ],
            "audit": _audit_mqs_catalog,
        },
    ]


def _bootstrap_command_args(args: argparse.Namespace, *, include_jitter: bool = False) -> list[str]:
    fidelity_level = str(args.bootstrap_fidelity_level)
    n_bootstrap = str(n_bootstrap_for_level(fidelity_level))
    command = [
        "--table",
        args.event_table,
        "--mode",
        "paperfaith",
        "--variant",
        "A",
        "--power-window-s",
        "20.0",
        "--stack-method",
        "nth_root",
        "--nth-root-order",
        "4",
        "--threshold-pcts",
        "50,70,85",
        "--seed",
        "0",
    ]
    if include_jitter:
        command.extend(["--jitter-limit-s", "10.0"])
    command.extend(
        [
            "--input-type",
            "envelope",
            "--n-bootstrap",
            n_bootstrap,
            "--bootstrap-fidelity-level",
            fidelity_level,
        ]
    )
    return command


def _validation_out_dir(args: argparse.Namespace) -> Path:
    return Path(args.manifest).parent


def _add_finding(findings: list[dict[str, Any]], severity: str, code: str, detail: str, **extra: Any) -> None:
    findings.append({"severity": severity, "code": code, "detail": detail, **extra})


def _nearest_existing_parent(path: Path) -> Path | None:
    current = Path(path)
    while not current.exists():
        if current.parent == current:
            return None
        current = current.parent
    return current


def _check_readable_json(path: Path, findings: list[dict[str, Any]], missing_code: str, invalid_code: str) -> None:
    if not path.exists():
        _add_finding(findings, "error", missing_code, f"Missing required JSON file: {path}", path=str(path))
        return
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _add_finding(findings, "error", invalid_code, f"Unreadable or invalid JSON file: {path}: {exc}", path=str(path))


def _check_event_table(path: Path, findings: list[dict[str, Any]]) -> None:
    if not path.exists():
        _add_finding(findings, "error", "missing_event_table", f"Missing event table: {path}", path=str(path))
        return
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if "event_id" not in (reader.fieldnames or []):
                _add_finding(findings, "error", "invalid_event_table", "Event table is missing event_id column", path=str(path))
                return
            next(reader, None)
    except Exception as exc:
        _add_finding(findings, "error", "invalid_event_table", f"Unreadable event table: {path}: {exc}", path=str(path))


def _check_readable_file(path: Path, findings: list[dict[str, Any]], missing_code: str, invalid_code: str) -> None:
    if not path.exists():
        _add_finding(findings, "error", missing_code, f"Missing required file: {path}", path=str(path))
        return
    try:
        with path.open("rb") as handle:
            handle.read(1)
    except Exception as exc:
        _add_finding(findings, "error", invalid_code, f"Unreadable file: {path}: {exc}", path=str(path))


def _command_tokens(command: str | None) -> list[str]:
    if command is None:
        return []
    command = str(command).strip()
    if not command or command.lower() == "none":
        return []
    if command == "auto":
        found = shutil.which("seisglitch")
        return [found] if found else []
    return shlex.split(command)


def _check_seisglitch_resolution(args: argparse.Namespace, findings: list[dict[str, Any]]) -> None:
    if args.seisglitch_command == "identity":
        return
    if args.seisglitch_pythonpath:
        pythonpath = Path(args.seisglitch_pythonpath)
        if not pythonpath.exists():
            _add_finding(
                findings,
                "error",
                "seisglitch_pythonpath_missing",
                f"SEISglitch PYTHONPATH does not exist: {pythonpath}",
                path=str(pythonpath),
            )

    tokens = _command_tokens(args.seisglitch_command)
    if not tokens:
        _add_finding(
            findings,
            "error",
            "seisglitch_command_unresolved",
            f"SEISglitch command could not be resolved: {args.seisglitch_command}",
            command=str(args.seisglitch_command),
        )
        return

    executable = tokens[0]
    resolved = shutil.which(executable) if os.sep not in executable else (executable if Path(executable).exists() else None)
    if resolved is None:
        _add_finding(
            findings,
            "error",
            "seisglitch_command_unresolved",
            f"SEISglitch command entrypoint could not be resolved: {executable}",
            command=str(args.seisglitch_command),
        )
        return

    if Path(resolved).name.startswith("python") and len(tokens) > 1 and (os.sep in tokens[1] or tokens[1].endswith(".py")):
        script = Path(tokens[1])
        if not script.exists():
            _add_finding(
                findings,
                "error",
                "seisglitch_command_unresolved",
                f"SEISglitch Python entry script does not exist: {script}",
                command=str(args.seisglitch_command),
            )


def _check_inventory_file(args: argparse.Namespace, findings: list[dict[str, Any]]) -> None:
    if args.inventory_file != "IRIS":
        inventory_file = Path(args.inventory_file)
        if not inventory_file.exists():
            _add_finding(
                findings,
                "error",
                "inventory_file_missing",
                f"SEISglitch inventory file does not exist: {inventory_file}",
                path=str(inventory_file),
            )


def _check_output_writability(path: Path, findings: list[dict[str, Any]]) -> None:
    target_dir = path.parent
    existing = _nearest_existing_parent(target_dir)
    if existing is None or not os.access(existing, os.W_OK | os.X_OK):
        _add_finding(
            findings,
            "error",
            "output_dir_not_writable",
            f"Output directory parent is not writable: {target_dir}",
            path=str(target_dir),
        )


def _check_declared_env(findings: list[dict[str, Any]]) -> None:
    for module in ("numpy", "obspy", "matplotlib"):
        try:
            __import__(module)
        except Exception as exc:
            _add_finding(findings, "error", "declared_env_import_failed", f"Required module import failed: {module}: {exc}")
    env_prefix = os.environ.get("CONDA_PREFIX") or os.environ.get("MAMBA_PREFIX") or sys.prefix
    if Path(env_prefix).name != "mars-ic":
        _add_finding(
            findings,
            "warning",
            "declared_env_not_detected",
            f"Python environment is not named mars-ic: {env_prefix}",
            python_executable=sys.executable,
        )


def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    input_audit: dict[str, Any] = {
        "status": "not_run_from_scratch",
        "amendment_reference": INPUT_AUDIT_AMENDMENT_REFERENCE,
    }
    if not args.from_scratch:
        try:
            input_audit = _run_production_input_audit()
        except InputAuditError as exc:
            input_audit = exc.diagnosis
            _add_finding(
                findings,
                "error",
                "input_audit_failed",
                "Paper 0 verify-only input audit failed",
                reason_category=exc.diagnosis["reason_category"],
                reason_categories=exc.diagnosis["reason_categories"],
                offending_paths=exc.diagnosis["offending_paths"],
                offending_path_count=exc.diagnosis["offending_path_count"],
                diagnosis=exc.diagnosis,
            )
    statuses = list(args.allow_deglitch_status or DEFAULT_ALLOWED_DEGLITCH_STATUSES)
    unknown_statuses = sorted(set(statuses).difference(DEGLITCH_STATUS_VOCABULARY))
    if unknown_statuses:
        _add_finding(
            findings,
            "error",
            "unknown_deglitch_status",
            f"Unknown deglitch status override: {', '.join(unknown_statuses)}",
            expected=list(DEGLITCH_STATUS_VOCABULARY),
        )
    if VERIFIED_DEGLITCH_STATUS not in statuses:
        severity = "warning" if set(statuses) != set(DEFAULT_ALLOWED_DEGLITCH_STATUSES) else "error"
        unverified_statuses = _unverified_deglitch_statuses(statuses)
        _add_finding(
            findings,
            severity,
            "strict_gate_unreachable",
            (
                "Strict validation requires mps_ucla_verified, but the selected deglitch lane "
                f"allows only: {', '.join(statuses)}"
            ),
            strict_gate=VERIFIED_DEGLITCH_STATUS,
            verified_only_gate=VERIFIED_DEGLITCH_STATUS,
            allowed_statuses=statuses,
            unverified_statuses=unverified_statuses,
            attestation_level=_weakest_deglitch_status(unverified_statuses or statuses),
        )
    if VERIFIED_DEGLITCH_STATUS in statuses and not str(args.ucla_command or "").strip():
        _add_finding(
            findings,
            "warning",
            "ucla_command_missing_for_verified_gate",
            "The verified deglitch gate requires UCLA verification evidence; no UCLA runner command is configured.",
        )

    _check_declared_env(findings)
    _check_seisglitch_resolution(args, findings)
    _check_inventory_file(args, findings)
    _check_readable_json(Path(args.data_manifest), findings, "missing_data_manifest", "invalid_data_manifest")
    _check_event_table(Path(args.event_table), findings)
    _check_readable_file(Path(args.mqs_catalog), findings, "missing_mqs_catalog", "invalid_mqs_catalog")
    _check_output_writability(Path(args.manifest), findings)

    status = "failed" if any(item["severity"] == "error" for item in findings) else "passed"
    return {
        "status": status,
        "findings": findings,
        "input_audit": input_audit,
        "checked_at": _utc_now(),
        "mutates_results": False,
    }


def _validation_command(args: argparse.Namespace, label: str, *, incremental_check: str | None = None, aggregate_only: bool = False) -> dict[str, Any]:
    cmd = [
        "scripts/07_validation/generate_validation_report.py",
        "--event-table",
        args.event_table,
        "--catalog",
        args.mqs_catalog,
        "--raw-dir",
        args.raw_dir,
        "--mode",
        "current-run",
        "--out-dir",
        str(_validation_out_dir(args)),
    ]
    if incremental_check:
        cmd.extend(["--incremental-check", incremental_check, "--no-strict-gates"])
    if aggregate_only:
        cmd.extend(["--aggregate-only", "--strict-gates"])
    if args.require_current_provenance:
        cmd.append("--require-current-provenance")
    return _command(label, *cmd)


def build_stage_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
    allowed_deglitch_statuses = validate_deglitch_statuses(args.allow_deglitch_status)
    deglitch_cmd = [
        "scripts/02_preprocess/deglitch_mps_ucla.py",
        "--in-dir",
        args.raw_dir,
        "--seisglitch-command",
        args.seisglitch_command,
        "--inventory-file",
        args.inventory_file,
    ]
    if args.seisglitch_pythonpath:
        deglitch_cmd.extend(["--seisglitch-pythonpath", args.seisglitch_pythonpath])
    if args.ucla_command:
        deglitch_cmd.extend(["--ucla-command", args.ucla_command])
    for allowed in allowed_deglitch_statuses:
        deglitch_cmd.extend(["--allow-status", allowed])

    rotate_cmd = ["scripts/02_preprocess/rotate_uvw_to_zne.py"]
    for allowed in allowed_deglitch_statuses:
        rotate_cmd.extend(["--allow-deglitch-status", allowed])
    if args.allow_raw_diagnostic:
        rotate_cmd.append("--allow-raw-diagnostic")

    detect_cmd = ["scripts/03_vespagram/detect_peaks.py"]
    if args.require_current_provenance:
        detect_cmd.append("--require-current-provenance")

    return [
        _command("deglitch", *deglitch_cmd),
        _validation_command(args, "validation_deglitch", incremental_check="deglitch"),
        _command("rotate", *rotate_cmd),
        _command("bandpass", "scripts/02_preprocess/bandpass_filter.py"),
        _command("polarization", "scripts/02_preprocess/polarization_filter.py"),
        _command("fdpa", "scripts/02_preprocess/fdpa.py"),
        _command("glitch_flags", "scripts/02_preprocess/glitch_flagging.py"),
        _command(
            "align",
            "scripts/02_preprocess/align_and_cut.py",
            "--event-table",
            args.event_table,
            "--catalog",
            args.mqs_catalog,
        ),
        _command("normalize", "scripts/02_preprocess/normalize_and_envelope.py"),
        _validation_command(args, "validation_inventory", incremental_check="inventory"),
        _validation_command(args, "validation_preprocessing", incremental_check="preprocessing"),
        _validation_command(args, "validation_alignment", incremental_check="alignment"),
        _validation_command(args, "validation_model", incremental_check="model"),
        _command("vespagrams", "scripts/03_vespagram/run_vespagrams.py", "--event-table", args.event_table),
        _validation_command(args, "validation_benchmark", incremental_check="benchmark"),
        _command("detect_peaks", *detect_cmd),
        _command("bootstrap_type1", "scripts/04_bootstrap/bootstrap_type1.py", *_bootstrap_command_args(args)),
        _command("bootstrap_type2", "scripts/04_bootstrap/bootstrap_type2_distance.py", *_bootstrap_command_args(args)),
        _validation_command(args, "validation_type2_distance_stratified", incremental_check="type2_distance_stratified"),
        _command("bootstrap_type3", "scripts/04_bootstrap/bootstrap_type3_alignment_jitter.py", *_bootstrap_command_args(args, include_jitter=True)),
        _validation_command(args, "validation_type3_alignment_jitter", incremental_check="type3_alignment_jitter"),
        _command("fit_bootstrap", "scripts/04_bootstrap/fit_gaussian.py"),
        _validation_command(args, "validation_bootstrap", incremental_check="bootstrap"),
        _validation_command(args, "validation", aggregate_only=True),
    ]


def _run_download_stage(stage: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    audit = stage["audit"](args)
    entry: dict[str, Any] = {
        "label": stage["label"],
        "args": stage["args"],
        "started_at": _utc_now(),
    }
    if args.dry_run:
        entry.update(
            {
                "status": "dry_run",
                "action": "would_skip" if audit["valid"] else "would_run",
                "returncode": 0,
                "audit": audit,
            }
        )
        return entry
    if audit["valid"]:
        entry.update(
            {
                "status": "skipped",
                "action": "manifest_valid",
                "returncode": 0,
                "audit": audit,
                "finished_at": _utc_now(),
            }
        )
        return entry

    completed = subprocess.run(stage["args"], cwd=repo_path("."), text=True, capture_output=True, check=False)
    entry.update(
        {
            "action": "ran",
            "returncode": int(completed.returncode),
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
            "precheck": audit,
            "finished_at": _utc_now(),
        }
    )
    if completed.returncode != 0:
        entry["status"] = "failed"
        return entry

    postcheck = stage["audit"](args)
    entry["postcheck"] = postcheck
    entry["status"] = "succeeded" if postcheck["valid"] else "failed_manifest_check"
    return entry


def _summary_path_for_validation_stage(stage_args: list[str], manifest_path: Path) -> Path:
    if "--out-dir" in stage_args:
        idx = stage_args.index("--out-dir")
        if idx + 1 < len(stage_args):
            return Path(stage_args[idx + 1]) / "validation_summary.json"
    return manifest_path.parent / "validation_summary.json"


def _validation_summary_path(stage_args: list[str], manifest_path: Path) -> Path:
    return _summary_path_for_validation_stage(stage_args, manifest_path)


def _read_validation_summary(stage_args: list[str], manifest_path: Path) -> dict[str, Any] | None:
    summary_path = _validation_summary_path(stage_args, manifest_path)
    if not summary_path.exists():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def _apply_validation_stage_result(
    manifest: dict[str, Any],
    entry: dict[str, Any],
    args: argparse.Namespace,
    manifest_path: Path,
) -> None:
    summary = _read_validation_summary(entry["args"], manifest_path)
    failures: list[str] = []
    if summary is None:
        manifest["validation_status"] = "failed"
        manifest["validation_failures"] = ["validation_summary.json was not written"]
        manifest["current_provenance_enforcement"] = {
            "requested": bool(args.require_current_provenance),
            "enforced": False,
            "status": "summary_missing",
        }
        entry["status"] = "failed"
        return

    deglitch_attestation = _deglitch_validation_attestation(summary)
    if deglitch_attestation:
        manifest["deglitch_attestation"] = deglitch_attestation

    validation = summary.get("validation_status", {})
    status = str(validation.get("status", "failed"))
    failures.extend(str(item) for item in validation.get("failures", []))
    enforcement = summary.get(
        "current_provenance_enforcement",
        {
            "requested": bool(args.require_current_provenance),
            "enforced": False,
            "status": "missing_enforcement_block",
        },
    )
    if args.require_current_provenance and not bool(enforcement.get("enforced")):
        status = "failed"
        failures.append("current provenance was requested but not enforced by validation")
    if args.require_current_provenance and enforcement.get("status") != "current":
        status = "failed"
        failures.append(f"current provenance status is not current: {enforcement.get('status')}")
    deglitch_allowed = _deglitch_payload_allowed(summary.get("deglitch"), args.allow_deglitch_status)
    if deglitch_allowed:
        failures = [failure for failure in failures if not str(failure).startswith("deglitch")]
    if deglitch_allowed and not failures:
        status = "passed"
    manifest["current_provenance_enforcement"] = enforcement
    manifest["validation_status"] = "passed" if status == "passed" and not failures else "failed"
    manifest["validation_failures"] = failures
    manifest["paper_ready"] = manifest["validation_status"] == "passed"
    entry["validation_summary_path"] = str(_summary_path_for_validation_stage(entry["args"], manifest_path))
    returncode = int(entry.get("returncode", 0))
    if returncode not in {0, 2}:
        entry["status"] = "failed"
    elif manifest["validation_status"] == "passed" and returncode in {0, 2}:
        entry["status"] = "succeeded"
    else:
        entry["status"] = "validation_failed"


def _stage_arg_value(stage_args: list[str], flag: str, default: str | None = None) -> str | None:
    if flag in stage_args:
        idx = stage_args.index(flag)
        if idx + 1 < len(stage_args):
            return stage_args[idx + 1]
    return default


def _deglitch_summary_path_from_stage(entry: dict[str, Any]) -> Path | None:
    label = str(entry.get("label", ""))
    args = list(entry.get("args", []))
    if label == "deglitch":
        out_dir = _stage_arg_value(args, "--out-dir", str(repo_path("data/deglitched")))
        return Path(out_dir) / "deglitch_run_summary.json" if out_dir else None
    if label == "validation_deglitch":
        out_dir = _stage_arg_value(args, "--processed-dir", str(repo_path("data/processed")))
        processed_summary = Path(out_dir) / "deglitch_run_summary.json" if out_dir else None
        if processed_summary and processed_summary.exists():
            return processed_summary
        return repo_path("data/deglitched/deglitch_run_summary.json")
    return None


def _deglitch_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts = payload.get("status_counts")
    if isinstance(counts, dict) and counts:
        return {str(key): int(value) for key, value in counts.items()}
    out: dict[str, int] = {}
    for item in payload.get("events", []):
        status = str(item.get("overall_status", ""))
        if status:
            out[status] = out.get(status, 0) + 1
    return out


def _deglitch_attestation_from_payload(summary_path: Path, payload: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    events = payload.get("events", [])
    n_events = len(events) if isinstance(events, list) else sum(counts.values())
    complete = payload.get("run_status") == "complete"
    observed_statuses = set(counts)
    unverified_statuses = _unverified_deglitch_statuses(observed_statuses)
    verified = complete and bool(n_events) and observed_statuses == {VERIFIED_DEGLITCH_STATUS}
    accepted_partial_lane = complete and bool(n_events) and observed_statuses == {"succeeded_mps_only"}
    if verified:
        attestation_level = VERIFIED_DEGLITCH_STATUS
    elif accepted_partial_lane:
        attestation_level = "succeeded_mps_only"
    elif observed_statuses:
        attestation_level = _weakest_deglitch_status(observed_statuses)
    else:
        attestation_level = "unverified"
    return {
        "status": "pass" if verified else "fail",
        "detail": (
            "deglitch run summary verified MPS+UCLA for every event"
            if verified
            else (
                "deglitch run summary is missing verified MPS+UCLA status for every event; "
                f"unverified statuses: {', '.join(unverified_statuses) if unverified_statuses else 'none'}"
            )
        ),
        "summary_path": str(summary_path),
        "summary_sha256": _sha256_file(summary_path),
        "status_counts": counts,
        "verified_only_gate": VERIFIED_DEGLITCH_STATUS,
        "unverified_statuses": unverified_statuses,
        "attestation_level": attestation_level,
        "accepted_partial_lane_by_design": accepted_partial_lane,
        "n_events": n_events,
    }


def _deglitch_attestation_from_summary(summary_path: Path) -> dict[str, Any] | None:
    if not summary_path.exists():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _deglitch_attestation_from_payload(summary_path, payload, _deglitch_counts(payload))


def _deglitch_validation_attestation(summary: dict[str, Any]) -> dict[str, Any] | None:
    deglitch = summary.get("deglitch")
    if not isinstance(deglitch, dict):
        return None
    return {key: deglitch[key] for key in DEGLITCH_ATTESTATION_KEYS if key in deglitch}


def _deglitch_status_counts_allowed(counts: dict[str, int], allowed_statuses: list[str] | tuple[str, ...]) -> bool:
    return bool(counts) and set(counts).issubset(set(allowed_statuses))


def _deglitch_payload_allowed(payload: dict[str, Any] | None, allowed_statuses: list[str] | tuple[str, ...]) -> bool:
    if not isinstance(payload, dict):
        return False
    return _deglitch_status_counts_allowed(_deglitch_counts(payload), allowed_statuses)


def _deglitch_determined_failure(
    summary_path: Path,
    allowed_statuses: list[str] | tuple[str, ...],
) -> dict[str, Any] | None:
    if not summary_path.exists():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "check": "deglitch",
            "status": "failed",
            "detail": f"deglitch summary could not be parsed: {exc}",
            "summary_path": str(summary_path),
        }
    if payload.get("run_status") != "complete":
        return None
    counts = _deglitch_counts(payload)
    if _deglitch_status_counts_allowed(counts, allowed_statuses):
        return None
    attestation = _deglitch_attestation_from_payload(summary_path, payload, counts)
    observed = ", ".join(f"{key}={value}" for key, value in sorted(counts.items())) or "none"
    failure = {
        "check": "deglitch",
        "status": "failed",
        "detail": (
            "strict deglitch validation requires observed statuses to be in the declared allow-list "
            f"({', '.join(allowed_statuses)}); observed statuses: {observed}"
        ),
        "summary_path": str(summary_path),
        "status_counts": counts,
        "allowed_statuses": list(allowed_statuses),
    }
    failure.update({key: value for key, value in attestation.items() if key not in {"status", "detail"}})
    return failure


def _fragment_failure(check: str, fragment: dict[str, Any], args: argparse.Namespace) -> dict[str, Any] | None:
    summary = fragment.get("summary_fragment", {})
    check_payload: dict[str, Any] | None = None
    name = check
    if check == "inventory":
        check_payload = summary.get("inventory", {}).get("summary", {}).get("checks", {}).get("all_events_complete")
        name = "inventory.all_events_complete"
    elif check == "benchmark":
        check_payload = summary.get("benchmark", {}).get("check")
        if args.require_current_provenance and summary.get("benchmark", {}).get("current_provenance_status") != "current":
            return {
                "check": "current_provenance_enforcement",
                "status": "failed",
                "detail": "current provenance was requested but benchmark provenance is not current",
            }
    elif check == "bootstrap":
        check_payload = summary.get("bootstrap_fidelity")
        name = "bootstrap.fidelity"
    elif check == "preprocessing":
        for item in summary.get("preprocessing", []):
            item_check = item.get("check", {})
            if str(item_check.get("status", "")).lower() == "fail":
                detail = str(item_check.get("detail", "")).strip()
                event_id = str(item.get("event_id", "unknown"))
                return {"check": f"preprocessing.{event_id}", "status": "failed", "detail": detail or event_id}
    elif check == "alignment":
        for name, item in summary.get("alignment", {}).items():
            item_check = item.get("check", {})
            if str(item_check.get("status", "")).lower() == "fail":
                detail = str(item_check.get("detail", "")).strip()
                return {"check": f"alignment.{name}", "status": "failed", "detail": detail or name}
    elif check == "type2_distance_stratified":
        check_payload = summary.get("type2_distance_stratified")
    elif check == "type3_alignment_jitter":
        check_payload = summary.get("type3_alignment_jitter")
    elif check == "deglitch":
        check_payload = summary.get("deglitch")
        if _deglitch_payload_allowed(check_payload, args.allow_deglitch_status):
            return None
    elif check == "model":
        check_payload = summary.get("model", {}).get("check")
    if not check_payload or str(check_payload.get("status", "")).lower() != "fail":
        return None
    detail = str(check_payload.get("detail", "")).strip()
    return {"check": name, "status": "failed", "detail": detail or name}


def _incremental_validation_failures(args: argparse.Namespace) -> list[dict[str, Any]]:
    out_dir = _validation_out_dir(args) / "incremental_validation"
    failures = []
    for check in INCREMENTAL_VALIDATION_CHECKS:
        path = out_dir / f"{check}.json"
        if not path.exists():
            continue
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            failures.append({"check": check, "status": "failed", "detail": f"incremental validation fragment is unreadable: {exc}"})
            continue
        failure = _fragment_failure(check, fragment, args)
        if failure:
            failure["fragment_path"] = str(path)
            failures.append(failure)
    return failures


def _terminal_validation_determination(
    manifest: dict[str, Any],
    entry: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any] | None:
    if manifest.get("determined_terminal_validation"):
        return None
    failures: list[dict[str, Any]] = []
    summary_path = _deglitch_summary_path_from_stage(entry)
    if summary_path is not None:
        attestation = _deglitch_attestation_from_summary(summary_path)
        if attestation:
            manifest["deglitch_attestation"] = attestation
        failure = _deglitch_determined_failure(summary_path, args.allow_deglitch_status)
        if failure:
            failures.append(failure)
    failures.extend(_incremental_validation_failures(args))
    if not failures:
        return None
    return {
        "expected_terminal_status": "failed",
        "determined_at": _utc_now(),
        "determining_stage": entry["label"],
        "checks": failures,
    }


def _handle_determined_validation(
    manifest: dict[str, Any],
    entry: dict[str, Any],
    args: argparse.Namespace,
    manifest_path: Path,
) -> None:
    determination = _terminal_validation_determination(manifest, entry, args)
    if determination is None:
        return
    manifest["determined_terminal_validation"] = determination
    manifest["paper_ready"] = False
    if args.continue_despite_determined_validation:
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return
    manifest["execution_status"] = "stopped_determined_validation"
    manifest["status"] = "failed_validation_determined"
    manifest["validation_status"] = "failed"
    manifest["validation_failures"] = [item["detail"] for item in determination["checks"]]
    manifest["failed_stage"] = entry["label"]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raise DeterminedValidationError(
        f"Paper0 terminal validation determined failed after {entry['label']} (manifest: {manifest_path})"
    )


def run_paper0(args: argparse.Namespace) -> Path:
    args.allow_deglitch_status = validate_deglitch_statuses(args.allow_deglitch_status)
    input_audit = None
    if not args.from_scratch:
        input_audit = _run_production_input_audit()
    manifest_path = Path(args.manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if args.from_scratch and not args.dry_run:
        _clear_derived_outputs()
    if not args.dry_run:
        _clear_incremental_validation_state(args)
    commands = []
    if args.from_scratch:
        commands.extend(build_download_stage_commands(args))
    commands.extend(build_stage_commands(args))
    manifest: dict[str, Any] = {
        "created_at": _utc_now(),
        "git_commit": _git_commit(),
        "git_status_sha256": _git_status_sha(),
        "from_scratch": bool(args.from_scratch),
        "require_current_provenance": bool(args.require_current_provenance),
        "continue_despite_determined_validation": bool(args.continue_despite_determined_validation),
        "current_provenance_enforcement": {
            "requested": bool(args.require_current_provenance),
            "enforced": False,
            "status": "not_run",
        },
        "bootstrap_fidelity": fidelity_metadata(str(args.bootstrap_fidelity_level)),
        "dry_run": bool(args.dry_run),
        "stages": [],
        "execution_status": "in_progress",
        "validation_status": "not_run",
        "validation_failures": [],
        "determined_terminal_validation": None,
        "deglitch_attestation": None,
        "paper_ready": False,
        "status": "in_progress",
    }
    if input_audit is not None:
        manifest["input_audit"] = input_audit
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for stage in commands:
        if stage.get("kind") == "download":
            entry = _run_download_stage(stage, args)
        else:
            entry = {
                "label": stage["label"],
                "args": stage["args"],
                "started_at": _utc_now(),
            }
            if args.dry_run:
                entry.update({"status": "dry_run", "returncode": 0})
            else:
                if entry["label"] == "validation":
                    old_summary = _validation_summary_path(entry["args"], manifest_path)
                    if old_summary.exists():
                        old_summary.unlink()
                completed = subprocess.run(stage["args"], cwd=repo_path("."), text=True, capture_output=True, check=False)
                entry.update(
                    {
                        "status": "succeeded" if completed.returncode == 0 else "failed",
                        "returncode": int(completed.returncode),
                        "stdout_tail": completed.stdout[-4000:],
                        "stderr_tail": completed.stderr[-4000:],
                        "finished_at": _utc_now(),
                    }
                )
                if entry["label"] == "validation":
                    _apply_validation_stage_result(manifest, entry, args, manifest_path)
        manifest["stages"].append(entry)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not args.dry_run:
            _handle_determined_validation(manifest, entry, args, manifest_path)
        if entry["label"] == "validation" and entry["status"] == "validation_failed":
            manifest["execution_status"] = "succeeded"
            manifest["status"] = (
                "failed_validation_determined_continued"
                if manifest.get("determined_terminal_validation") and args.continue_despite_determined_validation
                else "failed_validation"
            )
            manifest["failed_stage"] = entry["label"]
            manifest["paper_ready"] = False
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if args.require_current_provenance and not bool(manifest["current_provenance_enforcement"].get("enforced")):
                raise RuntimeError(f"Paper0 current provenance enforcement failed (manifest: {manifest_path})")
            raise RuntimeError(f"Paper0 validation failed (manifest: {manifest_path})")
        if entry["status"] in {"failed", "failed_manifest_check"}:
            manifest["execution_status"] = "failed"
            manifest["status"] = "failed_execution"
            manifest["failed_stage"] = entry["label"]
            manifest["paper_ready"] = False
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raise RuntimeError(f"Paper0 stage failed: {entry['label']} (manifest: {manifest_path})")

    if args.dry_run:
        manifest["execution_status"] = "dry_run"
        manifest["validation_status"] = "not_run"
        manifest["paper_ready"] = False
        manifest["status"] = "dry_run"
    else:
        manifest["execution_status"] = "succeeded"
        if manifest.get("determined_terminal_validation") and manifest["validation_status"] != "failed":
            manifest["paper_ready"] = False
            manifest["status"] = "completed_with_determined_validation_failure"
        elif manifest["validation_status"] == "passed":
            manifest["paper_ready"] = True
            manifest["status"] = "succeeded"
        elif manifest["validation_status"] == "not_run":
            manifest["paper_ready"] = False
            manifest["status"] = "succeeded"
        else:
            manifest["paper_ready"] = False
            manifest["status"] = "failed_validation"
    manifest["finished_at"] = _utc_now()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the current Paper0 pipeline as a provenance-recorded DAG.")
    parser.add_argument("--preflight", action="store_true", help="Validate run configuration and inputs without executing stages.")
    parser.add_argument("--from-scratch", action="store_true", help="Delete known derived Paper0 outputs before running.")
    parser.add_argument("--require-current-provenance", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--manifest", default=str(repo_path("results/validation/paper0_run_manifest.json")))
    parser.add_argument("--data-manifest", default=str(repo_path("manifest/data_manifest.json")))
    parser.add_argument("--event-table", default=str(repo_path("manifest/event_table.csv")))
    parser.add_argument("--raw-dir", default=str(repo_path("data/raw")))
    parser.add_argument("--ak-out-dir", default=str(repo_path("data/models/ak_subset")))
    parser.add_argument("--khan-out-dir", default=str(repo_path("data/models/khan2023")))
    parser.add_argument("--mqs-catalog", default=str(repo_path("data/raw/mqs_v14_catalog.xml")))
    parser.add_argument("--seisglitch-command", default="auto")
    parser.add_argument("--seisglitch-pythonpath", default="")
    parser.add_argument(
        "--inventory-file",
        default="IRIS",
        help="A file path pins the SEISglitch station inventory; the default IRIS keeps the historical online fetch.",
    )
    parser.add_argument("--ucla-command", default="")
    parser.add_argument("--allow-deglitch-status", action="append", default=None)
    parser.add_argument("--allow-raw-diagnostic", action="store_true")
    parser.add_argument(
        "--continue-despite-determined-validation",
        action="store_true",
        help="Continue executing after known validation facts determine that the terminal strict gate will fail.",
    )
    parser.add_argument(
        "--bootstrap-fidelity-level",
        choices=sorted(BOOTSTRAP_FIDELITY_LEVELS),
        default=DEFAULT_BOOTSTRAP_FIDELITY_LEVEL,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.allow_deglitch_status is None:
        args.allow_deglitch_status = list(DEFAULT_ALLOWED_DEGLITCH_STATUSES)
    return args


def main() -> int:
    args = parse_args()
    if args.preflight:
        report = run_preflight(args)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "passed" else 2
    try:
        print(run_paper0(args))
        return 0
    except InputAuditError as exc:
        print(json.dumps(exc.diagnosis, indent=2, sort_keys=True), file=sys.stderr)
        return exc.returncode
    except DeterminedValidationError as exc:
        print(str(exc), file=sys.stderr)
        return exc.returncode


if __name__ == "__main__":
    sys.exit(main())
