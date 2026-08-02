VERDICT: FINDINGS-P0/P1

# Paper 0 draft v0.6 — bounded accuracy review of the UCLA-production fold

Scope was limited to the four items named in card `P0-UCLA-PROD-FOLD`: the
new dated production addition in DRAFT_seismica.md § 3.1, the replacement
block in § 5.5 through its coordinate-level bound, new conclusion item (vi),
and the two new NUMBERS.md rows. The registered card, P0-UCLA-PROD and
Amendment 1, the landed record under `history/20260802_ucla_prod/`,
REVIEW_readout.md T5, and NUMBERS.md wording cautions 1/3/4/5 were treated as
binding. No network was used and no source or evidence file was modified.

Counts: P0 = 0; P1 = 1; P2 = 2.

## Blocking finding

### P1-1 — § 5.5 says UCLA deglitching does not suppress “our ridge,” although the registered readout does not establish survival of that ridge

Location: `papers/Paper0/manuscript/DRAFT_seismica.md:775-776`.

Text at issue:

> The hypothesis that in-house deglitching could legitimately suppress our
> ridge is answered on the executable partition: it does not.

Three-part claim-impact test:

1. **Claim affected.** In the draft's established taxonomy, “the ridge” is
   the displaced 662/663.8 s ridge. The sentence therefore makes a direct
   scientific claim that UCLA-on-raw does not suppress that feature, rather
   than the permitted qualitative claim that non-agreement and target-box
   subordination persist.
2. **Concrete causal path.** A reader can reasonably cite this sentence as
   coordinate/feature-level deglitch robustness of the accepted ridge. The
   registered UCLA readout instead moves the global argmax from the MPS
   662.85 s, 0.0 s/deg cell (accepted context 663.80 s, -3.64 s/deg) to
   576.15 s, -10.0 s/deg. The registered readout did not measure or register
   persistence of the accepted ridge as a non-winning neighboring feature.
   Thus “it does not” overstates the evidence and conflicts with the binding
   T5 distinction between qualitative persistence and a deglitch-sensitive
   global coordinate.
3. **Reproducible evidence.** `readout/readout_table.tsv` and both lane CSV
   and validation JSON records give UCLA `576.15/-10.0/0.9002604365771639`
   versus MPS-19 `662.85/0.0/1.0139936603870638`; REVIEW_readout.md T5(c)
   requires the bounded formulation “the qualitative PKiKP disagreement
   remains while its global-argmax coordinate is deglitch-sensitive.” The
   manuscript's own lines 794-799 correctly state that same limitation,
   demonstrating the conflict inside the new block.

This is P1 because it changes the stated answer to the fold's central
deglitch-fidelity question and supplies a realistic path to a materially
false robustness claim. The later table makes the problem detectable but
does not neutralize the categorical sentence.

Mechanically applicable fix: replace the sentence at lines 775-776
with:

> The executable-partition result preserves the qualitative PKiKP
> disagreement and subordination of the published-target maximum under
> UCLA-on-raw provenance, but not the global-argmax coordinate itself.

That wording is consistent with the fold card, LANDING.md, REVIEW_readout.md
T5, and the already-correct qualification later in § 5.5.

## A1 — numerals, rounding, derived quantities, crashes, and partitions

Result: **PASS**. P1-1 is a formulation error, not a numerical error.

The six registered lane cells agree exactly across
`readout/readout_table.tsv`, the selected `paperfaith/envelope/A/
montalbetti_kanasewich_1970/nth_root/20.0` rows in each
`peak_comparison.csv`, and the corresponding `validation_summary.json`
benchmark objects:

| Lane / surface | Exact landed value | Draft rounded value |
| --- | --- | --- |
| UCLA global PKiKP argmax | 576.15, -10.0, 0.9002604365771639 | 576.15 / -10.0 / 0.9003 |
| UCLA published-box maximum | 584.0, -7.070707070707071, 0.7546588107912026 | 584.00 / -7.07 / 0.7547 |
| UCLA PKKP endpoint | 1341.25, -6.96969696969697, 0.30485471145072823 | 1341.25 / -6.97 / 0.3049 |
| MPS-19 global PKiKP argmax | 662.85, 0.0, 1.0139936603870638 | 662.85 / 0.0 / 1.0140 |
| MPS-19 published-box maximum | 584.0, -7.070707070707071, 0.7356290823379646 | 584.00 / -7.07 / 0.7356 |
| MPS-19 PKKP endpoint | 1340.95, -6.96969696969697, 0.24217531234211087 | 1340.95 / -6.97 / 0.2422 |

