# P0-UCLA-PROD implementation report

## Scientific state

- Question: whether the three accepted benchmark surfaces survive completion of
  the declared MPS-to-UCLA Octave chain.
- Artifact attempted: the registered S0235b runner-level positive-control output.
- Result: **CALIBRATION GATE FAIL** before a combined UCLA MiniSEED output or
  sidecar was produced. No production event was processed.
- Stop condition: reached. No repair, rerun, other control, runbook construction,
  or 26-event production command was attempted after the failure.

## Pinned implementation authority

- Worktree HEAD verified before all other actions:
  `98a2160e7c43cee9f378891d5fb149562fbd3871`.
- UCLA_v4 archive:
  `/Users/artuskg/GitRepos/MarsQuake/external/seisglitch/MATLAB_ALTERNATIVES/UCLA_v4.zip`.
- Required and observed archive SHA-256:
  `2eb91194a45e847e6ad58e94cb6f2f0ffc1f0fb838a12d40087c8f24de2dd2f7`.
- Shipped S0235b sample:
  `/Users/artuskg/marsquake_runs/20260801_ucla_equiv/ucla_v4/UCLA_v4/S0235b_VBB.mseed`,
  SHA-256 `a12273552c871602813ad807cc0e44c5c9c15bf85ac40e6546fe9790afd44450`.
- Preflight dependency check passed: `/opt/homebrew/bin/micromamba`, env
  `octave-ucla`, Octave `10.3.0`, signal `1.4.7`.

## Harness status pinned from source

The exact overall status produced when a sidecar does **not** claim
`verification_status="mps_ucla_verified"` is:

> `ucla_unverified`

Source citations in `scripts/02_preprocess/deglitch_mps_ucla.py`:

- line 31 defines `STATUS_UCLA_UNVERIFIED = "ucla_unverified"`;
- line 438 defines `sidecar_attested` as equality with
  `STATUS_MPS_UCLA_VERIFIED`;
- lines 442-443 inspect sidecar hash evidence only when that strict claim is
  present;
- lines 453-456 classify every non-strict sidecar as
  `external_ucla_command_wrote_file_unverified`, contract status
  `output_file_verified_not_algorithm_equivalence`, and overall
  `STATUS_UCLA_UNVERIFIED`.

The separately named enum
`sidecar_attested_not_independently_verified` is defined at line 33 but is
reachable at lines 449-452 only when the sidecar first claims
`mps_ucla_verified` and then lacks valid evidence. It is therefore not the
classification for a full-evidence sidecar that omits the strict claim. The
new writer was pinned to `verification_status="ucla_unverified"` and contains
a hard refusal to write `mps_ucla_verified`.

## New implementation files built before the gate

- `scripts/02_preprocess/ucla/run_ucla_octave.sh`
- `scripts/02_preprocess/ucla/ucla_driver.m`
- `scripts/02_preprocess/ucla/pause.m`
- `scripts/02_preprocess/ucla/write_sidecar.py`
- `scripts/02_preprocess/ucla/controls/pos1_fixture_reproduction.sh`
- `scripts/02_preprocess/ucla/controls/pos2_mps_byte_identity.sh`
- `scripts/02_preprocess/ucla/controls/adv1_channel_permuted.sh`
- `scripts/02_preprocess/ucla/controls/adv2_corrupt_sidecar.sh`
- control helpers under `scripts/02_preprocess/ucla/controls/`.

Shell and Python syntax checks passed before the gate. All files are new; no
existing file was edited. No canonical-checkout path was written.

## Calibration gate failure

Failing command:

```text
scripts/02_preprocess/ucla/controls/pos1_fixture_reproduction.sh /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1
```

Exit status: `1`.

Full combined stdout/stderr is retained at
`calibration/pos1/runner.log` (2,618 lines, 98,843 bytes), SHA-256
`ac4ac128963cd498398aa446b799a30ff764a2e155eefeb774b6b0fc41941435`.

Terminal failure:

```text
MKMSEED: writing file "/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1/work/ucla_mseed_parts/XB.ELYSE.02.BHU.2019.207"... done.
MKMSEED: writing file "/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1/work/ucla_mseed_parts/XB.ELYSE.02.BHV.2019.207"... done.
MKMSEED: writing file "/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1/work/ucla_mseed_parts/XB.ELYSE.02.BHW.2019.207"... done.
error: UCLA-DRIVER-FAIL: mkmseed wrote no files for BHU
error: called from
    /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/scripts/02_preprocess/ucla/ucla_driver.m at line 110 column 7
```

