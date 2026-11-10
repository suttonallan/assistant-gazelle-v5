"""Ivo apprend de ce que l'équipe change dans ses brouillons avant de les envoyer.

1. Quand Ivo écrit un brouillon dans un fil Front, il garde son texte (system_settings
   « ivo_brouillons_suivis »).
2. Quand un courriel part de ce fil (événement Front « outbound », lu par la surveillance
   d'Ivo), il compare la version envoyée à la sienne.
3. S'il y a un changement de fond (prix, service proposé, offre, politique, fait), il laisse
   UN commentaire : « Vous avez remplacé X par Y. Je retiens : … ? ». Les retouches de style,
   de ponctuation ou de politesse sont ignorées en silence.
4. Si Allan, Nicolas ou Louise répond « @Ivo oui », Ivo retient la règle (outil retenir_regle),
   et le cas devient un cas de test rejoué chaque nuit (system_settings « ivo_cas_appris »).

Ivo ne retient jamais rien sans ce « oui » : une exception propre à un client ne devient pas une règle.
"""
import difflib
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

_log = logging.getLogger(__name__)

CLE_SUIVIS = "ivo_brouillons_suivis"
CLE_CAS = "ivo_cas_appris"
DUREE_S = 21 * 86400          # un brouillon non envoyé après 3 semaines n'est plus suivi
MAX_SUIVIS = 200
MAX_CAS = 60
PREFIXE_LECON = "🤖 Ivo : vous avez modifié mon brouillon avant l'envoi."
_verrou = threading.Lock()   # lectures-écritures de system_settings ci-dessous


def _st():
    from core.supabase_storage import SupabaseStorage
    return SupabaseStorage(silent=True)


def _lire(cle: str, defaut):
    try:
        val = _st().get_system_setting(cle)
        if isinstance(val, str):
            val = json.loads(val)
        return val if isinstance(val, type(defaut)) else defaut
    except Exception:
        return defaut


def _ecrire(cle: str, val) -> None:
    try:
        _st().save_system_setting(cle, val)
    except Exception:
        _log.exception("Ivo apprentissage : écriture impossible (%s)", cle)


def memoriser_brouillon(conversation_id: str, texte: str, auteur_email: str, fil: str) -> None:
    """Appelé chaque fois qu'Ivo écrit ou réécrit un brouillon (le dernier remplace le précédent)."""
    with _verrou:
        _memoriser(conversation_id, texte, auteur_email, fil)


def _memoriser(conversation_id: str, texte: str, auteur_email: str, fil: str) -> None:
    suivis = _lire(CLE_SUIVIS, {})
    maintenant = time.time()
    suivis = {k: v for k, v in suivis.items() if maintenant - (v.get("quand") or 0) < DUREE_S}
    suivis[conversation_id] = {"texte": texte[:8000], "quand": maintenant, "auteur": auteur_email,
                               "fil": (fil or "")[-4000:]}
    if len(suivis) > MAX_SUIVIS:
        for k in sorted(suivis, key=lambda k: suivis[k]["quand"])[:len(suivis) - MAX_SUIVIS]:
            suivis.pop(k)
    _ecrire(CLE_SUIVIS, suivis)


def _normaliser(t: str) -> str:
    import re
    return re.sub(r"\s+", " ", (t or "").lower()).strip()


