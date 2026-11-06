"""Règles apprises par Ivo (« la prochaine fois, fais plutôt ceci »).

Une seule liste, partagée par Ivo dans Front (« @Ivo … ») et par la case de demandes
de l'appli. Seuls Allan, Nicolas et Louise peuvent ajouter ou retirer une règle.
Gardée dans system_settings « ivo_regles_reponse ».
"""
from typing import Any, Dict, List, Optional

from core.timezone_utils import aujourdhui_montreal

CLE = "ivo_regles_reponse"
AUTORISES = {"allan", "nicolas", "louise"}
COURRIELS = {"asutton@piano-tek.com": "Allan", "nlessard@piano-tek.com": "Nicolas", "info@piano-tek.com": "Louise",
             "margotcharignon@gmail.com": "Margot", "jpreny@gmail.com": "JP"}


def _st():
    from core.supabase_storage import SupabaseStorage
    return SupabaseStorage(silent=True)


def lire() -> List[Dict[str, Any]]:
    import json
    try:
        val = _st().get_system_setting(CLE)
        if isinstance(val, str):
            val = json.loads(val)
        sortie = []
        for r in val or []:
            sortie.append(r if isinstance(r, dict) else {"regle": str(r), "par": "?", "le": ""})
        return sortie
    except Exception:
        return []


def texte_pour_ia() -> str:
    regles = lire()
    if not regles:
        return ""
    return ("RÈGLES APPRISES DE L'ÉQUIPE (à suivre ; numérotées pour pouvoir en retirer une) :\n"
            + "\n".join(f"{i}. {r['regle']} (— {r.get('par') or '?'})" for i, r in enumerate(regles, 1)))


# ─── Cahier de connaissances (tâche Front « 📘 Cahier de connaissances d'Ivo », boîte info@) ───
# Ce que l'entreprise sait (tarifs, politiques, équipe, institutions, façons de faire).
# L'équipe le tient à jour dans Front, sans code : un commentaire = une section.
# Seuls les commentaires d'Allan, Nicolas et Louise comptent.
CAHIER_CONVERSATION = "cnv_steodan"
AUTEURS_CAHIER = {"asutton@piano-tek.com", "nlessard@piano-tek.com", "info@piano-tek.com"}
_CAHIER: Dict[str, Any] = {"t": 0.0, "texte": ""}


def cahier_pour_ia() -> str:
    import time
    if _CAHIER["texte"] and time.time() - _CAHIER["t"] < 600:
        return _CAHIER["texte"]
    try:
        from core.front_client import get_front_client
        coms = get_front_client().list_comments(CAHIER_CONVERSATION, limit=100)
        parts = []
        for c in sorted(coms, key=lambda c: c.get("posted_at") or 0):
            auteur = ((c.get("author") or {}).get("email") or "").lower()
            corps = (c.get("body") or "").strip()
            if auteur in AUTEURS_CAHIER and corps and not corps.startswith("🤖"):
                parts.append(corps)
        texte = ("CAHIER DE CONNAISSANCES DE PTM (ce que l'entreprise sait ; fait foi, à appliquer sans qu'on te le redise) :\n"
                 + "\n\n".join(parts))[:30000] if parts else ""
    except Exception:
        return _CAHIER["texte"]  # en cas de panne de Front, on garde la dernière version lue
    _CAHIER.update(t=time.time(), texte=texte)
    return texte


def peut_modifier(prenom: Optional[str]) -> bool:
    return (prenom or "").strip().lower() in AUTORISES


# Outils qui CHANGENT quelque chose (Gazelle, horaire, dossiers). Les autres membres de l'équipe
# (ex. Margot dans Front) peuvent poser des questions à Ivo, mais pas déclencher ces actions.
ACTIONS_RESERVEES = {"creer_client", "bloquer_technicien", "creer_rendez_vous", "create_joint_appointment",
                     "reactivate_estimate", "attach_email_photos_to_piano", "retenir_regle", "oublier_regle",
                     "ajouter_courriel_client", "ajouter_piano"}
MESSAGE_LECTURE_SEULE = ("Cette action est réservée à Allan, Nicolas et Louise : "
                         "je transmets la demande à Louise, qui peut l'autoriser dans ce fil.")
APPROBATRICE = "info@piano-tek.com"  # Louise : c'est elle qui autorise les actions demandées par l'équipe


def peut_agir(prenom: Optional[str]) -> bool:
    return peut_modifier(prenom)


def ajouter(regle: str, prenom: Optional[str]) -> Dict[str, Any]:
    regle = (regle or "").strip()
    if not regle:
        return {"ok": False, "message": "Règle vide."}
    if not peut_modifier(prenom):
        return {"ok": False, "message": "Seuls Allan, Nicolas et Louise peuvent ajouter une règle à Ivo."}
    regles = lire()
    if any(r["regle"].lower() == regle.lower() for r in regles):
        return {"ok": True, "message": "Cette règle existe déjà."}
    regles.append({"regle": regle, "par": prenom, "le": aujourdhui_montreal().isoformat()})
    _st().save_system_setting(CLE, regles)
    return {"ok": True, "message": f"Règle n° {len(regles)} retenue : « {regle} »"}


def retirer(numero: int, prenom: Optional[str]) -> Dict[str, Any]:
    if not peut_modifier(prenom):
        return {"ok": False, "message": "Seuls Allan, Nicolas et Louise peuvent retirer une règle d'Ivo."}
    regles = lire()
    if not 1 <= int(numero) <= len(regles):
        return {"ok": False, "message": f"Pas de règle n° {numero}."}
    r = regles.pop(int(numero) - 1)
    _st().save_system_setting(CLE, regles)
    return {"ok": True, "message": f"Règle retirée : « {r['regle']} »"}


OUTILS = [
    {"name": "retenir_regle",
     "description": ("Retient une règle pour toutes les fois suivantes, quand l'équipe dit « la prochaine fois… », "
                     "« dorénavant… », « à l'avenir… », « toujours… », « ne fais plus… ». Formule-la en une phrase "
                     "claire et générale (cas + quoi faire)."),
     "input_schema": {"type": "object", "required": ["regle"], "properties": {"regle": {"type": "string"}}}},
    {"name": "oublier_regle",
     "description": "Retire une règle apprise, par son numéro (liste des règles apprises).",
     "input_schema": {"type": "object", "required": ["numero"], "properties": {"numero": {"type": "integer"}}}},
]


def executer(nom: str, arg: Dict[str, Any], prenom: Optional[str]) -> Dict[str, Any]:
    if nom == "retenir_regle":
        return ajouter(arg.get("regle") or "", prenom)
    if nom == "oublier_regle":
        return retirer(int(arg.get("numero") or 0), prenom)
    return {"ok": False, "message": "Outil inconnu"}
