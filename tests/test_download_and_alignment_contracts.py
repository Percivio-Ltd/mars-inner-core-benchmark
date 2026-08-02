from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd
import pytest
from obspy import UTCDateTime

from scripts.shared import (
    PAPERSTYLE_ALGORITHM_REVISION,
    PAPERSTYLE_FDPA_METHOD,
    PAPERSTYLE_FDPA_TRANSFORM_FAMILY,
    PAPERSTYLE_FILTERBANK_METHOD,
    PAPERSTYLE_POLARIZATION_METHOD,
    import_local_module,
    sha256_file,
)

download_mqs_mod = import_local_module(
    "marsquake_download_mqs_catalog_test",
    "scripts/01_download/download_mqs_catalog.py",
)
download_ak_mod = import_local_module(
    "marsquake_download_ak_models_test",
    "scripts/01_download/download_ak_models.py",
)
download_khan_mod = import_local_module(
    "marsquake_download_khan_models_test",
    "scripts/01_download/download_khan_models.py",
)
align_mod = import_local_module(
    "marsquake_align_and_cut_contract_test",
    "scripts/02_preprocess/align_and_cut.py",
)

DEFAULT_CENTER_FREQUENCIES_HZ = np.array([(1.0 / 16.0) * (2.0 ** (idx / 2.0)) for idx in range(11)], dtype=np.float32)
DEFAULT_FDPA_FREQUENCIES_HZ = np.geomspace(0.2, 0.8, 13).astype(np.float32)


def _write_nd(path: Path, mantle_vp: float, outer_vp: float, inner_vp: float) -> None:
    path.write_text(
        "\n".join(
            [
                "mantle",
                f"0.0 {mantle_vp:.2f} 2.6 3.3",
                "1500.0 5.00 2.8 3.4",
                "outer-core",
                f"1600.0 {outer_vp:.2f} 0.0 4.0",
                f"1700.0 {outer_vp + 0.1:.2f} 0.0 4.1",
                "inner-core",
                f"2800.0 {inner_vp:.2f} 4.0 6.5",
            ]
        )
        + "\n"
    )


