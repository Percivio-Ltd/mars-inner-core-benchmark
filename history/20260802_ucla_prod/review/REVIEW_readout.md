VERDICT: COUNTERSIGN

# UCLA-ON-RAW lane — bounded scientific review

Card: `P0-UCLA-PROD`, Amendment 1. Scope: lead execution and the registered same-cell readout only. I did not re-review the accepted round-3/round-4 implementation. I applied the repository's P0/P1 three-part claim-impact test and severity ratchet. No P0 or P1 is supported. Two bounded interpretation-wording P2 observations are recorded below and do not withhold this countersign.

The authorities were read in the prescribed order: the registered card and Amendment 1, runbook §§4/5/7, the 2026-08-02 execution/readout record including commits `581819c2` and `ab9ae0ca`, and `AGENTS.md` review policy.

## T1 — archive-manifest verification: PASS

The recomputed manifest digests equal the two pinned digests. The `.sha256` seal files contain the same values. `ucla_raw/SHA256SUMS.tsv` has 3,179 listed product entries and `mps_subset/SHA256SUMS.tsv` has 1,503. Each lane root additionally contains the manifest and its `.sha256` seal, explaining filesystem totals two greater than the listed-product counts.

Exact digest command and output:

```sh
/usr/bin/shasum -a 256 worktree/lanes/ucla_raw/SHA256SUMS.tsv worktree/lanes/mps_subset/SHA256SUMS.tsv
```

```text
b808d834f50b99bcea44ad350df5e2e35a8033c53da51f1fd525ab6987c39498  worktree/lanes/ucla_raw/SHA256SUMS.tsv
a4ffa6fc7ea5df84e9b7f377e1cd2f83afbb6687c283fcb0402f4a2937dd9870  worktree/lanes/mps_subset/SHA256SUMS.tsv
```

Seal-file command and output:

```sh
cat worktree/lanes/ucla_raw/SHA256SUMS.tsv.sha256 worktree/lanes/mps_subset/SHA256SUMS.tsv.sha256
```

```text
b808d834f50b99bcea44ad350df5e2e35a8033c53da51f1fd525ab6987c39498	SHA256SUMS.tsv
a4ffa6fc7ea5df84e9b7f377e1cd2f83afbb6687c283fcb0402f4a2937dd9870	SHA256SUMS.tsv
```

I spot-verified five manifest-listed files per lane, checking both SHA-256 and byte size. Exact command:

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import hashlib
from pathlib import Path

root = Path('/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes')
checks = [
    'data/deglitched/S0235b.mseed',
    'data/deglitched/deglitch_run_summary.json',
    'results/validation/paper0_run_manifest.json',
    'results/validation/validation_summary.json',
    'results/tables/peak_comparison.csv',
]
for lane in ('ucla_raw', 'mps_subset'):
    lane_root = root / lane
    entries = {}
    for line in (lane_root / 'SHA256SUMS.tsv').read_text().splitlines():
        digest, size, rel = line.split('\t', 2)
        entries[rel] = (digest, int(size))
    print(f'{lane}: manifest_entries={len(entries)}')
    for rel in checks:
        expected_hash, expected_size = entries[rel]
        payload = (lane_root / rel).read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        actual_size = len(payload)
        assert (actual_hash, actual_size) == (expected_hash, expected_size)
        print(f'PASS {rel} sha256={actual_hash} bytes={actual_size}')