All six rows have `support_count=19`, `minimum_support=2`, `status=ok`, and
`current_provenance_status=current`.

The three accepted-23 context cells match LANDING.md's registered table and
the read-only canonical `results/tables/peak_comparison.csv` primary rows:

| Surface | Exact canonical value | Draft rounded value |
| --- | --- | --- |
| PKiKP global argmax | 663.8, -3.6363636363636367, 0.9326603162534909 | 663.80 / -3.64 / 0.9327 |
| PKiKP published-box maximum | 601.95, -6.666666666666666, 0.7736156900239739 | 601.95 / -6.67 / 0.7736 |
| PKKP endpoint | 1341.0, -6.96969696969697, 0.21425338569020153 | 1341.00 / -6.97 / 0.2143 |

The exact read-only selector/cross-file check was:

```sh
python3 - <<'PY'
import csv, json
from pathlib import Path
R=Path('/Users/artuskg/GitRepos/MarsQuake/history/20260802_ucla_prod')
sel={'global_PKIKP_argmax':('PKiKP','global','pkikp_global'),
     'published_PKIKP_target_box':('PKiKP','published_target','pkikp_published_target'),
     'PKKP_endpoint':('PKKP','paper_target','pkkp_paper_target')}
tsv=list(csv.DictReader((R/'readout/readout_table.tsv').open(),delimiter='\t'))
for lane in ('ucla_raw','mps_subset'):
    csvrows=list(csv.DictReader((R/f'lanes/{lane}/peak_comparison.csv').open()))
    js=json.loads((R/f'lanes/{lane}/validation_summary.json').read_text())
    for surface,(phase,label,jkey) in sel.items():
        c=next(d for d in csvrows if d['mode']=='paperfaith'
               and d['input_type']=='envelope' and d['norm_variant']=='A'
               and d['polarization_operator']=='montalbetti_kanasewich_1970'
               and d['stack_method']=='nth_root' and d['power_window_s']=='20.0'
               and d['phase']==phase and d['peak_label']==label)
        j=js['benchmark']['peaks'][jkey]
        t=next(d for d in tsv if d['lane']==lane and d['surface']==surface)
        assert (float(c['time_s']),float(c['slowness_sdeg']),float(c['power'])) == \
               (j['time_s'],j['slowness_sdeg'],j['power']) == \
               (float(t['time_s']),float(t['slowness_sdeg']),float(t['power']))
    print(lane, 'CSV_JSON_TSV_MATCH 3/3')
PY
```

Output:

```text
ucla_raw CSV_JSON_TSV_MATCH 3/3
mps_subset CSV_JSON_TSV_MATCH 3/3
```

Independent derivation, always using the MPS-19 value as denominator:

```sh
python3 - <<'PY'
ub,mb=0.7546588107912026,0.7356290823379646
up,mp=0.30485471145072823,0.24217531234211087
print(100*(ub-mb)/mb, round(100*(ub-mb)/mb,1))
print(100*(up-mp)/mp, round(100*(up-mp)/mp,1))
print(abs(1341.25-1340.95), 584.00-601.95)
PY
```

Output:

```text
2.586864618342431 2.6
25.88182854083525 25.9
0.2999999999999545 -17.950000000000045
```

Therefore the quoted 2.6%, 25.9%, 0.30 s, and `601.95 -> 584.00 s`
displacement are correct. The last displacement is properly assigned to
the event-set comparison because both 19-event deglitch lanes land on the
same 584.00 s, -7.070707... cell.

The partition and failure-class check used LANDING.md's frozen lists and
CENSUS.md's failure rows. Its output was:

```text
PARTITION 26 = 22 + 4 ; 22 = 19 + 3
STACK 19 VALIDATION 3 EXCLUDED 4 ['S0784a', 'S1015f', 'S1197a', 'S1222a']
S1197a: aa(_,2), empty glitch list indexed
S1222a: aa(_,2), empty glitch list indexed
S0784a: data(0), zero subscript at a detection edge
S1015f: filtfilt length greater than 6, too-short data-gap segment
```

This verifies the date, four-of-26 count, two empty-list crashes, the other
two named crash classes, the 22-event executable partition, and its 19-stack
+ 3-validation composition. Both lane summaries independently contain 22
expected events and 22 completed event records; the terminal counts are
`ucla_unverified: 22` and `succeeded_mps_only: 22`.

