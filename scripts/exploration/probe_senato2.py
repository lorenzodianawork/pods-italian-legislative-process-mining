#!/usr/bin/env python3
"""Sonda 2 sul Senato: struttura delle fasi dell'iter, stati, legislature, legame con la Camera.
Scrive in senato_probe2_output.txt"""
import json, urllib.request, urllib.parse, urllib.error, time
OUT = open("senato_probe2_output.txt", "w", encoding="utf-8")
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
        p("  ", " | ".join("%s=%s" % (k, v["value"].replace("http://dati.senato.it/osr/", "osr:")[:110]) for k, v in r.items()))

q("1) Ddl per legislatura", "SELECT ?l (COUNT(*) AS ?n) WHERE { ?d a osr:Ddl ; osr:legislatura ?l } GROUP BY ?l ORDER BY ?l", 40)
q("2) Proprieta' dei nodi-fase (via IterDdl.fase), campione 3000", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?f WHERE { ?it a osr:IterDdl ; osr:fase ?f } LIMIT 3000 } ?f ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("3) Proprieta' dei FaseIter (classe), campione 3000", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?f WHERE { ?f a osr:FaseIter } LIMIT 3000 } ?f ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("4) Iter completo di un ddl (id 23349): tutte le fasi con le loro proprieta'", "SELECT ?f ?p ?o WHERE { ?it a osr:IterDdl ; osr:idDdl 23349 ; osr:fase ?f . ?f ?p ?o } LIMIT 80", 80)
q("5) Iter di un ddl della XVII (campione): fasi con proprieta'", "SELECT ?d ?f ?p ?o WHERE { { SELECT ?d WHERE { ?d a osr:Ddl ; osr:legislatura 17 ; osr:statoDdl ?s . FILTER(CONTAINS(LCASE(?s),'approvato')) } LIMIT 1 } ?d osr:idDdl ?id . ?it a osr:IterDdl ; osr:idDdl ?id ; osr:fase ?f . ?f ?p ?o } LIMIT 80", 80)
q("6) Proprieta' di Ddl (campione 3000)", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?d WHERE { ?d a osr:Ddl } LIMIT 3000 } ?d ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("7) Valori di statoDdl (XVII)", "SELECT ?s (COUNT(*) AS ?n) WHERE { ?d a osr:Ddl ; osr:legislatura 17 ; osr:statoDdl ?s } GROUP BY ?s ORDER BY DESC(?n)", 40)
q("8) presentato/trasmesso x ramo (XVII)", "SELECT ?pt ?r (COUNT(*) AS ?n) WHERE { ?d a osr:Ddl ; osr:legislatura 17 ; osr:presentatoTrasmesso ?pt ; osr:ramo ?r } GROUP BY ?pt ?r", 20)
q("9) Proprieta' di Assegnazione (campione 2000)", "SELECT ?p (COUNT(*) AS ?n) WHERE { { SELECT ?a WHERE { ?a a osr:Assegnazione } LIMIT 2000 } ?a ?p ?o } GROUP BY ?p ORDER BY DESC(?n)")
q("10) Esempio di Assegnazione", "SELECT ?p ?o WHERE { { SELECT ?a WHERE { ?a a osr:Assegnazione } LIMIT 1 } ?a ?p ?o } LIMIT 30")
q("11) Proprieta' di SedutaAssemblea e Votazione (campione)", "SELECT ?c ?p (COUNT(*) AS ?n) WHERE { { SELECT ?s ?c WHERE { VALUES ?c { osr:SedutaAssemblea osr:Votazione osr:Procedura } ?s a ?c } LIMIT 1500 } ?s ?p ?o } GROUP BY ?c ?p ORDER BY ?c DESC(?n)", 60)
p("\nFine sonda 2.")
