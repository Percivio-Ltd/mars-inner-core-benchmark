# P0-ABL-POLOP-PROV — provenance-enforced operator-ablation rerun (2026-08-01)

Card registered before execution in `docs/research_pipeline.md` (commit
`6dda97d4`, prior to any output existing). Host: Nimue, lead session, one
finite observed chain. Isolated dir:
`/Users/artuskg/marsquake_runs/20260801T143200Z_ablpolop_prov` (3.4 GB,
deterministically regenerable in ~5 min from canonical
`data/processed/*_ZNE.mseed` + committed scripts; bulk stays local per the
large-artifact policy, claim-bearing product hash recorded here).

## Chain

Card-5 chain verbatim with enforcement added (no other free parameters;
windows are the fixed `POWER_WINDOWS_S` constant): copy 26
`*_ZNE.mseed` + `*_ZNE.rotation.json` → bandpass → polarization
(`--operator principal_axis_projection`) → fdpa → align_and_cut →
normalize_and_envelope → run_vespagrams → `detect_peaks.py
--require-current-provenance`. Timing: 14:32:44–14:37:44 UTC (5 min 0 s);
full log `chain.log`.

## Controls

1. Pre-chain positive: 4 polarization contract tests passed
   (`tests/test_preprocess_contracts.py -k polarization`, incl. the
   operator-difference assertion), `mars-ic` interpreter.
2. Registered reproduction rule (frozen in the card before execution):
   every row key of the recorded Card-5 CSV (SHA `0f927fd4…`) must
   reproduce with identical `(time_s, slowness_sdeg)`. OUTCOME: 240/240
   keys present, **zero coordinate deltas**, zero missing/extra keys
   (`compare_ablation_prov.py`).
3. Enforcement: **all 240 rows `current_provenance_status=current`**
   (the original table recorded `not_required` because enforcement was
   not requested).
4. Adverse (byte-flip): flipped byte 200 of the NPZ-recorded input trace
   `S1015f_ablation_C_envelope.npy` → enforced `detect_peaks` exited 1
   with `blocked_missing_current_provenance` writing no accepted table;
   byte-exact backup restored and verified
   (`d9550b61d11168bad979588a6b17663031329c4a5ad073adb7606d9275869d5c`
   pre == post). Scratch log `adverse_run.log` in the run dir.

## Verdict

REPRODUCED-AND-ENFORCED. The recorded ablation coordinates are exactly
reproduced under full current-provenance enforcement; the ablation table's
provenance limitation is discharged and Fig. 4a / § 4.4 ablation numbers
are claim-bearing eligible in the submitted version.

Enforced table: `peak_comparison_operator_ablation_provenance.csv`,
SHA-256 `512f78e1135ec4f4f729a48261f3a49b3c32fda21909ddfff13c57d1db1b0193`.
