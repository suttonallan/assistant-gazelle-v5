"""
Actions soumission (création / amélioration) déclenchées par le chat.

MVP : retourne un PREVIEW. L'exécution réelle (mutation Gazelle) se fait
après confirmation explicite de l'utilisateur via /chat/action/execute.

Garde-fous appliqués :
- Identity check via update_estimate_safe (à intégrer côté skill Gazelle)
- Soumissions toujours créées en DRAFT (l'envoi au client = action humaine)
- Pas de mutations destructrices (delete/cancel)
- Audit log + rate limit dans l'orchestrateur (intent_router.py)
"""
import logging
from typing import Dict, List, Optional

import requests

from core.gazelle_api_client import GazelleAPIClient

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# Recherche client (résolution du hint en client_id)
# ───────────────────────────────────────────────

SEARCH_CLIENT_QUERY = """
query($search: String!) {
    allEstimates(first: 5, filters: {search: $search}) {
        nodes {
            client {
                id
                defaultContact { firstName lastName }
                pianos: allPianos(first: 5) {
                    nodes { id make model year type }
                }
            }
        }
    }
}
"""


def resolve_client(client_hint: str) -> Optional[Dict]:
    """
    Résout un hint texte ('Joly', 'Levesque') en {client_id, contact, pianos}.
    Stratégie : passer par allEstimates + search (validé pour ce cas).
    Retourne None si introuvable ou ambigu.
    """
    if not client_hint:
        return None
    client = GazelleAPIClient()
    try:
        result = client._execute_query(SEARCH_CLIENT_QUERY, {'search': client_hint})
        nodes = result.get('data', {}).get('allEstimates', {}).get('nodes', []) or []
        # Dédupliquer par client_id
        seen = {}
        for n in nodes:
            c = (n or {}).get('client') or {}
            cid = c.get('id')
            if cid and cid not in seen:
                seen[cid] = c
        clients = list(seen.values())
        if len(clients) == 1:
            return clients[0]
        if len(clients) > 1:
            # Ambiguïté → retourner les options
            return {'_ambiguous': True, 'options': clients}
        return None
    except Exception as exc:
        logger.warning(f"resolve_client error: {exc}")
        return None


# ───────────────────────────────────────────────
# Lecture d'une soumission existante (pour improve)
# ───────────────────────────────────────────────

READ_ESTIMATE_QUERY = """
query($search: String!) {
    allEstimates(first: 5, filters: {search: $search}) {
        nodes {
            id number notes estimatedOn isArchived
            recommendedTierTotal
            client { id defaultContact { firstName lastName } }
            piano { id make model year }
            allEstimateTiers {
                id sequenceNumber isPrimary subtotal taxTotal total
                allEstimateTierGroups {
                    name
                    allEstimateTierItems {
                        name amount quantity duration description
                        masterServiceItem { id }
                    }
                }
            }
        }
    }
}
"""


def read_estimate(number: int) -> Optional[Dict]:
    """Lit une soumission par numéro. Retourne None si introuvable."""
    client = GazelleAPIClient()
    try:
        result = client._execute_query(READ_ESTIMATE_QUERY, {'search': str(number)})
        nodes = result.get('data', {}).get('allEstimates', {}).get('nodes', []) or []
        for n in nodes:
            if n.get('number') == number:
                return n
        return None
    except Exception as exc:
        logger.warning(f"read_estimate error: {exc}")
        return None


# ───────────────────────────────────────────────
# CREATE — preview d'une nouvelle soumission
# ───────────────────────────────────────────────

