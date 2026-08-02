# A registered public-data reproducibility benchmark for the reported PKiKP detection of a Martian inner core

**Draft for Seismica (v0.6, 2026-08-02; independently reviewed for
artifact accuracy — full v0.2 review plus bounded reviews of each dated
fold. v0.4 added the § 5.6 relation to the independently posted Visser
et al. (2026) re-analysis; v0.5 added the § 5.4 same-data calibration
fold, the § 5.6 cross-selection execution, the dated § 3.1
UCLA-feasibility update, the § 5.4 Earth known-truth control completion
(deviation-flagged), and the pinned Fig. 5/Table 3 — all dated
additions since v0.3 countersigned 2026-08-02
(`history/20260802_v05_review/`). v0.6 folds the UCLA production
same-cell comparison from the countersigned production card
(`history/20260802_ucla_prod/`) into §§ 3.1, 5.5, and 6; the fold's
bounded accuracy review found one P1 wording overclaim, repaired in the
single registered fix round with the reviewer's bounded formulation,
plus two mechanical P2s (both applied). Not yet submitted; journal
packaging in progress.**

Author: Artus Krohn-Grimberghe (Percivio Ltd.) — corresponding author,
artus@percivio.com. ORCID: to be added at submission.

---

## Abstract

Bi et al. (2025) report a 600-km solid inner core in Mars, based partly on
a PKiKP vespagram peak at 604 ± 2 s after P and −6.5 ± 0.6 s/deg from
stacked InSight marsquakes. We present a registered public-data
reimplementation; success criteria, windows, and statistical rules were
frozen before outcome inspection, and the headline lane uses only the
public MPS deglitch stage. We recover a supported local maximum inside the
published target box (601.95 s, −6.67 s/deg), but it never wins: the
registered argmax is a displaced ridge (663.8 s, −3.64 s/deg) at 1.21× the
target-box power, and six single-event removals each hand the 23-event
stack's argmax to a time-adjacent shallow-slowness branch.
Composition–outcome association gives p = 0.0039 and 1.0 × 10⁻⁴ in two
same-data designs. Distance-scrambled stacks reach
ridge-level peak power in 75.5% of realizations (target-box level: 48.0%);
an ideally coherent arrival injected at the published coordinates wins at
0.25× pre-P noise RMS. The authors' second deglitch method, run on raw
data over the executable 19-event sub-stack, preserves the qualitative
disagreement and target-box subordination (box maximum cell-identical)
while the global-argmax coordinate is deglitch-sensitive. This is
reproducible non-agreement plus internal fragility, not a refutation; all
artifacts are released hash-pinned.

## Non-technical summary

A recent high-profile study reported that Mars has a solid inner core, partly
based on a faint seismic echo (PKiKP) found by stacking many marsquakes
recorded by NASA's InSight lander. We rebuilt that analysis from scratch using
only public data and code, and we wrote down all of our decision rules before
looking at the results. Our reconstruction does find a secondary feature at
the reported location — but the strongest feature in the search window is an
unexplained one about a minute later, and whether that later feature stays on
top depends on single marsquakes: remove any one of six specific quakes from
the stack of 23 and the top spot shifts to a feature near the reported
arrival time (though not with the reported apparent-velocity signature).
This does not disprove the inner-core detection, because the original team
used some in-house processing steps we cannot exactly reproduce. It does show
that the public-data version of the measurement is not yet robust, and it
provides an openly verifiable benchmark that the community — including the
original authors — can run and extend.

## 1. Introduction

The detection of core-transiting seismic phases from single-station planetary
data is among the hardest measurements in seismology. Bi et al. (2025)
report PKiKP and PKKP arrivals in stacked InSight data and infer a solid
inner core of ~600 km radius for Mars. The claim rests on vespagram peaks
recovered from low signal-to-noise stacks of order-20 events recorded by a
single station, after event-specific deglitching, polarization filtering,
alignment on direct-P picks, and slant stacking.

Results of this kind are, by construction, difficult for the community to
check: the waveform data are public, but the processing pipeline is a
sequence of outcome-sensitive choices (event selection, deglitching,
polarization operator, normalization, alignment, stacking exponent, peak
selection) whose interaction determines whether a marginal feature appears.
Reproducibility work in this regime faces a specific epistemic trap:
reimplementers have many degrees of freedom too, so an uncontrolled
"failed to reproduce" is as weak as an uncontrolled detection.

We therefore built the reimplementation as a registered benchmark. All
outcome-sensitive analytical choices — event set, windows, target boxes,
tolerance rules, stacking parameters, bootstrap designs, statistical
thresholds, and peak-selection rules — were frozen in a versioned
specification before the affected outcomes were inspected, with deviations
recorded on a registered amendment log stating why each change is not fitted
to results. The pipeline is provenance-gated end to end: every input is
checksum-pinned, every derived product embeds the hash chain of its inputs,
and every claim-bearing stage fails closed on missing or stale provenance
rather than silently substituting data. Positive and adverse controls
accompany each claim-bearing step.

This paper reports what that benchmark finds: a reproducibly displaced
argmax, a subordinate but supported local maximum inside the published-pair
target box, and — the central result — a quantified single-event fragility
of the displaced ridge's rank-1 status. We state at the outset what this is
not: our
pipeline is not the authors' pipeline, and agreement with the published
coordinates was never a success criterion. A reproducible disagreement,
honestly bounded, is the deliverable.

## 2. Data

All inputs are public and checksum-manifested (2,693 path+digest entries;
the manifest is machine-verified at every run):

- **Waveforms.** InSight SEIS VBB (Lognonné et al., 2019) 20 sps
  BHU/BHV/BHW MiniSEED for 26 catalogued marsquakes (PDS
  `urn:nasa:pds:insight_seis` v3.0 via IRIS), cut around each event.
- **Catalog and picks.** MQS V14 event catalog (DOI 10.12686/a21): preferred
  origins, event metadata, and direct-P picks used for alignment.
- **Reference models.** The public AK model subset (DOI
  10.18715/IPGP.2021.kpmqrnz8; Stähler et al., 2021) and the Khan et al.
  (2023) model ensemble (DOI 10.18715/IPGP.2023.llxn7e6d), used for TauP
  (Crotwell et al., 1999) travel-time context and provenance-tracked model
  comparisons.
- **Published pick tables.** The Bi et al. (2025) supplementary tables,
  archived with per-file SHA-256 and converted to CSV for the comparison
  surfaces.

The PKiKP stack uses the 23 events assigned `set=vespagram` by the registered
event-set split; the other three (S1102a, S1153a, S1415a, at 73–88°
distance) are registered `set=validation` events, processed through alignment
and normalization but reserved from the stack. Stack support at the reported
features is 23/23.

## 3. Methods

### 3.1 Pipeline

The chain is: deglitching → UVW→ZNE rotation → polarization filtering →
alignment and cutting on MQS direct-P picks (common grid [−100, 2200) s
relative to P) → normalization → vespagram slant stacking → registered peak
detection and comparison → bootstrap resampling → validation. The chain is
implemented in Python on ObsPy (Beyreuther et al., 2010).

- **Deglitching** uses the public MPS/SEISglitch method (Scholz et al.,
  2020; pinned to an exact
  upstream commit, run in a pinned legacy environment for bit-stable
  behavior). For the UCLA half of the published two-method scheme, a public
  MATLAB archive exists (`UCLA_v4`); at the time the benchmark ran, no
  maintained executable route was available to this pipeline, so the UCLA
  stage was not reproducibly executed. The pipeline records the honest
  attestation `succeeded_mps_only` (26/26 events), records the strict
  two-method attestation `mps_ucla_verified` as failed, accepts the partial
  lane by design, and treats this as a first-class, visible limitation
  rather than an approximation to hide. A registered feasibility card
  (2026-08-01, dated addition) subsequently established that the archive is
  executable without MATLAB: it runs under GNU Octave with a two-line shim
  on a single used-path incompatibility, reproducing the package's own
  shipped reference fixtures to machine precision. A registered single-event
  equivalence card then compared the Octave route against the authors'
  shipped MATLAB reference on S0235b under a rule frozen before the run and
  classified the outcome DIVERGENT-MINOR: per-channel glitch counts 43/43,
  34/34, and 36/37, port-noise ratios 0.04–0.09 (all within the 0.1 bound),
  the divergence localized to one glitch whose selection flips between
  platforms plus a one-sample fit-window offset — the published package's
  glitch selection is not platform-stable at the margin. The strict
  `mps_ucla_verified` attestation remains deliberately reserved, and every
  headline result in this paper is MPS-only. A registered production card
  (2026-08-02, dated addition) subsequently executed the UCLA stage
  end-to-end: the archive's shipped code crashes on four of the 26 events
  (empty-glitch-list indexing on two, a zero subscript at a detection
  edge, and a too-short segment fed to filtering), so a 22-event
  executable partition (19 stack + 3 validation events) was frozen a
  priori and the full benchmark chain was run twice over it — once with
  `UCLA_v4` deglitching the raw input directly (an explicit identity
  pre-stage records the terminal status `ucla_unverified`; no MPS
  processing is claimed) and once with the MPS lane restricted to the same
  partition, so the deglitch method is the single factor differing between
  lanes. Byte-identity controls anchored both lanes — the production UCLA
  product for S0235b equals the single-event census product, and the
  subset MPS product equals the accepted canonical product — and an
  adverse control confirmed that the excluded events are rejected
  mechanically by the lane's allow-list rather than discretionarily. The
  comparison itself is reported in § 5.5.
- **Polarization filtering** uses a public Montalbetti–Kanasewich-style
  principal-axis/DOP projection (after Montalbetti & Kanasewich, 1970;
  labeled as a public approximation; the
  authors' exact operator is not released), with a labeled
  principal-axis-projection ablation as an alternative operator.
- **Vespagrams** are fourth-root slant stacks (Muirhead & Datt, 1976) on
  envelope input at reference
  distance 29.0°, slowness −10…0 s/deg (100 steps), 20 s power window,
  minimum stack support 2. The registered primary lane is
  `paperfaith/envelope/A/montalbetti_kanasewich_1970/nth_root/20.0 s`.
- **Peak comparison** uses frozen target boxes from the published values:
  PKiKP 584–624 s × [−7.1, −5.9] s/deg (published 604 ± 2 s,
  −6.5 ± 0.6 s/deg); PKKP 1320–1360 s × [−8, −6] s/deg. Distance
  uncertainty is folded into the tolerance audit (a 2° distance uncertainty
  at ~7 s/deg is ~14 s of moveout, not a ±2 s coordinate tolerance).
- **Bootstrap.** Type I (event resampling), Type II (distance-stratified),
  and Type III (±10 s P-pick jitter) designs, N = 200, labeled
  `methods_robustness_200`: these quantify the robustness of our methods,
  and are not claimed to be equivalent to the published bootstrap.

### 3.2 Registration and governance

Seven success criteria were frozen in the specification, none of which
require agreement with the published coordinates. Outcome-sensitive rules
live on a dated, append-only amendment log; each amendment states why it is
not outcome-fitted. Peak-selection for the leave-one-out analysis (§ 4.3)
was frozen — including its branch boundary at 632.0 s — before execution,
and when its positive control initially failed (the card's literal
"full-grid" argmax rule found a grid-edge artifact), the repair was made by
a registered pre-execution amendment adopting the production
window-and-support rule, not by silently patching code. Every claim-bearing
run carries a positive control (known-true reproduction) and an adverse
control (deliberate corruption must fail closed); adverse failures stop the
pipeline rather than degrade it. Supplementary Table S1 compacts the
recorded outcomes of these controls for every claim-bearing surface,
including four documented control weaknesses and their registered
dispositions.
The full benchmark was subjected to three independent model-assisted
completion reviews; all confirmed the § A.4 criteria with zero P0
(invalidating) findings, with earlier-round P1 findings repaired and
re-reviewed.

### 3.3 What is deliberately not claimed

Phase identity is never asserted for any feature; travel-time consistency
with computed branches is reported as interpretive context only. Bootstrap
outputs are methods-robustness statistics. The composition-association test
(§ 4.3) is a same-data calibration, not an independent replication.

## 4. Results

### 4.1 The benchmark reproduces a displaced argmax

A fresh, fully provenance-enforced end-to-end run (every configured stage
succeeded, validation passed; all 26 events deglitched `succeeded_mps_only`,
with the strict `mps_ucla_verified` attestation failed and the MPS-only lane
accepted by design) yields, in the registered primary lane: a supported
PKiKP-window argmax (inclusive 550–700 s window, full −10…0 s/deg slowness
grid, minimum support 2) at **663.80 s, −3.64 s/deg** (support 23/23) versus
the published **604 s, −6.5 s/deg** — a displacement of **+59.8 s** in time
and ≈ +2.9 s/deg in slowness (Fig. 1; Table 1). The displacement is
reproducible to the byte: the peak-comparison table from the fresh run is
SHA-256-identical to the table produced three weeks earlier on a different
environment build, across an inventory change (`8df5f5c8…`). The displaced
ridge is configuration-stable under one argmax implementation: at the
registered 20-s power window the envelope-variant maxima are 663.80 (A),
664.10 (B), and 664.85 s (C), and the separate 1-s power-window sweep places
the analogous ridge at 662.05–662.80 s across variants A–C — neighboring
cells on the same broad ridge, with the spread a power-window and
normalization sensitivity, not a second independent reader.

Inside the published-pair target box, the pipeline finds a supported,
support-complete local maximum at **601.95 s, −6.67 s/deg** — within the
uncertainty-folded tolerance of the published pair (though outside the raw
±2 s / ±0.6 s/deg box). A supported local maximum is therefore present
inside the target box in the public reconstruction; it is just never the
argmax.

### 4.2 How subordinate is the target-box feature?

Under the registered significance reading (rules frozen before inspection):
the target-box maximum ranks **6,938th** among supported grid cells in the
lane, sits at background quantile **0.714**, and carries stack power 0.774
against the displaced ridge's 0.933 — a power ratio of **1.21** in the
ridge's favor (Table 1). The PKKP-side mirror statistic behaves analogously:
a supported within-tolerance local maximum at 1341.0 s, −6.97 s/deg at rank
13,395 (background quantile 0.393), with the PKKP-window argmax elsewhere
(~1236 s, −6.1 s/deg).

We stress the reading discipline: (601.95 s, −6.67 s/deg) is the *maximum
inside the published-pair target box*, not "the published PKiKP pair"; the
published coordinates themselves are a box, not a cell.

Both statistics are calibrated by a registered same-data null (§ 5.4):
under randomly sampled distance assignments that destroy moveout
coherence, 75.5% of scrambled realizations of the same stack reach the
displaced ridge's power and 48.0% reach the target-box maximum's.

### 4.3 The ridge's rank-1 status is six-events fragile

The central result. Three distinct features must be kept apart here:
(i) the *target-box maximum* at 601.95 s, −6.67 s/deg; (ii) a *shallow
602-family branch* — time-adjacent to the published time but at shallow
slowness; and (iii) the *displaced 662-family ridge* at 663.8 s, −3.64 s/deg.

Under the pre-registered leave-one-out design (branch boundary 632.0 s
frozen in advance; deterministic 22-event restacks through the production
loader and peak rule; byte-identical repeat control), removing any single
one of **six** events — S0325a, S0474a, S0864a, S1012d, S1022a, S1039b —
flips the supported PKiKP-window argmax from the displaced ridge to the
shallow 602-family branch: the flips land at 602.0–606.4 s but at
−3.43…0.0 s/deg, *outside* the target-box slowness range [−7.1, −5.9]
(Fig. 2; Table 2). The target-box maximum itself never becomes the argmax
in any removal. The flips are not marginal: the argmax jumps 57.5–61.9 s.
The other seventeen removals move the argmax by at most **0.95 s**. There
is no intermediate case.

The displaced ridge is therefore the argmax only when all six of these
events are present simultaneously — a conjunction of six single-event
dependencies in a 23-event stack. What the sweep establishes is fragility
of the *ridge's rank-1 status* against a time-adjacent shallow-slowness
competitor; it does not show the target-box maximum winning under any
removal. Four of the six flip events (S0474a, S1012d, S1022a, S1039b) are
exactly the flip-set events flagged by the family-wise-error-controlled
composition test below; two (S0325a, S0864a) were not flagged by the
registered resampling diagnostics and were found only by the sweep.

Complementary composition evidence, all registered before reading:

- **Composition association.** Under label-permutation nulls that provably
  sever the association, the 602-vs-662 branch outcome is materially
  associated with event-set composition in both bootstrap designs (Type I
  max-T p = 0.0039; Type II p = 1.0 × 10⁻⁴). By design, the FWE-significant
  events are: Type I — S1039b and S1022a (inclusion favors the 662 branch);
  Type II — additionally S0474a and S1012d positive, and S0820a and S0484b
  negative (inclusion favors the early branch); see Table 2. Registered
  honesty clauses: this is a same-data calibration, and — because mean
  selected distance is a deterministic function of event composition within
  the fixed event table — distance and composition effects are not
  separately identifiable from these products.
- **Occupancy bimodality.** Type I bootstrap occupancy for PKiKP is bimodal:
  602–603 s regions dominate at the 50% and 70% thresholds while the 664 s
  region dominates at 85% — both occupancy families occur under the
  registered conditional resampling (Fig. 3).
- **Design insensitivity.** The 662-branch fraction is statistically
  indistinguishable between bootstrap designs (Type I 0.635, 95% CI
  [0.566, 0.699]; Type II 0.550, [0.481, 0.617]) — the fragility is not an
  artifact of resampling design (Fig. 3).
- **PKKP contrast.** The instability is feature-specific, not
  pipeline-generic: on the PKKP side the registered occupancy-cell argmax
  is stable-early under both bootstrap designs — Type I and Type II agree
  at all three occupancy thresholds (largest |Δt| = 1.65 s, largest
  |Δs| = 0.20 s/deg, well inside the frozen |Δt| ≤ 5 s, |Δs| ≤ 0.5 s/deg
  concordance rule), with every reading nearest the early ~1236 s,
  −6.1 s/deg feature and no PKiKP-style branch competition between
  thresholds or designs.

### 4.4 What does *not* explain the displacement

- **Alignment error.** The registered ±10 s P-pick jitter audit (with a
  demonstrated-power 60 s exploratory lane) shows material occupancy-region
  sensitivity (PKiKP centroid displacement 5.05 s, broadening 31×), but
  ±10 s explains at most ~5 s — and even 60 s of jitter at most ~28 s — of
  the +59.8 s displacement (Fig. 4b). Alignment jitter of plausible
  magnitude cannot move the target-box feature onto the ridge.
- **Polarization operator.** Swapping the M-K-style operator for the labeled
  principal-axis ablation leaves the target-box maximum non-global under
  both operators; the subordinate within-tolerance local maximum at the
  target-box coordinates is operator-robust. The *identity* of the
  envelope-A winner, however, is operator-sensitive: at the registered 20-s
  window the principal-axis winner is a shallow-slowness time-adjacent
  feature at 603.25 s, −3.54 s/deg (601.90 s, −3.54 s/deg in the 1-s
  power-window sweep) — note: not the target-box maximum, whose slowness is
  −6.67. The operator swap thus removes most of the *time* displacement in
  envelope A while leaving the slowness mismatch and the target-box
  subordination in place; the 662 s ridge survives the swap in envelope
  variants B and C (Fig. 4a).
- **Kinematics.** At the registered geometry (29.0°, 33 km depth), the
  published pair and the target box are kinematically consistent with the
  reference-model PKiKP family (model slowness ≈ −6.36 s/deg). Zero branches
  in the registered reference-model query are consistent with either
  competing feature (the registered 1-s comparison points F2 = 662.05 s,
  −3.43 s/deg and F1 = 601.9 s, −3.54 s/deg). On the PKKP side, zero
  branches in the query match the observed features or the first published
  reference; the second published reference (1341.0 s, −7.0 s/deg) is
  consistent with PKIKKIKP. The registered query, in other words, finds
  kinematically consistent branches at the published coordinates and none
  at the features that outcompete them — an asymmetry of model consistency,
  not a prediction of detectability.

### 4.5 Chain integrity

The result set is guarded end to end: a repository-resident identity
verifier binds every evidence locator to its digest (a transplanted digest
fails closed); vespagram payloads verify lane identity against path identity
before any merge; the model stage re-queries the generated travel-time model
and requires registered P/PKiKP times within 0.01 s; and every
non-from-scratch run begins with a verify-only audit of all 2,693 manifest
entries (the three source ZIP archives are digest-pinned nonresident by a
registered amendment, with byte-verified custody copies in object storage).
Adverse controls for each guard are demonstrated in the test suite
(criterion-scoped run: 1,271 passed / 1 skipped / 0 failed).

## 5. Discussion

### 5.1 The deflationary reading, taken seriously

A referee should hold, and we hold, the deflationary reading: our pipeline
is not the authors' pipeline. The deglitch lane is MPS-only where the
original applied a second, in-house UCLA-lineage step; the polarization
operator is a public reconstruction; the alignment and normalization are
ours; the bootstrap is a methods-robustness instrument. "The public
reconstruction disagrees" could in principle mean "the public approximation
is insufficient," not "the claim is fragile." Two findings survive that
reading, because they are internal to our own pipeline:

1. **The invariant.** Across both polarization operators, all envelope
   variants, and a byte-stable rerun across environments, the target-box
   maximum is never the argmax. The operators disagree about what wins; they
   agree about what loses.
2. **The conjunction.** Even granting every approximation, within this one
   fixed pipeline the displaced ridge's rank-1 status trades against a
   time-adjacent shallow-slowness branch on the removal of any one of six
   specific events. A winning feature whose rank-1 status depends
   conjunctively on six of 23 events — two of them not flagged by the
   registered resampling diagnostics — is fragile in a sense that no
   fidelity argument about *our* approximations removes, because the
   fragility is measured within a single consistent analysis.

### 5.2 Model-conditioned peak selection

The kinematic asymmetry of § 4.4 suggests the generalizable methodological
point: in low-SNR single-station stacks, peak selection conditioned on a
model prediction will find a peak where the model says to look — the
target-box feature is a supported local maximum within folded tolerance —
while a stronger unexplained feature can sit nearby, invisible to a search
that never leaves the box. Vespagram detections of this kind should routinely
report (i) the global-versus-box rank and power ratio of the candidate, and
(ii) a single-event leave-one-out sweep of the global argmax. Both are
nearly free to compute and either would have surfaced the fragility
reported here. An independent re-analysis has since instantiated the same
structural concern in model space, by scanning the conditioning model
itself (§ 5.6).

### 5.3 Calibration on independently constrained ground: the lunar-analog blind test

The methodological concern of § 5.2 is not hypothetical: the identical
machinery has been calibrated once, blind, on a body whose deep interior is
independently constrained — not gospel ground truth (the lunar estimates
are themselves stacking-derived, a caveat its pre-registration records),
but independent of the machinery under test. In a companion experiment (2026-07-06) we ported
the source-array vespagram pipeline 1:1 to Apollo lunar long-period data —
six of the seven modules byte-identical to the audited Mars implementation
used here, the seventh differing in import mechanics only — and asked,
under criteria frozen before any waveform contact (pre-registration SHA-256
`ab5f8034…`), whether it recovers the lunar core, whose radius carries
independent estimates near 330–380 km (Weber et al., 2011; Garcia et al.,
2011). The data were 228 quality-passing event-windowed traces from Apollo
stations 12/14/15/16 (network XA), with events and per-station P arrivals
taken from the Nakamura catalogue and the Nunn et al. (2020)
compiled-arrival supplement; declared adaptations were confined to the data
reality (principally long-period vertical only, no polarization filter,
Lanczos resampling to 20 Hz, and a lunar −100…+1200 s cut window; the full
declared list is in the archived report and pre-registration).

The pre-registration froze two detection grades so that the test could be
rigged in neither direction. G1 ("paper-grade": |ΔT| ≤ 25 s, |Δp| ≤ 1.2
s/deg, σ_T ≤ 10 s, σ_p ≤ 1.0 s/deg, occupancy ≥ 0.50, Type-III
concordance) mirrors the precision the published Mars analysis reports;
G2 ("replication-grade": |ΔT| ≤ 50 s, |Δp| ≤ 2.0 s/deg, σ_T ≤ 50 s,
σ_p ≤ 1.5 s/deg, occupancy ≥ 0.45) mirrors what our own Mars rerun
actually achieves at the 85%
occupancy threshold (σ_T = 43.0 s PKiKP, 49.3 s PKKP;
`results/tables/bootstrap_picks.csv`). Held only to G1, the lunar test
would fail a standard the Mars reproduction itself does not meet; held only
to G2, it would pass trivially.

The pre-registered verdict was METHOD-FRAGILE at both grades. At G1 the
method detected nothing on the real Moon (0 of 3 primary deep-moonquake
configurations) while phase-randomized noise still "detected" a lunar core
in 15% of realizations and station-swapped geometry in 33% — synthetic
noise outperformed the actual Moon at the claimed precision. At G2 the
method detected core reflections everywhere: real data 3/3, and
distance-scrambled data 75/75, phase-randomized noise 72/75,
station-swapped geometry 6/6, and 16 of 24 arbitrary decoy windows. The
implied core radii of the surviving detections scatter from 100 to 470 km
and disagree between stations far beyond the pre-registered consistency
tolerance.

For the present benchmark this calibration closes a loop the Mars data
cannot close by themselves. At replication-grade tightness, box-localized
occupancy peaks arise unconditionally — in scrambled data and pure noise,
at false-alarm rates near one — so whatever evidential weight such peaks
carry must come entirely from the tightness of the reported uncertainties.
That tightness is precisely the property the public reconstruction does not
reproduce: the G2 grade above is anchored to our own rerun's σ_T. Cheap
matched nulls — event-scramble and decoy windows — are the natural
extension of the § 5.2 recommendations, and on the Moon they were the
entire difference between an apparent detection and a demonstrable false
alarm. Their Mars-side counterparts are reported in § 5.4.

The calibration has its own limits, recorded in its archived report. Apollo
long-period data are a harder stacking target than InSight VBB data
(intense scattering coda, 10-bit resolution, peaked instrument response),
and the primary trace counts (11–16) sit below the Mars set's 23. Fragility
on the Moon therefore does not prove the Mars detections false; what it
demonstrates is that the method's internal consistency checks — bootstrap
occupancy, multi-configuration presence — cannot by themselves distinguish
true from false arrivals at these noise conditions and trace counts, and
that null behavior must be characterized per dataset. One geometric caveat
cuts in the method's favor: deep-moonquake sources compress the
core-reflection slowness discriminant to ≈ −1 s/deg, intrinsically harder
than the Mars PKiKP geometry (≈ −6.5 s/deg) — though surface-source impact
configurations (≈ −3.4 s/deg) showed the same detect-everything pattern at
G2.

The citable record is the archived report, the frozen pre-registration with
its dated amendments, and the criteria/target/radius code, all in
repository custody; the bulk run products of the 2026-07-06 campaign were
not retained, and neither were the port's retrieval, preprocessing, and
stacking runners. The protocol is therefore reconstructable in principle
from the pre-registration and public Apollo data, but the exact experiment
is not regenerable from retained custody alone. It predates this paper's
registration regime and is cited as a dated companion experiment, not
folded into this paper's provenance-enforced chain.

### 5.4 Same-data calibration of the detection machinery

The lunar calibration closed with an obligation rather than a conclusion:
null behavior must be characterized per dataset (§ 5.3), and the dataset
that matters here is the Mars stack itself. We therefore ran the § 5.2
recommendations on the benchmark's own data as three registered
calibration cards — an event-scramble null (the Mars-side counterpart of
the lunar N1 null), a synthetic injection ladder, and a decoy-box family
statistic — each with statistics, thresholds, seeds, ladders, controls,
and stop conditions frozen in a registered card text before that card
executed, with dated, outcome-neutral amendments, and with memos,
adjudications, control outcomes, and per-artifact hashes in repository
custody. All three are same-data calibrations in the § 3.3 sense: they
measure how the frozen detection criteria behave on this event set and
noise field — when moveout coherence is destroyed, when a known coherent
arrival is added, and when the target box is displaced across the
surface. None re-measures propagation physics; none can prove the
published detection true or false.

**Event-scramble null.** The null permutes the 23 catalogued epicentral
distances across the stacked events (N = 200 seeded permutations; the
identity assignment is excluded and carried separately), leaving traces,
alignment masks, and envelopes untouched: moveout coherence is destroyed
while the envelope population the stack integrates is preserved. The
realization stack is the production stack — the runner imports the
repository stacking and peak-detection code, and the identity permutation
reproduces the canonical argmax and target-box cells with exact float
equality, on stack grids array-identical to the canonical chain's. The
regenerated canonical lane is line-identical to the production peak table
(SHA-256 `8df5f5c8…`), an effect control confirms that permuted distances
change the stack grid massively, and a repeated realization is
byte-identical (Table S1e). All 200 realizations completed with no errors
and no NaN statistics.

Against the frozen thresholds — 0.9327, the canonical ridge power, and
0.7736, the real target-box maximum — the null is not rare but modal:
**151 of 200** scrambled realizations produce a supported PKiKP-window
argmax at or above the ridge power — a false-alarm rate of 0.755
(exceedance p = 152/201 = 0.756) — and **96 of 200** produce a target-box
maximum at or above the real one (false-alarm rate 0.480; p = 97/201 =
0.483). The real ridge sits near the 24th percentile of its own scramble
null — the null median, 0.979, exceeds it — and the real target-box
maximum sits at the null median (0.767). (The fourth-root stack's power
normalization permits null powers above unity — null maxima 1.333 and
1.076 — and thresholds were applied exactly as frozen, with no
rescaling.)

Under the frozen criteria, then, ridge-quality and target-box-quality
peaks are the ordinary product of fourth-root stacking of these 23
normalized envelopes under randomly sampled distance assignments from the
registered permutation null: on this data set, the peak-power and
box-occupancy machinery has no discriminating power against
moveout-incoherent alternatives. The registered honesty clause bounds the
reading. This is a same-data calibration: the null destroys moveout
coherence while keeping the envelopes, so it calibrates the machinery's
false-alarm behavior on this noise field, not event-set propagation
physics; it is conditional on the observed distance multiset; and event
selection, alignment jitter, and renormalization are covered by the
separate registered bootstrap lanes (§ 3.1). It proves no detection
false; it calibrates the detection criteria themselves. With it, the
matched null the lunar experiment showed to be decisive (§ 5.3, N1 firing
75/75 at replication grade) exists for the Mars data: the displaced
663.8-s ridge and the target-box maximum are both statistically
unremarkable against the scramble null (Fig. 5) — the false-alarm-side
complement of the leave-one-out fragility of § 4.3.

**Injection ladder.** The scramble null calibrates false alarms; the
injection ladder calibrates sensitivity — could this stack have seen a
published-coordinate arrival, and at what amplitude does one out-compete
the displaced ridge? Into each event's aligned, band-passed,
polarization-filtered trace we injected a synthetic arrival at the
published pair — an impulse at t_i = 604 + (−6.5)(Δ_i − 29°),
band-limited by the chain's own 0.2–0.8 Hz zero-phase filter call — with
peak amplitude α times that trace's pre-P (−60 to −10 s) noise RMS; α is
a per-trace, pre-normalization SNR scale on the processed traces, and the
registered ladder is α ∈ {0, 0.25, 0.5, 1, 2, 4, 8}. Everything
downstream is the chain's own machinery (normalization, envelope,
stacking, peak detection). The α = 0 lane reproduces the canonical cell
field-for-field under full provenance enforcement; the injection
convention is proven rather than assumed — the production shift formula
recovers the injected time as 604.0 ± 0.051 s for 23/23 stacked traces in
every lane — and repeated lanes are byte-identical. The injected lanes
are exploratory by necessity (an injection invalidates the
alignment-stage provenance hash by construction, and is recorded as such
rather than masked); the mechanical claim rides on the enforced α = 0
gate and the determinism controls (Table S1e).

The measured flip is floor-limited (Table 3): **α\* = 0.25**, the smallest
registered nonzero rung, under both frozen outcome definitions
(argmax-in-box, and target-box power at or above the ridge's 0.9327). At
α = 0.25 the global supported argmax moves from the displaced ridge into
the published target box, at (602.95 s, −6.46 s/deg) with power 1.248
against the ridge's 0.933, and it stays in the box at every larger rung.
The true flip point therefore lies somewhere in (0, 0.25] and is not
further resolved: no smaller rungs were registered, and none were added
after the outcome was seen. Per the card's outcome-neutral framing, two
readings follow. As sensitivity: the chain detects a coherent arrival at
the published coordinates at ≤ 0.25× pre-P RMS amplitude, so the
non-detection at α = 0 is not explained by the machinery being too
insensitive — provided a real arrival were as moveout-coherent as the
synthetic one. As margin: the observed ridge's global dominance over the
published-coordinate family is worth less than 0.25× pre-P RMS of
coherent energy at the published coordinates — the amplitude-domain
expression of the same fragility that § 4.3 measured in composition.

One frozen control of this card failed, and is disclosed rather than
repaired. The α = 8 positive control required the recovered argmax to
land within one grid cell of (604, −6.5); the observed argmax, (603.90 s,
−6.46 s/deg), is within one slowness cell but 0.10 s — two 0.05-s time
cells — early. The registered tripwire ran to the letter: the convention
was re-verified exact, the rerun was byte-identical and failed
identically, and the run stopped and reported rather than coding around
the wording. Adjudication recorded the failure as a control-tolerance
design flaw, not a convention or pipeline defect. The discriminating
evidence: the argmax time converges monotonically toward 604.0 as α
grows — 602.95, 603.30, 603.50, 603.65, 603.80, 603.90 s across the
ladder — approaching from the direction of the pre-existing in-box
background maximum at 601.95 s, exactly the signature of additive
background peak-pulling under envelope smoothing at finite α; a genuine
convention error would displace the peak by tens of seconds, flip the
recovered moveout sign, or collapse the 23-fold support, and would not
converge. The α = 8 lane is therefore not quoted here as a passed literal
control; the convention claim rests on the numeric shift-recovery check
above.

The design bounds the reading in the machinery's favor. The injection is
ideally coherent — exact −6.5 s/deg moveout at exact catalog distances,
an identical wavelet in every trace, exact P-alignment — whereas a real
arrival carries pick error, distance uncertainty, and waveform
variability, all of which dilute coherent gain: α\* from this design is a
lower bound on the amplitude a real arrival would need. And α is a
machine-level SNR scale on the processed, polarization-weighted traces,
not a statement about raw ground motion.

**Decoy-box family statistic.** A third card asked the family-wise
question latent in § 4.2: what fraction of target-box-sized (40 s ×
1.2 s/deg) decoy boxes, slid across the frozen sweep span (box centers
250–2100 s, full slowness range), contains a maximum at least as high as
the real target-box maximum? The box reader validated exactly,
reproducing four independently recorded anchors — the canonical argmax
cell, the target-box maximum 0.7736, the ridge-cell box 0.9327, and a
PKKP mirror threshold 0.2143 recorded before the sweep — but the card's
frozen adverse control failed: a box confined to the pre-P segment
([−90, −50] s × [−7.1, −5.9] s/deg), required to stay below 0.7736 on the
premise that the pre-P surface is quiet, returned a supported maximum of
**49.37**, independently re-derived from the stack file outside the
reader. The run stopped, as registered.

Because the reader is proven correct, the failure is a data property of
the canonical stacking surface — and that property, not any family
fraction, is this card's finding. The variant-A supported-power surface
carries an early-time trace-edge/normalization artifact ramp: 19 of 26
variant-A envelopes carry onset transients 5–355× the target-window scale
immediately after their valid-data onsets — trace-start/mask-edge energy
amplified by the variant-A normalization — and these survive the
minimum-support-2 mask with supported stacked power up to 1395 in the
pre-P segment, decaying monotonically into the early sweep span (largest
in-sweep box maximum 2.40, at center 280 s). Band-resolved, 100% of decoy
boxes with centers in 250–400 s exceed both PKiKP thresholds, against 0%
at 800–1600 s, with a small late trace-edge rise. The family fractions
the card froze were computed but are confounded by this demonstrated
ramp, and are therefore not accepted as false-alarm-style rates (they
remain recorded, with the per-box tables, in the card's history record).
The confirmatory family-rate lane on this surface is closed: the
band-resolved outcomes have been seen, so any restricted-domain variant
would be outcome-exposed and could only be exploratory, and a
confirmatory family statistic would require a fresh registration whose
null design excludes edge transients by per-event valid-data onset —
designed, and honestly labeled as designed, after this mechanism finding.
For the present benchmark the ramp is an additional reason the
uncertainty-folded standing of the target-box maximum (§ 4.2) should not
be over-read, and a documented instance of the control discipline doing
its designed job: the adverse control stopped a confounded statistic
before it entered this paper.

Taken together, the accepted calibrations bracket the detection machinery
on the same data that produced § 4. On the false-alarm side, destroying
moveout coherence leaves the PKiKP-window peak statistics essentially
unchanged: ridge-level argmax power arises in 75.5% of scrambled
realizations, target-box-level power in 48.0%. On the sensitivity side,
an ideally coherent published-coordinate arrival at one quarter of the
per-trace pre-P noise RMS out-competes the displaced ridge. The ridge of
§ 4.1 is therefore simultaneously statistically unremarkable against its
own scramble null, six-events fragile in composition (§ 4.3), and
globally dominant by a margin worth less than 0.25× pre-P RMS of coherent
target-coordinate energy; symmetrically, the target-box maximum's
within-tolerance standing (§ 4.2) is a property that nearly half of the
scrambled stacks reproduce, on a surface that additionally carries a
demonstrated early-time artifact ramp. None of this proves the published
detection false: these are same-data calibrations of a public
reconstruction, and the deflationary reading of § 5.1 stands. What they
establish is benchmark-internal and quantitative: on this surface, under
these frozen criteria, neither supported peak power nor in-box occupancy
discriminates moveout-coherent structure from moveout-incoherent
alternatives, so the evidential weight of a detection must come from
properties these nulls do not already reproduce — on the Moon that
property was the tightness of the reported uncertainties (§ 5.3), and it
is precisely the property the public reconstruction does not recover.

A fourth registered card executed the same frozen chain across the two
published 23-event selections and their 21-event intersection. Because it
answers a question about the relation to the independent re-analysis
rather than about the machinery, its result — the headline structure is
selection-invariant — is reported there (§ 5.6).

The triptych's Earth end executed as a registered single-station port of
the frozen machinery to known-truth data: 33 usable vertical-component
traces (from 40 selected events, M 6.2–7.8, 25.4–35.0°) at the quiet GSN
borehole station ANMO, aligned on ak135-predicted P from catalog
hypocenters, with three target phases (PcP primary, PKiKP secondary, ScS
plausibility boundary), twelve decoy windows, a 25-realization
event-scramble null, and two frozen grades mirroring the lunar pair —
paper-grade G1 and deliberately lenient replication-grade G2 (run record
`history/20260801_earth_ctrl/`). One registered control did not survive
contact with the data: the pilot alignment gate (envelope argmax within
±10 s of predicted P) failed on the pilot trace — argmax at +29.25 s, the
search-window edge, despite an envelope SNR of 66× the pre-P median — and
the gate statistic was then replaced by an onset criterion under which
the same trace passes. That replacement is a post-hoc criteria change
outside the preregistration's frozen repair rule, which permitted fixing
the alignment convention only; under the strict frozen reading the
registered remedy for a pilot failure was to stop. The production run and
everything reported below therefore carries exploratory,
deviation-flagged standing, and is reported under that flag rather than
not at all.

Under the frozen grading, the ported machinery did not recover the known
phases: PcP is undetected at both grades — as are PKiKP and ScS — while
the same-machinery nulls stay quiet (per-phase false-alarm rates
0.000–0.250, all below the frozen 1/3 quiet-null criterion), so the
preregistered verdict is NOT-RECOVERED at both grades; at the
replication grade the same stack also certifies two wrong-place decoy
windows (Table S1f). No directional interpretation of the
fitted-versus-predicted time offsets is drawn; the one initially offered
did not survive countersign review and is retired in the run record. The
triptych thus closes with both known-truth ends down: the lunar port
returned METHOD-FRAGILE on hard data (§ 5.3), and the Earth port fails
to recover PcP on easy data — large, well-located events on a quiet
station — under its preregistered criteria. Neither known-truth exercise
demonstrates that this machinery recovers known core phases under frozen
criteria, which bears directly on the evidential weight a same-machinery
detection on unknown-truth Mars data can carry, independent of the
same-data nulls above.

### 5.5 Limitations

The MPS-only deglitch lane is the largest fidelity gap and is prominently
attested in every product. The registered feasibility and single-event
equivalence cards (§ 3.1, dated additions) established an executable
public route to `UCLA_v4` and its DIVERGENT-MINOR standing against the
authors' shipped reference, and a registered production card (2026-08-02,
dated addition; § 3.1) then executed the follow-up those cards left open —
a production UCLA-stage pass and its effect on the benchmark surfaces. The
executable-partition result preserves the qualitative PKiKP disagreement
and subordination of the published-target maximum under UCLA-on-raw
provenance, but not the global-argmax coordinate itself. On the a-priori
frozen 19-event sub-stack, with the deglitch method the single factor
differing between lanes, the three registered readout surfaces compare
same-cell as:

| Registered surface | UCLA-on-raw (19-event stack) | MPS (19-event stack) | Accepted MPS (23-event stack, context) |
| --- | --- | --- | --- |
| PKiKP global argmax | 576.15 s, −10.0 s/deg, power 0.9003 | 662.85 s, 0.0 s/deg, power 1.0140 | 663.80 s, −3.64 s/deg, power 0.9327 |
| PKiKP published-box maximum | 584.00 s, −7.07 s/deg, power 0.7547 | 584.00 s, −7.07 s/deg, power 0.7356 | 601.95 s, −6.67 s/deg, power 0.7736 |
| PKKP endpoint | 1341.25 s, −6.97 s/deg, power 0.3049 | 1340.95 s, −6.97 s/deg, power 0.2422 | 1341.00 s, −6.97 s/deg, power 0.2143 |

The published-box maximum lands in the identical native-grid cell under
both deglitch methods (powers 2.6% apart); the PKKP endpoint is
same-slowness and 0.30 s near-concordant, with a 25.9% relative power
difference disclosed because no robustness tolerance was registered for
that surface. The qualitative PKiKP disagreement persists: the UCLA lane's
global maximum (power 0.9003) remains distinct from and stronger than its
published-target row (power 0.7547), so the published-target maximum stays
subordinate under UCLA provenance as well. The global-argmax coordinate,
by contrast, is deglitch-sensitive — the UCLA lane selects a third
near-degenerate location at the slowness-domain edge (576.15 s,
−10.0 s/deg), beyond the two branch families the leave-one-out control
documents (§ 4.3) — so the argmax is branch-fragile to both event removal
and deglitch method and is not a stable readout surface. The
23-to-19-event comparison also attributes the box-maximum displacement
(601.95 → 584.00 s) to the event set rather than the deglitch method,
since both deglitch lanes agree exactly at 19 events. Three bounds on the
comparison: the UCLA lane's terminal status is `ucla_unverified` (the
strict `mps_ucla_verified` attestation remains reserved; § 3.1); the
comparison runs on the 19-event sub-stack rather than the full 23-event
stack; and the persistence statement is qualitative — coordinate-level
robustness holds only where stated cell-exactly above. N = 200 bootstrap
realizations bound the resolution of occupancy statistics. The
composition-association p-values are same-data calibrations, and distance
and composition effects are not separately identifiable within the fixed
event table. The operator-ablation table was originally recorded at
`current_provenance_status=not_required`; a registered provenance-enforced
rerun of the identical chain subsequently reproduced all 240 rows with
exactly identical coordinates, every row at
`current_provenance_status=current`, and a byte-flip adverse control
failing closed — the ablation numbers used here carry full provenance
standing. TauP context uses public reference
models in a bounded registered query, not the authors' preferred interior
models. Nothing here addresses the PKKP-side detection with the same depth
as the PKiKP side.

### 5.6 Relation to the published claim and to independent re-analysis

Our result is a reproducible non-agreement plus internal fragility under a
registered public reconstruction. It is not a refutation, and the original
detection may survive exact-pipeline scrutiny. If it does, this benchmark
still stands as a public, runnable robustness benchmark for the claim — and
the released, hash-pinned pipeline gives the original authors a concrete,
runnable surface against which to demonstrate exactly which non-public step
makes the difference.

While this work was in preparation, Visser, Munch, Khan, Frost, and
Giardini (2026) — a team including InSight mission scientists — posted an
independent re-analysis of the same event family. They compute linear-stack
vespagrams together with an F-vespagram coherence statistic while varying
the assumed inner-core radius of the conditioning model between 50 and
650 km, and report coherent, in-window candidates for multiple radii —
200–300 km and 500–600 km for PKiKP (with beam amplitudes for the 200- and
300-km models exceeding those of the 600-km model) and 100–600 km for
PKIKKIKP — concluding that the data provide no definitive evidence for an
inner core. Their diagnosis and ours are independent and complementary
forms of non-uniqueness: their model-conditioned radius scan shows that a
search conditioned on a model prediction finds candidates for many assumed
radii (the § 5.2 concern instantiated in model space), while our registered
reconstruction shows that at the published radius the published coordinates
are not the dominant feature of the search surface, and that the dominant
feature's rank-1 status is itself six-events fragile (§ 4.1–§ 4.3). The two
studies share no code and differ in stacking method, filter band, and
normalization, yet converge on the same conclusion: the reported phase
attribution is not yet robust.

Two reproducibility-specific observations follow. First, their
preprocessing (deglitched waveforms, Butterworth band-pass,
Montalbetti–Kanasewich polarization filtering) sits in the same
public-methods family as our reconstruction, which independently supports
that this family is what the published description specifies. Second,
their stack uses 23 events described as those considered by Bi et al.
(2025), but the event list in their supplement differs from the frozen
23-event stack set declared in the Bi et al. supplementary tables
(archived here with hash-pinned provenance): it omits S0105a and S0189a
and includes S0409d and S0809a, two events that do not appear in the
archived published event tables.

Rather than leaving the selection difference as a caveat, we executed the
registered chain on their selection and on the 21-event intersection of
the two selections (registered as a cross-selection card after their
posting, with the two added events passed through the same gated
deglitch-and-rotation lane). The headline structure is
selection-invariant: in all three selections the global supported argmax
is the displaced ridge in the same slowness cell at 663.80–663.95 s
(rank 1), already fixed by the 21 shared events, while the
published-coordinate box maximum stays subordinate throughout and sinks
further under their selection (rank 6,938 canonical → 15,809 intersection
→ 25,172 Visser selection). The six ridge-critical events of § 4.3 are
common to both selections, consistent with this invariance. The
non-agreement reported here is therefore not an artifact of the two-event
selection difference. Event-exact declaration still matters, but at a
finer grain: the archived published tables record S0325a at
Δ = 39.7 ± 6.1°, inside the declared < 40° selection cut, while the
Khan et al. (2023) distances used by Visser et al. list the same event at
40.8 ± 1.7°, outside it — the declared selection rule is
catalog-dependent at its boundary, so the reproducible object is a
declared, hash-pinned event list rather than a selection rule. Their
materials are stated to be available on request; the present benchmark is
public and runnable, so a cross-execution of the two pipelines on the
exact declared event set is possible as soon as theirs is released.

## 6. Conclusions

Under a fully registered, provenance-gated public reconstruction of the
Bi et al. (2025) PKiKP vespagram analysis: (i) a supported local maximum
exists inside the published-pair target box (601.95 s, −6.67 s/deg) but
ranks 6,938th in the lane, carrying 0.83× the power of (17% less than) a
displaced, kinematically unexplained ridge 59.8 s later at shallower
slowness; (ii) the rank-1 status of that ridge depends conjunctively on six
of the 23 stacked events, any one of whose removal hands the argmax to a
time-adjacent shallow-slowness branch — not to the target-box maximum,
which never wins; (iii) plausible alignment error and bootstrap design do
not explain the displacement, while swapping the polarization operator
relocates the envelope-A winner in time but leaves the target-box maximum
non-global and the slowness mismatch unexplained; (iv) the
peak-comparison table and the leave-one-out repeat control are reproducible
to the byte from public inputs with frozen rules, and every claim-bearing
number traces to a hash-pinned artifact; (v) registered same-data
calibrations show the frozen detection criteria have no discriminating
power against moveout-incoherent alternatives on this data set — 75.5% /
48.0% scramble false-alarm rates at ridge / target-box quality — while an
ideally coherent injected arrival at the published coordinates
out-competes the ridge at 0.25× pre-P noise RMS (§ 5.4); and (vi) a
registered production pass of the authors' other deglitch method
(`UCLA_v4`, run on raw data over the a-priori frozen executable 19-event
sub-stack) leaves the qualitative disagreement and the subordination of
the published-target maximum in place — the published-box maximum is
cell-identical under both deglitch methods, while the global-argmax
coordinate itself is deglitch-sensitive (§ 5.5). Single-station core-phase
detections need — and with this benchmark, have — a public fragility
instrument; a pre-registered lunar blind test of the same machinery shows
why, producing "detections" in scrambled data and pure noise at
false-alarm rates near one at exactly the uncertainty tightness the public
reconstruction achieves (§ 5.3). The same-data scramble null closes that
loop on the benchmark's own stack (§ 5.4).

## Data and code availability

The complete pipeline, registered specification with amendment log,
manifests, per-artifact SHA-256 identities, and all small claim-bearing
tables will be archived before submission as a versioned public deposit
with a reproducibility capsule [OPERATOR INPUT at submission: repository
URL and archive DOI];
bulk stack products are hash-pinned in the capsule record and
regenerable from public inputs. All input data are public (PDS/IRIS,
MQS, IPGP Dataverse, Nature SI).

## Acknowledgements

This project used AI-assisted engineering and analysis (Anthropic Claude and
OpenAI Codex model families) under registered human-controlled criteria;
all scientific rules were frozen in versioned records before outcome
inspection, and all claim-bearing numbers trace to hash-pinned artifacts
(companion: NUMBERS.md). [Funding statement: OPERATOR INPUT at submission —
confirm wording, e.g., "This work received no external funding."]

## Author contributions

Artus Krohn-Grimberghe (sole author), per the CRediT taxonomy:
Conceptualization, Data curation, Formal analysis, Investigation,
Methodology, Project administration, Resources, Software, Validation,
Visualization, Writing – original draft, Writing – review & editing.

## Competing interests

The author declares no competing interests. [OPERATOR CONFIRM at
submission.]

## References (complete; verified against Crossref/DataCite publisher records 2026-08-02, record `history/20260802_ref_verify/`; recheck Visser et al. journal status at submission assembly)

- Beyreuther, M., Barsch, R., Krischer, L., Megies, T., Behr, Y., &
  Wassermann, J. (2010). ObsPy: A Python toolbox for seismology.
  *Seismological Research Letters*, 81(3), 530–533.
  https://doi.org/10.1785/gssrl.81.3.530
- Bi, H., Sun, D., Sun, N., Mao, Z., Dai, M., & Hemingway, D. (2025).
  Seismic detection of a 600-km solid inner core in Mars. *Nature*, 645,
  67–72. https://doi.org/10.1038/s41586-025-09361-9 (Author Correction:
  *Nature*, 648, E18, 2025, https://doi.org/10.1038/s41586-025-09981-1;
  citation-only, not affecting the pick tables used here).
