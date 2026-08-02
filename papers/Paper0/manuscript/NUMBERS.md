# Number-provenance companion for DRAFT_seismica.md (v0.6)

Every claim-bearing numeral in the draft, mapped to its recorded artifact.
Rows cite the registered record surface; artifact SHA-256 prefixes are the
identities recorded in `CONTINUITY-paper0.md` / `docs/research_pipeline.md`.

| Draft statement | Value(s) | Source artifact / record |
| --- | --- | --- |
| Published PKiKP pair | 604 ± 2 s, −6.5 ± 0.6 s/deg | Bi et al. (2025); `papers/Paper0/Paper0.md:49` |
| PKiKP target box | 584–624 s × [−7.1, −5.9] s/deg | `Paper0.md:808,1098` (registered) |
| PKKP target box | 1320–1360 s × [−8, −6] s/deg | `Paper0.md:808,1099` (registered) |
| Uncertainty folding example | 2° ≈ 14 s at ~7 s/deg | `Paper0.md:799` |
| Global PKiKP-window maximum | 663.8 s, −3.6364 s/deg, power 0.9327, support 23 | `sig_statement_reading.json` (`pkikp.global`); LOO `full_set.json`; table SHA `8df5f5c8…` |
| 1-s power-window ridge band | A 662.05 / B 662.20 / C 662.80 s (−3.43…−3.64 s/deg); at the registered 20-s window: A 663.80 / B 664.10 / C 664.85 s | `results/tables/peak_comparison.csv` nth_root envelope rows (one argmax implementation, `detect_peaks.py` 550–700 s supported window; the band is a power-window/normalization sensitivity, NOT a second reader) |
| Displacement vs published (canonical) | **+59.8 s** = 663.80 − 604.00, registered primary 20-s A lane, supported argmax in the inclusive 550–700 s window, full −10…0 s/deg grid, min support 2 | `sig_statement_reading.json` (`pkikp.global`); `peak_comparison.csv` A/20.0 global row (`dt_vs_paper_s` 59.80) |
| Target-box maximum | 601.95 s, −6.67 s/deg, power 0.7736 | `sig_statement_reading.json` (`pkikp.published_target`) |
| Target-box rank | 6,938 | `sig_statement_reading.json` S1; claims matrix `Paper0.md:1221` |
| Background quantile | 0.7141 | `sig_statement_reading.json` S2 |
| Power ratio | 1.2056 → "1.21×" | `sig_statement_reading.json` S3 |
| Tolerance flags | outside raw box; within uncertainty-folded | `sig_statement_reading.json` S4 pair |
| PKKP mirror | 1341.0 s, −6.97 s/deg, rank 13,395, quantile 0.3927, within tolerance | `sig_statement_reading.json` (`pkkp_mirror`); claims matrix `Paper0.md:1223` |
| PKKP global | ~1236 s, −6.1 s/deg | BENCH-E2E record |
| Byte-identical reproduction | fresh `peak_comparison.csv` == 2026-07-06 table | SHA-256 `8df5f5c85473…07ce` both runs (BENCH-E2E record) |
| LOO flip count / events | 6 of 23: S0325a, S0474a, S0864a, S1012d, S1022a, S1039b | `history/20260726_publication_assessment/loo/loo_verdict.json`, `loo_table.csv` |
| Flip magnitudes | argmax jumps 57.5–61.9 s; flips land 602.0–606.4 s at −3.43…0.0 s/deg — OUTSIDE the target-box slowness range [−7.1, −5.9]; the target-box maximum never wins | `loo_table.csv` (abs_dt_vs_full_s, slowness_sdeg per flip row) |
| Non-flip bound | ≤ 0.95 s (17 events) | `loo_table.csv` |
| Branch boundary | 632.0 s, frozen pre-execution | `CARD_P0-LOO-INFLUENCE.md` + registered amendment 1 (commit f5d4f043) |
| Determinism control | byte-identical S1015f repeat (NPZ+JSON) | `loo_verdict.json` (`determinism_control`) |
| LOO positive control | full-set restack reproduces 663.8 / −3.6364 exactly | `loo_verdict.json` (`positive_control_full_set_reproduced`) |
| FWE overlap | union over designs: Type I flags S1039b, S1022a; Type II adds S0474a, S1012d (positive) and S0820a, S0484b (negative, non-flips); 4 of 6 flips in the union; S0325a, S0864a unflagged | `comp_assoc_reading.json` `designs.*.per_event[].fwe_flag` + ledger COMP-ASSOC/LOO entries |
| Composition association p | Type I max-T p = 0.0039; Type II p = 1.0 × 10⁻⁴ | `comp_assoc_reading.json` (omnibus_p 0.00389961…, 9.999e-05), SHA `d8140daf…` |
| FWE concentration | S1039b, S1022a (inclusion favors 662) | P0-COMP-ASSOC record |
| Same-data calibration clause | registered honesty clause | P0-COMP-ASSOC card + record |
| Occupancy bimodality | 602/603 s at 50/70%; 664 s at 85% | BENCH-E2E record (Type I occupancy) |
| Branch fractions by design | Type I f662 0.635 [0.566, 0.699]; Type II 0.550 [0.481, 0.617] | `t2read_feature_competition.json` (SHA `53793b24…`) |
| PKKP occupancy concordance | Type I vs II argmax at 50/70/85%: (1236.95, −6.57) vs (1235.40, −6.67); (1234.35, −5.96) vs (1236.00, −6.16); (1234.90, −5.96) vs (1234.50, −5.86); max Δt 1.65 s, max Δs 0.202 s/deg; all concordant (frozen Δt≤5, Δs≤0.5), all nearest early_G1 (1236.05, −6.06) | `t2read_pkkp_argmax.json` (SHA `921d0ba2…`); re-verified with a discriminating time-reversal adverse control: `history/20260801_pkkp_concordance/pkkp_concordance_verification.json` |
| Jitter audit | ±10 s: PKiKP centroid dt 5.05 s, broadening 31.2×; PKKP dt 46.75 s, 68.9×; explains ≤ ~5 s (±10 s) and ≤ ~28 s (60 s lane) of +59.8 s | `t3power_power_comparison.json` (SHA `798268b0…`); P0-C5-T3POWER record |
| Ablation invariance | target-box maximum global under neither operator; subordinate local max operator-robust; envelope-A principal-axis winner BY WINDOW: 601.90 s (1-s row), 603.25 s (registered 20-s row), both −3.54 s/deg; its 20-s target-box max cell is (602.45, −6.57); 662 ridge survives in B/C | `ablpolop_peak_comparison_operator_ablation.csv` (SHA `0f927fd4…`); P0-ABL-POLOP record |
| Ablation controls | 80 operator-independent rows, deltas 0.000; zero M-K-labeled rows in adverse | P0-ABL-POLOP record |
| TauP geometry | 29.0°, 33 km; P 224.131 s, PKiKP 808.136 s (0.01 s positive control) | P0-TAUP-PREDICT record; criterion-6 values |
| Model consistency | published pair + target box ~ PKiKP family (model slowness ≈ −6.36); zero branches for F1 (601.9, −3.54) / F2 (662.05, −3.43) | `taup_phase_prediction_comparison.csv` (SHA `e7e8cfee…`) |
| PKKP kinematics | zero branches for G1/G2/T_box/Pub1; Pub2 (1341.0, −7.0) ~ PKIKKIKP | `taup_pkkp_side_reading.csv` (SHA `feff9258…`) |
| Bootstrap label | `methods_robustness_200`, N = 200 | BENCH-E2E record; `Paper0.md` bootstrap contract |
| Deglitch attestation | 26/26 `succeeded_mps_only`, pinned inventory | BENCH-E2E record; criterion-2 records |
| Event counts | 26 catalogued: 23 `set=vespagram` + 3 `set=validation` reserved (S1102a, S1153a, S1415a at 73–88°) — reserved, NOT "excluded by lane rules"; support 23/23 | `manifest/event_table.csv` rows 24–26; `Paper0.md` event-set split |
| Manifest audit | 2,693 path+sha256 entries; three archives digest-pinned nonresident | `scripts/paper0_input_audit.py` real control (2026-07-31); Paper0.md amendment row 2026-07-31 |
| Criterion-scoped tests | 1,271 passed / 1 skipped / 0 failed | P0-ASSEMBLY-CGR record (criterion 7 closure) |
| Completion reviews | three independent, zero P0 | gpt-5.6 formal review; Codex adversarial audit; GPT Pro C1–C4 (`history/20260726_gptpro_results_doublecheck/DOUBLECHECK.md`) |
| Grid [−100, 2200) s | alignment invariant | `Paper0.md:613` |
| Vespagram lane constants | ref 29.0°, slowness −10…0 (100 steps), 4th root, 20 s window, min support 2 | `Paper0.md` § vespagram contract; LOO runner constants |
| S1: input audit | 2,393 inputs checksum-valid; adverse manifest stales exactly 1 intended file | ledger criterion-1 record, run `20260722T040215Z`, audit SHA `f318d7eb…` |
| S1: TauP controls | P 224.131 s, PKiKP 808.136 s, differential 584.0 s within 0.01 s; 10° adverse moves differential > 5 s | `taup_phase_prediction_comparison.csv` (SHA `e7e8cfee…`); P0-TAUP-PREDICT record |
| S1: COMP-ASSOC adverse lanes | Type I permuted-label all null (p 0.864/0.660/0.329); Type II 1 of 3 material — below registered ≥2/3 void rule | `comp_assoc_reading.json` (SHA `d8140daf…`) |
| S1: jitter audit power lane | 60 s lane centroid displacement: PKiKP 27.9 s (27.88), PKKP 63.7 s (63.71) | `t3power_power_comparison.json` (SHA `798268b0…`); P0-C5-T3POWER record |
| S1: LOO controls | full-set cell (663.80, −3.6364, power 0.9327, support 23) reproduced; S1015f hold-out repeat byte-identical | P0-LOO-INFLUENCE record; registered amendment 1 (commit `f5d4f043`) |
| S1: PKKP concordance controls | six cells reproduced exactly; time-reversal adverse reproduces 0/6 | `history/20260801_pkkp_concordance/pkkp_concordance_verification.json` |
| Lunar blind test verdict (§ 5.3) | METHOD-FRAGILE at both frozen grades; G1: real 0/3, noise null 15%, station-swap 33%; G2: real 3/3, event-scramble 75/75, phase-randomized noise 72/75, station-swap 6/6, decoy windows 16/24; implied radii 100–470 km, station-inconsistent | `docs/lunar_analog_report.md` (commit `5602143b`) §§ 3.2–3.4; PREREG `results/lunar_analog/PREREG_criteria.md` SHA `ab5f8034…e119` (re-verified 2026-08-01); run products not retained — the archived report is the quotable record (card P0-LUNAR-FOLD) |
| Lunar data + port scale (§ 5.3) | 228 QC-passing traces, Apollo 12/14/15/16 (network XA); primary configs 11–16 traces; six of seven modules byte-identical, seventh import-mechanics only; adaptations (principal, not exhaustive — full declared list in report § 1 + PREREG): LP vertical, no polarization filter, Lanczos → 20 Hz, −100…+1200 s cut | report §§ 1–2; PREREG addendum C (Nunn 2020 Zenodo supplement, XA network DOI `10.7914/SN/XA_1969`) |
| Lunar grades ↔ Mars rerun anchor (§ 5.3) | G1 \|ΔT\| ≤ 25 s / \|Δp\| ≤ 1.2 / σ_T ≤ 10 s / σ_p ≤ 1.0 / occupancy ≥ 0.50 / Type-III concordance; G2 \|ΔT\| ≤ 50 s / \|Δp\| ≤ 2.0 / σ_T ≤ 50 s / σ_p ≤ 1.5 / occupancy ≥ 0.45; Mars 85%-threshold rerun σ_T: PKiKP 43.0 s, PKKP 49.3 s | report § 1 (frozen grades; PREREG § grades); `results/tables/bootstrap_picks.csv` (85% rows 43.004 / 49.347, re-verified 2026-08-01) |
| Lunar slowness geometry (§ 5.3) | deep-moonquake core-reflection discriminant ≈ −1 s/deg vs Mars PKiKP ≈ −6.5 s/deg; impact configs ≈ −3.4 s/deg | report § 2 |
| Lunar reference radii (§ 5.3) | Weber et al. 2011 R_OC ≈ 330 km; Garcia et al. 2011 VPREMOON R ≈ 380 km | report § "summary"; PREREG § context |
| Visser et al. re-analysis facts (§ 5.6) | posted 2026-07-20, DOI `10.21203/rs.3.rs-10379955/v1`; radius grid 50–650 km (50-km steps); PKiKP candidates 200–300 and 500–600 km (200/300-km beam amplitudes > 600-km); PKIKKIKP 100–600 km; linear stack + F-vespagram; deglitched + Butterworth band-pass + Montalbetti–Kanasewich; materials "available upon request" | preprint pp. 1–10 (abstract, §§ 2–4, Open Research), archived `references/library/pdfs/visser2026_no_inner_core_preprint.pdf` SHA `2ebdc512…a51713`; Crossref record for the DOI (posted date) |
| Visser event-set difference (§ 5.6) | their stack = 23 events; vs the archived Bi et al. frozen 23-event `set=vespagram` split: omits S0105a, S0189a; adds S0409d, S0809a (absent from the archived published event tables); 21 shared | supplement Table S1, archived `references/library/pdfs/visser2026_no_inner_core_si.pdf` SHA `5fadfffe…c8de7`; `manifest/event_table.csv` (26 rows: 23 `set=vespagram` + 3 `set=validation`; provenance `Paper0.md` § B.2 from the SI archive under `references/original_paper/SI/`); repo-wide search 2026-08-01: S0409d/S0809a appear in no archived Bi et al. table |
| Cross-selection execution (§ 5.6) | global supported argmax: canonical 23 → (663.80, −3.6364, 0.9327, support 23); intersection 21 → (663.95, −3.6364, 1.0599, 21); Visser selection 23 → (663.90, −3.6364, 1.0887, 23) — all rank 1, same slowness cell; target-box max rank 6,938 → 15,809 → 25,172 (box max (601.95, −6.6667, 0.7736) → (602.10, −6.6667, 0.7336) → (602.05, −6.5657, 0.6765)); six § 4.3 ridge-critical events common to both selections | countersigned card P0-XSEL-VISSER (registered `fe38a196` pre-execution): `history/20260801_xsel_visser/` — MEMO SHA `e7f9eba1…`, countersign `3da51e5f…`, variant tables `e5ccee5c…` (xsel21) / `725d5c14…` (v23); all controls incl. bit-exact gate, two LOO known-answer singles, byte-flip fail-closed |
| S0325a distance-catalog boundary (§ 5.6) | archived Bi tables: Δ = 39.7 ± 6.1° (inside the declared < 40° cut); Visser Table S1 (Khan et al. 2023 distances): 40.8 ± 1.7° (outside) | `manifest/event_table.csv` row S0325a (39.7, err 6.1, `set=vespagram`); supplement Table S1, archived SI PDF SHA `5fadfffe…c8de7` |
| § 5.4 scramble design | N = 200 seeded distance permutations of the 23 stacked events (identity excluded, carried separately); traces/masks/envelopes untouched; all realizations completed, zero errors, zero NaN | `history/20260801_mars_scramble/MEMO.md` §§ "Scramble runner"/"Sweep"/"Frozen statistics" (SHA `06e2eb11…`); `null_table.csv` (201 rows, SHA `12aa226d…`); `ADJUDICATION.md` "N = 200 … zero errors/NaN" |
| § 5.4 scramble frozen thresholds | ridge 0.9327 (real 0.9326603162534909); target 0.7736 (real 0.7736156900239739) | `frozen_stats.json` (SHA `03302442…`) `frozen_thresholds` + `real_values`; same values as existing rows "Global PKiKP-window maximum" / "Target-box maximum" |
| § 5.4 + § 4.2 caveat + abstract + conclusions: ridge false-alarm rate | 0.755 = 151/200 → "75.5%"; exceedance p_ridge = 152/201 = 0.7562 → "0.756" | `frozen_stats.json` `FAR_ridge`/`p_ridge`; MEMO "Frozen statistics"; ADJUDICATION "Accepted outcomes"; independently recounted from `null_table.csv` 2026-08-02 |
| § 5.4 + § 4.2 caveat + abstract + conclusions: target false-alarm rate | 0.480 = 96/200 → "48.0%"; p_target = 97/201 = 0.4826 → "0.483" | same as previous row (`FAR_target`/`p_target`) |
| § 5.4 ridge-null location | null median 0.979 (q50 0.9789989259829242); null max 1.333 (1.3326855577951884); real ridge ≈ 24th percentile of its own null | `frozen_stats.json` `ridge_quantiles.q50` + `ridge_null_max`; MEMO "Interpretation" (~24th percentile); ADJUDICATION "near the 24th percentile" |
| § 5.4 target-null location | null median 0.767 (0.7667363876652029); null max 1.076 (1.0764746107453875); real target-box maximum at the null median | `frozen_stats.json` `target_quantiles.q50` + `target_null_max`; ADJUDICATION "sits at the null median" |
| § 5.4/S1e scramble gate | regenerated 240-row canonical lane line-identical to production `peak_comparison.csv`; SHA-256 `8df5f5c8…` (same identity as existing "Byte-identical reproduction" row) | MEMO "Canonical-lane regeneration" (gate table SHA `8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce`); ADJUDICATION "Gate PASS" |
| S1e scramble identity control | identity permutation reproduces canonical argmax + target-box cells, exact float equality on all seven recorded values; identity grids array-identical (NaN-aware) to the canonical chain NPZ | MEMO "Controls (STEP 3)" (a); `null_table.csv` row `realization=0` (recount 2026-08-02: 663.8 / −3.6363636363636367 / 0.9326603162534909; box 0.7736156900239739) |
| S1e scramble effect + determinism controls | seed-1 grid differs in 4,525,248 nonzero \|Δ\| cells (max \|Δ\| 1357.7); seed-1 rerun byte-identical; sweep r0/r1 rows byte-identical to control rows | MEMO "Controls (STEP 3)" (b), (c) + "Sweep (STEP 4)" |
| § 5.4 injection design | impulse at t_i = 604 + (−6.5)(Δ_i − 29°); chain's own 0.2–0.8 Hz zero-phase band-pass; peak amplitude = α × pre-P RMS (−60…−10 s window); ladder α ∈ {0, 0.25, 0.5, 1, 2, 4, 8} | `history/20260801_inject_recov/MEMO.md` (SHA `8cff2a9f…`) §§ "Question"/"STEP 2"/"Injection implementation"; `ADJUDICATION.md` "What the run established" item 3 |
| § 5.4 + abstract + conclusions: α\* | α\*_argmax = α\*_power = 0.25; true flip point unresolved in (0, 0.25]; no sub-0.25 rungs registered or added post hoc | `recovery_table.csv` (SHA `0b7a66a4…`); MEMO "Recovery table"; ADJUDICATION "Accepted outcomes" |
| § 5.4 α = 0.25 rung | argmax (602.95 s, −6.4646 s/deg → "−6.46"), power 1.2483 → "1.248" vs ridge 0.933; global argmax in-box at every rung ≥ 0.25 | `recovery_table.csv` α=0.25 row (recount 2026-08-02: 602.95, −6.4646464646464645, 1.2483490424619448, support 23); ADJUDICATION item 3 |
| § 5.4 convention proof | production roll formula recovers 604.0 ± 0.051 s for 23/23 stacked traces in every injected lane | MEMO "STEP 2" + "Positive-control adjudication" step 1; ADJUDICATION "convention proven, not assumed" |
| § 5.4/S1e injection α = 0 gate | canonical cell field-for-field under full enforcement; 240/240 rows `current`; gate table SHA `8df5f5c8…`; NPZ SHA `2ff8995e…` | MEMO "STEP 1"; ADJUDICATION item 1 |
| S1e injection determinism | α = 1 and α = 8 reruns byte-identical incl. NPZ container bytes | MEMO "Controls" (c) + adjudication section step 2 |
| § 5.4 α = 8 disclosure | observed argmax (603.90 s, −6.4646 → "−6.46"); 0.10 s = two 0.05-s time cells from 604.0; slowness within one grid cell; monotone convergence 602.95 → 603.30 → 603.50 → 603.65 → 603.80 → 603.90 s; α = 0 in-box background max at 601.95 s; adjudicated control-tolerance design flaw; NOT quotable as a passed literal control | `recovery_table.csv` (all rungs); MEMO "Controls" (b) + "Positive-control adjudication"; ADJUDICATION "Adjudication of the failed literal control"; `REVIEW_RECORD.md` (SHA `7c5fc2a8…`) |
| § 5.4 decoy design | PKiKP decoy boxes 40 s × 1.2 s/deg; box centers t ∈ [250, 2100] s (stride 5 s × 0.1 s/deg) | `docs/research_pipeline.md` § P0-DECOY-FAM (frozen method); `history/20260801_decoy_fam/MEMO.md` (SHA `b69bb92f…`) |
| § 5.4/S1e decoy reader anchors | gate cell (663.8, −3.6364, 0.9327, 23); target-box 0.7736 (0.7736156900239739); ridge box 0.9327 (0.9326603162534909); PKKP mirror threshold 0.2143 (0.21425338569020153, recorded pre-sweep) | MEMO "Recorded PKKP-family threshold" + "Controls"; `decoy_family_summary.json` (SHA `4c91a3c2…`) `controls.*`; `pkkp_threshold_record.json` (SHA `498e0141…`) |
| § 5.4 decoy adverse failure | frozen pre-P box [−90, −50] s × [−7.1, −5.9] s/deg required < 0.7736; observed supported max 49.37 (49.37176439112555), independently re-derived from the NPZ outside the reader | MEMO "Controls" A1 + "Why A1 failed"; `decoy_family_summary.json` `controls.A1_adverse`; ADJUDICATION item 2 |
| § 5.4 edge-ramp finding | 19/26 variant-A envelopes with onset transients 5–355× target-window scale immediately after valid-data onsets; supported pre-P stacked power up to 1395; largest in-sweep box max 2.40 (2.397) at center 280 s | MEMO "Why A1 failed" + "Frozen statistics" descriptive structure; ADJUDICATION items 2–3 |
| § 5.4 band-resolved exceedance | 100% of decoy boxes at centers 250–400 s exceed both PKiKP thresholds; 0% at 800–1600 s; late trace-edge rise (not quantified in draft text) | MEMO "Frozen statistics" descriptive structure; ADJUDICATION item 2 ("100 % at centers 250–400 s, 0 % at 800–1600 s") |
| § 5.4 decoy fractions disposition (no numerals quoted in draft) | family fractions computed but confounded by the demonstrated edge ramp; NOT accepted as false-alarm rates; confirmatory family-rate lane on this surface closed | ADJUDICATION items 2–4 (values remain only in the history record: MEMO "Frozen statistics", `decoy_family_summary.json`) |
| § 5.4 lunar cross-reference | N1 event-scramble 75/75 at replication grade (reuse) | existing row "Lunar blind test verdict (§ 5.3)" — no new source |
| § 3.1 UCLA feasibility (dated addition) | `UCLA_v4` executable without MATLAB: GNU Octave 10.3.0 + Octave-Forge signal 1.4.7 / control 4.2.3; one used-path incompatibility (`ifft(...,'symmetric')`) closed by a 2-line conjugate-mirror shim; all three shipped green fixtures reproduced to ≤ 5.6e-16 (fixture provenance proven) | countersigned card P0-UCLA-FEAS: `history/20260801_ucla_feas/` — FEASIBILITY_CARD SHA `0168fdd0…`, LANDING.md (attestation reserved pre-discriminator) |
| § 3.1 UCLA equivalence (dated addition) | DIVERGENT-MINOR under the rule frozen pre-run: lengths 142840 exact; glitch counts U/V/W 43/43, 34/34, 36/37; port-noise ratios R_ch 0.0886 / 0.0429 / 0.0833 (all < 0.1; only the W count blocks EQUIVALENT); divergence localized to one t ≈ 66 s glitch flipping platforms + a +10-sample (one 2-sps sample) fit-window offset; determinism bitwise-exact; channel-permuted adverse reference → NOT-EQUIVALENT (R_ch ≈ 0.98–1.00) | countersigned card P0-UCLA-EQUIV (zero findings): `history/20260801_ucla_equiv/` — MEMO SHA `99b99382…`, comparison_table.csv; strict `mps_ucla_verified` stays reserved per LANDING.md |
| § 5.4 Earth control design | 33 usable vertical traces (of 40 selected events; M 6.2–7.8; 25.41–34.96° → "25.4–35.0°") at IU.ANMO.00.BHZ (quiet GSN borehole); ak135 P alignment from catalog hypocenters; 15 frozen windows = 3 targets (PcP primary, PKiKP secondary, ScS boundary) + 12 decoys; N1 = 25 scramble realizations; grades G1/G2 mirror lunar | `history/20260801_earth_ctrl/REPORT.md` §§ 3–6; `PREREG.md` (chain `PREREG_SHA256.txt`) |
| § 5.4 Earth pilot-gate deviation | registered argmax gate FAILED: argmax +29.25 s (search-window edge), envelope SNR 66× pre-P median; DEV-2026-08-01-3 replaced the statistic post hoc (onset first-crossing; same trace −0.05 s, 66.1×) — out-of-boundary under the frozen repair rule ("alignment convention only"); strict reading: pilot FAIL → STOP ⇒ production exploratory, deviation-flagged | REPORT.md §§ 5, 9; countersign r1 P1-1 + r2 (`history/20260801_earth_ctrl/countersign/`) |
| § 5.4 + S1f Earth verdicts + FARs | NOT-RECOVERED at G1 and G2; PcP/PKiKP/ScS all undetected; FAR^PcP: N1 0.000/0.080, N2 0.000/0.250 (G1/G2), all < 1/3; at G2 two wrong-place decoy windows certified | `history/20260801_earth_ctrl/analysis/verdicts.csv` (post-fix hash `f5967f7a…`, byte-identical across the P1-2 grader repair); REPORT.md § 9 |
| § 3.1 UCLA production pass (dated addition) | 4 of 26 events crash in shipped `UCLA_v4` (S1197a/S1222a `aa(_,2)` empty-glitch-list indexing; S0784a zero subscript; S1015f `filtfilt` too-short segment) → a-priori 22-event partition = 19 stack + 3 validation; full chain ran twice (UCLA-on-raw identity pre-stage, terminal `ucla_unverified` 22/22, vs subset-matched MPS `succeeded_mps_only` 22/22); controls: pos-A production-vs-census S0235b byte-identical (`e9fe30fb…`), pos-B subset-MPS-vs-accepted S0235b byte-identical (`73410b11…`), adv-A S1197a mechanically rejected by the sole allow-list | countersigned card P0-UCLA-PROD Amendment 1 (zero P0/P1): `history/20260802_ucla_prod/` — LANDING.md, CENSUS.md, review/REVIEW_readout.md |
| § 5.5 same-cell table + § 6 (vi) | six registered lane-readout cells plus three accepted-23 context cells: UCLA-19 argmax 576.15 s/−10.0/0.9003 (0.9002604365771639), box 584.00/−7.07 (−7.070707…)/0.7547, PKKP 1341.25/−6.97/0.3049; MPS-19 argmax 662.85/0.0/1.0140, box 584.00/−7.07/0.7356, PKKP 1340.95/−6.97/0.2422; accepted-23 context 663.80/−3.64/0.9327, 601.95/−6.67/0.7736, 1341.00/−6.97/0.2143; derived: box powers 2.6% apart ((0.7546588−0.7356291)/0.7356291 = 0.0259), PKKP powers 25.9% apart ((0.3048547−0.2421753)/0.2421753 = 0.2588), PKKP offset 0.30 s, box displacement 601.95 → 584.00 s (event-set effect: both lanes cell-identical at 19 events); UCLA argmax = third near-degenerate location beyond the two LOO families (§ 4.3); support 19, minimum_support 2, all rows `ok`/`current` | `history/20260802_ucla_prod/readout/readout_table.tsv` (six lane cells) + `lanes/*/peak_comparison.csv` (SHA `265153e6…` / `dc9e579a…`) + `history/20260802_ucla_prod/LANDING.md` (accepted-23 context cells); review-precise formulations per `history/20260802_ucla_prod/review/REVIEW_readout.md` T5 (COUNTERSIGN) |

