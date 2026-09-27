#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconcilie les doublons de services Orford (concert six pianos).

Garde les 3 entrees propres du 4 juin. Avant suppression, fusionne le vrai
travail supplementaire (points de contact des cordes, capo d'astro, retouches
d'unissons) dans ces entrees. Puis supprime les 20 fragments « Technicien :
Technicien » crees a chaque frappe par l'ancien auto-save casse.

Garde-fous : ne supprime QUE des evenements dont les notes contiennent
« Technicien : Technicien » ; ne touche jamais aux 3 entrees a garder.

Usage :
  python scripts/reconcile_orford_duplicates.py            # APERCU
  python scripts/reconcile_orford_duplicates.py --execute  # applique
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.gazelle_api_client import GazelleAPIClient  # noqa: E402

KEEP = {
    "evt_YbJiK6ZQ3BxHbzbW": "Yamaha G3",
    "evt_1hlUimPyx2GYFNwQ": "Shigeru SK-EX",
    "evt_myacjYaufxLDmYyr": "CF III",
}

# Travail reel a fusionner dans les entrees du 4 juin (texte a ajouter)
APPENDS = {
    "evt_YbJiK6ZQ3BxHbzbW":
        "\nTravail additionnel : travail sur tous les points de contact des cordes.",
    "evt_1hlUimPyx2GYFNwQ":
        "\nTravail additionnel : travail sur le point de contact des cordes au capo d'astro ; "
        "retouches d'unissons pour le concert (6 pianos).",
}

DELETE = [
    # Yamaha G3 (4)
    "evt_q2l9TaeJOTFUL3D7", "evt_mXO9cKvuGdykf0TF", "evt_UmtIw3OQtPmErveI", "evt_jeEo5gZAF6sDEK7U",
    # Shigeru SK-EX (12)
    "evt_WSNydb8P3riqlaJ3", "evt_0PAwV2VpzLOwi6z6", "evt_LUIJz1idY6FYChGb", "evt_XXtzN5sGHFgbTyej",
    "evt_KqL5fMSN7LVq2ddL", "evt_4SzQUYez8CT0032o", "evt_wLp6bcAjV1EvjOK3", "evt_ayYLxXCu3vl8JGyP",
    "evt_HJaLXeTZV0OgPNre", "evt_3g0bvPhHGeA5qcAU", "evt_bIdiEmQbEla8pxif", "evt_tDV4iazGkya9GSWD",
    # CF III (4)
    "evt_xcOkNItfNDjKIvS2", "evt_715ANjRhWBE0KCUQ", "evt_wUs8CzEl48WjzekH", "evt_XTx8ZI6D3YAlLh7Y",
]

GUARD = "Technicien : Technicien"

Q_NOTES = "query($id:String!){event(eventId:$id){id notes status}}"
M_UPDATE = "mutation($id:String!,$input:PrivateEventInput!){updateEvent(id:$id,input:$input){event{id} mutationErrors{fieldName messages}}}"
M_DELETE = "mutation($id:String!){deleteEvent(id:$id){isDeleted mutationErrors{fieldName messages}}}"


def get_notes(g, eid):
    e = (g._execute_query(Q_NOTES, {"id": eid}).get("data") or {}).get("event")
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    dry = not args.execute

    g = GazelleAPIClient()

    # Garde-fou : aucun chevauchement keep/delete
    overlap = set(KEEP) & set(DELETE)
    if overlap:
        print(f"ARRET : chevauchement keep/delete {overlap}. Rien fait."); return

    print("=" * 68)
    print("RECONCILIATION DOUBLONS ORFORD — " + ("APERCU" if dry else "EXECUTION"))
    print("=" * 68)

    # 1. Fusion du vrai travail dans les entrees a garder
    print("\n--- FUSION (updateEvent) ---")
    for eid, add in APPENDS.items():
        e = get_notes(g, eid)
        if not e:
            print(f"  {eid} introuvable — saute."); continue
        cur = e.get("notes") or ""
        if add.strip() in cur:
            print(f"  {KEEP.get(eid, eid)} : deja fusionne, rien a faire."); continue
        new = cur + add
        print(f"  {KEEP.get(eid, eid)} ({eid}) : +{add.strip()[:70]}...")
        if not dry:
            r = g._execute_query(M_UPDATE, {"id": eid, "input": {"notes": new}})
            errs = ((r.get("data") or {}).get("updateEvent") or {}).get("mutationErrors") or []
            print("     OK" if not errs else f"     ERREUR {errs}")

    # 2. Suppression gardee des fragments
    print("\n--- SUPPRESSION (deleteEvent) ---")
    deleted = skipped = 0
    for eid in DELETE:
        e = get_notes(g, eid)
        if not e:
            print(f"  {eid} : deja absent."); continue
        notes = e.get("notes") or ""
        if GUARD not in notes:
            print(f"  {eid} : NE CONTIENT PAS le garde-fou — SAUTE (par securite)."); skipped += 1; continue
        snippet = notes.split("Travail:")[-1].split("Observations")[0].strip()[:45]
        print(f"  supprimer {eid}  \"{snippet}\"")
        if not dry:
            r = g._execute_query(M_DELETE, {"id": eid})
            node = (r.get("data") or {}).get("deleteEvent") or {}
            if node.get("isDeleted"):
                deleted += 1
            else:
                print(f"     ECHEC {node.get('mutationErrors')}"); skipped += 1

    print("\n" + "=" * 68)
    if dry:
        print(f"APERCU : {len(DELETE)} a supprimer, {len(APPENDS)} a fusionner. Relancer avec --execute.")
    else:
        print(f"FAIT : {deleted} supprimes, {skipped} sautes, {len(APPENDS)} fusionnes.")


if __name__ == "__main__":
    main()
