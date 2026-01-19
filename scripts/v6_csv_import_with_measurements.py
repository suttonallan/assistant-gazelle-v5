#!/usr/bin/env python3
"""
v6 CSV Import avec Extraction de Mesures Temp/Hum

Import bulk sécurisé du CSV Timeline avec:
- Extraction automatique des mesures temp/hum depuis le texte
- Stockage dans metadata (JSON structuré)
- Génération d'external_id unique
- Lookup piano_id depuis Piano Token
- Batch processing pour performance
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import csv
import re
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from core.supabase_storage import SupabaseStorage
from supabase import create_client
import requests


def extract_measurements(text: str) -> Optional[Dict[str, int]]:
    """
    Extrait température et humidité d'un texte avec détection intelligente.
    
    Retourne: {'temperature': 20, 'humidity': 33} ou None
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Pattern 1: Format compact "20C, 33%" ou "20°, 33%"
    compact_pattern = r'(\d+)\s*([CcFf°](?:\s*[CcFf])?)\s*,?\s*(\d+)\s*%'
    match = re.search(compact_pattern, text)
    if match:
        temp_value = int(match.group(1))
        temp_unit = match.group(2).strip().upper()
        humidity_value = int(match.group(3))
        
        # Convertir Fahrenheit en Celsius si nécessaire
        if 'F' in temp_unit:
            temp_value = int((temp_value - 32) * 5 / 9)
        
        return {'temperature': temp_value, 'humidity': humidity_value}
    
    # Pattern 2: "température 23, humidité 35%"
    pattern2 = r'temp[ée]rature[^0-9]*(\d+)[^0-9]*humidit[ée][^0-9]*(\d+)\s*%'
    match = re.search(pattern2, text_lower, re.IGNORECASE)
    if match:
        return {'temperature': int(match.group(1)), 'humidity': int(match.group(2))}
    
    # Pattern 3: "23° celsius, humidité relative 35%"
    pattern3 = r'(\d+)\s*°\s*(?:celsius|C)?\s*,?\s*(?:humidité|humidity)[^0-9]*(\d+)\s*%'
    match = re.search(pattern3, text_lower, re.IGNORECASE)
    if match:
        return {'temperature': int(match.group(1)), 'humidity': int(match.group(2))}
    
    return None


