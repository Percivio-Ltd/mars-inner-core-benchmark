# Final bounded review — Seismica draft fix round

## VERDICT

**COUNTERSIGNED.** No new P0-grade defect was introduced by the fix round. The nine prior P1 paths are substantively repaired, the manuscript now preserves the three-feature taxonomy, and the newly attached values agree with their recorded artifacts. The bounded residuals below are P2 only and do not withhold the countersign under the mandated severity ratchet.

## Nine-row P1 resolution table

| Finding | Fixed? | Correct? | Note |
| --- | --- | --- | --- |
| 1. LOO conflation of the target-box maximum and shallow 602-family branch | Yes | Yes | The abstract, non-technical summary, §4.3, §5.1, conclusions, and Fig. 2 list now distinguish the target-box maximum `(601.95, -6.67)`, the shallow LOO landing family, and the displaced ridge. `loo_table.csv` confirms six landings at `601.95–606.35 s`, `-3.434…0.0 s/deg`; none is in `[-7.1, -5.9]`, and the target-box maximum never becomes the argmax. |
| 2. False “two registered readers” account / mixed power windows | Mostly | Yes in the manuscript; one P2 companion residue | The draft correctly describes one argmax implementation, the 1-s power-window A/B/C ridge at `662.05/662.20/662.80 s`, the 20-s A/B/C maxima at `663.80/664.10/664.85 s`, and canonical `+59.8 s`. `NUMBERS.md` rows 14–15 and caution 3 are correct. `NUMBERS.md:36` still says the jitter result explains part of “+58 s”; this is a stale P2 shorthand, not a manuscript claim or a new P0. |
| 3. Operator robustness overstatement and wrong ablation-window coordinate | Yes | Yes | The recorded invariant is now used: the target-box maximum is non-global under both operators, the envelope-A winner is operator-sensitive, and the ridge survives in B/C. The ablation CSV confirms A/20-s argmax `(603.25, -3.5354)`, A/1-s argmax `(601.90, -3.5354)`, and the distinct A/20-s target-box cell `(602.45, -6.5657)`. |
| 4. Detection/significance/phase-identity ceiling violations | Yes | Yes | The prohibited “detection present,” “not noise,” and model-predicts-detectability formulations are gone. The replacement language is limited to a supported local maximum inside the target box, conditional occupancy, and kinematic consistency in the bounded registered query. No fixed sentence asserts false-alarm significance or phase identity. |
| 5. Inverted “1.21× less power” statement | Yes | Yes | The conclusion now reports target/ridge `0.83×`, or `17%` less; `sig_statement_reading.json` gives `0.7736156900 / 0.9326603163 = 0.829472`. Elsewhere the reciprocal `1.205586` is correctly stated in the ridge's favor. |
| 6. Misclassification of the other three events | Yes | Yes | The draft and `NUMBERS.md` name S1102a, S1153a, and S1415a as reserved `set=validation` events rather than lane exclusions. `manifest/event_table.csv` contains 23 `vespagram` and exactly these three `validation` rows at `73.3/84.8/88.2°`. |
| 7. Overbroad “flagged by no other diagnostic” | Yes | Yes | The abstract, §4.3, and §5.1 now say S0325a and S0864a were not flagged by the registered resampling diagnostics, which is the scope established by the record. |
| 8. UCLA availability and MPS-only status | Yes | Yes | The abstract makes MPS-only status prominent; Methods names the public `UCLA_v4` MATLAB archive and says it was not reproducibly executed; §4.1 records 26/26 `succeeded_mps_only`, strict `mps_ucla_verified` failure, and acceptance by design. This matches `paper0_run_manifest.json` and the recorded UCLA inventory boundary. |
| 9. Missing composition/distance identifiability limit | Yes | Yes | §4.3 and §5.3 now reproduce the artifact's limit: within the fixed event table, mean selected distance is a deterministic function of composition, so the two effects are not separately identifiable. The added per-design FWE wording also matches `comp_assoc_reading.json`. |

Requested `NUMBERS.md` spot-check: the 1-s and 20-s bands, canonical A/20-s displacement, ablation coordinates including `(602.45, -6.57)`, FWE union and signs, 23+3 event split, and six LOO landing ranges all match the recorded CSV/JSON artifacts. The sole numerical wording residue is the `+58 s` shorthand at line 36 noted below.

## Residual P2 observations (recorded only)

1. `papers/Paper0/manuscript/NUMBERS.md:36` retains “of +58 s” in the jitter row. It should say “of +59.8 s” to satisfy the companion's own canonical-displacement rule; the manuscript itself uses `+59.8 s` consistently.
2. `DRAFT_seismica.md:3` and `NUMBERS.md:1` still label themselves v0.1 although this fix round is v0.2. This is presentation/version bookkeeping only.
3. The non-technical summary's “secondary feature at the reported location” (`DRAFT_seismica.md:53–54`) is a looser gloss than “supported local maximum inside the published-pair target box.” Its following LOO sentence does preserve the essential third-feature distinction, so this does not recreate the prior conflation or detection claim.
4. The pre-existing operator-ablation provenance limitation remains: its rows are `current_provenance_status=not_required`. The draft now explicitly bounds this in §5.3 and the Fig. 4 note; a provenance-enforced rerun remains required before panel 4a is submitted claim-bearingly.

## External-collaborator readiness of v0.2

Version 0.2 is ready for a substantive external-collaborator conversation: its headline now accurately says that the public primary 20-s reconstruction has a supported target-box maximum that is non-global, a `+59.8 s` displaced argmax, and a ridge whose rank-1 status is LOO-fragile against a distinct shallow-slowness branch—not that the target-box feature trades rank 1 with the ridge, proves a detection, or refutes the published claim. The stale companion shorthand and version labels should be cleaned before circulation if convenient, and the already-disclosed ablation provenance item remains a submission-stage condition, but none is material enough to withhold this countersign.
