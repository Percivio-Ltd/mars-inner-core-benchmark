# P0-DECOY-FAM — lead adjudication of the stop-and-report (2026-08-01)

Card: `docs/research_pipeline.md` § "P0-DECOY-FAM — decoy-box family
statistic", registered at commit `a2163d49` (frozen; chain recap corrected by
registered amendment 1, dated, pre-outcome). Worker memo: `MEMO.md` in this
directory (SHA-256 `b69bb92f…`, byte-identical to the run-dir original).
Evidence dir: `/Users/artuskg/marsquake_runs/20260801_decoy_fam/` (per-box
tables `decoy_boxes_pkikp.csv` `163f894d…` and `decoy_boxes_pkkp.csv`
`88c21aee…` remain there — deterministically regenerable, hashes recorded).

## What the run established

1. Gate and reader validity are beyond doubt: the regenerated canonical lane
   is byte-identical to the committed production table (`8df5f5c8…`), and the
   box reader reproduced four independent recorded anchors exactly (gate
   cell, published-target box 0.7736, ridge box 0.9327, PKKP box equal to
   the pre-sweep recorded threshold 0.2143).
2. The frozen adverse control A1 (pre-P box [−90, −50] s × [−7.1, −5.9]
   s/deg must stay below 0.7736) FAILED at 49.37 — independently re-derived
   off the NPZ. Because the reader is proven correct, the failure is a data
   property of the canonical variant-A surface: trace-start/mask-edge
   transients (19/26 events at 5–355× target-window scale immediately after
   their valid-data onsets) survive the min-support-2 mask with supported
   stacked power up to 1395 pre-P, decaying monotonically into the early
   sweep span (band maxima 1395 → 1.8 across [−90, −70] → [150, 250] s;
   largest in-sweep box max 2.397 at t_center = 280 s).

## Adjudication

1. The run is ACCEPTED as a stop-and-report. The adverse control did exactly
   its designed job: it demonstrated, before any family-wise number entered
   the draft, that the card's null design presumed a quiet pre-P/edge
   surface which the canonical variant-A lane does not have.
2. The frozen family fractions are COMPUTED-BUT-CONFOUNDED and are NOT
   accepted as false-alarm-style rates: F_decoy_target_excl 0.2471,
   F_decoy_ridge_excl 0.1771, F_decoy_pkkp_excl 0.7325. The frozen sweep
   span [250, 2100] s includes the demonstrated edge/normalization ramp;
   band-resolved exceedance is 100 % at centers 250–400 s, 0 % at
   800–1600 s, 13.2 %/7.7 % at the late trace edge. A statistic whose
   exceedances are dominated by a demonstrated artifact band cannot be
   quoted as background-competition context for the target reading.
3. The quotable scientific finding of this card is the demonstrated surface
   property itself: the canonical variant-A supported-power surface carries
   an early-time edge/normalization artifact ramp (and a late-edge rise)
   that any family-wise or background statistic over this surface must
   first account for. This is a demonstrated empirical blocker with the
   failing command and evidence preserved (`decoy_reader_run.log`), i.e.
   progress in the sense of AGENTS.md § "What counts as progress" item 3.
4. No post-hoc domain surgery: the band-resolved outcomes have been seen,
   so any restricted-domain family statistic (e.g. excluding t < 600 s) is
   now outcome-exposed and could only ever be labeled exploratory. The
   confirmatory family-rate lane on this surface is CLOSED. If a
   confirmatory family statistic is ever wanted, it needs a fresh card with
   a null design derived from the mechanism (edge-transient exclusion by
   per-event valid-data onset), registered before any new statistic is
   computed, and honestly marked as designed after this run's mechanism
   finding.
5. Countersign: correctly NOT REQUESTED by the worker — the card's
   countersign step presupposed passing controls. Closure is by this
   adjudication record; the severity ratchet applies to its content.

## Effect on the draft

Nothing in the current draft quotes a decoy-family fraction, so nothing is
retracted. The draft's § 5 robustness discussion may cite the demonstrated
edge-ramp property (with this record as evidence) as an additional reason
the uncertainty-folded target-box reading should not be over-read; it must
not quote 0.2471/0.1771/0.7325 as false-alarm rates.
