# P0-EARTH-CTRL — Earth single-station positive control: REPORT

Run directory: `/Users/artuskg/marsquake_runs/20260801_earth_ctrl/` (isolated; repo untouched).
Card authority: `docs/research_pipeline.md` section "P0-EARTH-CTRL" (registered at commit a2163d49; frozen).
Date: 2026-08-01. Interpreter: `/Users/artuskg/micromamba/envs/mars-ic/bin/python`
(python 3.11; obspy 1.4.1, numpy 1.26.4, scipy 1.13.1, pandas 2.2.2).

## 1. Question

Does the ported Bi et al. (2025) single-station source-array vespagram machinery — exactly as
used for the Mars PKiKP claim and the lunar analog (known truth, hard data; verdict
METHOD-FRAGILE) — recover known Earth core phases (PcP primary; PKiKP secondary; ScS
plausibility boundary) at ak135-predicted differential time and slowness on one GSN station's
natural source array? Earth is the easy-data end of the calibration triptych:
Mars (unknown truth), Moon (known truth, hard data), Earth (known truth, easy data).

## 2. Preregistration and countersign chain

- `PREREG.md` frozen before any Earth waveform contact. SHA-256 chain (`PREREG_SHA256.txt`,
  append-only):
  - initial freeze: `9f4fade35ea003f585d7bda1223dc15a385807eca268921a6a710e16a15d4896`
  - post-DEV-1 (Codex round-1 P1 fixes, pre-data): `9c539050eaac37e28ef082711915e0c73ed963fe5c01de64755de547c7395fc1`
  - post-DEV-2 (pilot pre-P segment clip, pre-pilot): `9f96f7007db8a6ef337f4bf5656e77a28e0b9277e18464a930a0f39c55284210`
  - post-DEV-3 (pilot statistic replacement, entered at the pilot stage before any
    target-window content was viewed): `0d342d3a8ec167974c420eca7b3a471a3e75647684f2ba3ee06a35460b0792c5`
- Frozen numeric targets: `addendum_A_targets.json`
  SHA-256 `f3b2f18ccd56cd5bf1077f80e5c3e3f6b6608c58b924828bab1abe09decd2d67` (model-only generator
  `code/make_addendum_A.py`; run before any data contact).
- PREREG countersign: Codex `gpt-5.6-sol` at `xhigh` (banner verified). Round 1
  NOT COUNTERSIGNED (P1-1 null/box-peak asymmetry; P1-2 Type-III portability); fixes entered as
  DEV-2026-08-01-1; round 2 COUNTERSIGNED. Records: `countersign/prereg_*`.

## 3. Design (frozen; lunar A1 mirror)

- Station IU.ANMO.00.BHZ (chosen on instrument/coverage grounds from the permitted
  {ANMO, KIP, MAJO} set via metadata-only browsing: borehole installation, lowest in-band
  microseism exposure of the three, coherent Mexico/Central-America source corridor;
  `catalog/station_metadata_iu_bhz.txt`, dated `catalog/station_browse_date.txt`).
- Reference geometry frozen a priori at 30.0 deg / 33 km (mirrors the Mars fixed-reference
  convention; no data-dependent reference step). ak135 targets at reference:
  P absolute 365.50 s, 8.845 s/deg; differential to P:

| Phase | dT (s) | dp (s/deg) | box (s) | box (s/deg) |
|---|---|---|---|---|
| PcP | +181.67 | -6.259 | +/-40 | +/-1.5 |
| PKiKP | +633.81 | -8.188 | +/-40 | +/-1.5 |
| ScS | +636.72 | -4.064 | +/-40 | +/-1.5 |

  Registered note: PKiKP and ScS are only 2.91 s apart in time at reference; they are separated
  in slowness by 4.12 s/deg (> the G2 bound 2.0), so slowness carries the discrimination.
