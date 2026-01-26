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
                    is_real_tech = apt_technician in self.REAL_TECHNICIAN_IDS

                    print(f"✅ Match trouvé:")
                    print(f"   Demande: {appointment_date} {time_str} - Salle {room}")
                    print(f"   RV Gazelle: {apt_id} - {apt_title}")
                    if apt_technician:
                        if is_real_tech:
                            print(f"   Technicien: {apt_technician}")
                        else:
                            print(f"   Technicien: À attribuer (pas encore assigné)")

                    details.append({
                        "request_id": request_id,
                        "appointment_id": apt_id,
                        "appointment_title": apt_title,
                        "technician_id": apt_technician if is_real_tech else None,
                        "matched": True,
                        "has_real_technician": is_real_tech
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
                            if is_real_tech:
                                print(f"   💾 Statut: CREATED_IN_GAZELLE (tech: {apt_technician})")
                            else:
                                print(f"   💾 RV lié avec 'À attribuer' (statut: CREATED_IN_GAZELLE)")
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
            
            # 4. Vérifier les demandes déjà liées pour mise à jour statut COMPLETED
            # ET synchroniser les techniciens depuis Gazelle (source de vérité)
            completed_count = 0
            tech_sync_count = 0
            if not request_ids:  # Seulement en mode "sync all"
                linked_requests = self._get_linked_not_completed_requests()
                if linked_requests:
                    print(f"\n{'='*70}")
                    print(f"🔍 VÉRIFICATION DES RV COMPLÉTÉS ET SYNCHRONISATION TECHNICIENS")
                    print(f"{'='*70}")
                    print(f"   {len(linked_requests)} demande(s) liées à vérifier\n")

                    # Créer un index des RV Gazelle par external_id
                    gazelle_by_id = {apt.get('external_id'): apt for apt in gazelle_appointments}

                    for request in linked_requests:
                        request_id = request.get('id')
                        apt_id = request.get('appointment_id')
                        appointment_date = request.get('appointment_date', '')[:10] if request.get('appointment_date') else ''
                        room = request.get('room', '')
                        current_tech = request.get('technician_id')

                        # Trouver le RV Gazelle correspondant
                        gazelle_apt = gazelle_by_id.get(apt_id)
                        if gazelle_apt:
                            gazelle_status = gazelle_apt.get('status', '').upper()
                            gazelle_tech = gazelle_apt.get('technicien')
                            
                            # Synchroniser le technicien depuis Gazelle (source de vérité)
                            if gazelle_tech and current_tech != gazelle_tech:
                                if not dry_run:
                                    try:
                                        self.storage.client.table('place_des_arts_requests')\
                                            .update({
                                                'technician_id': gazelle_tech,
                                                'updated_at': datetime.now().isoformat()
                                            })\
                                            .eq('id', request_id)\
                                            .execute()
                                        tech_sync_count += 1
                                        tech_name = 'À attribuer' if gazelle_tech == 'usr_HihJsEgkmpTEziJo' else gazelle_tech
                                        print(f"🔄 Technicien synchronisé: {appointment_date} - {room} → {tech_name}")
                                    except Exception as e:
                                        logger.warning(f"Erreur sync technicien pour {request_id}: {e}")
                            
                            # Vérifier si complété
                            if gazelle_status in ('COMPLETE', 'COMPLETED'):
                                print(f"✅ RV complété trouvé:")
                                print(f"   Demande: {appointment_date} - Salle {room}")
                                print(f"   RV Gazelle: {apt_id}")

                                if not dry_run:
                                    success = self._update_request_status(request_id, 'COMPLETED')
                                    if success:
                                        completed_count += 1
                                        print(f"   💾 Statut mis à jour: COMPLETED")
                                    else:
                                        warnings.append(f"Erreur mise à jour statut demande {request_id}")
                                print()

                    if completed_count > 0 or tech_sync_count > 0 or dry_run:
                        if tech_sync_count > 0:
                            print(f"   {tech_sync_count} technicien(s) synchronisé(s) depuis Gazelle")
                        if completed_count > 0:
                            print(f"   {completed_count} demande(s) marquée(s) comme complétée(s)")
                        print()

            print(f"\n{'='*70}")
            print(f"📊 RÉSULTAT SYNCHRONISATION")
            print(f"{'='*70}")
            print(f"   Demandes vérifiées: {len(requests)}")
            print(f"   Correspondances trouvées: {matched_count}")
            if not dry_run:
                print(f"   Demandes mises à jour: {updated_count}")
                print(f"   Demandes complétées: {completed_count}")
            print(f"{'='*70}\n")

            return {
                "success": True,
                "checked": len(requests),
                "matched": matched_count,
                "updated": updated_count if not dry_run else 0,
                "completed": completed_count if not dry_run else 0,
                "message": f"{matched_count}/{len(requests)} correspondances, {completed_count} complétées",
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

    def _get_linked_not_completed_requests(self) -> List[Dict]:
        """Récupère les demandes liées à un RV Gazelle mais pas encore complétées."""
        try:
            result = self.storage.client.table('place_des_arts_requests')\
                .select('*')\
                .not_.is_('appointment_id', 'null')\
                .neq('status', 'COMPLETED')\
                .neq('status', 'BILLED')\
                .order('appointment_date', desc=False)\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération demandes liées: {e}")
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
            # Utiliser appointment_date (pas start_datetime qui peut être NULL)
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

            result = self.storage.client.table('gazelle_appointments')\
                .select('*')\
                .gte('appointment_date', cutoff_date)\
                .order('appointment_date')\
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

        Critères de matching (scoring):
        1. OBLIGATOIRE: Même jour
        2. +10 pts: "Place des Arts" dans le titre
        3. +3 pts: Mots-clés de for_who dans le titre
        4. +5 pts: Salle correspond dans location ou description
        5. +3 pts: Salle dans le titre
        6. +4 pts: Heure correspond (±2h)
        """
        import re

        request_date_str = request.get('appointment_date')
        if not request_date_str:
            return None

        # Normaliser la date de la demande en YYYY-MM-DD
        request_date = request_date_str[:10] if isinstance(request_date_str, str) else str(request_date_str)[:10]

        request_time = request.get('time', '')
        request_room = (request.get('room', '') or '').upper().strip()
        request_for_who = (request.get('for_who', '') or '').upper().strip()

        # Filtrer les RV du même jour
        # Note: Les RV Gazelle ont appointment_date (YYYY-MM-DD) ET appointment_time séparés
        same_day_appointments = []
        for apt in gazelle_appointments:
            # Utiliser appointment_date (pas start_datetime qui peut être NULL)
            apt_date_str = apt.get('appointment_date')
            if not apt_date_str:
                # Fallback sur start_datetime si disponible
                apt_datetime_str = apt.get('start_datetime')
                if apt_datetime_str:
                    apt_date_str = apt_datetime_str[:10]
                else:
                    continue

            # Normaliser en YYYY-MM-DD
            apt_date_str = apt_date_str[:10] if apt_date_str else ''

            if apt_date_str == request_date:
                # Extraire l'heure
                apt_hour = 0
                apt_time_str = apt.get('appointment_time', '')
                if apt_time_str:
                    try:
                        apt_hour = int(apt_time_str.split(':')[0])
                    except:
                        pass
                same_day_appointments.append((apt, apt_hour))

        if not same_day_appointments:
            return None

        # Scorer chaque RV candidat
        best_match = None
        best_score = 0

        for apt, apt_hour in same_day_appointments:
            score = 1  # Base: même jour

            apt_title = (apt.get('title', '') or '').upper()
            apt_location = (apt.get('location', '') or '').upper().strip()
            apt_description = (apt.get('description', '') or '').upper()
            apt_notes = (apt.get('notes', '') or '').upper()

            # CRITÈRE 1: Titre contient "Place des Arts" (priorité haute)
            if 'PLACE DES ARTS' in apt_title:
                score += 10

            # CRITÈRE 2: Titre contient des mots-clés de la demande (for_who)
            if request_for_who:
                # Extraire les mots significatifs (plus de 3 caractères)
                for_who_words = [w for w in request_for_who.split() if len(w) > 3]
                for word in for_who_words:
                    if word in apt_title:
                        score += 3
                        break  # Un seul mot suffit

            # CRITÈRE 3: Salle correspond
            # Vérifier dans location, description, notes
            all_text = apt_location + ' ' + apt_description + ' ' + apt_notes
            if request_room:
                if request_room in all_text:
                    score += 5
                # Aussi vérifier dans le titre
                if request_room in apt_title:
                    score += 3

            # CRITÈRE 4: Heure correspond (si disponible)
            if request_time and apt_hour > 0:
                # Parser l'heure de la demande (format "8h", "18h", "avant 9h", etc.)
                time_match = re.search(r'(\d{1,2})h?', str(request_time).upper())
                if time_match:
                    request_hour = int(time_match.group(1))
                    # Tolérance de ±2h
                    if abs(apt_hour - request_hour) <= 2:
                        score += 4

            if score > best_score:
                best_score = score
                best_match = apt

        return best_match
    
    # IDs des vrais techniciens (pas "À attribuer")
    # Inclure aussi les IDs alternatifs qui correspondent aux mêmes techniciens
    REAL_TECHNICIAN_IDS = {
        'usr_HcCiFk7o0vZ9xAI0',  # Nick
        'usr_ofYggsCDt2JAVeNP',  # Allan
        'usr_ReUSmIJmBF86ilY1',  # JP (ID standard)
        'usr_QmEpdeM2xMgZVkDS',  # JP (ID alternatif si différent dans Gazelle)
    }
    
    # Mapping pour normaliser les IDs alternatifs vers les IDs standards
    TECH_ID_NORMALIZATION = {
        'usr_QmEpdeM2xMgZVkDS': 'usr_ReUSmIJmBF86ilY1',  # ID alternatif JP → ID standard JP
    }
    
    def _normalize_technician_id(self, tech_id: Optional[str]) -> Optional[str]:
        """Normalise un ID technicien (convertit les IDs alternatifs vers les standards)."""
        if not tech_id:
            return None
        return self.TECH_ID_NORMALIZATION.get(tech_id, tech_id)

    def _link_request_to_appointment(
        self,
        request_id: str,
        appointment_id: str,
        technician_id: Optional[str] = None
    ) -> bool:
        """Lie une demande PDA à un RV Gazelle et met à jour le technicien."""
        try:
            # Vérifier si c'est un vrai technicien (pas "À attribuer")
            is_real_technician = technician_id in self.REAL_TECHNICIAN_IDS

            update_data = {
                'appointment_id': appointment_id,
                'updated_at': datetime.now().isoformat()
            }

            # Toujours mettre à jour le technicien depuis Gazelle (source de vérité)
            if technician_id:
                update_data['technician_id'] = technician_id
            
            # Marquer "CREATED_IN_GAZELLE" si le RV existe (même avec "À attribuer")
            update_data['status'] = 'CREATED_IN_GAZELLE'

            result = self.storage.client.table('place_des_arts_requests')\
                .update(update_data)\
                .eq('id', request_id)\
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Erreur lien demande {request_id}: {e}")
            return False

    def _update_request_status(self, request_id: str, status: str) -> bool:
        """Met à jour le statut d'une demande PDA."""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }

            result = self.storage.client.table('place_des_arts_requests')\
                .update(update_data)\
                .eq('id', request_id)\
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Erreur mise à jour statut demande {request_id}: {e}")
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