PY
```

Output:

```text
ucla_raw: manifest_entries=3179
PASS data/deglitched/S0235b.mseed sha256=e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db bytes=1253376
PASS data/deglitched/deglitch_run_summary.json sha256=8ec57edbea1706dd9a873476f3f01ad685810f5cb0e4a7b8089d8b7715b475a6 bytes=10681
PASS results/validation/paper0_run_manifest.json sha256=ff93cd0a008493da5c9194b4a54841bfa50307998d896a916e6108982f2ea07f bytes=59439
PASS results/validation/validation_summary.json sha256=d2b21fb569184078e9869dfb42606bb51eac11d6403352c61abfc824f6709c23 bytes=36517
PASS results/tables/peak_comparison.csv sha256=265153e62b1442c572d3d1fa91eaf128ba3f895add18ac97005f5fd19e1aa2c8 bytes=74236
mps_subset: manifest_entries=1503
PASS data/deglitched/S0235b.mseed sha256=73410b11b144b944872c7a1acfce9cb5d1141ea4e35bbde95880a56180207cff bytes=691200
PASS data/deglitched/deglitch_run_summary.json sha256=ccff0c9a92c423e1991a9a6215989f3c3e5fac1d140c81f2e156f37a52b7d441 bytes=10196
PASS results/validation/paper0_run_manifest.json sha256=8af8062344fd3c4ad7a395c7266a7538725fb9ebb9ef52df189a8d2276d5c17c bytes=58609
PASS results/validation/validation_summary.json sha256=da6464d2dce5f7c9ceb73b9cf172762c4b94296fa60340cbd5b6d90be69be4e8 bytes=36745
PASS results/tables/peak_comparison.csv sha256=dc9e579af59d818769dbea277f8f1ef8e1b2c3ba7b9d4054085a61fe6bb21eab bytes=74559
```

## T2 — verbatim registered readout: PASS

I ran runbook §7's script verbatim with the prescribed interpreter. Every assertion passed, including the CSV-to-validation-JSON equality assertions. Exact command:

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import csv
import json
from pathlib import Path

root = Path("/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree")
lanes = {
    "ucla_raw": (root / "lanes/ucla_raw", {"ucla_unverified": 22}),
    "mps_subset": (root / "lanes/mps_subset", {"succeeded_mps_only": 22}),
}
surfaces = {
    ("PKiKP", "global"): ("global_PKIKP_argmax", "displaced_ridge"),
    ("PKiKP", "published_target"): ("published_PKIKP_target_box", "published_PKIKP_box"),
    ("PKKP", "paper_target"): ("PKKP_endpoint", "PKKP_target"),
}

print("lane\tsurface\ttime_s\tslowness_sdeg\tpower\tstatus\tcurrent_provenance_status")
for lane, (lane_root, expected_counts) in lanes.items():
    manifest = json.loads((lane_root / "results/validation/paper0_run_manifest.json").read_text())
    assert manifest["execution_status"] == "succeeded"
    assert manifest["validation_status"] == "passed"
    assert manifest["deglitch_attestation"]["status_counts"] == expected_counts
    assert manifest["deglitch_attestation"]["n_events"] == 22

    rows = list(csv.DictReader((lane_root / "results/tables/peak_comparison.csv").open(newline="")))
    selected = {}
    for row in rows:
        identity = (
            row["mode"] == "paperfaith"
            and row["input_type"] == "envelope"
            and row["norm_variant"] == "A"
            and row["stack_method"] == "nth_root"
            and float(row["power_window_s"]) == 20.0
        )
        key = (row["phase"], row["peak_label"])
        if identity and key in surfaces:
            assert key not in selected
            selected[key] = row
    assert set(selected) == set(surfaces)

    summary = json.loads((lane_root / "results/validation/validation_summary.json").read_text())
    endpoints = {row["endpoint_label"]: row for row in summary["benchmark"]["named_endpoint_rows"]}
    for key, (surface, endpoint_label) in surfaces.items():
        row = selected[key]
        endpoint = endpoints[endpoint_label]
        for field in ("time_s", "slowness_sdeg", "power"):
            assert float(row[field]) == float(endpoint[field]), (lane, surface, field)
        print(
            lane,
            surface,
            row["time_s"],
            row["slowness_sdeg"],
            row["power"],
            row["status"],
            row["current_provenance_status"],
            sep="\t",
        )
PY
```

Output:

