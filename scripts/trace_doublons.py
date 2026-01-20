#!/usr/bin/env python3
"""
Trace exactement quand et comment les doublons sont ajoutés.
"""
import sys
sys.path.insert(0, '/Users/allansutton/Documents/assistant-gazelle-v5')

from modules.reports.service_reports import ServiceReports
from core.supabase_storage import SupabaseStorage
from supabase import create_client

# Monkey-patch pour tracer les ajouts
original_build = ServiceReports._build_rows_from_timeline

def traced_build(self, entries, clients_map):
    import pytz
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    MONTREAL_TZ = ZoneInfo("America/Montreal")
    
    rows_by_tab = {tab: [] for tab in ["UQAM", "Vincent", "Place des Arts"]}
    rows_by_tab["Alertes Maintenance"] = []
    
    # Tracer les ajouts
    addition_log = []
    
    # Fonction pour ajouter avec trace
    def traced_append(tab, row, source):
        sig = f"{row[0]}|||{row[2][:80]}"
        addition_log.append({
            'tab': tab,
            'source': source,
            'signature': sig,
            'client': row[3][:40],
            'desc': row[2][:60]
        })
        rows_by_tab[tab].append(row)
    
    # Séparer services et mesures
    services = []
    measurements = []
    
    for entry in entries:
        entry_type = entry.get("entry_type") or ""
        if entry_type == "SERVICE_ENTRY_MANUAL":
            services.append(entry)
        elif entry_type == "PIANO_MEASUREMENT":
            measurements.append(entry)
    
    print(f"📊 Services: {len(services)}, Measurements: {len(measurements)}\n")
    
    # Mesures groupées (code simplifié pour le traçage)
    measurements_by_piano_date = {}
    
    # Traiter les services
    for service in services:
        piano = service.get("piano") or {}
        entity_id = service.get("entity_id")
        client_id = piano.get("client_external_id") or entity_id
        client_name = clients_map.get(client_id, "Inconnu")
        
        description = service.get("title") or service.get("description") or ""
        date_raw = service.get("occurred_at") or service.get("entry_date", "")
        entry_date = self._to_montreal_date(date_raw)
        
        row = [
            entry_date,
            "Service",
            description,
            client_name,
            piano.get("make") or "",
            piano.get("model") or "",
            piano.get("serial_number") or "",
            piano.get("type") or "",
            str(piano.get("year") or ""),
            piano.get("location") or "",
            "",  # technicien simplifié
            ""   # mesure simplified
        ]
        
        # Categoriser
        tabs = self._categories_for_entry(client_name, description)
        
        for tab in tabs:
            traced_append(tab, row, f"SERVICE: {service.get('external_id')}")
    
    # Analyser les ajouts
    print("🔍 Analyse des ajouts:\n")
    
    # Compter par signature
    from collections import Counter
    signatures = Counter([log['signature'] for log in addition_log if log['tab'] == 'Alertes Maintenance'])
    
    duplicates = {sig: count for sig, count in signatures.items() if count > 1}
    
    if duplicates:
        print(f"❌ {len(duplicates)} signatures dupliquées dans les ajouts!\n")
        print("Exemples:")
        for i, (sig, count) in enumerate(list(duplicates.items())[:5]):
            print(f"\n{i+1}. Signature: {sig[:60]}...")
            print(f"   Ajoutée {count} fois:")
            
            # Trouver toutes les occurrences
            occurrences = [log for log in addition_log if log['signature'] == sig and log['tab'] == 'Alertes Maintenance']
            for occ in occurrences:
                print(f"      - Source: {occ['source']}")
                print(f"        Client: {occ['client']}")
    else:
        print("✅ Aucune signature dupliquée dans les ajouts!")
    
    return rows_by_tab

# Appliquer le monkey-patch
ServiceReports._build_rows_from_timeline = traced_build

# Tester
print("🔬 Test avec trace complète\n")
print("="*70 + "\n")

service = ServiceReports()
storage = SupabaseStorage()
supabase = create_client(storage.supabase_url, storage.supabase_key)

# Récupérer quelques entrées
result = supabase.table('gazelle_timeline_entries').select('''
    external_id,description,title,entry_date,occurred_at,entity_id,entity_type,event_type,entry_type,piano_id,user_id,
    piano:gazelle_pianos(make,model,serial_number,type,year,location,client_external_id),
    user:users(first_name,last_name)
''').in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT']).order('occurred_at', desc=True).limit(5000).execute()

entries = result.data

clients_result = supabase.table('gazelle_clients').select('external_id,company_name').execute()
clients_map = {c['external_id']: c['company_name'] for c in clients_result.data if c.get('external_id')}

rows_by_tab = service._build_rows_from_timeline(entries, clients_map)

print(f"\n📊 Résultats:")
for tab, rows in rows_by_tab.items():
    if rows:
        print(f"   {tab}: {len(rows)} lignes")
