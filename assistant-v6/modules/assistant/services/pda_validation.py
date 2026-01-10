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
        appointment_time: Optional[str] = None,
        debug: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Cherche un RV Gazelle qui correspond à une demande Place des Arts.

        Match par:
        - Date de RV (avec fenêtre ±1 jour pour timezone)
        - Heure de RV (avec fenêtre ±2h si fournie)
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
                'TM': ['THÉÂTRE MAISONNEUVE', 'THEATRE MAISONNEUVE', 'TM', 'T.M.', 'MAISONNEUVE'],
                'C5': ['C5', 'CINQUIÈME SALLE', '5E SALLE'],
                '5E': ['C5', 'CINQUIÈME SALLE', '5E SALLE', '5E', '5EME SALLE'],
                'SCL': ['CLAUDE LÉVEILLÉ', 'CLAUDE LEVEILLE', 'SCL', 'STUDIO CLAUDE'],
                'CLAUDE LÉVEILLÉ': ['CLAUDE LÉVEILLÉ', 'CLAUDE LEVEILLE', 'SCL'],
                'TJD': ['JEAN-DUCEPPE', 'JEAN DUCEPPE', 'TJD', 'DUCEPPE'],
            }

            # Obtenir les variations pour cette salle
            room_upper = room.upper()
            variations = room_variations.get(room_upper, [room_upper])

            # CORRECTION TIMEZONE: Chercher avec fenêtre ±1 jour
            # La date PDA est en timezone Montreal, mais Gazelle stocke en UTC
            # Un RV à minuit Montreal (2026-01-11T00:00 EST) = 2026-01-11T05:00 UTC
            # mais pourrait apparaître comme 2026-01-10 ou 2026-01-11 selon l'heure
            from datetime import datetime, timedelta
            date_obj = datetime.strptime(date_only, '%Y-%m-%d')
            date_before = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
            date_after = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

            url = f"{self.storage.api_url}/gazelle_appointments"
            url += "?select=*"
            # Fenêtre de recherche: date ±1 jour (pour gérer décalages timezone)
            url += f"&appointment_date=gte.{date_before}"
            url += f"&appointment_date=lte.{date_after}"
            # Chercher "PdA" OU "Place des Arts" dans titre OU notes
            url += "&or=(notes.ilike.*PdA*,notes.ilike.*Place des Arts*,title.ilike.*Place des Arts*)"

            if debug:
                print(f"    🔍 Recherche RV Gazelle: date={date_only} (fenêtre {date_before} → {date_after}), salle={room}")

            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code == 200:
                results = response.json()

                # Helper: Parser l'heure de la demande PDA (ex: "avant 8h", "13h30", "10h")
                def parse_pda_time(time_str: Optional[str]) -> Optional[int]:
                    """Extrait l'heure en minutes depuis minuit. Ex: '13h30' → 810, 'avant 8h' → 480"""
                    if not time_str:
                        return None

                    time_lower = time_str.lower().strip()

                    # Retirer "avant", "après", "vers", etc.
                    time_lower = time_lower.replace('avant', '').replace('après', '').replace('vers', '').strip()

                    # Parser "13h30", "13h", "8h30"
                    import re
                    match = re.search(r'(\d{1,2})h(\d{2})?', time_lower)
                    if match:
                        hour = int(match.group(1))
                        minute = int(match.group(2)) if match.group(2) else 0
                        return hour * 60 + minute

                    return None

                # Helper: Parser l'heure Gazelle (format "HH:MM:SS" ou "HH:MM")
                def parse_gazelle_time(time_str: Optional[str]) -> Optional[int]:
                    """Extrait l'heure en minutes depuis minuit. Ex: '13:30:00' → 810"""
                    if not time_str:
                        return None

                    parts = time_str.split(':')
                    if len(parts) >= 2:
                        try:
                            hour = int(parts[0])
                            minute = int(parts[1])
                            return hour * 60 + minute
                        except ValueError:
                            return None

                    return None

                # Parser l'heure demandée
                requested_time_mins = parse_pda_time(appointment_time) if appointment_time else None

                if debug and requested_time_mins:
                    hours = requested_time_mins // 60
                    mins = requested_time_mins % 60
                    print(f"    ⏰ Heure demandée: {appointment_time} → {hours:02d}h{mins:02d} (±2h)")

                # Filtrer par salle dans les notes (avec variations)
                for appt in results:
                    notes = (appt.get('notes', '') or '').upper()

                    # Vérifier si une des variations de salle est dans les notes
                    room_match = False
                    for variation in variations:
                        if variation in notes:
                            room_match = True
                            break

                    if not room_match:
                        continue

                    # Si heure fournie, filtrer avec fenêtre ±2h
                    if requested_time_mins is not None:
                        gazelle_time_mins = parse_gazelle_time(appt.get('appointment_time'))

                        if gazelle_time_mins is not None:
                            time_diff = abs(gazelle_time_mins - requested_time_mins)

                            if debug:
                                gz_hours = gazelle_time_mins // 60
                                gz_mins = gazelle_time_mins % 60
                                print(f"      📍 Candidat: {appt.get('external_id')} - Gazelle: {gz_hours:02d}h{gz_mins:02d}, Diff: {time_diff}min")

                            # Fenêtre de ±2h = 120 minutes
                            if time_diff <= 120:
                                if debug:
                                    print(f"      ✅ Trouvé (heure compatible): {appt.get('external_id')} - {appt.get('notes', '')[:60]}")
                                return appt
                            else:
                                if debug:
                                    print(f"      ⏭️  Heure trop éloignée (diff: {time_diff}min > 120min)")
                                continue
                        else:
                            # Gazelle n'a pas d'heure, accepter quand même (match sur date + salle)
                            if debug:
                                print(f"      ✅ Trouvé (pas d'heure Gazelle): {appt.get('external_id')} - {appt.get('notes', '')[:60]}")
                            return appt
                    else:
                        # Pas d'heure demandée, accepter le premier match sur date + salle
                        if debug:
                            print(f"      ✅ Trouvé: {appt.get('external_id')} - {appt.get('notes', '')[:60]}")
                        return appt

                if debug and results:
                    print(f"      ⚠️  {len(results)} RV trouvés mais aucun ne correspond à salle '{room}' + heure '{appointment_time}'")
                    for appt in results:
                        print(f"         - {appt.get('appointment_time', 'N/A')} {appt.get('notes', '')[:80]}")

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
