#!/usr/bin/env python3
"""
Remplit le champ personnalisé « Numéro client » (custom2) de chaque fiche Gazelle
avec l'identifiant du client (cli_…).

Pourquoi : les rappels Gazelle n'ont pas de code de fusion pour l'identifiant du
client. Avec ce champ, le modèle de rappel peut construire le lien personnel vers
la page de réservation PTM :
    https://reserver.pianotechniquemontreal.com/{{client.custom2}}

Règles :
- on écrit seulement dans un champ VIDE (jamais d'écrasement d'une autre valeur) ;
- un champ qui contient déjà le bon numéro est laissé tel quel ;
- un champ qui contient autre chose est signalé, pas modifié.

Usage :
    python3 scripts/remplir_numero_client.py --essai     # compte seulement, n'écrit rien
    python3 scripts/remplir_numero_client.py             # remplit les fiches vides
    python3 scripts/remplir_numero_client.py --limite 5  # remplit au plus 5 fiches (test)
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from core.gazelle_api_client import GazelleAPIClient  # noqa: E402

CHAMP = "custom2"
PAUSE_ENTRE_ECRITURES = 0.25  # secondes : rester poli avec l'API Gazelle

REQ_LISTE = """
query Clients($after: String) {
  allClients(first: 100, after: $after) {
    nodes { id %s }
    pageInfo { hasNextPage endCursor }
  }
}
""" % CHAMP

REQ_MAJ = """
mutation MajClient($id: String!, $input: PrivateClientInput!) {
  updateClient(id: $id, input: $input) {
    client { id %s }
    mutationErrors { fieldName messages }
  }
}
""" % CHAMP


def tous_les_clients(api: GazelleAPIClient):
    apres = None
    while True:
        res = api._execute_query(REQ_LISTE, {"after": apres})
        bloc = (res.get("data") or {}).get("allClients") or {}
        yield from bloc.get("nodes") or []
        info = bloc.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            return
        apres = info.get("endCursor")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--essai", action="store_true", help="compter seulement, ne rien écrire")
    ap.add_argument("--limite", type=int, default=0, help="nombre maximal de fiches à remplir (0 = toutes)")
    args = ap.parse_args()

    api = GazelleAPIClient()
    total = deja_bons = remplis = 0
    a_remplir: list[str] = []
    conflits: list[tuple[str, str]] = []

    for c in tous_les_clients(api):
        total += 1
        valeur = (c.get(CHAMP) or "").strip()
        if valeur == c["id"]:
            deja_bons += 1
        elif not valeur:
            a_remplir.append(c["id"])
        else:
            conflits.append((c["id"], valeur))

    print(f"Fiches lues : {total} · déjà remplies : {deja_bons} · à remplir : {len(a_remplir)} · autre valeur : {len(conflits)}")
    for cid, val in conflits[:20]:
        print(f"  ⚠️ {cid} contient déjà « {val} » — laissé tel quel")

    if args.essai:
        print("Mode essai : rien n'a été écrit.")
        return 0

    cibles = a_remplir[: args.limite] if args.limite else a_remplir
    erreurs = 0
    for i, cid in enumerate(cibles, 1):
        try:
            res = api._execute_query(REQ_MAJ, {"id": cid, "input": {CHAMP: cid}})
            p = (res.get("data") or {}).get("updateClient") or {}
            if p.get("mutationErrors"):
                raise ValueError(p["mutationErrors"])
            if (p.get("client") or {}).get(CHAMP) != cid:
                raise ValueError(f"valeur relue inattendue : {p}")
            remplis += 1
        except Exception as e:  # une fiche en erreur n'arrête pas les autres
            erreurs += 1
            print(f"  ❌ {cid} : {e}")
            if erreurs >= 20:
                print("Trop d'erreurs, arrêt.")
                break
        if i % 200 == 0:
            print(f"  … {i}/{len(cibles)}")
        time.sleep(PAUSE_ENTRE_ECRITURES)

    print(f"✅ {remplis} fiche(s) remplie(s), {erreurs} erreur(s).")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