## A2 — compliance with binding T5 formulations

Result: **FAIL (P1-1)** for lines 775-776. All other T5 requirements pass.

- Neither the scoped § 5.5 block nor conclusion (vi) uses “persists
  unchanged,” “bistable,” or the blanket “deglitch-robust at the registered
  cells.”
- The exact approved branch statement appears at lines 798-799: “branch-
  fragile to both event removal and deglitch method.”
- The published-box result alone is called cell-identical. PKKP is called
  same-slowness and 0.30 s near-concordant, and the 25.9% power difference
  and absence of a registered tolerance are disclosed.
- Lines 803-807 expressly reserve `mps_ucla_verified`, label the UCLA lane
  `ucla_unverified`, limit the comparison to 19 rather than 23 events, and
  say persistence is qualitative with coordinate-level robustness only
  where stated cell-exactly.
- Lines 791-799 and conclusion (vi) correctly state qualitative persistence
  alongside a deglitch-sensitive global coordinate. P1-1 is the sole
  contradictory sentence.

The bounded phrase check was:

```sh
sed -n '768,807p' /Users/artuskg/GitRepos/MarsQuake/papers/Paper0/manuscript/DRAFT_seismica.md \
  | rg 'persists unchanged|bistable|deglitch-robust at the registered cells|branch-fragile to both event removal and deglitch method|ucla_unverified|mps_ucla_verified|qualitative|coordinate-level'
```

## A3 — registered adverse-control content

Result: **PASS**.

- Terminal `ucla_unverified` and the reserved strict
  `mps_ucla_verified` attestation are both explicit in §§ 3.1 and 5.5.
- § 3.1 states that four shipped-code failures produced an a-priori frozen
  22-event partition of 19 stack plus 3 validation events; § 5.5 labels the
  comparison as the 19-event sub-stack rather than the accepted 23-event
  stack.
- Persistence is explicitly qualitative. The global coordinate is explicitly
  deglitch-sensitive.
- The adv-A JSON reproduces S1197a's `aa(_,2)` failure with return code 1,
  terminal `succeeded_mps_only`, while the sole allowed status is
  `ucla_unverified`; LANDING.md records the resulting nonzero allow-list
  rejection.

Exact gate/control check:

```sh
python3 - <<'PY'
import json
from pathlib import Path
R=Path('/Users/artuskg/GitRepos/MarsQuake/history/20260802_ucla_prod')
for lane in ('ucla_raw','mps_subset'):
    s=json.loads((R/f'lanes/{lane}/deglitch_run_summary.json').read_text())
    m=json.loads((R/f'lanes/{lane}/paper0_run_manifest.json').read_text())
    print(lane,s['allowed_statuses'],s['status_counts'],len(s['expected_event_ids']),
          len(s['events']),m['execution_status'],m['status'],m['validation_status'],
          m['deglitch_attestation']['verified_only_gate'])
a=json.loads((R/'controls/adv_A_S1197a.deglitch.json').read_text())
print('adv-A',a['event_id'],a['mps']['status'],a['ucla']['status'],
      a['ucla']['returncode'],a['overall_status'],'aa(_,2)' in a['ucla']['stderr'])
PY
```

Output:

```text
ucla_raw ['ucla_unverified'] {'ucla_unverified': 22} 22 22 succeeded succeeded passed mps_ucla_verified
mps_subset ['succeeded_mps_only'] {'succeeded_mps_only': 22} 22 22 succeeded succeeded passed mps_ucla_verified
adv-A S1197a identity_passthrough failed 1 succeeded_mps_only True
```

## A4 — cross-references, conclusion list, and wording cautions

Result: **PASS WITH P2-1**.

- § 3.1 points forward to § 5.5 at line 195; § 5.5 points back to the
  dated § 3.1 additions at lines 770 and 773.
- The leave-one-out reference is correctly § 4.3.
- Conclusion (vi) agrees with the bounded § 5.5 result: qualitative
  non-agreement and target-box subordination remain, the published-box cell
  is identical between the two 19-event lanes, and the global coordinate is
  deglitch-sensitive.
- The new material never calls 601.95 s the published pair, never describes
  the 1-s ridge band as another reader, and keeps the 576.15 s domain-edge
  location distinct from the two LOO branch families. It does not merge that
  new location into the target-box maximum or shallow 602-family branch.
