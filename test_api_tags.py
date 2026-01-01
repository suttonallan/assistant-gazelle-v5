#!/usr/bin/env python3
import requests
import json

# Test avec include_inactive
response = requests.get("http://localhost:8000/vincent-dindy/pianos?include_inactive=true")
data = response.json()

print(f"Count avec include_inactive: {data.get('count')}")

piano_avec_tag = [p for p in data['pianos'] if p.get('hasNonTag')]
print(f"Pianos avec tag NON: {len(piano_avec_tag)}")

if piano_avec_tag:
    p = piano_avec_tag[0]
    print(f"Exemple: {p.get('serie')} @ {p.get('local')}")
    print(f"  Tags: {p.get('tags')}")
    print(f"  hasNonTag: {p.get('hasNonTag')}")