Cause localized from the failing implementation and output paths: the driver
passed a base ending in `.D` to `mkmseed`, but shipped `mkmseed.m` reconstructs
the filename without that data-quality component and wrote
`XB.ELYSE.02.BH?.2019.207`. The new concatenation lookup searched for the
nonexistent pattern `XB.ELYSE.02.BH?.D.*` and failed. The three generated
channel files were retained as evidence. Per the calibration instruction, this
was not patched or rerun.

Gate subconditions:

- (a) **FAIL**: combined `OUT` does not exist, so non-empty/ObsPy-readable/three
  channels at expected sample rate could not be established.
- (b) **FAIL**: the sidecar writer was never reached; no sidecar exists.
- (c) **FAIL/NOT REACHED**: `pos1_fixture_reproduction.sh` stopped on the runner
  exit before the frozen comparator ran.

## Deviations and unverified items

- **DEVIATION:** `RUNBOOK_ucla_prod.md` was not created. The calibration
  stop-and-report instruction was reached before runbook construction.
- **DEVIATION:** the implementation is not production-ready because its
  concatenation filename assumption is wrong, as demonstrated above.
- **UNVERIFIED:** combined output encoding/readability/channel count/sample
  rate, sidecar parsing/evidence, and the frozen positive comparison.
- **UNVERIFIED:** the three controls not required inside the calibration gate
  were built but not executed.
- **UNVERIFIED:** exact `run_paper0.py` production CLI and manifest-copy
  sequence were not frozen into a runbook because work stopped at the gate.
- The 26-event production pass was not run.

## Round 2

### F1 concatenation repair

The shipped `PREPmkmseed.m` establishes both sides of the filename contract:
lines 1–3 give `mkmseed` the `.D`-suffixed BHU/BHV/BHW bases, lines 4–6 call
`mkmseed` with those bases, and line 7 concatenates what the writer actually
emits with `!cat XB.* >temp.mseed`. The retained Round 1 evidence showed those
emitted names are `XB.ELYSE.02.BH?.2019.207`, without `.D`.

The minimal repair leaves the calls and U/V/W concatenation structure intact.
`scripts/02_preprocess/ucla/ucla_driver.m` lines 89–92 still pass the shipped
`.D` bases to `mkmseed`; lines 106–109 now select the writer's emitted
channel-specific namespace `XB.ELYSE.02.BH?.*`, and `sort(...)` retains
chronological lexicographic ordering for multi-day parts. The successful rerun
then found exactly one 2019.207 file for each fixture channel.

The host has `octave-ucla` under the Homebrew micromamba root and `mars-ic`
under `/Users/artuskg/micromamba`. The three controls that invoke `mars-ic`
therefore scope `MAMBA_ROOT_PREFIX=/Users/artuskg/micromamba` only to those
Python invocations; the UCLA runner continues to resolve `octave-ucla` from its
original root. This is environment selection only and does not change the
fixture, algorithm, comparator, or tolerances.

### Fresh calibration gate

The required fresh command was run exactly from the worktree:

```text
scripts/02_preprocess/ucla/controls/pos1_fixture_reproduction.sh /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2
```

It exited `0`. The retained terminal results are:

```text
MKMSEED: writing file "/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/work/ucla_mseed_parts/XB.ELYSE.02.BHU.2019.207"... done.
MKMSEED: writing file "/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/work/ucla_mseed_parts/XB.ELYSE.02.BHV.2019.207"... done.
MKMSEED: writing file "/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/work/ucla_mseed_parts/XB.ELYSE.02.BHW.2019.207"... done.
UCLA-DRIVER-PASS: rows U/V/W=43/34/36 elapsed=48.5 output=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/S0235b_ucla.mseed
UCLA-RUNNER-PASS: output=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/S0235b_ucla.mseed sidecar=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/S0235b_ucla.mseed.ucla.json parameters_sha256=98382efd2132d07f8bac0c946e1fa6c62e965c6cccf0d9152eb0055464985e1e
```

#### Gate (a) and (b): independent output and sidecar check

The independent check used the required environment spelling (with its pinned
root so the named environment resolves):

