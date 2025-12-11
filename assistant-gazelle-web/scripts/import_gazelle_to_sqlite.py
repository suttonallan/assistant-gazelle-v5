"""
Import des donnees depuis l'API Gazelle vers SQLite
Piano Technique Montreal - Version Web

Ce script :
1. Cree la base SQLite si elle n'existe pas
2. Cree les tables necessaires
3. Importe les donnees depuis l'API Gazelle GraphQL
4. Limite a 100 clients pour test initial

Utilise la meme logique OAuth2 que Import_all_data.py
"""

# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Fix encoding pour Windows PowerShell (seulement si nécessaire)
if sys.platform == "win32" and hasattr(sys.stdout, 'buffer'):
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass  # Si ça échoue, on continue sans fix d'encodage

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration
API_URL = "https://gazelleapp.io/graphql/private/"
TOKEN_FILE = "data/gazelle_token.json"  # Dans le dossier data du projet parent
DB_PATH = "data/gazelle_web.db"

# OAuth2 credentials (mêmes que Import_all_data.py)
CLIENT_ID = "yCLgIwBusPMX9bZHtbzePvcNUisBQ9PeA4R93OwKwNE"
CLIENT_SECRET = "CHiMzcYZ2cVgBCjQ7vDCxr3jIE5xkLZ_9v4VkU-O9Qc"

# Configuration SQL Server (optionnel - pour import initial depuis SQL Server existant)
# Essayer d'abord SQL_SERVER_CONN_STR, sinon utiliser DB_CONN_STR du projet principal
SQL_SERVER_CONN_STR = os.getenv("SQL_SERVER_CONN_STR") or os.getenv("DB_CONN_STR")
if not SQL_SERVER_CONN_STR:
    try:
        # Essayer d'importer depuis le projet principal
        from app.assistant_gazelle_v4_secure import Config
        SQL_SERVER_CONN_STR = getattr(Config, 'DB_CONN_STR', None)
    except:
        SQL_SERVER_CONN_STR = None

USE_SQL_SERVER_FOR_INITIAL_IMPORT = os.getenv("USE_SQL_SERVER_FOR_INITIAL_IMPORT", "true").lower() == "true"  # Par défaut activé

# Limite pour test initial
MAX_CLIENTS = 100

current_tokens = {}


def load_tokens():
    """Charge les tokens OAuth depuis le fichier"""
    # Chercher le token dans le projet parent
    parent_token_file = Path(__file__).parent.parent.parent / "data" / "gazelle_token.json"
    token_file = parent_token_file if parent_token_file.exists() else Path(TOKEN_FILE)
    
    try:
        with open(token_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERREUR] Impossible de charger {token_file}: {e}")
        return None


def save_tokens(token_data):
    """Sauvegarde les tokens OAuth dans le fichier"""
    token_file = Path(TOKEN_FILE)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    with open(token_file, 'w') as f:
        json.dump(token_data, f, indent=2)


def refresh_access_token(refresh_token):
    """Rafraîchit le token d'accès OAuth"""
    print("[INFO] Rafraîchissement du token OAuth...")
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    try:
        response = requests.post("https://gazelleapp.io/developer/oauth/token", data=data)
        response.raise_for_status()
        new_token_data = response.json()
        if "refresh_token" not in new_token_data:
            new_token_data["refresh_token"] = refresh_token
        save_tokens(new_token_data)
        print("[OK] Token rafraîchi")
        return new_token_data
    except Exception as e:
        print(f"[ERREUR] Échec du rafraîchissement: {e}")
        return None


def make_api_call(payload):
    """Effectue un appel GraphQL API"""
    global current_tokens
    headers = {"Authorization": f"Bearer {current_tokens.get('access_token')}"}
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        resp_json = response.json()
        if "errors" in resp_json:
            print(f"[ERREUR] GraphQL: {json.dumps(resp_json['errors'], indent=2)}")
            return None
        return resp_json
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("[AVERTISSEMENT] Token expiré, rafraîchissement...")
            refreshed = refresh_access_token(current_tokens.get('refresh_token'))
            if refreshed:
                current_tokens.update(refreshed)
                return make_api_call(payload)
        print(f"[ERREUR] HTTP: {e}")
        return None
    except Exception as e:
        print(f"[ERREUR] API call: {e}")
        return None


