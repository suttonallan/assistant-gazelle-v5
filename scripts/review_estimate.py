#!/usr/bin/env python3
"""
Agent de revision de soumissions Gazelle.

Lit une soumission depuis l'API Gazelle, l'analyse avec Claude,
et suggere des ameliorations premium/ultra-luxe.
Apprend des preferences d'Allan au fil du temps.

Usage:
    python3 scripts/review_estimate.py 11900
    python3 scripts/review_estimate.py 11900 --dry-run
    python3 scripts/review_estimate.py 11900 --model opus
"""

import argparse
import json
import os
import sys
import copy
from pathlib import Path
from typing import Dict, List, Optional, Any

# Ajouter le projet au path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / '.env')

# Couleurs terminal
class C:
    BOLD = '\033[1m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    DIM = '\033[2m'
    RESET = '\033[0m'


# --- Chargement des preferences apprises ---

def load_preferences(storage: SupabaseStorage) -> List[Dict]:
    """Charge les preferences depuis Supabase."""
    try:
        url = f"{storage.api_url}/estimate_review_preferences?select=*&order=created_at.desc"
        response = __import__('requests').get(url, headers=storage._get_headers())
        if response.status_code == 200:
            prefs = response.json()
            print(f"{C.DIM}  {len(prefs)} preferences apprises chargees{C.RESET}")
            return prefs
        elif response.status_code == 404:
            print(f"{C.YELLOW}  Table estimate_review_preferences non trouvee. Executez:{C.RESET}")
            print(f"{C.DIM}  sql/create_estimate_review_preferences.sql{C.RESET}")
            return []
        else:
            print(f"{C.DIM}  Preferences: HTTP {response.status_code}{C.RESET}")
            return []
    except Exception as e:
        print(f"{C.DIM}  Preferences non disponibles: {e}{C.RESET}")
        return []


def save_preference(storage: SupabaseStorage, category: str, item_key: str,
                    original: Optional[str], preferred: str, accepted: bool,
                    scope: str = "global"):
    """Sauvegarde une preference dans Supabase."""
    try:
        import requests
        url = f"{storage.api_url}/estimate_review_preferences"
        data = {
            "category": category,
            "item_key": item_key,
            "original": original,
            "preferred": preferred,
            "accepted": accepted,
            "scope": scope
        }
        response = requests.post(url, json=data, headers=storage._get_headers())
        if response.status_code in (200, 201):
            return True
    except Exception:
        pass
    return False


def format_preferences_for_prompt(preferences: List[Dict]) -> str:
    """Formate les preferences en texte pour le prompt Claude."""
    if not preferences:
        return ""

    # Grouper par categorie, ne garder que les globales acceptees
    accepted = [p for p in preferences if p.get('accepted', True) and p.get('scope') == 'global']
    refused = [p for p in preferences if not p.get('accepted', True) and p.get('scope') == 'global']

    lines = []
    if accepted:
        lines.append("## Preferences VALIDEES par Allan (TOUJOURS appliquer) :")
        for p in accepted[:30]:  # Limiter
            lines.append(f"- [{p['category']}] {p['item_key']}: \"{p['preferred']}\"" +
                         (f" (remplace: \"{p['original']}\")" if p.get('original') else ""))

    if refused:
        lines.append("\n## Suggestions REFUSEES par Allan (NE PAS reproposer) :")
        for p in refused[:20]:
            lines.append(f"- [{p['category']}] {p['item_key']}: \"{p.get('original', '')}\" refuse")

    return "\n".join(lines)


# --- Chargement du knowledge doc ---

def load_knowledge() -> str:
    """Charge la base de connaissances statique."""
    knowledge_path = PROJECT_ROOT / 'docs' / 'knowledge_estimate_review.md'
    if knowledge_path.exists():
        return knowledge_path.read_text(encoding='utf-8')
    print(f"{C.RED}  ERREUR: {knowledge_path} non trouve{C.RESET}")
    return ""


# --- Analyse Claude ---

def analyze_with_claude(estimate: Dict, knowledge: str, preferences_text: str,
                        model: str = "claude-sonnet-4-20250514") -> Dict:
    """Envoie la soumission a Claude pour analyse."""
    from anthropic import Anthropic

    client_info = estimate.get('client', {})
    piano_info = estimate.get('piano', {})
    contact = client_info.get('defaultContact', {})
    client_name = (f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
                   or client_info.get('companyName', 'Client inconnu'))

    # Construire le resume de la soumission
    tiers_summary = []
    for tier in estimate.get('allEstimateTiers', []):
        tier_info = {
            'id': tier['id'],
            'isPrimary': tier.get('isPrimary'),
            'total': tier.get('total', 0),
            'notes': tier.get('notes'),
            'groups': [],
            'ungrouped_items': []
        }
        for group in tier.get('allEstimateTierGroups', []):
            group_info = {
                'id': group['id'],
                'name': group.get('name', ''),
                'items': []
            }
            for item in group.get('allEstimateTierItems', []):
                group_info['items'].append({
                    'id': item['id'],
                    'name': item.get('name', ''),
                    'description': item.get('description'),
                    'educationDescription': item.get('educationDescription'),
                    'amount': item.get('amount', 0),
                    'quantity': item.get('quantity', 100),
                    'type': item.get('type'),
                    'masterServiceItem': item.get('masterServiceItem'),
                })
            tier_info['groups'].append(group_info)

        for item in tier.get('allUngroupedEstimateTierItems', []):
            tier_info['ungrouped_items'].append({
                'id': item['id'],
                'name': item.get('name', ''),
                'description': item.get('description'),
                'amount': item.get('amount', 0),
                'quantity': item.get('quantity', 100),
                'masterServiceItem': item.get('masterServiceItem'),
            })
        tiers_summary.append(tier_info)

    estimate_json = json.dumps({
        'number': estimate.get('number'),
        'client': client_name,
        'client_notes': client_info.get('personalNotes'),
        'piano': {
            'make': piano_info.get('make'),
            'model': piano_info.get('model'),
            'type': piano_info.get('type'),
            'year': piano_info.get('year'),
            'location': piano_info.get('location'),
            'notes': piano_info.get('notes'),
        },
        'notes': estimate.get('notes'),
        'tiers': tiers_summary,
    }, indent=2, ensure_ascii=False)

    system_prompt = f"""Tu es un expert en facturation et soumissions pour Piano Technique Montreal, un service premium/ultra-luxe d'entretien et restauration de pianos.

{knowledge}

{preferences_text}

## Instructions

Analyse la soumission ci-dessous et propose des ameliorations. Pour chaque suggestion, fournis:
- Le type de suggestion
- L'item concerne (avec son ID si modification)
- Le texte actuel et le texte propose
- La raison de la modification

IMPORTANT:
- Les montants sont en CENTIMES (45000 = 450.00$)
- Les quantites sont en CENTIEMES (100 = 1 unite)
- Ne JAMAIS suggerer d'items du groupe "Pour techniciens"
- Respecter les preferences apprises ci-dessus
- Ton premium et professionnel dans toutes les descriptions
- Si la soumission est deja bien faite, dire pourquoi et donner un score eleve

Reponds UNIQUEMENT en JSON valide avec cette structure exacte:
{{
  "score_global": <1-10>,
  "resume": "<resume en 1-2 phrases>",
  "suggestions": [
    {{
      "type": "<description|naming|missing_item|bonus_item|price_adjustment|notes>",
      "item_id": "<eti_xxx ou null si nouvel item>",
      "item_key": "<mit_xxx ou nom generique pour apprentissage>",
      "group_name": "<nom du groupe si applicable>",
      "current": "<texte/valeur actuel ou null>",
      "proposed": "<texte/valeur propose>",
      "amount": <montant en centimes si applicable, sinon null>,
      "reason": "<raison de la suggestion>"
    }}
  ]
}}"""

    anthropic = Anthropic()
    response = anthropic.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": f"Analyse cette soumission:\n\n{estimate_json}"}],
        system=system_prompt,
    )

    response_text = response.content[0].text.strip()

    # Extraire le JSON (parfois Claude entoure de ```json...```)
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        json_lines = []
        in_json = False
        for line in lines:
            if line.startswith('```') and not in_json:
                in_json = True
                continue
            elif line.startswith('```') and in_json:
                break
            elif in_json:
                json_lines.append(line)
        response_text = '\n'.join(json_lines)

    return json.loads(response_text)


