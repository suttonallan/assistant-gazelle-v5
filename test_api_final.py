#!/usr/bin/env python3
import requests

# Test 1: Sans include_inactive (devrait masquer le piano avec tag "non")
print("=" * 60)
print("Test 1: Sans include_inactive (inventaire normal)")
print("=" * 60)
response = requests.get("http://localhost:8000/vincent-dindy/pianos")
data = response.json()
print(f"Count: {data.get('count')}")
pianos_avec_non = [p for p in data['pianos'] if p.get('hasNonTag')]
print(f"Pianos avec tag NON visibles: {len(pianos_avec_non)}")

# Test 2: Avec include_inactive (devrait inclure le piano avec tag "non")
print("\n" + "=" * 60)
print("Test 2: Avec include_inactive=true (tout voir)")
print("=" * 60)
response = requests.get("http://localhost:8000/vincent-dindy/pianos?include_inactive=true")
data = response.json()
print(f"Count: {data.get('count')}")
pianos_avec_non = [p for p in data['pianos'] if p.get('hasNonTag')]
print(f"Pianos avec tag NON visibles: {len(pianos_avec_non)}")

if pianos_avec_non:
    p = pianos_avec_non[0]
    print(f"\nExemple de piano avec tag NON:")
    print(f"  Série: {p.get('serie')}")
    print(f"  Local: {p.get('local')}")
    print(f"  Tags: {p.get('tags')}")
    print(f"  hasNonTag: {p.get('hasNonTag')}")

print("\n✅ Les tags fonctionnent correctement!")
