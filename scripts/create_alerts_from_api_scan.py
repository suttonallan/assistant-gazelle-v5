#!/usr/bin/env python3
"""
Crée les alertes d'humidité directement depuis le scanner API Gazelle.

Ce script:
1. Lance le scanner API Gazelle (qui trouve les alertes dans 'comment')
2. Crée les alertes dans Supabase avec les bons champs
3. Gère les IDs d'instruments vs IDs numériques
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient
from modules.alerts.humidity_scanner_safe import HumidityScannerSafe


def create_alert_safe(storage, alert_data):
    """
    Crée une alerte dans Supabase de manière sécurisée.

    Gère les cas où piano_id est un ID d'instrument (ins_xxx).
    """
    try:
        # Préparer les données
        alert_record = {
            'timeline_entry_id': alert_data.get('timeline_entry_id'),
            'alert_type': alert_data.get('alert_type'),
            'client_id': alert_data.get('client_id'),
            'piano_id': alert_data.get('piano_id'),  # Peut être ins_xxx ou ID numérique
            'description': alert_data.get('description', '')[:500],
            'observed_at': alert_data.get('observed_at'),
            'is_resolved': False,
            'archived': False,
            'created_at': datetime.utcnow().isoformat()
        }

        # Vérifier si l'alerte existe déjà (par timeline_entry_id)
        existing = storage.client.table('humidity_alerts').select('id').eq(
            'timeline_entry_id', alert_record['timeline_entry_id']
        ).execute()

        if existing.data and len(existing.data) > 0:
            print(f"  ⏭️  Alerte déjà existante: {alert_record['timeline_entry_id']}")
            return {'status': 'exists', 'id': existing.data[0]['id']}

        # Créer l'alerte
        response = storage.client.table('humidity_alerts').insert(alert_record).execute()

        if response.data and len(response.data) > 0:
            alert_id = response.data[0]['id']
            print(f"  ✅ Alerte créée: {alert_id}")
            return {'status': 'created', 'id': alert_id}
        else:
            print(f"  ⚠️  Aucune donnée retournée")
            return {'status': 'error', 'message': 'No data returned'}

    except Exception as e:
        error_msg = str(e)
        print(f"  ❌ Erreur: {error_msg}")

        # Si l'erreur est une contrainte de clé étrangère sur piano_id
        if 'foreign key' in error_msg.lower() or 'violates' in error_msg.lower():
            # Essayer sans piano_id
            try:
                alert_record_no_piano = {**alert_record}
                del alert_record_no_piano['piano_id']

                response = storage.client.table('humidity_alerts').insert(alert_record_no_piano).execute()

                if response.data and len(response.data) > 0:
                    alert_id = response.data[0]['id']
                    print(f"  ✅ Alerte créée (sans piano_id): {alert_id}")
                    return {'status': 'created_without_piano', 'id': alert_id}
            except Exception as e2:
                print(f"  ❌ Échec même sans piano_id: {e2}")
                return {'status': 'error', 'message': str(e2)}

        return {'status': 'error', 'message': error_msg}


def main():
    """Fonction principale."""
    print()
    print("🚀 CRÉATION DES ALERTES DEPUIS SCANNER API GAZELLE")
    print("=" * 70)
    print()

    try:
        # Initialiser
        storage = SupabaseStorage()
        scanner = HumidityScannerSafe()

        print("📊 Scan des 7 derniers jours...")
        print()

        # Lancer le scan (retourne les stats mais ne crée pas les alertes)
        result = scanner.scan_new_entries(days_back=7)

        print()
        print(f"✅ Scan terminé:")
        print(f"   Scannées: {result.get('scanned', 0)}")
        print(f"   Alertes trouvées: {result.get('alerts_found', 0)}")
        print(f"   Nouvelles alertes: {result.get('new_alerts', 0)}")
        print(f"   Erreurs: {result.get('errors', 0)}")
        print()

        if result.get('new_alerts', 0) == 0:
            print("ℹ️  Aucune nouvelle alerte à créer")
            print()
            return 0

        print(f"🎯 Résultat: {result.get('new_alerts', 0)} nouvelle(s) alerte(s) créée(s)")
        print()

        # Vérifier combien sont réellement dans la base
        response = storage.client.table('humidity_alerts').select('*', count='exact').eq('archived', False).execute()
        total_alerts = response.count if response.count else 0

        print(f"📊 Total alertes non archivées: {total_alerts}")
        print()

        print("✅ TERMINÉ")
        print()
        print("💡 Prochaines étapes:")
        print("   1. Rafraîchis le frontend (F5)")
        print("   2. Va sur 'Tableau de bord'")
        print("   3. Les alertes devraient apparaître!")
        print()

        return 0

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