Wording cautions (updated after the 2026-08-01 independent accuracy review
of draft v0.1; findings and resolutions in
`history/20260801_draft_accuracy_review/`):

1. Never gloss (601.95, −6.67) as "the published PKiKP pair" — it is the
   maximum inside the published-pair target box (draft complies everywhere
   after the v0.2 fix round, including the conclusions).
2. DISCHARGED 2026-08-01 (card P0-ABL-POLOP-PROV): the registered
   provenance-enforced rerun of the identical Card-5 chain reproduced all
   240 ablation rows with exactly identical coordinates, every row
   `current_provenance_status=current`, and the byte-flip adverse control
   failing closed. The ablation numbers / Fig. 4a are claim-bearing
   eligible. Enforced table SHA `512f78e1…`; record
   `history/20260801_ablpolop_prov/`.
3. RESOLVED (review caution-3 resolution): there is ONE argmax
   implementation — `detect_peaks.py` global rows are the supported argmax
   over the inclusive 550–700 s window and full slowness grid;
   `read_sig_statement.py` merely selects the recorded 20-s A-lane row from
   the same table. The 662.0–662.8 s band is the 1-s power-window A/B/C
   rows; the 20-s A/B/C rows are 663.80/664.10/664.85 s. Canonical
   displacement: **+59.8 s** (663.80 − 604.00, registered 20-s A lane).
   Never describe the band and the primary argmax as "two registered
   readers".
