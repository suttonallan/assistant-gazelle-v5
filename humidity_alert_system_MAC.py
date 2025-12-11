import sqlite3
import os

# CHANGEMENT CRITIQUE: Pointez vers la nouvelle base de données migrée
DB_PATH = 'db_test_v5.sqlite'


def get_db_connection():
    """
    Remplace l'ancienne connexion (ex: SQL Server, API).
    Retourne une connexion SQLite vers la base de données migrée.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    # Active les clés étrangères pour l'intégrité des données
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def check_alerts():
    """
    Fonction principale pour vérifier les alertes de maintenance.
    Adaptez cette fonction selon vos besoins spécifiques.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Exemple de requête pour récupérer les alertes non résolues
        # Adaptez selon votre schéma et vos besoins
        cursor.execute("""
            SELECT 
                ma.Id,
                ma.DateObservation,
                ma.AlertType,
                ma.Description,
                ma.IsResolved,
                c.CompanyName as ClientName
            FROM MaintenanceAlerts ma
            LEFT JOIN Clients c ON c.Id = ma.ClientId
            WHERE ma.IsResolved = 0
            ORDER BY ma.DateObservation DESC
        """)
        
        alerts = cursor.fetchall()
        
        # Convertir les Row objects en dictionnaires pour faciliter l'utilisation
        result = []
        for row in alerts:
            result.append(dict(row))
        
        return result
        
    except sqlite3.Error as e:
        print(f"Erreur SQLite: {e}")
        return []
    finally:
        conn.close()


def get_client_alerts(client_id):
    """
    Récupère toutes les alertes pour un client spécifique.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                ma.Id,
                ma.DateObservation,
                ma.AlertType,
                ma.Description,
                ma.IsResolved,
                ma.ResolvedDate
            FROM MaintenanceAlerts ma
            WHERE ma.ClientId = ?
            ORDER BY ma.DateObservation DESC
        """, (client_id,))
        
        alerts = cursor.fetchall()
        return [dict(row) for row in alerts]
        
    except sqlite3.Error as e:
        print(f"Erreur SQLite: {e}")
        return []
    finally:
        conn.close()


def resolve_alert(alert_id):
    """
    Marque une alerte comme résolue.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        from datetime import datetime
        resolved_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            UPDATE MaintenanceAlerts
            SET IsResolved = 1,
                ResolvedDate = ?
            WHERE Id = ?
        """, (resolved_date, alert_id))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except sqlite3.Error as e:
        print(f"Erreur SQLite: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    # Exemple d'utilisation
    print("🔍 Vérification des alertes de maintenance...")
    alerts = check_alerts()
    
    if alerts:
        print(f"\n✅ {len(alerts)} alerte(s) non résolue(s) trouvée(s):\n")
        for alert in alerts:
            print(f"  - Alerte #{alert['Id']}: {alert['AlertType']}")
            print(f"    Client: {alert.get('ClientName', 'N/A')}")
            print(f"    Date: {alert['DateObservation']}")
            print(f"    Description: {alert['Description'][:50]}...")
            print()
    else:
        print("✅ Aucune alerte non résolue.")




