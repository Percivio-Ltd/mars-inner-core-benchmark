# CARD P0-SIG-STATEMENT — registered headline significance reading

Registered 2026-07-26 by the lead, BEFORE any reading of the target
quantities, under operator direction ("Yes, run them"). Confirmatory
reading of registered statistics from the frozen current-gate peak
table; no new computation of scientific fields.

## Scientific question

For the publication's single headline sentence: in the registered
primary public lane, how subordinate is the published-pair target-box
maximum relative to the competing global ridge, in rank, background
quantile, and stack power?

- Criterion linkage: § A.4 benchmark surface (E.4 rows 1-2 context);
  publication framing per `PUBLICATION_ASSESSMENT.md`.
- Artifact: one JSON verdict
  (`history/20260726_publication_assessment/sig_statement_reading.json`)
  with SHA-256 recorded in the ledger.

## Prior-knowledge disclosure

Already recorded (not new): global 663.80 s/−3.64 s/deg rank 1;
published-pair 601.95 s/−6.67 s/deg with target-box rank 6938, outside
exact tolerance, inside uncertainty-folded tolerance; PKKP paper-target
1341.00/−6.97 rank 13395 within tolerance. NEW quantities under this
card: the background quantile of the published-pair target-box peak, the
global/published-pair stack-power ratio, and the PKKP mirror quantile.
No threshold or lane choice is tuned after seeing the new quantities:
every selector below is fixed by already-frozen records.

## Registered reading rules (frozen)

1. Source table: `results/tables/peak_comparison.csv`. Before reading,
   its SHA-256 MUST equal the digest recorded for it in
   `history/20260725_assembly_cgr/cgr_identity_manifest.sha256`
   (locator-bound; run `scripts/07_validation/verify_cgr_identity.py`
   first — any failure aborts the card).
2. Lane selector (PKiKP): rows with `phase=PKiKP`, `mode=paperfaith`,
   `norm_variant=A` (registered primary lane,
   `REGISTERED_PRIMARY_LANE_BY_PHASE`), and lane fields equal to those
   of the row whose `peak_label=global` matches the recorded current-gate
   header values (663.80, −3.64 at 2 dp). If that row is not unique
   across lanes, ABORT as ambiguous (no discretionary choice).
3. Registered outputs, PKiKP lane:
   - S1 `target_box_rank` of `peak_label=published_target` (restate).
   - S2 `box_peak_background_quantile` of `published_target` (NEW).
   - S3 power ratio `power(global) / power(published_target)` (NEW).
   - S4 both tolerance booleans of `published_target` (restate).
4. PKKP mirror (same lane-selection rule via the recorded 1341.00/−6.97
   `paper_target`): rank restated; background quantile NEW.
5. Headline sentence template (registered): "In the registered primary
   public lane, the published PKiKP pair is a within-uncertainty-folded-
   tolerance local maximum at target-box rank {S1} and background
   quantile {S2}, while the unexplained displaced ridge carries {S3}×
   its stack power."

## Controls

- Positive: the selected `global` row must reproduce 663.80/−3.64 and
  the `published_target` row 601.95/−6.67 (2 dp); PKKP `paper_target`
  1341.00/−6.97. Any mismatch aborts (reader or identity defect).
- Adverse (fail-closed): running the identity gate against a scratch
  copy of the table with one digit altered must FAIL before any read.
- Determinism: the reading executed twice; byte-identical JSON.

## Stop condition

One JSON artifact + ledger Done entry with the filled headline sentence.
No further analysis, no threshold interpretation beyond the template.
