from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from obspy import UTCDateTime, read

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import (
    PAPERSTYLE_ALIGNMENT_REVISION,
    PAPERSTYLE_ALGORITHM_REVISION,
    PAPERSTYLE_FDPA_METHOD,
    PAPERSTYLE_FDPA_TRANSFORM_FAMILY,
    PAPERSTYLE_FILTERBANK_METHOD,
    PAPERSTYLE_POLARIZATION_METHOD,
    event_texts_have_exact_event_id,
    find_best_event_match,
    get_preferred_origin,
    load_event_table,
    read_catalog,
    repo_path,
    sha256_file,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
CANONICAL_POLARIZATION_PARAMETERS = {
    "win_length_s": 5.0,
    "overlap": 0.9,
    "dop_power": 1.0,
}
CANONICAL_FILTERBANK_CENTER_FREQUENCIES_HZ = np.array(
    [(1.0 / 16.0) * (2.0 ** (idx / 2.0)) for idx in range(11)],
    dtype=np.float64,
)
CANONICAL_FDPA_FREQUENCIES_HZ = np.geomspace(0.2, 0.8, 13).astype(np.float64)
ALLOWED_POLARIZATION_OPERATORS = {
    "principal_axis_projection",
    "montalbetti_kanasewich_1970",
}


def _require_close(value: object, expected: float, *, event_id: str, label: str, context: str) -> None:
    if value is None or not np.isclose(float(value), float(expected), rtol=0.0, atol=1e-6):
        raise RuntimeError(
            f"Invalid current polarization products for {event_id}: {context} parameter mismatch for {label}"
        )


def _require_array_close(value: object, expected: np.ndarray, *, event_id: str, label: str, context: str) -> None:
    arr = np.asarray(value, dtype=np.float64)
    expected = np.asarray(expected, dtype=np.float64)
    if arr.shape != expected.shape or not np.allclose(arr, expected, rtol=0.0, atol=1e-6):
        raise RuntimeError(
            f"Invalid current polarization products for {event_id}: {context} parameter mismatch for {label}"
        )


def _relative_time_axis(npts: int, sampling_rate: float, pre: float) -> np.ndarray:
    return np.arange(npts, dtype=np.float64) / float(sampling_rate) - float(pre)


def _cut_with_zero_padding(tr, p_time: UTCDateTime, pre: float, post: float):
    sr = float(tr.stats.sampling_rate)
    target_n = int(round((float(pre) + float(post)) * sr))
    target_start = p_time - pre
    src_start = int(round((target_start - tr.stats.starttime) * sr))
    src_end = src_start + target_n

    out = np.zeros(target_n, dtype=tr.data.dtype)
    valid = np.zeros(target_n, dtype=bool)
    src_lo = max(0, src_start)
    src_hi = min(len(tr.data), src_end)
    if src_hi > src_lo:
        dst_lo = src_lo - src_start
        dst_hi = dst_lo + (src_hi - src_lo)
        out[dst_lo:dst_hi] = tr.data[src_lo:src_hi]
        valid[dst_lo:dst_hi] = True

    window = tr.copy()
    window.data = out
    window.stats.starttime = target_start
    window.stats.npts = target_n
    return window, valid, src_start, src_end


def _event_matches_id(event, event_id: str) -> bool:
    if isinstance(event, dict):
        texts = [event.get("resource_id", "")] + list(event.get("descriptions", []))
    else:
        resource = getattr(event, "resource_id", None)
        texts = [resource.id] if resource is not None else []
        descriptions = getattr(event, "event_descriptions", []) or []
        texts.extend(description.text for description in descriptions if getattr(description, "text", None))
    return event_texts_have_exact_event_id(texts, event_id)


def get_matching_pick(event, event_id: str):
    if isinstance(event, dict):
        preferred_origin = get_preferred_origin(event)
        picks = [
            p for p in event.get("picks", [])
            if p.get("waveform_id", {}).get("network_code") == "XB"
            and p.get("waveform_id", {}).get("station_code") == "ELYSE"
            and (p.get("phase_hint") or "").upper() == "P"
        ]

        if preferred_origin and preferred_origin.get("arrivals"):
            preferred_ids = {
                a["pick_id"] for a in preferred_origin["arrivals"]
                if a.get("pick_id") and (a.get("phase") or "").upper() == "P"
            }
            preferred = [p for p in picks if p.get("resource_id") in preferred_ids]
            if preferred:
                return sorted(preferred, key=lambda p: p["time"].timestamp)[0]

        if len(picks) == 1:
            return picks[0]
        if picks:
            return sorted(picks, key=lambda p: p["time"].timestamp)[0]
    else:
        preferred_origin = get_preferred_origin(event)
        picks = []
        if event.picks:
            picks = [
                p for p in event.picks
                if getattr(p.waveform_id, "network_code", None) == "XB"
                and getattr(p.waveform_id, "station_code", None) == "ELYSE"
                and (p.phase_hint or "").upper() == "P"
            ]

        if preferred_origin and preferred_origin.arrivals:
            preferred_ids = {a.pick_id.id for a in preferred_origin.arrivals if a.pick_id and (a.phase or "").upper() == "P"}
            preferred = [p for p in picks if p.resource_id and p.resource_id.id in preferred_ids]
            if preferred:
                return sorted(preferred, key=lambda p: p.time.timestamp)[0]

        if len(picks) == 1:
            return picks[0]
        if picks:
            return sorted(picks, key=lambda p: p.time.timestamp)[0]
    raise ValueError(f"No XB/ELYSE/P pick for {event_id}")


def _candidate_p_picks(event) -> list:
    if isinstance(event, dict):
        return [
            p for p in event.get("picks", [])
            if p.get("waveform_id", {}).get("network_code") == "XB"
            and p.get("waveform_id", {}).get("station_code") == "ELYSE"
            and (p.get("phase_hint") or "").upper() == "P"
        ]
    return [
        p for p in (event.picks or [])
        if getattr(p.waveform_id, "network_code", None) == "XB"
        and getattr(p.waveform_id, "station_code", None) == "ELYSE"
        and (p.phase_hint or "").upper() == "P"
    ]


def _preferred_p_pick_ids(event) -> set[str]:
    preferred_origin = get_preferred_origin(event)
    if isinstance(event, dict):
        if not preferred_origin:
            return set()
        return {
            a["pick_id"] for a in preferred_origin.get("arrivals", [])
            if a.get("pick_id") and (a.get("phase") or "").upper() == "P"
        }
    if not preferred_origin or not getattr(preferred_origin, "arrivals", None):
        return set()
    return {
        a.pick_id.id for a in preferred_origin.arrivals
        if a.pick_id and (a.phase or "").upper() == "P"
    }


def _pick_resource_id(pick) -> str | None:
    if isinstance(pick, dict):
        return pick.get("resource_id")
    resource_id = getattr(pick, "resource_id", None)
    return resource_id.id if resource_id is not None else None


def _pick_waveform_id(pick) -> dict[str, str | None]:
    if isinstance(pick, dict):
        return dict(pick.get("waveform_id", {}))
    waveform_id = getattr(pick, "waveform_id", None)
    return {
        "network_code": getattr(waveform_id, "network_code", None),
        "station_code": getattr(waveform_id, "station_code", None),
        "location_code": getattr(waveform_id, "location_code", None),
        "channel_code": getattr(waveform_id, "channel_code", None),
    }


def _event_resource_id(event) -> str | None:
    if isinstance(event, dict):
        return event.get("resource_id")
    resource_id = getattr(event, "resource_id", None)
    return resource_id.id if resource_id is not None else None


def _origin_resource_id(origin) -> str | None:
    if isinstance(origin, dict):
        return origin.get("resource_id")
    resource_id = getattr(origin, "resource_id", None)
    return resource_id.id if resource_id is not None else None


def _preferred_origin_time(event) -> str | None:
    preferred_origin = get_preferred_origin(event)
    if isinstance(preferred_origin, dict):
        value = preferred_origin.get("time")
        return value.isoformat() if value is not None else None
    if preferred_origin is None or getattr(preferred_origin, "time", None) is None:
        return None
    return preferred_origin.time.isoformat()


def _pick_selection_metadata(event, pick, event_id: str, catalog_origin_delta_s: float | None, matched_by_event_id: bool | None) -> dict[str, object]:
    candidates = _candidate_p_picks(event)
    preferred_ids = _preferred_p_pick_ids(event)
    pick_id = _pick_resource_id(pick)
    return {
        "pick_resource_id": pick_id,
        "pick_phase_hint": (pick.get("phase_hint") if isinstance(pick, dict) else getattr(pick, "phase_hint", None)),
        "pick_waveform_id": _pick_waveform_id(pick),
        "candidate_p_pick_count": len(candidates),
        "preferred_origin_p_pick_ids": sorted(preferred_ids),
        "pick_selected_from_preferred_origin_arrival": bool(pick_id and pick_id in preferred_ids),
        "event_id_match_used": bool(matched_by_event_id),
        "catalog_origin_delta_s": None if catalog_origin_delta_s is None else float(catalog_origin_delta_s),
        "catalog_preferred_origin_time_utc": _preferred_origin_time(event),
        "selection_note": (
            "Event ID matches may be used despite large origin-time deltas; this is why Type III P-pick jitter is required."
        ),
    }


def validate_paperstyle_polarization_products(event_id: str, in_dir: Path) -> None:
    source_path = in_dir / f"{event_id}_ZNE.mseed"
    trace_path = in_dir / f"{event_id}_Z_polfilt.mseed"
    metadata_path = in_dir / f"{event_id}_Z_polfilt.polarization.json"
    filterbank_path = in_dir / f"{event_id}_mk_filterbank.npz"
    fdpa_path = in_dir / f"{event_id}_fdpa.npz"
    missing = [path.name for path in (source_path, trace_path, metadata_path, filterbank_path, fdpa_path) if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing current polarization products for {event_id}: {', '.join(missing)}")

    metadata = json.loads(metadata_path.read_text())
    if metadata.get("method") != PAPERSTYLE_POLARIZATION_METHOD:
        raise RuntimeError(f"Invalid current polarization products for {event_id}: unexpected method")
    if metadata.get("algorithm_revision") != PAPERSTYLE_ALGORITHM_REVISION:
        raise RuntimeError(f"Invalid current polarization products for {event_id}: algorithm_revision mismatch")
    if metadata.get("operator") not in ALLOWED_POLARIZATION_OPERATORS:
        raise RuntimeError(f"Invalid current polarization products for {event_id}: unexpected operator")
    if metadata.get("is_rectilinearity_z_weight_proxy") is not False:
        raise RuntimeError(f"Invalid current polarization products for {event_id}: stale rectilinearity proxy metadata")
    for key, expected in CANONICAL_POLARIZATION_PARAMETERS.items():
        _require_close(
            metadata.get(key),
            expected,
            event_id=event_id,
            label=key,
            context="canonical",
        )
    _require_array_close(
        metadata.get("bandpass_hz"),
        np.array([0.2, 0.8], dtype=np.float64),
        event_id=event_id,
        label="bandpass_hz",
        context="canonical",
    )
    source_zne_sha256 = metadata.get("source_zne_sha256")
    if source_zne_sha256 != sha256_file(source_path):
        raise RuntimeError(f"Invalid current polarization products for {event_id}: source_zne_sha256 mismatch")
    if metadata.get("output_trace_sha256") != sha256_file(trace_path):
        raise RuntimeError(f"Invalid current polarization products for {event_id}: output trace hash mismatch")

    with np.load(filterbank_path, allow_pickle=False) as payload:
        try:
            if payload["method"].item() != PAPERSTYLE_FILTERBANK_METHOD:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: unexpected filter-bank method")
            if "algorithm_revision" not in payload or payload["algorithm_revision"].item() != PAPERSTYLE_ALGORITHM_REVISION:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: filter-bank algorithm_revision mismatch")
            if "source_zne_sha256" not in payload or payload["source_zne_sha256"].item() != source_zne_sha256:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: filter-bank source_zne_sha256 mismatch")
            _require_array_close(
                payload["center_frequencies_hz"] if "center_frequencies_hz" in payload else np.array([]),
                CANONICAL_FILTERBANK_CENTER_FREQUENCIES_HZ,
                event_id=event_id,
                label="center_frequencies_hz",
                context="filter-bank",
            )
            _require_close(
                payload["bandwidth_octaves"] if "bandwidth_octaves" in payload else None,
                0.5,
                event_id=event_id,
                label="bandwidth_octaves",
                context="filter-bank",
            )
            _require_close(
                payload["envelope_window_s"] if "envelope_window_s" in payload else None,
                5.0,
                event_id=event_id,
                label="envelope_window_s",
                context="filter-bank",
            )
            comparisons = {
                "win_length_s": float(payload["polarization_window_s"]),
                "overlap": float(payload["polarization_overlap"]),
                "dop_power": float(payload["dop_power"]),
                "sampling_rate_hz": float(payload["sampling_rate_hz"]),
                "npts": int(payload["npts"]),
            }
            if "operator" in payload and str(payload["operator"].item()) != str(metadata.get("operator")):
                raise RuntimeError(f"Invalid current polarization products for {event_id}: parameter mismatch for operator")
            for key, actual in comparisons.items():
                expected = metadata.get(key)
                if expected is None or not np.isclose(float(expected), float(actual), rtol=0.0, atol=1e-6):
                    raise RuntimeError(f"Invalid current polarization products for {event_id}: parameter mismatch for {key}")
        except KeyError as exc:
            raise RuntimeError(f"Invalid current polarization products for {event_id}: missing filter-bank key {exc.args[0]}") from exc
    with np.load(fdpa_path, allow_pickle=False) as payload:
        try:
            if payload["method"].item() != PAPERSTYLE_FDPA_METHOD:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: unexpected FDPA method")
            if "algorithm_revision" not in payload or payload["algorithm_revision"].item() != PAPERSTYLE_ALGORITHM_REVISION:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: FDPA algorithm_revision mismatch")
            if payload["transform_family"].item() != PAPERSTYLE_FDPA_TRANSFORM_FAMILY:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: unexpected FDPA transform")
            if "source_zne_sha256" not in payload or payload["source_zne_sha256"].item() != source_zne_sha256:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: FDPA source_zne_sha256 mismatch")
            for key in ("sampling_rate_hz", "npts"):
                expected = metadata.get(key)
                actual = float(payload[key]) if key == "sampling_rate_hz" else int(payload[key])
                if expected is None or not np.isclose(float(expected), float(actual), rtol=0.0, atol=1e-6):
                    raise RuntimeError(f"Invalid current polarization products for {event_id}: parameter mismatch for {key}")
            expected_fdpa = {
                "window_overlap": 0.9,
                "window_cycles": 3.0,
                "dop_threshold": 0.6,
            }
            for key, expected in expected_fdpa.items():
                if key not in payload or not np.isclose(float(payload[key]), expected, rtol=0.0, atol=1e-6):
                    raise RuntimeError(f"Invalid current polarization products for {event_id}: FDPA parameter mismatch for {key}")
            if "bandpass_hz" not in payload or not np.allclose(payload["bandpass_hz"], np.array([0.2, 0.8]), rtol=0.0, atol=1e-6):
                raise RuntimeError(f"Invalid current polarization products for {event_id}: FDPA parameter mismatch for bandpass_hz")
            if "frequencies_hz" not in payload:
                raise RuntimeError(f"Invalid current polarization products for {event_id}: FDPA parameter mismatch for frequencies_hz")
            _require_array_close(
                payload["frequencies_hz"],
                CANONICAL_FDPA_FREQUENCIES_HZ,
                event_id=event_id,
                label="frequencies_hz",
                context="FDPA",
            )
        except KeyError as exc:
            raise RuntimeError(f"Invalid current polarization products for {event_id}: missing FDPA key {exc.args[0]}") from exc


def align_event(
    event_id: str,
    origin_time: str,
    event,
    in_dir: Path,
    out_dir: Path,
    *,
    catalog_origin_delta_s: float | None = None,
    matched_by_event_id: bool | None = None,
):
    p_pick = get_matching_pick(event, event_id)
    if isinstance(p_pick, dict):
        pick_time = p_pick.get("time")
    else:
        pick_time = p_pick.time
    if p_pick is None or pick_time is None:
        raise ValueError(f"No P pick for {event_id}")

    p_time = UTCDateTime(pick_time)
    pre = 100.0
    post = 2200.0
    preferred_origin = get_preferred_origin(event)
    lock_record = {
        "event_id": event_id,
        "catalog_event_id": _event_resource_id(event),
        "preferred_origin_id": _origin_resource_id(preferred_origin),
        "p_pick_resource_id": _pick_resource_id(p_pick),
        "p_pick_utc": p_time.isoformat(),
        "waveform_id": _pick_waveform_id(p_pick),
        "catalog_origin_delta_s": None if catalog_origin_delta_s is None else float(catalog_origin_delta_s),
        "matched_by_event_id": bool(matched_by_event_id),
        "alignment_metadata_paths": [],
    }

    for mode in ["ablation", "paperfaith"]:
        src_name = {
            "ablation": f"{event_id}_Z_filt.mseed",
            "paperfaith": f"{event_id}_Z_polfilt.mseed",
        }[mode]
        src = in_dir / src_name
        out_path = out_dir / f"{event_id}_aligned_{mode}.mseed"
        time_path = out_dir / f"{event_id}_{mode}_times.npy"
        mask_path = out_dir / f"{event_id}_{mode}_valid_samples.npy"
        metadata_path_out = out_path.with_suffix(".alignment.json")
        for stale in (out_path, time_path, mask_path, metadata_path_out):
            if stale.exists():
                stale.unlink()
        if not src.exists():
            logger.warning("Missing %s for %s", src_name, event_id)
            continue
        if mode == "paperfaith":
            validate_paperstyle_polarization_products(event_id, in_dir)

        st = read(str(src))
        if not st:
            raise ValueError(f"Empty stream: {src}")

        tr = st[0]
        window, valid_mask, source_start_sample, source_end_sample = _cut_with_zero_padding(tr, p_time, pre, post)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_out_path = out_path.with_suffix(out_path.suffix + ".tmp")
        window.write(str(tmp_out_path), format="MSEED")

        t = _relative_time_axis(len(window.data), window.stats.sampling_rate, pre)
        tmp_time_path = time_path.with_suffix(time_path.suffix + ".tmp.npy")
        tmp_mask_path = mask_path.with_suffix(mask_path.suffix + ".tmp.npy")
        np.save(tmp_time_path, t.astype(np.float64))
        np.save(tmp_mask_path, valid_mask)
        tmp_out_path.replace(out_path)
        tmp_time_path.replace(time_path)
        tmp_mask_path.replace(mask_path)
        alignment_metadata = {
            "event_id": event_id,
            "mode": mode,
            "artifact_schema_version": "paper0-alignment-mask-v1",
            "method": f"direct_p_alignment_{mode}",
            "algorithm_revision": PAPERSTYLE_ALIGNMENT_REVISION,
            "input_trace": str(src),
            "input_trace_sha256": sha256_file(src),
            "output_trace_sha256": sha256_file(out_path),
            "time_axis_sha256": sha256_file(time_path),
            "valid_sample_mask": str(mask_path),
            "valid_sample_mask_sha256": sha256_file(mask_path),
            "valid_sample_count": int(np.count_nonzero(valid_mask)),
            "valid_sample_fraction": float(np.count_nonzero(valid_mask) / max(1, valid_mask.size)),
            "source_start_sample_for_cut": int(source_start_sample),
            "source_end_sample_for_cut": int(source_end_sample),
            "p_pick_utc": p_time.isoformat(),
            "pick_selection": _pick_selection_metadata(
                event,
                p_pick,
                event_id,
                catalog_origin_delta_s,
                matched_by_event_id,
            ),
            "pre_s": pre,
            "post_s": post,
            "sampling_rate_hz": float(window.stats.sampling_rate),
            "npts": int(window.stats.npts),
        }
        if mode == "paperfaith":
            metadata_path = src.with_suffix(".polarization.json")
            filterbank_path = in_dir / f"{event_id}_mk_filterbank.npz"
            fdpa_path = in_dir / f"{event_id}_fdpa.npz"
            alignment_metadata.update(
                {
                    "method": "direct_p_alignment_with_current_paperstyle_polarization",
                    "paperstyle_algorithm_revision": PAPERSTYLE_ALGORITHM_REVISION,
                    "polarization_metadata_sha256": sha256_file(metadata_path),
                    "filterbank_sha256": sha256_file(filterbank_path),
                    "fdpa_sha256": sha256_file(fdpa_path),
                }
            )
        metadata_path_out.write_text(
            json.dumps(alignment_metadata, indent=2, sort_keys=True) + "\n"
        )
        lock_record["alignment_metadata_paths"].append(str(metadata_path_out))

        logger.info(
            "Aligned %s (%s): npts=%d, sr=%.3f, P=%s",
            event_id,
            mode,
            len(window.data),
            tr.stats.sampling_rate,
            p_time.isoformat(),
        )
    return lock_record


def _write_alignment_summary(out_dir: Path, summary: dict[str, object]) -> None:
    summary_path = out_dir / "alignment_run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_locked_pick_manifest(
    out_dir: Path,
    *,
    event_table: Path,
    catalog_xml: Path,
    records: list[dict[str, object]],
) -> Path:
    manifest_path = out_dir / "alignment_locked_manifest.json"
    payload = {
        "artifact_schema_version": "paper0-locked-picks-v1",
        "event_table": str(event_table),
        "event_table_sha256": sha256_file(event_table) if Path(event_table).exists() else "",
        "catalog_xml": str(catalog_xml),
        "catalog_sha256": sha256_file(catalog_xml) if Path(catalog_xml).exists() else "",
        "events": records,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_sha = sha256_file(manifest_path)
    for record in records:
        for metadata_text in record.get("alignment_metadata_paths", []) or []:
            metadata_path = Path(str(metadata_text))
            if not metadata_path.exists():
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["locked_pick_manifest_path"] = str(manifest_path)
            metadata["locked_pick_manifest_sha256"] = manifest_sha
            metadata["locked_pick_event_id"] = record.get("event_id")
            metadata["locked_pick_resource_id"] = record.get("p_pick_resource_id")
            metadata["locked_pick_utc"] = record.get("p_pick_utc")
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def align_all(event_table: Path, catalog_xml: Path, in_dir: Path, out_dir: Path):
    rows = load_event_table(event_table)
    catalog = read_catalog(catalog_xml)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {
        "event_table": str(event_table),
        "catalog_xml": str(catalog_xml),
        "input_dir": str(in_dir),
        "output_dir": str(out_dir),
        "expected_events": len(rows),
        "events": [],
        "status_counts": {},
    }
    lock_records: list[dict[str, object]] = []

    def record(event_id: str, status: str, reason: str = "") -> None:
        events = summary["events"]
        assert isinstance(events, list)
        events.append({"event_id": event_id, "status": status, "reason": reason})
        status_counts = summary["status_counts"]
        assert isinstance(status_counts, dict)
        status_counts[status] = int(status_counts.get(status, 0)) + 1

    for row in rows:
        event_id = row["event_id"]
        origin = row["origin_time"]

        required_inputs = [
            in_dir / f"{event_id}_Z_filt.mseed",
            in_dir / f"{event_id}_Z_polfilt.mseed",
        ]
        missing_inputs = [str(p.name) for p in required_inputs if not p.exists()]
        if missing_inputs:
            reason = f"missing filtered traces: {', '.join(missing_inputs)}"
            logger.error("Skipping %s (%s)", event_id, reason)
            record(event_id, "failed_missing_inputs", reason)
            continue

        try:
            event, time_delta = find_best_event_match(catalog, event_id, origin)
        except ValueError as exc:
            logger.error("Skipping %s (%s)", event_id, exc)
            record(event_id, "failed_catalog_match", str(exc))
            continue
        matched_by_id = _event_matches_id(event, event_id)
        if abs(time_delta) > 30 and not matched_by_id:
            reason = f"No close catalog time match for {event_id} (delta={time_delta}s)"
            logger.error(
                "No close catalog time match for %s (delta=%ss), skipping",
                event_id,
                time_delta,
            )
            record(event_id, "failed_catalog_match", reason)
            continue
        if abs(time_delta) > 30 and matched_by_id:
            logger.warning(
                "Using event-id match for %s despite origin-time delta=%ss",
                event_id,
                time_delta,
            )
        try:
            lock_record = align_event(
                event_id,
                origin,
                event,
                in_dir,
                out_dir,
                catalog_origin_delta_s=float(time_delta),
                matched_by_event_id=matched_by_id,
            )
            if lock_record:
                lock_records.append(lock_record)
        except Exception as exc:
            logger.error("Align failed for %s: %s", event_id, exc)
            record(event_id, "failed_alignment", str(exc))
            continue
        record(event_id, "succeeded")

    failures = [
        event
        for event in summary["events"]
        if isinstance(event, dict) and event.get("status") != "succeeded"
    ]
    summary["status"] = "failed" if failures else "succeeded"
    if not failures:
        manifest_path = _write_locked_pick_manifest(
            out_dir,
            event_table=event_table,
            catalog_xml=catalog_xml,
            records=lock_records,
        )
        summary["locked_pick_manifest"] = str(manifest_path)
        summary["locked_pick_manifest_sha256"] = sha256_file(manifest_path)
    _write_alignment_summary(out_dir, summary)
    if failures:
        raise RuntimeError(
            json.dumps(
                {
                    "alignment_batch_failed": {
                        "failed": len(failures),
                        "expected_events": len(rows),
                        "summary_path": str(out_dir / "alignment_run_summary.json"),
                    }
                },
                indent=2,
                sort_keys=True,
            )
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Align each trace on direct P and cut")
    parser.add_argument("--event-table", default=str(repo_path("manifest/event_table.csv")))
    parser.add_argument("--catalog", default=str(repo_path("data/raw/mqs_v14_catalog.xml")))
    parser.add_argument("--in-dir", default=str(repo_path("data/processed")))
    parser.add_argument("--out-dir", default=str(repo_path("data/processed")))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    align_all(Path(args.event_table), Path(args.catalog), Path(args.in_dir), Path(args.out_dir))
