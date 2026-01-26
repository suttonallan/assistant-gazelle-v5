#!/usr/bin/env python3
"""
Script pour forcer la synchronisation des techniciens depuis Gazelle vers PDA.

Gazelle est la source de vérité : met à jour tous les techniciens dans PDA
pour correspondre à ceux dans Gazelle.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from datetime import datetime

def fix_technician_sync(dry_run: bool = True):
    """Force la synchronisation des techniciens depuis Gazelle."""
    print("\n" + "="*70)
    print("🔧 SYNCHRONISATION FORCÉE DES TECHNICIENS")
    print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
    print("="*70 + "\n")
    
    storage = SupabaseStorage()
    
    # Récupérer toutes les demandes avec appointment_id
    try:
        result = storage.client.table('place_des_arts_requests')\
            .select('id,appointment_id,technician_id,appointment_date,room,for_who')\
            .not_.is_('appointment_id', 'null')\
            .execute()
        
        requests = result.data if result.data else []
    except Exception as e:
        print(f"❌ Erreur récupération demandes: {e}")
        return
    
    if not requests:
        print("✅ Aucune demande avec appointment_id\n")
        return
    
    print(f"📋 {len(requests)} demande(s) avec appointment_id\n")
    
    # Récupérer les appointment_ids
    appointment_ids = [r.get('appointment_id') for r in requests if r.get('appointment_id')]
    
    # Récupérer les techniciens depuis Gazelle
    try:
        gazelle_appts = storage.client.table('gazelle_appointments')\
            .select('external_id,technicien')\
            .in_('external_id', appointment_ids)\
            .execute()
        
        tech_by_appt = {apt.get('external_id'): apt.get('technicien') for apt in (gazelle_appts.data or []) if apt.get('technicien')}
    except Exception as e:
        print(f"❌ Erreur récupération RV Gazelle: {e}")
        return
    
    print(f"📅 {len(tech_by_appt)} RV trouvé(s) dans Gazelle avec technicien\n")
    
    # IDs des techniciens
    REAL_TECHNICIAN_IDS = {
        'usr_HcCiFk7o0vZ9xAI0': 'Nick',
        'usr_ofYggsCDt2JAVeNP': 'Allan',
        'usr_ReUSmIJmBF86ilY1': 'JP',
        'usr_HihJsEgkmpTEziJo': 'À attribuer'
    }
    
    updated_count = 0
    
    for request in requests:
        request_id = request.get('id')
        appointment_id = request.get('appointment_id')
        current_tech = request.get('technician_id')
        gazelle_tech = tech_by_appt.get(appointment_id)
        
        if gazelle_tech and current_tech != gazelle_tech:
            # Incohérence détectée
            current_name = REAL_TECHNICIAN_IDS.get(current_tech, current_tech) if current_tech else 'Aucun'
            gazelle_name = REAL_TECHNICIAN_IDS.get(gazelle_tech, gazelle_tech)
            
            print(f"⚠️  Incohérence détectée:")
            print(f"   {request.get('appointment_date', '')[:10]} - {request.get('room', '')} - {request.get('for_who', '')}")
            print(f"   PDA: {current_name} ({current_tech})")
            print(f"   Gazelle: {gazelle_name} ({gazelle_tech})")
            print(f"   → À mettre à jour: {gazelle_name}")
            
            if not dry_run:
                try:
                    update_result = storage.client.table('place_des_arts_requests')\
                        .update({
                            'technician_id': gazelle_tech,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', request_id)\
                        .execute()
                    
                    if update_result.data:
                        updated_count += 1
                        print(f"   💾 Mis à jour")
                except Exception as e:
                    print(f"   ❌ Erreur: {e}")
            print()
        elif not current_tech and gazelle_tech:
            # Pas de technicien dans PDA mais présent dans Gazelle
            gazelle_name = REAL_TECHNICIAN_IDS.get(gazelle_tech, gazelle_tech)
            print(f"✅ Technicien manquant:")
            print(f"   {request.get('appointment_date', '')[:10]} - {request.get('room', '')} - {request.get('for_who', '')}")
            print(f"   Gazelle: {gazelle_name} ({gazelle_tech})")
            print(f"   → À ajouter: {gazelle_name}")
            
            if not dry_run:
                try:
                    update_result = storage.client.table('place_des_arts_requests')\
                        .update({
                            'technician_id': gazelle_tech,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', request_id)\
                        .execute()
                    
                    if update_result.data:
                        updated_count += 1
                        print(f"   💾 Mis à jour")
                except Exception as e:
                    print(f"   ❌ Erreur: {e}")
            print()
    
    print("="*70)
    if dry_run:
        print(f"💡 Mode DRY RUN - {updated_count} demande(s) seraient mises à jour")
        print(f"   Relancez avec --apply pour effectuer les mises à jour\n")
    else:
        print(f"✅ {updated_count} demande(s) mise(s) à jour\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Forcer la synchronisation des techniciens depuis Gazelle"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Effectuer les mises à jour (par défaut: simulation)'
    )
    
    args = parser.parse_args()
    
    fix_technician_sync(dry_run=not args.apply)
