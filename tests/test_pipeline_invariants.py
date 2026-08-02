from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from obspy import Stream, Trace, UTCDateTime
import pytest

from scripts.shared import (
    PAPERSTYLE_ALIGNMENT_REVISION,
    find_best_event_match,
    read_catalog,
    import_local_module,
    repo_path,
    sha256_file,
)
from scripts.shared import write_manifest, load_manifest

normalize_and_save = import_local_module(
    "marsquake_normalize_and_envelope_test",
    "scripts/02_preprocess/normalize_and_envelope.py",
).normalize_and_save
run_paper0_mod = import_local_module(
    "marsquake_run_paper0_test",
    "scripts/run_paper0.py",
)


def _write_trace(path: Path, data, sampling_rate: float = 20.0):
    tr = Trace(data=np.asarray(data, dtype=np.float32))
    tr.stats.sampling_rate = sampling_rate
    tr.stats.network = "XB"
    st = Stream([tr])
    path.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(path), format="MSEED")


def _write_alignment_contract(path: Path, event: str, mode: str, out_dir: Path, npts: int, time_axis: np.ndarray | None = None):
    if time_axis is None:
        time_axis = np.arange(npts, dtype=np.float64) / 20.0 - 100.0
    time_path = out_dir / f"{event}_{mode}_times.npy"
    mask_path = out_dir / f"{event}_{mode}_valid_samples.npy"
    np.save(time_path, time_axis.astype(np.float64))
    np.save(mask_path, np.ones(npts, dtype=bool))
    path.with_suffix(".alignment.json").write_text(
        json.dumps(
            {
                "event_id": event,
                "mode": mode,
                "algorithm_revision": PAPERSTYLE_ALIGNMENT_REVISION,
                "output_trace_sha256": sha256_file(path),
                "time_axis_sha256": sha256_file(time_path),
                "valid_sample_mask_sha256": sha256_file(mask_path),
                "sampling_rate_hz": 20.0,
                "npts": npts,
            }
        ),
        encoding="utf-8",
    )


def test_normalize_and_envelope_output_shape_contract(tmp_path):
    event = "S0001"
    mode = "ablation"
    in_path = tmp_path / f"{event}_{mode}_input.mseed"
    data = np.linspace(-1.0, 1.0, 1200)
    _write_trace(in_path, data)
    time_axis = np.linspace(-100.0, 2200.0, data.size)
    _write_alignment_contract(in_path, event, mode, tmp_path, data.size, time_axis)

    normalize_and_save(event, mode, in_path, time_axis, tmp_path)

    for variant in ("A", "B", "C"):
        wf = np.load(tmp_path / f"{event}_{mode}_{variant}_waveform.npy")
        env = np.load(tmp_path / f"{event}_{mode}_{variant}_envelope.npy")
        t = np.load(tmp_path / f"{event}_{mode}_{variant}_times.npy")
        assert wf.shape == data.shape
        assert env.shape == data.shape
        assert t.shape == data.shape
        assert np.isfinite(wf).all()

    assert (tmp_path / f"{event}_{mode}_A_waveform.npy").exists()
    assert (tmp_path / f"{event}_{mode}_C_envelope.npy").exists()


def test_normalize_and_envelope_rejects_zero_std_trace(tmp_path):
    event = "S0002"
    mode = "paperfaith"
    in_path = tmp_path / f"{event}_{mode}_input.mseed"
    data = np.ones(600, dtype=np.float32)
    _write_trace(in_path, data)
    time_axis = np.linspace(-100.0, 2200.0, data.size)
    _write_alignment_contract(in_path, event, mode, tmp_path, data.size, time_axis)

    with pytest.raises(ValueError, match="Zero-variance normalization window"):
        normalize_and_save(event, mode, in_path, time_axis, tmp_path)

    assert not (tmp_path / f"{event}_{mode}_A_waveform.npy").exists()
    assert not (tmp_path / f"{event}_{mode}_B_waveform.npy").exists()
    assert not (tmp_path / f"{event}_{mode}_C_waveform.npy").exists()


def test_manifest_item_requires_path_and_checksum(tmp_path):
    manifest = tmp_path / "manifest" / "data_manifest.json"
    write_manifest(manifest, {"created_at": "2026-01-01T00:00:00Z", "items": []})

    # missing required runtime keys should fail this contract check
    payload = load_manifest(manifest)
    payload["items"].append({"path": "data/raw/missing.mseed"})
    write_manifest(manifest, payload)

    loaded = load_manifest(manifest)
    assert len(loaded["items"]) == 1
    item = loaded["items"][0]
    assert "sha256" not in item
    assert "path" in item


def test_normalize_and_save_requires_alignment_metadata_and_valid_mask(tmp_path):
    event = "S0004"
    mode = "ablation"
    in_path = tmp_path / f"{event}_{mode}.mseed"
    data = np.linspace(-1.0, 1.0, 400)
    _write_trace(in_path, data)

    with pytest.raises(FileNotFoundError, match="alignment metadata"):
        normalize_and_save(event, mode, in_path, np.arange(data.size, dtype=np.float64) / 20.0 - 100.0, tmp_path)