def create_database_schema(conn):
    """Crée les tables SQLite selon le schéma défini"""
    cursor = conn.cursor()
    
    # Clients
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Clients (
            Id TEXT PRIMARY KEY,
            CompanyName TEXT,
            FirstName TEXT,
            LastName TEXT,
            Status TEXT,
            Tags TEXT,
            DefaultContactId TEXT,
            CreatedAt TEXT,
            UpdatedAt TEXT
        )
    """)
    
    # Contacts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Contacts (
            Id TEXT PRIMARY KEY,
            ClientId TEXT,
            FirstName TEXT,
            LastName TEXT,
            FOREIGN KEY (ClientId) REFERENCES Clients(Id)
        )
    """)
    
    # Pianos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Pianos (
            Id TEXT PRIMARY KEY,
            ClientId TEXT,
            Make TEXT,
            Model TEXT,
            SerialNumber TEXT,
            Type TEXT,
            Year INTEGER,
            Notes TEXT,
            Location TEXT,
            FOREIGN KEY (ClientId) REFERENCES Clients(Id)
        )
    """)
    
    # Appointments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Appointments (
            Id TEXT PRIMARY KEY,
            ClientId TEXT,
            TechnicianId TEXT,
            PianoId TEXT,
            Description TEXT,
            AppointmentStatus TEXT,
            EventType TEXT,
            StartAt TEXT,
            Duration INTEGER,
            IsAllDay INTEGER,
            Notes TEXT,
            ConfirmedByClient INTEGER,
            FOREIGN KEY (ClientId) REFERENCES Clients(Id),
            FOREIGN KEY (PianoId) REFERENCES Pianos(Id)
        )
    """)
    
    # TimelineEntries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TimelineEntries (
            Id TEXT PRIMARY KEY,
            ClientId TEXT,
            PianoId TEXT,
            InvoiceId TEXT,
            EstimateId TEXT,
            OccurredAt TEXT,
            EntryType TEXT,
            Title TEXT,
            Details TEXT,
            UserId TEXT,
            FOREIGN KEY (ClientId) REFERENCES Clients(Id),
            FOREIGN KEY (PianoId) REFERENCES Pianos(Id)
        )
    """)
    
    # Invoices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Invoices (
            Id TEXT PRIMARY KEY,
            ClientId TEXT,
            Number TEXT,
            Status TEXT,
            SubTotal REAL,
            Total REAL,
            Notes TEXT,
            CreatedAt TEXT,
            DueOn TEXT,
            FOREIGN KEY (ClientId) REFERENCES Clients(Id)
        )
    """)
    
    # InvoiceItems
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS InvoiceItems (
            Id TEXT PRIMARY KEY,
            InvoiceId TEXT,
            PianoId TEXT,
            Description TEXT,
            Quantity REAL,
            Amount REAL,
            Total REAL,
            FOREIGN KEY (InvoiceId) REFERENCES Invoices(Id),
            FOREIGN KEY (PianoId) REFERENCES Pianos(Id)
        )
    """)
    
    # Index pour performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_status ON Clients(Status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_clientid ON Contacts(ClientId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pianos_clientid ON Pianos(ClientId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_clientid ON Appointments(ClientId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_technicianid ON Appointments(TechnicianId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_startat ON Appointments(StartAt)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_clientid ON TimelineEntries(ClientId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_occurredat ON TimelineEntries(OccurredAt)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_clientid ON Invoices(ClientId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoiceitems_invoiceid ON InvoiceItems(InvoiceId)")
    
    conn.commit()
    print("[OK] Schéma de base de données créé")


def format_datetime(dt_str):
    """Convertit une date/datetime en format ISO 8601 pour SQLite"""
    if not dt_str:
        return None
    try:
        # Si c'est déjà une string ISO, la retourner
        if isinstance(dt_str, str):
            # Essayer de parser et reformater pour s'assurer du format
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            return dt.isoformat()
        return dt_str
    except:
        return dt_str


def import_clients(conn, limit=MAX_CLIENTS):
    """Importe les clients via les rendez-vous (car allClientsBatched n'existe pas dans l'API)"""
    print(f"[INFO] Import des clients via rendez-vous (limite: {limit} clients uniques)...")
    
    # Récupérer les rendez-vous pour extraire les clients
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    query_events = """
    query GetEvents($first: Int, $after: String, $filters: PrivateAllEventsFilter) {
      allEventsBatched(first: $first, after: $after, filters: $filters) {
        nodes {
          id
          client {
            id
            companyName
            status
            tags
            defaultContact {
              id
            }
            createdAt
            updatedAt
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    cursor = conn.cursor()
    client_ids_seen = set()
    imported = 0
    has_next_page = True
    after_cursor = None
    
    filters = {
        "startOn": start_date,
        "endOn": end_date,
        "type": ["APPOINTMENT"]
    }
    
    # Récupérer les clients via les rendez-vous
    while has_next_page and imported < limit:
        payload = {
            "query": query_events,
            "variables": {
                "first": 100,
                "after": after_cursor,
                "filters": filters
            }
        }
        
        result = make_api_call(payload)
        if not result or 'data' not in result or 'allEventsBatched' not in result['data']:
            print("[ERREUR] Réponse API invalide pour événements")
            break
        
        batch = result['data']['allEventsBatched']
        nodes = batch.get('nodes', [])
        
        for node in nodes:
            client_data = node.get('client')
            if not client_data:
                continue
            
            client_id = client_data.get('id')
            if not client_id or client_id in client_ids_seen:
                continue
            
            if imported >= limit:
                break
            
            try:
                default_contact = client_data.get('defaultContact', {})
                default_contact_id = default_contact.get('id') if default_contact else None
                
                cursor.execute("""
                    INSERT OR REPLACE INTO Clients 
                    (Id, CompanyName, FirstName, LastName, Status, Tags, DefaultContactId, CreatedAt, UpdatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_id,
                    client_data.get('companyName'),
                    None,  # FirstName/LastName sont dans Contacts
                    None,
                    client_data.get('status'),
                    json.dumps(client_data.get('tags')) if client_data.get('tags') else None,
                    default_contact_id,
                    format_datetime(client_data.get('createdAt')),
                    format_datetime(client_data.get('updatedAt'))
                ))
                client_ids_seen.add(client_id)
                imported += 1
            except Exception as e:
                print(f"[ERREUR] Erreur import client {client_id}: {e}")
        
        page_info = batch.get('pageInfo', {})
        has_next_page = page_info.get('hasNextPage', False) and imported < limit
        after_cursor = page_info.get('endCursor')
    
    conn.commit()
    print(f"[OK] {imported} clients importés")
    return imported


def import_contacts(conn, client_ids):
    """Importe les contacts pour les clients spécifiés"""
    if not client_ids:
        return 0
    
    print(f"[INFO] Import des contacts pour {len(client_ids)} clients...")
    
    # Option 1: Depuis SQL Server si disponible
    if USE_SQL_SERVER_FOR_INITIAL_IMPORT and SQL_SERVER_CONN_STR:
        try:
            # Import relatif depuis le même dossier
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, script_dir)
            from import_contacts_pianos_from_sql_server import import_contacts_from_sql_server
            imported = import_contacts_from_sql_server(SQL_SERVER_CONN_STR, conn, set(client_ids))
            if imported > 0:
                print(f"[OK] {imported} contacts importés depuis SQL Server")
                return imported
        except ImportError as e:
            print(f"[AVERTISSEMENT] Module SQL Server non disponible: {e}")
        except Exception as e:
            print(f"[AVERTISSEMENT] Erreur import depuis SQL Server: {e}")
    
    # Option 2: Depuis l'API GraphQL (fallback)
    print("[INFO] Tentative d'import depuis l'API GraphQL...")
    
    # Récupérer les contacts via client(id) pour chaque client
    query = """
    query GetClientContacts($clientId: ID!) {
      client(id: $clientId) {
        id
        contacts {
          nodes {
            id
            firstName
            lastName
          }
        }
      }
    }
    """
    
    cursor = conn.cursor()
    imported = 0
    contacts_seen = set()
    
    # Pour chaque client, récupérer ses contacts
    for client_id in client_ids:
        payload = {
            "query": query,
            "variables": {
                "clientId": client_id
            }
        }
        
        result = make_api_call(payload)
        if not result or 'data' not in result or 'client' not in result['data']:
            continue
        
        client_data = result['data']['client']
        if not client_data:
            continue
        
        contacts_data = client_data.get('contacts', {}).get('nodes', [])
        
        for contact_data in contacts_data:
            contact_id = contact_data.get('id')
            if not contact_id or contact_id in contacts_seen:
                continue
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO Contacts (Id, ClientId, FirstName, LastName)
                    VALUES (?, ?, ?, ?)
                """, (
                    contact_id,
                    client_id,
                    contact_data.get('firstName'),
                    contact_data.get('lastName')
                ))
                contacts_seen.add(contact_id)
                imported += 1
            except Exception as e:
                print(f"[ERREUR] Erreur import contact {contact_id}: {e}")
    
    conn.commit()
    if imported > 0:
        print(f"[OK] {imported} contacts importés depuis l'API")
    else:
        print("[AVERTISSEMENT] Aucun contact importé depuis l'API")
    return imported


def import_pianos(conn, client_ids):
    """Importe les pianos pour les clients spécifiés"""
    if not client_ids:
        return 0
    
    print(f"[INFO] Import des pianos pour {len(client_ids)} clients...")
    
    # Option 1: Depuis SQL Server si disponible
    if USE_SQL_SERVER_FOR_INITIAL_IMPORT and SQL_SERVER_CONN_STR:
        try:
            # Import relatif depuis le même dossier
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, script_dir)
            from import_contacts_pianos_from_sql_server import import_pianos_from_sql_server
            imported = import_pianos_from_sql_server(SQL_SERVER_CONN_STR, conn, set(client_ids))
            if imported > 0:
                print(f"[OK] {imported} pianos importés depuis SQL Server")
                return imported
        except ImportError as e:
            print(f"[AVERTISSEMENT] Module SQL Server non disponible: {e}")
        except Exception as e:
            print(f"[AVERTISSEMENT] Erreur import depuis SQL Server: {e}")
    
    # Option 2: Depuis l'API GraphQL (fallback)
    print("[INFO] Tentative d'import depuis l'API GraphQL...")
    
    # Récupérer les pianos via client(id) pour chaque client
    query = """
    query GetClientPianos($clientId: ID!) {
      client(id: $clientId) {
        id
        pianos {
          nodes {
            id
            clientId
            make
            model
            serialNumber
            type
            year
            location
            notes
          }
        }
      }
    }
    """
    
    cursor = conn.cursor()
    imported = 0
    pianos_seen = set()
    
    # Pour chaque client, récupérer ses pianos
    for client_id in client_ids:
        payload = {
            "query": query,
            "variables": {
                "clientId": client_id
            }
        }
        
        result = make_api_call(payload)
        if not result or 'data' not in result or 'client' not in result['data']:
            continue
        
        client_data = result['data']['client']
        if not client_data:
            continue
        
        pianos_data = client_data.get('pianos', {}).get('nodes', [])
        
        for piano_data in pianos_data:
            piano_id = piano_data.get('id')
            if not piano_id or piano_id in pianos_seen:
                continue
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO Pianos 
                    (Id, ClientId, Make, Model, SerialNumber, Type, Year, Notes, Location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    piano_id,
                    client_id,
                    piano_data.get('make'),
                    piano_data.get('model'),
                    piano_data.get('serialNumber'),
                    piano_data.get('type'),
                    piano_data.get('year'),
                    piano_data.get('notes'),
                    piano_data.get('location')
                ))
                pianos_seen.add(piano_id)
                imported += 1
            except Exception as e:
                print(f"[ERREUR] Erreur import piano {piano_id}: {e}")
    
    conn.commit()
    if imported > 0:
        print(f"[OK] {imported} pianos importés depuis l'API")
    else:
        print("[AVERTISSEMENT] Aucun piano importé depuis l'API")
    return imported
    
    cursor = conn.cursor()
    imported = 0
    pianos_seen = set()
    has_next_page = True
    after_cursor = None
    
    # Récupérer les rendez-vous pour accéder aux pianos
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
    
    filters = {
        "startOn": start_date,
        "endOn": end_date,
        "type": ["APPOINTMENT"]
    }
    
    while has_next_page:
        payload = {
            "query": query,
            "variables": {
                "first": 100,
                "after": after_cursor,
                "filters": filters
            }
        }
        
        result = make_api_call(payload)
        if not result or 'data' not in result or 'allEventsBatched' not in result['data']:
            break
        
        batch = result['data']['allEventsBatched']
        nodes = batch.get('nodes', [])
        
        for node in nodes:
            if node.get('clientId') not in client_ids:
                continue
            
            piano_data = node.get('piano')
            if not piano_data:
                continue
            
            piano_id = piano_data.get('id')
            if not piano_id or piano_id in pianos_seen:
                continue
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO Pianos 
                    (Id, ClientId, Make, Model, SerialNumber, Type, Year, Notes, Location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    piano_id,
                    piano_data.get('clientId'),
                    piano_data.get('make'),
                    piano_data.get('model'),
                    piano_data.get('serialNumber'),
                    piano_data.get('type'),
                    piano_data.get('year'),
                    piano_data.get('notes'),
                    piano_data.get('location')
                ))
                pianos_seen.add(piano_id)
                imported += 1
            except Exception as e:
                print(f"[ERREUR] Erreur import piano {piano_id}: {e}")
        
        page_info = batch.get('pageInfo', {})
        has_next_page = page_info.get('hasNextPage', False)
        after_cursor = page_info.get('endCursor')
    
    conn.commit()
    print(f"[OK] {imported} pianos importés")
    return imported


def import_appointments(conn, client_ids, days_back=60, days_forward=365):
    """Importe les rendez-vous pour les clients spécifiés"""
    if not client_ids:
        return 0
    
    print(f"[INFO] Import des rendez-vous (60 jours passés, 365 jours futurs)...")
    
    start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=days_forward)).strftime('%Y-%m-%d')
    
    query = """
    query GetAppointments($first: Int, $after: String, $filters: PrivateAllEventsFilter) {
      allEventsBatched(first: $first, after: $after, filters: $filters) {
        nodes {
          id
          client {
            id
          }
          start
          confirmedByClient
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    cursor = conn.cursor()
    imported = 0
    has_next_page = True
    after_cursor = None
    
    filters = {
        "startOn": start_date,
        "endOn": end_date,
        "type": ["APPOINTMENT"]
    }
    
    while has_next_page:
        payload = {
            "query": query,
            "variables": {
                "first": 100,
                "after": after_cursor,
                "filters": filters
            }
        }
        
        result = make_api_call(payload)
        if not result or 'data' not in result or 'allEventsBatched' not in result['data']:
            break
        
        batch = result['data']['allEventsBatched']
        nodes = batch.get('nodes', [])
        
        for node in nodes:
            # Extraire clientId depuis l'objet client
            client_obj = node.get('client', {})
            client_id = client_obj.get('id') if client_obj else None
            
            # Filtrer seulement les clients importés
            if not client_id or client_id not in client_ids:
                continue
            
            try:
                # L'API GraphQL ne retourne que id, start, confirmedByClient
                # Les autres champs seront NULL pour l'instant
                cursor.execute("""
                    INSERT OR REPLACE INTO Appointments 
                    (Id, ClientId, TechnicianId, PianoId, Description, AppointmentStatus, EventType,
                     StartAt, Duration, IsAllDay, Notes, ConfirmedByClient)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    node.get('id'),
                    client_id,
                    None,  # TechnicianId - non disponible dans cette query
                    None,  # PianoId - non disponible dans cette query
                    None,  # Description - non disponible dans cette query
                    'ACTIVE',  # Par défaut
                    'APPOINTMENT',  # Par défaut
                    format_datetime(node.get('start')),
                    None,  # Duration - non disponible
                    0,  # IsAllDay - par défaut
                    None,  # Notes - non disponible
                    1 if node.get('confirmedByClient') else 0
                ))
                imported += 1
            except Exception as e:
                print(f"[ERREUR] Erreur import appointment {node.get('id')}: {e}")
        
        page_info = batch.get('pageInfo', {})
        has_next_page = page_info.get('hasNextPage', False)
        after_cursor = page_info.get('endCursor')
    
    conn.commit()
    print(f"[OK] {imported} rendez-vous importés")
    return imported


