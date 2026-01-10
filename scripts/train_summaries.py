#!/usr/bin/env python3
"""
🎓 Système d'Entraînement des Sommaires - Piano-Tek

Interface locale pour raffiner les formats de sommaires de journée
et d'informations client. Utilise les vraies données de Supabase.

Similaire au système V4 mais avec feedback en langage naturel.

Usage:
    python3 scripts/train_summaries.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from zoneinfo import ZoneInfo

from core.supabase_storage import SupabaseStorage
from modules.assistant.services.queries import GazelleQueries
from modules.travel_fees.calculator import TravelFeeCalculator


class SummaryTrainer:
    """Système d'entraînement pour les formats de sommaires."""

    def __init__(self):
        self.storage = SupabaseStorage()
        self.queries = GazelleQueries(self.storage)
        self.results_file = Path(__file__).parent / 'summary_training_results.json'
        self.results = self._load_results()

        # Initialiser le calculateur de frais (optionnel si API key disponible)
        try:
            self.travel_calculator = TravelFeeCalculator()
            self.travel_fees_enabled = True
        except ValueError:
            print("⚠️ Google Maps API key non trouvée - frais de déplacement désactivés")
            print("   Définir GOOGLE_MAPS_API_KEY dans .env pour activer")
            self.travel_calculator = None
            self.travel_fees_enabled = False

    def _load_results(self) -> List[Dict[str, Any]]:
        """Charge les résultats d'entraînement existants."""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Erreur chargement résultats: {e}")
                return []
        return []

    def _save_results(self):
        """Sauvegarde les résultats d'entraînement."""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Erreur sauvegarde résultats: {e}")

    def _calculate_travel_fees(self, appt: Dict[str, Any], assigned_tech: Optional[str] = None) -> Optional[str]:
        """
        Calcule les frais de déplacement pour un RV.

        Args:
            appt: Dictionnaire du rendez-vous avec adresse
            assigned_tech: Nom du technicien assigné (optionnel)

        Returns:
            Texte formaté avec les frais, ou None si impossible
        """
        if not self.travel_fees_enabled or not self.travel_calculator:
            return None

        # Construire l'adresse de destination
        postal_code = appt.get('client_postal_code', '')
        address = appt.get('client_address', '')
        city = appt.get('client_city', '')

        # Essayer d'abord le code postal (plus fiable pour Google Maps)
        destination = postal_code if postal_code else f"{address}, {city}" if address and city else None

        if not destination:
            return None

        try:
            return self.travel_calculator.format_for_assistant(destination, assigned_tech)
        except Exception as e:
            print(f"⚠️ Erreur calcul frais déplacement: {e}")
            return None

    def _format_appointment_compact(self, appt: Dict[str, Any]) -> str:
        """Format compact: une ligne par RV."""
        time = appt.get('appointment_time', 'N/A')
        client = appt.get('client_name', 'N/A')
        title = appt.get('title', 'N/A')
        return f"{time} - {title} - {client}"

    def _format_appointment_detailed(self, appt: Dict[str, Any]) -> str:
        """Format détaillé: avec adresse, téléphone, contacts et service history."""
        time = appt.get('appointment_time', 'N/A')
        title = appt.get('title', 'N/A')
        client = appt.get('client_name', 'N/A')
        address = appt.get('client_address', '')
        city = appt.get('client_city', '')
        phone = appt.get('client_phone', '')

        lines = [f"🕐 {time} - {title}"]
        lines.append(f"   👤 {client}")
        if address and city:
            lines.append(f"   📍 {address}, {city}")
        if phone:
            lines.append(f"   📞 {phone}")
        
        # Ajouter les contacts associés - TOUS
        associated_contacts = appt.get('associated_contacts', [])
        if associated_contacts:
            print(f"🔍 DEBUG: {len(associated_contacts)} contacts trouvés pour {client}")
            lines.append(f"   👥 Contacts associés ({len(associated_contacts)}):")
            for contact in associated_contacts:
                contact_line = f"      • {contact.get('name', 'N/A')}"
                if contact.get('role'):
                    contact_line += f" ({contact.get('role')})"
                if contact.get('phone'):
                    contact_line += f" - 📞 {contact.get('phone')}"
                if contact.get('email'):
                    contact_line += f" - ✉️ {contact.get('email')}"
                lines.append(contact_line)
        else:
            print(f"🔍 DEBUG: Aucun contact associé pour {client}")
        
        # Ajouter les notes du service history - TOUTES
        service_notes = appt.get('service_history_notes', [])
        if service_notes:
            print(f"🔍 DEBUG: {len(service_notes)} notes de service pour {client}")
            lines.append(f"   📝 Notes service ({len(service_notes)}):")
            for note in service_notes:  # TOUTES les notes, pas seulement 3
                # Nettoyer et tronquer la note (mais garder plus de texte)
                clean_note = note[:500] + '...' if len(note) > 500 else note
                lines.append(f"      • {clean_note}")
        else:
            print(f"🔍 DEBUG: Aucune note de service pour {client}")
        
        # ============================================================
        # AFFICHAGE DES PIANOS AVEC LEURS NOTES
        # ============================================================
        # Les notes des pianos sont souvent très importantes car elles contiennent:
        # - Historique du piano
        # - Problèmes récurrents
        # - Réparations effectuées
        # - Notes techniques importantes
        # On les affiche AVANT les notes client car elles sont généralement plus pertinentes
        pianos = appt.get('pianos', [])
        if pianos:
            print(f"🔍 DEBUG: {len(pianos)} pianos trouvés pour {client}")
            lines.append(f"   🎹 Pianos ({len(pianos)}):")
            for piano in pianos:
                # Construire la ligne d'information du piano
                piano_line = f"      • {piano.get('make', '')} {piano.get('model', '')}".strip()
                if piano.get('serial_number'):
                    piano_line += f" (S/N: {piano.get('serial_number')})"
                if piano.get('year'):
                    piano_line += f" - {piano.get('year')}"
                if piano.get('location'):
                    piano_line += f" - 📍 {piano.get('location')}"
                lines.append(piano_line)
                
                # Afficher les notes du piano (tronquées à 500 caractères pour lisibilité)
                # Les notes complètes sont disponibles dans la modale web
                piano_notes = piano.get('notes', '')
                if piano_notes:
                    notes_display = piano_notes[:500] + '...' if len(piano_notes) > 500 else piano_notes
                    lines.append(f"         📝 {notes_display}")
        else:
            print(f"🔍 DEBUG: Aucun piano trouvé pour {client}")
        
        # Ajouter les notes du client - TOUJOURS afficher si elles existent
        client_notes = appt.get('client_notes', '')
        if client_notes:
            print(f"🔍 DEBUG: Notes client trouvées pour {client}: {len(client_notes)} caractères")
            # AFFICHER TOUTES LES NOTES, pas de filtrage
            lines.append(f"   📋 Notes client:")
            # Afficher les notes complètes (tronquer à 1000 caractères max pour lisibilité)
            notes_display = client_notes[:1000] + '...' if len(client_notes) > 1000 else client_notes
            lines.append(f"      {notes_display}")
        else:
            print(f"🔍 DEBUG: Aucune note client pour {client} (appt keys: {list(appt.keys())})")

        # Ajouter les frais de déplacement si disponibles
        assigned_tech = appt.get('assigned_to_name')  # Nom du technicien assigné
        travel_fees = self._calculate_travel_fees(appt, assigned_tech)
        if travel_fees:
            lines.append("")  # Ligne vide pour séparer
            lines.append(travel_fees)

        return '\n'.join(lines)

    def _format_appointment_v4_style(self, appt: Dict[str, Any]) -> str:
        """Format V4: avec distance, reminders, contacts et service history."""
        time = appt.get('appointment_time', 'N/A')
        title = appt.get('title', 'N/A')
        client = appt.get('client_name', 'N/A')
        address = appt.get('client_address', '')
        city = appt.get('client_city', '')
        notes = appt.get('notes', '')

        lines = [f"{time} - {client}"]
        if address and city:
            lines.append(f"  Adresse: {address}, {city}")
            # Note: Distance Matrix API pourrait être ajouté ici
        lines.append(f"  Service: {title}")
        
        # Ajouter les contacts associés
        associated_contacts = appt.get('associated_contacts', [])
        if associated_contacts:
            for contact in associated_contacts:
                contact_info = contact.get('name', 'N/A')
                if contact.get('role'):
                    contact_info += f" ({contact.get('role')})"
                lines.append(f"  Contact: {contact_info}")
        
        # Ajouter les notes du service history (important pour V4) - TOUTES
        service_notes = appt.get('service_history_notes', [])
        if service_notes:
            lines.append(f"  Service History ({len(service_notes)}):")
            for note in service_notes:  # TOUTES les notes
                clean_note = note[:300] + '...' if len(note) > 300 else note
                lines.append(f"    • {clean_note}")

        # Extraction reminders (comme V4)
        if notes and '!!' in notes:
            reminders = [line.strip() for line in notes.split('\n') if '!!' in line]
            if reminders:
                lines.append(f"  ⚠️ RAPPEL: {', '.join(reminders)}")

        # Ajouter les frais de déplacement (V4 moderne)
        assigned_tech = appt.get('assigned_to_name')
        travel_fees = self._calculate_travel_fees(appt, assigned_tech)
        if travel_fees:
            lines.append("")
            # Format V4: plus simple, juste le montant
            lines.append(f"  💰 Frais déplacement:")
            for line in travel_fees.split('\n'):
                if line.strip() and not line.startswith('💰'):
                    lines.append(f"    {line.strip()}")

        return '\n'.join(lines)

    def generate_day_summary(
        self,
        date: datetime,
        technicien: Optional[str] = None,
        format_style: str = 'compact'
    ) -> Dict[str, Any]:
        """
        Génère un sommaire de journée avec les vraies données.

        Args:
            date: Date du sommaire
            technicien: Nom du technicien (None = tous)
            format_style: 'compact', 'detailed', ou 'v4'

        Returns:
            Dict avec les RV et le sommaire formaté
        """
        # Récupérer les RV du jour
        appointments = self.queries.get_appointments(
            date=date,
            technicien=technicien
        )

        # Enrichir avec infos client/contact
        # RÈGLE SIMPLE: cli_xxx = CLIENT (a timeline, contacts associés, notes)
        #               con_xxx = CONTACT (juste nom, adresse, téléphone)
        print(f"🔍 DEBUG: Enrichissement de {len(appointments)} rendez-vous...")
        for appt in appointments:
            entity_id = appt.get('client_external_id')
            if not entity_id:
                print(f"⚠️ DEBUG: Rendez-vous sans client_external_id: {appt.get('id')}")
                continue
            
            # Détecter par préfixe (plus fiable que _source)
            is_client = entity_id.startswith('cli_')
            is_contact = entity_id.startswith('con_')
            
            # Chercher l'entité
            results = self.queries.search_clients([entity_id])
            if not results:
                appt['client_name'] = 'N/A'
                continue
            
            entity = results[0]
            
            # TRAITEMENT CONTACT (simple, pas d'enrichissement)
            if is_contact:
                first = entity.get('first_name', '')
                last = entity.get('last_name', '')
                appt['client_name'] = f"{first} {last}".strip() or entity.get('name', 'N/A')
                appt['client_address'] = entity.get('address', '')
                appt['client_city'] = entity.get('city', '')
                appt['client_phone'] = entity.get('phone', entity.get('email', ''))
                continue  # STOP ici pour les contacts
            
            # TRAITEMENT CLIENT (avec enrichissement)
            if is_client:
                # Clients ont 'company_name', pas 'name'
                appt['client_name'] = entity.get('company_name', 'N/A')
                appt['client_address'] = entity.get('address', '')
                appt['client_city'] = entity.get('city', '')
                appt['client_phone'] = entity.get('phone', '')
                # Chercher les notes dans toutes les colonnes possibles
                appt['client_notes'] = entity.get('notes', '') or entity.get('note', '') or entity.get('description', '') or entity.get('client_notes', '')
                
                # ============================================================
                # RÉCUPÉRATION DES PIANOS DU CLIENT AVEC LEURS NOTES
                # ============================================================
                # IMPORTANT: Les notes des pianos contiennent souvent des informations
                # cruciales (historique, réparations, problèmes récurrents, etc.)
                # qui doivent être affichées dans les sommaires détaillés.
                # On récupère les pianos séparément pour pouvoir les afficher
                # individuellement avec leurs notes complètes.
                try:
                    import requests
                    pianos_url = f"{self.queries.storage.api_url}/gazelle_pianos?client_external_id=eq.{entity_id}&select=external_id,notes,make,model,serial_number,type,year,location&limit=10"
                    pianos_response = requests.get(pianos_url, headers=self.queries.storage._get_headers())
                    if pianos_response.status_code == 200:
                        pianos = pianos_response.json()
                        print(f"🔍 DEBUG: {len(pianos)} pianos trouvés pour client {entity_id}")
                        
                        # Stocker les pianos avec leurs notes séparément dans l'objet rendez-vous
                        # Cela permet de les afficher individuellement dans les formats détaillés
                        appt['pianos'] = []
                        for piano in pianos:
                            piano_info = {
                                'external_id': piano.get('external_id', ''),
                                'make': piano.get('make', ''),
                                'model': piano.get('model', ''),
                                'serial_number': piano.get('serial_number', ''),
                                'type': piano.get('type', ''),
                                'year': piano.get('year', ''),
                                'location': piano.get('location', ''),
                                'notes': piano.get('notes', '')  # Notes détaillées du piano
                            }
                            # Ajouter seulement si le piano a au moins une info (make, model ou notes)
                            if piano_info['make'] or piano_info['model'] or piano_info['notes']:
                                appt['pianos'].append(piano_info)
                        
                        if appt['pianos']:
                            print(f"✅ {len(appt['pianos'])} pianos avec infos ajoutés pour {entity_id}")
                except Exception as e:
                    print(f"⚠️ Erreur récupération pianos: {e}")
                    import traceback
                    traceback.print_exc()
                
                # DEBUG: Afficher toutes les clés de l'entité pour voir ce qui est disponible
                print(f"🔍 DEBUG: Client {entity_id} - Clés disponibles: {list(entity.keys())}")
                print(f"🔍 DEBUG: Client {entity_id} - notes: {bool(appt['client_notes'])} ({len(appt['client_notes'])} caractères)")
                if appt['client_notes']:
                    print(f"🔍 DEBUG: Extrait notes: {appt['client_notes'][:200]}...")
                
                # ============================================================
                # RÉCUPÉRATION DE L'HISTORIQUE DE SERVICE (TIMELINE)
                # ============================================================
                # IMPORTANT: L'historique de service peut être lié soit au client
                # directement, soit aux pianos du client. On cherche donc dans
                # les deux endroits pour avoir un historique complet.
                # Les notes de service contiennent des informations sur les
                # interventions passées, réparations, problèmes récurrents, etc.
                try:
                    import requests
                    service_notes = []
                    
                    # 1. Chercher timeline pour le client directement
                    # (certaines entrées peuvent être liées au client globalement)
                    print(f"🔍 DEBUG: Recherche timeline pour client {entity_id}...")
                    timeline_entries_client = self.queries.get_timeline_entries(entity_id, entity_type='client', limit=20)
                    print(f"🔍 DEBUG: {len(timeline_entries_client)} entrées timeline client trouvées")
                    
                    # 2. Chercher les pianos du client pour ensuite chercher leur timeline
                    # (la plupart des interventions sont liées à un piano spécifique)
                    print(f"🔍 DEBUG: Recherche pianos pour client {entity_id}...")
                    pianos_url = f"{self.queries.storage.api_url}/gazelle_pianos?client_external_id=eq.{entity_id}&limit=20"
                    pianos_response = requests.get(pianos_url, headers=self.queries.storage._get_headers())
                    pianos = []
                    if pianos_response.status_code == 200:
                        pianos = pianos_response.json()
                        print(f"🔍 DEBUG: {len(pianos)} pianos trouvés pour client {entity_id}")
                    
                    # 3. Chercher timeline pour chaque piano du client
                    # (chaque piano peut avoir son propre historique d'interventions)
                    timeline_entries_pianos = []
                    for piano in pianos:
                        piano_id = piano.get('external_id')
                        if piano_id:
                            print(f"🔍 DEBUG: Recherche timeline pour piano {piano_id}...")
                            piano_timeline = self.queries.get_timeline_entries(piano_id, entity_type='piano', limit=10)
                            timeline_entries_pianos.extend(piano_timeline)
                            print(f"🔍 DEBUG: {len(piano_timeline)} entrées timeline pour piano {piano_id}")
                    
                    # Combiner toutes les entrées (client + tous les pianos)
                    all_timeline_entries = timeline_entries_client + timeline_entries_pianos
                    print(f"🔍 DEBUG: Total {len(all_timeline_entries)} entrées timeline (client + pianos)")
                    
                    # DEBUG: Afficher le contenu des entrées pour diagnostic
                    if all_timeline_entries:
                        print(f"🔍 DEBUG: Première entrée timeline: {all_timeline_entries[0]}")
                    
                    # Extraire les notes de toutes les colonnes possibles
                    # (les colonnes peuvent varier selon la source des données)
                    for e in all_timeline_entries:
                        note = e.get('notes') or e.get('description') or e.get('content') or e.get('note') or e.get('text') or e.get('summary')
                        if note:
                            service_notes.append(str(note))
                    
                    print(f"🔍 DEBUG: {len(service_notes)} notes extraites de {len(all_timeline_entries)} entrées")
                    
                    # Stocker les notes de service (limité à 10 pour éviter la surcharge)
                    if service_notes:
                        appt['service_history_notes'] = service_notes[:10]
                        print(f"✅ {len(service_notes)} notes de service ajoutées pour {entity_id}")
                    else:
                        print(f"ℹ️ Aucune note de service trouvée pour {entity_id}")
                except Exception as e:
                    print(f"⚠️ Erreur timeline {entity_id}: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Contacts associés - SEULEMENT pour clients
                try:
                    import requests
                    print(f"🔍 DEBUG: Recherche contacts associés pour client {entity_id}...")
                    contacts_url = f"{self.queries.storage.api_url}/gazelle_contacts?client_external_id=eq.{entity_id}&limit=10"
                    print(f"🔍 DEBUG: URL contacts = {contacts_url}")
                    contacts_response = requests.get(contacts_url, headers=self.queries.storage._get_headers())
                    print(f"🔍 DEBUG: Status contacts: {contacts_response.status_code}")
                    
                    if contacts_response.status_code == 200:
                        contacts = contacts_response.json()
                        print(f"🔍 DEBUG: {len(contacts)} contacts trouvés dans la réponse")
                        
                        # DEBUG: Afficher le premier contact pour voir sa structure
                        if contacts:
                            print(f"🔍 DEBUG: Premier contact: {contacts[0]}")
                            print(f"🔍 DEBUG: Clés du premier contact: {list(contacts[0].keys())}")
                        
                        if contacts:
                            appt['associated_contacts'] = [
                                {
                                    'name': f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('name', 'N/A'),
                                    'role': c.get('role') or c.get('title') or '',
                                    'phone': c.get('phone') or c.get('telephone') or '',
                                    'email': c.get('email') or ''
                                }
                                for c in contacts[:5]
                            ]
                            print(f"✅ {len(contacts)} contacts associés ajoutés pour {entity_id}")
                        else:
                            print(f"ℹ️ Liste contacts vide pour {entity_id}")
                    else:
                        print(f"⚠️ Erreur HTTP contacts: {contacts_response.status_code}")
                        print(f"⚠️ Réponse complète: {contacts_response.text[:500]}")
                except Exception as e:
                    print(f"⚠️ Erreur contacts associés {entity_id}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Vérifier que les données enrichies sont bien dans l'objet
            has_contacts = bool(appt.get('associated_contacts'))
            has_notes = bool(appt.get('service_history_notes'))
            has_client_notes = bool(appt.get('client_notes'))
            if is_client and (has_contacts or has_notes or has_client_notes):
                print(f"✅ Client {entity_id} enrichi: contacts={has_contacts}, service_notes={has_notes}, client_notes={has_client_notes}")

        # Formater selon le style
        formatter_map = {
            'compact': self._format_appointment_compact,
            'detailed': self._format_appointment_detailed,
            'v4': self._format_appointment_v4_style
        }

        formatter = formatter_map.get(format_style, self._format_appointment_compact)

        # Générer le sommaire
        if not appointments:
            summary = f"📅 {date.strftime('%Y-%m-%d')}\n\nAucun rendez-vous"
            if technicien:
                summary += f" pour {technicien}"
        else:
            tech_name = f" - {technicien}" if technicien else ""
            summary = f"📅 {date.strftime('%Y-%m-%d')}{tech_name}\n"
            summary += f"{'='*50}\n\n"
            summary += f"{len(appointments)} rendez-vous:\n\n"

            for i, appt in enumerate(appointments, 1):
                if format_style == 'compact':
                    summary += f"{i}. {formatter(appt)}\n"
                else:
                    summary += f"{i}. {formatter(appt)}\n\n"

        # Debug: vérifier que les données enrichies sont présentes - DUMP COMPLET
        enriched_count = 0
        for idx, appt in enumerate(appointments):
            has_contacts = bool(appt.get('associated_contacts'))
            has_notes = bool(appt.get('service_history_notes'))
            has_client_notes = bool(appt.get('client_notes'))
            
            print(f"\n{'='*60}")
            print(f"📋 RENDEZ-VOUS #{idx + 1}: {appt.get('client_name', 'N/A')}")
            print(f"{'='*60}")
            print(f"  ID: {appt.get('id')}")
            print(f"  client_external_id: {appt.get('client_external_id')}")
            print(f"  associated_contacts: {has_contacts} ({len(appt.get('associated_contacts', []))} contacts)")
            if has_contacts:
                for c in appt.get('associated_contacts', []):
                    print(f"    - {c}")
            print(f"  service_history_notes: {has_notes} ({len(appt.get('service_history_notes', []))} notes)")
            if has_notes:
                for i, note in enumerate(appt.get('service_history_notes', [])[:2]):
                    print(f"    {i+1}. {note[:100]}...")
            print(f"  client_notes: {has_client_notes} ({len(appt.get('client_notes', ''))} caractères)")
            if has_client_notes:
                print(f"    {appt.get('client_notes', '')[:200]}...")
            print(f"  TOUTES LES CLÉS: {list(appt.keys())}")
            
            if has_contacts or has_notes or has_client_notes:
                enriched_count += 1
        
        print(f"\n📊 RÉSUMÉ: {enriched_count}/{len(appointments)} rendez-vous avec données enrichies")
        print(f"{'='*60}\n")

        return {
            'date': date.isoformat(),
            'technicien': technicien,
            'format_style': format_style,
            'appointments_count': len(appointments),
            'appointments': appointments,
            'summary': summary
        }

    def generate_client_summary(
        self,
        client_id: str,
        format_style: str = 'compact'
    ) -> Dict[str, Any]:
        """
        Génère un sommaire d'informations client.

        Args:
            client_id: ID externe du client
            format_style: 'compact', 'detailed', ou 'v4'

        Returns:
            Dict avec infos client et pianos
        """
        # Récupérer le client ou contact
        # Note: client_id peut être cli_xxx (client) ou con_xxx (contact)
        results = self.queries.search_clients([client_id])
        if not results:
            return {
                'client_id': client_id,
                'found': False,
                'summary': f"❌ Client/Contact {client_id} non trouvé"
            }

        entity = results[0]
        source = entity.get('_source', 'client')
        is_contact = (source == 'contact') or client_id.startswith('con_')
        
        # ENRICHISSEMENT COMPLET (comme dans generate_day_summary)
        # Récupérer les pianos avec leurs notes (seulement pour les clients, pas les contacts)
        pianos = []
        service_notes = []
        associated_contacts = []
        client_notes = ''
        
        if not is_contact:
            # Seulement les clients ont des pianos
            import requests
            
            # 1. Récupérer les pianos avec leurs notes
            pianos_url = f"{self.storage.api_url}/gazelle_pianos?client_external_id=eq.{client_id}&select=external_id,notes,make,model,serial_number,type,year,location&limit=10"
            pianos_response = requests.get(pianos_url, headers=self.storage._get_headers())
            if pianos_response.status_code == 200:
                pianos_raw = pianos_response.json()
                for piano in pianos_raw:
                    piano_info = {
                        'external_id': piano.get('external_id', ''),
                        'make': piano.get('make', ''),
                        'model': piano.get('model', ''),
                        'serial_number': piano.get('serial_number', ''),
                        'type': piano.get('type', ''),
                        'year': piano.get('year', ''),
                        'location': piano.get('location', ''),
                        'notes': piano.get('notes', '')
                    }
                    if piano_info['make'] or piano_info['model'] or piano_info['notes']:
                        pianos.append(piano_info)
            
            # 2. Récupérer les notes du client
            client_notes = entity.get('notes', '') or entity.get('note', '') or entity.get('description', '')
            
            # 3. Récupérer l'historique de service (timeline)
            try:
                timeline_entries_client = self.queries.get_timeline_entries(client_id, entity_type='client', limit=20)
                
                # Chercher aussi les timeline des pianos
                for piano in pianos:
                    piano_id = piano.get('external_id')
                    if piano_id:
                        piano_timeline = self.queries.get_timeline_entries(piano_id, entity_type='piano', limit=10)
                        timeline_entries_client.extend(piano_timeline)
                
                # Extraire les notes
                for e in timeline_entries_client:
                    note = e.get('notes') or e.get('description') or e.get('content') or e.get('note') or e.get('text') or e.get('summary')
                    if note:
                        service_notes.append(str(note))
            except Exception as e:
                print(f"⚠️ Erreur timeline {client_id}: {e}")
            
            # 4. Récupérer les contacts associés
            try:
                contacts_url = f"{self.storage.api_url}/gazelle_contacts?client_external_id=eq.{client_id}&limit=10"
                contacts_response = requests.get(contacts_url, headers=self.storage._get_headers())
                if contacts_response.status_code == 200:
                    contacts = contacts_response.json()
                    if contacts:
                        associated_contacts = [
                            {
                                'name': f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get('name', 'N/A'),
                                'role': c.get('role') or c.get('title') or '',
                                'phone': c.get('phone') or c.get('telephone') or '',
                                'email': c.get('email', '')
                            }
                            for c in contacts[:5]
                        ]
            except Exception as e:
                print(f"⚠️ Erreur contacts associés {client_id}: {e}")

        # Récupérer les derniers RV du client
        # Note: get_appointments ne filtre pas par client_id directement
        # On récupère les RV récents et on filtre après
        from datetime import datetime, timedelta
        recent_appts_all = self.queries.get_appointments(
            date=datetime.now(),
            technicien=None,
            limit=50
        )
        # Filtrer par client_id (peut être cli_xxx ou con_xxx)
        client_appts = [a for a in recent_appts_all if a.get('client_external_id') == client_id]

        # Formater selon le style
        # Note: clients utilisent company_name, contacts utilisent first_name/last_name
        if is_contact:
            first = entity.get('first_name', '')
            last = entity.get('last_name', '')
            entity_name = f"{first} {last}".strip() or 'N/A'
        else:
            entity_name = entity.get('company_name', 'N/A')
        if format_style == 'compact':
            summary = f"👤 {entity_name}\n"
            if entity.get('city'):
                summary += f"📍 {entity.get('city')}\n"
            if is_contact:
                summary += f"📧 Contact (pas de pianos)\n"
            else:
                summary += f"🎹 {len(pianos)} piano(s)\n"
            if client_appts:
                summary += f"📅 Dernier RV: {client_appts[0].get('appointment_date', 'N/A')}"

        elif format_style == 'detailed':
            summary = f"👤 **{entity_name}**\n"
            if is_contact:
                summary += f"📧 Type: Contact\n"
            summary += f"{'='*50}\n\n"
            if entity.get('address'):
                summary += f"📍 {entity.get('address')}, {entity.get('city', '')} {entity.get('postal_code', '')}\n"
            if entity.get('phone'):
                summary += f"📞 {entity.get('phone')}\n"
            if entity.get('email'):
                summary += f"📧 {entity.get('email')}\n"

            if is_contact:
                summary += f"\n📧 **Type:** Contact (pas de pianos associés)\n"
            else:
                summary += f"\n🎹 **Pianos ({len(pianos)}):**\n"
            for piano in pianos:
                summary += f"  - {piano.get('brand', 'N/A')} {piano.get('model', '')}"
                if piano.get('serial_number'):
                    summary += f" (S/N: {piano.get('serial_number')})"
                summary += "\n"

            if client_appts:
                summary += f"\n📅 **Derniers RV:**\n"
                for appt in client_appts[:3]:
                    summary += f"  - {appt.get('appointment_date')}: {appt.get('title', 'N/A')}\n"

        else:  # v4
            summary = f"{entity_name}\n"
            if entity.get('address'):
                summary += f"Adresse: {entity.get('address')}, {entity.get('city', '')}\n"
            
            # Ajouter les contacts associés
            if not is_contact and associated_contacts:
                summary += f"\nContacts associés:\n"
                for contact in associated_contacts:
                    summary += f"  - {contact.get('name', 'N/A')}"
                    if contact.get('role'):
                        summary += f" ({contact.get('role')})"
                    summary += "\n"
            
            # Ajouter les notes du client
            if client_notes:
                summary += f"\nNotes: {client_notes[:300]}{'...' if len(client_notes) > 300 else ''}\n"
            if entity.get('phone'):
                summary += f"Tél: {entity.get('phone')}\n"

            if is_contact:
                summary += f"\nType: Contact (pas de pianos)\n"
            else:
                summary += f"\nPianos: {len(pianos)}\n"
                for piano in pianos:
                    piano_line = f"  • {piano.get('make', 'N/A')} {piano.get('model', '')}"
                    if piano.get('serial_number'):
                        piano_line += f" (S/N: {piano.get('serial_number')})"
                    summary += piano_line + "\n"
                    # Ajouter les notes du piano
                    if piano.get('notes'):
                        summary += f"    Notes: {piano.get('notes')[:200]}{'...' if len(piano.get('notes', '')) > 200 else ''}\n"
            
            # Ajouter l'historique de service
            if service_notes:
                summary += f"\nService History:\n"
                for note in service_notes[:3]:
                    summary += f"  • {note[:200]}{'...' if len(note) > 200 else ''}\n"

        return {
            'client_id': client_id,
            'found': True,
            'entity': entity,
            'is_contact': is_contact,
            'pianos_count': len(pianos) if not is_contact else 0,
            'pianos': pianos if not is_contact else [],
            'recent_appointments': client_appts,
            'format_style': format_style,
            'summary': summary
        }

    def _get_feedback(self, summary_type: str, generated_summary: str) -> Dict[str, Any]:
        """
        Demande feedback en langage naturel sur le sommaire.

        Args:
            summary_type: 'day' ou 'client'
            generated_summary: Le sommaire généré

        Returns:
            Dict avec feedback et note implicite
        """
        print("\n" + "="*70)
        print("💬 FEEDBACK EN LANGAGE NATUREL")
        print("="*70)
        print("\nOptions:")
        print("1. Donner feedback détaillé (recommandé)")
        print("2. Note rapide (1-5)")
        print("3. Passer (pas d'évaluation)")

        choice = input("\nChoix: ").strip()

        if choice == '3':
            return {'mode': 'skipped'}

        elif choice == '2':
            # Mode note rapide
            rating = input("Note (1-5): ").strip()
            comment = input("Commentaire (optionnel): ").strip()

            try:
                rating_int = int(rating)
                if 1 <= rating_int <= 5:
                    return {
                        'mode': 'structured',
                        'rating': rating_int,
                        'comment': comment if comment else None
                    }
            except ValueError:
                pass

            print("⚠️ Note invalide, passé")
            return {'mode': 'skipped'}

        else:  # Mode feedback naturel (défaut)
            print("\n💬 Feedback en langage naturel")
            print("Décris ce que le sommaire devrait contenir/améliorer.")
            print("Exemples:")
            print("  - Tu aurais dû inclure le numéro de téléphone")
            print("  - La réponse devrait mentionner la distance")
            print("  - Manque le temps de déplacement estimé")
            print("\nTape ton feedback (ligne vide pour terminer):")

            feedback_lines = []
            while True:
                line = input()
                if not line:
                    break
                feedback_lines.append(line)

            if not feedback_lines:
                return {'mode': 'skipped'}

            feedback = '\n'.join(feedback_lines)

            # Extraction note implicite
            implicit_rating = self._extract_implicit_rating(feedback)

            return {
                'mode': 'natural',
                'feedback': feedback,
                'implicit_rating': implicit_rating
            }

    def _extract_implicit_rating(self, feedback: str) -> Optional[int]:
        """Extrait une note implicite du feedback naturel."""
        feedback_lower = feedback.lower()

        # Mots positifs (5/5)
        if any(word in feedback_lower for word in ['excellent', 'parfait', 'impeccable', 'super']):
            return 5

        # Mots très bons (4/5)
        if any(word in feedback_lower for word in ['très bon', 'bien', 'bon']):
            return 4

        # Mots moyens (3/5)
        if any(word in feedback_lower for word in ['correct', 'acceptable', 'ok', 'moyen']):
            return 3

        # Mots négatifs (2/5)
        if any(word in feedback_lower for word in ['insuffisant', 'mauvais', 'pas bon', 'manque']):
            return 2

        # Mots très négatifs (1/5)
        if any(word in feedback_lower for word in ['terrible', 'inutilisable', 'incorrect', 'nul']):
            return 1

        return None

    def interactive_training(self):
        """Mode interactif d'entraînement."""
        print("🎓 Système d'Entraînement des Sommaires - Piano-Tek")
        print("="*70)
        print("\nUtilise les vraies données de Supabase pour générer et raffiner")
        print("les formats de sommaires de journée et d'informations client.\n")

        while True:
            print("\n" + "="*70)
            print("MENU PRINCIPAL")
            print("="*70)
            print("\n1. Tester sommaire de journée")
            print("2. Tester sommaire client")
            print("3. Voir historique d'entraînement")
            print("4. Comparer formats côte à côte")
            print("5. Quitter")

            choice = input("\nChoix: ").strip()

            if choice == '1':
                self._train_day_summary()
            elif choice == '2':
                self._train_client_summary()
            elif choice == '3':
                self._show_training_history()
            elif choice == '4':
                self._compare_formats()
            elif choice == '5':
                print("\n👋 À bientôt!")
                break
            else:
                print("❌ Choix invalide")

    def _train_day_summary(self):
        """Entraîne un sommaire de journée."""
        print("\n" + "="*70)
        print("SOMMAIRE DE JOURNÉE")
        print("="*70)

        # Choix de la date
        print("\nChoix de date:")
        print("1. Aujourd'hui")
        print("2. Demain")
        print("3. Date spécifique (YYYY-MM-DD)")

        date_choice = input("\nChoix: ").strip()

        montreal_tz = ZoneInfo('America/Montreal')
        today = datetime.now(montreal_tz)

        if date_choice == '1':
            date = today
        elif date_choice == '2':
            date = today + timedelta(days=1)
        elif date_choice == '3':
            date_str = input("Date (YYYY-MM-DD): ").strip()
            try:
                date = datetime.fromisoformat(date_str).replace(tzinfo=montreal_tz)
            except ValueError:
                print("❌ Date invalide")
                return
        else:
            print("❌ Choix invalide")
            return

        # Choix du technicien
        print("\nTechnicien:")
        print("1. Tous")
        print("2. Nick")
        print("3. Jean-Philippe")
        print("4. Allan")

        tech_choice = input("\nChoix: ").strip()
        tech_map = {'1': None, '2': 'Nick', '3': 'Jean-Philippe', '4': 'Allan'}
        technicien = tech_map.get(tech_choice)

        if technicien is None and tech_choice != '1':
            print("❌ Choix invalide")
            return

        # Choix du format
        print("\nFormat:")
        print("1. Compact (une ligne par RV)")
        print("2. Détaillé (avec adresse et téléphone)")
        print("3. V4 Style (avec reminders)")

        format_choice = input("\nChoix: ").strip()
        format_map = {'1': 'compact', '2': 'detailed', '3': 'v4'}
        format_style = format_map.get(format_choice, 'compact')

        # Générer le sommaire
        print("\n⏳ Génération du sommaire...")
        result = self.generate_day_summary(date, technicien, format_style)

        # Afficher
        print("\n" + "="*70)
        print("SOMMAIRE GÉNÉRÉ")
        print("="*70)
        print(result['summary'])
        print("\n" + "="*70)

        # Demander feedback
        feedback = self._get_feedback('day', result['summary'])

        # Sauvegarder
        if feedback['mode'] != 'skipped':
            training_record = {
                'timestamp': datetime.now().isoformat(),
                'type': 'day_summary',
                'date': result['date'],
                'technicien': result['technicien'],
                'format_style': result['format_style'],
                'appointments_count': result['appointments_count'],
                'summary': result['summary'],
                'feedback': feedback
            }

            self.results.append(training_record)
            self._save_results()
            print("\n✅ Feedback sauvegardé!")

    def _train_client_summary(self):
        """Entraîne un sommaire client."""
        print("\n" + "="*70)
        print("SOMMAIRE CLIENT")
        print("="*70)

        # Rechercher un client
        search = input("\nNom du client à rechercher: ").strip()
        if not search:
            print("❌ Recherche annulée")
            return

        # Chercher clients (search_clients attend une liste)
        clients = self.queries.search_clients([search])

        if not clients:
            print(f"\n❌ Aucun client trouvé pour: {search}")
            return

        # Afficher résultats
        print(f"\n🔍 {len(clients)} résultat(s) trouvé(s) (clients + contacts):\n")
        for i, entity in enumerate(clients, 1):
            source = entity.get('_source', 'client')
            entity_type = "📧 Contact" if source == 'contact' else "👤 Client"
            # Note: clients ont company_name, contacts ont first_name/last_name
            if entity.get('_source') == 'contact':
                first = entity.get('first_name', '')
                last = entity.get('last_name', '')
                name = f"{first} {last}".strip() or 'N/A'
            else:
                name = entity.get('company_name', 'N/A')
            print(f"{i}. {entity_type} {name} - {entity.get('city', 'N/A')}")

        # Sélection
        choice = input("\nNuméro du client: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(clients):
                selected_client = clients[idx]
            else:
                print("❌ Choix invalide")
                return
        except ValueError:
            print("❌ Choix invalide")
            return

        # Choix du format
        print("\nFormat:")
        print("1. Compact")
        print("2. Détaillé")
        print("3. V4 Style")

        format_choice = input("\nChoix: ").strip()
        format_map = {'1': 'compact', '2': 'detailed', '3': 'v4'}
        format_style = format_map.get(format_choice, 'compact')

        # Générer le sommaire
        print("\n⏳ Génération du sommaire...")
        result = self.generate_client_summary(
            selected_client.get('external_id'),
            format_style
        )

        # Afficher
        print("\n" + "="*70)
        print("SOMMAIRE GÉNÉRÉ")
        print("="*70)
        print(result['summary'])
        print("\n" + "="*70)

        # Demander feedback
        feedback = self._get_feedback('client', result['summary'])

        # Sauvegarder
        if feedback['mode'] != 'skipped':
            training_record = {
                'timestamp': datetime.now().isoformat(),
                'type': 'client_summary',
                'client_id': result['client_id'],
                'client_name': result.get('client', {}).get('name'),
                'format_style': result['format_style'],
                'pianos_count': result['pianos_count'],
                'summary': result['summary'],
                'feedback': feedback
            }

            self.results.append(training_record)
            self._save_results()
            print("\n✅ Feedback sauvegardé!")

    def _show_training_history(self):
        """Affiche l'historique d'entraînement."""
        if not self.results:
            print("\n📭 Aucun résultat d'entraînement")
            return

        print("\n" + "="*70)
        print(f"HISTORIQUE D'ENTRAÎNEMENT ({len(self.results)} sessions)")
        print("="*70)

        for i, result in enumerate(reversed(self.results), 1):
            print(f"\n{i}. [{result['timestamp'][:19]}] {result['type']}")
            print(f"   Format: {result['format_style']}")

            feedback = result.get('feedback', {})
            if feedback.get('mode') == 'natural':
                rating = feedback.get('implicit_rating')
                if rating:
                    stars = '⭐' * rating
                    print(f"   Note implicite: {stars} ({rating}/5)")
                print(f"   💬 Feedback:")
                for line in feedback['feedback'].split('\n'):
                    print(f"      {line}")
            elif feedback.get('mode') == 'structured':
                rating = feedback.get('rating')
                stars = '⭐' * rating
                print(f"   Note: {stars} ({rating}/5)")
                if feedback.get('comment'):
                    print(f"   💬 {feedback['comment']}")

    def _compare_formats(self):
        """Compare les 3 formats côte à côte."""
        print("\n" + "="*70)
        print("COMPARAISON DE FORMATS")
        print("="*70)

        print("\nQue veux-tu comparer?")
        print("1. Sommaire de journée")
        print("2. Sommaire client")

        choice = input("\nChoix: ").strip()

        if choice == '1':
            # Date
            montreal_tz = ZoneInfo('America/Montreal')
            date = datetime.now(montreal_tz)

            print("\n⏳ Génération des 3 formats...")

            compact = self.generate_day_summary(date, None, 'compact')
            detailed = self.generate_day_summary(date, None, 'detailed')
            v4_style = self.generate_day_summary(date, None, 'v4')

            print("\n" + "="*70)
            print("FORMAT COMPACT")
            print("="*70)
            print(compact['summary'])

            print("\n" + "="*70)
            print("FORMAT DÉTAILLÉ")
            print("="*70)
            print(detailed['summary'])

            print("\n" + "="*70)
            print("FORMAT V4")
            print("="*70)
            print(v4_style['summary'])

        elif choice == '2':
            # Chercher un client
            search = input("\nNom du client: ").strip()
            clients = self.queries.search_clients([search])

            if not clients:
                print(f"\n❌ Aucun client trouvé")
                return

            client_id = clients[0].get('external_id')

            print("\n⏳ Génération des 3 formats...")

            compact = self.generate_client_summary(client_id, 'compact')
            detailed = self.generate_client_summary(client_id, 'detailed')
            v4_style = self.generate_client_summary(client_id, 'v4')

            print("\n" + "="*70)
            print("FORMAT COMPACT")
            print("="*70)
            print(compact['summary'])

            print("\n" + "="*70)
            print("FORMAT DÉTAILLÉ")
            print("="*70)
            print(detailed['summary'])

            print("\n" + "="*70)
            print("FORMAT V4")
            print("="*70)
            print(v4_style['summary'])

        else:
            print("❌ Choix invalide")


def main():
    """Point d'entrée principal."""
    trainer = SummaryTrainer()
    trainer.interactive_training()


if __name__ == '__main__':
    main()
