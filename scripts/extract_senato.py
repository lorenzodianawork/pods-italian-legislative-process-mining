#!/usr/bin/env python3
"""
Estrazione dal Linked Open Data del Senato (endpoint SPARQL https://dati.senato.it/sparql).
Produce in data/raw/senato/:  ddl.csv, assegnazioni.csv, iter.csv, queries/*.rq, MANIFEST.json
Uso (dalla radice del repo):  python3 scripts/extract_senato.py [--legs 17 18 19]

Vincoli dell'endpoint scoperti con le sonde (vedi docs/ e scripts/exploration/):
- l'endpoint taglia SILENZIOSAMENTE i risultati a 10.000 righe  -> ogni query deve restare sotto; lo script lo controlla;
- il filtro web risponde 403 a STRAFTER()/STR() su ?d con "/ddl/" e ad URL molto lunghi (>~4 KB) -> si usano finestre di date;
- le POST sono rifiutate (403) -> solo GET.
Solo libreria standard Python.
"""
import argparse, csv, datetime, json, os, time, urllib.parse, urllib.request, urllib.error

EP = "https://dati.senato.it/sparql"
PFX = ("PREFIX osr: <http://dati.senato.it/osr/>\n"
       "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n")
OUT = "data/raw/senato"
CAP = 10000
LEG_YEARS = {16: (2008, 2013), 17: (2013, 2018), 18: (2018, 2022), 19: (2022, 2026)}

Q_COUNT = "SELECT (COUNT(*) AS ?n) WHERE { ?d a osr:Ddl ; osr:legislatura @LEG@ }"
Q_DDL = """SELECT ?d ?idDdl ?ramo ?pt ?dp ?fase ?nf ?stato ?dstato ?natura ?prog ?titolo ?nleg ?dleg WHERE {
  ?d a osr:Ddl ; osr:legislatura @LEG@ ; osr:idDdl ?idDdl ; osr:ramo ?ramo ;
     osr:presentatoTrasmesso ?pt ; osr:dataPresentazione ?dp ; osr:fase ?fase .
  OPTIONAL { ?d osr:numeroFase ?nf }    OPTIONAL { ?d osr:statoDdl ?stato }
  OPTIONAL { ?d osr:dataStatoDdl ?dstato } OPTIONAL { ?d osr:natura ?natura }
  OPTIONAL { ?d osr:progressivoIter ?prog } OPTIONAL { ?d osr:titolo ?titolo }
  OPTIONAL { ?d osr:numeroLegge ?nleg }  OPTIONAL { ?d osr:dataLegge ?dleg }
}"""
ASSEG_BODY = """?d a osr:Ddl ; osr:legislatura @LEG@ ; osr:assegnazione ?a . ?a osr:dataAssegnazione ?da .
  OPTIONAL { ?a osr:organo ?organo } OPTIONAL { ?a rdfs:label ?label }
  OPTIONAL { ?a osr:sede ?sede }     OPTIONAL { ?a osr:tipoCommissione ?tipo }"""
Q_ASSEG = "SELECT ?d ?da ?organo ?label ?sede ?tipo WHERE {\n  " + ASSEG_BODY + '\n  FILTER(STR(?da) >= "@D0@") FILTER(STR(?da) < "@D1@")\n}'
Q_ASSEG_COUNT = "SELECT (COUNT(*) AS ?n) WHERE {\n  " + ASSEG_BODY + "\n}"
Q_ITER = """SELECT ?idDdl ?prog ?d WHERE {
  ?it a osr:IterDdl ; osr:idDdl ?idDdl ; osr:fase ?f . ?f osr:ddl ?d ; osr:progrIter ?prog . ?d osr:legislatura @LEG@
}"""

def run(query):
    url = EP + "?" + urllib.parse.urlencode({"query": PFX + query, "format": "application/sparql-results+json"})
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json", "User-Agent": "Mozilla/5.0 (PODS-UPC student project)"})
            with urllib.request.urlopen(req, timeout=180) as r:
                rows = json.load(r)["results"]["bindings"]
            if len(rows) >= CAP: raise SystemExit("Risultato = %d righe: tetto dell'endpoint raggiunto, dati TRONCATI. Query:\n%s" % (len(rows), query[:500]))
            return rows
        except urllib.error.HTTPError as e:
            if e.code in (400, 403, 404): raise SystemExit("HTTP %s (url=%d caratteri) per la query:\n%s" % (e.code, len(url), query[:600]))
            err = "HTTP %s" % e.code
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            err = type(e).__name__
        wait = 3 * 2 ** attempt
        print("   [retry %d] %s, attendo %ds" % (attempt + 1, err, wait)); time.sleep(wait)
    raise SystemExit("Endpoint non raggiungibile dopo 5 tentativi")

