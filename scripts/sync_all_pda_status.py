#!/usr/bin/env python3
"""
Script de synchronisation complète des statuts Place des Arts.

Ce script :
1. Synchronise toutes les demandes avec les RV Gazelle (lie les appointment_id)
2. Vérifie les RV complétés et met à jour les statuts COMPLETED
3. Enrichit les techniciens depuis les RV Gazelle
4. Met à jour les statuts CREATED_IN_GAZELLE pour les demandes avec technicien actif
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.place_des_arts.services.gazelle_sync import GazelleSyncService

def sync_all_statuses():
    """Synchronise tous les statuts des demandes Place des Arts."""
    print("\n" + "="*70)
    print("🔄 SYNCHRONISATION COMPLÈTE DES STATUTS PLACE DES ARTS")
    print("="*70 + "\n")
    
    storage = SupabaseStorage()
    sync_service = GazelleSyncService(storage)
    
    # 1. Synchroniser toutes les demandes (lier les RV)
    print("📋 Étape 1: Synchronisation des demandes avec les RV Gazelle...")
    print("-" * 70)
    sync_result = sync_service.sync_requests_with_gazelle(
        request_ids=None,  # Toutes les demandes
        dry_run=False
    )
    
    print(f"\n✅ Synchronisation terminée:")
    print(f"   - Demandes vérifiées: {sync_result.get('checked', 0)}")
    print(f"   - Correspondances trouvées: {sync_result.get('matched', 0)}")
    print(f"   - Demandes mises à jour: {sync_result.get('updated', 0)}")
    print(f"   - Demandes complétées: {sync_result.get('completed', 0)}")
    
    # 2. Vérifier les RV complétés (y compris ceux non liés)
    print("\n📋 Étape 2: Vérification des RV complétés...")
    print("-" * 70)
    
    try:
        # Récupérer toutes les demandes non complétées
        result = storage.client.table('place_des_arts_requests')\
            .select('*')\
            .neq('status', 'COMPLETED')\
            .neq('status', 'BILLED')\
            .order('appointment_date', desc=False)\
            .execute()
        
        all_requests = result.data if result.data else []
    except Exception as e:
        print(f"❌ Erreur récupération demandes: {e}")
        return
    
    if not all_requests:
        print("✅ Aucune demande à vérifier\n")
        return
    
    print(f"📋 {len(all_requests)} demande(s) à vérifier\n")
    
    # Récupérer tous les RV Gazelle
    gazelle_appointments = sync_service._get_gazelle_appointments()
    gazelle_by_id = {apt.get('external_id'): apt for apt in gazelle_appointments}
    
    # Vérifier chaque demande
    updated_completed = 0
    updated_technicians = 0
    
    for request in all_requests:
        request_id = request.get('id')
        appointment_id = request.get('appointment_id')
        status = request.get('status', '')
        technician_id = request.get('technician_id')
        
        # Vérifier si le RV est complété
        if appointment_id:
            gazelle_apt = gazelle_by_id.get(appointment_id)
            if gazelle_apt:
                gazelle_status = gazelle_apt.get('status', '').upper()
                if gazelle_status in ('COMPLETE', 'COMPLETED'):
                    # Mettre à jour le statut à COMPLETED
                    success = sync_service._update_request_status(request_id, 'COMPLETED')
                    if success:
                        updated_completed += 1
                        print(f"✅ {request.get('appointment_date', '')[:10]} - {request.get('room', '')} → COMPLETED")
        
        # Enrichir le technicien depuis le RV Gazelle si manquant
        if appointment_id and not technician_id:
            gazelle_apt = gazelle_by_id.get(appointment_id)
            if gazelle_apt:
                tech_from_gazelle = gazelle_apt.get('technicien')
                if tech_from_gazelle and tech_from_gazelle in sync_service.REAL_TECHNICIAN_IDS:
                    # Mettre à jour le technicien et le statut si nécessaire
                    update_data = {
                        'technician_id': tech_from_gazelle,
                        'updated_at': datetime.now().isoformat()
                    }
                    if status != 'CREATED_IN_GAZELLE':
                        update_data['status'] = 'CREATED_IN_GAZELLE'
                    
                    try:
                        result = storage.client.table('place_des_arts_requests')\
                            .update(update_data)\
                            .eq('id', request_id)\
                            .execute()
                        
                        if result.data:
                            updated_technicians += 1
                            print(f"✅ {request.get('appointment_date', '')[:10]} - {request.get('room', '')} → Technicien {tech_from_gazelle} ajouté")
                    except Exception as e:
                        print(f"⚠️  Erreur mise à jour technicien pour {request_id}: {e}")
        
        # Si pas de appointment_id, chercher un RV correspondant
        elif not appointment_id:
            matched_apt = sync_service._find_matching_appointment(
                request,
                gazelle_appointments
            )
            
            if matched_apt:
                apt_id = matched_apt.get('external_id')
                tech_from_gazelle = matched_apt.get('technicien')
                gazelle_status = matched_apt.get('status', '').upper()
                
                # Lier le RV
                is_real_tech = tech_from_gazelle in sync_service.REAL_TECHNICIAN_IDS
                
                if gazelle_status in ('COMPLETE', 'COMPLETED'):
                    # RV complété, lier et marquer complété
                    link_success = sync_service._link_request_to_appointment(
                        request_id,
                        apt_id,
                        tech_from_gazelle
                    )
                    if link_success:
                        status_success = sync_service._update_request_status(request_id, 'COMPLETED')
                        if status_success:
                            updated_completed += 1
                            print(f"✅ {request.get('appointment_date', '')[:10]} - {request.get('room', '')} → Lié et COMPLETED")
                elif is_real_tech:
                    # RV trouvé avec technicien actif, lier et marquer CREATED_IN_GAZELLE
                    link_success = sync_service._link_request_to_appointment(
                        request_id,
                        apt_id,
                        tech_from_gazelle
                    )
                    if link_success:
                        updated_technicians += 1
                        print(f"✅ {request.get('appointment_date', '')[:10]} - {request.get('room', '')} → Lié et CREATED_IN_GAZELLE")
    
    print(f"\n✅ Vérification terminée:")
    print(f"   - Demandes complétées: {updated_completed}")
    print(f"   - Techniciens ajoutés/mis à jour: {updated_technicians}")
    
    print("\n" + "="*70)
    print("✅ SYNCHRONISATION COMPLÈTE TERMINÉE")
    print("="*70 + "\n")
    print(f"Résumé:")
    print(f"  - Synchronisation initiale: {sync_result.get('updated', 0)} demande(s) mise(s) à jour")
    print(f"  - RV complétés détectés: {updated_completed} demande(s)")
    print(f"  - Techniciens enrichis: {updated_technicians} demande(s)")
    print()


if __name__ == "__main__":
    from datetime import datetime
    sync_all_statuses()
