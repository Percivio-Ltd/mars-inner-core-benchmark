# P0-MARS-SCRAMBLE — Mars-side event-scramble null: verdict memo

Worker memo for the registered card P0-MARS-SCRAMBLE
(`docs/research_pipeline.md`, frozen at commit a2163d49). Isolated run dir:
`/Users/artuskg/marsquake_runs/20260801_mars_scramble/`. Repo read-only
throughout; scientific interpreter `/Users/artuskg/micromamba/envs/mars-ic/bin/python`.

## Question

How often does the Mars 23-event source-array stack produce PKiKP-window
peaks of ridge quality (canonical supported argmax power 0.9327) or
target-box quality (published-box max 0.7736) when event distances are
permuted, destroying moveout coherence? This is the lunar N1 null — which
fired 75/75 at replication grade on the Moon — run for the first time on the
Mars data itself: the same-data false-alarm calibration of the
occupancy/argmax machinery (Paper 0 § 4/§ 5 peak-comparison honesty; A1
recommendation that every single-station stacking claim carry a matched
null suite).

## Canonical-lane regeneration and gate (STEP 1)

Chain (one finite observed run, 18:19:54–18:24:59 UTC, `chain.log`): copied
26 `data/processed/*_ZNE.mseed` + `*_ZNE.rotation.json` into the isolated
dir, then bandpass → polarization → fdpa → align_and_cut →
normalize_and_envelope → run_vespagrams → `detect_peaks.py
--require-current-provenance`, all stages `--in-dir/--out-dir` (or
`--data-dir/--input-dir/--out-csv`) pointed at the isolated dir.

Operator resolution: the card's chain recap says `principal_axis_projection`,
which is internally inconsistent with the card's own frozen gate cell and
thresholds; committed evidence (production `results/tables/peak_comparison.csv`,
the ablation card's recorded operator-sensitivity finding, and
`run_paper0.py`'s flagless polarization invocation) pins the canonical lane
to the default operator `montalbetti_kanasewich_1970`. Resolution was
recorded in `DECISION_operator_resolution.md` BEFORE the chain ran and was
ACCEPTED by the lead pre-outcome; the lead is amending the card text with a
dated amendment. No frozen statistic, seed, threshold, N, or control was
altered.

GATE OUTCOME: PASS. The regenerated `peak_comparison_canonical.csv`
(240 rows, all `current_provenance_status=current`) contains the canonical
PKiKP global supported argmax exactly:

- global: t=663.8 s, s=−3.6363636363636367 s/deg, power=0.9326603162534909,
  support=23 — bit-identical to the production row;
- published_target: power=0.7736156900239739 (the frozen 0.7736 threshold
  source), t=601.95, s=−6.666…, support 23;
- stronger than required: the entire 240-row regenerated table is
  line-identical to the production `results/tables/peak_comparison.csv`.

Gate table SHA-256:
`8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce`.

## Scramble runner (STEP 2)

`scramble_runner.py` implemented by Codex `gpt-5.6-sol` at `xhigh`
(banner verified in `codex_impl_stdout.log`; brief
`codex_impl_brief.txt`; summary `codex_impl_out.md`). Reviewed line-by-line
by this worker: genuine import of the repo stack
(`compute_vespagram.py` → `stacking.py`) and of the detect_peaks argmax/box
functions; frozen constants asserted against the module authorities
(min support 2, window (550, 700), box 584–624 × [−7.1, −5.9], ref distance
29.0, slowness −10…0 in 100 steps, nth-root n=4, 20-s power window);
permutation law exactly `numpy.random.default_rng(20260801 + i)`,
`rng.permutation(23)`, identity rejected by redraw from the same rng;
distances permuted per-realization (`base[permutation]`), traces/masks
never touched; deterministic .17g CSV output written atomically; np.save-only
grid dumps. Codex transcript audited: no out-of-scope writes, no execution
beyond a source-only syntax check.

## Controls (STEP 3, registered order) — ALL PASS

(a) Positive: identity permutation through the runner reproduces the
    canonical cell with exact float equality on all seven recorded values
    (argmax t/s/power/support; box power/t/s), and the runner's identity
    vespagram grid and support-count grid are array-identical (NaN-aware)
    to the canonical chain NPZ `vesp/paperfaith/envelope/A/nth_root_win20.npz`
    — the runner IS the canonical stack. Artifacts: `control_identity.csv`,
    `ctl_r000_vesp.npy`, `ctl_r000_support.npy`.
(b) Effect: seed-1's per-trace shift table differs from identity's
    (`ctlA_r001_shifts.csv` vs `ctl_r000_shifts.csv`), and its vespagram
    grid differs massively: 4,525,248 nonzero |Δ| cells (max |Δ| 1357.7),
    NaN support-edge pattern shifted — the runner cannot be silently
    ignoring permuted distances.
(c) Determinism: seed-1 run twice → byte-identical results CSV, vespagram
    grid, support grid, and shift table (`control_seed1_runA.csv` vs
    `control_seed1_runB.csv`, `ctlA_*` vs `ctlB_*`).

## Sweep (STEP 4)

One finite observed run (`sweep.log`, progress line per realization):
identity + realizations 1–200, all 201 completed, zero errors, zero
blocked/NaN realizations. Cross-run consistency: the sweep's r0 row is
byte-identical to the identity-control row and its r1 row byte-identical to
the seed-1 control row.

## Frozen statistics (registered before execution; computed by the
pre-registered `compute_frozen_stats.py`, written before any null existed)

