from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from obspy import Stream, Trace, UTCDateTime, read

from scripts.shared import (
    ABLATION_BANDPASS_REVISION,
    PAPERSTYLE_ALGORITHM_REVISION,
    PAPERSTYLE_ALIGNMENT_REVISION,
    PAPERSTYLE_FDPA_METHOD,
    PAPERSTYLE_FDPA_TRANSFORM_FAMILY,
    PAPERSTYLE_FILTERBANK_METHOD,
    PAPERSTYLE_POLARIZATION_METHOD,
    PAPERSTYLE_NORMALIZATION_REVISION,
    ROTATION_ZNE_REVISION,
    import_local_module,
    repo_path,
    sha256_file,
)

bandpass_file = import_local_module(
    "marsquake_bandpass_filter_test",
    "scripts/02_preprocess/bandpass_filter.py",
).bandpass_file
glitch_mod = import_local_module(
    "marsquake_glitch_flagging_test",
    "scripts/02_preprocess/glitch_flagging.py",
)
normalize_and_save = import_local_module(
    "marsquake_normalize_and_envelope_regression_test",
    "scripts/02_preprocess/normalize_and_envelope.py",
).normalize_and_save
polarization_filter_file = import_local_module(
    "marsquake_polarization_filter_test",
    "scripts/02_preprocess/polarization_filter.py",
).polarization_filter_file
rotate_mod = import_local_module(
    "marsquake_rotate_uvw_to_zne_test",
    "scripts/02_preprocess/rotate_uvw_to_zne.py",
)
validation_mod = import_local_module(
    "marsquake_validation_report_contract_test",
    "scripts/07_validation/generate_validation_report.py",
)


def _deglitch_module():
    source = repo_path("scripts/02_preprocess/deglitch_mps_ucla.py")
    assert source.exists(), "Paper0 needs an executable MPS+UCLA deglitch stage before rotation"
    return import_local_module(
        "marsquake_deglitch_mps_ucla_test",
        "scripts/02_preprocess/deglitch_mps_ucla.py",
    )


def _write_trace(path: Path, data, sampling_rate: float = 20.0, channel: str = "BHZ"):
    tr = Trace(data=np.asarray(data, dtype=np.float32))
    tr.stats.sampling_rate = sampling_rate
    tr.stats.network = "XB"
    tr.stats.station = "ELYSE"
    tr.stats.channel = channel
    tr.stats.mseed = {"encoding": "FLOAT32"}
    st = Stream([tr])
    path.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(path), format="MSEED")


def _write_zne(path: Path, z, n, e, sampling_rate: float = 20.0):
    st = Stream()
    for channel, data in [("BHZ", z), ("BHN", n), ("BHE", e)]:
        tr = Trace(data=np.asarray(data, dtype=np.float32))
        tr.stats.sampling_rate = sampling_rate
        tr.stats.network = "XB"
        tr.stats.station = "ELYSE"
        tr.stats.channel = channel
        tr.stats.mseed = {"encoding": "FLOAT32"}
        st.append(tr)
    path.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(path), format="MSEED")


def _write_uvw(path: Path, u, v, w, sampling_rate: float = 20.0, starttime_offsets_s: tuple[float, float, float] | None = None):
    st = Stream()
    start = UTCDateTime("2020-01-01T00:00:00Z")
    offsets = starttime_offsets_s or (0.0, 0.0, 0.0)
    for (channel, data), offset_s in zip([("BHU", u), ("BHV", v), ("BHW", w)], offsets):
        tr = Trace(data=np.asarray(data, dtype=np.float32))
        tr.stats.sampling_rate = sampling_rate
        if starttime_offsets_s is not None:
            tr.stats.starttime = start + offset_s
        tr.stats.network = "XB"
        tr.stats.station = "ELYSE"
        tr.stats.location = "02"
        tr.stats.channel = channel
        tr.stats.mseed = {"encoding": "FLOAT32"}
        st.append(tr)
    path.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(path), format="MSEED")