- Crotwell, H. P., Owens, T. J., & Ritsema, J. (1999). The TauP Toolkit:
  Flexible seismic travel-time and ray-path utilities. *Seismological
  Research Letters*, 70(2), 154–160. https://doi.org/10.1785/gssrl.70.2.154
- Garcia, R. F., Gagnepain-Beyneix, J., Chevrot, S., & Lognonné, P.
  (2011). Very preliminary reference Moon model. *Physics of the Earth
  and Planetary Interiors*, 188(1–2), 96–113.
  https://doi.org/10.1016/j.pepi.2011.06.015 (A 2012 erratum,
  https://doi.org/10.1016/j.pepi.2012.03.009, corrects a-priori deep
  moonquake locations and the internal pressure computation; it does not
  affect the core-radius estimate cited here.)
- InSight Mars SEIS Data Service (2019). SEIS raw data, InSight Mission
  [data set]. IPGP, JPL, CNES, ETHZ, ICL, MPS, ISAE-Supaero, LPG, MSFC.
  https://doi.org/10.18715/SEIS.INSIGHT.XB_2016 (accessed via PDS
  `urn:nasa:pds:insight_seis` v3.0 and FDSN network XB; exact input
  files SHA-256-pinned in `manifest/data_manifest.json`).
- InSight Marsquake Service (2023). Mars Seismic Catalogue, InSight
  Mission, V14 (2023-04-01) [data set]. ETHZ, IPGP, JPL, ICL, University
  of Bristol. https://doi.org/10.12686/a21