N = 200 null realizations; real values from the regenerated canonical lane:
ridge (global argmax power) 0.9326603162534909, target-box power
0.7736156900239739.

- FAR_ridge (null argmax power ≥ 0.9327): **0.755** (151/200)
- FAR_target (null target-box max ≥ 0.7736): **0.480** (96/200)
- Exceedance p_ridge = (1 + #{null ≥ real})/(N+1) = **0.7562** (152/201)
- Exceedance p_target = **0.4826** (97/201)
- Ridge null quantiles (5/25/50/75/95%):
  0.9192 / 0.9364 / 0.9790 / 1.0429 / 1.1938; null max 1.3327
- Target-box null quantiles (5/25/50/75/95%):
  0.6007 / 0.6780 / 0.7667 / 0.8460 / 0.9794; null max 1.0765
- NaN counts: 0 (ridge), 0 (target)

`frozen_stats.json` records the exact values.

## Interpretation

The Mars 23-event stack reproduces the lunar N1 behavior on its own data:
destroying moveout coherence leaves the PKiKP-window peak statistics
essentially unchanged. Three-quarters (75.5%) of distance-scrambled
realizations produce a full-window supported argmax at or above the
canonical ridge power, and the real canonical value sits at only the ~24th
percentile of its own scramble null (p_ridge 0.756, two-sided reading: the
real ridge is *typical*, not exceptional; the null median 0.979 exceeds
it). Nearly half (48.0%) of scrambles reach the published-target-box
quality, and the real target-box maximum lies at the null median (p_target
0.483). Under the frozen criteria, ridge-quality and target-box-quality
peaks are the ordinary product of 4th-root stacking of these 23 normalized
envelopes at ANY distance assignment: the peak-power and box-occupancy
machinery has no discriminating power against moveout-incoherent
alternatives on this data set.

Registered honesty clause (carried in substance): this is a same-data
calibration; the null destroys moveout coherence while keeping envelopes,
so it calibrates the machinery's box-occupancy behavior on this noise
field, not event-set propagation physics. It does not prove any detection
false; it quantifies the false-alarm behavior of the detection criteria
themselves. For Paper 0 § 4/§ 5 this is the matched null suite the A1
report demanded: the displaced 663.8-s ridge and the 0.7736 target-box
maximum are both statistically unremarkable against the scramble null.

## Residual uncertainty

- The null keeps the envelope set fixed; it does not calibrate against
  alternative event selections, alignment jitter, or amplitude
  renormalization (those are separate registered lanes: bootstrap
  types 1–3).
- Permutations preserve the multiset of the 23 distances; the null is
  conditional on the observed distance distribution (as registered).
- 200 realizations bound the exceedance p to ≥ 1/201 ≈ 0.005; irrelevant
  here since both p values are near the middle of the null.
- The nth-root stack's power normalization means null powers can exceed 1
  (median 0.979, max 1.333); thresholds were applied exactly as frozen,
  with no rescaling.

## Artifact hashes (SHA-256)

- `null_table.csv` (201 rows: identity + 200 nulls):
  `12aa226d7e755b9bc691de9d7d1872b25041ee73993f3829c25eb5849fbe06c6`
- `frozen_stats.json`:
  `0330244276493fa7470ad685feefe0115cf5577ce428ef1eaa3d16124eb134c4`
- `scramble_runner.py`:
  `81758d9042453d76f77cb73f525163fad9011ab447d3484194dd4ec71ec2ab11`
- `peak_comparison_canonical.csv` (gate table):
  `8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce`
- `control_identity.csv`:
  `d118cf4ed1fbf10f5a7ce0e158faf51fa0c8604d8cd9f930820fad10f2533f59`
- `control_seed1_runA.csv`:
  `02d1a0df85d1f9036f299c4ca685894c5f056a5cb7d3c8da3bca272a1a8c620a`
