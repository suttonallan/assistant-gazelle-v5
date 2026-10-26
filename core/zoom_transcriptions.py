"""
Appels enregistrés Zoom Phone → note fiable dans la chronologie Gazelle.

Le résumé IA de Zoom oublie des détails (disponibilités, courriel épelé) et se trompe
parfois de prix. Quand un appel est enregistré, on travaille plutôt à partir de la
transcription complète de l'enregistrement :

1. Toutes les 10 minutes, on liste les enregistrements des 2 derniers jours.
2. Pour chaque enregistrement pas encore traité dont la transcription est prête,
   on la télécharge et Claude en tire la note (même consignes et même classement
   que les résumés : fiche du client, client potentiel créé, ou courriel à info@).
3. Transcription toujours absente 3 h après l'appel → courriel à info@ pour ne
   rien perdre.

Permissions nécessaires sur l'app Zoom « texto zomm vers assistant » :
phone:read:list_recordings:admin et phone:read:recording_transcript:admin.
Sans elles, ce module ne fait rien (et le résumé IA reste la source).
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

from core.zoom_sms import get_zoom_access_token, ZOOM_API_BASE_URL

CLE_TRAITES = "zoom_transcriptions_traitees"
DELAI_ABANDON = timedelta(hours=3)


def _get(chemin: str, token: str, **params) -> Dict[str, Any]:
    r = requests.get(f"{ZOOM_API_BASE_URL}{chemin}", headers={"Authorization": f"Bearer {token}"},
                     params=params or None, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Zoom GET {chemin} → {r.status_code} : {r.text[:300]}")
    return r.json()


def enregistrements_recents(jours: int = 2) -> List[Dict[str, Any]]:
    """Enregistrements d'appels du compte sur les derniers jours (toutes lignes et files)."""
    token = get_zoom_access_token()
    fin = datetime.now(timezone.utc).date()
    debut = fin - timedelta(days=jours)
    tous, suivant = [], ""
    for _ in range(10):
        params = {"from": str(debut), "to": str(fin), "page_size": 100}
        if suivant:
            params["next_page_token"] = suivant
        d = _get("/phone/recordings", token, **params)
        tous += d.get("recordings") or []
        suivant = d.get("next_page_token") or ""
        if not suivant:
            break
    return tous


def _texte_transcription(brut: Any) -> str:
    """Transforme la transcription Zoom (JSON, structure tolérée) en texte « Interlocuteur : phrase »."""
    if isinstance(brut, str):
        return brut
    lignes: List[str] = []

    def parcourir(o):
        if isinstance(o, dict):
            if isinstance(o.get("text"), str) and o["text"].strip():
                qui = ""
                users = o.get("users") or o.get("speakers") or []
                if isinstance(users, list) and users and isinstance(users[0], dict):
                    qui = users[0].get("username") or users[0].get("name") or ""
                qui = qui or o.get("username") or o.get("speaker") or ""
                lignes.append(f"{qui} : {o['text'].strip()}" if qui else o["text"].strip())
                return
            for v in o.values():
                parcourir(v)
        elif isinstance(o, list):
            for v in o:
                parcourir(v)

    parcourir(brut)
    return "\n".join(lignes)


def telecharger_transcription(rec: Dict[str, Any], token: str) -> str:
    """Texte de la transcription, ou "" si elle n'est pas (encore) prête."""
    url = rec.get("transcript_download_url")
    try:
        if url:
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
            if r.status_code != 200:
                return ""
            try:
                return _texte_transcription(r.json())
            except ValueError:
                return r.text
        return _texte_transcription(_get(f"/phone/recording_transcript/download/{rec['id']}", token))
    except Exception:
        return ""


def _numeros_externes(rec: Dict[str, Any]) -> List[str]:
    from core.zoom_resumes_appels import _chiffres, NUMEROS_PTM
    vus = []
    for cle in ("caller_number", "callee_number", "caller_did_number", "callee_did_number"):
        d = _chiffres(rec.get(cle))
        if len(d) == 10 and d not in NUMEROS_PTM and d not in vus:
            vus.append(d)
    return vus


def _date(v: Any):
    from core.zoom_resumes_appels import _date_iso
    return _date_iso(v)


def traiter() -> Dict[str, Any]:
    """Point d'entrée de la tâche planifiée. Ne lève jamais d'exception."""
    from core.supabase_storage import SupabaseStorage
    from core.zoom_resumes_appels import (cles_zoom_configurees, trouver_client, reecrire_resume,
                                          classer_note, _courriel_secours)
    if not cles_zoom_configurees():
        return {"note": "clés Zoom absentes"}
    try:
        recs = enregistrements_recents()
    except Exception as e:
        msg = str(e)
        if "401" in msg or "403" in msg or "scope" in msg.lower():
            return {"note": "permission d'enregistrements absente sur l'app Zoom"}
        print(f"⚠️ Enregistrements Zoom illisibles : {msg}")
        return {"erreur": msg}

    db = SupabaseStorage()
    traites = db.get_system_setting(CLE_TRAITES) or []
    token = get_zoom_access_token()
    bilan = {"traites": 0, "en_attente": 0, "abandonnes": 0}

    for rec in recs:
        rid = str(rec.get("id") or "")
        if not rid or rid in traites:
            continue
        numeros = _numeros_externes(rec)
        texte = telecharger_transcription(rec, token)
        moment = _date(rec.get("date_time") or rec.get("start_time"))

        if not texte.strip():
            if moment and datetime.now(timezone.utc) - moment > DELAI_ABANDON:
                _courriel_secours("Transcription Zoom introuvable 3 h après l'appel : écouter l'enregistrement dans Zoom.",
                                  numeros, "Appel enregistré sans transcription")
                traites.append(rid)
                bilan["abandonnes"] += 1
            else:
                bilan["en_attente"] += 1
            continue

        appel = {
            "transcription": texte,
            "date": rec.get("date_time"),
            "duree_secondes": rec.get("duration"),
            "sens": rec.get("direction"),
            "employe_ptm": rec.get("owner", {}).get("name") if isinstance(rec.get("owner"), dict) else rec.get("owner_name"),
            "_ids": {"recording_id": rid},
        }
        try:
            client = trouver_client(numeros)
            r = reecrire_resume(appel, client)
            res = classer_note(r, numeros, client, f"enr:{rid}")
            if res.get("ok"):
                traites.append(rid)
                bilan["traites"] += 1
                print(f"✅ Appel enregistré {rid} classé : {res}")
        except Exception as e:
            print(f"❌ Transcription {rid} non traitée : {e}")

    db.save_system_setting(CLE_TRAITES, traites[-1000:])
    return bilan
