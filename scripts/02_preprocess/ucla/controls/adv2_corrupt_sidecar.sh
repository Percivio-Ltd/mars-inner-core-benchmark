#!/bin/bash
set -euo pipefail

readonly CONTROL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(cd -- "$CONTROL_DIR/../../../.." && pwd -P)"
readonly SOURCE="/Users/artuskg/marsquake_runs/20260801_ucla_equiv/ucla_v4/UCLA_v4/S0235b_VBB.mseed"
readonly SOURCE_SHA256="a12273552c871602813ad807cc0e44c5c9c15bf85ac40e6546fe9790afd44450"
readonly MICROMAMBA="/opt/homebrew/bin/micromamba"
readonly MARS_IC_ROOT="/Users/artuskg/micromamba"
readonly OUTDIR="${1:-$REPO_ROOT/lead_controls/adv2}"

/usr/bin/python3 - "$REPO_ROOT" "$OUTDIR" <<'PY'
import os
import sys
root, target = map(os.path.realpath, sys.argv[1:])
if os.path.commonpath((root, target)) != root:
    raise SystemExit(f"FAIL: evidence directory is outside worktree: {target}")
PY
[[ ! -e "$OUTDIR" ]] || { echo "FAIL: evidence directory exists: $OUTDIR"; exit 1; }
actual_source_sha="$(/usr/bin/shasum -a 256 "$SOURCE" | /usr/bin/awk '{print $1}')"
[[ "$actual_source_sha" == "$SOURCE_SHA256" ]] || {
  echo "FAIL: shipped sample SHA-256 mismatch: expected=$SOURCE_SHA256 actual=$actual_source_sha"
  exit 1
}

MAMBA_ROOT_PREFIX="$MARS_IC_ROOT" "$MICROMAMBA" run -n mars-ic python "$CONTROL_DIR/corrupt_sidecar_check.py" \
  --repo-root "$REPO_ROOT" \
  --source-mseed "$SOURCE" \
  --evidence-dir "$OUTDIR"