def test_normalize_and_save_excludes_zero_padded_samples_from_statistics(tmp_path):
    event = "S0005"
    mode = "ablation"
    in_path = tmp_path / f"{event}_{mode}.mseed"
    data = np.concatenate([np.zeros(100), np.linspace(1.0, 2.0, 300)]).astype(np.float32)
    _write_trace(in_path, data)
    time_axis = np.linspace(-100.0, 2200.0, data.size)
    _write_alignment_contract(in_path, event, mode, tmp_path, data.size, time_axis)
    mask_path = tmp_path / f"{event}_{mode}_valid_samples.npy"
    mask = np.ones(data.size, dtype=bool)
    mask[:100] = False
    np.save(mask_path, mask)
    metadata_path = in_path.with_suffix(".alignment.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["valid_sample_mask_sha256"] = sha256_file(mask_path)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    normalize_and_save(event, mode, in_path, time_axis, tmp_path)

    metadata = json.loads((tmp_path / f"{event}_{mode}_C.normalization.json").read_text(encoding="utf-8"))
    assert metadata["normalization_valid_sample_count"] == 300


def test_read_catalog_accepts_xml_suffix(tmp_path):
    xml = tmp_path / "events.xml"
    xml.write_text("<q></q>")
    with pytest.raises(Exception):
        read_catalog(xml)


def test_catalog_missing_path_fails_fast(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_catalog(tmp_path / "does-not-exist.xml")


def test_find_best_event_match_rejects_far_fallbacks():
    catalog = [
        {
            "resource_id": "event-a",
            "descriptions": [],
            "origins": [{"resource_id": "origin-a", "time": UTCDateTime("2020-01-01T00:10:00Z"), "arrivals": []}],
        }
    ]
    with pytest.raises(ValueError, match="within 30 s"):
        find_best_event_match(catalog, "S0000x", "2020-01-01T00:00:00Z")


def test_paper0_orchestrator_dry_run_writes_stage_manifest(tmp_path):
    args = run_paper0_mod.parse_args([])
    args.from_scratch = False
    args.dry_run = True
    args.manifest = str(tmp_path / "paper0_run_manifest.json")

    manifest_path = run_paper0_mod.run_paper0(args)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    labels = [stage["label"] for stage in payload["stages"]]
    assert payload["execution_status"] == "dry_run"
    assert payload["validation_status"] == "not_run"
    assert payload["status"] == "dry_run"
    assert labels[:5] == ["deglitch", "validation_deglitch", "rotate", "bandpass", "polarization"]
    assert labels[-1] == "validation"
    assert "--aggregate-only" in payload["stages"][-1]["args"]
    assert "--strict-gates" in payload["stages"][-1]["args"]
    assert "--require-current-provenance" in payload["stages"][-1]["args"]


def test_paper0_preflight_reports_all_findings_without_writing_results(tmp_path):
    args = run_paper0_mod.parse_args(
        [
            "--preflight",
            "--manifest",
            str(tmp_path / "results" / "validation" / "paper0_run_manifest.json"),
            "--data-manifest",
            str(tmp_path / "manifest" / "missing_data_manifest.json"),
            "--event-table",
            str(tmp_path / "manifest" / "missing_event_table.csv"),
            "--mqs-catalog",
            str(tmp_path / "data" / "raw" / "missing_catalog.xml"),
            "--seisglitch-command",
            str(tmp_path / "bin" / "missing-seisglitch"),
            "--allow-deglitch-status",
            "partial_mps_only",
            "--allow-deglitch-status",
            "succeeded_mps_only",
        ]
    )

    report = run_paper0_mod.run_preflight(args)

    assert report["status"] == "failed"
    codes = {finding["code"] for finding in report["findings"]}
    assert {
        "missing_data_manifest",
        "missing_event_table",
        "missing_mqs_catalog",
        "seisglitch_command_unresolved",
        "unknown_deglitch_status",
        "strict_gate_unreachable",
    }.issubset(codes)
    assert not (tmp_path / "results").exists()


def test_paper0_preflight_checks_local_inventory_path(tmp_path, monkeypatch):
    missing_inventory = tmp_path / "missing_inventory.xml"
    args = run_paper0_mod.parse_args(["--inventory-file", str(missing_inventory)])
    _disable_preflight_io_checks(monkeypatch)

    report = run_paper0_mod.run_preflight(args)

    inventory_findings = [finding for finding in report["findings"] if finding["code"] == "inventory_file_missing"]
    assert report["status"] == "failed"
    assert inventory_findings == [
        {
            "severity": "error",
            "code": "inventory_file_missing",
            "detail": f"SEISglitch inventory file does not exist: {missing_inventory}",
            "path": str(missing_inventory),
        }
    ]

    existing_inventory = tmp_path / "inventory.xml"
    existing_inventory.write_text("<Inventory />", encoding="utf-8")
    for inventory_file in ("IRIS", str(existing_inventory)):
        args = run_paper0_mod.parse_args(["--inventory-file", inventory_file])
        report = run_paper0_mod.run_preflight(args)
        assert report["status"] == "passed"
        assert all(finding["code"] != "inventory_file_missing" for finding in report["findings"])


def test_paper0_preflight_warns_for_declared_partial_deglitch_allowlist(monkeypatch):
    args = run_paper0_mod.parse_args(["--allow-deglitch-status", "succeeded_mps_only"])
    _disable_preflight_io_checks(monkeypatch)

    report = run_paper0_mod.run_preflight(args)

    strict_gate = [finding for finding in report["findings"] if finding["code"] == "strict_gate_unreachable"]
    assert report["status"] == "passed"
    assert len(strict_gate) == 1
    assert strict_gate[0]["severity"] == "warning"
    assert strict_gate[0]["allowed_statuses"] == ["succeeded_mps_only"]
    assert strict_gate[0]["verified_only_gate"] == "mps_ucla_verified"
    assert strict_gate[0]["unverified_statuses"] == ["succeeded_mps_only"]
    assert strict_gate[0]["attestation_level"] == "succeeded_mps_only"


def test_paper0_preflight_preserves_ucla_command_missing_warning_when_verified_allowed(monkeypatch):
    args = run_paper0_mod.parse_args(
        [
            "--allow-deglitch-status",
            "mps_ucla_verified",
            "--allow-deglitch-status",
            "succeeded_mps_only",
        ]
    )
    _disable_preflight_io_checks(monkeypatch)

    report = run_paper0_mod.run_preflight(args)

    findings = {finding["code"]: finding for finding in report["findings"]}
    assert report["status"] == "passed"
    assert "strict_gate_unreachable" not in findings
    assert findings["ucla_command_missing_for_verified_gate"]["severity"] == "warning"


def test_paper0_orchestrator_wires_type2_provenance_and_bootstrap_fidelity():
    args = run_paper0_mod.parse_args(
        [
            "--bootstrap-fidelity-level",
            "methods_robustness_200",
            "--require-current-provenance",
            "--inventory-file",
            "custom-inventory.xml",
        ]
    )

    commands = run_paper0_mod.build_stage_commands(args)
    by_label = {stage["label"]: stage["args"] for stage in commands}
    labels = [stage["label"] for stage in commands]

    assert labels[labels.index("bootstrap_type1") + 1] == "bootstrap_type2"
    assert by_label["bootstrap_type1"][-6:] == [
        "--input-type",
        "envelope",
        "--n-bootstrap",
        "200",
        "--bootstrap-fidelity-level",
        "methods_robustness_200",
    ]
    assert by_label["bootstrap_type2"][-6:] == [
        "--input-type",
        "envelope",
        "--n-bootstrap",
        "200",
        "--bootstrap-fidelity-level",
        "methods_robustness_200",
    ]
    assert by_label["bootstrap_type3"][-6:] == [
        "--input-type",
        "envelope",
        "--n-bootstrap",
        "200",
        "--bootstrap-fidelity-level",
        "methods_robustness_200",
    ]
    assert "--require-current-provenance" in by_label["detect_peaks"]
    assert "--require-current-provenance" in by_label["validation"]
    assert "--strict-gates" in by_label["validation"]
    inventory_index = by_label["deglitch"].index("--inventory-file")
    assert by_label["deglitch"][inventory_index : inventory_index + 2] == [
        "--inventory-file",
        "custom-inventory.xml",
    ]


def test_paper0_stage_plan_runs_incremental_validation_before_terminal_aggregate():
    args = run_paper0_mod.parse_args(["--require-current-provenance"])

    commands = run_paper0_mod.build_stage_commands(args)
    labels = [stage["label"] for stage in commands]
    by_label = {stage["label"]: stage["args"] for stage in commands}

    assert labels[labels.index("deglitch") + 1] == "validation_deglitch"
    assert labels.index("validation_inventory") > labels.index("normalize")
    assert labels.index("validation_preprocessing") > labels.index("normalize")
    assert labels.index("validation_alignment") > labels.index("normalize")
    assert labels.index("validation_benchmark") > labels.index("vespagrams")
    assert labels.index("validation_type2_distance_stratified") > labels.index("bootstrap_type2")
    assert labels.index("validation_type3_alignment_jitter") > labels.index("bootstrap_type3")
    assert labels.index("validation_bootstrap") > labels.index("fit_bootstrap")
    assert labels[-1] == "validation"
    assert "--aggregate-only" in by_label["validation"]
    assert "--incremental-check" not in by_label["validation"]
    inventory_index = by_label["deglitch"].index("--inventory-file")
    assert by_label["deglitch"][inventory_index : inventory_index + 2] == ["--inventory-file", "IRIS"]
    for label in labels:
        if label.startswith("validation_"):
            assert "--incremental-check" in by_label[label]
            assert "--out-dir" in by_label[label]


def _write_data_manifest(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"created_at": "2026-01-01T00:00:00Z", "items": items}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _paper0_args(tmp_path: Path):
    args = run_paper0_mod.parse_args([])
    args.from_scratch = True
    args.dry_run = True
    args.manifest = str(tmp_path / "paper0_run_manifest.json")
    args.data_manifest = str(tmp_path / "manifest" / "data_manifest.json")
    args.event_table = str(tmp_path / "manifest" / "event_table.csv")
    args.raw_dir = str(tmp_path / "data" / "raw")
    args.ak_out_dir = str(tmp_path / "data" / "models" / "ak_subset")
    args.khan_out_dir = str(tmp_path / "data" / "models" / "khan2023")
    args.mqs_catalog = str(tmp_path / "data" / "raw" / "mqs_v14_catalog.xml")
    return args


def _write_event_table(path: Path, event_ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "event_id,origin_time,set\n"
        + "".join(f"{event_id},2021-01-01T00:00:00Z,vespagram\n" for event_id in event_ids),
        encoding="utf-8",
    )


def _valid_download_fixture(tmp_path: Path, event_ids: list[str]) -> list[dict]:
    items = []
    raw_dir = tmp_path / "data" / "raw"
    for event_id in event_ids:
        path = raw_dir / f"{event_id}.mseed"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"{event_id}-waveform".encode("utf-8"))
        items.append({"type": "waveform", "event_id": event_id, "path": str(path.relative_to(tmp_path)), "sha256": sha256_file(path)})

    mqs = raw_dir / "mqs_v14_catalog.xml"
    mqs.write_text("<quakeml></quakeml>", encoding="utf-8")
    items.append({"type": "mqs_catalog", "path": str(mqs.relative_to(tmp_path)), "sha256": sha256_file(mqs)})

    ak = tmp_path / "data" / "models" / "ak_subset" / "ak_subset_raw" / "AK_model_1.nd"
    ak.parent.mkdir(parents=True, exist_ok=True)
    ak.write_text("mantle\n", encoding="utf-8")
    items.append(
        {
            "type": "model_extracted",
            "dataset_pid": run_paper0_mod.AK_DATASET_PID,
            "path": str(ak.relative_to(tmp_path)),
            "sha256": sha256_file(ak),
        }
    )
    items.append({"type": "model_archive", "dataset_pid": run_paper0_mod.AK_DATASET_PID, "dataset_name": "ak_subset"})

    khan = tmp_path / "data" / "models" / "khan2023" / "README.txt"
    khan.parent.mkdir(parents=True, exist_ok=True)
    khan.write_text("khan models\n", encoding="utf-8")
    items.append(
        {
            "type": "model_file",
            "dataset_pid": run_paper0_mod.KHAN_DATASET_PID,
            "path": str(khan.relative_to(tmp_path)),
            "sha256": sha256_file(khan),
        }
    )
    items.append({"type": "model_mapping", "dataset_pid": run_paper0_mod.KHAN_DATASET_PID, "mapping": {"status": "test"}})
    return items


def _write_deglitch_summary(summary_path: Path, status_counts: dict[str, int]) -> None:
    events = []
    for status, count in status_counts.items():
        for _idx in range(count):
            event_id = f"S{len(events) + 1:04d}"
            events.append({"event_id": event_id, "overall_status": status})
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(
            {
                "run_status": "complete",
                "expected_event_ids": [event["event_id"] for event in events],
                "status_counts": status_counts,
                "events": events,
            }
        ),
        encoding="utf-8",
    )


