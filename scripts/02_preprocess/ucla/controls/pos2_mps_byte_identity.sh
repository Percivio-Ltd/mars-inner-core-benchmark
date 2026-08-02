#!/bin/bash
set -euo pipefail

if [[ "$#" -lt 2 || "$#" -gt 3 ]]; then
  echo "usage: $0 ISOLATED_MPS_PRODUCT CANONICAL_ACCEPTED_MPS_PRODUCT [EVIDENCE_DIR]" >&2
  exit 64
fi

readonly CONTROL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(cd -- "$CONTROL_DIR/../../../.." && pwd -P)"
readonly ISOLATED="$1"
readonly CANONICAL="$2"
readonly EVIDENCE_DIR="${3:-$REPO_ROOT/lead_controls/pos2}"

/usr/bin/python3 - "$REPO_ROOT" "$EVIDENCE_DIR" <<'PY'
import os
import sys
root, target = map(os.path.realpath, sys.argv[1:])
if os.path.commonpath((root, target)) != root:
    raise SystemExit(f"FAIL: evidence directory is outside worktree: {target}")
PY
[[ -f "$ISOLATED" ]] || { echo "FAIL: isolated MPS product missing: $ISOLATED"; exit 1; }
[[ -f "$CANONICAL" ]] || { echo "FAIL: canonical accepted MPS product missing: $CANONICAL"; exit 1; }
[[ ! -e "$EVIDENCE_DIR" ]] || { echo "FAIL: evidence directory exists: $EVIDENCE_DIR"; exit 1; }
/bin/mkdir -p "$EVIDENCE_DIR"

isolated_sha="$(/usr/bin/shasum -a 256 "$ISOLATED" | /usr/bin/awk '{print $1}')"
canonical_sha="$(/usr/bin/shasum -a 256 "$CANONICAL" | /usr/bin/awk '{print $1}')"
{
  echo "isolated_path=$ISOLATED"
  echo "isolated_sha256=$isolated_sha"
  echo "canonical_path=$CANONICAL"
  echo "canonical_sha256=$canonical_sha"
} > "$EVIDENCE_DIR/sha256.txt"

if [[ "$isolated_sha" != "$canonical_sha" ]]; then
  echo "FAIL: pos2_mps_byte_identity hashes differ evidence=$EVIDENCE_DIR/sha256.txt"
  exit 1
fi
echo "PASS: pos2_mps_byte_identity sha256=$isolated_sha evidence=$EVIDENCE_DIR/sha256.txt"
