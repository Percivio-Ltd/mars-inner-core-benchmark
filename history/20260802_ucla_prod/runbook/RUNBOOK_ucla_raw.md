# UCLA-on-raw Amendment 1 production runbook

This runbook is for the lead operator. It does not authorize a background job,
network access, a commit, or a write to
`/Users/artuskg/GitRepos/MarsQuake`. Run every command from
`/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree`. Stop before any
production command unless `git rev-parse HEAD` prints
`98a2160e7c43cee9f378891d5fb149562fbd3871`.

## Registered scientific item

- Paper 0 uncertainty: whether the registered global PKiKP maximum, published
  PKiKP target-box maximum, and PKKP target endpoint change when the frozen
  19-event stack is prepared by UCLA-on-raw instead of MPS deglitching.
- Next artifact: two independently archived 22-event product trees,
  `lanes/ucla_raw/` and `lanes/mps_subset/`, from the same Amendment 1 event
  table and raw files.
- Exact inputs: `manifest/event_table_ucla22.csv`, the 22 corresponding
  `data/raw/S*.mseed` files, `manifest/data_manifest.json`, the MQS V14
  catalog, the worktree inventory, and the already resident model directories.
- Smallest production command: each `scripts/run_paper0.py` command below.
- Positive controls: pos-A (UCLA S0235b byte identity) and pos-B (MPS S0235b
  byte identity).
- Adverse control: adv-A, S1197a identity+UCLA, must fail UCLA with
  `aa(_,2): out of bound` and terminate as `succeeded_mps_only`, which the UCLA
  pass allow-list rejects.
- Stop condition: stop without starting or overwriting the next lane if a
  staging hash differs, adv-A does not reach its registered terminal, a pass
  returns nonzero, its event count/status differs from the required all-event
  status, a positive-control hash differs, or current-provenance/subset gates
  fail. Preserve the failing tree in place for lead adjudication.

The subset table contains 22 events: 19 `set=vespagram` events and the same 3
`set=validation` events as the full table. The only four excluded events are
S0784a, S1015f, S1197a, and S1222a. They are excluded operationally by being
absent from `data/raw_ucla22/`; the deglitch batch enumerates only
`--in-dir/*.mseed` (`scripts/02_preprocess/deglitch_mps_ucla.py:674-689`).

## 1. Stage and verify the 22 raw files

The staging directory must be new. Do not reuse or clean an existing
`data/raw_ucla22/`; stop and adjudicate it instead. This command looks up each
digest using the required manifest key `data/raw/<event>.mseed`, verifies the
canonical worktree source, copies it, verifies the staged copy, asserts the
four exact exclusions, and prints the verification table.

```sh
cd /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree
test "$(git rev-parse HEAD)" = 98a2160e7c43cee9f378891d5fb149562fbd3871
test ! -e data/raw_ucla22

/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import csv
import hashlib
import json
import shutil
from pathlib import Path

root = Path("/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree")
table = root / "manifest/event_table_ucla22.csv"
full_table = root / "manifest/event_table.csv"
manifest = root / "manifest/data_manifest.json"
stage = root / "data/raw_ucla22"

rows = list(csv.DictReader(table.open(newline="", encoding="utf-8")))
event_ids = [row["event_id"] for row in rows]
full_ids = [row["event_id"] for row in csv.DictReader(full_table.open(newline="", encoding="utf-8"))]
assert len(event_ids) == 22 and len(set(event_ids)) == 22
assert set(full_ids) - set(event_ids) == {"S0784a", "S1015f", "S1197a", "S1222a"}
assert set(event_ids).issubset(full_ids)

by_path = {}
for item in json.loads(manifest.read_text(encoding="utf-8"))["items"]:
    if item.get("path") and item.get("sha256"):
        by_path[item["path"]] = item["sha256"]

stage.mkdir()
print("event_id\tmanifest_key\texpected_sha256\tsource_sha256\tstaged_sha256\tstatus")
for event_id in event_ids:
    key = f"data/raw/{event_id}.mseed"
    expected = by_path[key]
    source = root / key
    target = stage / f"{event_id}.mseed"
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    assert source_sha == expected, (event_id, "source", expected, source_sha)
    shutil.copy2(source, target)
    staged_sha = hashlib.sha256(target.read_bytes()).hexdigest()
    assert staged_sha == expected, (event_id, "staged", expected, staged_sha)
    print(f"{event_id}\t{key}\t{expected}\t{source_sha}\t{staged_sha}\tPASS")

observed = {path.stem for path in stage.glob("*.mseed")}
assert observed == set(event_ids)
print(f"PASS staged_event_count={len(observed)} excluded=S0784a,S1015f,S1197a,S1222a")
PY
```

