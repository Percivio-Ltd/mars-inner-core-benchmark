# Bounded draft-accuracy review — Paper 0 v0.5

## 1. Calibration gate

Initial `git rev-parse HEAD` returned `93ef6b96867a0eb032b7c80669c3b7160759ce11`, as required.

Using realizations 1–200 from `null_table.csv` against `frozen_stats.json:frozen_thresholds`:

- Ridge ≥ 0.9327: **151/200**
- Target box ≥ 0.7736: **96/200**

**CALIBRATION GATE: PASS.**

The shared checkout subsequently advanced to `e2911b99…`; a read-only comparison found no differences in any scoped manuscript or authority path, so this review remains bound to the requested `93ef6b96…` state.

## 2. Named checks

**C1 — PASS.** `DRAFT_seismica.md:594–596` says the injection moves the global argmax “into the published target box” at `(602.95, −6.46)`; `NUMBERS.md:123–127` explicitly identifies it as a fourth object distinct from `(601.95, −6.67)` and the published pair.

**C2 — PASS.** `DRAFT_seismica.md:609–627`, Table S1e, `NUMBERS.md:81`, and `table3_injection_ladder.md:17` consistently report the α = 8 literal control as **FAILED**, never as passed.

**C3 — PASS.** No numeric decoy-family fraction appears in the draft or `NUMBERS.md`; `DRAFT_seismica.md:661–666` gives only the adjudicated band result—100% at centers 250–400 s versus 0% at 800–1600 s—and disposition-only family wording.

**C4 — FAIL.** The values are correct—75.5%/48.0% and p = 0.756/0.483—and `DRAFT_seismica.md:553–554` uses the required phrase, but the scoped §4.2 caveat at `DRAFT_seismica.md:272–274` says only “under randomly sampled distance assignments,” omitting “from the registered permutation null.”

**C5 — PASS.** `DRAFT_seismica.md:709–746`, Table S1f, and `NUMBERS.md:91–93` carry the exploratory, deviation-flagged standing and correctly report 33/40, M 6.2–7.8, +29.25 s, 66×, PcP FARs 0.000/0.080 and 0.000/0.250, two G2 wrong-place certifications, and NOT-RECOVERED at both grades; no prohibited directional offset interpretation or decoy-center time is quoted.

**C6 — PASS.** The four weakness entries are: (1) LOO full-grid positive-control repair, S1b; (2) vacuous transpose adverse-control replacement, S1c; (3) α = 8 one-cell tolerance failure, S1e; and (4) Earth pilot-gate failure/post-hoc replacement, S1f. The separate adverse control is the decoy pre-P control that fired and blocked the family statistic, S1e.

**C7 — PASS.** The §5.3 forward hook points to §5.4; §5.4 points correctly to S1e, S1f, Fig. 5, Table 3, and §5.6; all five listed figures and three tables exist in both listed formats where applicable; no stale Visser pointer to §5.5 remains.

**C8 — FAIL.** Fig. 5 annotations are explicitly checked, the committed Table 3 exactly matches `write_table3()` output from the pinned CSV, and its footnotes are correct. However, `make_figures.py:405–452` does not `check()` every value later tabulated at `make_figures.py:846–855`: powers, supports, slownesses, and target-box values for several rungs flow through without value-specific assertions.

**C9 — PASS.** The scoped bundle records 43/43, 34/34, 36/37; exact R_ch values 0.0886/0.0429/0.0833; the descriptive equivalent of EXECUTABLE-OCTAVE; DIVERGENT-MINOR; reserved `mps_ucla_verified`; and consistent MPS-only language in §§3.1 and 5.5.

**C10 — PASS.** All scoped load-bearing scientific numbers map to matching `NUMBERS.md` rows. Twenty-three rows were spot-verified against their authorities: rows 64–71, 75–81, 84–86, 89–90, and all three Earth rows 91–93.

**C11 — PASS.** The Garcia note confines the erratum to deep-moonquake locations and internal-pressure computation and correctly states that the cited core-radius estimate is unaffected; the Visser DOI `10.21203/rs.3.rs-10379955/v1` and posted date 20 July 2026 match the archived verification record.

**C12 — PASS.** The manuscript’s 25.4–35.0° is the correct rounding of 25.41–34.96°; the 1/3 criterion matches REPORT §9; G1/G2 mirror the lunar grades; and ANMO is correctly expanded as `IU.ANMO.00.BHZ` in `NUMBERS.md:91`.

## 3. Numbered findings

1. **P2 — §4.2 omits the registered-permutation-null qualifier.**  
   **File:** `papers/Paper0/manuscript/DRAFT_seismica.md:272`.  
   **Affected claim:** the scope of the 75.5%/48.0% scramble calibration.  
   **Causal path:** the shorter wording can be read as generalizing beyond the registered sampled permutation law, although the preceding sentence names a registered same-data null and §5.4 supplies the exact qualifier. No alternative implementation or materially different scientific outcome is demonstrated.  
   **Evidence:** `history/20260801_mars_scramble/ADJUDICATION.md:67–71` records this wording boundary as P2-2 and requires “randomly sampled distance assignments from the registered permutation null.” The severity ratchet therefore forbids escalation on the same evidence.

2. **P2 — Table 3’s value-specific assertion coverage is incomplete.**  
   **Files:** `papers/Paper0/manuscript/make_figures.py:405`, `papers/Paper0/manuscript/make_figures.py:419`, and `papers/Paper0/manuscript/make_figures.py:846`.  
   **Affected claim:** the figure-list statement that injection-ladder rung values are asserted against recorded values before output, and the reproducibility guard around Table 3.  
   **Causal path:** several parsed rung fields—especially later-rung power/support/slowness and target-box power/time—are rendered without corresponding value-specific `check()` assertions. The full-file SHA-256 pin still prevents an uncoordinated input change, and an independent in-memory reconstruction matched the committed table byte-for-byte, so no current scientific value is wrong and no P1 claim-impact path is established.  
   **Evidence:** the CSV pin is correct (`0b7a66a4…`), all committed table values match `recovery_table.csv`, and the footnotes match the injection adjudication; the defect is bounded assertion/test coverage.

VERDICT: COUNTERSIGNED