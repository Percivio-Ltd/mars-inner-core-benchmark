#!/bin/bash
set -euo pipefail

readonly CONTROL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(cd -- "$CONTROL_DIR/../../../.." && pwd -P)"
readonly RUNNER="$REPO_ROOT/scripts/02_preprocess/ucla/run_ucla_octave.sh"
readonly SOURCE="/Users/artuskg/marsquake_runs/20260801_ucla_equiv/ucla_v4/UCLA_v4/S0235b_VBB.mseed"
readonly SOURCE_SHA256="a12273552c871602813ad807cc0e44c5c9c15bf85ac40e6546fe9790afd44450"
readonly REF_DC="/Users/artuskg/marsquake_runs/20260801_ucla_equiv/refs/dc.mat"
readonly REF_AA="/Users/artuskg/marsquake_runs/20260801_ucla_equiv/refs/aaout3.mat"
readonly MICROMAMBA="/opt/homebrew/bin/micromamba"
readonly MARS_IC_ROOT="/Users/artuskg/micromamba"
readonly OUTDIR="${1:-$REPO_ROOT/lead_controls/adv1}"

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

/bin/mkdir -p "$OUTDIR"
MAMBA_ROOT_PREFIX="$MARS_IC_ROOT" "$MICROMAMBA" run -n mars-ic python "$CONTROL_DIR/permute_s0235.py" \
  "$SOURCE" "$OUTDIR/S0235b_channel_permuted.mseed" 2>&1 | /usr/bin/tee "$OUTDIR/permutation.log"
"$RUNNER" "$OUTDIR/S0235b_channel_permuted.mseed" \
  "$OUTDIR/S0235b_channel_permuted_ucla.mseed" "$OUTDIR/work" 2>&1 | /usr/bin/tee "$OUTDIR/runner.log"
MAMBA_ROOT_PREFIX="$MARS_IC_ROOT" "$MICROMAMBA" run -n mars-ic python "$CONTROL_DIR/compare_fixture.py" \
  --mode adverse \
  --run-mat "$OUTDIR/work/ucla_results.mat" \
  --reference-dc "$REF_DC" \
  --reference-aa "$REF_AA" \
  --evidence-json "$OUTDIR/comparison.json" 2>&1 | /usr/bin/tee "$OUTDIR/comparison.log"

echo "PASS: adv1_channel_permuted detected frozen-rule divergence evidence=$OUTDIR/comparison.json"
