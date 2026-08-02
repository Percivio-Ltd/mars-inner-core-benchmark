# PREREG: Lunar Analog Blind Test of the Bi et al. (2025) Source-Array Vespagram Method

Status: FROZEN 2026-07-05 (job A1, Fable leader). Amendments after this date require a dated entry in
Section 11 (Deviations log) BEFORE the affected results are viewed, plus a ledger entry in
`CONTINUITY-lunar-analog.md`. Silent parameter changes invalidate the affected configuration.

Scope: this document freezes station set, event-selection rules, pipeline parameters, detection
criteria, the null-test suite, and verdict rules BEFORE any Apollo waveform is downloaded, plotted,
stacked, or otherwise inspected by anyone on this job.

---

## 1. Objective and symmetric outcomes

Question: does the single-station, fourth-root, envelope, source-array vespagram methodology of
Bi et al. 2025 (Nature; Methods in `references/original_paper/https-10.1038-s41586-025-09361-9.md`,
released code `references/original_paper/Mars_IC-main/`) recover a consistent lunar core signal from
Apollo data, where independent (though themselves stacking-derived and partially contested) estimates
exist: Weber et al. 2011 (Science 331:309, R_OC ~330 km, R_IC ~240 km) and Garcia et al. 2011 VPREMOON
(PEPI 188:96, R_core 380±40 km)?

This is a method-sensitivity study, not a test against gospel ground truth. Both outcomes are
reportable and publishable:
- RECOVERED: consistent core-phase detections across stations under the frozen criteria, with null
  false-alarm rates well below the real detection rate.
- METHOD-FRAGILE: no consistent recovery, or null configurations fire at comparable rates.

The test is blind: workers executing data retrieval and pipeline runs receive procedure and criteria
only — never the reference radii, never a hoped-for outcome. The mapping from measured (T, p) to
implied core radius (Section 7) is applied by the leader only after detection statistics are computed.

## 2. Configurations under test

Primary configurations (one per station; the unit of the study-level verdict):

| Config | Station | Event set | Band |
|--------|---------|-----------|------|
| P12-DM | Apollo 12 | DM (deep moonquake A-clusters) | 27–40° |
| P14-DM | Apollo 14 | DM | 27–40° |
| P15-DM | Apollo 15 | DM | 27–40° |
| P16-DM | Apollo 16 | DM | 27–40° |

Pre-declared fallback: if a primary config has <8 qualifying traces (Section 3.4), widen its band to
20–60° (config renamed Pxx-DM-wide, "reduced-comparability" flag). If still <8: NOT-EVALUABLE.

Secondary configurations (reported, not part of the primary verdict):
- Sxx-SHQ: shallow moonquakes (Nakamura HFT/shallow class), band 15–70°, per station.
- Pxx-DM-CS: cluster-stack variant of each primary config — one trace per A-cluster, built as the
  linear mean of that cluster's aligned traces before envelope computation; all else identical.
- Depth-sensitivity variant: primary configs re-run with per-trace true cluster depths in the
  alignment predictions instead of the uniform reference depth (Section 5, row "ref depth").
- Ixx-IMP (added by DEV-2026-07-05-4, pre-stacking): impact events (artificial + natural meteoroid)
  with published per-event, per-station P picks, band 15–70°, per station; source depth 0 km. Surface
  sources are the closest structural analog to the Mars events (33 km assumed depth) and artificial
  impacts carry exact ground-truth locations/times; N is small (~2–8 per station), so this remains
  diagnostic, never part of the primary verdict. Mixed-class configurations (impacts + deep
  moonquakes in one stack) are NOT run: the ~0 km vs ~900 km source-depth split violates the
  method's common-source-depth assumption and would test a straw man.

## 3. Data specification (frozen rules; instantiated in Addendum B before waveform contact)

### 3.1 Stations and channels
- Stations: Apollo PSE stations 12, 14, 15, 16 (network XA at IRIS; original PSE via JAXA DARTS).
- Instrument: long-period (LP) seismometer, vertical component (LPZ / MHZ or equivalent delivered
  code; worker records exact codes, sampling rates, and peaked/flat mode per time range in the
  manifest). Horizontals are not used in primary configs (Deviation D-ADAPT-1, Section 5 notes).
