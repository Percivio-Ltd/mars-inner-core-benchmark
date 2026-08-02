# P0-XSEL-VISSER — Cross-selection invariance of the PKiKP benchmark structure

Run dir: `/Users/artuskg/marsquake_runs/20260801_xsel_visser/` (repo read-only throughout; commit at execution `7d669b72`, card frozen at `fe38a196`, extract `card_text_frozen_fe38a196.md` sha256 `7f724e46244a9bb233f74b30a9ea28c13f319ccaaa7a1f3c4ef972837ed2200a`).
Interpreter: `/Users/artuskg/micromamba/envs/mars-ic/bin/python`. Dates: 2026-08-01/02 UTC.

## 1. Question

Is the benchmark's headline PKiKP structure — 662-family global supported ridge with the
published target-box maximum subordinate — invariant across the two published 23-event
selections (Bi `set=vespagram` vs Visser et al. 2026 Table S1, a 2-out/2-in swap:
omit S0105a, S0189a; add S0409d, S0809a), and does the 21-event intersection already
determine it?

Variants: XSEL-21 = canonical 23 minus {S0105a, S0189a}; XSEL-V23 = intersection plus
{S0409d, S0809a}.

## 2. Frozen per-variant readouts

Registered lane paperfaith/envelope/A/nth_root/win20/montalbetti_kanasewich_1970;
production stack (slowness −10..0 s/deg, 100 steps, ref 29.0°, 20 s power window,
min support 2). Family rule verbatim: "602-family" if time_s < 632.0 else "662-family".
Target-box rank = 1 + supported finite cells with strictly greater power within the
broad PKiKP mask (s −10..0 × t 550–700); box = t 584–624 s × s [−7.1, −5.9].

| Selection | Global supported argmax (t s, s s/deg, power, support) | Family | Global rank | Target-box max (t, s, power) | Box rank |
|---|---|---|---|---|---|
| Canonical 23 (reference) | 663.80, −3.6363636363636367, 0.9326603162534909, 23 | 662-family | 1 | 601.95, −6.666666666666666, 0.7736156900239739 | 6938 |
| XSEL-21 (intersection) | 663.95, −3.6363636363636367, 1.0598720995065811, 21 | 662-family | 1 | 602.10, −6.666666666666666, 0.7336002265040527 | 15809 |
| XSEL-V23 (Visser 23) | 663.90, −3.6363636363636367, 1.0886853459975248, 23 | 662-family | 1 | 602.05, −6.565656565656566, 0.6765041138613289 | 25172 |

Each variant was computed twice by independent code paths — the production chain
(run_vespagrams → enforced detect_peaks; XSEL-21 additionally as a table-driven sweep
over the canonical lane) and the reviewed subset runner (`xsel_runner.py`, extending the
registered LOO holdout mechanics) — with bit-identical results (collector controls
`xsel21_subset_csv_consistency`, `v23_subset_csv_consistency`).

## 3. Interpretation (outcome-neutral, within the card's scope)

The headline structure is invariant under the published selection swap. In all three
selections the global supported argmax lies in the same slowness cell
(−3.6363636363636367 s/deg) at 663.8–663.95 s (662-family) and is the rank-1 supported
cell, while the published target-box maximum remains subordinate (rank 6938 / 15809 /
25172 among supported cells of the broad PKiKP mask). The 21-event intersection already
exhibits the structure; neither Bi's pair (S0105a, S0189a) nor Visser's pair
(S0409d, S0809a) creates or removes it. The known single-event branch fragility of the
LOO card (S0189a holdout argmax at s = 0.0) does not propagate to any of the three
registered selections here. No statement beyond these registered readouts is made.

## 4. Controls (card) — all resolved

1. POSITIVE (canonical 23 gate): PASSED bit-exact, twice. Chain CSV registered-lane
   global row and runner full-set both give t=663.8, s=−3.6363636363636367,
   power=0.9326603162534909, support 23; runner gate `{applicable: true, passed: true}`.
   All 240 CSV rows `current_provenance_status=current`.
2. KNOWN-ANSWER SINGLES (through the extended runner): PASSED bit-exact.
   holdout S0105a → 663.75, −3.6363636363636367, 1.0123297663708317, support 22,
   662-family; holdout S0189a → 663.40, 0.0, 0.9770995126907189, support 22, 662-family.
   Both equal the recorded LOO rows.