# --- Affichage ---

def display_results(analysis: Dict, estimate_number: int):
    """Affiche les resultats de l'analyse dans le terminal."""
    score = analysis.get('score_global', 0)
    resume = analysis.get('resume', '')
    suggestions = analysis.get('suggestions', [])

    # Score avec couleur
    if score >= 8:
        score_color = C.GREEN
    elif score >= 5:
        score_color = C.YELLOW
    else:
        score_color = C.RED

    print(f"\n{'='*60}")
    print(f"{C.BOLD}  REVISION SOUMISSION #{estimate_number}{C.RESET}")
    print(f"{'='*60}")
    print(f"\n  Score: {score_color}{C.BOLD}{score}/10{C.RESET}")
    print(f"  {C.DIM}{resume}{C.RESET}")

    if not suggestions:
        print(f"\n  {C.GREEN}Aucune suggestion - la soumission est excellente!{C.RESET}\n")
        return

    # Grouper par type
    type_labels = {
        'description': 'Descriptions',
        'naming': 'Noms d\'items',
        'missing_item': 'Items manquants',
        'bonus_item': 'Items bonus suggeres',
        'price_adjustment': 'Ajustements de prix',
        'notes': 'Notes de la soumission',
    }
    type_colors = {
        'description': C.CYAN,
        'naming': C.BLUE,
        'missing_item': C.MAGENTA,
        'bonus_item': C.GREEN,
        'price_adjustment': C.YELLOW,
        'notes': C.DIM,
    }

    by_type = {}
    for s in suggestions:
        t = s.get('type', 'other')
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(s)

    for idx, s in enumerate(suggestions):
        t = s.get('type', 'other')
        color = type_colors.get(t, C.RESET)
        label = type_labels.get(t, t.upper())

        print(f"\n  {color}{C.BOLD}[{idx+1}] {label}{C.RESET}")

        if s.get('item_id'):
            print(f"      Item: {C.DIM}{s['item_id']}{C.RESET}")
        if s.get('group_name'):
            print(f"      Groupe: {s['group_name']}")

        if s.get('current'):
            current_display = s['current']
            if isinstance(current_display, (int, float)):
                current_display = f"{current_display/100:.2f}$"
            print(f"      Actuel:  {C.RED}{current_display}{C.RESET}")

        proposed = s.get('proposed', '')
        if isinstance(proposed, (int, float)):
            proposed = f"{proposed/100:.2f}$"
        print(f"      Propose: {C.GREEN}{proposed}{C.RESET}")

        if s.get('amount') is not None:
            print(f"      Montant: {s['amount']/100:.2f}$")

        print(f"      {C.DIM}Raison: {s.get('reason', '')}{C.RESET}")