The 22 expected event/digest pairs are:

```text
S0918a  84a5fe149f671ced00deff642cdc5e1afe7e26944b0100f18e7d6425e3b1e16f
S0235b  3ecde9902877ddd77cc4ecd4858cf0c85815744af80cf954acc3e85d8ea7ab89
S0864a  53f136f5e77efaeb14ab3f07e90178ea4d881e60eb67a327ad9d6c827157ae4a
S0474a  474518969b80ac38ad9ff96c3939ce58ca1ad706a4c8f1e3c65fb84027582805
S0916d  d67d8e9586352908212bd07fa778ee3518370a77fb80631b89877fd95fbc91f2
S0802a  9617e0f5cf487c273c918c5acee59cb6a906102107ab7a485f26ef003beeec88
S0173a  a4dd5cd1718ae40f7f3c4f94fd2afca83cd6a3d5589f74f1640bab274d5cfe19
S0820a  d07eed87cb4da9acb7f9e3afabaea92d43eea4fcc5d2852a9a3f2297777980b3
S1048d  ba8228acc15ed4753db95bd3c60252a64137118b58ee298695a945631dc08803
S1133c  8f45b11eb24fb5ff2f20415b2725e558c2cb375ab824a3dd1a67f3bebd48eea9
S0290b  3347ddc4b1109af234282844b5888e58f07415fdb12f50c0d223cbf346cd902a
S1039b  8db285b3a9ea22753fa46228ef7ab0f5b6205751f01d6b9118e3fc4a9f70e802
S1022a  df9c3583c6c347998b5fc684e0be6ad61bb938ef1cce6dd7e69d72b05911cfcd
S0484b  d66e8a81f055963a016b57243b1419630d2c9c7d324693c3282c479aa8215ae5
S0105a  ffaac66830175871cb1284824082e8f618332930c24f53c1b4be3977259765e6
S0189a  d14a3159f775eaa623ed9eabe714a656ba8604703edfcdc3eb304af3b7e682ac
S1157a  4d73b79500b8682ab9bda4a0835b06d957c4a3be516cdb2c88637ea0e91b70c9
S1012d  7cca30eeb7b413897520033905958e893e78c0ccbe5e4f09a196261cd44d78d3
S0325a  659c5d5ac1be53176b150770f6d7479b431ca2a6ab80039cb184880ca6d5c539
S1102a  bf0bf57dee0d7eca09e8ba13602c29b691a8d61e4c72c406b27648a11d320829
S1153a  d1d2a7e404fb8e91bafb759516217ecb3b9e9c10035d7dd48f36c713456b530d
S1415a  a3cf6692bc188b25ee52eaa2f7068970d1d3396b9002cf7f949f86bfc64625dc
```

The non-`--from-scratch` runner performs the registered full resident-input
audit before it writes the run manifest (`scripts/run_paper0.py:1126-1166`).
Because the data manifest deliberately keys the source paths under `data/raw/`,
the printed staging table above is the explicit provenance bridge for the
copied `data/raw_ucla22/` paths. Downstream subset completeness is checked
against the supplied event table and raw directory by the inventory validator
(`scripts/07_validation/generate_validation_report.py:255-280`).

## 2. Archive helper and attempt-1 preservation

Define this finite helper once in the lead shell. It writes a sorted per-file
SHA-256/size manifest, writes the digest of that manifest, and immediately
re-verifies every listed file. It refuses symlinks and excludes only its two
own manifest files.