def import_timeline(conn, client_ids):
    """Importe TOUTE la timeline pour les clients spécifiés (sans limite de date)"""
    if not client_ids:
        return 0
    
    print(f"[INFO] Import de TOUTE la timeline pour {len(client_ids)} clients (sans limite de date)...")
    
    # Récupérer la timeline via client(id) pour chaque client
    query = """
    query GetClientTimeline($clientId: ID!, $first: Int, $after: String) {
      client(id: $clientId) {
        id
        timelineEntries(first: $first, after: $after) {
          nodes {
            id
            pianoId
            invoiceId
            estimateId
            occurredAt
            entryType
            title
            details
            userId
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    
    cursor = conn.cursor()
    imported = 0
    timeline_seen = set()
    
    # Pour chaque client, récupérer sa timeline (paginée)
    for client_id in client_ids:
        has_next_page = True
        after_cursor = None
        
        while has_next_page:
            payload = {
                "query": query,
                "variables": {
                    "clientId": client_id,
                    "first": 100,
                    "after": after_cursor
                }
            }
            
            result = make_api_call(payload)
            if not result or 'data' not in result or 'client' not in result['data']:
                break
            
            client_data = result['data']['client']
            if not client_data:
                break
            
            timeline_data = client_data.get('timelineEntries', {})
            nodes = timeline_data.get('nodes', [])
            
            for node in nodes:
                timeline_id = node.get('id')
                if not timeline_id or timeline_id in timeline_seen:
                    continue
                
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO TimelineEntries 
                        (Id, ClientId, PianoId, InvoiceId, EstimateId, OccurredAt, EntryType, Title, Details, UserId)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        timeline_id,
                        client_id,
                        node.get('pianoId'),
                        node.get('invoiceId'),
                        node.get('estimateId'),
                        format_datetime(node.get('occurredAt')),
                        node.get('entryType'),
                        node.get('title'),
                        node.get('details'),
                        node.get('userId')
                    ))
                    timeline_seen.add(timeline_id)
                    imported += 1
                except Exception as e:
                    print(f"[ERREUR] Erreur import timeline {timeline_id}: {e}")
            
            page_info = timeline_data.get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)
            after_cursor = page_info.get('endCursor')
    
    conn.commit()
    print(f"[OK] {imported} entrées de timeline importées")
    return imported


def import_invoices(conn, client_ids):
    """Importe les factures pour les clients spécifiés"""
    if not client_ids:
        return 0
    
    print(f"[INFO] Import des factures pour {len(client_ids)} clients...")
    
    # Récupérer les factures via client(id) pour chaque client
    query = """
    query GetClientInvoices($clientId: ID!, $first: Int, $after: String) {
      client(id: $clientId) {
        id
        invoices(first: $first, after: $after) {
          nodes {
            id
            number
            status
            subTotal {
              amount
            }
            total {
              amount
            }
            notes
            createdAt
            dueOn
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    
    cursor = conn.cursor()
    imported = 0
    invoices_seen = set()
    
    # Pour chaque client, récupérer ses factures (paginées)
    for client_id in client_ids:
        has_next_page = True
        after_cursor = None
        
        while has_next_page:
            payload = {
                "query": query,
                "variables": {
                    "clientId": client_id,
                    "first": 100,
                    "after": after_cursor
                }
            }
            
            result = make_api_call(payload)
            if not result or 'data' not in result or 'client' not in result['data']:
                break
            
            client_data = result['data']['client']
            if not client_data:
                break
            
            invoices_data = client_data.get('invoices', {})
            nodes = invoices_data.get('nodes', [])
            
            for node in nodes:
                invoice_id = node.get('id')
                if not invoice_id or invoice_id in invoices_seen:
                    continue
                
                try:
                    sub_total = node.get('subTotal', {}).get('amount') if node.get('subTotal') else None
                    total = node.get('total', {}).get('amount') if node.get('total') else None
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO Invoices 
                        (Id, ClientId, Number, Status, SubTotal, Total, Notes, CreatedAt, DueOn)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        invoice_id,
                        client_id,
                        node.get('number'),
                        node.get('status'),
                        sub_total,
                        total,
                        node.get('notes'),
                        format_datetime(node.get('createdAt')),
                        format_datetime(node.get('dueOn'))
                    ))
                    invoices_seen.add(invoice_id)
                    imported += 1
                except Exception as e:
                    print(f"[ERREUR] Erreur import invoice {invoice_id}: {e}")
            
            page_info = invoices_data.get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)
            after_cursor = page_info.get('endCursor')
    
    conn.commit()
    print(f"[OK] {imported} factures importées")
    return imported


def main():
    """Fonction principale"""
    global current_tokens
    
    print("=" * 70)
    print("IMPORT GAZELLE -> SQLITE - Version Web")
    print("=" * 70)
    
    # 1. Charger les tokens OAuth
    print("\n[INFO] Chargement des tokens OAuth...")
    current_tokens = load_tokens()
    if not current_tokens:
        print("[ERREUR] Impossible de charger les tokens. Vérifiez data/gazelle_token.json")
        return 1
    
    print("[OK] Tokens chargés")
    
    # 2. Créer/ouvrir la base SQLite
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[INFO] Connexion à la base SQLite: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")  # Activer les foreign keys
    
    # 3. Créer le schéma
    print("\n[INFO] Création du schéma de base de données...")
    create_database_schema(conn)
    
    # 4. Importer les données
    print(f"\n[INFO] Début de l'import (limite: {MAX_CLIENTS} clients)...")
    
    # Clients
    client_count = import_clients(conn, limit=MAX_CLIENTS)
    if client_count == 0:
        print("[ERREUR] Aucun client importé, arrêt")
        conn.close()
        return 1
    
    # Récupérer les IDs des clients importés
    cursor = conn.cursor()
    cursor.execute("SELECT Id FROM Clients")
    client_ids = [row[0] for row in cursor.fetchall()]
    
    # Contacts
    import_contacts(conn, client_ids)
    
    # Pianos
    import_pianos(conn, client_ids)
    
    # Appointments
    import_appointments(conn, client_ids)
    
    # Timeline - TOUTE la timeline pour les clients importés (sans limite de date)
    import_timeline(conn, client_ids)
    
    # Invoices (optionnel, peut échouer si l'API ne supporte pas)
    try:
        import_invoices(conn, client_ids)
    except Exception as e:
        print(f"[AVERTISSEMENT] Import invoices échoué: {e}")
    
    # 5. Résumé
    print("\n" + "=" * 70)
    print("RÉSUMÉ DE L'IMPORT")
    print("=" * 70)
    
    cursor.execute("SELECT COUNT(*) FROM Clients")
    print(f"Clients: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM Contacts")
    print(f"Contacts: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM Pianos")
    print(f"Pianos: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM Appointments")
    print(f"Rendez-vous: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM TimelineEntries")
    print(f"Timeline: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM Invoices")
    print(f"Factures: {cursor.fetchone()[0]}")
    
    print("=" * 70)
    print(f"[OK] Import terminé avec succès dans {db_path}")
    
    conn.close()
    return 0


if __name__ == "__main__":
    exit(main())