- Khan, A., Huang, D., Durán, C., Sossi, P., Giardini, D., & Murakami,
  M. (2023). Updated interior structure models of Mars with a liquid
  silicate layer atop the Martian core [data set]. IPGP Research
  Collection (Dataverse). https://doi.org/10.18715/IPGP.2023.llxn7e6d
  (deposit files incl. `Core.zip`, SHA-256-pinned in
  `manifest/data_manifest.json`).
- Lognonné, P., Banerdt, W. B., Giardini, D., Pike, W. T., Christensen,
  U., et al. (2019). SEIS: InSight's seismic experiment for internal
  structure of Mars. *Space Science Reviews*, 215, 12.
  https://doi.org/10.1007/s11214-018-0574-6
- Montalbetti, J. F., & Kanasewich, E. R. (1970). Enhancement of
  teleseismic body phases with a polarization filter. *Geophysical
  Journal of the Royal Astronomical Society*, 21(2), 119–129.
  https://doi.org/10.1111/j.1365-246X.1970.tb01771.x
- Muirhead, K. J., & Datt, R. (1976). The N-th root process applied to
  seismic array data. *Geophysical Journal of the Royal Astronomical
  Society*, 47(1), 197–210.
  https://doi.org/10.1111/j.1365-246X.1976.tb01269.x
