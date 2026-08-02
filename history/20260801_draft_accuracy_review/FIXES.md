# Fix-round record — Seismica draft v0.1 → v0.2 (2026-08-01)

Review: `REVIEW_codex_gpt56sol_xhigh.md` (Codex `gpt-5.6-sol` at `xhigh`,
read-only, against clean `a5432f3b`). Verdict: BLOCKED — zero P0, nine P1.
This record maps each finding to its resolution in the fix round (lead-applied
edits to `papers/Paper0/manuscript/DRAFT_seismica.md` and `NUMBERS.md`).
Load-bearing review claims were independently re-verified against the
artifacts before editing (LOO landing slownesses via the generated Table 2;
1-s vs 20-s peak-table rows and the ablation A/20-s cells via direct CSV
extraction; the three `set=validation` events via `manifest/event_table.csv`).

## P1 resolutions (all fixed)

1. **LOO conflation of 602-features** — adopted the three-feature taxonomy
   (target-box maximum / shallow 602-family branch / displaced ridge) in the
   abstract, non-technical summary, § 4.3 (rewritten, retitled "The ridge's
   rank-1 status is six-events fragile"), § 5.1, conclusions, and the Fig. 2
   entry. Flip landing coordinates (602.0–606.4 s at −3.43…0.0 s/deg,
   outside the target-box slowness range) now stated; "the target-box
   maximum never becomes the argmax" stated explicitly.
2. **"Two registered readers" false** — replaced with the one-implementation
   statement: `detect_peaks.py` supported 550–700 s argmax; the 662.05–662.80
   band is the 1-s power-window A/B/C rows; 20-s rows are 663.80/664.10/
   664.85; `read_sig_statement.py` selects the recorded 20-s A row.
   Canonical displacement fixed at **+59.8 s** everywhere ("58–60" removed).
3. **Operator overstatement / wrong window attachment** — abstract now states
   the recorded invariant (target-box maximum non-global under both
   operators; envelope-A winner operator-sensitive; ridge survives B/C);
   § 4.4 binds coordinates to windows (603.25 s at 20 s; 601.90 s at 1 s)
   and states that the swap removes most of the time displacement in A while
   leaving the slowness mismatch and subordination; conclusions no longer
   list operator choice among "does not explain".
4. **Detection-ceiling violations** — removed/replaced: "weak signal where
   the study reported it", "the detection is not yet robust" (non-technical
   summary); "published detection is therefore present" (§ 4.1); "rather
   than one being noise" (§ 4.3); "model predicts a detection" (§ 4.4, now
   "asymmetry of model consistency, not a prediction of detectability");
   "target-box feature is real" (§ 5.2); "genuine local maximum exists at
   the published coordinates" (conclusions). Standard wording: "supported
   local maximum inside the published-pair target box".
5. **"1.21× less power" inversion** — conclusions now state "0.83× the power
   of (17% less than)" with the ratio in the ridge's favor elsewhere.
6. **23/26 events** — § 2 now names S1102a/S1153a/S1415a as registered
   `set=validation` events (73–88°), processed but reserved; "excluded by
   documented lane rules" removed.
7. **"Flagged by no other diagnostic"** — narrowed to "not flagged by the
   registered resampling diagnostics" (abstract, § 4.3, § 5.1).
8. **UCLA availability** — § 3.1 and § 5.3 now state the public `UCLA_v4`
   archive exists but no maintained executable route was available, the
   UCLA stage was not reproducibly executed, strict `mps_ucla_verified`
   failed, and the MPS-only lane is accepted by design; § 4.1 uses the exact
   run status; abstract carries MPS-only prominently.
9. **Identifiability clause** — added to § 4.3 (composition bullet) and
   § 5.3: distance and composition effects are not separately identifiable
   within the fixed event table.

## P2 disposition

Folded into sentences already being rewritten (no scope expansion): FWE
per-design detail incl. Type II negatives (§ 4.3, Table 2); byte-identical
scoping (conclusions iv); "zero critical findings" → "zero P0, P1s repaired
and re-reviewed" (§ 3.2); "of record" → "a public, runnable robustness
benchmark" (§ 5.4); MPS-only abstract emphasis (with P1-8); target-box gloss
in conclusions (with P1-4/5); ablation `current_provenance_status=not_required`
disclosure (§ 5.3 + Fig. 4 note — rerun itself remains an open recorded P2).

To backlog (recorded in `docs/research_pipeline.md`, not fixed in-cycle):
PKKP occupancy stable-early contrast; compact controls table/supplement;
submission completeness/retention family (references, DOI capsule, retention
items).

## Final review outcome (cycle closure)

The one bounded final review (`FINAL_REVIEW_codex_gpt56sol_xhigh.md`, same
reviewer, restricted to the fixes) returned **COUNTERSIGNED** with zero new
P0 and verified all nine resolutions against the recorded artifacts. Residual
P2 disposition: (1) `NUMBERS.md:36` "+58 s" → "+59.8 s" and (2) v0.1 → v0.2
version headers in both files were applied post-countersign as lead cleanup
before landing; (3) the non-technical-summary gloss is recorded as acceptable
(the reviewer confirms it does not recreate the conflation); (4) the
provenance-enforced ablation rerun remains the recorded submission-stage
condition in `docs/research_pipeline.md`. No further review rounds occur.

## Figures

Figs 1–4 and Tables 1–2 were generated before the fix round by
`papers/Paper0/manuscript/make_figures.py` (pinned inputs, asserted controls,
provenance sidecar; commit `cccb8cfa`). The figures encode per-window and
per-design values directly from the artifacts and required no change under
the review; the Fig. 2/Fig. 4 caption obligations are recorded in the
draft's figure list.
