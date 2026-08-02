"""USAGE

Check registered MQS catalogue pins against an upstream catalogue manifest.

Example:
  python scripts/rc_catalogue_watch.py \
    --manifest manifest/data_manifest.json \
    --catalog data/raw/mqs_v14_catalog.xml \
    --upstream-json upstream_catalogues.json \
    --out-dir results/catalogue_watch

The upstream manifest is JSON with a `catalogues` list. Each row should carry
`path` and `sha256`; `doi`, `version`, and `source` are recorded when present.
The command exits 0 only when the registered pin, local file hash, and upstream
hash agree. Drift or fetch failures write `catalogue_watch_diff.json` and exit 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Mapping


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _manifest_root(path: Path) -> Path:
    if path.parent.name == "manifest":
        return path.parent.parent
    return path.parent


def _relative_catalog_path(manifest_path: Path, catalog_path: Path) -> str:
    root = _manifest_root(manifest_path)
    try:
        return str(catalog_path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(catalog_path)


def _load_registered_catalogue(manifest_path: Path, catalog_path: Path) -> dict[str, object]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    relpath = _relative_catalog_path(manifest_path, catalog_path)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("manifest missing items list")
    matches = [
        dict(item)
        for item in items
        if isinstance(item, Mapping)
        and item.get("type") == "mqs_catalog"
        and item.get("path") == relpath
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one registered MQS catalogue row for {relpath}, found {len(matches)}")
    row = matches[0]
    row["path"] = relpath
    row["local_sha256"] = _sha256_file(catalog_path)
    return row


def _load_upstream(args: argparse.Namespace) -> dict[str, Any]:
    if args.upstream_json:
        return json.loads(Path(args.upstream_json).read_text(encoding="utf-8"))
    request = urllib.request.Request(args.upstream_url, headers={"User-Agent": "MarsQuake-rc-catalogue-watch/1"})
    with urllib.request.urlopen(request, timeout=float(args.timeout_s)) as response:
        return json.loads(response.read().decode("utf-8"))


def _upstream_rows(payload: Mapping[str, object]) -> list[dict[str, object]]:
    rows = payload.get("catalogues")
    if not isinstance(rows, list):
        raise ValueError("upstream manifest missing catalogues list")
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _match_upstream_row(rows: list[dict[str, object]], registered: Mapping[str, object]) -> dict[str, object] | None:
    registered_path = str(registered.get("path", ""))
    for row in rows:
        if row.get("path") == registered_path:
            return row
    registered_source = str(registered.get("source", ""))
    for row in rows:
        if row.get("source") and str(row["source"]) in registered_source:
            return row
    return None


def _diff(registered: Mapping[str, object], upstream: Mapping[str, object] | None) -> list[dict[str, object]]:
    if upstream is None:
        return [{"field": "catalogue", "registered": registered.get("path"), "upstream": None}]
    differences = []
    registered_sha256 = registered.get("sha256")
    if str(registered_sha256) != str(upstream.get("sha256")):
        differences.append({
            "field": "sha256",
            "registered": registered_sha256,
            "upstream": upstream.get("sha256"),
        })
    local_sha256 = registered.get("local_sha256")
    if str(local_sha256) != str(registered_sha256):
        differences.append({
            "field": "local_sha256",
            "registered": registered_sha256,
            "local": local_sha256,
        })
    return differences


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--catalog", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--upstream-json")
    source.add_argument("--upstream-url")
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--out-dir", default="results/catalogue_watch")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    try:
        registered = _load_registered_catalogue(Path(args.manifest), Path(args.catalog))
        upstream_payload = _load_upstream(args)
        upstream = _match_upstream_row(_upstream_rows(upstream_payload), registered)
    except Exception as exc:
        _write_json(
            out_dir / "catalogue_watch_diff.json",
            {
                "status": "fetch_failed",
                "reason": str(exc),
                "manifest": args.manifest,
                "catalog": args.catalog,
            },
        )
        return 1

    differences = _diff(registered, upstream)
    if differences:
        _write_json(
            out_dir / "catalogue_watch_diff.json",
            {
                "status": "drift",
                "registered": registered,
                "upstream": upstream,
                "differences": differences,
            },
        )
        return 1

    _write_json(
        out_dir / "catalogue_watch_status.json",
        {
            "status": "match",
            "checked": [
                {
                    "path": registered["path"],
                    "registered_sha256": registered["sha256"],
                    "local_sha256": registered["local_sha256"],
                    "upstream_sha256": upstream["sha256"] if upstream else None,
                    "upstream_version": upstream.get("version") if upstream else None,
                    "upstream_doi": upstream.get("doi") if upstream else None,
                }
            ],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
