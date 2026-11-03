#!/usr/bin/env python3
"""
PODS - costruzione dell'event log dell'iter legislativo (Camera, legislature XVII-XIX)
a partire dai dump RDF ufficiali (zip in data/raw/camera/, scaricati con scripts/download_all.sh).
Case = atto Camera (progetto di legge); activity = stato iter / assegnazione / trasmissione; timestamp = data (solo giorno).
Uso (dalla radice del repo):  python3 scripts/build_event_log.py
Output: data/processed/iter_camera.csv (+ .xes se pm4py e' installato)
"""
import re, collections, statistics, csv, datetime as dt, zipfile, io, argparse, os
ap = argparse.ArgumentParser()
ap.add_argument("--raw", default="data/raw/camera", help="cartella con gli zip della Camera")
ap.add_argument("--out", default="data/processed/iter_camera.csv")
ARGS = ap.parse_args()
LINE = re.compile(r'^<([^>]+)>\t<([^>]+)>\t(.*) \.\s*$')
def triples(fn):
    """fn = nome del file come nel dump (es. 'atto.rdf'): si legge in streaming da <raw>/<fn>.zip"""
    with zipfile.ZipFile(os.path.join(ARGS.raw, fn + ".zip")) as z:
        with z.open(z.namelist()[0]) as fh:
            for line in io.TextIOWrapper(fh, encoding='utf-8', errors='replace'):
                m = LINE.match(line)
                if m: yield m.groups()
def lit(o): return o.split('"')[1] if o.startswith('"') else o.strip('<>')
def key(p): return p.rsplit('/',1)[-1].rsplit('#',1)[-1]

# 1) atti
ATTO_KEEP = {'rif_leg','rif_statoIter','rif_assegnazione','rif_trasmissione','iniziativa','date','title'}
atti = collections.defaultdict(lambda: collections.defaultdict(list))
for fn in ('atto.rdf','atto-19.rdf'):
    for s,p,o in triples(fn):
        k = key(p)
        if k in ATTO_KEEP: atti[s][k].append(lit(o))
LEGS = {'repubblica_17':'XVII','repubblica_18':'XVIII','repubblica_19':'XIX'}
atti = {s:d for s,d in atti.items() if d.get('rif_leg') and d['rif_leg'][0].rsplit('/',1)[-1] in LEGS}
print("atti XVII-XIX:", len(atti))

# 2) eventi (stato, assegnazione, trasmissione)
def load(fns, wanted):
    out = collections.defaultdict(dict)
    for fn in fns:
        for s,p,o in triples(fn):
            k = key(p)
            if k in wanted and not p.endswith('22-rdf-syntax-ns#type'): out[s].setdefault(k, lit(o))
    return out
stato  = load(('statoIter.rdf','statoIter-19.rdf'), {'type','date','label'})
assegn = load(('assegnazione.rdf','assegnazione-19.rdf'), {'date','sede','label'})
assegn_org = collections.defaultdict(list)
for fn in ('assegnazione.rdf','assegnazione-19.rdf'):
    for s,p,o in triples(fn):
        if key(p)=='rif_organo': assegn_org[s].append(lit(o).rsplit('/',1)[-1])
trasm  = load(('trasmissione.rdf','trasmissione-19.rdf'), {'date','provenance','label'})

ORDER = [("Da assegnare",0),("Assegn",1),("In corso di esame",2),("Concluso l'esame",3),("In stato di relazione",3),
         ("In discussione",4),("Rinviato dall",4.5),("Esame in",4),("Approvato, segue Navette",6.5),("Navetta",7),
         ("Approvato definitivamente",8),("Approvato",6),("Ritirato",9),("Assorbit",9),("decaduto",9),("Respinto",9),
         ("Cancellato",9),("Conclusione anomala",9),("Restituito",9),("Non raggiunto",9),("Ricevimento",8.5),("Rinviato alle Camere",8.5)]
def rank(a):
    for k,r in ORDER:
        if k.lower() in a.lower(): return r
    return 5

rows = []
for a,d in atti.items():
    case = a.rsplit('/',1)[-1]
    leg = LEGS[d['rif_leg'][0].rsplit('/',1)[-1]]
    ini = (d.get('iniziativa') or [''])[0]
    for sid in d.get('rif_statoIter',[]):
        s = stato.get(sid)
        if s and s.get('date') and s.get('type'):
            rows.append((case,leg,ini,'statoIter',s['type'],s['date']))
    for sid in d.get('rif_assegnazione',[]):
        s = assegn.get(sid)
        if s and s.get('date'):
            rows.append((case,leg,ini,'assegnazione','Assegnazione in Commissione (sede %s)'%s.get('sede','?'),s['date']))
    for sid in d.get('rif_trasmissione',[]):
        s = trasm.get(sid)
        if s and s.get('date'):
            rows.append((case,leg,ini,'trasmissione','Navetta: trasmesso dalla %s'%s.get('provenance','?'),s['date']))

# dedupe + ordinamento (data, poi rango logico: la data ha solo precisione giornaliera)
seen=set(); ev=[]
for r in rows:
    if r in seen: continue
    seen.add(r)
    try: ts = dt.datetime.strptime(r[5],'%Y%m%d')
    except ValueError: continue
    ev.append((r[0],r[1],r[2],r[3],r[4],ts))
ev.sort(key=lambda e:(e[0],e[5],rank(e[4])))
with open(ARGS.out,'w',newline='',encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['case_id','legislatura','iniziativa','source','activity','timestamp'])
    for e in ev: w.writerow([*e[:5], e[5].strftime('%Y-%m-%d')])

# 3) statistiche
cases = collections.defaultdict(list)
for e in ev: cases[e[0]].append(e)
print("\nEVENT LOG:", len(ev), "eventi |", len(cases), "casi con >=1 evento |", len(set(e[4] for e in ev)), "attivita' distinte")
print("eventi per fonte:", dict(collections.Counter(e[3] for e in ev)))
for leg in ('XVII','XVIII','XIX'):
    cs = [c for c,v in cases.items() if v[0][1]==leg]
    n = [len(cases[c]) for c in cs]; dur = [(cases[c][-1][5]-cases[c][0][5]).days for c in cs]
    print(f"  {leg}: {len(cs)} casi | eventi/caso media {statistics.mean(n):.1f} | durata mediana {statistics.median(dur)} gg | >=6 eventi: {sum(1 for x in n if x>=6)} | con navetta: {sum(1 for c in cs if any(e[3]=='trasmissione' for e in cases[c]))}")
var = collections.Counter(tuple(e[4] for e in v) for v in cases.values())
print("\nvarianti distinte:", len(var), "| copertura top-10:", f"{sum(n for _,n in var.most_common(10))/len(cases):.0%}")
for v,n in var.most_common(6): print(f"  {n:>5}  " + " > ".join(v)[:170])
fin = collections.Counter(v[-1][4] for v in cases.values())
print("\nUltimo stato (esito):"); [print(f"  {n:>5}  {a}") for a,n in fin.most_common(10)]

try:
    import pandas as pd, pm4py
    df = pd.read_csv(ARGS.out, parse_dates=['timestamp'])
    df = df.rename(columns={'case_id':'case:concept:name','activity':'concept:name','timestamp':'time:timestamp'})
    pm4py.write_xes(pm4py.format_dataframe(df, case_id='case:concept:name', activity_key='concept:name', timestamp_key='time:timestamp'), ARGS.out.replace('.csv', '.xes'))
    print("\nscritto XES")
except Exception as ex:
    print("\n(XES non scritto:", ex, ")")
