#!/usr/bin/env python3
"""
smart_import_all_data.py - Import intelligent et massif Gazelle → Supabase

Triple Flux (GraphQL):
- allInvoices → gazelle_invoices
- allEstimates → gazelle_estimates  
- allTimelineEntries (depuis 2016) → gazelle_timeline_entries

Filtre Anti-Bruit Strict:
- Ignore Mailchimp, emails ouverts, création/suppression rendez-vous
- Garde seulement les entrées de haute valeur technique

Extraction de Mesures:
- Regex pour humidité (45%), température (23°), fréquence (440Hz)
- Stocke dans colonnes dédiées

Conservation de l'Existant:
- UPSERT pour éviter doublons
- Utilise GazelleAPIClient et SupabaseStorage
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage
from supabase import create_client


class SmartImport:
    """Import intelligent avec filtrage qualité."""
    
    # Patterns anti-bruit
    NOISE_PATTERNS = [
        r'Mailchimp',
        r'Email opened',
        r'Email delivered',
        r'Email sent',
        r'A créé un rendez-vous',
        r'Suppression d\'un rendez-vous',
        r'Appointment created',
        r'Appointment deleted',
        r'Email bounced',
        r'Email clicked',
    ]
    
    def __init__(self, dry_run: bool = False, delay: float = 0.5):
        """
        Initialise l'import.
        
        Args:
            dry_run: Si True, affiche sans écrire dans Supabase
            delay: Délai en secondes entre requêtes API (défaut: 0.5s)
        """
        print("🔬 Initialisation Smart Import...")
        self.dry_run = dry_run
        self.delay = delay
        self.stats = {
            'invoices': {'success': 0, 'errors': 0, 'filtered': 0},
            'estimates': {'success': 0, 'errors': 0, 'filtered': 0},
            'timeline': {'success': 0, 'errors': 0, 'filtered': 0, 'noise_filtered': 0}
        }
        
        if dry_run:
            print("⚠️  MODE DRY-RUN: Aucune écriture dans Supabase")
        
        print(f"⏱️  Délai entre requêtes: {delay}s")
        self.api_client = GazelleAPIClient()
        self.storage = SupabaseStorage(silent=True)
        self.supabase = create_client(self.storage.supabase_url, self.storage.supabase_key)
        print("✅ Smart Import initialisé")
    
    def is_valuable(self, entry: Dict[str, Any]) -> bool:
        """
        Filtre anti-bruit strict: détermine si une entrée est de haute valeur.
        
        Rejette:
        - Administratif (Mailchimp, emails ouverts)
        - Marketing (campagnes email)
        - Logistique basique (création/suppression rendez-vous sans contenu)
        """
        # Ignorer les entrées sans contenu
        comment = entry.get('comment', '') or ''
        summary = entry.get('summary', '') or ''
        combined_text = f"{summary} {comment}".strip().lower()
        
        if not combined_text:
            # Rendez-vous terminé sans commentaire = pas de valeur
            entry_type = entry.get('type', '').upper()
            if entry_type in ['APPOINTMENT', 'APPOINTMENT_COMPLETION']:
                return False
            return True  # Autres types sans texte peuvent être gardés
        
        # Vérifier patterns anti-bruit
        for pattern in self.NOISE_PATTERNS:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return False
        
        return True
    
    def _map_entry_type(self, gazelle_type: str) -> str:
        """
        Mappe les types Gazelle vers les types valides de la contrainte Supabase.
        
        Contrainte SQL accepte:
        - APPOINTMENT, CONTACT_EMAIL, NOTE, APPOINTMENT_COMPLETION,
        - SYSTEM_NOTIFICATION, SERVICE_ENTRY_MANUAL, PIANO_MEASUREMENT,
        - INVOICE_PAYMENT, ERROR_MESSAGE
        """
        type_mapping = {
            # Types déjà valides
            'APPOINTMENT': 'APPOINTMENT',
            'CONTACT_EMAIL': 'CONTACT_EMAIL',
            'NOTE': 'NOTE',
            'APPOINTMENT_COMPLETION': 'APPOINTMENT_COMPLETION',
            'SYSTEM_NOTIFICATION': 'SYSTEM_NOTIFICATION',
            'SERVICE_ENTRY_MANUAL': 'SERVICE_ENTRY_MANUAL',
            'PIANO_MEASUREMENT': 'PIANO_MEASUREMENT',
            'INVOICE_PAYMENT': 'INVOICE_PAYMENT',
            'ERROR_MESSAGE': 'ERROR_MESSAGE',
            
            # Mapping des types automatisés vers types valides
            'CONTACT_EMAIL_AUTOMATED': 'CONTACT_EMAIL',
            'SERVICE_ENTRY_AUTOMATED': 'SERVICE_ENTRY_MANUAL',
            'SYSTEM_MESSAGE': 'SYSTEM_NOTIFICATION',
            
            # Mapping des types factures/soumissions
            'INVOICE': 'INVOICE_PAYMENT',
            'INVOICE_LOG': 'NOTE',
            'ESTIMATE': 'NOTE',
            'ESTIMATE_LOG': 'NOTE',
        }
        
        return type_mapping.get(gazelle_type, 'NOTE')  # Défaut: NOTE
    
    def extract_measurements(self, text: str) -> Dict[str, Optional[float]]:
        """
        Extrait les mesures depuis le texte:
        - Humidité: 45%, humidité 45
        - Température: 23°, 23C, 23°C
        - Fréquence: 440Hz, 440 Hz
        """
        if not text:
            return {'humidity': None, 'temperature': None, 'frequency': None}
        
        measurements = {'humidity': None, 'temperature': None, 'frequency': None}
        text_lower = text.lower()
        
        # Humidité: 45%, humidité 45, RH 45%
        humidity_patterns = [
            r'humidit[ée].*?(\d+)\s*%',
            r'rh.*?(\d+)\s*%',
            r'(\d+)\s*%.*?humidit',
        ]
        for pattern in humidity_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    measurements['humidity'] = float(match.group(1))
                    break
                except:
                    pass
        
        # Température: 23°, 23C, 23°C, température 23
        temp_patterns = [
            r'temp[ée]rature.*?(\d+)',
            r'(\d+)\s*[°C]',
            r'(\d+)\s*celsius',
        ]
        for pattern in temp_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    temp = float(match.group(1))
                    # Si > 100, probablement Fahrenheit
                    if temp > 100:
                        temp = (temp - 32) * 5 / 9
                    measurements['temperature'] = temp
                    break
                except:
                    pass
        
        # Fréquence: 440Hz, 440 Hz, 440.5Hz
        freq_pattern = r'(\d+(?:\.\d+)?)\s*Hz'
        match = re.search(freq_pattern, text, re.IGNORECASE)
        if match:
            try:
                measurements['frequency'] = float(match.group(1))
            except:
                pass
        
        return measurements
    
    def import_invoices(self) -> Dict[str, int]:
        """Importe les factures (allInvoices) vers gazelle_invoices."""
        print("\n" + "="*70)
        print("📄 IMPORT FACTURES (allInvoices → gazelle_invoices)")
        if self.dry_run:
            print("⚠️  MODE DRY-RUN - Aucune écriture")
        print("="*70)
        
        try:
            invoices = self.api_client.get_invoices(limit=10000)
            print(f"✅ {len(invoices)} factures récupérées depuis Gazelle")
            
            for invoice in invoices:
                try:
                    invoice_id = invoice.get('id')
                    client_id = invoice.get('clientId')
                    
                    # Préparer record Supabase
                    record = {
                        'external_id': invoice_id,
                        'client_external_id': client_id,
                        'invoice_number': invoice.get('number'),
                        'invoice_date': invoice.get('invoiceDate'),
                        'status': invoice.get('status'),
                        'subtotal': invoice.get('subTotal'),
                        'total': invoice.get('total'),
                        'due_date': invoice.get('dueOn'),
                        'notes': invoice.get('notes'),
                        'metadata': invoice  # JSON complet pour référence
                    }
                    
                    # Nettoyer None
                    record = {k: v for k, v in record.items() if v is not None}
                    
                    if self.dry_run:
                        print(f"  [DRY-RUN] UPSERT: {invoice.get('number', invoice_id)}")
                        self.stats['invoices']['success'] += 1
                    else:
                        # UPSERT
                        result = self.supabase.table('gazelle_invoices')\
                            .upsert(record, on_conflict='external_id')\
                            .execute()
                        
                        if result.data:
                            print(f"  [INVOICES] OK: {invoice.get('number', invoice_id)}")
                            self.stats['invoices']['success'] += 1
                    
                except Exception as e:
                    print(f"  [INVOICES] ERREUR: {invoice.get('id', 'unknown')} - {e}")
                    self.stats['invoices']['errors'] += 1
                    # Continue - atomicité: une erreur ne bloque pas le reste
            
            return {'total': len(invoices), 'imported': self.stats['invoices']['success']}
            
        except Exception as e:
            print(f"❌ Erreur import factures: {e}")
            import traceback
            traceback.print_exc()
            return {'total': 0, 'imported': 0}
    
    def import_estimates(self) -> Dict[str, int]:
        """Importe les soumissions (allEstimates) vers gazelle_estimates."""
        print("\n" + "="*70)
        print("📋 IMPORT SOUMISSIONS (allEstimates → gazelle_estimates)")
        if self.dry_run:
            print("⚠️  MODE DRY-RUN - Aucune écriture")
        print("="*70)
        
        try:
            # Note: get_estimates() doit exister dans GazelleAPIClient
            # Si absent, créer la méthode ou utiliser query directe
            query = """
            query {
                allEstimates(first: 10000) {
                    nodes {
                        id
                        clientId
                        number
                        estimateDate
                        status
                        total
                        notes
                    }
                }
            }
            """
            
            time.sleep(self.delay)  # Pagination sécurisée
            result = self.api_client._execute_query(query)
            estimates = result.get('data', {}).get('allEstimates', {}).get('nodes', [])
            print(f"✅ {len(estimates)} soumissions récupérées depuis Gazelle")
            
            for estimate in estimates:
                try:
                    estimate_id = estimate.get('id')
                    client_id = estimate.get('clientId')
                    
                    record = {
                        'external_id': estimate_id,
                        'client_external_id': client_id,
                        'estimate_number': estimate.get('number'),
                        'estimate_date': estimate.get('estimateDate'),
                        'status': estimate.get('status'),
                        'total': estimate.get('total'),
                        'notes': estimate.get('notes'),
                        'metadata': estimate
                    }
                    
                    record = {k: v for k, v in record.items() if v is not None}
                    
                    if self.dry_run:
                        print(f"  [DRY-RUN] UPSERT: {estimate.get('number', estimate_id)}")
                        self.stats['estimates']['success'] += 1
                    else:
                        # UPSERT
                        result = self.supabase.table('gazelle_estimates')\
                            .upsert(record, on_conflict='external_id')\
                            .execute()
                        
                        if result.data:
                            print(f"  [ESTIMATES] OK: {estimate.get('number', estimate_id)}")
                            self.stats['estimates']['success'] += 1
                    
                except Exception as e:
                    print(f"  [ESTIMATES] ERREUR: {estimate.get('id', 'unknown')} - {e}")
                    self.stats['estimates']['errors'] += 1
                    # Continue - atomicité
            
            return {'total': len(estimates), 'imported': self.stats['estimates']['success']}
            
        except Exception as e:
            print(f"❌ Erreur import soumissions: {e}")
            import traceback
            traceback.print_exc()
            return {'total': 0, 'imported': 0}
    
    def import_timeline(self, since_date: str = None) -> Dict[str, int]:
        """
        Importe la timeline en mode FENÊTRE GLISSANTE (7 derniers jours par défaut).

        Applique le filtre anti-bruit strict et extraction de mesures.
        
        Args:
            since_date: Date de début (ISO format). Si None, utilise 7 jours en arrière.
        """
        # Mode fenêtre glissante: 7 derniers jours par défaut
        if since_date is None:
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(days=7)
            since_date = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
            print("\n" + "="*70)
            print(f"📝 IMPORT TIMELINE - MODE FENÊTRE GLISSANTE (7 derniers jours)")
            print("="*70)
        else:
            print("\n" + "="*70)
            print(f"📝 IMPORT TIMELINE (allTimelineEntries depuis {since_date})")
            print("="*70)
        
        try:
            # Récupérer toutes les entrées depuis 2016 avec pagination sécurisée
            # Note: get_timeline_entries pagine automatiquement, mais on ajoute un délai
            # pour les requêtes multiples si nécessaire
            entries = self.api_client.get_timeline_entries(limit=None, since_date=since_date)
            print(f"✅ {len(entries)} entrées timeline récupérées depuis Gazelle")
            
            # Filtre anti-bruit strict
            valuable_entries = []
            rejected_count = 0
            
            for entry in entries:
                if self.is_valuable(entry):
                    valuable_entries.append(entry)
                else:
                    rejected_count += 1
                    self.stats['timeline']['noise_filtered'] += 1
            
            print(f"📊 Filtre qualité: {len(valuable_entries)}/{len(entries)} entrées de haute valeur")
            print(f"   → {rejected_count} entrées rejetées (anti-bruit)")
            
            # Audit Mode: Résumé par client
            client_stats = defaultdict(int)
            for entry in valuable_entries:
                client = entry.get('client', {})
                client_id = client.get('id') if client else None
                if client_id:
                    client_stats[client_id] += 1
            
            if client_stats:
                print(f"\n📋 Répartition par client (entrées de haute valeur):")
                for client_id, count in list(client_stats.items())[:10]:
                    print(f"   {client_id}: {count} entrées")
                if len(client_stats) > 10:
                    print(f"   ... et {len(client_stats) - 10} autres clients")
            
            # Import avec extraction de mesures
            for entry in valuable_entries:
                try:
                    # Délai entre chaque import pour ne pas surcharger Supabase/Cloudflare
                    # Note: Pagination Gazelle est gérée par get_timeline_entries
                    # Ce délai est pour l'écriture Supabase uniquement
                    if self.delay > 0 and not self.dry_run:
                        time.sleep(self.delay)
                    external_id = entry.get('id')
                    entry_type = entry.get('type', 'NOTE')
                    
                    # Récupérer texte combiné pour extraction mesures
                    summary = entry.get('summary', '') or ''
                    comment = entry.get('comment', '') or ''
                    combined_text = f"{summary} {comment}".strip()
                    
                    # Extraire mesures
                    measurements = self.extract_measurements(combined_text)
                    
                    # Parser dates
                    occurred_at_raw = entry.get('occurredAt')
                    occurred_at_iso = None
                    if occurred_at_raw:
                        try:
                            dt = datetime.fromisoformat(occurred_at_raw.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            occurred_at_iso = dt.isoformat()
                        except:
                            occurred_at_iso = occurred_at_raw
                    
                    # Construire record Supabase
                    client_obj = entry.get('client', {})
                    piano_obj = entry.get('piano', {})
                    user_obj = entry.get('user', {})
                    
                    # Mapping des types Gazelle vers types valides Supabase
                    # Contrainte SQL accepte: APPOINTMENT, CONTACT_EMAIL, NOTE, APPOINTMENT_COMPLETION,
                    # SYSTEM_NOTIFICATION, SERVICE_ENTRY_MANUAL, PIANO_MEASUREMENT, INVOICE_PAYMENT, ERROR_MESSAGE
                    entry_type_gazelle = entry_type.upper() if entry_type else 'NOTE'
                    entry_type_mapped = self._map_entry_type(entry_type_gazelle)
                    
                    # Schéma v5: utiliser les mêmes colonnes que sync_to_supabase.py
                    record = {
                        'external_id': external_id,
                        'client_id': client_obj.get('id') if client_obj else None,
                        'piano_id': piano_obj.get('id') if piano_obj else None,
                        'user_id': user_obj.get('id') if user_obj else None,
                        'occurred_at': occurred_at_iso,
                        'entry_type': entry_type_mapped,  # Type mappé vers valeurs valides
                        'title': summary[:500] if summary else None,
                        'description': comment[:2000] if comment else None,
                    }
                    
                    # Ajouter mesures si extraites
                    metadata = {}
                    if measurements['humidity'] is not None:
                        metadata['humidity'] = measurements['humidity']
                    if measurements['temperature'] is not None:
                        metadata['temperature'] = measurements['temperature']
                    if measurements['frequency'] is not None:
                        metadata['frequency'] = measurements['frequency']
                    
                    if metadata:
                        record['metadata'] = metadata
                    
                    # Nettoyer None
                    record = {k: v for k, v in record.items() if v is not None and v != ''}
                    
                    if self.dry_run:
                        # Afficher label simple
                        label = comment[:50] if comment else summary[:50] or entry_type
                        print(f"  [DRY-RUN] UPSERT: {label}")
                        self.stats['timeline']['success'] += 1
                    else:
                        # UPSERT
                        result = self.supabase.table('gazelle_timeline_entries')\
                            .upsert(record, on_conflict='external_id')\
                            .execute()
                        
                        if result.data:
                            # Afficher label simple
                            label = comment[:50] if comment else summary[:50] or entry_type
                            print(f"  [TIMELINE] OK: {label}")
                            self.stats['timeline']['success'] += 1
                    
                except Exception as e:
                    entry_id = entry.get('id', 'unknown')
                    print(f"  [TIMELINE] ERREUR: {entry_id} - {e}")
                    self.stats['timeline']['errors'] += 1
                    # Continue - atomicité: une erreur ne bloque pas le reste
            
            return {
                'total': len(entries),
                'valuable': len(valuable_entries),
                'imported': self.stats['timeline']['success']
            }
            
        except Exception as e:
            print(f"❌ Erreur import timeline: {e}")
            import traceback
            traceback.print_exc()
            return {'total': 0, 'valuable': 0, 'imported': 0}
    
    def run_all(self, since_date: str = "2016-01-01T00:00:00Z"):
        """Exécute l'import complet des 3 flux."""
        print("\n" + "="*70)
        print("🚀 SMART IMPORT - TRIPLE FLUX COMPLET")
        print("="*70)
        
        results = {
            'invoices': self.import_invoices(),
            'estimates': self.import_estimates(),
            'timeline': self.import_timeline(since_date=since_date)
        }
        
        # Résumé final avec logs clairs
        print("\n" + "="*70)
        print("📊 RÉSUMÉ FINAL")
        print("="*70)
        
        # Factures
        inv = self.stats['invoices']
        print(f"📄 FACTURES:")
        print(f"   Succès: {inv['success']} | Échecs: {inv['errors']} | Filtrés: {inv['filtered']}")
        
        # Soumissions
        est = self.stats['estimates']
        print(f"📋 SOUMISSIONS:")
        print(f"   Succès: {est['success']} | Échecs: {est['errors']} | Filtrés: {est['filtered']}")
        
        # Timeline
        tl = self.stats['timeline']
        print(f"📝 TIMELINE:")
        print(f"   Succès: {tl['success']} | Échecs: {tl['errors']} | Filtrés (bruit): {tl['noise_filtered']}")
        print(f"   Total récupéré: {results['timeline']['total']}")
        print(f"   Haute valeur: {results['timeline']['valuable']}")
        
        if self.dry_run:
            print("\n⚠️  MODE DRY-RUN - Aucune donnée écrite dans Supabase")
        
        print("="*70)


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Import - Import intelligent Gazelle → Supabase")
    parser.add_argument('--since', type=str, default="2016-01-01T00:00:00Z",
                       help='Date de début pour timeline (format ISO)')
    parser.add_argument('--invoices-only', action='store_true', help='Importer seulement les factures')
    parser.add_argument('--estimates-only', action='store_true', help='Importer seulement les soumissions')
    parser.add_argument('--timeline-only', action='store_true', help='Importer seulement la timeline')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Mode dry-run: affiche sans écrire dans Supabase')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Délai en secondes entre requêtes (défaut: 0.5s)')
    args = parser.parse_args()
    
    importer = SmartImport(dry_run=args.dry_run, delay=args.delay)
    
    if args.invoices_only:
        importer.import_invoices()
    elif args.estimates_only:
        importer.import_estimates()
    elif args.timeline_only:
        importer.import_timeline(since_date=args.since)
    else:
        # Import complet
        importer.run_all(since_date=args.since)


if __name__ == '__main__':
    main()
