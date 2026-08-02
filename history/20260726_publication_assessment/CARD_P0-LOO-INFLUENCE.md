# CARD P0-LOO-INFLUENCE — registered leave-one-out event influence

Registered 2026-07-26 by the lead, BEFORE implementation and BEFORE any
leave-one-out result exists, under operator direction ("Yes, run them").

## Scientific question

Does removal of any single event from the 23-event set change which
branch wins the global maximum in the registered primary PKiKP lane?
This quantifies "the detection depends on 1-2 events" for publication
(reviewer-anticipated), as a different estimand from the recorded
COMP-ASSOC inclusion-difference test.

- Criterion linkage: § A.4 benchmark surface, E.4 row-4 confidence;
  publication framing per `PUBLICATION_ASSESSMENT.md`.
- Artifact: per-event LOO argmax table + JSON verdict under
  `history/20260726_publication_assessment/loo/`, SHA-256s in the
  ledger.

## Prior-knowledge disclosure

COMP-ASSOC (recorded) flagged S1039b and S1022a by inclusion-difference
under resampling designs; the branch competition is known
composition-associated. LOO is a distinct estimand (deterministic
22-event restack per held-out event, full-set grid argmax). No rule
below is tuned to those events; all 23 events are treated identically.

## Registered rules (frozen)

1. Lane: the registered primary PKiKP lane exactly as selected by
   CARD_P0-SIG-STATEMENT rule 2 (same combo; same grid; same inputs).
2. For each event e in the 23: recompute the lane vespagram from the
   identical normalized/aligned per-event inputs excluding e (22
   events), identical grid and stacking parameters, through the existing
   production loaders/stackers (`run_vespagrams.load_combo_data` +
   `stacking` functions); take the global argmax over the full grid.
3. Branch classification: frozen pass-2 boundary t_b = 632.0 s —
   argmax time < 632.0 s → 602-family; ≥ 632.0 s → 662-family.
4. M1 (material, confirmatory): any event whose removal flips the
   global-argmax branch relative to the full-set branch.
5. M2 (descriptive): per-event |Δt|, |Δs| of the argmax vs full set;
   flip count; the identity of flipping events.
6. Provenance: the LOO runner must consume the same provenance-gated
   inputs as production (fail closed on missing provenance); it must
   not write into `results/` production paths (outputs only under the
   card's history directory or a declared scratch path).

## Controls

- Positive: the runner's full-set (23-event) recomputation must
  reproduce the recorded current-gate global argmax cell
  (663.80 s, −3.64 s/deg) exactly; mismatch aborts the card (runner
  defect, not a result).
- Adverse (fail-closed): a nonexistent event ID must error; an
  inconsistent input manifest (one per-event input removed on a scratch
  copy) must fail the provenance gate, not silently restack.
- Determinism: one held-out recomputation repeated; identical argmax
  and identical output hash.

## Implementation route

Codex implementation cycle (bounded): new script
`scripts/03_vespagram/loo_influence.py` + tests, reusing existing
loaders/stackers; no modification to production vespagram scripts,
`detect_peaks.py`, or any registered surface. Fable diff review before
first scientific execution; cycle rules per AGENTS.md.

## Stop condition

23 LOO rows + verdict JSON + ledger Done entry stating M1 events (or
none) under the frozen boundary. Runtime guard: if a single restack
exceeds ~10 minutes, report cost after 3 events before continuing
(long-run procedure). No re-tuning of t_b or lane after results.

## Registered amendment 1 (2026-07-26, pre-execution)

Trigger and timing: the implementation's single authorized full-set
positive control FAILED CLOSED (exit 2, no artifacts written) because
rule 2's literal "global argmax over the full grid" is internally
inconsistent with this card's own positive control. The recorded
control cell (663.80 s, −3.64 s/deg) is defined by the production peak
rule `detect_peaks.find_global_peak`: the argmax over the inclusive
PKiKP window `PKIKP_WINDOW = (550.0, 700.0)` s (`detect_peaks.py:27`),
all slownesses, restricted to finite cells with stack support ≥
`DEFAULT_MIN_STACK_SUPPORT` (= 2) (`detect_peaks.py:161-176`). Over the
full −100…2200 s axis the maximum sits at the double grid edge
(−86.95 s, −10.0 s/deg), outside both registered branch families, and
the control can never pass. No hold-out restack was executed and no LOO
outcome has been observed; the only inspected outcome is the full-set
field, whose windowed argmax was recorded before this card existed.

Amended rule 2 (replaces the argmax clause only): take the global
argmax by the production rule —
`detect_peaks.find_global_peak(field, t_axis, s_axis, *PKIKP_WINDOW,
support_counts, DEFAULT_MIN_STACK_SUPPORT)`; a blocked or otherwise
non-ok peak status is a runner failure (fail closed), never a
classified result. Loaders, stackers, grid, lane, the 632.0 s boundary,
M1/M2, all controls, and every other rule are unchanged. The branch
families are subsets of the window: [550, 632) → 602-family,
[632, 700] → 662-family.

Not outcome-fitted: the amendment adopts the pre-existing registered
production definition (the same rule that produced the recorded control
cell and the SIG-STATEMENT endpoints), was forced by a failed-closed
positive control, and precedes any leave-one-out execution.
