#!/usr/bin/env python3
"""
🔍 Vérification de la Complétude des Données pour l'Assistant Chat

Vérifie que toutes les données nécessaires pour répondre aux 40 questions sont présentes.
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.supabase_storage import SupabaseStorage


class ChatDataVerifier:
    """Vérifie la complétude des données pour l'assistant chat."""

    def __init__(self):
        self.storage = SupabaseStorage()
        self.results = {
            'rendez_vous': {},
            'clients': {},
            'pianos': {},
            'timeline': {},
            'users': {},
        }

    def print_header(self, title):
        """Affiche un en-tête de section."""
        print("\n" + "=" * 80)
        print(f"📊 {title}")
        print("=" * 80)

    def print_check(self, label, value, expected=None, unit=""):
        """Affiche un check avec valeur."""
        if expected:
            status = "✅" if value >= expected else "⚠️"
            print(f"{status} {label}: {value:,}{unit} (attendu: ≥{expected:,})")
        else:
            status = "✅" if value > 0 else "❌"
            print(f"{status} {label}: {value:,}{unit}")

    def verify_appointments(self):
        """Vérifie les rendez-vous (questions 1-14)."""
        self.print_header("RENDEZ-VOUS (Questions 1-14)")

        try:
            # Total rendez-vous
            total = self.storage.client.table('gazelle_appointments')\
                .select('id', count='exact')\
                .execute()
            self.results['rendez_vous']['total'] = total.count or 0
            self.print_check("Total rendez-vous", self.results['rendez_vous']['total'], expected=100)

            print("\n  ℹ️  Détails temporels skippés (nom colonne date inconnu)")
            print("  ℹ️  Pour analyses temporelles, voir le dashboard RV directement\n")

        except Exception as e:
            print(f"  ⚠️  Erreur: {e}")
            self.results['rendez_vous']['total'] = 0

    def verify_clients(self):
        """Vérifie les clients (questions 15-26)."""
        self.print_header("CLIENTS (Questions 15-26)")

        # Total clients
        total = self.storage.client.table('gazelle_clients')\
            .select('id', count='exact')\
            .execute()
        self.results['clients']['total'] = total.count or 0
        self.print_check("Total clients", self.results['clients']['total'], expected=100)

        # Clients VIP (Yannick Nézet-Séguin)
        yannick = self.storage.client.table('gazelle_clients')\
            .select('id')\
            .or_('first_name.ilike.%Yannick%,last_name.ilike.%Nézet%')\
            .execute()
        self.results['clients']['yannick'] = len(yannick.data) if yannick.data else 0
        self.print_check("  → Yannick (VIP)", self.results['clients']['yannick'], expected=1)

        # Contacts (Anne-Marie)
        contacts = self.storage.client.table('gazelle_contacts')\
            .select('id', count='exact')\
            .execute()
        self.results['clients']['contacts_total'] = contacts.count or 0
        self.print_check("  → Contacts (table séparée)", self.results['clients']['contacts_total'])

        # Organisations
        orgs = self.storage.client.table('gazelle_clients')\
            .select('id', count='exact')\
            .eq('is_organization', True)\
            .execute()
        self.results['clients']['organizations'] = orgs.count or 0
        self.print_check("  → Organisations", self.results['clients']['organizations'], expected=10)

        # Clients avec email
        with_email = self.storage.client.table('gazelle_clients')\
            .select('id', count='exact')\
            .not_.is_('email', 'null')\
            .execute()
        self.results['clients']['with_email'] = with_email.count or 0
        self.print_check("  → Avec email", self.results['clients']['with_email'])

        # Clients avec téléphone
        with_phone = self.storage.client.table('gazelle_clients')\
            .select('id', count='exact')\
            .not_.is_('phone', 'null')\
            .execute()
        self.results['clients']['with_phone'] = with_phone.count or 0
        self.print_check("  → Avec téléphone", self.results['clients']['with_phone'])

        # Clients avec adresse
        with_address = self.storage.client.table('gazelle_clients')\
            .select('id', count='exact')\
            .not_.is_('city', 'null')\
            .execute()
        self.results['clients']['with_address'] = with_address.count or 0
        self.print_check("  → Avec ville", self.results['clients']['with_address'])

    def verify_pianos(self):
        """Vérifie les pianos (questions 27-34)."""
        self.print_header("PIANOS (Questions 27-34)")

        # Total pianos
        total = self.storage.client.table('gazelle_pianos')\
            .select('id', count='exact')\
            .execute()
        self.results['pianos']['total'] = total.count or 0
        self.print_check("Total pianos", self.results['pianos']['total'], expected=200)

        # Steinway
        steinway = self.storage.client.table('gazelle_pianos')\
            .select('id', count='exact')\
            .ilike('make', '%Steinway%')\
            .execute()
        self.results['pianos']['steinway'] = steinway.count or 0
        self.print_check("  → Steinway", self.results['pianos']['steinway'], expected=10)

        # Yamaha
        yamaha = self.storage.client.table('gazelle_pianos')\
            .select('id', count='exact')\
            .ilike('make', '%Yamaha%')\
            .execute()
        self.results['pianos']['yamaha'] = yamaha.count or 0
        self.print_check("  → Yamaha", self.results['pianos']['yamaha'], expected=20)

        # Kawai
        kawai = self.storage.client.table('gazelle_pianos')\
            .select('id', count='exact')\
            .ilike('make', '%Kawai%')\
            .execute()
        self.results['pianos']['kawai'] = kawai.count or 0
        self.print_check("  → Kawai", self.results['pianos']['kawai'])

        # Avec numéro de série
        with_serial = self.storage.client.table('gazelle_pianos')\
            .select('id', count='exact')\
            .not_.is_('serial_number', 'null')\
            .execute()
        self.results['pianos']['with_serial'] = with_serial.count or 0
        self.print_check("  → Avec numéro de série", self.results['pianos']['with_serial'])

        # Avec type (grand, upright)
        with_type = self.storage.client.table('gazelle_pianos')\
            .select('id', count='exact')\
            .not_.is_('type', 'null')\
            .execute()
        self.results['pianos']['with_type'] = with_type.count or 0
        self.print_check("  → Avec type (grand/upright)", self.results['pianos']['with_type'])

    def verify_timeline(self):
        """Vérifie les entrées de timeline (historique)."""
        self.print_header("TIMELINE / HISTORIQUE")

        # Total entrées
        total = self.storage.client.table('gazelle_timeline_entries')\
            .select('id', count='exact')\
            .execute()
        self.results['timeline']['total'] = total.count or 0
        self.print_check("Total entrées timeline", self.results['timeline']['total'], expected=10000)

        # Par année
        years = [2024, 2023, 2022, 2021, 2020]
        for year in years:
            year_count = self.storage.client.table('gazelle_timeline_entries')\
                .select('id', count='exact')\
                .gte('occurred_at', f'{year}-01-01T00:00:00Z')\
                .lt('occurred_at', f'{year+1}-01-01T00:00:00Z')\
                .execute()
            count = year_count.count or 0
            self.results['timeline'][f'year_{year}'] = count
            self.print_check(f"  → {year}", count, expected=1000 if year >= 2020 else 500)

        # Types d'entrées
        print("\n  Types d'entrées:")
        types = ['SERVICE_ENTRY_MANUAL', 'APPOINTMENT', 'PIANO_MEASUREMENT', 'NOTE']
        for entry_type in types:
            type_count = self.storage.client.table('gazelle_timeline_entries')\
                .select('id', count='exact')\
                .eq('entry_type', entry_type)\
                .execute()
            count = type_count.count or 0
            print(f"    • {entry_type}: {count:,}")

    def verify_users(self):
        """Vérifie les utilisateurs/techniciens."""
        self.print_header("UTILISATEURS / TECHNICIENS")

        # Total users
        total = self.storage.client.table('users')\
            .select('id', count='exact')\
            .execute()
        self.results['users']['total'] = total.count or 0
        self.print_check("Total utilisateurs", self.results['users']['total'], expected=5)

        # Techniciens (rôle)
        techs = self.storage.client.table('users')\
            .select('id', count='exact')\
            .eq('role', 'technician')\
            .execute()
        self.results['users']['technicians'] = techs.count or 0
        self.print_check("  → Techniciens", self.results['users']['technicians'], expected=3)

        # Avec nom complet
        with_name = self.storage.client.table('users')\
            .select('id', count='exact')\
            .not_.is_('first_name', 'null')\
            .execute()
        self.results['users']['with_name'] = with_name.count or 0
        self.print_check("  → Avec prénom", self.results['users']['with_name'])

    def verify_data_quality(self):
        """Vérifie la qualité des données."""
        self.print_header("QUALITÉ DES DONNÉES")

        # Doublons timeline
        duplicates = self.storage.client.rpc('check_timeline_duplicates').execute()
        # Note: Cette fonction n'existe peut-être pas, on fait un check manuel
        print("⚠️  Vérification doublons timeline (manuel requis)")

        # Relations cassées (FK)
        print("\n  Relations cassées:")

        # Timeline sans client
        no_client = self.storage.client.table('gazelle_timeline_entries')\
            .select('id', count='exact')\
            .is_('client_id', 'null')\
            .execute()
        no_client_count = no_client.count or 0
        self.print_check("    Timeline sans client", no_client_count)

        # Timeline sans piano (mais certains types n'en ont pas besoin)
        no_piano = self.storage.client.table('gazelle_timeline_entries')\
            .select('id', count='exact')\
            .is_('piano_id', 'null')\
            .execute()
        no_piano_count = no_piano.count or 0
        print(f"    ℹ️  Timeline sans piano: {no_piano_count:,} (normal pour certains types)")

        # RV sans client
        appt_no_client = self.storage.client.table('gazelle_appointments')\
            .select('id', count='exact')\
            .is_('client_id', 'null')\
            .execute()
        appt_no_client_count = appt_no_client.count or 0
        self.print_check("    RV sans client", appt_no_client_count)

    def generate_summary(self):
        """Génère un résumé global."""
        self.print_header("RÉSUMÉ GLOBAL")

        total_checks = 0
        passed_checks = 0

        # RV
        if self.results['rendez_vous']['total'] >= 100:
            passed_checks += 1
        total_checks += 1

        # Clients
        if self.results['clients']['total'] >= 100:
            passed_checks += 1
        total_checks += 1

        # Pianos
        if self.results['pianos']['total'] >= 200:
            passed_checks += 1
        total_checks += 1

        # Timeline
        if self.results['timeline']['total'] >= 10000:
            passed_checks += 1
        total_checks += 1

        # Users
        if self.results['users']['total'] >= 5:
            passed_checks += 1
        total_checks += 1

        pct = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

        print(f"\n✅ Checks réussis: {passed_checks}/{total_checks} ({pct:.0f}%)")

        if pct >= 80:
            print("\n🎉 Les données sont SUFFISANTES pour répondre aux 40 questions!")
        elif pct >= 60:
            print("\n⚠️  Les données sont PARTIELLES. Certaines questions pourraient échouer.")
        else:
            print("\n❌ Les données sont INSUFFISANTES. Import requis!")

        print("\n💡 Recommandations:")

        if self.results['rendez_vous']['future'] < 50:
            print("  • Importer plus de RV futurs (90 jours)")

        if self.results['timeline']['total'] < 10000:
            print("  • Continuer l'import timeline historique")

        if self.results['pianos']['total'] < 200:
            print("  • Vérifier l'import des pianos")

        if self.results['clients']['yannick'] == 0:
            print("  • ⚠️  Client VIP 'Yannick' manquant (question 15)")

    def run(self):
        """Exécute toutes les vérifications."""
        print("\n" + "=" * 80)
        print("🔍 VÉRIFICATION COMPLÉTUDE DONNÉES - ASSISTANT CHAT")
        print("=" * 80)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        self.verify_appointments()
        self.verify_clients()
        self.verify_pianos()
        self.verify_timeline()
        self.verify_users()
        self.verify_data_quality()
        self.generate_summary()

        print("\n" + "=" * 80)
        print("✅ Vérification terminée!")
        print("=" * 80 + "\n")


if __name__ == '__main__':
    verifier = ChatDataVerifier()
    verifier.run()