```sh
mq_hash_archive() {
  /Users/artuskg/micromamba/envs/mars-ic/bin/python - "$1" <<'PY'
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
assert root.is_dir(), root
manifest = root / "SHA256SUMS.tsv"
digest_record = root / "SHA256SUMS.tsv.sha256"
excluded = {manifest, digest_record}
files = []
for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
    if path.is_symlink():
        raise RuntimeError(f"archive symlink is not permitted: {path}")
    if path.is_file() and path not in excluded:
        payload = path.read_bytes()
        files.append((hashlib.sha256(payload).hexdigest(), len(payload), path.relative_to(root).as_posix()))
manifest.write_text("".join(f"{sha}\t{size}\t{name}\n" for sha, size, name in files), encoding="utf-8")
manifest_sha = hashlib.sha256(manifest.read_bytes()).hexdigest()
digest_record.write_text(f"{manifest_sha}\tSHA256SUMS.tsv\n", encoding="utf-8")
for expected, expected_size, name in files:
    payload = (root / name).read_bytes()
    assert len(payload) == expected_size
    assert hashlib.sha256(payload).hexdigest() == expected
assert hashlib.sha256(manifest.read_bytes()).hexdigest() == manifest_sha
print(f"PASS archive={root} files={len(files)} SHA256SUMS.tsv_sha256={manifest_sha}")
PY
}
```

Before pass 1, move exactly the attempt-1 chained outputs named by the lead:
the complete `data/deglitched/` directory, the complete
`data/processed/deglitch_work/` directory, and the complete contents of
`results/validation/` by moving that directory as a unit. Nothing is deleted.

```sh
test ! -e lanes/chained_attempt1
mkdir -p lanes/chained_attempt1/data/processed lanes/chained_attempt1/results
mv data/deglitched lanes/chained_attempt1/data/deglitched
mv data/processed/deglitch_work lanes/chained_attempt1/data/processed/deglitch_work
mv results/validation lanes/chained_attempt1/results/validation
mkdir -p data/deglitched data/processed/deglitch_work results/validation
mq_hash_archive lanes/chained_attempt1
/usr/bin/shasum -a 256 lanes/chained_attempt1/SHA256SUMS.tsv lanes/chained_attempt1/results/validation/paper0_run_manifest.json lanes/chained_attempt1/data/deglitched/deglitch_run_summary.json
```

Record the helper's file count and `SHA256SUMS.tsv_sha256`, plus the three
explicit hashes printed last. The recreated worktree directories are
`data/deglitched/`, `data/processed/deglitch_work/`, and
`results/validation/`. The rest of `data/processed/` remains in place; at the
time of this runbook it has no other attempt-1 product directory.

## 3. adv-A — S1197a registered adverse control

Run this before pass 1 from a new worktree-local control root. It has the same
one-file identity+UCLA CLI shape as calibration gate F1 and deliberately uses
the production lane's sole `ucla_unverified` allow-list.

```sh
test ! -e lanes/controls/adv_A
mkdir -p lanes/controls/adv_A/input lanes/controls/adv_A/output lanes/controls/adv_A/work
cp -p data/raw/S1197a.mseed lanes/controls/adv_A/input/S1197a.mseed

/Users/artuskg/micromamba/envs/mars-ic/bin/python scripts/02_preprocess/deglitch_mps_ucla.py \
  --in-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes/controls/adv_A/input \
  --out-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes/controls/adv_A/output \
  --work-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/lanes/controls/adv_A/work \
  --inventory-file /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/inputs/XB_ELYSE_response_inventory.xml \
  --seisglitch-command identity \
  --ucla-command '/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/scripts/02_preprocess/ucla/run_ucla_octave.sh {input} {output} {work_dir}' \
  --allow-status ucla_unverified
```

Required observable: the command returns nonzero because UCLA stderr contains
`aa(_,2): out of bound`; `output/S1197a.deglitch.json` records
`ucla.status="failed"` and `overall_status="succeeded_mps_only"`; the output
MiniSEED is byte-identical to the staged raw input; and
`output/deglitch_run_summary.json` reports
`{"succeeded_mps_only": 1}`. This is the expected rejection, not permission to
add `succeeded_mps_only` to pass 1.

Verify that terminal explicitly before proceeding:

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import json
from pathlib import Path