- Nunn, C., Garcia, R. F., Nakamura, Y., et al. (2020). Lunar seismology:
  A data and instrumentation review. *Space Science Reviews*, 216, 89.
  https://doi.org/10.1007/s11214-020-00709-3 (electronic supplement:
  Zenodo, https://doi.org/10.5281/zenodo.3560482).
- Apollo Passive Seismic Experiments (1969–1977). FDSN network XA [data
  set]. International Federation of Digital Seismograph Networks.
  https://doi.org/10.7914/SN/XA_1969
- Scholz, J.-R., Widmer-Schnidrig, R., Davis, P., Lognonné, P., Pinot,
  B., Garcia, R. F., et al. (2020). Detection, analysis, and removal of
  glitches from InSight's seismic data from Mars. *Earth and Space
  Science*, 7, e2020EA001317. https://doi.org/10.1029/2020EA001317
- Stähler, S., Khan, A., Banerdt, W. B., Lognonné, P., Giardini, D.,
  et al. (2021). Interior models of Mars from inversion of seismic body
  waves, V1.0 [data set]. IPGP Research Collection (Dataverse).
  https://doi.org/10.18715/IPGP.2021.kpmqrnz8
- Visser, M., Munch, F., Khan, A., Frost, D. A., & Giardini, D.
  (2026). No solid evidence for an inner core on Mars. Research Square
  preprint rs-10379955, version 1, posted 20 July 2026.
  https://doi.org/10.21203/rs.3.rs-10379955/v1 (preprint and supplement
  archived with SHA-256 provenance in this repository's reference
  library).