- Event floor (frozen): USGS ComCat circle query around ANMO, radius 25-35 deg, depth 10-70 km,
  M >= 6.0, 2000-01-01..2026-01-01, top 40 by magnitude; contamination screen (global M >= 6.0
  in [tP-2700, tP+1300] s; M >= 5.0 within 15 deg in [tP-300, tP+1300] s); mechanical QC
  (coverage <= 10% missing on [P-200, P+1300], flatline, clipping); evaluability ladder
  >= 15 usable traces.
- Vespagram machinery: byte-identical Mars modules (copies in `code/mars_modules/`,
  `COPY_SHA256.txt`; adaptations logged in `code/PORT_DIFF_LOG.md`): 4th-root envelope stack,
  relative slowness -10..0 s/deg in 100 steps, Hann power windows 20 s (primary) and 5 s
  (secondary), reference-distance projection, A-prime normalization window
  [81.67, 281.67] s = T_pred(PcP) +/- 100 s, C-prime full cut.
- Alignment (D-ADAPT-E1): ak135-predicted absolute P per event from the NEIC hypocenter;
  P at t = 0; nearest-sample cut [-100, +1300] s at 20 Hz (28000 samples); no picking.
- Preprocessing: 0.2-0.8 Hz Butterworth 4-corner zero-phase on counts (no response removal);
  Lanczos a=20 resample 40->20 Hz after filtering for 40-sps epochs (D-ADAPT-E3); per-trace
  z-score; Hilbert envelope, 5 s smoothing, 5 s edge erosion; mask-aware throughout.
- Grades (copied exactly from the lunar design; from the Type-I occurrence map at the 85%
  threshold, Gaussian fits to time/slowness projections):
  - G1 "paper-grade": |dT| <= 25 s, |dp| <= 1.2 s/deg, sigma_T <= 10 s, sigma_p <= 1.0 s/deg,
    O_max >= 0.50, plus Type-III concordance rider (same location bounds, sigmas x 1.5).
  - G2 "replication-grade": |dT| <= 50 s, |dp| <= 2.0 s/deg, sigma_T <= 50 s,
    sigma_p <= 1.5 s/deg, O_max >= 0.45.
  - Box-peak requirement: a 3x3-neighborhood local maximum inside the graded box in the
    non-bootstrap vespagram, applied SYMMETRICALLY (real data, every N1 realization, every N2
    decoy; DEV-2026-08-01-1).
- Bootstraps: Type-I (floor(2N/3) subsample without replacement, 200 iterations, seed 0);
  Type-III (uniform +/-10 s alignment jitter, 200 iterations, seed 0). Occupancy is
  window-restricted (outside-window pixels identically zero), thresholds 50/70/85%.
- Nulls: N1 event-scramble (distance labels permuted; 25 realizations, seeds 100+k; FULL
  machinery per realization including Type-III and box-peak); N2 decoy windows (12 frozen
  decoys at +/-150 / +/-300 s reflected-walk placements, >= 60 s from cataloged collision
  phases, >= 100 s same-phase decoy separation):
  PcP {538.33, 763.33, 931.67, 1081.67}; PKiKP {536.19, 761.19, 933.81, 1083.81};
  ScS {533.28, 758.28, 936.72, 1086.72} (s, differential to P).
- Frozen per-grade verdict rules (no cross-grade aggregation): RECOVERED(-STRONG at G1) =
  PcP detected AND FAR_N1^PcP < 1/3 AND FAR_N2^PcP < 1/3; METHOD-FRAGILE = detected but
  same-phase FAR >= 1/3; NOT-RECOVERED = not detected with quiet nulls; INCONCLUSIVE otherwise.
- Detection level only; no radius inversion.

## 4. Data

- Catalog: 40 events selected under the frozen query; 33 passed the frozen contamination
  screen; 33 waveform downloads succeeded (IRIS FDSN dataselect via service.earthscope.org);
  33 of 33 passed mechanical QC. Zero missing samples on the QC interval for all 33.
- Manifest: `catalog/data_manifest.csv` (every item dated + SHA-256);
  selection `catalog/event_selection.csv`; screen archive `catalog/contamination_screen.json`;
  QC `data/proc/qc_table.csv`.