def _comparer(brouillon: str, envoye: str) -> Optional[Dict[str, Any]]:
    """Demande au modèle les changements de fond et une règle générale possible (ou rien)."""
    from anthropic import Anthropic
    from api.ivo_routes import MODELE
    outil = {"name": "lecon", "description": "Résultat de la comparaison.",
             "input_schema": {"type": "object", "required": ["changements_de_fond"], "properties": {
                 "changements_de_fond": {"type": "array", "items": {"type": "string"},
                                         "description": "Chaque changement de fond, « avant → après », en une ligne."},
                 "regle": {"type": ["string", "null"],
                           "description": "Règle générale à retenir pour les prochains clients, ou null."}}}}
    systeme = (
        "Tu compares le brouillon d'Ivo (assistant de Piano Technique Montréal) et le courriel que l'équipe a "
        "réellement envoyé au client. Ignore : la signature, le texte cité des messages précédents, la ponctuation, "
        "les fautes, les retouches de style ou de politesse, l'ordre des phrases. Ne retiens que les changements de "
        "FOND : prix ou frais, service proposé, offre, politique, délai, information factuelle ajoutée, retirée ou "
        "corrigée. Puis, seulement si le changement révèle une façon de faire valable pour d'autres clients, "
        "formule UNE règle générale en une phrase (le cas + quoi faire). Si le changement est propre à ce client "
        "(sa date, son adresse, une exception), regle = null. Aucun changement de fond : liste vide et regle = null. "
        "Appelle OBLIGATOIREMENT l'outil « lecon », sans autre texte.")
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    for _ in range(2):
        rep = client.messages.create(
            model=MODELE, max_tokens=800, system=systeme, tools=[outil], tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": f"BROUILLON D'IVO :\n{brouillon}\n\nCOURRIEL ENVOYÉ :\n{envoye}"}])
        bloc = next((b for b in rep.content if getattr(b, "type", "") == "tool_use"), None)
        if bloc:
            return dict(bloc.input)
    return None


def traiter_envoi(conversation_id: str, texte_envoye: str) -> Dict[str, Any]:
    """Un courriel vient de partir de ce fil : comparer avec le dernier brouillon d'Ivo."""
    with _verrou:
        suivis = _lire(CLE_SUIVIS, {})
        suivi = suivis.get(conversation_id)
        if not suivi:
            return {"statut": "ignoré", "raison": "pas de brouillon d'Ivo suivi"}
        suivis.pop(conversation_id, None)
        _ecrire(CLE_SUIVIS, suivis)
    brouillon = suivi.get("texte") or ""
    if difflib.SequenceMatcher(None, _normaliser(brouillon), _normaliser(texte_envoye)).ratio() > 0.985:
        return {"statut": "ok", "raison": "envoyé presque tel quel"}
    res = _comparer(brouillon, texte_envoye)
    if not res or not res.get("changements_de_fond"):
        return {"statut": "ok", "raison": "aucun changement de fond"}
    lignes = "\n".join(f"- {c}" for c in res["changements_de_fond"][:5])
    regle = (res.get("regle") or "").strip()
    if regle:
        corps = (f"{PREFIXE_LECON} Je retiens pour les prochains clients : « {regle[:300]} » ?\n"
                 "Répondez « @Ivo oui » pour que je la retienne (vous pouvez la corriger dans votre réponse). "
                 f"Sinon, ignorez ce message : je ne retiens rien.\n\nCe que vous avez changé :\n{lignes}")
    else:
        corps = (f"{PREFIXE_LECON}\n{lignes}\n\nÇa me semble propre à ce client, donc je ne retiens rien. "
                 "Si c'est une règle pour les prochaines fois, répondez « @Ivo retiens : … ».")
    from core.front_client import get_front_client
    get_front_client().add_comment(conversation_id, corps, suivi.get("auteur") or "info@piano-tek.com")
    if regle:
        with _verrou:
            suivis = _lire(CLE_SUIVIS, {})
            suivis["lecon:" + conversation_id] = {"quand": time.time(), "fil": suivi.get("fil") or "",
                                                  "regle": regle, "texte": "", "auteur": suivi.get("auteur")}
            _ecrire(CLE_SUIVIS, suivis)
    return {"statut": "ok", "raison": "leçon proposée", "regle": regle or None}


def regle_retenue(conversation_id: Optional[str], regle: str) -> None:
    """Après retenir_regle dans un fil où Ivo avait proposé une leçon : le cas devient un cas de test."""
    if not conversation_id:
        return
    with _verrou:
        suivis = _lire(CLE_SUIVIS, {})
        lecon = suivis.pop("lecon:" + conversation_id, None)
        if not lecon or not lecon.get("fil"):
            return
        _ecrire(CLE_SUIVIS, suivis)
        cas = _lire(CLE_CAS, [])
        cas.append({"nom": f"Appris le {time.strftime('%Y-%m-%d')} : {regle[:70]}", "fil": lecon["fil"],
                    "consigne": "Rédige une réponse au client.", "regle": regle,
                    "criteres": f"Le brouillon respecte cette règle : {regle}", "conversation": conversation_id})
        _ecrire(CLE_CAS, cas[-MAX_CAS:])


def retirer_cas(regle: str) -> None:
    """Une règle oubliée ne doit plus faire échouer son cas de test chaque nuit."""
    with _verrou:
        cas = _lire(CLE_CAS, [])
        reste = [c for c in cas if (c.get("regle") or "").strip().lower() != (regle or "").strip().lower()]
        if len(reste) != len(cas):
            _ecrire(CLE_CAS, reste)


def cas_appris() -> List[Dict[str, Any]]:
    return _lire(CLE_CAS, [])
