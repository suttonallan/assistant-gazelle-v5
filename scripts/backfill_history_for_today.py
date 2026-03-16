#!/usr/bin/env python3
"""
BACKFILL TIMELINE CIBLÉ — Clients des rendez-vous à venir.

Récupère l'historique COMPLET (toutes années) de chaque client qui a un RV
dans les prochains jours, puis UPSERT dans gazelle_timeline_entries.
Skip intelligent : les clients déjà backfillés ne sont pas re-traités.

Usage:
    # Prochains 7 jours (défaut)
    python3 scripts/backfill_history_for_today.py

    # Un seul client (par nom partiel)
    python3 scripts/backfill_history_for_today.py --client "Blouin"

    # Dry-run (affiche sans écrire)
    python3 scripts/backfill_history_for_today.py --dry-run

    # Date spécifique (un seul jour)
    python3 scripts/backfill_history_for_today.py --date 2026-03-17

    # Nombre de jours à couvrir
    python3 scripts/backfill_history_for_today.py --days 14

    # Forcer le re-backfill même si déjà fait
    python3 scripts/backfill_history_for_today.py --force
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from core.timezone_utils import parse_gazelle_datetime, format_for_supabase


# Rate-limiting: pause entre chaque page GraphQL (évite le 429)
RATE_LIMIT_DELAY = 0.5  # secondes


def get_clients_for_date_range(storage: SupabaseStorage,
                                start_date: str, end_date: str) -> dict:
    """Récupère les client_ids uniques des RV sur une plage de dates.
    Returns: {client_id: title}"""
    url = (
        f"{storage.api_url}/gazelle_appointments?"
        f"appointment_date=gte.{start_date}"
        f"&appointment_date=lte.{end_date}"
        f"&select=client_external_id,title"
    )
    resp = requests.get(url, headers=storage._get_headers(), timeout=10)
    if resp.status_code != 200:
        print(f"  Erreur recuperation RV: {resp.status_code}")
        return {}

    seen = {}
    for appt in resp.json():
        cid = appt.get('client_external_id')
        if cid and cid not in seen:
            seen[cid] = appt.get('title', '')
    return seen


def get_client_info(storage: SupabaseStorage, client_id: str) -> dict:
    """Récupère nom + created_at du client depuis Supabase."""
    url = (
        f"{storage.api_url}/gazelle_clients?"
        f"external_id=eq.{client_id}"
        f"&select=first_name,last_name,company_name,created_at"
    )
    resp = requests.get(url, headers=storage._get_headers(), timeout=10)
    if resp.status_code == 200 and resp.json():
        c = resp.json()[0]
        name = (
            c.get('company_name')
            or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            or client_id
        )
        return {'name': name, 'created_at': c.get('created_at', '')}
    return {'name': client_id, 'created_at': ''}


def client_needs_backfill(storage: SupabaseStorage, client_id: str,
                           client_created_at: str) -> bool:
    """Détermine si un client a besoin d'un backfill.

    Un client est considéré DÉJÀ backfillé si sa plus ancienne entrée
    dans Supabase est plus vieille que la fenêtre de sync quotidienne
    (30 jours). La sync automatique ne couvre que les 30 derniers jours,
    donc toute donnée plus ancienne a forcément été importée par un
    backfill précédent.

    Retourne True si le backfill est nécessaire.
    """
    # Récupérer la plus ancienne entrée timeline
    url = (
        f"{storage.api_url}/gazelle_timeline_entries?"
        f"client_id=eq.{client_id}"
        f"&select=occurred_at"
        f"&order=occurred_at.asc"
        f"&limit=1"
    )
    resp = requests.get(url, headers=storage._get_headers(), timeout=10)

    if resp.status_code != 200 or not resp.json():
        # Aucune entrée → backfill nécessaire
        return True

    oldest_str = resp.json()[0].get('occurred_at', '')[:10]
    if not oldest_str:
        return True

    try:
        oldest_date = datetime.strptime(oldest_str, '%Y-%m-%d').date()
        cutoff = (datetime.now() - timedelta(days=45)).date()

        # Si la plus ancienne entrée est plus vieille que 45 jours,
        # c'est qu'un backfill a déjà eu lieu (la sync quotidienne
        # ne couvre que 30 jours). Marge de 45j pour sécurité.
        if oldest_date < cutoff:
            return False

        return True

    except ValueError:
        return True


def filter_by_client_name(clients: dict, storage: SupabaseStorage,
                           name_filter: str) -> dict:
    """Filtre la liste de clients par nom partiel (case-insensitive)."""
    filtered = {}
    name_lower = name_filter.lower()
    for cid, title in clients.items():
        info = get_client_info(storage, cid)
        if name_lower in info['name'].lower() or name_lower in title.lower():
            filtered[cid] = title
    return filtered


def backfill_client_timeline(api_client: GazelleAPIClient,
                              storage: SupabaseStorage,
                              client_id: str, client_name: str,
                              dry_run: bool = False) -> dict:
    """Récupère TOUTE la timeline d'un client via Gazelle et UPSERT dans Supabase.

    Returns:
        {'synced': int, 'skipped': int, 'errors': int}
    """
    query = """
    query GetAllEntriesForClient($clientId: String!, $cursor: String) {
        allTimelineEntries(clientId: $clientId, first: 100, after: $cursor) {
            edges {
                node {
                    id
                    occurredAt
                    type
                    summary
                    comment
                    client { id }
                    piano { id }
                    invoice { id }
                    estimate { id }
                    user { id }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """

    synced = 0
    skipped = 0
    errors = 0
    cursor = None
    page = 0
    all_entries = []

    while True:
        page += 1
        variables = {"clientId": client_id}
        if cursor:
            variables["cursor"] = cursor

        try:
            result = api_client._execute_query(query, variables)
            data = result.get('data', {}).get('allTimelineEntries', {})
            edges = data.get('edges', [])
            page_info = data.get('pageInfo', {})

            if not edges:
                break

            for edge in edges:
                entry = edge.get('node', {})
                all_entries.append(entry)

            print(f"   Page {page}: {len(edges)} entrees (total: {len(all_entries)})")

            if not page_info.get('hasNextPage'):
                break

            cursor = page_info.get('endCursor')
            time.sleep(RATE_LIMIT_DELAY)

        except Exception as e:
            print(f"   Erreur page {page}: {e}")
            break

    if not all_entries:
        print(f"   Aucune entree trouvee dans Gazelle")
        return {'synced': 0, 'skipped': 0, 'errors': 0}

    # Trouver la plus ancienne entrée
    oldest = None
    for entry in all_entries:
        occ = entry.get('occurredAt', '')
        if occ and (oldest is None or occ < oldest):
            oldest = occ

    print(f"   {len(all_entries)} entrees "
          f"(plus ancienne: {oldest[:10] if oldest else '?'})")

    if dry_run:
        print(f"   DRY-RUN — aucune ecriture")
        return {'synced': len(all_entries), 'skipped': 0, 'errors': 0}

    # UPSERT dans Supabase
    for entry in all_entries:
        try:
            external_id = entry.get('id')
            if not external_id:
                skipped += 1
                continue

            # Parser occurred_at
            occurred_at_raw = entry.get('occurredAt')
            occurred_at_utc = None
            if occurred_at_raw:
                try:
                    dt = parse_gazelle_datetime(occurred_at_raw)
                    if dt:
                        occurred_at_utc = format_for_supabase(dt)
                except Exception:
                    # Fallback: format brut
                    try:
                        dt = datetime.fromisoformat(
                            occurred_at_raw.replace('Z', '+00:00'))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        occurred_at_utc = dt.isoformat()
                    except Exception:
                        occurred_at_utc = occurred_at_raw

            # Extraire les IDs relationnels
            client_obj = entry.get('client', {})
            piano_obj = entry.get('piano', {})
            invoice_obj = entry.get('invoice', {})
            estimate_obj = entry.get('estimate', {})
            user_obj = entry.get('user', {})

            entry_type = entry.get('type', 'UNKNOWN')
            title = (entry.get('summary') or '').strip()
            description = (entry.get('comment') or '').strip()

            record = {
                'external_id': external_id,
                'client_id': client_obj.get('id') if client_obj else None,
                'piano_id': piano_obj.get('id') if piano_obj else None,
                'invoice_id': invoice_obj.get('id') if invoice_obj else None,
                'estimate_id': estimate_obj.get('id') if estimate_obj else None,
                'user_id': user_obj.get('id') if user_obj else None,
                'occurred_at': occurred_at_utc,
                'entry_type': entry_type,
            }

            # Protection: ne pas écraser avec des valeurs vides
            if title:
                record['title'] = title
            if description:
                record['description'] = description

            url = (f"{storage.api_url}/gazelle_timeline_entries"
                   f"?on_conflict=external_id")
            headers = storage._get_headers()
            headers['Prefer'] = 'resolution=merge-duplicates'

            resp = requests.post(url, headers=headers, json=record)

            if resp.status_code in [200, 201]:
                synced += 1
            elif resp.status_code == 409 and 'user_id' in resp.text:
                # FK violation sur user_id — réessayer sans user_id
                record.pop('user_id', None)
                resp2 = requests.post(url, headers=headers, json=record)
                if resp2.status_code in [200, 201]:
                    synced += 1
                else:
                    errors += 1
            else:
                errors += 1
                if errors <= 3:
                    print(f"   Erreur UPSERT {external_id}: "
                          f"{resp.status_code} - {resp.text[:100]}")

        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"   Exception: {str(e)[:100]}")

    return {'synced': synced, 'skipped': skipped, 'errors': errors}


def verify_client_since(storage: SupabaseStorage, client_id: str) -> str:
    """Vérifie la plus ancienne entrée timeline pour un client."""
    url = (
        f"{storage.api_url}/gazelle_timeline_entries?"
        f"client_id=eq.{client_id}"
        f"&select=occurred_at"
        f"&order=occurred_at.asc"
        f"&limit=1"
    )
    resp = requests.get(url, headers=storage._get_headers(), timeout=10)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0].get('occurred_at', '')[:10]
    return "(aucune donnee)"


def main():
    parser = argparse.ArgumentParser(
        description="Backfill timeline cible — clients des prochains jours")
    parser.add_argument('--date', type=str, default=None,
                        help='Date cible unique (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7,
                        help='Nombre de jours a couvrir (defaut: 7)')
    parser.add_argument('--client', type=str, default=None,
                        help='Filtre par nom de client (partiel)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Affiche sans ecrire dans Supabase')
    parser.add_argument('--force', action='store_true',
                        help='Forcer le re-backfill meme si deja fait')
    args = parser.parse_args()

    storage = SupabaseStorage()
    api_client = GazelleAPIClient()

    # Déterminer la plage de dates
    if args.date:
        start_date = args.date
        end_date = args.date
        label = start_date
    else:
        start = datetime.now()
        end = start + timedelta(days=args.days - 1)
        start_date = start.strftime('%Y-%m-%d')
        end_date = end.strftime('%Y-%m-%d')
        label = f"{start_date} -> {end_date} ({args.days} jours)"

    print(f"\n{'='*70}")
    print(f"BACKFILL TIMELINE CIBLE — {label}")
    print(f"{'='*70}\n")

    # 1. Récupérer tous les clients uniques sur la plage
    clients = get_clients_for_date_range(storage, start_date, end_date)
    if not clients:
        print("Aucun rendez-vous trouve pour cette periode.")
        return

    print(f"{len(clients)} clients uniques avec RV sur la periode\n")

    # 2. Filtrer par nom si demandé
    if args.client:
        clients = filter_by_client_name(clients, storage, args.client)
        if not clients:
            print(f"Aucun client trouve contenant \"{args.client}\"")
            return
        print(f"Filtre: {len(clients)} client(s) correspondant "
              f"a \"{args.client}\"\n")

    # 3. Backfill chaque client (avec skip intelligent)
    total_synced = 0
    total_errors = 0
    total_skipped_clients = 0

    client_list = list(clients.items())
    for i, (cid, title) in enumerate(client_list, 1):
        info = get_client_info(storage, cid)
        client_name = info['name']
        created_at = info['created_at']

        # Skip intelligent : vérifier si déjà backfillé
        if not args.force and not client_needs_backfill(storage, cid, created_at):
            print(f"[{i}/{len(client_list)}] {client_name} — deja backfille, skip")
            total_skipped_clients += 1
            continue

        print(f"\n{'_'*50}")
        print(f"[{i}/{len(client_list)}] {client_name} ({cid})")
        print(f"{'_'*50}")

        before = verify_client_since(storage, cid)
        print(f"   Plus ancienne entree AVANT: {before}")

        result = backfill_client_timeline(
            api_client, storage, cid, client_name,
            dry_run=args.dry_run
        )

        total_synced += result['synced']
        total_errors += result['errors']

        if not args.dry_run:
            after = verify_client_since(storage, cid)
            if after != before:
                print(f"   CORRIGE! {before} -> {after}")
            else:
                print(f"   Apres: {after} (inchange)")

        # Rate limit entre clients
        if i < len(client_list):
            time.sleep(1)

    # 4. Résumé
    print(f"\n{'='*70}")
    print(f"RESUME BACKFILL:")
    print(f"   Clients sur la periode: {len(clients)}")
    print(f"   Deja backfilles (skip): {total_skipped_clients}")
    print(f"   Clients traites: {len(clients) - total_skipped_clients}")
    print(f"   Entrees synchronisees: {total_synced}")
    print(f"   Erreurs: {total_errors}")
    if args.dry_run:
        print(f"   MODE DRY-RUN — aucune ecriture effectuee")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
