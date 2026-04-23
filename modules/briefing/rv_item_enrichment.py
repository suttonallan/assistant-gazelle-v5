#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enrichissement automatique des items de RV bookés en ligne.

Quand un client book en ligne via Gazelle self-scheduling, le RV est créé
avec le MSL client-facing court (ex: "Entretien et accord"). Ce n'est pas
ce qu'on veut sur la facture — on veut le template tech complet avec accord
440Hz, nettoyage détaillé, lecture température/humidité.

Ce module remplace les items client-facing par les templates tech, LA VEILLE
au soir pour les RV du lendemain. Le tech voit donc le template complet
quand il arrive sur place, et la facture générée depuis le RV a la bonne
description.

SÉCURITÉ :
- Read-modify-write : lit la liste complète, garde les items non-trigger, remplace
- Durée du RV préservée (input explicite)
- Skip si status CANCELLED ou notes non-vides
- Skip si pattern de trigger non reconnu
- Jamais de suppression de RV (updateEvent, pas deleteEvent)

Table de correspondance :
    Entretien seul             → mit_GL9kL9FS1mHifXY3
    Entretien + PLS            → mit_fyPj2I8R4VQtEkkm
    Premium seul               → mit_kccXg0ktam7Wyrwk
    Premium + PLS              → mit_fce43Ev1EfuKyHBW
    Extra-propre seul          → mit_lBzwoPaEj95bhDiD
    Extra-propre + PLS         → mit_Md6XzB0noTdOlKhF

Items toujours préservés :
    - Traitement de l'eau 227 ml (mit_6ocqn0yaeqNK0Vxk)
    - Tout item sans MSL ou avec un MSL non-trigger
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# MAPPING
# ═══════════════════════════════════════════════════════════

MSL_ENTRETIEN    = 'mit_N6BwvFPuAnai6zXh'
MSL_PREMIUM      = 'mit_tHdTbZYDos7SgJzX'
MSL_EXTRA_PROPRE = 'mit_HJ1snRRwAIRsjdyn'
MSL_PLS          = 'mit_W6d9sM3kyouKBY0c'

TRIGGER_MSLS = {MSL_ENTRETIEN, MSL_PREMIUM, MSL_EXTRA_PROPRE, MSL_PLS}

REPLACEMENT_RULES = {
    frozenset([MSL_ENTRETIEN]):                      'mit_GL9kL9FS1mHifXY3',
    frozenset([MSL_ENTRETIEN, MSL_PLS]):             'mit_fyPj2I8R4VQtEkkm',
    frozenset([MSL_PREMIUM]):                        'mit_kccXg0ktam7Wyrwk',
    frozenset([MSL_PREMIUM, MSL_PLS]):               'mit_fce43Ev1EfuKyHBW',
    frozenset([MSL_EXTRA_PROPRE]):                   'mit_lBzwoPaEj95bhDiD',
    frozenset([MSL_EXTRA_PROPRE, MSL_PLS]):          'mit_Md6XzB0noTdOlKhF',
}

# ═══════════════════════════════════════════════════════════
# FETCH
# ═══════════════════════════════════════════════════════════

FETCH_QUERY = """
query($start: CoreDate!, $end: CoreDate!) {
    allEventsBatched(first: 200, filters: {startOn: $start, endOn: $end}) {
        nodes {
            id title start duration notes type status
            client { id defaultContact { firstName lastName } }
            user { id }
            allServiceItems(first: 30) {
                nodes {
                    id name amount quantity duration type isTaxable isTuning
                    masterServiceItem { id }
                    piano { id }
                }
            }
        }
    }
}
"""

FETCH_MSL_LIST_QUERY = """
query {
    allMasterServiceItems {
        id name amount duration type isTaxable isTuning
    }
}
"""


def fetch_rvs_for_date(client, target_date: date) -> List[Dict]:
    """Fetch tous les RV APPOINTMENT actifs pour target_date."""
    start = target_date.strftime('%Y-%m-%d')
    end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
    result = client._execute_query(FETCH_QUERY, {'start': start, 'end': end})
    events = result.get('data', {}).get('allEventsBatched', {}).get('nodes', []) or []
    return [
        e for e in events
        if e.get('type') == 'APPOINTMENT' and e.get('status') != 'CANCELLED'
    ]


def fetch_msl_cache(client) -> Dict[str, Dict]:
    """Fetch all MSLs once and return a dict by id."""
    try:
        result = client._execute_query(FETCH_MSL_LIST_QUERY)
        items = result.get('data', {}).get('allMasterServiceItems', []) or []
        return {it['id']: it for it in items}
    except Exception as exc:
        logger.warning(f"Failed to fetch MSL cache: {exc}")
        return {}