def preview_create_estimate(intent: Dict) -> Dict:
    """
    Construit un PREVIEW de la soumission qu'on créerait. Pas de mutation.

    Retourne :
        {
            'ok': True,
            'preview': {
                'client': {...},
                'piano': {...},
                'bundles': ['marteaux', 'cordes_basses', ...],
                'estimated_total': float,
                'tiers_summary': [...],
            },
            'message': 'Voici la soumission que je vais créer. Confirme pour la pousser dans Gazelle.'
        }
    """
    bundles = intent.get('bundles', [])
    if not bundles:
        return {
            'ok': False,
            'message': "Aucun service identifié dans ta demande. Précise par exemple : « marteaux + cordes basses + grand entretien »."
        }

    client_hint = intent.get('client_hint')
    if not client_hint:
        return {
            'ok': False,
            'message': "Je n'ai pas identifié de client. Précise : « pour Mme Joly »."
        }

    client = resolve_client(client_hint)
    if not client:
        return {
            'ok': False,
            'message': f"Aucun client trouvé pour « {client_hint} ». Vérifie l'orthographe ou crée la fiche dans Gazelle d'abord."
        }
    if client.get('_ambiguous'):
        opts = client['options'][:5]
        names = [
            f"{(c.get('defaultContact') or {}).get('firstName','')} "
            f"{(c.get('defaultContact') or {}).get('lastName','')}"
            for c in opts
        ]
        return {
            'ok': False,
            'message': f"Plusieurs clients correspondent à « {client_hint} » : {', '.join(names)}. Précise le nom complet."
        }

    contact = client.get('defaultContact') or {}
    pianos = (client.get('pianos') or {}).get('nodes', [])
    return {
        'ok': True,
        'preview': {
            'action_type': 'estimate.create',
            'client': {
                'id': client.get('id'),
                'name': f"{contact.get('firstName','')} {contact.get('lastName','')}".strip(),
            },
            'pianos_available': [
                {'id': p.get('id'), 'desc': f"{p.get('make','')} {p.get('model','')} {p.get('year','')}".strip()}
                for p in pianos
            ],
            'bundles_requested': bundles,
        },
        'message': (
            f"Soumission à créer pour {contact.get('firstName','')} {contact.get('lastName','')} "
            f"avec les bundles suivants : {', '.join(bundles)}. "
            f"⚠️ MVP : la création réelle nécessite de spécifier le piano et les détails. "
            f"Confirme pour qu'Allan finalise la création."
        ),
    }


# ───────────────────────────────────────────────
# IMPROVE — preview d'amélioration d'une soumission existante
# ───────────────────────────────────────────────

# Patterns de friction qu'on détecte automatiquement
def detect_frictions(estimate: Dict) -> List[str]:
    """Liste les frictions détectées dans une soumission existante."""
    frictions = []
    tiers = estimate.get('allEstimateTiers') or []
    for tier in tiers:
        for grp in tier.get('allEstimateTierGroups') or []:
            for item in grp.get('allEstimateTierItems') or []:
                amount = item.get('amount') or 0
                name = item.get('name') or ''
                if amount == 0 and 'avertissement' in name.lower():
                    frictions.append(f"Item à 0$ « {name[:60]} » → devrait être dans les notes")
                if amount == 0 and item.get('description'):
                    frictions.append(f"Item à 0$ avec description « {name[:60]} » → à intégrer dans un autre item")
    return frictions


def preview_improve_estimate(intent: Dict) -> Dict:
    """Construit un PREVIEW de l'amélioration d'une soumission existante."""
    number = intent.get('estimate_number')
    if not number:
        return {
            'ok': False,
            'message': "Aucun numéro de soumission identifié. Précise : « améliore la soumission #11929 »."
        }

    est = read_estimate(number)
    if not est:
        return {
            'ok': False,
            'message': f"Soumission #{number} introuvable dans Gazelle."
        }

    if est.get('isArchived'):
        return {
            'ok': False,
            'message': f"Soumission #{number} est archivée. Je ne modifie pas les soumissions archivées."
        }

    contact = (est.get('client') or {}).get('defaultContact') or {}
    piano = est.get('piano') or {}
    frictions = detect_frictions(est)

    return {
        'ok': True,
        'preview': {
            'action_type': 'estimate.improve',
            'estimate_number': number,
            'estimate_id': est.get('id'),
            'client_name': f"{contact.get('firstName','')} {contact.get('lastName','')}".strip(),
            'piano_desc': f"{piano.get('make','')} {piano.get('model','')} {piano.get('year','')}".strip(),
            'current_total': (est.get('recommendedTierTotal') or 0) / 100,
            'frictions_detected': frictions,
            'frictions_count': len(frictions),
        },
        'message': (
            f"Soumission #{number} de {contact.get('firstName','')} {contact.get('lastName','')} "
            f"({piano.get('make','')} {piano.get('model','')}) — "
            f"{len(frictions)} friction(s) détectée(s). "
            f"⚠️ MVP : l'amélioration concrète nécessite de définir les changements à appliquer. "
            f"Confirme pour qu'Allan finalise."
        ),
    }
