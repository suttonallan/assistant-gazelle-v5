#!/usr/bin/env python3
"""
Script de correction complète des demandes PDA historiques.

Ce script effectue une synchronisation complète des demandes Place des Arts
(décembre 2025 et antérieures) avec les RV Gazelle:

1. LINKING: Trouve et lie les demandes sans appointment_id aux RV Gazelle correspondants
2. TECHNICIENS: Synchronise tous les techniciens depuis Gazelle (source de vérité)
3. STATUTS: Met à jour les statuts (COMPLETED si RV complété, CREATED_IN_GAZELLE sinon)

Gazelle est la SOURCE DE VÉRITÉ ABSOLUE pour:
- Les techniciens assignés
- Les statuts des RV
- L'existence des RV

Usage:
    python fix_historical_pda_requests.py                    # Dry run (simulation)
    python fix_historical_pda_requests.py --apply            # Exécution réelle
    python fix_historical_pda_requests.py --before 2026-01-15  # Traiter jusqu'à une date spécifique
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage


# IDs des techniciens
REAL_TECHNICIAN_IDS = {
    'usr_HcCiFk7o0vZ9xAI0': 'Nick',      # Nicolas Lessard
    'usr_ofYggsCDt2JAVeNP': 'Allan',     # Allan Sutton
    'usr_ReUSmIJmBF86ilY1': 'JP',        # Jean-Philippe Reny
    'usr_HihJsEgkmpTEziJo': 'À attribuer',  # Placeholder
    'usr_QmEpdeM2xMgZVkDS': 'JP (alt)',  # ID alternatif pour JP
}

# Mapping pour normaliser les IDs alternatifs
TECH_ID_NORMALIZATION = {
    'usr_QmEpdeM2xMgZVkDS': 'usr_ReUSmIJmBF86ilY1',  # JP alt → JP standard
}


def get_tech_name(tech_id: Optional[str]) -> str:
    """Retourne le nom du technicien ou 'Aucun' si None."""
    if not tech_id:
        return 'Aucun'
    return REAL_TECHNICIAN_IDS.get(tech_id, tech_id)


def normalize_tech_id(tech_id: Optional[str]) -> Optional[str]:
    """Normalise un ID technicien (convertit les IDs alternatifs)."""
    if not tech_id:
        return None
    return TECH_ID_NORMALIZATION.get(tech_id, tech_id)


def find_matching_appointment(
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
    request_date_str = request.get('appointment_date')
    if not request_date_str:
        return None

    try:
        # Parser la date de la demande (format YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
        if isinstance(request_date_str, str):
            request_date_str = request_date_str[:10]  # Prendre seulement YYYY-MM-DD
        request_date = request_date_str
    except Exception as e:
        print(f"⚠️  Erreur parsing date demande: {e}")
        return None

    request_room = (request.get('room', '') or '').upper().strip()
    request_for_who = (request.get('for_who', '') or '').upper().strip()
    request_time = request.get('time', '')

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
            # Construire un datetime pour l'heure
            apt_time_str = apt.get('appointment_time', '')
            apt_hour = 0
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


def fix_historical_pda_requests(before_date: str = "2026-01-01", dry_run: bool = True):
    """
    Corrige toutes les demandes PDA historiques.

    Args:
        before_date: Traiter les demandes avant cette date (YYYY-MM-DD)
        dry_run: Si True, simulation sans mise à jour
    """
    print("\n" + "=" * 70)
    print("🔧 CORRECTION COMPLÈTE DES DEMANDES PDA HISTORIQUES")
    print(f"   Date limite: avant {before_date}")
    print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
    print("=" * 70)

    storage = SupabaseStorage()

    # Compteurs
    stats = {
        'total_requests': 0,
        'unlinked_requests': 0,
        'linked_requests': 0,
        'newly_linked': 0,
        'tech_updated': 0,
        'status_to_completed': 0,
        'status_to_created': 0,
        'no_match_found': 0,
        'errors': []
    }

    # ============================================================
    # ÉTAPE 1: Récupérer toutes les demandes historiques
    # ============================================================
    print(f"\n{'='*70}")
    print("📋 ÉTAPE 1: Récupération des demandes historiques")
    print("=" * 70)

    try:
        result = storage.client.table('place_des_arts_requests')\
            .select('*')\
            .lt('appointment_date', before_date)\
            .order('appointment_date', desc=True)\
            .execute()

        all_requests = result.data or []
        stats['total_requests'] = len(all_requests)
    except Exception as e:
        print(f"❌ Erreur récupération demandes: {e}")
        return stats

    print(f"   📊 {len(all_requests)} demande(s) trouvée(s) avant {before_date}")

    # Séparer les demandes liées et non liées
    unlinked_requests = [r for r in all_requests if not r.get('appointment_id')]
    linked_requests = [r for r in all_requests if r.get('appointment_id')]

    stats['unlinked_requests'] = len(unlinked_requests)
    stats['linked_requests'] = len(linked_requests)

    print(f"   🔗 {len(linked_requests)} demande(s) avec RV lié")
    print(f"   ⚠️  {len(unlinked_requests)} demande(s) SANS RV lié")

    # ============================================================
    # ÉTAPE 2: Récupérer tous les RV Gazelle
    # ============================================================
    print(f"\n{'='*70}")
    print("📅 ÉTAPE 2: Récupération des RV Gazelle")
    print("=" * 70)

    try:
        # Récupérer les RV depuis novembre 2025 (pour couvrir décembre)
        # Utiliser appointment_date (pas start_datetime qui peut être NULL)
        result = storage.client.table('gazelle_appointments')\
            .select('*')\
            .gte('appointment_date', '2025-11-01')\
            .lt('appointment_date', before_date)\
            .order('appointment_date')\
            .execute()

        gazelle_appointments = result.data or []
    except Exception as e:
        print(f"❌ Erreur récupération RV Gazelle: {e}")
        return stats

    print(f"   📊 {len(gazelle_appointments)} RV Gazelle trouvé(s)")

    # Créer un index par external_id pour lookup rapide
    gazelle_by_id = {apt.get('external_id'): apt for apt in gazelle_appointments}

    # ============================================================
    # ÉTAPE 3: Lier les demandes sans appointment_id
    # ============================================================
    if unlinked_requests:
        print(f"\n{'='*70}")
        print("🔗 ÉTAPE 3: Liaison des demandes sans RV")
        print("=" * 70)

        for request in unlinked_requests:
            request_id = request.get('id')
            date_str = request.get('appointment_date', '')[:10] if request.get('appointment_date') else ''
            room = request.get('room', '')
            for_who = request.get('for_who', '')[:40]

            # Chercher un RV correspondant
            matched_apt = find_matching_appointment(request, gazelle_appointments)

            if matched_apt:
                apt_id = matched_apt.get('external_id')
                apt_title = matched_apt.get('title', 'N/A')
                apt_tech = matched_apt.get('technicien')
                apt_status = (matched_apt.get('status', '') or '').upper()

                # Déterminer le nouveau statut
                if apt_status in ('COMPLETE', 'COMPLETED'):
                    new_status = 'COMPLETED'
                else:
                    new_status = 'CREATED_IN_GAZELLE'

                print(f"\n✅ Match trouvé:")
                print(f"   Demande: {date_str} | {room} | {for_who}")
                print(f"   RV: {apt_title[:50]}")
                print(f"   Technicien Gazelle: {get_tech_name(apt_tech)}")
                print(f"   Statut: {request.get('status')} → {new_status}")

                if not dry_run:
                    try:
                        update_data = {
                            'appointment_id': apt_id,
                            'status': new_status,
                            'updated_at': datetime.now().isoformat()
                        }
                        if apt_tech:
                            update_data['technician_id'] = apt_tech

                        storage.client.table('place_des_arts_requests')\
                            .update(update_data)\
                            .eq('id', request_id)\
                            .execute()

                        stats['newly_linked'] += 1
                        if new_status == 'COMPLETED':
                            stats['status_to_completed'] += 1
                        else:
                            stats['status_to_created'] += 1

                        print(f"   💾 Lié et mis à jour")
                    except Exception as e:
                        print(f"   ❌ Erreur: {e}")
                        stats['errors'].append(f"Linking {request_id}: {e}")
                else:
                    stats['newly_linked'] += 1
                    if new_status == 'COMPLETED':
                        stats['status_to_completed'] += 1
                    else:
                        stats['status_to_created'] += 1
            else:
                print(f"\n⚠️  Pas de match:")
                print(f"   {date_str} | {room} | {for_who}")
                stats['no_match_found'] += 1

    # ============================================================
    # ÉTAPE 4: Vérifier et corriger les demandes déjà liées
    # ============================================================
    if linked_requests:
        print(f"\n{'='*70}")
        print("🔄 ÉTAPE 4: Vérification des demandes liées")
        print("=" * 70)

        for request in linked_requests:
            request_id = request.get('id')
            apt_id = request.get('appointment_id')
            date_str = request.get('appointment_date', '')[:10] if request.get('appointment_date') else ''
            room = request.get('room', '')
            for_who = request.get('for_who', '')[:40]
            current_status = request.get('status', '')
            current_tech = request.get('technician_id')

            # Trouver le RV Gazelle correspondant
            gazelle_apt = gazelle_by_id.get(apt_id)

            if not gazelle_apt:
                # RV non trouvé dans notre période - essayer de le récupérer directement
                try:
                    result = storage.client.table('gazelle_appointments')\
                        .select('*')\
                        .eq('external_id', apt_id)\
                        .execute()
                    if result.data:
                        gazelle_apt = result.data[0]
                except:
                    pass

            if gazelle_apt:
                gazelle_tech = gazelle_apt.get('technicien')
                gazelle_status = (gazelle_apt.get('status', '') or '').upper()

                needs_update = False
                update_data = {'updated_at': datetime.now().isoformat()}
                changes = []

                # Vérifier le technicien
                if gazelle_tech and current_tech != gazelle_tech:
                    update_data['technician_id'] = gazelle_tech
                    changes.append(f"Tech: {get_tech_name(current_tech)} → {get_tech_name(gazelle_tech)}")
                    needs_update = True

                # Vérifier le statut
                if gazelle_status in ('COMPLETE', 'COMPLETED') and current_status != 'COMPLETED':
                    update_data['status'] = 'COMPLETED'
                    changes.append(f"Statut: {current_status} → COMPLETED")
                    needs_update = True
                elif gazelle_status not in ('COMPLETE', 'COMPLETED') and current_status == 'PENDING':
                    update_data['status'] = 'CREATED_IN_GAZELLE'
                    changes.append(f"Statut: PENDING → CREATED_IN_GAZELLE")
                    needs_update = True

                if needs_update:
                    print(f"\n🔄 Correction:")
                    print(f"   {date_str} | {room} | {for_who}")
                    for change in changes:
                        print(f"   → {change}")

                    if not dry_run:
                        try:
                            storage.client.table('place_des_arts_requests')\
                                .update(update_data)\
                                .eq('id', request_id)\
                                .execute()

                            if 'technician_id' in update_data:
                                stats['tech_updated'] += 1
                            if 'status' in update_data:
                                if update_data['status'] == 'COMPLETED':
                                    stats['status_to_completed'] += 1
                                else:
                                    stats['status_to_created'] += 1

                            print(f"   💾 Mis à jour")
                        except Exception as e:
                            print(f"   ❌ Erreur: {e}")
                            stats['errors'].append(f"Update {request_id}: {e}")
                    else:
                        if 'technician_id' in update_data:
                            stats['tech_updated'] += 1
                        if 'status' in update_data:
                            if update_data['status'] == 'COMPLETED':
                                stats['status_to_completed'] += 1
                            else:
                                stats['status_to_created'] += 1
            else:
                print(f"\n⚠️  RV Gazelle introuvable pour: {date_str} | {room} | {for_who}")
                print(f"   appointment_id: {apt_id}")

    # ============================================================
    # RÉSUMÉ FINAL
    # ============================================================
    print(f"\n{'='*70}")
    print("📊 RÉSUMÉ FINAL")
    print("=" * 70)
    print(f"   Demandes analysées: {stats['total_requests']}")
    print(f"   - Déjà liées: {stats['linked_requests']}")
    print(f"   - Sans RV: {stats['unlinked_requests']}")
    print()

    if dry_run:
        print("   📝 ACTIONS QUI SERAIENT EFFECTUÉES:")
    else:
        print("   ✅ ACTIONS EFFECTUÉES:")

    print(f"   - Nouvellement liées: {stats['newly_linked']}")
    print(f"   - Techniciens mis à jour: {stats['tech_updated']}")
    print(f"   - Statuts → COMPLETED: {stats['status_to_completed']}")
    print(f"   - Statuts → CREATED_IN_GAZELLE: {stats['status_to_created']}")
    print(f"   - Sans match trouvé: {stats['no_match_found']}")

    if stats['errors']:
        print(f"\n   ❌ Erreurs ({len(stats['errors'])}):")
        for error in stats['errors'][:5]:
            print(f"      - {error}")
        if len(stats['errors']) > 5:
            print(f"      ... et {len(stats['errors']) - 5} autres")

    if dry_run:
        print(f"\n   💡 Relancez avec --apply pour effectuer les mises à jour")

    print("=" * 70 + "\n")

    return stats


def verify_final_state(before_date: str = "2026-01-01"):
    """Vérifie l'état final après correction."""
    print("\n" + "=" * 70)
    print("🔍 VÉRIFICATION DE L'ÉTAT FINAL")
    print("=" * 70)

    storage = SupabaseStorage()

    # Requête pour trouver les incohérences restantes
    query = """
    SELECT
        pda.id,
        pda.appointment_date,
        pda.room,
        pda.for_who,
        pda.status as status_pda,
        pda.technician_id as tech_pda,
        pda.appointment_id
    FROM place_des_arts_requests pda
    WHERE pda.appointment_date < %s
    ORDER BY pda.appointment_date DESC
    """

    try:
        # Récupérer les demandes historiques
        result = storage.client.table('place_des_arts_requests')\
            .select('id,appointment_date,room,for_who,status,technician_id,appointment_id')\
            .lt('appointment_date', before_date)\
            .order('appointment_date', desc=True)\
            .execute()

        requests = result.data or []

        # Compter par statut
        status_counts = {}
        unlinked_count = 0
        pending_with_no_link = 0

        for r in requests:
            status = r.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1

            if not r.get('appointment_id'):
                unlinked_count += 1
                if status == 'PENDING':
                    pending_with_no_link += 1

        print(f"\n   Total demandes: {len(requests)}")
        print(f"\n   Par statut:")
        for status, count in sorted(status_counts.items()):
            emoji = "✅" if status == "COMPLETED" else ("🔵" if status == "CREATED_IN_GAZELLE" else "🟠")
            print(f"      {emoji} {status}: {count}")

        print(f"\n   Sans RV lié: {unlinked_count}")
        print(f"   PENDING sans lien: {pending_with_no_link}")

        if pending_with_no_link == 0:
            print(f"\n   ✅ Aucune demande 'rose nouveau' restante!")
        else:
            print(f"\n   ⚠️  {pending_with_no_link} demande(s) toujours en 'rose nouveau'")

    except Exception as e:
        print(f"❌ Erreur vérification: {e}")

    print("=" * 70 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Correction complète des demandes PDA historiques"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Effectuer les mises à jour (par défaut: simulation)'
    )
    parser.add_argument(
        '--before',
        type=str,
        default='2026-01-01',
        help='Traiter les demandes avant cette date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Seulement vérifier l\'état actuel'
    )

    args = parser.parse_args()

    if args.verify_only:
        verify_final_state(args.before)
    else:
        fix_historical_pda_requests(
            before_date=args.before,
            dry_run=not args.apply
        )

        # Toujours afficher la vérification à la fin
        if args.apply:
            verify_final_state(args.before)