```text
MAMBA_ROOT_PREFIX=/Users/artuskg/micromamba /opt/homebrew/bin/micromamba run -n mars-ic python -c 'from pathlib import Path; import hashlib, json; from obspy import read; out=Path("/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/S0235b_ucla.mseed"); sidecar=Path(str(out)+".ucla.json"); assert out.is_file() and out.stat().st_size > 0; stream=read(str(out)); expected_ids=["XB.ELYSE.02.BHU","XB.ELYSE.02.BHV","XB.ELYSE.02.BHW"]; observed=sorted((tr.id,float(tr.stats.sampling_rate),int(tr.stats.npts)) for tr in stream); assert len(stream)==3; assert [row[0] for row in observed]==expected_ids; assert all(row[1]==20.0 for row in observed); payload=json.loads(sidecar.read_text()); required=["algorithm","parameters_sha256","expected_output_sha256","verification_status"]; assert all(key in payload for key in required); recomputed=hashlib.sha256(out.read_bytes()).hexdigest(); assert payload["verification_status"]=="ucla_unverified"; assert payload["expected_output_sha256"]==recomputed; print("OUT exists=True size={} ObsPy_readable=True trace_count={}".format(out.stat().st_size,len(stream))); [print("TRACE id={} sampling_rate={:.1f} npts={}".format(trace_id,rate,npts)) for trace_id,rate,npts in observed]; print("SIDECAR parsed=True keys={}".format(",".join(required))); print("algorithm={}".format(payload["algorithm"])); print("parameters_sha256={}".format(payload["parameters_sha256"])); print("verification_status={}".format(payload["verification_status"])); print("expected_output_sha256={}".format(payload["expected_output_sha256"])); print("independently_recomputed_sha256={}".format(recomputed)); print("PASS: independent OUT and sidecar checks")'
```

Its assertion-bearing output was:

```text
OUT exists=True size=3489792 ObsPy_readable=True trace_count=3
TRACE id=XB.ELYSE.02.BHU sampling_rate=20.0 npts=142840
TRACE id=XB.ELYSE.02.BHV sampling_rate=20.0 npts=142840
TRACE id=XB.ELYSE.02.BHW sampling_rate=20.0 npts=142840
SIDECAR parsed=True keys=algorithm,parameters_sha256,expected_output_sha256,verification_status
algorithm=UCLA_v4 MAIN2SPS+MAIN20SPSJuly26, octave-10.3.0, signal-1.4.7
parameters_sha256=98382efd2132d07f8bac0c946e1fa6c62e965c6cccf0d9152eb0055464985e1e
verification_status=ucla_unverified
expected_output_sha256=37d8ceead3134d3b548fa1d7b23d025411bb79bdda6b0962cc856a3669a9cb9f
independently_recomputed_sha256=37d8ceead3134d3b548fa1d7b23d025411bb79bdda6b0962cc856a3669a9cb9f
PASS: independent OUT and sidecar checks
```

ObsPy additionally emitted its installed `pkg_resources` deprecation warning
and two `InternalMSEEDWarning` messages for fractional-second fields at byte
offsets 954368 and 2138112; neither prevented parsing or altered the asserted
trace inventory. Gate (a) is **PASS** and gate (b) is **PASS**. The new
`parameters_sha256` is
`98382efd2132d07f8bac0c946e1fa6c62e965c6cccf0d9152eb0055464985e1e`;
it changed because `ucla_driver.m` is in the hashed parameter set.

#### Gate (c): frozen comparator

The comparator output was:

```text
channel=U count=43/43 R_ch=0.088590 max_abs_delta=174.523908
channel=V count=34/34 R_ch=0.042927 max_abs_delta=277.638789
channel=W count=36/37 R_ch=0.083265 max_abs_delta=223.689586
classification=DIVERGENT-MINOR
PASS: evidence=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/comparison.json
PASS: pos1_fixture_reproduction output=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/S0235b_ucla.mseed sidecar=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/S0235b_ucla.mseed.ucla.json evidence=/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/pos1_r2/comparison.json
```

Observed counts are exactly 43/34/36. Every ratio is at or below the frozen 0.1
bound. Gate (c) and the overall Round 2 calibration gate are **PASS**.

### Round 2 deviations and unverified items

- **DEVIATION:** none from the Round 2 requested scientific path or frozen
  comparison rule.
