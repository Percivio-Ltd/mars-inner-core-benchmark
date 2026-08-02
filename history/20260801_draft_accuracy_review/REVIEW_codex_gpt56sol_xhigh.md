# Independent accuracy review — Seismica draft v0.1

Review baseline: clean `a5432f3be6940b3fd161880c48fdd3233d225280`. This was a read-only review of the two manuscript files against the named repository authorities. No network access, other model, or repository mutation was used.

## VERDICT

**BLOCKED.** No P0 was found. The draft is numerically much stronger than an ordinary v0.1, but the following P1 findings must be repaired before it is shown to a potential external collaborator as a claim-bearing scientific draft:

1. **P1 — the central LOO narrative conflates two different 602-s features.** The target-box maximum is `(601.95 s, -6.67 s/deg)`. The six LOO flips instead land at `601.95–606.35 s` and `-3.434…0.0 s/deg`; none is in the registered target-box slowness interval `[-7.1, -5.9] s/deg`. The LOO result establishes single-event fragility of the displaced ridge against a third, time-adjacent/shallow-slowness family, not a flip between the target-box maximum and the displaced ridge.
2. **P1 — the “two registered readers, one feature” explanation is false.** `read_sig_statement.py` selects a pre-existing `detect_peaks.py` table row; it does not independently calculate an argmax. The `662.05/662.20/662.80 s` band comes from the `1.0 s` power-window A/B/C rows, while `663.80 s` is the A/`20.0 s` row. The difference is lane configuration, not two reader definitions.
3. **P1 — operator robustness is overstated and attached to the wrong ablation coordinate.** The abstract implies that the displaced `663.8 s` ridge is the winner under every tested configuration, and the conclusion says operator choice does not explain the displacement. The record says the envelope-A winner is operator-sensitive. For the primary `20.0 s` A lane, the principal-axis winner is `(603.25 s, -3.535 s/deg)`; `(601.90 s, -3.535 s/deg)` is the separate `1.0 s` row.
4. **P1 — several sentences exceed the registered detection/phase-identity ceiling.** “The published detection is therefore present,” “rather than one being noise,” “the model ... predicts a detection,” and the non-technical claim that “the detection is not yet robust” go beyond the claims matrix. Paper 0 establishes supported target-box statistics and conditional stability, not detection significance, noise rejection, or phase identity.
5. **P1 — “1.21× less power” is mathematically wrong.** The recorded ratio is ridge/target `= 1.205586`; equivalently, the target has `0.82947×` the ridge power, or about `17.05%` less power. “The ridge carries 1.21× the target's power” is correct.
6. **P1 — the 23/26 sample description gives the wrong status for the other three events.** `S1102a`, `S1153a`, and `S1415a` are registered `set=validation` events, processed but reserved from the stack. They are not three events “excluded by documented lane rules.”
7. **P1 — “flagged by no other diagnostic” is broader than the record.** `S0325a` and `S0864a` were not flagged by the registered T2READ/COMP-ASSOC resampling diagnostics. The authorities do not establish that no other diagnostic flagged them.
8. **P1 — the UCLA limitation is internally inconsistent and overstates public unavailability.** A concrete public `UCLA_v4.zip` archive is recorded, but no MATLAB/Octave executable or maintained, validated wrapper was available. The correct limitation is that the UCLA stage was not reproducibly executed in this pipeline and exact author-side equivalence is unavailable—not that the UCLA half is simply “not publicly runnable.”
9. **P1 — the composition result omits its registered identifiability limit.** The same-data-calibration clause is present, which is good, but the draft must also state that mean selected distance is a deterministic function of event composition in the fixed table, so distance and composition effects are not separately identifiable from these products.

The binding overall interpretation—**reproducible non-agreement plus internal fragility under a public reconstruction, not a refutation**—is stated correctly in the abstract and §5.4. The P1s above concern what, exactly, is fragile and what the artifacts permit the manuscript to call a detection.

## NUMBER-FIDELITY findings

### NF-1 — canonical displacement and mixed lane values (P1)