root = Path("lanes/controls/adv_A")
metadata = json.loads((root / "output/S1197a.deglitch.json").read_text())
summary = json.loads((root / "output/deglitch_run_summary.json").read_text())
assert "aa(_,2): out of bound" in metadata["ucla"]["stderr"]
assert metadata["ucla"]["status"] == "failed"
assert metadata["overall_status"] == "succeeded_mps_only"
assert summary["run_status"] == "complete"
assert summary["status_counts"] == {"succeeded_mps_only": 1}
assert (root / "output/S1197a.mseed").read_bytes() == (root / "input/S1197a.mseed").read_bytes()
assert (root / "output/S1197a.mseed").read_bytes() == (root / "work/S1197a/S1197a_mps_before_ucla.mseed").read_bytes()
print("PASS adv-A crash, restore, terminal, and allow-list rejection")
PY
```

The terminal is fixed by the harness: it saves the pre-UCLA product at lines
389-392, invokes UCLA at lines 393-405, and on a nonzero return copies the
backup over the output and assigns `STATUS_SUCCEEDED_MPS_ONLY` at lines
406-415 of `scripts/02_preprocess/deglitch_mps_ucla.py`. Batch lines 727-741
then reject that observed status because it is not in the sole allow-list.

## 4. Pass 1 — UCLA-on-raw

Run exactly once. `ucla_unverified` is the sole allowed terminal status; do not
add `succeeded_mps_only`. Identity is a byte-verbatim pre-stage, so UCLA is the
only deglitch method requested (`deglitch_mps_ucla.py:674-697`).

```sh
cd /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree

/Users/artuskg/micromamba/envs/mars-ic/bin/python scripts/run_paper0.py \
  --manifest /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/results/validation/paper0_run_manifest.json \
  --data-manifest /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/manifest/data_manifest.json \
  --event-table /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/manifest/event_table_ucla22.csv \
  --raw-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/raw_ucla22 \
  --ak-out-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/models/ak_subset \
  --khan-out-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/models/khan2023 \
  --mqs-catalog /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/raw/mqs_v14_catalog.xml \
  --seisglitch-command identity \
  --seisglitch-pythonpath /Users/artuskg/GitRepos/MarsQuake/external/seisglitch \
  --inventory-file /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/inputs/XB_ELYSE_response_inventory.xml \
  --ucla-command '/Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/scripts/02_preprocess/ucla/run_ucla_octave.sh {input} {output} {work_dir}' \
  --allow-deglitch-status ucla_unverified \
  --bootstrap-fidelity-level methods_robustness_200
```

Before archival, require command exit 0 and assert
`deglitch_run_summary.json.run_status == "complete"`, exactly 22 event rows,
and `status_counts == {"ucla_unverified": 22}`. Also require the run manifest
to end with `execution_status="succeeded"`, `status="succeeded"`,
`validation_status="passed"`, and the same status count under
`deglitch_attestation`. A mismatch is a stop condition.

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import json
from pathlib import Path

summary = json.loads(Path("data/deglitched/deglitch_run_summary.json").read_text())
manifest = json.loads(Path("results/validation/paper0_run_manifest.json").read_text())
assert summary["run_status"] == "complete"
assert len(summary["events"]) == 22
assert summary["status_counts"] == {"ucla_unverified": 22}
assert manifest["execution_status"] == "succeeded"
assert manifest["status"] == "succeeded"
assert manifest["validation_status"] == "passed"
assert manifest["deglitch_attestation"]["status_counts"] == {"ucla_unverified": 22}
assert manifest["deglitch_attestation"]["n_events"] == 22
print("PASS UCLA-on-raw 22-event terminal and manifest gates")
PY
```

### pos-A and pass-1 archive

Archive the complete freshly written product roots. The exact DAG product tree
is `data/deglitched/`, all of `data/processed/`, `results/bootstrap/`,
`results/vespagrams/`, `results/validation/`, and the two DAG-written table
files `results/tables/peak_comparison.csv` and
`results/tables/bootstrap_picks.csv`. `results/tables/event_dossier.csv` and
`results/figures/` are not written by this DAG and remain outside the lane
archive.

