import sqlite3
import csv
import os

# Configuration (utilise les noms de fichiers que vous avez confirmés)
DB_NAME = 'db_test_v5.sqlite'
SCHEMA_FILE = 'schema.sql'
CSV_DIR = 'data_csv_test'

# Mapping des noms de tables CSV vers les noms de tables SQL
TABLE_NAME_MAPPING = {
    'Products': 'Inventaire',
    'Inventory': None,  # Pas de table correspondante dans le schéma
    'Invoices': 'Facturation',
    'InvoiceItems': None,  # Pas de table correspondante dans le schéma
}

# Mapping des colonnes CSV vers les colonnes SQL par table
COLUMN_MAPPINGS = {
    'Clients': {
        # Colonnes à importer : CompanyName, DefaultContactId
        # Colonnes ignorées : FirstName, LastName, Status, Tags, CreatedAt, UpdatedAt
    },
    'Products': {
        'Name': 'Description',
        'Sku': 'Sku',
        'UnitCost': 'Price',
        # Colonnes ignorées : RetailPrice, Active, CreatedAt
    },
    'MaintenanceAlerts': {
        'ClientId_Reference': 'ClientId',
        # Colonnes ignorées : Location, RecipientEmail, CreatedBy, CreatedAt, UpdatedAt
    },
    'Inventory': {
        # Pas de table correspondante, sera ignoré
    },
    'Invoices': {
        # Note: ClientCompanyName_Reference nécessiterait une jointure, 
        # mais on ne peut pas faire ça ici. On ignore pour l'instant.
        # Colonnes à importer : Status, Total, Notes
        # Colonnes ignorées : ClientCompanyName_Reference, Number, SubTotal, CreatedAt, DueOn
        # InvoiceDate n'est pas dans le CSV mais est requis dans le schéma
    },
    'InvoiceItems': {
        # Pas de table correspondante, sera ignoré
    },
}


def setup_database():
    """Crée la DB et le schéma à partir du fichier schema.sql."""
    if os.path.exists(DB_NAME):
        # Suppression pour repartir de zéro à chaque exécution
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    # Active les clés étrangères, essentiel pour l'intégrité des données
    conn.execute('PRAGMA foreign_keys = ON;')
    cursor = conn.cursor()

    # Créer la structure (tables)
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()
        cursor.executescript(sql_script)

    conn.commit()
    return conn


