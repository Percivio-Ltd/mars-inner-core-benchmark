# PREREG: Earth Single-Station Positive Control of the Bi et al. (2025) Source-Array Vespagram Method (P0-EARTH-CTRL)

Status: FROZEN 2026-08-01 (registered card P0-EARTH-CTRL, `docs/research_pipeline.md` @ a2163d49;
executing worker sub-Fable). Amendments after this freeze require a dated entry in §12 (Deviations
log) BEFORE the affected results are viewed. Silent parameter changes invalidate the affected output.

Scope: this document freezes station, channel, event-selection floors, alignment convention,
pipeline parameters, numeric detection targets, the two detection grades, the null-test suite, and
verdict rules BEFORE any Earth waveform is downloaded, plotted, stacked, or otherwise inspected by
this job. Only station/channel metadata and event-catalog metadata (no waveforms) were accessed
before this freeze; each access is dated and archived under `catalog/`.

Isolated run directory: `/Users/artuskg/marsquake_runs/20260801_earth_ctrl/` (the repo
`/Users/artuskg/GitRepos/MarsQuake` is read-only for this job).

---

## 1. Objective and symmetric outcomes

Question: does the single-station, fourth-root, envelope, source-array vespagram machinery of
Bi et al. (2025), as reimplemented in the audited MarsQuake modules (`scripts/02_preprocess`,
`scripts/03_vespagram`, `scripts/04_bootstrap`) and ported 1:1 to the Moon in job A1
(`docs/lunar_analog_report.md`), recover known Earth core phases (PcP, PKiKP; ScS as a
plausibility-boundary phase) at ak135-predicted (time, slowness) on a single high-quality GSN
station's natural source array? The Moon showed the method fails on a hard target with a known
core; Earth answers whether it works on an easy one. This completes the calibration triptych:
Mars (unknown truth), Moon (known truth, hard data), Earth (known truth, easy data).

Both outcomes are reportable and publishable:
- RECOVERED / RECOVERED-STRONG: the frozen criteria detect the primary phase with null
  false-alarm rates well below the detection rate (§9).
- NOT-RECOVERED or METHOD-FRAGILE: no recovery, or nulls fire at comparable rates (§9).

Agreement with an expected result is never required. Detection-level only: NO radius inversion.

## 2. Station and channel (selected on instrument/coverage grounds before this freeze)

Candidates offered by the card: ANMO / KIP / MAJO. Metadata browsed 2026-08-01T18:21:22Z
(`catalog/station_metadata_iu_bhz.txt`) and 18:22Z (`catalog/event_counts_by_station.txt`);
no waveform contact.

**Selected: IU.ANMO.00.BHZ** (Albuquerque, New Mexico; 34.94591 N, -106.4572 E).

Grounds (recorded before any waveform contact):
1. Instrument/noise: borehole installation at 145-188 m depth (Geotech KS-54000 to 2018-07-09,
   Streckeisen STS-6A after), in the continental interior — the lowest secondary-microseism
   (0.1-0.35 Hz) environment of the three candidates. The frozen 0.2-0.8 Hz analysis band overlaps
   the secondary-microseism band, so this directly maximizes in-band SNR. KIP (island, vault STS-1)
   and MAJO (coastal Japan, vault STS-1) sit in high-microseism environments; MAJO additionally has
   heavy regional seismicity that the contamination screen (§3.4) would repeatedly trigger on.
2. Coverage: 84 catalog events with M >= 6.0, depth 10-70 km, 25-35 deg epicentral distance,
   2000-2026 (ANMO; vs KIP 97, MAJO 185 — all ample for the >= 15-trace support scale). The ANMO
   25-35 deg annulus is dominated by the Mexico/Central-America subduction arc: a single coherent
   source corridor spanning the full distance window — the closest structural analog to the Mars
   Cerberus Fossae source region.
3. Continuity: continuous 00/BHZ epochs 1998-present; GSN reference station.

Channel: BHZ, location 00, vertical only. Native rate 20 sps to 2018-07-09, 40 sps after.
No response deconvolution (mirrors the Mars pipeline, which filters counts and z-scores per trace);
per-trace z-score makes epoch gain changes irrelevant. Per-trace instrument epoch is recorded in
the manifest.

## 3. Event selection (frozen floors; instantiated from catalog only, before waveform contact)