def _write_current_paperstyle_products(in_dir: Path, event_id: str) -> None:
    source_path = in_dir / f"{event_id}_ZNE.mseed"
    trace_path = in_dir / f"{event_id}_Z_polfilt.mseed"
    source_path.write_bytes(f"{event_id}-source-zne".encode("utf-8"))
    trace_path.write_bytes(f"{event_id}-polarized-output".encode("utf-8"))
    source_sha = sha256_file(source_path)
    (in_dir / f"{event_id}_Z_polfilt.polarization.json").write_text(
        json.dumps(
            {
                "method": PAPERSTYLE_POLARIZATION_METHOD,
                "algorithm_revision": PAPERSTYLE_ALGORITHM_REVISION,
                "operator": "principal_axis_projection",
                "is_rectilinearity_z_weight_proxy": False,
                "source_zne_sha256": source_sha,
                "output_trace_sha256": sha256_file(trace_path),
                "bandpass_hz": [0.2, 0.8],
                "win_length_s": 5.0,
                "overlap": 0.9,
                "dop_power": 1.0,
                "sampling_rate_hz": 20.0,
                "npts": 8,
            }
        )
    )
    np.savez(
        in_dir / f"{event_id}_mk_filterbank.npz",
        method=np.array(PAPERSTYLE_FILTERBANK_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        center_frequencies_hz=DEFAULT_CENTER_FREQUENCIES_HZ,
        band_edges_hz=np.column_stack(
            [DEFAULT_CENTER_FREQUENCIES_HZ / (2.0**0.25), DEFAULT_CENTER_FREQUENCIES_HZ * (2.0**0.25)]
        ).astype(np.float32),
        bandwidth_octaves=np.array(0.5, dtype=np.float32),
        polarization_window_s=np.array(5.0, dtype=np.float32),
        polarization_overlap=np.array(0.9, dtype=np.float32),
        dop_power=np.array(1.0, dtype=np.float32),
        source_zne_sha256=np.array(source_sha),
        envelope_window_s=np.array(5.0, dtype=np.float32),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
        window_overlap=np.array(0.9, dtype=np.float32),
        window_cycles=np.array(3.0, dtype=np.float32),
        dop_threshold=np.array(0.6, dtype=np.float32),
        bandpass_hz=np.array([0.2, 0.8], dtype=np.float32),
        frequencies_hz=DEFAULT_FDPA_FREQUENCIES_HZ,
    )
    np.savez(
        in_dir / f"{event_id}_fdpa.npz",
        method=np.array(PAPERSTYLE_FDPA_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        transform_family=np.array(PAPERSTYLE_FDPA_TRANSFORM_FAMILY),
        source_zne_sha256=np.array(source_sha),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
        window_overlap=np.array(0.9, dtype=np.float32),
        window_cycles=np.array(3.0, dtype=np.float32),
        dop_threshold=np.array(0.6, dtype=np.float32),
        bandpass_hz=np.array([0.2, 0.8], dtype=np.float32),
        frequencies_hz=DEFAULT_FDPA_FREQUENCIES_HZ,
    )


def test_download_mqs_catalog_writes_catalog_to_path(tmp_path, monkeypatch):
    out = tmp_path / "mqs.xml"

    class DummyCatalog:
        def write(self, filename, format):
            assert format == "QUAKEML"
            Path(filename).write_text("<q></q>")

    class DummyClient:
        def __init__(self, name):
            assert name == "IRIS"

        def get_events(self, catalog):
            assert catalog == "MQS"
            return DummyCatalog()

    monkeypatch.setattr(download_mqs_mod, "Client", DummyClient)
    assert download_mqs_mod.download_from_iris(out) is True
    assert out.read_text() == "<q></q>"


def test_event_id_matching_rejects_substring_collisions():
    catalog = [
        {
            "resource_id": "smi:local/S1015f_extra",
            "descriptions": ["not-the-event-S1015f_extra"],
            "origins": [{"resource_id": "origin-wrong", "time": UTCDateTime("2021-01-01T00:00:00Z"), "arrivals": []}],
        },
        {
            "resource_id": "smi:local/event/S1015f",
            "descriptions": ["S1015f"],
            "origins": [{"resource_id": "origin-right", "time": UTCDateTime("2021-01-01T00:10:00Z"), "arrivals": []}],
        },
    ]

    event, delta = align_mod.find_best_event_match(catalog, "S1015f", "2021-01-01T00:00:00Z")

    assert event["resource_id"].endswith("/S1015f")
    assert delta == pytest.approx(600.0)
    assert align_mod._event_matches_id(catalog[0], "S1015f") is False
    assert align_mod._event_matches_id(catalog[1], "S1015f") is True


def test_pick_representative_models_ranks_outer_core_only(tmp_path):
    _write_nd(tmp_path / "model_a.nd", mantle_vp=5.0, outer_vp=5.1, inner_vp=99.0)
    _write_nd(tmp_path / "model_b.nd", mantle_vp=5.0, outer_vp=5.5, inner_vp=1.0)
    _write_nd(tmp_path / "model_c.nd", mantle_vp=5.0, outer_vp=5.9, inner_vp=2.0)

    selected, criterion = download_ak_mod.pick_representative_models(tmp_path)

    assert criterion == "percentile-ranking"
    assert selected["lower"].name == "model_a.nd"
    assert selected["mean"].name == "model_b.nd"
    assert selected["upper"].name == "model_c.nd"


def test_align_all_includes_validation_events(tmp_path, monkeypatch):
    rows = [
        {"event_id": "S0001", "origin_time": "2021-01-01T00:00:00Z", "set": "vespagram"},
        {"event_id": "S0002", "origin_time": "2021-01-02T00:00:00Z", "set": "validation"},
    ]
    called = []
    in_dir = tmp_path / "processed"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    for event_id in ("S0001", "S0002"):
        (in_dir / f"{event_id}_Z_filt.mseed").write_bytes(b"x")
        (in_dir / f"{event_id}_Z_polfilt.mseed").write_bytes(b"x")
        _write_current_paperstyle_products(in_dir, event_id)

    monkeypatch.setattr(align_mod, "load_event_table", lambda _: rows)
    monkeypatch.setattr(align_mod, "read_catalog", lambda _: object())
    monkeypatch.setattr(align_mod, "find_best_event_match", lambda catalog, event_id, origin: (object(), 0.0))
    def fake_align(event_id, origin_time, event, in_dir_arg, out_dir_arg, **kwargs):
        called.append(event_id)
        return {
            "event_id": event_id,
            "catalog_event_id": f"smi:local/event/{event_id}",
            "preferred_origin_id": f"smi:local/origin/{event_id}",
            "p_pick_resource_id": f"smi:local/pick/{event_id}",
            "p_pick_utc": origin_time,
            "waveform_id": {"network_code": "XB", "station_code": "ELYSE", "location_code": "02", "channel_code": "BHZ"},
            "alignment_metadata_paths": [],
        }

    monkeypatch.setattr(align_mod, "align_event", fake_align)

    align_mod.align_all(tmp_path / "event_table.csv", tmp_path / "catalog.xml", in_dir, out_dir)

    assert called == ["S0001", "S0002"]
    summary = json.loads((out_dir / "alignment_run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "succeeded"
    assert summary["status_counts"] == {"succeeded": 2}
    locked = json.loads((out_dir / "alignment_locked_manifest.json").read_text(encoding="utf-8"))
    assert locked["artifact_schema_version"] == "paper0-locked-picks-v1"
    assert [item["event_id"] for item in locked["events"]] == ["S0001", "S0002"]
    assert locked["events"][0]["p_pick_resource_id"] == "smi:local/pick/S0001"


def test_align_all_fails_closed_and_writes_summary_for_missing_inputs(tmp_path, monkeypatch):
    rows = [{"event_id": "S0001", "origin_time": "2021-01-01T00:00:00Z", "set": "vespagram"}]
    in_dir = tmp_path / "processed"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "S0001_Z_filt.mseed").write_bytes(b"x")

    monkeypatch.setattr(align_mod, "load_event_table", lambda _: rows)
    monkeypatch.setattr(align_mod, "read_catalog", lambda _: object())

    with pytest.raises(RuntimeError, match="alignment_batch_failed"):
        align_mod.align_all(tmp_path / "event_table.csv", tmp_path / "catalog.xml", in_dir, out_dir)

    summary = json.loads((out_dir / "alignment_run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "failed"
    assert summary["status_counts"] == {"failed_missing_inputs": 1}


def test_khan_manifest_excludes_generated_taup_npz_and_locks(tmp_path, monkeypatch):
    root = tmp_path / "khan"
    model_dir = root / "LSL_Models_TauP"
    model_dir.mkdir(parents=True)
    (model_dir / "Model_1.nd").write_text("mantle\n")
    (model_dir / "Model_1.npz").write_bytes(b"generated")
    (model_dir / "Model_2.npz.lock").write_bytes(b"")
    (model_dir / "Model_3.npz.invalid").write_bytes(b"invalid")
    (model_dir / "source_coefficients.npz").write_bytes(b"source-in-model-dir")
    source_dir = root / "SourcePayload"
    source_dir.mkdir()
    (source_dir / "coefficients.npz").write_bytes(b"source")
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(download_khan_mod, "repo_path", lambda rel: tmp_path if rel == "." else tmp_path / rel)

    download_khan_mod.append_extracted_file_entries(manifest, "doi:test", root)

    paths = [item["path"] for item in json.loads(manifest.read_text(encoding="utf-8"))["items"]]
    assert paths == [
        "khan/LSL_Models_TauP/Model_1.nd",
        "khan/LSL_Models_TauP/source_coefficients.npz",
        "khan/SourcePayload/coefficients.npz",
    ]


def test_paperstyle_alignment_requires_current_polarization_products(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    (in_dir / "S0003_Z_polfilt.mseed").write_bytes(b"x")

    with pytest.raises(RuntimeError, match="current polarization products"):
        align_mod.validate_paperstyle_polarization_products("S0003", in_dir)


def test_paperstyle_alignment_rejects_inconsistent_polarization_parameters(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    (in_dir / "S0004_Z_polfilt.mseed").write_bytes(b"x")
    _write_current_paperstyle_products(in_dir, "S0004")
    np.savez(
        in_dir / "S0004_mk_filterbank.npz",
        method=np.array(PAPERSTYLE_FILTERBANK_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        center_frequencies_hz=DEFAULT_CENTER_FREQUENCIES_HZ,
        bandwidth_octaves=np.array(0.5, dtype=np.float32),
        polarization_window_s=np.array(5.0, dtype=np.float32),
        polarization_overlap=np.array(0.5, dtype=np.float32),
        dop_power=np.array(1.0, dtype=np.float32),
        source_zne_sha256=np.array(sha256_file(in_dir / "S0004_ZNE.mseed")),
        envelope_window_s=np.array(5.0, dtype=np.float32),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
    )

    with pytest.raises(RuntimeError, match="parameter mismatch"):
        align_mod.validate_paperstyle_polarization_products("S0004", in_dir)


def test_paperstyle_alignment_rejects_stale_algorithm_revision(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    _write_current_paperstyle_products(in_dir, "S0011")
    metadata_path = in_dir / "S0011_Z_polfilt.polarization.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["algorithm_revision"] = "paper0-old-algorithm"
    metadata_path.write_text(json.dumps(metadata))

    with pytest.raises(RuntimeError, match="algorithm_revision mismatch"):
        align_mod.validate_paperstyle_polarization_products("S0011", in_dir)


def test_paperstyle_alignment_rejects_inconsistent_fdpa_parameters(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    (in_dir / "S0005_Z_polfilt.mseed").write_bytes(b"x")
    _write_current_paperstyle_products(in_dir, "S0005")
    np.savez(
        in_dir / "S0005_fdpa.npz",
        method=np.array(PAPERSTYLE_FDPA_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        transform_family=np.array(PAPERSTYLE_FDPA_TRANSFORM_FAMILY),
        source_zne_sha256=np.array(sha256_file(in_dir / "S0005_ZNE.mseed")),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
        window_overlap=np.array(0.5, dtype=np.float32),
        window_cycles=np.array(3.0, dtype=np.float32),
        dop_threshold=np.array(0.6, dtype=np.float32),
        bandpass_hz=np.array([0.2, 0.8], dtype=np.float32),
        frequencies_hz=DEFAULT_FDPA_FREQUENCIES_HZ,
    )

    with pytest.raises(RuntimeError, match="FDPA parameter mismatch"):
        align_mod.validate_paperstyle_polarization_products("S0005", in_dir)


def test_paperstyle_alignment_rejects_noncanonical_polarization_window(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    _write_current_paperstyle_products(in_dir, "S0008")
    metadata_path = in_dir / "S0008_Z_polfilt.polarization.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["win_length_s"] = 10.0
    metadata_path.write_text(json.dumps(metadata))
    np.savez(
        in_dir / "S0008_mk_filterbank.npz",
        method=np.array(PAPERSTYLE_FILTERBANK_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        center_frequencies_hz=DEFAULT_CENTER_FREQUENCIES_HZ,
        bandwidth_octaves=np.array(0.5, dtype=np.float32),
        polarization_window_s=np.array(10.0, dtype=np.float32),
        polarization_overlap=np.array(0.9, dtype=np.float32),
        dop_power=np.array(1.0, dtype=np.float32),
        source_zne_sha256=np.array(sha256_file(in_dir / "S0008_ZNE.mseed")),
        envelope_window_s=np.array(5.0, dtype=np.float32),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
    )

    with pytest.raises(RuntimeError, match="canonical parameter mismatch for win_length_s"):
        align_mod.validate_paperstyle_polarization_products("S0008", in_dir)


def test_paperstyle_alignment_rejects_noncanonical_filterbank_grid(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    _write_current_paperstyle_products(in_dir, "S0009")
    np.savez(
        in_dir / "S0009_mk_filterbank.npz",
        method=np.array(PAPERSTYLE_FILTERBANK_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        center_frequencies_hz=np.array([0.4], dtype=np.float32),
        bandwidth_octaves=np.array(0.5, dtype=np.float32),
        polarization_window_s=np.array(5.0, dtype=np.float32),
        polarization_overlap=np.array(0.9, dtype=np.float32),
        dop_power=np.array(1.0, dtype=np.float32),
        source_zne_sha256=np.array(sha256_file(in_dir / "S0009_ZNE.mseed")),
        envelope_window_s=np.array(5.0, dtype=np.float32),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
    )

    with pytest.raises(RuntimeError, match="center_frequencies_hz"):
        align_mod.validate_paperstyle_polarization_products("S0009", in_dir)


def test_paperstyle_alignment_rejects_noncanonical_fdpa_frequency_grid(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    _write_current_paperstyle_products(in_dir, "S0010")
    np.savez(
        in_dir / "S0010_fdpa.npz",
        method=np.array(PAPERSTYLE_FDPA_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        transform_family=np.array(PAPERSTYLE_FDPA_TRANSFORM_FAMILY),
        source_zne_sha256=np.array(sha256_file(in_dir / "S0010_ZNE.mseed")),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
        window_overlap=np.array(0.9, dtype=np.float32),
        window_cycles=np.array(3.0, dtype=np.float32),
        dop_threshold=np.array(0.6, dtype=np.float32),
        bandpass_hz=np.array([0.2, 0.8], dtype=np.float32),
        frequencies_hz=np.array([0.4], dtype=np.float32),
    )

    with pytest.raises(RuntimeError, match="frequencies_hz"):
        align_mod.validate_paperstyle_polarization_products("S0010", in_dir)


def test_paperstyle_alignment_rejects_mixed_source_filterbank(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    _write_current_paperstyle_products(in_dir, "S0006")
    np.savez(
        in_dir / "S0006_mk_filterbank.npz",
        method=np.array(PAPERSTYLE_FILTERBANK_METHOD),
        algorithm_revision=np.array(PAPERSTYLE_ALGORITHM_REVISION),
        polarization_window_s=np.array(5.0, dtype=np.float32),
        polarization_overlap=np.array(0.9, dtype=np.float32),
        dop_power=np.array(1.0, dtype=np.float32),
        source_zne_sha256=np.array("different-source"),
        sampling_rate_hz=np.array(20.0, dtype=np.float32),
        npts=np.array(8, dtype=np.int64),
        time_axis_s=np.arange(8, dtype=np.float32) / 20.0,
    )

    with pytest.raises(RuntimeError, match="source_zne_sha256"):
        align_mod.validate_paperstyle_polarization_products("S0006", in_dir)


def test_paperstyle_alignment_rejects_trace_rewritten_after_metadata(tmp_path):
    in_dir = tmp_path / "processed"
    in_dir.mkdir()
    _write_current_paperstyle_products(in_dir, "S0007")
    (in_dir / "S0007_Z_polfilt.mseed").write_bytes(b"stale-rewritten-output")

    with pytest.raises(RuntimeError, match="output trace hash mismatch"):
        align_mod.validate_paperstyle_polarization_products("S0007", in_dir)


def test_relative_time_axis_matches_sampling_rate():
    axis = align_mod._relative_time_axis(npts=5, sampling_rate=20.0, pre=100.0)
    assert np.allclose(axis, np.array([-100.0, -99.95, -99.90, -99.85, -99.80]))
