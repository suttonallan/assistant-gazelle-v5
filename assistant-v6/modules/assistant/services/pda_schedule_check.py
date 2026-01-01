#!/usr/bin/env python3
"""
Vérification de l'horaire des techniciens pour Place des Arts

Affiche le calendrier du technicien assigné pour voir:
- S'il a déjà un RV Gazelle à cette date/heure
- Son horaire complet de la journée
- Conflits potentiels
"""

import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# Ajouter le parent au path pour importer SupabaseStorage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from modules.storage.supabase import SupabaseStorage


class ScheduleChecker:
    """Vérification de l'horaire des techniciens"""

    def __init__(self):
        """Initialise avec connexion Supabase"""
        self.storage = SupabaseStorage()
        print("✅ ScheduleChecker initialisé")

    def get_technician_schedule(
        self,
        tech_id: str,
        date: str,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Récupère tous les RV d'un technicien pour une date donnée.

        Args:
            tech_id: ID du technicien (ex: usr_HcCiFk7o0vZ9xAI0)
            date: Date au format YYYY-MM-DD
            debug: Mode débogage

        Returns:
            Liste des RV triés par heure
        """
        try:
            # Extraire juste la date (YYYY-MM-DD)
            date_only = date[:10] if date else None
            if not date_only:
                return []

            url = f"{self.storage.api_url}/gazelle_appointments"
            url += "?select=*"
            url += f"&appointment_date=eq.{date_only}"
            url += f"&technicien=eq.{tech_id}"
            url += "&order=appointment_time.asc"

            if debug:
                print(f"    🔍 Recherche RV pour {tech_id} le {date_only}")

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                results = response.json()
                if debug:
                    print(f"      ✅ Trouvé {len(results)} RV")
                return results
            else:
                if debug:
                    print(f"      ❌ Erreur {response.status_code}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur get_technician_schedule: {e}")
            return []

    def check_pda_request_schedule(
        self,
        request_id: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Vérifie l'horaire du technicien pour une demande Place des Arts.

        Args:
            request_id: ID de la demande PDA
            debug: Mode débogage

        Returns:
            Dict avec l'horaire du technicien et les conflits potentiels
        """
        try:
            # Récupérer la demande PDA
            url = f"{self.storage.api_url}/place_des_arts_requests"
            url += f"?id=eq.{request_id}"
            url += "&select=*"

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code != 200 or not response.json():
                return {'error': 'Demande non trouvée'}

            pda_request = response.json()[0]
            tech_id = pda_request.get('technician_id')
            appt_date = pda_request.get('appointment_date')
            pda_time = pda_request.get('time', '')
            room = pda_request.get('room', 'N/A')

            if not tech_id:
                return {'error': 'Aucun technicien assigné'}

            # Mapping des noms de techniciens
            tech_names = {
                'usr_HcCiFk7o0vZ9xAI0': 'Nick',
                'usr_ofYggsCDt2JAVeNP': 'Allan',
                'usr_ReUSmIJmBF86ilY1': 'JP'
            }
            tech_name = tech_names.get(tech_id, tech_id)

            # Récupérer l'horaire du technicien
            schedule = self.get_technician_schedule(tech_id, appt_date, debug=debug)

            # Analyser les conflits potentiels
            conflicts = []
            for rv in schedule:
                rv_time = rv.get('appointment_time', '')
                rv_notes = rv.get('notes', '')

                # Vérifier si c'est le même RV Place des Arts
                if 'PDA' in rv_notes.upper() or 'PLACE DES ARTS' in rv_notes.upper():
                    if room.upper() in rv_notes.upper():
                        conflicts.append({
                            'type': 'match',
                            'time': rv_time,
                            'notes': rv_notes[:80],
                            'external_id': rv.get('external_id')
                        })
                else:
                    # Autre RV qui pourrait créer un conflit
                    conflicts.append({
                        'type': 'other',
                        'time': rv_time,
                        'notes': rv_notes[:80],
                        'external_id': rv.get('external_id')
                    })

            return {
                'technician_id': tech_id,
                'technician_name': tech_name,
                'date': appt_date,
                'pda_time': pda_time,
                'pda_room': room,
                'schedule': schedule,
                'conflicts': conflicts,
                'total_appointments': len(schedule)
            }

        except Exception as e:
            print(f"⚠️ Erreur check_pda_request_schedule: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}

    def display_schedule(self, request_id: str):
        """Affiche l'horaire du technicien de manière lisible"""
        result = self.check_pda_request_schedule(request_id, debug=True)

        if 'error' in result:
            print(f"❌ Erreur: {result['error']}")
            return

        print(f"\n{'='*80}")
        print(f"📅 Horaire de {result['technician_name']} - {result['date'][:10]}")
        print(f"{'='*80}")

        print(f"\n🎭 Demande Place des Arts:")
        print(f"   Salle: {result['pda_room']}")
        print(f"   Heure: {result['pda_time']}")

        print(f"\n📋 Calendrier du jour ({result['total_appointments']} RV):")

        if not result['schedule']:
            print("   Aucun RV ce jour-là")
        else:
            for rv in result['schedule']:
                time = rv.get('appointment_time', 'N/A')
                notes = rv.get('notes', '')[:60]
                is_pda = 'PDA' in notes.upper() or 'PLACE DES ARTS' in notes.upper()
                icon = '🎭' if is_pda else '📌'

                print(f"\n   {icon} {time}")
                print(f"      {notes}")

                if is_pda and result['pda_room'].upper() in notes.upper():
                    print(f"      ✅ C'est le RV Place des Arts!")

        # Résumé des conflits
        print(f"\n{'='*80}")
        pda_matches = [c for c in result['conflicts'] if c['type'] == 'match']
        other_rvs = [c for c in result['conflicts'] if c['type'] == 'other']

        if pda_matches:
            print(f"✅ RV Place des Arts trouvé dans Gazelle ({len(pda_matches)})")
        else:
            print(f"⚠️  Aucun RV Place des Arts trouvé dans Gazelle")

        if other_rvs:
            print(f"ℹ️  {len(other_rvs)} autre(s) RV ce jour-là")


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Vérifier horaire technicien Place des Arts')
    parser.add_argument('request_id', help='ID de la demande Place des Arts')
    args = parser.parse_args()

    checker = ScheduleChecker()
    checker.display_schedule(args.request_id)
