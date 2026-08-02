VERDICT: COUNTERSIGN

## Verification results

### Object pins

All reviewed objects matched their required SHA-256 pins:

- `MEMO.md`: `e7f9eba122fd2736b35b8bc6ed1e4568ff361c29c7f5fbb4174d64783948f184`
- `results.json`: `1990dd5324c85b6e6d38595893f623f3b7a177f06463ef11ba0c14e13462bd31`
- `card_text_frozen_fe38a196.md`: `7f724e46244a9bb233f74b30a9ea28c13f319ccaaa7a1f3c4ef972837ed2200a`

### Registered-lane readouts

I independently ran the repository peak detector in memory with current-provenance enforcement on each registered `paperfaith/envelope/A/nth_root/win20` NPZ. These recomputations exactly matched the corresponding CSV rows and MEMO Section 2:

| Selection | Global supported argmax `(t, s, power, support)` | Target-box maximum `(t, s, power)` | Box rank |
|---|---|---|---:|
| Canonical 23 | `(663.8, -3.6363636363636367, 0.9326603162534909, 23)` | `(601.95, -6.666666666666666, 0.7736156900239739)` | 6938 |
| XSEL-21 | `(663.95, -3.6363636363636367, 1.0598720995065811, 21)` | `(602.1, -6.666666666666666, 0.7336002265040527)` | 15809 |
| XSEL-V23 | `(663.9, -3.6363636363636367, 1.0886853459975248, 23)` | `(602.05, -6.565656565656566, 0.6765041138613289)` | 25172 |

All global maxima are rank 1 and classify as `662-family` under the frozen `time_s < 632.0` rule.

Direct CSV scans found exactly 240 rows in each of:

- `peaks/peak_comparison_canonical.csv`
- `peaks/peak_comparison_xsel21.csv`
- `peaks/peak_comparison_v23.csv`

Each contained 240/240 `current_provenance_status=current` rows and exactly one registered PKiKP `global` and `published_target` row.

### Subset artifacts and controls

I extracted the broad-mask argmax directly from each subset NPZ using finite cells with support ≥2 over `t=550–700 s`, then compared it with the JSON:

- `subsets_canonical/full_set.json`: `(663.8, -3.6363636363636367, 0.9326603162534909, 23)`
- `subsets_canonical/hold_out_S0105a.json`: `(663.75, -3.6363636363636367, 1.0123297663708317, 22)`
- `subsets_canonical/hold_out_S0189a.json`: `(663.4, 0.0, 0.9770995126907189, 22)`
- `subsets_canonical/hold_out_S0105a_S0189a.json`: `(663.95, -3.6363636363636367, 1.0598720995065811, 21)`
- `subsets_v23/full_set.json`: `(663.9, -3.6363636363636367, 1.0886853459975248, 23)`

All five NPZ/JSON comparisons were exact. The canonical, XSEL-21, and V23 subset fields, support maps, axes, and event arrays were also element-for-element identical to their production-chain registered-lane NPZs.

The positive and known-answer controls reproduce both the frozen card’s displayed values and the full-precision recorded LOO artifacts under `history/20260726_publication_assessment/loo/runs/`.

`results.json` contains 10 controls, all with `passed=true`. Its eight input hashes independently matched both the files and `ARTIFACTS_SHA256.txt`. The manifest has 3210 valid entries and hashes to `e5bb29415e1cc63efaaeac5f64e4215389d67fcd50c9770eb4fc5a432e203ee1`.

## Procedure conformance

