"""
Fonction utilitaire pour importer contacts et pianos depuis SQL Server
Utilisé pour l'import initial quand l'API GraphQL ne permet pas de récupérer ces données directement
"""

import pyodbc
import sqlite3
from typing import List, Set
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def import_contacts_from_sql_server(sql_server_conn_str: str, sqlite_conn: sqlite3.Connection, client_ids: Set[str]) -> int:
    """
    Importe les contacts depuis SQL Server pour les clients spécifiés.
    
    Args:
        sql_server_conn_str: Chaîne de connexion SQL Server
        sqlite_conn: Connexion SQLite
        client_ids: Set des IDs de clients à importer
        
    Returns:
        Nombre de contacts importés
    """
    if not client_ids:
        return 0
    
    try:
        sql_server_conn = pyodbc.connect(sql_server_conn_str)
        cursor_sql = sql_server_conn.cursor()
        cursor_sqlite = sqlite_conn.cursor()
        
        # Convertir le set en tuple pour la requête SQL
        client_ids_tuple = tuple(client_ids)
        placeholders = ','.join(['?' for _ in client_ids])
        
        query = f"""
            SELECT Id, ClientId, FirstName, LastName
            FROM Contacts
            WHERE ClientId IN ({placeholders})
        """
        
        cursor_sql.execute(query, client_ids_tuple)
        imported = 0
        
        for row in cursor_sql.fetchall():
            try:
                cursor_sqlite.execute("""
                    INSERT OR REPLACE INTO Contacts (Id, ClientId, FirstName, LastName)
                    VALUES (?, ?, ?, ?)
                """, (row.Id, row.ClientId, row.FirstName, row.LastName))
                imported += 1
            except Exception as e:
                logger.error(f"Erreur import contact {row.Id}: {e}")
        
        sqlite_conn.commit()
        sql_server_conn.close()
        
        logger.info(f"{imported} contacts importés depuis SQL Server")
        return imported
        
    except Exception as e:
        logger.error(f"Erreur lors de l'import des contacts depuis SQL Server: {e}")
        return 0


def import_pianos_from_sql_server(sql_server_conn_str: str, sqlite_conn: sqlite3.Connection, client_ids: Set[str]) -> int:
    """
    Importe les pianos depuis SQL Server pour les clients spécifiés.
    
    Args:
        sql_server_conn_str: Chaîne de connexion SQL Server
        sqlite_conn: Connexion SQLite
        client_ids: Set des IDs de clients à importer
        
    Returns:
        Nombre de pianos importés
    """
    if not client_ids:
        return 0
    
    try:
        sql_server_conn = pyodbc.connect(sql_server_conn_str)
        cursor_sql = sql_server_conn.cursor()
        cursor_sqlite = sqlite_conn.cursor()
        
        # Convertir le set en tuple pour la requête SQL
        client_ids_tuple = tuple(client_ids)
        placeholders = ','.join(['?' for _ in client_ids])
        
        query = f"""
            SELECT Id, ClientId, Make, Model, SerialNumber, Type, Year, Notes, Location
            FROM Pianos
            WHERE ClientId IN ({placeholders})
        """
        
        cursor_sql.execute(query, client_ids_tuple)
        imported = 0
        
        for row in cursor_sql.fetchall():
            try:
                cursor_sqlite.execute("""
                    INSERT OR REPLACE INTO Pianos 
                    (Id, ClientId, Make, Model, SerialNumber, Type, Year, Notes, Location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.Id, row.ClientId, row.Make, row.Model, row.SerialNumber,
                    row.Type, row.Year, row.Notes, row.Location
                ))
                imported += 1
            except Exception as e:
                logger.error(f"Erreur import piano {row.Id}: {e}")
        
        sqlite_conn.commit()
        sql_server_conn.close()
        
        logger.info(f"{imported} pianos importés depuis SQL Server")
        return imported
        
    except Exception as e:
        logger.error(f"Erreur lors de l'import des pianos depuis SQL Server: {e}")
        return 0