```sh
test ! -e lanes/ucla_raw
mkdir -p lanes/ucla_raw/data lanes/ucla_raw/results/tables
mv data/deglitched lanes/ucla_raw/data/deglitched
mv data/processed lanes/ucla_raw/data/processed
mv results/bootstrap lanes/ucla_raw/results/bootstrap
mv results/vespagrams lanes/ucla_raw/results/vespagrams
mv results/validation lanes/ucla_raw/results/validation
mv results/tables/peak_comparison.csv lanes/ucla_raw/results/tables/peak_comparison.csv
mv results/tables/bootstrap_picks.csv lanes/ucla_raw/results/tables/bootstrap_picks.csv
mq_hash_archive lanes/ucla_raw

cmp -s lanes/ucla_raw/data/deglitched/S0235b.mseed lead_controls/raw_census/S0235b/S0235b_raw_ucla.mseed
/usr/bin/shasum -a 256 lanes/ucla_raw/data/deglitched/S0235b.mseed lead_controls/raw_census/S0235b/S0235b_raw_ucla.mseed
/usr/bin/shasum -a 256 lanes/ucla_raw/SHA256SUMS.tsv lanes/ucla_raw/data/deglitched/deglitch_run_summary.json lanes/ucla_raw/results/validation/paper0_run_manifest.json lanes/ucla_raw/results/validation/validation_summary.json lanes/ucla_raw/results/tables/peak_comparison.csv
```

pos-A must print the same fixed hash for both S0235b files:
`e9fe30fb25701c6ce9bd8b94824f94549063bbcc358ac0167e858c1dfc72d4db`.
Record it, the archive-manifest hash, and the four critical product hashes.

Only after every assertion and pos-A passes, recreate these pass-2 targets:

```sh
mkdir -p data/deglitched data/processed/deglitch_work results/bootstrap results/validation results/vespagrams results/tables
```

## 5. Pass 2 — subset-matched MPS only

The real SEISglitch command is copied exactly from `RUNBOOK_ucla_prod.md`.
There is deliberately no `--ucla-command`. The event table, staged raw
directory, manifest, catalog, models, inventory, bootstrap fidelity, Python
interpreter, and working directory remain identical to pass 1.

```sh
cd /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree

/Users/artuskg/micromamba/envs/mars-ic/bin/python scripts/run_paper0.py \
  --manifest /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/results/validation/paper0_run_manifest.json \
  --data-manifest /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/manifest/data_manifest.json \
  --event-table /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/manifest/event_table_ucla22.csv \
  --raw-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/raw_ucla22 \
  --ak-out-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/models/ak_subset \
  --khan-out-dir /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/models/khan2023 \
  --mqs-catalog /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/raw/mqs_v14_catalog.xml \
  --seisglitch-command '/Users/artuskg/micromamba/envs/seisglitch-legacy/bin/python /Users/artuskg/GitRepos/MarsQuake/external/seisglitch/Scripts/seisglitch' \
  --seisglitch-pythonpath /Users/artuskg/GitRepos/MarsQuake/external/seisglitch \
  --inventory-file /Users/artuskg/marsquake_runs/20260802_ucla_prod/worktree/data/inputs/XB_ELYSE_response_inventory.xml \
  --allow-deglitch-status succeeded_mps_only \
  --bootstrap-fidelity-level methods_robustness_200
```

Before archival, require command exit 0, a complete 22-event deglitch summary
with exactly `{"succeeded_mps_only": 22}`, and a succeeded/passed run manifest
whose `deglitch_attestation` has that same count, `n_events=22`,
`attestation_level="succeeded_mps_only"`, and
`accepted_partial_lane_by_design=true`.

```sh
/Users/artuskg/micromamba/envs/mars-ic/bin/python - <<'PY'
import json
from pathlib import Path

summary = json.loads(Path("data/deglitched/deglitch_run_summary.json").read_text())
manifest = json.loads(Path("results/validation/paper0_run_manifest.json").read_text())
attestation = manifest["deglitch_attestation"]
assert summary["run_status"] == "complete"
assert len(summary["events"]) == 22
assert summary["status_counts"] == {"succeeded_mps_only": 22}
assert manifest["execution_status"] == "succeeded"
assert manifest["status"] == "succeeded"
assert manifest["validation_status"] == "passed"
assert attestation["status_counts"] == {"succeeded_mps_only": 22}
assert attestation["n_events"] == 22
assert attestation["attestation_level"] == "succeeded_mps_only"
assert attestation["accepted_partial_lane_by_design"] is True
print("PASS MPS subset 22-event terminal and manifest gates")
PY
```

