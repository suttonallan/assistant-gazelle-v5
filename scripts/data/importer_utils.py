#!/usr/bin/env python3
"""
Utilitaires pour importer des données CSV/JSON depuis Gazelle vers Supabase.
Supporte l'import par lots (batch) pour optimiser les performances.

Usage:
    from scripts.data.importer_utils import GazelleImporter

    importer = GazelleImporter()
    importer.import_clients_from_csv('data/export_gazelle_clients.csv')
    importer.import_pianos_from_json('data/export_gazelle_pianos.json')
"""

import os
import sys
import csv
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from core.supabase_storage import SupabaseStorage

load_dotenv()


class GazelleImporter:
    """
    Classe pour importer des données Gazelle vers Supabase.
    """

    # Taille des lots pour insertion batch
    BATCH_SIZE = 100

    # Mapping des colonnes Gazelle → Supabase (à adapter selon exports réels)
    COLUMN_MAPPING = {
        'clients': {
            'GazelleClientId': 'gazelle_id',
            'LastName': 'nom',
            'FirstName': 'prenom',
            'Email': 'email',
            'Phone': 'telephone',
            'MobilePhone': 'telephone_mobile',
            'Address': 'adresse',
            'City': 'ville',
            'PostalCode': 'code_postal',
            'Province': 'province',
            'Country': 'pays',
            'Notes': 'notes',
            'ClientType': 'type_client',
            'Status': 'statut'
        },
        'pianos': {
            'GazellePianoId': 'gazelle_id',
            'GazelleClientId': 'gazelle_client_id_temp',  # Sera résolu en client_id
            'SerialNumber': 'numero_serie',
            'Brand': 'marque',
            'Model': 'modele',
            'Type': 'type_piano',
            'YearManufactured': 'annee_fabrication',
            'Location': 'localisation',
            'Notes': 'notes',
            'Status': 'statut'
        },
        'appointments': {
            'GazelleAppointmentId': 'gazelle_id',
            'GazelleClientId': 'gazelle_client_id_temp',
            'GazellePianoId': 'gazelle_piano_id_temp',
            'TechnicianId': 'technicien_id',
            'TechnicianName': 'technicien_nom',
            'Title': 'titre',
            'Description': 'description',
            'StartDate': 'date_debut',
            'EndDate': 'date_fin',
            'DurationMinutes': 'duree_minutes',
            'ServiceType': 'type_service',
            'Status': 'statut',
            'ServiceAddress': 'adresse_service',
            'TechnicianNotes': 'notes_technicien',
            'EstimatedAmount': 'montant_prevu',
            'FinalAmount': 'montant_final'
        }
    }

    def __init__(self):
        """Initialise le storage Supabase."""
        self.storage = SupabaseStorage()
        print("✅ GazelleImporter initialisé")

    def read_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Lit un fichier CSV et retourne une liste de dictionnaires.

        Args:
            file_path: Chemin vers le fichier CSV

        Returns:
            Liste de dictionnaires (une ligne = un dict)
        """
        data = []
        csv_path = Path(file_path)

        if not csv_path.exists():
            print(f"❌ Fichier CSV introuvable: {file_path}")
            return data

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)

        print(f"📄 CSV lu: {len(data)} lignes depuis {csv_path.name}")
        return data

    def read_json(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Lit un fichier JSON et retourne une liste de dictionnaires.

        Args:
            file_path: Chemin vers le fichier JSON

        Returns:
            Liste de dictionnaires
        """
        json_path = Path(file_path)

        if not json_path.exists():
            print(f"❌ Fichier JSON introuvable: {file_path}")
            return []

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Si c'est un dict avec une clé 'data' ou 'results', extraire
        if isinstance(data, dict):
            if 'data' in data:
                data = data['data']
            elif 'results' in data:
                data = data['results']

        print(f"📄 JSON lu: {len(data)} éléments depuis {json_path.name}")
        return data

    def map_columns(
        self,
        row: Dict[str, Any],
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Mappe les colonnes Gazelle vers les colonnes Supabase.

        Args:
            row: Ligne source (dict Gazelle)
            entity_type: Type d'entité ('clients', 'pianos', 'appointments')

        Returns:
            Dictionnaire avec colonnes Supabase
        """
        if entity_type not in self.COLUMN_MAPPING:
            print(f"⚠️  Type d'entité inconnu: {entity_type}")
            return row

        mapping = self.COLUMN_MAPPING[entity_type]
        mapped_row = {}

        for gazelle_col, supabase_col in mapping.items():
            if gazelle_col in row and row[gazelle_col]:
                value = row[gazelle_col]

                # Conversions spécifiques
                if supabase_col.endswith('_id') and value:
                    # Garder les IDs comme string
                    mapped_row[supabase_col] = str(value)
                elif 'date' in supabase_col.lower() and value:
                    # Parser les dates si besoin
                    try:
                        # Format attendu: ISO 8601 ou 'YYYY-MM-DD HH:MM:SS'
                        if 'T' in value or ' ' in value:
                            mapped_row[supabase_col] = value
                        else:
                            mapped_row[supabase_col] = f"{value}T00:00:00"
                    except:
                        mapped_row[supabase_col] = value
                elif 'annee' in supabase_col and value:
                    # Années en integer
                    try:
                        mapped_row[supabase_col] = int(value)
                    except:
                        mapped_row[supabase_col] = None
                elif 'montant' in supabase_col and value:
                    # Montants en float
                    try:
                        mapped_row[supabase_col] = float(str(value).replace(',', '.'))
                    except:
                        mapped_row[supabase_col] = 0.0
                else:
                    mapped_row[supabase_col] = value

        # Ajouter timestamp de synchronisation
        mapped_row['last_sync_gazelle'] = datetime.now().isoformat()

        return mapped_row

    def resolve_foreign_keys(
        self,
        data: List[Dict[str, Any]],
        entity_type: str
    ) -> List[Dict[str, Any]]:
        """
        Résout les clés étrangères (gazelle_id → UUID Supabase).

        Args:
            data: Liste des lignes mappées
            entity_type: Type d'entité

        Returns:
            Liste avec clés étrangères résolues
        """
        if entity_type not in ['pianos', 'appointments']:
            return data

        print(f"🔗 Résolution des clés étrangères pour {entity_type}...")

        # Construire un mapping gazelle_id → uuid pour clients et pianos
        clients_map = {}
        pianos_map = {}

        if entity_type in ['pianos', 'appointments']:
            clients = self.storage.get_data('clients')
            for client in clients:
                if client.get('gazelle_id'):
                    clients_map[client['gazelle_id']] = client['id']

        if entity_type == 'appointments':
            pianos = self.storage.get_data('pianos')
            for piano in pianos:
                if piano.get('gazelle_id'):
                    pianos_map[piano['gazelle_id']] = piano['id']

        # Résoudre les références
        resolved_data = []
        for row in data:
            # Clients
            if 'gazelle_client_id_temp' in row:
                gazelle_client_id = row.pop('gazelle_client_id_temp')
                if gazelle_client_id in clients_map:
                    row['client_id'] = clients_map[gazelle_client_id]
                else:
                    print(f"⚠️  Client Gazelle {gazelle_client_id} introuvable")

            # Pianos
            if 'gazelle_piano_id_temp' in row:
                gazelle_piano_id = row.pop('gazelle_piano_id_temp')
                if gazelle_piano_id in pianos_map:
                    row['piano_id'] = pianos_map[gazelle_piano_id]
                else:
                    print(f"⚠️  Piano Gazelle {gazelle_piano_id} introuvable")

            resolved_data.append(row)

        return resolved_data

    def import_batch(
        self,
        table_name: str,
        data: List[Dict[str, Any]],
        batch_size: int = BATCH_SIZE
    ) -> int:
        """
        Importe des données par lots dans Supabase.

        Args:
            table_name: Nom de la table cible
            data: Liste des lignes à insérer
            batch_size: Taille des lots

        Returns:
            Nombre de lignes insérées avec succès
        """
        total = len(data)
        success_count = 0

        print(f"\n📦 Import vers {table_name}: {total} lignes")

        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size

            print(f"   Lot {batch_num}/{total_batches} ({len(batch)} lignes)...", end=" ")

            try:
                # Utiliser l'API REST directement pour batch insert
                url = f"{self.storage.api_url}/{table_name}"
                headers = self.storage._get_headers()
                headers["Prefer"] = "resolution=merge-duplicates"

                response = requests.post(url, headers=headers, json=batch, timeout=30)

                if response.status_code in [200, 201, 204]:
                    success_count += len(batch)
                    print("✅")
                else:
                    print(f"❌ Erreur {response.status_code}: {response.text[:100]}")

            except Exception as e:
                print(f"❌ Exception: {e}")

        print(f"\n✅ Import terminé: {success_count}/{total} lignes insérées\n")
        return success_count

    def import_clients_from_csv(self, csv_file: str) -> int:
        """Importe les clients depuis un CSV Gazelle."""
        print("\n" + "=" * 70)
        print("📥 IMPORT CLIENTS DEPUIS CSV")
        print("=" * 70)

        # Lire le CSV
        raw_data = self.read_csv(csv_file)
        if not raw_data:
            return 0

        # Mapper les colonnes
        mapped_data = [self.map_columns(row, 'clients') for row in raw_data]

        # Importer
        return self.import_batch('clients', mapped_data)

    def import_pianos_from_csv(self, csv_file: str) -> int:
        """Importe les pianos depuis un CSV Gazelle."""
        print("\n" + "=" * 70)
        print("📥 IMPORT PIANOS DEPUIS CSV")
        print("=" * 70)

        # Lire le CSV
        raw_data = self.read_csv(csv_file)
        if not raw_data:
            return 0

        # Mapper les colonnes
        mapped_data = [self.map_columns(row, 'pianos') for row in raw_data]

        # Résoudre les clés étrangères (client_id)
        resolved_data = self.resolve_foreign_keys(mapped_data, 'pianos')

        # Importer
        return self.import_batch('pianos', resolved_data)

    def import_appointments_from_csv(self, csv_file: str) -> int:
        """Importe les rendez-vous depuis un CSV Gazelle."""
        print("\n" + "=" * 70)
        print("📥 IMPORT APPOINTMENTS DEPUIS CSV")
        print("=" * 70)

        # Lire le CSV
        raw_data = self.read_csv(csv_file)
        if not raw_data:
            return 0

        # Mapper les colonnes
        mapped_data = [self.map_columns(row, 'appointments') for row in raw_data]

        # Résoudre les clés étrangères (client_id, piano_id)
        resolved_data = self.resolve_foreign_keys(mapped_data, 'appointments')

        # Importer
        return self.import_batch('appointments', resolved_data)

    def import_from_json(self, json_file: str, entity_type: str) -> int:
        """
        Import générique depuis JSON.

        Args:
            json_file: Fichier JSON source
            entity_type: Type ('clients', 'pianos', 'appointments')
        """
        print("\n" + "=" * 70)
        print(f"📥 IMPORT {entity_type.upper()} DEPUIS JSON")
        print("=" * 70)

        # Lire JSON
        raw_data = self.read_json(json_file)
        if not raw_data:
            return 0

        # Mapper
        mapped_data = [self.map_columns(row, entity_type) for row in raw_data]

        # Résoudre FK si nécessaire
        if entity_type in ['pianos', 'appointments']:
            mapped_data = self.resolve_foreign_keys(mapped_data, entity_type)

        # Importer
        return self.import_batch(entity_type, mapped_data)


def main():
    """Exemple d'utilisation du script."""
    print("\n" + "=" * 70)
    print("🚀 GAZELLE IMPORTER - UTILITAIRE D'IMPORT")
    print("=" * 70)

    print("\nℹ️  Ce module fournit des classes utilitaires pour importer")
    print("   des données Gazelle (CSV/JSON) vers Supabase.\n")

    print("📖 Usage:")
    print("   from scripts.data.importer_utils import GazelleImporter")
    print("")
    print("   importer = GazelleImporter()")
    print("   importer.import_clients_from_csv('data/clients.csv')")
    print("   importer.import_pianos_from_csv('data/pianos.csv')")
    print("   importer.import_appointments_from_csv('data/appointments.csv')")
    print("")
    print("📋 Format CSV attendu:")
    print("   - Headers en anglais (mapping automatique)")
    print("   - Encodage UTF-8 avec BOM accepté")
    print("   - Colonnes GazelleClientId, GazellePianoId pour références\n")


if __name__ == "__main__":
    main()
