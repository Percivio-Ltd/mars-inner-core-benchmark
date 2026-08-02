#!/usr/bin/python3
"""Hash frozen UCLA inputs and write the non-strict production sidecar."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ALGORITHM = "UCLA_v4 MAIN2SPS+MAIN20SPSJuly26, octave-10.3.0, signal-1.4.7"
STRICT_STATUS = "mps_ucla_verified"
NON_STRICT_STATUS = "ucla_unverified"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parameters_hash(entries: list[str]) -> str:
    parsed: list[tuple[str, Path]] = []
    for entry in entries:
        if "=" not in entry:
            raise SystemExit(f"entry must be LABEL=PATH: {entry}")
        label, raw_path = entry.split("=", 1)
        path = Path(raw_path)
        if not label or not path.is_file():
            raise SystemExit(f"missing parameter input {label}: {path}")
        parsed.append((label, path))
    labels = [label for label, _ in parsed]
    if len(labels) != len(set(labels)):
        raise SystemExit("parameter input labels must be unique")
    digest = hashlib.sha256()
    for label, path in sorted(parsed):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
        digest.update(b"\n")
    return digest.hexdigest()


def write_sidecar(output: Path, parameters_sha256: str, verification_status: str) -> None:
    if verification_status == STRICT_STATUS:
        raise SystemExit("strict mps_ucla_verified attestation is reserved and forbidden")
    if verification_status != NON_STRICT_STATUS:
        raise SystemExit(f"verification_status must be {NON_STRICT_STATUS}")
    if not output.is_file() or output.stat().st_size == 0:
        raise SystemExit(f"output is missing or empty: {output}")
    if len(parameters_sha256) != 64:
        raise SystemExit("parameters_sha256 must be a 64-character SHA-256 digest")
    sidecar = Path(str(output) + ".ucla.json")
    if sidecar.exists():
        raise SystemExit(f"refusing to overwrite sidecar: {sidecar}")
    payload = {
        "algorithm": ALGORITHM,
        "expected_output_sha256": sha256_file(output),
        "parameters_sha256": parameters_sha256,
        "verification_status": verification_status,
    }
    temporary = sidecar.with_name(sidecar.name + ".partial")
    if temporary.exists():
        raise SystemExit(f"refusing to overwrite temporary sidecar: {temporary}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, sidecar)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    hash_parser = subparsers.add_parser("hash")
    hash_parser.add_argument("--entry", action="append", required=True)
    write_parser = subparsers.add_parser("write")
    write_parser.add_argument("--output", type=Path, required=True)
    write_parser.add_argument("--parameters-sha256", required=True)
    write_parser.add_argument("--verification-status", required=True)
    args = parser.parse_args()
    if args.command == "hash":
        print(parameters_hash(args.entry))
    else:
        write_sidecar(args.output, args.parameters_sha256, args.verification_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
