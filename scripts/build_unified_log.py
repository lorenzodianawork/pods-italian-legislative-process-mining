#!/usr/bin/env python3
"""Costruisce il log eventi UNIFICATO Camera + Senato (legislature XVII-XIX).

Case  = un "iter" (tutte le letture della stessa legge nei due rami) = idDdl del Senato.
Eventi Camera = data/processed/iter_camera.csv (statoIter + assegnazioni + trasmissioni),
                agganciati al case tramite (legislatura, numero): atto Camera ac{leg}_{n} <-> Senato fase "C.{n}".
Eventi Senato = solo per le letture con ramo S (le righe ramo C del Senato duplicano la Camera: non si contano):
                presentazione/presa in carico, assegnazioni a commissione, ultimo stato noto.

Uso (dalla radice del repo):  python3 scripts/build_unified_log.py
Output: data/processed/unified_log.csv, data/processed/cases.csv (+ unified_log.xes se pm4py e' installato)
"""
import csv, re, html, collections, datetime as dt, sys

RAW = "data/raw/senato/"
CAM = "data/processed/iter_camera.csv"
OUT_LOG = "data/processed/unified_log.csv"
OUT_CASES = "data/processed/cases.csv"
FASE = re.compile(r"^([CS])\.(\d+)(-[A-Za-z]+)?$")
LEG_ROMAN = {"17": "XVII", "18": "XVIII", "19": "XIX"}
ROMAN_LEG = {v: k for k, v in LEG_ROMAN.items()}

ddl = [d for d in csv.DictReader(open(RAW + "ddl.csv", encoding="utf-8")) if d["legislatura"] in LEG_ROMAN]
by_uri = {d["ddl"]: d for d in ddl}
by_iter = collections.defaultdict(list)
for d in ddl:
    by_iter[d["idDdl"]].append(d)


def prog(d):
    try:
        return int(d["progressivoIter"])
    except ValueError:
        return 99


# --- mappa atto Camera -> (case, lettura) ---
atto2case = {}
for idd, rows in by_iter.items():
    for d in rows:
        m = FASE.match(d["fase"])
        if d["ramo"] == "C" and m:  # include le riletture: Camera ac17_1248-B <-> Senato C.1248-B
            atto2case["ac%s_%s%s" % (d["legislatura"], m.group(2), (m.group(3) or "").upper())] = (idd, prog(d), d["fase"])

events = []  # (case, date, reading, rank, chamber, activity, resource, source, fase)
orphan = 0
camera_seen = set()
for i, r in enumerate(csv.DictReader(open(CAM, encoding="utf-8"))):
    key = atto2case.get(r["case_id"])
    if not key:
        orphan += 1
        continue
    idd, rd, fase = key
    camera_seen.add(r["case_id"])
    events.append((idd, r["timestamp"], rd, 10 + i * 1e-9, "C", "C: " + r["activity"], "", "camera/" + r["source"], fase))

# --- eventi Senato (solo letture con ramo S) ---
assegn = collections.defaultdict(list)
for a in csv.DictReader(open(RAW + "assegnazioni.csv", encoding="utf-8")):
    assegn[a["ddl"]].append(a)
for idd, rows in by_iter.items():
    for d in rows:
        if d["ramo"] != "S":
            continue
        rd = prog(d)
        act = "S: Presentazione" if d["presentatoTrasmesso"] == "presentato" else "S: Presa in carico (trasmesso dalla Camera)"
        events.append((idd, d["dataPresentazione"], rd, 0, "S", act, "", "senato/ddl", d["fase"]))
        for a in assegn.get(d["ddl"], []):
            tipo = a["sede"] or a["tipoCommissione"] or "n.d."
            events.append((idd, a["dataAssegnazione"], rd, 5, "S", "S: Assegnazione commissione (%s)" % tipo,
                           html.unescape(a["label"] or a["organo"]), "senato/assegnazione", d["fase"]))
        if d["statoDdl"] and d["dataStatoDdl"]:
            events.append((idd, d["dataStatoDdl"], rd, 20, "S", "S: Stato - " + d["statoDdl"], "", "senato/statoDdl", d["fase"]))

# --- ordina, deduplica, scrivi ---
by_case = collections.defaultdict(list)
for e in events:
    if e[1]:
        by_case[e[0]].append(e)
rows_out, cases = [], []
for idd, evs in by_case.items():
    evs.sort(key=lambda e: (e[1], e[2], e[3]))
    seen, clean = set(), []
    for e in evs:
        k = (e[1], e[5], e[6], e[8])
        if k in seen:
            continue
        seen.add(k)
        clean.append(e)
    rd = by_iter[idd]
    leg = rd[0]["legislatura"]
    cid = "L%s_iter%s" % (leg, idd)
    for e in clean:
        rows_out.append([cid, LEG_ROMAN[leg], e[1], e[5], e[4], e[2], e[6], e[7], e[8]])
    rd_sorted = sorted(rd, key=prog)
    t0, t1 = clean[0][1], clean[-1][1]
    days = (dt.date.fromisoformat(t1) - dt.date.fromisoformat(t0)).days
    stati = [d["statoDdl"] for d in rd_sorted]
    cases.append([cid, LEG_ROMAN[leg], idd, len(rd_sorted), len(rd_sorted) - 1, rd_sorted[0]["ramo"],
                  "".join(sorted({d["ramo"] for d in rd_sorted})), rd_sorted[0]["natura"],
                  int(rd_sorted[0]["natura"].startswith("di conversione")), stati[-1],
                  int(any("Legge" in s for s in stati)), len(clean), t0, t1, days])

rows_out.sort(key=lambda r: (r[0], r[2]))  # stabile: mantiene l'ordine logico dentro lo stesso giorno
with open(OUT_LOG, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["case_id", "legislatura", "timestamp", "activity", "chamber", "reading", "resource", "source", "fase"])
    w.writerows(rows_out)
with open(OUT_CASES, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["case_id", "legislatura", "idDdl", "n_readings", "n_navette", "first_chamber", "chambers", "natura",
                "is_decree_law", "last_senato_state", "senato_says_law", "n_events", "start", "end", "duration_days"])
    w.writerows(cases)

print("eventi:", len(rows_out), "| cases:", len(cases), "| atti Camera orfani (non agganciati):", orphan)
print("atti Camera agganciati:", len(camera_seen), "/", len(atto2case))
print("eventi per ramo:", dict(collections.Counter(r[4] for r in rows_out)))
print("cases per legislatura:", dict(collections.Counter(c[1] for c in cases)))
print("cases per n_readings:", dict(sorted(collections.Counter(c[3] for c in cases).items())))
chs = collections.defaultdict(set)
for r in rows_out:
    chs[r[0]].add(r[4])
print("cases con eventi di entrambi i rami:", sum(1 for v in chs.values() if len(v) == 2))
print("decreti-legge (natura):", sum(c[8] for c in cases))
print("top attivita':", collections.Counter(r[3] for r in rows_out).most_common(12))
print("assegnazioni Senato per sede:", collections.Counter(r[3] for r in rows_out if "Assegnazione" in r[3]).most_common())

try:
    import pandas as pd, pm4py
    df = pd.read_csv(OUT_LOG)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = pm4py.format_dataframe(df, case_id="case_id", activity_key="activity", timestamp_key="timestamp")
    pm4py.write_xes(df, "data/processed/unified_log.xes")
    print("XES scritto: data/processed/unified_log.xes")
except Exception as ex:
    print("XES non scritto (%s): ok, usa il CSV o installa pm4py" % type(ex).__name__)