- **Draft text:** “`58–60 s` late” (lines 22, 183), “`662.0–662.8 s` ... across envelope variants A–C” followed by “lane A (`663.8 s`)” and “two registered readers” (lines 187–190), and “`~58 s` away” (line 352).
- **Artifact value:** the registered primary public lane is `paperfaith/envelope/A/montalbetti_kanasewich_1970/nth_root/20.0 s`; its supported PKiKP-window argmax is `663.80 s`, so the displacement from `604.0 s` is exactly `+59.80 s`. The `1.0 s` power-window A/B/C rows are `662.05`, `662.20`, and `662.80 s`, respectively. They are different normalization variants at a different power-window setting, not outputs of a second argmax reader.
- **Files:** `history/20260726_publication_assessment/sig_statement_reading.json` (`lane`, `pkikp.global`); `results/tables/peak_comparison.csv` A/B/C `nth_root/1.0` and A `nth_root/20.0` rows; `scripts/03_vespagram/detect_peaks.py:23-28,161-200,313-314`; `history/20260726_publication_assessment/read_sig_statement.py:61-72`; `papers/Paper0/manuscript/NUMBERS.md:13-15,59-65`.

Use one headline value: **`+59.8 s`**, defined as `663.80 - 604.00 s` for the registered A/20-s lane's supported argmax in the inclusive `550–700 s` PKiKP search window. A cross-variant 1-s result may be reported separately, explicitly labeled.

### NF-2 — ablation winner is attached to the wrong power window (P1)

- **Draft text:** “the ablation's winner is ... `601.9 s, -3.54 s/deg`” (lines 259–262), in a section otherwise discussing the registered primary `20 s` configuration.
- **Artifact value:** principal-axis A/`nth_root/1.0 s` gives `(601.90, -3.5354)`; principal-axis A/`nth_root/20.0 s` gives `(603.25, -3.5354)`. Its 20-s target-box maximum is a different cell, `(602.45, -6.5657)`. The draft and `NUMBERS.md` must bind the chosen coordinate to its power window.
- **File:** `history/20260725_research_pipeline_restock/ablpolop_peak_comparison_operator_ablation.csv:82-83,92-93`; `papers/Paper0/manuscript/NUMBERS.md:37`.

The TauP comparison points `(601.9, -3.54)` and `(662.05, -3.43)` do match `taup_phase_prediction_comparison.csv`; they are the registered **1-s** F1/F2 comparison points and should be labeled that way when used alongside the 20-s primary result.

### NF-3 — inverted power statement (P1)

- **Draft text:** “ranks 6,938th in the lane with `1.21× less power` than [the] ridge” (lines 350–352).
- **Artifact value:** target power `0.7736156900`; ridge power `0.9326603163`; ridge/target `1.2055860918`. The target is `0.829472×` the ridge, or `17.0528%` lower—not “1.21× less.”
- **File:** `history/20260726_publication_assessment/sig_statement_reading.json` (`pkikp.global.power`, `pkikp.published_target.power`, `S3_power_ratio_global_over_published_target`).

The abstract and §4.2 use the ratio correctly (“ridge carries `1.21×` the target's power” / “ratio in the ridge's favor”).

### NF-4 — LOO magnitudes are correct, but their omitted landing coordinates change the interpretation (P1)

- **Draft text:** “argmax jumps `57.5–61.9 s`; ... seventeen ... at most `0.95 s`” and flips to the “`602-family published-adjacent feature`” (lines 218–228).
- **Artifact value:** the requested recomputation confirms six flips with `|dt| = 57.45–61.85 s`, conventionally reported `57.5–61.9 s`; landing times are `601.95–606.35 s`, reported `602.0–606.4 s`; 17 non-flips have maximum `|dt| = 0.950000… s`. The flip slownesses are:

  - `S0325a`: `602.25 s, -3.4343 s/deg`
  - `S0474a`: `606.35 s, 0.0 s/deg`
  - `S0864a`: `601.95 s, -2.8283 s/deg`
  - `S1012d`: `602.15 s, -2.6263 s/deg`
  - `S1022a`: `602.20 s, -2.8283 s/deg`
  - `S1039b`: `602.05 s, -2.8283 s/deg`

- **File:** `history/20260726_publication_assessment/loo/loo_table.csv:7-8,13,16,18-19`; `loo_verdict.json` (`m1_flip_count`, `m1_flipping_events`, `full_set`).

