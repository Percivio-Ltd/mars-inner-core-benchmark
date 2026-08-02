from __future__ import annotations

import csv
import hashlib
import json
import logging
import importlib.util
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)
EVENT_MATCH_MAX_DELTA_S = 30.0
NOMINAL_SAMPLE_RATE_HZ = 20.0
PAPERSTYLE_ALGORITHM_REVISION = "paper0-public-mk-fdpa-v2"
PAPERSTYLE_ALIGNMENT_REVISION = "paper0-direct-p-alignment-v3"
PAPERSTYLE_NORMALIZATION_REVISION = "paper0-zscore-envelope-v2"
ABLATION_BANDPASS_REVISION = "paper0-z-bandpass-v1"
ROTATION_ZNE_REVISION = "paper0-uvw-zne-v1"
PAPERSTYLE_POLARIZATION_METHOD = "public_mk_style_principal_axis_dop_projection"
PAPERSTYLE_FILTERBANK_METHOD = "public_mk_style_filter_bank_diagnostic"
PAPERSTYLE_FDPA_METHOD = "public_fdpa_style_stockwell_covariance_diagnostic"
PAPERSTYLE_FDPA_TRANSFORM_FAMILY = "public_fdpa_style_stockwell_covariance_diagnostic"

BED_NS = "http://quakeml.org/xmlns/bed/1.2"
QML_NS = "http://quakeml.org/xmlns/quakeml"
NS = {"bed": BED_NS, "q": QML_NS}
EVENT_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[A-Z]\d{4}[a-z](?![A-Za-z0-9_])")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_path(rel: str) -> Path:
    return project_root() / rel


def module_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def make_relative_path(path: Path) -> str:
    path = Path(path)
    try:
        return str(path.relative_to(project_root()))
    except ValueError:
        return str(path)


def import_local_module(module_name: str, relpath: str):
    """Load a module from a repository-relative path."""
    source = project_root() / relpath
    if not source.exists():
        raise FileNotFoundError(source)

    spec = importlib.util.spec_from_file_location(module_name, str(source))
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {source}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def infer_nominal_sample_rate_hz(
    time_axis: np.ndarray,
    *,
    nominal_hz: float = NOMINAL_SAMPLE_RATE_HZ,
    snap_atol_hz: float = 0.01,
) -> float:
    """Infer sample rate from a time axis, snapping near-nominal production axes to 20 Hz."""
    axis = np.asarray(time_axis, dtype=np.float64)
    if axis.ndim != 1 or axis.size < 2:
        raise ValueError("time_axis must be a 1D array with at least two samples")
    diffs = np.diff(axis)
    dt = float(np.median(diffs))
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("time_axis must be strictly increasing")
    if np.any(diffs <= 0.0):
        raise ValueError("time_axis must be strictly increasing")
    spacing_spread = float(np.percentile(diffs, 99.9) - np.percentile(diffs, 0.1))
    if spacing_spread > max(abs(dt) * 1e-2, 1e-6):
        raise ValueError("time_axis spacing is not uniform enough to infer a sampling rate")
    inferred = 1.0 / dt
    if abs(inferred - float(nominal_hz)) <= float(snap_atol_hz):
        return float(nominal_hz)
    return float(inferred)


def load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "items": [],
        }
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if "items" not in payload:
        payload["items"] = []
    if "created_at" not in payload:
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
    return payload