- Weber, R. C., Lin, P.-Y., Garnero, E. J., Williams, Q., & Lognonné, P.
  (2011). Seismic detection of the lunar core. *Science*, 331(6015),
  309–312. https://doi.org/10.1126/science.1199375

---

## Figures and tables

Generated by `make_figures.py` (in this directory) from SHA-256-pinned
recorded artifacts only. The generator re-derives the registered argmax,
target-box maximum, LOO flip set, branch fraction, FWE union,
scramble-null exceedance recounts, and injection-ladder rung values from
the pinned inputs and asserts them against the recorded values before
writing any output (an adverse shifted-box control must fail); input and output
digests are in `figures/figure_provenance.json`.

- **Fig. 1** (`figures/fig1_vespagram.*`) Registered-lane vespagram (full
  23-event stack, 520–720 s view) with the displaced ridge argmax, the
  target-box maximum, the published pair with its uncertainties, the frozen
  target box, the registered 550–700 s argmax window, and the
  reference-model PKiKP-family overlay (PKiKP, pPKiKP, sPKiKP). Sources:
  full-set NPZ (SHA-256 `f4b3a03a…`, S3-pinned, byte-verified) +
  `taup_phase_prediction_comparison.csv`.
- **Fig. 2** (`figures/fig2_loo.*`) Leave-one-out sweep: |Δt| of the
  supported PKiKP-window argmax per held-out event (six 57.5–61.9 s flips
  vs seventeen ≤ 0.95 s; log scale), with the four flips FWE-flagged in
  either bootstrap design marked. Caption must state that flips land on the
  shallow 602-family branch, not the target-box maximum. Source:
  `loo_table.csv` + `comp_assoc_reading.json`.
