#!/usr/bin/env python3
"""Sonda sul Linked Open Data del Senato (dati.senato.it). Solo libreria standard.
Scrive tutto in senato_probe_output.txt (da condividere con Claude)."""
import json, re, sys, urllib.request, urllib.parse, urllib.error
OUT = open("senato_probe_output.txt", "w", encoding="utf-8")
def p(*a):
    s = " ".join(str(x) for x in a); print(s); OUT.write(s + "\n"); OUT.flush()
UA = {"User-Agent": "Mozilla/5.0 (PODS-UPC student project)"}

def get(url, accept=None, timeout=90):
    h = dict(UA); 
    if accept: h["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
        return r.status, r.geturl(), r.read()

def sparql(q):
    for base in ("https://dati.senato.it/sparql", "http://dati.senato.it/sparql"):
        url = base + "?" + urllib.parse.urlencode({"query": q, "format": "application/sparql-results+json"})
        try:
            st, final, body = get(url, "application/sparql-results+json")
            return json.loads(body)["results"]["bindings"], base
        except urllib.error.HTTPError as e:
            p("   HTTP", e.code, e.reason, "su", base)
        except Exception as e:
            p("   ERRORE", type(e).__name__, str(e)[:120], "su", base)
    return None, None

p("=== 1) Pagine web: link di download ===")
for u in ["https://dati.senato.it/", "http://dati.senato.it/DatiSenato/browse/7?testo_generico=12&legislatura=17",
          "http://dati.senato.it/DatiSenato/browse/6?testo_generico=11&legislatura=13"]:
    p("\n--", u)
    try:
        st, final, body = get(u); html = body.decode("utf-8", "replace")
        p("   status", st, "->", final, "| bytes", len(body))
        t = re.search(r"<title>(.*?)</title>", html, re.S); p("   title:", t.group(1).strip()[:100] if t else "-")
        links = sorted(set(re.findall(r'href="([^"]+)"', html)))
        keep = [l for l in links if re.search(r"download|dump|zip|rdf|csv|json|xml|sparql|ddl|iter|browse", l, re.I)]
        for l in keep[:60]: p("   ", l)
        p("   (", len(links), "link totali,", len(keep), "rilevanti )")
    except Exception as e:
        p("   ERRORE", type(e).__name__, str(e)[:150])

p("\n=== 2) SPARQL: classi presenti ===")
rows, base = sparql("SELECT DISTINCT ?c WHERE { ?s a ?c } LIMIT 80")
classes = []
if rows:
    p("endpoint funzionante:", base)
    classes = [r["c"]["value"] for r in rows]
    for c in classes: p("  ", c)

p("\n=== 3) Proprieta' di un esempio per le classi rilevanti (ddl / iter / fase) ===")
for c in [c for c in classes if re.search(r"ddl|iter|fase|statoddl|presentazione", c, re.I)][:8]:
    p("\n-- classe", c)
    rr, _ = sparql("SELECT ?s ?p ?o WHERE { { SELECT ?s WHERE { ?s a <%s> } LIMIT 1 } ?s ?p ?o } LIMIT 40" % c)
    for r in (rr or []):
        p("  ", r["p"]["value"].replace("http://dati.senato.it/osr/", "osr:"), "=", r["o"]["value"][:110])
p("\nFine sonda.")