# ═══════════════════════════════════════════════════════════
# DETECTION
# ═══════════════════════════════════════════════════════════

def detect_pattern(items: List[Dict]) -> Tuple[Optional[frozenset], List[Dict], List[Dict]]:
    """
    Retourne (pattern_key, trigger_items, preserved_items).
    pattern_key=None si aucune règle ne matche.
    """
    trigger_msls = set()
    trigger_items = []
    preserved_items = []

    for it in items:
        msl_id = (it.get('masterServiceItem') or {}).get('id')
        if msl_id and msl_id in TRIGGER_MSLS:
            trigger_msls.add(msl_id)
            trigger_items.append(it)
        else:
            preserved_items.append(it)

    pattern_key = frozenset(trigger_msls)
    if pattern_key not in REPLACEMENT_RULES:
        return None, trigger_items, preserved_items
    return pattern_key, trigger_items, preserved_items


# ═══════════════════════════════════════════════════════════
# BUILD UPDATE PAYLOAD
# ═══════════════════════════════════════════════════════════

def item_to_input(it: Dict) -> Dict:
    """Convertit un EventServiceItem lu en PrivateEventServiceItemInput pour le preserve."""
    msl_id = (it.get('masterServiceItem') or {}).get('id')
    piano_id = (it.get('piano') or {}).get('id')
    payload = {
        'name': it.get('name') or '',
        'amount': it.get('amount') or 0,
        'quantity': it.get('quantity') or 100,
        'duration': it.get('duration') or 0,
        'type': it.get('type') or 'LABOR_FIXED_RATE',
        'isTaxable': bool(it.get('isTaxable', True)),
        'isTuning': bool(it.get('isTuning', False)),
    }
    if msl_id:
        payload['masterServiceItemId'] = msl_id
    if piano_id:
        payload['pianoId'] = piano_id
    return payload


def detect_language(trigger_items: List[Dict], msl_cache: Dict[str, Dict]) -> str:
    """Détecte la langue des items originaux en comparant leur name à celui du MSL.
    Retourne 'en_US' ou 'fr_CA' (défaut fr_CA).
    """
    for it in trigger_items:
        orig_name = (it.get('name') or '').strip()
        msl_id = (it.get('masterServiceItem') or {}).get('id')
        if not msl_id:
            continue
        msl = msl_cache.get(msl_id) or {}
        msl_name = msl.get('name') or {}
        if isinstance(msl_name, dict):
            if orig_name and orig_name == (msl_name.get('en_US') or '').strip():
                return 'en_US'
            if orig_name and orig_name == (msl_name.get('fr_CA') or '').strip():
                return 'fr_CA'
    return 'fr_CA'  # défaut


def build_replacement_item(
    replacement_msl: Dict,
    trigger_items: List[Dict],
    language: str,
) -> Dict:
    """Construit le nouvel item à partir du MSL template + infos des items retirés."""
    # Durée = somme des durées des triggers retirés (préserve l'équilibre du RV)
    total_duration = sum((it.get('duration') or 0) for it in trigger_items)
    # Montant = montant du MSL (le prix standard du service)
    amount = replacement_msl.get('amount') or 0
    # Name dans la bonne langue
    name_i18n = replacement_msl.get('name') or {}
    name_str = ''
    if isinstance(name_i18n, dict):
        name_str = name_i18n.get(language) or name_i18n.get('fr_CA') or name_i18n.get('en_US') or ''
    else:
        name_str = str(name_i18n)

    # Piano : prend le piano du premier item trigger (probable lien principal)
    piano_id = None
    for it in trigger_items:
        pid = (it.get('piano') or {}).get('id')
        if pid:
            piano_id = pid
            break

    payload = {
        'masterServiceItemId': replacement_msl['id'],
        'name': name_str,
        'amount': amount,
        'quantity': 100,
        'duration': total_duration,
        'type': replacement_msl.get('type') or 'LABOR_FIXED_RATE',
        'isTaxable': bool(replacement_msl.get('isTaxable', True)),
        'isTuning': bool(replacement_msl.get('isTuning', False)),
    }
    if piano_id:
        payload['pianoId'] = piano_id
    return payload


# ═══════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════

UPDATE_QUERY = """
mutation($id: String!, $input: PrivateEventInput!) {
    updateEvent(id: $id, input: $input) {
        event {
            id title duration
            allServiceItems(first: 30) {
                nodes {
                    id name amount
                    masterServiceItem { id }
                }
            }
        }
        mutationErrors { messages }
    }
}
"""


