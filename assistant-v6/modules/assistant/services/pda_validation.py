#!/usr/bin/env python3
"""
Validation de cohérence Place des Arts <-> Calendrier Gazelle

Détecte les incohérences entre:
- Le statut marqué dans place_des_arts_requests
- L'existence réelle du RV dans gazelle_appointments
"""

import sys
import os
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import requests
from dotenv import load_dotenv

# Charger .env
load_dotenv()

# Ajouter le parent au path pour importer SupabaseStorage
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

# Try to import from different locations depending on where we're called from
try:
    from modules.storage.supabase import SupabaseStorage
except ImportError:
    from core.supabase_storage import SupabaseStorage


class PlaceDesArtsValidator:
    """Validation de cohérence PDA <-> Gazelle"""

    def __init__(self, storage=None):
        """
        Initialise avec connexion Supabase

        Args:
            storage: Instance de SupabaseStorage (optionnel, créé si non fourni)
        """
        self.storage = storage if storage else SupabaseStorage()
        if not storage:
            print("✅ PlaceDesArtsValidator initialisé")

    def get_pda_requests(
        self,
        status: str = None,
        with_appointment_id: bool = None,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Récupère les demandes Place des Arts"""
        try:
            url = f"{self.storage.api_url}/place_des_arts_requests"
            url += "?select=*"

            if status:
                url += f"&status=eq.{status}"

            if with_appointment_id is not None:
                if with_appointment_id:
                    url += "&appointment_id=not.is.null"
                else:
                    url += "&appointment_id=is.null"

            url += f"&limit={limit}"
            url += "&order=appointment_date.desc"

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"  ❌ Erreur {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur get_pda_requests: {e}")
            import traceback
            traceback.print_exc()
            return []

    def find_gazelle_appointment_for_pda(
        self,
        appointment_date: str,
        room: str,
        debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Cherche un RV Gazelle qui correspond à une demande Place des Arts.

        Match par:
        - Date de RV
        - Notes contenant "PdA" OU "Place des Arts"
        - Salle (avec variations: MS → Maison Symphonique, etc.)
        """
        try:
            # Extraire juste la date (YYYY-MM-DD)
            # Gère les formats: "2026-01-14" OU "2026-01-14T00:00:00+00:00"
            if not appointment_date:
                return None

            if 'T' in appointment_date:
                date_only = appointment_date.split('T')[0]
            else:
                date_only = appointment_date[:10]

            # Mapping des salles PDA → variations dans Gazelle
            room_variations = {
                'MS': ['MAISON SYMPHONIQUE', 'MAISON SYM', 'MS', 'M.S.', 'MSM'],
                'MSM': ['MAISON SYMPHONIQUE', 'MAISON SYM', 'MS', 'M.S.', 'MSM'],
                'WP': ['WILFRID-PELLETIER', 'WP', 'W.P.', 'WILFRID PELLETIER'],
                'C5': ['C5', 'CINQUIÈME SALLE', '5E SALLE'],
                'CLAUDE LÉVEILLÉ': ['CLAUDE LÉVEILLÉ', 'CLAUDE LEVEILLE'],
            }

            # Obtenir les variations pour cette salle
            room_upper = room.upper()
            variations = room_variations.get(room_upper, [room_upper])

            url = f"{self.storage.api_url}/gazelle_appointments"
            url += "?select=*"
            url += f"&appointment_date=eq.{date_only}"
            # Chercher "PdA" OU "Place des Arts" dans titre OU notes
            url += "&or=(notes.ilike.*PdA*,notes.ilike.*Place des Arts*,title.ilike.*Place des Arts*)"

            if debug:
                print(f"    🔍 Recherche RV Gazelle: date={date_only}, salle={room} (variations: {variations})")

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                results = response.json()

                # Filtrer par salle dans les notes (avec variations)
                for appt in results:
                    notes = (appt.get('notes', '') or '').upper()

                    # Vérifier si une des variations de salle est dans les notes
                    for variation in variations:
                        if variation in notes:
                            if debug:
                                print(f"      ✅ Trouvé: {appt.get('external_id')} - {appt.get('notes', '')[:60]}")
                            return appt

                if debug and results:
                    print(f"      ⚠️  {len(results)} RV trouvés mais aucun ne correspond à salle '{room}'")
                    for appt in results:
                        print(f"         - {appt.get('notes', '')[:80]}")

                return None
            else:
                return None

        except Exception as e:
            print(f"⚠️ Erreur find_gazelle_appointment_for_pda: {e}")
            return None

    def validate_coherence(
        self,
        limit: int = 500,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Valide la cohérence entre PDA et Gazelle.

        Retourne les incohérences détectées:
        - status_mismatch: Statut dit CREATED_IN_GAZELLE mais pas d'appointment_id
        - missing_appointment: A un appointment_id mais RV n'existe pas dans Gazelle
        - orphaned_appointments: appointment_id pointant vers un RV qui n'existe plus
        """
        print(f"\n{'='*80}")
        print("🔍 Validation de cohérence Place des Arts <-> Gazelle")
        print(f"{'='*80}")

        # Récupérer toutes les demandes PDA
        all_requests = self.get_pda_requests(limit=limit)
        print(f"\n📊 {len(all_requests)} demandes Place des Arts à valider")

        # Catégories d'incohérences
        assigned_with_rv = []  # Assigné ET RV existe dans Gazelle
        assigned_no_rv = []  # Assigné MAIS pas de RV dans Gazelle
        status_created_with_rv = []  # Dit CREATED_IN_GAZELLE ET RV existe
        status_created_no_rv = []  # Dit CREATED_IN_GAZELLE MAIS pas de RV

        for req in all_requests:
            req_id = req.get('id')
            status = req.get('status', '')
            room = req.get('room', 'N/A')
            appt_date = req.get('appointment_date', 'N/A')
            tech_id = req.get('technician_id')

            # Chercher si un RV existe dans Gazelle (par date + salle + "Place des Arts")
            gazelle_appt = self.find_gazelle_appointment_for_pda(
                appointment_date=appt_date,
                room=room,
                debug=debug
            )

            # Cas 1: Technicien assigné (ASSIGN_OK ou COMPLETED)
            if status in ('ASSIGN_OK', 'COMPLETED') and tech_id:
                if gazelle_appt:
                    # OK: assigné ET RV existe
                    assigned_with_rv.append({
                        'id': req_id,
                        'room': room,
                        'date': appt_date,
                        'status': status,
                        'technician_id': tech_id,
                        'gazelle_appt_id': gazelle_appt.get('external_id'),
                        'gazelle_tech': gazelle_appt.get('technicien')
                    })
                    if debug:
                        print(f"  ✅ {req_id}: Assigné ET RV existe ({gazelle_appt.get('external_id')})")
                else:
                    # ALERTE: assigné MAIS pas de RV
                    assigned_no_rv.append({
                        'id': req_id,
                        'room': room,
                        'date': appt_date,
                        'status': status,
                        'technician_id': tech_id,
                        'issue': 'Technicien assigné mais aucun RV dans Gazelle'
                    })
                    if debug:
                        print(f"  ⚠️  {req_id}: Assigné MAIS pas de RV dans Gazelle")

            # Cas 2: Statut dit CREATED_IN_GAZELLE
            elif status == 'CREATED_IN_GAZELLE':
                if gazelle_appt:
                    # OK: statut cohérent
                    status_created_with_rv.append({
                        'id': req_id,
                        'room': room,
                        'date': appt_date,
                        'status': status,
                        'gazelle_appt_id': gazelle_appt.get('external_id')
                    })
                    if debug:
                        print(f"  ✅ {req_id}: CREATED_IN_GAZELLE ET RV existe")
                else:
                    # ALERTE: dit créé MAIS pas de RV
                    status_created_no_rv.append({
                        'id': req_id,
                        'room': room,
                        'date': appt_date,
                        'status': status,
                        'issue': 'Statut dit CREATED_IN_GAZELLE mais aucun RV dans Gazelle'
                    })
                    if debug:
                        print(f"  ❌ {req_id}: Dit CREATED_IN_GAZELLE MAIS pas de RV")

        # Résumé
        print(f"\n{'='*80}")
        print("📊 RÉSUMÉ DE VALIDATION")
        print(f"{'='*80}")
        print(f"✅ Assignés avec RV: {len(assigned_with_rv)}")
        print(f"⚠️  Assignés SANS RV: {len(assigned_no_rv)}")
        print(f"✅ Statut CREATED avec RV: {len(status_created_with_rv)}")
        print(f"❌ Statut CREATED SANS RV: {len(status_created_no_rv)}")

        return {
            'total_requests': len(all_requests),
            'assigned_with_rv': assigned_with_rv,
            'assigned_no_rv': assigned_no_rv,
            'status_created_with_rv': status_created_with_rv,
            'status_created_no_rv': status_created_no_rv,
        }


# ============================================================================
# Test de validation
# ============================================================================

if __name__ == "__main__":
    validator = PlaceDesArtsValidator()

    result = validator.validate_coherence(limit=500, debug=True)

    print(f"\n{'='*80}")
    print("🔍 INCOHÉRENCES DÉTECTÉES")
    print(f"{'='*80}")

    if result['status_created_no_rv']:
        print(f"\n❌ STATUT CRÉÉ MAIS PAS DE RV ({len(result['status_created_no_rv'])}):")
        for item in result['status_created_no_rv'][:5]:
            print(f"  - {item['id']}: {item['room']} ({item['date']})")
            print(f"    Issue: {item['issue']}")

    if result['assigned_no_rv']:
        print(f"\n⚠️  ASSIGNÉ MAIS PAS DE RV ({len(result['assigned_no_rv'])}):")
        for item in result['assigned_no_rv'][:5]:
            print(f"  - {item['id']}: {item['room']} ({item['date']})")
            print(f"    Tech: {item['technician_id']}")
            print(f"    Issue: {item['issue']}")

    if result['assigned_with_rv']:
        print(f"\n✅ ASSIGNÉS AVEC RV ({len(result['assigned_with_rv'])}):")
        for item in result['assigned_with_rv'][:3]:
            print(f"  - {item['id']}: {item['room']} ({item['date']})")
            print(f"    RV Gazelle: {item['gazelle_appt_id']}")
