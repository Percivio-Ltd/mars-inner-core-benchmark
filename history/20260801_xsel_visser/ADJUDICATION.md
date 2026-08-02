# P0-XSEL-VISSER — lead adjudication and landing (2026-08-02)

Card: `docs/research_pipeline.md` § "P0-XSEL-VISSER — cross-selection
sensitivity of the benchmark structure", registered at commit `fe38a196`
before execution. Worker executed across a session-window kill (resumed from
disk 2026-08-02); countersign VERDICT: COUNTERSIGN by exact Codex
`gpt-5.6-sol` at `xhigh` (banner verified; the reviewer independently
recomputed all readouts from the NPZs). Files here are byte-identical copies
from the isolated run dir (`/Users/artuskg/marsquake_runs/20260801_xsel_visser/`,
full 3210-file manifest `ARTIFACTS_SHA256.txt` + addendum): memo
`e7f9eba1…`, countersign `3da51e5f…`, collector `results.json`, variant peak
tables `e5ccee5c…` (XSEL-21) / `725d5c14…` (XSEL-V23).

## Accepted outcomes (frozen readouts, registered lane
paperfaith/envelope/A/nth_root/win20/montalbetti_kanasewich_1970)

| Selection | Global supported argmax | Family/rank | Target-box max | Box rank |
|---|---|---|---|---|
| Canonical 23 | 663.80, −3.6364, 0.9327, sup 23 | 662 / 1 | 601.95, −6.6667, 0.7736 | 6,938 |
| XSEL-21 (intersection) | 663.95, −3.6364, 1.0599, sup 21 | 662 / 1 | 602.10, −6.6667, 0.7336 | 15,809 |
| XSEL-V23 (Visser Table S1) | 663.90, −3.6364, 1.0887, sup 23 | 662 / 1 | 602.05, −6.5657, 0.6765 | 25,172 |

Accepted interpretation (outcome-neutral options registered in the card;
the data selected): the headline benchmark structure is
selection-invariant across the two published 23-event selections and is
already fixed by their 21-event intersection; the published-coordinate box
maximum is subordinate in all three and sinks under the Visser selection.
The non-agreement is not an artifact of the two-event selection
difference. Notable registered detail: S0189a's single removal relocates
the argmax slowness to 0.0 (recorded LOO row), yet the two-event holdout
restores the canonical slowness cell — event interactions are
non-monotone, reinforcing that declared, hash-pinned event lists (not
selection rules) are the reproducible object. The S0325a boundary fact
(39.7 ± 6.1° archived vs 40.8 ± 1.7° in Visser's catalog) is verified for
§ 5.5 use.

## Controls — all card controls resolved

Positive gate bit-exact twice (663.8, −3.6363636363636367,
0.9326603162534909, support 23; 240/240 rows current). Known-answer
holdout singles bit-exact to the recorded LOO rows (S0105a → 663.75,
−3.6364, 1.0123, 22; S0189a → 663.40, 0.0, 0.9771, 22). Adverse
byte-flip on the pre-registered D1 target: enforced detect_peaks failed
closed (`blocked_missing_current_provenance`, no table written), restore
SHA-verified. Deglitch fail path and FDSN stall: not triggered — both
Visser-only events came through the accepted MPS-only lane
(`succeeded_mps_only`, samples modified). Mechanical collector 10/10.

## P2 dispositions (recorded, non-blocking, not fixed in-cycle)

1. Worker's D2 parenthetical "1.0–5.5 s pre-P" is wrong (actual canonical
   spread 0.078–63.556 s); coverage conclusion unchanged. Do not quote the
   parenthetical.
2. The adverse control demonstrates the registered enforcement surface
   (stack-input `.npy`), not a literal raw-mseed flip; raw files are
   outside the registered enforcement surface (disclosed in the memo).
3. Attempt-1 deglitch failure log preserved without the full doubled-path
   evidence (overwritten by the corrected rerun); the failure was a worker
   invocation defect (relative-path cwd), not a lane failure.
4. Session-termination cause (subscription-window exhaustion) is asserted
   from context, not independently logged.

## Consequence

Draft § 5.5 updated (dated addition, covered by the pending bounded v0.5
review): cross-selection execution paragraph + S0325a catalog-boundary
sentence; NUMBERS rows added with sources pinned to this record. The
"levers Visser" operator request (2026-08-01) is thereby discharged with a
countersigned empirical result rather than prose.
