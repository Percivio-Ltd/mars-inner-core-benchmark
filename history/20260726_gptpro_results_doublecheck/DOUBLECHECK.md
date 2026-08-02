# GPT Pro completion-review results — lead double-check

Date: 2026-07-26. Operator deposited
`history/20260726_paper0_completion_gptpro_review/results/C{1-4}.md` and asked
for a double-check. This record verifies the results against the package
contract and the repository's own artifacts, disposes every finding under the
AGENTS.md severity policy and ratchet, and executes the cheap discriminating
checks the reviews requested where the evidence is minutes away.

## 1. Package integrity

Recomputed SHA-256 of all four bundles matches
`bundles/INDEX.md` exactly:

- C1 `deeec081e914377578712fa4bac2ae98a2974bcb0adf0c455fcd07c28162fe37`
- C2 `26b3fa7cc884d137dfb6f2eda6fe6b45fbb29162712f8640d78931ccabb4db87`
- C3 `04fe694fe57ee2c9d6caf58469cd0977dad6175628860d25b6e36666a0f1fa93`
- C4 `e769cde8dc2acf682fd009d6d622c38497e7bc1bd74a1ccc6bde7048f7bc9e39`

The bundles embedded byte-identical copies of the artifacts we hold: the
SHA-256 of our `history/20260725_scout_pass3/comp_assoc_reading.json`
(`d8140daf2141a1ff…`) appears in BUNDLE_C3's source manifest. The reviews
therefore adjudicated exactly the frozen evidence, and C2/C4 additionally
report recomputing all embedded source digests successfully.

## 2. Verdict matrix (as returned)

| Bundle | Proposition | § A.4 | Fable notification |
|---|---|---|---|
| C1 criterion-7 closure | PASS WITH P2 | SUPPORTS | QUALIFIES |
| C2 benchmark robustness | BLOCKED | SUPPORTS | BLOCKS |
| C3 bootstrap/kinematics | BLOCKED | SUPPORTS | BLOCKS |
| C4 criteria 1–6 provenance | PASS WITH P2 | QUALIFIES | QUALIFIES |

Aggregate: **zero P0 findings in all four reviews. § A.4 benchmark completion
is supported by all four** (C4 qualifies on custody/retention). Every P1
(C2-P1-1/2/3, C3-P1-1) is raised against the compressed
`evidence/FABLE_NOTIFICATION.md` frozen into the bundles — a surface that was
already superseded by the twice-narrowed ledger completion entry before these
results arrived.

## 3. P1 disposition — discharged by prior supersession, verified line-by-line

The narrowed completion entry (`CONTINUITY-paper0.md`, "PAPER 0 COMPLETE"
entry, narrowed 2026-07-26) was checked against each P1's own resolving
wording:

- **C2-P1-1** (exact/folded tolerance conflation): ledger says "subordinate
  target-box maximum at 601.95 s, −6.67 s/deg (outside exact tolerance,
  inside uncertainty-folded tolerance)" — the endpoint is not called the
  published pair, and both tolerance classes are stated. Matches C2's
  resolving sentence.
- **C2-P1-2** (operator robustness): ledger says "The published pair is not
  the global maximum under either tested polarization operator; exact-ridge
  operator robustness is not claimed (the envelope-A winner flips…)" —
  exactly C2's surviving narrow statement.
- **C2-P1-3** (jitter robustness): ledger says "Audited alignment error does
  not explain the full time offset, though occupancy regions are materially
  sensitive to the registered ±10 s jitter (material centroid displacement,
  31–69× broadening)" — exactly C2's surviving narrow statement.
- **C3-P1-1** (composition "not distance"): ledger says "Branch membership is
  associated with event-set composition…, but distance and composition are
  not separately identifiable in the fixed products" — exactly C3's
  replacement wording. C3 itself confirms: "The later narrowed completion
  record adopts exactly that boundary, explicitly superseding the broader
  interpretation." C2 likewise records as a failed attack that Paper0.md
  propagates the overstatement.

Ratchet note: these P1s were valid against the notification at its freeze
time and are recorded as such; they impose no new repair because the
supersession pre-dates the results' arrival and adopts their resolving
wording verbatim.

## 4. Numeric verification — every load-bearing claim re-checked

