#!/usr/bin/env python3
"""Crée (ou met à jour) le cycle de rappel Gazelle « Clients éloignés ».

Copie du cycle « Français » (mêmes délais, même confirmation de RV, mêmes tâches
d'appel), mais les courriels « piano à accorder » expliquent que la réservation en
ligne est maintenant possible malgré la distance. N'assigne AUCUN client.
Idempotent : relancer met à jour les messages du cycle existant.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv; load_dotenv()
from core.gazelle_api_client import GazelleAPIClient

NOM = "Clients éloignés"
SOURCE = "lcy_VEOrJHKlyLhGaNa4"  # cycle « Français »
SUJET = "Votre piano : vous pouvez maintenant prendre rendez-vous en ligne"
TEXTE = """Bonjour {{client.first_name}},

Selon nos dossiers, votre piano pourrait avoir besoin d’un accord dans un proche avenir.

Comme votre piano se trouve à une certaine distance de Montréal, il n’était pas toujours possible de prendre rendez-vous en ligne avec nous. C’est maintenant chose faite : notre nouvelle page de réservation vous montre les plages disponibles et les frais de déplacement applicables avant que vous confirmiez.

**[Prendre rendez-vous](https://reserver.pianotechniquemontreal.com/{{client.custom2}})**

Si vous habitez plus loin (Estrie, Laurentides, etc.), la même page vous permet de nous indiquer vos disponibilités. Notre coordonnatrice vous contactera ensuite pour fixer le rendez-vous.

Au plaisir de revoir votre piano,

**{{company.name}}**  
{{company.phone}}  
{{company.email}}
"""
ETATS_PIANO = {"COMING_DUE", "DUE", "OVERDUE_STAGE_1", "OVERDUE_STAGE_2"}
FENETRES = ("confWindowCode autoConfWindowCode criticalConfWindowCode cancelUnconfirmedWindowCode dueWindowCode "
            "overdue1WindowCode overdue2WindowCode overdue3WindowCode overdue4WindowCode").split()
MSG = ("kind state reminderKind recurringMessage recurringSubject firstMessage firstSubject specialMessage "
       "specialSubject frequencyCode frequencyFrom firstDelayCode limit").split()

api = GazelleAPIClient()
def q(t, v=None):
    r = api._execute_query(t, v or {})
    if r.get("errors"):
        print(f"::error title=Gazelle::{str(r['errors'])[:1500]}"); sys.exit(1)
    return r["data"]
def charge_utile(mutation):
    """Champs de retour de la mutation (pour récupérer l'id et les erreurs)."""
    d = q('{ __schema { mutationType { fields { name type { name } } } } }')
    t = next(f["type"]["name"] for f in d["__schema"]["mutationType"]["fields"] if f["name"] == mutation)
    return [f["name"] for f in q('query($n:String!){ __type(name:$n){ fields { name } } }', {"n": t})["__type"]["fields"]]
def verifier(res, nom):
    erreurs = (res.get(nom) or {}).get("mutationErrors")
    if erreurs:
        print(f"::error title={nom}::{erreurs}"); sys.exit(1)

LC = f"id name {' '.join(FENETRES)} lifecycleMessages {{ id {' '.join(MSG)} }}"
tous = q(f"{{ allLifecycles(first: 50) {{ nodes {{ {LC} }} }} }}")["allLifecycles"]["nodes"]
source = next(l for l in tous if l["id"] == SOURCE)
cible = next((l for l in tous if l["name"] == NOM), None)

if not cible:
    champs = charge_utile("createLifecycle")
    sel = "lifecycle { id }" if "lifecycle" in champs else ""
    res = q(f"mutation($i: PrivateLifecycleInput!) {{ createLifecycle(input: $i) {{ {sel} mutationErrors {{ fieldName messages }} }} }}",
            {"i": {"name": NOM, "default": False, **{k: source[k] for k in FENETRES}}})
    verifier(res, "createLifecycle")
    tous = q(f"{{ allLifecycles(first: 50) {{ nodes {{ {LC} }} }} }}")["allLifecycles"]["nodes"]
    cible = next(l for l in tous if l["name"] == NOM)
    print(f"::notice title=Cycle::Cree ({cible['id']})")

existants = {(m["kind"], m["state"], m["reminderKind"]): m for m in cible["lifecycleMessages"] or []}
for m in source["lifecycleMessages"]:
    voulu = {k: m[k] for k in MSG}
    if m["state"] in ETATS_PIANO and m["reminderKind"] == "EMAIL":
        voulu.update(recurringSubject=SUJET, recurringMessage=TEXTE)
    cle = (m["kind"], m["state"], m["reminderKind"])
    if cle in existants:
        actuel = existants[cle]
        if all(actuel[k] == voulu[k] for k in MSG):
            continue
        modif = {k: voulu[k] for k in MSG if k not in ("kind", "state", "reminderKind")}
        res = q("mutation($id: String!, $i: PrivateUpdateLifecycleMessageInput!) { updateLifecycleMessage(id: $id, input: $i) { mutationErrors { fieldName messages } } }",
                {"id": actuel["id"], "i": modif})
        verifier(res, "updateLifecycleMessage")
    else:
        res = q("mutation($i: PrivateCreateLifecycleMessageInput!) { createLifecycleMessage(input: $i) { mutationErrors { fieldName messages } } }",
                {"i": {"lifecycleId": cible["id"], **voulu}})
        verifier(res, "createLifecycleMessage")

# Relecture
cible = next(l for l in q(f"{{ allLifecycles(first: 50) {{ nodes {{ {LC} }} }} }}")["allLifecycles"]["nodes"] if l["name"] == NOM)
nb = len(cible["lifecycleMessages"] or [])
nouveaux = sum(1 for m in cible["lifecycleMessages"] if m["recurringSubject"] == SUJET)
ok = nb == len(source["lifecycleMessages"]) and nouveaux == 4
print(f"::notice title=Verification::{nb} messages (source : {len(source['lifecycleMessages'])}), {nouveaux} courriels au nouveau texte, {'OK' if ok else 'ECART'}")
sys.exit(0 if ok else 1)
