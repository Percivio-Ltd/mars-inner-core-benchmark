# PREREG Addendum C — Apollo pick/catalogue + waveform data sources (proposed)

**Authored:** 2026-07-05 (Fable leader, from the main MarsQuake session — handoff before session close).
**Type:** proposed pre-registration addendum to `PREREG_criteria.md` (data-source ranking only; **no analysis
choices changed**, no code). Does not alter any frozen window/threshold/success criterion — it only tells the
Phase-2 worker *where* the ranked inputs actually live. Apply by folding into the PREREG's ranked pick-source
list and bumping its amendment hash, then resume Phase 2.

## Why this addendum exists

Phase-2 stalled on "no machine-readable Apollo P/S pick table" (see `metadata/search_*_picks_*.json`,
`metadata/wayback_utig_*_cdx.json`, `metadata/source_attempts.csv` — UTIG / Wayback / OpenAlex all dead-ended).
That was a **false wall**: the picks are not published as a standalone table; they are embedded as QuakeML
`<pick>`/`<arrival>` elements inside the Nunn et al. (2020) electronic supplement catalogue — the **same
QuakeML format** the repo already parses for the Mars V14 catalogue. A "standalone pick table" search will
always fail; parsing the QuakeML succeeds.

## Verified records (all checked 2026-07-05 via web search/fetch; label = VERIFIED unless noted)

### C1 — Catalogue + arrival picks (NEW #1 pick source) — VERIFIED
- **Nunn, C. et al. (2020). "Lunar Seismology: a data and instrumentation review — Electronic Supplement."
  Zenodo. Concept DOI 10.5281/zenodo.3560482** — https://zenodo.org/records/3560482
- Relevant files in the record:
  - `LunarCatalog_Nakamura_1981_and_updates_v1.xml` (QuakeML, ~21 MB) — the Nakamura 1981+updates catalogue;
    **expected to carry P (and sparser S) phase arrivals as QuakeML picks.**
  - `Nunn19_LunarCatalog_v1.xml` (QuakeML, ~607 kB) + `Nunn19_LunarCatalog_v1.xlsx` — event catalogue with
    origin times/locations.
  - `station_parameters.csv` — Apollo 12/14/15/16 coordinates (satisfies PREREG station-coordinate task).
  - `levent.1008c` — the binary levent catalogue (already retrieved by Phase 2; provenance now unified here).
  - Deep-moonquake stacks: `Bulow_et_al_2007_*`, `Lognonne_et_al_2003_*`, `Nakamura2005_*` (context only;
    PREREG blindness rules still forbid using stacks as detection inputs).
- Companion paper to cite alongside the supplement: **Nunn et al. (2020), Space Sci. Rev. 216:89,
  DOI 10.1007/s11214-020-00709-3** (ADS 2020SSRv..216...89N).

### C2 — Waveforms (closes the "zero waveforms" gap) — VERIFIED
- **Apollo Passive Seismic Experiment, FDSN network `XA` (1969–1977). DOI 10.7914/SN/XA_1969** —
  https://doi.org/10.7914/SN/XA_1969
- Pull event-windowed miniSEED via an FDSN client (IRIS/EarthScope DMC), the same mechanism used for
  `XB.ELYSE` on Mars. Stations XA.S12/S14/S15/S16, long-period (and short-period where needed) channels.
- Modern SEED re-archive reference (cite for waveform provenance): **Nunn et al. (2022), PSJ, "A New Archive
  of Apollo's Lunar Seismic Data", DOI 10.3847/PSJ/ac87af.**

### C3 — Secondary mirror (fallback only) — VERIFIED (portal live 2026-07-05)
- **JAXA DARTS Seismology (Apollo):** https://www.darts.isas.jaxa.jp/planet/seismology/apollo/
- Use only if a Zenodo/IRIS asset 403s (as Weber 2011 Table S3 did — that failure is recorded and stands as
  a genuine NO-EVIDENCE for the Weber reference model; it does **not** block the method port, which needs
  VPREMOON only, already obtained under `models/`).

## Proposed change to PREREG ranked pick-source preference

Replace the current ranking (was: (1) UTIG/DARTS arrival files, (2) Lognonné 2003, (3) Garcia 2011,
(4) Bulow 2007) with:

1. **Nunn et al. 2020 Zenodo QuakeML** (`LunarCatalog_Nakamura_1981_and_updates_v1.xml`, then
   `Nunn19_LunarCatalog_v1.xml`) — parse with `obspy.read_events()` or the repo QuakeML loader.
2. Lognonné et al. 2003 pick tables — 3.
3. Garcia et al. 2011 pick tables — 4 (VPREMOON already retrieved).
4. Bulow et al. 2007 compilations — 5.
5. UTIG/DARTS raw arrival files — demoted to last resort (institutional/dead-ended this run).

Rule unchanged: **picks are used as published; never create or adjust a pick.** Document which catalogue and
which QuakeML `pick`/`arrival` fields were used, with sha256 of the downloaded `.xml`.

## One UNCONFIRMED step (must verify before declaring Phase 2 complete)

- **UNCONFIRMED:** that `LunarCatalog_Nakamura_1981_and_updates_v1.xml` actually contains per-event P/S
  arrival picks (vs. origins only). Confirm by parsing and reporting pick counts per phase per station.
  Expectation: good **P** coverage; **S is famously sparse/emergent** on lunar records, so an S-poor result
  is a data property, not a retrieval failure. If picks are genuinely absent from the QuakeML, fall through
  to source #2 (Lognonné 2003) and record the QuakeML pick-field audit as evidence.

## Mechanical next actions for the resuming A1 leader/worker

1. `curl`/`wget` the Zenodo record files (C1) + FDSN-fetch XA waveforms (C2) into `data/` with sha256 +
   access-date logging (existing evidence discipline).
2. Parse the QuakeML; emit the normalized pick CSV the PREREG's Addendum-A/B generators expect
   (event id, station, phase, pick time, quality, source).
3. Run the Fable metadata gate (≥5 events cross-checked vs the Nakamura catalogue) already specified in the
   PREREG, then proceed to Phase 3 RUN.

## Provenance of this addendum
All DOIs/URLs above verified 2026-07-05 by the main-session Fable leader via web search + fetch (Zenodo record
contents fetched directly; XA DOI, SSR DOI, PSJ DOI, and SSR record cross-confirmed). No primary PDF was
paywalled for the two load-bearing items (Zenodo record, XA network DOI). Fold into `PREREG_criteria.md` and
re-hash before Phase 2 resumes.
