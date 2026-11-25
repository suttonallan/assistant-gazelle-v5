"""Heures de travail d'un technicien un jour donné, telles que réglées dans Gazelle
(disponibilités du planificateur : jours, heures, semaines alternées, dates exclues).

Lecture seule, au plus une fois l'heure par technicien. Sert à Ivo : plages libres et
garde-fou avant de créer un RV. Ce que Gazelle applique déjà à la réservation en ligne,
on l'applique ainsi aux RV créés par l'assistant.
"""
import logging
import time
from datetime import date, datetime, time as heure, timedelta
from typing import Any, Dict, List, Optional, Tuple

_CHAMPS = "startTime endTime recurrenceRule startDate endDate includeDates excludeDates"
_CACHE: Dict[str, Tuple[float, Optional[List[Dict[str, Any]]]]] = {}
_JOURS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _dispos(gz, user_id: str) -> Optional[List[Dict[str, Any]]]:
    """Disponibilités Gazelle du technicien ; None si illisibles."""
    le, val = _CACHE.get(user_id, (0.0, None))
    if time.time() - le < 3600 and val is not None:
        return val
    try:
        res = gz._execute_query("query($u: String!) { allSchedulerAvailabilities(userId: $u) { %s } }" % _CHAMPS,
                                {"u": user_id})
        val = (res.get("data") or {}).get("allSchedulerAvailabilities")
        if res.get("errors") or not isinstance(val, list):
            raise RuntimeError(res.get("errors"))
    except Exception as e:
        logging.warning(f"Disponibilités Gazelle de {user_id} illisibles : {e}")
        return None
    _CACHE[user_id] = (time.time(), val)
    return val


def _s_applique(d: Dict[str, Any], jour: date) -> bool:
    iso = jour.isoformat()
    if iso in (d.get("excludeDates") or []):
        return False
    if iso in (d.get("includeDates") or []):
        return True
    debut, fin = d.get("startDate"), d.get("endDate")
    if not debut or iso < debut or (fin and iso > fin):
        return False
    regle = dict(p.split("=", 1) for p in (d.get("recurrenceRule") or "").replace("RRULE:", "").split(";") if "=" in p)
    if regle.get("FREQ", "WEEKLY") != "WEEKLY":
        return False  # forme inconnue : on ne devine pas
    if jour.weekday() not in {_JOURS[j] for j in regle.get("BYDAY", "").split(",") if j in _JOURS}:
        return False
    intervalle = int(regle.get("INTERVAL") or 1)
    d0 = date.fromisoformat(debut)
    semaines = ((jour - timedelta(days=jour.weekday())) - (d0 - timedelta(days=d0.weekday()))).days // 7
    return semaines % intervalle == 0


def heures_travail(gz, user_id: str, jour: date, tz) -> Tuple[bool, Optional[Tuple[datetime, datetime]]]:
    """(connu, bornes). connu=False : disponibilités illisibles, ne rien conclure.
    connu=True et bornes=None : ce jour-là, le technicien n'a pas de disponibilité dans Gazelle."""
    dispos = _dispos(gz, user_id)
    if dispos is None:
        return False, None
    if not dispos:
        return False, None  # aucun réglage (ex. Allan) : on ne conclut rien
    plages = []
    for d in dispos:
        try:
            if _s_applique(d, jour):
                plages.append((heure.fromisoformat(d["startTime"]), heure.fromisoformat(d["endTime"])))
        except Exception:
            continue
    if not plages:
        return True, None
    return True, (datetime.combine(jour, min(a for a, _ in plages), tz),
                  datetime.combine(jour, max(b for _, b in plages), tz))