def write_manifest(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def append_manifest_entry(path: Path, entry: Dict[str, Any]) -> None:
    payload = load_manifest(path)
    entry = dict(entry)
    if "created_at" not in entry:
        entry["created_at"] = datetime.now(timezone.utc).isoformat()
    payload.setdefault("items", []).append(entry)
    write_manifest(path, payload)


def load_event_table(path: Path) -> List[Dict[str, str]]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def text_has_exact_event_id(text: object, event_id: str) -> bool:
    if text is None:
        return False
    return str(event_id) in EVENT_ID_PATTERN.findall(str(text))


def event_texts_have_exact_event_id(texts, event_id: str) -> bool:
    return any(text_has_exact_event_id(item, event_id) for item in texts)


def _obspy_time_and_events():
    from obspy import UTCDateTime, read_events

    return UTCDateTime, read_events


def read_catalog(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    _UTCDateTime, read_events = _obspy_time_and_events()
    if path.suffix.lower() == ".xml":
        try:
            return read_events(str(path))
        except Exception as exc:
            logger.warning("ObsPy read_events failed for %s, falling back to XML parser: %s", path, exc)
            return read_mqs_catalog_xml(path)
    if path.suffix.lower() in {".json", ".geojson", ".txt"}:
        raise ValueError("Expected QuakeML XML file for MQS catalog.")
    return read_events(str(path))


def parse_utc(value: str) -> UTCDateTime:
    UTCDateTime, _read_events = _obspy_time_and_events()
    return UTCDateTime(value)


def find_best_event_match(catalog, event_id: str, origin_time_iso: str):
    target = parse_utc(origin_time_iso)
    candidates = []
    for event in catalog:
        hit = False
        descriptions = []
        if isinstance(event, dict):
            resource_id = event.get("resource_id")
            if resource_id:
                descriptions.append(resource_id)
            descriptions.extend(event.get("descriptions", []))
            preferred_origin = get_preferred_origin(event)
            if preferred_origin and preferred_origin.get("time"):
                delta = abs(preferred_origin["time"].timestamp - target.timestamp)
            else:
                delta = float("inf")
        else:
            if event.resource_id is not None:
                descriptions.append(event.resource_id.id)
            for description in event.event_descriptions or []:
                if description.text:
                    descriptions.append(description.text)
            for comment in event.comments or []:
                if comment.text and comment.text.text:
                    descriptions.append(comment.text.text)

            if event.origins:
                preferred_origin = event.preferred_origin() or event.origins[0]
                delta = abs(preferred_origin.time.timestamp - target.timestamp)
            else:
                delta = float("inf")

        if event_texts_have_exact_event_id(descriptions, event_id):
            hit = True

        candidates.append((hit, delta, event))

    exact = [item for item in candidates if item[0]]
    if exact:
        exact = sorted(exact, key=lambda x: abs(x[1]))
        return exact[0][2], exact[0][1]

    fallback = sorted(candidates, key=lambda x: abs(x[1]))
    if fallback and abs(float(fallback[0][1])) <= EVENT_MATCH_MAX_DELTA_S:
        return fallback[0][2], fallback[0][1]
    if fallback:
        raise ValueError(
            f"No catalog event within {EVENT_MATCH_MAX_DELTA_S:.0f} s for {event_id} near {origin_time_iso}; "
            f"nearest fallback is {float(fallback[0][1]):.1f} s away"
        )
    raise ValueError(f"No matching event found for {event_id} near {origin_time_iso}")


def _findtext(node, path: str) -> str | None:
    return node.findtext(path, namespaces=NS)


def read_mqs_catalog_xml(path: Path):
    root = ET.parse(path).getroot()
    if root.tag not in {f"{{{QML_NS}}}quakeml", f"{{{BED_NS}}}quakeml"}:
        raise ValueError(f"Unsupported MQS XML root tag: {root.tag}")
    events = []
    for event in root.findall(".//bed:event", NS):
        descriptions = [
            text.strip()
            for text in (
                _findtext(desc, "bed:text")
                for desc in event.findall("bed:description", NS)
            )
            if text and text.strip()
        ]
        picks = []
        for pick in event.findall("bed:pick", NS):
            waveform = pick.find("bed:waveformID", NS)
            picks.append(
                {
                    "resource_id": pick.get("publicID"),
                    "phase_hint": (_findtext(pick, "bed:phaseHint") or "").strip(),
                    "time": parse_utc(_findtext(pick, "bed:time/bed:value")),
                    "waveform_id": {
                        "network_code": waveform.get("networkCode") if waveform is not None else None,
                        "station_code": waveform.get("stationCode") if waveform is not None else None,
                        "location_code": waveform.get("locationCode") if waveform is not None else None,
                        "channel_code": waveform.get("channelCode") if waveform is not None else None,
                    },
                }
            )

        origins = []
        for origin in event.findall("bed:origin", NS):
            arrivals = []
            for arrival in origin.findall("bed:arrival", NS):
                pick_id = _findtext(arrival, "bed:pickID")
                arrivals.append(
                    {
                        "pick_id": pick_id.strip() if pick_id else None,
                        "phase": (_findtext(arrival, "bed:phase") or "").strip(),
                    }
                )
            origin_time = _findtext(origin, "bed:time/bed:value")
            origins.append(
                {
                    "resource_id": origin.get("publicID"),
                    "time": parse_utc(origin_time) if origin_time else None,
                    "arrivals": arrivals,
                }
            )

        events.append(
            {
                "resource_id": event.get("publicID"),
                "descriptions": descriptions,
                "preferred_origin_id": (_findtext(event, "bed:preferredOriginID") or "").strip() or None,
                "origins": origins,
                "picks": picks,
            }
        )
    if not events:
        raise ValueError(f"No MQS events found in XML: {path}")
    return events


def get_preferred_origin(event):
    if isinstance(event, dict):
        preferred_id = event.get("preferred_origin_id")
        origins = event.get("origins", [])
        if preferred_id:
            for origin in origins:
                if origin.get("resource_id") == preferred_id:
                    return origin
        return origins[0] if origins else None
    return event.preferred_origin() or (event.origins[0] if event.origins else None)
