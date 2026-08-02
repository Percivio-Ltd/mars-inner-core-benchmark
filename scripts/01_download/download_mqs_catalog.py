from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from obspy.clients.fdsn import Client

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import append_manifest_entry, repo_path, sha256_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SAGE_V14_PAGE = "https://ds.iris.edu/ds/nodes/dmc/tools/mars-events/v14/"


def download_from_iris( out_file: Path ) -> bool:
    client = Client("IRIS")
    cat = client.get_events(catalog="MQS")
    cat.write(str(out_file), format="QUAKEML")
    return True


def download_fallback_url(url: str, out_file: Path) -> bool:
    req = Request(url, headers={"User-Agent": "mars-ic-pipeline"})
    with urlopen(req, timeout=120) as resp:
        data = resp.read()
    if not data.startswith(b"<?xml") and b"<quakeml" not in data[:100]:
        return False
    out_file.write_bytes(data)
    return True


def find_sage_v14_catalog_url(page_url: str = SAGE_V14_PAGE) -> str:
    req = Request(page_url, headers={"User-Agent": "mars-ic-pipeline"})
    with urlopen(req, timeout=120) as resp:
        html = resp.read().decode("utf-8", "ignore")

    candidates = re.findall(r'href=["\']([^"\']+events_mars_extended_multiorigin_v14_[^"\']+\.xml)["\']', html, flags=re.IGNORECASE)
    if not candidates:
        raise RuntimeError(f"Could not locate v14 event catalog link on {page_url}")

    href = candidates[0]
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"https://ds.iris.edu{href}"
    return f"{page_url.rstrip('/')}/{href}"


def download_mqs_catalog(manifest_path: Path, out_file: Path) -> None:
    out_file.parent.mkdir(parents=True, exist_ok=True)
    method = "IRIS FDSN Client.get_events(catalog='MQS')"
    try:
        download_from_iris(out_file)
        logger.info("Downloaded MQS V14 via IRIS")
    except Exception as exc:
        logger.error("IRIS catalog download failed: %s", exc)
        fallback_urls = []
        try:
            fallback_urls.append(find_sage_v14_catalog_url())
        except Exception as page_exc:
            logger.warning("Could not resolve SAGE v14 catalog URL: %s", page_exc)
        for url in fallback_urls:
            try:
                ok = download_fallback_url(url, out_file)
                method = f"fallback:{url}"
                if ok:
                    logger.info("Downloaded MQS V14 via %s", url)
                    break
            except (HTTPError, URLError):
                logger.warning("Fallback URL failed: %s", url)
                continue
        else:
            raise RuntimeError("All MQS V14 download methods failed")

    append_manifest_entry(
        manifest_path,
        {
            "type": "mqs_catalog",
            "path": str(out_file.relative_to(repo_path("."))),
            "format": "QuakeML",
            "source": method,
            "sha256": sha256_file(out_file),
        },
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Download MQS V14 catalog")
    parser.add_argument(
        "--manifest",
        default=str(repo_path("manifest/data_manifest.json")),
    )
    parser.add_argument(
        "--out-file",
        default=str(repo_path("data/raw/mqs_v14_catalog.xml")),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download_mqs_catalog(Path(args.manifest), Path(args.out_file))
