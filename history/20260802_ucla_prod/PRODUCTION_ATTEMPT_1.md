# P0-UCLA-PROD — production attempt 1: chained lane inexecutable (STOP-AND-REPORT)

Date: 2026-08-02. Card: `docs/research_pipeline.md` § P0-UCLA-PROD (registered
2026-08-02, commit `98a2160e`). Run directory:
`/Users/artuskg/marsquake_runs/20260802_ucla_prod/` (isolated worktree
`worktree/` at `98a2160e`, branch `wt/20260802-ucla-prod`).

## Scientific state

- Question: do the three accepted benchmark surfaces survive UCLA-chained
  deglitching (UCLA on MPS output per the harness contract)?
- Result of attempt 1: **the registered chained lane is empirically
  inexecutable with shipped UCLA_v4.** The production pass ran once and the
  all-or-nothing gate failed the run by design after the deglitch stage:
  24 of 26 events could not complete the UCLA step. No mixed lane was
  accepted; no vespagram, peak, or surface output was produced or inspected.
  Outcome-blindness is intact: the blocker is a software crash census, not a
  scientific readout.
- The canonical checkout, accepted manifest, and canonical `data/deglitched/`
  were never written. The failed run manifest exists only inside the worktree
  (`worktree/results/validation/paper0_run_manifest.json`,
  `status=failed_validation_determined`, `failed_stage=deglitch`,
  `paper_ready=false`).

## Implementation and controls (all registered controls PASS)

Implementation per the card: Codex round 1 built the runner
(`scripts/02_preprocess/ucla/run_ucla_octave.sh`), Octave driver, sidecar
writer, and four control scripts, and stopped honestly at the calibration
gate on a concatenation-glob defect; the single-P1 fix round repaired it
anchored on shipped `PREPmkmseed.m` and passed the gate. Lead line-by-line
review both rounds; no repo file modified; the attested-not-verified enum was
pinned from source as `ucla_unverified` (`deglitch_mps_ucla.py` lines 438,
453-456) and the sidecar writer hard-refuses `mps_ucla_verified`.

Lead-executed controls (evidence under `worktree/lead_controls/`):

| Control | Outcome | Evidence |
| --- | --- | --- |
| adv1 channel-permuted S0235b | PASS — counts 36/42/34 vs 43/34/37, every port-noise ratio ≈ 0.997–0.999, classified NOT-EQUIVALENT | `lead_controls/adv1/comparison.json` |
| adv2 corrupt `expected_output_sha256` | PASS — mismatch detected, overall `ucla_unverified`, no accepted status reachable | `lead_controls/adv2/classification.json` |
| pos1 fixture reproduction (lead rerun) | PASS — 43/34/36, ratios 0.089/0.043/0.083 ≤ 0.1, DIVERGENT-MINOR, identical to the implementation gate run (deterministic) | `lead_controls/pos1/comparison.json` |
| Raw staging | PASS 27/27 — 26 event files + MQS catalog SHA-256-verified against `manifest/data_manifest.json` on source and destination; inventory pin `34e7405e…` identical in canonical and worktree | shell transcript in session record |
| pos2 MPS byte-identity | NOT RUN — registered post-production; production did not complete | — |

## Production pass and failure mechanism

Launched 2026-08-02 ~05:19 UTC from the worktree as one finite observed
command (exact RUNBOOK invocation; sole allowed status
`--allow-deglitch-status ucla_unverified`). Exited 2 at ~05:27 UTC:

> strict deglitch validation requires observed statuses to be in the declared
> allow-list (ucla_unverified); observed statuses: succeeded_mps_only=24,
> ucla_unverified=2

Fresh deglitch summary: `worktree/data/deglitched/deglitch_run_summary.json`,
SHA-256 `3817409228c7bf419537c62916c4cbb49f739e6da3dcfed6da9ef653a01ef984`.

Per-event census (from the per-event `*.deglitch.json` records; UCLA was
invoked for every event and returned nonzero for 24):

| MPS state | Events | UCLA outcome |
| --- | ---: | --- |
| `succeeded` (MPS removed glitches) | 22 | crash `error: I2(1): out of bound 0 (dimensions are 1x0)` — call chain `MAIN2SPS:60 → stalta:33 → QuickClean:4` |
| `succeeded_no_glitches` (MPS removed nothing) | 2 (S1022a, S1102a) | UCLA completed; status `ucla_unverified` |
| `succeeded_no_glitches` | 2 (S1197a, S1222a) | crash `error: aa(_,2): out of bound 0 (dimensions are 0x0)` (second unguarded empty-index site) |

Interpretation: shipped UCLA_v4's detection path indexes its first STA/LTA
trigger (`I2(1)`) and its glitch list (`aa`) without zero-detection guards.
MPS-cleaned input leaves the detector with nothing to find, so the chained
configuration crashes on exactly the events MPS actually cleaned (22/22
correlation). Even on the four events MPS left untouched — the closest proxy
for raw input — two of four crash at the second site. The crashes are inside
the shipped `.m` code, not the port wrapper: the driver's own postcondition
errors (prefix `UCLA-DRIVER-FAIL`) never fired.

Both registered readout directions (surfaces survive / do not survive) are
therefore unreachable under the frozen chained semantics; the reportable
outcome of attempt 1 is the demonstrated blocker above.

## Lane discipline honored

Per the card: no per-event fallback, no mixed lane, no second attempt, no
harness or shipped-code modification. The card's registered non-executed
alternative (UCLA-on-raw) remains available only via a fresh registered
amendment.

## Cheapest next discriminating action

Before any amendment decision: a pure executability census of the production
runner on the 26 manifest-verified raw inputs (no harness, no pipeline, no
scientific readout — per-event exit status and crash site only, outputs to
`worktree/lead_controls/raw_census/`). It discriminates between:

- most raw events complete → an amended UCLA-on-raw lane is executable and
  worth registering;
- raw events also crash broadly → UCLA_v4 as-shipped cannot process the
  benchmark event set at all, and Paper 0 §5.5 can be upgraded from "UCLA
  stage not executed" to "UCLA stage demonstrably non-executable as-shipped
  on this event set", with this record as evidence.

Either census outcome is scientifically useful; neither inspects a benchmark
surface.
