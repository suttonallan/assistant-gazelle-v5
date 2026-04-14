"""Assistant conversationnel v0 — point d'entrée minimal pour les actions
demandées en langage naturel par Allan ou Louise dans la boîte client.

Pour l'instant, supporte UNE seule action : créer un RV conjoint
(accompagnateur) à partir d'un RV existant.

Architecture :
- POST /assistant/joint-appointment {message, current_user_first_name?}
- Claude Haiku parse la requête via tool use et extrait les paramètres
- Le backend résout les techniciens, trouve le RV source dans Gazelle live
- Crée le clone type PERSONAL (le client ne reçoit pas de 2e notif)
- Annote l'event original (titre + notes) avec le nom de l'accompagnateur
- Retourne success + IDs des deux events

Référence :
- Skill gazelle workflow clone_appointment_joint
- Mémoire feedback project_rv_conjoint_personal_type, project_rv_conjoint_title_safe
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/assistant", tags=["assistant"])


# ─────────────────────────────────────────────────────────────────────
# RESOLVED USER IDS — récupérés via introspection allUsers le 2026-04-12
# ─────────────────────────────────────────────────────────────────────

KNOWN_TECHS = {
    # Aliases en minuscules → user_id Gazelle
    "allan": "usr_ofYggsCDt2JAVeNP",
    "allan sutton": "usr_ofYggsCDt2JAVeNP",
    "nicolas": "usr_HcCiFk7o0vZ9xAI0",
    "nicolas lessard": "usr_HcCiFk7o0vZ9xAI0",
    "nic": "usr_HcCiFk7o0vZ9xAI0",
    "jp": "usr_ReUSmIJmBF86ilY1",
    "j-p": "usr_ReUSmIJmBF86ilY1",
    "jean-philippe": "usr_ReUSmIJmBF86ilY1",
    "jean philippe": "usr_ReUSmIJmBF86ilY1",
    "jean-philippe reny": "usr_ReUSmIJmBF86ilY1",
    "margot": "usr_bbt59aCUqUaDWA8n",
    "margot charignon": "usr_bbt59aCUqUaDWA8n",
}

TECH_DISPLAY_NAMES = {
    "usr_ofYggsCDt2JAVeNP": "Allan Sutton",
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas Lessard",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe Reny",
    "usr_bbt59aCUqUaDWA8n": "Margot Charignon",
}

TECH_FIRST_NAMES = {
    "usr_ofYggsCDt2JAVeNP": "Allan",
    "usr_HcCiFk7o0vZ9xAI0": "Nicolas",
    "usr_ReUSmIJmBF86ilY1": "Jean-Philippe",
    "usr_bbt59aCUqUaDWA8n": "Margot",
}


def resolve_tech(name: str) -> Optional[str]:
    """Résout un nom/prénom/alias en user_id Gazelle. None si inconnu."""
    if not name:
        return None
    return KNOWN_TECHS.get(name.strip().lower())


# ─────────────────────────────────────────────────────────────────────
# RESOLUTION DES DATES RELATIVES
# ─────────────────────────────────────────────────────────────────────

WEEKDAYS_FR = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
    "vendredi": 4, "samedi": 5, "dimanche": 6,
}


def resolve_relative_date(date_str: str) -> Optional[str]:
    """Résout 'demain', 'aujourd'hui', 'lundi', '2026-04-15' en YYYY-MM-DD.

    Retourne None si non parseable.
    """
    if not date_str:
        return None
    s = date_str.strip().lower()
    today = date.today()

    if s in ("aujourd'hui", "aujourd hui", "ajd", "today"):
        return today.isoformat()
    if s in ("demain", "tomorrow"):
        return (today + timedelta(days=1)).isoformat()
    if s in ("hier", "yesterday"):
        return (today - timedelta(days=1)).isoformat()
    if s in ("apres-demain", "après-demain", "après demain"):
        return (today + timedelta(days=2)).isoformat()

    # Format ISO direct
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # Jour de la semaine → prochain
    for fr, wd in WEEKDAYS_FR.items():
        if fr in s:
            days_ahead = (wd - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # "lundi" dit un lundi → on prend le suivant
            return (today + timedelta(days=days_ahead)).isoformat()

    return None


# ─────────────────────────────────────────────────────────────────────
# CLAUDE TOOL USE — DÉFINITION DE L'OUTIL
# ─────────────────────────────────────────────────────────────────────

JOINT_APPOINTMENT_TOOL = {
    "name": "create_joint_appointment",
    "description": (
        "Crée un rendez-vous conjoint en clonant un RV existant pour un "
        "technicien accompagnateur. Le clone est de type PERSONAL pour que "
        "le client ne reçoive pas de notification dupliquée. Utilise cet "
        "outil quand l'utilisateur demande d'ajouter quelqu'un comme "
        "accompagnateur, partenaire, apprenti ou observateur sur un RV."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "source_tech_first_name": {
                "type": "string",
                "description": (
                    "Prénom du technicien principal qui a déjà le RV. "
                    "Valeurs acceptées : Allan, Nicolas, JP, Jean-Philippe, Margot. "
                    "Si non précisé explicitement, utiliser le prénom de l'utilisateur "
                    "courant fourni dans le contexte."
                ),
            },
            "source_date": {
                "type": "string",
                "description": (
                    "Date du RV. Accepte 'aujourd'hui', 'demain', 'lundi', "
                    "'mardi', etc., ou format YYYY-MM-DD."
                ),
            },
            "source_time_hint": {
                "type": "string",
                "description": (
                    "Heure approximative si mentionnée (ex: '14h', '9h30', 'matin'). "
                    "Optionnel — utile seulement si le tech a plusieurs RV ce jour."
                ),
            },
            "client_name_hint": {
                "type": "string",
                "description": (
                    "Nom du client si mentionné (ex: 'Tremblay'). "
                    "Optionnel — utile pour désambiguïser."
                ),
            },
            "companion_first_name": {
                "type": "string",
                "description": (
                    "Prénom du technicien accompagnateur à ajouter au RV. "
                    "Valeurs : Allan, Nicolas, JP, Jean-Philippe, Margot."
                ),
            },
        },
        "required": ["source_tech_first_name", "source_date", "companion_first_name"],
    },
}


# ─────────────────────────────────────────────────────────────────────
# HANDLER DU TOOL — exécute la création du RV conjoint dans Gazelle
# ─────────────────────────────────────────────────────────────────────


def execute_joint_appointment(
    source_tech_first_name: str,
    source_date: str,
    companion_first_name: str,
    source_time_hint: Optional[str] = None,
    client_name_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Exécute le workflow joint RV. Retourne un dict avec success + détails."""
    from core.gazelle_api_client import GazelleAPIClient

    source_tech_id = resolve_tech(source_tech_first_name)
    companion_tech_id = resolve_tech(companion_first_name)
    if not source_tech_id:
        return {
            "success": False,
            "error": f"Technicien principal inconnu : '{source_tech_first_name}'. Connus : Allan, Nicolas, JP, Margot.",
        }
    if not companion_tech_id:
        return {
            "success": False,
            "error": f"Accompagnateur inconnu : '{companion_first_name}'. Connus : Allan, Nicolas, JP, Margot.",
        }
    if source_tech_id == companion_tech_id:
        return {
            "success": False,
            "error": f"Le technicien principal et l'accompagnateur sont la même personne ({TECH_DISPLAY_NAMES[source_tech_id]}).",
        }

    iso_date = resolve_relative_date(source_date)
    if not iso_date:
        return {
            "success": False,
            "error": f"Date non interprétable : '{source_date}'. Utilise 'aujourd'hui', 'demain', un jour de semaine, ou YYYY-MM-DD.",
        }

    gz = GazelleAPIClient()

    # Récupérer tous les events de la journée pour le tech principal
    fetch_query = """
    query($filters: PrivateAllEventsFilter) {
        allEventsBatched(first: 50, filters: $filters) {
            nodes {
                id title start duration type status notes
                user { id firstName lastName }
                client { id defaultContact { firstName lastName } }
                allEventPianos(first: 5) { nodes { piano { id make model } } }
            }
        }
    }
    """
    fetch_result = gz._execute_query(
        fetch_query,
        {"filters": {
            "startOn": iso_date,
            "endOn": iso_date,
            "type": ["APPOINTMENT"],
        }},
    )
    nodes = fetch_result.get("data", {}).get("allEventsBatched", {}).get("nodes", []) or []

    # Filtrer sur le tech principal
    candidates = [n for n in nodes if (n.get("user") or {}).get("id") == source_tech_id]

    if not candidates:
        return {
            "success": False,
            "error": f"Aucun RV trouvé pour {TECH_DISPLAY_NAMES[source_tech_id]} le {iso_date}.",
        }

    # Désambiguïser via les hints
    def matches_time(node, hint):
        if not hint:
            return True
        # Extraire l'heure "14h", "9h30", "9:30"
        m = re.search(r"(\d{1,2})\s*[h:]\s*(\d{0,2})", hint.lower())
        if not m:
            # "matin" / "après-midi" / "soir"
            start_str = node.get("start", "")
            try:
                hour = datetime.fromisoformat(start_str.replace("Z", "+00:00")).astimezone().hour
            except Exception:
                return True
            h_lower = hint.lower()
            if "matin" in h_lower:
                return hour < 12
            if "après-midi" in h_lower or "apres-midi" in h_lower or "pm" in h_lower:
                return 12 <= hour < 18
            if "soir" in h_lower:
                return hour >= 17
            return True
        target_h = int(m.group(1))
        target_m = int(m.group(2)) if m.group(2) else 0
        try:
            dt = datetime.fromisoformat(node.get("start", "").replace("Z", "+00:00"))
            # Convertir UTC en heure de Montréal (approx -4h en avril, EDT)
            local_h = (dt.hour - 4) % 24
            local_m = dt.minute
        except Exception:
            return True
        # Tolérance ±1h
        node_minutes = local_h * 60 + local_m
        target_minutes = target_h * 60 + target_m
        return abs(node_minutes - target_minutes) <= 60

    def matches_client(node, hint):
        if not hint:
            return True
        contact = (node.get("client") or {}).get("defaultContact") or {}
        full_name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".lower()
        return hint.strip().lower() in full_name

    filtered = [
        c for c in candidates
        if matches_time(c, source_time_hint) and matches_client(c, client_name_hint)
    ]

    if not filtered:
        # Aucun match avec les hints — retourner les candidats bruts pour clarification
        return {
            "success": False,
            "error": (
                f"Aucun RV ne correspond exactement aux critères. "
                f"{TECH_DISPLAY_NAMES[source_tech_id]} a {len(candidates)} RV le {iso_date}. "
                f"Précise l'heure ou le nom du client."
            ),
            "candidates": [
                {
                    "id": c["id"],
                    "start": c.get("start", ""),
                    "client": (
                        ((c.get("client") or {}).get("defaultContact") or {}).get("firstName", "")
                        + " "
                        + ((c.get("client") or {}).get("defaultContact") or {}).get("lastName", "")
                    ).strip(),
                    "title": c.get("title", ""),
                }
                for c in candidates
            ],
        }

    if len(filtered) > 1:
        return {
            "success": False,
            "error": (
                f"{len(filtered)} RV correspondent. Précise davantage l'heure ou le client."
            ),
            "candidates": [
                {
                    "id": c["id"],
                    "start": c.get("start", ""),
                    "client": (
                        ((c.get("client") or {}).get("defaultContact") or {}).get("firstName", "")
                        + " "
                        + ((c.get("client") or {}).get("defaultContact") or {}).get("lastName", "")
                    ).strip(),
                    "title": c.get("title", ""),
                }
                for c in filtered
            ],
        }

    source = filtered[0]
    source_id = source["id"]
    source_title = source.get("title") or ""
    source_notes = source.get("notes") or ""
    contact = (source.get("client") or {}).get("defaultContact") or {}
    client_name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip() or "(client inconnu)"
    pianos = (source.get("allEventPianos", {}) or {}).get("nodes", []) or []
    piano_str = ", ".join(
        f"{p['piano']['make']} {p['piano']['model']}" for p in pianos if p.get("piano")
    ) or "—"

    companion_first = TECH_FIRST_NAMES[companion_tech_id]
    companion_full = TECH_DISPLAY_NAMES[companion_tech_id]
    source_full = TECH_DISPLAY_NAMES[source_tech_id]

    # 1. Créer le clone type PERSONAL
    clone_input = {
        "title": f"[Accompagnement] {source_title}",
        "start": source["start"],
        "duration": source.get("duration") or 60,
        "type": "PERSONAL",
        "userId": companion_tech_id,
        "notes": (
            f"Accompagnement de {source_full} chez {client_name}.\n"
            f"Piano : {piano_str}\n"
            f"Event principal : {source_id}"
        ),
    }

    create_mutation = """
    mutation CreateEvent($input: PrivateEventInput!) {
        createEvent(input: $input) {
            event { id title start type }
            mutationErrors { fieldName messages }
        }
    }
    """
    create_result = gz._execute_query(create_mutation, {"input": clone_input})
    create_payload = create_result.get("data", {}).get("createEvent") or {}
    errs = create_payload.get("mutationErrors") or []
    if errs:
        return {
            "success": False,
            "error": f"Échec création clone : {errs}",
        }
    clone_event = create_payload.get("event") or {}
    clone_id = clone_event.get("id")

    # 2. Annoter l'event original (titre + notes)
    new_title = f"{source_title} + {companion_first}"
    new_notes = (
        (source_notes + ("\n\n" if source_notes else ""))
        + f"Accompagné par {companion_full} (event clone : {clone_id})"
    )

    update_mutation = """
    mutation UpdateEvent($id: String!, $input: PrivateEventInput!) {
        updateEvent(id: $id, input: $input) {
            event { id title }
            mutationErrors { fieldName messages }
        }
    }
    """
    update_result = gz._execute_query(
        update_mutation,
        {"id": source_id, "input": {"title": new_title, "notes": new_notes}},
    )
    update_payload = update_result.get("data", {}).get("updateEvent") or {}
    update_errs = update_payload.get("mutationErrors") or []
    annotation_warning = None
    if update_errs:
        annotation_warning = f"Clone créé mais annotation de l'original a échoué : {update_errs}"

    return {
        "success": True,
        "source_event_id": source_id,
        "source_event_new_title": new_title if not update_errs else source_title,
        "clone_event_id": clone_id,
        "client_name": client_name,
        "source_tech": source_full,
        "companion_tech": companion_full,
        "date": iso_date,
        "annotation_warning": annotation_warning,
    }


