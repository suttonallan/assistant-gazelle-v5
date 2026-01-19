#!/usr/bin/env python3
"""
Génère la liste de courriels pour les clients dont les pianos
ont une humidité critique (< 20%) pour proposer Dampp-Chaser.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


def generate_dampchaser_campaign():
    """
    Génère la campagne d'emails Dampp-Chaser pour humidité critique.
    """
    print("\n" + "="*80)
    print("🎯 CAMPAGNE DAMPP-CHASER - Humidité Critique < 20%")
    print("="*80)
    print("\nDécembre 2024 - Détection automatique\n")
    
    s = SupabaseStorage()
    
    # 1. Trouver les pianos avec humidité < 20% en décembre 2024
    result = s.client.table('gazelle_timeline_entries')\
        .select('piano_id, client_id, occurred_at, entry_type, description, metadata')\
        .gte('occurred_at', '2024-12-01')\
        .lt('occurred_at', '2025-01-01')\
        .not_.is_('metadata', 'null')\
        .not_.is_('piano_id', 'null')\
        .not_.is_('client_id', 'null')\
        .order('occurred_at', desc=True)\
        .execute()
    
    # Grouper par client
    clients_data = {}
    for entry in result.data:
        metadata = entry.get('metadata')
        if metadata and isinstance(metadata, dict):
            humidity = metadata.get('humidity')
            if humidity and humidity < 20:
                client_id = entry.get('client_id')
                piano_id = entry.get('piano_id')
                
                if client_id not in clients_data:
                    clients_data[client_id] = {
                        'piano_id': piano_id,
                        'min_humidity': humidity,
                        'date': entry.get('occurred_at', '')[:10],
                        'description': entry.get('description', '')
                    }
                elif humidity < clients_data[client_id]['min_humidity']:
                    clients_data[client_id].update({
                        'min_humidity': humidity,
                        'date': entry.get('occurred_at', '')[:10],
                        'description': entry.get('description', '')
                    })
    
    print(f"✅ {len(clients_data)} clients identifiés avec humidité critique\n")
    print("="*80)
    
    # 2. Générer les courriels
    for i, (client_id, data) in enumerate(sorted(clients_data.items()), 1):
        piano_id = data['piano_id']
        humidity = data['min_humidity']
        date = data['date']
        
        print(f"\n📧 COURRIEL #{i}")
        print("-" * 80)
        print(f"Client ID: {client_id}")
        print(f"Piano ID: {piano_id}")
        print(f"💧 Humidité minimale: {humidity}%")
        print(f"📅 Date de mesure: {date}")
        
        # Extraire le nom du client depuis la description si possible
        desc = data.get('description', '')
        
        print("\n📝 TEXTE SUGGÉRÉ:")
        print("-" * 80)
        print(f"""
Objet: Protection de votre piano - Humidité critique détectée

Bonjour,

Lors de notre visite du {date}, nous avons constaté que l'humidité 
de votre piano est descendue à {humidity}%, ce qui est bien en dessous 
du seuil recommandé de 35-50%.

Cette situation peut causer:
• Fissures dans la table d'harmonie
• Désaccord rapide et instable
• Dommages permanents au bois et à la mécanique

🛡️ SOLUTION RECOMMANDÉE: Système Dampp-Chaser

Le système Dampp-Chaser maintient automatiquement l'humidité idéale 
à l'intérieur de votre piano, 24h/24, 365 jours par an.

Avantages:
✓ Protection permanente contre les variations d'humidité
✓ Stabilité de l'accord prolongée
✓ Préservation de la valeur de votre instrument
✓ Installation professionnelle en une seule visite

Prix: À partir de 750$ (installation incluse)

Contactez-nous pour une consultation gratuite:
📞 514-xxx-xxxx
📧 info@pianotechnique.ca

Cordialement,
L'équipe Piano Technique Montréal
        """.strip())
        
        print("\n" + "-" * 80)
    
    print("\n" + "="*80)
    print("✅ CAMPAGNE GÉNÉRÉE!")
    print("="*80)
    print(f"\n📊 Résumé:")
    print(f"   • {len(clients_data)} clients ciblés")
    print(f"   • Humidité minimale détectée: {min(d['min_humidity'] for d in clients_data.values())}%")
    print(f"   • Potentiel de vente: {len(clients_data)} × 750$ = {len(clients_data) * 750}$")
    
    print("\n💡 Prochaines étapes:")
    print("   1. Envoyer les courriels personnalisés")
    print("   2. Appeler les clients 2-3 jours après")
    print("   3. Proposer une visite d'évaluation gratuite")
    print("   4. Préparer les devis Dampp-Chaser\n")
    
    return clients_data


if __name__ == '__main__':
    generate_dampchaser_campaign()
