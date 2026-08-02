# P0-UCLA-PROD Amendment 1 — UCLA-on-raw production lane (landed 2026-08-02)

Sibling records in this directory: `PRODUCTION_ATTEMPT_1.md` (the chained
attempt-1 production record) and `CENSUS.md` (the 26-event raw
executability census whose 22/4 partition Amendment 1 froze a priori).

## Registered scientific item

Card P0-UCLA-PROD, Amendment 1, registered in `docs/research_pipeline.md`
(commit `102264e4`) before any readout surface was inspected. Question: does
the Paper 0 benchmark's displaced-ridge disagreement with the published
PKiKP coordinates depend on the deglitch method? The lane runs the full
Paper 0 DAG on raw data deglitched by the UCLA_v4 code (explicit opt-in
identity pre-stage, terminal status `ucla_unverified`, no MPS claim) over a
frozen 22-event partition, against a subset-matched MPS-only pass, and reads
exactly three registered same-cell surfaces from each lane at the native
grid.

Frozen partition — stack (19): S0105a S0173a S0189a S0235b S0290b S0325a
S0474a S0484b S0802a S0820a S0864a S0916d S0918a S1012d S1022a S1039b
S1048d S1133c S1157a; validation (3): S1102a S1153a S1415a; excluded a
priori: S0784a S1015f S1197a S1222a.

## Delegated implementation cycle

Codex `gpt-5.6-sol` at `xhigh` implemented the wiring (round 3), one fix
round (round 4), one final review; accepted with zero code drift (reviewed
diff `worker/reviewed_diff_r3.patch`, sha256
`b0bd6cb85ef81687f384e387d554a1827693d55ee679c7c1bb9d469acb237207`,
re-verified identical at landing). Deliverables: identity pre-stage in
`scripts/02_preprocess/deglitch_mps_ucla.py`; orchestrator forwarding fixes
in `scripts/run_paper0.py` (the latent non-forwarding of
`--event-table`/`--raw-dir`/`--catalog` was adjudicated NO P0/P1 for prior
runs — checkout-anchored defaults coincided with prior flag values — but
was load-bearing for this subset lane); `manifest/event_table_ucla22.csv`;
`tests/test_ucla_raw_identity.py`; `RUNBOOK_ucla_raw.md` (execution
document, copy under `runbook/`). Worker records under `worker/`.

## Controls

- pos-A (production ↔ census): pass-1 S0235b UCLA product byte-identical to
  the single-event census product; both sha256
  `e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db`. PASS.
- pos-B (subset MPS ↔ accepted): pass-2 S0235b MPS product byte-identical to
  the canonical accepted `data/deglitched/S0235b.mseed`; both sha256
  `73410b11b144b944872c7a1acfce9cb5d1141ea4e35bbde95880a56180207cff`. PASS.
- adv-A (excluded-event rejection): S1197a through identity+UCLA crashed at
  the registered `aa(_,2): out of bound` site, output restored byte-identical
  from backup, terminal `succeeded_mps_only`, and the lane's sole allow-list
  rejected it with nonzero exit (`Disallowed deglitch statuses:
  S1197a=succeeded_mps_only`). PASS (records under `controls/adv_A_*`).
- Cross-run determinism (by-product of the interrupted-attempt quarantines):
  first three pass-1 events byte-identical across independent attempts, 3/3.

## Execution history

Pass 1 required three attempts; each interrupted tree was quarantined whole
and unmixed (no in-place rerun; the runner refuses overwrites):

1. Attempt 1 killed by the session harness mid-run (~bootstrap_type2);
   deglitch had already completed 22/22 `ucla_unverified`. Quarantined to
   `lanes/pass1_interrupted_1/` (its complete deglitch summary is
   `quarantine/pass1_interrupted_1_deglitch_run_summary.json`).
2. Attempt 2 deadlocked at S0235b's UCLA stage: in a fully detached TTY-less
   session the shipped UCLA code's data-dependent figure path deadlocks the
   Octave↔gnuplot terminal handshake (Octave blocked on the FIFO reply,
   gnuplot children blocked on stdin; 3.5 h at 0% CPU; diagnosed by stack
   sample and fd inspection before any kill). Quarantined to
   `lanes/pass1_interrupted_2/`. Minimal correction: `GNUTERM=dumb` +
   `GNUPLOT_DEFAULT_GTERM=dumb` exports in
   `scripts/02_preprocess/ucla/run_ucla_octave.sh` (env pin only). The pin
   was gate-verified in the exact failing conditions (detached, TTY-less,
   single-event S0235b): completion + product byte-identity to the census
   (`controls/gnuterm_gate*`). Because the runner hashes itself,
   `parameters_sha256` legitimately superseded
   `98382efd2132d07f8bac0c946e1fa6c62e965c6cccf0d9152eb0055464985e1e` →
   `e79c60d72e79a86a5235eb73a264ea441e5d74c77ca32571330799db467de37d`
   (uniform across all lane events).
