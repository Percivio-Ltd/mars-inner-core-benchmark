from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from obspy import Stream, Trace

from scripts.shared import import_local_module


def _deglitch_module():
    return import_local_module(
        "marsquake_deglitch_ucla_raw_identity_test",
        "scripts/02_preprocess/deglitch_mps_ucla.py",
    )


def _run_paper0_module():
    return import_local_module(
        "marsquake_run_paper0_ucla_raw_identity_test",
        "scripts/run_paper0.py",
    )


def _write_uvw(path: Path) -> None:
    stream = Stream()
    for channel, scale in (("BHU", 1.0), ("BHV", 2.0), ("BHW", 3.0)):
        trace = Trace(data=np.arange(120, dtype=np.float32) * np.float32(scale))
        trace.stats.sampling_rate = 20.0
        trace.stats.network = "XB"
        trace.stats.station = "ELYSE"
        trace.stats.location = "02"
        trace.stats.channel = channel
        trace.stats.mseed = {"encoding": "FLOAT32"}
        stream.append(trace)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream.write(str(path), format="MSEED")


def test_identity_mode_copies_bytes_without_mps_claim(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0235b.mseed"
    out_path = tmp_path / "deglitched" / "S0235b.mseed"
    _write_uvw(raw_path)

    metadata = deglitch.run_deglitch_event(
        event_id="S0235b",
        input_path=raw_path,
        output_path=out_path,
        work_dir=tmp_path / "work",
        seisglitch_command="identity",
    )

    assert out_path.read_bytes() == raw_path.read_bytes()
    assert metadata["methods_requested"] == ["UCLA"]
    assert metadata["mps"] == {"status": "identity_passthrough"}
    assert metadata["commands"] == []
    assert metadata["overall_status"] == "succeeded_mps_only"
    assert metadata["samples_modified"] is False


def test_identity_mode_with_fake_ucla_success_is_ucla_unverified(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0235b.mseed"
    out_path = tmp_path / "deglitched" / "S0235b.mseed"
    _write_uvw(raw_path)

    def fake_runner(command, **_kwargs):
        shutil.copyfile(command[1], command[2])
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0235b",
        input_path=raw_path,
        output_path=out_path,
        work_dir=tmp_path / "work",
        seisglitch_command="identity",
        ucla_command=["fake-ucla", "{input}", "{output}"],
        runner=fake_runner,
    )

    assert metadata["mps"] == {"status": "identity_passthrough"}
    assert metadata["overall_status"] == "ucla_unverified"
    assert metadata["ucla"]["status"] == "external_ucla_command_wrote_file_unverified"


def test_non_identity_command_still_runs_seisglitch_detect_path(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0235b.mseed"
    out_path = tmp_path / "deglitched" / "S0235b.mseed"
    _write_uvw(raw_path)
    calls = []

    def fake_runner(command, **_kwargs):
        calls.append(list(command))
        return deglitch.CommandResult(args=command, returncode=7, stderr="expected detect failure")

    metadata = deglitch.run_deglitch_event(
        event_id="S0235b",
        input_path=raw_path,
        output_path=out_path,
        work_dir=tmp_path / "work",
        seisglitch_command=["fake-seisglitch"],
        runner=fake_runner,
    )

    assert len(calls) == 1
    assert calls[0][0:2] == ["fake-seisglitch", "detect"]
    assert metadata["methods_requested"] == ["MPS", "UCLA"]
    assert metadata["mps"]["status"] == "failed_detect"


def test_orchestrator_forwards_identity_and_subset_table(tmp_path):
    run_paper0 = _run_paper0_module()
    event_table = tmp_path / "event_table_ucla22.csv"
    raw_dir = tmp_path / "raw_ucla22"
    args = run_paper0.parse_args(
        [
            "--event-table",
            str(event_table),
            "--raw-dir",
            str(raw_dir),
            "--seisglitch-command",
            "identity",
            "--ucla-command",
            "fake-ucla {input} {output} {work_dir}",
            "--allow-deglitch-status",
            "ucla_unverified",
        ]
    )

    findings = []
    run_paper0._check_seisglitch_resolution(args, findings)
    assert findings == []

    commands = {stage["label"]: stage["args"] for stage in run_paper0.build_stage_commands(args)}
    assert commands["deglitch"][commands["deglitch"].index("--in-dir") + 1] == str(raw_dir)
    assert commands["deglitch"][commands["deglitch"].index("--seisglitch-command") + 1] == "identity"
    for label, flag in (
        ("align", "--event-table"),
        ("vespagrams", "--event-table"),
        ("bootstrap_type1", "--table"),
        ("bootstrap_type2", "--table"),
        ("bootstrap_type3", "--table"),
        ("validation", "--event-table"),
    ):
        assert commands[label][commands[label].index(flag) + 1] == str(event_table)
