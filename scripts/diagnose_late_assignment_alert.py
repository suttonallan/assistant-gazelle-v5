#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier pourquoi une alerte "Late Assignment" 
n'a pas été déclenchée pour un rendez-vous spécifique.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

# Charger les variables d'environnement
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Ajouter le répertoire racine au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.supabase_storage import SupabaseStorage
from core.timezone_utils import MONTREAL_TZ
import requests

def diagnose_appointment(client_name: str, appointment_date: str):
    """
    Diagnostique pourquoi une alerte Late Assignment n'a pas été déclenchée.
    
    Args:
        client_name: Nom du client (ex: "Allan Sutton")
        appointment_date: Date du rendez-vous (format YYYY-MM-DD, ex: "2026-01-25")
    """
    print("=" * 80)
    print("🔍 DIAGNOSTIC ALERTE LATE ASSIGNMENT")
    print("=" * 80)
    print(f"📅 Date du RV: {appointment_date}")
    print(f"👤 Client: {client_name}")
    print()
    
    storage = SupabaseStorage()
    
    # 1. Chercher le rendez-vous dans Supabase
    print("1️⃣  Recherche du rendez-vous dans Supabase...")
    # D'abord chercher le client par nom (gazelle_clients a first_name et last_name)
    clients_url = f"{storage.api_url}/gazelle_clients"
    clients_params = {
        'select': 'external_id,first_name,last_name,company_name',
        'limit': '1000'
    }
    clients_response = requests.get(clients_url, headers=storage._get_headers(), params=clients_params)
    
    if clients_response.status_code != 200:
        print(f"❌ Erreur recherche client: {clients_response.status_code} - {clients_response.text}")
        return
    
    all_clients = clients_response.json()
    # Filtrer en Python pour trouver le client
    matching_clients = []
    search_name = client_name.lower()
    for c in all_clients:
        first = (c.get('first_name') or '').lower()
        last = (c.get('last_name') or '').lower()
        company = (c.get('company_name') or '').lower()
        full_name = f"{first} {last}".strip()
        
        if search_name in full_name or search_name in company or (first and last and search_name == full_name):
            matching_clients.append(c)
    
    if not matching_clients:
        print(f"❌ Client '{client_name}' non trouvé dans gazelle_clients")
        print(f"   → {len(all_clients)} clients dans la base")
        return
    
    if len(matching_clients) > 1:
        print(f"⚠️  {len(matching_clients)} clients trouvés, utilisation du premier:")
        for c in matching_clients:
            print(f"   - {c.get('first_name')} {c.get('last_name')} ({c.get('external_id')})")
    
    client_id = matching_clients[0].get('external_id')
    client_full_name = f"{matching_clients[0].get('first_name', '')} {matching_clients[0].get('last_name', '')}".strip()
    print(f"   ✅ Client trouvé: {client_full_name} (ID: {client_id})")
    
    # Maintenant chercher le rendez-vous
    url = f"{storage.api_url}/gazelle_appointments"
    params = {
        'client_external_id': f'eq.{client_id}',
        'appointment_date': f'eq.{appointment_date}',
        'select': 'external_id,appointment_date,appointment_time,technicien,last_notified_tech_id,client_external_id,location,created_at,updated_at'
    }
    
    response = requests.get(url, headers=storage._get_headers(), params=params)
    
    if response.status_code != 200:
        print(f"❌ Erreur requête Supabase: {response.status_code} - {response.text}")
        return
    
    appointments = response.json()
    
    if not appointments:
        print(f"❌ Aucun rendez-vous trouvé pour '{client_name}' le {appointment_date}")
        print("   → Le RV n'a peut-être pas encore été synchronisé depuis Gazelle")
        print("   → Vérifiez que la sync a été exécutée récemment")
        return
    
    print(f"✅ {len(appointments)} rendez-vous trouvé(s)")
    print()
    
    for appt in appointments:
        print(f"📋 RV ID: {appt.get('external_id')}")
        print(f"   Date: {appt.get('appointment_date')}")
        print(f"   Heure: {appt.get('appointment_time')}")
        print(f"   Technicien (Gazelle ID): {appt.get('technicien')}")
        print(f"   Last Notified Tech ID: {appt.get('last_notified_tech_id')}")
        print(f"   Client ID: {appt.get('client_external_id')}")
        print(f"   Lieu: {appt.get('location')}")
        print(f"   Créé: {appt.get('created_at')}")
        print(f"   Mis à jour: {appt.get('updated_at')}")
        print()
        
        # 2. Vérifier si c'est aujourd'hui ou demain
        print("2️⃣  Vérification date (aujourd'hui ou demain)...")
        today = datetime.now(MONTREAL_TZ).date()
        tomorrow = today + timedelta(days=1)
        
        appt_date_str = appt.get('appointment_date')
        if appt_date_str:
            try:
                if isinstance(appt_date_str, str):
                    appt_date = date.fromisoformat(appt_date_str)
                else:
                    appt_date = appt_date_str
                
                is_today_or_tomorrow = appt_date == today or appt_date == tomorrow
                
                print(f"   Aujourd'hui: {today}")
                print(f"   Demain: {tomorrow}")
                print(f"   Date RV: {appt_date}")
                print(f"   ✅ Dans la plage (aujourd'hui/demain): {is_today_or_tomorrow}")
                
                if not is_today_or_tomorrow:
                    print(f"   ❌ PROBLÈME: Le RV n'est pas pour aujourd'hui ou demain")
                    print(f"      → Les alertes Late Assignment ne sont déclenchées que pour les RV d'aujourd'hui/demain")
                    return
                    
            except Exception as e:
                print(f"   ❌ Erreur parsing date: {e}")
                return
        else:
            print(f"   ❌ PROBLÈME: Pas de date dans le rendez-vous")
            return
        
        print()
        
        # 3. Vérifier si le technicien est défini
        print("3️⃣  Vérification technicien...")
        technicien = appt.get('technicien')
        last_notified = appt.get('last_notified_tech_id')
        
        if not technicien:
            print(f"   ❌ PROBLÈME: Aucun technicien assigné au RV")
            print(f"      → Les alertes ne sont déclenchées que si un technicien est assigné")
            return
        
        print(f"   ✅ Technicien assigné: {technicien}")
        print(f"   Last Notified: {last_notified}")
        print()
        
        # 4. Vérifier la logique de détection
        print("4️⃣  Vérification logique de détection...")
        print("   Logique: Alerte si:")
        print("   - Nouveau RV (pas d'ancien technicien) OU")
        print("   - Technicien a changé ET last_notified != nouveau technicien")
        print()
        
        # On ne peut pas savoir l'ancien technicien maintenant, mais on peut vérifier last_notified
        if last_notified == technicien:
            print(f"   ⚠️  ATTENTION: last_notified_tech_id == technicien ({technicien})")
            print(f"      → L'alerte a peut-être déjà été envoyée et le flag a été mis à jour")
            print(f"      → Vérifiez la table late_assignment_queue")
        else:
            print(f"   ✅ Condition remplie: last_notified ({last_notified}) != technicien ({technicien})")
            print(f"      → Une alerte devrait être déclenchée")
        print()
        
        # 5. Vérifier la queue late_assignment
        print("5️⃣  Vérification queue late_assignment_queue...")
        queue_url = f"{storage.api_url}/late_assignment_queue"
        queue_params = {
            'appointment_external_id': f'eq.{appt.get("external_id")}',
            'select': '*',
            'order': 'created_at.desc'
        }
        
        queue_response = requests.get(queue_url, headers=storage._get_headers(), params=queue_params)
        
        if queue_response.status_code == 200:
            queue_items = queue_response.json()
            if queue_items:
                print(f"   ✅ {len(queue_items)} entrée(s) dans la queue")
                for item in queue_items:
                    print(f"      - Status: {item.get('status')}")
                    print(f"        Scheduled: {item.get('scheduled_send_at')}")
                    print(f"        Created: {item.get('created_at')}")
                    print(f"        Sent: {item.get('sent_at')}")
            else:
                print(f"   ❌ PROBLÈME: Aucune entrée dans late_assignment_queue")
                print(f"      → L'alerte n'a pas été insérée dans la queue")
                print(f"      → Possible causes:")
                print(f"         • La sync n'a pas été exécutée depuis la création/modification du RV")
                print(f"         • Une erreur s'est produite lors de la détection")
        else:
            print(f"   ⚠️  Erreur requête queue: {queue_response.status_code}")
        
        print()
        
        # 6. Vérifier les logs de sync récents
        print("6️⃣  Vérification logs de sync récents...")
        sync_url = f"{storage.api_url}/sync_logs"
        sync_params = {
            'script_name': 'eq.sync_to_supabase',
            'order': 'created_at.desc',
            'limit': '5',
            'select': 'created_at,status,error_message,tables_updated'
        }
        
        sync_response = requests.get(sync_url, headers=storage._get_headers(), params=sync_params)
        
        if sync_response.status_code == 200:
            sync_logs = sync_response.json()
            if sync_logs:
                print(f"   ✅ {len(sync_logs)} log(s) de sync récent(s):")
                for log in sync_logs[:3]:
                    print(f"      - {log.get('created_at')}: {log.get('status')}")
                    if 'appointments' in str(log.get('tables_updated', '')):
                        print(f"        ✅ Appointments synchronisés")
            else:
                print(f"   ⚠️  Aucun log de sync récent")
        else:
            print(f"   ⚠️  Erreur requête sync_logs: {sync_response.status_code}")
        
        print()
        
        # 7. Vérifier si le technicien existe dans users
        print("7️⃣  Vérification technicien dans table users...")
        users_url = f"{storage.api_url}/users"
        users_params = {
            'external_id': f'eq.{technicien}',
            'select': 'id,email,name,external_id'
        }
        
        users_response = requests.get(users_url, headers=storage._get_headers(), params=users_params)
        
        if users_response.status_code == 200:
            users = users_response.json()
            if users:
                user = users[0]
                print(f"   ✅ Technicien trouvé dans users:")
                print(f"      - Nom: {user.get('name')}")
                print(f"      - Email: {user.get('email')}")
                print(f"      - External ID: {user.get('external_id')}")
            else:
                print(f"   ❌ PROBLÈME: Technicien {technicien} non trouvé dans users")
                print(f"      → L'email ne pourra pas être envoyé même si l'alerte est dans la queue")
        else:
            print(f"   ⚠️  Erreur requête users: {users_response.status_code}")
        
        print()
        print("=" * 80)
        print("📊 RÉSUMÉ DU DIAGNOSTIC")
        print("=" * 80)
        print()
        print("Actions recommandées:")
        print("1. Si le RV n'est pas dans Supabase: Exécuter une sync manuelle")
        print("2. Si pas d'entrée dans la queue: Vérifier les logs de sync pour erreurs")
        print("3. Si entrée en queue mais status='pending': Vérifier que le notifier tourne")
        print("4. Si technicien non trouvé dans users: Vérifier que external_id est correct")
        print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnostiquer pourquoi une alerte Late Assignment n\'a pas été déclenchée')
    parser.add_argument('--client', type=str, required=True, help='Nom du client (ex: "Allan Sutton")')
    parser.add_argument('--date', type=str, required=True, help='Date du RV (format YYYY-MM-DD, ex: "2026-01-25")')
    
    args = parser.parse_args()
    
    diagnose_appointment(args.client, args.date)