def test_deglitch_stage_blocks_without_mps_instead_of_copying_raw(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0004.mseed"
    out_path = tmp_path / "deglitched" / "S0004.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)

    metadata = deglitch.run_deglitch_event(
        event_id="S0004",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=None,
        ucla_command=None,
    )

    assert metadata["overall_status"] == "blocked"
    assert metadata["methods_requested"] == ["MPS", "UCLA"]
    assert metadata["mps"]["status"] == "blocked_missing_seisglitch"
    assert metadata["ucla"]["status"] == "blocked_not_attempted"
    assert metadata["samples_modified"] is False
    assert metadata["metadata_path"] == str(out_path.with_suffix(".deglitch.json"))
    assert out_path.exists() is False
    saved = deglitch.read_metadata(out_path.with_suffix(".deglitch.json"))
    assert saved["overall_status"] == "blocked"


def test_deglitch_stage_removes_stale_output_before_blocked_rerun(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0004.mseed"
    out_path = tmp_path / "deglitched" / "S0004.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    _write_uvw(out_path, np.ones(80) * 9.0, np.ones(80) * 9.0, np.ones(80) * 9.0)

    metadata = deglitch.run_deglitch_event(
        event_id="S0004",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=None,
        ucla_command=None,
    )

    assert metadata["overall_status"] == "blocked"
    assert out_path.exists() is False


def test_deglitch_stage_rejects_same_input_and_output_path(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0004.mseed"
    _write_uvw(raw_path, np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)

    metadata = deglitch.run_deglitch_event(
        event_id="S0004",
        input_path=raw_path,
        output_path=raw_path,
        work_dir=tmp_path / "work",
        seisglitch_command=["seisglitch"],
    )

    assert metadata["overall_status"] == "failed"
    assert metadata["mps"]["status"] == "blocked_invalid_output_path"
    assert raw_path.exists()


def test_deglitch_config_targets_raw_uvw_and_sequential_mps_then_ucla(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0005.mseed"
    _write_uvw(raw_path, np.arange(100), np.arange(100) + 1.0, np.arange(100) + 2.0)

    config = deglitch.build_seisglitch_config(
        waveform_path=raw_path,
        inventory_file="IRIS",
        work_dir=tmp_path / "work",
        output_path=tmp_path / "deglitched" / "S0005.mseed",
    )

    assert config["mode_order"] == ["detect", "remove"]
    assert config["waveform_files"] == [str(raw_path)]
    assert config["inventory_file"] == "IRIS"
    assert config["detect"]["detector"]["components"] == ["U", "V", "W"]
    assert config["remove"]["remover"]["preserve_raw_input"] is False
    assert config["ucla"]["status_if_unconfigured"] == "blocked_missing_ucla_runner"
    assert config["ucla"]["runner_output_expected"].endswith("work/S0005_ucla.mseed")
    assert config["ucla"]["final_output_path"].endswith("deglitched/S0005.mseed")


def test_deglitch_stage_records_success_only_when_external_outputs_exist(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0006.mseed"
    out_path = tmp_path / "deglitched" / "S0006.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)

    def fake_runner(command, **kwargs):
        if "detect" in command:
            detector = work_dir / "S0006" / "glitches_S0006.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.5)
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0006",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        ucla_command=None,
        runner=fake_runner,
    )

    assert out_path.exists()
    assert metadata["mps"]["status"] == "succeeded"
    assert metadata["ucla"]["status"] == "blocked_missing_ucla_runner"
    assert metadata["overall_status"] == "succeeded_mps_only"
    assert metadata["samples_modified"] is True


def test_deglitch_stage_promotes_inferred_mps_workdir_output(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0010.mseed"
    out_path = tmp_path / "deglitched" / "S0010.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)

    def fake_runner(command, **kwargs):
        if "detect" in command:
            detector = work_dir / "S0010" / "glitches_S0010.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            mps_output = work_dir / "S0010" / "S0010_deglitched.mseed"
            deglitch.copy_mps_output_for_test(raw_path, mps_output, scale=0.5)
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0010",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        runner=fake_runner,
    )

    assert metadata["mps"]["status"] == "succeeded"
    assert out_path.exists()
    assert np.allclose(read(str(out_path))[0].data, 0.5)


def test_deglitch_stage_does_not_mark_ucla_succeeded_without_output(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0006.mseed"
    out_path = tmp_path / "deglitched" / "S0006.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)

    def fake_runner(command, **kwargs):
        if "detect" in command:
            detector = work_dir / "S0006" / "glitches_S0006.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.5)
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0006",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        ucla_command=["octave", "--eval", "run_ucla('{input}', '{output}')"],
        runner=fake_runner,
    )

    assert metadata["mps"]["status"] == "succeeded"
    assert metadata["ucla"]["status"] == "failed_missing_ucla_output"
    assert metadata["overall_status"] == "succeeded_mps_only"
    assert out_path.exists()
    assert np.allclose(read(str(out_path))[0].data, 0.5)


def test_deglitch_stage_marks_write_only_ucla_output_unverified(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0009.mseed"
    out_path = tmp_path / "deglitched" / "S0009.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)
    commands = []

    def fake_runner(command, **kwargs):
        commands.append(list(command))
        if "detect" in command:
            detector = work_dir / "S0009" / "glitches_S0009.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.5)
        if "octave" in command:
            ucla_output = work_dir / "S0009" / "S0009_ucla.mseed"
            deglitch.copy_mps_output_for_test(raw_path, ucla_output, scale=0.25)
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0009",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        ucla_command=["octave", "--eval", "run_ucla('{input}', '{output}', '{work_dir}')"],
        runner=fake_runner,
    )

    assert metadata["overall_status"] == "ucla_unverified"
    assert metadata["ucla"]["status"] == "external_ucla_command_wrote_file_unverified"
    assert metadata["ucla"]["contract_status"] == "output_file_verified_not_algorithm_equivalence"
    assert metadata["ucla"]["ucla_input_sha256"] == sha256_file(work_dir / "S0009" / "S0009_mps_before_ucla.mseed")
    assert metadata["ucla"]["ucla_output_sha256"] == metadata["ucla"]["final_output_sha256"]
    assert metadata["ucla"]["samples_modified_ucla"] is True
    assert np.allclose(read(str(out_path))[0].data, 0.25)
    octave_args = next(command for command in commands if "octave" in command)
    assert "{input}" not in octave_args[-1]
    assert "{output}" not in octave_args[-1]
    assert "{work_dir}" not in octave_args[-1]


def test_deglitch_stage_bare_verified_sidecar_is_attested_not_verified(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0022.mseed"
    out_path = tmp_path / "deglitched" / "S0022.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)

    def fake_runner(command, **kwargs):
        if "detect" in command:
            detector = work_dir / "S0022" / "glitches_S0022.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.5)
        if "octave" in command:
            ucla_output = work_dir / "S0022" / "S0022_ucla.mseed"
            deglitch.copy_mps_output_for_test(raw_path, ucla_output, scale=0.25)
            ucla_output.with_suffix(ucla_output.suffix + ".ucla.json").write_text(
                json.dumps({"verification_status": "mps_ucla_verified"})
            )
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0022",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        ucla_command=["octave", "--eval", "run_ucla('{input}', '{output}')"],
        runner=fake_runner,
    )

    assert metadata["overall_status"] == "sidecar_attested_not_independently_verified"
    assert metadata["ucla"]["status"] == "sidecar_attested_not_independently_verified"
    assert metadata["ucla"]["contract_status"] == "sidecar_attested_not_independently_verified"
    assert set(metadata["ucla"]["ucla_sidecar_missing_verified_evidence"]) == {
        "algorithm",
        "parameters_sha256",
        "expected_output_verification",
    }


@pytest.mark.parametrize(
    "evidence_key,evidence_value",
    [
        ("verification_evidence_uri", "https://example.invalid/ucla-verification/S0024"),
        ("verification_evidence_path", "missing-verification-record.json"),
    ],
)
def test_deglitch_stage_evidence_pointer_does_not_verify_ucla_output(tmp_path, evidence_key, evidence_value):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0024.mseed"
    out_path = tmp_path / "deglitched" / "S0024.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)

    def fake_runner(command, **kwargs):
        if "detect" in command:
            detector = work_dir / "S0024" / "glitches_S0024.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.5)
        if "octave" in command:
            ucla_output = work_dir / "S0024" / "S0024_ucla.mseed"
            deglitch.copy_mps_output_for_test(raw_path, ucla_output, scale=0.25)
            ucla_output.with_suffix(ucla_output.suffix + ".ucla.json").write_text(
                json.dumps(
                    {
                        "verification_status": "mps_ucla_verified",
                        "algorithm": "public-ucla-fixture",
                        "parameters_sha256": "fixture-parameters",
                        evidence_key: evidence_value,
                    }
                )
            )
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0024",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        ucla_command=["octave", "--eval", "run_ucla('{input}', '{output}')"],
        runner=fake_runner,
    )

    assert metadata["overall_status"] == "sidecar_attested_not_independently_verified"
    assert metadata["ucla"]["status"] == "sidecar_attested_not_independently_verified"
    assert metadata["ucla"]["ucla_sidecar_verification_evidence_key"] == evidence_key
    assert "expected_output_verification" in metadata["ucla"]["ucla_sidecar_missing_verified_evidence"]


def test_deglitch_stage_promotes_mps_ucla_verified_only_with_sidecar(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0019.mseed"
    out_path = tmp_path / "deglitched" / "S0019.mseed"
    work_dir = tmp_path / "work"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)

    def fake_runner(command, **kwargs):
        if "detect" in command:
            detector = work_dir / "S0019" / "glitches_S0019.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.5)
        if "octave" in command:
            ucla_output = work_dir / "S0019" / "S0019_ucla.mseed"
            deglitch.copy_mps_output_for_test(raw_path, ucla_output, scale=0.25)
            ucla_output.with_suffix(ucla_output.suffix + ".ucla.json").write_text(
                json.dumps(
                    {
                        "verification_status": "mps_ucla_verified",
                        "algorithm": "public-ucla-fixture",
                        "parameters_sha256": "fixture-parameters",
                        "expected_output_sha256": deglitch._sha256_file(ucla_output),
                    }
                )
            )
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0019",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["seisglitch"],
        ucla_command=["octave", "--eval", "run_ucla('{input}', '{output}')"],
        runner=fake_runner,
    )

    assert metadata["overall_status"] == "mps_ucla_verified"
    assert metadata["ucla"]["status"] == "mps_ucla_verified"
    assert metadata["ucla"]["ucla_sidecar_sha256"] == sha256_file(work_dir / "S0019" / "S0019_ucla.mseed.ucla.json")


def test_deglitch_stage_fails_when_mps_detect_writes_no_detector_file(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0007.mseed"
    out_path = tmp_path / "deglitched" / "S0007.mseed"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)
    calls = []

    def fake_runner(command, **kwargs):
        calls.append(list(command))
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0007",
        input_path=raw_path,
        output_path=out_path,
        work_dir=tmp_path / "work",
        seisglitch_command=["seisglitch"],
        runner=fake_runner,
    )

    assert metadata["mps"]["status"] == "failed_missing_detector_file"
    assert metadata["overall_status"] == "failed"
    assert out_path.exists() is False
    assert calls == [["seisglitch", "detect", metadata["mps"]["config_path"]]]


def test_deglitch_stage_can_run_seisglitch_from_public_checkout_pythonpath(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0008.mseed"
    out_path = tmp_path / "deglitched" / "S0008.mseed"
    work_dir = tmp_path / "work"
    checkout_path = tmp_path / "seisglitch-checkout"
    _write_uvw(raw_path, np.ones(120), np.ones(120) * 2.0, np.ones(120) * 3.0)
    env_seen = []

    def fake_runner(command, **kwargs):
        env_seen.append(kwargs["env"]["PYTHONPATH"])
        if "detect" in command:
            detector = work_dir / "S0008" / "glitches_S0008.txt"
            detector.write_text("000001  2020-01-01T00:00:00  2020-01-01T00:00:25  U\n")
        if "remove" in command:
            deglitch.copy_mps_output_for_test(raw_path, out_path, scale=0.25)
        return deglitch.CommandResult(args=command, returncode=0, stdout="ok", stderr="")

    metadata = deglitch.run_deglitch_event(
        event_id="S0008",
        input_path=raw_path,
        output_path=out_path,
        work_dir=work_dir,
        seisglitch_command=["python", str(checkout_path / "Scripts" / "seisglitch")],
        seisglitch_pythonpath=checkout_path,
        runner=fake_runner,
    )

    assert metadata["mps"]["status"] == "succeeded"
    assert env_seen and all(str(checkout_path) in value for value in env_seen)


def test_deglitch_cli_exposes_public_checkout_pythonpath_option():
    deglitch = _deglitch_module()

    parser = deglitch.build_arg_parser()
    args = parser.parse_args(["--seisglitch-pythonpath", "/tmp/seisglitch"])

    assert args.seisglitch_pythonpath == "/tmp/seisglitch"


def test_validation_report_cli_exposes_current_provenance_requirement():
    parser = validation_mod.parse_args

    args = parser(["--require-current-provenance"])

    assert args.require_current_provenance is True


def test_validation_report_benchmark_combo_uses_registered_variant_a():
    assert validation_mod.BENCHMARK_COMBO["mode"] == "paperfaith"
    assert validation_mod.BENCHMARK_COMBO["input_type"] == "envelope"
    assert validation_mod.BENCHMARK_COMBO["variant"] == "A"
    assert validation_mod.REGISTERED_PRIMARY_LANE_BY_PHASE == {"PKiKP": "A", "PKKP": "A"}


def test_validation_model_check_fails_closed_on_malformed_taup_npz(tmp_path):
    generated_model = tmp_path / "generated.nd"
    np.savez(generated_model.with_suffix(".npz"), not_a_taup_model=np.asarray([1.0]))

    result = validation_mod.check_model_taup_archive(generated_model)
    validation_status = validation_mod.evaluate_validation_status(
        {"model": {"check": result["check"]}}
    )

    assert result["check"]["status"] == "fail"
    assert str(generated_model.with_suffix(".npz")) in result["check"]["detail"]
    assert any(failure.startswith("model:") for failure in validation_status["failures"])


def test_validation_model_check_accepts_real_registered_taup_model():
    generated_model = repo_path(
        "data/models/paper0_ref_1800.00-5.00-5.80-600.00-0.300.nd"
    )

    result = validation_mod.check_model_taup_archive(generated_model)

    assert result["check"]["status"] == "pass"
    assert result["arrival_times_s"]["P"] == pytest.approx(224.13121127761386)
    assert result["arrival_times_s"]["PKiKP"] == pytest.approx(808.1356988289882)
    assert result["arrival_times_s"]["P"] < result["arrival_times_s"]["PKiKP"]


def test_validation_peak_taxonomy_keeps_registered_named_endpoints(monkeypatch, tmp_path):
    def fake_detect(_path, **_kwargs):
        return (
            [
                ("PKiKP", "global", 663.8, -3.6363636363636367, 0.9326603162534909),
                ("PKiKP", "published_target", 601.95, -6.666666666666666, 0.7736156900239739),
                ("PKKP", "paper_target", 1341.0, -6.96969696969697, 0.21425338569020153),
            ],
            {},
        )

    monkeypatch.setattr(validation_mod.detect_mod, "detect", fake_detect)

    peaks = validation_mod.benchmark_peak_map(tmp_path / "fixture.npz")

    assert set(peaks) >= {"displaced_ridge", "published_PKIKP_box", "PKKP_target"}
    assert peaks["displaced_ridge"]["time_s"] == pytest.approx(663.8)
    assert peaks["displaced_ridge"]["slowness_sdeg"] == pytest.approx(-3.6363636363636367)
    assert peaks["published_PKIKP_box"]["time_s"] == pytest.approx(601.95)
    assert peaks["published_PKIKP_box"]["slowness_sdeg"] == pytest.approx(-6.666666666666666)
    assert peaks["PKKP_target"]["time_s"] == pytest.approx(1341.0)
    assert peaks["PKKP_target"]["slowness_sdeg"] == pytest.approx(-6.96969696969697)
    assert peaks["pkikp_global"]["time_s"] == pytest.approx(peaks["displaced_ridge"]["time_s"])
    assert peaks["pkikp_published_target"]["time_s"] == pytest.approx(peaks["published_PKIKP_box"]["time_s"])
    assert peaks["pkkp_paper_target"]["time_s"] == pytest.approx(peaks["PKKP_target"]["time_s"])


def test_validation_report_deglitch_gate_refuses_attested_not_verified_status(tmp_path):
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    summary_path = processed_dir / "deglitch_run_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "run_status": "complete",
                "status_counts": {"sidecar_attested_not_independently_verified": 1},
                "events": [
                    {
                        "event_id": "S0025",
                        "overall_status": "sidecar_attested_not_independently_verified",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = validation_mod.check_deglitch_summary(processed_dir)

    assert result["status"] == "fail"
    assert result["verified_only_gate"] == "mps_ucla_verified"
    assert result["unverified_statuses"] == ["sidecar_attested_not_independently_verified"]


def test_validation_bootstrap_warning_uses_robust_estimators_when_fit_degenerate(tmp_path):
    bootstrap_dir = tmp_path / "bootstrap"
    bootstrap_dir.mkdir()
    slowness = np.linspace(-10.0, 0.0, 100)
    time = np.linspace(550.0, 700.0, 3001)
    occ = np.zeros((100, 3001), dtype=np.float64)
    occ[62, 2280] = 1.0
    for phase in ("pkikp", "pkkp"):
        np.savez(
            bootstrap_dir / f"type1_{phase}_occupancy.npz",
            occupancy=occ,
            slowness_axis=slowness,
            time_axis=time,
            n_bootstrap=np.asarray(200, dtype=np.int32),
            bootstrap_fidelity_level=np.asarray("methods_robustness_200"),
            bootstrap_published_equivalent=np.asarray(False),
            declared_published_n_bootstrap=np.asarray(10000, dtype=np.int32),
        )

    bootstrap_csv = tmp_path / "bootstrap_picks.csv"
    bootstrap_csv.write_text(
        "\n".join(
            [
                "phase,bootstrap_type,mean_time_s,sigma_time_s,mean_slowness_sdeg,sigma_slowness_sdeg,"
                "time_fit_converged,slowness_fit_converged,fit_fallback_used,degenerate_fit,fit_quality_reasons,"
                "time_fit_residual_rms,slowness_fit_residual_rms,time_projection_nonzero_bins,"
                "slowness_projection_nonzero_bins,occupancy_argmax_time_s,occupancy_argmax_slowness_sdeg,"
                "occupancy_argmax_value,weighted_median_time_s,weighted_median_slowness_sdeg,"
                "occupied_cell_count,high_occupancy_component_count,n_bootstrap,threshold_pct",
                "pkikp,type1,630.3412219882591,43.00446876874065,-0.00358113047202732,0.4135851428833738,"
                "True,False,False,True,slowness:residual_rms_fraction|tri_estimator_inconsistency,"
                "0.42974527984151156,18.85574722290039,2609,100,664.0,-3.7373738288879395,"
                "0.4749999940395355,638.6,-3.535353422164917,85986,6,200,85",
                "pkkp,type1,1341.0,1.0,-7.0,0.5,True,True,False,False,,0.1,0.1,3,3,1341.0,-7.0,1.0,1341.0,-7.0,9,1,200,85",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = validation_mod.plot_bootstrap_diagnostics(
        bootstrap_dir,
        bootstrap_csv,
        tmp_path / "validation",
        {
            "peaks": {
                "pkikp_global": {"time_s": 663.8, "slowness_sdeg": -3.64},
                "pkkp_paper_target": {"time_s": 1341.0, "slowness_sdeg": -7.0},
            }
        },
    )

    detail = result["checks"]["pkikp"]["detail"]
    assert "robust estimators" in detail
    assert "occupancy argmax Δt=60.00s Δs=2.76s/deg" in detail
    assert "weighted median Δt=34.60s Δs=2.96s/deg" in detail
    assert "degenerate_fit" in detail
    assert "centroid" not in detail
    assert "Δs=6.50" not in detail


def test_validation_bootstrap_fidelity_is_disclosed_from_payloads(tmp_path):
    bootstrap_dir = tmp_path / "bootstrap"
    bootstrap_dir.mkdir()
    slowness = np.linspace(-10.0, 0.0, 100)
    time = np.linspace(550.0, 700.0, 3001)
    occ = np.zeros((100, 3001), dtype=np.float64)
    occ[62, 2280] = 1.0
    for phase in ("pkikp", "pkkp"):
        np.savez(
            bootstrap_dir / f"type1_{phase}_occupancy.npz",
            occupancy=occ,
            slowness_axis=slowness,
            time_axis=time,
            n_bootstrap=np.asarray(200, dtype=np.int32),
            bootstrap_fidelity_level=np.asarray("methods_robustness_200"),
            bootstrap_published_equivalent=np.asarray(False),
            declared_published_n_bootstrap=np.asarray(10000, dtype=np.int32),
        )

    bootstrap_csv = tmp_path / "bootstrap_picks.csv"
    bootstrap_csv.write_text(
        "\n".join(
            [
                "phase,bootstrap_type,mean_time_s,sigma_time_s,mean_slowness_sdeg,sigma_slowness_sdeg,"
                "time_fit_converged,slowness_fit_converged,fit_fallback_used,degenerate_fit,fit_quality_reasons,"
                "time_fit_residual_rms,slowness_fit_residual_rms,time_projection_nonzero_bins,"
                "slowness_projection_nonzero_bins,occupancy_argmax_time_s,occupancy_argmax_slowness_sdeg,"
                "occupancy_argmax_value,weighted_median_time_s,weighted_median_slowness_sdeg,"
                "occupied_cell_count,high_occupancy_component_count,n_bootstrap,threshold_pct",
                "pkikp,type1,604.0,1.0,-6.5,0.5,True,True,False,False,,0.1,0.1,3,3,604.0,-6.5,1.0,604.0,-6.5,9,1,200,85",
                "pkkp,type1,1341.0,1.0,-7.0,0.5,True,True,False,False,,0.1,0.1,3,3,1341.0,-7.0,1.0,1341.0,-7.0,9,1,200,85",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = validation_mod.plot_bootstrap_diagnostics(
        bootstrap_dir,
        bootstrap_csv,
        tmp_path / "validation",
        {
            "peaks": {
                "displaced_ridge": {"time_s": 663.8, "slowness_sdeg": -3.64},
                "PKKP_target": {"time_s": 1341.0, "slowness_sdeg": -7.0},
            }
        },
    )

    assert result["fidelity"]["level"] == "methods_robustness_200"
    assert result["fidelity"]["n_bootstrap"] == 200
    assert result["fidelity"]["published_equivalent"] is False
    assert result["fidelity"]["published_n_bootstrap"] == 10000


def test_validation_gates_fail_when_type2_distance_artifacts_missing(tmp_path):
    result = validation_mod.check_type2_distance_artifacts(tmp_path)

    assert result["status"] == "fail"
    assert "type2_pkikp_distance_stratified_occupancy.npz" in result["detail"]
    assert "type2_pkkp_distance_stratified_occupancy.npz" in result["detail"]


def test_validation_bootstrap_missing_type1_artifact_is_structured_failure(tmp_path):
    result = validation_mod.plot_bootstrap_diagnostics(
        tmp_path / "bootstrap",
        tmp_path / "missing_bootstrap_picks.csv",
        tmp_path / "validation",
        {"peaks": {}},
    )

    assert result["fidelity"]["status"] == "fail"
    assert result["checks"]["pkikp"]["status"] == "fail"
    assert "missing type1_pkikp_occupancy.npz" in result["checks"]["pkikp"]["detail"]


def test_validation_full_mode_uses_fresh_benchmark_fragment(tmp_path, monkeypatch):
    benchmark_calls = []
    bootstrap_inputs = []

    def fake_benchmark(_path, out_dir, *, validation_mode, require_current_provenance):
        marker = out_dir.name
        benchmark_calls.append(marker)
        return {
            "marker": marker,
            "check": {"status": "pass", "detail": "fresh benchmark"},
            "current_provenance_status": "not_required",
        }

    def fake_bootstrap(_bootstrap_dir, _bootstrap_csv, _out_dir, benchmark_summary):
        bootstrap_inputs.append(benchmark_summary.get("marker"))
        return {
            "fidelity": {
                "status": "pass",
                "detail": "ok",
                "level": "methods_robustness_200",
                "n_bootstrap": 200,
                "published_equivalent": False,
                "published_n_bootstrap": 10000,
            },
            "checks": {
                "pkikp": {"status": "pass", "detail": "ok"},
                "pkkp": {"status": "pass", "detail": "ok"},
            },
        }

    monkeypatch.setattr(validation_mod, "build_event_inventory", lambda *_args: {"summary": {"checks": {"all_events_complete": {"status": "pass", "detail": "ok"}}}})
    monkeypatch.setattr(validation_mod, "load_event_table", lambda _path: [])
    monkeypatch.setattr(validation_mod, "representative_event_ids", lambda _rows: ["S0001"])
    monkeypatch.setattr(validation_mod, "plot_preprocessing_gallery", lambda *_args: [])
    monkeypatch.setattr(validation_mod, "build_alignment_sheet", lambda *_args: {"check": {"status": "pass", "detail": "ok"}})
    monkeypatch.setattr(validation_mod, "plot_benchmark_vespagram", fake_benchmark)
    monkeypatch.setattr(validation_mod, "plot_bootstrap_diagnostics", fake_bootstrap)
    monkeypatch.setattr(validation_mod, "check_type2_distance_artifacts", lambda _path: {"status": "pass", "detail": "ok"})
    monkeypatch.setattr(validation_mod, "check_type3_jitter_artifacts", lambda _path: {"status": "pass", "detail": "ok"})
    monkeypatch.setattr(validation_mod, "check_deglitch_summary", lambda _path: {"status": "pass", "detail": "ok"})
    monkeypatch.setattr(validation_mod, "plot_model_profiles", lambda *_args: {"check": {"status": "pass", "detail": "ok"}})
    monkeypatch.setattr(validation_mod, "write_markdown_summary", lambda _summary, path: path.write_text("# ok\n", encoding="utf-8"))

    stale_out = tmp_path / "stale_validation"
    stale_dir = stale_out / "incremental_validation"
    stale_dir.mkdir(parents=True)
    (stale_dir / "benchmark.json").write_text(
        json.dumps(
            {
                "check": "benchmark",
                "summary_fragment": {
                    "benchmark": {
                        "marker": "stale-fragment",
                        "check": {"status": "fail", "detail": "stale benchmark"},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    for out_dir in (stale_out, tmp_path / "clean_validation"):
        json_path, _md_path = validation_mod.generate_validation_report(
            event_table=tmp_path / "events.csv",
            catalog_path=tmp_path / "catalog.xml",
            raw_dir=tmp_path / "raw",
            processed_dir=tmp_path / "processed",
            vesp_dir=tmp_path / "vespagrams",
            bootstrap_dir=tmp_path / "bootstrap",
            bootstrap_csv=tmp_path / "bootstrap.csv",
            base_model=tmp_path / "base.nd",
            generated_model=tmp_path / "generated.nd",
            out_dir=out_dir,
        )
        summary = json.loads(json_path.read_text(encoding="utf-8"))
        assert summary["benchmark"]["marker"] == out_dir.name

    assert bootstrap_inputs == ["stale_validation", "clean_validation"]
    assert benchmark_calls == ["stale_validation", "clean_validation"]


def test_validation_type3_gate_rejects_wrong_bootstrap_fidelity(tmp_path):
    bootstrap_dir = tmp_path / "bootstrap"
    bootstrap_dir.mkdir()
    for phase in ("pkikp", "pkkp"):
        np.savez(
            bootstrap_dir / f"type3_{phase}_p_pick_jitter.npz",
            occupancy=np.zeros((2, 2), dtype=np.float32),
            occupancy_maps=np.zeros((1, 2, 2), dtype=np.float32),
            jitter_seconds=np.zeros((7, 2), dtype=np.float32),
            event_ids=np.array(["S0001", "S0002"]),
            peak_times=np.zeros(7, dtype=np.float32),
            base_peak_time_s=np.asarray(0.0, dtype=np.float32),
            base_peak_slowness_sdeg=np.asarray(0.0, dtype=np.float32),
            mode=np.asarray("paperfaith"),
            variant=np.asarray("A"),
            input_type=np.asarray("envelope"),
            input_provenance_json=np.asarray("[]"),
            n_bootstrap=np.asarray(7, dtype=np.int32),
            jitter_limit_s=np.asarray(10.0, dtype=np.float32),
            bootstrap_fidelity_level=np.asarray("methods_robustness_200"),
            bootstrap_published_equivalent=np.asarray(False),
            declared_published_n_bootstrap=np.asarray(10000, dtype=np.int32),
        )

    result = validation_mod.check_type3_jitter_artifacts(bootstrap_dir)

    assert result["status"] == "fail"
    assert "requires N=200; got N=7" in result["detail"]


def test_validation_summary_lines_are_lane_qualified_and_attested(tmp_path):
    summary = {
        "inventory": {"summary": {"n_complete": 26, "n_events": 26}},
        "benchmark": {
            "check": {
                "status": "pass",
                "detail": "current-run mode records historical deltas for context but does not gate on stale coordinates",
            },
            "peaks": {
                "displaced_ridge": {"time_s": 663.8, "slowness_sdeg": -3.64},
                "published_PKIKP_box": {"time_s": 601.95, "slowness_sdeg": -6.67},
                "PKKP_target": {"time_s": 1341.05, "slowness_sdeg": -6.97},
            },
        },
        "bootstrap": {"checks": {"pkikp": {"status": "warn", "detail": "ok"}, "pkkp": {"status": "pass", "detail": "ok"}}},
        "bootstrap_fidelity": {
            "level": "methods_robustness_200",
            "n_bootstrap": 200,
            "published_equivalent": False,
            "published_n_bootstrap": 10000,
        },
        "type2_distance_stratified": {"status": "pass", "detail": "ok"},
        "type3_alignment_jitter": {"status": "pass", "detail": "ok"},
        "deglitch": {
            "status": "fail",
            "detail": "strict verified-only gate not met",
            "attestation_level": "succeeded_mps_only",
            "accepted_partial_lane_by_design": True,
            "verified_only_gate": "mps_ucla_verified",
        },
        "model": {"check": {"status": "pass", "detail": "ok"}},
        "preprocessing": [],
    }
    out = tmp_path / "validation_summary.md"

    validation_mod.write_markdown_summary(summary, out)

    text = out.read_text(encoding="utf-8")
    assert "Benchmark check [lane=paperfaith/envelope/A/nth_root/win20; audit=current-run-stale-baseline]" in text
    assert "published-target replication gates remain separate" in text
    assert "Benchmark displaced_ridge [key=displaced_ridge; lane=paperfaith/envelope/A/nth_root/win20; window=550-700s]" in text
    assert "Benchmark published_PKIKP_box [key=published_PKIKP_box; lane=paperfaith/envelope/A/nth_root/win20; window=584-624s]" in text
    assert "Benchmark PKKP_target [key=PKKP_target; lane=paperfaith/envelope/A/nth_root/win20; window=1320-1360s]" in text
    assert "[key=pkikp_global; lane=paperfaith/envelope/A/nth_root/win20; window=550-700s]: t=601.95" not in text
    assert "Bootstrap fidelity: methods_robustness_200 (N=200; published-equivalent=False; published N=10000)" in text
    assert "Type II distance-stratified artifacts: pass" in text
    assert "Delta notation: all validation offsets use explicit Δ versus the named target" in text
    assert "Deglitch summary [attestation=succeeded_mps_only-by-design; strict_gate=mps_ucla_verified]" in text
    assert "- Deglitch summary: fail" not in text


def test_validation_status_fails_on_preprocessing_and_alignment_check_failures():
    summary = {
        "inventory": {"summary": {"checks": {"all_events_complete": {"status": "pass", "detail": "ok"}}}},
        "benchmark": {"check": {"status": "pass", "detail": "ok"}},
        "bootstrap_fidelity": {"status": "pass", "detail": "ok"},
        "type2_distance_stratified": {"status": "pass", "detail": "ok"},
        "type3_alignment_jitter": {"status": "pass", "detail": "ok"},
        "deglitch": {"status": "pass", "detail": "ok"},
        "model": {"check": {"status": "pass", "detail": "ok"}},
        "current_provenance_enforcement": {"requested": False, "enforced": False},
        "preprocessing": [
            {"event_id": "S0001", "check": {"status": "fail", "detail": "gallery missing"}},
        ],
        "alignment": {
            "paperfaith_envelope": {"check": {"status": "fail", "detail": "non-finite alignment sheet"}},
        },
    }

    result = validation_mod.evaluate_validation_status(summary)

    assert result["status"] == "failed"
    assert "preprocessing.S0001: gallery missing" in result["failures"]
    assert "alignment.paperfaith_envelope: non-finite alignment sheet" in result["failures"]


def test_deglitch_all_fails_fast_when_raw_inputs_are_absent(tmp_path):
    deglitch = _deglitch_module()

    with pytest.raises(FileNotFoundError, match="No raw MiniSEED inputs"):
        deglitch.run_all(
            in_dir=tmp_path / "empty-raw",
            out_dir=tmp_path / "deglitched",
            work_dir=tmp_path / "work",
            seisglitch_command=None,
        )


def test_deglitch_all_writes_summary_and_fails_closed_on_blocked_status(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0011.mseed"
    out_dir = tmp_path / "deglitched"
    _write_uvw(raw_path, np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)

    with pytest.raises(RuntimeError, match="Disallowed deglitch statuses"):
        deglitch.run_all(
            in_dir=raw_path.parent,
            out_dir=out_dir,
            work_dir=tmp_path / "work",
            seisglitch_command=None,
        )

    summary = json.loads((out_dir / "deglitch_run_summary.json").read_text())
    assert summary["run_status"] == "complete"
    assert summary["expected_event_ids"] == ["S0011"]
    assert summary["status_counts"] == {"blocked": 1}
    assert summary["events"][0]["event_id"] == "S0011"
    assert summary["events"][0]["overall_status"] == "blocked"


def test_deglitch_all_defaults_to_verified_mps_ucla_status(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0020.mseed"
    out_dir = tmp_path / "deglitched"
    _write_uvw(raw_path, np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)

    with pytest.raises(RuntimeError, match="Disallowed deglitch statuses"):
        deglitch.run_all(
            in_dir=raw_path.parent,
            out_dir=out_dir,
            work_dir=tmp_path / "work",
            seisglitch_command=None,
            allowed_statuses=None,
        )


def test_deglitch_all_rejects_unknown_allowed_status_before_running(tmp_path):
    deglitch = _deglitch_module()
    raw_path = tmp_path / "raw" / "S0025.mseed"
    _write_uvw(raw_path, np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)

    with pytest.raises(ValueError, match="Unknown deglitch status"):
        deglitch.run_all(
            in_dir=raw_path.parent,
            out_dir=tmp_path / "deglitched",
            work_dir=tmp_path / "work",
            seisglitch_command=None,
            allowed_statuses={"partial_mps_only"},
        )

    assert not (tmp_path / "deglitched" / "deglitch_run_summary.json").exists()


def test_rotate_cli_defaults_to_deglitched_input():
    parser = rotate_mod.build_arg_parser()
    args = parser.parse_args([])

    assert Path(args.in_dir).name == "deglitched"


def test_rotate_to_zne_allows_subsample_starttime_spread_and_records_provenance(tmp_path):
    path = tmp_path / "deglitched" / "S0028.mseed"
    out_path = tmp_path / "processed" / "S0028_ZNE.mseed"
    _write_uvw(
        path,
        np.ones(80),
        np.ones(80) * 2.0,
        np.ones(80) * 3.0,
        sampling_rate=20.0,
        starttime_offsets_s=(0.0, 0.001, 0.001),
    )

    rotate_mod.rotate_to_zne(path, out_path)

    metadata = json.loads(out_path.with_suffix(".rotation.json").read_text(encoding="utf-8"))
    assert out_path.exists()
    assert metadata["uvw_starttime_max_spread_s"] == 0.001


def test_rotate_to_zne_records_zero_starttime_spread(tmp_path):
    path = tmp_path / "deglitched" / "S0029.mseed"
    out_path = tmp_path / "processed" / "S0029_ZNE.mseed"
    _write_uvw(
        path,
        np.ones(80),
        np.ones(80) * 2.0,
        np.ones(80) * 3.0,
        sampling_rate=20.0,
        starttime_offsets_s=(0.0, 0.0, 0.0),
    )

    rotate_mod.rotate_to_zne(path, out_path)

    metadata = json.loads(out_path.with_suffix(".rotation.json").read_text(encoding="utf-8"))
    assert out_path.exists()
    assert metadata["uvw_starttime_max_spread_s"] == 0.0


def test_rotate_to_zne_rejects_starttime_spread_at_one_sample(tmp_path):
    path = tmp_path / "deglitched" / "S0030.mseed"
    out_path = tmp_path / "processed" / "S0030_ZNE.mseed"
    _write_uvw(
        path,
        np.ones(80),
        np.ones(80) * 2.0,
        np.ones(80) * 3.0,
        sampling_rate=20.0,
        starttime_offsets_s=(0.0, 0.05, 0.0),
    )

    with pytest.raises(ValueError, match="UVW traces must share"):
        rotate_mod.rotate_to_zne(path, out_path)

    assert not out_path.exists()


@pytest.mark.parametrize("misalignment", ["sampling_rate", "npts"])
def test_rotate_to_zne_rejects_misaligned_uvw_traces(tmp_path, misalignment):
    path = tmp_path / "deglitched" / "S0026.mseed"
    out_path = tmp_path / "processed" / "S0026_ZNE.mseed"
    start = UTCDateTime("2020-01-01T00:00:00Z")
    st = Stream()
    for channel, data in [
        ("BHU", np.ones(80)),
        ("BHV", np.ones(79) if misalignment == "npts" else np.ones(80) * 2.0),
        ("BHW", np.ones(80) * 3.0),
    ]:
        tr = Trace(data=np.asarray(data, dtype=np.float32))
        tr.stats.sampling_rate = 10.0 if channel == "BHV" and misalignment == "sampling_rate" else 20.0
        tr.stats.starttime = start
        tr.stats.network = "XB"
        tr.stats.station = "ELYSE"
        tr.stats.location = "02"
        tr.stats.channel = channel
        tr.stats.mseed = {"encoding": "FLOAT32"}
        st.append(tr)
    path.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(path), format="MSEED")

    with pytest.raises(ValueError, match="UVW traces must share"):
        rotate_mod.rotate_to_zne(path, out_path)

    assert not out_path.exists()


def test_rotate_all_rejects_unknown_allowed_deglitch_status(tmp_path):
    in_dir = tmp_path / "deglitched"
    out_dir = tmp_path / "processed"
    _write_uvw(in_dir / "S0027.mseed", np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    (in_dir / "deglitch_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "complete",
                "expected_event_ids": ["S0027"],
                "events": [{"event_id": "S0027", "overall_status": "succeeded_mps_only"}],
            }
        )
    )

    with pytest.raises(ValueError, match="Unknown deglitch status"):
        rotate_mod.rotate_all(in_dir, out_dir, allowed_deglitch_statuses={"partial_mps_only"})

    assert not (out_dir / "S0027_ZNE.mseed").exists()


def test_rotate_all_fails_fast_when_deglitched_inputs_are_absent(tmp_path):
    with pytest.raises(FileNotFoundError, match="No MiniSEED inputs"):
        rotate_mod.rotate_all(tmp_path / "empty-deglitched", tmp_path / "processed")


def test_rotate_all_requires_successful_deglitch_summary_by_default(tmp_path):
    in_dir = tmp_path / "deglitched"
    out_dir = tmp_path / "processed"
    _write_uvw(in_dir / "S0012.mseed", np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    (in_dir / "deglitch_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "complete",
                "expected_event_ids": ["S0012"],
                "events": [{"event_id": "S0012", "overall_status": "succeeded_mps_only"}],
            }
        )
    )

    with pytest.raises(RuntimeError, match="Disallowed deglitch statuses"):
        rotate_mod.rotate_all(in_dir, out_dir)


def test_rotate_all_refuses_attested_not_verified_by_default(tmp_path):
    in_dir = tmp_path / "deglitched"
    out_dir = tmp_path / "processed"
    _write_uvw(in_dir / "S0023.mseed", np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    (in_dir / "deglitch_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "complete",
                "expected_event_ids": ["S0023"],
                "events": [
                    {
                        "event_id": "S0023",
                        "overall_status": "sidecar_attested_not_independently_verified",
                    }
                ],
            }
        )
    )

    with pytest.raises(RuntimeError, match="Disallowed deglitch statuses"):
        rotate_mod.rotate_all(in_dir, out_dir)


def test_rotate_all_allows_partial_deglitch_status_when_explicit(tmp_path):
    in_dir = tmp_path / "deglitched"
    out_dir = tmp_path / "processed"
    _write_uvw(in_dir / "S0013.mseed", np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    (in_dir / "deglitch_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "complete",
                "expected_event_ids": ["S0013"],
                "events": [{"event_id": "S0013", "overall_status": "succeeded_mps_only"}],
            }
        )
    )

    count = rotate_mod.rotate_all(in_dir, out_dir, allowed_deglitch_statuses={"succeeded_mps_only"})

    assert count == 1
    assert (out_dir / "S0013_ZNE.mseed").exists()


def test_rotate_all_rejects_incomplete_deglitch_summary(tmp_path):
    in_dir = tmp_path / "deglitched"
    out_dir = tmp_path / "processed"
    _write_uvw(in_dir / "S0014.mseed", np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    (in_dir / "deglitch_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "in_progress",
                "expected_event_ids": ["S0014"],
                "events": [],
            }
        )
    )

    with pytest.raises(RuntimeError, match="Deglitch run summary is not complete"):
        rotate_mod.rotate_all(in_dir, out_dir)


def test_rotate_all_requires_exact_summary_and_mseed_event_set(tmp_path):
    in_dir = tmp_path / "deglitched"
    out_dir = tmp_path / "processed"
    _write_uvw(in_dir / "S0015.mseed", np.ones(80), np.ones(80) * 2.0, np.ones(80) * 3.0)
    (in_dir / "deglitch_run_summary.json").write_text(
        json.dumps(
            {
                "run_status": "complete",
                "expected_event_ids": ["S0015", "S0016"],
                "events": [
                    {"event_id": "S0015", "overall_status": "succeeded"},
                    {"event_id": "S0016", "overall_status": "succeeded"},
                ],
            }
        )
    )

    with pytest.raises(RuntimeError, match="Deglitch summary/file event mismatch"):
        rotate_mod.rotate_all(in_dir, out_dir)


def test_bandpass_file_preserves_ablation_z_only_contract(tmp_path):
    t = np.arange(0.0, 20.0, 0.05)
    in_path = tmp_path / "S0001_ZNE.mseed"
    out_path = tmp_path / "S0001_Z_filt.mseed"
    _write_zne(
        in_path,
        np.sin(2.0 * np.pi * 0.4 * t),
        np.cos(2.0 * np.pi * 0.4 * t),
        np.sin(2.0 * np.pi * 0.2 * t),
    )

    bandpass_file(in_path, out_path)

    st = read(str(out_path))
    assert len(st) == 1
    assert st[0].stats.channel == "BHZ"


def test_bandpass_file_writes_source_bound_metadata(tmp_path):
    t = np.arange(0.0, 20.0, 0.05)
    in_path = tmp_path / "S0020_ZNE.mseed"
    out_path = tmp_path / "S0020_Z_filt.mseed"
    _write_zne(
        in_path,
        np.sin(2.0 * np.pi * 0.4 * t),
        np.zeros_like(t),
        np.zeros_like(t),
    )

    bandpass_file(in_path, out_path)

    metadata = json.loads(out_path.with_suffix(".bandpass.json").read_text(encoding="utf-8"))
    assert metadata["method"] == "zero_phase_bhz_bandpass"
    assert metadata["algorithm_revision"] == ABLATION_BANDPASS_REVISION
    assert metadata["source_zne_sha256"] == sha256_file(in_path)
    assert metadata["output_trace_sha256"] == sha256_file(out_path)
    assert metadata["bandpass_hz"] == [0.2, 0.8]


def test_polarization_filter_consumes_zne_and_suppresses_poorly_polarized_motion(tmp_path):
    rng = np.random.default_rng(7)
    t = np.arange(0.0, 20.0, 0.05)
    split = t.size // 2
    z = np.sin(2.0 * np.pi * 0.4 * t)
    n = np.zeros_like(z)
    e = np.zeros_like(z)
    z[split:] += 0.6 * rng.normal(size=t.size - split)
    n[split:] = 0.7 * rng.normal(size=t.size - split)
    e[split:] = 0.7 * rng.normal(size=t.size - split)

    in_path = tmp_path / "S0002_ZNE.mseed"
    out_path = tmp_path / "S0002_Z_polfilt.mseed"
    _write_zne(in_path, z, n, e)

    polarization_filter_file(in_path, out_path)

    filtered = read(str(out_path))[0].data.astype(float)
    noisy_before = np.sqrt(np.mean(np.square(z[split:])))
    noisy_after = np.sqrt(np.mean(np.square(filtered[split:])))
    linear_before = np.sqrt(np.mean(np.square(z[:split])))
    linear_after = np.sqrt(np.mean(np.square(filtered[:split])))

    assert noisy_after < noisy_before
    assert linear_after > 0.4 * linear_before


def test_true_montalbetti_kanasewich_branch_component_weights_original_components():
    pol_mod = import_local_module(
        "marsquake_true_mk_filter_test",
        "scripts/02_preprocess/polarization_filter.py",
    )
    t = np.arange(0.0, 40.0, 0.05)
    z = np.sin(2.0 * np.pi * 0.4 * t)
    n = z.copy()
    e = np.zeros_like(z)

    principal = pol_mod.principal_axis_dop_filter_arrays(z, n, e, 20.0)
    true_mk = pol_mod.montalbetti_kanasewich_filter_arrays(z, n, e, 20.0)

    assert true_mk.shape == z.shape
    assert np.max(np.abs(true_mk)) < np.max(np.abs(principal))
    assert np.corrcoef(true_mk, z)[0, 1] > 0.95


def test_polarization_filter_writes_true_mk_operator_metadata(tmp_path):
    pol_mod = import_local_module(
        "marsquake_true_mk_file_test",
        "scripts/02_preprocess/polarization_filter.py",
    )
    t = np.arange(0.0, 20.0, 0.05)
    z = np.sin(2.0 * np.pi * 0.4 * t)
    n = z.copy()
    e = np.zeros_like(z)
    in_path = tmp_path / "S0021_ZNE.mseed"
    out_path = tmp_path / "S0021_Z_polfilt.mseed"
    _write_zne(in_path, z, n, e)

    pol_mod.polarization_filter_file(in_path, out_path, operator="montalbetti_kanasewich_1970")

    metadata = json.loads(out_path.with_suffix(".polarization.json").read_text())
    assert metadata["operator"] == "montalbetti_kanasewich_1970"
    assert metadata["method_section"] == (
        "Montalbetti & Kanasewich (1970), Enhancement of Teleseismic Body Phases with a Polarization Filter, "
        "Geophys. J. R. astr. Soc. 21(2):119-129; "
        "equation-number attribution UNCONFIRMED-from-paywalled-source"
    )
    assert metadata["mk_rectilinearity_power"] == pytest.approx(1.0)
    assert metadata["mk_direction_power"] == pytest.approx(2.0)


def test_polarization_filter_default_invocation_writes_registered_mk_metadata(tmp_path):
    t = np.arange(0.0, 20.0, 0.05)
    z = np.sin(2.0 * np.pi * 0.4 * t)
    n = 0.5 * z
    e = np.zeros_like(z)

    in_path = tmp_path / "S0017_ZNE.mseed"
    out_path = tmp_path / "S0017_Z_polfilt.mseed"
    _write_zne(in_path, z, n, e)

    polarization_filter_file(in_path, out_path)

    metadata_path = out_path.with_suffix(".polarization.json")
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text())
    assert metadata["method"] == PAPERSTYLE_POLARIZATION_METHOD
    assert metadata["algorithm_revision"] == PAPERSTYLE_ALGORITHM_REVISION
    assert metadata["operator"] == "montalbetti_kanasewich_1970"
    assert metadata["legacy_artifact_mode"] == "paperfaith"
    assert metadata["is_rectilinearity_z_weight_proxy"] is False
    assert "principal-axis/DOP projection" not in metadata["notes"]
    assert metadata["source_zne_sha256"] == sha256_file(in_path)
    assert metadata["output_trace_sha256"] == sha256_file(out_path)
    assert metadata["overlap"] == pytest.approx(0.9)


def test_polarization_filter_explicit_principal_axis_notes_stay_labeled_ablation(tmp_path):
    pol_mod = import_local_module(
        "marsquake_principal_axis_metadata_test",
        "scripts/02_preprocess/polarization_filter.py",
    )
    t = np.arange(0.0, 20.0, 0.05)
    z = np.sin(2.0 * np.pi * 0.4 * t)
    n = 0.5 * z
    e = np.zeros_like(z)

    in_path = tmp_path / "S0024_ZNE.mseed"
    out_path = tmp_path / "S0024_Z_polfilt.mseed"
    _write_zne(in_path, z, n, e)

    pol_mod.polarization_filter_file(in_path, out_path, operator="principal_axis_projection")

    metadata = json.loads(out_path.with_suffix(".polarization.json").read_text())
    assert metadata["operator"] == "principal_axis_projection"
    assert "principal-axis/DOP projection ablation" in metadata["notes"]


def test_filter_bank_outputs_half_octave_mk_envelopes(tmp_path):
    pol_mod = import_local_module(
        "marsquake_polarization_filter_bank_test",
        "scripts/02_preprocess/polarization_filter.py",
    )
    assert hasattr(pol_mod, "write_filter_bank_file")
    t = np.arange(0.0, 32.0, 0.05)
    z = np.sin(2.0 * np.pi * 0.5 * t)
    n = 0.2 * z
    e = np.zeros_like(z)
    in_path = tmp_path / "S0018_ZNE.mseed"
    out_path = tmp_path / "S0018_mk_filterbank.npz"
    _write_zne(in_path, z, n, e)

    pol_mod.write_filter_bank_file(in_path, out_path)

    with np.load(out_path, allow_pickle=False) as payload:
        assert payload["method"].item() == PAPERSTYLE_FILTERBANK_METHOD
        assert payload["algorithm_revision"].item() == PAPERSTYLE_ALGORITHM_REVISION
        assert payload["operator"].item() == "montalbetti_kanasewich_1970"
        assert payload["source_zne_sha256"].item() == sha256_file(in_path)
        assert payload["bandwidth_octaves"].item() == pytest.approx(0.5)
        assert payload["envelope_window_s"].item() == pytest.approx(5.0)
        freqs = payload["center_frequencies_hz"]
        assert freqs[0] == pytest.approx(1.0 / 16.0)
        assert freqs[-1] == pytest.approx(2.0)
        assert payload["filtered_waveforms"].shape == payload["envelopes"].shape
        assert payload["filtered_waveforms"].shape[0] == freqs.size
        assert payload["time_axis_s"].shape == (t.size,)


def test_fdpa_outputs_s_transform_cross_spectral_dop_products(tmp_path):
    fdpa_source = repo_path("scripts/02_preprocess/fdpa.py")
    assert fdpa_source.exists(), "Paper0 needs an FDPA diagnostic stage, not only a Z-weight proxy"
    fdpa_mod = import_local_module(
        "marsquake_fdpa_test",
        "scripts/02_preprocess/fdpa.py",
    )

    rng = np.random.default_rng(11)
    t = np.arange(0.0, 40.0, 0.05)
    split = t.size // 2
    z = np.sin(2.0 * np.pi * 0.4 * t)
    n = np.zeros_like(z)
    e = np.zeros_like(z)
    z[split:] = rng.normal(scale=0.4, size=t.size - split)
    n[split:] = rng.normal(scale=0.4, size=t.size - split)
    e[split:] = rng.normal(scale=0.4, size=t.size - split)
    in_path = tmp_path / "S0019_ZNE.mseed"
    out_path = tmp_path / "S0019_fdpa.npz"
    _write_zne(in_path, z, n, e)

    fdpa_mod.fdpa_file(
        in_path,
        out_path,
        frequencies_hz=np.array([0.4], dtype=np.float64),
        window_cycles=3.0,
    )

    with np.load(out_path, allow_pickle=False) as payload:
        assert payload["method"].item() == PAPERSTYLE_FDPA_METHOD
        assert payload["algorithm_revision"].item() == PAPERSTYLE_ALGORITHM_REVISION
        assert payload["transform_family"].item() == PAPERSTYLE_FDPA_TRANSFORM_FAMILY
        assert payload["source_zne_sha256"].item() == sha256_file(in_path)
        assert payload["window_overlap"].item() == pytest.approx(0.9)
        assert payload["dop_threshold"].item() == pytest.approx(0.6)
        assert payload["dop"].shape == (1, t.size)
        assert payload["vrm"].shape == payload["hrm"].shape == payload["dop"].shape
        assert payload["vrm_minus_hrm"].shape == payload["dop"].shape
        assert payload["dop_mask"].dtype == np.bool_
        assert float(np.nanmean(payload["dop"][0, :split])) > float(np.nanmean(payload["dop"][0, split:]))


def test_fdpa_circular_mean_helper_respects_azimuth_wrap_and_invalid_values():
    fdpa_mod = import_local_module(
        "marsquake_fdpa_circular_mean_test",
        "scripts/02_preprocess/fdpa.py",
    )

    wrapped = fdpa_mod._circular_mean_degrees(np.array([359.0, 1.0], dtype=np.float64))

    assert min(abs(wrapped), abs(wrapped - 360.0)) < 1e-6
    assert np.isnan(fdpa_mod._circular_mean_degrees(np.array([np.nan], dtype=np.float64)))


def test_validation_inventory_requires_waveform_and_envelope_provenance(tmp_path, monkeypatch):
    event_id = "S7777"
    event_table = tmp_path / "event_table.csv"
    event_table.write_text(
        "event_id,origin_time,set,distance_deg\n"
        f"{event_id},2020-01-01T00:00:00Z,validation,29.0\n",
        encoding="utf-8",
    )
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    out_dir = tmp_path / "validation"
    raw_dir.mkdir()
    processed_dir.mkdir()
    (raw_dir / f"{event_id}.mseed").write_bytes(b"raw")
    source_path = processed_dir / f"{event_id}_ZNE.mseed"
    pol_path = processed_dir / f"{event_id}_Z_polfilt.mseed"
    source_path.write_bytes(b"source-zne")
    pol_path.write_bytes(b"polarized")
    source_sha = sha256_file(source_path)
    source_path.with_suffix(".rotation.json").write_text(
        json.dumps(
            {
                "method": "uvw_to_zne_nominal_seis_vbb",
                "algorithm_revision": ROTATION_ZNE_REVISION,
                "input_deglitched_trace": str(raw_dir / f"{event_id}.mseed"),
                "input_deglitched_sha256": sha256_file(raw_dir / f"{event_id}.mseed"),
                "output_zne_trace": str(source_path),
                "output_zne_sha256": source_sha,
                "deglitch_run_summary_sha256": "fake-summary-sha",
            }
        ),
        encoding="utf-8",
    )
    (processed_dir / f"{event_id}_Z_filt.mseed").write_bytes(b"filtered")
    (processed_dir / f"{event_id}_Z_polfilt.polarization.json").write_text(
        json.dumps(
            {
                    "method": PAPERSTYLE_POLARIZATION_METHOD,
                    "algorithm_revision": PAPERSTYLE_ALGORITHM_REVISION,
                    "operator": "principal_axis_projection",
                "is_rectilinearity_z_weight_proxy": False,
                "source_zne_sha256": source_sha,
                "output_trace_sha256": sha256_file(pol_path),
                "bandpass_hz": [0.2, 0.8],
                "win_length_s": 5.0,
                "overlap": 0.9,
                "dop_power": 1.0,
                "sampling_rate_hz": 20.0,
                "npts": 8,
            }
        ),
        encoding="utf-8",
    )
    centers = np.array([(1.0 / 16.0) * (2.0 ** (idx / 2.0)) for idx in range(11)], dtype=np.float32)
    fdpa_freqs = np.geomspace(0.2, 0.8, 13).astype(np.float32)
    np.savez(
        processed_dir / f"{event_id}_mk_filterbank.npz",
        method=np.array(PAPERSTYLE_FILTERBANK_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        center_frequencies_hz=centers,
        bandwidth_octaves=np.array(0.5, dtype=np.float32),
        polarization_window_s=np.array(5.0, dtype=np.float32),
        polarization_overlap=np.array(0.9, dtype=np.float32),
        dop_power=np.array(1.0, dtype=np.float32),
        source_zne_sha256=np.array(source_sha),
        envelope_window_s=np.array(5.0, dtype=np.float32),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
    )
    np.savez(
        processed_dir / f"{event_id}_fdpa.npz",
        method=np.array(PAPERSTYLE_FDPA_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        transform_family=np.array(PAPERSTYLE_FDPA_TRANSFORM_FAMILY),
        source_zne_sha256=np.array(source_sha),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        window_overlap=np.array(0.9, dtype=np.float32),
        window_cycles=np.array(3.0, dtype=np.float32),
        dop_threshold=np.array(0.6, dtype=np.float32),
        bandpass_hz=np.array([0.2, 0.8], dtype=np.float32),
        frequencies_hz=fdpa_freqs,
    )
    _write_trace(processed_dir / f"{event_id}_aligned_ablation.mseed", np.zeros(8, dtype=np.float32))
    aligned_path = processed_dir / f"{event_id}_aligned_paperfaith.mseed"
    _write_trace(aligned_path, np.zeros(8, dtype=np.float32))
    aligned_time_path = processed_dir / f"{event_id}_paperfaith_times.npy"
    aligned_mask_path = processed_dir / f"{event_id}_paperfaith_valid_samples.npy"
    np.save(aligned_time_path, np.arange(8, dtype=np.float32) / 20.0)
    np.save(aligned_mask_path, np.ones(8, dtype=bool))
    aligned_metadata_path = aligned_path.with_suffix(".alignment.json")
    aligned_metadata_path.write_text(
        json.dumps(
            {
                "input_trace_sha256": sha256_file(pol_path),
                "algorithm_revision": PAPERSTYLE_ALIGNMENT_REVISION,
                "paperstyle_algorithm_revision": PAPERSTYLE_ALGORITHM_REVISION,
                "polarization_metadata_sha256": sha256_file(processed_dir / f"{event_id}_Z_polfilt.polarization.json"),
                "filterbank_sha256": sha256_file(processed_dir / f"{event_id}_mk_filterbank.npz"),
                "fdpa_sha256": sha256_file(processed_dir / f"{event_id}_fdpa.npz"),
                "output_trace_sha256": sha256_file(aligned_path),
                "time_axis_sha256": sha256_file(aligned_time_path),
                "valid_sample_mask_sha256": sha256_file(aligned_mask_path),
                "mode": "paperfaith",
                "sampling_rate_hz": 20.0,
                "npts": 8,
            }
        ),
        encoding="utf-8",
    )
    waveform_path = processed_dir / f"{event_id}_paperfaith_C_waveform.npy"
    envelope_path = processed_dir / f"{event_id}_paperfaith_C_envelope.npy"
    waveform_mask_path = processed_dir / f"{event_id}_paperfaith_C_waveform_valid_samples.npy"
    envelope_mask_path = processed_dir / f"{event_id}_paperfaith_C_envelope_valid_samples.npy"
    variant_time_path = processed_dir / f"{event_id}_paperfaith_C_times.npy"
    np.save(waveform_path, np.zeros(8, dtype=np.float32))
    np.save(envelope_path, np.zeros(8, dtype=np.float32))
    np.save(waveform_mask_path, np.ones(8, dtype=bool))
    np.save(envelope_mask_path, np.ones(8, dtype=bool))
    np.save(variant_time_path, np.arange(8, dtype=np.float32) / 20.0)
    (processed_dir / f"{event_id}_paperfaith_C.normalization.json").write_text(
        json.dumps(
            {
                "artifact_schema_version": "paper0-normalized-mask-v1",
                "event_id": event_id,
                "mode": "paperfaith",
                "variant": "C",
                "method": "zscore_window_and_smoothed_envelope",
                "input_aligned_sha256": sha256_file(aligned_path),
                "algorithm_revision": PAPERSTYLE_NORMALIZATION_REVISION,
                "input_alignment_metadata_sha256": sha256_file(aligned_metadata_path),
                "input_valid_sample_mask_sha256": sha256_file(aligned_mask_path),
                "waveform_sha256": sha256_file(waveform_path),
                "envelope_sha256": sha256_file(envelope_path),
                "waveform_valid_sample_mask_sha256": sha256_file(waveform_mask_path),
                "envelope_valid_sample_mask_sha256": sha256_file(envelope_mask_path),
                "time_axis_sha256": sha256_file(variant_time_path),
                "normalization_window_s": [-100.0, 2200.0],
                "normalization_valid_sample_count": 8,
                "sampling_rate_hz": 20.0,
                "npts": 8,
            }
        ),
        encoding="utf-8",
    )
    np.save(waveform_path, np.ones(8, dtype=np.float32))
    monkeypatch.setattr(validation_mod, "read_catalog", lambda _: object())
    monkeypatch.setattr(validation_mod, "find_best_event_match", lambda catalog, event_id_arg, origin: (object(), 0.0))
    monkeypatch.setattr(validation_mod.align_mod, "_event_matches_id", lambda event, event_id_arg: True)
    monkeypatch.setattr(
        validation_mod.align_mod,
        "get_matching_pick",
        lambda event, event_id_arg: {"time": "2020-01-01T00:00:00Z"},
    )

    inventory = validation_mod.build_event_inventory(event_table, tmp_path / "catalog.xml", raw_dir, processed_dir, out_dir)

    assert inventory["rows"][0]["complete_processing"] is False
    assert "waveform hash mismatch" in inventory["rows"][0]["paperstyle_normalization_status"]


def test_normalize_and_save_uses_passed_time_axis_when_available(tmp_path):
    event = "S0003"
    mode = "paperfaith"
    in_path = tmp_path / f"{event}_{mode}.mseed"
    data = np.linspace(-1.0, 1.0, 400)
    custom_time = np.linspace(-100.0, 2200.0, data.size, dtype=np.float32)
    _write_trace(in_path, data)
    time_path = tmp_path / f"{event}_{mode}_times.npy"
    mask_path = tmp_path / f"{event}_{mode}_valid_samples.npy"
    np.save(time_path, custom_time.astype(np.float64))
    np.save(mask_path, np.ones(data.size, dtype=bool))
    in_path.with_suffix(".alignment.json").write_text(
        json.dumps(
            {
                "event_id": event,
                "mode": mode,
                "algorithm_revision": PAPERSTYLE_ALIGNMENT_REVISION,
                "output_trace_sha256": sha256_file(in_path),
                "time_axis_sha256": sha256_file(time_path),
                "valid_sample_mask_sha256": sha256_file(mask_path),
                "sampling_rate_hz": 20.0,
                "npts": data.size,
            }
        ),
        encoding="utf-8",
    )

    normalize_and_save(event, mode, in_path, custom_time, tmp_path)

    saved = np.load(tmp_path / f"{event}_{mode}_C_times.npy")
    assert np.allclose(saved, custom_time)


def test_glitch_flag_output_base_event_id_matches_paper0():
    assert glitch_mod._base_event_id("S0235b_Z_filt") == "S0235b"