- **Fig. 3** (`figures/fig3_occupancy.*`) Type I bootstrap argmax-time
  bimodality (N = 200, `methods_robustness_200`, registered 632.0 s
  boundary) and 662-branch fractions with Wilson 95% CIs for both designs.
  Sources: `type1_pkikp_occupancy.npz`, `t2read_feature_competition.json`.
- **Fig. 4** (`figures/fig4_ablation_jitter.*`) (a) PKiKP argmax time per
  envelope variant × polarization operator × power window (the envelope-A
  operator sensitivity and B/C ridge survival); (b) jitter-audit centroid
  displacements and broadening ratios vs the observed 59.8 s displacement.
  Note: the ablation values are provenance-discharged — the registered
  enforced rerun reproduced all 240 rows coordinate-identically with every
  row `current_provenance_status=current` (§ 5.5;
  `history/20260801_ablpolop_prov/`). Sources:
  `ablpolop_peak_comparison_operator_ablation.csv`,
  `t3power_power_comparison.json`, `peak_comparison.csv`.
- **Table 1** (`tables/table1_peak_extract.md`) Registered-lane peak-table
  extract: argmax vs target-box features, both phases, ranks, quantiles,
  power ratio, tolerance flags. Source: `peak_comparison.csv` (SHA-256
  `8df5f5c8…`).