The magnitudes and counts are faithful. The manuscript must add “time-adjacent but outside the target-box slowness range” and stop presenting this as competition between the target-box cell and ridge.

### NF-5 — event counts are right but their meaning is wrong (P1)

- **Draft text:** “23 events admitted ... (three of the 26 are excluded by documented lane rules)” (lines 114–116).
- **Artifact value:** 26 rows comprise 23 `set=vespagram` plus three `set=validation`: `S1102a`, `S1153a`, `S1415a`. Paper0.md says these are processed through alignment and normalization and reserved for validation.
- **Files:** `manifest/event_table.csv:25-27`; `papers/Paper0/Paper0.md:242-247`.

### NF-6 — high-risk numerals that do match

I checked the remaining claim-bearing numerals and SHA prefixes in the draft and `NUMBERS.md`. No mismatch was found for:

- published `(604 ± 2 s, -6.5 ± 0.6 s/deg)`, the registered boxes, `29.0°/33 km`, grid, support, and vespagram constants;
- `2,693` manifest path+SHA entries (the manifest has 2,695 items, exactly 2,693 of them path+SHA records), 26 events, 23 stack events, and 26/26 `succeeded_mps_only`;
- primary target-box `(601.95, -6.6667)`, rank `6,938`, quantile `0.714108`, power `0.773616`; ridge `(663.80, -3.6364)`, power `0.932660`, ratio `1.205586`;
- PKKP target `(1341.00, -6.9697)`, rank `13,395`, quantile `0.392739`, and the approximate early global near `1236 s, -6.1 s/deg`;
- the six LOO event IDs, 22-event restacks, boundary `632.0 s`, and the derived LOO spans above;
- COMP-ASSOC p-values `0.00389961` and `9.9990e-05`; branch fractions and Wilson intervals `0.635 [0.5663,0.6986]` and `0.550 [0.4808,0.6174]`;
- Type-I occupancy cells at `603.4/602.05/664.0 s` for 50/70/85%; Type-III values `5.0536 s`, `31.2436×`, and `27.8829 s` used as `5.05`, `31×`, and `~28 s`;
- TauP values and consistency flags, `N=200`, the `1,271 passed / 1 skipped / 0 failed` scoped run, and the two draft SHA prefixes `8df5f5c8…` and `f4b3a03a…`;
- the artifact prefixes in `NUMBERS.md`: `d8140daf…`, `53793b24…`, `798268b0…`, `0f927fd4…`, `e7e8cfee…`, and `feff9258…`.

## CLAIM DISCIPLINE findings

### CD-1 — the draft turns ridge fragility into target-detection fragility (P1)

The abstract says “the competition between the two features is fragile”; the non-technical summary describes a reported-location signal and a later signal and says “which of the two wins” flips; §5.1 calls the trade a “detection-adjacent feature” competition; the conclusion says removals flip to the “published-adjacent branch.” In the record there are at least three distinct objects:

1. target-box maximum: `(601.95, -6.67)`;
2. shallow/time-adjacent 602-family: approximately `601.95–606.35 s`, `-3.43…0.0 s/deg` in LOO (F1 is `(601.9,-3.54)` in the 1-s operator/TauP comparison);
3. displaced 662/664-family ridge: primary `(663.8,-3.64)`.

The LOO finding materially strengthens the manuscript, but it strengthens the statement “the displaced ridge's broad-window dominance is single-event-fragile.” It does **not** show that the registered target-box maximum becomes global when one of the six events is removed. This distinction must be explicit in the abstract, non-technical summary, §4.3, discussion, conclusion, and Fig. 2 caption/legend.

### CD-2 — registered detection/significance ceiling is crossed (P1)

The following formulations are not allowed by `Paper0.md:1194,1221-1225`:

- lines 47–53: “a weak signal where the study reported it” and “the detection is not yet robust”;
- lines 192–196: “The published detection is therefore present”;
- lines 239–242: occupancy coexistence “rather than one being noise”;
- lines 264–272: “The model ... predicts a detection at the published coordinates”;
- lines 313–320: “the target-box feature is real” in a model-conditioned-detection argument;
- lines 349–352: “a genuine local maximum exists at the published coordinates.”

