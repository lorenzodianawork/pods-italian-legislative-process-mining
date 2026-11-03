#!/usr/bin/env python3
"""Verifica (1) che idDdl raggruppi le letture della stessa legge nel Senato e (2) come agganciare Senato e Camera.
Uso (dalla radice del repo): python3 scripts/exploration/join_check.py   -> stampa a video (output salvato in docs/join_check_output.txt)"""
import csv, re, zipfile, io, collections, statistics
S = "data/raw/senato/"; C = "data/raw/camera/"
ddl = list(csv.DictReader(open(S + "ddl.csv", encoding="utf-8")))
iter_rows = list(csv.DictReader(open(S + "iter.csv", encoding="utf-8")))
print("ddl:", len(ddl), "| iter.csv:", len(iter_rows))

print("\n== 1) Senato: ramo x presentato/trasmesso per legislatura ==")
for leg in ("17", "18", "19"):
    c = collections.Counter((d["ramo"], d["presentatoTrasmesso"]) for d in ddl if d["legislatura"] == leg)
    print("  leg", leg, dict(c))
pat = re.compile(r"^([CS])\.(\d+)(-[A-Za-z]+)?$")
bad = [d["fase"] for d in ddl if not pat.match(d["fase"])]
print("  'fase' non conformi a C.n / S.n[-X]:", len(bad), bad[:5])
print("  ramo coerente col prefisso di fase:", sum(1 for d in ddl if pat.match(d["fase"]) and pat.match(d["fase"]).group(1) == d["ramo"]), "/", len(ddl))
print("  fase con suffisso (-B, -C...) = riletture:", sum(1 for d in ddl if (pat.match(d["fase"]) or [None]*4)[3]), "| per presentatoTrasmesso:",
      dict(collections.Counter(d["presentatoTrasmesso"] for d in ddl if pat.match(d["fase"]) and pat.match(d["fase"]).group(3))))

print("\n== 2) Iter = gruppi per idDdl ==")
grp = collections.defaultdict(list)
for d in ddl: grp[d["idDdl"]].append(d)
size = collections.Counter(len(v) for v in grp.values())
print("  gruppi idDdl:", len(grp), "| dimensione (n letture: n gruppi):", dict(sorted(size.items())[:8]))
ok_prog = ok_date = first_pres = both = alt = multi = 0
for v in grp.values():
    if len(v) < 2: continue
    multi += 1
    v2 = sorted(v, key=lambda d: int(d["progressivoIter"] or 0))
    progs = [int(d["progressivoIter"] or 0) for d in v2]
    ok_prog += progs == list(range(1, len(v) + 1)) or len(set(progs)) == len(progs)
    ds = [d["dataPresentazione"] for d in v2]; ok_date += ds == sorted(ds)
    first_pres += v2[0]["presentatoTrasmesso"] == "presentato"
    rami = [d["ramo"] for d in v2]; both += len(set(rami)) == 2; alt += all(rami[i] != rami[i+1] for i in range(len(rami)-1))
print("  iter con >=2 letture:", multi)
print("   - progressivoIter univoco nel gruppo:", ok_prog, "| date crescenti con progressivo:", ok_date, "| prima lettura 'presentato':", first_pres)
print("   - coinvolgono entrambe le Camere:", both, "| rami alternati C/S a ogni lettura:", alt)
byuri = {d["ddl"]: d for d in ddl}
match = mism = miss = 0
for r in iter_rows:
    d = byuri.get(r["ddl"])
    if not d: miss += 1
    elif d["idDdl"] == r["idDdl"] and d["progressivoIter"] == r["progrIter"]: match += 1
    else: mism += 1
print("  iter.csv vs ddl.csv (idDdl e progressivo coincidono):", match, "| discordanti:", mism, "| ddl non in ddl.csv:", miss)
print("  esempi di iter lungo (>=4 letture):")
for k, v in [(k, v) for k, v in grp.items() if len(v) >= 4][:3]:
    print("   idDdl", k, "->", " > ".join("%s(%s,%s)" % (d["fase"], d["presentatoTrasmesso"][:4], d["dataPresentazione"]) for d in sorted(v, key=lambda d: int(d["progressivoIter"] or 0))))

print("\n== 3) Aggancio Camera <-> Senato (chiave: legislatura + numero) ==")
cam = collections.defaultdict(set)
for fn in ("atto.rdf.zip", "atto-19.rdf.zip"):
    with zipfile.ZipFile(C + fn) as z, z.open(z.namelist()[0]) as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
            m = re.match(r"^<http://dati\.camera\.it/ocd/attocamera\.rdf/ac(\d+)_(\d+)>\t<http://www\.w3\.org/1999/02/22-rdf-syntax-ns#type>", line)
            if m and m.group(1) in ("17", "18", "19"): cam[m.group(1)].add(m.group(2))
last = {}
for r in csv.DictReader(open("data/processed/iter_camera.csv", encoding="utf-8")): last[r["case_id"]] = r["activity"]
sen_c = collections.defaultdict(dict)
for d in ddl:
    m = pat.match(d["fase"])
    if m and m.group(1) == "C" and not m.group(3): sen_c[d["legislatura"]][m.group(2)] = d
for leg in ("17", "18", "19"):
    A, B = cam[leg], set(sen_c[leg])
    print("  leg %s: atti Camera %d | ddl Senato con fase C.n (prima lettura) %d | in comune %d | solo Camera %d | solo Senato %d" % (leg, len(A), len(B), len(A & B), len(A - B), len(B - A)))
    both = A & B
    tab = collections.Counter(("Camera:Legge" if "Legge" in last.get("ac%s_%s" % (leg, n), "") else "Camera:altro", "Senato:Legge" if "Legge" in sen_c[leg][n]["statoDdl"] else "Senato:altro") for n in both)
    print("     incrocio esito (in comune):", dict(tab))
    nav = sum(1 for n in A if any("Navetta" in last.get("ac%s_%s" % (leg, n), "") or "Senato" in last.get("ac%s_%s" % (leg, n), "") for _ in [0]))
    print("     atti Camera il cui ultimo stato cita Senato/navetta:", nav)
