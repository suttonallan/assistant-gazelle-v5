#!/usr/bin/env python3
"""
Module de synchronisation des données de l'API Gazelle vers SQLite.

Synchronise les clients et les alertes de maintenance depuis l'API GraphQL
vers la base de données SQLite locale.
"""

import sqlite3
import os
from typing import Dict, Optional
from .gazelle_api_client import GazelleAPIClient
from .db_utils import get_db_path, ensure_db_directory


class SyncManager:
    """Gère la synchronisation des données API vers SQLite."""
    
    def __init__(self, db_path: str = None):
        """
        Initialise le gestionnaire de synchronisation.
        
        Args:
            db_path: Chemin vers la base de données SQLite (défaut: utilise get_db_path())
        """
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        ensure_db_directory(db_path)
        self.api = GazelleAPIClient()
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Permet l'accès par nom de colonne
        
        # Mapping des ExternalId (API) vers les Id internes (SQLite)
        self.external_id_to_internal_id: Dict[str, int] = {}
        self.has_external_id_column = False
        self._check_external_id_column()
        self._load_client_mapping()
    
    def _check_external_id_column(self) -> None:
        """Vérifie si la colonne ExternalId existe dans la table Clients."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(Clients)")
            columns = [col[1] for col in cursor.fetchall()]
            self.has_external_id_column = 'ExternalId' in columns
        except sqlite3.OperationalError:
            self.has_external_id_column = False
    
    def _load_client_mapping(self) -> None:
        """Charge le mapping des ExternalId vers les Id internes depuis la DB."""
        if not self.has_external_id_column:
            return
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT Id, ExternalId FROM Clients WHERE ExternalId IS NOT NULL")
            for row in cursor.fetchall():
                self.external_id_to_internal_id[row['ExternalId']] = row['Id']
        except sqlite3.OperationalError:
            # La colonne ExternalId n'existe peut-être pas encore
            pass
    
    def _ensure_external_id_column(self) -> None:
        """S'assure que la colonne ExternalId existe dans la table Clients."""
        if self.has_external_id_column:
            return
        
        cursor = self.conn.cursor()
        try:
            # Ajouter sans UNIQUE car SQLite ne peut pas ajouter UNIQUE à une table existante avec données
            cursor.execute("ALTER TABLE Clients ADD COLUMN ExternalId TEXT")
            self.conn.commit()
            self.has_external_id_column = True
            print("✅ Colonne ExternalId ajoutée à la table Clients")
        except sqlite3.OperationalError as e:
            print(f"⚠️ Erreur lors de l'ajout de la colonne ExternalId: {e}")
    
    def sync_clients(self) -> int:
        """
        Synchronise les clients depuis l'API vers SQLite.
        
        Returns:
            Nombre de clients synchronisés
        """
        try:
            # S'assurer que la colonne ExternalId existe
            self._ensure_external_id_column()
            
            # Récupérer les clients depuis l'API
            api_clients = self.api.get_clients()
            
            if not api_clients:
                print("⚠️ Aucun client récupéré depuis l'API")
                return 0
            
            cursor = self.conn.cursor()
            synced_count = 0
            
            for client_data in api_clients:
                try:
                    external_id = client_data.get('id')  # ID de l'API (format cli_xxx)
                    company_name_raw = client_data.get('companyName')
                    company_name = company_name_raw.strip() if company_name_raw else ''
                    
                    # Extraire les données du contact par défaut
                    default_contact = client_data.get('defaultContact', {})
                    default_contact_id = default_contact.get('id') if default_contact else None
                    
                    # Si CompanyName est vide, utiliser "FirstName LastName" du defaultContact
                    if not company_name and default_contact:
                        first_name = default_contact.get('firstName', '').strip()
                        last_name = default_contact.get('lastName', '').strip()
                        if first_name or last_name:
                            company_name = f"{first_name} {last_name}".strip()
                    
                    # Si toujours vide après le fallback, ignorer
                    if not company_name:
                        print(f"⚠️ Client {external_id} ignoré (CompanyName et nom de contact vides)")
                        continue
                    
                    email = None
                    phone = None
                    address = None
                    
                    if default_contact:
                        default_email = default_contact.get('defaultEmail', {})
                        if default_email:
                            email = default_email.get('email')
                        
                        default_phone = default_contact.get('defaultPhone', {})
                        if default_phone:
                            phone = default_phone.get('phoneNumber')
                        
                        default_location = default_contact.get('defaultLocation', {})
                        if default_location:
                            municipality = default_location.get('municipality', '')
                            postal_code = default_location.get('postalCode', '')
                            if municipality or postal_code:
                                address = f"{municipality} {postal_code}".strip()
                    
                    # Vérifier si le client existe déjà (par ExternalId si disponible, sinon par CompanyName)
                    if self.has_external_id_column:
                        cursor.execute("SELECT Id FROM Clients WHERE ExternalId = ?", (external_id,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # UPDATE
                            cursor.execute("""
                                UPDATE Clients 
                                SET CompanyName = ?, 
                                    DefaultContactId = ?,
                                    Email = ?,
                                    Phone = ?,
                                    Address = ?
                                WHERE ExternalId = ?
                            """, (company_name, default_contact_id, email, phone, address, external_id))
                            internal_id = existing['Id']
                        else:
                            # INSERT
                            cursor.execute("""
                                INSERT INTO Clients (ExternalId, CompanyName, DefaultContactId, Email, Phone, Address)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (external_id, company_name, default_contact_id, email, phone, address))
                            internal_id = cursor.lastrowid
                    else:
                        # Fallback: utiliser CompanyName pour trouver le client existant
                        cursor.execute("SELECT Id FROM Clients WHERE CompanyName = ?", (company_name,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # UPDATE
                            cursor.execute("""
                                UPDATE Clients 
                                SET CompanyName = ?, 
                                    DefaultContactId = ?,
                                    Email = ?,
                                    Phone = ?,
                                    Address = ?
                                WHERE Id = ?
                            """, (company_name, default_contact_id, email, phone, address, existing['Id']))
                            internal_id = existing['Id']
                        else:
                            # INSERT
                            cursor.execute("""
                                INSERT INTO Clients (CompanyName, DefaultContactId, Email, Phone, Address)
                                VALUES (?, ?, ?, ?, ?)
                            """, (company_name, default_contact_id, email, phone, address))
                            internal_id = cursor.lastrowid
                    
                    # Mettre à jour le mapping
                    self.external_id_to_internal_id[external_id] = internal_id
                    synced_count += 1
                    
                except Exception as e:
                    print(f"❌ Erreur lors de la synchronisation du client {client_data.get('id', 'unknown')}: {e}")
                    continue
            
            self.conn.commit()
            print(f"✅ {synced_count} clients synchronisés")
            return synced_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Erreur lors de la synchronisation des clients: {e}")
            raise
    
    def sync_maintenance_alerts(self) -> int:
        """
        Synchronise les alertes de maintenance depuis l'API vers SQLite.
        
        Note: Les alertes de maintenance ne sont pas récupérées depuis l'API Gazelle.
        Elles sont créées en interne en analysant les timeline entries.
        
        Returns:
            Nombre d'alertes synchronisées (toujours 0 car non disponible depuis l'API)
        """
        print("ℹ️  Les alertes de maintenance ne sont pas synchronisées depuis l'API Gazelle.")
        print("   Elles sont créées en interne en analysant les timeline entries.")
        return 0
    
    def sync_all(self) -> None:
        """
        Synchronise tous les types de données (clients puis alertes).
        Affiche un résumé de la synchronisation.
        """
        print("=" * 60)
        print("🔄 Début de la synchronisation Gazelle → SQLite")
        print("=" * 60)
        
        try:
            # Synchroniser les clients d'abord (nécessaire pour les alertes)
            print("\n📋 Synchronisation des clients...")
            clients_count = self.sync_clients()
            
            # Synchroniser les alertes
            print("\n🔔 Synchronisation des alertes de maintenance...")
            alerts_count = self.sync_maintenance_alerts()
            
            # Résumé
            print("\n" + "=" * 60)
            print("✅ Synchronisation terminée")
            print("=" * 60)
            print(f"📊 Résumé:")
            print(f"   • Clients synchronisés: {clients_count}")
            print(f"   • Alertes synchronisées: {alerts_count}")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Erreur lors de la synchronisation: {e}")
            raise
        finally:
            self.conn.close()
    
    def close(self) -> None:
        """Ferme la connexion à la base de données."""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    try:
        sync_manager = SyncManager()
        sync_manager.sync_all()
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        exit(1)

