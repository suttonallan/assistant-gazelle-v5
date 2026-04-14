"""Assistant conversationnel v0 — endpoints pour les actions demandées
en langage naturel par Allan ou Louise dans la boîte client.

Actions supportées :
1. RV conjoint (accompagnateur) — POST /assistant/joint-appointment
2. Révision/amélioration de soumission — POST /assistant/review-estimate
3. Recherche par mot-clé dans events/notes — POST /assistant/search-keyword

Architecture :
- Claude Haiku parse la requête via tool use et extrait les paramètres
- Le backend interroge Gazelle live (pas la cache Supabase) pour les
  données fraîches
- Pour les actions destructrices, utilise les patterns de garde du skill
  gazelle (PERSONAL pour les clones d'event, etc.)

Référence :
- Skill gazelle (.claude/skills/gazelle/workflows/)
- Mémoire feedback project_rv_conjoint_personal_type, project_rv_conjoint_title_safe,
  feedback_update_estimate_safe_required, feedback_soumissions_pas_signature
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


# ═════════════════════════════════════════════════════════════════════
# WORKFLOW 2 — Révision / amélioration d'une soumission
# ═════════════════════════════════════════════════════════════════════

REVIEW_ESTIMATE_TOOL = {
    "name": "review_estimate",
    "description": (
        "Analyse une soumission Gazelle existante et retourne des suggestions "
        "d'amélioration. Utilise cet outil quand l'utilisateur demande de "
        "réviser, analyser, améliorer, ou corriger une soumission. Identifie "
        "la soumission soit par son numéro (ex: '11919') soit par le nom du "
        "client (ex: 'Giroux', 'Mme Tremblay'). Cet outil est en mode dry-run "
        "— il PROPOSE des corrections mais ne les applique pas."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "estimate_number": {
                "type": "integer",
                "description": (
                    "Numéro public de la soumission (ex: 11919). À fournir "
                    "si l'utilisateur le mentionne explicitement avec un # ou "
                    "comme nombre."
                ),
            },
            "client_name_hint": {
                "type": "string",
                "description": (
                    "Nom (ou partie de nom) du client si la soumission est "
                    "identifiée par client plutôt que par numéro (ex: 'Giroux')."
                ),
            },
        },
    },
}


def _format_currency(cents: int) -> str:
    return f"{cents/100:.2f} $"


def execute_review_estimate(
    estimate_number: Optional[int] = None,
    client_name_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Lit une soumission Gazelle et retourne une analyse + suggestions.

    Mode lecture seule (dry-run). Retourne une liste d'issues avec leur
    sévérité et la correction proposée. L'utilisateur applique manuellement.
    """
    from core.gazelle_api_client import GazelleAPIClient

    if not estimate_number and not client_name_hint:
        return {
            "success": False,
            "error": "Précise soit un numéro de soumission, soit un nom de client.",
        }

    gz = GazelleAPIClient()

    # Query de base réutilisée
    fetch_query = """
    query($search: String!) {
        allEstimates(first: 10, filters: {search: $search}) {
            nodes {
                id number notes estimatedOn expiresOn locale
                isArchived
                recommendedTierTotal
                client { id defaultContact { firstName lastName } }
                piano { id make model year }
                allEstimateTiers {
                    id sequenceNumber isPrimary notes
                    subtotal taxTotal total
                    allEstimateTierGroups {
                        id name sequenceNumber
                        allEstimateTierItems {
                            id name sequenceNumber amount quantity
                            description isTaxable
                            masterServiceItem { id }
                        }
                    }
                    allUngroupedEstimateTierItems {
                        id name amount quantity description isTaxable
                        masterServiceItem { id }
                    }
                }
            }
        }
    }
    """

    # Résolution de l'estimate
    estimate = None
    if estimate_number:
        result = gz._execute_query(fetch_query, {"search": str(estimate_number)})
        nodes = result.get("data", {}).get("allEstimates", {}).get("nodes", []) or []
        for n in nodes:
            if n.get("number") == int(estimate_number):
                estimate = n
                break
        if not estimate:
            return {
                "success": False,
                "error": f"Soumission #{estimate_number} introuvable dans Gazelle.",
            }
    else:
        # Recherche par nom de client — on prend la PLUS RÉCENTE non archivée
        result = gz._execute_query(fetch_query, {"search": client_name_hint})
        nodes = result.get("data", {}).get("allEstimates", {}).get("nodes", []) or []
        # Filtrer sur le nom client + non archivé, trier par estimatedOn desc
        matching = []
        hint_lower = client_name_hint.strip().lower()
        for n in nodes:
            if n.get("isArchived"):
                continue
            contact = (n.get("client") or {}).get("defaultContact") or {}
            full = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".lower()
            if hint_lower in full:
                matching.append(n)
        if not matching:
            return {
                "success": False,
                "error": f"Aucune soumission active trouvée pour '{client_name_hint}'.",
            }
        if len(matching) > 1:
            # Plusieurs candidates — retourner pour clarification
            return {
                "success": False,
                "error": f"{len(matching)} soumissions actives pour '{client_name_hint}'. Précise le numéro.",
                "candidates": [
                    {
                        "number": m.get("number"),
                        "estimated_on": m.get("estimatedOn"),
                        "total": m.get("recommendedTierTotal"),
                        "client": (
                            ((m.get("client") or {}).get("defaultContact") or {}).get("firstName", "")
                            + " "
                            + ((m.get("client") or {}).get("defaultContact") or {}).get("lastName", "")
                        ).strip(),
                    }
                    for m in matching
                ],
            }
        estimate = matching[0]

    # ─── Analyse heuristique des frictions ───
    issues = []
    contact = (estimate.get("client") or {}).get("defaultContact") or {}
    client_full = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
    piano = estimate.get("piano") or {}
    piano_str = f"{piano.get('make', '')} {piano.get('model', '') or ''}".strip()

    notes = estimate.get("notes") or ""
    tiers = estimate.get("allEstimateTiers") or []

    # Issue 1 : Items à 0 $ (friction #2)
    zero_items = []
    for tier in tiers:
        for group in tier.get("allEstimateTierGroups") or []:
            for item in group.get("allEstimateTierItems") or []:
                if (item.get("amount") or 0) == 0:
                    zero_items.append({
                        "name": item.get("name", ""),
                        "tier": tier.get("sequenceNumber", "?"),
                        "group": group.get("name", ""),
                        "description_excerpt": (item.get("description") or "")[:100],
                    })
        for item in tier.get("allUngroupedEstimateTierItems") or []:
            if (item.get("amount") or 0) == 0:
                zero_items.append({
                    "name": item.get("name", ""),
                    "tier": tier.get("sequenceNumber", "?"),
                    "group": "(non-groupé)",
                    "description_excerpt": (item.get("description") or "")[:100],
                })
    if zero_items:
        issues.append({
            "type": "items_zero_dollar",
            "severity": "high",
            "title": f"{len(zero_items)} item(s) à 0 $ détecté(s)",
            "description": (
                "Les items à 0 $ sont visuellement dissonants pour le client. "
                "Soit (a) supprime-les et déplace leur contenu dans la description "
                "d'un item facturé existant, soit (b) déplace-les dans les notes "
                "de la soumission s'il s'agit d'avertissements."
            ),
            "items": zero_items,
        })

    # Issue 2 : Tier 2 ne ⊇ Tier 1 (friction #1)
    if len(tiers) >= 2:
        # Construire les sets d'items par (msl_id, name)
        def collect_keys(tier):
            keys = set()
            for g in tier.get("allEstimateTierGroups") or []:
                for it in g.get("allEstimateTierItems") or []:
                    msl = (it.get("masterServiceItem") or {}).get("id")
                    keys.add((msl, it.get("name")))
            for it in tier.get("allUngroupedEstimateTierItems") or []:
                msl = (it.get("masterServiceItem") or {}).get("id")
                keys.add((msl, it.get("name")))
            return keys
        # Trier par sequenceNumber
        sorted_tiers = sorted(tiers, key=lambda t: t.get("sequenceNumber", 0))
        t1_keys = collect_keys(sorted_tiers[0])
        t2_keys = collect_keys(sorted_tiers[1])
        missing_in_t2 = t1_keys - t2_keys
        if missing_in_t2:
            missing_names = [name for (_, name) in missing_in_t2]
            issues.append({
                "type": "tier_inclusion_violation",
                "severity": "critical",
                "title": "Tier 2 ne contient pas tout Tier 1",
                "description": (
                    "Règle UX PTM : l'option recommandée doit toujours INCLURE "
                    "tout le contenu de l'option de base + des extras, sans rien "
                    "retirer. Sinon le client ne comprend pas la différence."
                ),
                "missing_items": missing_names,
            })

    # Issue 3 : Avertissements absents des notes
    has_warning_section = bool(re.search(r"avertissement|warning", notes, re.IGNORECASE))
    has_extension_work = False
    extension_keywords = ["cordes", "marteaux", "sommier", "manches"]
    for tier in tiers:
        for g in tier.get("allEstimateTierGroups") or []:
            for it in g.get("allEstimateTierItems") or []:
                name_lower = (it.get("name") or "").lower()
                if any(kw in name_lower for kw in extension_keywords):
                    has_extension_work = True
                    break
    if has_extension_work and not has_warning_section:
        issues.append({
            "type": "missing_warnings",
            "severity": "medium",
            "title": "Travaux importants sans section avertissement",
            "description": (
                "Cette soumission contient des travaux de cordes/marteaux/sommier "
                "qui nécessitent généralement une section AVERTISSEMENTS dans les "
                "notes (étirement des cordes neuves, accords de stabilisation non "
                "inclus, fragilité, etc.)."
            ),
        })

    # Issue 4 : Signature résiduelle "Piano Tek Musique" (règle Allan)
    if "Piano Tek Musique" in notes or "— Nicolas Lessard" in notes:
        issues.append({
            "type": "residual_signature",
            "severity": "low",
            "title": "Signature dans les notes",
            "description": (
                "Allan a demandé de ne plus inclure de ligne signature type "
                "« — Piano Tek Musique » dans les notes. Gazelle identifie déjà "
                "l'entreprise dans le header de la soumission."
            ),
        })

    # Issue 5 : Cordes basses séparées (matériel + install non fusionnés)
    # On vérifie qu'on a 2 ITEMS DISTINCTS : un avec le MSL matériel, un avec le
    # MSL install. Si un seul item porte les deux concepts (comme le bundle PTM
    # cordes_basses_complet « Cordes des basses — fourniture et installation »),
    # il ne faut PAS flagger.
    cordes_material_item_id = None
    cordes_install_item_id = None
    for tier in tiers:
        for g in tier.get("allEstimateTierGroups") or []:
            for it in g.get("allEstimateTierItems") or []:
                msl = (it.get("masterServiceItem") or {}).get("id")
                if msl == "mit_2HBYLndAxf1C993j":
                    cordes_material_item_id = it.get("id")
                if msl == "mit_uiSzTQHCmcYYte4n":
                    cordes_install_item_id = it.get("id")
    if (
        cordes_material_item_id
        and cordes_install_item_id
        and cordes_material_item_id != cordes_install_item_id
    ):
        issues.append({
            "type": "cordes_basses_split",
            "severity": "medium",
            "title": "Cordes des basses en 2 lignes au lieu d'un bundle",
            "description": (
                "Les MSL « Cordes des basses » et « Installer les cordes des basses » "
                "sont 2 items distincts. Le bundle PTM `cordes_basses_complet` les "
                "fusionne en une seule ligne « Cordes des basses — fourniture et "
                "installation » à 2 000 $ pour une lisibilité client."
            ),
        })

    # Issue 6 : Description héritée du MSL (générique, non personnalisée)
    generic_desc_count = 0
    for tier in tiers:
        for g in tier.get("allEstimateTierGroups") or []:
            for it in g.get("allEstimateTierItems") or []:
                desc = (it.get("description") or "").strip()
                # Si la description ne contient pas de puces (•) et fait < 200 chars,
                # c'est probablement la description générique du MSL
                if desc and "•" not in desc and len(desc) < 200:
                    generic_desc_count += 1
    if generic_desc_count >= 3:
        issues.append({
            "type": "generic_descriptions",
            "severity": "low",
            "title": f"{generic_desc_count} item(s) avec description générique du MSL",
            "description": (
                "Plusieurs items utilisent la description par défaut du MasterServiceItem "
                "Gazelle au lieu d'une liste d'actions personnalisées. La pratique PTM "
                "v6 est de surcharger la description avec des puces décrivant les actions "
                "concrètes effectuées sur CE piano."
            ),
        })

    # ─── Résumé global ───
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    issues.sort(key=lambda i: severity_order.get(i["severity"], 9))

    summary_parts = [
        f"Soumission #{estimate.get('number')} — {client_full or '?'}",
        f"Piano : {piano_str or '?'}",
        f"Tiers : {len(tiers)}",
    ]
    total = estimate.get("recommendedTierTotal")
    if total:
        summary_parts.append(f"Total recommandé : {_format_currency(total)}")

    return {
        "success": True,
        "estimate_number": estimate.get("number"),
        "estimate_id": estimate.get("id"),
        "client_name": client_full,
        "piano": piano_str,
        "summary": " · ".join(summary_parts),
        "issues_count": len(issues),
        "issues": issues,
    }


