# Lunar Analog Blind Test of the Bi et al. (2025) Source-Array Vespagram Method

Job A1 final report — 2026-07-06. Fable leader with three Codex data/port workers.
Pre-registration: `results/lunar_analog/PREREG_criteria.md` (frozen 2026-07-05 before any Apollo
waveform contact; all amendments dated, outcome-neutral, and logged pre-results; final SHA256
`ab5f80340a2a9f6c7e28fbe7f35198e9ffb968070c2e7d1f86728a9af6e5e119`). Full audit trail, data
manifests, run outputs, and analysis tables under `results/lunar_analog/`.

## One-paragraph summary

We ported the single-station, fourth-root, envelope, source-array vespagram machinery of Bi et al.
(2025) 1:1 to Apollo lunar data (six of seven pipeline modules byte-identical to the repo's audited
Mars implementation) and asked, under pre-registered criteria, whether it recovers the lunar core —
a body where independent estimates exist (Weber et al. 2011: R_OC ≈ 330 km; Garcia et al. 2011
VPREMOON: R ≈ 380 km). The answer is a clean, symmetric negative with high evidential value: **at
the statistical tightness the paper claims ("paper-grade", σ_T ≤ 10 s), the method detects nothing
on the real Moon (0/3 stations) while still false-alarming on scrambled and synthetic-noise nulls
(15–33%); at the tightness the repo's own Mars rerun actually achieves ("replication-grade",
σ_T ≤ 50 s), the method "detects" core reflections everywhere — real data (3/3 stations), randomly
distance-scrambled data (75/75 realizations), phase-randomized noise (72/75), station-swapped
geometry (6/6), and two-thirds of arbitrary decoy windows.** The implied core radii of the
"detections" scatter from 100 to 470 km and disagree between stations. Formal pre-registered
verdict at both grades: **METHOD-FRAGILE** — the machinery's occupancy peaks are, by themselves,
not evidence of core phases at these trace counts and noise conditions.

## 1. Design

- **Method fidelity.** The port copies the repo's Mars pipeline (`scripts/02_preprocess`,
  `03_vespagram`, `04_bootstrap` — itself the audited reimplementation of the paper's Methods):
  0.2–0.8 Hz zero-phase Butterworth; alignment on published P picks (P at t=0); per-trace z-score;
  Hilbert envelope with 5 s smoothing; 4th-root stack over relative slowness −10→0 s/° (100 steps);
  Hann-window power (20 s primary); Type I (⌊2N/3⌋ resample, 200 iter) and Type III (±10 s jitter)
  bootstraps; occurrence maps at the 85% threshold with Gaussian-fit statistics. Diff audit:
  `stacking, bandpass_filter, align_and_cut, normalize_and_envelope, detect_peaks, bootstrap_type1,
  bootstrap_type3` byte-identical; `compute_vespagram` differs in import mechanics only. Lunar
  adaptations (declared): LP-vertical only, no polarization filter; Lanczos resample 6.625→20 Hz;
  cut −100…+1200 s.
- **Blindness.** Pipeline workers never saw the PREREG, reference radii, detection thresholds, or
  outcome language; they delivered mechanical statistics. The leader applied frozen criteria only
  after run and null outputs existed as files.
- **Two frozen grades (the key calibration decision).** G1 "paper-grade" mirrors the precision the
  paper reports (e.g. PKiKP σ_T = 2 s, σ_p = 0.6 s/°): |ΔT| ≤ 25 s, |Δp| ≤ 1.2 s/°, σ_T ≤ 10 s,
  σ_p ≤ 1.0 s/°, occupancy ≥ 0.50, Type-III concordance. G2 "replication-grade" mirrors what the
  repo's own Mars rerun achieves at the 85% threshold (PKiKP σ_T = 43.0 s, PKKP σ_T = 49.3 s,
  argmax occupancy 0.475–0.68; `results/tables/bootstrap_picks.csv`): |ΔT| ≤ 50 s, |Δp| ≤ 2.0 s/°,
  σ_T ≤ 50 s, σ_p ≤ 1.5 s/°, occupancy ≥ 0.45. Without G2 the lunar test would be rigged to fail
  (held to a standard the Mars analysis itself does not meet); without G1 it would be rigged to
  pass trivially.
- **Targets.** Model-derived (TauP), never copied Mars seconds: PcP (both models), PKiKP (Weber),
  ScS, PKPPKP, per config at its reference distance/depth; boxes ±40 s, ±1.5 s/°
  (`results/lunar_analog/addendum_A_targets.csv`).

## 2. Data

