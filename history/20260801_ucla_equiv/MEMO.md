# P0-UCLA-EQUIV — UCLA_v4 Octave-vs-MATLAB reference equivalence on S0235b

Date: 2026-08-01. Host: Nimue (macOS arm64, Darwin 24.6.0). Author: sub-Fable worker.
Run dir: `/Users/artuskg/marsquake_runs/20260801_ucla_equiv/`.
Canonical repo consulted read-only; no canonical-path, `data/`, or `results/` writes.

Card authority: `docs/research_pipeline.md` § "P0-UCLA-EQUIV" registered at commit
`a4f63483`, frozen copy `card_text_frozen_a4f63483.md`
(SHA-256 `9b740f745d62a8e5c0611d6c64e69c25bd669a02593e667ccda2b29392ceea91`);
verified identical to the current worktree card text. Readouts, decision rule,
alignment precondition, and controls were fixed there before any outcome existed.
Lead pre-decisions (LANDING.md, taken before this run): shipped fixtures as-is,
`MAIN20SPSReconcile` included, `Conservative = 0`, full shipped sample extent.

## CLASSIFICATION: DIVERGENT-MINOR (frozen rule, applied mechanically)

- EQUIVALENT limb fails: counts (43, 34, 36) are not exactly (43, 34, 37) — W
  is short by one fitted glitch. (All three R_ch would have passed the 0.1
  bar.)
- DIVERGENT-MINOR limb holds: |dN| = (0, 0, 1) <= 2 per channel AND
  R_ch = (0.0886, 0.0429, 0.0833) <= 0.5 on every channel.
- Card consequences: mismatched glitches localized below; strict
  `mps_ucla_verified` attestation stays reserved; lead adjudicates. Per the
  card's registered outcome-neutral interpretation this is a reproducible,
  localizable MATLAB<->Octave divergence in a published deglitch package; the
  accepted MPS-only lane and its honest caveat stand unchanged; no benchmark
  rerun is in scope.

## Question

Does UCLA_v4, executed under the countersigned Octave route (P0-UCLA-FEAS,
verdict EXECUTABLE-OCTAVE), numerically reproduce the authors' own shipped
MATLAB outputs (`dc.mat`, `aaout3.mat`) on the archive's own sample event
`S0235b_VBB.mseed`? This gates whether `mps_ucla_verified` strict attestation
can ever rest on the Octave lane; both directions are registered as valid
outcomes.

## Setup

- Environment: micromamba env `octave-ucla` — GNU Octave 10.3.0 (conda-forge,
  osx-arm64), Octave Forge `signal` 1.4.7 + `control` 4.2.3 (rebuild recipe in
  `history/20260801_ucla_feas/FEASIBILITY_CARD.md`). Verified live:
  `octave --version` = 10.3.0; `butter`/`filtfilt` smoke check passed.
- Inputs: `external/seisglitch/MATLAB_ALTERNATIVES/UCLA_v4.zip`
  (SHA-256 `2eb91194a45e847e6ad58e94cb6f2f0ffc1f0fb838a12d40087c8f24de2dd2f7`),
  fresh-extracted three times: `run1/` (pass 1), `run2/` (pass 2, determinism),
  `ucla_v4/` (read-only precheck). Pristine references extracted separately to
  `refs/`: `dc.mat`
  SHA-256 `7cc4f0dadc14c5da533e46532d4090954ea1f07f552792769191c29512798647`,
  `aaout3.mat`
  SHA-256 `90c6bf09db4bfbc9ad32b7a276cce83c74394c08b2085e7faa26e4966d122eb7`.
  Starting state verified byte-identical across all extractions. No Paper 0
  event data touched.
- Shipped flow driven by `scripts/ucla_equiv_driver.m`, mirroring `MAIN.m` from
  its line 24 (`file='S0235b_VBB.mseed'`) onward: `MAIN2SPS` (XseedDataFDS
  channel selection 02:BHU/BHV/BHW → `funcadjustTimes` → decimate to 2 sps →
  `stalta` → `funcPeaker` pass 1 at cclim=0.9 → `MAIN20SPSReconcile` as shipped
  → `funcPeaker` pass 2 at cclim=0.4 → `PlotFinalNew2SPS`) → `pause(3)` →
  `MAIN20SPSJuly26` (shipped `Conservative=0` three-model competition,
  `PREP08`/`PREP03`/`PREP39` + `testSpikes` + residual replacement; saves
  `aaout3`/`dc`; ends with `PlotFinalNew`). `MakeGlitch` NOT called; shipped
  green/parameter fixtures loaded as-is (verified: cclim=0.9, cclim2=0.8,
  Nlevel=4, NLIMspike=3, fetch=1, Conservative=0).
