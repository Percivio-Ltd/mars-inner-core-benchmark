from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.shared import repo_path


SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SECTION_RE = re.compile(
    r"^(?P<marks>#{1,6})\s+R\.1A\b.*Current-Gate Execution Record",
    re.IGNORECASE,
)
MANIFEST_ENTRY_RE = re.compile(r"^(?P<digest>[0-9a-fA-F]{64})[ \t]+(?P<locator>\*?.+?)\s*$")
PIN_RE = re.compile(r"^#\s*pin\s+(?P<digest>[0-9a-fA-F]{64})\s+(?P<locator>\S+)\s*$")


class IdentityVerificationError(RuntimeError):
    pass


def _read_text(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise IdentityVerificationError(f"{label} is missing or unreadable: {path}: {exc}") from exc


def _table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _code_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def parse_identity_table(paper_path: Path) -> list[tuple[str, str]]:
    lines = _read_text(Path(paper_path), "Paper 0 identity table").splitlines()
    section_start = None
    section_level = None
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line.strip())
        if match:
            section_start = index + 1
            section_level = len(match.group("marks"))
            break
    if section_start is None or section_level is None:
        raise IdentityVerificationError(
            f"zero identity rows parsed: R.1A Current-Gate Execution Record not found in {paper_path}"
        )

    section_end = len(lines)
    for index in range(section_start, len(lines)):
        heading = re.match(r"^(#{1,6})\s+", lines[index].strip())
        if heading and len(heading.group(1)) <= section_level:
            section_end = index
            break

    header_index = None
    for index in range(section_start, section_end):
        cells = _table_cells(lines[index])
        if [cell.lower() for cell in cells] == ["label", "locator", "full sha-256"]:
            header_index = index
            break
    if header_index is None:
        raise IdentityVerificationError(
            f"zero identity rows parsed: R.1A identity table header not found in {paper_path}"
        )

    separator_index = header_index + 1
    if separator_index >= section_end:
        raise IdentityVerificationError(
            f"unparseable R.1A identity table in {paper_path}: missing separator row"
        )
    separator_cells = _table_cells(lines[separator_index])
    if len(separator_cells) != 3 or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator_cells):
        raise IdentityVerificationError(
            f"unparseable R.1A identity table separator in {paper_path}: {lines[separator_index]!r}"
        )

    pairs: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for index in range(separator_index + 1, section_end):
        raw = lines[index]
        if not raw.strip():
            break
        if not raw.lstrip().startswith("|"):
            raise IdentityVerificationError(
                f"unparseable R.1A identity row {index + 1} in {paper_path}: {raw!r}"
            )
        cells = _table_cells(raw)
        if len(cells) != 3:
            raise IdentityVerificationError(
                f"unparseable R.1A identity row {index + 1} in {paper_path}: {raw!r}"
            )
        locator = _code_cell(cells[1])
        digest = _code_cell(cells[2]).lower()
        if not locator or not SHA256_RE.fullmatch(digest):
            raise IdentityVerificationError(
                f"unparseable R.1A identity row {index + 1} in {paper_path}: "
                f"locator={locator!r}, digest={digest!r}"
            )
        previous = seen.get(locator)
        if previous is not None:
            raise IdentityVerificationError(
                f"duplicate locator in R.1A identity table: locator={locator}, "
                f"digest={digest}, previous_digest={previous}"
            )
        seen[locator] = digest
        pairs.append((locator, digest))

    if not pairs:
        raise IdentityVerificationError(f"zero identity rows parsed from {paper_path}")
    return pairs


