#!/usr/bin/env python3
"""
Backfill complet de toutes les timeline entries depuis Gazelle vers Supabase.

USAGE (sur le serveur Render ou en local avec les bonnes env vars):
    python scripts/backfill_timeline_full.py

Ce script:
1. Récupère TOUTES les timeline entries de Gazelle (sans filtre de date)
2. Les insère dans Supabase (upsert sur external_id, pas de doublons)
3. Affiche la progression

Variables d'environnement requises:
    GAZELLE_CLIENT_ID, GAZELLE_CLIENT_SECRET (OAuth2 Gazelle)
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_ANON_KEY)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync


def main():
    print("=" * 60)
    print("BACKFILL COMPLET — Timeline entries Gazelle → Supabase")
    print("=" * 60)

    api_client = GazelleAPIClient()
    storage = SupabaseStorage()

    print("\n📡 Récupération de TOUTES les timeline entries depuis Gazelle...")
    print("   (sans filtre de date — historique complet)")

    all_entries = api_client.get_timeline_entries(since_date=None, limit=None)
    print(f"\n📥 {len(all_entries)} timeline entries récupérées au total")

    if not all_entries:
        print("❌ Aucune entrée — vérifiez les credentials Gazelle")
        return

    # Trier par date pour voir la plage
    dates = []
    for e in all_entries:
        occ = e.get('occurredAt', '')
        if occ and len(str(occ)) >= 10:
            dates.append(str(occ)[:10])
    if dates:
        dates.sort()
        print(f"   📅 Plage: {dates[0]} → {dates[-1]}")
        print(f"   📊 {len(set(dates))} jours distincts")

    # Utiliser le sync manager pour faire l'upsert
    sync = GazelleToSupabaseSync(api_client=api_client, storage=storage)

    print(f"\n💾 Upsert dans Supabase ({len(all_entries)} entrées)...")

    synced = 0
    errors = 0
    batch_size = 50

    for i in range(0, len(all_entries), batch_size):
        batch = all_entries[i:i + batch_size]
        for entry_data in batch:
            try:
                from core.timezone_utils import (
                    parse_gazelle_datetime, format_for_supabase
                )
                import requests as http_requests

                external_id = entry_data.get('id', '')
                occurred_at_raw = entry_data.get('occurredAt')
                occurred_at_utc = None

                if occurred_at_raw:
                    dt_parsed = parse_gazelle_datetime(occurred_at_raw)
                    if dt_parsed:
                        occurred_at_utc = format_for_supabase(dt_parsed)

                client_node = entry_data.get('client') or {}
                piano_node = entry_data.get('piano') or {}
                invoice_node = entry_data.get('invoice') or {}
                estimate_node = entry_data.get('estimate') or {}
                user_node = entry_data.get('user') or {}

                record = {
                    'external_id': external_id,
                    'client_id': client_node.get('id') if isinstance(client_node, dict) else None,
                    'piano_id': piano_node.get('id') if isinstance(piano_node, dict) else None,
                    'invoice_id': invoice_node.get('id') if isinstance(invoice_node, dict) else None,
                    'estimate_id': estimate_node.get('id') if isinstance(estimate_node, dict) else None,
                    'user_id': user_node.get('id') if isinstance(user_node, dict) else None,
                    'entry_type': entry_data.get('type', ''),
                    'title': (entry_data.get('summary') or '')[:500],
                    'description': (entry_data.get('comment') or '')[:2000],
                    'occurred_at': occurred_at_utc,
                }

                # Upsert via REST
                url = f"{storage.api_url}/gazelle_timeline_entries"
                headers = storage._get_headers()
                headers['Prefer'] = 'resolution=merge-duplicates'
                resp = http_requests.post(url, headers=headers, json=record)

                if resp.status_code in (200, 201):
                    synced += 1
                elif resp.status_code == 409:
                    synced += 1  # Already exists, that's fine
                else:
                    errors += 1
                    if errors <= 5:
                        print(f"   ⚠️  Erreur {resp.status_code}: {resp.text[:100]}")

            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ❌ {e}")

        pct = min(100, int((i + len(batch)) / len(all_entries) * 100))
        print(f"   [{pct:3d}%] {synced} insérés, {errors} erreurs", end='\r')

    print(f"\n\n✅ Backfill terminé!")
    print(f"   Insérés/mis à jour: {synced}")
    print(f"   Erreurs: {errors}")
    print(f"   Total traité: {synced + errors}")


if __name__ == '__main__':
    main()
