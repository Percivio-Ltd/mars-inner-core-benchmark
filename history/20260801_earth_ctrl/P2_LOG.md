# P0-EARTH-CTRL — P2 backlog (recorded, not fixed in-cycle)

Source: `countersign/report_countersign_r1.md` (Codex `gpt-5.6-sol` `xhigh`, banner verified;
round-1 review of REPORT.md pre-fix SHA-256
`09d61324ac54c1df0fbc345cb2309ceb5ae2e13d8c4cd3a4439e7e39c0dd325a`).
Policy: MarsQuake AGENTS.md delegated-cycle rules — P2 findings are recorded to the backlog,
never fixed in-cycle, and never block. Severity ratchet applies: these findings cannot be
re-raised at higher severity on the same evidence.

## P2-3 (verbatim from round-1 review)

> **P2 — Absolute offsets are incorrectly narrated as signed offsets.** `grade.py` deliberately
> records absolute `dt` and `dp` ([grade.py](code/grade.py:23)), but the report prints positive
> signs and calls all target fits late and less-negative ([REPORT.md](REPORT.md:144)). The
> underlying 85% rows show fitted times 145.505, 601.674, and 602.875 s versus targets 181.67,
> 633.81, and 636.72 s—each is early. PcP slowness is −9.346 versus −6.259, hence more
> negative, not less-negative ([stats_real.csv](runs/real/stats_real.csv:4)). This invalidates
> the stated late-bias/source-duration interpretation but not the absolute-bound grading.

Disposition: recorded, not fixed in-cycle. Exception mandated by lead adjudication: the
late-bias/source-duration INTERPRETATION sentences were countersign-invalidated and were
REMOVED (not sign-corrected) wherever the P1-1 rewrite touched them; remaining sign-narration
prose (e.g. "+" signs in the section-7 table, the "less-negative/P-like ridge side" clause)
stays as-is in this cycle and is superseded by this record: detection-table `dt_vs_pred_s`,
`dp_vs_pred_sdeg` are ABSOLUTE values; fitted 85% centroids are EARLY in time for all three
targets and MORE negative in slowness for PcP (see stats_real.csv).

## P2-4 (verbatim from round-1 review)

> **P2 — The fired decoy region is mislocated.** The fires are `PcP_decoy+150` and
> `PKiKP_decoy+150` ([far_table.csv](analysis/far_table.csv:6)), whose frozen centers are
> 931.67 and 933.81 s ([addendum_A_targets.json](addendum_A_targets.json:43);
> [addendum_A_targets.json](addendum_A_targets.json:83)). The report instead places them at
> 538.33 and 536.19 s, which are the `−300` decoys ([REPORT.md](REPORT.md:208)). FARs and
> verdicts remain unchanged.

Disposition: recorded, not fixed in-cycle (section 8 prose not touched by the P1 fixes). This
record supersedes the prose: the two G2 decoy fires are the far_table rows `PcP_decoy+150` and
`PKiKP_decoy+150`; authoritative window geometry is `addendum_A_targets.json`.

## P2-5 (verbatim from round-1 review)

> **P2 — Some execution telemetry is not artifact-traceable.** The 1.46 s, 7.8 min, and
> 15.2 min timings appear in the report ([REPORT.md](REPORT.md:123)), but the runner only
> prints those values to stdout ([run_real.py](code/run_real.py:122)), and no real-run
> stdout/timing artifact appears in the inventory
> ([ARTIFACT_SHA256.txt](analysis/ARTIFACT_SHA256.txt:8)). This is a provenance gap without
> result impact.

Disposition: recorded, not fixed in-cycle. Timings are operational telemetry, not scientific
quantities; no timing artifact was added in the fix round.
