#!/usr/bin/env python3
"""
Script pour corriger le mapping des MaintenanceAlerts.
Trouve les correspondances flexibles entre CompanyName dans MaintenanceAlerts_ClientMapping.csv
et les CompanyName dans la table Clients.
"""

import sqlite3
import csv
import os
from difflib import SequenceMatcher

DB_PATH = 'db_test_v5.sqlite'
CSV_DIR = 'data_csv_test'
MAPPING_FILE = os.path.join(CSV_DIR, 'MaintenanceAlerts_ClientMapping.csv')
MAINTENANCE_ALERTS_FILE = os.path.join(CSV_DIR, 'MaintenanceAlerts.csv')


def similarity(a, b):
    """Calcule la similarité entre deux chaînes (0.0 à 1.0)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def find_best_match(target_name, client_names):
    """
    Trouve le meilleur match pour un CompanyName donné.
    Retourne (client_id, company_name, score) ou None si pas de bon match.
    """
    if not target_name or not target_name.strip():
        return None
    
    target_name = target_name.strip()
    best_match = None
    best_score = 0.0
    threshold = 0.6  # Seuil de similarité minimum
    
    for client_id, company_name in client_names.items():
        if not company_name:
            continue
        
        score = similarity(target_name, company_name)
        if score > best_score and score >= threshold:
            best_score = score
            best_match = (client_id, company_name, score)
    
    return best_match


def load_client_company_names(conn):
    """Charge tous les clients avec leur CompanyName"""
    cursor = conn.cursor()
    cursor.execute("SELECT Id, CompanyName FROM Clients")
    return {row[0]: row[1] for row in cursor.fetchall()}


def load_mapping_data():
    """Charge les données de MaintenanceAlerts_ClientMapping.csv"""
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ Fichier non trouvé: {MAPPING_FILE}")
        return []
    
    mapping_data = []
    with open(MAPPING_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping_data.append({
                'alert_id': row.get('AlertId_Original', '').strip(),
                'company_name': row.get('ClientCompanyName', '').strip()
            })
    
    return mapping_data


def load_maintenance_alerts_data():
    """Charge les données de MaintenanceAlerts.csv pour obtenir les ClientId_Reference"""
    if not os.path.exists(MAINTENANCE_ALERTS_FILE):
        print(f"❌ Fichier non trouvé: {MAINTENANCE_ALERTS_FILE}")
        return []
    
    alerts_data = []
    with open(MAINTENANCE_ALERTS_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            alerts_data.append({
                'line_index': idx,
                'client_id_ref': row.get('ClientId_Reference', '').strip()
            })
    
    return alerts_data


def create_mapping_table(conn):
    """Crée une table temporaire pour stocker les mappings"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_client_mapping (
            external_id TEXT PRIMARY KEY,
            client_id INTEGER,
            company_name TEXT,
            match_score REAL
        )
    """)
    conn.commit()


def update_mappings(conn):
    """Met à jour les mappings en trouvant les correspondances"""
    print("🔍 Chargement des données...")
    
    # Charger les clients
    client_names = load_client_company_names(conn)
    print(f"   ✅ {len(client_names)} clients chargés")
    
    # Charger le mapping
    mapping_data = load_mapping_data()
    print(f"   ✅ {len(mapping_data)} entrées de mapping chargées")
    
    # Charger les alertes
    alerts_data = load_maintenance_alerts_data()
    print(f"   ✅ {len(alerts_data)} alertes chargées")
    
    # Créer la table temporaire
    create_mapping_table(conn)
    cursor = conn.cursor()
    
    # Créer un dictionnaire: external_id -> company_name
    external_id_to_company = {}
    for idx, alert in enumerate(alerts_data):
        external_id = alert['client_id_ref']
        if external_id and external_id.startswith('cli_'):
            # Trouver le CompanyName correspondant dans le mapping
            if idx < len(mapping_data):
                company_name = mapping_data[idx]['company_name']
                if company_name:
                    external_id_to_company[external_id] = company_name
    
    print(f"\n🔗 Recherche des correspondances...")
    matches_found = 0
    matches_exact = 0
    matches_fuzzy = 0
    
    for external_id, target_company in external_id_to_company.items():
        # Chercher correspondance exacte d'abord
        exact_match = None
        for client_id, company_name in client_names.items():
            if company_name and company_name.strip().lower() == target_company.lower():
                exact_match = (client_id, company_name, 1.0)
                break
        
        if exact_match:
            client_id, company_name, score = exact_match
            cursor.execute("""
                INSERT OR REPLACE INTO temp_client_mapping 
                (external_id, client_id, company_name, match_score)
                VALUES (?, ?, ?, ?)
            """, (external_id, client_id, company_name, score))
            matches_found += 1
            matches_exact += 1
        else:
            # Chercher correspondance flexible
            fuzzy_match = find_best_match(target_company, client_names)
            if fuzzy_match:
                client_id, company_name, score = fuzzy_match
                cursor.execute("""
                    INSERT OR REPLACE INTO temp_client_mapping 
                    (external_id, client_id, company_name, match_score)
                    VALUES (?, ?, ?, ?)
                """, (external_id, client_id, company_name, score))
                matches_found += 1
                matches_fuzzy += 1
                print(f"   🔄 Match flexible: '{target_company}' → '{company_name}' (score: {score:.2f})")
    
    conn.commit()
    
    print(f"\n✅ Mappings créés:")
    print(f"   - Correspondances exactes: {matches_exact}")
    print(f"   - Correspondances flexibles: {matches_fuzzy}")
    print(f"   - Total: {matches_found} mappings")
    
    return matches_found


def update_map_external_ids_function():
    """
    Met à jour la fonction map_external_ids dans import_sqlite_data.py
    pour utiliser les mappings de la table temporaire.
    """
    print("\n💡 Note: Pour utiliser ces mappings, vous devrez:")
    print("   1. Réimporter les données avec import_sqlite_data.py")
    print("   2. Ou modifier map_external_ids() pour lire temp_client_mapping")


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🔧 CORRECTION DU MAPPING MAINTENANCEALERTS")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de données non trouvée: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        matches = update_mappings(conn)
        
        if matches > 0:
            print(f"\n✅ {matches} mappings créés dans temp_client_mapping")
            print("\n📋 Pour voir les mappings:")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM temp_client_mapping")
            for row in cursor.fetchall():
                print(f"   {row['external_id']} → Client #{row['client_id']} ({row['company_name']}) [score: {row['match_score']:.2f}]")
        else:
            print("\n⚠️ Aucun mapping trouvé")
        
        update_map_external_ids_function()
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    main()

