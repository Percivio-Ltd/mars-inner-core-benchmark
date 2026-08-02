# P0-INJECT-RECOV — lead adjudication of the countersigned stop-and-report (2026-08-01)

Card: `docs/research_pipeline.md` § "P0-INJECT-RECOV — synthetic injection
recovery ladder", registered at commit `a2163d49`; executed under registered
amendment 1 (canonical default operator `montalbetti_kanasewich_1970`,
recorded at commit `310fa81c`, applied pre-polarization). Worker memo:
`MEMO.md` (SHA-256 `8cff2a9f…`), recovery table `recovery_table.csv`
(`0b7a66a4…`), Codex `gpt-5.6-sol` `xhigh` review record `REVIEW_RECORD.md`
(`7c5fc2a8…`) — all byte-identical to the run-dir originals
(`/Users/artuskg/marsquake_runs/20260801_inject_recov/`, 4.5 GB,
regenerable, repo untouched).

## What the run established

1. Gate exact: the α = 0 lane reproduces the canonical cell field-for-field
   under full provenance enforcement (240/240 rows current), including the
   published_target row (601.95 s, −6.6667 s/deg, 0.7736).
2. Injection convention proven, not assumed: the production roll formula
   recovers 604.0 ± 0.051 s for 23/23 stacked traces in every lane, and
   both determinism reruns are byte-identical including NPZ bytes.
3. Ladder (frozen rungs α ∈ {0, 0.25, 0.5, 1, 2, 4, 8} × pre-P RMS,
   impulse at t_i = 604 + (−6.5)(Δ_i − 29°), chain's own 0.2–0.8 Hz
   zero-phase Butterworth): every rung α ≥ 0.25 puts the global argmax
   INSIDE the published target box at −6.4646 s/deg with the argmax equal
   to the box maximum; α = 0.25 lands at (602.95, −6.4646, 1.2483).
4. The α = 8 positive control FAILED its literal wording: observed argmax
   (603.90, −6.4646) is within one slowness cell of (604, −6.5) but 0.10 s
   = two 0.05-s time cells away, where the frozen wording allowed one cell.

## Adjudication of the failed literal control

ACCEPTED AS A CONTROL-TOLERANCE DESIGN FLAW, not a pipeline, convention, or
result defect. Grounds, all recorded in the memo before adjudication:

- The control's underlying intent — that the injection convention maps an
  impulse onto (604, −6.5) — is verified by a strictly stronger check
  (numeric roll recovery, 604.0 ± 0.051 s, 23/23 traces).
- The observed displacement is exactly the signature of additive
  background peak-pulling: the argmax time converges monotonically toward
  604.0 as α grows (602.95 → 603.30 → 603.50 → 603.65 → 603.80 → 603.90),
  from the direction of the α = 0 in-box background maximum at 601.95 s.
  A genuine convention error would displace by tens of seconds or flip
  sign, and would not converge.
- The one-cell wording ignored envelope smoothing plus finite-α
  superposition with real background energy; at any finite α the argmax
  is pulled toward nearby background maxima. The tripwire branch ran as
  registered (convention re-verified, rerun byte-identical) and correctly
  stopped rather than coding around the wording.

Consequences: the α = 8 lane is NOT quotable as a passed literal control;
it IS quotable as the recorded convention-verification evidence above.

## Accepted outcomes

The frozen ladder outcomes are ACCEPTED with the failed-literal-control
disclosure attached:

- α*_argmax = α*_power = 0.25 — the smallest registered rung already flips
  the global argmax from the 662-family ridge into the published target
  box; the true flip point lies in (0, 0.25] and is not further resolved
  (no rungs below 0.25 were registered; none may be added post hoc).
- Interpretation (both directions, per the card's outcome-neutral
  framing): (i) sensitivity — the chain detects a coherent arrival at the
  published coordinates at ≤ 0.25× pre-P RMS amplitude; (ii) margin — the
  observed ridge's global dominance over the published-coordinate family
  is worth less than 0.25× pre-P RMS of coherent energy at the published
  coordinates. Reading (ii) is the calibration-relevant complement to the
  leave-one-out fragility result.

## Countersign status

Round 1: NOT COUNTERSIGNED (one P1 — the literal α = 8 failure — upheld
and driving the single fix round). Final bounded review: COUNTERSIGNED as
a stop-and-report record; two P2s recorded non-blocking. This adjudication
closes the card; draft integration is deferred to the combined
calibration-results fold (one bounded review over all surviving
calibration cards), where the α* result enters with its disclosure.