def val(b, k): return b.get(k, {}).get("value", "")

def windows(leg):
    y0, y1 = LEG_YEARS.get(leg, (2008, 2026)); y0 -= 1; y1 += 1
    yield ("0000-01-01", "%04d-01-01" % y0)                      # coda precedente
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            yield ("%04d-%02d-01" % (y, m), "%04d-%02d-01" % (y + (m == 12), 1 if m == 12 else m + 1))
    yield ("%04d-01-01" % (y1 + 1), "9999-12-31")               # coda successiva

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--legs", nargs="+", type=int, default=[17, 18, 19]); a = ap.parse_args()
    os.makedirs(OUT + "/queries", exist_ok=True)
    for name, q in (("count", Q_COUNT), ("ddl", Q_DDL), ("assegnazioni", Q_ASSEG), ("assegnazioni_count", Q_ASSEG_COUNT), ("iter", Q_ITER)):
        open("%s/queries/%s.rq" % (OUT, name), "w").write(PFX + q + "\n")
    manifest = {"endpoint": EP, "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "legislatures": a.legs, "counts": {}}
    L = lambda q, leg: q.replace("@LEG@", str(leg))

    # 1) ddl (una query per legislatura)
    ddl_rows, seen = [], set()
    for leg in a.legs:
        expected = int(val(run(L(Q_COUNT, leg))[0], "n"))
        rows = run(L(Q_DDL, leg)); n_new = 0
        for b in rows:
            u = val(b, "d")
            if u in seen: continue
            seen.add(u); n_new += 1
            ddl_rows.append([leg, u, val(b,"idDdl"), val(b,"ramo"), val(b,"pt"), val(b,"dp"), val(b,"fase"), val(b,"nf"), val(b,"stato"),
                             val(b,"dstato"), val(b,"natura"), val(b,"prog"), " ".join(val(b,"titolo").split()), val(b,"nleg"), val(b,"dleg")])
        print("leg %d: ddl attesi %d, righe %d, distinti %d%s" % (leg, expected, len(rows), n_new, "" if n_new == expected else "  <-- ATTENZIONE"))
        manifest["counts"]["ddl_leg_%d" % leg] = {"expected": expected, "rows": len(rows), "distinct": n_new}
    with open(OUT + "/ddl.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["legislatura","ddl","idDdl","ramo","presentatoTrasmesso","dataPresentazione","fase","numeroFase",
                                       "statoDdl","dataStatoDdl","natura","progressivoIter","titolo","numeroLegge","dataLegge"]); w.writerows(ddl_rows)

    # 2) iter (una query per legislatura)
    with open(OUT + "/iter.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["idDdl", "progrIter", "ddl"]); si = set(); n_i = 0
        for leg in a.legs:
            for b in run(L(Q_ITER, leg)):
                row = (val(b,"idDdl"), val(b,"prog"), val(b,"d"))
                if row not in si: si.add(row); w.writerow(row); n_i += 1
            print("leg %d: iter cumulati %d" % (leg, n_i))

    # 3) assegnazioni (finestre mensili di date, controllo di completezza contro COUNT)
    n_a = 0; t0 = time.time()
    with open(OUT + "/assegnazioni.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["ddl","dataAssegnazione","organo","label","sede","tipoCommissione"]); sa = set()
        for leg in a.legs:
            expected = int(val(run(L(Q_ASSEG_COUNT, leg))[0], "n")); raw = 0
            for k, (d0, d1) in enumerate(windows(leg)):
                for b in run(L(Q_ASSEG, leg).replace("@D0@", d0).replace("@D1@", d1)):
                    raw += 1
                    row = (val(b,"d"), val(b,"da"), val(b,"organo"), " ".join(val(b,"label").split()), val(b,"sede"), val(b,"tipo"))
                    if row not in sa: sa.add(row); w.writerow(row); n_a += 1
                if k % 24 == 0: print("  leg %d finestra %s | righe grezze %d / %d attese | %.0fs" % (leg, d0, raw, expected, time.time() - t0))
                time.sleep(0.15)
            ok = (raw == expected)
            print("leg %d: assegnazioni righe grezze %d, attese %d -> %s" % (leg, raw, expected, "OK, completo" if ok else "<-- NON COINCIDE"))
            manifest["counts"]["assegnazioni_leg_%d" % leg] = {"expected_rows": expected, "raw_rows": raw, "complete": ok}
    manifest["counts"].update({"ddl_total": len(ddl_rows), "assegnazioni_distinte": n_a, "iter_rows": n_i})
    json.dump(manifest, open(OUT + "/MANIFEST.json", "w"), indent=2)
    print("\nFATTO: %d ddl, %d assegnazioni distinte, %d righe iter -> %s/" % (len(ddl_rows), n_a, n_i, OUT))

if __name__ == "__main__": main()