- Variant construction conforms: canonical contains 23 registered events; XSEL-21 removes exactly `S0105a` and `S0189a`; V23 adds exactly `S0409d` and `S0809a`. Table hashes are respectively `c9dbf74a…4fc82ec5`, `06427aeb…49426d8`, and `75938d64…5654a63`.
- New rows contain the frozen parameters exactly: S0409d `(A, 28.2°, 70.0°)` and S0809a `(A, 30.9°, 91.0°)`.
- Catalog recomputation found one matching event each, with preferred origins `2020-01-21T11:27:02.464172Z` and `2021-03-07T11:09:26.997140Z`, and XB/ELYSE P picks `11:31:05.388096` and `11:13:15.949092`.
- `tables/fetch_table.csv` and `fetch_prestage/fetch_table.csv` are byte-identical at SHA-256 `317ac6685f05cf29ef0925f11c0c6a342117a8c33b95f5d1479cc4c5e078ac0c`.
- Raw fetches contain the required three XB.ELYSE.02 BHU/BHV/BHW traces, 20 Hz and 51200 samples. Hashes are `70a52e2c…b9f7b45e` and `16cc3ca9…f0609f73`.
- Deglitch summary `5df9eee3…e9571f2c` records both events as `succeeded_mps_only`, MPS `succeeded`, and `samples_modified=true`; detector tables exist. The legacy environment is Python 3.10.20, NumPy 1.23.5, SciPy 1.9.3; SEISglitch is at `e594a626…` with the recorded one-line `np.atleast_2d` compatibility patch.
- Rotation sidecar hashes and every referenced deglitch-metadata, summary, input, and ZNE-output hash recomputed exactly. ZNE hashes are `94ae4d62…c1fc701` and `7e8134dc…5ca456`; UVW start-time spreads are 0.001 s and 0.0 s.
- All 53 canonical staged inputs and all 52 V23 manifest entries matched both their staged destinations and recorded source hashes.
- `run_chain_canonical.sh` and `run_chain_v23.sh` execute the registered bandpass → polarization → FDPA → alignment → normalization/envelope → vespagram → enforced peak sequence. No polarization override is supplied, and payloads record `montalbetti_kanasewich_1970`. The relevant repository scripts and inputs are byte-identical at execution commit `7d669b72`, card commit `fe38a196`, and the reviewed checkout.
- The adverse control flipped byte 200 of `lane_v23/S0409d_paperfaith_A_envelope.npy`: `a185e749…fff5c16b` → `83461381…d265364c`. Enforced detection exited 1 with `blocked_missing_current_provenance`, named the mismatching input, and wrote no scratch table. The target and retained backup both currently hash to the original `a185e749…fff5c16b`.
- Only the registered five subset outputs and three peak tables exist. No single-swap decomposition beyond the two controls, radius scan, F-statistic artifact, or additional PKKP-specific analysis was found.

## Findings

No P0 or P1 finding satisfies the required active-claim, causal-path, and reproducible-evidence test.

## P2 observations — non-blocking

1. **D2 numeric parenthetical is inaccurate.** The MEMO and `DECISIONS_pre_execution.md` say canonical table origins sit `1.0–5.5 s` pre-P. Across the 23 registered rows, recomputation gives `0.077854–63.555670 s`. The consequential coverage statement remains correct: the 60 s fetch lead produces `60.077854–123.555670 s`, agreeing with the MEMO’s rounded `60–124 s`. New-event requested pre-P margins are `302.923924 s` and `288.951952 s`.  
   Claim impact: only the explanatory parenthetical is affected; alignment is P-pick anchored and all registered readouts are unchanged. Evidence: `tables/event_table_canonical.csv` and `lane_canonical/*_aligned_paperfaith.alignment.json`.

2. **The adverse control implements D1, not the frozen card’s literal raw-file flip.** `detect_peaks.py` re-hashes seven path/hash arrays and checks that deglitch-summary hashes are nonempty; it does not re-hash `raw_fetch/*.mseed` or the summary files themselves. Thus the envelope flip validly demonstrates fail-closed behavior at the enforced stack-input surface, but not raw-fetch enforcement. The MEMO discloses the raw-file limitation, so no active invariance claim relies on broader enforcement. Its phrase that enforcement “re-hashes … the deglitch summary hash” should more precisely say it checks for a nonempty recorded hash.

3. **Attempt-1 diagnosis is not fully preserved.** `logs/deglitch_attempt1_relpath_defect.log` records two failures and the fail-closed traceback, but not the claimed command arguments, doubled path, or SEISglitch stdout; those per-event metadata files were overwritten by the successful rerun. The relative-path causal explanation is consistent with wrapper behavior, but cannot be reconstructed solely from the frozen attempt log. This affects audit hardening only: final detector files, successful command records, outputs, and provenance hashes are independently present and verified.

4. **Resume chronology is verified, but the termination cause is not independently logged.** `peak_comparison_v23.csv` was written at `2026-08-01 20:07:21 UTC`; V23 subset, adverse control, collector, and MEMO were written from `2026-08-02 02:42:53 UTC` onward, supporting the stated roughly six-hour resume gap. The supplied artifacts do not independently establish that subscription exhaustion caused the termination. This is a source-attribution limitation with no path to the registered scientific result.