3. ADVERSE (byte-flip, fail-closed): PASSED. Flipped byte 200 (XOR 0xFF) of the
   fetched-event input `lane_v23/S0409d_paperfaith_A_envelope.npy`
   (orig sha256 `a185e749…fff5c16b`, flipped `83461381…d265364c`); enforced
   detect_peaks over `vesp_v23` exited 1 with
   `blocked_missing_current_provenance` ("sha256 mismatch for input_trace_paths:
   …/lane_v23/S0409d_paperfaith_A_envelope.npy"); no scratch table written; byte-exact
   backup restored and SHA-256 re-verified equal to the original. Log
   `logs/adverse_control.log`.
4. DEGLITCH FAIL PATH: NOT TRIGGERED. Both new events genuinely passed the accepted
   MPS-only lane (`succeeded_mps_only`, samples_modified=true, detector tables present).
5. FDSN STALL: NOT TRIGGERED. Both events fetched promptly via IRIS FDSN.

Mechanical collector (`collect_results.py` → `results.json`,
sha256 `1990dd53…13462bd31`): 10/10 controls passed, including all-rows-current for all
three CSVs, canonical CSV gate cell exact, runner↔CSV consistency for both variants, and
V23 gate correctly not applicable.

## 5. Lane evidence

Canonical lane: 26 `*_ZNE.mseed` + `*.rotation.json` pairs byte-verified (SHA-256)
from `data/processed/` (`inputs_manifest.json`, `b58e9472…1fa77cb8`); registered chain
bandpass → polarization (default montalbetti_kanasewich_1970, no --operator flag) →
fdpa → align_and_cut (repo manifest + MQS v14 catalog) → normalize_and_envelope →
run_vespagrams → detect_peaks --require-current-provenance.

XSEL-V23 new-event lane (S0409d, S0809a):
- Catalog: unique MQS v14 ID matches with preferred-origin XB/ELYSE P picks.
  S0409d origin 2020-01-21T11:27:02.464172Z (P 11:31:05.388096); S0809a origin
  2021-03-07T11:09:26.997140Z (P 11:13:15.949092). Frozen card parameters used for the
  table rows: Δ=28.2°/BAZ=70°/A and Δ=30.9°/BAZ=91°/A.
- Fetch: XB.ELYSE.02.BHU/V/W, window [origin−60 s, origin+2500 s], merge fill 0.0;
  3 traces each, 20 Hz, 51200 npts; UVW starttime spread ≤ 1 ms. Raw sha256:
  S0409d `70a52e2c…b9f7b45e`, S0809a `16cc3ca9…f0609f73`.
- Deglitch (accepted MPS-only lane): wrapper `deglitch_mps_ucla.py` in mars-ic spawning
  pinned SEISglitch (legacy env python 3.10.20 / NumPy 1.23.5 / SciPy 1.9.3,
  `external/seisglitch` @ e594a626 with the single-row removal patch), pinned inventory
  copy byte-verified. Both events `overall_status=succeeded_mps_only`,
  `samples_modified=true`; run summary sha256 `5df9eee3…e9571f2c`.
- Rotation: rotate2zne (U=135/V=15/W=255, dips −29.3), sidecars record deglitch summary
  hash and `output_zne_sha256`; spread 0.001 s.
- Gate before lane entry: `tables/fetch_table.csv` (built by the reviewed
  `make_variant_tables.py` from catalog + frozen card parameters) byte-identical (cmp)
  to the pre-registered `fetch_prestage/fetch_table.csv` that drove the download.
- lane_v23: 26 pairs per V23 table byte-verified (24 canonical from `data/processed/`,
  2 fetched from `rotated_new/`), `lane_v23_manifest.json` `ccbc85c8…9585d84`; then the
  identical registered chain with `tables/event_table_v23.csv`.

Variant tables (byte-preserving edits of the canonical bytes;
`tables_manifest.json` `060a994e…fa834fed1`): canonical copy sha
`c9dbf74a…4fc82ec5` (equals repo manifest); xsel21 `06427aeb…49426b26d8` (canonical
minus the two rows); v23 `75938d64…cfd5654a63` (plus `27,S0409d,A,…,28.2,,70.0,vespagram`
after S0918a and `28,S0809a,A,…,30.9,,91.0,vespagram` after S1022a). S1015f extraction
control on the origin-extraction path passed (`2021-10-04T04:52:29.248537Z`).

## 6. Honest caveats and residual uncertainty

- Adverse-control target (pre-registered decision D1, `DECISIONS_pre_execution.md`,
  written before any outcome existed): the card's literal "fetched raw input" (the raw
  BH mseed) is mechanically unreachable by provenance enforcement — after deglitch,
  nothing re-reads it; enforcement re-hashes the seven recorded product arrays plus the
  deglitch summary hash. The flip was therefore applied to the NPZ-recorded input trace
  of a fetched event (ABL-POLOP-PROV analogue). Consequence: raw→deglitched linkage is
  attested by recorded hashes (rotation sidecar → deglitch summary → per-event
  metadata), not by live re-hashing of the raw file. A raw-file flip would NOT be
  caught by enforcement; this is a property of the registered enforcement surface, not
  of this run.
- New-row origin times (D2) are MQS v14 catalog preferred origins. The committed
  canonical table's origin_time values are not catalog origin values (they sit 1.0–5.5 s
  pre-P); alignment is P-pick-anchored and ID-matched (catalog-delta tolerated), so
  this affects only raw-fetch coverage margin (new events carry ~240–300 s pre-P vs
  60–124 s for canonical events), not the cut or the stack.
