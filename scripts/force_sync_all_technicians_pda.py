#!/usr/bin/env python3
"""
Script pour forcer la synchronisation complète de TOUS les techniciens
depuis Gazelle vers PDA pour toutes les demandes liées.

Gazelle est la source de vérité absolue pour les techniciens.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from datetime import datetime

def force_sync_all_technicians(dry_run: bool = True):
    """Force la synchronisation de tous les techniciens depuis Gazelle."""
    print("\n" + "="*70)
    print("🔧 SYNCHRONISATION FORCÉE DE TOUS LES TECHNICIENS")
    print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
    print("="*70 + "\n")

    storage = SupabaseStorage()

    # IDs des techniciens
    REAL_TECHNICIAN_IDS = {
        'usr_HcCiFk7o0vZ9xAI0': 'Nick',
        'usr_ofYggsCDt2JAVeNP': 'Allan',
        'usr_ReUSmIJmBF86ilY1': 'JP',
        'usr_HihJsEgkmpTEziJo': 'À attribuer',
        'usr_QmEpdeM2xMgZVkDS': 'JP (alt)'
    }

    # Récupérer TOUTES les demandes avec appointment_id
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

    # Récupérer TOUS les appointment_ids
    appointment_ids = [r.get('appointment_id') for r in requests if r.get('appointment_id')]

    if not appointment_ids:
        print("✅ Aucun appointment_id à vérifier\n")
        return

    # Récupérer TOUS les techniciens depuis Gazelle
    try:
        gazelle_appts = storage.client.table('gazelle_appointments')\
            .select('external_id,technicien')\
            .in_('external_id', appointment_ids)\
            .execute()

        tech_by_appt = {apt.get('external_id'): apt.get('technicien')
                       for apt in (gazelle_appts.data or []) if apt.get('technicien')}
    except Exception as e:
        print(f"❌ Erreur récupération RV Gazelle: {e}")
        return

    print(f"📅 {len(tech_by_appt)} RV trouvé(s) dans Gazelle avec technicien\n")

    updated_count = 0
    inconsistencies = []

    for request in requests:
        request_id = request.get('id')
        appointment_id = request.get('appointment_id')
        current_tech = request.get('technician_id')
        gazelle_tech = tech_by_appt.get(appointment_id)

        if gazelle_tech:
            # Gazelle a un technicien - c'est la source de vérité
            if current_tech != gazelle_tech:
                current_name = REAL_TECHNICIAN_IDS.get(current_tech, current_tech) if current_tech else 'Aucun'
                gazelle_name = REAL_TECHNICIAN_IDS.get(gazelle_tech, gazelle_tech)

                inconsistencies.append({
                    'id': request_id,
                    'date': request.get('appointment_date', '')[:10],
                    'room': request.get('room', ''),
                    'for_who': request.get('for_who', ''),
                    'pda_tech': current_name,
                    'gazelle_tech': gazelle_name
                })

                if not dry_run:
                    # FORCER la mise à jour
                    try:
                        storage.client.table('place_des_arts_requests')\
                            .update({
                                'technician_id': gazelle_tech,
                                'updated_at': datetime.now().isoformat()
                            })\
                            .eq('id', request_id)\
                            .execute()
                        updated_count += 1
                    except Exception as e:
                        print(f"❌ Erreur mise à jour {request_id}: {e}")
        elif not current_tech and gazelle_tech:
            # Technicien manquant dans PDA mais présent dans Gazelle
            gazelle_name = REAL_TECHNICIAN_IDS.get(gazelle_tech, gazelle_tech)
            inconsistencies.append({
                'id': request_id,
                'date': request.get('appointment_date', '')[:10],
                'room': request.get('room', ''),
                'for_who': request.get('for_who', ''),
                'pda_tech': 'Aucun',
                'gazelle_tech': gazelle_name
            })

            if not dry_run:
                try:
                    storage.client.table('place_des_arts_requests')\
                        .update({
                            'technician_id': gazelle_tech,
                            'updated_at': datetime.now().isoformat()
                        })\
                        .eq('id', request_id)\
                        .execute()
                    updated_count += 1
                except Exception as e:
                    print(f"❌ Erreur ajout technicien {request_id}: {e}")

    print("="*70)
    if inconsistencies:
        print(f"📋 {len(inconsistencies)} incohérence(s) détectée(s):\n")
        for inc in inconsistencies[:20]:  # Afficher les 20 premières
            print(f"   - {inc['date']} | {inc['room']} | {inc['for_who'][:40]}")
            print(f"     PDA: {inc['pda_tech']} → Gazelle: {inc['gazelle_tech']}")
        if len(inconsistencies) > 20:
            print(f"   ... et {len(inconsistencies) - 20} autres")
        print()

    if dry_run:
        print(f"💡 Mode DRY RUN - {len(inconsistencies)} demande(s) seraient mises à jour")
        print(f"   Relancez avec --apply pour effectuer les mises à jour\n")
    else:
        print(f"✅ {updated_count} demande(s) mise(s) à jour\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Forcer la synchronisation de tous les techniciens depuis Gazelle"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Effectuer les mises à jour (par défaut: simulation)'
    )

    args = parser.parse_args()

    force_sync_all_technicians(dry_run=not args.apply)