```text
lane	surface	time_s	slowness_sdeg	power	status	current_provenance_status
ucla_raw	global_PKIKP_argmax	576.15	-10.0	0.9002604365771639	ok	current
ucla_raw	published_PKIKP_target_box	584.0	-7.070707070707071	0.7546588107912026	ok	current
ucla_raw	PKKP_endpoint	1341.25	-6.96969696969697	0.30485471145072823	ok	current
mps_subset	global_PKIKP_argmax	662.85	0.0	1.0139936603870638	ok	current
mps_subset	published_PKIKP_target_box	584.0	-7.070707070707071	0.7356290823379646	ok	current
mps_subset	PKKP_endpoint	1340.95	-6.96969696969697	0.24217531234211087	ok	current
```

This matches the ledger's six cells cell-for-cell at its recorded display precision: `576.15/-10.0/0.9003`, `584.00/-7.0707/0.7547`, `1341.25/-6.9697/0.3049`, `662.85/0.0/1.0140`, `584.00/-7.0707/0.7356`, and `1340.95/-6.9697/0.2422`. All six status cells are `ok` and all six provenance cells are `current`, as recorded.

## T3 — §§4/5 gates, terminal counts, and controls: PASS

The archived JSON fields satisfy every specified pass-1 and pass-2 gate. Exact field-quotation command:

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import json
from collections import Counter
from pathlib import Path
root = Path('/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes')
for lane in ('ucla_raw', 'mps_subset'):
    lane_root = root / lane
    summary = json.loads((lane_root / 'data/deglitched/deglitch_run_summary.json').read_text())
    manifest = json.loads((lane_root / 'results/validation/paper0_run_manifest.json').read_text())
    att = manifest['deglitch_attestation']
    stages = manifest['stages']
    quoted = {
        'summary': {'run_status': summary['run_status'], 'event_rows': len(summary['events']), 'status_counts': summary['status_counts']},
        'manifest': {key: manifest[key] for key in ('execution_status', 'status', 'validation_status')},
        'deglitch_attestation': {key: att[key] for key in ('status_counts', 'n_events', 'attestation_level', 'accepted_partial_lane_by_design')},
        'stages': {
            'n': len(stages),
            'status_counts': dict(Counter(stage['status'] for stage in stages)),
            'non_succeeded': [stage['label'] for stage in stages if stage['status'] != 'succeeded'],
            'returncode_counts': dict(Counter(str(stage['returncode']) for stage in stages)),
        },
    }
    assert quoted['stages']['non_succeeded'] == []
    print(lane + '=' + json.dumps(quoted, sort_keys=True, separators=(',', ':')))