### Why `succeeded_mps_only` is independently forced

The following citations use the immutable checked-in views requested by the
lead (`git show HEAD:scripts/run_paper0.py | nl -ba` and
`git show HEAD:results/validation/paper0_run_manifest.json`):

```python
# HEAD scripts/run_paper0.py:54
DEFAULT_ALLOWED_DEGLITCH_STATUSES = (VERIFIED_DEGLITCH_STATUS,)

# HEAD scripts/run_paper0.py:612
severity = "warning" if set(statuses) != set(DEFAULT_ALLOWED_DEGLITCH_STATUSES) else "error"

# HEAD scripts/run_paper0.py:1260-1261
if args.allow_deglitch_status is None:
    args.allow_deglitch_status = list(DEFAULT_ALLOWED_DEGLITCH_STATUSES)
```

The checked-in accepted 2026-07-25 manifest records:

```text
deglitch_attestation.status_counts = {"succeeded_mps_only": 26}
deglitch_attestation.attestation_level = "succeeded_mps_only"
deglitch_attestation.accepted_partial_lane_by_design = true
deglitch_attestation.n_events = 26
```

Thus omission of the flag would have selected verified-only
`mps_ucla_verified`, which cannot accept the observed all-MPS-only terminal.
The accepted run must have supplied the non-default literal
`succeeded_mps_only`; HEAD line 612 makes that explicit non-default selection
a warning rather than an error. The current batch implementation also assigns
`succeeded_mps_only` when no UCLA runner is configured
(`deglitch_mps_ucla.py:380-387`) and rejects any event not contained in the
explicit allow-list (`:727-741`).

### pos-B and pass-2 archive

```sh
test ! -e lanes/mps_subset
mkdir -p lanes/mps_subset/data lanes/mps_subset/results/tables
mv data/deglitched lanes/mps_subset/data/deglitched
mv data/processed lanes/mps_subset/data/processed
mv results/bootstrap lanes/mps_subset/results/bootstrap
mv results/vespagrams lanes/mps_subset/results/vespagrams
mv results/validation lanes/mps_subset/results/validation
mv results/tables/peak_comparison.csv lanes/mps_subset/results/tables/peak_comparison.csv
mv results/tables/bootstrap_picks.csv lanes/mps_subset/results/tables/bootstrap_picks.csv
mq_hash_archive lanes/mps_subset

cmp -s lanes/mps_subset/data/deglitched/S0235b.mseed /Users/artuskg/GitRepos/MarsQuake/data/deglitched/S0235b.mseed
/usr/bin/shasum -a 256 lanes/mps_subset/data/deglitched/S0235b.mseed /Users/artuskg/GitRepos/MarsQuake/data/deglitched/S0235b.mseed
/usr/bin/shasum -a 256 lanes/mps_subset/SHA256SUMS.tsv lanes/mps_subset/data/deglitched/deglitch_run_summary.json lanes/mps_subset/results/validation/paper0_run_manifest.json lanes/mps_subset/results/validation/validation_summary.json lanes/mps_subset/results/tables/peak_comparison.csv
```

The canonical path is read-only. pos-B must print equal hashes; record those,
the archive-manifest hash, and the four critical product hashes. Recreate the
empty working targets only if another lead-approved run needs them; do not
delete either lane archive.

All moves above are worktree-local archival moves. Any Git-tracked files moved
out of their original paths appear as deletions and must remain uncommitted
working-state. Do not restore, stage, commit, or publish them as part of these
runs.

## 6. Stages and gates in both passes

Both commands omit `--from-scratch`. Therefore no download stage or network
path runs. `scripts/run_paper0.py:1126-1140` performs the resident-input audit,
clears only stale incremental validation state, and builds the same downstream
DAG. Lines 709-740 enumerate, in order:

