#!/usr/bin/env python3
"""
Script pour mettre à jour les statuts des demandes Place des Arts
selon l'existence du RV dans Gazelle.

Si un appointment_id existe et que le RV est trouvé dans Gazelle,
le statut doit être CREATED_IN_GAZELLE (même si technicien est "À attribuer").
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from datetime import datetime

def fix_statuses_from_gazelle(dry_run: bool = True):
    """Met à jour les statuts selon l'existence des RV dans Gazelle."""
    print("\n" + "="*70)
    print("🔧 MISE À JOUR DES STATUTS SELON GAZELLE")
    print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
    print("="*70 + "\n")
    
    storage = SupabaseStorage()
    
    # Récupérer toutes les demandes avec appointment_id mais statut pas CREATED_IN_GAZELLE
    try:
        result = storage.client.table('place_des_arts_requests')\
            .select('id,appointment_id,status,technician_id')\
            .not_.is_('appointment_id', 'null')\
            .neq('status', 'CREATED_IN_GAZELLE')\
            .neq('status', 'COMPLETED')\
            .neq('status', 'BILLED')\
            .execute()
        
        requests_to_check = result.data if result.data else []
    except Exception as e:
        print(f"❌ Erreur récupération demandes: {e}")
        return
    
    if not requests_to_check:
        print("✅ Aucune demande à vérifier\n")
        return
    
    print(f"📋 {len(requests_to_check)} demande(s) avec appointment_id mais statut pas CREATED_IN_GAZELLE\n")
    
    # Récupérer les appointment_ids
    appointment_ids = [r.get('appointment_id') for r in requests_to_check if r.get('appointment_id')]
    
    if not appointment_ids:
        print("✅ Aucun appointment_id à vérifier\n")
        return
    
    # Vérifier dans Gazelle
    try:
        gazelle_appts = storage.client.table('gazelle_appointments')\
            .select('external_id,technicien')\
            .in_('external_id', appointment_ids)\
            .execute()
        
        found_appt_ids = {apt.get('external_id') for apt in (gazelle_appts.data or [])}
        tech_by_appt = {apt.get('external_id'): apt.get('technicien') for apt in (gazelle_appts.data or []) if apt.get('technicien')}
    except Exception as e:
        print(f"❌ Erreur récupération RV Gazelle: {e}")
        return
    
    print(f"📅 {len(found_appt_ids)} RV trouvé(s) dans Gazelle\n")
    
    # Mettre à jour les statuts
    updated_count = 0
    
    for request in requests_to_check:
        request_id = request.get('id')
        appointment_id = request.get('appointment_id')
        current_status = request.get('status')
        
        if appointment_id in found_appt_ids:
            # Le RV existe dans Gazelle, mettre à jour le statut
            print(f"✅ {appointment_id[:20]}... - Statut actuel: {current_status}")
            print(f"   → À mettre à jour: CREATED_IN_GAZELLE")
            
            # Enrichir aussi le technicien si présent dans Gazelle
            tech_from_gazelle = tech_by_appt.get(appointment_id)
            update_data = {
                'status': 'CREATED_IN_GAZELLE',
                'updated_at': datetime.now().isoformat()
            }
            
            if tech_from_gazelle and not request.get('technician_id'):
                update_data['technician_id'] = tech_from_gazelle
                print(f"   → Technicien enrichi: {tech_from_gazelle}")
            
            if not dry_run:
                try:
                    result = storage.client.table('place_des_arts_requests')\
                        .update(update_data)\
                        .eq('id', request_id)\
                        .execute()
                    
                    if result.data:
                        updated_count += 1
                        print(f"   💾 Mis à jour")
                except Exception as e:
                    print(f"   ❌ Erreur: {e}")
            print()
    
    print("="*70)
    if dry_run:
        print(f"💡 Mode DRY RUN - {len([r for r in requests_to_check if r.get('appointment_id') in found_appt_ids])} demande(s) seraient mises à jour")
        print(f"   Relancez avec --apply pour effectuer les mises à jour\n")
    else:
        print(f"✅ {updated_count} demande(s) mise(s) à jour\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Mettre à jour les statuts PDA selon l'existence des RV dans Gazelle"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Effectuer les mises à jour (par défaut: simulation)'
    )
    
    args = parser.parse_args()
    
    fix_statuses_from_gazelle(dry_run=not args.apply)