PY
```

Output:

```text
ucla_raw={"deglitch_attestation":{"accepted_partial_lane_by_design":false,"attestation_level":"ucla_unverified","n_events":22,"status_counts":{"ucla_unverified":22}},"manifest":{"execution_status":"succeeded","status":"succeeded","validation_status":"passed"},"stages":{"n":24,"non_succeeded":[],"returncode_counts":{"0":23,"2":1},"status_counts":{"succeeded":24}},"summary":{"event_rows":22,"run_status":"complete","status_counts":{"ucla_unverified":22}}}
mps_subset={"deglitch_attestation":{"accepted_partial_lane_by_design":true,"attestation_level":"succeeded_mps_only","n_events":22,"status_counts":{"succeeded_mps_only":22}},"manifest":{"execution_status":"succeeded","status":"succeeded","validation_status":"passed"},"stages":{"n":24,"non_succeeded":[],"returncode_counts":{"0":23,"2":1},"status_counts":{"succeeded":24}},"summary":{"event_rows":22,"run_status":"complete","status_counts":{"succeeded_mps_only":22}}}
```

Thus both summaries are `complete`, both contain exactly 22 event rows with the required sole terminal status, both manifests are `succeeded/succeeded/passed`, and all 24 stage records in each lane have `status="succeeded"`. The terminal validation stage's recorded return code is 2 in each lane, while its normalized stage status is `succeeded` and the manifest's `validation_status` is `passed`; this is consistent with the already-recorded designed strict-gate signal, not a stage-status failure.

I also independently repeated the two byte-comparison positive controls. Exact command and output:

```sh
if cmp -s worktree/lanes/ucla_raw/data/deglitched/S0235b.mseed worktree/lead_controls/raw_census/S0235b/S0235b_raw_ucla.mseed; then echo 'pos-A cmp: PASS'; else echo 'pos-A cmp: FAIL'; fi
/usr/bin/shasum -a 256 worktree/lanes/ucla_raw/data/deglitched/S0235b.mseed worktree/lead_controls/raw_census/S0235b/S0235b_raw_ucla.mseed
if cmp -s worktree/lanes/mps_subset/data/deglitched/S0235b.mseed /Users/artuskg/GitRepos/MarsQuake/data/deglitched/S0235b.mseed; then echo 'pos-B cmp: PASS'; else echo 'pos-B cmp: FAIL'; fi
/usr/bin/shasum -a 256 worktree/lanes/mps_subset/data/deglitched/S0235b.mseed /Users/artuskg/GitRepos/MarsQuake/data/deglitched/S0235b.mseed
```

```text
pos-A cmp: PASS
e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db  worktree/lanes/ucla_raw/data/deglitched/S0235b.mseed
e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db  worktree/lead_controls/raw_census/S0235b/S0235b_raw_ucla.mseed
pos-B cmp: PASS
73410b11b144b944872c7a1acfce9cb5d1141ea4e35bbde95880a56180207cff  worktree/lanes/mps_subset/data/deglitched/S0235b.mseed
73410b11b144b944872c7a1acfce9cb5d1141ea4e35bbde95880a56180207cff  /Users/artuskg/GitRepos/MarsQuake/data/deglitched/S0235b.mseed
```

The ledger records adv-A before the affected readout: S1197a reproduced the registered `aa(_,2)` failure; input restoration was byte-exact; the terminal `succeeded_mps_only` was rejected by the lane allow-list. No contradictory archive or manifest evidence was found.

## T4 — registration discipline and selector identity: PASS

The Git record orders registration before execution/readout and leaves the registered card unchanged through readout. Exact ordering command and output:

```sh
git -C /Users/artuskg/GitRepos/MarsQuake log --reverse --ancestry-path --format='%h %cI %s' 102264e4^..ab9ae0ca -- docs/research_pipeline.md CONTINUITY-paper0.md
```

```text
102264e4 2026-08-02T07:42:46+02:00 Land raw census (22/26 executable); register P0-UCLA-PROD amendment 1 (UCLA-on-raw subset lane)
29e23e94 2026-08-02T07:49:01+02:00 Record Amendment 1 wiring dispatch and allow-status pre-derivation
087070b6 2026-08-02T08:10:28+02:00 Record wiring-round acceptance, forwarding-defect adjudication, fix dispatch
536dcf71 2026-08-02T08:25:33+02:00 Record fix-round acceptance, staging, adv-A pass, pass-1 launch
734d7875 2026-08-02T08:51:09+02:00 Record pass-1 kill, quarantine, detached attempt-2 relaunch
0591fafd 2026-08-02T12:33:27+02:00 Record gnuplot deadlock diagnosis, GNUTERM fix, attempt-3 relaunch
581819c2 2026-08-02T13:04:01+02:00 Record pass-1 completion, pos-A, ucla_raw archive, pass-2 launch
ab9ae0ca 2026-08-02T13:54:19+02:00 Record pass-2 completion, pos-B, and registered same-cell readout
```

Exact card-drift command:

```sh
git -C /Users/artuskg/GitRepos/MarsQuake diff --name-status 102264e4..ab9ae0ca -- docs/research_pipeline.md
```

Output: `<no output>`.

The exact registered selector and the three one-to-one surface mappings were independently asserted in both archives. Command:

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import csv, json
from pathlib import Path
root = Path('/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes')
selector = {'mode':'paperfaith','input_type':'envelope','norm_variant':'A','stack_method':'nth_root','power_window_s':20.0}
mapping = {
    ('PKiKP','global'): ('displaced_ridge','pkikp_global','550-700s'),
    ('PKiKP','published_target'): ('published_PKIKP_box','pkikp_published_target','584-624s'),
    ('PKKP','paper_target'): ('PKKP_target','pkkp_paper_target','1320-1360s'),
}
print('selector=' + json.dumps(selector, sort_keys=True))
for lane in ('ucla_raw','mps_subset'):
    lane_root = root / lane
    csv_rows = list(csv.DictReader((lane_root/'results/tables/peak_comparison.csv').open(newline='')))
    endpoint_rows = {r['endpoint_label']: r for r in json.loads((lane_root/'results/validation/validation_summary.json').read_text())['benchmark']['named_endpoint_rows']}
    for key, (endpoint_label, registered_key, window) in mapping.items():
        rows = [r for r in csv_rows if r['mode']==selector['mode'] and r['input_type']==selector['input_type'] and r['norm_variant']==selector['norm_variant'] and r['stack_method']==selector['stack_method'] and float(r['power_window_s'])==selector['power_window_s'] and (r['phase'],r['peak_label'])==key]
        assert len(rows)==1
        row, endpoint = rows[0], endpoint_rows[endpoint_label]
        assert (endpoint['registered_key'],endpoint['phase'],endpoint['peak_label'],endpoint['window'],endpoint['primary_lane_variant']) == (registered_key,key[0],key[1],window,'A')
        print(f'{lane}\t{key[0]},{key[1]}\t{endpoint_label}\t{registered_key}\t{window}\tsupport={row["support_count"]}/{row["minimum_support"]}')
PY
```

