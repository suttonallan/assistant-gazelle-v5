"""
Générateur de résumés intelligents pour appointments.

Génère des résumés contextuels en analysant l'historique client/piano.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class SmartSummaryGenerator:
    """Génère des résumés intelligents à partir des données client/piano/historique."""

    def __init__(self, storage):
        self.storage = storage

    def _get_entry_date(self, entry: Dict[str, Any]) -> Optional[datetime]:
        """
        Helper: Extrait la date d'une entrée (supporte 'occurred_at' et 'date').

        Args:
            entry: Dict contenant une date

        Returns:
            datetime ou None
        """
        # Essayer 'occurred_at' (format raw Supabase) puis 'date' (format TimelineEntry)
        date_str = entry.get('occurred_at') or entry.get('date')
        if not date_str:
            return None

        try:
            if isinstance(date_str, str):
                # Support format ISO avec/sans timezone
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return date_str
        except:
            return None

    def generate_client_summary(
        self,
        client_id: str,
        timeline_entries: List[Dict[str, Any]],
        comfort_info: Dict[str, Any]
    ) -> str:
        """
        Génère un résumé intelligent du client.

        Ex: "Client depuis 2018, fait accorder son piano chaque année en septembre.
             Préfère être contacté par email. Attention au chien nerveux."

        Args:
            client_id: ID du client
            timeline_entries: Entrées de timeline du client
            comfort_info: Infos de confort (animaux, notes, etc.)

        Returns:
            Résumé textuel intelligent
        """
        summary_parts = []

        # 1. Ancienneté client
        if timeline_entries:
            dates = [self._get_entry_date(e) for e in timeline_entries]
            dates = [d for d in dates if d]  # Filter None

            if dates:
                first_date = min(dates)
                days_since_first = (datetime.now() - first_date).days
                years = days_since_first // 365

                if years >= 1:
                    summary_parts.append(f"Client depuis {first_date.year} ({years} ans)")
                elif days_since_first <= 30:
                    # Nouveau client = première visite il y a moins de 30 jours
                    summary_parts.append("Nouveau client")
                else:
                    # Entre 30 jours et 1 an: afficher les mois
                    months = days_since_first // 30
                    summary_parts.append(f"Client depuis {months} mois")

        # 2. Fréquence de service
        service_freq = self._analyze_service_frequency(timeline_entries)
        if service_freq:
            summary_parts.append(service_freq)

        # 3. Mois préféré
        preferred_month = self._find_preferred_service_month(timeline_entries)
        if preferred_month:
            summary_parts.append(f"Services habituellement en {preferred_month}")

        # 4. Langue préférée
        if comfort_info.get('preferred_language'):
            lang = comfort_info['preferred_language']
            if lang.lower() not in ['français', 'french']:
                summary_parts.append(f"Préfère communiquer en {lang}")

        # 5. Animaux (priorité)
        if comfort_info.get('dog_name') or comfort_info.get('cat_name'):
            animals = []
            if comfort_info.get('dog_name'):
                dog_name = comfort_info['dog_name']
                breed = comfort_info.get('dog_breed', '')
                animals.append(f"chien {dog_name}" + (f" ({breed})" if breed else ""))
            if comfort_info.get('cat_name'):
                animals.append(f"chat {comfort_info['cat_name']}")

            summary_parts.append(f"⚠️ Présence de {' et '.join(animals)}")

        # 6. Tempérament client
        if comfort_info.get('temperament'):
            temperament = comfort_info['temperament'].lower()
            if any(word in temperament for word in ['difficile', 'exigeant', 'pointilleux']):
                summary_parts.append(f"Client {temperament}")

        # 7. Notes spéciales importantes
        if comfort_info.get('special_notes'):
            notes = comfort_info['special_notes']
            important_notes = self._extract_important_notes(notes)
            if important_notes:
                summary_parts.append(important_notes)

        # Joindre avec des points
        return ". ".join(summary_parts) + "." if summary_parts else "Aucun historique disponible."

    def generate_piano_summary(
        self,
        piano_id: str,
        timeline_entries: List[Dict[str, Any]],
        piano_info: Dict[str, Any]
    ) -> str:
        """
        Génère un résumé intelligent du piano.

        Ex: "Steinway D de 1968, accordé 3x/an, climat stable avec Life Saver System.
             Dernière réparation majeure en 2023 (changement de cordes)."

        Args:
            piano_id: ID du piano
            timeline_entries: Entrées de timeline du piano
            piano_info: Infos du piano (marque, modèle, année, etc.)

        Returns:
            Résumé textuel intelligent
        """
        summary_parts = []

        # 1. Info piano de base
        make = piano_info.get('make', 'Piano')
        model = piano_info.get('model', '')
        year = piano_info.get('year', '')

        piano_desc = make
        if model:
            piano_desc += f" {model}"
        if year:
            try:
                age = datetime.now().year - int(year)
                piano_desc += f" de {year} ({age} ans)"
            except:
                piano_desc += f" de {year}"

        summary_parts.append(piano_desc)

        # 2. Life Saver System / Dampp-Chaser
        if piano_info.get('has_dampp_chaser') or piano_info.get('dampp_chaser_installed'):
            summary_parts.append("équipé Life Saver System")

        # 3. Fréquence d'accord
        tuning_freq = self._analyze_service_frequency(timeline_entries)
        if tuning_freq:
            summary_parts.append(tuning_freq)

        # 4. Stabilité climatique
        climate = self._analyze_climate_stability(timeline_entries)
        if climate:
            summary_parts.append(climate)

        # 5. Réparations majeures récentes
        repairs = self._find_major_repairs(timeline_entries)
        if repairs:
            summary_parts.append(repairs)

        # 6. Problèmes récurrents
        issues = self._find_recurring_issues(timeline_entries)
        if issues:
            summary_parts.append(f"⚠️ {issues}")

        # Joindre avec des points
        return ". ".join(summary_parts) + "." if summary_parts else "Aucun historique disponible."

    # === MÉTHODES HELPER ===

    def _analyze_service_frequency(self, timeline_entries: List[Dict[str, Any]]) -> Optional[str]:
        """Analyse la fréquence de service (ex: 'accordé 3x/an')."""
        if not timeline_entries:
            return None

        # Compter les services sur la dernière année
        one_year_ago = datetime.now().replace(year=datetime.now().year - 1)
        recent_services = []

        for entry in timeline_entries:
            entry_type = entry.get('entry_type') or entry.get('type', '')
            if entry_type in ['SERVICE_ENTRY_MANUAL', 'APPOINTMENT', 'service']:
                dt = self._get_entry_date(entry)
                if dt and dt >= one_year_ago:
                    recent_services.append(dt)

        count = len(recent_services)
        if count >= 3:
            return f"accordé {count}x/an"
        elif count == 2:
            return "accordé 2x/an"
        elif count == 1:
            return "accordé 1x/an"

        return None

    def _find_preferred_service_month(self, timeline_entries: List[Dict[str, Any]]) -> Optional[str]:
        """Trouve le mois préféré pour services (si pattern évident)."""
        if not timeline_entries:
            return None

        months = []
        for entry in timeline_entries:
            entry_type = entry.get('entry_type') or entry.get('type', '')
            if entry_type in ['SERVICE_ENTRY_MANUAL', 'APPOINTMENT', 'service']:
                dt = self._get_entry_date(entry)
                if dt:
                    months.append(dt.month)

        if not months:
            return None

        # Trouver le mois le plus fréquent
        month_counts = {}
        for month in months:
            month_counts[month] = month_counts.get(month, 0) + 1

        if not month_counts:
            return None

        most_common_month = max(month_counts, key=month_counts.get)
        count = month_counts[most_common_month]

        # Si au moins 3 services dans ce mois, c'est significatif
        if count >= 3:
            month_names = ['', 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                          'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
            return month_names[most_common_month]

        return None

    def _extract_important_notes(self, notes: str) -> Optional[str]:
        """Extrait les points importants des notes spéciales."""
        if not notes:
            return None

        # Mots-clés importants
        keywords = [
            'attention', 'prudence', 'fragile', 'nerveux', 'difficile',
            'allergique', 'sensible', 'important', 'toujours', 'jamais'
        ]

        # Chercher si notes contiennent mots-clés
        notes_lower = notes.lower()
        has_keywords = any(keyword in notes_lower for keyword in keywords)

        if has_keywords:
            # Limiter à 100 caractères
            if len(notes) > 100:
                return notes[:97] + "..."
            return notes

        return None

    def _analyze_climate_stability(self, timeline_entries: List[Dict[str, Any]]) -> Optional[str]:
        """Analyse la stabilité climatique du piano (humidité/température)."""
        if not timeline_entries:
            return None

        # Extraire mesures d'humidité récentes
        humidity_readings = []

        for entry in timeline_entries:
            metadata = entry.get('metadata', {})
            if isinstance(metadata, dict):
                humidity = metadata.get('humidity') or entry.get('humidity')
                if humidity:
                    try:
                        humidity_readings.append(float(humidity))
                    except:
                        continue

        if len(humidity_readings) >= 3:
            avg_humidity = sum(humidity_readings) / len(humidity_readings)
            variation = max(humidity_readings) - min(humidity_readings)

            if variation <= 5:
                return "climat très stable"
            elif variation <= 10:
                return "climat stable"
            elif variation <= 15:
                return "climat variable"
            else:
                return "⚠️ climat instable"

        return None

    def _find_major_repairs(self, timeline_entries: List[Dict[str, Any]]) -> Optional[str]:
        """Trouve les réparations majeures récentes."""
        if not timeline_entries:
            return None

        major_keywords = [
            'remplacement cordes', 'changement cordes', 'refection',
            'réparation majeure', 'restauration', 'chevilles'
        ]

        recent_repairs = []
        for entry in timeline_entries:
            description = (entry.get('description') or entry.get('details') or '').lower()
            title = (entry.get('title') or entry.get('summary') or '').lower()
            combined = description + ' ' + title

            for keyword in major_keywords:
                if keyword in combined:
                    dt = self._get_entry_date(entry)
                    if dt:
                        # Garder seulement dernières 3 années
                        three_years_ago = datetime.now().replace(year=datetime.now().year - 3)
                        if dt >= three_years_ago:
                            repair_desc = keyword.title()
                            recent_repairs.append(f"{repair_desc} ({dt.year})")
                            break

        if recent_repairs:
            return "Réparations: " + ", ".join(recent_repairs[:2])  # Max 2 réparations

        return None

    def _find_recurring_issues(self, timeline_entries: List[Dict[str, Any]]) -> Optional[str]:
        """Détecte les problèmes récurrents."""
        if not timeline_entries:
            return None

        issue_keywords = [
            'humidité', 'désaccord', 'touches collantes', 'pédale',
            'feutres usés', 'cordes cassées'
        ]

        issue_counts = {}

        for entry in timeline_entries:
            description = (entry.get('description') or entry.get('details') or '').lower()
            title = (entry.get('title') or entry.get('summary') or '').lower()
            combined = description + ' ' + title

            for keyword in issue_keywords:
                if keyword in combined:
                    issue_counts[keyword] = issue_counts.get(keyword, 0) + 1

        # Si un problème revient 3x+, c'est récurrent
        recurring = [issue for issue, count in issue_counts.items() if count >= 3]

        if recurring:
            return f"Problème récurrent: {recurring[0]}"

        return None