### 3.1 Catalog source and query
- Source ranking: (1) USGS NEIC ComCat FDSN event service
  (`https://earthquake.usgs.gov/fdsnws/event/1/query`); (2) ISC Bulletin FDSN event service —
  fallback ONLY if USGS is unreachable; no other substitution.
- Frozen query: circle center (34.94591, -106.4572), minradius 25.0, maxradius 35.0 deg;
  mindepth 10, maxdepth 70 km; minmagnitude 6.0 (preferred magnitude, any type); origin time
  2000-01-01T00:00:00Z to 2026-01-01T00:00:00Z.
- Selection: rank by preferred magnitude descending (tie: earlier origin); take the top 40.
- Full query URL, access date, and SHA-256 of the raw response are recorded in
  `catalog/data_manifest.csv`.

### 3.2 Distances and alignment parameters
- Epicentral distance: great-circle from the catalog epicenter to the station coordinates above,
  WGS84 via obspy `gps2dist_azimuth` / 111.195 km per degree equivalent (obspy `locations2degrees`
  convention; recorded per event).
- Source parameters per event: catalog preferred origin (time, lat, lon, depth). Depths are
  catalog values (no re-estimation).

### 3.3 Alignment convention (declared adaptation D-ADAPT-E1)
- Mars aligned on MQS-published P picks (P at t=0). Earth traces are aligned on the ak135
  TauP-predicted absolute P arrival: t_P = origin_time + T_ak135(P; catalog depth, catalog
  distance), P at t=0. No picking is performed or adjusted by this job.
- Justification (a priori): NEIC hypocenters and origin times at these magnitudes give predicted-P
  accuracy of ~1-2 s at 30 deg — better than typical single-trace pick scatter, deterministic, and
  free of pick-availability selection effects. The pilot control (§10) verifies the full
  convention end-to-end on real data before the production run: observed P envelope energy must
  peak at t = 0 within tolerance.

### 3.4 Contamination screen (catalog-only, mechanical, frozen)
Exclude a candidate event if (self excluded from both tests):
- any global catalog event with M >= 6.0 has origin time in [t_P_abs - 2700 s, t_P_abs + 1300 s]; or
- any catalog event with M >= 5.0 within 15 deg of the candidate epicenter has origin time in
  [t_P_abs - 300 s, t_P_abs + 1300 s],
where t_P_abs is the candidate's predicted absolute P time at ANMO. Queried from the same catalog
source; responses archived and hashed.

### 3.5 Mechanical waveform QC (the only waveform inspection permitted before runs)
Applied per trace, scripted, no visual review of target windows:
- Coverage: trace must cover [P-200 s, P+1300 s] with <= 10% missing samples; gaps <= 2 s are
  linearly interpolated (samples flagged invalid in the valid-sample mask); longer gaps leave
  masked (invalid) samples; a trace with > 10% invalid samples in the cut window is excluded.
- Flatline: exclude if the fraction of identical consecutive samples in the cut window >= 0.98,
  or the window variance is zero.
- Clipping: exclude if (fraction of samples equal to trace min + fraction equal to trace max)
  > 5% AND peak-to-peak span >= 100 counts.
- Per-trace record: instrument epoch, native sample rate, miniSEED quality codes; no exclusions
  on quality codes (GSN GPS timing), recorded only.
- No SNR-based exclusion (mirrors Mars: no per-trace SNR gate).

### 3.6 Evaluability and pre-declared fallback ladder
- >= 15 usable traces: full support scale (Mars used 23).
- If < 15 usable from the top-40: extend to top-60 by the same ranking (still M >= 6.0).
- If still < 15: lower the floor to M >= 5.8 (133 candidates), top-60, same ranking.
- If still < 15 but >= 8: proceed with flag "reduced-power" (lunar evaluability floor).
- If < 8: NOT-EVALUABLE; stop and report.
Only this ladder is permitted; each step is a dated §12 entry made before any stacking.

## 4. Reference geometry and frozen numeric targets (Addendum A)

- Model: ak135 (obspy built-in). Reference distance 30.0 deg, reference depth 33.0 km — frozen
  a priori as the center of the selection annulus and the Mars paper's assumed source depth.
  (Mars froze a fixed reference of 29.0 deg, `run_vespagrams.py:305`; the fixed-reference
  convention is mirrored rather than the lunar median-derived rule, removing a data-dependent step.)
