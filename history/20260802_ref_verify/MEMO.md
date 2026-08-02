# Paper 0 References — publisher-record verification memo

Run: 20260802_ref_verify. Input: `papers/Paper0/manuscript/DRAFT_seismica.md`
"## References" (lines 577–636) at origin/main = `9d854462` (v0.4,
2026-08-01), plus a body sweep (lines 1–576) and the NUMBERS.md DOI rows.
Primary route: Crossref REST (`api.crossref.org/works/<doi>`) for articles,
DataCite REST (`api.datacite.org/dois/<doi>`) for datasets. Raw responses:
`api_responses/` (22 files). Verification date: 2026-08-02.

## Controls (run before the sweep)

- **Positive** — `10.1038/s41586-025-09361-9` (Bi et al. 2025): HTTP 200;
  Crossref returns *Nature*, vol. 645, pages 67–72, issued 2025-09-03,
  authors Bi (Huixing), Sun (Daoyuan), Sun (Ningyu), Mao (Zhu),
  Dai (Mingwei), Hemingway (Douglas), title "Seismic detection of a 600-km
  solid inner core in Mars" — exactly the drafted entry. PASS
  (`api_responses/control_positive_bi2025.json`).
- **Adverse** — fabricated `10.1038/s41586-999-99999-9`: HTTP 404,
  "Resource not found." PASS — the checker discriminates
  (`api_responses/control_adverse_fabricated.txt`).

## Headline findings

1. **Bi et al. (2025) has a published Author Correction** — *Nature* 648
   (8094), E18, 3 Dec 2025, doi `10.1038/s41586-025-09981-1` (Crossref
   `updated-by` on the main record). Content (from the archived copy at
   `references/original_paper/s41586-025-09981-1.txt`, also indexed in
   `paper_facts.yaml`): citation-only — in Methods "Composition of the
   Martian core", ref. 54 was replaced by ref. 70 (Huang et al. 2023, GRL).
   It does **not** touch the seismic pick tables / SI that Paper 0
   reconstructs, so no claim impact; but the References entry may want an
   appended "(Author Correction: *Nature*, 648, E18, 2025,
   https://doi.org/10.1038/s41586-025-09981-1)" for completeness. Lead's
   call.
