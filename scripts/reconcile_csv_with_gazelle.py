#!/usr/bin/env python3
"""
Script de réconciliation CSV ↔ Gazelle pour Vincent d'Indy.

Compare les 119 pianos dans Gazelle avec les 91 pianos du CSV.
Marque chaque piano avec is_in_csv = True/False dans Supabase.
Génère un rapport des différences pour décision manuelle.
"""

import sys
import os
import csv
from typing import List, Dict, Set

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage

# ID du client Vincent d'Indy
VINCENT_DINDY_CLIENT_ID = "cli_9UMLkteep8EsISbG"
CSV_PATH = "/Users/allansutton/Documents/assistant-gazelle-v5/api/data/pianos_vincent_dindy.csv"


class PianoReconciliator:
    """Réconcilie les pianos entre Gazelle et CSV."""

    def __init__(self):
        self.gazelle_client = GazelleAPIClient()
        self.supabase = SupabaseStorage()
        self.stats = {
            'gazelle_total': 0,
            'csv_total': 0,
            'in_both': 0,
            'only_in_gazelle': 0,
            'only_in_csv': 0,
            'gazelle_active': 0,
            'gazelle_inactive': 0
        }

    def load_gazelle_pianos(self) -> List[Dict]:
        """Charge tous les pianos Vincent d'Indy depuis Gazelle."""

        print("🔍 Chargement des pianos depuis Gazelle...")

        query = """
        query GetVincentDIndyPianos($clientId: String!) {
          allPianos(first: 200, filters: { clientId: $clientId }) {
            nodes {
              id
              serialNumber
              make
              model
              location
              type
              status
              notes
              calculatedLastService
              calculatedNextService
              serviceIntervalMonths
            }
          }
        }
        """

        variables = {"clientId": VINCENT_DINDY_CLIENT_ID}

        result = self.gazelle_client._execute_query(query, variables)
        pianos = result.get("data", {}).get("allPianos", {}).get("nodes", [])

        self.stats['gazelle_total'] = len(pianos)
        self.stats['gazelle_active'] = sum(1 for p in pianos if p.get('status') == 'ACTIVE')
        self.stats['gazelle_inactive'] = len(pianos) - self.stats['gazelle_active']

        print(f"✅ {len(pianos)} pianos chargés depuis Gazelle")
        print(f"   - Actifs: {self.stats['gazelle_active']}")
        print(f"   - Inactifs: {self.stats['gazelle_inactive']}")

        return pianos

    def load_csv_pianos(self) -> List[Dict]:
        """Charge les pianos depuis le CSV."""

        print(f"\n🔍 Chargement des pianos depuis CSV...")
        print(f"   Fichier: {CSV_PATH}")

        pianos = []

        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pianos.append(row)

        self.stats['csv_total'] = len(pianos)

        print(f"✅ {len(pianos)} pianos chargés depuis CSV")

        return pianos

    def normalize_serial(self, serial: str) -> str:
        """Normalise un numéro de série pour comparaison."""
        if not serial:
            return ""
        return serial.strip().lower().replace(" ", "")

    def reconcile(self, gazelle_pianos: List[Dict], csv_pianos: List[Dict]) -> Dict:
        """
        Réconcilie les pianos entre Gazelle et CSV.

        Returns:
            Dict avec les résultats de la réconciliation
        """

        print("\n🔄 Réconciliation CSV ↔ Gazelle...")
        print("=" * 80)

        # Créer un set des numéros de série du CSV (normalisés)
        csv_serials = set()
        csv_by_serial = {}

        for csv_piano in csv_pianos:
            serial = csv_piano.get('# série', '') or csv_piano.get('serie', '')
            normalized = self.normalize_serial(serial)
            if normalized:
                csv_serials.add(normalized)
                csv_by_serial[normalized] = csv_piano

        # Analyser chaque piano Gazelle
        in_both = []
        only_in_gazelle = []

        for gz_piano in gazelle_pianos:
            gz_serial = self.normalize_serial(gz_piano.get('serialNumber', ''))

            if gz_serial and gz_serial in csv_serials:
                # Piano dans les deux
                in_both.append({
                    'gazelle': gz_piano,
                    'csv': csv_by_serial[gz_serial]
                })
            else:
                # Piano seulement dans Gazelle
                only_in_gazelle.append(gz_piano)

        # Trouver les pianos seulement dans CSV
        gazelle_serials = set(
            self.normalize_serial(p.get('serialNumber', ''))
            for p in gazelle_pianos
            if self.normalize_serial(p.get('serialNumber', ''))
        )

        only_in_csv = []
        for csv_piano in csv_pianos:
            serial = csv_piano.get('# série', '') or csv_piano.get('serie', '')
            normalized = self.normalize_serial(serial)
            if normalized and normalized not in gazelle_serials:
                only_in_csv.append(csv_piano)

        self.stats['in_both'] = len(in_both)
        self.stats['only_in_gazelle'] = len(only_in_gazelle)
        self.stats['only_in_csv'] = len(only_in_csv)

        return {
            'in_both': in_both,
            'only_in_gazelle': only_in_gazelle,
            'only_in_csv': only_in_csv
        }

    def update_supabase_flags(self, reconciliation: Dict, dry_run: bool = True):
        """
        Met à jour les flags is_in_csv dans Supabase.

        Args:
            reconciliation: Résultats de la réconciliation
            dry_run: Si True, n'applique pas les changements
        """

        print(f"\n{'🔍 [DRY RUN]' if dry_run else '💾'} Mise à jour des flags Supabase...")

        updates_applied = 0

        # Marquer les pianos présents dans les deux
        for match in reconciliation['in_both']:
            gz_id = match['gazelle']['id']
            csv_serial = match['csv'].get('# série', '') or match['csv'].get('serie', '')

            if not dry_run:
                try:
                    # Essayer de mettre à jour via l'API REST
                    import requests

                    url = f"{self.supabase.api_url}/vincent_dindy_piano_updates?piano_id=eq.{csv_serial}"
                    headers = self.supabase._get_headers()

                    # Vérifier si l'entrée existe
                    response = requests.get(url, headers=headers)

                    if response.status_code == 200 and response.json():
                        # Mettre à jour
                        update_data = {'is_in_csv': True, 'gazelle_id': gz_id}
                        response = requests.patch(url, json=update_data, headers=headers)
                    else:
                        # Créer l'entrée
                        insert_data = {'piano_id': csv_serial, 'gazelle_id': gz_id, 'is_in_csv': True}
                        response = requests.post(
                            f"{self.supabase.api_url}/vincent_dindy_piano_updates",
                            json=insert_data,
                            headers=headers
                        )

                    if response.status_code in [200, 201]:
                        updates_applied += 1
                    else:
                        print(f"  ⚠️  Erreur pour {csv_serial}: HTTP {response.status_code}")

                except Exception as e:
                    print(f"  ⚠️  Erreur pour {csv_serial}: {e}")
            else:
                print(f"  ✓ Marquerait {csv_serial} → is_in_csv=True")

        # Marquer les pianos seulement dans Gazelle
        for gz_piano in reconciliation['only_in_gazelle']:
            gz_id = gz_piano['id']
            gz_serial = gz_piano.get('serialNumber', 'N/A')

            if not dry_run:
                try:
                    import requests

                    # Utiliser gazelle_id comme clé de recherche
                    url = f"{self.supabase.api_url}/vincent_dindy_piano_updates?gazelle_id=eq.{gz_id}"
                    headers = self.supabase._get_headers()

                    # Vérifier si l'entrée existe
                    response = requests.get(url, headers=headers)

                    if response.status_code == 200 and response.json():
                        # Mettre à jour
                        update_data = {'is_in_csv': False}
                        response = requests.patch(url, json=update_data, headers=headers)
                    else:
                        # Créer l'entrée
                        insert_data = {
                            'piano_id': gz_serial if gz_serial and gz_serial != 'N/A' else None,
                            'gazelle_id': gz_id,
                            'is_in_csv': False
                        }
                        response = requests.post(
                            f"{self.supabase.api_url}/vincent_dindy_piano_updates",
                            json=insert_data,
                            headers=headers
                        )

                    if response.status_code in [200, 201]:
                        updates_applied += 1
                    else:
                        print(f"  ⚠️  Erreur pour {gz_serial}: HTTP {response.status_code}")

                except Exception as e:
                    print(f"  ⚠️  Erreur pour {gz_serial}: {e}")
            else:
                print(f"  ✓ Marquerait {gz_serial} → is_in_csv=False")

        if not dry_run:
            print(f"\n✅ {updates_applied} mises à jour appliquées")
        else:
            print(f"\n💡 {len(reconciliation['in_both']) + len(reconciliation['only_in_gazelle'])} mises à jour seraient appliquées")

    def generate_report(self, reconciliation: Dict) -> str:
        """Génère un rapport Markdown des différences."""

        lines = []

        # Header
        lines.append("# Rapport de Réconciliation CSV ↔ Gazelle")
        lines.append("")
        lines.append("**Client:** École Vincent-d'Indy")
        lines.append(f"**Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Statistiques
        lines.append("## 📊 Statistiques")
        lines.append("")
        lines.append(f"- **Pianos dans Gazelle:** {self.stats['gazelle_total']}")
        lines.append(f"  - Actifs: {self.stats['gazelle_active']}")
        lines.append(f"  - Inactifs: {self.stats['gazelle_inactive']}")
        lines.append(f"- **Pianos dans CSV:** {self.stats['csv_total']}")
        lines.append(f"- **Pianos dans les deux:** {self.stats['in_both']}")
        lines.append(f"- **Pianos seulement dans Gazelle:** {self.stats['only_in_gazelle']}")
        lines.append(f"- **Pianos seulement dans CSV:** {self.stats['only_in_csv']}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Pianos seulement dans Gazelle
        lines.append("## 🆕 Pianos dans Gazelle mais PAS dans CSV")
        lines.append("")
        lines.append(f"**Total:** {len(reconciliation['only_in_gazelle'])} pianos")
        lines.append("")

        if reconciliation['only_in_gazelle']:
            lines.append("| Gazelle ID | Serial | Marque | Modèle | Local | Status | Dernier Accord |")
            lines.append("|------------|--------|--------|--------|-------|--------|----------------|")

            for p in sorted(reconciliation['only_in_gazelle'], key=lambda x: x.get('status', '')):
                gz_id = p['id']
                serial = p.get('serialNumber', 'N/A')
                make = p.get('make', '?')
                model = p.get('model', '')
                location = p.get('location', 'N/A')
                status = p.get('status', 'N/A')
                last_service = p.get('calculatedLastService', 'Jamais')

                lines.append(f"| `{gz_id}` | {serial} | {make} | {model} | {location} | {status} | {last_service} |")

            lines.append("")
        else:
            lines.append("*Aucun piano trouvé seulement dans Gazelle.*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Pianos seulement dans CSV
        lines.append("## ⚠️ Pianos dans CSV mais PAS dans Gazelle")
        lines.append("")
        lines.append(f"**Total:** {len(reconciliation['only_in_csv'])} pianos")
        lines.append("")

        if reconciliation['only_in_csv']:
            lines.append("| Serial CSV | Marque | Local |")
            lines.append("|------------|--------|-------|")

            for p in reconciliation['only_in_csv']:
                serial = p.get('# série', '') or p.get('serie', 'N/A')
                make = p.get('Piano', '') or p.get('marque', '?')
                location = p.get('local', 'N/A')

                lines.append(f"| {serial} | {make} | {location} |")

            lines.append("")
            lines.append("**⚠️ Action requise:** Ces pianos sont dans votre CSV mais introuvables dans Gazelle.")
            lines.append("Raisons possibles:")
            lines.append("- Piano vendu/retiré de Gazelle")
            lines.append("- Erreur de numéro de série dans CSV")
            lines.append("- Piano attribué à un autre client dans Gazelle")
            lines.append("")
        else:
            lines.append("*Tous les pianos CSV ont été trouvés dans Gazelle!*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Recommandations
        lines.append("## 💡 Recommandations")
        lines.append("")

        if self.stats['only_in_gazelle'] > 0:
            lines.append(f"### Pianos dans Gazelle uniquement ({self.stats['only_in_gazelle']})")
            lines.append("")
            active_only_gz = sum(1 for p in reconciliation['only_in_gazelle'] if p.get('status') == 'ACTIVE')
            inactive_only_gz = self.stats['only_in_gazelle'] - active_only_gz

            lines.append(f"- **{active_only_gz} pianos actifs** non listés dans CSV")
            lines.append(f"  → Décision: Ajouter au CSV ou marquer comme 'hors inventaire' dans l'interface?")
            lines.append("")
            lines.append(f"- **{inactive_only_gz} pianos inactifs** non listés dans CSV")
            lines.append(f"  → Ces pianos ne sont probablement plus à l'école (vendus, retirés)")
            lines.append(f"  → Recommandation: Les masquer par défaut dans l'interface")
            lines.append("")

        if self.stats['only_in_csv'] > 0:
            lines.append(f"### Pianos dans CSV uniquement ({self.stats['only_in_csv']})")
            lines.append("")
            lines.append("⚠️ **Action requise:** Vérifier ces pianos manuellement")
            lines.append("- Vérifier les numéros de série dans Gazelle")
            lines.append("- Confirmer s'ils sont toujours à l'école")
            lines.append("- Les retirer du CSV si vendus/transférés")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("**Prochaine étape:**")
        lines.append("")
        lines.append("Exécuter avec `--apply` pour marquer les pianos dans Supabase:")
        lines.append("```bash")
        lines.append("python3 scripts/reconcile_csv_with_gazelle.py --apply")
        lines.append("```")

        return "\n".join(lines)

    def run(self, apply: bool = False):
        """
        Exécute la réconciliation complète.

        Args:
            apply: Si True, applique les changements dans Supabase
        """

        print("\n" + "=" * 80)
        print("🔄 RÉCONCILIATION CSV ↔ GAZELLE - VINCENT D'INDY")
        print("=" * 80)

        # 1. Charger les données
        gazelle_pianos = self.load_gazelle_pianos()
        csv_pianos = self.load_csv_pianos()

        # 2. Réconcilier
        reconciliation = self.reconcile(gazelle_pianos, csv_pianos)

        # 3. Afficher les résultats
        print("\n" + "=" * 80)
        print("📊 RÉSULTATS")
        print("=" * 80)
        print(f"✅ Pianos dans les deux:          {self.stats['in_both']}")
        print(f"🆕 Pianos seulement dans Gazelle: {self.stats['only_in_gazelle']}")
        print(f"⚠️  Pianos seulement dans CSV:    {self.stats['only_in_csv']}")

        # 4. Mettre à jour Supabase
        self.update_supabase_flags(reconciliation, dry_run=not apply)

        # 5. Générer le rapport
        print("\n📝 Génération du rapport...")
        report = self.generate_report(reconciliation)

        output_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "rapport_reconciliation_vincent_dindy.md"
        )

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"✅ Rapport sauvegardé: {output_file}")

        # 6. Afficher un aperçu des pianos seulement dans Gazelle
        if reconciliation['only_in_gazelle']:
            print(f"\n🔍 Aperçu des {min(5, len(reconciliation['only_in_gazelle']))} premiers pianos UNIQUEMENT dans Gazelle:")
            print("=" * 80)

            for i, p in enumerate(reconciliation['only_in_gazelle'][:5], 1):
                status = p.get('status', 'N/A')
                make = p.get('make', '?')
                model = p.get('model', '')
                location = p.get('location', 'N/A')
                serial = p.get('serialNumber', 'N/A')

                print(f"{i}. [{status}] {make} {model}")
                print(f"   Serial: {serial} | Local: {location}")
                print(f"   ID: {p['id']}")
                print()

        print("\n" + "=" * 80)
        print(f"✅ Réconciliation terminée!")
        print(f"📄 Consultez le rapport complet: {output_file}")

        if not apply:
            print("\n💡 Pour appliquer les changements dans Supabase:")
            print("   python3 scripts/reconcile_csv_with_gazelle.py --apply")

        print("=" * 80)


def main():
    """Point d'entrée principal."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Réconcilie les pianos CSV avec Gazelle pour Vincent d'Indy"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help="Appliquer les changements dans Supabase (par défaut: dry-run)"
    )

    args = parser.parse_args()

    reconciliator = PianoReconciliator()
    reconciliator.run(apply=args.apply)


if __name__ == "__main__":
    main()
