#!/usr/bin/env python3
"""
Script pour mettre à jour les CompanyName dans la table Clients
avec les noms réels trouvés dans MaintenanceAlerts_ClientMapping.csv.

Utilise la logique flexible pour trouver les correspondances et mettre à jour
les noms synthétisés comme "Client Inconnu (L1)" avec les vrais noms.
"""

import sqlite3
import csv
import os

import os

# Chemin vers la racine du projet
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(PROJECT_ROOT, 'db_test_v5.sqlite')
CSV_DIR = os.path.join(PROJECT_ROOT, 'data_csv_test')
MAPPING_FILE = os.path.join(CSV_DIR, 'MaintenanceAlerts_ClientMapping.csv')
MAINTENANCE_ALERTS_FILE = os.path.join(CSV_DIR, 'MaintenanceAlerts.csv')


def load_mapping_data():
    """Charge les données de MaintenanceAlerts_ClientMapping.csv"""
    if not os.path.exists(MAPPING_FILE):
        print(f"❌ Fichier non trouvé: {MAPPING_FILE}")
        return []
    
    mapping_data = []
    with open(MAPPING_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            company_name = row.get('ClientCompanyName', '').strip()
            if company_name:  # Ignorer les lignes vides
                mapping_data.append({
                    'alert_id': row.get('AlertId_Original', '').strip(),
                    'company_name': company_name
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
            client_id_ref = row.get('ClientId_Reference', '').strip()
            if client_id_ref and client_id_ref.startswith('cli_'):
                alerts_data.append({
                    'line_index': idx,
                    'client_id_ref': client_id_ref
                })
    
    return alerts_data


def get_client_id_from_external_id(conn, external_id):
    """Récupère le ClientId depuis temp_client_mapping"""
    cursor = conn.cursor()
    
    # Utiliser temp_client_mapping (créée par fix_maintenancealerts_mapping.py)
    cursor.execute("""
        SELECT client_id FROM temp_client_mapping 
        WHERE external_id = ?
    """, (external_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    return None


def update_client_company_names(conn):
    """Met à jour les CompanyName dans Clients avec les noms réels"""
    print("🔍 Chargement des données...")
    
    # Charger les mappings
    mapping_data = load_mapping_data()
    print(f"   ✅ {len(mapping_data)} entrées de mapping chargées")
    
    # Créer un dictionnaire: external_id -> company_name
    # En utilisant l'index de ligne comme correspondance entre les deux fichiers
    external_id_to_company = {}
    
    # Lire MaintenanceAlerts.csv ligne par ligne pour faire correspondre avec le mapping
    if os.path.exists(MAINTENANCE_ALERTS_FILE):
        with open(MAINTENANCE_ALERTS_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                external_id = row.get('ClientId_Reference', '').strip()
                if external_id and external_id.startswith('cli_'):
                    # Trouver le CompanyName correspondant dans le mapping (même index)
                    if idx < len(mapping_data):
                        company_name = mapping_data[idx]['company_name']
                        if company_name:
                            external_id_to_company[external_id] = company_name
        
        print(f"   ✅ {len(external_id_to_company)} correspondances external_id -> CompanyName trouvées")
    
    print(f"\n🔗 Recherche des correspondances ClientId -> CompanyName...")
    
    cursor = conn.cursor()
    updates_made = 0
    company_name_updates = {}  # client_id -> company_name (pour éviter les doublons)
    
    for external_id, company_name in external_id_to_company.items():
        # Trouver le ClientId correspondant
        client_id = get_client_id_from_external_id(conn, external_id)
        
        if client_id:
            # Stocker la mise à jour (plusieurs external_id peuvent pointer vers le même client)
            company_name_updates[client_id] = company_name
            print(f"   ✅ {external_id} → Client #{client_id} → '{company_name}'")
        else:
            print(f"   ⚠️ {external_id} → ClientId non trouvé")
    
    print(f"\n📝 Mise à jour des CompanyName dans la table Clients...")
    
    # Mettre à jour les CompanyName
    for client_id, company_name in company_name_updates.items():
        # Vérifier le nom actuel
        cursor.execute("SELECT CompanyName FROM Clients WHERE Id = ?", (client_id,))
        current_name = cursor.fetchone()[0]
        
        # Mettre à jour seulement si le nom actuel est synthétisé ou différent
        if not current_name or current_name.startswith('Client Inconnu') or current_name != company_name:
            cursor.execute("""
                UPDATE Clients 
                SET CompanyName = ? 
                WHERE Id = ?
            """, (company_name, client_id))
            updates_made += 1
            print(f"   ✅ Client #{client_id}: '{current_name}' → '{company_name}'")
        else:
            print(f"   ⏭️  Client #{client_id}: déjà à jour ('{current_name}')")
    
    conn.commit()
    
    print(f"\n✅ {updates_made} CompanyName mis à jour dans la table Clients")
    return updates_made


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🔄 MISE À JOUR DES COMPANYNAME DANS CLIENTS")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de données non trouvée: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        updates = update_client_company_names(conn)
        
        if updates > 0:
            print(f"\n✅ Mise à jour terminée: {updates} clients mis à jour")
            print("\n💡 Vous pouvez maintenant réimporter les données si nécessaire")
        else:
            print("\n⚠️ Aucune mise à jour nécessaire")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()


if __name__ == '__main__':
    main()