- **UNVERIFIED:** the lead-only `adv1_channel_permuted.sh`,
  `adv2_corrupt_sidecar.sh`, and post-production
  `pos2_mps_byte_identity.sh` controls have not been executed in this fix
  round. Their exact execution order and paths are pinned in
  `RUNBOOK_ucla_prod.md`.
- **UNVERIFIED:** the 26-event UCLA production result and the three registered
  Paper 0 surface comparisons remain pending lead execution. The production
  pass was not run, as required.
- The failed Round 1 evidence directory `calibration/pos1` was left untouched.

## Round 3

### Scientific state and stop

Amendment 1 asks whether the three registered Paper 0 surfaces survive UCLA-on-raw
on the frozen 19-event stack, compared with a subset-matched MPS stack. The bounded
implementation produced an explicit identity pre-stage, a verbatim 22-row subset
table, and targeted tests. Calibration gate (i) passed. Calibration gate (ii)
failed before UCLA execution because the accepted runner rejected the temporary
calibration output root as outside the isolated worktree. The binding
STOP-AND-REPORT condition therefore stopped Round 3 without a retry, without the
post-change existing-suite run, and without authoring `RUNBOOK_ucla_raw.md`.

### Full harness and orchestrator diff

```diff
diff --git a/scripts/02_preprocess/deglitch_mps_ucla.py b/scripts/02_preprocess/deglitch_mps_ucla.py
index 8c46d6c1..2b22245a 100644
--- a/scripts/02_preprocess/deglitch_mps_ucla.py
+++ b/scripts/02_preprocess/deglitch_mps_ucla.py
@@ -26,6 +26,7 @@ logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
 logger = logging.getLogger(__name__)
 
 MPS_STATUS_BLOCKED = "blocked_missing_seisglitch"
+MPS_STATUS_IDENTITY = "identity_passthrough"
 UCLA_STATUS_BLOCKED = "blocked_missing_ucla_runner"
 STATUS_SUCCEEDED_MPS_ONLY = "succeeded_mps_only"
 STATUS_UCLA_UNVERIFIED = "ucla_unverified"
@@ -493,6 +494,9 @@ def run_deglitch_event(
     metadata_path = output_path.with_suffix(".deglitch.json")
     work_event_dir = work_dir / event_id
     metadata = _metadata_base(event_id, input_path, output_path, metadata_path, work_event_dir)
+    identity_passthrough = seisglitch_command == "identity"
+    if identity_passthrough:
+        metadata["methods_requested"] = ["UCLA"]
     command_env = _build_command_env(seisglitch_pythonpath)
     if output_path.resolve() == input_path.resolve():
         metadata["overall_status"] = "failed"
@@ -521,6 +525,18 @@ def run_deglitch_event(
         _write_json(metadata_path, metadata)
         return metadata
 
+    if identity_passthrough:
+        output_path.parent.mkdir(parents=True, exist_ok=True)
+        work_event_dir.mkdir(parents=True, exist_ok=True)
+        shutil.copyfile(input_path, output_path)
+        metadata["mps"] = {"status": MPS_STATUS_IDENTITY}
+        metadata["samples_modified"] = False
+        _run_ucla_if_configured(metadata, ucla_command, output_path, work_event_dir, runner)
+        if output_path.exists():
+            metadata["samples_modified"] = _streams_differ(input_path, output_path)
+        _write_json(metadata_path, metadata)
+        return metadata
+
     work_event_dir.mkdir(parents=True, exist_ok=True)
     working_input = work_event_dir / input_path.name
     if working_input.resolve() != input_path.resolve():
@@ -629,7 +645,7 @@ def build_arg_parser() -> argparse.ArgumentParser:
     parser.add_argument(
         "--seisglitch-command",
         default="auto",
-        help="Command for SEISglitch/MPS, or 'auto' to use PATH, or 'none' to write blocked metadata.",
+        help="Command for SEISglitch/MPS, 'identity' for byte-verbatim passthrough, 'auto' to use PATH, or 'none' to write blocked metadata.",
     )
     parser.add_argument(
         "--seisglitch-pythonpath",
@@ -666,6 +682,7 @@ def run_all(
     allowed_statuses: set[str] | Sequence[str] | None = None,
 ) -> int:
     allowed = validate_deglitch_statuses(allowed_statuses)
+    methods_requested = ["UCLA"] if seisglitch_command == "identity" else list(METHODS_REQUESTED)
     files = sorted(Path(in_dir).glob("*.mseed"))
     if not files:
         raise FileNotFoundError(f"No raw MiniSEED inputs found in {in_dir}")
@@ -676,7 +693,7 @@ def run_all(
         {
             "created_at": _utc_now(),
             "run_status": "in_progress",
-            "methods_requested": list(METHODS_REQUESTED),
+            "methods_requested": methods_requested,
             "allowed_statuses": sorted(allowed),
             "expected_event_ids": expected_event_ids,
             "status_counts": {},
@@ -711,7 +728,7 @@ def run_all(
     summary = {
         "created_at": _utc_now(),
         "run_status": "complete",
-        "methods_requested": list(METHODS_REQUESTED),
+        "methods_requested": methods_requested,
         "allowed_statuses": sorted(allowed),
         "expected_event_ids": expected_event_ids,
         "status_counts": dict(sorted(status_counts.items())),
diff --git a/scripts/run_paper0.py b/scripts/run_paper0.py
index f67e3c8b..30e2d15d 100644
--- a/scripts/run_paper0.py
+++ b/scripts/run_paper0.py
@@ -391,6 +391,8 @@ def _bootstrap_command_args(args: argparse.Namespace, *, include_jitter: bool =
     fidelity_level = str(args.bootstrap_fidelity_level)
     n_bootstrap = str(n_bootstrap_for_level(fidelity_level))
     command = [
+        "--table",
+        args.event_table,
         "--mode",
         "paperfaith",
         "--variant",
@@ -487,6 +489,8 @@ def _command_tokens(command: str | None) -> list[str]:
 
 
 def _check_seisglitch_resolution(args: argparse.Namespace, findings: list[dict[str, Any]]) -> None:
+    if args.seisglitch_command == "identity":
+        return
     if args.seisglitch_pythonpath:
         pythonpath = Path(args.seisglitch_pythonpath)
         if not pythonpath.exists():
@@ -654,6 +658,12 @@ def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
 def _validation_command(args: argparse.Namespace, label: str, *, incremental_check: str | None = None, aggregate_only: bool = False) -> dict[str, Any]:
     cmd = [
         "scripts/07_validation/generate_validation_report.py",
+        "--event-table",
+        args.event_table,
+        "--catalog",
+        args.mqs_catalog,
+        "--raw-dir",
+        args.raw_dir,
         "--mode",
         "current-run",
         "--out-dir",
@@ -672,6 +682,8 @@ def build_stage_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
     allowed_deglitch_statuses = validate_deglitch_statuses(args.allow_deglitch_status)
     deglitch_cmd = [
         "scripts/02_preprocess/deglitch_mps_ucla.py",
+        "--in-dir",
+        args.raw_dir,
         "--seisglitch-command",
         args.seisglitch_command,
         "--inventory-file",
@@ -702,13 +714,20 @@ def build_stage_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
         _command("polarization", "scripts/02_preprocess/polarization_filter.py"),
         _command("fdpa", "scripts/02_preprocess/fdpa.py"),
         _command("glitch_flags", "scripts/02_preprocess/glitch_flagging.py"),
-        _command("align", "scripts/02_preprocess/align_and_cut.py"),
+        _command(
+            "align",
+            "scripts/02_preprocess/align_and_cut.py",
+            "--event-table",
+            args.event_table,
+            "--catalog",
+            args.mqs_catalog,
+        ),
         _command("normalize", "scripts/02_preprocess/normalize_and_envelope.py"),
         _validation_command(args, "validation_inventory", incremental_check="inventory"),
         _validation_command(args, "validation_preprocessing", incremental_check="preprocessing"),
         _validation_command(args, "validation_alignment", incremental_check="alignment"),
         _validation_command(args, "validation_model", incremental_check="model"),
-        _command("vespagrams", "scripts/03_vespagram/run_vespagrams.py"),
+        _command("vespagrams", "scripts/03_vespagram/run_vespagrams.py", "--event-table", args.event_table),
         _validation_command(args, "validation_benchmark", incremental_check="benchmark"),
         _command("detect_peaks", *detect_cmd),
         _command("bootstrap_type1", "scripts/04_bootstrap/bootstrap_type1.py", *_bootstrap_command_args(args)),
```