From `results/tables/peak_comparison.csv` (identity-gated, digest
`8df5f5c8…` per the audit's identity check):

- 20 s M-K global: (663.80, −3.6364) ✓; published-target endpoint
  (601.95, −6.6667), `within_published_tolerance=False`,
  `within_uncertainty_folded_tolerance=True`,
  `uncertainty_folded_time_tolerance_s=24.75`, rank 6938,
  `local_max_neighbor_check=True` ✓ (all of C2-P1-1's figures).
- 1 s published-target row: (602.50, −6.8687), exact-tolerance True ✓
  (C2's scale-mixing observation).

From `history/20260725_research_pipeline_restock/ablpolop_…ablation.csv`:

- Principal-axis/DOP 20 s global: (603.25, −3.5354) rank 1, exact False;
  target-box endpoint (602.45, −6.5657) rank 10131, exact True ✓
  (C2-P1-2's figures, including the ~60.55 s winner switch).
- Ablation rows carry `current_provenance_status=not_required` ✓ —
  C2-P2-2 confirmed accurate (new P2, see § 7).

From `history/20260725_research_pipeline_restock/t3power_power_comparison.json`:

- PKiKP j10: dt 5.0536 s, ds 2.4085 s/deg, broadening 31.2436×, material ✓;
  PKKP j10: 46.7466 s, 0.2771 s/deg, 68.9188×, material ✓ (C2-P1-3's figures).

From `history/20260725_scout_pass3/comp_assoc_reading.json`:

- identifiability note verbatim as C3 quotes it ✓; Type I omnibus_p
  0.00390, f662 0.635 ✓; Type II omnibus_p 9.999e-05, f662 0.55 ✓;
  positive controls reproduced ✓; adverse label-permutation Type II 1/3
  material, `adverse_void=False` ✓; FWE flags: common positives S1039b,
  S1022a; Type II additionally S0474a(+), S1012d(+), S0820a(−), S0484b(−) ✓
  (C3's "additional positive and negative FWE events").

C4's criterion-1 arithmetic (2695 = 2693 + 2; 2693 = 2393 + 300) and its
"three absent Khan ZIPs, 2,390 valid current paths" match the independently
reached P0-CHAIN-FAILCLOSED Repair-2 stop-and-report (2,061/2,064 Khan +
302/302 AK + 26/26 waveforms + 1/1 catalog) — two independent routes to the
same three files. `Cloud-backed storage` confirmed at `papers/Paper0/Paper0.md:199`
(C4's bundle-deficiency quote is accurate).

## 5. Cheap discriminating checks executed now (discharges)

1. **S3 remote byte identity** (C2-P2-3 / C2-U2, C4-P2-4 / U6 half 1):
   downloaded the exact object
   `s3://marsquake/paper0_evidence/20260725_bench_e2e/nth_root_win20.npz`
   at VersionId `6Pf_TnIpmWsveK4mk_AxSO3TxX5wQs9c`;
   `shasum -a 256` over the 56,545,416 received bytes =
   `9d46868b188fe018b41bb644c3a938580fbc6d3902a921affd172693b4b84e40`,
   equal to the pinned digest and the object's declared metadata. GET
   receipt (matches the bundle's HEAD receipt field-for-field):

   ```json
   {"LastModified": "2026-07-25T17:08:27+00:00", "ContentLength": 56545416,
    "ETag": "\"87078db4a6f8a7b63b84c03bf3aefa19-7\"",
    "VersionId": "6Pf_TnIpmWsveK4mk_AxSO3TxX5wQs9c",
    "Metadata": {"sha256": "9d46868b188fe018b41bb644c3a938580fbc6d3902a921affd172693b4b84e40",
                 "git_commit": "ff746202", "run": "paper0_bench_e2e_20260725T085336Z"}}
   ```

2. **`ff746202` vs `e65240a5` commit mapping** (C2-U3, C4-U6 half 2):
   `e65240a5e827c4a3279b9900fb78a05e0304b8de` = "Forward --inventory-file
   through the Paper 0 orchestrator" (2026-07-25 10:53:01 +0200) — the run's
   generation commit, matching the run start 08:53:36Z.
   `ff74620207a46ae139df876f51b48d340b6ec638` = "Land current-gate benchmark
   evidence: displacement reproduced" (12:09:31 +0200). Ancestry verified by
   `git log` traversal: the generation commit is an ancestor of the
   upload-time commit. Interpretation: the S3 `git_commit` metadata records
   the checkout at upload time; the generation commit is bound inside the
   hash-pinned run manifest. Custody chain coherent.

3. **Validation return-code 2** (C2-U6, C4-P2-3 / U5):
   `scripts/07_validation/generate_validation_report.py:1250-1253` — exit 2
   iff `--strict-gates` and the summary's `validation_status.status` is not
   "passed"; `results/validation/validation_summary.json` records exactly one
   failure: "deglitch: … unverified statuses: succeeded_mps_only" (the
   honest MPS-only lane). `scripts/run_paper0.py:802-818`
   (`_apply_validation_stage_result`) applies the registered
   `--allow-deglitch-status` acceptance: allowed deglitch failures are
   stripped, the remaining empty failure set yields
   `validation_status: passed`, and return codes {0, 2} are the explicit
   stage contract (`run_paper0.py:74-75` defines
   `DeterminedValidationError.returncode = 2`). The
   (rc=2, stage succeeded, validation passed) triple is the designed
   representation of "all gates pass except the honestly recorded,
   registered-accepted MPS-only deglitch attestation" — the same design C4's
   own failed attack #4 validated.

4. **Explicit `allow_pickle=False` loads** (C4-P2-5 / U7): all six bootstrap
   NPZs loaded with `numpy.load(path, allow_pickle=False)` (numpy 1.26.4),
   full-file SHA-256s equal to the identity list, `peak_times` shape (200,)
   each:
   `f4b22d09…`, `082b1ac3…`, `cc02aeb6…`, `8c880a24…`, `bd130a99…`,
   `f4a625f9…`.

5. **C1's unretained-transcript items** (C1-P2-2 in part, C1-U registers
   1–3): discharged after the bundle freeze by
   `history/20260726_criterion7_logs/` (commit `7088c6e8`, post-dating the
   bundles): the contemporaneous scoped/full pytest logs are archived with
   SHA-256s and the full Track-B attribution re-derives from the archived
   full log exactly (73E+3F certificates, 38E+1F census, 13F solver, 13F
   mirror, 14F cache-recovery, zero non-Track-B). Residual (stands, already
   recorded): the exact dirty `git status` payload of the historical runs
   was never retained.

6. **Stale `docs/CURRENT_STATE.md` next-action** (C1-P2-3; third independent
   flag after the Codex audit and gpt-5.6): the canonical state surface is
   synchronized in this commit — criterion 7 and § A.4 completion recorded,
   next action routed to the LOO influence card. Discharged.

## 6. Ratchet and convergence notes

- C3-P2-2 (vacuous transpose control), C3-P2-3 (outcome parenthetical +
  min-Vp 5.0 vs 3.6656), C3-P2-4 (midpoint 632.05 vs frozen 632.0),
  C3-P2-5 (R.1A criterion-7 overstatement) are **re-findings of the four
  pass-3 countersign P2s already in the backlog** (recorded in
  `docs/research_pipeline.md` before the bundles were built) — independent
  convergence, no new entries, no escalation (no new claim-impact evidence;
  C3 itself keeps them P2 and confirms the frozen 632.0 boundary and the
  discriminating bound stand). The LOO card states the 632.0 s boundary as a
  frozen constant, not a midpoint claim.
- C1-P2-1 (dirty-count wording) was already discharged by the ledger's
  criterion-7 count qualification annotation; verified still accurate.
- C2-P2-1 / C4-P2-2 / C4-U4 (from_scratch:false, unretained status payload)
  re-find the recorded retention P2 family; recorded, not escalated.
- C4-P2-1 (historical criterion-1 JSON unrestorable; three Khan ZIPs absent)
  converges with the Repair-2 stop-and-report and folds into the pending
  operator decision (hydrate vs registered fetch-on-demand amendment).

## 7. New P2s recorded to the backlog (this review round)

1. Operator-ablation table lacks a current-provenance execution manifest
   (`current_provenance_status=not_required` on all rows) — rerun both
   operators from the primary input matrix with enforcement before any
   external claim-bearing use (C2-P2-2).
2. `papers/Paper0/Paper0.md:199` lists "Cloud-backed storage" as an excluded
   dependency while evidence custody now uses S3 — scope the sentence to
   execution-time dependencies via the registered amendment surface only
   (C4 bundle deficiency).
3. SIG-statement headline template glosses the target-box maximum as "the
   published PKiKP pair"; the precise referent is the box endpoint
   (601.95, −6.67), 2.05 s from the published (604, −6.5). The artifact JSON
   carries the exact coordinates and both tolerance flags adjacent; any
   external reuse must use the box-endpoint phrasing (self-identified from
   C2-P1-1's pattern; the frozen card template itself is not retro-edited).
4. Identities/reasons of the 16 skipped tests in the green § D.5 run — retain
   `-rs` output on the next § D.5 execution (C1-U6).
5. TauP freshness is transferred via byte-identity of the fresh NPZ; add a
   clean-environment rebuild that queries the fresh path directly
   (C4-P2-6 / U9).
6. Prospective retention practice: keep full stage logs and per-stage
   validation fragments (and exact status payloads) for future
   claim-bearing runs (C1/C2/C4 retention registers).

## 8. Standing outcome

Paper 0's § A.4 completion now carries three independent completion reviews
(parallel Codex audit; gpt-5.6 formal review; GPT Pro C1–C4 on frozen
packages) with the same shape: **completion supported, zero P0, current
artifacts and numerics verified, all interpretation-wording P1s resolved by
the narrowed completion record, residual findings P2-bounded** (custody,
retention, and precision). The remaining open items are the LOO influence
card (runner in implementation) and the two operator decisions (Repair-2
route; external publication direction).