4. Three-feature taxonomy is mandatory wording: target-box maximum
   (601.95, −6.67) / shallow 602-family branch (602.0–606.4 s at
   −3.43…0.0 s/deg; LOO flip target; 1-s comparison point F1) / displaced
   ridge (663.80, −3.64). LOO fragility is about the RIDGE's rank-1 status;
   the target-box maximum never becomes the argmax.
5. The injected argmax (602.95, −6.46 at α = 0.25; § 5.4) is a FOURTH
   object: inside the target box but distinct from the real target-box
   maximum (601.95, −6.67). The injection "moves the global argmax into
   the published target box" — never "recovers the target-box maximum"
   or "the published pair". Decoy family fractions are confounded and
   never quotable as rates; the § 5.4 scramble FARs (75.5% / 48.0%) are
   the only accepted false-alarm numbers.
6. Earth-control results (§ 5.4, S1f) carry exploratory,
   deviation-flagged standing under the strict frozen reading (post-hoc
   pilot-gate replacement; the registered remedy was STOP). NEVER quote a
   directional (late/early) reading of the Earth fitted-vs-predicted
   offsets (countersign-invalidated; P2-3) and never quote decoy-window
   center times (P2-4); quotable Earth numbers are the § 5 pilot record
   and the verdict/FAR set in `analysis/verdicts.csv`.