- Alignment predictions use per-event catalog parameters (§3.3); the reference geometry is used
  only for targets and the vespagram projection.
- Targets (generated by `code/make_addendum_A.py`, model-only; output
  `addendum_A_targets.json`, SHA-256
  `f3b2f18ccd56cd5bf1077f80e5c3e3f6b6608c58b924828bab1abe09decd2d67`):

| Phase | diff T (s) | diff p (s/deg) | box T (s) | box p (s/deg) |
|---|---|---|---|---|
| PcP | +181.67 | -6.259 | [141.67, 221.67] | [-7.759, -4.759] |
| PKiKP | +633.81 | -8.188 | [593.81, 673.81] | [-9.688, -6.688] |
| ScS | +636.72 | -4.064 | [596.72, 676.72] | [-5.564, -2.564] |

- Boxes: T_pred +/- 40 s, p_pred +/- 1.5 s/deg (lunar addendum-A convention). Absolute reference
  P: t = 365.50 s, slowness 8.845 s/deg.
- Primary target phase: **PcP** (the strongest core reflection; the "decisive phase" analog).
  PKiKP is the secondary, amplitude-hard target (known-weak at 30 deg on Earth; its recovery or
  non-recovery calibrates the Mars PKiKP claim, which used 23 far noisier traces). ScS on
  vertical is the plausibility-boundary phase (SV projects weakly on Z at this steep incidence;
  a "detection" here is evidence of promiscuity, not of skill).
- Registered note: PKiKP and ScS differ by only 2.91 s in time and share (nearly) one search
  window; only the slowness dimension separates them (predictions 4.12 s/deg apart, > the 2.0
  s/deg G2 location bound, so both cannot pass location simultaneously).
- No slowness-grid or cut-window auto-extension is triggered (all |p_pred| < 9.0 s/deg;
  all T_pred < 1100 s).

## 5. Pipeline parameters (1:1 map from the Mars modules; declared adaptations only)

