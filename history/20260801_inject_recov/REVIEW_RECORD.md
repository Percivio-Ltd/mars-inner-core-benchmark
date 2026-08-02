# P0-INJECT-RECOV — delegated-cycle review record (2026-08-01)

Implementation: Codex gpt-5.6-sol xhigh wrote inject_and_stack.py +
collect_recovery.py (codex/impl_out.md); sub-Fable line-by-line review
before execution: no P0/P1 defects.

Countersign round 1 (codex/countersign_r1_out.md): NOT COUNTERSIGNED.
One P1: the frozen alpha=8 positive control fails on the literal
"within one grid cell" reading (603.90 s = two 0.05-s time cells from
604.00; slowness within one cell); continuing to interpretation leaves the
card's acceptance provenance unresolved. All other checks passed (gate
fidelity, alpha=0, provenance handling, determinism, recovery extraction).

Fix round (single): tripwire remedial path executed to the letter —
convention re-verified exact against stacking.py (23/23), alpha/a8r rerun
byte-identical, memo converted to a STOP-AND-REPORT record with the
adjudication package; outcomes marked provisional. No data, script, table,
or registered element altered.

Final review (codex/countersign_r2_out.md): VERDICT: COUNTERSIGNED —
"solely for the STOP-AND-REPORT record, not a passed-control result."
Recorded P2 observations (non-blocking, not fixed in-cycle, backlog):
1. P2: substantive detectability interpretation remains in the memo,
   bounded as non-final by the provisional/lead-adjudication language.
2. P2: the memo's mechanism attribution names the 20-s Hann smoothing
   specifically, though the frozen outputs do not isolate that stage from
   envelope smoothing and nonlinear stacking; the convention check,
   alpha-monotone convergence, and pull direction are supported.

MEMO.md is preserved exactly as countersigned; this file records the rounds.
