# P0-INJECT-RECOV — synthetic injection/recovery detectability (memo)

Worker: sub-Fable (bounded), 2026-08-01. Isolated dir:
`/Users/artuskg/marsquake_runs/20260801_inject_recov/`. Repo
`/Users/artuskg/GitRepos/MarsQuake` read-only throughout (HEAD 310fa81c
during execution); scientific execution exclusively with
`/Users/artuskg/micromamba/envs/mars-ic/bin/python`.

## Question (card, frozen at commit a2163d49)

At what injected amplitude does a synthetic arrival at the published PKiKP
pair (604 s, −6.5 s/deg) become the supported argmax of the real 23-event
stack — could this event set have seen the published arrival at plausible
SNR, and at what amplitude does it out-compete the displaced 662-family
ridge? Frozen outcomes: α*_argmax (smallest α whose global supported argmax
lies inside the target box 584–624 s × [−7.1, −5.9] s/deg) and α*_power
(smallest α with target-box max ≥ 0.9327, the ridge power). Ladder frozen:
α ∈ {0, 0.25, 0.5, 1, 2, 4, 8}.

## Operator correction (registered amendment)

The card's chain recap inherited `--operator principal_axis_projection` from
the ablation card — a transcription slip. Lead correction received in-thread
BEFORE the polarization stage ran here; registered amendment 1 (commit
310fa81c, dated 2026-08-01, pre-outcome, outcome-neutral, explicitly covering
P0-INJECT-RECOV) fixes the chain recap to the CANONICAL DEFAULT operator
`montalbetti_kanasewich_1970` (what `scripts/run_paper0.py` invokes with no
`--operator` flag). The frozen anchors (gate cell; 0.9327; 0.7736) are
default-operator values; the principal-axis lane's enforced table
(`history/20260801_ablpolop_prov/`) contains no such cell. No frozen
statistic, threshold, ladder value, outcome definition, or control changed.

## STEP 1 — canonical lane gate (PASSED, exact)

Chain regenerated in `lane_gate_mk/` from the 26 copied
`data/processed/*_ZNE.mseed` + `*_ZNE.rotation.json` (plus copies of
`manifest/event_table.csv`, `data/raw/mqs_v14_catalog.xml`): bandpass →
polarization (default operator montalbetti_kanasewich_1970) → fdpa →
align_and_cut → normalize_and_envelope → run_vespagrams →
`detect_peaks.py --require-current-provenance`. Log:
`lane_gate_mk_chain.log` (18:23–18:29 UTC, exit 0; 240-row table, all 240
rows `current_provenance_status=current`).

GATE ROW (paperfaith/envelope/A, nth_root, win 20.0, PKiKP global):
time 663.8 s, slowness −3.6363636363636367 s/deg, power 0.9326603162534909,
support 23 — byte-identical, field for field, to the production reference in
`results/tables/peak_comparison.csv`. The published_target row
(601.95, −6.666666666666666, 0.7736156900239739) also reproduces exactly.
This untouched lane is the α = 0 row.

- `lane_gate_mk/peak_comparison.csv`
  SHA-256 8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce
- `lane_gate_mk/vespagrams/paperfaith/envelope/A/nth_root_win20.npz`
  SHA-256 2ff8995ebc6aa103d48e906dc0f726d68d114ec958a4133cc4b4bc238fd4d175

## STEP 2 — recorded shift convention

From `scripts/03_vespagram/stacking.py`: per-trace roll =
`int(round(−slowness × (Δ_i − ref) × sr))` samples; positive roll shifts the
trace toward later times (zero-padded, no wraparound); ref = 29.0°, sr = 20 Hz.
Hence stack cell (t, s) reads trace_i at t + s × (Δ_i − 29°), and an impulse
injected at t_i = 604 + (−6.5) × (Δ_i − 29°) maps onto cell (604, −6.5).
Full note: `notes/convention.md`. Verified in execution two ways: (i) the
per-event numeric convention check (production roll formula applied to each
injected sample index recovers 604.0 within 0.051 s) passed 23/23 in every
injected lane (`alpha/a*/convention_check.json`); (ii) the α = 8 positive
control below.

## Injection implementation (tool reviewed line-by-line, then executed)

Codex `gpt-5.6-sol` at `xhigh` (banner verified) implemented
`inject_and_stack.py` + `collect_recovery.py` from the frozen brief
(`codex/brief_impl.txt`, output `codex/impl_out.md`); the sub-Fable reviewed
both files line-by-line against the repo code before execution (no P0/P1
defects; scripts SHA-256
425a20e0ed83f88abff6547eb72b58921039d16d53eb23e750bc2b41e3185040 and
c341bcdf59471de6fea00a2e0f90bde30dde16a86f75f7f15137b901bb1ee9d3).