def parse_identity_manifest(manifest_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    text = _read_text(Path(manifest_path), "CGR identity manifest")
    if not text.strip():
        raise IdentityVerificationError(f"empty CGR identity manifest: {manifest_path}")

    resident: dict[str, str] = {}
    pins: dict[str, str] = {}
    parsed = 0
    for index, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            pin = PIN_RE.fullmatch(line)
            if pin:
                locator = pin.group("locator")
                digest = pin.group("digest").lower()
                target = pins
            elif re.match(r"^#\s*pin\b", line):
                raise IdentityVerificationError(
                    f"unparseable pin line {index} in {manifest_path}: {raw!r}"
                )
            else:
                continue
        else:
            entry = MANIFEST_ENTRY_RE.fullmatch(line)
            if not entry:
                raise IdentityVerificationError(
                    f"unparseable manifest line {index} in {manifest_path}: {raw!r}"
                )
            locator = entry.group("locator").lstrip("*").strip()
            digest = entry.group("digest").lower()
            target = resident
        if not locator:
            raise IdentityVerificationError(
                f"unparseable manifest line {index} in {manifest_path}: empty locator, digest={digest}"
            )
        previous = target.get(locator)
        if previous is not None:
            raise IdentityVerificationError(
                f"duplicate manifest locator: locator={locator}, digest={digest}, "
                f"previous_digest={previous}"
            )
        target[locator] = digest
        parsed += 1

    if parsed == 0:
        raise IdentityVerificationError(f"empty CGR identity manifest: {manifest_path}")
    return resident, pins


def _sha256_file(path: Path, locator: str, expected_digest: str) -> str:
    if not path.is_file():
        raise IdentityVerificationError(
            f"resident file is missing or unreadable: locator={locator}, "
            f"digest={expected_digest}, path={path}"
        )
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise IdentityVerificationError(
            f"resident file is missing or unreadable: locator={locator}, "
            f"digest={expected_digest}, path={path}: {exc}"
        ) from exc
    return digest.hexdigest()


def verify_cgr_identity(
    paper_path: Path,
    manifest_path: Path,
    repo_root: Path,
) -> dict[str, object]:
    pairs = parse_identity_table(Path(paper_path))
    resident, pins = parse_identity_manifest(Path(manifest_path))
    all_manifest_digests = set(resident.values()) | set(pins.values())

    for locator, table_digest in pairs:
        is_s3 = locator.startswith("s3://")
        entries = pins if is_s3 else resident
        manifest_digest = entries.get(locator)
        if manifest_digest is None:
            transplant = table_digest in all_manifest_digests
            detail = "digest appears under a different locator (transplanted digest)" if transplant else "digest absent"
            raise IdentityVerificationError(
                f"locator absent from manifest: locator={locator}, digest={table_digest}; {detail}"
            )
        if manifest_digest != table_digest:
            transplant = table_digest in all_manifest_digests
            detail = "transplanted digest paired with wrong locator" if transplant else "digest mismatch"
            raise IdentityVerificationError(
                f"{detail}: locator={locator}, table_digest={table_digest}, "
                f"manifest_digest={manifest_digest}"
            )
        if is_s3:
            continue

        locator_path = Path(locator)
        path = locator_path if locator_path.is_absolute() else Path(repo_root) / locator_path
        actual_digest = _sha256_file(path, locator, table_digest)
        if actual_digest != table_digest:
            raise IdentityVerificationError(
                f"resident digest mismatch: locator={locator}, expected_digest={table_digest}, "
                f"actual_digest={actual_digest}, path={path}"
            )

    return {
        "status": "pass",
        "verified_pairs": len(pairs),
        "resident_pairs": sum(not locator.startswith("s3://") for locator, _ in pairs),
        "s3_pin_pairs": sum(locator.startswith("s3://") for locator, _ in pairs),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify locator-bound identities in the Paper 0 R.1A current-gate record."
    )
    parser.add_argument("--paper", default=str(repo_path("papers/Paper0/Paper0.md")))
    parser.add_argument(
        "--manifest",
        default=str(repo_path("history/20260725_assembly_cgr/cgr_identity_manifest.sha256")),
    )
    parser.add_argument("--repo-root", default=str(repo_path(".")))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_cgr_identity(
            Path(args.paper),
            Path(args.manifest),
            Path(args.repo_root),
        )
    except IdentityVerificationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "CGR identity verification passed: "
        f"{result['verified_pairs']} locator/digest pairs "
        f"({result['resident_pairs']} resident, {result['s3_pin_pairs']} S3 pins)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