Output:

```text
selector={"input_type": "envelope", "mode": "paperfaith", "norm_variant": "A", "power_window_s": 20.0, "stack_method": "nth_root"}
ucla_raw	PKiKP,global	displaced_ridge	pkikp_global	550-700s	support=19/2
ucla_raw	PKiKP,published_target	published_PKIKP_box	pkikp_published_target	584-624s	support=19/2
ucla_raw	PKKP,paper_target	PKKP_target	pkkp_paper_target	1320-1360s	support=19/2
mps_subset	PKiKP,global	displaced_ridge	pkikp_global	550-700s	support=19/2
mps_subset	PKiKP,published_target	published_PKIKP_box	pkikp_published_target	584-624s	support=19/2
mps_subset	PKKP,paper_target	PKKP_target	pkkp_paper_target	1320-1360s	support=19/2
```

These are exactly the card's global PKiKP argmax, published PKiKP target-box maximum, and PKKP endpoint. All six rows have the frozen 19-event support and minimum support 2.

Conclusion on outcome blindness: no outcome-sensitive choice is recorded after inspection of an affected outcome. Amendment 1 froze the 22/19 partition, two lanes, selectors, cells, controls, and comparison rule in `102264e4`. The execution then followed controls/gates, archive sealing, and finally readout in `ab9ae0ca`. The `GNUTERM=dumb` runner-environment correction occurred before surface inspection, was followed by a detached positive-control rerun that was byte-identical, and is already a P2 baseline item; it supplies no new basis for escalation.

## T5 — Interpretation audit: PASS WITH P2 PRECISION OBSERVATIONS

### (a) Published-box displacement: supported

The event-set attribution is supported within the registered comparison. The relevant causal comparison is MPS-23 versus MPS-19: the deglitch method and accepted configuration are held fixed while the event subset changes, and the maximum moves from `601.95/-6.667` to `584.00/-7.0707`. The UCLA-19 lane independently lands on the same `584.00/-7.0707` cell. Thus the observed 23-to-19 displacement is an event-set effect and not a UCLA-versus-MPS effect among these two registered 19-event lanes. This does not make a claim about untested deglitch methods or event sets.

