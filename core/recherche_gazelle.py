"""Recherche de plages par le moteur de Gazelle lui-même (API privée, schedulerV2Search) :
c'est le même calcul que « Trouver une plage » dans Gazelle — route et trafic, secteurs,
heures de travail, pauses, battement, plages préférées, maximum de RV par jour.

Une recherche coûte à Gazelle : seulement quand l'équipe demande une plage pour un client
précis, une à la fois, jamais automatique ni en boucle. Garde-fous : 1 recherche / 15 s,
au plus 20 par heure. Lire la progression ou les résultats d'une recherche existante est permis.
"""
import logging
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

_VERROU = threading.Lock()
_RECHERCHES: deque = deque()

M_RECHERCHE = """mutation($p: PrivateSchedulerV2SearchInput) {
  schedulerV2Search(searchParams: $p) { searchId technicianSearchSignatures warnings
    mutationErrors { fieldName messages } } }"""
Q_PROGRES = "query($s: [String!]!) { schedulerV2SearchProgress(technicianSearchSignatures: $s) }"
Q_RESULTATS = """query($s: [String!]!) { schedulerV2SearchResults(technicianSearchSignatures: $s) {
  errors results { technicianSearchSignature slots { startsAt technicianId duration buffer isAPreferredSlot
    beforeTravelMinutes afterTravelMinutes outsideServiceAreaMinutes flags } } } }"""


class RechercheRefusee(Exception):
    pass


def _autoriser() -> None:
    with _VERROU:
        now = time.time()
        while _RECHERCHES and now - _RECHERCHES[0] > 3600:
            _RECHERCHES.popleft()
        if _RECHERCHES and now - _RECHERCHES[-1] < 15:
            raise RechercheRefusee("Une recherche Gazelle vient d'être lancée : attendre 15 secondes.")
        if len(_RECHERCHES) >= 20:
            raise RechercheRefusee("Plafond de 20 recherches Gazelle par heure atteint.")
        _RECHERCHES.append(now)


def chercher_plages(gz, date_visee: str, duree_min: int, user_ids: List[str],
                    client_id: Optional[str] = None, adresse: Optional[str] = None,
                    delai_max: float = 40.0) -> Dict[str, Any]:
    """Lance UNE recherche Gazelle et renvoie {search_id, plages: [...], avertissements}."""
    if not (client_id or adresse):
        raise RechercheRefusee("Il faut le client (ou l'adresse) pour que Gazelle calcule la route.")
    _autoriser()
    p: Dict[str, Any] = {"targetDate": date_visee, "duration": int(duree_min), "userIds": user_ids}
    if client_id:
        p["clientId"] = client_id
    if adresse:
        p["addressLine"] = adresse
    res = gz._execute_query(M_RECHERCHE, {"p": p})
    r = ((res or {}).get("data") or {}).get("schedulerV2Search") or {}
    if res.get("errors") or r.get("mutationErrors") or not r.get("technicianSearchSignatures"):
        raise RechercheRefusee(f"Gazelle a refusé la recherche : {r.get('mutationErrors') or res.get('errors')}")
    sigs = r["technicianSearchSignatures"]
    fin = time.monotonic() + delai_max
    fini = False
    while time.monotonic() < fin:
        prog = ((gz._execute_query(Q_PROGRES, {"s": sigs}).get("data") or {}).get("schedulerV2SearchProgress")) or 0
        if prog >= 100:
            fini = True
            break
        time.sleep(0.7)
    plages: List[Dict[str, Any]] = []
    while True:
        w = ((gz._execute_query(Q_RESULTATS, {"s": sigs}).get("data") or {}).get("schedulerV2SearchResults")) or {}
        for t in w.get("results") or []:
            plages += t.get("slots") or []
        if plages or (fini and w.get("results") is not None) or time.monotonic() >= fin:
            break
        time.sleep(0.7)
    if w.get("errors"):
        logging.warning(f"Recherche Gazelle : {w['errors']}")
    plages.sort(key=lambda s: s.get("startsAt") or "")
    return {"search_id": r.get("searchId"), "plages": plages,
            "avertissements": (r.get("warnings") or []) + (w.get("errors") or [])}
