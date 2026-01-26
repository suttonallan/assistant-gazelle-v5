#!/usr/bin/env python3
"""
Script pour vérifier et mettre à jour les demandes Place des Arts
qui ont des RV complétés dans Gazelle mais qui ne sont pas encore marquées.

Ce script :
1. Vérifie TOUTES les demandes (même sans appointment_id)
2. Cherche les RV Gazelle correspondants par date/salle
3. Vérifie si ces RV sont complétés
4. Met à jour les statuts en conséquence
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from modules.place_des_arts.services.gazelle_sync import GazelleSyncService

def check_all_requests_for_completed_appointments(dry_run: bool = True):
    """
    Vérifie toutes les demandes PDA pour trouver les RV complétés dans Gazelle.
    
    Args:
        dry_run: Si True, affiche seulement les résultats sans mettre à jour
    """
    print(f"\n{'='*70}")
    print(f"🔍 VÉRIFICATION DES DEMANDES AVEC RV COMPLÉTÉS")
    print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
    print(f"{'='*70}\n")
    
    storage = SupabaseStorage()
    sync_service = GazelleSyncService(storage)
    
    # 1. Récupérer TOUTES les demandes (pas seulement celles sans appointment_id)
    try:
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
    
    # 2. Récupérer tous les RV Gazelle pour Place des Arts
    gazelle_appointments = sync_service._get_gazelle_appointments()
    print(f"📅 {len(gazelle_appointments)} RV Gazelle chargés\n")
    
    # Créer un index par external_id pour les demandes déjà liées
    gazelle_by_id = {apt.get('external_id'): apt for apt in gazelle_appointments}
    
    # 3. Vérifier chaque demande
    found_completed = []
    found_unlinked = []
    found_not_created = []
    
    for request in all_requests:
        request_id = request.get('id')
        appointment_id = request.get('appointment_id')
        appointment_date = request.get('appointment_date', '')[:10] if request.get('appointment_date') else ''
        room = request.get('room', '')
        status = request.get('status', '')
        for_who = request.get('for_who', '')
        
        # Si déjà liée, vérifier le statut du RV
        if appointment_id:
            gazelle_apt = gazelle_by_id.get(appointment_id)
            if gazelle_apt:
                gazelle_status = gazelle_apt.get('status', '').upper()
                if gazelle_status in ('COMPLETE', 'COMPLETED'):
                    found_completed.append({
                        'request': request,
                        'appointment': gazelle_apt,
                        'reason': 'RV lié et complété'
                    })
        else:
            # Pas de lien, chercher un RV correspondant
            matched_apt = sync_service._find_matching_appointment(
                request,
                gazelle_appointments
            )
            
            if matched_apt:
                apt_id = matched_apt.get('external_id')
                gazelle_status = matched_apt.get('status', '').upper()
                
                if gazelle_status in ('COMPLETE', 'COMPLETED'):
                    # RV complété trouvé mais pas lié
                    found_unlinked.append({
                        'request': request,
                        'appointment': matched_apt,
                        'reason': 'RV complété trouvé mais pas lié'
                    })
                elif status != 'CREATED_IN_GAZELLE':
                    # RV trouvé mais pas marqué "créé gazelle"
                    found_not_created.append({
                        'request': request,
                        'appointment': matched_apt,
                        'reason': 'RV trouvé mais statut pas "créé gazelle"'
                    })
    
    # 4. Afficher les résultats
    print(f"\n{'='*70}")
    print(f"📊 RÉSULTATS")
    print(f"{'='*70}\n")
    
    if found_completed:
        print(f"✅ {len(found_completed)} demande(s) avec RV complété (déjà liées):")
        for item in found_completed:
            req = item['request']
            apt = item['appointment']
            print(f"   • {req.get('appointment_date', '')[:10]} - {req.get('room', '')} - {req.get('for_who', '')}")
            print(f"     Statut actuel: {req.get('status')}")
            print(f"     RV Gazelle: {apt.get('external_id')} - {apt.get('title', '')}")
            print(f"     → À mettre à jour: COMPLETED")
            print()
    
    if found_unlinked:
        print(f"🔗 {len(found_unlinked)} demande(s) avec RV complété (pas liées):")
        for item in found_unlinked:
            req = item['request']
            apt = item['appointment']
            print(f"   • {req.get('appointment_date', '')[:10]} - {req.get('room', '')} - {req.get('for_who', '')}")
            print(f"     Statut actuel: {req.get('status')}")
            print(f"     RV Gazelle: {apt.get('external_id')} - {apt.get('title', '')}")
            print(f"     → À lier et mettre à jour: COMPLETED")
            print()
    
    if found_not_created:
        print(f"⚠️  {len(found_not_created)} demande(s) avec RV trouvé mais pas 'créé gazelle':")
        for item in found_not_created:
            req = item['request']
            apt = item['appointment']
            print(f"   • {req.get('appointment_date', '')[:10]} - {req.get('room', '')} - {req.get('for_who', '')}")
            print(f"     Statut actuel: {req.get('status')}")
            print(f"     RV Gazelle: {apt.get('external_id')} - {apt.get('title', '')}")
            print(f"     → À lier et mettre à jour: CREATED_IN_GAZELLE")
            print()
    
    if not found_completed and not found_unlinked and not found_not_created:
        print("✅ Aucune demande nécessitant une mise à jour\n")
        return
    
    # 5. Mettre à jour si pas dry_run
    if not dry_run:
        print(f"\n{'='*70}")
        print(f"💾 MISE À JOUR")
        print(f"{'='*70}\n")
        
        updated_count = 0
        
        # Mettre à jour les demandes avec RV complété (déjà liées)
        for item in found_completed:
            req = item['request']
            apt = item['appointment']
            success = sync_service._update_request_status(req.get('id'), 'COMPLETED')
            if success:
                updated_count += 1
                print(f"✅ {req.get('appointment_date', '')[:10]} - {req.get('room', '')} → COMPLETED")
        
        # Lier et mettre à jour les demandes avec RV complété (pas liées)
        for item in found_unlinked:
            req = item['request']
            apt = item['appointment']
            apt_id = apt.get('external_id')
            apt_technician = apt.get('technicien')
            
            # Lier d'abord
            link_success = sync_service._link_request_to_appointment(
                req.get('id'),
                apt_id,
                apt_technician
            )
            
            # Puis marquer complété
            if link_success:
                status_success = sync_service._update_request_status(req.get('id'), 'COMPLETED')
                if status_success:
                    updated_count += 1
                    print(f"✅ {req.get('appointment_date', '')[:10]} - {req.get('room', '')} → Lié et COMPLETED")
        
        # Lier et mettre à jour les demandes avec RV trouvé mais pas "créé gazelle"
        for item in found_not_created:
            req = item['request']
            apt = item['appointment']
            apt_id = apt.get('external_id')
            apt_technician = apt.get('technicien')
            
            # Lier et mettre à jour le statut
            link_success = sync_service._link_request_to_appointment(
                req.get('id'),
                apt_id,
                apt_technician
            )
            
            if link_success:
                updated_count += 1
                print(f"✅ {req.get('appointment_date', '')[:10]} - {req.get('room', '')} → Lié et CREATED_IN_GAZELLE")
        
        print(f"\n✅ {updated_count} demande(s) mise(s) à jour\n")
    else:
        print(f"\n💡 Mode DRY RUN - Aucune mise à jour effectuée")
        print(f"   Relancez avec --apply pour effectuer les mises à jour\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Vérifier les demandes PDA avec RV complétés dans Gazelle"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Effectuer les mises à jour (par défaut: simulation)'
    )
    
    args = parser.parse_args()
    
    check_all_requests_for_completed_appointments(dry_run=not args.apply)