Allowed wording is: a **supported local maximum/statistic exists inside the published-pair target box**; it is outside exact coordinate tolerance but inside the uncertainty-folded tolerance; bootstrap reports **conditional stability/occupancy**, not false-alarm significance; the registered TauP query finds PKiKP-family calculations kinematically consistent with the published/target-box neighborhood, without identifying the observed cell as PKiKP. “Not noise,” “published detection present,” and “model predicts a detection” require downstream null/identifiability evidence that Paper 0 explicitly says is pending.

### CD-3 — operator statement contradicts the recorded amendment (P1)

The body correctly states that the exact envelope-A winner is operator-sensitive and that the ridge survives in B/C. The abstract's construction—target feature subordinate under every configuration, followed by “the global stack maximum is a displaced ridge near 663.8 s”—nevertheless reads as if the ridge wins every configuration. It does not. The conclusion's claim that “polarization operator choice ... do[es] not explain the displacement” is likewise too broad: changing the operator moves the 20-s A winner from `(663.8,-3.64)` to `(603.25,-3.54)`, eliminating most of the time displacement while leaving a large slowness mismatch and leaving the target-box maximum non-global.

Use the recorded invariant: **the target-box maximum is non-global under both tested operators; which competing feature wins in envelope A is operator-sensitive; the displaced ridge remains global in B/C.** Do not claim exact-ridge operator robustness.

### CD-4 — TauP interpretation is mostly disciplined, with one blocking sentence (P1)

The explicit §3.3 disclaimer and most of §4.4 comply with the Level-2 cap. “The model ... predicts a detection at the published coordinates” does not. TauP predicts calculated arrivals under a model; it does not predict observability or establish that a measured local maximum is that phase. Replace it with the kinematic-consistency formulation above. Also qualify “zero computed branches” as “zero branches in the registered reference-model query,” because the artifact is a bounded phase/model sweep, not a universal phase exclusion.

### CD-5 — bootstrap fidelity is correctly disclosed, but one inference is not (P1)

The draft correctly says `methods_robustness_200`, `N=200`, and “not ... equivalent to the published bootstrap” in Methods, and repeats the methods-robustness limitation in Discussion. That satisfies the requested fidelity check. The sentence “the two families coexist at comparable bootstrap occupancy rather than one being noise” crosses the separate registered rule that bootstrap stability is not detection significance or false-alarm evidence. Stop after “both occupancy families occur under the registered conditional resampling.”

### CD-6 — composition wording needs the complete honesty clause (P1)

The same-data-calibration clause appears in §3.3, §4.3, and §5.3 and should be retained. Add the artifact's identifiability sentence: “Within the fixed event table, mean selected distance is a deterministic function of composition; distance and composition effects are not separately identifiable from these products.” Also report the FWE result by design rather than only saying events “concentrate” on two common positives: Type I positive FWE events are `S1039b` and `S1022a`; Type II additionally has positive `S0474a` and `S1012d` and negative `S0820a` and `S0484b`.

### CD-7 — MPS-only limitation is prominent but not yet fully correct (P1/P2 split)

The largest fidelity gap is prominently named in Methods and §5.3, and the draft correctly records 26/26 `succeeded_mps_only`. The factual formulation needs repair: the repository records a public `MATLAB_ALTERNATIVES/UCLA_v4.zip` archive, but no resolved MATLAB/Octave executable or maintained validated wrapper. Say that the UCLA stage was not reproducibly executed and the accepted run is MPS-only. In §4.1, replace the shorthand “all stages green, 26/26 deglitch attestations” with the exact record: every configured stage succeeded and all 26 events were `succeeded_mps_only`, while strict `mps_ucla_verified` remained `fail` and `accepted_partial_lane_by_design=true`. Adding “MPS-only” explicitly to the abstract would make this largest fidelity gap appropriately prominent for external readers (emphasis aspect is P2; the public-availability mismatch is P1).

### CD-8 — binding conclusion is otherwise correct

The draft repeatedly says this is not the authors' pipeline, not a refutation, and that exact author-side deglitching or polarization could suppress the ridge. Those statements accurately preserve the recorded boundary. The defensible headline after repair is:

> The registered public reconstruction reproducibly does not place the target-box maximum at rank 1; its primary 20-s PKiKP-window argmax is displaced by 59.8 s, and that displaced ridge's rank-1 status is single-event-fragile against a separate shallow-slowness, time-adjacent branch. This is public-pipeline non-agreement plus internal fragility, not a refutation or phase-identification result.

