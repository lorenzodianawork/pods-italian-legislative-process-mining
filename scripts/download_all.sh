#!/bin/bash
# Scarica TUTTI i dati del progetto: dump RDF della Camera (zip originali) + estrazione SPARQL dal Senato.
# Uso (dalla radice del repo):  bash scripts/download_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw/camera data/raw/senato data/processed
BASE="https://dati.camera.it/ocd/dump"
echo "== Camera: dump RDF (CC BY-SA 4.0) =="
for f in atto atto-19 assegnazione assegnazione-19 trasmissione trasmissione-19 statoIter statoIter-19; do
  if [ -f "data/raw/camera/$f.rdf.zip" ]; then echo "  gia' presente: $f.rdf.zip"; continue; fi
  curl -fSL --retry 3 -o "data/raw/camera/$f.rdf.zip" "$BASE/$f.rdf.zip" && echo "  scaricato: $f.rdf.zip ($(du -h data/raw/camera/$f.rdf.zip | cut -f1))"
done
( cd data/raw/camera
  if command -v shasum >/dev/null; then shasum -a 256 *.zip > SHA256SUMS.txt; else sha256sum *.zip > SHA256SUMS.txt; fi
  date -u +%Y-%m-%dT%H:%M:%SZ > RETRIEVED_AT.txt )
echo; echo "== Senato: estrazione SPARQL =="
python3 scripts/extract_senato.py
echo; echo "Fatto. Prossimo passo: python3 scripts/build_event_log.py"