# --- Construction des tiers pour mutation ---

TPS_TAX_ID = "tax_JeCfY4wfbXtN6J28"
TPS_RATE = 5000
TVQ_TAX_ID = "tax_xe9FEApq94zI7kXD"
TVQ_RATE = 9975


def _build_taxes(amount: int, is_taxable: bool) -> list:
    """Construit le tableau de taxes TPS+TVQ pour un item."""
    if not is_taxable or amount == 0:
        return []
    tps = round(amount * TPS_RATE / 100000)
    tvq = round(amount * TVQ_RATE / 100000)
    return [
        {'taxId': TPS_TAX_ID, 'rate': TPS_RATE, 'total': tps},
        {'taxId': TVQ_TAX_ID, 'rate': TVQ_RATE, 'total': tvq},
    ]


def build_tiers_input(estimate: Dict, approved_suggestions: List[Dict]) -> List[Dict]:
    """
    Reconstruit la structure estimateTiers avec les suggestions approuvees appliquees.

    L'API updateEstimate remplace TOUT, donc on doit reconstruire completement.
    """
    tiers = estimate.get('allEstimateTiers', [])
    tiers_input = []

    # Index des modifications par item_id
    mods_by_item = {}
    new_items = []
    notes_update = None

    for s in approved_suggestions:
        if s.get('type') == 'notes':
            notes_update = s.get('proposed')
        elif s.get('type') in ('missing_item', 'bonus_item'):
            new_items.append(s)
        elif s.get('item_id'):
            mods_by_item[s['item_id']] = s

    for tier in tiers:
        tier_input = {
            "sequenceNumber": tier.get('sequenceNumber', 0),
            "isPrimary": tier.get('isPrimary', True),
            "notes": tier.get('notes'),
            "allowSelfSchedule": tier.get('allowSelfSchedule', False),
            "estimateTierGroups": [],
            "ungroupedEstimateTierItems": [],
        }
        if tier.get('targetPerformanceLevel') is not None:
            tier_input["targetPerformanceLevel"] = tier['targetPerformanceLevel']

        for group in tier.get('allEstimateTierGroups', []):
            group_input = {
                "name": group.get('name', ''),
                "sequenceNumber": group.get('sequenceNumber', 0),
                "estimateTierItems": [],
            }

            for item in group.get('allEstimateTierItems', []):
                item_input = _build_item_input(item, mods_by_item.get(item['id']))
                group_input["estimateTierItems"].append(item_input)

            tier_input["estimateTierGroups"].append(group_input)

        # Items non-groupes
        for item in tier.get('allUngroupedEstimateTierItems', []):
            item_input = _build_item_input(item, mods_by_item.get(item['id']))
            tier_input["ungroupedEstimateTierItems"].append(item_input)

        # Ajouter les nouveaux items dans le bon groupe ou en non-groupe
        for new_item in new_items:
            new_item_input = _build_new_item_input(new_item)
            target_group = new_item.get('group_name')

            if target_group:
                # Chercher le groupe existant
                placed = False
                for g in tier_input["estimateTierGroups"]:
                    if g["name"] == target_group:
                        g["estimateTierItems"].append(new_item_input)
                        placed = True
                        break
                if not placed:
                    # Creer le groupe
                    tier_input["estimateTierGroups"].append({
                        "name": target_group,
                        "sequenceNumber": len(tier_input["estimateTierGroups"]),
                        "estimateTierItems": [new_item_input],
                    })
            else:
                tier_input["ungroupedEstimateTierItems"].append(new_item_input)

        tiers_input.append(tier_input)

    return tiers_input, notes_update


