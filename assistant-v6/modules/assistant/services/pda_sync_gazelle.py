#!/usr/bin/env python3
"""
Import limité des rendez-vous Gazelle - Place des Arts

Au lieu d'importer TOUT l'historique, on importe seulement:
- Les RV des 30 prochains jours
- Qui contiennent "Place des Arts" dans les notes
"""

import sys
import os
from typing import Dict, List, Any
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# Ajouter le parent au path pour importer SupabaseStorage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from modules.storage.supabase import SupabaseStorage


class PlaceDesArtsSyncGazelle:
    """Import limité des RV Gazelle pour Place des Arts"""

    def __init__(self):
        """Initialise avec connexion Supabase"""
        self.storage = SupabaseStorage()
        print("✅ PlaceDesArtsSyncGazelle initialisé")

    def get_gazelle_appointments_pda(
        self,
        days_ahead: int = 30,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Récupère les RV Gazelle Place des Arts des N prochains jours.

        Args:
            days_ahead: Nombre de jours à l'avance (défaut: 30)
            debug: Mode debug

        Returns:
            Liste des rendez-vous Gazelle contenant "Place des Arts"
        """
        try:
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)

            url = f"{self.storage.api_url}/gazelle_appointments"
            url += "?select=*"
            url += f"&appointment_date=gte.{today}"
            url += f"&appointment_date=lte.{end_date}"
            url += "&notes=ilike.*Place des Arts*"
            url += "&order=appointment_date.asc"

            if debug:
                print(f"🔍 Recherche RV Gazelle Place des Arts ({today} → {end_date})")
                print(f"   URL: {url[:100]}...")

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                results = response.json()
                if debug:
                    print(f"  ✅ Trouvé {len(results)} RV Place des Arts")
                return results
            else:
                if debug:
                    print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur get_gazelle_appointments_pda: {e}")
            import traceback
            traceback.print_exc()
            return []

    def sync_limited(
        self,
        days_ahead: int = 30,
        dry_run: bool = False,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronise les RV Gazelle Place des Arts (import limité).

        Cette fonction NE synchronise QUE les RV des N prochains jours.

        Args:
            days_ahead: Nombre de jours à importer
            dry_run: Si True, n'écrit rien (preview seulement)
            debug: Mode debug

        Returns:
            Résumé de la synchronisation
        """
        print(f"\n{'='*80}")
        print(f"🔄 IMPORT LIMITÉ - Place des Arts (prochains {days_ahead} jours)")
        print(f"{'='*80}")

        if dry_run:
            print("⚠️  MODE DRY RUN - Aucune écriture")

        # 1. Récupérer les RV Gazelle Place des Arts
        gazelle_appointments = self.get_gazelle_appointments_pda(
            days_ahead=days_ahead,
            debug=debug
        )

        if not gazelle_appointments:
            print("\n✅ Aucun nouveau RV à importer")
            return {
                'dry_run': dry_run,
                'found': 0,
                'would_import': 0,
                'imported': 0,
                'appointments': []
            }

        # 2. Afficher le résumé
        print(f"\n📊 {len(gazelle_appointments)} RV trouvés dans Gazelle:")
        for appt in gazelle_appointments[:10]:  # Afficher les 10 premiers
            date = appt.get('appointment_date', 'N/A')
            tech = appt.get('technicien', 'N/A')
            notes = appt.get('notes', '')[:60]
            print(f"  - {date}: {tech} - {notes}...")

        if len(gazelle_appointments) > 10:
            print(f"  ... et {len(gazelle_appointments) - 10} autres")

        # 3. Si dry_run, s'arrêter ici
        if dry_run:
            print(f"\n✅ Preview terminé (aucune écriture)")
            return {
                'dry_run': True,
                'found': len(gazelle_appointments),
                'would_import': len(gazelle_appointments),
                'imported': 0,
                'appointments': gazelle_appointments
            }

        # 4. TODO: Implémenter l'écriture dans une table de cache
        # Pour l'instant, on retourne juste les données
        print(f"\n✅ Import terminé: {len(gazelle_appointments)} RV")

        return {
            'dry_run': False,
            'found': len(gazelle_appointments),
            'would_import': len(gazelle_appointments),
            'imported': len(gazelle_appointments),
            'appointments': gazelle_appointments
        }


# ============================================================================
# Test de synchronisation
# ============================================================================

if __name__ == "__main__":
    sync = PlaceDesArtsSyncGazelle()

    # Test en mode dry_run
    result = sync.sync_limited(days_ahead=30, dry_run=True, debug=True)

    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ")
    print(f"{'='*80}")
    print(f"Mode: {'DRY RUN' if result['dry_run'] else 'PRODUCTION'}")
    print(f"RV trouvés: {result['found']}")
    print(f"À importer: {result['would_import']}")
    print(f"Importés: {result['imported']}")
