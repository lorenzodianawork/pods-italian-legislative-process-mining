# Process Mining of the Italian Legislative Process

Course project for *Process-Oriented Data Science* (PODS), MSc Data Science, UPC Barcelona (FIB), 2026/27.

## What this project is about

How does a bill become law in Italy? The Constitution (arts. 70–74, 77) prescribes a *de-jure* process: a bill is presented, assigned to a committee, examined, voted in one chamber, and then sent to the other chamber (the *navetta*), until both chambers approve the identical text. Decree-laws must be converted within 60 days. The real process is far messier: bills are merged, abandoned, bounced between the chambers several times, or never examined at all.

We treat each bill as a **case** and each step of its life as an **event**, and use process mining to compare the de-jure with the de-facto process, across **both chambers** (Camera dei Deputati and Senato della Repubblica) and the XVII, XVIII and XIX legislatures (2013 – today).

## Research questions (summary)

1. **Discovery** – what does the real legislative process look like, per chamber and per type of bill (ordinary, constitutional, decree-law conversion)?
2. **Conformance** – how far is the real behaviour from the constitutional model? (incl. the 60-day deadline of decree-laws)
3. **Performance** – where are the bottlenecks (assignment, committee, floor, waiting between chambers)?
4. **Bicameral analysis** – how often and how long does a bill "ping-pong" between chambers, and what differentiates bills that become law from those that die?
5. **Deviance / root cause** – which attributes (initiative, type, legislature, committee) explain slow or failed bills?

## Data

| Source | What | Licence |
|---|---|---|
| [dati.camera.it](https://dati.camera.it/ocd/dump/) (RDF dumps) | bills (`atto`), iter states (`statoIter`), committee assignments, transmissions between chambers | CC BY-SA 4.0 |
| [dati.senato.it](https://dati.senato.it/sparql) (SPARQL) | bills (`ddl`), iter grouping of readings, committee assignments, last known state | CC BY 3.0 (see `data/DATA_NOTES.md`) |

Size after integration: **18,269 cases (iters) and ≈100,000 events** (legislatures XVII–XIX); 1,268 cases involve events in both chambers.
Full description of how the data was downloaded, integrated and what its limits are: [`data/DATA_NOTES.md`](data/DATA_NOTES.md).

## Repository layout

```
data/raw/camera/      original Camera dumps (zip) + SHA256SUMS.txt + RETRIEVED_AT.txt
data/raw/senato/      Senato extraction (ddl.csv, assegnazioni.csv, iter.csv), queries/ and MANIFEST.json
data/processed/       iter_camera.csv (Camera only), unified_log.csv + cases.csv (Camera + Senato)
scripts/              download_all.sh, extract_senato.py, build_event_log.py, build_unified_log.py
scripts/exploration/  probes used to understand the two data sources (outputs in docs/)
docs/                 raw outputs of the checks run while building the dataset
```

## Reproduce

```bash
bash scripts/download_all.sh            # downloads Camera dumps + extracts Senato data (~5 min)
python3 scripts/build_event_log.py --raw data/raw/camera --out data/processed/iter_camera.csv
python3 scripts/build_unified_log.py    # -> data/processed/unified_log.csv, cases.csv (needs only the standard library)
```

Tools for the analysis: PM4Py (main), Disco / ProM for exploratory visualisation.

## Related work

Cross-Organizational Analysis of Parliamentary Processes (arXiv:2508.10381) applies process mining to three German state parliaments (unicameral; performance and deviance analysis). Our work adds process discovery, conformance checking against the constitutional model, and the bicameral dimension.
