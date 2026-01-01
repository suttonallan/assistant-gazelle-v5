#!/usr/bin/env python3
"""
Import des invoice items Gazelle → Supabase
Récupère les factures avec leurs line items et les stocke dans gazelle_invoice_items
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from supabase import create_client

def main():
    print('\n' + '='*80)
    print('🔄 IMPORT INVOICE ITEMS GAZELLE → SUPABASE')
    print('='*80)

    # Initialisation
    api_client = GazelleAPIClient()
    storage = SupabaseStorage()
    supabase = create_client(storage.supabase_url, storage.supabase_key)

    # Étape 1: Récupérer les factures avec leurs items
    print('\n📄 Récupération des factures depuis Gazelle...')
    invoices = api_client.get_invoices(limit=None)  # None = toutes les factures
    print(f'✅ {len(invoices)} factures récupérées')

    # Étape 2: Extraire et préparer les invoice items
    print('\n🔧 Extraction des line items...')
    all_items = []
    invoices_with_items = 0
    
    for invoice in invoices:
        invoice_id = invoice.get('id')
        items_connection = invoice.get('allInvoiceItems', {})
        items = items_connection.get('nodes', [])
        
        if items:
            invoices_with_items += 1
            
        for item in items:
            item_record = {
                'external_id': item.get('id'),
                'invoice_external_id': invoice_id,
                'description': item.get('description'),
                'type': item.get('type'),
                'sequence_number': item.get('sequenceNumber'),
                'quantity': item.get('quantity'),
                'amount': item.get('amount'),
                'sub_total': item.get('subTotal'),
                'tax_total': item.get('taxTotal'),
                'total': item.get('total'),
                'billable': item.get('billable'),
                'taxable': item.get('taxable')
            }
            all_items.append(item_record)
    
    print(f'✅ {len(all_items)} line items trouvés dans {invoices_with_items} factures')

    # Étape 3: Afficher quelques exemples
    print('\n📋 Exemples de line items (5 premiers):')
    print('-'*80)
    for i, item in enumerate(all_items[:5]):
        print(f"{i+1}. {item['external_id']}")
        print(f"   Type: {item['type']}")
        print(f"   Description: {item['description'][:60] if item['description'] else 'N/A'}")
        print(f"   Quantité: {item['quantity']} × {item['amount']}$ = {item['total']}$")
        print()

    # Étape 4: Insérer dans Supabase
    if all_items:
        print(f'\n💾 Insertion de {len(all_items)} items dans Supabase...')
        
        # Insérer par lots de 100
        batch_size = 100
        synced = 0
        errors = 0
        
        for i in range(0, len(all_items), batch_size):
            batch = all_items[i:i+batch_size]
            try:
                supabase.table('gazelle_invoice_items').upsert(
                    batch,
                    on_conflict='external_id'
                ).execute()
                synced += len(batch)
                print(f'  ✅ Lot {i//batch_size + 1}: {len(batch)} items insérés')
            except Exception as e:
                errors += len(batch)
                print(f'  ❌ Erreur lot {i//batch_size + 1}: {e}')
    
    # Résumé
    print('\n' + '='*80)
    print('📊 RÉSUMÉ DE L\'IMPORT')
    print('='*80)
    print(f'✅ Line items synchronisés: {synced}')
    print(f'❌ Erreurs: {errors}')
    print(f'📄 Factures avec items: {invoices_with_items}/{len(invoices)}')
    print('='*80)

    # Vérification statistiques
    print('\n📊 Statistiques par type:')
    result = supabase.table('gazelle_invoice_items').select('type').execute()
    if result.data:
        from collections import Counter
        types = Counter(item['type'] for item in result.data if item.get('type'))
        for item_type, count in types.most_common():
            print(f'  - {item_type}: {count} items')

if __name__ == '__main__':
    main()
