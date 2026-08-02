from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Iterable, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from obspy import UTCDateTime
from obspy.clients.fdsn import Client
from obspy.clients.fdsn.header import FDSNException
from obspy import read

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import (
    append_manifest_entry,
    load_event_table,
    make_relative_path,
    parse_utc,
    repo_path,
    sha256_file,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


MARS_EVENT_PAGE = "https://service.iris.edu/irisws/mars-events/1/"


def _request_bytes(url: str, timeout: int = 120) -> Tuple[bytes, str]:
    req = Request(url, headers={"User-Agent": "mars-ic-pipeline"})
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
        ctype = resp.headers.get("Content-Type", "").lower()
    return payload, ctype


def _extract_download_links(text: str) -> Iterable[str]:
    # Try JSON / HTML style links first
    links = re.findall(r"https?://[^\"'<>\s]+\.mseed", text, flags=re.IGNORECASE)
    for link in links:
        yield link
    for link in re.findall(r"/[^\"'<>\s]+\.mseed", text, flags=re.IGNORECASE):
        if link.startswith("http"):
            continue
        yield f"https://service.iris.edu{link}"


def _candidate_mars_event_urls(event_id: str, origin_time: str) -> Iterable[str]:
    # These endpoints are intentionally broad; whichever one resolves is used.
    yield f"{MARS_EVENT_PAGE}query?eventid={event_id}&format=xml"
    yield f"{MARS_EVENT_PAGE}query?eventid={event_id}&format=mseed"
    yield f"{MARS_EVENT_PAGE}query?eventid={event_id}&format=data"
    # Older/alternate forms
    yield f"{MARS_EVENT_PAGE}query?event={event_id}&format=xml"
    yield f"{MARS_EVENT_PAGE}query?event={event_id}&format=mseed"
    # Include origin-time query to improve catalog lookup coverage where event ids are not explicit.
    yield f"{MARS_EVENT_PAGE}query?time={origin_time}&format=xml"


def download_single_event(
    client: Client,
    event_row: dict,
    config: dict,
    output_dir: Path,
) -> Path:
    origin_time = parse_utc(event_row["origin_time"])
    starttime = origin_time - float(config["pre_arrival_s"])
    endtime = origin_time + float(config["post_arrival_s"])
    event_id = event_row["event_id"]

    out = output_dir / f"{event_id}.mseed"
    st = client.get_waveforms(
        network=config["network"],
        station=config["station"],
        location=config["location"],
        channel=config["channels"],
        starttime=starttime,
        endtime=endtime,
    )
    st.merge(fill_value=0.0)
    out.parent.mkdir(parents=True, exist_ok=True)
    st.write(str(out), format="MSEED")
    logger.info("Downloaded %s -> %s", event_id, out)
    return out


def download_via_mars_events_fallback(event_row: dict, output_dir: Path) -> Tuple[Path, str]:
    event_id = event_row["event_id"]
    out = output_dir / f"{event_id}.mseed"
    origin = event_row["origin_time"]

    last_error = "not tried"
    for candidate in _candidate_mars_event_urls(event_id, origin):
        try:
            data, ctype = _request_bytes(candidate)
            text = data.decode("utf-8", errors="ignore")

            # Direct binary payload
            if ctype.startswith("application") and b"MSE" in data[:4]:
                out.write_bytes(data)
                logger.info("Fallback binary download succeeded for %s via %s", event_id, candidate)
                return out, candidate

            # HTML/JSON with embedded download links
            for url in _extract_download_links(text):
                try:
                    downloaded, _ctype = _request_bytes(url)
                    if b"" == downloaded:
                        continue
                    out.write_bytes(downloaded)
                    logger.info("Fallback link download succeeded for %s via %s", event_id, url)
                    return out, url
                except Exception as exc:  # pragma: no cover
                    last_error = f"{candidate} -> {url}: {exc}"
                    continue

            # Some endpoints return quasi-XML QuakeML or station data directly.
            if b"<?xml" in data[:200] or b"<Quakeml" in data[:200] or b"<quakeml" in data[:200]:
                # If this is an XML response that is not seismic trace data, skip and continue.
                last_error = f"{candidate} returned non-trace XML"
                continue

            # Heuristic last-resort: save raw response if it looks like mseed magic bytes.
            if data[:4] == b"MSEd":
                out.write_bytes(data)
                logger.info("Fallback raw download succeeded for %s via %s", event_id, candidate)
                return out, candidate
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = f"{candidate}: {exc}"
            continue
        except Exception as exc:
            last_error = f"{candidate}: {exc}"
            continue

    raise RuntimeError(f"Mars-events fallback failed for {event_id}: {last_error}")


def download_waveforms(
    event_table_path: Path,
    manifest_path: Path,
    output_dir: Path,
    stop_on_error: bool = True,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_event_table(event_table_path)
    client = Client("IRIS")
    cfg = {
        "network": "XB",
        "station": "ELYSE",
        "location": "02",
        "channels": "BHU,BHV,BHW",
        "pre_arrival_s": 60,
        "post_arrival_s": 2500,
    }

    for row in rows:
        event_id = row["event_id"]
        origin_time = parse_utc(row["origin_time"])
        try:
            out = download_single_event(client, row, cfg, output_dir)
            append_manifest_entry(
                manifest_path,
                {
                    "type": "waveform",
                    "event_id": event_id,
                    "path": make_relative_path(out),
                    "source": "IRIS FDSN get_waveforms",
                    "sha256": sha256_file(out),
                    "network": cfg["network"],
                    "station": cfg["station"],
                    "location": cfg["location"],
                    "channels": cfg["channels"],
                    "start_time": str(origin_time - cfg["pre_arrival_s"]),
                    "end_time": str(origin_time + cfg["post_arrival_s"]),
                    "method": "client.get_waveforms",
                },
            )
            continue
        except (FDSNException, Exception) as exc:
            logger.error("IRIS FDSN failed for %s: %s", event_id, exc)
            logger.info("Attempting mars-events fallback for %s", event_id)
            try:
                out, source = download_via_mars_events_fallback(row, output_dir)
                append_manifest_entry(
                    manifest_path,
                    {
                        "type": "waveform",
                        "event_id": event_id,
                        "path": make_relative_path(out),
                        "source": "IRIS mars-events fallback",
                        "source_url": source,
                        "sha256": sha256_file(out),
                        "method": "mars-events fallback",
                        "error": str(exc),
                    },
                )
            except Exception as fallback_exc:
                error_msg = f"IRIS failed: {exc}; fallback failed: {fallback_exc}"
                if stop_on_error:
                    raise RuntimeError(f"FAILED event {event_id}: {error_msg}") from fallback_exc
                logger.warning("Skipping %s due to errors: %s", event_id, error_msg)
                append_manifest_entry(
                    manifest_path,
                    {
                        "type": "waveform",
                        "event_id": event_id,
                        "path": None,
                        "source": "failed",
                        "error": error_msg,
                    },
                )


def parse_args():
    parser = argparse.ArgumentParser(description="Download IRIS waveforms for Paper 0")
    parser.add_argument(
        "--event-table",
        default=str(repo_path("manifest/event_table.csv")),
    )
    parser.add_argument(
        "--manifest",
        default=str(repo_path("manifest/data_manifest.json")),
    )
    parser.add_argument("--out-dir", default=str(repo_path("data/raw")))
    parser.add_argument("--continue-on-fail", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download_waveforms(
        Path(args.event_table),
        Path(args.manifest),
        Path(args.out_dir),
        stop_on_error=not args.continue_on_fail,
    )