# ─────────────────────────────────────────────────────────────────────
# ENDPOINT PUBLIC
# ─────────────────────────────────────────────────────────────────────


class AssistantRequest(BaseModel):
    message: str
    current_user_first_name: Optional[str] = None  # pour résoudre "mon RV de demain"


@router.post("/joint-appointment", response_model=Dict[str, Any])
async def joint_appointment(req: AssistantRequest):
    """Parse une demande en langage naturel et exécute le workflow RV conjoint.

    Exemples de requêtes acceptées :
    - "fais un RV conjoint avec Margot pour le RV de Nicolas demain à 14h"
    - "ajoute JP au RV de Tremblay demain matin"
    - "duplique mon RV de 10h pour Margot" (avec current_user_first_name=Allan)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurée")

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    today_iso = date.today().isoformat()
    user_context = ""
    if req.current_user_first_name:
        user_context = (
            f"\n\nL'utilisateur courant qui pose la question est {req.current_user_first_name}. "
            f"Si la requête contient 'mon RV', 'mon rendez-vous', utilise {req.current_user_first_name} "
            f"comme source_tech_first_name par défaut."
        )

    system_prompt = (
        f"Tu es l'assistant Gazelle de Piano Tek Musique. Aujourd'hui c'est {today_iso}. "
        "Ton rôle est de parser une demande en langage naturel et d'extraire les "
        "paramètres pour l'outil create_joint_appointment.\n\n"
        "Techniciens connus : Allan, Nicolas, JP (Jean-Philippe), Margot.\n\n"
        "Si la demande n'est PAS une demande de RV conjoint (par exemple, c'est juste "
        "un nom de client), ne pas appeler l'outil et répondre 'Cette demande ne semble "
        "pas être une demande de RV conjoint.'"
        + user_context
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=[JOINT_APPOINTMENT_TOOL],
            system=system_prompt,
            messages=[{"role": "user", "content": req.message}],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur Claude API : {exc}")

    # Chercher un tool_use dans la réponse
    tool_call = None
    text_response = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "create_joint_appointment":
            tool_call = block.input
        elif block.type == "text":
            text_response.append(block.text)

    if not tool_call:
        return {
            "success": False,
            "intent_recognized": False,
            "message": " ".join(text_response) or "Je n'ai pas compris la demande comme un RV conjoint.",
        }

    # Exécuter le tool
    try:
        result = execute_joint_appointment(**tool_call)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "intent_recognized": True,
            "tool_input": tool_call,
            "error": f"Erreur d'exécution : {exc}",
        }

    result["intent_recognized"] = True
    result["tool_input"] = tool_call
    return result
