# Pre-registered resolution: canonical-lane polarization operator

Recorded 2026-08-01 BEFORE executing any chain stage in this isolated dir
(worker for card P0-MARS-SCRAMBLE, frozen at commit a2163d49).

## The contradiction inside the frozen card text

The card's chain recap says "exactly as the P0-ABL-POLOP-PROV card (bandpass →
polarization `principal_axis_projection` → …)" while its non-negotiable
positive gate and frozen thresholds are:

- gate cell: PKiKP global supported argmax (663.80 s, −3.6364 s/deg,
  power 0.9327, support 23);
- FAR_ridge threshold 0.9327; FAR_target threshold 0.7736.

These two elements cannot both be executed: committed, pre-existing evidence
shows the `principal_axis_projection` chain cannot produce the gate cell.

## Committed evidence (all pre-dating this run; none generated here)

1. `results/tables/peak_comparison.csv` line 92 (production, provenance
   `current`): `paperfaith,envelope,A,montalbetti_kanasewich_1970,nth_root,
   20.0,PKiKP,global,663.8,-3.6363636363636367,0.9326603162534909,23,…`
   — exactly the gate cell, under the canonical default operator.
2. Same file, published_target row: power `0.7736156900239739` — exactly the
   frozen FAR_target threshold 0.7736, same canonical lane.
3. `history/20260801_ablpolop_prov/peak_comparison_operator_ablation_provenance.csv`
   (the deterministic P0-ABL-POLOP-PROV rerun): the same lane under
   `principal_axis_projection` yields `603.25,-3.5353535353535355,
   0.9332648265013125,23` — not the gate cell; no row of that 240-row table
   contains (663.80, −3.6364, 0.9327).
4. `docs/research_pipeline.md`, P0-ABL-POLOP card status: "the envelope-A
   global argmax is operator-sensitive (flips to 601.9 s/−3.54)" — the
   operator-sensitivity of exactly this argmax is a registered finding.
5. `scripts/run_paper0.py` invokes `polarization_filter.py` with no
   `--operator` flag; the committed default is
   `montalbetti_kanasewich_1970` (`polarization_filter.py` line 480).

## Resolution (registered before running)

The card's scientific object is "the canonical lane", and every frozen
numeric anchor (gate cell, 0.9327, 0.7736) is exactly and only the canonical
default-operator lane value. The parenthetical operator flag is a
transcription slip carried over from the ablation card's chain recap (that
card's purpose was the *other* operator). "Exactly as the P0-ABL-POLOP-PROV
card" is honored for the isolation mechanics: copied `*_ZNE.mseed` +
`*_ZNE.rotation.json` inputs, isolated dir, identical stage sequence,
`--require-current-provenance` enforcement.

Therefore the polarization stage in this run is executed with the canonical
production operator, passed explicitly:
`--operator montalbetti_kanasewich_1970`.

No frozen statistic, seed, threshold, N, or control is altered. The
non-negotiable gate stays fully armed: if the regenerated table does not
contain the gate cell, the worker stops and reports without proceeding.
This note is written so the countersigner and the lead can adjudicate the
resolution itself; if the lead rejects it, the run is discarded, not
reinterpreted.

## Lead adjudication (received 2026-08-01, before any scramble output existed)

ACCEPTED by the lead: "the card's chain recap carried a transcription slip
from the ablation card; the canonical lane's frozen numeric anchors (gate
cell 663.80/−3.6364/0.9327/support 23; thresholds 0.9327/0.7736) are
default-operator (`montalbetti_kanasewich_1970`) values, and
`scripts/run_paper0.py` passes no --operator flag." The lead is amending the
registered card text with a dated, outcome-neutral pre-outcome amendment
citing this decision record. All frozen statistics, seeds, thresholds, N,
and controls remain unchanged; the gate stays fully armed (stop-and-report
if the regenerated table lacks the gate cell).
