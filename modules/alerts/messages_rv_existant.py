#!/usr/bin/env python3
"""
Messages clients dans Front (boîte info@) : signaler un rendez-vous déjà pris.

Cas réel (2026-10-16) : une cliente laisse un message vocal, puis quelques
minutes plus tard prend un rendez-vous en ligne, accepté par le technicien.
Le lendemain matin, Louise voit le message et rappelle la cliente sans savoir
qu'elle avait déjà son rendez-vous.

Règle générale (pas de cas par cas) : chaque message client OUVERT dans info@
est rapproché de la fiche Gazelle (par téléphone ou courriel). Si ce client a
un rendez-vous à venir, on ajoute un commentaire interne dans la conversation
Front : date, heure, technicien. Rien n'est fermé ni masqué : Louise garde son
jugement, elle a seulement l'information au bon endroit.

La vérification tourne à intervalles réguliers (pas seulement à l'arrivée du
message) : un RV pris APRÈS le message est donc signalé au passage suivant.
Un même RV n'est signalé qu'une fois par conversation.
"""
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

INBOX_INFO = "inb_342mn"
JOURS_A_SURVEILLER = 4
CLE_SIGNALES = "messages_rv_existant_signales"
AUTEUR_COMMENTAIRE = "asutton@piano-tek.com"

# Adresses qui ne sont jamais celles d'un client (avis automatiques, équipe).
DOMAINES_IGNORES = ("piano-tek.com", "gznmail.com", "gazelleapp.io", "zoom.us",
                    "frontapp.com", "google.com", "interac.ca", "payments.interac.ca")

TECHS = {
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_bbt59aCUqUaDWA8n": "Margot",
    "usr_tndhXmnT0iakT4HF": "Louise",
}

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juill.", "août",
        "sept.", "oct.", "nov.", "déc."]


def _chiffres(v: Any) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return d


def telephone_du_sujet(sujet: str) -> Optional[str]:
    """« Nouveau message vocal de (514) 592-8664 … » / « 📩 SMS Reçu de +15145928664 »."""
    m = re.search(r"(?:message vocal de|SMS Re[çc]u de)\s*([+\d()\s.\-]{10,20})", sujet or "", re.I)
    if not m:
        return None
    d = _chiffres(m.group(1))
    return d if len(d) == 10 else None


def courriel_client(conv: Dict[str, Any]) -> Optional[str]:
    handle = ((conv.get("recipient") or {}).get("handle") or "").strip().lower()
    if "@" not in handle or handle.split("@")[1].endswith(DOMAINES_IGNORES):
        return None
    return handle


def _client_par_courriel(courriel: str) -> Optional[str]:
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    h = db._get_headers()
    for table, champ in (("gazelle_clients", "external_id"), ("gazelle_contacts", "client_external_id")):
        try:
            r = requests.get(f"{db.api_url}/{table}", headers=h, timeout=15,
                             params={"select": champ, "email": f"ilike.{courriel}", "limit": "1"})
            lignes = r.json() if r.status_code == 200 else []
        except Exception:
            lignes = []
        if lignes and lignes[0].get(champ):
            return lignes[0][champ]
    return None


def _client_par_telephone(tel: str) -> Optional[str]:
    from core.zoom_resumes_appels import trouver_client
    c = trouver_client([tel])
    return (c or {}).get("external_id")


def nom_client(client_id: str) -> str:
    """Nom affiché de la fiche Gazelle (pour que la note dise DE QUI il s'agit)."""
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    try:
        r = requests.get(f"{db.api_url}/gazelle_clients", headers=db._get_headers(), timeout=15,
                         params={"select": "company_name,first_name,last_name",
                                 "external_id": f"eq.{client_id}", "limit": "1"})
        c = (r.json() if r.status_code == 200 else [None])[0] or {}
    except Exception:
        c = {}
    return (c.get("company_name")
            or " ".join(x for x in (c.get("first_name"), c.get("last_name")) if x)
            or "Ce client")


def prochain_rv(client_id: str) -> Optional[Dict[str, Any]]:
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage()
    maintenant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        r = requests.get(
            f"{db.api_url}/gazelle_appointments", headers=db._get_headers(), timeout=15,
            params={
                "select": "external_id,appointment_date,appointment_time,technicien,status,start_datetime",
                "client_external_id": f"eq.{client_id}",
                "start_datetime": f"gte.{maintenant}",
                "status": "neq.CANCELLED",
                "order": "start_datetime.asc",
                "limit": "1",
            })
        lignes = r.json() if r.status_code == 200 else []
    except Exception:
        lignes = []
    return lignes[0] if lignes else None


def texte_commentaire(rv: Dict[str, Any], nom: str = "Ce client", par: str = "") -> str:
    quand = str(rv.get("appointment_date") or "")[:10]
    try:
        d = datetime.strptime(quand, "%Y-%m-%d")
        quand = f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"
    except ValueError:
        pass
    heure = str(rv.get("appointment_time") or "")[:5]
    if heure:
        quand += f" à {heure.replace(':', ' h ')}"
    tech = TECHS.get(rv.get("technicien") or "", "")
    avec = f" avec {tech}" if tech else ""
    source = f" (fiche Gazelle trouvée par {par})" if par else ""
    return (f"📅 {nom}{source} a déjà un rendez-vous : {quand}{avec}. "
            "Vérifier avant de rappeler. (Assistant Gazelle)")


def verifier_messages() -> Dict[str, int]:
    """Point d'entrée de la tâche planifiée."""
    from core.front_client import get_front_client
    from core.supabase_storage import SupabaseStorage

    stats = {"conversations": 0, "clients_trouves": 0, "signales": 0}
    front = get_front_client()
    db = SupabaseStorage()
    deja = db.get_system_setting(CLE_SIGNALES) or []

    depuis = time.time() - JOURS_A_SURVEILLER * 86400
    requete = f"inbox:{INBOX_INFO} is:open"
    convs = front._get(f"/conversations/search/{quote(requete, safe='')}",
                       params={"limit": 100}).get("_results", [])
    convs = [c for c in convs if (c.get("created_at") or 0) >= depuis]

    nouveaux = []
    for conv in convs:
        stats["conversations"] += 1
        tel = telephone_du_sujet(conv.get("subject", ""))
        client_id = _client_par_telephone(tel) if tel else None
        par = f"le numéro ({tel[:3]}) {tel[3:6]}-{tel[6:]}" if client_id else ""
        if not client_id:
            courriel = courriel_client(conv)
            client_id = _client_par_courriel(courriel) if courriel else None
            par = f"le courriel {courriel}" if client_id else ""
        if not client_id:
            continue
        stats["clients_trouves"] += 1

        rv = prochain_rv(client_id)
        if not rv:
            continue
        cle = f"{conv['id']}:{rv['external_id']}"
        if cle in deja:
            continue
        try:
            front.add_comment(conv["id"], texte_commentaire(rv, nom_client(client_id), par),
                              AUTEUR_COMMENTAIRE)
            nouveaux.append(cle)
            stats["signales"] += 1
        except Exception as e:
            print(f"⚠️ Commentaire Front impossible ({conv['id']}) : {e}")

    if nouveaux:
        db.save_system_setting(CLE_SIGNALES, (deja + nouveaux)[-500:])
    return stats


if __name__ == "__main__":
    print(verifier_messages())
