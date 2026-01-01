#!/usr/bin/env python3
"""
Script pour suggérer des associations entre items internes et items MSL Gazelle.
Utilise la similarité des noms pour proposer des matches.
"""

import requests
from difflib import SequenceMatcher
import json

API_URL = "http://localhost:8000"

def similarity(a, b):
    """Calcule la similarité entre deux chaînes (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_matches():
    """Trouve les associations possibles entre items internes et MSL"""

    # Charger le catalogue
    response = requests.get(f"{API_URL}/inventaire/catalogue")
    data = response.json()
    items = data.get('produits', [])

    # Séparer les items
    msl_items = [i for i in items if i.get('gazelle_product_id')]
    internal_items = [i for i in items if not i.get('gazelle_product_id') and i.get('is_inventory_item')]

    print(f"\n{'='*80}")
    print(f"🔍 ANALYSE DES ASSOCIATIONS MSL ↔ INVENTAIRE INTERNE")
    print(f"{'='*80}\n")
    print(f"📊 {len(msl_items)} items MSL Gazelle")
    print(f"📦 {len(internal_items)} items inventaire interne\n")

    # Chercher des matches pour chaque item interne
    suggestions = []

    for internal in internal_items:
        internal_name = internal.get('nom', '')
        if not internal_name:
            continue

        # Chercher le meilleur match MSL
        best_match = None
        best_score = 0

        for msl in msl_items:
            msl_name = msl.get('nom', '')
            if not msl_name:
                continue

            score = similarity(internal_name, msl_name)

            if score > best_score:
                best_score = score
                best_match = msl

        # Seulement suggérer si la similarité est >= 40%
        if best_match and best_score >= 0.4:
            suggestions.append({
                'internal': internal,
                'msl': best_match,
                'score': best_score
            })

    # Trier par score décroissant
    suggestions.sort(key=lambda x: x['score'], reverse=True)

    # Afficher les suggestions
    print(f"{'='*80}")
    print(f"💡 SUGGESTIONS D'ASSOCIATIONS (score >= 40%)")
    print(f"{'='*80}\n")

    high_confidence = []
    medium_confidence = []
    low_confidence = []

    for sugg in suggestions:
        score = sugg['score']
        internal = sugg['internal']
        msl = sugg['msl']

        confidence = "🟢 HAUTE" if score >= 0.8 else "🟡 MOYENNE" if score >= 0.6 else "🟠 FAIBLE"

        item = {
            'confidence': confidence,
            'score': score,
            'internal_code': internal.get('code_produit'),
            'internal_name': internal.get('nom'),
            'msl_id': msl.get('gazelle_product_id'),
            'msl_name': msl.get('nom'),
            'msl_price': msl.get('prix_unitaire', 0)
        }

        if score >= 0.8:
            high_confidence.append(item)
        elif score >= 0.6:
            medium_confidence.append(item)
        else:
            low_confidence.append(item)

    # Afficher par catégorie de confiance
    if high_confidence:
        print(f"🟢 HAUTE CONFIANCE (≥80% similarité) - {len(high_confidence)} matches\n")
        for item in high_confidence:
            print(f"  Score: {item['score']*100:.1f}%")
            print(f"  Interne: [{item['internal_code']}] {item['internal_name']}")
            print(f"  MSL:     [{item['msl_id']}] {item['msl_name']}")
            print(f"  Prix MSL: {item['msl_price']:.2f}$")
            print()

    if medium_confidence:
        print(f"\n🟡 CONFIANCE MOYENNE (60-79% similarité) - {len(medium_confidence)} matches\n")
        for item in medium_confidence:
            print(f"  Score: {item['score']*100:.1f}%")
            print(f"  Interne: [{item['internal_code']}] {item['internal_name']}")
            print(f"  MSL:     [{item['msl_id']}] {item['msl_name']}")
            print(f"  Prix MSL: {item['msl_price']:.2f}$")
            print()

    if low_confidence:
        print(f"\n🟠 FAIBLE CONFIANCE (40-59% similarité) - {len(low_confidence)} matches\n")
        for item in low_confidence[:10]:  # Limiter à 10
            print(f"  Score: {item['score']*100:.1f}%")
            print(f"  Interne: [{item['internal_code']}] {item['internal_name']}")
            print(f"  MSL:     [{item['msl_id']}] {item['msl_name']}")
            print()

    # Générer le SQL pour les matches haute confiance
    if high_confidence:
        print(f"\n{'='*80}")
        print(f"📝 SQL POUR APPLIQUER LES MATCHES HAUTE CONFIANCE")
        print(f"{'='*80}\n")
        print("-- Copie-colle ces commandes dans Supabase SQL Editor:\n")

        for item in high_confidence:
            print(f"-- {item['score']*100:.1f}% match: {item['internal_name']}")
            print(f"UPDATE produits_catalogue")
            print(f"SET gazelle_product_id = '{item['msl_id']}'")
            print(f"WHERE code_produit = '{item['internal_code']}';")
            print()

    print(f"\n{'='*80}")
    print(f"✅ RÉSUMÉ")
    print(f"{'='*80}")
    print(f"🟢 Haute confiance: {len(high_confidence)} matches (≥80%)")
    print(f"🟡 Moyenne confiance: {len(medium_confidence)} matches (60-79%)")
    print(f"🟠 Faible confiance: {len(low_confidence)} matches (40-59%)")
    print(f"❌ Non matchés: {len(internal_items) - len(suggestions)} items")
    print()

if __name__ == "__main__":
    try:
        find_matches()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