- Mode handling: peaked and flat mode traces are both admitted; mode recorded per trace; per-trace
  z-score normalization is the mitigation (as in the Mars pipeline). No response deconvolution
  (mirrors Mars pipeline, which filters counts and z-scores per trace).

### 3.2 Event catalogue and picks
- Event source: Nakamura et al. lunar event catalogue (UTIG technical report / DARTS distribution;
  "levent" latest available revision; worker records revision, URL, access date, checksum).
- Deep moonquake set DM: events classified as deep moonquakes belonging to A-clusters with published
  cluster locations and depths (primary location table: Nakamura 2005 JGR "Farside deep moonquakes"
  and its tabulated nearside clusters; worker records exact table + DOI). Event-to-cluster assignment
  from the catalogue; cluster coordinates/depths give source parameters for all member events.
- Shallow set SHQ: events classified as shallow moonquakes (a.k.a. HFT) with published epicentres
  (Nakamura 1979 PLPSC or later revision; record exact source).
- P arrival picks (ranking amended by DEV-2026-07-05-2, folding in PREREG Addendum C plus the leader's
  pseudo-pick audit): operative source = the per-station arrival-time columns of the Nunn et al. 2020
  electronic-supplement S3 compiled-arrival-times workbook (Zenodo concept DOI 10.5281/zenodo.3560482;
  seven constituent source sheets normalized in data/catalogue/arrival_picks_nunn2020_*_normalized.csv).
  When several sheets give a P time for the same (event, station), use the value from the highest-ranked
  sheet — (1) lognonne2003, (2) nakamura1983, (3) goins1978, (4) horvath1979, (5) koyama_unpublished,
  (6) bulow2007, (7) na_zhu2015 — never averaged or otherwise combined; record the cross-source spread
  per pick. Sheet-content audit is logged before any stacking. AUDIT NOTE (2026-07-05, leader-VERIFIED):
  the QuakeML file LunarCatalog_Nakamura_1981_and_updates_v1.xml carries 25,376 "P picks" that are all
  whole-minute times, identical across stations within each event — they are levent signal-start times
  converted to pick elements, NOT seismic arrival picks; that file is used only as the event/detection
  inventory, never for alignment. Rule unchanged: picks are NEVER made or adjusted by this job — an
  event without a published per-station P pick is excluded. If pick uncertainty classes exist in the
  source, record them.
- Distances: great-circle distance from published cluster/epicentre coordinates to station
  coordinates, computed on a 1737.4 km sphere. Distance = catalogue-derived only.

### 3.3 Mechanical QC (the only waveform inspection permitted before runs)
Applied per trace, scripted, no visual review of target windows:
- Coverage: trace must cover [P−200 s, P+1300 s] with ≤10% missing samples; gaps ≤2 s are linearly
  interpolated; longer gaps ⇒ exclude trace.
- Flat/dead segments (recalibrated by DEV-2026-07-05-3): exclude only if the fraction of identical
  consecutive samples in the cut window ≥ 0.98, or the window variance is zero. (Original >5% rule was
  written for Mars 20-Hz VBB data; Apollo LP 10-bit digitization at ambient noise below instrument
  resolution makes consecutive-identical samples the norm — measured median 0.76 across downloaded
  traces — so the original rule excluded physically normal records.)
- Clipping (recalibrated by DEV-2026-07-05-3): exclude if (fraction of samples equal to the trace
  minimum + fraction equal to the trace maximum) > 5% AND the trace peak-to-peak span ≥ 100 digital
  units (a rail-hitting live trace). Constant/dead traces are handled by the flatline rule; the
  original "at instrument min/max" test mis-fired on them because trace min equals max.
- Timing: traces with known timing-quality flags worse than nominal in the source archive ⇒ exclude
  (record archive flag definitions in manifest).

