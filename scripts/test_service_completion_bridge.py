#!/usr/bin/env python3
"""
Test du Service Completion Bridge

Ce script teste le pont modulaire entre l'Assistant et le moteur Gazelle.

Usage:
    python3 scripts/test_service_completion_bridge.py [piano_id]

Exemples:
    # Test avec le piano de test par défaut
    python3 scripts/test_service_completion_bridge.py

    # Test avec un piano spécifique
    python3 scripts/test_service_completion_bridge.py ins_RXJMSDTckzu2Xswd
"""

import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.service_completion_bridge import complete_service_session


def test_bridge(piano_id: str):
    """
    Test complet du Service Completion Bridge.

    Args:
        piano_id: ID Gazelle du piano à tester
    """
    print(f"\n{'='*70}")
    print(f"TEST DU SERVICE COMPLETION BRIDGE")
    print(f"{'='*70}\n")

    # Notes de service de test
    service_notes = """
Accord 440 Hz
Cordes en bon état
Température: 22°C
Humidité: 45%
Notes: Mécanique légèrement bruyante, à surveiller
    """.strip()

    print(f"📋 Paramètres du test:")
    print(f"   Piano ID: {piano_id}")
    print(f"   Institution: vincent-dindy")
    print(f"   Technicien: Nicolas")
    print(f"   Notes de service:")
    for line in service_notes.split('\n'):
        print(f"      {line}")
    print(f"\n{'='*70}\n")

    try:
        # Appeler le pont modulaire
        result = complete_service_session(
            piano_id=piano_id,
            service_notes=service_notes,
            institution="vincent-dindy",
            technician_name="Nicolas",
            service_type="TUNING",
            metadata={
                'test_run': True,
                'script': 'test_service_completion_bridge.py'
            }
        )

        # Afficher les résultats
        print(f"\n{'='*70}")
        print(f"RÉSULTATS DU TEST")
        print(f"{'='*70}\n")

        if result['success']:
            print(f"✅ SUCCÈS - Service complété avec succès!\n")
            print(f"📊 Détails:")
            print(f"   Piano ID: {result['piano_id']}")
            print(f"   Event ID Gazelle: {result['gazelle_event_id']}")
            print(f"   Last Tuned mis à jour: {result['last_tuned_updated']}")
            print(f"   Note de service créée: {result['service_note_created']}")
            print(f"   Mesure créée: {result['measurement_created']}")

            if result['measurement_values']:
                temp = result['measurement_values']['temperature']
                humidity = result['measurement_values']['humidity']
                print(f"   Valeurs mesurées: {temp}°C, {humidity}%")

            print(f"   Piano remis en INACTIVE: {result['piano_set_inactive']}")
            print(f"   Timestamp: {result['timestamp']}")

            print(f"\n{'='*70}")
            print(f"🎯 VÉRIFICATIONS À FAIRE DANS GAZELLE:")
            print(f"{'='*70}")
            print(f"1. Ouvrir le piano dans Gazelle: {piano_id}")
            print(f"2. Vérifier que 'Last Tuned' est mis à jour")
            print(f"3. Vérifier que l'historique contient une nouvelle entrée")
            print(f"4. Vérifier que la température/humidité est enregistrée")
            print(f"5. Vérifier que le piano est en statut INACTIVE")
            print(f"{'='*70}\n")

            return 0
        else:
            print(f"❌ ÉCHEC - Erreur lors de la complétion du service\n")
            print(f"   Erreur: {result.get('error', 'Erreur inconnue')}")
            print(f"   Piano ID: {result['piano_id']}")
            print(f"   Timestamp: {result['timestamp']}")
            print(f"\n{'='*70}\n")

            return 1

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ EXCEPTION - Erreur non gérée")
        print(f"{'='*70}\n")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")

        import traceback
        print(f"\nTraceback:")
        traceback.print_exc()
        print(f"\n{'='*70}\n")

        return 1


if __name__ == "__main__":
    # Piano ID par défaut (piano de test Vincent d'Indy)
    default_piano_id = "ins_RXJMSDTckzu2Xswd"

    # Récupérer le piano ID depuis les arguments ou utiliser le défaut
    piano_id = sys.argv[1] if len(sys.argv) > 1 else default_piano_id

    # Exécuter le test
    exit_code = test_bridge(piano_id)

    sys.exit(exit_code)