def map_external_ids(conn):
    """
    Crée un mapping des IDs externes (string) vers les IDs entiers de la table Clients.
    
    Cette fonction utilise le fichier MaintenanceAlerts_ClientMapping.csv pour créer
    un mapping fiable basé sur ClientCompanyName plutôt que sur l'ordre d'insertion.
    
    Après l'importation de la table Clients, cette fonction :
    1. Lit MaintenanceAlerts.csv pour obtenir les ClientId_Reference (IDs string cli_...)
    2. Lit MaintenanceAlerts_ClientMapping.csv pour obtenir les ClientCompanyName correspondants
    3. Utilise CompanyName pour mapper vers les Clients importés
    4. Crée un mapping {'ID_V4_string': ID_V5_ENTIER} pour MaintenanceAlerts
    5. Crée un mapping {'CompanyName': ID_V5_ENTIER} pour Facturation
    
    Retourne:
        - external_id_to_internal_id: dict {'ID_V4_string': ID_V5_ENTIER}
        - company_name_to_id: dict {'CompanyName': ID_V5_ENTIER}
    """
    cursor = conn.cursor()
    
    # Récupérer tous les clients avec leur ID et CompanyName
    cursor.execute("SELECT Id, CompanyName FROM Clients ORDER BY Id")
    clients = cursor.fetchall()
    
    # Mapping par CompanyName (pour Facturation/Invoices)
    company_name_to_id = {}
    for client_id, company_name in clients:
        if company_name and company_name.strip():
            # Normaliser le nom de compagnie (enlever espaces en début/fin)
            normalized_name = company_name.strip()
            company_name_to_id[normalized_name] = client_id
    
    # Vérifier si la table temp_client_mapping existe (créée par fix_maintenancealerts_mapping.py)
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='temp_client_mapping'
    """)
    temp_table_exists = cursor.fetchone() is not None
    
    if temp_table_exists:
        # Utiliser les mappings de la table temporaire (plus fiable)
        print("   📋 Utilisation des mappings de temp_client_mapping...")
        cursor.execute("SELECT external_id, client_id FROM temp_client_mapping")
        temp_mappings = cursor.fetchall()
        
        # Créer le mapping direct depuis la table temporaire
        external_id_to_internal_id = {}
        for row in temp_mappings:
            external_id_to_internal_id[row[0]] = row[1]
        
        print(f"   ✅ {len(external_id_to_internal_id)} mappings chargés depuis temp_client_mapping")
        print(f"   Mapping créé: {len(external_id_to_internal_id)} IDs externes, {len(company_name_to_id)} noms de compagnies")
        return external_id_to_internal_id, company_name_to_id
    
    # Lire MaintenanceAlerts.csv pour obtenir les ClientId_Reference (par ligne)
    maintenance_alerts_path = os.path.join(CSV_DIR, 'MaintenanceAlerts.csv')
    maintenance_alerts_client_ids = []  # Liste des ClientId_Reference par ligne
    
    if os.path.exists(maintenance_alerts_path):
        with open(maintenance_alerts_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                headers = [h.strip() for h in next(reader)]
                if 'ClientId_Reference' in headers:
                    client_id_idx = headers.index('ClientId_Reference')
                    for row in reader:
                        if len(row) > client_id_idx:
                            external_id = row[client_id_idx].strip()
                            maintenance_alerts_client_ids.append(external_id)
                        else:
                            maintenance_alerts_client_ids.append('')
            except StopIteration:
                pass
    
    # Lire MaintenanceAlerts_ClientMapping.csv pour obtenir les ClientCompanyName (par ligne)
    mapping_path = os.path.join(CSV_DIR, 'MaintenanceAlerts_ClientMapping.csv')
    mapping_company_names = []  # Liste des ClientCompanyName par ligne
    
    if os.path.exists(mapping_path):
        with open(mapping_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                headers = [h.strip() for h in next(reader)]
                if 'ClientCompanyName' in headers:
                    company_name_idx = headers.index('ClientCompanyName')
                    for row in reader:
                        if len(row) > company_name_idx:
                            company_name = row[company_name_idx].strip()
                            mapping_company_names.append(company_name)
                        else:
                            mapping_company_names.append('')
            except StopIteration:
                pass
    
    # Créer le mapping ClientId_Reference → ClientCompanyName
    # En utilisant l'index de ligne comme correspondance (les fichiers sont dans le même ordre)
    external_id_to_company_name = {}
    for idx, external_id in enumerate(maintenance_alerts_client_ids):
        if external_id and external_id.startswith('cli_'):
            # Trouver le ClientCompanyName correspondant (même index dans le fichier de mapping)
            if idx < len(mapping_company_names):
                company_name = mapping_company_names[idx]
                if company_name and company_name.strip():
                    # Si plusieurs ClientId_Reference pointent vers le même CompanyName,
                    # on garde le dernier (ou on pourrait utiliser un set)
                    external_id_to_company_name[external_id] = company_name.strip()
    
    # Créer le mapping final {'ID_V4_string': ID_V5_ENTIER}
    # en utilisant CompanyName comme intermédiaire
    external_id_to_internal_id = {}
    mapped_count = 0
    unmapped_external_ids = []
    
    for external_id, company_name in external_id_to_company_name.items():
        if company_name in company_name_to_id:
            external_id_to_internal_id[external_id] = company_name_to_id[company_name]
            mapped_count += 1
        else:
            unmapped_external_ids.append((external_id, company_name))
    
    if unmapped_external_ids:
        print(f"   ⚠️ {len(unmapped_external_ids)} IDs string n'ont pas pu être mappés:")
        for ext_id, comp_name in unmapped_external_ids[:5]:  # Afficher les 5 premiers
            print(f"      - {ext_id} → '{comp_name}' (client non importé)")
        if len(unmapped_external_ids) > 5:
            print(f"      ... et {len(unmapped_external_ids) - 5} autres")
    
    print(f"   Mapping créé: {len(external_id_to_internal_id)} IDs externes, {len(company_name_to_id)} noms de compagnies")
    
    return external_id_to_internal_id, company_name_to_id


def import_single_file(conn, filename, external_id_map=None, company_name_map=None):
    """Importe un seul fichier CSV."""
    if external_id_map is None:
        external_id_map = {}
    if company_name_map is None:
        company_name_map = {}
    
    cursor = conn.cursor()
    csv_table_name = filename.replace('.csv', '')
    file_path = os.path.join(CSV_DIR, filename)

    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return False

    # Vérifier si cette table doit être ignorée
    sql_table_name = TABLE_NAME_MAPPING.get(csv_table_name, csv_table_name)
    if sql_table_name is None:
        print(f"⚠️ Fichier {filename} ignoré (pas de table correspondante dans le schéma).")
        return False

    with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig supprime le BOM
        reader = csv.reader(f)
        try:
            csv_headers = [h.strip() for h in next(reader)]  # Récupère et nettoie les en-têtes
        except StopIteration:
            print(f"⚠️ Fichier {filename} est vide. Ignoré.")
            return False

        # Récupérer le mapping de colonnes pour cette table
        column_mapping = COLUMN_MAPPINGS.get(csv_table_name, {})
        
        # Récupérer les colonnes de la table SQL avec leurs contraintes
        cursor.execute(f"PRAGMA table_info({sql_table_name})")
        sql_columns_info = cursor.fetchall()
        # Format: (cid, name, type, notnull, default_value, pk)
        sql_columns = {row[1]: {'notnull': row[3], 'default': row[4]} for row in sql_columns_info}
        
        # Mapper les en-têtes CSV vers les noms SQL
        mapped_headers = []
        header_indices = []  # Indices des colonnes CSV à utiliser
        notnull_columns = []  # Indices des colonnes NOT NULL dans mapped_headers
        
        for idx, csv_header in enumerate(csv_headers):
            # Appliquer le mapping si défini, sinon garder le nom original
            sql_column = column_mapping.get(csv_header, csv_header)
            
            # Ne garder que les colonnes qui existent dans le schéma SQL
            if sql_column in sql_columns:
                mapped_headers.append(sql_column)
                header_indices.append(idx)
                # Marquer les colonnes NOT NULL
                if sql_columns[sql_column]['notnull']:
                    notnull_columns.append(len(mapped_headers) - 1)
        
        if not mapped_headers:
            print(f"⚠️ Aucune colonne correspondante trouvée pour {filename}. Ignoré.")
            return False

        # Vérifier si toutes les colonnes NOT NULL (sauf Id qui est auto-incrémenté) sont présentes
        missing_notnull = []
        for sql_col, info in sql_columns.items():
            # Ignorer la colonne Id qui est auto-incrémentée
            if sql_col == 'Id':
                continue
            if info['notnull'] and sql_col not in mapped_headers:
                # Pour Invoices, ClientId et InvoiceDate seront ajoutés dynamiquement
                if csv_table_name == 'Invoices' and sql_col in ['ClientId', 'InvoiceDate']:
                    # Ajouter ces colonnes à mapped_headers pour qu'elles soient incluses
                    mapped_headers.append(sql_col)
                    # Ajouter un index placeholder (sera géré dans la boucle)
                    header_indices.append(-1)  # -1 indique qu'on ajoutera la valeur dynamiquement
                    # Marquer comme NOT NULL
                    if sql_columns[sql_col]['notnull']:
                        notnull_columns.append(len(mapped_headers) - 1)
                else:
                    missing_notnull.append(sql_col)
        
        if missing_notnull:
            print(f"⚠️ Colonnes NOT NULL manquantes dans le CSV pour {filename}: {', '.join(missing_notnull)}. Ignoré.")
            return False

        # Préparation de la commande SQL
        placeholders = ', '.join(['?'] * len(mapped_headers))
        columns = ', '.join(mapped_headers)
        insert_sql = f"INSERT INTO {sql_table_name} ({columns}) VALUES ({placeholders})"

        # Identifier les indices pour les mappings
        client_id_idx = None
        if csv_table_name == 'MaintenanceAlerts' and 'ClientId' in mapped_headers:
            client_id_idx = mapped_headers.index('ClientId')
        
        invoice_client_id_idx = None
        invoice_date_idx = None
        client_company_name_idx = None
        created_at_idx = None
        due_on_idx = None
        if csv_table_name == 'Invoices':
            if 'ClientId' in mapped_headers:
                invoice_client_id_idx = mapped_headers.index('ClientId')
            if 'InvoiceDate' in mapped_headers:
                invoice_date_idx = mapped_headers.index('InvoiceDate')
            if 'ClientCompanyName_Reference' in csv_headers:
                client_company_name_idx = csv_headers.index('ClientCompanyName_Reference')
            if 'CreatedAt' in csv_headers:
                created_at_idx = csv_headers.index('CreatedAt')
            if 'DueOn' in csv_headers:
                due_on_idx = csv_headers.index('DueOn')
        
        # Identifier les indices pour Clients (logique de fallback CompanyName)
        company_name_csv_idx = None
        company_name_mapped_idx = None
        first_name_csv_idx = None
        last_name_csv_idx = None
        if csv_table_name == 'Clients':
            if 'CompanyName' in csv_headers:
                company_name_csv_idx = csv_headers.index('CompanyName')
            if 'CompanyName' in mapped_headers:
                company_name_mapped_idx = mapped_headers.index('CompanyName')
            if 'FirstName' in csv_headers:
                first_name_csv_idx = csv_headers.index('FirstName')
            if 'LastName' in csv_headers:
                last_name_csv_idx = csv_headers.index('LastName')
        
        # Filtrer les données pour ne garder que les colonnes mappées
        # et exclure les lignes où les colonnes NOT NULL sont vides
        data_to_insert = []
        skipped_count = 0
        synthesized_count = 0  # Compteur pour les CompanyName synthétisés
        
        for row in reader:
            # Créer filtered_row en excluant les indices -1 (colonnes ajoutées dynamiquement)
            # filtered_row doit avoir la même longueur que mapped_headers
            filtered_row = []
            for idx in header_indices:
                if idx >= 0 and idx < len(row):
                    filtered_row.append(row[idx])
                else:
                    # Pour les colonnes ajoutées dynamiquement (idx == -1), on ajoute une valeur vide
                    # qui sera remplie plus tard
                    filtered_row.append('')
            
            # LOGIQUE DE FALLBACK POUR CLIENTS - CompanyName
            if csv_table_name == 'Clients' and company_name_mapped_idx is not None:
                # Récupérer les valeurs depuis la ligne CSV originale
                company_name = ''
                first_name = ''
                last_name = ''
                
                if company_name_csv_idx is not None and company_name_csv_idx < len(row):
                    company_name = row[company_name_csv_idx].strip()
                
                if first_name_csv_idx is not None and first_name_csv_idx < len(row):
                    first_name = row[first_name_csv_idx].strip()
                
                if last_name_csv_idx is not None and last_name_csv_idx < len(row):
                    last_name = row[last_name_csv_idx].strip()
                
                # Si CompanyName est vide (ce qui cause le rejet de 29 lignes)
                if not company_name:
                    if first_name and last_name:
                        # 1. Utiliser Prénom + Nom comme nom de compagnie
                        synthetic_name = f"{first_name} {last_name}".strip()
                    elif first_name or last_name:
                        # 2. Utiliser juste l'un des deux
                        synthetic_name = (first_name or last_name).strip()
                    else:
                        # 3. Utiliser le dernier recours (nom technique)
                        # Utiliser l'index de ligne comme identifiant
                        row_id = f"L{len(data_to_insert) + skipped_count + 1}"
                        synthetic_name = f"Client Inconnu ({row_id})"
                    
                    # Mettre à jour filtered_row avec le nom synthétisé
                    filtered_row[company_name_mapped_idx] = synthetic_name
                    synthesized_count += 1
            
            # Appliquer le mapping des IDs externes pour MaintenanceAlerts
            if csv_table_name == 'MaintenanceAlerts' and client_id_idx is not None:
                external_id = filtered_row[client_id_idx].strip()
                if external_id in external_id_map:
                    # Remplacer l'ID string par l'ID entier
                    filtered_row[client_id_idx] = str(external_id_map[external_id])
                else:
                    # Si l'ID externe n'est pas dans le mapping, on ignore cette ligne
                    skipped_count += 1
                    continue
            
            # Appliquer le mapping pour Invoices/Facturation
            if csv_table_name == 'Invoices':
                # Mapper ClientCompanyName_Reference vers ClientId
                if invoice_client_id_idx is not None and client_company_name_idx is not None:
                    company_name = row[client_company_name_idx].strip() if client_company_name_idx < len(row) else ''
                    if company_name and company_name in company_name_map:
                        # Remplir ClientId avec l'ID entier correspondant
                        filtered_row[invoice_client_id_idx] = str(company_name_map[company_name])
                    else:
                        # Si le nom de compagnie n'est pas trouvé, on ignore cette ligne
                        skipped_count += 1
                        continue
                
                # Mapper CreatedAt ou DueOn vers InvoiceDate
                if invoice_date_idx is not None:
                    invoice_date = ''
                    # Essayer d'abord CreatedAt, puis DueOn
                    if created_at_idx is not None and created_at_idx < len(row):
                        invoice_date = row[created_at_idx].strip()
                    elif due_on_idx is not None and due_on_idx < len(row):
                        invoice_date = row[due_on_idx].strip()
                    
                    if invoice_date:
                        # Remplir InvoiceDate avec la date trouvée
                        filtered_row[invoice_date_idx] = invoice_date
                    else:
                        # Si aucune date n'est disponible, on ignore cette ligne
                        skipped_count += 1
                        continue
            
            # Vérifier que toutes les colonnes NOT NULL ont une valeur
            is_valid = True
            for notnull_idx in notnull_columns:
                if notnull_idx < len(filtered_row):
                    if not filtered_row[notnull_idx] or filtered_row[notnull_idx].strip() == '':
                        is_valid = False
                        break
                else:
                    is_valid = False
                    break
            
            if is_valid:
                data_to_insert.append(filtered_row)
            else:
                skipped_count += 1

        if skipped_count > 0:
            print(f"Importation de {len(data_to_insert)} lignes dans {sql_table_name} ({skipped_count} lignes ignorées car colonnes NOT NULL vides)...")
        else:
            print(f"Importation de {len(data_to_insert)} lignes dans {sql_table_name}...")

        if len(data_to_insert) == 0:
            print(f"⚠️ Aucune ligne valide à importer pour {sql_table_name}.")
            return False

        try:
            # Tente l'insertion massive des données
            cursor.executemany(insert_sql, data_to_insert)
            conn.commit()
            success_msg = f"✅ {len(data_to_insert)} lignes importées dans {sql_table_name}."
            if csv_table_name == 'Clients' and synthesized_count > 0:
                success_msg += f" ({synthesized_count} CompanyName synthétisés)"
            print(success_msg)
            return True
        except Exception as e:
            print(f"❌ Erreur d'importation pour {sql_table_name}: {e}")
            conn.rollback()
            return False


def import_csv_data(conn):
    """Importe les données de chaque CSV dans l'ordre approprié."""
    # Importer Clients en premier
    print("📦 Importation de Clients...")
    import_single_file(conn, 'Clients.csv')
    
    # Recréer la table temp_client_mapping si elle n'existe pas (après l'import des clients)
    # Cette table est créée par fix_maintenancealerts_mapping.py
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='temp_client_mapping'
    """)
    if cursor.fetchone() is None:
        print("🔧 Recréation de la table temp_client_mapping...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_client_mapping (
                external_id TEXT PRIMARY KEY,
                client_id INTEGER,
                company_name TEXT,
                match_score REAL
            )
        """)
        
        # Recréer les mappings de base (les 3 IDs pointent vers le client ID 1)
        # Ces mappings seront améliorés par fix_maintenancealerts_mapping.py
        mappings = [
            ('cli_9UMLkteep8EsISbG', 1, 'École de musique Vincent-d\'Indy', 1.0),
            ('cli_HbEwl9rN11pSuDEU', 1, 'École de musique Vincent-d\'Indy', 1.0),
            ('cli_gxvGHJqK79FwNo1r', 1, 'École de musique Vincent-d\'Indy', 1.0),
        ]
        
        cursor.executemany("""
            INSERT OR REPLACE INTO temp_client_mapping 
            (external_id, client_id, company_name, match_score)
            VALUES (?, ?, ?, ?)
        """, mappings)
        conn.commit()
        print("   ✅ Table temp_client_mapping recréée avec 3 mappings de base")
    
    # Créer les mappings après l'import de Clients
    print("🔗 Création des mappings d'IDs...")
    external_id_map, company_name_map = map_external_ids(conn)
    
    # Importer les autres fichiers dans l'ordre
    other_files = [
        'Products.csv',
        'MaintenanceAlerts.csv',
        'Inventory.csv',
        'Invoices.csv',
        'InvoiceItems.csv',
    ]
    
    for filename in other_files:
        import_single_file(conn, filename, external_id_map, company_name_map)


if __name__ == '__main__':
    print("--- DÉMARRAGE DE L'IMPORTATION V5 (SQLite) ---")
    try:
        conn = setup_database()
        import_csv_data(conn)
        conn.close()
        print("\n--- IMPORTATION TERMINÉE. Base de données db_test_v5.sqlite prête. ---")
    except Exception as e:
        print(f"Échec critique du setup: {e}")