@router.post("/review-estimate", response_model=Dict[str, Any])
async def review_estimate(req: AssistantRequest):
    """Parse une demande de révision de soumission et retourne les suggestions.

    Exemples :
    - "améliore la soumission #11919"
    - "révise la soumission de M Giroux"
    - "analyse #11920"
    - "qu'est-ce qui cloche dans la soumission de Tremblay ?"
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurée")

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    system_prompt = (
        "Tu es l'assistant Gazelle de Piano Tek Musique. Ton rôle est de "
        "parser une demande de révision de soumission et d'extraire les "
        "paramètres pour l'outil review_estimate.\n\n"
        "Si l'utilisateur mentionne un numéro (ex: '#11919', '11919', "
        "'la soumission 11919'), utilise estimate_number.\n"
        "Si l'utilisateur mentionne un nom de client (ex: 'M Giroux', "
        "'Mme Tremblay', 'soumission de Dupont'), utilise client_name_hint.\n"
        "Si la demande n'est PAS une demande de révision de soumission, "
        "ne pas appeler l'outil et répondre 'Cette demande ne semble pas "
        "être une demande de révision de soumission.'"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            tools=[REVIEW_ESTIMATE_TOOL],
            system=system_prompt,
            messages=[{"role": "user", "content": req.message}],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur Claude API : {exc}")

    tool_call = None
    text_response = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "review_estimate":
            tool_call = block.input
        elif block.type == "text":
            text_response.append(block.text)

    if not tool_call:
        return {
            "success": False,
            "intent_recognized": False,
            "message": " ".join(text_response) or "Je n'ai pas compris la demande comme une révision de soumission.",
        }

    try:
        result = execute_review_estimate(
            estimate_number=tool_call.get("estimate_number"),
            client_name_hint=tool_call.get("client_name_hint"),
        )
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


# ═════════════════════════════════════════════════════════════════════
# WORKFLOW 3 — Recherche libre par mot-clé dans les events/notes
# ═════════════════════════════════════════════════════════════════════

SEARCH_KEYWORD_TOOL = {
    "name": "search_events_by_keyword",
    "description": (
        "Cherche dans les notes et titres des rendez-vous Gazelle (events) "
        "tous ceux qui mentionnent un mot-clé. Utilise cet outil quand "
        "l'utilisateur demande de retrouver une visite, un service, un "
        "problème ou un contexte précis dont il se souvient vaguement. "
        "Exemples : 'chez quel client JP a réparé du polyester récemment', "
        "'qui a un PLS qui fuit', 'retrouve la note où Nicolas mentionne "
        "Steinway K-52', 'quels pianos ont des chevilles fatiguées'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": (
                    "Le mot-clé ou expression courte à chercher dans les notes "
                    "et titres des events. Doit être spécifique (ex: 'polyester', "
                    "'chevilles fatiguées', 'fuite humidistat'). Évite les mots "
                    "trop génériques comme 'piano' ou 'accord'."
                ),
            },
            "tech_filter_first_name": {
                "type": "string",
                "description": (
                    "Optionnel — restreint la recherche aux events d'un "
                    "technicien spécifique. Valeurs : Allan, Nicolas, JP, "
                    "Jean-Philippe, Margot. Si l'utilisateur dit 'JP et Allan', "
                    "laisse vide et le backend retournera tous les techs."
                ),
            },
            "months_back": {
                "type": "integer",
                "description": (
                    "Optionnel — nombre de mois en arrière à scanner. "
                    "Défaut 24. Maximum 60."
                ),
            },
        },
        "required": ["keyword"],
    },
}


def execute_search_keyword(
    keyword: str,
    tech_filter_first_name: Optional[str] = None,
    months_back: Optional[int] = None,
) -> Dict[str, Any]:
    """Sweep Gazelle events pour trouver les mentions du mot-clé.

    Retourne jusqu'à 25 résultats les plus récents, triés par date desc,
    avec un extrait de la note pour chaque match.
    """
    from core.gazelle_api_client import GazelleAPIClient

    if not keyword or not keyword.strip():
        return {"success": False, "error": "Mot-clé manquant ou vide."}
    keyword_lower = keyword.strip().lower()

    months = max(1, min(months_back or 24, 60))

    tech_id = None
    if tech_filter_first_name:
        tech_id = resolve_tech(tech_filter_first_name)
        if not tech_id:
            return {
                "success": False,
                "error": f"Technicien inconnu : '{tech_filter_first_name}'.",
            }

    gz = GazelleAPIClient()

    today = date.today()
    windows = []
    win_end = today
    # Fenêtres de 90 jours pour rester sous le cap de pagination de Gazelle
    for _ in range((months * 30 + 89) // 90):
        win_start = win_end - timedelta(days=90)
        windows.append((win_start.isoformat(), win_end.isoformat()))
        win_end = win_start - timedelta(days=1)

    query = """
    query Search($filters: PrivateAllEventsFilter) {
        allEventsBatched(first: 200, filters: $filters) {
            nodes {
                id title start notes status
                user { id firstName lastName }
                client { id defaultContact { firstName lastName } }
                allEventPianos(first: 3) { nodes { piano { make model } } }
            }
        }
    }
    """

    matches = []
    seen_ids = set()
    total_scanned = 0
    for start_d, end_d in windows:
        try:
            r = gz._execute_query(query, {"filters": {"startOn": start_d, "endOn": end_d}})
        except Exception:
            continue
        nodes = r.get("data", {}).get("allEventsBatched", {}).get("nodes", []) or []
        total_scanned += len(nodes)
        for n in nodes:
            if n["id"] in seen_ids:
                continue
            if tech_id and (n.get("user") or {}).get("id") != tech_id:
                continue
            notes = (n.get("notes") or "").lower()
            title = (n.get("title") or "").lower()
            if keyword_lower in notes or keyword_lower in title:
                seen_ids.add(n["id"])
                matches.append(n)

    matches.sort(key=lambda n: n.get("start") or "", reverse=True)
    matches = matches[:25]

    results = []
    for n in matches:
        u = n.get("user") or {}
        contact = (n.get("client") or {}).get("defaultContact") or {}
        client_name = f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
        pianos = (n.get("allEventPianos", {}) or {}).get("nodes", []) or []
        piano_str = ", ".join(
            f"{p['piano']['make']} {p['piano']['model']}".strip()
            for p in pianos if p.get("piano")
        )

        notes_full = n.get("notes") or ""
        excerpt = ""
        if keyword_lower in notes_full.lower():
            idx = notes_full.lower().find(keyword_lower)
            start = max(0, idx - 60)
            end = min(len(notes_full), idx + len(keyword) + 100)
            excerpt = notes_full[start:end].replace("\n", " ").strip()
            if start > 0:
                excerpt = "…" + excerpt
            if end < len(notes_full):
                excerpt = excerpt + "…"
        elif keyword_lower in (n.get("title") or "").lower():
            excerpt = f"(dans le titre : {n.get('title', '')})"

        results.append({
            "event_id": n["id"],
            "date": (n.get("start") or "")[:10],
            "tech_first_name": u.get("firstName", ""),
            "tech_last_name": u.get("lastName", ""),
            "client_id": (n.get("client") or {}).get("id"),
            "client_name": client_name,
            "piano": piano_str or None,
            "title": n.get("title", ""),
            "excerpt": excerpt,
        })

    return {
        "success": True,
        "keyword": keyword,
        "tech_filter": TECH_DISPLAY_NAMES.get(tech_id) if tech_id else None,
        "months_scanned": months,
        "total_events_scanned": total_scanned,
        "results_count": len(results),
        "results": results,
    }


@router.post("/search-keyword", response_model=Dict[str, Any])
async def search_keyword(req: AssistantRequest):
    """Parse une demande de recherche par mot-clé et retourne les events matchants.

    Exemples :
    - "chez quel client JP a réparé du polyester récemment"
    - "retrouve la note où Nicolas mentionne Steinway K-52"
    - "qui a une fuite de PLS"
    - "quels pianos ont des chevilles fatiguées"
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurée")

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    today_iso = date.today().isoformat()
    system_prompt = (
        f"Tu es l'assistant Gazelle de Piano Tek Musique. Aujourd'hui c'est {today_iso}. "
        "Ton rôle est de parser une demande de recherche libre dans les notes/titres "
        "des rendez-vous, et d'extraire les paramètres pour l'outil "
        "search_events_by_keyword.\n\n"
        "Techniciens connus : Allan, Nicolas, JP (Jean-Philippe), Margot.\n\n"
        "Identifie le mot-clé MÉTIER significatif (ex: 'polyester', 'humidistat', "
        "'cordelettes', 'Steinway K-52', 'fuite'). Évite les mots vides ('quel', "
        "'récemment', 'chez', 'quand', 'dernièrement'). Si l'utilisateur mentionne "
        "un seul technicien explicitement, utilise tech_filter_first_name. S'il "
        "mentionne plusieurs techniciens (ex: 'JP et Allan'), laisse vide pour "
        "scanner tous.\n\n"
        "QUALIFICATIF TEMPOREL → months_back. Interprète SÉMANTIQUEMENT toute "
        "mention de temps dans la requête (n'importe quelle formulation, "
        "synonyme ou tournure libre) et choisis la valeur la plus proche en "
        "te basant sur ces ancres :\n"
        "  - très récent (jours, cette semaine) → 1\n"
        "  - récent (~quelques semaines, ce mois-ci) → 3\n"
        "  - assez récent (quelques mois) → 6\n"
        "  - cette année → 12\n"
        "  - l'année dernière → 18\n"
        "  - il y a longtemps → 36\n"
        "  - historique complet, depuis toujours → 60\n"
        "  - aucun qualificatif temporel dans la requête → laisse months_back "
        "vide (backend mettra 24 par défaut)\n\n"
        "Si la demande n'est PAS une recherche par mot-clé, ne pas appeler l'outil."
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            tools=[SEARCH_KEYWORD_TOOL],
            system=system_prompt,
            messages=[{"role": "user", "content": req.message}],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur Claude API : {exc}")

    tool_call = None
    text_response = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "search_events_by_keyword":
            tool_call = block.input
        elif block.type == "text":
            text_response.append(block.text)

    if not tool_call:
        return {
            "success": False,
            "intent_recognized": False,
            "message": " ".join(text_response) or "Je n'ai pas compris la demande comme une recherche par mot-clé.",
        }

    try:
        result = execute_search_keyword(
            keyword=tool_call.get("keyword"),
            tech_filter_first_name=tool_call.get("tech_filter_first_name"),
            months_back=tool_call.get("months_back"),
        )
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