```text
deglitch
validation_deglitch
rotate
bandpass
polarization
fdpa
glitch_flags
align
normalize
validation_inventory
validation_preprocessing
validation_alignment
validation_model
vespagrams
validation_benchmark
detect_peaks
bootstrap_type1
bootstrap_type2
validation_type2_distance_stratified
bootstrap_type3
validation_type3_alignment_jitter
fit_bootstrap
validation_bootstrap
validation
```

The same 22-row table is propagated to alignment, vespagrams, all three
bootstraps, and validation; the same raw subset is propagated to deglitch and
validation (`run_paper0.py:390-420`, `:658-735`). Deglitch and rotation receive
the same pass-specific sole allow-status (`:681-701`). The early deglitch
status-count test is a non-empty subset of the explicit list (`:961-968`); the
incremental deglitch check honors it (`:1043-1046`), and determined-failure
handling stops immediately on a disallowed observed terminal (`:971-1005`,
`:1082-1119`). Inventory gates use the supplied table and raw directory, so
they require exactly those 22 raw and downstream event products.

The incremental validation commands use `--no-strict-gates`; the final
aggregate uses `--strict-gates` (`run_paper0.py:658-678`). The validation
summary still records the verified-only deglitch check as failed for these
explicit unverified lanes, but `_apply_validation_stage_result` removes only
that deglitch failure when the observed counts are allowed, while retaining
every other failure and current-provenance gate (`:813-869`). Production does
not implicitly run `--preflight`; if the lead runs either same-argument command
with `--preflight`, the explicit non-default unverified allow-list takes the
HEAD-line-612 warning path rather than the verified-only error path.

Every stage command, return code, status, and output tail is recorded under
`results/validation/paper0_run_manifest.json.stages[]`
(`run_paper0.py:1168-1199`). That manifest also binds `git_commit`,
`git_status_sha256`, `input_audit`, `bootstrap_fidelity`,
`deglitch_attestation`, current-provenance enforcement, terminal validation,
and final status (`:1141-1166`, `:1221-1241`).

## 7. Registered same-cell readout — lead only

Do not browse images or search for alternate peaks. In each archived lane use
these two exact artifacts:

1. `results/tables/peak_comparison.csv`: select only
   `mode=paperfaith`, `input_type=envelope`, `norm_variant=A`,
   `stack_method=nth_root`, `power_window_s=20`, and then the three rows
   `(PKiKP, global)`, `(PKiKP, published_target)`, and
   `(PKKP, paper_target)`. Read `time_s`, `slowness_sdeg`, `power`,
   `support_count`, `minimum_support`, `status`, and
   `current_provenance_status`.
2. `results/validation/validation_summary.json`: under
   `benchmark.named_endpoint_rows[]`, select `endpoint_label` values
   `displaced_ridge`, `published_PKIKP_box`, and `PKKP_target`. Read
   `registered_key`, `phase`, `peak_label`, `window`,
   `primary_lane_variant`, `time_s`, `slowness_sdeg`, and `power`.

The exact mapping is:

| Registered surface | CSV `phase,peak_label` | validation endpoint |
|---|---|---|
| global PKiKP argmax | `PKiKP,global` | `displaced_ridge` |
| published PKiKP target-box maximum | `PKiKP,published_target` | `published_PKIKP_box` |
| PKKP endpoint | `PKKP,paper_target` | `PKKP_target` |

`detect_peaks.py:313-354` computes those three cells; lines 401-407 name the
rows; lines 552-617 populate their fields; and lines 620-665 write
`results/tables/peak_comparison.csv` (default path at :668-672). The validation
registry fixes their keys, roles, and windows at
`generate_validation_report.py:36-66`, maps the same detector results at
`:543-570`, and serializes the three rows at `:573-578` and `:633-637` into
`validation_summary.json` (`:1464-1468`).

Use the archived run manifest beside each summary to verify the lane's
`deglitch_attestation.status_counts`, `n_events`, `stages[]` success, and
terminal status before putting its three coordinates into the comparison
table. The CSV and JSON coordinates must agree cell-for-cell; disagreement is
a stop condition, not an invitation to inspect a neighboring maximum.

This lead-only command performs only that registered readout and prints the
same-cell table; it does not inspect any other outcome.

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
