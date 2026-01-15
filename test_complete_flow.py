#!/usr/bin/env python3
"""Test complet du flow - Parser + Preview API response."""

from modules.place_des_arts.services.email_parser import parse_email_text
import json

# Exemple réel d'Annie Jenkins
test_text = """
Est-ce possible pour vous de faire un accord du Steinway 9' D - New York à 442 de la Salle D le 20 janvier entre 8h00 et 9h00?

Merci de me confirmer si c'est possible.

ANNIE JENKINS
"""

print("=" * 80)
print("TEST COMPLET - Format naturel Annie Jenkins")
print("=" * 80)
print(f"\nTexte d'entrée:\n{test_text}")
print("\n" + "=" * 80)

# 1. Parser le texte
parsed = parse_email_text(test_text)

print(f"\n📋 ÉTAPE 1: Parsing")
print(f"Nombre de demandes détectées: {len(parsed)}")

if not parsed:
    print("❌ Aucune demande détectée")
    exit(1)

# 2. Simuler la réponse de l'API /preview
from datetime import datetime

needs_validation = False
preview = []

for idx, item in enumerate(parsed, start=1):
    appt_val = item.get("date")
    if isinstance(appt_val, datetime):
        appt_val = appt_val.date().isoformat()

    confidence = item.get("confidence", 0.0)
    warnings = item.get("warnings", [])
    is_unusual_format = confidence < 1.0 or len(warnings) > 0

    if is_unusual_format:
        needs_validation = True

    row = {
        "appointment_date": appt_val if isinstance(appt_val, str) else item.get("date"),
        "room": item.get("room"),
        "for_who": item.get("for_who"),
        "diapason": item.get("diapason"),
        "requester": item.get("requester"),
        "piano": item.get("piano"),
        "time": item.get("time"),
        "service": item.get("service"),
        "notes": item.get("notes"),
        "confidence": confidence,
        "warnings": warnings,
        "needs_validation": is_unusual_format
    }
    preview.append(row)

# 3. Afficher le résultat comme l'API le retournerait
api_response = {
    "success": True,
    "preview": preview,
    "count": len(preview),
    "needs_validation": needs_validation,
    "message": "Veuillez vérifier les champs détectés avant d'importer" if needs_validation else "Demandes détectées avec haute confiance"
}

print("\n" + "=" * 80)
print("📤 ÉTAPE 2: Réponse API /preview")
print("=" * 80)
print(json.dumps(api_response, indent=2, ensure_ascii=False, default=str))

print("\n" + "=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)
print(f"✅ Demandes détectées: {api_response['count']}")
print(f"🔍 Validation requise: {'OUI' if api_response['needs_validation'] else 'NON'}")
print(f"💬 Message: {api_response['message']}")

if api_response['needs_validation']:
    print("\n⚠️  FORMAT INHABITUEL DÉTECTÉ")
    print("→ L'utilisateur sera invité à vérifier/corriger les champs")
    print("→ Cette correction sera enregistrée pour apprentissage futur")
else:
    print("\n✅ FORMAT RECONNU")
    print("→ Import direct possible sans validation")

print("\n" + "=" * 80)