`run_paper0.py` required changes. Identity was already forwarded literally by
the stage builder, and `ucla_unverified` was already in the unchanged status
vocabulary. The added preflight exception at lines 491–493 prevents the
built-in identity value from being resolved as an external executable. No
attestation or status-gating logic changed: lines 907–940 derive
`attestation_level` from observed statuses, while lines 961–968 accept any
non-empty observed status set contained in the explicit allow-list. The added
argument forwarding at lines 390–420 and 658–735 is also required: before this
diff the CLI checked `--event-table` but downstream alignment, vespagram,
bootstrap, and validation silently used their default 26-row table. Defaults
still resolve to the same pre-existing paths.

### Frozen event membership and loader proof

`manifest/event_table_ucla22.csv` has 22 rows and is byte-for-byte the original
table after dropping only S0784a, S1015f, S1197a, and S1222a. It contains 19
`set=vespagram` rows and the original 3 `set=validation` rows.

```python
# scripts/shared.py:137-143: every row and its literal set field is retained.
reader = csv.DictReader(f)
for row in reader:
    rows.append(row)

# scripts/03_vespagram/run_vespagrams.py:71-74: only stack rows enter a vespagram.
for row in rows:
    if row["set"] != "vespagram":
        continue

# scripts/04_bootstrap/bootstrap_type1.py:277-280: bootstrap uses the same split.
for row in rows:
    if row.get("set") != "vespagram":
        continue

# scripts/07_validation/generate_validation_report.py:256,262-265,362-366:
# validation inventories every row and records its reserved set unchanged.
rows = load_event_table(event_table)
for row in rows:
    event_id = row["event_id"]
inventory.append({"event_id": event_id, "set": row["set"], ...})
```

