#!/usr/bin/env python3
"""Lecture seule : tous les cycles de vie (rappels) Gazelle et leurs messages,
pour audit. Aucune écriture. Résultat dans les annotations GitHub."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient
api = GazelleAPIClient()
r = api._execute_query("""{ allLifecycles(first: 50) { totalCount nodes {
  id name default clientCount confWindowCode autoConfWindowCode criticalConfWindowCode
  cancelUnconfirmedWindowCode dueWindowCode overdue1WindowCode overdue2WindowCode
  overdue3WindowCode overdue4WindowCode
  lifecycleMessages { id kind state reminderKind firstDelayCode frequencyCode frequencyFrom limit
    firstSubject firstMessage recurringSubject recurringMessage specialSubject specialMessage updatedAt } } } }""")
if r.get("errors"):
    print(f"::error title=Erreur::{json.dumps(r['errors'])[:3000]}"); sys.exit(1)
data = json.dumps(r["data"], ensure_ascii=False, separators=(",", ":"))
morceaux = [data[i:i + 55000] for i in range(0, len(data), 55000)]
print(f"::notice title=Taille::{len(data)} caracteres, {len(morceaux)} morceaux")
for n, m in enumerate(morceaux[:9], 1):
    print(f"::notice title=Partie {n}::" + m.replace("%", "%25").replace("\r", "").replace("\n", "%0A"))