## CAUTION-3 RESOLUTION

### 1. `detect_peaks.py` GLOBAL-row semantics

The relevant implementation is:

```python
# scripts/03_vespagram/detect_peaks.py:27-28
PKIKP_WINDOW = (550.0, 700.0)
PKKP_WINDOW = (1200.0, 1500.0)

# scripts/03_vespagram/detect_peaks.py:161-176,188
mask_t = (t_axis >= t_min) & (t_axis <= t_max)
finite_supported = np.isfinite(data) & (support_counts >= int(minimum_support))
candidate_mask = finite_supported[:, mask_t]
sub = np.where(candidate_mask, data[:, mask_t], -np.inf)
idx = int(np.argmax(sub))

# scripts/03_vespagram/detect_peaks.py:313-314
p = find_global_peak(v, t, s, *PKIKP_WINDOW, support_counts, minimum_support)
q = find_global_peak(v, t, s, *PKKP_WINDOW, support_counts, minimum_support)
```

Thus a PKiKP `peak_label=global` row is **not the whole-time-grid maximum**. It is the maximum over all slowness rows in the artifact and the **inclusive 550–700 s time window**, after excluding non-finite cells and cells with support below `minimum_support`. For the relevant products the slowness grid is `-10…0 s/deg` (100 points), `minimum_support=2`, and the winning cells have support 23.

The draft's `662.0–662.8 s` band comes specifically from these three peak-table rows:

- `paperfaith/envelope/A/montalbetti_kanasewich_1970/nth_root/1.0`: `662.05 s, -3.4343 s/deg`;
- the corresponding B/`1.0` row: `662.20 s, -3.4343 s/deg`;
- the corresponding C/`1.0` row: `662.80 s, -3.6364 s/deg`.

It is therefore the released-scale **1-s power-window A/B/C band**, not the primary 20-s A/B/C band and not a whole-grid result. At 20 s, the A/B/C maxima are `663.80`, `664.10`, and `664.85 s`.

### 2. `read_sig_statement.py` “global” semantics

`read_sig_statement.py` does not read the NPZ or execute another support/window argmax. It identity-gates `peak_comparison.csv`, then selects an already generated PKiKP/global row using a recorded endpoint:

```python
# history/20260726_publication_assessment/read_sig_statement.py:61-72
candidates = [
    r for r in rows
    if r["phase"] == "PKiKP" and r["peak_label"] == "global"
    and r["mode"] == "paperfaith" and r["norm_variant"] == "A"
    and r2(r["time_s"]) == RECORDED["pkikp_global"][0]
    and r2(r["slowness_sdeg"]) == RECORDED["pkikp_global"][1]
]
g = candidates[0]
lane = {k: g[k] for k in LANE_FIELDS}
```

`RECORDED["pkikp_global"]` is `(663.80, -3.64)` (`read_sig_statement.py:16-20`). That endpoint uniquely selects the `paperfaith/envelope/A/montalbetti_kanasewich_1970/nth_root/20.0` table row. Its “global” semantics are inherited from `detect_peaks.py`: supported argmax over the inclusive 550–700 s window and all slowness rows. The significance reader adds no different support or window rule; it selects the row and computes target-rank/quantile/power-ratio reporting from it.

### 3. Is “two registered readers, one feature” exactly right?

**No.** There is one peak-table argmax implementation plus a later registered table-row selector. The reported cells may reasonably be described as neighboring cells on the same broad ridge, but the numerical difference arises from comparing `power_window_s=1.0` A/B/C rows with the primary `power_window_s=20.0` A row. Calling them “two registered readers” obscures the actual sensitivity parameter and falsely suggests independent computational confirmation.

### 4. Recommended canonical displacement

Use **`+59.8 s`**, defined as:

> `663.80 s - 604.00 s` for the supported argmax in the inclusive `550–700 s` PKiKP window, across the full `-10…0 s/deg` slowness grid, in the registered primary `paperfaith/envelope/A/montalbetti_kanasewich_1970/nth_root/20.0 s` lane (`minimum_support=2`, winning support `23`).

Recommended submitted wording:

