# A registered public-data reproducibility benchmark for the reported PKiKP detection of a Martian inner core

Reproducibility capsule for the manuscript

> Krohn-Grimberghe, A. (2026). *A registered public-data reproducibility
> benchmark for the reported PKiKP detection of a Martian inner core.*
> Draft v0.6 (2026-08-02), prepared for submission to Seismica.
> Archived release: [doi:10.5281/zenodo.21762439](https://doi.org/10.5281/zenodo.21762439)
> (v0.6 tarball, sha256 `866dec8e…`). Preprint: to be added.

Corresponding author: Artus Krohn-Grimberghe (Percivio Ltd.),
<artus@percivio.com>.

## What this is

Bi et al. (2025, Nature) report a ~600-km solid inner core in Mars, based
partly on a PKiKP vespagram peak at 604 ± 2 s after P from stacked InSight
marsquakes. This repository is the public capsule of a **registered
reimplementation from public data only**: success criteria, windows, and
statistical rules were frozen in a registered specification
(`papers/Paper0/Paper0.md`, with a dated amendment log) before the affected
outcomes were inspected.

The benchmark's registered outcome classes treat a reproducible
*disagreement* with the published coordinates as a valid scientific result;
agreement was never required. The manuscript
(`papers/Paper0/manuscript/DRAFT_seismica.md`) reports what the frozen
pipeline actually produces, with positive and adverse controls.

Everything here is either pipeline code, the registered specification, the
manuscript sources, small claim-bearing result tables, or verbatim internal
provenance records cited by the manuscript. Bulk inputs (waveforms,
catalogue, external model archives) are **pinned by SHA-256 and fetched by
script**, not redistributed.

## Repository contents

| Path | Contents |
| --- | --- |
| `papers/Paper0/Paper0.md` | Registered specification with frozen success criteria and the dated amendment log |
| `papers/Paper0/manuscript/` | Manuscript source (`DRAFT_seismica.md`), numeric provenance companion (`NUMBERS.md`), figures + `figure_provenance.json`, tables, and the rendering-only `make_figures.py` |
| `scripts/` | The full Paper 0 pipeline: `run_paper0.py` orchestrator; stages `01_download` … `07_validation`; shared modules; `paper0_input_audit.py`; `paper0_provenance.py` |
| `manifest/` | Registered input manifest (`data_manifest.json`, SHA-256 pins) and event tables (23-event set; 22-event UCLA subset) |
| `tests/` | Pipeline contract tests (pytest; `slow` marker is opt-in) |
| `results/manuscript_inputs/full_set.npz` | The exact 23-event full-set vespagram product behind the headline figures (identity below) |
| `results/tables/`, `results/bootstrap/`, `results/validation/`, `results/lunar_analog/` | Small claim-bearing tables, bootstrap occupancy products, the run-validation manifest, and the preregistered lunar-analog criteria |
| `history/` | Verbatim internal research records cited by the manuscript and by `NUMBERS.md` (controls, reviews, production runs) |
| `docs/` | Supporting scientific documents cited by the shipped records |
| `environment.yml`, `environment.lock.yml`, `Dockerfile` | Declared software environment (conda/mamba; locked versions; container recipe) |

## Quick start

```sh
# 1. Environment
mamba env create -f environment.lock.yml   # or environment.yml / Dockerfile
mamba activate mars-ic

# 2. Fetch pinned public inputs (writes data/ locally; verifies SHA-256 pins)
python scripts/01_download/download_mqs_catalog.py
python scripts/01_download/download_ak_models.py
python scripts/01_download/download_khan_models.py
python scripts/01_download/download_waveforms.py

# 3. Preflight (includes the registered input audit)
python scripts/run_paper0.py --preflight

# 4. Full pipeline
python scripts/run_paper0.py

# 5. Tests
python -m pytest -q

# 6. Figures/tables (rendering-only; asserts every number against pinned artifacts)
python papers/Paper0/manuscript/make_figures.py
```

**Preflight caveat (registered):** a from-scratch invocation
(`--from-scratch --preflight`) skips the registered input audit because the
inputs do not exist yet. After downloading inputs, always run the plain
`python scripts/run_paper0.py --preflight` so the audit executes against the
manifest pins.

## Pinned external inputs (not redistributed)

These are public datasets whose redistribution rights belong to their
providers. The pipeline fetches them and byte-verifies each against
`manifest/data_manifest.json`.

| Input | Source | Identity |
| --- | --- | --- |
| MQS marsquake catalogue v14 (`data/raw/mqs_v14_catalog.xml`) | MQS / IPGP data centre | sha256 `cf6f7dff22e336bdc7d80cc0b60c93028fe566a4137e0357179a006598991ca9` |
| InSight SEIS waveforms | FDSN (IRIS / IPGP) | per-file pins in `manifest/data_manifest.json` |
| Khan et al. (2023) model archives `Core.zip`, `LSL_Models.zip`, `LSL_Models_TauP.zip` | IPGP Dataverse, DOI [10.18715/IPGP.2023.llxn7e6d](https://doi.org/10.18715/IPGP.2023.llxn7e6d) | sha256 `45bc822d90e56ade754ad9deaa08866aecf3d63818ced56c4a1be4200000390f`, `40b2041c81c9db09a849c82bf3456dc4f31569af484d47f2a8c394f55a1711f3`, `c54ba3ddeb5cb01a6ee24fba164c0475b1127166c4e65afd725a9cc071c3b0f4` |
| AK reference models | fetched by `download_ak_models.py` | pins in manifest |
| `seisglitch` (deglitching, MPS lane) | [pss-gitlab.math.univ-paris-diderot.fr/data-processing-wg/seisglitch](https://pss-gitlab.math.univ-paris-diderot.fr/data-processing-wg/seisglitch) | commit `e594a6263792008d0a0e9eb522f51f0f5464deaf` (not vendored; clone at this commit into `external/seisglitch`) |

## Included claim-bearing artifact identities

`results/manuscript_inputs/full_set.npz` — the 23-event full-set vespagram
product used by the headline figures and the leave-one-out analysis:
55,667,634 bytes, sha256
`f4b3a03af9bff68d6fa2750e9eaaa28511e638de32f569c34e40152483c9c280`.
`make_figures.py` byte-verifies this file against the pin recorded in
`history/20260726_publication_assessment/loo/loo_verdict.json` before
rendering anything.

All other shipped result files are small; their identities are recorded in
`results/validation/paper0_run_manifest.json`, `figure_provenance.json`, and
the per-record SHA tables under `history/`.

## Verification-lane status (adverse control, preserved)

The pipeline defines a strict `mps_ucla_verified` waveform-provenance
attestation lane. That strict attestation **remains reserved**: it has
deliberately not been granted, and this capsule does not upgrade it. The
landed UCLA-raw production comparison
(`history/20260802_ucla_prod/`) reports the same-cell comparison on its own
`ucla_unverified` terms with its countersigned review record. Treating the
reserved lane as an open adverse control is part of the registered design.

## Provenance records: what is included and what is not

Included under `history/` (verbatim, unmodified): every internal record
cited by the manuscript or by `NUMBERS.md` — the ablation/polarization
provenance check, Earth known-truth control, injection–recovery ladder,
Mars scramble null, reference-verification pass, UCLA feasibility /
equivalence / production records, v0.5 and v0.6 accuracy reviews, PKKP
concordance check, decoy-family control, cross-selection (Visser) execution,
publication-assessment leave-one-out records, and an independent results
double-check. These records name the machines, dates, and automated
reviewer/worker roles that produced them; they are research records, not
polished prose.

Not included (referenced by the registered specification but retained in
the private working repository's archive): internal operational surfaces
(`docs/CURRENT_STATE.md`, `docs/verification_ledger.md`,
`docs/research_pipeline.md`), pre-benchmark model-review bundles
(`history/20260704_*`), Paper 1 confirmatory records
(`history/20260709_paper1_confirmatory/`), and other program-management
records not cited by the manuscript. The registered specification is
reproduced verbatim, so pointers to those surfaces remain visible in its
text. None of them carries scientific numbers used by the manuscript; the
manuscript's own citation closure is complete within this repository.

## Bulk evidence index (S3)

Deterministically regenerable bulk products are parked in a private S3
bucket and listed here by URI and SHA-256. They can be re-derived by
running the pipeline (byte identity is asserted by the recorded hashes), or
requested from the corresponding author.

| Object | SHA-256 / identity |
| --- | --- |
| `s3://marsquake/paper0_evidence/20260726_loo_influence/` (24 leave-one-out NPZs + `full_set.npz`) | per-file SHA-256s in `history/20260726_publication_assessment/loo/loo_table.csv` and `loo_verdict.json` |
| `s3://marsquake/paper0_evidence/20260725_bench_e2e/nth_root_win20.npz` (headline vespagram cube, 56,545,416 B) | `9d46868b188fe018b41bb644c3a938580fbc6d3902a921affd172693b4b84e40` |
| `s3://marsquake/paper0_evidence/20260802_ucla_prod/lanes_ucla_raw.tar.gz` | `42777da69f9a0f94d424a2b629f7ffbd954fb7f6e491d8d138e37d92468d32f5` |
| `s3://marsquake/paper0_evidence/20260802_ucla_prod/lanes_mps_subset.tar.gz` | `ea4949dbc48008b273ee7b32c60a1e6c6a4c322005ab96d948fed7fda9822d0c` |
| `s3://marsquake/paper0_evidence/20260802_ucla_prod/lanes_chained_attempt1.tar.gz` | `3f3e450cff6e90b6b0bc6996ed973cba928e372cf37d141d94afcff4f7d93173` |
| `s3://marsquake/paper0_evidence/20260802_ucla_prod/tarballs.sha256` | manifest of the three tarballs |

## Citing

See `CITATION.cff`. The v0.6 state of this repository is archived at
[doi:10.5281/zenodo.21762439](https://doi.org/10.5281/zenodo.21762439)
(deterministic `git archive` of tag `v0.6`, commit `b3752bf2`). Until
the preprint is posted, `papers/Paper0/manuscript/DRAFT_seismica.md` is
the manuscript source of record.

## License

MIT (see `LICENSE`) for the code and authored content in this repository.
Pinned external datasets and software retain their providers' licenses.
