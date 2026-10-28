#!/usr/bin/env python3
"""Lecture seule : vérifier le code de fusion du « Numéro client » (custom2)
dans les rappels Gazelle, par l'aperçu de Gazelle. Aucune écriture."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
def q(t, v=None): return api._execute_query(t, v or {})
def note(titre, txt): print(f"::notice title={titre}::" + str(txt)[:6000].replace("%", "%25").replace("\n", "%0A"))

r = q("""{ __schema { queryType { fields { name args { name type { name kind ofType { name kind ofType { name } } } } type { name ofType { name } } } } } }""")
for f in r["data"]["__schema"]["queryType"]["fields"]:
    if f["name"] in ("lifecycleMessagePreview", "templatePreview"):
        note("Args " + f["name"], json.dumps(f, ensure_ascii=False))
# Un client actif avec custom2 rempli
c = q("{ allClients(first: 1, filters: {status: ACTIVE}) { nodes { id custom2 } } }")
note("Client test", json.dumps(c, ensure_ascii=False)[:500])