Per α ∈ {0.25, 0.5, 1, 2, 4, 8}, per event (all 26 injected; only the 23
set=="vespagram" traces are stacked): copy the aligned paperfaith stage
products to `alpha/a{tag}/`; on float64: unit impulse at
idx = round((t_i + 100) × 20) on the aligned axis (t = idx/20 − 100, t=0 at
P); band-limited by THE CHAIN'S OWN filter call
(`Trace.filter("bandpass", freqmin=0.2, freqmax=0.8, corners=4,
zerophase=True)`, verbatim from `scripts/02_preprocess/bandpass_filter.py`);
peak-normalized and scaled so the wavelet's peak amplitude equals
α × RMS of that trace's pre-P window (−60…−10 s ∩ alignment valid mask;
1001 samples, fully valid for all events). Injected trace written back as
float32 MSEED (chain encoding). α is thereby the per-trace PRE-normalization
SNR scale (registered interpretation). Downstream: the chain's own
`normalize_and_envelope.py` (unmodified CLI) → canonical-combo stack
(paperfaith/envelope/A, nth_root n=4, win 20 s, slowness −10…0 × 100, min
support 2, ref 29°) through the repo's `compute_vespagram` → the repo's
`detect_peaks.py`. Per-event injection records: `alpha/a*/injection.json`.

Provenance statement (explicit, per card structure): injected lanes run
detect_peaks WITHOUT `--require-current-provenance`, and the stack loader
bypasses `validate_normalized_products`, BECAUSE the injection is not a
recorded chain stage — it invalidates the alignment output hash by
construction. No provenance JSON was modified or fabricated to mask that;
injected rows carry `current_provenance_status=not_required` and the
recovery table column `provenance_mode=exploratory_no_provenance_flag`.
The claim rides on the fully enforced α = 0 gate and the α = 8 positive
control, per the card.

## Controls

- (a) Adverse, α = 0: PASSED exactly — the untouched lane reproduces the
  canonical argmax cell (663.8, −3.6363636363636367, 0.9326603162534909,
  support 23) field-for-field under full provenance enforcement.
- (b) Positive, α = 8: LITERAL READING FAILED — see "Positive-control
  adjudication" below. Global supported argmax at
  (603.9 s, −6.4646464646464645 s/deg, power 7.550677911773551, support 23):
  slowness is within one grid cell of −6.5 (−6.5 lies between grid cells
  −6.5657 and −6.4646; step 10/99 ≈ 0.1010), but the time coordinate is
  0.10 s = TWO 0.05-s time cells from 604.0, so the frozen wording "within
  one grid cell of (604, −6.5)" is not literally met on the time axis.
- (c) Determinism: the α = 1 lane rerun (`alpha/a1r/`) is byte-identical to
  `alpha/a1/` in lane_summary.json (which embeds the vespagram and
  support-count array SHA-256s), injection.json, peak_comparison.csv, AND
  the raw vespagram .npz container bytes.

## Positive-control adjudication (α = 8): STOP-AND-REPORT

Status: the frozen control failed on its literal reading (time axis, by one
extra 0.05-s cell). The card's tripwire path was executed to the letter and
terminates here in STOP-AND-REPORT to the lead:

1. Mandated fix step — "fix the convention against the stacking code":
   re-verified; there is nothing to fix. The injection convention is exactly
   the production convention: for every one of the 23 stacked traces, the
   production roll formula (`stacking.py` `_roll_for`, s = −6.5) applied to
   the injected sample index recovers 604.0 within 0.051 s (two ±1-sample
   roundings), in every injected lane (`alpha/a*/convention_check.json`).