- **Table 2** (`tables/table2_flip_events.md`) The six flipping events:
  distance, flip landing coordinates (all at shallow slowness), |Δt|,
  per-design FWE status, and per-design Δ inclusion probability. Source:
  `loo_table.csv` + `comp_assoc_reading.json`.
- **Fig. 5** (`figures/fig5_scramble_null.*`) Scramble-null distributions
  (§ 5.4): histograms of the 200 null realizations' supported
  PKiKP-window argmax powers (panel A) and target-box maximum powers
  (panel B), real value marked, recorded exceedance counts (151/200 =
  0.755; 96/200 = 0.480) and null medians annotated; every annotated
  number is asserted against the frozen card record before rendering.
  Sources: `null_table.csv` + `frozen_stats.json`
  (`history/20260801_mars_scramble/`, SHA-pinned).
- **Table 3** (`tables/table3_injection_ladder.md`) Injection-recovery
  ladder (§ 5.4): per registered rung α ∈ {0, 0.25, 0.5, 1, 2, 4, 8},
  the global argmax (time, slowness, power, support), in-target-box flag,
  and target-box maximum, with footnotes fixing the α = 0 canonical-lane
  standing and the α = 8 failed literal control. Source:
  `recovery_table.csv` (`history/20260801_inject_recov/`, SHA-pinned).

