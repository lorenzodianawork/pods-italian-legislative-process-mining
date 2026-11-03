#!/usr/bin/env python3
"""Sonda 3 Senato: verifica che IterDdl = sequenza delle letture (navetta). Scrive senato_probe3_output.txt"""
import json, urllib.request, urllib.parse, urllib.error, time
OUT = open("senato_probe3_output.txt", "w", encoding="utf-8")
def p(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n"); OUT.flush()
EP = "https://dati.senato.it/sparql"
PFX = "PREFIX osr: <http://dati.senato.it/osr/>\n"
def q(title, query, maxrows=40):
    p("\n--", title)
    url = EP + "?" + urllib.parse.urlencode({"query": PFX + query, "format": "application/sparql-results+json"})
    t = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json", "User-Agent": "Mozilla/5.0 (PODS-UPC student project)"})
        with urllib.request.urlopen(req, timeout=150) as r: rows = json.load(r)["results"]["bindings"]
    except urllib.error.HTTPError as e:
        p("   HTTP", e.code, e.reason, "|", e.read()[:300].decode("utf-8", "replace").replace("\n", " ")); return
    except Exception as e:
        p("   ERRORE", type(e).__name__, str(e)[:200]); return
    p("   %d righe in %.1fs" % (len(rows), time.time() - t))
    for r in rows[:maxrows]:
        p("  ", " | ".join("%s=%s" % (k, v["value"].replace("http://dati.senato.it/osr/", "osr:").replace("http://dati.senato.it/ddl/", "ddl/")[:90]) for k, v in r.items()))

MEMB = """SELECT ?prog ?m ?ramo ?pt ?dp ?st ?dst ?fase WHERE {
  ?it a osr:IterDdl ; osr:idDdl %s ; osr:fase ?f . ?f osr:ddl ?m ; osr:progrIter ?prog .
  ?m osr:ramo ?ramo ; osr:presentatoTrasmesso ?pt ; osr:dataPresentazione ?dp ; osr:statoDdl ?st ; osr:dataStatoDdl ?dst ; osr:fase ?fase } ORDER BY ?prog"""
q("A) Membri dell'iter ancorato al ddl 41899 (XVII)", MEMB % 41899)
q("B) Leggi approvate XVII (campione) con numero e data legge", "SELECT ?d ?id ?num ?dl ?fase WHERE { ?d osr:legislatura 17 ; osr:numeroLegge ?num ; osr:dataLegge ?dl ; osr:idDdl ?id ; osr:fase ?fase } LIMIT 6")
q("C) Distribuzione: numero di letture (FaseIter) per iter", "SELECT ?n (COUNT(*) AS ?iter) WHERE { SELECT ?it (COUNT(?f) AS ?n) WHERE { ?it a osr:IterDdl ; osr:fase ?f } GROUP BY ?it } GROUP BY ?n ORDER BY ?n", 30)
q("D) Totale IterDdl", "SELECT (COUNT(*) AS ?n) WHERE { ?it a osr:IterDdl }")
q("E) Proprieta' SedutaAssemblea (campione)", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?s WHERE { ?s a osr:SedutaAssemblea } LIMIT 1500 } ?s ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("F) Proprieta' Votazione (campione)", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?s WHERE { ?s a osr:Votazione } LIMIT 1500 } ?s ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("G) Proprieta' SedutaCommissione (campione)", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?s WHERE { ?s a osr:SedutaCommissione } LIMIT 1500 } ?s ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("H) Ddl XVII con ramo=C: sono gli stessi atti della Camera? (campione con sameAs/titolo/fase)", "SELECT ?d ?fase ?pt ?dp ?t WHERE { ?d osr:legislatura 17 ; osr:ramo 'C' ; osr:fase ?fase ; osr:presentatoTrasmesso ?pt ; osr:dataPresentazione ?dp ; osr:titolo ?t } LIMIT 8")
q("I) Limite righe: quante righe restituisce una query senza LIMIT (ddl XIX)", "SELECT ?d WHERE { ?d a osr:Ddl ; osr:legislatura 19 }", 3)
p("\nFine sonda 3.")