- Deglitch attempt 1 failed (`failed_missing_detector_file`) due to an executor
  invocation defect: relative --in/--out/--work paths made seisglitch resolve its config
  against the subprocess cwd (doubled path; this SEISglitch build exits 0 on
  config-not-found). Diagnosed from recorded ARGS/stdout, rerun with absolute paths;
  the detector never saw data in attempt 1, so this is not a lane failure. Evidence:
  `logs/deglitch_attempt1_relpath_defect.log`, superseded outputs overwritten by the
  recorded successful rerun (`logs/deglitch.log`).
- The session was killed by subscription exhaustion (~20:07 UTC 2026-08-01) immediately
  after `peak_comparison_v23.csv` was written; work resumed ~6 h later from disk. All
  pre-kill artifacts were re-verified from disk before continuing; the V23 restack,
  adverse control, collector, and this memo are post-resume. No MarsQuake state outside
  the run dir was written at any point.
- Stack support caveat inherited from the production lane: support_count 23 (or 21/22)
  reflects the registered min-support-2 supported-cell convention of the lane, and
  power values are 4th-root stack amplitudes in the lane's normalized units; values are
  comparable across selections only within this lane.

## 7. Artifact inventory

Full manifest: `ARTIFACTS_SHA256.txt` (3210 files) sha256
`e5bb29415e1cc63efaaeac5f64e4215389d67fcd50c9770eb4fc5a432e203ee1`.

Key artifacts (sha256, path relative to run dir):
- `8df5f5c85473460e19e10021db52c997945f3bee6f4f8aac461251a5a0bf07ce  peaks/peak_comparison_canonical.csv`
- `e5ccee5c0f922aff16cb0c2829347984c484a75756804143517e4cba7d7b80c7  peaks/peak_comparison_xsel21.csv`
- `725d5c14ea31d2c324ffe4aae2cc354745017e9ecb2b9c6f531e0bbe75d87940  peaks/peak_comparison_v23.csv`
- `07d7a2741422e9fc0b6af8d2aae527ff73d245f50391938bed3831551f0f5b95  subsets_canonical/full_set.json`
- `7e38800f2968d312225a76c0feb5fe2e7686b329fb1b2e08f20ae69e3d81f3e5  subsets_canonical/hold_out_S0105a.json`
- `6d25a85f04e80f92146385c2f4462ed2ac0d26725f88073491049fe21e11e01e  subsets_canonical/hold_out_S0189a.json`
- `7ab19386a1a4e354f2f85324e94a6f715a31f0673a36f72c658eb31dedcb862a  subsets_canonical/hold_out_S0105a_S0189a.json`
- `20a570b509f8c6c4f0d2b4849cc3da856098ff149464ec6aa2f37763c431e0bb  subsets_v23/full_set.json`
- `1990dd5324c85b6e6d38595893f623f3b7a177f06463ef11ba0c14e13462bd31  results.json`
- `c9dbf74a89abc45db1539d7efbf6a54f44c4e4d5ccbcd44e746ea33d4fc82ec5  tables/event_table_canonical.csv`
- `06427aeb5c4ba9f6cc89dddf03905909b879d1fd91e3fbb2f1954149426b26d8  tables/event_table_xsel21.csv`
- `75938d64e2b44f8b00d781e86504d2a822af1778adfd511096133fcfd5654a63  tables/event_table_v23.csv`
- `317ac6685f05cf29ef0925f11c0c6a342117a8c33b95f5d1479cc4c5e078ac0c  tables/fetch_table.csv` (byte-identical to `fetch_prestage/fetch_table.csv`)
- `060a994e73422df1746d577aa1de49a5bc9ab365507231bdea8fadafa834fed1  tables/tables_manifest.json`
- `b58e94726b27a5a4c753ebd742683d7bc7fd8e952a409d4a9cdd4ddb1fa77cb8  inputs_manifest.json`
- `ccbc85c8dcf4255b48921e8b6f39820b63afcef1ef36532314b85566b9585d84  lane_v23_manifest.json`
- Raw/processed new-event files: raw `70a52e2c…`, `16cc3ca9…`; deglitched `f3b9fa85…`,
  `38444036…`; ZNE `94ae4d62…`, `7e8134dc…`; sidecars `6d7e0beb…`, `b001a89c…`
  (full 64-hex values in ARTIFACTS_SHA256.txt).

Executed code: `stage_inputs.py`, `stage_lane_v23.py`, `run_chain_canonical.sh`,
`run_chain_v23.sh`, `run_xsel21_sweep.sh`, `adverse_control.py` (executor-authored);
`xsel_runner.py`, `make_variant_tables.py`, `collect_results.py` (Codex gpt-5.6-sol
xhigh, session 019fbed1-8e5c-7292-9938-c501bac96ce7, banner verified; reviewed
line-by-line against the card before execution; hashes in ARTIFACTS_SHA256.txt).
Codex I/O under `codex/`. Stop condition of the card met: two variant tables, controls,
memo; no further variants, decompositions, radius scans, F-statistics, or PKKP
extension were run.
