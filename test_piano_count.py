#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.gazelle_api_client import GazelleAPIClient
import json

client = GazelleAPIClient()

query = """
query GetPianoWithTags($clientId: String!) {
  allPianos(first: 200, filters: { clientId: $clientId }) {
    nodes {
      id
      serialNumber
      location
      tags
    }
  }
}
"""

result = client._execute_query(query, {"clientId": "cli_9UMLkteep8EsISbG"})
pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

print(f"Total pianos dans Gazelle: {len(pianos)}")

# Compter ceux avec tag "non"
pianos_avec_non = []
for p in pianos:
    tags_str = p.get('tags', '')
    if tags_str:
        try:
            tags = json.loads(tags_str)
            if 'non' in [t.lower() for t in tags]:
                pianos_avec_non.append(p)
                print(f"  - Piano {p.get('serialNumber')} @ {p.get('location')} - tags: {tags}")
        except:
            pass

print(f"\nPianos avec tag 'non': {len(pianos_avec_non)}")
print(f"Pianos sans tag 'non': {len(pianos) - len(pianos_avec_non)}")

# Chercher le piano 151244
print("\nRecherche du piano 151244:")
piano_151244 = [p for p in pianos if p.get('serialNumber') == '151244']
if piano_151244:
    p = piano_151244[0]
    print(f"✓ Trouvé: {p.get('serialNumber')} @ {p.get('location')}")
    print(f"  Tags: {p.get('tags')}")
else:
    print("✗ Piano 151244 non trouvé")

# Afficher TOUS les pianos avec tags (peu importe le tag)
print("\nTous les pianos avec tags (peu importe le tag):")
for p in pianos:
    tags_str = p.get('tags', '')
    if tags_str:
        print(f"  - Piano {p.get('serialNumber')} @ {p.get('location')} - tags: {tags_str}")
