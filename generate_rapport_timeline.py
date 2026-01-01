#!/usr/bin/env python3
"""
Script pour générer le Rapport Timeline de l'assistant V5.

Génère les 4 onglets:
- UQAM
- Vincent
- Place des Arts
- Alertes Maintenance

Usage:
    python3 generate_rapport_timeline.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from modules.reports.service_reports import run_reports

if __name__ == "__main__":
    print("📊 Génération du Rapport Timeline de l'assistant v5...")
    print("=" * 70)
    print("Google Sheet: Rapport Timeline de l'assistant v5")
    print("=" * 70)

    # Générer le rapport (mode replace, pas append)
    result = run_reports(append=False)

    print("\n" + "=" * 70)
    print("✅ Rapport généré avec succès!")
    print("=" * 70)

    for tab, count in result.items():
        print(f"   {tab}: {count} lignes")

    print("\n🔗 Voir le rapport:")
    print("   https://docs.google.com/spreadsheets/d/1ZZsMrIT0BEwHKQ6-BKGzFoXR3k99zCEzixp0tsRKUj8")