- Items (i) through (vi) are all present in order. The only list defect is
  the non-blocking duplicated conjunction recorded as P2-1 below.

## A5 — NUMBERS.md trace rows, paths, and hashes

Result: **PASS WITH P2-2**.

The named landed files all exist. Recomputed hashes and manifest entries
match the NUMBERS.md prefixes:

```sh
shasum -a 256 \
  /Users/artuskg/GitRepos/MarsQuake/history/20260802_ucla_prod/lanes/ucla_raw/peak_comparison.csv \
  /Users/artuskg/GitRepos/MarsQuake/history/20260802_ucla_prod/lanes/mps_subset/peak_comparison.csv
rg -n 'e9fe30fb|73410b11|265153e6|dc9e579a' \
  /Users/artuskg/GitRepos/MarsQuake/history/20260802_ucla_prod/LANDING.md \
  /Users/artuskg/GitRepos/MarsQuake/history/20260802_ucla_prod/lanes/{ucla_raw,mps_subset}/SHA256SUMS.tsv
```

Checked full values:

```text
pos-A S0235b       e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db
pos-B S0235b       73410b11b144b944872c7a1acfce9cb5d1141ea4e35bbde95880a56180207cff
ucla peak table    265153e62b1442c572d3d1fa91eaf128ba3f895add18ac97005f5fd19e1aa2c8
mps peak table     dc9e579af59d818769dbea277f8f1ef8e1b2c3ba7b9d4054085a61fe6bb21eab
```

The row-94 sources `LANDING.md`, `CENSUS.md`, and
`review/REVIEW_readout.md` exist and support the production/control row.
The row-95 lane files and hashes support all six new lane cells. LANDING.md
supports the three accepted-23 context cells, which also retain their
earlier canonical NUMBERS.md traces. P2-2 records a path/source precision
repair; no numeral is unsupported or incorrect.

## A6 — MPS-only headline-result standing

Result: **PASS**, subject to fixing P1-1.

The accepted MPS-23 values remain explicitly labeled “Accepted MPS
(23-event stack, context).” The UCLA-on-raw material is presented in § 5.5
as a bounded 19-event limitation/robustness comparison, with
`ucla_unverified` standing and no equivalence upgrade. Conclusion (vi)
states only the qualitative robustness result and does not substitute the
UCLA coordinates or powers for the paper's MPS-only headline measurements.
Thus the § 3.1 sentence that headline results remain MPS-only is compatible
with the fold. P1-1 must nevertheless be fixed because it overclaims what
that robustness comparison establishes.

## P2 list

### P2-1 — duplicated conclusion-list conjunction

At DRAFT_seismica.md:904 and :909, the insertion leaves “; and (v) ...;
and (vi)”. This is a list-coherence/prose defect with only one reasonable
scientific reading and is non-blocking. Mechanical fix: delete `and ` before
`(v)` at line 904, leaving the single final conjunction before `(vi)`.

### P2-2 — NUMBERS.md row 95 over-compresses the nine-cell provenance and uses a non-resolving review-file shorthand

NUMBERS.md:95 says “nine cells verbatim from the registered readout,” but
`readout/readout_table.tsv` contains the six new lane rows; the three
accepted-23 context cells are supplied by LANDING.md's registered table and
their pre-existing canonical traces. The same source cell refers to bare
`REVIEW_readout.md`, while the landed file is
`review/REVIEW_readout.md`. The values are correct, so this is a bounded
traceability precision issue. Mechanical fix: change the lead-in to “six
registered lane-readout cells plus three accepted-23 context cells”; add
`history/20260802_ucla_prod/LANDING.md` to the evidence cell; and replace the
bare review filename with
`history/20260802_ucla_prod/review/REVIEW_readout.md`.

## Closing

Every scoped numeral, rounded form, crash attribution, partition count,
terminal count, selected cell, derived percentage/offset/displacement, and
requested hash prefix reproduces from the binding records. The adverse
bounds, cross-references, three-feature discipline, distinct new branch,
and MPS-only headline standing are otherwise preserved. I withhold
countersign solely for P1-1: the categorical “does not suppress our ridge”
sentence exceeds the registered qualitative result and conflicts with the
deglitch-sensitive argmax readout. Apply that one blocking wording repair;
the two listed P2 edits are mechanically bounded and do not block.
