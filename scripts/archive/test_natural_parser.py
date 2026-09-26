#!/usr/bin/env python3
"""Test du parser en langage naturel pour Place des Arts."""

from modules.place_des_arts.services.email_parser import parse_email_text

# Exemple réel d'Annie Jenkins
test_text = """
Est-ce possible pour vous de faire un accord du Steinway 9' D - New York à 442 de la Salle D le 20 janvier entre 8h00 et 9h00?

Merci de me confirmer si c'est possible.

ANNIE JENKINS
"""

print("=" * 80)
print("TEST PARSER - Format naturel Annie Jenkins")
print("=" * 80)
print(f"\nTexte d'entrée:\n{test_text}")
print("\n" + "=" * 80)

result = parse_email_text(test_text)

print(f"\nRésultat du parsing:")
print(f"Nombre de demandes détectées: {len(result)}")
print("\n" + "=" * 80)

for idx, req in enumerate(result, 1):
    print(f"\nDemande #{idx}:")
    print(f"  Date:       {req.get('date')}")
    print(f"  Heure:      {req.get('time')}")
    print(f"  Salle:      {req.get('room')}")
    print(f"  Piano:      {req.get('piano')}")
    print(f"  Diapason:   {req.get('diapason')}")
    print(f"  Service:    {req.get('service')}")
    print(f"  Pour qui:   {req.get('for_who')}")
    print(f"  Demandeur:  {req.get('requester')}")
    print(f"  Notes:      {req.get('notes')}")
    print(f"  Confiance:  {req.get('confidence'):.2f}")
    if req.get('warnings'):
        print(f"  ⚠️  Avertissements: {', '.join(req.get('warnings', []))}")

print("\n" + "=" * 80)
print("✅ Test terminé!")
print("=" * 80)
