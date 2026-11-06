#!/usr/bin/env python3
"""Lecture seule : pour chaque cycle de rappel Gazelle, montre les lignes de lien
(scheduling_link, reserver.pianotechniquemontreal.com) de chaque courriel.
Gabarits seulement : aucune donnée client. N'écrit rien dans Gazelle."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

api = GazelleAPIClient()
MSG = "id kind state reminderKind recurringSubject recurringMessage firstSubject firstMessage specialSubject specialMessage"
r = api._execute_query("{ allLifecycles(first: 50) { nodes { id name lifecycleMessages { %s } } } }" % MSG)
if r.get("errors"):
    print(f"::error title=Erreur::{str(r['errors'])[:1500]}"); sys.exit(1)
for c in r["data"]["allLifecycles"]["nodes"]:
    lignes = [f"{c['id']} « {c['name']} »"]
    for m in c.get("lifecycleMessages") or []:
        if m["reminderKind"] != "EMAIL":
            continue
        for champ in ("recurring", "first", "special"):
            texte = m.get(f"{champ}Message") or ""
            liens = [l.strip() for l in texte.splitlines() if re.search(r"scheduling_link|reserver\.pianotech", l)]
            if texte:
                lignes.append(f"- {m['id']} {m['state']}/{champ} | {m.get(champ + 'Subject') or ''} | " + (" || ".join(liens) or "(aucun lien)"))
    print("::notice title=Cycle::" + "%0A".join(x.replace("%", "%25") for x in lignes)[:3800])