## Supplementary Table S1: registered controls and their recorded outcomes

Each claim-bearing surface in this paper carries a positive control (a
known-true value the implementation must reproduce) and an adverse or
falsifying control (a deliberate corruption or null the implementation must
reject). This table compacts the recorded outcomes; full identities, hashes,
and run IDs are in the repository ledger and history records. Four
entries deliberately document control weaknesses and their recorded
dispositions — the fourth being the Earth pilot-gate failure and its
post-hoc replacement (S1f) — and one records an adverse control whose
firing blocked a confounded statistic (S1e) — reporting those is part of the benchmark's
claim.

### S1a — Input and provenance controls

| Surface | Positive control (recorded outcome) | Adverse / falsifying control (recorded outcome) |
| --- | --- | --- |
| Input integrity audit | 2,393 versioned inputs checksum-valid (run `20260722T040215Z`) | Adverse manifest makes exactly the one intended file stale, nothing else |
| Deglitch lane status | 26/26 events `succeeded_mps_only` in the accepted run | Strict `mps_ucla_verified` attestation FAILED and is reported as failed; the MPS-only lane is accepted by design, not silently upgraded |
| Rotation input gating | Audited input and isolated copy hash-identical; exact BHU/BHV/BHW at 20 Hz (S0105a) | Rotation fails closed when `deglitch_run_summary.json` is absent |

### S1b — Chain and peak-selection controls

| Surface | Positive control (recorded outcome) | Adverse / falsifying control (recorded outcome) |
| --- | --- | --- |
| End-to-end provenance chain | Accepted-run manifest: every stage succeeded, validation passed, current provenance requested and enforced | Peak detection with current-provenance enforcement exits blocked on a byte-flipped upstream trace |
| Peak-table reading (§ 4.1–4.2) | Figure layer re-derives the windowed supported argmax and target-box maximum and asserts equality with the recorded significance reading | A target box shifted by +100 s must not — and does not — reproduce the reading |
| Leave-one-out runner (§ 4.3) | Full-set restack reproduces the recorded cell exactly (663.80 s, −3.6364 s/deg, power 0.9327, support 23); S1015f hold-out repeat is byte-identical | Fail-closed tests: no supported in-window cell ⇒ nonzero exit, no artifacts. Documented weakness/repair: the card's initial "full-grid" rule failed its own positive control (grid-edge artifact) and was repaired by a registered pre-execution amendment, not a silent patch |

### S1c — Resampling and operator controls

| Surface | Positive control (recorded outcome) | Adverse / falsifying control (recorded outcome) |
| --- | --- | --- |
| Composition association (§ 4.3) | Recorded branch fractions and Wilson CIs reproduced; synthetic composition label detected as material | Permuted-label lanes: Type I all null (p = 0.864/0.660/0.329); Type II 1 of 3 material — below the registered ≥ 2/3 void rule |
| PKKP occupancy concordance (§ 4.3) | All six recorded Type I/II argmax cells re-derived exactly from the pinned occupancy products | Documented weakness/repair: the original transpose adverse control was vacuous by construction (recorded as such); replaced by a shape-preserving time-reversal control that reproduces 0/6 readings |
| Alignment-jitter audit (§ 4.4) | Zero-jitter lane reproduces base peak scalars to float32 identity; occupancy maps exactly binary | Audit power demonstrated: a 6×-excessive 60 s lane is material on both phases (PKiKP centroid displacement 27.9 s; PKKP 63.7 s) — the registered ±10 s lane's sensitivity is a finding, not an instrument floor |
| Polarization-operator ablation (§ 4.4) | 80 operator-independent rows reproduce the benchmark exactly (max Δt = 0.000 s, max Δs = 0.000 s/deg); registered provenance-enforced rerun reproduces all 240 rows coordinate-identically with every row `current` | Zero rows carry the M-K operator label (lane-contamination check); in the enforced rerun a byte-flipped input trace fails closed as missing-current-provenance |

### S1d — Model and external-calibration controls

| Surface | Positive control (recorded outcome) | Adverse / falsifying control (recorded outcome) |
| --- | --- | --- |
| Reference-model kinematic query (§ 4.4) | P 224.131 s, PKiKP 808.136 s, differential 584.0 s — within 0.01 s of the registered criterion values | A 10° geometry shift moves the differential by > 5 s; an impossible query point matches zero rows |
| Lunar-analog blind test (§ 5.3; dated companion experiment) | Port fidelity: six of seven modules byte-identical to the audited Mars implementation (diff audit recorded); deterministic rerun byte-identical; catalogue and velocity-model checksums verified against live sources | Four-null suite is the experiment's central instrument: at replication grade, event-scramble fires 75/75, phase-randomized noise 72/75, station-swap 6/6, decoy windows 16/24 (FAR 0.67–1.00) while real paper-grade detections are 0/3. Custody: archived report + frozen PREREG (SHA `ab5f8034…`) + criteria code in git; bulk run products not retained |

### S1e — Same-data calibration controls (§ 5.4)

| Surface | Positive control (recorded outcome) | Adverse / falsifying control (recorded outcome) |
| --- | --- | --- |
| Event-scramble null (§ 5.4) | Identity permutation reproduces the canonical argmax and target-box cells with exact float equality on all seven recorded values, on grids array-identical to the canonical chain; regenerated lane line-identical to the production table (SHA `8df5f5c8…`) | Effect control: a single permutation changes 4,525,248 vespagram cells (max \|Δ\| 1357.7) — permuted distances cannot be silently ignored; seed-1 rerun byte-identical; sweep rows byte-identical to the control rows |
| Injection ladder (§ 5.4) | α = 0 lane reproduces the canonical cell field-for-field under full provenance enforcement (240/240 rows current); production shift formula recovers the injected time 604.0 ± 0.051 s for 23/23 stacked traces in every lane; α = 1 and α = 8 reruns byte-identical including stack files | Documented weakness/disposition: the α = 8 literal "within one grid cell" control FAILED on the time axis (603.90 s = two 0.05-s cells from 604.0; slowness within one cell) and was adjudicated a control-tolerance design flaw — monotone α-convergence toward 604.0 from the in-box background maximum at 601.95 s; a convention error would displace by tens of seconds or flip sign. Not quotable as a passed literal control |
| Decoy-box family (§ 5.4) | Reader reproduces four independent recorded anchors exactly: canonical argmax cell; target-box maximum 0.7736; ridge-cell box 0.9327; pre-sweep-recorded PKKP threshold 0.2143 | Frozen pre-P adverse box (required < 0.7736) returned 49.37 — the control FIRED and stopped the run, demonstrating the edge-ramp surface property; family fractions computed but confounded, not accepted; confirmatory family-rate lane on this surface closed |

### S1f — Earth known-truth control (§ 5.4)

| Surface | Positive control (recorded outcome) | Adverse / falsifying control (recorded outcome) |
| --- | --- | --- |
| Earth single-station port (§ 5.4) | Known-truth recovery expectation NOT met: PcP undetected at both frozen grades (PKiKP and ScS also undetected) → verdict NOT-RECOVERED at G1 and G2. Upstream, the registered pilot alignment gate FAILED (argmax +29.25 s at the search-window edge, envelope SNR 66×) and its statistic was replaced post hoc — an out-of-boundary deviation under the frozen repair rule; strict frozen reading: pilot FAIL → STOP, so the production run carries exploratory, deviation-flagged standing | Same-machinery nulls stayed quiet: FAR^PcP 0.000/0.080 (N1) and 0.000/0.250 (N2) at G1/G2 — all below the frozen 1/3 criterion, so the non-detection is not null-noise masking; at G2 the stack nonetheless certifies two wrong-place decoy windows. Full record, deviation log, and P2 backlog: `history/20260801_earth_ctrl/` |
