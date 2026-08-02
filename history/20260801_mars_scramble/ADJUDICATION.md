# P0-MARS-SCRAMBLE — lead adjudication and landing (2026-08-02)

Card: `docs/research_pipeline.md` § "P0-MARS-SCRAMBLE — Mars-side
event-scramble null", registered at commit `a2163d49`; executed under
registered amendment 1 (canonical default operator
`montalbetti_kanasewich_1970`, recorded at commit `310fa81c`). Files in this
directory are byte-identical copies from the isolated run dir
(`/Users/artuskg/marsquake_runs/20260801_mars_scramble/`; large grids remain
there): memo `06e2eb11…`, null table `12aa226d…` (matches memo-recorded
hash), frozen stats `03302442…` (matches), runner `81758d90…` (matches),
countersign brief + verdict.

## Countersign

VERDICT: COUNTERSIGNED, round 1 of 1, zero P0/P1. Banner verified from
`codex_countersign_stdout.log` (run dir): `model: gpt-5.6-sol`,
`reasoning effort: xhigh`. The reviewer independently verified gate rows and
both required hashes, the runner's use of the repository stack/detection
functions, the registered permutation law (distances only), all four
control classes, and recomputed every quoted statistic (151/200, 96/200,
152/201, 97/201, all quantiles) and the forced-operator resolution.

Process note: the countersign output landed on disk at 19:25 UTC 2026-08-01;
the worker session ended in the subscription-window exhaustion before it
could process the verdict. The lead verified banner, verdict, and hashes
directly from disk and landed the card; no worker-side step remained other
than this bookkeeping.

## Accepted outcomes (frozen statistics, computed by the pre-registered
script before any null existed)

Gate PASS: regenerated canonical lane is line-identical to the production
240-row table (SHA `8df5f5c8…`), global argmax bit-identical
(663.8 s, −3.6363636363636367 s/deg, 0.9326603162534909, support 23).

N = 200 distance-permutation nulls (+ identity), zero errors/NaN:

- FAR_ridge = 0.755 (151/200 nulls reach the canonical global-argmax power
  ≥ 0.9327); exceedance p_ridge = 152/201 = 0.7562 — the real ridge sits
  near the 24th percentile of its own null (null median 0.979 exceeds it).
- FAR_target = 0.480 (96/200 reach the published-target-box max ≥ 0.7736);
  p_target = 97/201 = 0.4826 — the real target-box maximum sits at the
  null median.

Accepted interpretation (registered honesty clause carried): under the
frozen criteria, ridge-quality and target-box-quality peaks are the
ordinary product of 4th-root stacking of these 23 normalized envelopes
under randomly sampled distance assignments — the peak-power and
box-occupancy machinery has no discriminating power against
moveout-incoherent alternatives on this data set. Same-data calibration
only: it does not prove any detection false; it calibrates the detection
criteria. This is the Mars-side counterpart of the lunar N1 null (75/75)
and completes the matched null suite the A1 report demanded.

## P2 dispositions (recorded, never fixed in-cycle; hashes stay frozen)

1. Decision-timing wording (countersign P2-1): the memo states the operator
   resolution was recorded "BEFORE the chain ran"; filesystem evidence
   shows it was created at 18:22:10 UTC, after chain start (18:19:54) and
   after the canonical 20-s surface write (18:21:56), though before runner
   creation and before any scramble output existed. Corrected reading for
   all downstream use: the resolution predates all permutation execution
   and all outcome exposure of any scramble statistic, and the operator
   choice is uniquely forced by pre-existing frozen anchors (gate cell +
   thresholds), so no outcome-fitting path exists. The memo's stronger
   wording is not to be quoted.
2. Scope wording (countersign P2-2): the memo's "at ANY distance
   assignment" overstates; the evidence supports "under randomly sampled
   distance assignments from the registered permutation null" (bounded by
   the 75.5 % / 48.0 % figures). Downstream text (draft v0.5 fold) must use
   the corrected phrasing.

## Consequence for the draft

Enters the combined calibration-results fold (v0.5) alongside the
injection ladder (α* = 0.25) and the decoy edge-ramp finding: the
scramble null quantifies the false-alarm behavior that the injection
margin reading (< 0.25× pre-P RMS dominance) and the LOO fragility already
suggested. Draft integration deferred to that single bounded review.
