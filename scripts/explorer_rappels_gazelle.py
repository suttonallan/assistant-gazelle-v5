#!/usr/bin/env python3
"""Lecture seule : quelles requêtes/mutations de l'API privée Gazelle touchent
les rappels (reminders), cycles de vie (lifecycles) et modèles de courriel ?
Aucune écriture. Résultat dans les annotations GitHub."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

MOTIF = re.compile(r"remind|lifecycle|template|campaign|emailMessage|messageTemplate", re.I)
api = GazelleAPIClient()
res = api._execute_query("""{ __schema {
  queryType { fields { name args { name } } }
  mutationType { fields { name args { name type { name kind ofType { name } } } } } } }""")
s = (res.get("data") or {}).get("__schema") or {}
q = [f["name"] for f in (s.get("queryType") or {}).get("fields") or [] if MOTIF.search(f["name"])]
m = [f for f in (s.get("mutationType") or {}).get("fields") or [] if MOTIF.search(f["name"])]
print("REQUETES:", q)
print("MUTATIONS:", [x["name"] for x in m])
print(f"::notice title=Requetes::{', '.join(q) or 'aucune'}")
print(f"::notice title=Mutations::{', '.join(x['name'] for x in m) or 'aucune'}")
# Types d'entrée des mutations trouvées
for x in m:
    for a in x["args"]:
        t = a["type"].get("name") or (a["type"].get("ofType") or {}).get("name")
        if t and t.endswith("Input"):
            r = api._execute_query('query($n:String!){ __type(name:$n){ inputFields { name } } }', {"n": t})
            champs = [f["name"] for f in ((r.get("data") or {}).get("__type") or {}).get("inputFields") or []]
            print(f"::notice title={x['name']} {t}::{', '.join(champs)}")
# Champs des types rappel/cycle de vie
for nom in ["PrivateReminder", "PrivateReminderTemplate", "PrivateLifecycle", "PrivateLifecycleReminder", "PrivateEmailTemplate"]:
    r = api._execute_query('query($n:String!){ __type(name:$n){ fields { name } } }', {"n": nom})
    t = (r.get("data") or {}).get("__type")
    if t:
        print(f"::notice title=Type {nom}::{', '.join(f['name'] for f in t.get('fields') or [])}")