### (b) Global-argmax branch fragility: core claim supported; wording P2

The six cells directly demonstrate deglitch-method sensitivity of the global argmax at the fixed 19-event subset: `576.15/-10.0` under UCLA-on-raw versus `662.85/0.0` under MPS. The already-recorded P0-LOO-INFLUENCE result separately demonstrates event-removal fragility: six single-event removals changed the 662-family global branch to the 602-family. It is therefore supported to say the new flip is consistent with the already documented general fragility of the global argmax.

P2 precision observation: the stronger phrase “the global argmax is bistable under small perturbations, and the deglitch method is one such perturbation” is not fully established by these records. P0-LOO documents 662↔602-family flips, whereas this readout adds a 576.15 s domain-edge branch; “bistable” is consequently too narrow across the combined record, and no registered metric classifies the MPS-to-UCLA operator change as “small.” A bounded formulation is: “the global argmax is branch-fragile to both event removal and deglitch method.” This is a prose-precision P2: the table already discloses the actual cells, and it does not alter the scientific result.

### (c) Net displaced-ridge statement: qualitative result supported; exact-cell robustness wording P2

The qualitative Paper 0 non-agreement persists under UCLA-on-raw: the UCLA global maximum remains distinct from the published-target row and has greater power (`0.900260...` versus `0.754659...`), so the published-target maximum remains subordinate. The published-box maximum is exactly same-cell across the two 19-event lanes. The PKKP endpoint is also close in coordinate space, with identical slowness and a disclosed 0.30 s time offset.

P2 precision observation: “persists unchanged” is safe only if “unchanged” refers to the qualitative disagreement/subordination verdict, not to the displaced-ridge coordinate, which changes materially from the accepted/MPS late branch to the UCLA 576.15 s domain-edge branch. Likewise, “the two claim-referenced target surfaces are deglitch-robust at the registered cells” overstates the preregistered same-cell result for PKKP: its times are `1341.25` and `1340.95`, so it is not an exact same-cell time result, and its powers are `0.3048547` and `0.2421753` (about a 25.9% relative difference using MPS as denominator). No robustness tolerance was registered. A precise formulation is: “the published-box maximum is exact same-cell; PKKP is same-slowness and 0.30 s near-concordant; the qualitative PKiKP disagreement remains while its global-argmax coordinate is deglitch-sensitive.” Again this is P2 because the exact differences are already disclosed and the central non-agreement conclusion remains supported.

The bounded recorded evidence used for this audit was obtained with:

```sh
sed -n '872,887p' /Users/artuskg/GitRepos/MarsQuake/docs/research_pipeline.md; sed -n '1413,1440p' /Users/artuskg/GitRepos/MarsQuake/CONTINUITY-paper0.md
```

Relevant exact output:

```text
- Status: done (2026-07-26). Positive control exact; determinism
  byte-identical; M1 MATERIAL — six of 23 removals flip the branch to
  the 602-family (S0325a, S0474a, S0864a, S1012d, S1022a, S1039b); the
  662-ridge is global only with all six present.

- Interpretation (both registered directions): (a) Deglitch-method
  dimension at the fixed 19-event stack — the published-PKiKP-box
  maximum lands in the IDENTICAL native-grid cell under UCLA-on-raw
  and MPS (584.00 s, −7.0707 s/deg; powers differ 2.6% relative);
  the PKKP endpoint sits at the same slowness cell with a 0.30 s
  time offset (small against the 20 s power window). The global
  PKiKP argmax flips branch: UCLA-on-raw selects the early
  domain-edge branch (576.15 s, −10.0 s/deg) while MPS-subset
  selects the late branch (662.85 s, 0.0 s/deg) — consistent with
  the six-event branch fragility demonstrated by P0-LOO-INFLUENCE
  (75ca5db4/4a5f733e): the global argmax is bistable under small
  perturbations, and the deglitch method is one such perturbation.
  (b) Event-set dimension (MPS-19 vs accepted MPS-23, context) —
  the box maximum displaces 601.95 → 584.00 s with both deglitch
  lanes agreeing exactly at 19 events, so that displacement is an
  event-set effect, not a deglitch-method effect; the PKKP endpoint
  is essentially event-set-invariant; the global argmax keeps its
  ~663 s time but moves slowness −3.636 → 0.0. Net scientific
  statement for Paper 0: the benchmark's displaced-ridge
  disagreement with the published PKiKP coordinates persists
  unchanged under UCLA deglitch provenance on raw data — the two
  claim-referenced target surfaces are deglitch-robust at the
  registered cells, and the only deglitch-sensitive surface is the
  already-documented fragile global argmax.
```