The validation alignment surface independently selects only `set=vespagram`
at `generate_validation_report.py:479-481`, so the three validation-reserved
rows are processed and inventoried but never enter a stack.

### Tests and calibration gates

- Baseline existing suites:
  `tests/test_preprocess_contracts.py tests/test_pipeline_invariants.py
  tests/test_paper0_input_audit.py` — **98 passed, 0 failed**, 15 warnings.
  The preceding bare `pytest` attempt executed no tests (`pytest` absent from
  PATH, exit 127); the declared mars-ic interpreter produced the counts above.
- New targeted file `tests/test_ucla_raw_identity.py` — **4 passed, 0 failed**,
  1 warning. It covers byte identity/no MPS method claim,
  identity+fake-UCLA=`ucla_unverified`, the unchanged non-identity detect path,
  and orchestrator identity/subset argument forwarding.
- Post-diff existing suites — **not run** because gate (ii)'s STOP condition
  fired. Consequently the required identical-or-better after count is not
  established.
- Gate (i) — **PASS**. Input and identity output SHA-256 are both
  `3ecde9902877ddd77cc4ecd4858cf0c85815744af80cf954acc3e85d8ea7ab89`;
  bytes compare equal; metadata records `methods_requested=["UCLA"]`,
  `mps.status=identity_passthrough`, and terminal
  `overall_status=succeeded_mps_only`.
- Gate (ii) — **FAIL**. The one invocation recorded return code 1 and
  `overall_status=succeeded_mps_only`; runner stderr was:
  `UCLA-RUNNER-FAIL: write target is outside the isolated worktree:
  /private/tmp/marsquake_ucla_raw_round3.RHG6Si/gate_ii/work/S0235b/S0235b_ucla.mseed`.
  No UCLA output/census byte comparison was reached. Evidence:
  `/tmp/marsquake_ucla_raw_round3.RHG6Si/gate_ii/deglitched/S0235b.deglitch.json`.
- Gate (iii) — **FAIL (incomplete)**. The new targeted file passed, but the
  post-diff existing suites were prohibited by the gate-(ii) stop.

`git diff --check` passed for the four implemented paths checked before the
stop. `calibration/` and `lead_controls/` were not modified.

### Deviations and unverified items

- **DEVIATION:** gate (ii) was invoked with outputs under `/tmp`; the accepted
  runner's isolation contract permits writes only under the isolated worktree.
  The invocation therefore failed at the runner boundary before UCLA rather
  than testing the intended end-to-end scientific control. The no-retry stop
  condition was honored.
- **UNVERIFIED:** UCLA output identity to the accepted S0235b census product,
  post-diff existing-suite regression count, and full calibration gate (iii).
