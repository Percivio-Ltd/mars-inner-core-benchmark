from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from obspy import read

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import repo_path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MPS_STATUS_BLOCKED = "blocked_missing_seisglitch"
MPS_STATUS_IDENTITY = "identity_passthrough"
UCLA_STATUS_BLOCKED = "blocked_missing_ucla_runner"
STATUS_SUCCEEDED_MPS_ONLY = "succeeded_mps_only"
STATUS_UCLA_UNVERIFIED = "ucla_unverified"
STATUS_MPS_UCLA_VERIFIED = "mps_ucla_verified"
STATUS_SIDECAR_ATTESTED_NOT_VERIFIED = "sidecar_attested_not_independently_verified"
DEGLITCH_STATUS_VOCABULARY = (
    STATUS_SUCCEEDED_MPS_ONLY,
    STATUS_UCLA_UNVERIFIED,
    STATUS_MPS_UCLA_VERIFIED,
    STATUS_SIDECAR_ATTESTED_NOT_VERIFIED,
)
DEFAULT_ALLOWED_DEGLITCH_STATUSES = (STATUS_MPS_UCLA_VERIFIED,)
METHODS_REQUESTED = ["MPS", "UCLA"]
UCLA_HASH_VERIFICATION_EVIDENCE_KEYS = (
    "expected_output_sha256",
    "fixture_output_sha256",
    "verification_fixture_sha256",
)
UCLA_POINTER_VERIFICATION_EVIDENCE_KEYS = (
    "verification_evidence_uri",
    "verification_evidence_path",
)
UCLA_VERIFICATION_EVIDENCE_KEYS = UCLA_HASH_VERIFICATION_EVIDENCE_KEYS + UCLA_POINTER_VERIFICATION_EVIDENCE_KEYS


class CommandResult:
    def __init__(self, args: Sequence[str], returncode: int, stdout: str = "", stderr: str = ""):
        self.args = list(args)
        self.returncode = int(returncode)
        self.stdout = stdout
        self.stderr = stderr


