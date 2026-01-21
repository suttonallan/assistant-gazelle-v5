#!/usr/bin/env python3
"""
Service de synchronisation Place des Arts ↔ Gazelle.

Synchronise les demandes Place des Arts avec les rendez-vous Gazelle:
- Trouve les RV Gazelle correspondant aux demandes PDA
- Lie les demandes aux RV (appointment_id)
- Met à jour les statuts
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

logger = logging.getLogger(__name__)


class GazelleSyncService:
    """Service de synchronisation Place des Arts avec Gazelle."""
    
    # Client ID Place des Arts
    PDA_CLIENT_ID = "cli_HbEwl9rN11pSuDEU"
    
    def __init__(self, storage: Optional[SupabaseStorage] = None):
        """Initialise le service de synchronisation."""
        self.storage = storage or SupabaseStorage()
    
    def sync_requests_with_gazelle(
        self,
        request_ids: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Synchronise les demandes PDA avec les RV Gazelle.
        
        Args:
            request_ids: Liste des IDs de demandes à synchroniser (None = toutes)
            dry_run: Si True, ne fait que vérifier sans mettre à jour
        
        Returns:
            {
                "success": True/False,
                "checked": nombre de demandes vérifiées,
                "matched": nombre de correspondances trouvées,
                "updated": nombre de demandes mises à jour,
                "details": [...],
                "warnings": [...]
            }
        """
        try:
            print(f"\n{'='*70}")
            print(f"🔄 SYNCHRONISATION PLACE DES ARTS ↔ GAZELLE")
            print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
            print(f"{'='*70}\n")
            
            # 1. Récupérer les demandes PDA
            if request_ids:
                requests = self._get_requests_by_ids(request_ids)
            else:
                # Toutes les demandes sans appointment_id
                requests = self._get_unlinked_requests()
            
            if not requests:
                return {
                    "success": True,
                    "checked": 0,
                    "matched": 0,
                    "updated": 0,
                    "message": "Aucune demande à synchroniser",
                    "details": [],
                    "warnings": []
                }
            
            print(f"📋 {len(requests)} demande(s) à vérifier\n")
            
            # 2. Récupérer tous les RV Gazelle pour Place des Arts
            gazelle_appointments = self._get_gazelle_appointments()
            
            print(f"📅 {len(gazelle_appointments)} RV Gazelle chargés\n")
            
            # 3. Matcher les demandes avec les RV
            matched_count = 0
            updated_count = 0
            details = []
            warnings = []
            
            for request in requests:
                request_id = request.get('id')
                appointment_date = request.get('appointment_date')
                room = request.get('room', '')
                time_str = request.get('time', '')
                
                # Chercher un RV correspondant
                matched_apt = self._find_matching_appointment(
                    request,
                    gazelle_appointments
                )
                
                if matched_apt:
                    matched_count += 1
                    apt_id = matched_apt.get('external_id')
                    apt_title = matched_apt.get('title', 'N/A')
                    # Le champ s'appelle 'technicien' dans gazelle_appointments (c'est l'ID Gazelle)
                    apt_technician = matched_apt.get('technicien')

                    print(f"✅ Match trouvé:")
                    print(f"   Demande: {appointment_date} {time_str} - Salle {room}")
                    print(f"   RV Gazelle: {apt_id} - {apt_title}")
                    if apt_technician:
                        print(f"   Technicien: {apt_technician}")

                    details.append({
                        "request_id": request_id,
                        "appointment_id": apt_id,
                        "appointment_title": apt_title,
                        "technician_id": apt_technician,
                        "matched": True
                    })

                    # Mettre à jour si pas dry_run
                    if not dry_run:
                        success = self._link_request_to_appointment(
                            request_id,
                            apt_id,
                            apt_technician
                        )
                        if success:
                            updated_count += 1
                            print(f"   💾 Lien enregistré" + (f" (tech: {apt_technician})" if apt_technician else ""))
                        else:
                            warnings.append(f"Erreur mise à jour demande {request_id}")
                    print()
                else:
                    print(f"⚠️  Pas de match:")
                    print(f"   Demande: {appointment_date} {time_str} - Salle {room}")
                    
                    details.append({
                        "request_id": request_id,
                        "appointment_id": None,
                        "matched": False,
                        "reason": "Aucun RV Gazelle correspondant trouvé"
                    })
                    print()
            
            print(f"\n{'='*70}")
            print(f"📊 RÉSULTAT SYNCHRONISATION")
            print(f"{'='*70}")
            print(f"   Demandes vérifiées: {len(requests)}")
            print(f"   Correspondances trouvées: {matched_count}")
            if not dry_run:
                print(f"   Demandes mises à jour: {updated_count}")
            print(f"{'='*70}\n")
            
            return {
                "success": True,
                "checked": len(requests),
                "matched": matched_count,
                "updated": updated_count if not dry_run else 0,
                "message": f"{matched_count}/{len(requests)} correspondances trouvées",
                "details": details,
                "warnings": warnings,
                "dry_run": dry_run
            }
            
        except Exception as e:
            logger.error(f"Erreur synchronisation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "checked": 0,
                "matched": 0,
                "updated": 0,
                "details": [],
                "warnings": []
            }
    
    def _get_unlinked_requests(self) -> List[Dict]:
        """Récupère toutes les demandes sans appointment_id."""
        try:
            result = self.storage.client.table('place_des_arts_requests')\
                .select('*')\
                .is_('appointment_id', 'null')\
                .order('appointment_date', desc=False)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération demandes: {e}")
            return []
    
    def _get_requests_by_ids(self, request_ids: List[str]) -> List[Dict]:
        """Récupère des demandes spécifiques par leurs IDs."""
        try:
            result = self.storage.client.table('place_des_arts_requests')\
                .select('*')\
                .in_('id', request_ids)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération demandes: {e}")
            return []
    
    def _get_gazelle_appointments(self) -> List[Dict]:
        """Récupère tous les RV Gazelle pour Place des Arts."""
        try:
            # Récupérer les RV des 60 derniers jours
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
            
            result = self.storage.client.table('gazelle_appointments')\
                .select('*')\
                .gte('start_datetime', f'{cutoff_date}T00:00:00')\
                .order('start_datetime')\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération RV Gazelle: {e}")
            return []
    
    def _find_matching_appointment(
        self,
        request: Dict,
        gazelle_appointments: List[Dict]
    ) -> Optional[Dict]:
        """
        Trouve un RV Gazelle correspondant à une demande PDA.
        
        Critères de matching:
        1. Même date (jour)
        2. Même heure (si disponible, tolérance ±2h)
        3. Même salle/location (si disponible)
        """
        request_date_str = request.get('appointment_date')
        if not request_date_str:
            return None
        
        try:
            # Parser la date de la demande
            if isinstance(request_date_str, str):
                if 'T' in request_date_str:
                    request_date = datetime.fromisoformat(request_date_str.replace('Z', '+00:00'))
                else:
                    request_date = datetime.fromisoformat(request_date_str)
            else:
                request_date = request_date_str
            
            request_date = request_date.date() if hasattr(request_date, 'date') else request_date
        except Exception as e:
            logger.warning(f"Erreur parsing date demande: {e}")
            return None
        
        request_time = request.get('time', '')
        request_room = request.get('room', '').upper().strip()
        
        # Filtrer les RV du même jour
        same_day_appointments = []
        for apt in gazelle_appointments:
            apt_datetime_str = apt.get('start_datetime')
            if not apt_datetime_str:
                continue
            
            try:
                apt_datetime = datetime.fromisoformat(apt_datetime_str.replace('Z', '+00:00'))
                apt_date = apt_datetime.date()
                
                if apt_date == request_date:
                    same_day_appointments.append(apt)
            except Exception as e:
                continue
        
        if not same_day_appointments:
            return None
        
        # Si plusieurs RV le même jour, affiner avec l'heure et la salle
        best_match = None
        best_score = 0
        
        for apt in same_day_appointments:
            score = 1  # Base: même jour
            
            # Bonus pour salle
            apt_location = apt.get('location', '').upper().strip()
            if request_room and apt_location:
                if request_room in apt_location or apt_location in request_room:
                    score += 2
            
            # Bonus pour heure (TODO: parser les heures et comparer)
            # Pour l'instant on prend le premier match du jour
            
            if score > best_score:
                best_score = score
                best_match = apt
        
        return best_match
    
    def _link_request_to_appointment(
        self,
        request_id: str,
        appointment_id: str,
        technician_id: Optional[str] = None
    ) -> bool:
        """Lie une demande PDA à un RV Gazelle et met à jour le technicien."""
        try:
            update_data = {
                'appointment_id': appointment_id,
                'status': 'CREATED_IN_GAZELLE',  # Demande liée à un RV Gazelle
                'updated_at': datetime.now().isoformat()
            }

            # Ajouter le technicien si disponible
            if technician_id:
                update_data['technician_id'] = technician_id

            result = self.storage.client.table('place_des_arts_requests')\
                .update(update_data)\
                .eq('id', request_id)\
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Erreur lien demande {request_id}: {e}")
            return False


# Fonction helper pour utilisation depuis CLI
def sync_place_des_arts(dry_run: bool = False) -> Dict:
    """
    Synchronise toutes les demandes Place des Arts avec Gazelle.
    
    Args:
        dry_run: Si True, simulation sans mise à jour
    
    Returns:
        Résultat de la synchronisation
    """
    service = GazelleSyncService()
    return service.sync_requests_with_gazelle(dry_run=dry_run)


if __name__ == "__main__":
    # Test du service
    import argparse
    
    parser = argparse.ArgumentParser(description="Synchroniser Place des Arts avec Gazelle")
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans mise à jour')
    args = parser.parse_args()
    
    result = sync_place_des_arts(dry_run=args.dry_run)
    
    print(f"\n✅ Synchronisation terminée")
    print(f"   Résultat: {result.get('message')}")
