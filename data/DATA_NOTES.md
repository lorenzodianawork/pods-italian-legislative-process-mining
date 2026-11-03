# Data notes: how the data was obtained and integrated

Retrieved on **2026-11-03** (UTC). Scope: legislatures XVII (2013), XVIII (2018), XIX (2022–).

## 1. Camera dei Deputati (`data/raw/camera/`)

- The SPARQL endpoint `dati.camera.it/sparql` returned HTTP 502 for every query on the retrieval day, so we used the official **RDF dumps** (N-Triples, zipped) from `https://dati.camera.it/ocd/dump/`.
- Files (one pair per period: XVII–XVIII in the plain file, XIX in the `-19` file): `atto`, `statoIter`, `assegnazione`, `trasmissione`.
- Integrity: `SHA256SUMS.txt`; retrieval time: `RETRIEVED_AT.txt`. The original zips are committed; extracted `.rdf` files are git-ignored.
- `statoIter` has **no link back to the bill**; the link is the property `ocd:rif_statoIter` in the `atto` dump, so `atto` is required.
- Licence: **CC BY-SA 4.0**, © Camera dei Deputati – dati.camera.it.

Script: `scripts/download_all.sh` (download) and `scripts/build_event_log.py` (join → `data/processed/iter_camera.csv`).

## 2. Senato della Repubblica (`data/raw/senato/`)

Extracted from the SPARQL endpoint `https://dati.senato.it/sparql` with `scripts/extract_senato.py`; the exact queries are saved in `queries/`, row counts and timestamps in `MANIFEST.json`.

| File | Content | Rows |
|---|---|---|
| `ddl.csv` | one row per reading of a bill (`fase` = `S.601`, `C.1248-B`...), with `idDdl`, chamber, presented/transmitted, date, last state | 19,801 |
| `assegnazioni.csv` | assignments to committees (date, committee, `sede`: referente / redigente / deliberante / legislativa; `tipoCommissione`) | 109,220 |
| `iter.csv` | membership of readings in an iter (`idDdl`, progressive number) | 20,636 |

Constraints of the endpoint that shaped the extractor (all discovered empirically, see `docs/senato_probe*_output.txt`):

- **Silent cap of 10,000 rows per query** → large tables are fetched with monthly date windows; the script aborts if any window reaches the cap.
- HTTP 403 on POST, on `STR/STRAFTER` filters and on URLs longer than ~4 KB → GET only, date-string filters, short queries.
- **Completeness check**: for each legislature, the rows retrieved are compared with `COUNT(*)`; all checks passed ("OK, completo").
- In legislature XVIII the ddl query returned 6,515 rows for 6,479 distinct ddl (multiple state rows); duplicates removed.
- Licence: Senato open data are released under **CC BY 3.0 (Italy)** – verify the wording at https://dati.senato.it before publishing the report.

## 3. Integration (`scripts/build_unified_log.py`)

- **Case = iter.** The Senato `idDdl` is shared by all readings of the same law in both chambers (checked: 18,337 groups; 1,280 with ≥2 readings, all involving both chambers; 1,263 alternate strictly Camera/Senato).
- **Join Camera ↔ Senato** on (legislature, number): Camera `ac17_1248` ↔ Senato `fase = C.1248`; second readings `ac17_1248-B` ↔ `C.1248-B`. First-reading match is practically perfect (XVII 4822/4822, XVIII 3705/3706, XIX 3172/3172). See `docs/join_check_output.txt`.
- **No double counting**: Senato rows with `ramo = C` describe Camera readings already in the Camera dump, so only readings with `ramo = S` contribute Senato events (presentation / takeover, committee assignments, last known state).
- Event names are prefixed `C:` / `S:`. Ordering: date, then reading number, then a logical rank (the data has day precision only).
- Output: `unified_log.csv` (case_id, legislatura, timestamp, activity, chamber, reading, resource, source, fase) and `cases.csv` (one row per case: readings, number of navette, bill type, decree-law flag, last Senato state, duration…).

Result: 18,269 cases, 100,048 events (C 42,147 / S 57,901).

## 4. Known limits (please read before analysing)

1. **Day-level timestamps** → events on the same day are ordered by a heuristic, not by true order.
2. **Camera states are coarse** (36 labels) and 57% of Camera bills stop at "Assegnato" (never examined). Most analyses should be filtered to cases with enough events (e.g. ≥ 6 events: 7,103 cases) and the filter must be reported.
3. **Senato internal detail is thin**: only presentation date, assignments and the *latest* state (`statoDdl`, with its date). Floor/committee votes are not linked to bills in the open data.
4. **Outcome fields disagree across chambers** (e.g. Camera ends in "Legge" while Senato `statoDdl` is not, and vice versa). We do not trust a single field: define the outcome explicitly in the report.
5. `numeroLegge` (Senato) is unreliable; 53 ddl have composite `fase` strings (combined bills, e.g. `S.859-1357-1378-B`) and `progressivoIter` is non-unique in ~1,072 iter rows.
6. ~72 Camera bills (0.6%, mostly composite readings) could not be attached to a Senato iter and are **not** in the unified log (484 events); they remain in `iter_camera.csv`.
7. **Legislative seat** (*sede legislativa*, art. 72 c.3) is almost absent in the Camera data (1 assignment) but present in the Senato (`deliberante` 110, `legislativa` 119 assignments) → conformance on the legislative-seat procedure can only be tested on the Senate side.
8. Decree-laws are identifiable in the Senato (`natura = di conversione di decreto-legge`: 416 cases, 312 converted); only 1 of the 312 converted cases exceeds 60 days from presentation to last event (median 56 days) – to be verified, it may be a data artefact.
