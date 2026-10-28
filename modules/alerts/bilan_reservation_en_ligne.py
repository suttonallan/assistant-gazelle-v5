"""Bilan quotidien de la nouvelle page de réservation en ligne → info@ (Front).

Lit la table reservation_en_ligne_evenements (alimentée par le service de
réservation, dépôt privé ptm-reservation) et envoie UN message par jour :
entonnoir anonyme par étape, réservations faites par la nouvelle page,
personnes parties sans envoyer leur demande (coordonnées laissées), hors zone.
Aucun message si la journée n'a eu aucune activité.
"""
from __future__ import annotations

import html
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from core.timezone_utils import MONTREAL_TZ

DESTINATAIRE = "info@piano-tek.com"
TABLE = "reservation_en_ligne_evenements"
CLE_ENVOYES = "bilan_reservation_en_ligne_envoyes"

# Libellés des étapes, dans l'ordre de la page (voir static/index.html de ptm-reservation)
ETAPES = {1: "Ont ouvert la page (choix du piano)", 2: "Sont passés au choix du moment",
          3: "Sont arrivés aux coordonnées", 4: "Ont envoyé leur demande"}
RATTRAPAGE_JOURS = 7      # un bilan manqué (redéploiement, échec d'envoi) part le lendemain
CONSERVATION_JOURS = 60   # Loi 25 : coordonnées effacées du journal après ce délai (restent dans Gazelle)
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _jour_fr(j: date) -> str:
    return f"{j.day} {MOIS[j.month - 1]} {j.year}"


def _evenements(jour: date) -> List[Dict[str, Any]]:
    from core.supabase_storage import SupabaseStorage
    db = SupabaseStorage(silent=True)
    base = lambda: db.client.table(TABLE).select("cree_le,type,cle,client_id,details").eq("jour", jour.isoformat())
    # Étapes et autres événements lus séparément : les étapes, nombreuses, ne
    # doivent jamais faire disparaître les demandes et abandons (limite de lignes).
    autres = base().neq("type", "etape").order("cree_le").limit(1000).execute().data or []
    etapes, debut = [], 0
    while True:
        lot = base().eq("type", "etape").order("id").range(debut, debut + 999).execute().data or []
        etapes += lot
        if len(lot) < 1000:
            break
        debut += 1000
    return etapes + autres


def _heure(iso: str) -> str:
    import re
    try:
        # Python 3.10 : fromisoformat refuse les fractions de seconde de longueur variable
        propre = re.sub(r"\.\d+", "", iso.replace("Z", "+00:00"))
        return datetime.fromisoformat(propre).astimezone(MONTREAL_TZ).strftime("%H h %M")
    except (ValueError, AttributeError):
        return ""


