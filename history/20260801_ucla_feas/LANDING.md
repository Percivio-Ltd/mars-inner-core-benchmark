# P0-UCLA-FEAS — lead landing record (2026-08-01)

Countersign round 1 of 1: COUNTERSIGNED (banner re-verified by the lead from
`countersign_round1_stdout.log`: `model: gpt-5.6-sol`, `reasoning effort:
xhigh`, codex-exit=0). Card SHA-256 `0168fdd0233156dfe83cb4a0def65bd8d704d11b
ff668f00851601384d7ac8ec`; countersign output SHA-256 `985a3659…`; brief
SHA-256 `fc281537…`. The files in this directory were copied byte-identical
from the isolated run dir (`/Users/artuskg/marsquake_runs/20260801_ucla_feas/`)
and re-hashed at landing against `artifact_hashes.sha256` and
`COUNTERSIGN_RECORD.txt` (12/12 OK). The one recorded P2 (probe3-vs-probe4
traceability wording) is non-blocking and clarified in the countersign record;
no fix round was required.

## Lead decisions on the card's open questions

Taken at landing and BEFORE the registered discriminator run (P0-UCLA-EQUIV),
so they cannot be fitted to its outcome:

1. Attestation semantics (Q1): the card's recommendation is ADOPTED —
   runner-side self-attested `expected_output_sha256` is self-attestation and
   is NOT sufficient for `verification_status: mps_ucla_verified`. That status
   is reserved until the S0235b MATLAB-reference equivalence run classifies
   EQUIVALENT under the frozen rule in the P0-UCLA-EQUIV card; even then,
   claiming it in production requires a further registered decision.
2. Chaining semantics (Q2, UCLA-on-MPS-output vs raw): deferred to the future
   production card; the equivalence run uses the shipped sample directly and
   does not touch the harness.
3. `MAIN20SPSReconcile` (Q3), `Conservative` flag (Q4), green functions (Q5):
   for the equivalence run these are FORCED as-shipped (Reconcile included;
   Conservative = 0; shipped fixtures), because the shipped reference outputs
   `dc.mat`/`aaout3.mat` were produced by the shipped flow — any deviation
   would invalidate the comparison. Production-run choices remain open for the
   future card.
4. Windowing (Q6): the equivalence run uses the shipped sample's full extent
   as-is; Paper 0 windowing questions stay with the production card.

## Scope note

This card changes no benchmark result. The accepted Paper 0 deglitch lane
remains MPS-only (`succeeded_mps_only`, 26/26) with the strict
`mps_ucla_verified` attestation honestly reported as failed; this landing only
establishes that the UCLA route is executable without MATLAB and registers the
discriminator that could eventually change that reporting through registered
steps.
