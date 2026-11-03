#!/usr/bin/env python3
"""Sonda 4: quale costrutto SPARQL fa scattare il 403 del filtro web del Senato? Scrive docs/senato_probe4_output.txt
Uso (dalla radice del repo): python3 scripts/exploration/probe_senato4.py"""
import json, time, urllib.request, urllib.parse, urllib.error
OUT = open("docs/senato_probe4_output.txt", "w", encoding="utf-8")
def p(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n"); OUT.flush()
EP = "https://dati.senato.it/sparql"
PFX = "PREFIX osr: <http://dati.senato.it/osr/>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
def t(name, query, show=2):
    url = EP + "?" + urllib.parse.urlencode({"query": PFX + query, "format": "application/sparql-results+json"})
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/sparql-results+json", "User-Agent": "Mozilla/5.0 (PODS-UPC student project)"})
        with urllib.request.urlopen(req, timeout=170) as r: rows = json.load(r)["results"]["bindings"]
        p("OK   %-46s %6d righe %5.1fs  url=%d" % (name, len(rows), time.time() - t0, len(url)))
        for r in rows[:show]: p("       ", {k: v["value"][-40:] for k, v in r.items()})
    except urllib.error.HTTPError as e:
        p("HTTP %d %-42s url=%d" % (e.code, name, len(url)))
    except Exception as e:
        p("ERR  %-46s %s" % (name, type(e).__name__))
    time.sleep(1.0)

BASE = "?d a osr:Ddl ; osr:legislatura 17 ; osr:assegnazione ?a . ?a osr:dataAssegnazione ?da ."
OPT = " OPTIONAL { ?a osr:organo ?organo } OPTIONAL { ?a rdfs:label ?label } OPTIONAL { ?a osr:sede ?sede } OPTIONAL { ?a osr:tipoCommissione ?tipo }"
ID = 'xsd:integer(STRAFTER(STR(?d), "/ddl/"))'
t("A base (3 var), LIMIT 5",                "SELECT ?d ?da WHERE { %s } LIMIT 5" % BASE)
t("B base + 4 OPTIONAL, LIMIT 5",            "SELECT ?d ?da ?organo ?label ?sede ?tipo WHERE { %s %s } LIMIT 5" % (BASE, OPT))
t("C FILTER semplice STRAFTER >= (no &&)",   "SELECT ?d ?da WHERE { %s FILTER(%s >= 45000) } LIMIT 5" % (BASE, ID))
t("D due FILTER separati (>= e <=)",         "SELECT ?d ?da WHERE { %s FILTER(%s >= 45000) FILTER(%s <= 46000) } LIMIT 5" % (BASE, ID, ID))
t("E un FILTER con &&",                      "SELECT ?d ?da WHERE { %s FILTER(%s >= 45000 && %s <= 46000) } LIMIT 5" % (BASE, ID, ID))
t("F FILTER su data assegnazione (stringa)", 'SELECT ?d ?da WHERE { %s FILTER(STR(?da) >= "2014-01-01") FILTER(STR(?da) < "2014-04-01") } LIMIT 5' % BASE)
t("G FILTER ?d = <IRI>",                     "SELECT ?d ?da WHERE { %s FILTER(?d = <http://dati.senato.it/ddl/45397>) } LIMIT 5" % BASE)
t("H FILTER ?d IN (<IRI>,<IRI>)",            "SELECT ?d ?da WHERE { %s FILTER(?d IN (<http://dati.senato.it/ddl/45397>, <http://dati.senato.it/ddl/45398>)) } LIMIT 5" % BASE)
t("I COUNT assegnazioni leg 17",             "SELECT (COUNT(*) AS ?n) WHERE { ?d a osr:Ddl ; osr:legislatura 17 ; osr:assegnazione ?a }")
t("J leg 17 intera, LIMIT 100000 (cap righe?)", "SELECT ?d ?da ?organo ?sede WHERE { %s OPTIONAL { ?a osr:organo ?organo } OPTIONAL { ?a osr:sede ?sede } } LIMIT 100000" % BASE, show=0)
t("K iter leg 17 intera, LIMIT 100000",      "SELECT ?idDdl ?prog ?d WHERE { ?it a osr:IterDdl ; osr:idDdl ?idDdl ; osr:fase ?f . ?f osr:ddl ?d ; osr:progrIter ?prog . ?d osr:legislatura 17 } LIMIT 100000", show=0)
t("L iter con FILTER STRAFTER (due filter)", "SELECT ?idDdl ?prog ?d WHERE { ?it a osr:IterDdl ; osr:idDdl ?idDdl ; osr:fase ?f . ?f osr:ddl ?d ; osr:progrIter ?prog . ?d osr:legislatura 17 FILTER(%s >= 45000) FILTER(%s <= 45300) } LIMIT 50" % (ID, ID))
p("\nFine sonda 4.")