## T6 — bounded inspection and canonical-checkout isolation: PASS

This review inspected no bootstrap values, bootstrap NPZ payloads, `bootstrap_picks.csv` values, images, neighboring peaks, or alternate outcomes. The readout used only the exact two artifacts per lane named in §7 and only the registered selector/surface fields. T1 read manifest text and computed hashes; it did not open scientific values in unregistered products. The ledger explicitly records first surface inspection only after gates, controls, and archive sealing, and says bootstrap products remained uninspected. I found no contrary record.

The archived run manifests contain no canonical-checkout `data/deglitched` or `results` path. Exact command and output:

```sh
rg -n '/Users/artuskg/GitRepos/MarsQuake/(data/deglitched|results)(/|"|$)' worktree/lanes/ucla_raw/results/validation/paper0_run_manifest.json worktree/lanes/mps_subset/results/validation/paper0_run_manifest.json
```

```text
<no matches>
```

I checked canonical working state, committed path changes between registration and readout, and post-registration file mtimes. Exact command:

```sh
git -C /Users/artuskg/GitRepos/MarsQuake status --short --untracked-files=all -- data/deglitched results; git -C /Users/artuskg/GitRepos/MarsQuake diff --name-status 102264e4..ab9ae0ca -- data/deglitched results; find /Users/artuskg/GitRepos/MarsQuake/data/deglitched /Users/artuskg/GitRepos/MarsQuake/results -type f -newermt '2026-08-02 07:42:46' -print
```

Output: `<no output>`. Thus there are no tracked or untracked canonical changes in those scopes, no committed changes to those paths between registration and readout, and no files there newer than Amendment 1's registration time. Pos-B's independent byte comparison additionally confirms the canonical S0235b reference remained the pinned accepted product.

## P2 observations and severity ratchet

The four supplied baseline P2s remain P2: (1) `bootstrap_type1`'s bare cwd-relative `--table` default; (2) `succeeded_mps_only` enum reuse for identity-without-UCLA terminals; (3) the need to pin the gnuplot terminal for reproducibility; and (4) the recorded `parameters_sha256` supersession `98382efd…` to `e79c60d7…` after the runner environment edit. I found no new concrete, demonstrated claim-impact evidence that would permit escalation under the ratchet.

Two new bounded P2 wording observations are recorded in T5: replace the combined-record “bistable/small perturbation” characterization with general branch fragility, and distinguish the exact same-cell published-box result from the PKKP same-slowness/0.30 s near-concordance and from the deglitch-sensitive global coordinate. Neither supplies any part of the three-part P0/P1 test.

## Closing

Both sealed archives are internally consistent; the registered gates, terminal counts, stage statuses, and positive controls reproduce; the verbatim §7 readout passes and matches the ledger; registration and archive/readout ordering preserve outcome blindness; and the canonical checkout is untouched in the specified scopes. The six cells support the bounded event-set and qualitative non-agreement conclusions. With the two non-blocking wording precisions recorded above, I COUNTERSIGN the lead execution and registered same-cell readout for `P0-UCLA-PROD`, Amendment 1.
