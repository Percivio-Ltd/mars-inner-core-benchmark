# P0-EARTH-CTRL port diff log

Custody: `mars_modules/` holds copies of the repo originals (SHA-256 in
`mars_modules/COPY_SHA256.txt`; repo at commit of 2026-08-01, read-only). Every adaptation from
the Mars modules is listed here; anything not listed is byte-identical or verbatim-copied.

## Byte-identical modules (used as-is)
- `mars_modules/stacking.py` == `scripts/03_vespagram/stacking.py` (imported by the kernel; the
  nth-root stack, zero-padded shift, support logic — untouched).
- `mars_modules/fit_gaussian.py` == `scripts/04_bootstrap/fit_gaussian.py` (imported as a library:
  `fit_projection`, `weighted_median`, `assess_projection_fit_quality`; its Mars-specific
  `fit_bootstrap_maps` file-naming wrapper is not called).

## Import-mechanics-only adaptations (lunar precedent)
- `earth_kernel.compute_vespagram`: function body copied verbatim from
  `scripts/03_vespagram/compute_vespagram.py`; only the import block changed (direct import of the
  copied stacking module instead of `scripts.shared.import_local_module`). Mirrors the lunar port
  ("compute_vespagram differs in import mechanics only").
- `earth_kernel` envelope helpers `window_indices`, `_contiguous_true_runs`, `_erode_valid_mask`,
  `_masked_segment_envelope`, `_smooth_over_valid_support`: copied verbatim from
  `scripts/02_preprocess/normalize_and_envelope.py`; `normalize_variant` reproduces the z-score +
  envelope sequence of `normalize_and_save` (lines 109-130) with the window passed as an argument
  (Mars hardcodes the A/B/C window dict; Earth windows are the frozen A'/C').
- `earth_kernel._is_local_maximum`: copied verbatim from `scripts/03_vespagram/detect_peaks.py`
  lines 207-216. `box_peak_local_max` is the thin box-argmax wrapper (the Mars original wraps the
  same check in its provenance-heavy table machinery).

## D-ADAPT-E4 (declared in PREREG §5): bootstrap parameterization
- `earth_bootstrap.bootstrap_type1_earth` mirrors `bootstrap_type1.py`:
  pick_n = max(2, floor(2N/3)) (line 97), rng = default_rng(seed), one `rng.choice` per iteration
  with `sorted(...)` (line 116), per-iteration `compute_vespagram` with the same fixed arguments,
  window-max -> threshold occupancy -> mean maps. Changes: windows dict argument instead of the
  hardcoded pkikp (550,700) / pkkp (1200,1500); ref_distance argument (30.0) instead of hardcoded
  29.0 (line 141); repo provenance/fidelity imports dropped; occupancy returned in-memory per
  window label. The occupancy helper `_phase_peak_occupancy` is copied verbatim from
  `bootstrap_type3_alignment_jitter.py:113-141` (identical logic to type1's inline `max_mask`).
- `earth_bootstrap.bootstrap_type3_earth` mirrors `bootstrap_type3_alignment_jitter.py`:
  one `rng.uniform(-10, 10, n_events)` per iteration, all events jittered (no subsampling),
  `shift_trace_on_time_axis` / `shift_mask_on_time_axis` copied verbatim (lines 84-100).
  Same parameterization changes as type1.
- RNG draw order is preserved exactly in both (one draw per iteration, nothing else consumes the
  stream), so seeds reproduce bit-identically under the same inputs.
- Omitted from the type3 mirror: the Mars module's base (unjittered) vespagram and its
  `base_peak_*` npz metadata fields (bootstrap_type3_alignment_jitter.py:186-217). These are
  metadata-only — grading reads exclusively the occupancy-map statistics; the non-bootstrap
  vespagram and its box peaks are computed independently in `run_real.py`. RNG unaffected (the
  base computation consumes no random draws).

## Earth-specific drivers (new code, no Mars counterpart)
- `make_addendum_A.py` (frozen targets/decoys; PREREG §4/§8), `acquire.py` (PREREG §3),
  `preprocess.py` (PREREG §3.5/§5; cut logic `cut_zero_padded` reproduces
  `align_and_cut._cut_with_zero_padding` nearest-sample semantics verbatim, time axis
  `arange(npts)/sr - pre` verbatim `_relative_time_axis`), `run_real.py`, `run_n1.py`,
  `grade.py` (grade_row verbatim from `results/lunar_analog/code/apply_criteria.py:43-53`;
  G1 Type-III rider logic verbatim from lines 91-100; box-peak gate applied symmetrically per
  DEV-2026-08-01-1).
