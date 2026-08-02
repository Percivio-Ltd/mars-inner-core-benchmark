from __future__ import annotations

import csv
import builtins
import importlib.util
import json
import numpy as np
import pytest
import sys
from pathlib import Path

from scripts.shared import (
    append_manifest_entry,
    infer_nominal_sample_rate_hz,
    load_event_table,
    load_manifest,
    make_relative_path,
    repo_path,
    write_manifest,
)


def test_load_manifest_defaults_for_missing_file(tmp_path):
    path = tmp_path / "manifest.json"
    payload = load_manifest(path)
    assert path.exists() is False
    assert isinstance(payload, dict)
    assert "created_at" in payload
    assert "items" in payload
    assert payload["items"] == []


def test_shared_non_waveform_helpers_import_without_obspy(monkeypatch, tmp_path):
    removed = {name: module for name, module in list(sys.modules.items()) if name == "obspy" or name.startswith("obspy.")}
    for name in removed:
        sys.modules.pop(name, None)
    real_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "obspy" or name.startswith("obspy."):
            raise ModuleNotFoundError("blocked obspy import")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    spec = importlib.util.spec_from_file_location("marsquake_shared_no_obspy_test", repo_path("scripts/shared.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        assert module.load_manifest(tmp_path / "missing.json")["items"] == []
    finally:
        sys.modules.update(removed)


def test_append_manifest_entry_roundtrip(tmp_path):
    path = tmp_path / "manifest.json"
    write_manifest(path, {"created_at": "2026-03-10T00:00:00Z", "items": []})
    append_manifest_entry(
        path,
        {
            "url": "https://example.test/one",
            "path": "data/raw/S0001.mseed",
            "sha256": "abc",
            "status": "ok",
        },
    )
    payload = load_manifest(path)
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    for k in ["url", "path", "sha256", "status", "created_at"]:
        assert k in item


def test_load_manifest_with_corrupt_json_fails_fast(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"created_at": "x", "items": [}')
    with pytest.raises(json.JSONDecodeError):
        load_manifest(path)


def test_make_relative_path_inside_root(tmp_path):
    root = repo_path(".")
    inside = root / "data" / "raw" / "S0001.mseed"
    assert make_relative_path(inside) == "data/raw/S0001.mseed"


def test_make_relative_path_outside_root(tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    rel = make_relative_path(outside)
    assert rel == str(outside)


def test_load_event_table_parses_all_columns(tmp_path):
    path = tmp_path / "event_table.csv"
    rows = [
        ["index", "event_id", "quality", "origin_time", "distance_deg", "distance_err", "baz_deg", "set"],
        ["1", "S0001", "A", "2021-01-01T00:00:00.000000Z", "29.0", "1.0", "90.0", "vespagram"],
        ["2", "S0002", "B", "2021-01-02T00:00:00.000000Z", "30.0", "2.0", "", "validation"],
    ]
    path.write_text("\n".join(",".join(r) for r in rows) + "\n")

    parsed = load_event_table(path)
    assert len(parsed) == 2
    assert parsed[0]["event_id"] == "S0001"
    assert parsed[1]["set"] == "validation"
    assert float(parsed[0]["distance_deg"]) == 29.0
    assert parsed[1]["baz_deg"] == ""


def test_infer_nominal_sample_rate_snaps_float32_near_20hz_axis():
    axis = (np.arange(46000, dtype=np.float64) / 20.0 - 100.0).astype(np.float32)
    assert infer_nominal_sample_rate_hz(axis) == 20.0


def test_infer_nominal_sample_rate_preserves_non_nominal_fixture_axis():
    axis = np.linspace(-100.0, 2200.0, 2301)
    assert infer_nominal_sample_rate_hz(axis) == 1.0


def test_vespagram_payload_shape_contract(tmp_path):
    v = np.random.RandomState(0).normal(size=(11, 1000)).astype(np.float32)
    slowness = np.linspace(-10.0, 0.0, 11)
    time = np.linspace(-100.0, 2200.0, 1000)
    out = tmp_path / "vespagram_payload.npz"

    np.savez(
        out,
        vespagram=v,
        slowness_axis=slowness,
        time_axis=time,
        events=np.array(["S0001", "S0002"], dtype=object),
        distances=np.array([29.0, 30.0], dtype=float),
        mode="paperfaith",
        input_type="waveform",
        norm_variant="C",
        power_window_s=20.0,
    )

    payload = np.load(out, allow_pickle=True)
    assert payload["vespagram"].shape == (len(slowness), len(time))
    assert len(payload["slowness_axis"]) == 11
    assert payload["time_axis"].ndim == 1
    assert payload["time_axis"].shape[0] == payload["vespagram"].shape[1]


def test_malformed_payload_missing_required_key(tmp_path):
    out = tmp_path / "bad_payload.npz"
    np.savez(
        out,
        vespagram=np.zeros((2, 2)),
        slowness_axis=np.array([-1, 1]),
        time_axis=np.array([0, 1]),
    )
    payload = np.load(out, allow_pickle=True)
    required = {"vespagram", "slowness_axis", "time_axis", "mode", "input_type", "norm_variant", "power_window_s"}
    assert not required.issubset(set(payload.files))