def _build_item_input(item: Dict, mod: Optional[Dict] = None) -> Dict:
    """Construit un PrivateEstimateTierItemInput depuis un item existant + modification."""
    amount = item.get('amount', 0)

    result = {
        "name": item.get('name', ''),
        "sequenceNumber": item.get('sequenceNumber', 0),
        "amount": amount,
        "quantity": item.get('quantity', 100),
        "duration": item.get('duration') or 0,
        "type": item.get('type', 'LABOR_FIXED_RATE'),
        "isTaxable": item.get('isTaxable', True),
        "isTuning": item.get('isTuning', False),
        "photos": [],
    }

    if item.get('description') is not None:
        result["description"] = item['description']
    if item.get('educationDescription') is not None:
        result["educationDescription"] = item['educationDescription']

    msi = item.get('masterServiceItem')
    if msi and msi.get('id'):
        result["masterServiceItemId"] = msi['id']

    # Appliquer la modification
    if mod:
        mod_type = mod.get('type')
        if mod_type == 'naming':
            result["name"] = mod['proposed']
        elif mod_type == 'description':
            result["description"] = mod['proposed']
        elif mod_type == 'price_adjustment':
            if mod.get('amount') is not None:
                result["amount"] = int(mod['amount'])
                amount = result["amount"]

    # Taxes doivent inclure rate sinon erreur API
    result["taxes"] = _build_taxes(amount, result["isTaxable"])

    return result


def _build_new_item_input(suggestion: Dict) -> Dict:
    """Construit un PrivateEstimateTierItemInput pour un nouvel item."""
    amount = int(suggestion.get('amount', 0)) if suggestion.get('amount') else 0

    result = {
        "name": suggestion.get('proposed', ''),
        "sequenceNumber": 99,
        "amount": amount,
        "quantity": 100,
        "duration": 0,
        "type": "LABOR_FIXED_RATE",
        "isTaxable": True,
        "isTuning": False,
        "taxes": _build_taxes(amount, True),
        "photos": [],
    }

    # Si un item_key est un MIT ID, le lier
    item_key = suggestion.get('item_key', '')
    if item_key.startswith('mit_'):
        result["masterServiceItemId"] = item_key

    return result


