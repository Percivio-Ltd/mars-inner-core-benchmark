#!/bin/bash
set -euo pipefail

if [[ "$#" -ne 3 ]]; then
  echo "usage: $0 IN OUT WORKDIR" >&2
  exit 64
fi

readonly IN="$1"
readonly OUT="$2"
readonly WORKDIR="$3"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly WORKTREE_ROOT="$(cd -- "$SCRIPT_DIR/../../.." && pwd -P)"
readonly CANONICAL_ROOT="/Users/artuskg/GitRepos/MarsQuake"
readonly UCLA_ARCHIVE="$CANONICAL_ROOT/external/seisglitch/MATLAB_ALTERNATIVES/UCLA_v4.zip"
readonly UCLA_ARCHIVE_SHA256="2eb91194a45e847e6ad58e94cb6f2f0ffc1f0fb838a12d40087c8f24de2dd2f7"
readonly MICROMAMBA="/opt/homebrew/bin/micromamba"
readonly PYTHON="/usr/bin/python3"

fail() {
  echo "UCLA-RUNNER-FAIL: $*" >&2
  exit 1
}

[[ -x "$MICROMAMBA" ]] || fail "missing micromamba executable: $MICROMAMBA"
[[ -f "$UCLA_ARCHIVE" ]] || fail "missing pinned UCLA_v4 archive: $UCLA_ARCHIVE"
[[ -s "$IN" ]] || fail "input is missing or empty: $IN"

for target in "$OUT" "$WORKDIR"; do
  "$PYTHON" - "$WORKTREE_ROOT" "$CANONICAL_ROOT" "$target" <<'PY' || exit 1
import os
import sys

worktree, canonical, target = map(os.path.realpath, sys.argv[1:])
if os.path.commonpath((worktree, target)) != worktree:
    raise SystemExit(f"UCLA-RUNNER-FAIL: write target is outside the isolated worktree: {target}")
if os.path.commonpath((canonical, target)) == canonical:
    raise SystemExit(f"UCLA-RUNNER-FAIL: canonical-checkout write target refused: {target}")
PY
done

actual_archive_sha256="$(/usr/bin/shasum -a 256 "$UCLA_ARCHIVE" | /usr/bin/awk '{print $1}')"
[[ "$actual_archive_sha256" == "$UCLA_ARCHIVE_SHA256" ]] || \
  fail "UCLA_v4 archive SHA-256 mismatch: expected $UCLA_ARCHIVE_SHA256, got $actual_archive_sha256"

[[ ! -e "$OUT" ]] || fail "refusing to overwrite output: $OUT"
[[ ! -e "$OUT.ucla.json" ]] || fail "refusing to overwrite sidecar: $OUT.ucla.json"
/bin/mkdir -p "$WORKDIR" "$(/usr/bin/dirname "$OUT")"

readonly RUNTIME_DIR="$WORKDIR/ucla_runtime"
[[ ! -e "$RUNTIME_DIR" ]] || fail "runtime directory already exists: $RUNTIME_DIR"
/bin/mkdir "$RUNTIME_DIR"
/usr/bin/unzip -q "$UCLA_ARCHIVE" -d "$RUNTIME_DIR"
readonly ARCHIVE_DIR="$RUNTIME_DIR/UCLA_v4"
[[ -d "$ARCHIVE_DIR" ]] || fail "archive did not extract UCLA_v4 directory"

parameter_entries=(
  "fixture/Conservative.mat=$ARCHIVE_DIR/Conservative.mat"
  "fixture/NLIMspike.mat=$ARCHIVE_DIR/NLIMspike.mat"
  "fixture/Nlevel.mat=$ARCHIVE_DIR/Nlevel.mat"
  "fixture/aaout3.mat=$ARCHIVE_DIR/aaout3.mat"
  "fixture/cclim.mat=$ARCHIVE_DIR/cclim.mat"
  "fixture/cclim2.mat=$ARCHIVE_DIR/cclim2.mat"
  "fixture/dc.mat=$ARCHIVE_DIR/dc.mat"
  "fixture/fetch.mat=$ARCHIVE_DIR/fetch.mat"
  "fixture/green20sps.mat=$ARCHIVE_DIR/green20sps.mat"
  "fixture/green2sps.mat=$ARCHIVE_DIR/green2sps.mat"
  "fixture/greenspike.mat=$ARCHIVE_DIR/greenspike.mat"
  "driver/pause.m=$SCRIPT_DIR/pause.m"
  "driver/run_ucla_octave.sh=$SCRIPT_DIR/run_ucla_octave.sh"
  "driver/ucla_driver.m=$SCRIPT_DIR/ucla_driver.m"
  "driver/write_sidecar.py=$SCRIPT_DIR/write_sidecar.py"
)

hash_args=()
for entry in "${parameter_entries[@]}"; do
  hash_args+=(--entry "$entry")
done
parameters_sha256="$($PYTHON "$SCRIPT_DIR/write_sidecar.py" hash "${hash_args[@]}")"

export UCLA_INPUT_PATH="$IN"
export UCLA_OUTPUT_PATH="$OUT"
export UCLA_WORK_DIR="$WORKDIR"
export UCLA_ARCHIVE_DIR="$ARCHIVE_DIR"
export UCLA_DRIVER_DIR="$SCRIPT_DIR"
# Shipped UCLA code opens figures; without a controlling TTY the Octave/gnuplot
# handshake deadlocks. Pin gnuplot to the TTY-independent dumb terminal.
export GNUTERM="dumb"
export GNUPLOT_DEFAULT_GTERM="dumb"

"$MICROMAMBA" run -n octave-ucla octave --no-gui --norc "$SCRIPT_DIR/ucla_driver.m"
[[ -s "$OUT" ]] || fail "Octave completed without a non-empty output: $OUT"

"$PYTHON" "$SCRIPT_DIR/write_sidecar.py" write \
  --output "$OUT" \
  --parameters-sha256 "$parameters_sha256" \
  --verification-status "ucla_unverified"

echo "UCLA-RUNNER-PASS: output=$OUT sidecar=$OUT.ucla.json parameters_sha256=$parameters_sha256"