def generate_external_id(row: Dict) -> str:
    """Génère un external_id unique basé sur les données de la ligne."""
    # Utiliser Type + Timestamp + Client ID + hash du contenu
    content = f"{row.get('Type', '')}_{row.get('Timestamp', '')}_{row.get('Client ID', '')}_{row.get('Comment', '')}_{row.get('System Message', '')}"
    hash_obj = hashlib.md5(content.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()[:12]
    return f"tle_{hash_hex}"


def lookup_piano_id(piano_token: str, storage: SupabaseStorage) -> Optional[str]:
    """
    Lookup piano_id depuis Piano Token dans gazelle_pianos.
    
    Note: Piano Token du CSV = external_id dans Supabase (pas l'ID numérique).
    Retourne l'ID Supabase (colonne 'id'), pas l'external_id.
    """
    if not piano_token:
        return None
    
    try:
        supabase = create_client(storage.supabase_url, storage.supabase_key)
        # Chercher par external_id (Piano Token = external_id Gazelle)
        result = supabase.table('gazelle_pianos')\
            .select('id')\
            .eq('external_id', piano_token)\
            .limit(1)\
            .execute()
        
        if result.data and result.data[0].get('id'):
            return str(result.data[0].get('id'))  # Retourner l'ID Supabase (string)
    except Exception as e:
        # Erreur silencieuse - piano non trouvé est normal
        pass
    
    return None  # Piano non trouvé = None (pas d'erreur)


def parse_timestamp(ts_str: str) -> Optional[str]:
    """Parse timestamp CSV vers ISO format Supabase."""
    if not ts_str:
        return None
    
    try:
        # Format: "2024-11-11 06:05:22 UTC"
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S UTC")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception as e:
        print(f"  ⚠️  Erreur parsing timestamp '{ts_str}': {e}")
        return None


def map_entry_type(csv_type: str) -> str:
    """
    Mappe le Type CSV vers entry_type Supabase.
    
    Types valides selon contrainte CHECK:
    - APPOINTMENT, CONTACT_EMAIL, NOTE, APPOINTMENT_COMPLETION,
    - SYSTEM_NOTIFICATION, SERVICE_ENTRY_MANUAL, PIANO_MEASUREMENT,
    - INVOICE_PAYMENT, ERROR_MESSAGE
    """
    mapping = {
        'email': 'CONTACT_EMAIL',  # Email = CONTACT_EMAIL
        'log': 'NOTE',              # Log = NOTE
        'event': 'APPOINTMENT',     # Event = APPOINTMENT (si c'est un rendez-vous)
        'appointment': 'APPOINTMENT',
        'invoice': 'INVOICE_PAYMENT',  # Invoice = INVOICE_PAYMENT
        'service': 'SERVICE_ENTRY_MANUAL',
        'measurement': 'PIANO_MEASUREMENT',
    }
    mapped = mapping.get(csv_type.lower())
    if mapped:
        return mapped
    
    # Fallback: essayer de mapper intelligemment
    csv_lower = csv_type.lower()
    if 'appointment' in csv_lower or 'rendez-vous' in csv_lower:
        return 'APPOINTMENT'
    elif 'email' in csv_lower or 'mail' in csv_lower:
        return 'CONTACT_EMAIL'
    elif 'service' in csv_lower or 'entretien' in csv_lower:
        return 'SERVICE_ENTRY_MANUAL'
    elif 'measurement' in csv_lower or 'mesure' in csv_lower:
        return 'PIANO_MEASUREMENT'
    else:
        # Par défaut: NOTE (le plus sûr)
        return 'NOTE'


def import_csv_bulk(csv_path: str, batch_size: int = 100):
    """
    Import bulk du CSV avec extraction de mesures.
    
    Args:
        csv_path: Chemin vers le CSV
        batch_size: Taille des batchs (défaut: 100)
    """
    print(f"\n{'='*70}")
    print(f"📥 IMPORT CSV v6 - AVEC EXTRACTION MESURES")
    print(f"{'='*70}")
    print(f"📁 Fichier: {csv_path}")
    print(f"⚡ Batch size: {batch_size}")
    print(f"{'='*70}\n")
    
    storage = SupabaseStorage(silent=True)
    supabase = create_client(storage.supabase_url, storage.supabase_key)
    
    # Compteurs
    total_rows = 0
    imported = 0
    errors = 0
    measurements_extracted = 0
    batch = []
    
    start_time = time.time()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, 1):
            total_rows += 1
            
            try:
                # Générer external_id
                external_id = generate_external_id(row)
                
                # Parser timestamp
                occurred_at = parse_timestamp(row.get('Timestamp', ''))
                if not occurred_at:
                    errors += 1
                    continue
                
                # Extraire les mesures du texte
                comment = row.get('Comment', '') or ''
                system_msg = row.get('System Message', '') or ''
                combined_text = f"{comment} {system_msg}".strip()
                
                measurements = extract_measurements(combined_text)
                if measurements:
                    measurements_extracted += 1
                
                # Préparer metadata avec mesures si trouvées
                metadata = {}
                if measurements:
                    metadata['measurements'] = {
                        'temperature': measurements['temperature'],
                        'humidity': measurements['humidity'],
                        'source': 'extracted_from_text'
                    }
                
                # Ajouter infos piano si disponibles
                if row.get('Piano Token'):
                    metadata['piano_info'] = {
                        'token': row.get('Piano Token'),
                        'type': row.get('Piano Type'),
                        'make': row.get('Piano Make'),
                        'model': row.get('Piano Model'),
                        'serial': row.get('Piano Serial Number'),
                        'location': row.get('Piano Location'),
                        'year': row.get('Piano Year'),
                    }
                
                # Lookup piano_id (peut être None si non trouvé)
                piano_id = lookup_piano_id(row.get('Piano Token', ''), storage)
                # Si lookup échoue, piano_id sera None (pas d'erreur)
                
                # Construire l'enregistrement
                # Nettoyer les valeurs None pour éviter les erreurs de contrainte
                record = {
                    'external_id': external_id,
                    'client_external_id': row.get('Client ID', '') or None,
                    'entity_id': row.get('Client ID', '') or None,
                    'client_id': row.get('Client ID', '') or None,
                    'entry_type': map_entry_type(row.get('Type', '')),
                    'event_type': row.get('Type', '').lower()[:50] if row.get('Type') else None,
                    'title': row.get('System Message', '')[:500] if row.get('System Message') else None,
                    'description': comment[:2000] if comment else None,
                    'entry_date': occurred_at,
                    'occurred_at': occurred_at,
                    'entity_type': 'CLIENT',
                    'piano_id': piano_id,  # Peut être None
                    'created_by': row.get('Created By', '')[:100] if row.get('Created By') else None,
                    'metadata': metadata if metadata else None,
                }
                
                # Nettoyer les valeurs vides (les convertir en None)
                for key, value in list(record.items()):
                    if value == '':
                        record[key] = None
                
                batch.append(record)
                
                # Insérer par batch
                if len(batch) >= batch_size:
                    success_count, error_count = _insert_batch(storage, batch)
                    imported += success_count
                    errors += error_count
                    batch = []
                    
                    # Monitoring
                    if imported % 500 == 0:
                        print(f"📊 {imported:,} entrées importées | {measurements_extracted:,} mesures extraites")
            
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  ❌ Erreur ligne {row_num}: {e}")
        
        # Insérer le reste
        if batch:
            success_count, error_count = _insert_batch(storage, batch)
            imported += success_count
            errors += error_count
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"✅ IMPORT TERMINÉ")
    print(f"{'='*70}")
    print(f"📊 Total lignes: {total_rows:,}")
    print(f"✅ Importées: {imported:,}")
    print(f"❌ Erreurs: {errors}")
    print(f"🌡️  Mesures extraites: {measurements_extracted:,}")
    print(f"⏱️  Durée: {elapsed:.1f}s ({elapsed/60:.2f} min)")
    print(f"{'='*70}\n")