# --- Validation interactive ---

def interactive_review(suggestions: List[Dict], storage: SupabaseStorage,
                       estimate_number: int, dry_run: bool) -> List[Dict]:
    """Validation interactive des suggestions."""
    if not suggestions:
        return []

    print(f"\n{'─'*60}")
    print(f"{C.BOLD}  VALIDATION{C.RESET}" + (f" {C.DIM}(dry-run: aucun changement ne sera applique){C.RESET}" if dry_run else ""))
    print(f"{'─'*60}")
    print(f"  {C.DIM}o = accepter | n = refuser | t = tout accepter | q = quitter{C.RESET}\n")

    approved = []

    for idx, s in enumerate(suggestions):
        t = s.get('type', '?')
        proposed = s.get('proposed', '')
        if isinstance(proposed, (int, float)):
            proposed = f"{proposed/100:.2f}$"

        label = f"[{idx+1}/{len(suggestions)}] {t}: {proposed[:60]}"

        while True:
            choice = input(f"  {label} {C.BOLD}(o/n/t/q)?{C.RESET} ").strip().lower()

            if choice == 'o':
                approved.append(s)
                _save_preference_from_suggestion(storage, s, accepted=True, estimate_number=estimate_number)
                print(f"    {C.GREEN}Accepte{C.RESET}")
                break
            elif choice == 'n':
                _save_preference_from_suggestion(storage, s, accepted=False, estimate_number=estimate_number)
                print(f"    {C.RED}Refuse{C.RESET}")
                break
            elif choice == 't':
                for remaining in suggestions[idx:]:
                    approved.append(remaining)
                    _save_preference_from_suggestion(storage, remaining, accepted=True, estimate_number=estimate_number)
                print(f"    {C.GREEN}Tout accepte ({len(suggestions) - idx} suggestions){C.RESET}")
                return approved
            elif choice == 'q':
                print(f"    {C.YELLOW}Abandon{C.RESET}")
                return approved
            else:
                print(f"    {C.DIM}Choix invalide (o/n/t/q){C.RESET}")

    return approved


def _save_preference_from_suggestion(storage: SupabaseStorage, suggestion: Dict,
                                     accepted: bool, estimate_number: int):
    """Sauvegarde la decision comme preference pour apprentissage."""
    category = suggestion.get('type', 'other')
    item_key = suggestion.get('item_key', suggestion.get('item_id', 'unknown'))
    original = suggestion.get('current')
    proposed = suggestion.get('proposed', '')

    if isinstance(original, (int, float)):
        original = str(original)
    if isinstance(proposed, (int, float)):
        proposed = str(proposed)

    save_preference(
        storage=storage,
        category=category,
        item_key=item_key,
        original=original,
        preferred=proposed if accepted else (original or ''),
        accepted=accepted,
        scope='global'
    )


# --- Application des changements ---