def _mps_only_deglitch_attestation(summary_path: Path, n_events: int) -> dict:
    return {
        "status": "fail",
        "detail": "deglitch run summary is missing verified MPS+UCLA status for every event; unverified statuses: succeeded_mps_only",
        "summary_path": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "status_counts": {"succeeded_mps_only": n_events},
        "verified_only_gate": "mps_ucla_verified",
        "unverified_statuses": ["succeeded_mps_only"],
        "attestation_level": "succeeded_mps_only",
        "accepted_partial_lane_by_design": True,
        "n_events": n_events,
    }


def _disable_preflight_io_checks(monkeypatch) -> None:
    monkeypatch.setattr(run_paper0_mod, "_check_declared_env", lambda _findings: None)
    monkeypatch.setattr(run_paper0_mod, "_check_seisglitch_resolution", lambda _args, _findings: None)
    monkeypatch.setattr(run_paper0_mod, "_check_readable_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_paper0_mod, "_check_event_table", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_paper0_mod, "_check_readable_file", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(run_paper0_mod, "_check_output_writability", lambda *_args, **_kwargs: None)


def test_paper0_from_scratch_dry_run_plans_download_stages(tmp_path):
    _write_event_table(tmp_path / "manifest" / "event_table.csv", ["S0001", "S0002"])
    _write_data_manifest(tmp_path / "manifest" / "data_manifest.json", [])
    args = _paper0_args(tmp_path)

    manifest_path = run_paper0_mod.run_paper0(args)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    stages = payload["stages"]
    assert [stage["label"] for stage in stages[:4]] == [
        "download_waveforms",
        "download_ak_models",
        "download_khan_models",
        "download_mqs_catalog",
    ]
    assert stages[0]["status"] == "dry_run"
    assert stages[0]["action"] == "would_run"
    assert stages[0]["audit"]["missing_paths"] == ["data/raw/S0001.mseed", "data/raw/S0002.mseed"]
    assert stages[3]["audit"]["missing_paths"] == ["data/raw/mqs_v14_catalog.xml"]


def test_paper0_from_scratch_skips_valid_download_manifest_entries(tmp_path, monkeypatch):
    event_ids = ["S0001"]
    _write_event_table(tmp_path / "manifest" / "event_table.csv", event_ids)
    _write_data_manifest(tmp_path / "manifest" / "data_manifest.json", _valid_download_fixture(tmp_path, event_ids))
    args = _paper0_args(tmp_path)
    args.dry_run = False
    calls = []

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", lambda _args: [])
    monkeypatch.setattr(run_paper0_mod, "_clear_derived_outputs", lambda: None)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", lambda stage_args, **kwargs: calls.append(stage_args))

    manifest_path = run_paper0_mod.run_paper0(args)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["execution_status"] == "succeeded"
    assert payload["validation_status"] == "not_run"
    assert calls == []
    assert [stage["status"] for stage in payload["stages"][:4]] == ["skipped", "skipped", "skipped", "skipped"]
    assert {stage["action"] for stage in payload["stages"][:4]} == {"manifest_valid"}


def test_paper0_default_deglitch_allowlist_stops_on_mps_only_terminal_validation(tmp_path, monkeypatch):
    deglitch_dir = tmp_path / "deglitched"
    args = run_paper0_mod.parse_args([])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(tmp_path / "validation" / "paper0_run_manifest.json")
    calls = []

    def fake_commands(_args):
        return [
            {
                "label": "deglitch",
                "args": [
                    sys.executable,
                    "scripts/02_preprocess/deglitch_mps_ucla.py",
                    "--out-dir",
                    str(deglitch_dir),
                ],
            },
            {
                "label": "rotate",
                "args": [
                    sys.executable,
                    "scripts/02_preprocess/rotate_uvw_to_zne.py",
                    "--in-dir",
                    str(deglitch_dir),
                ],
            },
        ]

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(stage_args, **_kwargs):
        calls.append(stage_args[1])
        _write_deglitch_summary(deglitch_dir / "deglitch_run_summary.json", {"succeeded_mps_only": 1})
        return Completed()

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    with pytest.raises(run_paper0_mod.DeterminedValidationError) as excinfo:
        run_paper0_mod.run_paper0(args)

    assert excinfo.value.returncode == 2
    assert calls == ["scripts/02_preprocess/deglitch_mps_ucla.py"]
    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    determined = payload["determined_terminal_validation"]
    assert payload["status"] == "failed_validation_determined"
    assert payload["execution_status"] == "stopped_determined_validation"
    assert determined["expected_terminal_status"] == "failed"
    assert determined["determining_stage"] == "deglitch"
    assert determined["checks"][0]["check"] == "deglitch"
    assert "mps_ucla_verified" in determined["checks"][0]["detail"]
    assert determined["checks"][0]["attestation_level"] == "succeeded_mps_only"
    assert determined["checks"][0]["unverified_statuses"] == ["succeeded_mps_only"]


def test_paper0_declared_mps_only_deglitch_allowlist_can_reach_paper_ready_with_attestation(
    tmp_path, monkeypatch
):
    deglitch_dir = tmp_path / "deglitched"
    validation_dir = tmp_path / "validation"
    summary_path = deglitch_dir / "deglitch_run_summary.json"
    args = run_paper0_mod.parse_args(["--allow-deglitch-status", "succeeded_mps_only"])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(validation_dir / "paper0_run_manifest.json")
    calls = []

    def fake_commands(_args):
        return [
            {
                "label": "deglitch",
                "args": [
                    sys.executable,
                    "scripts/02_preprocess/deglitch_mps_ucla.py",
                    "--out-dir",
                    str(deglitch_dir),
                ],
            },
            {
                "label": "validation",
                "args": [
                    sys.executable,
                    "scripts/07_validation/generate_validation_report.py",
                    "--aggregate-only",
                    "--strict-gates",
                    "--out-dir",
                    str(validation_dir),
                ],
            },
        ]

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(stage_args, **_kwargs):
        calls.append(stage_args[1])
        if any("deglitch_mps_ucla.py" in part for part in stage_args):
            _write_deglitch_summary(summary_path, {"succeeded_mps_only": 2})
            return Completed()
        validation_dir.mkdir(parents=True, exist_ok=True)
        (validation_dir / "validation_summary.json").write_text(
            json.dumps(
                {
                    "deglitch": _mps_only_deglitch_attestation(summary_path, 2),
                    "validation_status": {"status": "passed", "failures": [], "paper_ready": True},
                    "current_provenance_enforcement": {
                        "requested": True,
                        "enforced": True,
                        "status": "current",
                    },
                }
            ),
            encoding="utf-8",
        )
        return Completed()

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    manifest_path = run_paper0_mod.run_paper0(args)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert calls == [
        "scripts/02_preprocess/deglitch_mps_ucla.py",
        "scripts/07_validation/generate_validation_report.py",
    ]
    assert payload["status"] == "succeeded"
    assert payload["validation_status"] == "passed"
    assert payload["paper_ready"] is True
    assert payload["determined_terminal_validation"] is None
    assert payload["deglitch_attestation"]["attestation_level"] == "succeeded_mps_only"
    assert payload["deglitch_attestation"]["unverified_statuses"] == ["succeeded_mps_only"]
    assert payload["deglitch_attestation"]["verified_only_gate"] == "mps_ucla_verified"


def test_paper0_continue_flag_records_determined_terminal_failure_and_runs_remaining_stages(tmp_path, monkeypatch):
    deglitch_dir = tmp_path / "deglitched"
    args = run_paper0_mod.parse_args(["--continue-despite-determined-validation"])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(tmp_path / "validation" / "paper0_run_manifest.json")
    calls = []

    def fake_commands(_args):
        return [
            {
                "label": "deglitch",
                "args": [
                    sys.executable,
                    "scripts/02_preprocess/deglitch_mps_ucla.py",
                    "--out-dir",
                    str(deglitch_dir),
                ],
            },
            {
                "label": "rotate",
                "args": [
                    sys.executable,
                    "scripts/02_preprocess/rotate_uvw_to_zne.py",
                    "--in-dir",
                    str(deglitch_dir),
                ],
            },
        ]

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(stage_args, **_kwargs):
        calls.append(stage_args[1])
        _write_deglitch_summary(deglitch_dir / "deglitch_run_summary.json", {"succeeded_mps_only": 1})
        return Completed()

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    manifest_path = run_paper0_mod.run_paper0(args)

    assert calls == [
        "scripts/02_preprocess/deglitch_mps_ucla.py",
        "scripts/02_preprocess/rotate_uvw_to_zne.py",
    ]
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    determined = payload["determined_terminal_validation"]
    assert determined["expected_terminal_status"] == "failed"
    assert determined["determining_stage"] == "deglitch"
    assert payload["status"] == "completed_with_determined_validation_failure"
    assert payload["paper_ready"] is False


def test_paper0_run_clears_stale_incremental_validation_fragments(tmp_path, monkeypatch):
    args = run_paper0_mod.parse_args([])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(tmp_path / "validation" / "paper0_run_manifest.json")
    stale_dir = tmp_path / "validation" / "incremental_validation"
    stale_dir.mkdir(parents=True)
    (stale_dir / "type2_distance_stratified.json").write_text(
        json.dumps(
            {
                "check": "type2_distance_stratified",
                "summary_fragment": {
                    "type2_distance_stratified": {
                        "status": "fail",
                        "detail": "stale failure",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_commands(_args):
        return [{"label": "rotate", "args": [sys.executable, "scripts/02_preprocess/rotate_uvw_to_zne.py"]}]

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", lambda stage_args, **_kwargs: calls.append(stage_args) or Completed())

    manifest_path = run_paper0_mod.run_paper0(args)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert calls == [[sys.executable, "scripts/02_preprocess/rotate_uvw_to_zne.py"]]
    assert payload["determined_terminal_validation"] is None
    assert not stale_dir.exists()


def test_paper0_fragment_failure_covers_preprocessing_and_alignment_checks():
    args = run_paper0_mod.parse_args([])

    preprocessing_failure = run_paper0_mod._fragment_failure(
        "preprocessing",
        {
            "summary_fragment": {
                "preprocessing": [
                    {"event_id": "S0001", "check": {"status": "pass", "detail": "ok"}},
                    {"event_id": "S0002", "check": {"status": "fail", "detail": "gallery missing"}},
                ]
            }
        },
        args,
    )
    alignment_failure = run_paper0_mod._fragment_failure(
        "alignment",
        {
            "summary_fragment": {
                "alignment": {
                    "paperfaith_envelope": {
                        "check": {"status": "fail", "detail": "non-finite alignment sheet"},
                    }
                }
            }
        },
        args,
    )

    assert preprocessing_failure == {
        "check": "preprocessing.S0002",
        "status": "failed",
        "detail": "gallery missing",
    }
    assert alignment_failure == {
        "check": "alignment.paperfaith_envelope",
        "status": "failed",
        "detail": "non-finite alignment sheet",
    }


def test_paper0_continue_flag_preserves_determined_status_after_terminal_validation_failure(tmp_path, monkeypatch):
    deglitch_dir = tmp_path / "deglitched"
    validation_dir = tmp_path / "validation"
    args = run_paper0_mod.parse_args(["--continue-despite-determined-validation"])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(validation_dir / "paper0_run_manifest.json")

    def fake_commands(_args):
        return [
            {
                "label": "deglitch",
                "args": [
                    sys.executable,
                    "scripts/02_preprocess/deglitch_mps_ucla.py",
                    "--out-dir",
                    str(deglitch_dir),
                ],
            },
            {
                "label": "validation",
                "args": [
                    sys.executable,
                    "scripts/07_validation/generate_validation_report.py",
                    "--aggregate-only",
                    "--strict-gates",
                    "--out-dir",
                    str(validation_dir),
                ],
            },
        ]

    class Completed:
        stdout = ""
        stderr = ""

        def __init__(self, returncode):
            self.returncode = returncode

    def fake_run(stage_args, **_kwargs):
        if any("deglitch_mps_ucla.py" in part for part in stage_args):
            _write_deglitch_summary(deglitch_dir / "deglitch_run_summary.json", {"succeeded_mps_only": 1})
            return Completed(0)
        validation_dir.mkdir(parents=True, exist_ok=True)
        (validation_dir / "validation_summary.json").write_text(
            json.dumps(
                {
                    "validation_status": {"status": "failed", "failures": ["deglitch"]},
                    "current_provenance_enforcement": {"requested": True, "enforced": True, "status": "current"},
                }
            ),
            encoding="utf-8",
        )
        return Completed(2)

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Paper0 validation failed"):
        run_paper0_mod.run_paper0(args)

    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    assert payload["status"] == "failed_validation_determined_continued"
    assert payload["validation_status"] == "failed"
    assert payload["determined_terminal_validation"]["expected_terminal_status"] == "failed"


def test_paper0_from_scratch_runs_stale_download_stage_and_rechecks_manifest(tmp_path, monkeypatch):
    event_ids = ["S0001"]
    _write_event_table(tmp_path / "manifest" / "event_table.csv", event_ids)
    items = _valid_download_fixture(tmp_path, event_ids)
    waveform = tmp_path / "data" / "raw" / "S0001.mseed"
    waveform.write_bytes(b"stale-waveform")
    _write_data_manifest(tmp_path / "manifest" / "data_manifest.json", items)
    args = _paper0_args(tmp_path)
    args.dry_run = False
    calls = []

    class Completed:
        returncode = 0
        stdout = "downloaded"
        stderr = ""

    def fake_run(stage_args, **kwargs):
        calls.append(stage_args)
        waveform.write_bytes(b"S0001-waveform")
        refreshed = _valid_download_fixture(tmp_path, event_ids)
        _write_data_manifest(tmp_path / "manifest" / "data_manifest.json", refreshed)
        return Completed()

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", lambda _args: [])
    monkeypatch.setattr(run_paper0_mod, "_clear_derived_outputs", lambda: None)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    manifest_path = run_paper0_mod.run_paper0(args)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(calls) == 1
    assert calls[0][1] == "scripts/01_download/download_waveforms.py"
    assert payload["stages"][0]["status"] == "succeeded"
    assert payload["stages"][0]["action"] == "ran"
    assert payload["stages"][0]["precheck"]["stale_paths"] == ["data/raw/S0001.mseed"]


def test_paper0_deglitch_status_vocabulary_matches_readme_contract():
    text = repo_path("README.md").read_text(encoding="utf-8")

    assert set(run_paper0_mod.DEFAULT_ALLOWED_DEGLITCH_STATUSES) == {"mps_ucla_verified"}
    assert run_paper0_mod.parse_args([]).allow_deglitch_status == ["mps_ucla_verified"]
    for status in run_paper0_mod.DEGLITCH_STATUS_VOCABULARY:
        assert re.search(rf"`{re.escape(status)}`", text)
    assert "partial_mps_only" not in text
    assert "`succeeded`" not in text
    with pytest.raises(ValueError, match="Unknown deglitch status"):
        run_paper0_mod.validate_deglitch_statuses(["partial_mps_only"])


def test_paper0_manifest_records_provenance_enforcement_from_validation_summary(tmp_path, monkeypatch):
    args = run_paper0_mod.parse_args(["--require-current-provenance"])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(tmp_path / "validation" / "paper0_run_manifest.json")

    def fake_commands(_args):
        return [
            {
                "label": "validation",
                "args": [
                    sys.executable,
                    "scripts/07_validation/generate_validation_report.py",
                    "--strict-gates",
                    "--require-current-provenance",
                    "--out-dir",
                    str(tmp_path / "validation"),
                ],
            }
        ]

    class Completed:
        returncode = 0
        stdout = "validation summary"
        stderr = ""

    def fake_run(_stage_args, **_kwargs):
        (tmp_path / "validation").mkdir(parents=True, exist_ok=True)
        (tmp_path / "validation" / "validation_summary.json").write_text(
            json.dumps(
                {
                    "validation_status": {"status": "passed", "failures": []},
                    "require_current_provenance": False,
                    "current_provenance_enforcement": {"requested": True, "enforced": False},
                }
            ),
            encoding="utf-8",
        )
        return Completed()

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="current provenance"):
        run_paper0_mod.run_paper0(args)

    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    assert payload["require_current_provenance"] is True
    assert payload["current_provenance_enforcement"] == {"requested": True, "enforced": False}
    assert payload["execution_status"] == "succeeded"
    assert payload["validation_status"] == "failed"
    assert payload["paper_ready"] is False


def test_paper0_manifest_splits_execution_and_validation_status(tmp_path, monkeypatch):
    args = run_paper0_mod.parse_args(["--require-current-provenance"])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(tmp_path / "validation" / "paper0_run_manifest.json")

    def fake_commands(_args):
        return [
            {
                "label": "validation",
                "args": [
                    sys.executable,
                    "scripts/07_validation/generate_validation_report.py",
                    "--strict-gates",
                    "--require-current-provenance",
                    "--out-dir",
                    str(tmp_path / "validation"),
                ],
            }
        ]

    class Completed:
        returncode = 2
        stdout = "validation failed"
        stderr = ""

    def fake_run(_stage_args, **_kwargs):
        (tmp_path / "validation").mkdir(parents=True, exist_ok=True)
        (tmp_path / "validation" / "validation_summary.json").write_text(
            json.dumps(
                {
                    "validation_status": {"status": "failed", "failures": ["type2_distance_stratified"]},
                    "current_provenance_enforcement": {"requested": True, "enforced": True},
                }
            ),
            encoding="utf-8",
        )
        return Completed()

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Paper0 validation failed"):
        run_paper0_mod.run_paper0(args)

    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    assert payload["execution_status"] == "succeeded"
    assert payload["validation_status"] == "failed"
    assert payload["status"] == "failed_validation"
    assert payload["paper_ready"] is False


def test_paper0_validation_execution_failure_does_not_trust_stale_passed_summary(tmp_path, monkeypatch):
    args = run_paper0_mod.parse_args(["--require-current-provenance"])
    args.from_scratch = False
    args.dry_run = False
    args.manifest = str(tmp_path / "validation" / "paper0_run_manifest.json")
    out_dir = tmp_path / "validation"
    out_dir.mkdir(parents=True)
    stale_summary = out_dir / "validation_summary.json"
    stale_summary.write_text(
        json.dumps(
            {
                "validation_status": {"status": "passed", "failures": []},
                "current_provenance_enforcement": {"requested": True, "enforced": True, "status": "current"},
            }
        ),
        encoding="utf-8",
    )

    def fake_commands(_args):
        return [
            {
                "label": "validation",
                "args": [
                    sys.executable,
                    "scripts/07_validation/generate_validation_report.py",
                    "--strict-gates",
                    "--require-current-provenance",
                    "--out-dir",
                    str(out_dir),
                ],
            }
        ]

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "crashed before summary"

    monkeypatch.setattr(run_paper0_mod, "build_stage_commands", fake_commands)
    monkeypatch.setattr(run_paper0_mod, "_git_commit", lambda: "test-commit")
    monkeypatch.setattr(run_paper0_mod, "_git_status_sha", lambda: "test-status")
    monkeypatch.setattr(run_paper0_mod.subprocess, "run", lambda *_args, **_kwargs: Completed())

    with pytest.raises(RuntimeError, match="Paper0 stage failed: validation"):
        run_paper0_mod.run_paper0(args)

    payload = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    assert not stale_summary.exists()
    assert payload["execution_status"] == "failed"
    assert payload["validation_status"] == "failed"
    assert payload["status"] == "failed_execution"
    assert payload["paper_ready"] is False


def test_paper0_direct_script_invocation_supports_dry_run(tmp_path):
    _write_event_table(tmp_path / "manifest" / "event_table.csv", ["S0001"])
    _write_data_manifest(tmp_path / "manifest" / "data_manifest.json", [])
    run_manifest = tmp_path / "paper0_run_manifest.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_paper0.py",
            "--from-scratch",
            "--dry-run",
            "--manifest",
            str(run_manifest),
            "--data-manifest",
            str(tmp_path / "manifest" / "data_manifest.json"),
            "--event-table",
            str(tmp_path / "manifest" / "event_table.csv"),
            "--raw-dir",
            str(tmp_path / "data" / "raw"),
            "--ak-out-dir",
            str(tmp_path / "data" / "models" / "ak_subset"),
            "--khan-out-dir",
            str(tmp_path / "data" / "models" / "khan2023"),
            "--mqs-catalog",
            str(tmp_path / "data" / "raw" / "mqs_v14_catalog.xml"),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(run_manifest.read_text(encoding="utf-8"))
    assert payload["stages"][0]["label"] == "download_waveforms"