def composer_bilan(jour: date, evts: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Retourne {sujet, html} ou None s'il n'y a rien à signaler."""
    if not evts:
        return None
    e = lambda s: html.escape(str(s) if s not in (None, "") else "—")
    etapes = Counter()
    for ev in evts:
        if ev["type"] == "etape":
            try:
                etapes[int((ev.get("cle") or "etape0")[5])] += 1
            except (ValueError, IndexError):
                pass
    par_type = lambda t: [ev for ev in evts if ev["type"] == t]
    reservations, hors_zone, refus = par_type("reservation"), par_type("hors_zone"), par_type("refus")
    # Abandons : une ligne par personne, et jamais quelqu'un qui a finalement envoyé
    # sa demande le même jour (on ne relance pas un client qui a réservé).
    abouties = {ev.get("client_id") for ev in reservations + hors_zone if ev.get("client_id")}
    abouties_coord = {((ev.get("details") or {}).get("courriel") or "").lower() for ev in hors_zone} - {""}
    abandons, vus = [], set()
    for ev in par_type("abandon"):
        cid = ev.get("client_id")
        courriel = ((ev.get("details") or {}).get("courriel") or "").lower()
        if cid in abouties or courriel in abouties_coord or (cid or courriel) in vus:
            continue
        vus.add(cid or courriel)
        abandons.append(ev)

    parties = [f"<p><b>Réservation en ligne — bilan du {_jour_fr(jour)}</b> "
               "(page reserver.pianotechniquemontreal.com)</p>"]

    if etapes:
        lignes = "".join(f"<tr><td>{e(ETAPES[n])}</td><td style='text-align:right'><b>{etapes.get(n, 0)}</b></td></tr>"
                         for n in sorted(ETAPES))
        parties.append("<p><b>Parcours des visiteurs</b> (anonyme)</p>"
                       f"<table cellpadding='4' style='border-collapse:collapse'>{lignes}</table>")

    def liste(titre: str, items: List[Dict[str, Any]], ligne) -> None:
        if items:
            parties.append(f"<p><b>{titre} ({len(items)})</b></p><ul>"
                           + "".join(f"<li>{ligne(ev)}</li>" for ev in items) + "</ul>")

    def qui(ev):
        d = ev.get("details") or {}
        return f"{e(d.get('nom'))} — {e(d.get('telephone'))} — {e(d.get('courriel'))}"

    liste("Demandes de rendez-vous envoyées par la nouvelle page", reservations,
          lambda ev: f"{e((ev.get('details') or {}).get('nom'))} — RV demandé : "
                     f"{e((ev.get('details') or {}).get('rendez_vous'))} (à approuver dans Gazelle)")
    liste("Partis sans envoyer leur demande (coordonnées laissées)", abandons,
          lambda ev: f"{qui(ev)} — à {_heure(ev['cree_le'])}")
    liste("Demandes hors zone à fixer", hors_zone, lambda ev: qui(ev))
    liste("Demandes refusées par Gazelle", refus,
          lambda ev: f"{qui(ev)} — {e((ev.get('details') or {}).get('raison'))}")

    if abandons:
        parties.append("<p>La page avisait ces personnes qu'on pourrait leur écrire <b>une seule fois</b> "
                       "pour les aider à compléter : un message, sans relance. La note est aussi dans leur fiche Gazelle.</p>")
    parties.append("<p style='color:#777'>Envoyé automatiquement par l'assistant, une fois par jour.</p>")

    sujet = (f"Réservation en ligne — bilan du {_jour_fr(jour)} : "
             f"{len(reservations)} demande(s), {len(abandons)} abandon(s) avec coordonnées")
    return {"sujet": sujet, "html": "".join(parties)}


def purger_coordonnees() -> None:
    """Efface nom, téléphone et courriel du journal après CONSERVATION_JOURS (les compteurs restent)."""
    from core.supabase_storage import SupabaseStorage
    limite = (datetime.now(MONTREAL_TZ).date() - timedelta(days=CONSERVATION_JOURS)).isoformat()
    SupabaseStorage(silent=True).client.table(TABLE).update({"details": {}}) \
        .lt("jour", limite).neq("type", "etape").execute()


def envoyer_bilans_en_attente() -> Dict[str, Any]:
    """Tâche du matin : la veille, plus tout jour récent dont le bilan n'est pas parti."""
    hier = datetime.now(MONTREAL_TZ).date() - timedelta(days=1)
    resultats = [envoyer_bilan(hier - timedelta(days=n)) for n in range(RATTRAPAGE_JOURS - 1, -1, -1)]
    try:
        purger_coordonnees()
    except Exception as e:  # noqa: BLE001 — la purge sera retentée demain
        print(f"⚠️ Purge du journal de réservation : {e}")
    return {"envoyes": [r["jour"] for r in resultats if r.get("envoye")],
            "echecs": [r["jour"] for r in resultats if r.get("a_envoyer") and not r.get("envoye") and not r.get("deja_envoye")]}


def envoyer_bilan(jour: Optional[date] = None, envoyer: bool = True) -> Dict[str, Any]:
    """Par défaut : la veille (heure de Montréal). N'envoie qu'une fois par jour."""
    from core.email_notifier import get_email_notifier
    from core.supabase_storage import SupabaseStorage

    jour = jour or (datetime.now(MONTREAL_TZ).date() - timedelta(days=1))
    bilan = composer_bilan(jour, _evenements(jour))
    stats: Dict[str, Any] = {"jour": jour.isoformat(), "a_envoyer": bool(bilan), "envoye": False}
    if bilan and envoyer and jour < date(2026, 10, 28):
        return stats  # le journal commence le 28 oct. 2026 : rien à rattraper avant
    if not bilan or not envoyer:
        if bilan:
            stats["apercu"] = bilan
        return stats
    db = SupabaseStorage(silent=True)
    deja = db.get_system_setting(CLE_ENVOYES) or []
    if jour.isoformat() in deja:
        stats["deja_envoye"] = True
        return stats
    ok = get_email_notifier().send_email(to_emails=[DESTINATAIRE], subject=bilan["sujet"],
                                         html_content=bilan["html"])
    if ok:
        db.save_system_setting(CLE_ENVOYES, (deja + [jour.isoformat()])[-60:])
    stats["envoye"] = ok
    return stats
