#!/usr/bin/env python3
"""
Script d'import automatique de TOUTES les années historiques.
Lance l'import séquentiel de start_year à end_year.

Usage:
    python3 import_all_history.py --start 2023 --end 2016
    
Lancer ce soir avant de partir pour avoir tout demain matin!
"""

import subprocess
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


def check_current_state():
    """Affiche l'état actuel de la base."""
    print("\n" + "="*80)
    print("📊 VÉRIFICATION DE L'ÉTAT ACTUEL")
    print("="*80 + "\n")
    
    s = SupabaseStorage()
    
    years_data = {}
    for year in range(2016, 2027):
        result = s.client.table('gazelle_timeline_entries')\
            .select('id', count='exact')\
            .gte('occurred_at', f'{year}-01-01')\
            .lt('occurred_at', f'{year+1}-01-01')\
            .limit(1)\
            .execute()
        
        count = result.count if hasattr(result, 'count') else 0
        years_data[year] = count
    
    print(f"{'Année':<10} | {'Entrées actuelles':<20}")
    print("-" * 40)
    for year, count in sorted(years_data.items()):
        status = "✅" if count > 10000 else "🔄" if count > 100 else "❌"
        print(f"{year:<10} | {status} {count:>10,}")
    
    print("\n" + "="*80 + "\n")
    return years_data


def import_year_range(start_year: int, end_year: int, dry_run: bool = False):
    """
    Importe toutes les années de start_year à end_year (inclus).
    
    Args:
        start_year: Année de début (ex: 2023)
        end_year: Année de fin (ex: 2016)
        dry_run: Si True, n'importe pas vraiment
    """
    print("\n" + "="*80)
    print(f"🚀 IMPORT AUTOMATIQUE - ANNÉES {start_year} → {end_year}")
    print("="*80 + "\n")
    
    if dry_run:
        print("⚠️  MODE DRY-RUN: Pas d'import réel\n")
    
    start_time = datetime.now()
    
    # Calculer le nombre d'années
    years = list(range(start_year, end_year - 1, -1))
    total_years = len(years)
    
    print(f"📋 Plan d'import:")
    print(f"   • {total_years} années à traiter")
    print(f"   • Estimation: ~{total_years * 30} minutes total")
    print(f"   • Début: {start_time.strftime('%H:%M:%S')}")
    print(f"   • Fin estimée: {(start_time.timestamp() + total_years * 1800)}")
    print("\n" + "="*80 + "\n")
    
    results = {}
    
    for i, year in enumerate(years, 1):
        print(f"\n{'='*80}")
        print(f"📅 ANNÉE {year} ({i}/{total_years})")
        print(f"{'='*80}\n")
        
        year_start = datetime.now()
        
        if dry_run:
            print(f"   [DRY-RUN] Simuler import de {year}...")
            import time
            time.sleep(2)
            results[year] = {'success': True, 'entries': 15000, 'errors': 0}
        else:
            # Lancer le script history_recovery
            cmd = [
                'python3',
                'scripts/history_recovery_year_by_year.py',
                '--start-year', str(year),
                '--end-year', str(year)
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=3600  # 1h max par année
                )
                
                # Parser le résultat
                output = result.stdout
                
                # Extraire les stats du résumé
                imported = 0
                errors = 0
                
                for line in output.split('\n'):
                    if 'entrées importées' in line.lower():
                        try:
                            imported = int(line.split(':')[1].strip().split()[0])
                        except:
                            pass
                    if 'erreurs' in line.lower() and ':' in line:
                        try:
                            errors = int(line.split(':')[1].strip().split()[0])
                        except:
                            pass
                
                results[year] = {
                    'success': result.returncode == 0,
                    'entries': imported,
                    'errors': errors
                }
                
                if result.returncode == 0:
                    print(f"   ✅ Année {year} importée avec succès!")
                    print(f"      • {imported:,} entrées")
                    print(f"      • {errors} erreurs")
                else:
                    print(f"   ❌ Erreur lors de l'import de {year}")
                    print(f"      Code: {result.returncode}")
                    
            except subprocess.TimeoutExpired:
                print(f"   ⚠️  Timeout sur {year} (> 1h)")
                results[year] = {'success': False, 'entries': 0, 'errors': 0}
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                results[year] = {'success': False, 'entries': 0, 'errors': 0}
        
        year_duration = (datetime.now() - year_start).total_seconds()
        print(f"\n   ⏱️  Durée: {year_duration/60:.1f} minutes")
        
        # Estimation pour les années restantes
        remaining = total_years - i
        if remaining > 0:
            eta_minutes = remaining * (year_duration / 60)
            print(f"   📊 Restant: {remaining} années (~{eta_minutes:.0f} min)")
    
    # Résumé final
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*80)
    print("📊 RÉSUMÉ FINAL - IMPORT COMPLET")
    print("="*80 + "\n")
    
    total_imported = sum(r['entries'] for r in results.values())
    total_errors = sum(r['errors'] for r in results.values())
    successes = sum(1 for r in results.values() if r['success'])
    
    print(f"⏱️  Durée totale: {total_duration/3600:.1f}h ({total_duration/60:.0f} min)")
    print(f"✅ Années réussies: {successes}/{total_years}")
    print(f"📥 Total importé: {total_imported:,} entrées")
    print(f"❌ Total erreurs: {total_errors}")
    
    print("\n📋 Détail par année:\n")
    print(f"{'Année':<10} | {'Status':<15} | {'Entrées':<15} | {'Erreurs':<10}")
    print("-" * 60)
    
    for year in sorted(results.keys(), reverse=True):
        r = results[year]
        status = "✅ Succès" if r['success'] else "❌ Échec"
        print(f"{year:<10} | {status:<15} | {r['entries']:>10,}     | {r['errors']:>5}")
    
    print("\n" + "="*80)
    
    # Vérifier l'état final
    if not dry_run:
        print("\n📊 VÉRIFICATION FINALE DANS SUPABASE:\n")
        check_current_state()
    
    print("\n✅ IMPORT AUTOMATIQUE TERMINÉ!")
    print("="*80 + "\n")
    
    return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Import automatique de toutes les années historiques'
    )
    parser.add_argument('--start', type=int, default=2023,
                        help='Année de début (défaut: 2023)')
    parser.add_argument('--end', type=int, default=2016,
                        help='Année de fin (défaut: 2016)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mode simulation (pas d\'import réel)')
    
    args = parser.parse_args()
    
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              🚀 IMPORT AUTOMATIQUE - HISTORIQUE COMPLET                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Vérifier l'état actuel
    check_current_state()
    
    # Confirmer
    if not args.dry_run:
        response = input(f"\n⚠️  Lancer l'import de {args.start} à {args.end}? (oui/non): ")
        if response.lower() not in ['oui', 'yes', 'o', 'y']:
            print("❌ Import annulé")
            sys.exit(0)
    
    # Lancer l'import
    results = import_year_range(args.start, args.end, args.dry_run)
    
    print("\n💡 Prochaines étapes:")
    print("   1. Vérifier les logs détaillés dans les fichiers recovery_*.log")
    print("   2. Tester l'assistant avec des requêtes sur toutes les années")
    print("   3. Créer des analyses de tendances sur 10 ans")
    print("   4. Savourer ! 🎹🏆\n")
