"""Règles apprises par Ivo (« la prochaine fois, fais plutôt ceci »).

Une seule liste, partagée par Ivo dans Front (« @Ivo … ») et par la case de demandes
de l'appli. Seuls Allan, Nicolas et Louise peuvent ajouter ou retirer une règle.
Gardée dans system_settings « ivo_regles_reponse ».
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

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


def peut_modifier(prenom: Optional[str]) -> bool:
    return (prenom or "").strip().lower() in AUTORISES


def ajouter(regle: str, prenom: Optional[str]) -> Dict[str, Any]:
    regle = (regle or "").strip()
    if not regle:
        return {"ok": False, "message": "Règle vide."}
    if not peut_modifier(prenom):
        return {"ok": False, "message": "Seuls Allan, Nicolas et Louise peuvent ajouter une règle à Ivo."}
    regles = lire()
    if any(r["regle"].lower() == regle.lower() for r in regles):
        return {"ok": True, "message": "Cette règle existe déjà."}
    regles.append({"regle": regle, "par": prenom, "le": datetime.now().strftime("%Y-%m-%d")})
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
