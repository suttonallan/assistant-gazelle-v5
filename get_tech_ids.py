#!/usr/bin/env python3
import requests
import os

url = 'https://beblgzvmjqkcillmcavk.supabase.co/rest/v1/users?select=id,email,name&limit=50'
headers = {
    'apikey': os.getenv('SUPABASE_KEY'),
    'Authorization': f"Bearer {os.getenv('SUPABASE_KEY')}"
}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    users = response.json()
    print(f"\nTrouvé {len(users)} utilisateurs\n")
    print("Tous les techniciens:")
    for user in users:
        if isinstance(user, dict):
            name = user.get('name', 'Sans nom')
            email = user.get('email', 'Sans email')
            uid = user.get('id')
            print(f"  {name:25s} {email:45s} {uid}")
else:
    print(f"Erreur: {response.text}")