Mars values from `scripts/02_preprocess`, `scripts/03_vespagram`, `scripts/04_bootstrap`
(the audited reimplementation of the paper's Methods), as in the lunar port.

| Parameter | Mars value (source) | Earth value | Note |
|---|---|---|---|
| Component | BHZ after ZNE rotation + polarization filter (paperfaith) | IU.ANMO.00.BHZ vertical only, no polarization filter | D-ADAPT-E2: mirrors lunar D-ADAPT-1 (vertical-only, envelope path) |
| Bandpass | 0.2-0.8 Hz Butterworth, 4 corners, zero-phase (`bandpass_filter.py:33`) | identical | band retained; ANMO chosen partly to minimize in-band microseism noise |
| Sampling | native 20 Hz (`shared.py:18`) | native 20 Hz epochs used as-is; 40-Hz epochs (post-2018-07-09) Lanczos-interpolated (a=20) to 20.0 Hz after filtering | D-ADAPT-E3: mirrors lunar D-ADAPT-2 mechanics |
| Alignment | MQS P pick, P at t=0 (`align_and_cut.py`) | ak135-predicted P (per-event catalog params), P at t=0 | D-ADAPT-E1 (§3.3); verified by pilot (§10) |
| Cut window | -100..2200 s rel. P | -100..+1300 s rel. P | covers all target boxes and decoys + margin |
| Normalization | per-trace z-score; variant A window 400-800 s (`normalize_and_envelope.py:24-28`) | A': z-score over [T_pred(PcP)-100, T_pred(PcP)+100] = [81.67, 281.67] s; C': full cut window | mirrors lunar A' primary convention; A' primary, C' secondary |
| Envelope | Hilbert envelope, 5.0 s smoothing, 5.0 s edge erosion (`normalize_and_envelope.py:21,125-130`) | identical (module functions reused) | |
| Input type | envelope (primary) | envelope only | waveform input not run (out of card scope) |
| Stack | 4th-root, n=4 (`run_vespagrams.py:220`; `stacking.py`) | identical (module copied) | pws not run |
| Min stack support | 2 (`stacking.py:6`) | identical | |
| Slowness grid | -10.0..0.0 s/deg, 100 steps (`run_vespagrams.py:189-191`) | identical | |
| Reference distance | 29.0 deg fixed (`run_vespagrams.py:305`) | 30.0 deg fixed | §4 |
| Power statistic | Hann-window power of stack (`compute_vespagram.py:82-93`) | identical; 20 s primary, 5 s secondary; grading at 20 s | |
| Peak search | target-box peak, 3x3 local-max check (`detect_peaks.py:207-216`) | identical logic on the earth vespagram | |
| Bootstrap Type I | floor(2N/3) events w/o replacement, 200 iters, seed 0, per-phase window max across all slowness, occupancy thresholds 50/70/85% (`bootstrap_type1.py`) | identical machinery; time windows = frozen box_t (+/-40 s) per graded window (3 phases; plus the 12 decoy windows in the real-data pass), full slowness axis; ref 30.0 | D-ADAPT-E4: window/ref parameterization only |
| Bootstrap Type III | uniform +/-10 s alignment jitter, 200 iters, seed 0 (`bootstrap_type3_alignment_jitter.py`) | identical machinery; same D-ADAPT-E4 window/ref parameterization (the Mars module hardcodes pkikp/pkkp windows and ref 29.0; both bootstrap modules are parameterized identically, no algorithm change) | G1 concordance input; computed for the 3 phase windows, the 12 decoy windows (real pass), and inside every N1 realization |
| Type II trigger | distance-stratified halving (paper Methods) | run diagnostically ONLY if > 50% of usable traces fall in a single 3-deg bin; never graded | lunar trigger rule |
| Occupancy statistic | occurrence map across iterations at threshold x window peak; verdicts at 85% | identical | |
| Uncertainty | Gaussian fits to occurrence-map T and p projections, 1-sigma (`fit_gaussian.py`) | identical (module reused) | |

Port custody: Mars modules are copied (never modified in place) into `code/` with a diff log of
every adaptation (`code/PORT_DIFF_LOG.md`). The repo stays unmodified.

## 6. Detection criteria (frozen numeric; copied exactly from the lunar design)

Per phase, computed from the Type-I occurrence map at the 85% threshold with Gaussian fits to its
time and slowness projections: fitted means (T_fit, p_fit), sigmas (sigma_T, sigma_p), argmax
occupancy O_max. A target-box peak must additionally exist in the non-bootstrap vespagram (local
maximum by the 3x3 neighbor check within the graded box, full stack support). This box-peak
requirement applies SYMMETRICALLY (DEV-2026-08-01-1): to real-data detections (real vespagram,
target box), to every N1 realization (that realization's own permuted-distance non-bootstrap
vespagram, target box), and to every N2 decoy (real vespagram, decoy box).

- G1 "paper-grade" detection (all of): |T_fit - T_pred| <= 25 s; |p_fit - p_pred| <= 1.2 s/deg;
  sigma_T <= 10 s; sigma_p <= 1.0 s/deg; O_max >= 0.50; and the Type-III (jitter) occurrence map
  satisfies the same location bounds with sigma limits relaxed 1.5x.
- G2 "replication-grade" detection (all of): |T_fit - T_pred| <= 50 s; |p_fit - p_pred| <= 2.0
  s/deg; sigma_T <= 50 s; sigma_p <= 1.5 s/deg; O_max >= 0.45.

Outcomes per phase: DETECTED-G1 / DETECTED-G2 / NOT-DETECTED. G1 implies G2. The calibration
context for the two grades is recorded in the lunar PREREG §6 and report §1 and is not re-derived
here; the numbers above are copied verbatim from the lunar design per the card.

## 7. (reserved — no radius mapping in this card)

Detection-level only. No implied-radius sweep is computed or reported.

## 8. Null-test suite (frozen)

Both nulls use the full §6 detection machinery (Type-I bootstrap, 200 iterations, both grades,
same frozen targets) on the usable-trace set.

- N1 event-scramble: randomly permute the distance labels across the usable traces (destroys
  moveout, preserves waveforms). 25 realizations, seeds 100+k (k=0..24), numpy default_rng
  permutation. Each realization runs the full machinery: its own non-bootstrap vespagram (box-peak
  local-max requirement per §6), Type-I bootstrap (200 iters, seed 0), and Type-III bootstrap
  (200 iters, seed 0) for the G1 concordance rider. FAR_N1(grade) reported per phase (fraction of
  realizations detecting that phase) and any-phase (fraction detecting at least one).
- N2 decoy windows: on the REAL (unscrambled) stack, run detection in the 12 frozen decoy boxes
  (4 per phase, same slowness box as the phase, centers pre-placed by the deterministic
  collision-avoiding walk in `code/make_addendum_A.py`; all 12 placed, walk steps recorded):

| Phase | shift -300 | shift -150 | shift +150 | shift +300 |
|---|---|---|---|---|
| PcP | 538.33 | 763.33 | 931.67 | 1081.67 |
| PKiKP | 536.19 | 761.19 | 933.81 | 1083.81 |
| ScS | 533.28 | 758.28 | 936.72 | 1086.72 |

  The decoy "prediction" for the location criteria is the decoy box center (time) with the
  phase's predicted slowness. Decoys are graded with the full machinery on the real data: the
  real-data Type-I and Type-III passes extract each decoy window alongside the phase windows
  (identical per-iteration vespagrams), and the box-peak local-max requirement applies within
  each decoy box of the real non-bootstrap vespagram (§6). FAR_N2(grade) = fraction of the 12
  decoy boxes yielding a detection; also reported per phase (fraction of its 4 decoys).
- Earth decoy-placement rule (geometry adaptation of lunar DEV-2026-07-05-1, declared pre-data):
  center domain [60, 1160] s; candidates c0 + 75*d*k reflected at the domain bounds; must clear
  every collision-list phase time by >= 60 s, the same-phase target by >= 60 s, and same-phase
  decoys by >= 100 s; collision list = first arrivals of {P, pP, sP, PP, PPP, PcP, pPcP, sPcP,
  S, sS, SS, ScP, PcS, ScS, PKiKP, SKiKP, PS, SP} at the reference geometry (SKS/PKP/PKKP absent
  at 30 deg), frozen in `addendum_A_targets.json`.

No N3 (station swap) — single-station design; no N4 (synthetic noise) — not in the card.

## 9. Study-level verdict rules (frozen)

Primary phase = PcP. With one configuration the real rate is 0 or 1, so the lunar rate-ratio
rules are instantiated as:

- RECOVERED: PcP DETECTED-G2 on real data, AND FAR_N1^PcP(G2) < 1/3 AND FAR_N2^PcP(G2) < 1/3.
- RECOVERED-STRONG: as above with all three conditions at G1.
- METHOD-FRAGILE: PcP detected at a grade, but FAR_N1^PcP or FAR_N2^PcP >= 1/3 at that grade
  (the "detection" is not distinguishable from the machinery's false-alarm behavior).
- NOT-RECOVERED: PcP NOT-DETECTED at G2 with nulls also quiet (both PcP FARs < 1/3 at G2) —
  the method misses an easy known target: a sensitivity-floor result.
- INCONCLUSIVE: anything else (including NOT-EVALUABLE data).

PKiKP and ScS outcomes and their FARs are always reported per grade alongside (secondary and
plausibility-boundary rows); they do not move the verdict. Any-phase FARs are reported for
comparability with the lunar table. All numbers appear in `analysis/detection_table.csv` and
`analysis/far_table.csv` regardless of outcome.

Grade precedence (DEV-2026-08-01-1): the verdict labels are evaluated and reported PER GRADE,
independently — one G1-level label (from the G1 detection + G1 FARs) and one G2-level label (from
the G2 detection + G2 FARs). No cross-grade aggregation: e.g. "RECOVERED-STRONG at G1;
METHOD-FRAGILE at G2" is a valid, fully reported outcome pair. The card-level headline quotes
both labels.

## 10. Positive control (pilot; BEFORE the production run)

Pilot event = the highest-magnitude usable event (tie: earlier origin). After bandpass, alignment,
and envelope (variant A'), the pilot trace must satisfy:
- P-alignment check: argmax of the envelope in the window [-30, +30] s lies within |t| <= 10 s
  (predicted P at t = 0 within tolerance; envelope smoothing is 5 s).
- SNR sanity: that envelope peak >= 3x the median envelope over the pre-P segment [-200, -50] s.
Pilot failure = STOP; diagnose and fix the alignment convention only; any fix is a dated §12
entry; no target-window inspection beyond the [-30, +30] s alignment window and the pre-P segment.

## 11. Environment, seeds, order of operations

- Interpreter: `/Users/artuskg/micromamba/envs/mars-ic/bin/python` exclusively (obspy 1.4.x,
  numpy 1.26.x; versions recorded in the report).
- Seeds: Type I seed 0; Type III seed 0; N1 realization k uses seed 100+k. No other RNG.
- Waveform source ranking: (1) EarthScope/IRIS FDSN dataselect
  (`service.iris.edu` -> `service.earthscope.org`); obspy FDSN client primary, raw curl to the
  same endpoint as mechanical fallback (same archive, not a source substitution). If acquisition
  stalls > 1 h total: STOP-AND-REPORT (card rule).
- Every download dated + SHA-256 in `catalog/data_manifest.csv`.
- Order: (1) this freeze + SHA-256 -> (2) Codex `gpt-5.6-sol` `xhigh` countersign of this PREREG
  -> (3) catalog query + selection + contamination screen (catalog-only) -> (4) waveform download
  + mechanical QC -> (5) pilot (§10) -> (6) production run + Type-III -> (7) N1/N2 nulls ->
  (8) detection/FAR tables -> (9) REPORT.md -> (10) final Codex countersign. No stacking, no
  target-window plots, no vespagrams before step 6; §6/§8/§9 are applied only after outputs exist
  as files.
- Timebox: if the full N1 suite would overrun the card timebox, the pre-declared floor is the
  card's own: 25 realizations (already the minimum; no further reduction permitted — a smaller
  count is a STOP-AND-REPORT).

## 12. Deviations log

- DEV-2026-08-01-1 (pre-data; no Earth waveform downloaded or inspected; entered after Codex
  countersign round 1, before round 2). Three amendments from the round-1 review
  (`countersign/prereg_countersign_r1.md`):
  (a) §6/§8: the non-bootstrap box-peak local-max requirement is applied symmetrically to real
  data, every N1 realization, and every N2 decoy box (round-1 P1-1; the original text exempted
  nulls, diverging from the lunar frozen design's "full detection machinery" rule);
  (b) §5/§8: D-ADAPT-E4 explicitly covers `bootstrap_type3_alignment_jitter.py` as well as
  `bootstrap_type1.py` (both hardcode Mars pkikp/pkkp windows and ref 29.0; both are parameterized
  to the frozen Earth windows and ref 30.0 with no algorithm change), and Type-III statistics are
  computed for all graded windows including inside N1 realizations and for N2 decoys (round-1
  P1-2: G1 grading was otherwise not executable);
  (c) §9: per-grade verdict evaluation with no cross-grade aggregation (round-1 P2).
  All amendments are outcome-neutral: entered before any waveform contact.
- DEV-2026-08-01-2 (pre-pilot; waveforms downloaded and mechanically QC'd, nothing stacked, no
  target-window content viewed, pilot not yet executed). §10 geometry fix: the pilot SNR pre-P
  segment [-200, -50] s lies partly outside the frozen cut window (starts -100 s) and the 5-s
  envelope edge erosion (envelope zero in [-100, -95]). Operative segment: [-90, -50] s. The
  alignment-check window [-30, +30] s and the |t| <= 10 s tolerance are unchanged.
- DEV-2026-08-01-3 (pilot STOP-and-diagnose; nothing stacked, no target-window content viewed;
  diagnosis used only the permitted [-30, +30] s and [-90, -50] s windows of the pilot trace).
  The frozen pilot statistic (envelope argmax in [-30, +30] within |t| <= 10) FAILED on the pilot
  event usp000juhz (M7.8): argmax at +29.25 s, at the window edge, with SNR 66x. Diagnosis: the
  envelope is flat (<= 1.1x pre-P median) through -5 s, first crosses 3x pre-P median at -2.05 s
  and 5x at -0.05 s, then rises monotonically — the predicted-P alignment (D-ADAPT-E1) is correct
  to ~0 s; the argmax statistic instead measures the M7.8 source duration (envelope maximum tens
  of seconds after onset), a large-earthquake effect absent on Mars-magnitude events. Per the
  card's "fix alignment convention only": the alignment CONVENTION is unchanged; the pilot CHECK
  statistic is replaced by the onset criterion — first crossing of 5x the pre-P median envelope
  within [-30, +30] must lie within |t| <= 10 s (plus the unchanged SNR >= 3 requirement).
  Operative pilot result: crossing -0.05 s, SNR 66.1 -> PASS. Recorded before any stacking.