2. **The two IPGP Dataverse deposits now have confirmed author lists**
   (this discharges the entry's registered "deposit author list to be
   confirmed at submission" note):
   - `10.18715/IPGP.2023.llxn7e6d` → Khan, A., Huang, D., Durán, C.,
     Sossi, P., Giardini, D., & Murakami, M. (2023). *Updated interior
     structure models of Mars with a liquid silicate layer atop the
     Martian core* [data set]. IPGP Research Collection. This makes the
     body's "Khan et al. (2023) model ensemble" (line 120) resolvable to a
     reference entry — currently it is an orphan citation (the entry is
     authorless).
   - `10.18715/IPGP.2021.kpmqrnz8` → Stähler, S., Khan, A., Banerdt,
     W. B., Lognonné, P., Giardini, D., et al. (41 creators) (2021).
     *Interior Models of Mars from inversion of seismic body waves*,
     V1.0 [data set]. IPGP Research Collection.
3. **Visser et al. (2026) preprint status verified**: Crossref type
   `posted-content/preprint`, posted 2026-07-20 — the draft's "Research
   Square preprint rs-10379955, version 1, posted 20 July 2026" is exactly
   right. A `/v2` probe returns 404 (no later version) and no journal
   version exists in Crossref as of 2026-08-02 (no `is-preprint-of`
   relation; bibliographic search returns only the preprint). One fix:
   the record **and** the preprint title page give the second author as
   "Federico Munch" — no middle initial — so "Munch, F. D." → "Munch, F."
   (body line 500 uses surnames only and is fine).
4. **Garcia et al. (2011) VPREMOON has a 2012 erratum** —
   `10.1016/j.pepi.2012.03.009`, *PEPI* 202–203, 89–91 (Crossref relation
   `erratum`). The draft entry backs the lunar R≈380 km context (§ 5.3 /
   NUMBERS row 61). Whether the erratum changes the cited radius context
   was not adjudicated here; flagging existence only. Lead's call whether
   to co-cite.
5. **Four entries lack DOIs that exist** (all resolved via Crossref
   title+author query, top match unambiguous): Garcia 2011
   (`10.1016/j.pepi.2011.06.015`), Montalbetti & Kanasewich 1970
   (`10.1111/j.1365-246X.1970.tb01771.x`), Muirhead & Datt 1976
   (`10.1111/j.1365-246X.1976.tb01269.x`), Weber et al. 2011
   (`10.1126/science.1199375`). Proposed entries in the CSV.
6. **Apollo XA entry**: registry title is plural — "Apollo Passive Seismic
   Experiment**s**" — and the DataCite record carries creator "Nunn, C",
   publisher "International Federation of Digital Seismograph Networks",
   nominal year 1969. Proposed FDSN-form entry in the CSV (or minimally
   pluralize the title).

## Per-entry statuses (16 entries)

- VERIFIED clean (8): Beyreuther 2010; Bi 2025 (with correction-notice
  note); Crotwell 1999; InSight SEIS Data Service 2019; MQS V14
  (`10.12686/a21` confirmed V14-specific: title "…V14 2023-04-01",
  version 14.0); Lognonné 2019; Nunn 2020 (incl. Zenodo supplement
  `10.5281/zenodo.3560482`, resolves, version-specific DOI); Scholz 2020.
- CORRECTED (8): Garcia 2011 (+DOI, erratum note); IPGP 2023 ensemble
  (authors+title from record); IPGP 2021 AK subset (authors+title from
  record); Montalbetti & Kanasewich 1970 (+DOI); Muirhead & Datt 1976
  (+DOI); Apollo XA (title plural / FDSN form); Visser 2026 ("Munch, F.");
  Weber 2011 (+DOI).
- UNRESOLVED: none. All 12 drafted DOIs resolve (10 Crossref, 6 DataCite
  counting the Zenodo supplement and both controls' target).

## Orphan check

**Body → References:** every body citation has an entry — with one
qualification: "Khan et al. (2023)" (line 120) currently points at the
authorless "Mars interior model ensemble (2023)" entry and is only
resolvable after the proposed rename (headline finding 2). NUMBERS.md
DOI rows cite nothing outside the reference list.

**References → body (entries never formally cited):** Seismica requires
every listed reference to be cited. Currently missing an in-text
author-year attachment:

- Beyreuther et al. 2010 — ObsPy is mentioned **nowhere** in the body;
  either add a software citation in Methods § 3.1 or drop the entry.
- Crotwell et al. 1999 — TauP appears (§ 2, § 5.4, figure sources) but
  never with the citation; attach at first mention.
- Lognonné et al. 2019 — SEIS/VBB data described in § 2 without citation.
- Scholz et al. 2020 — "MPS/SEISglitch method" (§ 3.1) without citation.
- Montalbetti & Kanasewich 1970 — named in prose ("Montalbetti–
  Kanasewich-style", § 3.1 and § 5.5) but never as (Author, year).
- Muirhead & Datt 1976 — "fourth-root slant stacks" (§ 3.1) without
  citation.
- InSight SEIS Data Service 2019 and Apollo XA 1969 — dataset entries;
  cited via DOI/network code in § 2/§ 5.3/NUMBERS but the XB DOI string
  appears only in the References. Acceptable for data citations; optional
  to add the DOI at the § 2 waveforms bullet.

## Caveats (honest limits)

- Field comparison is against registry metadata (Crossref/DataCite), not
  page scans of the typeset PDFs; where registries carry known quirks I
  said so (SEIS publisher string "MFSC" is a registry typo — draft's
  "MSFC" is the correct agency; Crossref renders GJRAS papers under the
  journal's current name "Geophysical Journal International"; Springer
  metadata prints "Insight's" in the Lognonné 2019 title).
- "No journal version of Visser et al." is a statement about Crossref as
  of 2026-08-02 — 13 days after posting; re-check at submission assembly.
- The Garcia 2012 erratum's effect on the cited R≈380 km context was not
  read here (metadata-only pass); its existence is flagged, content
  unadjudicated.
- Whether the pipeline actually uses ObsPy (for the proposed § 3.1
  citation sentence) was not verified in code; the lead knows.