- Visual neutralizations ONLY (card-permitted): `pause()` stubbed to a no-op
  (`stubs/pause.m`, path-shadowing; verified `pause(2)` elapsed 0.001 s) and
  plots rendered offscreen (headless; gnuplot fell back to an 'unknown'
  terminal producing no output — warnings only). No shipped `.m` file was
  modified; SHA-verified against the archive. The accept/reject logic reads
  neither pauses nor plot state.
- Driver error policy (fixed before running): a caught stage error is tolerated
  only if all computational postconditions hold AND the innermost stack frame
  is in the purely visual epilogue (`PlotFinalNew2SPS`/`PlotFinalNew`, which
  only read result variables); anything else is STOP-AND-REPORT.
- Comparator `scripts/compare_equiv.py` (mars-ic python, scipy 1.13.1) written
  and frozen BEFORE any chain outcome was inspected; implements the card's
  frozen readouts/decision rule mechanically.

## Frozen alignment precondition

After `funcadjustTimes`, each channel must have exactly 142840 samples
(reference length). SATISFIED three times independently: standalone precheck
(`logs/precheck_control.log`) and the in-run ALIGN-CHECK of both passes
(`logs/run1_driver.log`, `logs/run2_driver.log`): 142840 / 142840 / 142840.
No resampling or trimming was performed anywhere.

## Per-channel comparison table

Pass 1 (`run1_results.mat`) vs pristine shipped reference; full precision in
`comparison_table.csv`; comparator output in `logs/compare_main.log`.

| ch | len oct/ref | N_glitch oct vs ref | dN | R_ch | max abs(dc_oct-dc_ref) [counts] | rms(dc_oct-dc_ref) | rms(Data-dc_ref) | rows matched +/-2 |
|----|------------------|----|----|--------|-------|------|-------|----|
| U | 142840 / 142840 | 43 vs 43 | 0 | 0.0886 | 174.5 | 7.88 | 88.98 | 1 of 34 fitted |
| V | 142840 / 142840 | 34 vs 34 | 0 | 0.0429 | 277.6 | 5.55 | 129.26 | 3 of 30 fitted |
| W | 142840 / 142840 | 36 vs 37 | -1 | 0.0833 | 223.7 | 6.33 | 76.06 | 0 of 27/28 fitted |

The +/-2-sample fit-row matching (frozen, descriptive, non-decisional) matches
almost nothing NOT because the fits disagree wildly but because the
window-start indices carry a systematic +10-sample offset (below). Padding-row
counts (multi-glitch members) agree exactly per channel (9/9, 4/4, 9/9);
row-extraction failures 0 everywhere.

## Localization of the divergence (post-hoc descriptive, required by the
DIVERGENT-MINOR limb; `scripts/localize_posthoc.py`, `logs/localize_posthoc.log`)

1. Systematic window-start offset: pairing fitted rows at wide tolerance,
   offsets oct-ref concentrate at +10 samples at 20 sps = exactly one 2 sps
   sample (U: 30 of 33 pairs at +10, 2 at +20, 1 at 0; V: 26/30 at +10;
   W: 14 at +10 and 13 at +20, i.e. one-to-two 2 sps samples). The Octave
   2 sps detection stage (decimate -> filtfilt STA/LTA -> findmaxs argmax and
   offset-median) lands glitch indices one (sometimes two) 2 sps samples later
   than the authors' MATLAB run. The 20 sps refit re-centers phases within
   each window, so the corrections still track the reference (R_ch <= 0.089).
2. Count mismatch localized to ONE glitch: the reference fits a glitch at
   N1=1200 (window [1200,1700] at 20 sps, t about 66 s, fflag=3) on BOTH U and
   W; the Octave run fits it on NEITHER. On U the Octave run instead fits an
   extra glitch at N1=129010 (t about 6456 s, fflag=39) that the reference
   lacks, leaving N_U = 43 = 43 by cancellation; on W nothing compensates,
   giving 36 vs 37. V has no unpaired rows.