3. Attempt 3 completed cleanly (detached, `start_new_session`, stdin
   `DEVNULL`).

Before pass 1, the attempt-1 chained state was archived to
`lanes/chained_attempt1/` (2,103 files; per-file manifest
`quarantine/chained_attempt1_SHA256SUMS.tsv`, manifest sha256
`63042eeed37e134fdb267d8672ab5390586037ed61c9da90bef8edf3a202e87e`).

## Production passes and gates

Both passes: same 22-row event table, same staged `data/raw_ucla22/` input
dir, same manifest/catalog/models/inventory/fidelity
(`methods_robustness_200`), same interpreter and cwd; the deglitch method is
the single differing factor.

- Pass 1 (UCLA-on-raw): `--seisglitch-command identity` + real UCLA runner,
  `--allow-deglitch-status ucla_unverified` (sole). Exit 0; deglitch summary
  complete, 22 events, `{"ucla_unverified": 22}`; manifest
  `execution_status=succeeded`, `status=succeeded`,
  `validation_status=passed`; attestation same counts, `n_events=22`. No new
  event failure among the 22 (the card's stop condition never fired).
  Archived to `lanes/ucla_raw/` (3,179 files; `SHA256SUMS.tsv` sha256
  `b808d834f50b99bcea44ad350df5e2e35a8033c53da51f1fd525ab6987c39498`).
- Pass 2 (MPS subset): real seisglitch, no `--ucla-command`,
  `--allow-deglitch-status succeeded_mps_only` (the spelling independently
  forced by `run_paper0.py:54/612/1260-1261` plus the accepted manifest's
  attestation). Exit 0; `{"succeeded_mps_only": 22}`;
  succeeded/succeeded/passed; `attestation_level=succeeded_mps_only`,
  `accepted_partial_lane_by_design=true`. Archived to `lanes/mps_subset/`
  (1,503 files; `SHA256SUMS.tsv` sha256
  `a4ffa6fc7ea5df84e9b7f377e1cd2f83afbb6687c283fcb0402f4a2937dd9870`).

Critical product sha256 (also in each lane's `SHA256SUMS.tsv`):

| artifact | ucla_raw | mps_subset |
|---|---|---|
| deglitch_run_summary.json | `8ec57edbea1706dd9a873476f3f01ad685810f5cb0e4a7b8089d8b7715b475a6` | `ccff0c9a92c423e1991a9a6215989f3c3e5fac1d140c81f2e156f37a52b7d441` |
| paper0_run_manifest.json | `ff93cd0a008493da5c9194b4a54841bfa50307998d896a916e6108982f2ea07f` | `8af8062344fd3c4ad7a395c7266a7538725fb9ebb9ef52df189a8d2276d5c17c` |
| validation_summary.json | `d2b21fb569184078e9869dfb42606bb51eac11d6403352c61abfc824f6709c23` | `da6464d2dce5f7c9ceb73b9cf172762c4b94296fa60340cbd5b6d90be69be4e8` |
| peak_comparison.csv | `265153e62b1442c572d3d1fa91eaf128ba3f895add18ac97005f5fd19e1aa2c8` | `dc9e579af59d818769dbea277f8f1ef8e1b2c3ba7b9d4054085a61fe6bb21eab` |

## Registered same-cell readout

Executed with the runbook §7 script verbatim after both archives were
sealed; every assert passed, including CSV↔JSON cell-for-cell agreement;
`support_count=19`, `minimum_support=2` in all six cells
(`readout/readout_table.tsv`). Accepted 23-event MPS values are registered
context only.

| Surface | ucla_raw (19-ev) | mps_subset (19-ev) | accepted MPS (23-ev, context) |
|---|---|---|---|
| PKiKP global argmax | 576.15 s, −10.0 s/deg, p=0.9003 | 662.85 s, 0.0 s/deg, p=1.0140 | 663.8 s, −3.636 s/deg, p=0.9327 |
| PKiKP published-box max | 584.00 s, −7.0707 s/deg, p=0.7547 | 584.00 s, −7.0707 s/deg, p=0.7356 | 601.95 s, −6.667 s/deg, p=0.7736 |
| PKKP endpoint | 1341.25 s, −6.9697 s/deg, p=0.3049 | 1340.95 s, −6.9697 s/deg, p=0.2422 | 1341.00 s, −6.9697 s/deg, p=0.2143 |

## Interpretation

(a) Deglitch-method dimension (fixed 19-event stack): the published-PKiKP-box
maximum lands in the identical native-grid cell under both deglitch methods
(584.00 s, −7.0707 s/deg; powers differ 2.6% relative); the PKKP endpoint
sits at the same slowness cell with a 0.30 s time offset (small against the
20 s power window). The global PKiKP argmax flips location (UCLA-on-raw:
576.15 s at the −10 s/deg domain edge, power 0.9003; MPS: 662.85 s at
0.0 s/deg, power 1.0140). This extends, rather than repeats, the
P0-LOO-INFLUENCE fragility result: LOO documented exactly two branches
under single-event removal (662-family and 602-family, boundary 632 s);
the UCLA lane reveals a third near-degenerate argmax location at the
slowness-domain edge that no LOO run produced. The MPS-subset argmax
stays 662-family and coincides exactly with the LOO S1222a-hold-out cell
(662.85 s, 0.0 s/deg) — an independent cross-check, since S1222a is one
of the four excluded events. Net (review-precise formulation): the global
argmax is branch-fragile to both event removal and deglitch method; it is
not a stable readout surface. PKKP powers differ 25.9% relative (MPS
denominator) alongside the 0.30 s time offset — disclosed because no
robustness tolerance was registered for that surface.

(b) Event-set dimension (MPS-19 vs accepted MPS-23, context): the box
maximum displaces 601.95 → 584.00 s with both deglitch lanes agreeing
exactly at 19 events, so that displacement is an event-set effect, not a
deglitch-method effect; the PKKP endpoint is essentially event-set
invariant; the global argmax keeps its ~663 s time but moves slowness
−3.636 → 0.0.

Net statement for Paper 0 (adopting the bounded-review formulation): the
qualitative displaced-ridge disagreement with the published PKiKP
coordinates — non-agreement and subordination of the published-target
maximum — persists under UCLA deglitch provenance on raw data (the UCLA
lane's global maximum, power 0.9003, remains distinct from and stronger
than its published-target row, power 0.7547). The published-box maximum is
exact same-cell across the two deglitch methods; the PKKP endpoint is
same-slowness and 0.30 s near-concordant; the qualitative PKiKP
disagreement remains while its global-argmax coordinate is
deglitch-sensitive. Bootstrap products are archived in both lanes but were
outside the registered readout and remain uninspected.

## Bounded review

One independent reviewer (Codex `gpt-5.6-sol`, `xhigh`), bounded to the lead
execution path and the registered readout: brief
`review/review_brief_readout.txt`, report `review/REVIEW_readout.md`.
Verdict: COUNTERSIGN, zero P0/P1. The reviewer independently recomputed both
archive-manifest digests with per-lane spot hashes, re-ran the §7 readout
verbatim (six cells identical to the ledger), re-verified the §4/§5 gate
fields, pos-A/pos-B byte identities, registration-before-inspection
ordering, and canonical-checkout isolation (no writes, no path references,
no post-registration mtimes in the protected scopes). Two P2
interpretation-wording precisions were recorded and are incorporated in
this document's Interpretation section.

## P2 backlog recorded under this card

1. `bootstrap_type1.py` `--table` default is bare cwd-relative (type2/3 use
   `repo_path`).
2. `succeeded_mps_only` enum reuse for identity-without-UCLA terminals
   (transparent via `mps.status=identity_passthrough`).
3. Reproducibility packages must pin the gnuplot terminal (`GNUTERM=dumb`);
   shipped UCLA code opens figures on a data-dependent path and deadlocks
   TTY-less otherwise.
4. `parameters_sha256` self-hash supersession on any runner edit (recorded:
   `98382efd…` → `e79c60d7…`).
5. Review wording precision (incorporated here): "bistable under small
   perturbations" overstated the combined record — the bounded claim is
   branch-fragility to both event removal and deglitch method.
6. Review wording precision (incorporated here): "persists unchanged" and
   "deglitch-robust at the registered cells" are safe only for the
   qualitative disagreement/subordination verdict — the box maximum is
   exact same-cell, PKKP is same-slowness/0.30 s near-concordant (25.9%
   relative power difference), and the global-argmax coordinate is
   deglitch-sensitive.

## Artifact locations

- Full lane archives (bulk, deterministically regenerable, hash-bound by the
  committed `SHA256SUMS.tsv` files): S3
  `s3://marsquake/paper0_evidence/20260802_ucla_prod/` (tarballs with sha256
  metadata); local originals under
  `/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes/`.
- Code landed on `main`: the reviewed wiring diff, the UCLA runner harness
  (`scripts/02_preprocess/ucla/`, including the census control scripts),
  `manifest/event_table_ucla22.csv`, `tests/test_ucla_raw_identity.py`.
- The canonical accepted 23-event benchmark products under `results/` are
  untouched by this card.
