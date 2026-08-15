"""Parseur d'emails PdA basé LLM (Claude Sonnet).

Remplace/complète le parseur regex : Claude LIT l'email et décide s'il contient
une vraie demande de service à planifier, en ignorant les accusés de réception,
réactions, réponses automatiques et confirmations de facture — tout en sachant
extraire une demande qui vit dans un bloc cité/transféré.

Convention de retour de parse_email_llm() :
- None      -> le LLM n'a pas pu répondre (clé absente, erreur API) : l'appelant
               DOIT retomber sur le parseur regex (parse_email_text).
- []        -> le LLM a lu l'email et conclut : AUCUNE demande (accusé, réaction…).
- [ {...} ] -> demandes extraites (mêmes champs que le parseur regex).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-5"

_TOOL = {
    "name": "extraire_demandes_pda",
    "description": "Retourne les demandes de service PdA réellement contenues dans l'email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "est_demande": {
                "type": "boolean",
                "description": "true SEULEMENT si l'email demande de PLANIFIER au moins un service.",
            },
            "raison_si_non": {
                "type": "string",
                "description": "Si est_demande=false : pourquoi (accusé, réaction, auto-réponse, facture…).",
            },
            "demandes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date du service AAAA-MM-JJ."},
                        "time": {"type": "string", "description": "Heure ou moment (ex. '14h', 'avant midi'). Vide si absent."},
                        "room": {"type": "string", "description": "Salle (ex. 'Wilfrid-Pelletier', 'Maisonneuve', 'Salle D')."},
                        "for_who": {"type": "string", "description": "Pour qui / événement (ex. 'OSM', 'FIJM', artiste)."},
                        "piano": {"type": "string", "description": "Piano si mentionné (ex. 'Steinway D')."},
                        "diapason": {"type": "string", "description": "Diapason si mentionné (ex. '442')."},
                        "requester": {"type": "string", "description": "Personne qui demande, si claire."},
                    },
                    "required": ["date"],
                },
            },
        },
        "required": ["est_demande", "demandes"],
    },
}


def _system_prompt() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return (
        f"Tu extrais les demandes de service de piano pour Place des Arts / Opéra "
        f"de Montréal, envoyées à Piano Tek Musique. Aujourd'hui : {today}.\n\n"
        "Une DEMANDE = on te demande de planifier un service (accord/tuning, "
        "préparation de piano, réglage) à une date, dans une salle, pour un "
        "événement.\n\n"
        "IGNORE (est_demande=false, demandes=[]) si l'email est :\n"
        "- un accusé de réception (« bien reçu », « merci », « confirmé »),\n"
        "- une confirmation/relance de FACTURE ou de paiement,\n"
        "- une réaction (« [like] … reacted to your message »),\n"
        "- une réponse automatique / hors-bureau,\n"
        "- une simple discussion sans service à planifier.\n\n"
        "Une demande peut se trouver dans un bloc CITÉ ou TRANSFÉRÉ : extrais-la "
        "si l'email demande vraiment le service. Mais si la partie NEUVE ne fait "
        "qu'accuser réception d'un fil, NE ré-extrais PAS la demande citée.\n\n"
        "Dates en AAAA-MM-JJ (déduis l'année à partir d'aujourd'hui). Une entrée "
        "par service distinct (date + salle + heure). N'invente aucun champ absent."
    )


def parse_email_llm(subject: Optional[str], body: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """Voir la convention de retour dans le docstring du module."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not (body or "").strip():
        return None  # -> fallback regex

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        content = f"Objet : {subject or '(sans objet)'}\n\n{body}"
        resp = client.messages.create(
            model=_MODEL,
            # Sur Sonnet 5, le thinking adaptatif est actif quand le parametre
            # `thinking` est omis, et il partage ce plafond avec la reponse.
            # 1500 pouvait donc tronquer l'appel d'outil et faire retomber tout
            # le scan sur le parser regex sans que rien ne le signale.
            max_tokens=4000,
            system=_system_prompt(),
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "extraire_demandes_pda"},
            messages=[{"role": "user", "content": content}],
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "extraire_demandes_pda":
                data = block.input or {}
                if not data.get("est_demande"):
                    return []
                # Ne garder que les demandes avec au moins une date.
                return [d for d in (data.get("demandes") or []) if d.get("date")]
        return []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"parse_email_llm échec, fallback regex: {e}")
        return None