> In the registered primary 20-s public lane, the supported PKiKP-window argmax is at 663.80 s and -3.64 s/deg, 59.80 s later than the published 604.00-s time. The separate 1-s power-window sweep places the analogous ridge at 662.05–662.80 s across normalization variants A–C.

Do not call the supported PKiKP-window argmax the whole-grid “global stack maximum.”

## P2 list

These findings are non-blocking individually. Items already in `docs/research_pipeline.md` remain P2 under the severity ratchet.

1. **Recorded target-box gloss (ratcheted P2; do not escalate):** §4.2 correctly says `(601.95,-6.67)` is the target-box maximum, but the conclusion says a maximum “exists at the published coordinates” (lines 349–351), and `NUMBERS.md:53-54` incorrectly says the draft fully complies. Replace every shorthand with “maximum inside the published-pair target box.”
2. **Operator-ablation provenance (ratcheted P2; do not escalate):** every row in `ablpolop_peak_comparison_operator_ablation.csv` has `current_provenance_status=not_required`. The backlog explicitly requires a provenance-enforced rerun before external claim-bearing use. Draft v0.1 uses the ablation numbers without surfacing that status; Fig. 4 must not become a submitted claim-bearing figure until the recorded P2 is discharged or explicitly bounded.
3. **MPS-only emphasis:** add the exact MPS-only/strict-attestation-fail status to the abstract and §4.1. The gap is in Methods and Limitations already, so this is prominence rather than absence.
4. **PKKP omission:** the draft gives the PKKP target/global and TauP side, but omits the recorded contrast that PKKP occupancy is stable-early and concordant between Type I and Type II at all three thresholds. The Type II cells are `1235.4/-6.667` (50%), `1236.0/-6.162` (70%), and `1234.5/-5.859` (85%). This would strengthen, not weaken, the honesty of the PKiKP-specific fragility interpretation.
5. **Controls table/supplement:** the manuscript says controls accompany claim-bearing steps but does not report the important outcomes compactly: LOO full-set exact reproduction and S1015f byte-identical repeat; COMP-ASSOC positive and adverse-lane outcomes; TauP 10° adverse; strict MPS+UCLA fail/accepted-partial status. Add a methods/results control table or supplement rather than leaving all outcomes only in the repository record.
6. **FWE detail:** “concentrated on S1039b and S1022a” is too compressed. Report the Type-I and Type-II signed FWE sets explicitly, especially the two Type-II negative events, to avoid one-directional selection emphasis.
7. **Overbroad reproducibility phrasing:** “all of this is reproducible to the byte” (line 357) is broader than the explicitly demonstrated byte controls. The peak table was byte-identical across runs and the LOO S1015f repeat was byte-identical; say which artifacts were byte-identical.
8. **Review wording:** “three ... reviews ... zero critical findings” (lines 164–166) uses “critical” ambiguously. The record says zero P0, while prior reviews did record P1s that were subsequently repaired or narrowed. State that directly if the review history is retained in the manuscript.
9. **Submission completeness/retention family:** figures and tables remain plans; several references are marked “TBD”; the DOI capsule is prospective. The recorded P2 retention items (exact skip identities, direct fresh-NPZ TauP query, full stage/status retention) should be discharged in the submission evidence package, not presented as already complete.
10. **Promotional claim:** “the public robustness analysis of record” (line 342) is unnecessary and not established by an artifact. The narrower “a public, runnable robustness benchmark” is supported.

## Overall assessment for external-collaborator readiness

This draft is **not yet ready to show a potential external collaborator as a claim-bearing manuscript**. Its provenance map is unusually good, nearly all load-bearing numbers and hashes are accurate, the MPS-only/bootstrap limitations are substantially present, and the governing “non-agreement plus internal fragility—not refutation” stance is sound. The blocker is that the current prose merges the target-box maximum with a distinct shallow-slowness LOO branch, misdescribes the 662.x/663.8 difference as two readers rather than two power-window configurations, overstates operator invariance and detection significance, and inverts the power ratio once in the conclusion. These are bounded, repairable problems: after the P1 wording/attachment fixes, a provenance-enforced ablation rerun or explicit P2 bounding, and a focused recheck of abstract/body/conclusion/figure captions against the three-feature taxonomy, the draft should be suitable for a collaboration conversation.