def enrich_rv(client, rv: Dict, msl_cache: Dict[str, Dict], dry_run: bool = True) -> Dict:
    """
    Traite un RV. Retourne un dict de rapport.

    dry_run=True : n'appelle PAS updateEvent, retourne juste le plan.
    dry_run=False : applique la modification.
    """
    event_id = rv['id']
    client_obj = rv.get('client') or {}
    contact = client_obj.get('defaultContact') or {}
    client_name = f"{contact.get('firstName','')} {contact.get('lastName','')}".strip() or "?"
    duration = rv.get('duration', 0)
    items = (rv.get('allServiceItems') or {}).get('nodes', [])

    report = {
        'event_id': event_id,
        'client_name': client_name,
        'duration_min': duration,
        'action': 'SKIP',
        'reason': '',
    }

    # Safety 1 : skip si status CANCELLED déjà filtré en amont, mais re-check
    if rv.get('status') == 'CANCELLED':
        report['reason'] = 'RV CANCELLED'
        return report

    pattern_key, trigger_items, preserved_items = detect_pattern(items)
    if not pattern_key:
        report['reason'] = 'aucun pattern reconnu'
        return report

    replacement_msl_id = REPLACEMENT_RULES[pattern_key]
    replacement_msl = msl_cache.get(replacement_msl_id)
    if not replacement_msl:
        report['reason'] = f'MSL remplacement introuvable dans cache: {replacement_msl_id}'
        return report

    # Détection de langue basée sur les items originaux
    language = detect_language(trigger_items, msl_cache)

    # Construire la nouvelle liste d'items : preserved + replacement
    new_items = [item_to_input(it) for it in preserved_items]
    new_items.append(build_replacement_item(replacement_msl, trigger_items, language))

    report.update({
        'action': 'WOULD_MODIFY' if dry_run else 'MODIFIED',
        'pattern': sorted(pattern_key),
        'replacement_msl_id': replacement_msl_id,
        'removed_items': [
            {'msl_id': (it.get('masterServiceItem') or {}).get('id'), 'name': it.get('name')}
            for it in trigger_items
        ],
        'preserved_count': len(preserved_items),
        'new_items_count': len(new_items),
    })

    if dry_run:
        return report

    # LIVE : appliquer la modification
    update_input = {
        'duration': duration,  # Préserve la durée du RV explicitement
        'serviceItems': new_items,
    }
    try:
        result = client._execute_query(UPDATE_QUERY, {'id': event_id, 'input': update_input})
        data = result.get('data', {}).get('updateEvent', {}) or {}
        errors = data.get('mutationErrors') or []
        if errors:
            report['action'] = 'ERROR'
            report['error'] = json.dumps(errors, ensure_ascii=False)
            return report

        updated = data.get('event', {})
        updated_items = (updated.get('allServiceItems') or {}).get('nodes', [])
        report['verified_duration'] = updated.get('duration')
        report['verified_item_count'] = len(updated_items)
        report['verified_items'] = [
            {'msl_id': (it.get('masterServiceItem') or {}).get('id'), 'name': (it.get('name') or '')[:80]}
            for it in updated_items
        ]
        return report
    except Exception as exc:
        report['action'] = 'ERROR'
        report['error'] = str(exc)
        return report


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

def run_for_date(target_date: date, dry_run: bool = True) -> Dict:
    """Entry point — traite tous les RV de target_date."""
    from core.gazelle_api_client import GazelleAPIClient
    client = GazelleAPIClient()

    msl_cache = fetch_msl_cache(client)
    rvs = fetch_rvs_for_date(client, target_date)
    reports = [enrich_rv(client, rv, msl_cache, dry_run=dry_run) for rv in rvs]

    stats = {
        'date': target_date.isoformat(),
        'dry_run': dry_run,
        'total_rvs': len(rvs),
        'modified': sum(1 for r in reports if r['action'] in ('MODIFIED', 'WOULD_MODIFY')),
        'skipped': sum(1 for r in reports if r['action'] == 'SKIP'),
        'errors': sum(1 for r in reports if r['action'] == 'ERROR'),
        'reports': reports,
    }
    return stats


def run_tomorrow(dry_run: bool = False) -> Dict:
    """Entry point du scheduler : traite les RV de demain."""
    target = date.today() + timedelta(days=1)
    return run_for_date(target, dry_run=dry_run)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--date', type=str, default=None, help='YYYY-MM-DD (défaut = demain)')
    args = parser.parse_args()

    if args.date:
        target = date.fromisoformat(args.date)
    else:
        target = date.today() + timedelta(days=1)

    result = run_for_date(target, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