Apollo PSE LP-vertical, stations 12/14/15/16 (IRIS FDSN network XA; JAXA DARTS fallback), 228
QC-passing event-windowed traces. Events and picks: Nakamura levent.1008c catalogue (checksum-
verified against live UTIG) + published per-station P arrivals from the Nunn et al. (2020) S3
compiled-arrival workbook (156 unique event–station P picks after ranked single-source selection —
never averaged, never re-picked). A tempting alternative source was refuted during verification:
the 25,376 "P picks" in the Nunn QuakeML are minute-resolution levent signal-start times replicated
across stations, not seismic arrivals. Deep-moonquake traces are the workbook's dated cluster
reference occurrences (one per cluster–station). Pre-P noise PSDs confirm the 0.2–0.8 Hz band is
usable at all four stations.

**Configurations** (per pre-registered floors; trace counts = qc_ok):

| Config | Type | Band | N | Evaluable (≥8)? |
|---|---|---|---|---|
| P12/P14/P15/P16-DM | deep moonquakes | 27–40° | 4/5/5/5 | no (reported descriptively) |
| P12-DM-wide | deep moonquakes | 20–60° | 7 | no (misses by 1) |
| **P14/P15/P16-DM-wide** | **deep moonquakes** | **20–60°** | **11/16/14** | **yes — the primary test set** |
| I12/I14/I15/I16-IMP | impacts (diagnostic) | 15–70° | 15/5/17/19 | I12/I15/I16 yes |
| S15/S16-SHQ | shallow (diagnostic) | 15–70° | 6/3 | no |

A geometric finding worth flagging: deep-moonquake sources (~900–1000 km depth) compress the
core-reflection differential slowness to ≈ −1 s/° (vs −6.5 s/° for Mars PKiKP), intrinsically
weakening the method's slowness discrimination on the Moon's natural "source array"; surface-source
impact configs sit at ≈ −3.4 s/°.

## 3. Results

### 3.1 Real-data detections (frozen criteria; `analysis/detection_table.csv`)

At G2, 42 of 84 (config × model × phase) combinations "detect", including physically implausible
ones: ScS on vertical-only deep-moonquake stacks, PKPPKP through VPREMOON's undefined core velocity
(the source table literally lists `?`), and impact configs detecting nearly every phase under both
mutually inconsistent reference models simultaneously. On the primary test set and primary phase
family (core-reflected P): **3/3 stations at G2; 0/3 at G1.**

### 3.2 Null suite (frozen; DEV-5 realization counts; `analysis/far_table.csv`)

| Null | Unit | n | fires G2 | FAR G2 | fires G1 | FAR G1 |
|---|---|---|---|---|---|---|
| N1 event-scramble (distances permuted) | realization | 75 | 75 | **1.000** | 18 | 0.240 |
| N4 phase-randomized noise (spectra kept) | realization | 75 | 72 | **0.960** | 11 | 0.147 |
| N3 station swap (rank-mapped geometry) | ordered pair | 6* | 6 | **1.000** | 2 | 0.333 |
| N2 decoy windows (±150/300 s shifts) | decoy box | 24 | 16 | **0.667** | 0 | 0.000 |

*9 pairs ran; the 6 with evaluable-target boxes were graded.

Real G2 rate = 3/3 = 1.0. §9 fragility condition (any FAR ≥ real rate): met by N1 and N3, with N4
at 0.96. At G1: real rate 0 while nulls fire at 15–33% — **synthetic noise "detects" a lunar core
at paper-grade more often than the actual Moon does.**

### 3.3 Implied core radii of surviving G2 detections (§7 mapping; `analysis/implied_radii.csv`)

| Config | Model/phase | best-fit R (km) |
|---|---|---|
| P14-DM-wide | weber PKiKP | 100 (sweep floor) |
| P15-DM-wide | vpremoon PcP / weber PcP / weber PKiKP | 380 / 470 / 100 |
| P16-DM-wide | vpremoon PcP / weber PcP / weber PKiKP | 170 / 100 / 100 |

Scatter spans the entire sweep range; four of seven pin at the 100-km floor; station-to-station
disagreement far exceeds the ±20% consistency requirement. One slowness fit collapsed to the grid
edge (slowness ≈ 0, the P-coda ridge) — the same degeneracy the repo's Mars rerun shows for PKiKP.

### 3.4 Pre-registered verdict

**METHOD-FRAGILE at both grades** (PREREG §9): at G2 because nulls fire at or above the real rate;
at G1 because the real rate is zero while nulls still fire. The RECOVERED path additionally fails
on radius consistency. Per the PREREG, this is a reportable symmetric outcome: the test was
designed so that either recovery or fragility would be meaningful.

## 4. Implications for the Mars claim's methodology

1. **The occupancy machinery finds box-localized peaks unconditionally at replication-grade.**
   Envelope + 4th-root stacking + 85%-of-peak occurrence mapping over a ±40 s, ±1.5 s/° box yields
   "consistent" bootstrap peaks in scrambled data and pure noise with FAR ≈ 1. Whatever evidential
   weight the Mars detections carry must come entirely from the *tightness* of the reported
   uncertainties (σ_T ≈ 2–5 s), not from the existence, stability, or bootstrap-consistency of
   occupancy peaks.
