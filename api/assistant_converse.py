"""Assistant conversationnel — fil de discussion avec mémoire + tous les outils.

Contrairement aux endpoints à message unique (/review-estimate, /duplicate-estimate…),
celui-ci garde l'HISTORIQUE et laisse Claude choisir l'outil, ce qui permet les
suivis (« oui, réactive-la avec le prix à jour »).

POST /assistant/converse
  body : { messages: [{role, content}...], current_user_first_name? }
  ret  : { reply: str, actions: [ {type, result} ... ] }

Réutilise les outils et fonctions d'exécution déjà validés dans assistant_routes.
Les créations de soumission restent des BROUILLONS (rien n'est envoyé au client).
"""
import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.assistant_routes import (
    REVIEW_ESTIMATE_TOOL, SEARCH_KEYWORD_TOOL, JOINT_APPOINTMENT_TOOL,
    execute_review_estimate, execute_search_keyword, execute_joint_appointment,
)
from api.assistant_duplication import duplicate_estimate

router = APIRouter()

# Outil de réactivation/création à partir d'un numéro (le manquant côté chat).
REACTIVATE_ESTIMATE_TOOL = {
    "name": "reactivate_estimate",
    "description": (
        "Crée une NOUVELLE soumission (brouillon) à partir d'une soumission "
        "EXISTANTE identifiée par son numéro. Mets reprice=true quand "
        "l'utilisateur veut « réactiver », « une nouvelle soumission à jour », "
        "« avec les nouveaux prix / le prix à jour » : les montants sont alors "
        "remis aux tarifs courants du catalogue. reprice=false = copie fidèle. "
        "Ne fait qu'un brouillon (rien n'est envoyé au client)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "estimate_number": {"type": "integer",
                                "description": "Numéro de la soumission source (ex: 11766)."},
            "reprice": {"type": "boolean",
                        "description": "true = remettre aux prix courants ; false = copie fidèle."},
        },
        "required": ["estimate_number"],
    },
}

TOOLS = [REACTIVATE_ESTIMATE_TOOL, REVIEW_ESTIMATE_TOOL, SEARCH_KEYWORD_TOOL, JOINT_APPOINTMENT_TOOL]


def _run_tool(name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Exécute un outil et retourne un dict résultat (jamais d'exception qui remonte)."""
    try:
        if name == "reactivate_estimate":
            return duplicate_estimate(
                int(tool_input["estimate_number"]),
                reprice=bool(tool_input.get("reprice", False)),
            )
        if name == "review_estimate":
            return execute_review_estimate(
                estimate_number=tool_input.get("estimate_number"),
                client_name_hint=tool_input.get("client_name_hint"),
            )
        if name == "search_events_by_keyword":
            return execute_search_keyword(
                keyword=tool_input.get("keyword"),
                tech_filter_first_name=tool_input.get("tech_filter_first_name"),
                months_back=tool_input.get("months_back"),
            )
        if name == "create_joint_appointment":
            return execute_joint_appointment(**tool_input)
        return {"success": False, "error": f"Outil inconnu : {name}"}
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        return {"success": False, "error": f"Erreur d'exécution ({name}) : {exc}"}


class ConverseMessage(BaseModel):
    role: str = Field(..., description="'user' ou 'assistant'")
    content: str


class ConverseRequest(BaseModel):
    messages: List[ConverseMessage]
    current_user_first_name: Optional[str] = None


@router.post("/converse", response_model=Dict[str, Any])
async def converse(req: ConverseRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY non configurée")
    if not req.messages:
        return {"reply": "Pose-moi une question ou une demande.", "actions": []}

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    today_iso = date.today().isoformat()
    user_ctx = ""
    if req.current_user_first_name:
        user_ctx = f"\nL'utilisateur courant est {req.current_user_first_name}."

    system_prompt = (
        f"Tu es l'assistant Gazelle de Piano Tek Musique. Aujourd'hui : {today_iso}. "
        "Tu réponds en français, de façon concise et concrète. Techniciens connus : "
        "Allan, Nicolas, JP (Jean-Philippe), Margot.\n\n"
        "Tu as des OUTILS. Utilise-les quand c'est pertinent :\n"
        "- reactivate_estimate : créer une nouvelle soumission (brouillon) à partir "
        "d'un numéro. reprice=true pour « réactiver / à jour / nouveaux prix ».\n"
        "- review_estimate : analyser/réviser une soumission existante.\n"
        "- search_events_by_keyword : retrouver des rendez-vous par mot-clé.\n"
        "- create_joint_appointment : créer un RV conjoint.\n\n"
        "Sers-toi de l'HISTORIQUE : si l'utilisateur confirme (« oui », « vas-y ») une "
        "action que tu viens de proposer, exécute-la avec l'outil. Si une demande est "
        "ambiguë (numéro ou client manquant), pose UNE question courte au lieu de deviner. "
        "Les créations de soumission sont toujours des brouillons : rien n'est envoyé au client."
        + user_ctx
    )

    messages: List[Dict[str, Any]] = [{"role": m.role, "content": m.content} for m in req.messages]
    actions: List[Dict[str, Any]] = []

    # Boucle outil : Claude peut enchaîner quelques appels avant de répondre en texte.
    for _ in range(5):
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )
        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        texts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]

        if not tool_uses:
            return {"reply": " ".join(t for t in texts if t).strip()
                    or "D'accord.", "actions": actions}

        messages.append({"role": "assistant", "content": resp.content})
        tool_results = []
        for tu in tool_uses:
            result = _run_tool(tu.name, tu.input or {})
            actions.append({"type": tu.name, "input": tu.input, "result": result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })
        messages.append({"role": "user", "content": tool_results})

    return {"reply": "J'ai fait plusieurs étapes mais je n'ai pas pu conclure — reformule ?",
            "actions": actions}