def apply_changes(api_client: GazelleAPIClient, estimate: Dict,
                  approved_suggestions: List[Dict]):
    """Applique les suggestions approuvees via l'API Gazelle."""
    tiers_input, notes_update = build_tiers_input(estimate, approved_suggestions)

    input_data = {
        "estimateTiers": tiers_input,
    }
    if notes_update is not None:
        input_data["notes"] = notes_update

    estimate_id = estimate['id']
    print(f"\n  {C.BOLD}Application des changements...{C.RESET}")

    try:
        result = api_client.update_estimate(estimate_id, input_data)
        print(f"  {C.GREEN}Soumission mise a jour avec succes!{C.RESET}")
        new_total = 0
        for tier in result.get('allEstimateTiers', []):
            new_total = max(new_total, tier.get('total', 0))
        if new_total:
            print(f"  Nouveau total: {new_total/100:.2f}$")
        return True
    except Exception as e:
        print(f"  {C.RED}ERREUR lors de la mise a jour: {e}{C.RESET}")
        return False


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="Revision de soumissions Gazelle")
    parser.add_argument('number', type=int, help="Numero de la soumission (ex: 11900)")
    parser.add_argument('--dry-run', action='store_true', help="Analyse seulement, pas de modifications")
    parser.add_argument('--model', default='sonnet', choices=['sonnet', 'opus'],
                        help="Modele Claude a utiliser (defaut: sonnet)")
    args = parser.parse_args()

    model_map = {
        'sonnet': 'claude-sonnet-4-20250514',
        'opus': 'claude-opus-4-20250514',
    }
    model = model_map[args.model]

    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  AGENT DE REVISION DE SOUMISSIONS{C.RESET}")
    print(f"{C.BOLD}{'='*60}{C.RESET}")
    print(f"  Soumission: #{args.number}")
    print(f"  Modele: {args.model}")
    print(f"  Mode: {'dry-run (lecture seule)' if args.dry_run else 'interactif'}")

    # 1. Initialiser les clients
    print(f"\n{C.BOLD}[1/4] Connexion...{C.RESET}")
    api_client = GazelleAPIClient()
    storage = SupabaseStorage(silent=True)

    # 2. Fetch soumission
    print(f"\n{C.BOLD}[2/4] Chargement de la soumission #{args.number}...{C.RESET}")
    estimate = api_client.get_estimate_by_number(args.number)

    if not estimate:
        print(f"\n{C.RED}  Soumission #{args.number} non trouvee.{C.RESET}")
        sys.exit(1)

    # Afficher resume
    client_info = estimate.get('client', {})
    piano_info = estimate.get('piano', {})
    contact = client_info.get('defaultContact', {})
    client_name = (f"{contact.get('firstName', '')} {contact.get('lastName', '')}".strip()
                   or client_info.get('companyName', 'Client inconnu'))

    tiers = estimate.get('allEstimateTiers', [])
    total = max((t.get('total', 0) for t in tiers), default=0)
    item_count = sum(
        len(g.get('allEstimateTierItems', []))
        for t in tiers
        for g in t.get('allEstimateTierGroups', [])
    ) + sum(len(t.get('allUngroupedEstimateTierItems', [])) for t in tiers)

    print(f"  Client: {client_name}")
    print(f"  Piano: {piano_info.get('make', '?')} {piano_info.get('model', '')} ({piano_info.get('type', '?')})")
    print(f"  Total: {total/100:.2f}$ | {item_count} items | {len(tiers)} tier(s)")

    # 3. Charger knowledge + preferences
    print(f"\n{C.BOLD}[3/4] Analyse avec Claude ({args.model})...{C.RESET}")
    knowledge = load_knowledge()
    preferences = load_preferences(storage)
    preferences_text = format_preferences_for_prompt(preferences)

    # 4. Analyse Claude
    analysis = analyze_with_claude(estimate, knowledge, preferences_text, model=model)

    # Afficher resultats
    display_results(analysis, args.number)

    suggestions = analysis.get('suggestions', [])

    if not suggestions:
        print(f"\n{C.GREEN}  Rien a modifier!{C.RESET}\n")
        return

    # En dry-run, pas de validation interactive
    if args.dry_run:
        print(f"\n  {C.YELLOW}Mode dry-run: aucun changement applique.{C.RESET}")
        print(f"  {C.DIM}Relancez sans --dry-run pour appliquer.{C.RESET}\n")
        return

    # 5. Validation interactive
    approved = interactive_review(suggestions, storage, args.number, dry_run=False)

    if not approved:
        print(f"\n{C.YELLOW}  Aucune suggestion approuvee.{C.RESET}\n")
        return

    print(f"\n  {C.GREEN}{len(approved)}/{len(suggestions)} suggestions approuvees{C.RESET}")

    # 6. Appliquer les changements
    confirm = input(f"\n  {C.BOLD}Appliquer {len(approved)} changements a la soumission #{args.number}? (o/n) {C.RESET}").strip().lower()
    if confirm == 'o':
        apply_changes(api_client, estimate, approved)
    else:
        print(f"  {C.YELLOW}Changements non appliques.{C.RESET}\n")


if __name__ == '__main__':
    main()
