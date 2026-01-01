#!/usr/bin/env python3
"""Import complet des clients Gazelle → Supabase"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from supabase import create_client

def main():
    print('='*80)
    print('🔄 IMPORT CLIENTS GAZELLE → SUPABASE')
    print('='*80)
    
    api_client = GazelleAPIClient()
    storage = SupabaseStorage()
    supabase = create_client(storage.supabase_url, storage.supabase_key)
    
    print('\n📊 Récupération des clients...')
    clients = api_client.get_clients(limit=None)
    print(f'✅ {len(clients)} clients récupérés')
    
    print('\n🔧 Préparation des données...')
    batch = []
    for client in clients:
        batch.append({
            'external_id': client.get('id'),
            'company_name': client.get('companyName'),
            'email': client.get('email'),
            'phone': client.get('phone'),
            'city': client.get('city'),
            'postal_code': client.get('postalCode'),
            'status': client.get('status'),
            'tags': client.get('tags', []),
            'created_at': client.get('createdAt'),
            'updated_at': client.get('updatedAt')
        })
    
    print(f'\n💾 Insertion de {len(batch)} clients...')
    supabase.table('gazelle_clients').upsert(batch, on_conflict='external_id').execute()
    print(f'✅ Import terminé!')

if __name__ == '__main__':
    main()