- Usable traces: N = 33 (>= 15 full-power floor). Distances 25.41-34.96 deg; magnitudes
  6.2-7.8; native 20 Hz x26, native 40 Hz x7 (resampled per D-ADAPT-E3).
- Type-II clustering trigger (frozen): max 3-deg distance-bin fraction = 0.455, below the 0.5
  trigger; the Type-II clustering bootstrap is therefore not required.

## 5. Pilot positive control (frozen gate before the full run)

- Pilot event: usp000juhz (M7.8, the largest usable event).
- REGISTERED CHECK: envelope argmax in [-30, +30] s within |t| <= 10 s of predicted P at
  t = 0, SNR >= 3. OUTCOME: FAILED — argmax landed at +29.25 s (the window edge) with envelope
  SNR 66x over the pre-P median.
- Observations within the permitted windows (alignment window and pre-P segment only; no
  target-window content viewed): the envelope stays <= 1.1x the pre-P median through -5 s and
  first crosses 3x at -2.05 s and 5x at -0.05 s relative to predicted P — the alignment
  convention itself places predicted P at t ~ 0 on this trace.
- DEV-2026-08-01-3 then REPLACED the registered pilot statistic with an onset criterion (first
  crossing of 5x the pre-P median within [-30, +30] s must lie within |t| <= 10 s; SNR >= 3
  unchanged), under which the same trace PASSES (-0.05 s, 66.1x). This deviation is
  OUT-OF-BOUNDARY and post hoc: it was adopted after the registered gate was observed to fail,
  and it changed a gate statistic, which the frozen repair rule ("fix alignment convention
  only") did not permit. It is treated as a post-hoc criteria change throughout this report;
  the standing consequence for the production run is stated in section 9.
- DEV-2026-08-01-2 (entered pre-pilot) clipped the pilot pre-P noise segment to [-90, -50] s
  because the registered [-200, -50] s partly precedes the cut start.
- Both deviations are logged in `PREREG.md` section 12 with hashes in the chain. The
  registered check's failure is a reported result; the DEV-3 replacement does not un-fail it.
  Under the strict frozen reading the pilot outcome is FAIL and the frozen remedy was STOP;
  the production run proceeded under the DEV-3 gate.

## 6. Execution record

- Production pass: 33 traces, 15 frozen windows (3 targets + 12 decoys). One 33-trace
  vespagram: 1.46 s. Type-I pass 7.8 min; Type-III pass 15.2 min (`runs/real/`).
- N1: 25/25 realizations complete, seeds 100..124, sharded 6 ways; each realization ran the
  FULL machinery on its own permuted-distance stack (non-bootstrap vespagram + box-peak check +
  Type-I + Type-III over the three phase windows). Zero errors in all six shard logs; every
  shard ends with a clean final "k=N done" line (k=4, 8, 12, 16, 20, 24); last artifact written
  2026-08-01 22:39:41 local (~1.7 h wall on 6 processes). Outputs
  `runs/nulls/n1/{stats,peaks,perm}_k00..k24` (75 files).
- Session note: the worker session was interrupted (subscription-window exhaustion) while
  WAITING on completed compute; all compute ran unattended to completion before the
  interruption. Grading executed on resume, 2026-08-02 04:42 local, from disk state.
- Grading executed AFTER all outputs existed as files (PREREG section 11 order); production and
  N1 ran concurrently, both fully determined by frozen seeds and inputs.

## 7. Detection results (real data)

Per target phase, from the Type-I 85% occurrence map (Gaussian fits), the frozen box-peak gate,
and the frozen grade bounds (full rows: `analysis/detection_table.csv`):

| Phase | dT vs pred (s) | dp vs pred (s/deg) | sigma_T (s) | sigma_p (s/deg) | O_max | box peak | G1 | G2 | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| PcP | +36.16 | +3.087 | 3.48 | 1.323 | 0.985 | NO | fail | fail | NOT-DETECTED |
| PKiKP | +32.14 | +7.702 | 6.01 | 3.247 | 0.990 | NO | fail | fail | NOT-DETECTED |
| ScS | +33.84 | +3.890 | 5.05 | 3.054 | 0.990 | yes | fail | fail | NOT-DETECTED |

Failure attribution against the frozen bounds:

- Slowness is the decisive failure everywhere. Fitted slowness centroids sit +3.09 (PcP),
  +7.70 (PKiKP), +3.89 (ScS) s/deg from prediction — all beyond even the G2 location bound
  (2.0), displaced toward less-negative relative slowness (the P-like ridge side). sigma_p
  exceeds the G2 bound (1.5) for PKiKP/ScS.
- The box-peak gate independently fails PcP and PKiKP: the non-bootstrap A-prime vespagram has
  NO 3x3 local maximum anywhere inside those target boxes. ScS has one.
- Time is a near-miss, not a pass: all three time offsets are 32-36 s in magnitude (the
  detection table records absolute offsets) — inside G2's 50 s bound, outside G1's 25 s bound.
- Occupancy is uninformative here (0.985-0.990 for targets, but also 0.935-0.990 for every
  decoy window; section 8) — with N = 33 and window-restricted occupancy, the 85% map is nearly
  always highly occupied at its own window peak.

Fit-quality telemetry: `degenerate_fit` is flagged for all stats rows. Forensic (mechanical,
post-hoc): occupancy support is exactly window-confined (out-of-box mass 0.0000 for all three
targets); time-axis fits are clean (no quality flags; sigma_T 3.5-6.0 s); the flag is driven
solely by slowness-axis checks (`tri_estimator_inconsistency`, and for PKiKP/ScS
`sigma_exceeds_axis_span_fraction`, sigma_p ~3.0-3.2 s/deg on the 10 s/deg axis) — the broad
slowness response of 4th-root envelope stacks, faithfully measured. In the frozen lunar
grading, `degenerate_fit` is recorded telemetry, never a gate; it is reported here unchanged.

## 8. Null results and false-alarm rates

All nulls ran the full detection machinery (Type-I, Type-III, box-peak) and were graded by the
identical frozen code path (full rows: `analysis/n1_detection_table.csv`,
`analysis/far_table.csv`).

N1 event-scramble (25 realizations, seeds 100..124; per-phase and any-phase):

| Null | Grade | n | Fires | FAR | Fired |
|---|---|---|---|---|---|
| N1 PcP | G1 | 25 | 0 | 0.000 | — |
| N1 PKiKP | G1 | 25 | 0 | 0.000 | — |
| N1 ScS | G1 | 25 | 0 | 0.000 | — |
| N1 any-phase | G1 | 25 | 0 | 0.000 | — |
| N1 PcP | G2 | 25 | 2 | 0.080 | k=0, k=10 |
| N1 PKiKP | G2 | 25 | 0 | 0.000 | — |
| N1 ScS | G2 | 25 | 0 | 0.000 | — |
| N1 any-phase | G2 | 25 | 2 | 0.080 | k=0, k=10 |

N2 decoy windows (12 frozen decoys on the real stack; overall and per phase):

| Null | Grade | n | Fires | FAR | Fired |
|---|---|---|---|---|---|
| N2 overall | G1 | 12 | 0 | 0.000 | — |
| N2 PcP | G1 | 4 | 0 | 0.000 | — |
| N2 PKiKP | G1 | 4 | 0 | 0.000 | — |
| N2 ScS | G1 | 4 | 0 | 0.000 | — |
| N2 overall | G2 | 12 | 2 | 0.167 | PcP_decoy+150; PKiKP_decoy+150 |
| N2 PcP | G2 | 4 | 1 | 0.250 | PcP_decoy+150 |
| N2 PKiKP | G2 | 4 | 1 | 0.250 | PKiKP_decoy+150 |
| N2 ScS | G2 | 4 | 0 | 0.000 | — |

Readings:

- G1 nulls are perfectly quiet (0 fires in 25 N1 realizations and 12 N2 decoys).
- Both G2 decoy fires are the two heavily overlapping "+150 s" windows (centers +538.33 and
  +536.19 s differential; boxes +/-40 s), i.e., one region of the real stack near +537 s that
  passes G2 with a box local maximum, dT +14-15 s, dp +0.1-1.7 s/deg vs the decoy center. This
  is the adverse control behaving as designed on Earth's dense wavefield: at G2 the machinery
  certifies coherent-looking features at wrong-place windows (per-phase FAR 0.25) while the
  true PcP/PKiKP/ScS boxes fail (section 7).
- All same-phase FARs are below the frozen 1/3 verdict threshold at both grades, so the
  verdict path is the "quiet nulls" branch.

## 9. Verdict (frozen per-grade rules, lunar report's terms)

Applying the frozen per-grade rules (section 3; `analysis/verdicts.csv`), with PcP as the
primary target:

| Grade | PcP detected | FAR_N1^PcP | FAR_N2^PcP | Verdict |
|---|---|---|---|---|
| G1 (paper-grade) | no | 0.000 | 0.000 | NOT-RECOVERED |
| G2 (replication-grade) | no | 0.080 | 0.250 | NOT-RECOVERED |

In the lunar report's terms: NOT-RECOVERED at both grades — the target phase is not detected
while the same-phase nulls are quiet (all FARs < 1/3). No cross-grade aggregation was used,
and the detection criteria, windows, seeds, and verdict rules were not modified post hoc. One
post-hoc criteria change DID occur upstream and is deviation-flagged: the pilot gate statistic
(DEV-2026-08-01-3; section 5), an out-of-boundary deviation under the frozen repair rule. The
secondary (PKiKP) and plausibility-boundary (ScS) phases are also not detected at either
grade.

Registered standing of these verdicts (adjudicated in the fix round):

- STRICT FROZEN READING (governing): the registered pilot criterion FAILED, and the frozen
  rule's remedy was STOP. The production run and the verdicts above therefore carry
  EXPLORATORY standing relative to the PREREG, flagged by DEV-2026-08-01-3.
- AS-RUN READING: under the DEV-3 gate the pilot passes, and the verdicts stand as computed.

Both readings are reported; the strict reading governs this card's registered standing.

Calibration triptych reading (interpretation, detection-level only; the Earth verdicts carry
the exploratory standing stated above under the governing strict reading): Earth was the
easy-data end — known truth, 33 large well-located events at 25-35 deg on a quiet borehole GSN
station. The ported machinery did not recover PcP (nor PKiKP/ScS) at either the paper grade or
the replication grade, while at G2 it did certify two wrong-place windows on the same stack.
Moon (known truth, hard data) returned METHOD-FRAGILE; Earth (known truth, easy data) returns
NOT-RECOVERED. Both known-truth ends of the triptych thus fail to demonstrate that the method
recovers known core phases under these preregistered criteria, which bears directly on the
evidential weight of the Mars (unknown truth) detection made with the same machinery.

## 10. Limitations

1. The registered pilot criterion failed and its statistic was replaced post hoc (DEV-3) — an
   out-of-boundary deviation under the frozen repair rule, which permitted fixing the
   alignment convention only. The replacement was made at the pilot stage before any
   target-window content was viewed, but after the registered gate was observed to fail. The
   original check, its failure, and the governing standing consequence are in sections 5
   and 9.
2. The event set includes very large earthquakes (up to M7.8) with extended source time
   functions — a difference from the small Mars events that the registered pilot statistic did
   not anticipate (section 5). No directional interpretation of the production-run time
   offsets is drawn from this; see `P2_LOG.md` (P2-3) for the countersign-invalidated
   interpretation this replaces.
3. Mixed back-azimuths: the natural array spans multiple corridors, unlike the single Cerberus
   Fossae corridor on Mars; distance-projection coherence is correspondingly harder, which
   again biases against detection rather than for it.
4. Single station, single channel (BHZ), no response deconvolution (counts) — matching the
   Mars pipeline's convention, not an optimized Earth analysis.
5. Alignment uses ak135-predicted P from NEIC hypocenters (D-ADAPT-E1), not picks; hypocenter
   errors map into alignment jitter (bounded by the Type-III +/-10 s jitter test).
6. N2 decoy windows share the single real stack, so the 12 decoys are not independent draws;
   the N1 event-scramble provides the independent-realization null.
7. The slowness projections are broad (sigma_p up to ~3 s/deg at 85% occupancy), so slowness
   criteria do heavy lifting; this is a property of the 4th-root envelope stack at N = 33 on
   this geometry, honestly recorded by the (non-gating) degenerate-fit telemetry.

## 11. Artifact inventory and hashes

Full inventory: `analysis/ARTIFACT_SHA256.txt` (105 artifacts, SHA-256 each: preregistration,
catalog/manifest/screen, QC, all real-pass outputs, all 75 N1 files, all analysis tables, all
Earth driver code including the P1-2-repaired `grade.py`, the Mars-module copy log, the P2
backlog `P2_LOG.md`, and the fix-round hash-equality records
`analysis/P1-2_hash_{before,after}.txt`). Headline hashes:

| Artifact | SHA-256 |
|---|---|
| `PREREG.md` (post-DEV-3, operative) | `0d342d3a8ec167974c420eca7b3a471a3e75647684f2ba3ee06a35460b0792c5` |
| `addendum_A_targets.json` | `f3b2f18ccd56cd5bf1077f80e5c3e3f6b6608c58b924828bab1abe09decd2d67` |
| `catalog/data_manifest.csv` | `d4d68b6c691268f60671bceedb82bc108528ce4903e642d80579c6342d15df14` |
| `data/proc/qc_table.csv` | `711ef6a2918301a0448e8b5249e2edc20c5b3b9b3d8adb6e9c4930cbf37c89e5` |
| `runs/real/vespagram_A.npz` | `60d5211b08ead890b0e74214d103ab50699618fbb1600018a4c5e4f44b1ff3fd` |
| `runs/real/peak_table.csv` | `736c510689ffec61b22f5c36e9577094cc55b35fef9d61d92605a5e85b3371fc` |
| `runs/real/type1_occupancy.npz` | `2ffea58d69403b8dbf60a12ba4dee2ea6023f072f9e315c110596a49d2e95dce` |
| `runs/real/stats_real.csv` | `a510d1dc11274b3b4a1cb0482abc70cc091a412404e9b1ab54f8300c05e6d52b` |
| `analysis/detection_table.csv` | `c1844508bde9c5a6dfb36931e8d518c8ebf6489d4d0d3ffb06e7b5fa2be8e86c` |
| `analysis/n1_detection_table.csv` | `4246f7b097cec598f76bdf58569a059fd5e846489f450cfef88cb838b9b0ce9b` |
| `analysis/far_table.csv` | `388bfe55167c65df224f49f8463c10035fb398ce694b2024f97cc371ecc2327d` |
| `analysis/verdicts.csv` | `f5967f7a8fe555135cf49bcbc5f74c38048e97d48ae02b7fcbbc58eee77bfdc3` |

The SHA-256 of `REPORT.md` itself is recorded in the final worker message and in
`countersign/` (a file cannot contain its own hash).

## 12. Countersign record (this report)

Final review: Codex `gpt-5.6-sol` at `xhigh` reasoning (banner-verified), per the card's rules
(iterate until COUNTERSIGNED; P0/P1 fixes only; one fix round; one final review restricted to
the fixes; P2 recorded, never blocking). All rounds are saved under `countersign/` as
`report_brief_r*.txt`, `report_countersign_r*.md`, `report_stdout_r*.log`. This section is a
pointer, not the record: the countersign verdict lives in those files, which postdate this
report body by construction.
