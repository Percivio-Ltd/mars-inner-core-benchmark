# P0-EARTH-CTRL — landing record (2026-08-02)

Lead landing of the Earth single-station known-truth control after the
round-2 countersign. Host-local run directory:
`/Users/artuskg/marsquake_runs/20260801_earth_ctrl`. This directory holds
the claim-bearing subset of that run.

## Cycle

- PREREG countersigned before any waveform contact (round 1 → round 2
  COUNTERSIGNED; `countersign/prereg_countersign_r{1,2}.md`).
- Execution: 33 usable IU.ANMO.00.BHZ traces (40 selected under the
  frozen query), production pass + 25/25 N1 scramble realizations + 12
  decoy windows; grading only after all outputs existed as files
  (PREREG § 11 order).
- Report countersign round 1 (Codex `gpt-5.6-sol`, `xhigh`, banner
  verified): NOT COUNTERSIGNED — P1-1 (DEV-2026-08-01-3 pilot-gate
  statistic replacement, out-of-boundary and post hoc), P1-2
  (unregistered grader verdict branch), P2-3/4/5.
- Lead adjudication of the fix round: P1-1 → honest re-reporting only
  (registered gate reported FAILED at +29.25 s; dual standing, STRICT
  FROZEN READING GOVERNS → production verdicts carry exploratory,
  deviation-flagged standing; the countersign-invalidated
  late-bias/source-duration interpretation removed everywhere). P1-2 →
  grader restored to the frozen § 9 `INCONCLUSIVE` term with verdicts
  required byte-identical — proven: all four analysis-table hashes
  unchanged, only `code/grade.py` changed (`ecda80fb…` → `7f183bf7…`;
  `analysis/P1-2_hash_{before,after}.txt`). P2s recorded to `P2_LOG.md`,
  never fixed in-cycle (severity ratchet applies).
- Report countersign round 2: COUNTERSIGNED, zero new findings
  (`countersign/report_countersign_r2.md`; stdout banner `model:
  gpt-5.6-sol`, `reasoning effort: xhigh` verified).

## Countersign stdout logs (not committed; SHA-256)

- `report_stdout_r1.log`
  `be39cd436acf48faf844a3ef9433230498d51a51253937dc943cdc9c1321fceb`
- `report_stdout_r2.log`
  `52959bb774d1414ce092fd24eb9d14ccadfddad87f9945c138d476963ca425de`

## Committed here vs local-regenerable

Committed: `REPORT.md` (post-fix), `PREREG.md` + `PREREG_SHA256.txt`,
`P2_LOG.md`, `addendum_A_targets.json`, `code/` (incl. the repaired
`grade.py`), `analysis/` (detection/FAR/verdict tables, P1-2 hash
records, the 105-artifact `ARTIFACT_SHA256.txt` inventory), `catalog/`,
`runs/real/{stats_real,peak_table}.csv`, and `countersign/` briefs + md
verdicts.

Local-only, deterministically regenerable, every file hashed in
`analysis/ARTIFACT_SHA256.txt`: `data/` (~12 MB public IRIS waveforms,
re-fetchable per `catalog/data_manifest.csv`) and the remaining `runs/`
bulk (~67 MB vespagram/null NPZ outputs, reproducible from the committed
code and the frozen seeds 100–124).

## Standing (binding for any quotation)

Exploratory, deviation-flagged: the strict frozen reading governs, and
the registered remedy for the pilot failure was STOP. As-run verdicts:
NOT-RECOVERED at G1 and G2; PcP, PKiKP, and ScS undetected; FAR^PcP
N1 0.000/0.080 and N2 0.000/0.250 (G1/G2), all below the frozen 1/3
criterion; at G2 two wrong-place decoy windows certified. Never quote a
directional (late/early) offset interpretation (P2-3,
countersign-invalidated) or decoy-window center times (P2-4).

## Draft integration

§ 5.4 Earth triptych paragraphs + Table S1f; S1-preamble and § 3.2
control-weakness counts three → four; `NUMBERS.md` rows + caution 6 —
landed together with this record.