3. The waveform disagreement concentrates exactly there: rms(dc_oct-dc_ref)
   inside +/-1000-sample neighborhoods of the unpaired windows is 34.8 (U) /
   24.9 (W) counts, versus 4.5 / 5.5 counts everywhere else (V global 5.5).
   Outside the two mismatched-glitch neighborhoods the port tracks the
   authors' cleaned waveform at about 5 percent of the correction amplitude.

## Determinism control

PASS - EXACT. Two full chain passes from separate byte-identical fresh
extractions in fresh Octave processes (`run1/`, `run2/`) produced bitwise
identical results: dc exact, aaout3 exact (shapes (43,20)/(34,20)/(36,20)),
Data exact, max|dc1-dc2| = 0 on all channels (`logs/compare_determinism.log`,
`comparison_table.csv` determinism rows). Elapsed 147.4 s / 155.6 s.

## Positive control

`rdmseed` on the shipped sample, pristine extraction
(`logs/precheck_control.log`): 997 blocks (expect 997); npts
143076/143094/142855 @ 20.0 sps (expect exactly these; matches feasibility
card evidence item 3); fixture loads 11/11 with expected values/dimensions.
PRECHECK-PASS. Non-decisional smoke: `rdmseed(file,'plot')` (the shipped
XseedDataFDS call form) works offscreen.

## Adverse control

PASS. The comparison script re-run against the channel-permuted reference
(`dc.mat` cells rotated U->V->W; slot U <- old W, V <- old U, W <- old V)
classifies NOT-EQUIVALENT, as the card requires: R_ch = 1.002 / 0.978 / 0.999,
max|ddc| up to 5359 counts (`logs/compare_adverse.log`). The comparator
discriminates; no comparator fix round was needed.

## Interpretation and honest caveats

- Interpretation (within the card's registered outcome-neutral frame): the
  Octave route runs the authors' algorithm deterministically and reproduces
  the authors' MATLAB cleaned waveforms to about 5-9 percent of the physical
  correction amplitude, with identical multi-glitch grouping structure, but it
  is NOT numerically the authors' MATLAB run: a systematic one-2 sps-sample
  detection offset and two flipped borderline detections (one missed glitch at
  t about 66 s on U and W; one extra on U at t about 6456 s) survive to the
  output. Strict `mps_ucla_verified` attestation therefore stays reserved
  (LANDING.md decision 1); adjudication of any production use of the Octave
  lane is the lead's.
- Mechanism evidence status: the +10-sample offset and the flipped detections
  are DEMONSTRATED (localization above); their root cause (floating-point
  differences in decimate/filtfilt/inv-based LSQ between MATLAB and
  Octave/BLAS shifting discrete argmax and threshold crossings at the 2 sps
  detection stage) is PLAUSIBLE but not isolated to a specific operation.
  The feasibility card's caveat anticipated exactly this class of divergence
  (`mylsq.m` uses `inv()` on normal equations; bit-identity not expected).
- The reference `dc.mat`/`aaout3.mat` are the authors' shipped prior-run
  outputs, dimension- and provenance-consistent with the shipped sample event
  (verified 43/34/37 x 20 and 3 x 142840 on load), but the authors' exact
  MATLAB version and platform are unknown; "MATLAB reference" means "the
  archive's shipped outputs", exactly as the card defines it.
- The one tolerated deviation class: pause() stubbed and plots rendered to a
  no-output terminal. Both stages of both passes completed with stage1_ok =
  stage2_ok = 1 and NO caught errors, so no error-policy judgment call was
  ever exercised; the visual epilogues ran to completion offscreen.
- aaout3 comparison is by row count (frozen readout) and descriptive N1
  matching; element-wise fit-parameter deltas were not a registered readout
  and are not claimed.
- Determinism EXACT here means Octave-on-this-Mac determinism; it does not
  claim cross-platform Octave determinism.

## Artifacts

All under `/Users/artuskg/marsquake_runs/20260801_ucla_equiv/`, hashed in
`artifact_hashes.sha256`: this memo; `comparison_table.csv`; frozen card copy;
scripts (`ucla_equiv_driver.m`, `compare_equiv.py`, `precheck_control.m`,
`localize_posthoc.py`, `stubs/pause.m`); logs (precheck, run1/run2 drivers,
compare main/adverse/determinism, localize, pre-outcome script hashes);
results (`run1_results.mat`, `run2_results.mat`); pristine refs. Countersign
brief/output/stdout/record added after the countersign round.
