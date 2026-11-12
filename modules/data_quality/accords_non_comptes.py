#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Accords qui ne « comptent » pas comme accords dans Gazelle.

Pourquoi : Gazelle retient les rappels « piano dû pour un accord » tant qu'un accord
est prévu, et met à jour la date du dernier accord quand le RV est complété —
mais SEULEMENT si un service du RV est coché « accord » (isTuning). Un RV qui
contient un service d'accord non coché laisse partir le rappel et ne remet pas
la date à jour (cas Hélène Desjardins, 11 nov. 2026, expliqué par George de Gazelle).

Deux vérifications, en LECTURE seulement :
  1. services_accord_non_coches : articles actifs de la Master Service List dont le
     nom parle d'accord, mais qui ne sont pas cochés « accord ».
  2. rv_accord_non_compte : RV (passés récents et à venir) qui contiennent un
     service d'accord, mais où aucun service ni aucun piano n'est coché « accord ».
"""
import re
from datetime import date, timedelta
from typing import Any, Dict, List

_ACCORD = re.compile(r"\baccord(?!\s+instable)|\btuning\b(?!\s+stability)", re.I)

_Q_MSL = "query { allMasterServiceItems { id name isTuning isArchived } }"

_Q_RV = """query($start: CoreDate!, $end: CoreDate!) {
  allEventsBatched(first: 200, filters: {startOn: $start, endOn: $end}) {
    nodes { id start type status
      client { id companyName defaultContact { firstName lastName } }
      user { firstName }
      allEventPianos(first: 20) { nodes { isTuning piano { id make model calculatedLastService } } }
      allServiceItems(first: 30) { nodes { name isTuning masterServiceItem { id } } } } } }"""


def _nom(n) -> str:
    if isinstance(n, dict):
        return n.get("fr_CA") or n.get("en_US") or ""
    return n or ""


def _jour_montreal(iso) -> str:
    """Date (AAAA-MM-JJ) à Montréal d'un horodatage UTC de Gazelle."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Montreal")).date().isoformat()
    except ValueError:
        return iso[:10]


def services_accord_non_coches(gz) -> List[Dict[str, Any]]:
    items = ((gz._execute_query(_Q_MSL) or {}).get("data") or {}).get("allMasterServiceItems") or []
    return [{"id": i["id"], "nom": _nom(i.get("name"))} for i in items
            if not i.get("isArchived") and not i.get("isTuning") and _ACCORD.search(_nom(i.get("name")))]