2. Mandated rerun: `alpha/a8r/` rerun is BYTE-IDENTICAL to `alpha/a8/`
   (lane_summary.json, injection.json, peak_comparison.csv, npz). The
   literal control fails again identically. Per the tripwire ("if it still
   fails after one fix, STOP-AND-REPORT"), the item returns to the lead.

Discriminating evidence that the 0.10-s miss is background peak-pulling, not
a convention error (recorded for the lead's adjudication; no method change):

- Magnitude: a genuine injection/stacking convention disagreement displaces
  the recovered peak by order |s| × spread(Δ) — with Δ − 29° spanning −1.5°
  to +10.7°, a time-sign or shift-sign error produces tens of seconds of
  displacement and/or destroys the 23-fold coherence (support/power
  collapse) or flips the recovered moveout sign entirely. Observed: 0.10 s,
  full support 23, power 7.55, correct slowness cell.
- α-dependence: the argmax time converges monotonically toward 604.0 as the
  injection increasingly dominates the real background — 602.95 (α = 0.25),
  603.30, 603.50, 603.65, 603.80, 603.90 (α = 8). A convention offset would
  be α-independent; a background-pulling bias shrinks as α grows, exactly as
  observed. The pull direction (earlier) matches the pre-existing in-box
  background maximum at 601.95 s (α = 0 published_target row).
- The wavelet itself is zero-phase; its envelope peaks at the injected
  sample. The residual offset arises in the 20-s Hann power smoothing of
  signal-plus-real-noise, not in the mapping of injected samples to stack
  cells (which the numeric check proves exact).

Consequence for the outcomes below: the recovery table and α* values are
complete, deterministic measurements of the frozen ladder, reported as
PROVISIONAL pending the lead's adjudication of the α = 8 control (e.g.,
recording the control as satisfied in intent — convention verified exact —
with the literal one-cell wording judged against the 0.05-s time grid, or
any other lead ruling). No registered element was altered by the worker.

## Recovery table (frozen outcomes)

`tables/recovery_table.csv`
SHA-256 0b7a66a46e3f2e3f588676f54235366b95a5440d689d69dcff3f9a53719cd517
(also `tables/recovery_summary.json`,
49d1c8965268af6d078c82b1ba270d49d69af47540d4eb9b8c5b27d6f943112a).

| α | argmax t (s) | argmax s (s/deg) | argmax power | support | in box | target-box max |
|------|--------|------------|---------|----|-------|-----------|
| 0 | 663.8 | −3.636364 | 0.932660 | 23 | no | 0.773616 |
| 0.25 | 602.95 | −6.464646 | 1.248349 | 23 | yes | 1.248349 |
| 0.5 | 603.3 | −6.464646 | 1.620356 | 23 | yes | 1.620356 |
| 1 | 603.5 | −6.464646 | 2.177235 | 23 | yes | 2.177235 |
| 2 | 603.65 | −6.464646 | 3.059102 | 23 | yes | 3.059102 |
| 4 | 603.8 | −6.464646 | 4.632479 | 23 | yes | 4.632479 |
| 8 | 603.9 | −6.464646 | 7.550678 | 23 | yes | 7.550678 |

(Full precision in the CSV. At every injected α the global argmax lies
inside the target box, so the target-box max equals the global max.)

**α*_argmax = 0.25.  α*_power = 0.25** (identical under the literal frozen
threshold 0.9327 and under the full-precision ridge power
0.9326603162534909; recorded separately in `recovery_summary.json`).
PROVISIONAL per the positive-control adjudication section above.

## Interpretation (registered scale; no overreach)

Under the registered interpretation — α is a pre-normalization per-trace SNR
scale (injected peak amplitude = α × that trace's pre-P RMS on the aligned,
band-passed, polarization-filtered trace) — the smallest tested rung of the
frozen ladder already recovers the injection: a moveout-coherent arrival at
the published pair with per-trace amplitude only 0.25 × pre-P noise RMS
becomes the global supported argmax of the real 23-event stack (power 1.248
vs the displaced 662-family ridge at 0.933) and exceeds the ridge-power
threshold inside the target box. The ladder is floor-limited: 0.25 is the
smallest nonzero α registered, so the true flip point lies somewhere in
(0, 0.25]; the frozen outcome is reported over the frozen ladder only.

What this says about detectability: the stacking machinery, on this exact
event set and noise field, is highly sensitive to a PERFECTLY
moveout-coherent published-pair arrival — coherent gain over 23 envelopes is
strong enough that even a quarter-of-noise-RMS arrival out-competes the
662-family ridge. The observed non-detection at α = 0 (target-box max
0.7736 < ridge 0.9327) is therefore NOT explained by the machinery being
too insensitive to see a published-pair-like arrival of plausible amplitude,
PROVIDED the real arrival were as moveout-coherent as the synthetic one.

Residual uncertainty / limits (honest bounds):
1. The injection is ideally coherent: exact −6.5 s/deg moveout at exact
   catalog distances, identical wavelet, exact P-alignment. Real arrivals
   carry pick errors, distance errors (median σ_Δ = 3.5°), and waveform
   variability, all of which dilute coherent gain; α* from this design is
   therefore a LOWER bound on the amplitude a real arrival would need. The
   card's companion null (P0-MARS-SCRAMBLE) calibrates the opposite side
   (incoherent false-alarm behavior); neither replaces propagation physics.
2. Single injection site and wavelet by design (no wavelet-family or
   per-event tuning; card stop condition).
3. α rides on the pre-P RMS of the processed (filtered, polarization-
   weighted) trace, not raw ground motion; it is a machine-level SNR scale,
   which is exactly what the card registered.
4. Injected lanes are exploratory (provenance-unenforced by necessity, as
   registered above); the enforced α = 0 gate and byte-identical determinism
   rerun bound the mechanical risk.

## Stop condition

Terminated via the tripwire's STOP-AND-REPORT branch: seven α values only,
no wavelet-family exploration, no per-event tuning, no method changes. The
measurements and controls (α = 0 exact; determinism byte-identical;
convention 23/23 exact; α = 8 literal-wording miss by one time cell,
adjudication package above) return to the lead with the reviewer's finding.
