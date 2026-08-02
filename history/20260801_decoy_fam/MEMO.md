# P0-DECOY-FAM — decoy-box family statistic (memo)

Card: `docs/research_pipeline.md` § "P0-DECOY-FAM — decoy-box family statistic",
registered 2026-08-01 at commit `a2163d49` (frozen). Executor: bounded sub-Fable
worker; implementation: Codex `gpt-5.6-sol` `xhigh`; countersign: Codex
`gpt-5.6-sol` `xhigh`. Isolated dir: `/Users/artuskg/marsquake_runs/20260801_decoy_fam/`
(repo read-only; 26 `*_ZNE.mseed` + 26 `*_ZNE.rotation.json` copied byte-identically
from `data/processed/`, verified by SHA-256).

## Question

Across the full Mars vespagram (the canonical supported-power surface the draft's
S1/S2 statistics live on), what fraction of target-box-sized decoy boxes contain a
maximum at least as high as the real target-box maximum — the family-wise context
for the draft's "within uncertainty-folded tolerance" reading, extending the
recorded rank 6,938 / quantile 0.7141 point statistics to a box-family statement.

## Canonical-lane correction (recorded per lead direction, pre-outcome)

The registered card's chain recap said `polarization --operator
principal_axis_projection`. That flag was a transcription slip copied from the
P0-ABL-POLOP-PROV ablation card: the recorded enforced ablation table
(`history/20260801_ablpolop_prov/peak_comparison_operator_ablation_provenance.csv`,
SHA `512f78e1…`) contains NO row with the card's own frozen gate cell — its
envelope-A global under that operator is (603.25 s, −3.5354 s/deg, 0.9333) — while
the committed production table (`results/tables/peak_comparison.csv`, SHA
`8df5f5c8…`, manifest-gated) carries exactly the gate cell under the default
operator `montalbetti_kanasewich_1970` (what `scripts/run_paper0.py` invokes with
no `--operator` flag). The worker independently detected the inconsistency from
those recorded artifacts before any decoy statistic existed; the lead confirmed
mid-run and amended the registered card (dated, outcome-neutral). Resolution is
outcome-neutral: it was forced by the pre-registered gate cell and thresholds, not
by any sweep outcome (no sweep had run). A first, superseded regeneration under the
erroneous operator was stopped at the vespagram stage; its log is preserved as
`chain_principal_axis_SUPERSEDED.log` and its derived products were deleted before
the canonical rerun (inputs re-verified byte-identical to `data/processed/`
afterwards).

## Step 1 — canonical lane regeneration and gate

Chain (one finite observed run, `run_chain.sh`, log `chain.log`, ~10 min,
interpreter `~/micromamba/envs/mars-ic/bin/python`): bandpass → polarization
(default operator `montalbetti_kanasewich_1970`) → fdpa → align_and_cut →
normalize_and_envelope → run_vespagrams → `detect_peaks.py
--require-current-provenance` → `peak_comparison_decoy_fam.csv` (240 rows, all
`current_provenance_status=current`).

- GATE (frozen): the table must contain the canonical PKiKP global supported
  argmax (663.80 s, −3.6364 s/deg, power 0.9327, support 23). **PASS** — exactly
  one row: `paperfaith/envelope/A/nth_root/win20.0`, t = 663.8,
  s = −3.6363636363636367, power = 0.9326603162534909, support 23, operator
  `montalbetti_kanasewich_1970`.
- Stronger identity: the regenerated table is **byte-identical** to the committed
  production table — SHA-256
  `8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce` equals the
  `cgr_identity_manifest.sha256` entry for `results/tables/peak_comparison.csv`.
- `sig_statement_reading.json` regenerated in the isolated dir with the frozen
  P0-SIG-STATEMENT reader rules verbatim (`regen_read_sig_statement.py`; only the
  three path constants differ; identity gate ran against the same manifest digest
  and passed because the table is byte-identical; the reader's built-in positive
  and corruption controls passed). Values identical to the committed reading:
  rank 6938, quantile 0.7141, S3 ratio 1.21. SHA-256
  `4af7b025e990254fc39dc1219dca163b5e4a3638b206d0cba4fe944c6f6bea0d`.

## Recorded PKKP-family threshold (BEFORE the sweep)

Recorded 2026-08-01T18:29:25Z in `pkkp_threshold_record.json`, before any decoy
box was evaluated: the pkkp_mirror target-box maximum from the regenerated
reading's selected row (frozen reader rule `lane_row("PKKP", "paper_target")`) is

  **PKKP threshold = 0.21425338569020153**

(row: t = 1341.0 s, s = −6.96969696969697 s/deg, support 23, target_box_rank
13395, background quantile 0.3927, lane `paperfaith/envelope/A/nth_root/win20.0`
— the same canonical surface as the PKiKP family).

## Step 2 — the surface

The exact supported-power surface `detect_peaks.py` reads: per-NPZ
`vespagram` (slowness × time) with cells eligible iff
`np.isfinite(vespagram) & (support_counts >= minimum_support)` (`minimum_support`
= 2 in the payload). Sweep surface (both families):
`vesp/paperfaith/envelope/A/nth_root_win20.npz` from this regenerated lane
(grid: slowness `linspace(−10, 0, 100)`, time 0.05-s steps on [−100, 2200]).

## Method (frozen; execution record)

Codex `gpt-5.6-sol` `xhigh` implemented `decoy_box_reader.py` (banner verified in
`codex/reader_stdout.log`; a first Codex attempt died silently after startup and
was relaunched once — `codex/reader_stdout_attempt1_died.log`). The worker
reviewed the script line-by-line before execution: searchsorted closed-interval
box-to-grid mapping (left on lo, right on hi; slowness = axis 0, time = axis 1,
validated against the NPZ shape); supported surface exactly
`isfinite(v) & (support_counts >= minimum_support)`; frozen centers by integer
arithmetic (371 × 89 = 33,019 PKiKP; 371 × 81 = 30,051 PKKP, both asserted);
frozen thresholds as literals; NaN boxes stay in denominators, never numerators;
in-script gate replicating `find_global_peak` semantics runs before any sweep.
Review verdict: faithful; no P0/P1; P2 notes: PKKP threshold is CLI-trusted (by
design, cross-checked by supplementary control S1) and the summary carries a
nondeterministic timestamp field. Executed once on
`vesp/paperfaith/envelope/A/nth_root_win20.npz` with
`--pkkp-threshold 0.21425338569020153` (`decoy_reader_run.log`).

## Controls

- In-script gate: **PASS** — exact cell (663.79999999999995, −3.6363636363636367,
  0.93266031625349088, support 23).
- P1 positive (box = true target box, center (604, −6.5)): **PASS** — max
  0.7736156900239739 (exactly the recorded published_target power; rounds to
  0.7736).
- P2 positive (box centered on the exact ridge cell): **PASS** — max
  0.93266031625349088, exactly the gate-cell power (rounds to 0.9327).
- S1 supplementary (PKKP box = published PKKP target box): **PASS** — max
  0.21425338569020153, exactly the recorded pre-sweep threshold.
- A1 adverse (frozen: box entirely inside the pre-P segment,
  [−90, −50] s × [−7.1, −5.9] s/deg, must be < 0.7736): **FAIL** — observed max
  **49.37176439112555** (8,936 supported cells), independently re-derived from
  the NPZ outside the reader (identical value, argmax at t = −53.45 s,
  s = −5.96 s/deg).

**STOP-AND-REPORT.** Per the card and the dispatch instructions, a failing
control stops the run; nothing was coded around. The run terminated with the
reader's nonzero exit after writing the evidence artifacts.

## Why A1 failed (observed mechanism, no repair attempted)

The card's A1 rationale was "otherwise the surface indexing is wrong." Indexing
is demonstrably correct: gate, P1, P2, and S1 all reproduce their recorded
values exactly and independently of one another. The failure is a data property
of the canonical variant-A surface: supported stacked power in the pre-P segment
is enormous — up to **1395** at t = −86.95 s; per-time-band supported maxima
decay monotonically 1395 → 137 → 52 → 11 → 6.3 → 2.8 → 1.8 across
[−90, −70] → … → [150, 250] s. Per-event probing shows 19 of 26 variant-A
envelopes carry pre-P maxima 5–355× the target-window scale immediately after
their valid-data onsets (first valid sample between t = −95.0 and −55.05 s;
e.g. S0918a 355.1, S0916d 348.6, S0189a 266.7), i.e. trace-start/mask-edge
transients plus pre-P noise, amplified by the variant-A ("target window ≈ 1")
normalization and surviving the min-support-2 mask with support up to 23. The
frozen A1 premise (pre-P quiet below 0.7736) is empirically false on this
surface even though the box reader indexes it correctly.

## Frozen statistics (computed by the same run; NOT ACCEPTED — reported for the
## record pending lead adjudication of the failed adverse control)

- PKiKP boxes: 33,019 total; 368 overlap the target box; 96 contain the ridge
  cell; 0 empty (NaN) boxes.
  - F_decoy_target_incl = 8164/33019 = 0.24725158242224174
  - F_decoy_target_excl = 8068/32651 = **0.24709809806744051** (primary)
  - F_decoy_ridge_incl = 5831/33019 = 0.17659529361882553
  - F_decoy_ridge_excl = 5831/32923 = **0.1771102268930535** (primary)
- PKKP boxes: 30,051 total; 697 overlap the published PKKP target box; 0 NaN.
  - F_decoy_pkkp_incl = 21929/30051 = 0.72972613224185556
  - F_decoy_pkkp_excl = 21503/29354 = **0.73254070995435039** (primary)
  - threshold 0.21425338569020153 (recorded pre-sweep).
- Descriptive structure (read from the produced per-box table, no new choices):
  exceedance is concentrated where the early-coda decay ramp lives — centers
  t ∈ [250, 400] s: 100 % of boxes exceed both PKiKP thresholds; [400, 600]:
  79.7 % / 67.7 %; [600, 800]: 39.7 % / 0 %; [800, 1600]: 0 % / 0 %;
  [1600, 2100]: 13.2 % / 7.7 % (late trace-edge rise). Largest in-sweep box max
  2.397 at t_center = 280 s.

## Interpretation (bounded; run not accepted)

If the family statistic were accepted at face value, roughly a quarter of
target-box-sized decoy boxes anywhere in the sweep span would do at least as
well as the real target box, and ~18 % as well as the global ridge cell — with
the exceedances coming almost entirely from the early-coda ramp (t ≲ 600 s) and
a late-edge band, not from a uniform background. But the failed frozen adverse
control shows the card's control design presumed a quiet pre-P/edge surface that
this variant-A lane does not have, so whether the early-time exceedances are
"decoys" in the intended sense (background structure competing with the target)
or an edge/normalization artifact band requires lead adjudication before any
family-wise claim enters the draft's S1/S2 context. No threshold, box, span, or
stacking change was made or explored.

## Residual uncertainty

- Whether the card intends the decoy family to include the early-coda ramp
  (boxes at t ∈ [250, ~600] s) — the sweep span is frozen to include it, and
  100 % of those boxes exceed both thresholds, dominating the statistic.
- Whether A1 should be re-registered (amended control) against a demonstrated
  quiet band of this surface, versus treating the failed control as evidence
  the family statistic needs a different null design. Both are lead decisions;
  neither was taken here.
- The PKKP mirror numbers inherit the same early-ramp domination (0.73 of boxes
  exceed the low PKKP threshold 0.2143).

## Artifact hashes (SHA-256)

- `peak_comparison_decoy_fam.csv`
  `8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce`
  (byte-identical to the committed production table)
- `sig_statement_reading.json`
  `4af7b025e990254fc39dc1219dca163b5e4a3638b206d0cba4fe944c6f6bea0d`
- `pkkp_threshold_record.json`
  `498e014184350831c3fee4d4da92e92ccd14cb50a6a12d1d90e6e780f257f8a2`
- `decoy_box_reader.py`
  `cf82a337bc4b28408440e637ba81bf164f627ff086176e8acec887a3cdf59869`
- `decoy_boxes_pkikp.csv`
  `163f894d22bcb59669cb13800eda3119e990922e09b7626749e048fb97d17a50`
- `decoy_boxes_pkkp.csv`
  `88c21aeeafa76080091ead1e796961ab31e5d842d20b84c22afe5201065aeab8`
- `decoy_family_summary.json`
  `4c91a3c2daadf92848f4b902df7fddc41054eb0b31fdd1037a3f5dbd46b55c59`
  (contains the reader's own SHA-256s of both CSVs and all control outcomes)

Countersign: NOT REQUESTED — the run stopped at the failed frozen adverse
control per the card's stop discipline; Step 5/6 presuppose passing controls.
The lead adjudicates next steps.