def _insert_batch(storage: SupabaseStorage, batch: list) -> Tuple[int, int]:
    """
    Insère un batch d'entrées en une seule requête.
    Gère les erreurs de foreign key et les doublons.
    
    Returns:
        (success_count, error_count)
    """
    if not batch:
        return (0, 0)
    
    try:
        url = f"{storage.api_url}/gazelle_timeline_entries?on_conflict=external_id"
        headers = storage._get_headers()
        headers['Prefer'] = 'resolution=merge-duplicates'  # UPSERT
        
        resp = requests.post(url, headers=headers, json=batch, timeout=60)
        
        if resp.status_code in [200, 201]:
            return (len(batch), 0)
        else:
            # En cas d'erreur batch, insérer une par une
            success_count = 0
            error_count = 0
            
            for record in batch:
                try:
                    # Nettoyer piano_id si invalide (vérifier avant insertion)
                    if record.get('piano_id'):
                        try:
                            supabase = create_client(storage.supabase_url, storage.supabase_key)
                            check = supabase.table('gazelle_pianos')\
                                .select('id')\
                                .eq('id', record['piano_id'])\
                                .limit(1)\
                                .execute()
                            if not check.data:
                                # Piano n'existe pas, mettre à None
                                record['piano_id'] = None
                        except:
                            record['piano_id'] = None
                    
                    # Insertion individuelle
                    single_resp = requests.post(
                        url,
                        headers=headers,
                        json=record,
                        timeout=10
                    )
                    
                    if single_resp.status_code in [200, 201]:
                        success_count += 1
                    elif single_resp.status_code == 409:
                        # 409 = Doublon (normal avec UPSERT) ou foreign key
                        error_detail = single_resp.text
                        if '23505' in error_detail:
                            # Doublon - considéré comme succès (déjà existant)
                            success_count += 1
                        elif '23503' in error_detail:
                            # Foreign key - mettre piano_id à None et réessayer
                            record['piano_id'] = None
                            retry_resp = requests.post(url, headers=headers, json=record, timeout=10)
                            if retry_resp.status_code in [200, 201, 409]:
                                success_count += 1
                            else:
                                error_count += 1
                        else:
                            # Autre erreur 409
                            error_count += 1
                    else:
                        error_count += 1
                
                except Exception as e:
                    error_count += 1
            
            return (success_count, error_count)
    
    except Exception as e:
        print(f"  ❌ Erreur batch: {e}")
        return (0, len(batch))


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Import CSV Timeline avec extraction de mesures")
    parser.add_argument('csv_file', help='Chemin vers le CSV')
    parser.add_argument('--batch-size', type=int, default=100, help='Taille des batchs (défaut: 100)')
    
    args = parser.parse_args()
    
    import_csv_bulk(args.csv_file, batch_size=args.batch_size)
