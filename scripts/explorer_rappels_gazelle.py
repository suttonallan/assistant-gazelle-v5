#!/usr/bin/env python3
"""Lecture seule : structure et contenu des cycles de vie (rappels) Gazelle.
Aucune écriture. Résultat dans les annotations GitHub."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

api = GazelleAPIClient()
def q(t, v=None): return api._execute_query(t, v or {})

def type_de(nom_champ):
    r = q("""{ __schema { queryType { fields { name type { name kind ofType { name kind ofType { name kind ofType { name } } } } } } } }""")
    for f in r["data"]["__schema"]["queryType"]["fields"]:
        if f["name"] == nom_champ:
            t = f["type"]
            while t.get("ofType"): t = t["ofType"] if t.get("name") is None else t
            if t.get("name"): return t["name"]
            return None
def champs(t):
    r = q('query($n:String!){ __type(name:$n){ fields { name type { name kind ofType { name kind ofType { name kind ofType { name } } } } } } }', {"n": t})
    return ((r.get("data") or {}).get("__type") or {}).get("fields") or []
def nom_type(t):
    while t and not t.get("name"): t = t.get("ofType")
    return t.get("name") if t else None

lignes = []
tl = type_de("allLifecycles"); lignes.append(f"allLifecycles -> {tl}")
for f in champs(tl): lignes.append(f"  {tl}.{f['name']}: {nom_type(f['type'])}")
noeud = next((nom_type(f["type"]) for f in champs(tl) if f["name"] == "nodes"), tl)
if noeud and noeud != tl:
    for f in champs(noeud):
        lignes.append(f"  {noeud}.{f['name']}: {nom_type(f['type'])}")
        if "essage" in f["name"]:
            mt = nom_type(f["type"])
            for g in champs(mt):
                lignes.append(f"    {mt}.{g['name']}: {nom_type(g['type'])}")
                if g["name"] == "nodes":
                    for h in champs(nom_type(g["type"])):
                        lignes.append(f"      {nom_type(g['type'])}.{h['name']}: {nom_type(h['type'])}")
txt = "\n".join(lignes); print(txt)
print("::notice title=Structure::" + txt.replace("%", "%25").replace("\n", "%0A"))