Runner = Callable[[Sequence[str]], CommandResult]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_metadata(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _seisglitch_base_name(path: Path) -> str:
    parts = path.name.split(".")
    if len(parts) > 1:
        return ".".join(parts[:-1])
    return path.stem


def _expected_detector_file(waveform_path: Path) -> Path:
    return waveform_path.parent / f"glitches_{_seisglitch_base_name(waveform_path)}.txt"


def _expected_mps_output(waveform_path: Path) -> Path:
    suffix = waveform_path.suffix.lstrip(".") or "mseed"
    return waveform_path.parent / f"{_seisglitch_base_name(waveform_path)}_deglitched.{suffix}"


def build_seisglitch_config(
    waveform_path: Path,
    inventory_file: str,
    work_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    detector_file = _expected_detector_file(Path(waveform_path))
    return {
        "mode_order": ["detect", "remove"],
        "inventory_file": str(inventory_file),
        "waveform_files": [str(waveform_path)],
        "detect": {
            "detector": {
                "components": ["U", "V", "W"],
                "taper_length_per_side": 0.0,
                "pre_filt": False,
                "water_level": 60,
                "ACCfilter": {
                    "type": "bandpass",
                    "options": {
                        "freqmin": 0.001,
                        "freqmax": 0.1,
                        "corners": 3,
                        "zerophase": True,
                    },
                    "string": "0.001 < f < 0.1",
                },
                "threshold": 0.5e-9,
                "plot_triggering": False,
                "glitch_min_length": 5,
                "glitch_length": 25,
                "glitch_min_polarization": 0.91,
            }
        },
        "remove": {
            "glitch_detector_files": [str(detector_file)],
            "remover": {
                "preserve_raw_input": False,
                "glitch_window_leftright": 2,
                "glitch_prepend_zeros": 0,
                "glitch_interpolation_samples": 0,
                "glitch_subsample_factor": 1,
                "spike_fit": True,
                "spike_subsample_factor": 2,
                "spike_fit_samples_leftright": 7,
                "var_reduction_spike": 2,
                "var_reduction_total": 80,
                "show_fit": False,
                "store_glitches": True,
                "plot_removal_statistic": False,
            },
        },
        "ucla": {
            "status_if_unconfigured": UCLA_STATUS_BLOCKED,
            "input_expected": str(output_path),
            "runner_output_expected": str(work_dir / f"{output_path.stem}_ucla{output_path.suffix}"),
            "final_output_path": str(output_path),
        },
        "provenance": {
            "work_dir": str(work_dir),
            "final_output_path": str(output_path),
        },
    }


def _subprocess_runner(command: Sequence[str], **kwargs: Any) -> CommandResult:
    completed = subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        check=False,
        **kwargs,
    )
    return CommandResult(
        args=list(command),
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _build_command_env(seisglitch_pythonpath: Path | str | None) -> dict[str, str] | None:
    if seisglitch_pythonpath is None:
        return None
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    path = str(seisglitch_pythonpath)
    env["PYTHONPATH"] = path if not existing else f"{path}{os.pathsep}{existing}"
    return env


def _normalise_command(command: str | Sequence[str] | None) -> list[str] | None:
    if command is None:
        return None
    if isinstance(command, str):
        command = command.strip()
        if not command:
            return None
        return shlex.split(command)
    return [str(part) for part in command]


def resolve_seisglitch_command(command: str | Sequence[str] | None = "auto") -> list[str] | None:
    if command == "auto":
        found = shutil.which("seisglitch")
        return [found] if found else None
    return _normalise_command(command)


def _metadata_base(
    event_id: str,
    input_path: Path,
    output_path: Path,
    metadata_path: Path,
    work_dir: Path,
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "created_at": _utc_now(),
        "methods_requested": list(METHODS_REQUESTED),
        "input_path": str(input_path),
        "output_path": str(output_path),
        "metadata_path": str(metadata_path),
        "work_dir": str(work_dir),
        "samples_modified": False,
        "overall_status": "blocked",
        "mps": {"status": MPS_STATUS_BLOCKED},
        "ucla": {"status": "blocked_not_attempted"},
        "commands": [],
    }


def _path_contains(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _prepare_fresh_event_paths(input_path: Path, output_path: Path, work_event_dir: Path) -> None:
    if output_path.exists() and output_path.resolve() != input_path.resolve():
        output_path.unlink()
    if not work_event_dir.exists():
        return
    if _path_contains(work_event_dir, input_path):
        for stale in [
            _expected_detector_file(input_path),
            _expected_mps_output(input_path),
            work_event_dir / f"{input_path.stem}_ucla{input_path.suffix}",
        ]:
            if stale.exists() and stale.resolve() != input_path.resolve():
                stale.unlink()
        return
    shutil.rmtree(work_event_dir)


def _record_command(result: CommandResult) -> dict[str, Any]:
    return {
        "args": list(result.args),
        "returncode": int(result.returncode),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _sidecar_verification_evidence(sidecar_payload: Mapping[str, Any], actual_output_sha256: str) -> tuple[str, str, list[str]]:
    missing: list[str] = []
    if not str(sidecar_payload.get("algorithm", "")).strip():
        missing.append("algorithm")
    if not str(sidecar_payload.get("parameters_sha256", "")).strip():
        missing.append("parameters_sha256")

    evidence_key = ""
    evidence_value = ""
    for key in UCLA_VERIFICATION_EVIDENCE_KEYS:
        value = sidecar_payload.get(key)
        if str(value or "").strip():
            evidence_key = key
            evidence_value = str(value)
            break
    if not evidence_key:
        missing.append("expected_output_verification")
    elif evidence_key in UCLA_HASH_VERIFICATION_EVIDENCE_KEYS and evidence_value != actual_output_sha256:
        missing.append("expected_output_verification")
    elif evidence_key in UCLA_POINTER_VERIFICATION_EVIDENCE_KEYS:
        missing.append("expected_output_verification")

    return evidence_key, evidence_value, missing


def validate_deglitch_statuses(statuses: set[str] | Sequence[str] | None) -> set[str]:
    allowed = set(statuses or DEFAULT_ALLOWED_DEGLITCH_STATUSES)
    unknown = sorted(allowed.difference(DEGLITCH_STATUS_VOCABULARY))
    if unknown:
        expected = ", ".join(DEGLITCH_STATUS_VOCABULARY)
        raise ValueError(f"Unknown deglitch status: {', '.join(unknown)}; expected one of: {expected}")
    return allowed


def _streams_differ(left: Path, right: Path) -> bool:
    left_stream = sorted(read(str(left)), key=lambda tr: tr.id)
    right_stream = sorted(read(str(right)), key=lambda tr: tr.id)
    if len(left_stream) != len(right_stream):
        return True
    for left_trace, right_trace in zip(left_stream, right_stream):
        if left_trace.stats.channel != right_trace.stats.channel:
            return True
        if len(left_trace.data) != len(right_trace.data):
            return True
        if float(left_trace.stats.sampling_rate) != float(right_trace.stats.sampling_rate):
            return True
        if not np.array_equal(np.asarray(left_trace.data), np.asarray(right_trace.data)):
            return True
    return False


def _detector_file_has_glitch_rows(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("-") and not stripped.startswith("NUM"):
            return True
    return False


def _copy_stream(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    read(str(input_path)).write(str(output_path), format="MSEED")


def copy_mps_output_for_test(input_path: Path, output_path: Path, scale: float = 1.0) -> None:
    stream = read(str(input_path))
    for trace in stream:
        trace.data = np.asarray(trace.data, dtype=np.float32) * np.float32(scale)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stream.write(str(output_path), format="MSEED")


def _write_config_file(config_path: Path, config: Mapping[str, Any]) -> None:
    # JSON is valid YAML for SEISglitch's YAML loader and avoids a new runtime dependency.
    _write_json(config_path, config)


def _promote_mps_output(working_input: Path, output_path: Path) -> bool:
    if output_path.exists():
        return True
    inferred = _expected_mps_output(working_input)
    if not inferred.exists():
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(inferred, output_path)
    return True


def _run_ucla_if_configured(
    metadata: dict[str, Any],
    ucla_command: str | Sequence[str] | None,
    output_path: Path,
    work_event_dir: Path,
    runner: Callable[..., CommandResult],
) -> None:
    command = _normalise_command(ucla_command)
    if command is None:
        metadata["ucla"] = {
            "status": UCLA_STATUS_BLOCKED,
            "reason": "No public UCLA runner was configured; the known public scripts are MATLAB-oriented.",
        }
        metadata["overall_status"] = STATUS_SUCCEEDED_MPS_ONLY
        return

    ucla_output = work_event_dir / f"{output_path.stem}_ucla{output_path.suffix}"
    mps_backup = work_event_dir / f"{output_path.stem}_mps_before_ucla{output_path.suffix}"
    if output_path.exists():
        shutil.copy2(output_path, mps_backup)
    replacements = {
        "{input}": str(output_path),
        "{output}": str(ucla_output),
        "{work_dir}": str(work_event_dir),
    }
    formatted = []
    for part in command:
        value = str(part)
        for placeholder, replacement in replacements.items():
            value = value.replace(placeholder, replacement)
        formatted.append(value)
    result = runner(formatted, cwd=str(work_event_dir))
    metadata.setdefault("commands", []).append(_record_command(result))
    if result.returncode != 0:
        if mps_backup.exists():
            shutil.copy2(mps_backup, output_path)
        metadata["ucla"] = {
            "status": "failed",
            "returncode": result.returncode,
            "stderr": result.stderr,
        }
        metadata["overall_status"] = STATUS_SUCCEEDED_MPS_ONLY
        return

    if not ucla_output.exists():
        if mps_backup.exists():
            shutil.copy2(mps_backup, output_path)
        metadata["ucla"] = {
            "status": "failed_missing_ucla_output",
            "expected_output_path": str(ucla_output),
        }
        metadata["overall_status"] = STATUS_SUCCEEDED_MPS_ONLY
        return

    ucla_sidecar = ucla_output.with_suffix(ucla_output.suffix + ".ucla.json")
    sidecar_payload: dict[str, Any] = {}
    if ucla_sidecar.exists():
        try:
            sidecar_payload = json.loads(ucla_sidecar.read_text(encoding="utf-8"))
        except Exception:
            sidecar_payload = {"parse_error": "could_not_parse_ucla_sidecar"}
    ucla_input_sha256 = None
    if mps_backup.exists():
        ucla_input_sha256 = _sha256_file(mps_backup)
    shutil.copy2(ucla_output, output_path)
    output_sha256 = _sha256_file(output_path)
    sidecar_attested = sidecar_payload.get("verification_status") == STATUS_MPS_UCLA_VERIFIED
    evidence_key = ""
    evidence_value = ""
    missing_verified_evidence: list[str] = []
    if sidecar_attested:
        evidence_key, evidence_value, missing_verified_evidence = _sidecar_verification_evidence(sidecar_payload, output_sha256)

    if sidecar_attested and not missing_verified_evidence:
        ucla_status = STATUS_MPS_UCLA_VERIFIED
        contract_status = STATUS_MPS_UCLA_VERIFIED
        overall_status = STATUS_MPS_UCLA_VERIFIED
    elif sidecar_attested:
        ucla_status = STATUS_SIDECAR_ATTESTED_NOT_VERIFIED
        contract_status = STATUS_SIDECAR_ATTESTED_NOT_VERIFIED
        overall_status = STATUS_SIDECAR_ATTESTED_NOT_VERIFIED
    else:
        ucla_status = "external_ucla_command_wrote_file_unverified"
        contract_status = "output_file_verified_not_algorithm_equivalence"
        overall_status = STATUS_UCLA_UNVERIFIED
    metadata["ucla"] = {
        "status": ucla_status,
        "contract_status": contract_status,
        "output_path": str(ucla_output),
        "final_output_sha256": output_sha256,
        "ucla_input_sha256": ucla_input_sha256,
        "ucla_output_sha256": _sha256_file(ucla_output),
        "ucla_command_sha256": _sha256_text(json.dumps(formatted, sort_keys=True)),
        "ucla_runner_args": formatted,
        "ucla_sidecar_path": str(ucla_sidecar) if ucla_sidecar.exists() else "",
        "ucla_sidecar_sha256": _sha256_file(ucla_sidecar) if ucla_sidecar.exists() else "",
        "ucla_sidecar_verification_status": sidecar_payload.get("verification_status", "") if sidecar_payload else "",
        "ucla_sidecar_algorithm": sidecar_payload.get("algorithm", "") if sidecar_payload else "",
        "ucla_sidecar_parameters_sha256": sidecar_payload.get("parameters_sha256", "") if sidecar_payload else "",
        "ucla_sidecar_verification_evidence_key": evidence_key,
        "ucla_sidecar_verification_evidence": evidence_value,
        "ucla_sidecar_missing_verified_evidence": missing_verified_evidence,
        "samples_modified_ucla": _streams_differ(mps_backup, output_path) if mps_backup.exists() else None,
    }
    metadata["overall_status"] = overall_status


def run_deglitch_event(
    event_id: str,
    input_path: Path,
    output_path: Path,
    work_dir: Path,
    seisglitch_command: str | Sequence[str] | None = "auto",
    seisglitch_pythonpath: Path | str | None = None,
    ucla_command: str | Sequence[str] | None = None,
    inventory_file: str = "IRIS",
    runner: Callable[..., CommandResult] = _subprocess_runner,
) -> dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    work_dir = Path(work_dir)
    metadata_path = output_path.with_suffix(".deglitch.json")
    work_event_dir = work_dir / event_id
    metadata = _metadata_base(event_id, input_path, output_path, metadata_path, work_event_dir)
    identity_passthrough = seisglitch_command == "identity"
    if identity_passthrough:
        metadata["methods_requested"] = ["UCLA"]
    command_env = _build_command_env(seisglitch_pythonpath)
    if output_path.resolve() == input_path.resolve():
        metadata["overall_status"] = "failed"
        metadata["mps"] = {
            "status": "blocked_invalid_output_path",
            "reason": "Deglitch output path must differ from the raw input path.",
        }
        _write_json(metadata_path, metadata)
        return metadata
    _prepare_fresh_event_paths(input_path, output_path, work_event_dir)

    command = resolve_seisglitch_command(seisglitch_command)
    if command is None:
        metadata["mps"] = {
            "status": MPS_STATUS_BLOCKED,
            "reason": "SEISglitch executable was not found or not configured.",
        }
        _write_json(metadata_path, metadata)
        return metadata

    if not input_path.exists():
        metadata["mps"] = {
            "status": "blocked_missing_input",
            "reason": f"Missing raw UVW waveform file: {input_path}",
        }
        _write_json(metadata_path, metadata)
        return metadata

    if identity_passthrough:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work_event_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(input_path, output_path)
        metadata["mps"] = {"status": MPS_STATUS_IDENTITY}
        metadata["samples_modified"] = False
        _run_ucla_if_configured(metadata, ucla_command, output_path, work_event_dir, runner)
        if output_path.exists():
            metadata["samples_modified"] = _streams_differ(input_path, output_path)
        _write_json(metadata_path, metadata)
        return metadata

    work_event_dir.mkdir(parents=True, exist_ok=True)
    working_input = work_event_dir / input_path.name
    if working_input.resolve() != input_path.resolve():
        shutil.copy2(input_path, working_input)

    config = build_seisglitch_config(
        waveform_path=working_input,
        inventory_file=inventory_file,
        work_dir=work_event_dir,
        output_path=output_path,
    )
    config_path = work_event_dir / "seisglitch_config.yml"
    _write_config_file(config_path, config)
    metadata["mps"]["config_path"] = str(config_path)
    metadata["mps"]["working_input_path"] = str(working_input)

    detect_kwargs = {"cwd": str(work_event_dir)}
    if command_env is not None:
        detect_kwargs["env"] = command_env
    detect_result = runner([*command, "detect", str(config_path)], **detect_kwargs)
    metadata["commands"].append(_record_command(detect_result))
    if detect_result.returncode != 0:
        metadata["overall_status"] = "failed"
        metadata["mps"] = {
            "status": "failed_detect",
            "config_path": str(config_path),
            "returncode": detect_result.returncode,
            "stderr": detect_result.stderr,
        }
        _write_json(metadata_path, metadata)
        return metadata

    detector_file = _expected_detector_file(working_input)
    if not detector_file.exists():
        metadata["overall_status"] = "failed"
        metadata["mps"] = {
            "status": "failed_missing_detector_file",
            "config_path": str(config_path),
            "glitch_detector_file": str(detector_file),
        }
        _write_json(metadata_path, metadata)
        return metadata
    if detector_file.exists() and not _detector_file_has_glitch_rows(detector_file):
        _copy_stream(input_path, output_path)
        metadata["mps"] = {
            "status": "succeeded_no_glitches",
            "config_path": str(config_path),
            "glitch_detector_file": str(detector_file),
        }
        metadata["samples_modified"] = False
        _run_ucla_if_configured(metadata, ucla_command, output_path, work_event_dir, runner)
        if output_path.exists():
            metadata["samples_modified"] = _streams_differ(input_path, output_path)
        _write_json(metadata_path, metadata)
        return metadata

    remove_kwargs = {"cwd": str(work_event_dir)}
    if command_env is not None:
        remove_kwargs["env"] = command_env
    remove_result = runner([*command, "remove", str(config_path)], **remove_kwargs)
    metadata["commands"].append(_record_command(remove_result))
    if remove_result.returncode != 0:
        metadata["overall_status"] = "failed"
        metadata["mps"] = {
            "status": "failed_remove",
            "config_path": str(config_path),
            "glitch_detector_file": str(detector_file),
            "returncode": remove_result.returncode,
            "stderr": remove_result.stderr,
        }
        _write_json(metadata_path, metadata)
        return metadata

    if not _promote_mps_output(working_input, output_path):
        metadata["overall_status"] = "failed"
        metadata["mps"] = {
            "status": "failed_missing_mps_output",
            "config_path": str(config_path),
            "glitch_detector_file": str(detector_file),
            "expected_mps_output": str(_expected_mps_output(working_input)),
        }
        _write_json(metadata_path, metadata)
        return metadata

    metadata["mps"] = {
        "status": "succeeded",
        "config_path": str(config_path),
        "glitch_detector_file": str(detector_file),
    }
    metadata["samples_modified"] = _streams_differ(input_path, output_path)
    _run_ucla_if_configured(metadata, ucla_command, output_path, work_event_dir, runner)
    if output_path.exists():
        metadata["samples_modified"] = _streams_differ(input_path, output_path)
    _write_json(metadata_path, metadata)
    return metadata


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run public MPS/SEISglitch deglitching, with explicit UCLA provenance, before UVW->ZNE rotation."
    )
    parser.add_argument("--in-dir", default=str(repo_path("data/raw")))
    parser.add_argument("--out-dir", default=str(repo_path("data/deglitched")))
    parser.add_argument("--work-dir", default=str(repo_path("data/processed/deglitch_work")))
    parser.add_argument("--inventory-file", default="IRIS")
    parser.add_argument(
        "--seisglitch-command",
        default="auto",
        help="Command for SEISglitch/MPS, 'identity' for byte-verbatim passthrough, 'auto' to use PATH, or 'none' to write blocked metadata.",
    )
    parser.add_argument(
        "--seisglitch-pythonpath",
        default=None,
        help="Optional path to a public SEISglitch checkout to prepend to PYTHONPATH for direct script execution.",
    )
    parser.add_argument(
        "--ucla-command",
        default=None,
        help="Optional UCLA runner command. Tokens {input}, {output}, and {work_dir} are substituted.",
    )
    parser.add_argument(
        "--allow-status",
        action="append",
        default=None,
        help="Allow a terminal event status in batch mode. Defaults to requiring mps_ucla_verified for every event.",
    )
    return parser


def parse_args():
    parser = build_arg_parser()
    return parser.parse_args()


def run_all(
    in_dir: Path,
    out_dir: Path,
    work_dir: Path,
    seisglitch_command: str | Sequence[str] | None = "auto",
    seisglitch_pythonpath: Path | str | None = None,
    ucla_command: str | Sequence[str] | None = None,
    inventory_file: str = "IRIS",
    allowed_statuses: set[str] | Sequence[str] | None = None,
) -> int:
    allowed = validate_deglitch_statuses(allowed_statuses)
    methods_requested = ["UCLA"] if seisglitch_command == "identity" else list(METHODS_REQUESTED)
    files = sorted(Path(in_dir).glob("*.mseed"))
    if not files:
        raise FileNotFoundError(f"No raw MiniSEED inputs found in {in_dir}")
    expected_event_ids = [path.stem for path in files]
    summary_path = Path(out_dir) / "deglitch_run_summary.json"
    _write_json(
        summary_path,
        {
            "created_at": _utc_now(),
            "run_status": "in_progress",
            "methods_requested": methods_requested,
            "allowed_statuses": sorted(allowed),
            "expected_event_ids": expected_event_ids,
            "status_counts": {},
            "events": [],
        },
    )
    event_summaries = []
    for path in files:
        metadata = run_deglitch_event(
            event_id=path.stem,
            input_path=path,
            output_path=Path(out_dir) / path.name,
            work_dir=work_dir,
            seisglitch_command=seisglitch_command,
            seisglitch_pythonpath=seisglitch_pythonpath,
            ucla_command=ucla_command,
            inventory_file=inventory_file,
        )
        logger.info("%s: %s", path.stem, metadata["overall_status"])
        event_summaries.append(
            {
                "event_id": metadata["event_id"],
                "overall_status": metadata["overall_status"],
                "mps_status": metadata.get("mps", {}).get("status"),
                "ucla_status": metadata.get("ucla", {}).get("status"),
                "metadata_path": metadata["metadata_path"],
                "output_path": metadata["output_path"],
                "samples_modified": metadata["samples_modified"],
            }
        )
    status_counts = Counter(item["overall_status"] for item in event_summaries)
    summary = {
        "created_at": _utc_now(),
        "run_status": "complete",
        "methods_requested": methods_requested,
        "allowed_statuses": sorted(allowed),
        "expected_event_ids": expected_event_ids,
        "status_counts": dict(sorted(status_counts.items())),
        "events": event_summaries,
    }
    _write_json(summary_path, summary)
    disallowed = [item for item in event_summaries if item["overall_status"] not in allowed]
    if disallowed:
        bad = ", ".join(f"{item['event_id']}={item['overall_status']}" for item in disallowed)
        raise RuntimeError(f"Disallowed deglitch statuses: {bad}")
    return len(files)


def main() -> None:
    args = parse_args()
    seisglitch_command = None if str(args.seisglitch_command).lower() == "none" else args.seisglitch_command
    run_all(
        in_dir=Path(args.in_dir),
        out_dir=Path(args.out_dir),
        work_dir=Path(args.work_dir),
        seisglitch_command=seisglitch_command,
        seisglitch_pythonpath=args.seisglitch_pythonpath,
        ucla_command=args.ucla_command,
        inventory_file=args.inventory_file,
        allowed_statuses=validate_deglitch_statuses(args.allow_status),
    )


if __name__ == "__main__":
    main()