def _rv_fenetre(gz, debut: date, fin: date, requete: str = None) -> List[Dict]:
    res = gz._execute_query(requete or _Q_RV, {"start": debut.isoformat(), "end": fin.isoformat()}) or {}
    if res.get("errors"):
        raise RuntimeError(f"Gazelle : {res['errors']}")
    noeuds = ((res.get("data") or {}).get("allEventsBatched") or {}).get("nodes") or []
    if len(noeuds) >= 200 and (fin - debut).days > 1:  # fenêtre trop pleine : on la coupe en deux
        milieu = debut + timedelta(days=(fin - debut).days // 2)
        return _rv_fenetre(gz, debut, milieu, requete) + _rv_fenetre(gz, milieu, fin, requete)
    return noeuds


def rv_accord_non_compte(gz, jours_avant: int = 30, jours_apres: int = 90,
                         aujourd_hui: date = None) -> List[Dict[str, Any]]:
    """RV avec un service d'accord, mais rien de coché « accord » (ni service ni piano)."""
    from core.timezone_utils import aujourdhui_montreal
    jour = aujourd_hui or aujourdhui_montreal()
    debut, fin = jour - timedelta(days=jours_avant), jour + timedelta(days=jours_apres)
    vus, out = set(), []
    d = debut
    while d < fin:
        f = min(d + timedelta(days=7), fin)
        for ev in _rv_fenetre(gz, d, f):
            if ev["id"] in vus or ev.get("type") != "APPOINTMENT" or ev.get("status") == "CANCELLED":
                continue
            vus.add(ev["id"])
            services = (ev.get("allServiceItems") or {}).get("nodes") or []
            pianos = (ev.get("allEventPianos") or {}).get("nodes") or []
            if not any(_ACCORD.search(s.get("name") or "") for s in services):
                continue
            if not pianos or any(s.get("isTuning") for s in services) or any(p.get("isTuning") for p in pianos):
                continue
            jour_rv = _jour_montreal(ev.get("start"))
            if ev.get("status") == "COMPLETE" and all(
                    ((p.get("piano") or {}).get("calculatedLastService") or "") >= jour_rv for p in pianos):
                continue  # déjà corrigé à la main (date du dernier accord à jour)
            c = ev.get("client") or {}
            dc = c.get("defaultContact") or {}
            nom = c.get("companyName") or f"{dc.get('firstName', '')} {dc.get('lastName', '')}".strip()
            out.append({
                "event_id": ev["id"], "debut": ev.get("start"), "statut": ev.get("status"),
                "client_id": c.get("id"), "client": nom, "technicien": (ev.get("user") or {}).get("firstName"),
                "services": [(s.get("name") or "")[:80] for s in services],
                "pianos": [{"id": (p.get("piano") or {}).get("id"),
                            "piano": f"{(p.get('piano') or {}).get('make') or ''} {(p.get('piano') or {}).get('model') or ''}".strip(),
                            "dernier_service": (p.get("piano") or {}).get("calculatedLastService")} for p in pianos],
            })
        d = f
    return sorted(out, key=lambda r: r["debut"] or "")


# ════════════════════════════════════════════════════════════════════
# Surveillance élargie : « piano dû » malgré un RV, et date d'accord pas mise à jour
# ════════════════════════════════════════════════════════════════════
# Gazelle n'envoie pas le rappel « piano dû » si le PIANO a un accord prévu
# (nextTuningScheduled). Il le laisse partir si le piano n'est pas sur le RV
# (oublié, autre piano du client), ou si rien n'est coché accord. Après la visite,
# la date du dernier accord doit avancer ; sinon le rappel reviendra.

_Q_RV_LARGE = """query($start: CoreDate!, $end: CoreDate!) {
  allEventsBatched(first: 200, filters: {startOn: $start, endOn: $end}) {
    nodes { id start type status
      client { id companyName defaultContact { firstName lastName }
        allPianos(first: 20, status: [ACTIVE]) { nodes { id make model calculatedLastService calculatedNextService nextTuningScheduled { id } } } }
      user { firstName }
      allEventPianos(first: 20) { nodes { isTuning piano { id make model calculatedLastService } } } } } }"""


# Vincent-d'Indy, Place des Arts, Orford (+ tout client de 4 pianos actifs ou plus)
_INSTITUTIONS = {"cli_9UMLkteep8EsISbG", "cli_HbEwl9rN11pSuDEU", "cli_PmqPUBTbPFeCMGmz"}


def _nom_client(c) -> str:
    dc = (c or {}).get("defaultContact") or {}
    return (c or {}).get("companyName") or f"{dc.get('firstName', '')} {dc.get('lastName', '')}".strip()


def _piano_txt(p) -> str:
    return f"{p.get('make') or ''} {p.get('model') or ''}".strip() or p.get("id", "")


def rappels_a_risque(gz, jours_avant: int = 7, jours_apres: int = 21, aujourd_hui: date = None) -> List[Dict[str, Any]]:
    """1) RV à venir : piano du client en retard (ou dû avant le RV) que Gazelle ne relie à
          aucun accord prévu -> le client peut recevoir « piano dû » malgré son RV.
       2) RV complétés récents avec accord coché, mais date du dernier accord pas avancée."""
    from core.timezone_utils import aujourdhui_montreal
    jour = aujourd_hui or aujourdhui_montreal()
    debut, fin = jour - timedelta(days=jours_avant), jour + timedelta(days=jours_apres)
    evs, d = [], debut
    while d < fin:
        f = min(d + timedelta(days=7), fin)
        evs += _rv_fenetre(gz, d, f, _Q_RV_LARGE)
        d = f
    out, vus, signales = [], set(), set()
    for ev in sorted(evs, key=lambda e: e.get("start") or ""):
        if ev["id"] in vus or ev.get("type") != "APPOINTMENT" or ev.get("status") == "CANCELLED":
            continue
        vus.add(ev["id"])
        c = ev.get("client") or {}
        jour_rv = _jour_montreal(ev.get("start"))
        ev_pianos = (ev.get("allEventPianos") or {}).get("nodes") or []
        base = {"event_id": ev["id"], "jour": jour_rv, "statut": ev.get("status"), "client_id": c.get("id"),
                "client": _nom_client(c), "technicien": (ev.get("user") or {}).get("firstName")}
        if ev.get("status") == "COMPLETE":
            for n in ev_pianos:
                p = n.get("piano") or {}
                if n.get("isTuning") and (p.get("calculatedLastService") or "") < jour_rv:
                    out.append({**base, "type": "date_pas_mise_a_jour", "piano_id": p.get("id"), "piano": _piano_txt(p),
                                "detail": f"Accord coché et RV complété le {jour_rv}, mais dernier accord = "
                                          f"{p.get('calculatedLastService') or 'aucun'}."})
            continue
        if jour_rv < jour.isoformat():
            continue  # RV passé pas encore complété : hors sujet ici
        sur_rv = {(n.get("piano") or {}).get("id") for n in ev_pianos}
        pianos_client = (c.get("allPianos") or {}).get("nodes") or []
        if c.get("id") in _INSTITUTIONS or len(pianos_client) >= 4:
            continue  # institutions : accords à la demande, pas de rappels « piano dû » utiles
        for p in pianos_client:
            prochain = p.get("calculatedNextService") or ""
            if not prochain or prochain > jour_rv or p.get("nextTuningScheduled") or (c.get("id"), p["id"]) in signales:
                continue
            signales.add((c.get("id"), p["id"]))
            if not ev_pianos:
                pourquoi = "le RV n'a aucun piano attaché"
            elif p["id"] in sur_rv:
                pourquoi = "le piano est sur le RV mais pas coché « accord »"
            else:
                pourquoi = "ce piano n'est pas sur le RV (autre piano du client ?)"
            out.append({**base, "type": "piano_du_malgre_rv", "piano_id": p["id"], "piano": _piano_txt(p),
                        "detail": f"Accord dû le {prochain}, RV le {jour_rv}, mais Gazelle ne voit aucun accord prévu "
                                  f"pour ce piano : {pourquoi}. Le client peut recevoir « piano dû »."})
    return out
