#!/usr/bin/env python3
"""
Script de récupération historique année par année
Robuste, par batch, avec gestion d'erreurs isolées
"""

import sys
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage


class HistoryRecovery:
    def __init__(self):
        print("🔬 Initialisation History Recovery...")
        self.gazelle = GazelleAPIClient()
        self.supabase = SupabaseStorage()
        
        # Vérifier que le client Supabase est bien initialisé
        if not self.supabase.client:
            raise ValueError("❌ Client Supabase non initialisé. Installez 'supabase-py': pip install supabase")
        
        print("✅ History Recovery initialisé\n")
        
    def _map_entry_type(self, gazelle_type: str) -> str:
        """
        Mappe les types Gazelle vers les types valides de la contrainte Supabase RÉELLE.
        
        Contrainte SQL ACTUELLE accepte:
        - APPOINTMENT, CONTACT_EMAIL, NOTE, APPOINTMENT_COMPLETION,
        - SYSTEM_NOTIFICATION, SERVICE_ENTRY_MANUAL, PIANO_MEASUREMENT, ERROR_MESSAGE
        
        ⚠️ INVOICE_PAYMENT n'est PAS accepté dans la contrainte actuelle
        """
        type_mapping = {
            # Types valides (testés contre Supabase)
            'APPOINTMENT': 'APPOINTMENT',
            'CONTACT_EMAIL': 'CONTACT_EMAIL',
            'NOTE': 'NOTE',
            'APPOINTMENT_COMPLETION': 'APPOINTMENT_COMPLETION',
            'SYSTEM_NOTIFICATION': 'SYSTEM_NOTIFICATION',
            'SERVICE_ENTRY_MANUAL': 'SERVICE_ENTRY_MANUAL',
            'PIANO_MEASUREMENT': 'PIANO_MEASUREMENT',
            'ERROR_MESSAGE': 'ERROR_MESSAGE',
            
            # Mapping des types automatisés
            'CONTACT_EMAIL_AUTOMATED': 'CONTACT_EMAIL',
            'SERVICE_ENTRY_AUTOMATED': 'SERVICE_ENTRY_MANUAL',
            'SYSTEM_MESSAGE': 'SYSTEM_NOTIFICATION',
            
            # Mapping des types factures/soumissions → NOTE (INVOICE_PAYMENT rejeté)
            'INVOICE': 'NOTE',
            'INVOICE_PAYMENT': 'NOTE',
            'INVOICE_LOG': 'NOTE',
            'ESTIMATE': 'NOTE',
            'ESTIMATE_LOG': 'NOTE',
            
            # Type "service" en minuscules
            'service': 'SERVICE_ENTRY_MANUAL',
        }
        
        return type_mapping.get(gazelle_type, 'NOTE')  # Défaut: NOTE
    
    def extract_measurements(self, text: str) -> Dict[str, Optional[float]]:
        """Extrait humidité (%) et fréquence (Hz) du texte."""
        if not text:
            return {}
        
        measurements = {}
        
        # Humidité : 45%, 45 %
        humidity_match = re.search(r'(\d+)\s*%', text)
        if humidity_match:
            measurements['humidity'] = float(humidity_match.group(1))
        
        # Fréquence : 440Hz, 440 Hz
        freq_match = re.search(r'(\d+)\s*Hz', text, re.IGNORECASE)
        if freq_match:
            measurements['frequency'] = float(freq_match.group(1))
        
        # Température : 21°, 21 °C
        temp_match = re.search(r'(\d+)\s*°', text)
        if temp_match:
            measurements['temperature'] = float(temp_match.group(1))
        
        return measurements
    
    def import_year(self, year: int) -> Dict[str, int]:
        """Importe toutes les entrées pour une année donnée."""
        print(f"\n{'='*70}")
        print(f"📅 ANNÉE {year}")
        print(f"{'='*70}")
        
        # Dates de début et fin pour l'année
        start_date = f"{year}-01-01T00:00:00Z"
        end_date = f"{year}-12-31T23:59:59Z"
        
        stats = {
            'fetched': 0,
            'success': 0,
            'errors': 0,
            'batches': 0
        }
        
        # 1. Récupération depuis Gazelle (depuis le début de l'année)
        print(f"📥 Récupération des entrées depuis Gazelle...")
        print(f"   🔍 Période: {start_date} → {end_date}")
        print(f"   ⏳ Pagination en cours (100 entrées/page)...\n")

        # Récupérer toutes les entrées depuis le début de l'année
        all_timeline_entries = self.gazelle.get_timeline_entries(limit=None, since_date=start_date)
        
        # Filtrer pour garder uniquement l'année cible
        all_entries = []
        for entry in all_timeline_entries:
            occurred_at = entry.get('occurredAt', '')
            if occurred_at.startswith(str(year)):
                all_entries.append(entry)
            # Arrêter si on est passé avant l'année
            elif occurred_at:
                try:
                    entry_year = int(occurred_at[:4])
                    if entry_year < year:
                        break
                except:
                    pass
        
        stats['fetched'] = len(all_entries)
        print(f"✅ {stats['fetched']} entrées récupérées pour {year}\n")
        
        if stats['fetched'] == 0:
            print(f"⚠️  Aucune entrée pour {year}")
            return stats
        
        # 2. Import par batch de 500
        batch_size = 500
        total_batches = (len(all_entries) + batch_size - 1) // batch_size
        
        print(f"💾 Import dans Supabase par batch de {batch_size}...")
        print(f"📦 Total de {total_batches} batches à traiter\n")

        for i in range(0, len(all_entries), batch_size):
            batch = all_entries[i:i+batch_size]
            stats['batches'] += 1

            # 🔍 LOG TEMPS RÉEL - Progression du batch
            current_entry = i
            total_entries = len(all_entries)
            progress_pct = (current_entry / total_entries) * 100 if total_entries > 0 else 0

            print(f"  📍 Batch {stats['batches']}/{total_batches} | Entrées {current_entry:,}-{min(current_entry+batch_size, total_entries):,}/{total_entries:,} ({progress_pct:.1f}%)")

            records = []
            for entry in batch:
                try:
                    # ID externe
                    gazelle_id = entry.get('id', '')
                    external_id = f"tme_{gazelle_id.replace('tme_', '')}" if gazelle_id else None
                    
                    if not external_id:
                        stats['errors'] += 1
                        continue
                    
                    # Type - Mapper vers types SQL valides
                    entry_type_raw = entry.get('type', 'note')
                    entry_type = self._map_entry_type(entry_type_raw)
                    
                    # Textes
                    summary = entry.get('summary', '')
                    comment = entry.get('comment', '')
                    
                    # Extraire mesures du comment si présent
                    measurements = {}
                    if comment and ('%' in comment or 'Hz' in comment.upper() or '°' in comment):
                        measurements = self.extract_measurements(comment)
                    
                    # Date
                    occurred_at = entry.get('occurredAt')
                    occurred_at_iso = None
                    if occurred_at:
                        try:
                            dt = datetime.fromisoformat(occurred_at.replace('Z', '+00:00'))
                            occurred_at_iso = dt.strftime('%Y-%m-%d %H:%M:%S%z')
                        except:
                            pass
                    
                    # Relations (avec gestion NULL si FK manquante)
                    client_obj = entry.get('client')
                    piano_obj = entry.get('piano')
                    user_obj = entry.get('user')
                    invoice_obj = entry.get('invoice')
                    estimate_obj = entry.get('estimate')
                    
                    record = {
                        'external_id': external_id,
                        'client_id': client_obj.get('id') if client_obj else None,
                        'piano_id': piano_obj.get('id') if piano_obj else None,
                        'user_id': user_obj.get('id') if user_obj else None,
                        'occurred_at': occurred_at_iso,
                        'entry_type': entry_type,  # TYPE TEL QUEL
                        'title': summary[:500] if summary else None,
                        'description': comment[:2000] if comment else None,
                    }
                    
                    # Ajouter invoice_id et estimate_id si présents
                    if invoice_obj:
                        record['invoice_id'] = invoice_obj.get('id')
                    if estimate_obj:
                        record['estimate_id'] = estimate_obj.get('id')
                    
                    # Ajouter mesures si extraites
                    if measurements:
                        record['metadata'] = measurements
                    
                    records.append(record)
                    
                except Exception as e:
                    stats['errors'] += 1
                    continue
            
            # UPSERT du batch
            if records:
                try:
                    # Debug: vérifier le premier record
                    if stats['batches'] == 1:
                        print(f"  🔍 Premier record keys: {list(records[0].keys())}")
                        print(f"  🔍 entry_type du premier: {records[0].get('entry_type')}")

                    # 🔍 LOG TEMPS RÉEL - Début UPSERT
                    print(f"     ⏳ UPSERT de {len(records)} records...", end='', flush=True)

                    result = self.supabase.client.table('gazelle_timeline_entries')\
                        .upsert(records, on_conflict='external_id')\
                        .execute()

                    if result.data:
                        batch_success = len(result.data)
                        stats['success'] += batch_success
                        # 🔍 LOG TEMPS RÉEL - Succès avec stats
                        print(f" ✅ {batch_success} entrées | Total: {stats['success']:,}/{stats['fetched']:,}")
                    else:
                        print(f" ⚠️  Aucune donnée retournée")
                        
                except Exception as e:
                    # Si le batch échoue à cause d'une FK, réessayer entrée par entrée avec user_id=NULL
                    # 🔍 LOG TEMPS RÉEL - Erreur batch
                    print(f" ❌ ÉCHOUÉ!")
                    if stats['batches'] == 1:
                        print(f"     ⚠️  Erreur détaillée: {type(e).__name__}: {str(e)[:300]}")
                        import traceback
                        print("     📋 Traceback:")
                        traceback.print_exc()

                    print(f"     🔄 Retry entrée par entrée ({len(records)} records)...", end='', flush=True)

                    retry_success = 0
                    retry_errors = 0

                    for record in records:
                        try:
                            # Retirer user_id pour éviter erreur FK
                            safe_record = record.copy()
                            safe_record['user_id'] = None

                            result = self.supabase.client.table('gazelle_timeline_entries')\
                                .upsert(safe_record, on_conflict='external_id')\
                                .execute()

                            if result.data:
                                stats['success'] += 1
                                retry_success += 1
                        except Exception as e2:
                            stats['errors'] += 1
                            retry_errors += 1

                    # 🔍 LOG TEMPS RÉEL - Résultat retry
                    print(f" ✅ {retry_success} succès, ❌ {retry_errors} erreurs")
        
        print(f"\n{'='*70}")
        print(f"✅ Année {year} : {stats['success']} entrées importées")
        print(f"❌ Erreurs : {stats['errors']}")
        print(f"{'='*70}")
        
        return stats
    
    def run(self, start_year: int = 2024, end_year: int = 2016):
        """Lance la récupération année par année."""
        print("\n" + "="*70)
        print("🚀 RÉCUPÉRATION HISTORIQUE ANNÉE PAR ANNÉE")
        print("="*70)
        
        total_stats = {
            'fetched': 0,
            'success': 0,
            'errors': 0
        }
        
        for year in range(start_year, end_year - 1, -1):
            year_stats = self.import_year(year)
            total_stats['fetched'] += year_stats['fetched']
            total_stats['success'] += year_stats['success']
            total_stats['errors'] += year_stats['errors']
        
        print("\n" + "="*70)
        print("📊 RÉSUMÉ GLOBAL")
        print("="*70)
        print(f"📥 Entrées récupérées : {total_stats['fetched']}")
        print(f"✅ Entrées importées  : {total_stats['success']}")
        print(f"❌ Erreurs           : {total_stats['errors']}")
        print("="*70 + "\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Récupération historique année par année')
    parser.add_argument('--start-year', type=int, default=2024,
                        help='Année de départ (défaut: 2024)')
    parser.add_argument('--end-year', type=int, default=2016,
                        help='Année de fin (défaut: 2016)')
    
    args = parser.parse_args()
    
    recovery = HistoryRecovery()
    recovery.run(start_year=args.start_year, end_year=args.end_year)
