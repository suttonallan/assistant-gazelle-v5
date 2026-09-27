#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Push retroactif des services du concert six pianos (Orford) dans Gazelle.

Mecanisme : pour chaque piano, on cree un evenement DATE au jour reel du service
(pas aujourd'hui), on le complete avec une note d'historique de service, on
enregistre temperature/humidite si notee, le tout en restaurant le statut
ACTIVE/INACTIVE du piano (protege la limite de pianos facturables).

Usage :
  python scripts/push_orford_concert_services.py            # APERCU (dry-run), n'ecrit rien
  python scripts/push_orford_concert_services.py --execute  # pousse pour de vrai

isTuning=True UNIQUEMENT sur les pianos reellement accordes (met a jour la date
du dernier accord). Les autres : service enregistre sans toucher au suivi d'accord.
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.gazelle_api_client import GazelleAPIClient  # noqa: E402

ORFORD_CLIENT_ID = "cli_PmqPUBTbPFeCMGmz"
TECH_ID = "usr_HcCiFk7o0vZ9xAI0"          # Nicolas
EVENT_DATETIME = "2026-06-04T10:00:00-04:00"  # date reputee du service (4 juin 2026, EDT)
EVENT_DATE = "2026-06-04"                  # pour takenOn des mesures

# make/model attendus : verification d'identite avant tout push (anti-mauvais piano)
PIANOS = [
    {
        "id": "ins_6x9mNpxTvUsNpcdu", "attendu": "Yamaha G3 / F5211250",
        "is_tuning": True, "temp": None, "humidity": None,
        "note": (
            "Accord 440 Hz. Una corda : ajustement a revoir (augmenter ou reduire ?). "
            "Vis de pedalier serrees + reparation d'une vis (vis plate). Nettoyage du lit "
            "du clavier. Niveau du clavier : pas necessaire.\n"
            "Travel - wippen/chevalet : A#2, F#6, D#6, E6, D6, F6 ; marteaux/manche : C#6, F2."
        ),
    },
    {
        "id": "ins_4MBuN72Yy7HYuVb4", "attendu": "Shigeru Kawai SK-EX / 2756947",
        "is_tuning": True, "temp": None, "humidity": None,
        "note": (
            "Accord 440 Hz. Aigu sourd : friction (fait). Harmonisation (fait). Verifier la friction du Do#5 "
            "(fait ?). Friction au balancier. Enfoncement - blanches 10.2 mm ; noires 9.8-9.9 mm "
            "a plusieurs endroits (presque noyees : il faudrait monter l'enfoncement et le "
            "balancier encore plus). Ease key + lubrification + nivelage des touches blanches (fait)."
        ),
    },
    {
        "id": "ins_tLKLpJspxM3PVGEt", "attendu": "Yamaha CF III / S 6045000",
        "is_tuning": True, "temp": None, "humidity": None,
        "note": (
            "Accord rapide (Allan, 2 juin). G#5/A#5/B5 claquaient (marteaux decolles) : CA sur "
            "tous les marteaux (fait) ; traitement CA general (fait). Retouche meuble au feutre "
            "noir et vernis. Ressorts trop forts (ajustes). Butee haute : a faire (limiter la "
            "levee de la pedale, ajuster pour les touches). Bedding : a faire. Echappement C#5 et "
            "proches : chute. Garniture de touches ? F#3 trop dip ?\n"
            "Travel (fait) - chevalet/wippen : D1, F#2, F1 ; manche : D#1. L.O. : F2 a D#5. "
            "Hammer string mating jusqu'a G6."
        ),
    },
    {
        "id": "ins_WcMsKlJvodcoxqnm", "attendu": "Steinway D / 382881 (Salle Gilles Lefebvre)",
        "is_tuning": True, "temp": 22, "humidity": 37,
        "note": (
            "Accord 440 Hz. 22 degres, 37%. Retouches peinture noire. Des chevilles sont molasses (ex. A3 gauche). "
            "Voicing : C#5/A#5 click ; A6 ; traitement CA general des marteaux."
        ),
    },
    {
        "id": "ins_Wt9fJNbaudy7f0O5", "attendu": "Yamaha G3E / Q-5 / 4140139",
        "is_tuning": True, "temp": 23, "humidity": 37,
        "note": (
            "Accord 440 Hz. 23 degres, 37%. Bedding. Enfoncement pas suffisant (FAIT). Retouches au meuble "
            "(feutre noir). Vis du cadre serrees. Marteaux sables. Attache PLS brisee (remplacee). "
            "CA sur les tetes de marteaux qui claquent. Peinture noire sur les pattes du banc."
        ),
    },
    {
        "id": "ins_MaJawnxtZKTGqgAz", "attendu": "Yamaha G3A / Q-22 / 4215063",
        "is_tuning": True, "temp": None, "humidity": None,
        "note": (
            "Accord 440 Hz. Retouches feutre noir. Vis de la plaque (vis plate) serrees. Espacement des blanches. "
            "Ajustement de la ligne des marteaux. Ajustement de la butee haute. Investigation d'un "
            "buzz de table d'harmonie : sans succes."
        ),
    },
]

CREATE_EVENT = """
mutation CreateServiceEvent($input: PrivateEventInput!) {
  createEvent(input: $input) {
    event { id title start status }
    mutationErrors { fieldName messages }
  }
}
"""

COMPLETE_EVENT = """
mutation CompleteEvent($eventId: String!, $input: PrivateCompleteEventInput!) {
  completeEvent(eventId: $eventId, input: $input) {
    event { id status }
    mutationErrors { fieldName messages }
  }
}
"""

UPDATE_STATUS = """
mutation UpdatePianoStatus($pianoId: String!, $input: PrivatePianoInput!) {
  updatePiano(id: $pianoId, input: $input) {
    piano { id status }
    mutationErrors { fieldName messages }
  }
}
"""


def _errs(payload, key):
    node = (payload.get("data") or {}).get(key) or {}
    return node, node.get("mutationErrors") or []


def fetch_piano(client, pid):
    q = ("query($id:String!){piano(id:$id){id make model serialNumber status "
         "client{id companyName}}}")
    return (client._execute_query(q, {"id": pid}).get("data") or {}).get("piano")


def process_piano(client, p, dry_run):
    info = fetch_piano(client, p["id"])
    if not info:
        print(f"  ERREUR : piano {p['id']} introuvable. Saute.")
        return False
    ident = f"{info.get('make') or ''} {info.get('model') or ''} / {info.get('serialNumber')}".strip()
    cli = (info.get("client") or {}).get("id")
    status_before = info.get("status")
    meas = f" | mesure {p['temp']}/{p['humidity']}" if p["temp"] is not None else ""
    print(f"\n- {p['attendu']}")
    print(f"    Gazelle : {ident}  [{p['id']}]  statut={status_before}")
    print(f"    accord(isTuning)={p['is_tuning']}{meas}")
    print(f"    note : {p['note'][:90]}...")

    # Garde-fou identite : doit appartenir a Orford
    if cli != ORFORD_CLIENT_ID:
        print(f"    ERREUR : ce piano appartient a {cli}, pas Orford. SAUTE (rien pousse).")
        return False

    if dry_run:
        print("    [APERCU] rien ecrit.")
        return True

    # 1. createEvent date au jour du service
    ev_input = {
        "title": "Service - concert six pianos (Orford)",
        "start": EVENT_DATETIME,
        "duration": 60,
        "type": "APPOINTMENT",
        "notes": p["note"],
        "clientId": ORFORD_CLIENT_ID,
        "userId": TECH_ID,
        "pianos": [{"pianoId": p["id"], "isTuning": p["is_tuning"]}],
    }
    node, errs = _errs(client._execute_query(CREATE_EVENT, {"input": ev_input}), "createEvent")
    if errs:
        print(f"    ECHEC createEvent : {errs}")
        return False
    event_id = (node.get("event") or {}).get("id")
    print(f"    evenement cree : {event_id}")

    # 2. completeEvent -> entree dans l'historique de service
    comp = {"resultType": "COMPLETE",
            "serviceHistoryNotes": [{"pianoId": p["id"], "notes": p["note"]}]}
    node, errs = _errs(client._execute_query(COMPLETE_EVENT, {"eventId": event_id, "input": comp}),
                       "completeEvent")
    if errs:
        print(f"    ATTENTION completeEvent : {errs} (evenement cree, a completer a la main)")
    else:
        print("    historique de service cree (completeEvent COMPLETE)")

    # 3. mesure temperature/humidite si notee
    if p["temp"] is not None and p["humidity"] is not None:
        try:
            client.create_piano_measurement(p["id"], p["temp"], p["humidity"], taken_on=EVENT_DATE)
            print(f"    mesure enregistree : {p['temp']} degres / {p['humidity']}% ({EVENT_DATE})")
        except Exception as e:
            print(f"    ATTENTION mesure non enregistree : {e}")

    # 4. restaurer le statut si Gazelle a active un piano inactif (limite facturable)
    after = fetch_piano(client, p["id"])
    status_after = (after or {}).get("status")
    if status_before == "INACTIVE" and status_after == "ACTIVE":
        node, errs = _errs(client._execute_query(
            UPDATE_STATUS, {"pianoId": p["id"], "input": {"status": "INACTIVE"}}), "updatePiano")
        if errs:
            print(f"    ATTENTION : piano reste ACTIVE (echec restauration) : {errs}")
        else:
            print("    statut restaure a INACTIVE")
    else:
        print(f"    statut inchange ({status_after})")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="Pousse pour de vrai (defaut: apercu)")
    args = ap.parse_args()
    dry_run = not args.execute

    print("=" * 70)
    print(f"PUSH SERVICES CONCERT SIX PIANOS - ORFORD - date du service {EVENT_DATE}")
    print(f"Technicien : Nicolas ({TECH_ID})")
    print("MODE : " + ("APERCU (dry-run, rien ecrit)" if dry_run else "EXECUTION REELLE"))
    print("=" * 70)

    client = GazelleAPIClient()
    ok = 0
    for p in PIANOS:
        if process_piano(client, p, dry_run):
            ok += 1
    print("\n" + "=" * 70)
    print(f"{ok}/{len(PIANOS)} pianos traites.")
    if dry_run:
        print("Apercu seulement. Relancer avec --execute pour pousser.")


if __name__ == "__main__":
    main()
