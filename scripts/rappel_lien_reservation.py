#!/usr/bin/env python3
"""Rappel Gazelle « À accorder bientôt » (cycle Français) : ajoute le lien personnel
vers la page de réservation PTM, en gardant le lien Gazelle en second choix.

Touche UN seul message (lcm_oYKZhzjTW6WzXNH2), vérifie le texte actuel avant
d'écrire, relit après. Idempotent. Code de fusion vérifié dans l'éditeur Gazelle :
{{client.custom2}} = numéro client (rempli chaque nuit par remplir_numero_client.py).
Si le champ était vide, le lien mène à la page générale : jamais de lien brisé.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

MESSAGE_ID = "lcm_oYKZhzjTW6WzXNH2"
ANCIENNE = "Vous pouvez choisir votre rendez-vous en cliquant sur ce bouton :  {{scheduling_link}}"
NOUVELLE = ("Vous pouvez choisir votre rendez-vous en ligne ici : "
            "**[Prendre rendez-vous](https://reserver.pianotechniquemontreal.com/{{client.custom2}})**\n\n"
            "Vous préférez l’ancienne page de réservation ? {{scheduling_link}}")
CHAMPS = ("recurringMessage recurringSubject firstMessage firstSubject specialMessage specialSubject "
          "frequencyCode frequencyFrom firstDelayCode limit")

api = GazelleAPIClient()
def lire():
    r = api._execute_query(f'{{ lifecycle(id: "lcy_VEOrJHKlyLhGaNa4") {{ lifecycleMessages {{ id {CHAMPS} }} }} }}')
    return next(m for m in r["data"]["lifecycle"]["lifecycleMessages"] if m["id"] == MESSAGE_ID)

m = lire()
texte = m["recurringMessage"] or ""
if "reserver.pianotechniquemontreal.com" in texte:
    print("::notice title=Rappel::Deja a jour, rien a faire"); sys.exit(0)
if ANCIENNE not in texte:
    print("::error title=Rappel::Texte actuel inattendu, rien n'a ete modifie"); sys.exit(1)

entree = {k: m[k] for k in CHAMPS.split()}
entree["recurringMessage"] = texte.replace(ANCIENNE, NOUVELLE)
args = api._execute_query("""{ __schema { mutationType { fields { name args { name } } } } }""")
noms = next(f for f in args["data"]["__schema"]["mutationType"]["fields"] if f["name"] == "updateLifecycleMessage")
noms = [a["name"] for a in noms["args"]]
cle_id = "id" if "id" in noms else noms[0]
r = api._execute_query(
    f"mutation($id: String!, $input: PrivateUpdateLifecycleMessageInput!) {{ updateLifecycleMessage({cle_id}: $id, input: $input) {{ mutationErrors {{ fieldName messages }} }} }}",
    {"id": MESSAGE_ID, "input": entree})
if r.get("errors") or ((r.get("data") or {}).get("updateLifecycleMessage") or {}).get("mutationErrors"):
    print(f"::error title=Rappel::Refus Gazelle : {str(r)[:1500]}"); sys.exit(1)
apres = lire()
ok = apres["recurringMessage"] == entree["recurringMessage"] and all(apres[k] == m[k] for k in CHAMPS.split() if k != "recurringMessage")
print(f"::notice title=Rappel::{'Mis a jour et verifie' if ok else 'ECART a la relecture'}")
sys.exit(0 if ok else 1)