- **UNVERIFIED:** `RUNBOOK_ucla_raw.md` was not created after the stop. The lead
  commands, adv-A, both 22-event passes, pos-A, pos-B, and all readouts were not
  run or inspected.
- **UNVERIFIED:** the implementation and subset-table artifacts remain in the
  worktree for lead adjudication; no claim-bearing surface was produced.

## Round 4

### Scientific state

Amendment 1 asks whether the three registered Paper 0 peak surfaces change
between UCLA-on-raw and a subset-matched MPS-only preparation. This fix round
produced the missing worktree-local S0235b calibration artifact and the lead
runbook; it did not execute either 22-event pass or inspect a registered
surface.

### F1 — calibration gate (ii)

The real one-file lane was run with this exact command from the worktree:

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python scripts/02_preprocess/deglitch_mps_ucla.py --in-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/identity_gate_r4/input --out-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/identity_gate_r4/output --work-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/calibration/identity_gate_r4/work --inventory-file /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/inputs/XB_ELYSE_response_inventory.xml --seisglitch-command identity --ucla-command '/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/scripts/02_preprocess/ucla/run_ucla_octave.sh {input} {output} {work_dir}' --allow-status ucla_unverified
```

It exited 0. `calibration/identity_gate_r4/output/deglitch_run_summary.json`
records `run_status="complete"`, one event, and
`status_counts={"ucla_unverified": 1}`. The per-event terminal is
`overall_status="ucla_unverified"`.

```text
e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db  calibration/identity_gate_r4/output/S0235b.mseed
e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db  lead_controls/raw_census/S0235b/S0235b_raw_ucla.mseed
```

F1 is **PASS**: the production-shaped UCLA product is byte-identical to the
lead control, and every write target was inside the isolated worktree.

### F2 — post-diff suites

The combined mars-ic pytest invocation collected 102 tests and finished with
**102 passed, 0 failed, 15 warnings** in 4.03 seconds. The accepted existing
suites account for **98 passed**, exactly the Round 3 baseline; the targeted
`tests/test_ucla_raw_identity.py` file accounts for **4 passed**. Thus the
required existing-suite count is not lower than 98.

### F3 — lead runbook and rationale

`RUNBOOK_ucla_raw.md` now pins staged membership and digest verification, both
production commands, archival/hash boundaries, adv-A, pos-A, pos-B, the stage
and gate inventory, and the exact same-cell readout fields. The MPS allow-list
spelling is independently fixed by immutable HEAD evidence: HEAD
`scripts/run_paper0.py:54` makes `mps_ucla_verified` the default,
`:1260-1261` injects it only when no explicit list is supplied, and `:612`
downgrades an explicit non-default unverified list to a warning. The checked-in
accepted manifest records all 26 events as `succeeded_mps_only`,
`attestation_level="succeeded_mps_only"`, and
`accepted_partial_lane_by_design=true`; therefore the accepted MPS-only lane
must have used the explicit literal `succeeded_mps_only`.

The same 22-row event table and `data/raw_ucla22/` directory are pinned in both
passes. Current worktree `scripts/run_paper0.py:390-420` and `:658-735`
propagate the subset to bootstraps, validation, deglitch, alignment, and
vespagrams; `:681-701` propagates each sole allow-status to deglitch and
rotation; `:961-968` implements status-subset acceptance; and `:1043-1046`
applies it to incremental validation. The registered readout mapping is fixed
by `scripts/03_vespagram/detect_peaks.py:313-354`, `:401-407`, and `:552-665`,
and by `scripts/07_validation/generate_validation_report.py:36-66`, `:543-578`,
and `:633-637`.

### Round 4 deviations and unverified items

- **DEVIATION:** none. The Round 3 invocation error was corrected without a
  code change, and F1/F2 met their required outcomes.
- **UNVERIFIED:** adv-A remains lead-only and was not run in this fix round.
- **UNVERIFIED:** the UCLA-on-raw and subset-matched MPS 22-event passes, their
  archive manifests, and their production pos-A/pos-B controls remain pending
  lead execution.
- **UNVERIFIED:** no registered global PKiKP, published PKiKP target-box, or
  PKKP endpoint readout was executed or inspected; the comparison remains
  pending the two lead-run product trees.
- No code, accepted manifest/table/test, attempt-1 output, or read-only
  canonical-checkout path was modified in Round 4.