2. **That tightness is precisely what the repo's Mars rerun does not reproduce** (σ_T ≈ 43–49 s,
   PKiKP occupancy mass collapsed toward the slowness-grid edge; Paper 0/1 materials). The lunar
   test closes the loop: at the reproduced (loose) operating point, such peaks are demonstrably
   uninformative; at the claimed (tight) operating point, the method produced nothing on a body
   with a known core — while still false-alarming on nulls at 15–33% (n.b. lunar noise conditions
   differ; see limitations).
3. **Slowness discrimination is the load-bearing dimension, and it is fragile.** Multiple fits
   (lunar and Mars) collapse to the slowness-grid edge; the deep-source lunar geometry compresses
   the discriminant to ≈ −1 s/°. Any application of this method should demonstrate slowness
   resolution on nulls before interpreting peaks.
4. **Every future single-station stacking claim needs a matched null suite.** Event-scramble and
   decoy-window nulls are cheap (this study's entire null computation: ~9.5 h on a laptop) and
   would have flagged the fragility immediately. Their absence from the original Methods is the
   central methodological gap this test exposes.

## 5. Limitations

- Lunar LP data are not Mars VBB data: intense scattering coda, 10-bit resolution, and peaked-mode
  response make the Moon a *harder* stacking target. Fragility here does not prove the Mars
  detections are false — it proves the method's internal consistency checks (bootstrap occupancy,
  multi-configuration presence) cannot distinguish true from false at these SNRs and trace counts,
  and that its null-behavior must be characterized per-dataset.
- Trace counts (11–16 vs Mars's 23) are lower; the pre-registered reduced-power flags apply. The
  impact diagnostics (15–19 traces, ground-truth sources) nonetheless show the same
  detect-everything pattern.
- Deep-moonquake "events" are cluster reference occurrences with published stack-derived picks;
  pick-transfer precision is a data property we could not improve without violating the
  no-own-picks rule.
- VPREMOON's core velocities are undefined in the source (`?`); core-transiting VPREMOON phases
  (PKPPKP) are therefore model-arbitrary and were used only as additional detection surface, never
  for radius inference.
- N1/N4 ran at 25 realizations (pre-declared DEV-5 fallback; FAR resolution 4%) — immaterial given
  FARs of 0.96–1.00.
- The Weber-family radius sweep holds internal layer ratios fixed; alternative parameterizations
  would change best-fit values but not the scatter conclusion.

## 6. Proposed patches (for Paper 1 to absorb)

- **P1-LUNAR-1 (core argument).** Add the lunar analog as the method-validation section: the
  identical machinery, blind and pre-registered, yields FAR ≈ 1 nulls at replication-grade and zero
  real detections at paper-grade. Strengthens Paper 1's central claim that the Mars detections'
  evidential weight rests on unreproduced uncertainty tightness.
- **P1-LUNAR-2 (quantitative anchor).** Cite the two-grade calibration table: paper-claimed
  σ_T = 2–5 s vs repo-reproduced σ_T = 43–49 s vs lunar-null σ_T distributions (indistinguishable
  from real data at G2). One table, three columns, decisive.
- **P1-LUNAR-3 (recommendation).** Propose the minimal robustness standard for single-station
  source-array claims: pre-registered detection criteria + event-scramble and decoy-window nulls
  with reported FARs. This study is the worked example.
- **P1-LUNAR-4 (slowness caveat).** Note the recurring slowness-fit collapse to the grid edge
  (Mars PKiKP rerun; multiple lunar fits) as a diagnostic that occupancy mass is tracking the
  P-coda ridge rather than a distinct arrival.

## 7. Provenance

- PREREG + Addenda A/B hashes: PREREG `ab5f8034…e119`; targets `6140ec60…93f1`; inventory
  `28089391…d968`; models `vpremoon.nd 9d58259f…f56c`, `weber2011.nd 10ed4b24…fa37a`.
- Data workers 1–3 manifests: `results/lunar_analog/data_manifest.md` (sources, access-dated URLs,
  checksums, NO-EVIDENCE trail); pick-sheet audit: `data/catalogue/pick_sheet_audit.md`.
- Leader verification gates (ledger `CONTINUITY-lunar-analog.md`): catalogue checksum vs live UTIG;
  both velocity models vs primary/secondary sources; QuakeML pseudo-pick refutation; 5/5 event
  metadata checks vs raw levent records; byte-level port diff; deterministic rerun (byte-identical
  npz); full sweep executed by the leader end-to-end.
- Runs: `results/lunar_analog/runs/` (14 configs; per-config vespagram/occupancy npz + stats);
  nulls: `runs/nulls/` (N1 75, N2 24 boxes, N3 9 pairs, N4 75; zero failures; log
  `runs/nulls/null_sweep_20260706.log`).
- Analysis: `results/lunar_analog/analysis/{detection_table,far_table,implied_radii}.csv`,
  criteria code `code/apply_criteria.py`, radius sweep `code/radius_map.py`.
