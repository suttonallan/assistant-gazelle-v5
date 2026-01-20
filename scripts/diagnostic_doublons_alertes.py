#!/usr/bin/env python3
"""
Diagnostic approfondi des doublons dans Alertes Maintenance.
"""

from modules.reports.service_reports import ServiceReports
from core.supabase_storage import SupabaseStorage
from supabase import create_client

def main():
    print("🔍 DIAGNOSTIC APPROFONDI DES DOUBLONS\n")
    print("="*70)
    
    service = ServiceReports()
    storage = SupabaseStorage()
    supabase = create_client(storage.supabase_url, storage.supabase_key)
    
    # Récupérer TOUTES les timeline entries
    print("\n📥 Récupération timeline entries...")
    all_entries = []
    offset = 0
    page_size = 1000
    
    while True:
        result = supabase.table('gazelle_timeline_entries').select('''
            external_id,
            description,
            title,
            entry_type,
            occurred_at,
            piano_id,
            piano:gazelle_pianos(
                client_external_id,
                make
            )
        ''') \
        .in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT']) \
        .order('occurred_at', desc=True) \
        .range(offset, offset + page_size - 1) \
        .execute()
        
        batch = result.data or []
        if not batch:
            break
        
        all_entries.extend(batch)
        print(f"   Page {offset//page_size + 1}: {len(batch)} entrées (total: {len(all_entries)})")
        
        if len(batch) < page_size:
            break
        
        offset += page_size
    
    print(f"\n✅ Total récupéré: {len(all_entries)} entrées\n")
    
    # Récupérer clients map
    clients_result = supabase.table('gazelle_clients').select('external_id,company_name').execute()
    clients_map = {c['external_id']: c['company_name'] for c in clients_result.data if c.get('external_id')}
    
    # Construire les lignes avec diagnostic
    print("🏗️  Construction des lignes...\n")
    rows_by_tab = service._build_rows_from_timeline(all_entries, clients_map)
    
    # Analyser Alertes Maintenance
    alert_rows = rows_by_tab.get("Alertes Maintenance", [])
    print(f"📊 Alertes Maintenance: {len(alert_rows)} lignes construites\n")
    
    # Créer signatures et détecter doublons
    signatures = {}
    for i, row in enumerate(alert_rows):
        date = row[0]
        desc = row[2][:100]
        sig = f"{date}|||{desc}"
        if sig not in signatures:
            signatures[sig] = {
                'indices': [],
                'rows': []
            }
        signatures[sig]['indices'].append(i)
        signatures[sig]['rows'].append(row)
    
    # Identifier doublons
    duplicates = {sig: data for sig, data in signatures.items() if len(data['indices']) > 1}
    
    print(f"🔍 Analyse:")
    print(f"   Lignes uniques: {len(signatures)}")
    print(f"   Lignes dupliquées: {len(duplicates)}")
    print(f"   Total lignes: {len(alert_rows)}\n")
    
    if duplicates:
        print(f"❌ {len(duplicates)} alertes sont dupliquées AVANT insertion!\n")
        print("="*70)
        print("EXEMPLES DE DOUBLONS:\n")
        
        for i, (sig, data) in enumerate(list(duplicates.items())[:5]):
            date, desc = sig.split('|||')
            print(f"{i+1}. Date: {date}")
            print(f"   Description: {desc[:60]}...")
            print(f"   Apparaît {len(data['indices'])} fois aux indices: {data['indices']}")
            
            # Comparer les lignes complètes
            rows = data['rows']
            print(f"   Lignes identiques? {all(row == rows[0] for row in rows)}")
            
            if not all(row == rows[0] for row in rows):
                print("   ⚠️  Les lignes sont DIFFÉRENTES:")
                for j, row in enumerate(rows):
                    print(f"      Ligne {j+1}: Client={row[3][:30]}, Technicien={row[10]}")
            print()
        
        # Chercher pattern
        print("="*70)
        print("ANALYSE DES PATTERNS:\n")
        
        # Est-ce que toutes les doublons ont le même client?
        clients_in_dupes = set()
        for sig, data in duplicates.items():
            for row in data['rows']:
                clients_in_dupes.add(row[3])  # NomClient
        
        print(f"Clients affectés: {clients_in_dupes}")
        
    else:
        print("✅ Aucun doublon détecté!")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
