#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour lire un piano spécifique depuis l'API Gazelle
et analyser sa structure complète pour identifier l'historique/service history.

Piano de test: ins_9H7Mh59SXwEs2JxL (Allan Test Sutton)
"""

import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gazelle_api_client import GazelleAPIClient

# ID du piano de test
PIANO_ID = "ins_9H7Mh59SXwEs2JxL"


def get_piano_by_id(api_client: GazelleAPIClient, piano_id: str) -> dict:
    """
    Récupère un piano spécifique par son ID depuis l'API Gazelle.
    
    Utilise une requête GraphQL pour récupérer TOUTES les données du piano,
    y compris l'historique/service history.
    """
    # Requête 1: Récupérer le piano
    query_piano = """
    query GetPiano($pianoId: String!) {
        piano(id: $pianoId) {
            id
            make
            model
            serialNumber
            type
            year
            location
            notes
            damppChaserInstalled
            damppChaserHumidistatModel
            damppChaserMfgDate
            client {
                id
                companyName
            }
        }
    }
    """
    
    # Requête 2: Récupérer les timeline entries (on filtrera par piano_id côté client)
    query_timeline = """
    query GetTimelineEntries($cursor: String) {
        allTimelineEntries(first: 100, after: $cursor) {
            edges {
                node {
                    id
                    occurredAt
                    type
                    summary
                    comment
                    piano {
                        id
                    }
                    user {
                        id
                        firstName
                        lastName
                    }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """
    
    variables = {"pianoId": piano_id}
    
    try:
        # Récupérer le piano
        piano_result = api_client._execute_query(query_piano, variables)
        piano = piano_result.get('data', {}).get('piano', {})
        
        if not piano:
            raise ValueError(f"Piano {piano_id} non trouvé")
        
        # Récupérer les timeline entries et filtrer par piano_id
        all_timeline_entries = []
        cursor = None
        
        while True:
            timeline_vars = {}
            if cursor:
                timeline_vars["cursor"] = cursor
            
            timeline_result = api_client._execute_query(query_timeline, timeline_vars)
            timeline_data = timeline_result.get('data', {}).get('allTimelineEntries', {})
            edges = timeline_data.get('edges', [])
            
            # Filtrer les entrées pour ce piano
            for edge in edges:
                node = edge.get('node', {})
                node_piano = node.get('piano')
                if node_piano and node_piano.get('id') == piano_id:
                    all_timeline_entries.append(node)
            
            # Vérifier s'il y a une page suivante
            page_info = timeline_data.get('pageInfo', {})
            if not page_info.get('hasNextPage') or len(all_timeline_entries) >= 50:
                break
            
            cursor = page_info.get('endCursor')
        
        # Combiner les résultats
        combined_result = {
            'data': {
                'piano': piano,
                'timelineEntries': {
                    'edges': [{'node': entry} for entry in all_timeline_entries]
                }
            }
        }
        
        return combined_result
    except Exception as e:
        print(f"❌ Erreur lors de la requête: {e}")
        raise


def analyze_piano_structure(piano_data: dict):
    """Analyse la structure du piano pour identifier l'historique"""
    print("\n" + "="*80)
    print("📊 ANALYSE DE STRUCTURE")
    print("="*80)
    
    if 'data' not in piano_data or 'piano' not in piano_data['data']:
        print("❌ Structure de réponse inattendue")
        print(json.dumps(piano_data, indent=2))
        return
    
    piano = piano_data['data']['piano']
    
    # Informations de base
    print("\n🎹 INFORMATIONS DE BASE:")
    print(f"   ID: {piano.get('id')}")
    print(f"   Marque: {piano.get('make', 'Inconnu')}")
    print(f"   Modèle: {piano.get('model', 'N/A')}")
    print(f"   Série: {piano.get('serialNumber', 'N/A')}")
    print(f"   Localisation: {piano.get('location', 'N/A')}")
    
    # Client/Propriétaire
    client = piano.get('client', {})
    print(f"\n👤 PROPRIÉTAIRE:")
    print(f"   ID Client: {client.get('id', 'N/A')}")
    print(f"   Nom: {client.get('companyName', 'N/A')}")
    
    # Historique/Timeline (depuis la requête séparée)
    timeline_data = piano_data.get('data', {}).get('timelineEntries', {})
    edges = timeline_data.get('edges', [])
    
    print(f"\n📜 HISTORIQUE (Timeline Entries):")
    print(f"   Nombre d'entrées: {len(edges)}")
    
    if edges:
        print("\n   Exemples d'entrées:")
        for i, edge in enumerate(edges[:5], 1):
            node = edge.get('node', {})
            print(f"\n   {i}. Entrée Timeline:")
            print(f"      ID: {node.get('id')}")
            print(f"      Type: {node.get('type')}")
            print(f"      Date: {node.get('occurredAt')}")
            print(f"      Résumé: {node.get('summary', 'N/A')}")
            print(f"      Commentaire: {node.get('comment', 'N/A')[:100]}...")
            user = node.get('user', {})
            if user:
                print(f"      Technicien: {user.get('firstName')} {user.get('lastName')}")
    else:
        print("   ⚠️  Aucune entrée timeline trouvée")
    
    # Structure complète (pour debug)
    print("\n" + "="*80)
    print("🔍 STRUCTURE COMPLÈTE (JSON)")
    print("="*80)
    print(json.dumps(piano_data, indent=2, ensure_ascii=False))


def identify_required_fields(piano_data: dict):
    """Identifie les champs obligatoires pour ajouter une nouvelle entrée"""
    print("\n" + "="*80)
    print("🔑 CHAMPS OBLIGATOIRES POUR AJOUTER UNE NOTE")
    print("="*80)
    
    if 'data' not in piano_data or 'pianoById' not in piano_data['data']:
        return
    
    piano = piano_data['data']['pianoById']
    
    # Analyser une entrée existante pour voir la structure
    timeline_entries = piano.get('allTimelineEntries', {})
    edges = timeline_entries.get('edges', [])
    
    if edges:
        example_entry = edges[0].get('node', {})
        print("\n📋 Structure d'une entrée existante:")
        print(f"   - id: {example_entry.get('id')}")
        print(f"   - occurredAt: {example_entry.get('occurredAt')} (Date ISO)")
        print(f"   - type: {example_entry.get('type')} (Type d'entrée)")
        print(f"   - summary: {example_entry.get('summary')} (Résumé)")
        print(f"   - comment: {example_entry.get('comment')} (Commentaire détaillé)")
        print(f"   - user: {example_entry.get('user', {}).get('id')} (ID technicien)")
    
    print("\n💡 CHAMPS PROBABLEMENT OBLIGATOIRES:")
    print("   - pianoId: ID du piano (ins_9H7Mh59SXwEs2JxL)")
    print("   - occurredAt: Date/heure ISO 8601 (ex: 2025-01-15T10:30:00Z)")
    print("   - type: Type d'entrée (ex: SERVICE_ENTRY_MANUAL, NOTE, etc.)")
    print("   - summary: Résumé court de l'entrée")
    print("   - comment: Commentaire détaillé (optionnel)")
    print("   - userId: ID du technicien/utilisateur (probablement optionnel)")


def propose_mutation_script(piano_data: dict):
    """Propose le script POST exact pour ajouter une note"""
    print("\n" + "="*80)
    print("📝 SCRIPT POST PROPOSÉ (SANS EXÉCUTION)")
    print("="*80)
    
    if 'data' not in piano_data or 'pianoById' not in piano_data['data']:
        return
    
    piano = piano_data['data']['pianoById']
    piano_id = piano.get('id')
    
    # Analyser les types d'entrées existantes
    timeline_entries = piano.get('allTimelineEntries', {})
    edges = timeline_entries.get('edges', [])
    
    entry_types = set()
    for edge in edges:
        entry_type = edge.get('node', {}).get('type')
        if entry_type:
            entry_types.add(entry_type)
    
    print("\n🔍 Types d'entrées trouvées dans l'historique:")
    for entry_type in entry_types:
        print(f"   - {entry_type}")
    
    print("\n" + "-"*80)
    print("MUTATION GRAPHQL PROPOSÉE:")
    print("-"*80)
    
    mutation = """
mutation CreateTimelineEntry {
  createTimelineEntry(input: {
    pianoId: "ins_9H7Mh59SXwEs2JxL"
    occurredAt: "2025-01-15T10:30:00Z"
    type: SERVICE_ENTRY_MANUAL
    summary: "Test - Note de service ajoutée via API"
    comment: "Ceci est une note de test ajoutée depuis l'API Gazelle.\\n\\nDétails:\\n- Test de connexion API\\n- Validation de la structure"
  }) {
    id
    occurredAt
    type
    summary
    comment
    piano {
      id
    }
    user {
      id
      firstName
      lastName
    }
  }
}
"""
    
    print(mutation)
    
    print("\n" + "-"*80)
    print("SCRIPT PYTHON POUR EXÉCUTER LA MUTATION:")
    print("-"*80)
    
    python_script = f"""
from core.gazelle_api_client import GazelleAPIClient
from datetime import datetime

# Initialiser le client
api_client = GazelleAPIClient()

# Mutation GraphQL
mutation = '''
mutation CreateTimelineEntry {{
  createTimelineEntry(input: {{
    pianoId: "{piano_id}"
    occurredAt: "{{occurred_at}}"
    type: SERVICE_ENTRY_MANUAL
    summary: "{{summary}}"
    comment: "{{comment}}"
  }}) {{
    id
    occurredAt
    type
    summary
    comment
  }}
}}
'''

# Variables
occurred_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
summary = "Note de service - Test API"
comment = "Ceci est une note de test ajoutée depuis l'API Gazelle."

# Remplacer les variables
mutation = mutation.format(
    occurred_at=occurred_at,
    summary=summary,
    comment=comment
)

# Exécuter la mutation
try:
    result = api_client._execute_query(mutation)
    print("✅ Succès!")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"❌ Erreur: {{e}}")
"""
    
    print(python_script)
    
    print("\n⚠️  NOTE: Cette mutation est une ESTIMATION basée sur l'analyse de la structure.")
    print("   La structure exacte doit être validée avec la documentation Gazelle GraphQL.")
    print("   Ne pas exécuter sans validation préalable!")


def main():
    """Fonction principale"""
    print("\n" + "="*80)
    print("🦌 TEST LECTURE PIANO GAZELLE API")
    print("="*80)
    print(f"Piano ID: {PIANO_ID}")
    print("="*80)
    
    # Initialiser le client API
    print("\n📂 Initialisation du client API Gazelle...")
    try:
        api_client = GazelleAPIClient()
        print("✅ Client API initialisé")
    except Exception as e:
        print(f"❌ Erreur d'initialisation: {e}")
        return
    
    # Phase 1: Lecture du piano
    print(f"\n📖 PHASE 1: LECTURE DU PIANO")
    print("-"*80)
    print(f"Requête GET pour piano ID: {PIANO_ID}")
    
    try:
        piano_data = get_piano_by_id(api_client, PIANO_ID)
        print("✅ Piano récupéré avec succès!")
    except Exception as e:
        print(f"❌ Erreur lors de la lecture: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Phase 2: Analyse de structure
    print(f"\n🔍 PHASE 2: ANALYSE DE STRUCTURE")
    print("-"*80)
    analyze_piano_structure(piano_data)
    
    # Phase 3: Identification des champs obligatoires
    print(f"\n🔑 PHASE 3: IDENTIFICATION DES CHAMPS OBLIGATOIRES")
    print("-"*80)
    identify_required_fields(piano_data)
    
    # Phase 4: Proposition du script POST
    print(f"\n📝 PHASE 4: PROPOSITION DU SCRIPT POST")
    print("-"*80)
    propose_mutation_script(piano_data)
    
    print("\n" + "="*80)
    print("✅ ANALYSE TERMINÉE")
    print("="*80)
    print("\n⚠️  PROCHAINES ÉTAPES:")
    print("   1. Valider la structure avec la documentation Gazelle")
    print("   2. Vérifier les types d'entrées disponibles")
    print("   3. Tester la mutation sur un piano de test")
    print("   4. Une fois validé, exécuter sur le piano réel")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()

