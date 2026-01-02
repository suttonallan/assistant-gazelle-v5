#!/usr/bin/env python3
"""
Explorer le schéma GraphQL de PrivatePiano pour identifier tous les champs disponibles.

Date: 2026-01-01
"""

import sys
import json
from pathlib import Path

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient


def explore_piano_schema():
    """Explore le schéma GraphQL pour PrivatePiano."""
    client = GazelleAPIClient()

    print(f"\n{'='*70}")
    print(f"🔍 EXPLORATION DU SCHÉMA: PrivatePiano")
    print(f"{'='*70}\n")

    # Introspection query pour PrivatePiano
    query = """
    query {
        __type(name: "PrivatePiano") {
            name
            kind
            fields {
                name
                type {
                    name
                    kind
                    ofType {
                        name
                        kind
                    }
                }
                description
            }
        }
    }
    """

    try:
        result = client._execute_query(query)

        if not result:
            print("❌ Aucune réponse reçue")
            return

        type_info = result.get("data", {}).get("__type")

        if not type_info:
            print("❌ Type PrivatePiano non trouvé")
            return

        print(f"✅ Type: {type_info.get('name')}")
        print(f"   Kind: {type_info.get('kind')}\n")

        fields = type_info.get('fields', [])

        print(f"{'='*70}")
        print(f"CHAMPS DISPONIBLES ({len(fields)} champs)")
        print(f"{'='*70}\n")

        # Grouper par catégorie
        basic_fields = []
        relation_fields = []
        date_fields = []
        other_fields = []

        for field in fields:
            field_name = field.get('name')
            type_info_field = field.get('type', {})
            type_name = type_info_field.get('name')
            type_kind = type_info_field.get('kind')
            description = field.get('description', '')

            # Classer par catégorie
            if 'all' in field_name.lower() or type_kind == 'OBJECT':
                relation_fields.append((field_name, type_name, description))
            elif 'date' in field_name.lower() or 'time' in field_name.lower():
                date_fields.append((field_name, type_name, description))
            elif type_name in ['String', 'Int', 'Float', 'Boolean', 'ID']:
                basic_fields.append((field_name, type_name, description))
            else:
                other_fields.append((field_name, type_name, description))

        # Afficher champs basiques
        if basic_fields:
            print("📋 CHAMPS BASIQUES:")
            for name, type_name, desc in basic_fields:
                print(f"   • {name:25} : {type_name}")

        # Afficher champs de date
        if date_fields:
            print(f"\n📅 CHAMPS DE DATE:")
            for name, type_name, desc in date_fields:
                print(f"   • {name:25} : {type_name}")

        # Afficher relations (champs critiques pour historique)
        if relation_fields:
            print(f"\n🔗 RELATIONS (Historique/Services):")
            for name, type_name, desc in relation_fields:
                marker = "⭐" if 'event' in name.lower() or 'timeline' in name.lower() or 'service' in name.lower() else " "
                print(f"   {marker} {name:25} : {type_name}")

        # Afficher autres champs
        if other_fields:
            print(f"\n🔧 AUTRES CHAMPS:")
            for name, type_name, desc in other_fields:
                print(f"   • {name:25} : {type_name}")

        # Sauvegarder la structure complète en JSON
        output_file = Path(__file__).parent.parent / 'data' / 'piano_schema.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(type_info, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*70}")
        print(f"💾 Schéma complet sauvegardé dans:")
        print(f"   {output_file}")
        print(f"{'='*70}\n")

        return type_info

    except Exception as e:
        print(f"\n❌ Erreur lors de l'exploration du schéma: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Fonction principale."""
    print("\n" + "="*70)
    print("EXPLORATION: Schéma GraphQL de PrivatePiano")
    print("="*70)

    explore_piano_schema()

    print("\n" + "="*70)
    print("✅ Exploration terminée")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
