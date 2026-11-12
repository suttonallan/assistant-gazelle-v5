"""Historique complet d'un client Gazelle — une seule source pour Ivo, l'assistant et Ma Journée.

- messages_gazelle(...)   : section « Messages » de Gazelle (courriels/textos envoyés ou planifiés)
                            avec leur statut de suivi (ouvert, cliqué, livré, rejeté, désabonné…).
- suivi_soumission(...)   : le courriel d'une soumission a-t-il été envoyé, ouvert, cliqué ?
- dossier_client(...)     : texte complet du dossier (fiche, pianos, chronologie, factures,
                            soumissions avec suivi, messages) pour une question « que sait-on de ce client ? ».

Tout est en LECTURE seule, en direct de Gazelle, heures de Montréal.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.timezone_utils import MONTREAL_TZ

_log = logging.getLogger(__name__)

STATUTS_MSG = {"SENT": "envoyé", "ACCEPTED": "accepté", "DELIVERED": "livré", "OPENED": "ouvert",
               "CLICKED": "cliqué", "BOUNCED": "rejeté (adresse invalide)", "DROPPED": "abandonné",
               "FAILED": "échec", "UNDELIVERED": "non livré", "COMPLAINED": "signalé comme pourriel",
               "UNSUBSCRIBED": "désabonné", "PENDING": "en attente", "QUEUED": "en file",
               "RECEIVED": "reçu", "SCHEDULED": "planifié"}
# Statuts qui prouvent que le client a vu le message.
VUS = {"OPENED", "CLICKED", "UNSUBSCRIBED", "COMPLAINED"}

_Q_MESSAGES = """query($f: PrivateAllSentOrScheduledMessagesFilter, $after: String) {
  allSentOrScheduledMessages(first: 100, after: $after, filters: $f) {
    pageInfo { hasNextPage endCursor }
    nodes { id type status deliveryType sentOrScheduledAt shortSummary recipientName
      relatedId relatedType client { id } } } }"""


def _gz():
    from core.gazelle_api_client import GazelleAPIClient
    return GazelleAPIClient()


def _data(res: Dict[str, Any]) -> Dict[str, Any]:
    if res.get("errors"):
        raise RuntimeError(str(res["errors"])[:300])
    return res.get("data") or res


def _montreal(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return iso
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(MONTREAL_TZ).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso


def messages_gazelle(q: Optional[str] = None, client_id: Optional[str] = None,
                     limite: int = 25, pages: int = 1) -> List[Dict[str, Any]]:
    """Messages Gazelle correspondant à la recherche `q` (numéro de soumission/facture, nom…),
    filtrés sur `client_id` si fourni. Plus récents d'abord."""
    gz, out, after = _gz(), [], None
    for _ in range(max(1, pages)):
        bloc = _data(gz._execute_query(_Q_MESSAGES, {"f": {"search": q} if q else {}, "after": after}))
        bloc = bloc.get("allSentOrScheduledMessages") or {}
        for n in bloc.get("nodes") or []:
            if client_id and (n.get("client") or {}).get("id") != client_id:
                continue
            n["quand_montreal"] = _montreal(n.get("sentOrScheduledAt"))
            n["statut_fr"] = STATUTS_MSG.get(n.get("status"), n.get("status"))
            out.append(n)
        pi = bloc.get("pageInfo") or {}
        if len(out) >= limite or not pi.get("hasNextPage"):
            break
        after = pi.get("endCursor")
    return out[:limite]


def _nom_client(client_id: str) -> Dict[str, Any]:
    q = """query($id: String!) { client(id: $id) { id companyName status createdAt preferenceNotes
      defaultContact { firstName lastName } } }"""
    return (_data(_gz()._execute_query(q, {"id": client_id})).get("client")) or {}