### 3.4 Evaluability
- A configuration is EVALUABLE with ≥8 qualifying traces (Mars used 23). 8–15 traces ⇒ flag
  "reduced-power" in all outputs. Deep-moonquake events from the same cluster count individually in
  primary configs (they share distance labels; this mirrors the Mars design where each event is one
  trace and is itself a stressor of the method's independence assumptions — noted in the report).
- Addendum B (generated from catalogue tables only, before waveform contact) lists per config: event
  id, cluster id, distance, depth, pick time, pick source; plus the config's reference distance and
  reference depth (Section 5) and the evaluability verdict. SHA256 of Addendum B logged in the ledger
  before Phase 3 begins.

## 4. Reference models and predicted targets (Addendum A)

- Models: (M1) VPREMOON (Garcia et al. 2011) — fluid core R=380 km, no inner core distinction;
  (M2) Weber et al. 2011 model (their Table S3) — R_OC=330 km, R_IC=240 km, low-velocity/partial-melt
  layer to 480 km. Both built as TauP .nd files from the published tables into
  `results/lunar_analog/models/` with provenance notes; leader verifies each layer against sources.
- Target phases: computed by deterministic script (`results/lunar_analog/code/prereg_targets.py`,
  obspy TauP) for each config's reference distance and reference depth: all phases from the candidate
  list {PcP, PKiKP, PKKP, PKPPKP (P'P'), PKP, ScS} with differential time (phase − P) in [50, 1100] s
  and differential slowness in [−10.0, −0.5] s/deg. Primary target phase: the core-reflected P
  (PcP in M1; PcP and PKiKP in M2) — the "decisive phase" analog of Bi et al.'s PKiKP.
- Addendum A tables (per config × model × phase): T_pred (s, relative to P), p_pred (s/deg, relative
  to P), target box = T_pred ± 40 s, p_pred ± 1.5 s/deg. Boxes from M1 and M2 are evaluated
  separately. SHA256 of Addendum A logged in the ledger before Phase 3 begins.
- Grid/window auto-extension rules (deterministic): if any target differential slowness < −9.0 s/deg,
  extend the slowness grid to [floor(p_pred) − 1.0, 0] keeping step 0.1 s/deg. If any T_pred > 1100 s,
  extend the cut window end to max(T_pred) + 100 s (and the QC coverage requirement accordingly).

## 5. Pipeline parameters (1:1 map from the Mars pipeline)

Mars values are from `scripts/02_preprocess`, `scripts/03_vespagram`, `scripts/04_bootstrap` (the
audited reimplementation of the paper's Methods) — not the vendored Fig. 2f demo, where they differ.

| Parameter | Mars value (source) | Lunar value | Note |
|---|---|---|---|
| Component | BHZ (bandpass_filter.py:29) | LP vertical | D-ADAPT-1: no polarization filter (Apollo horizontals unreliable); mirrors repo "ablation/envelope" path |
| Bandpass | 0.2–0.8 Hz Butterworth, 4 corners, zero-phase (bandpass_filter.py:33,50) | identical | within LP response band; see UNCONFIRMED in ledger |
| Sampling | native 20 Hz (shared.py:17) | resample to 20.0 Hz by Lanczos interpolation (a=20) after filtering | D-ADAPT-2 (Apollo LP ≈6.625 sps) |
| Alignment | catalogued direct-P pick, P at t=0 (align_and_cut.py:104-148) | identical, using Section 3.2 picks | |
| Cut window | −100…2200 s rel. P (variant C domain) | −100…1200 s rel. P (auto-extend per §4) | smaller body, earlier core phases |
| Normalization | per-trace z-score; variant A window 400–800 s (normalize_and_envelope.py:24-28) | variant A′: z-score over [T_pred−100, T_pred+100] of the primary target phase (per model); variant C′: full cut window | A′ primary (mirrors paperfaith-A primary status) |
| Envelope | Hilbert envelope + 5.0 s smoothing, 5.0 s edge erosion (normalize_and_envelope.py:21,59-67) | identical | |
| Stack | 4th-root, n=4 (run_vespagrams.py:220; stacking.py) | identical | |
| Min stack support | 2 (stacking.py:6) | identical | |
| Slowness grid | −10.0…0.0 s/deg, 100 steps (run_vespagrams.py:189-191) | identical (auto-extend per §4) | |
| Reference distance | 29.0° (run_vespagrams.py:305) | per-config median catalogue distance of qualifying traces, rounded to 0.5° (Addendum B) | mirrors "within the event concentration" choice |
| Ref depth for predictions | 33 km uniform (paper Methods) | DM: median cluster depth of qualifying traces rounded to 25 km, uniform; SHQ: 0 km | true-depth variant is a frozen sensitivity config (§2) |
| Power statistic | Hann-window power of stack; windows 1/5/10/20 s (run_vespagrams.py:25; compute_vespagram.py:82-93) | 20 s primary, 5 s secondary | 20 s is the Mars default |
| Peak search | target-box peak + global-window peak, local-max neighbor check, background quantile (detect_peaks.py) | identical, boxes from Addendum A | both M1 and M2 boxes evaluated |
| Bootstrap Type I | resample ⌊2N/3⌋ events w/o replacement, 200 iters, seed 0 (bootstrap_type1.py) | identical | |
| Bootstrap Type II | distance-stratified halving of the 29–32° cluster (paper Methods) | triggered only if >50% of traces fall within any single 3° distance bin; 200 iters, seed 0 | deterministic trigger mirrors its Mars rationale |
| Bootstrap Type III | uniform ±10 s alignment jitter, 200 iters, seed 0 (bootstrap_type3_alignment_jitter.py) | identical | |
| Occupancy | cells ≥ threshold×window-peak set to 1 per iteration; occurrence map across iterations; thresholds 50/70/85%, verdicts at 85% (paper Methods l.234; bootstrap scripts) | identical | |
| Uncertainty | Gaussian fits to occurrence-map projections on T and p axes; 1σ reported | identical | |

Code: the Mars pipeline modules are copied (never modified in place) into
`results/lunar_analog/code/`, with a diff-log of every adaptation. Environment:
`MAMBA_ROOT_PREFIX=/Users/artus/micromamba micromamba run -n mars-ic python` (obspy 1.4.1,
numpy 1.26.4). All random seeds fixed: type1=0, type3=0, N1=100+k (realization k), N4=1000+k.

## 6. Detection criteria (frozen numeric)

Definitions, per configuration × model × target phase, all computed from the Type I occurrence map at
the 85% threshold, with Gaussian fits to its time and slowness projections (mirroring
`results/tables/bootstrap_picks.csv` fields): fitted means (T_fit, p_fit), fitted sigmas (σ_T, σ_p),
and argmax occupancy value O_max (fraction of the 200 iterations in which the modal cell is occupied).

A target-box peak must additionally exist in the non-bootstrap vespagram (local max within the
Addendum A box, full stack support).

Two frozen grades. Calibration context (recorded here so the grades cannot be re-tuned later): the
repo's own Mars rerun achieves, at threshold 85% (results/tables/bootstrap_picks.csv, 2026-07-05):
PKiKP σ_T=43.0 s, σ_p=0.41 s/deg (fit collapsed toward grid edge), O_max=0.475; PKKP σ_T=49.3 s,
σ_p=0.84 s/deg, O_max=0.68. The paper itself reports ±2 s / ±0.6 s/deg (PKiKP) and ±5 s / ±0.4 s/deg
(PKKP). Hence:

- G1 "paper-grade" detection (all of):
  |T_fit − T_pred| ≤ 25 s; |p_fit − p_pred| ≤ 1.2 s/deg; σ_T ≤ 10 s; σ_p ≤ 1.0 s/deg; O_max ≥ 0.50;
  and the Type III (jitter) occurrence map satisfies the same location bounds with σ limits relaxed
  1.5×.
- G2 "replication-grade" detection (all of):
  |T_fit − T_pred| ≤ 50 s; |p_fit − p_pred| ≤ 2.0 s/deg; σ_T ≤ 50 s; σ_p ≤ 1.5 s/deg; O_max ≥ 0.45.

Config-level outcomes per phase: DETECTED-G1 / DETECTED-G2 / NOT-DETECTED / NOT-EVALUABLE.
G1 implies G2. Outcomes are recorded for both models' target boxes independently.

## 7. Implied core radius mapping (leader-only, post-detection)

For each detection: sweep core radius 100–700 km in 10 km steps within each reference model family
(M1 mantle with variable R_core; M2 mantle with variable R_OC holding its internal ratios), recompute
(T_pred, p_pred) of the detected phase at the config's reference distance/depth via TauP, and take the
radius minimizing the σ-weighted misfit to (T_fit, p_fit). Uncertainty: propagate (σ_T, σ_p) through
the local numerical derivatives dT/dR, dp/dR. This mapping is executed only after Sections 6 and 8
outputs are complete, and only by the leader (workers never receive reference radii).

## 8. Null-test suite (frozen)

All nulls use the full detection machinery of Section 6 (including Type I bootstrap at 200 iterations
and both grades) applied to each EVALUABLE primary configuration. Null realization counts are chosen
for compute feasibility and give FAR resolution of 2%.

- N1 event-scramble: randomly permute the distance labels across the config's traces (destroys
  moveout, preserves waveforms). 50 realizations, seeds 100+k. FAR_N1 = fraction of realizations
  yielding a detection (per grade, any model box).
- N2 decoy windows: on the REAL (unscrambled) config, run detection in 4 decoy boxes per model:
  target box time-shifted by {−300, −150, +150, +300} s (same slowness box). A decoy overlapping any
  Addendum A predicted phase (either model) within ±60 s is shifted outward in further ±75 s steps
  until clear (deterministic). FAR_N2 = fraction of decoy boxes yielding a detection, where the decoy
  "prediction" for the location criterion is the decoy box centre.
- N3 station swap: for each ordered station pair (X→Y): traces of X (sorted by own distance) are
  assigned the sorted distance labels of Y's qualifying event set, reference distance/depth of Y,
  and Y's Addendum A boxes. Uses min(N_X, N_Y) traces. 12 ordered pairs; FAR_N3 = fraction of pairs
  yielding a detection.
- N4 synthetic noise: per trace, phase-randomized surrogate (FFT of the filtered, pre-envelope
  waveform over the cut window; magnitudes preserved, phases uniform random) — envelopes and all
  downstream steps recomputed from surrogates. 50 realizations, seeds 1000+k. FAR_N4 = fraction of
  realizations yielding a detection.

Compute fallback (pre-declared): if the full null suite exceeds the phase budget, realization counts
may be halved (25/25 for N1/N4) by a dated Deviations-log entry made BEFORE any null results are
viewed. No other reductions permitted.

## 9. Study-level verdict rules (frozen)

Let the "real rate" be the fraction of EVALUABLE primary configs with DETECTED-G2 for the primary
target phase (either model). Then:
- RECOVERED: ≥3 of 4 primary configs DETECTED-G2 for the same phase and same model family; implied
  radii (Section 7) mutually consistent within ±20%; and each of FAR_N1, FAR_N2, FAR_N4 < (real
  rate)/3, with N3 producing no more detections than expected from its FAR-equivalent (≤2 of 12).
- RECOVERED-STRONG: as above at G1.
- METHOD-FRAGILE: any of FAR_N1, FAR_N2, FAR_N4 ≥ real rate; or N3 detections ≥ real-station
  detections; or detections occur but implied radii scatter >±35% across stations.
- NOT-RECOVERED: real rate = 0 with ≥3 EVALUABLE configs and null FARs also ~0 (the method is
  quiet on the Moon: neither recovery nor false-alarm inflation — reportable as a sensitivity floor).
- INCONCLUSIVE: anything else (e.g., <3 EVALUABLE configs); report per-config detail.

Secondary configs and the SHQ set inform the report narrative but never the verdict.

## 10. Roles and blindness protocol

- Order of operations: (1) this freeze → (2) Addendum A (model targets; no waveform contact) →
  (3) Phase 2 data download + mechanical QC + Addendum B (catalogue-only) → (4) A+B hashes logged in
  ledger → (5) pipeline runs. No stacking, no target-window plots, no vespagrams before step 5.
- Worker prompts contain procedure and acceptance criteria only. Forbidden in worker prompts:
  reference core radii, Weber/Garcia expectations, "we expect X", any statement of desired outcome.
- The leader applies Section 7 and Section 9 only after Sections 6/8 outputs exist as files.
- Every worker deliverable passes the Fable verification gate (docs/prompts/_conventions.md): ≥3
  spot-checks vs primary sources, ≥1 independent recomputation, lane diff check, verdict labels.

## 11. Deviations log

- DEV-2026-07-05-1 (pre-data; no Apollo waveform touched, no lunar results exist). §8 N2 decoy rule
  amended: a decoy box must satisfy box_t_min ≥ 20 s after P. Rationale: a toy-model TauP check of the
  Addendum-A script showed deep-moonquake PcP−P differential times can be ~90 s, so decoys shifted by
  −150/−300 s would land before the P arrival. Fix: any decoy violating box_t_min ≥ 20 s (or colliding
  with a predicted phase per the existing rule) is shifted in +75 s steps until valid; if the four
  decoys cannot all be placed within the cut window, place as many as fit (minimum 2) and record the
  count. Amendment is outcome-neutral geometry hygiene, logged before Phase 2 data arrived.
- DEV-2026-07-05-2 (pre-stacking; waveforms downloaded but nothing stacked, no target-window content
  viewed). §3.2 pick-source ranking replaced per PREREG Addendum C (operator handoff,
  PREREG_addendum_C_pick_sources_20260705.md) plus the leader's audit finding that the Addendum-C
  rank-1 candidate (Nakamura QuakeML) contains only minute-resolution pseudo-picks (VERIFIED by
  parsing: 25,376 picks, all at second=0, all identical across stations per event). Operative pick
  source = Nunn 2020 S3 workbook per-station arrival columns with fixed sheet ranking; no averaging.
- DEV-2026-07-05-3 (pre-stacking). §3.3 flatline and clipping QC rules recalibrated for Apollo LP
  10-bit data (original rules excluded 57/59 physically normal traces; measured flatline-fraction
  median 0.76). New rules: flatline ≥ 0.98 or zero variance; clipping >5% at rails with p2p ≥ 100 DU.
  Recalibration used only full-window mechanical statistics — no target-window inspection, no
  stacking, no spectral content beyond the already-permitted pre-P PSD.
- DEV-2026-07-05-4 (pre-stacking). §2 adds the diagnostic Ixx-IMP impact configuration (per-event
  picks are best-verified for impacts; artificial impacts are exact ground truth) and codifies that
  mixed-class stacks are not run (common-source-depth assumption). No change to primary configs or
  verdict rules: the expected operative primaries remain Pxx-DM (27–40°, likely reduced-power at
  N=5–10 with all-source picks) with the pre-declared automatic 20–60° widening (N=8–20).
- DEV-2026-07-06-5 (invoking the §8 pre-declared compute fallback; logged BEFORE any null realization
  was run or viewed). N1 and N4 run at 25 realizations each (FAR resolution 4%) instead of 50: the
  measured cost is ~3.5–5 min per realization (each includes two 200-iteration Type-I bootstraps, one
  per model variant), so 50 realizations × 3 evaluable primaries × 2 null types ≈ 18–20 h exceeded the
  phase budget. N2 and N3 run in full. Seeds unchanged (100+k / 1000+k, k = 0..24). Also recorded
  here for completeness: two mechanical crash-repairs to the port orchestrator, neither touching any
  frozen analysis parameter — (a) same-channel split segments in one DARTS miniSEED are merged iff no
  gap exceeds the 2 s QC limit (I14-IMP crash, 2026-07-06); (b) the aggregate peak_table.csv was
  regenerated over all 14 configs after a single-config rerun truncated it; regeneration verified
  byte-identical on a spot-checked vespagram npz.