def messages_du_client(client_id: str, limite: int = 40, fiche: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """Tous les messages Gazelle récents d'un client (recherche par nom puis filtre sur la fiche)."""
    fiche = fiche or _nom_client(client_id)
    dc = fiche.get("defaultContact") or {}
    cle = (dc.get("lastName") or "").strip() or (fiche.get("companyName") or "").strip()
    if not cle:
        return []
    return messages_gazelle(q=cle, client_id=client_id, limite=limite, pages=5)


def suivi_soumission(numero: Any, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Suivi du courriel d'une soumission : {statut, statut_fr, quand, vu}. None si jamais envoyée."""
    try:
        msgs = messages_gazelle(q=str(numero), client_id=client_id, limite=10)
    except Exception as e:
        _log.warning("Suivi soumission %s indisponible : %s", numero, e)
        return None
    msgs = [m for m in msgs if f"#{numero}" in (m.get("shortSummary") or "")]
    if not msgs:
        return None
    # Le plus « avancé » des envois (ouvert > livré > envoyé), puis le plus récent.
    m = sorted(msgs, key=lambda m: (m.get("status") in VUS, m.get("sentOrScheduledAt") or ""), reverse=True)[0]
    return {"statut": m.get("status"), "statut_fr": m.get("statut_fr"), "quand": m.get("quand_montreal"),
            "vu": m.get("status") in VUS, "envois": len(msgs)}


def phrase_suivi(s: Optional[Dict[str, Any]]) -> str:
    """Phrase courte pour un briefing : « envoyée le 2024-05-28, ouverte par le client »."""
    if not s:
        return "jamais envoyée au client par Gazelle"
    jour = (s.get("quand") or "")[:10]
    if s.get("vu"):
        return f"envoyée le {jour}, OUVERTE par le client" + (" (lien cliqué)" if s.get("statut") == "CLICKED" else "")
    return f"envoyée le {jour}, statut « {s.get('statut_fr')} » (pas d'ouverture détectée)"


def dossier_client(client_id: str) -> str:
    """Dossier complet d'un client, en texte, pour répondre à « que sait-on de ce client ? »."""
    gz = _gz()
    parties: List[str] = []
    fiche: Dict[str, Any] = {}
    try:
        fiche = _nom_client(client_id)
        dc = fiche.get("defaultContact") or {}
        nom = fiche.get("companyName") or f"{dc.get('firstName') or ''} {dc.get('lastName') or ''}".strip()
        parties.append(f"FICHE : {nom} ({client_id}) — statut {fiche.get('status')} — client depuis "
                       f"{(fiche.get('createdAt') or '')[:10]}"
                       + (f"\nPréférences : {fiche['preferenceNotes'][:400]}" if fiche.get("preferenceNotes") else ""))
    except Exception as e:
        parties.append(f"FICHE : non disponible ({e})")

    try:
        res = _data(gz._execute_query("""query($c: String!) { allTimelineEntries(clientId: $c, first: 100) {
          edges { node { occurredAt type summary comment piano { id make model } } } } }""", {"c": client_id}))
        lignes = []
        for e in (res.get("allTimelineEntries") or {}).get("edges") or []:
            n = e["node"]
            texte = " — ".join(x for x in (n.get("summary"), n.get("comment")) if x)
            if not texte or n.get("type") == "SYSTEM_MESSAGE" and "fusionn" in texte:
                continue
            p = n.get("piano") or {}
            lignes.append(f"[{_montreal(n.get('occurredAt'))}] {n.get('type')}"
                          + (f" ({p.get('make')} {p.get('model') or ''})".rstrip() if p else "")
                          + f" : {texte[:350]}")
        parties.append("CHRONOLOGIE (plus récent d'abord) :\n" + ("\n".join(lignes[:60]) or "(vide)"))
    except Exception as e:
        parties.append(f"CHRONOLOGIE : non disponible ({e})")

    try:
        from api.ivo_routes import _factures_resume
        parties.append("FACTURES :" + _factures_resume(client_id))
    except Exception as e:
        parties.append(f"FACTURES : non disponibles ({e})")

    msgs: List[Dict[str, Any]] = []
    try:
        msgs = messages_du_client(client_id, limite=40, fiche=fiche)
    except Exception as e:
        parties.append(f"MESSAGES : non disponibles ({e})")

    try:
        res = _data(gz._execute_query("""query($c: String) { allEstimates(first: 20, filters: {clientId: $c}) {
          nodes { number estimatedOn expiresOn isArchived recommendedTierTotal } } }""", {"c": client_id}))
        lignes = []
        for est in (res.get("allEstimates") or {}).get("nodes") or []:
            num = est.get("number")
            envois = [m for m in msgs if f"#{num}" in (m.get("shortSummary") or "")]
            if envois:
                m = sorted(envois, key=lambda m: (m.get("status") in VUS, m.get("sentOrScheduledAt") or ""),
                           reverse=True)[0]
                suivi = phrase_suivi({"statut": m["status"], "statut_fr": m["statut_fr"],
                                      "quand": m["quand_montreal"], "vu": m["status"] in VUS})
            else:
                suivi = phrase_suivi(suivi_soumission(num, client_id))
            lignes.append(f"#{num} du {est.get('estimatedOn')} — {(est.get('recommendedTierTotal') or 0) / 100:.2f} $ — "
                          f"{'archivée' if est.get('isArchived') else 'active'}, expire le {est.get('expiresOn')} — {suivi}")
        parties.append("SOUMISSIONS :\n" + ("\n".join(lignes) or "(aucune)"))
    except Exception as e:
        parties.append(f"SOUMISSIONS : non disponibles ({e})")

    if msgs:
        lignes = [f"[{m['quand_montreal']}] {m['statut_fr']} — {(m.get('shortSummary') or '').strip()}" for m in msgs]
        desab = [m for m in msgs if m.get("status") == "UNSUBSCRIBED"]
        rejet = [m for m in msgs if m.get("status") in ("BOUNCED", "DROPPED", "UNDELIVERED", "FAILED")]
        alerte = ""
        if desab:
            alerte += f"\n⚠️ Le client s'est désabonné d'un courriel Gazelle le {desab[0]['quand_montreal'][:10]}."
        if rejet:
            alerte += f"\n⚠️ Courriel non livré le {rejet[0]['quand_montreal'][:10]} : adresse peut-être invalide."
        parties.append("MESSAGES GAZELLE (courriels/textos envoyés, avec suivi) :\n" + "\n".join(lignes) + alerte)
    return "\n\n".join(parties)[:20000]
