#!/usr/bin/env python3
"""
Service de synchronisation Place des Arts ↔ Gazelle.

Synchronise les demandes Place des Arts avec les rendez-vous Gazelle:
- Trouve les RV Gazelle correspondant aux demandes PDA
- Lie les demandes aux RV (appointment_id)
- Met à jour les statuts
"""

import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Ajouter le projet au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient

logger = logging.getLogger(__name__)


def extract_parking_amount(text: str) -> Optional[str]:
    """
    Extrait le montant de stationnement depuis un texte de description de service Gazelle.

    Formats détectés (insensible à la casse):
    - "stationnement : 9$"  / "stationnement: 9,50$"
    - "Stationnement 9"     / "stationnement 12.50"
    - "stat. 9$"            / "stat 9"  / "stat: 9$"
    - "parking: 9$"         / "parking 9"
    - Montants avec virgule ou point comme séparateur décimal

    Retourne le montant sous forme de string (ex: "9.00") ou None si non trouvé.
    """
    if not text:
        return None

    # Pattern pour les variantes du mot "stationnement"
    # stat, stat., statio, stationnement, parking
    # IMPORTANT: \b avant "stat" pour ne pas matcher "thermostat", "humidistat", "constat", etc.
    keyword = r'(?:stationnement|stationn\w*|\bstat\.?|parking)'

    # Pattern pour le montant: nombre avec optionnel décimales (virgule ou point) et optionnel $
    amount = r'(\d+(?:[.,]\d{1,2})?)\s*\$?'

    # Chercher: keyword + séparateurs optionnels + montant
    pattern = rf'{keyword}\s*[:=\-]?\s*{amount}'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        value_str = match.group(1).replace(',', '.')
        try:
            value = float(value_str)
            if value > 0:
                return f"{value:.2f}"
        except ValueError:
            pass

    return None


class GazelleSyncService:
    """Service de synchronisation Place des Arts avec Gazelle."""
    
    # Client ID Place des Arts
    PDA_CLIENT_ID = "cli_HbEwl9rN11pSuDEU"
    
    def __init__(self, storage: Optional[SupabaseStorage] = None):
        """Initialise le service de synchronisation."""
        self.storage = storage or SupabaseStorage()
    
    def sync_requests_with_gazelle(
        self,
        request_ids: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Synchronise les demandes PDA avec les RV Gazelle.
        
        Args:
            request_ids: Liste des IDs de demandes à synchroniser (None = toutes)
            dry_run: Si True, ne fait que vérifier sans mettre à jour
        
        Returns:
            {
                "success": True/False,
                "checked": nombre de demandes vérifiées,
                "matched": nombre de correspondances trouvées,
                "updated": nombre de demandes mises à jour,
                "details": [...],
                "warnings": [...]
            }
        """
        try:
            print(f"\n{'='*70}")
            print(f"🔄 SYNCHRONISATION PLACE DES ARTS ↔ GAZELLE")
            print(f"   Mode: {'DRY RUN (simulation)' if dry_run else 'MISE À JOUR RÉELLE'}")
            print(f"{'='*70}\n")
            
            # 1. Récupérer les demandes PDA
            if request_ids:
                requests = self._get_requests_by_ids(request_ids)
            else:
                # Toutes les demandes sans appointment_id
                requests = self._get_unlinked_requests()
            
            if not requests:
                return {
                    "success": True,
                    "checked": 0,
                    "matched": 0,
                    "updated": 0,
                    "message": "Aucune demande à synchroniser",
                    "details": [],
                    "warnings": []
                }
            
            print(f"📋 {len(requests)} demande(s) à vérifier\n")
            
            # 2. Récupérer tous les RV Gazelle pour Place des Arts
            gazelle_appointments = self._get_gazelle_appointments()
            
            print(f"📅 {len(gazelle_appointments)} RV Gazelle chargés\n")
            
            # 3. Matcher les demandes avec les RV
            matched_count = 0
            updated_count = 0
            details = []
            warnings = []
            
            for request in requests:
                request_id = request.get('id')
                appointment_date = request.get('appointment_date')
                room = request.get('room', '')
                time_str = request.get('time', '')
                
                # Chercher un RV correspondant
                matched_apt = self._find_matching_appointment(
                    request,
                    gazelle_appointments
                )
                
                if matched_apt:
                    matched_count += 1
                    apt_id = matched_apt.get('external_id')
                    apt_title = matched_apt.get('title', 'N/A')
                    # Le champ s'appelle 'technicien' dans gazelle_appointments (c'est l'ID Gazelle)
                    apt_technician = matched_apt.get('technicien')
                    is_real_tech = apt_technician in self.REAL_TECHNICIAN_IDS

                    print(f"✅ Match trouvé:")
                    print(f"   Demande: {appointment_date} {time_str} - Salle {room}")
                    print(f"   RV Gazelle: {apt_id} - {apt_title}")
                    if apt_technician:
                        if is_real_tech:
                            print(f"   Technicien: {apt_technician}")
                        else:
                            print(f"   Technicien: À attribuer (pas encore assigné)")

                    details.append({
                        "request_id": request_id,
                        "appointment_id": apt_id,
                        "appointment_title": apt_title,
                        "technician_id": apt_technician if is_real_tech else None,
                        "matched": True,
                        "has_real_technician": is_real_tech
                    })

                    # Mettre à jour si pas dry_run
                    if not dry_run:
                        success = self._link_request_to_appointment(
                            request_id,
                            apt_id,
                            apt_technician
                        )
                        if success:
                            updated_count += 1
                            if is_real_tech:
                                print(f"   💾 Statut: CREATED_IN_GAZELLE (tech: {apt_technician})")
                            else:
                                print(f"   💾 RV lié avec 'À attribuer' (statut: CREATED_IN_GAZELLE)")
                        else:
                            warnings.append(f"Erreur mise à jour demande {request_id}")
                    print()
                else:
                    print(f"⚠️  Pas de match:")
                    print(f"   Demande: {appointment_date} {time_str} - Salle {room}")
                    
                    details.append({
                        "request_id": request_id,
                        "appointment_id": None,
                        "matched": False,
                        "reason": "Aucun RV Gazelle correspondant trouvé"
                    })
                    print()
            
            # 4. Vérifier les demandes déjà liées pour mise à jour statut COMPLETED
            # ET synchroniser les techniciens depuis Gazelle (source de vérité)
            completed_count = 0
            tech_sync_count = 0
            if not request_ids:  # Seulement en mode "sync all"
                linked_requests = self._get_linked_not_completed_requests()
                if linked_requests:
                    print(f"\n{'='*70}")
                    print(f"🔍 VÉRIFICATION DES RV COMPLÉTÉS ET SYNCHRONISATION TECHNICIENS")
                    print(f"{'='*70}")
                    print(f"   {len(linked_requests)} demande(s) liées à vérifier\n")

                    # Créer un index des RV Gazelle par external_id
                    gazelle_by_id = {apt.get('external_id'): apt for apt in gazelle_appointments}

                    for request in linked_requests:
                        request_id = request.get('id')
                        apt_id = request.get('appointment_id')
                        appointment_date = request.get('appointment_date', '')[:10] if request.get('appointment_date') else ''
                        room = request.get('room', '')
                        current_tech = request.get('technician_id')

                        # Trouver le RV Gazelle correspondant
                        gazelle_apt = gazelle_by_id.get(apt_id)
                        if gazelle_apt:
                            gazelle_status = gazelle_apt.get('status', '').upper()
                            gazelle_tech = gazelle_apt.get('technicien')
                            
                            # Synchroniser le technicien depuis Gazelle (source de vérité)
                            if gazelle_tech and current_tech != gazelle_tech:
                                if not dry_run:
                                    try:
                                        self.storage.client.table('place_des_arts_requests')\
                                            .update({
                                                'technician_id': gazelle_tech,
                                                'updated_at': datetime.now().isoformat()
                                            })\
                                            .eq('id', request_id)\
                                            .execute()
                                        tech_sync_count += 1
                                        tech_name = 'À attribuer' if gazelle_tech == 'usr_HihJsEgkmpTEziJo' else gazelle_tech
                                        print(f"🔄 Technicien synchronisé: {appointment_date} - {room} → {tech_name}")
                                    except Exception as e:
                                        logger.warning(f"Erreur sync technicien pour {request_id}: {e}")
                            
                            # Vérifier si complété
                            if gazelle_status in ('COMPLETE', 'COMPLETED'):
                                print(f"✅ RV complété trouvé:")
                                print(f"   Demande: {appointment_date} - Salle {room}")
                                print(f"   RV Gazelle: {apt_id}")

                                # Extraire le montant de stationnement depuis la description Gazelle
                                parking_amount = self._extract_parking_from_appointment(gazelle_apt)
                                if parking_amount:
                                    print(f"   🅿️ Stationnement détecté: {parking_amount} $")

                                if not dry_run:
                                    success = self._update_request_status(
                                        request_id, 'COMPLETED', parking=parking_amount
                                    )
                                    if success:
                                        completed_count += 1
                                        print(f"   💾 Statut mis à jour: COMPLETED")
                                    else:
                                        warnings.append(f"Erreur mise à jour statut demande {request_id}")
                                print()

                    if completed_count > 0 or tech_sync_count > 0 or dry_run:
                        if tech_sync_count > 0:
                            print(f"   {tech_sync_count} technicien(s) synchronisé(s) depuis Gazelle")
                        if completed_count > 0:
                            print(f"   {completed_count} demande(s) marquée(s) comme complétée(s)")
                        print()

            print(f"\n{'='*70}")
            print(f"📊 RÉSULTAT SYNCHRONISATION")
            print(f"{'='*70}")
            print(f"   Demandes vérifiées: {len(requests)}")
            print(f"   Correspondances trouvées: {matched_count}")
            if not dry_run:
                print(f"   Demandes mises à jour: {updated_count}")
                print(f"   Demandes complétées: {completed_count}")
            print(f"{'='*70}\n")

            return {
                "success": True,
                "checked": len(requests),
                "matched": matched_count,
                "updated": updated_count if not dry_run else 0,
                "completed": completed_count if not dry_run else 0,
                "message": f"{matched_count}/{len(requests)} correspondances, {completed_count} complétées",
                "details": details,
                "warnings": warnings,
                "dry_run": dry_run
            }
            
        except Exception as e:
            logger.error(f"Erreur synchronisation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "checked": 0,
                "matched": 0,
                "updated": 0,
                "details": [],
                "warnings": []
            }
    
    def _get_unlinked_requests(self) -> List[Dict]:
        """Récupère toutes les demandes sans appointment_id."""
        try:
            result = self.storage.client.table('place_des_arts_requests')\
                .select('*')\
                .is_('appointment_id', 'null')\
                .order('appointment_date', desc=False)\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération demandes: {e}")
            return []

    def _get_linked_not_completed_requests(self) -> List[Dict]:
        """Récupère les demandes liées à un RV Gazelle mais pas encore complétées."""
        try:
            result = self.storage.client.table('place_des_arts_requests')\
                .select('*')\
                .not_.is_('appointment_id', 'null')\
                .neq('status', 'COMPLETED')\
                .neq('status', 'BILLED')\
                .order('appointment_date', desc=False)\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération demandes liées: {e}")
            return []
    
    def _get_requests_by_ids(self, request_ids: List[str]) -> List[Dict]:
        """Récupère des demandes spécifiques par leurs IDs."""
        try:
            result = self.storage.client.table('place_des_arts_requests')\
                .select('*')\
                .in_('id', request_ids)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération demandes: {e}")
            return []
    
    def _get_gazelle_appointments(self) -> List[Dict]:
        """Récupère tous les RV Gazelle pour Place des Arts."""
        try:
            # Récupérer les RV des 60 derniers jours
            # Utiliser appointment_date (pas start_datetime qui peut être NULL)
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

            result = self.storage.client.table('gazelle_appointments')\
                .select('*')\
                .eq('client_external_id', self.PDA_CLIENT_ID)\
                .gte('appointment_date', cutoff_date)\
                .order('appointment_date')\
                .execute()

            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erreur récupération RV Gazelle: {e}")
            return []
    
    def _find_matching_appointment(
        self,
        request: Dict,
        gazelle_appointments: List[Dict]
    ) -> Optional[Dict]:
        """
        Trouve un RV Gazelle correspondant à une demande PDA.

        Stratégie STRICTE — exige une correspondance solide basée sur
        plusieurs signaux indépendants pour éviter les amalgames entre
        RV distincts du même jour.

        Signaux évalués (chacun compte 1 point, 0 ou 1 — pas cumulable):
          - S1 SALLE    : salle (ex. "SALLE E") présente dans titre/location/desc
          - S2 FOR_WHO  : artiste/orchestre (ex. "ONJ", "OSM") présent dans le titre
          - S3 HEURE    : heure ±1h de l'heure demandée
          - S4 PIANO    : modèle/marque du piano mentionné dans le titre/notes

        Règles de décision:
          1. Même jour OBLIGATOIRE
          2. Score minimum REQUIS = 2 signaux indépendants
             (ex: salle + heure, ou salle + for_who, etc.)
          3. Le meilleur candidat doit AVOIR AU MOINS 1 POINT D'AVANCE
             sur le second candidat du même jour (sinon ambigu → rejet)
          4. Si plusieurs RV du même jour ont le même score max → rejet
             (ambiguïté — nécessite intervention humaine)
        """
        import re

        request_date_str = request.get('appointment_date')
        if not request_date_str:
            return None

        request_date = request_date_str[:10] if isinstance(request_date_str, str) else str(request_date_str)[:10]
        request_id_short = str(request.get('id', ''))[:8]

        request_time = request.get('time', '') or ''
        request_room = (request.get('room', '') or '').upper().strip()
        request_for_who = (request.get('for_who', '') or '').upper().strip()
        request_piano = (request.get('piano', '') or '').upper().strip()

        # Parser l'heure demandée (formats: "8h", "14h30", "avant 10h", "9h-11h", etc.)
        request_hour = None
        if request_time:
            hr_match = re.search(r'(\d{1,2})\s*H', request_time.upper())
            if hr_match:
                request_hour = int(hr_match.group(1))

        # Filtrer les RV du même jour
        same_day_appointments = []
        for apt in gazelle_appointments:
            apt_date_str = apt.get('appointment_date')
            if not apt_date_str:
                apt_datetime_str = apt.get('start_datetime')
                if apt_datetime_str:
                    apt_date_str = apt_datetime_str[:10]
                else:
                    continue

            apt_date_str = apt_date_str[:10] if apt_date_str else ''

            if apt_date_str == request_date:
                apt_hour = None
                apt_time_str = apt.get('appointment_time', '')
                if apt_time_str:
                    try:
                        apt_hour = int(str(apt_time_str).split(':')[0])
                    except Exception:
                        pass
                same_day_appointments.append((apt, apt_hour))

        if not same_day_appointments:
            return None

        def _word_in(needle: str, haystack: str) -> bool:
            """Recherche 'needle' dans 'haystack' avec frontières de mots."""
            if not needle or not haystack:
                return False
            return re.search(r'\b' + re.escape(needle) + r'\b', haystack) is not None

        # Extraire les mots-clés du piano (marques/modèles courants)
        piano_keywords = []
        if request_piano:
            for kw in ('STEINWAY', 'YAMAHA', 'BALDWIN', 'BÖSENDORFER', 'BOSENDORFER', 'FAZIOLI', 'KAWAI'):
                if kw in request_piano:
                    piano_keywords.append(kw)
            # Modèle "D", "B", "M", "C3", etc. après la marque — on ne les utilise pas
            # comme critère car trop courts et ambigus.

        # Extraire les mots-clés de for_who (≥ 3 caractères pour ignorer "DE", "LA", etc.)
        for_who_words = [w for w in re.findall(r'[A-ZÉÈÊÀÂÔÙÏ]{3,}', request_for_who)]

        # Évaluer chaque candidat
        scored = []  # liste de (score, signals_list, apt)

        for apt, apt_hour in same_day_appointments:
            apt_title = (apt.get('title', '') or '').upper()
            apt_location = (apt.get('location', '') or '').upper()
            apt_description = (apt.get('description', '') or '').upper()
            apt_notes = (apt.get('notes', '') or '').upper()
            apt_all = f"{apt_title} {apt_location} {apt_description} {apt_notes}"

            signals = []

            # S1 — Salle
            if request_room and (_word_in(request_room, apt_title)
                                 or _word_in(request_room, apt_location)
                                 or _word_in(request_room, apt_description)):
                signals.append('SALLE')

            # S2 — For_who / artiste
            if for_who_words:
                if any(_word_in(w, apt_title) or _word_in(w, apt_description) for w in for_who_words):
                    signals.append('FOR_WHO')

            # S3 — Heure (tolérance stricte ±1h)
            if request_hour is not None and apt_hour is not None:
                if abs(apt_hour - request_hour) <= 1:
                    signals.append('HEURE')

            # S4 — Piano (marque dans titre/desc)
            if piano_keywords:
                if any(kw in apt_all for kw in piano_keywords):
                    signals.append('PIANO')

            score = len(signals)
            scored.append((score, signals, apt))

        # Trier par score décroissant
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_signals, best_match = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0

        # Règle 2: exiger au moins 2 signaux indépendants
        if best_score < 2:
            logger.info(
                f"[MATCH REJETÉ] req={request_id_short} date={request_date} "
                f"room='{request_room}' for_who='{request_for_who}' time='{request_time}' — "
                f"score insuffisant ({best_score}/2 signaux: {best_signals})"
            )
            return None

        # Règle 3+4: exiger une marge ≥1 sur le 2e candidat (pas d'ambiguïté)
        if best_score == second_score:
            # Lister les candidats ex-aequo pour diagnostic
            tied = [a for s, _, a in scored if s == best_score]
            tied_titles = [f"{a.get('external_id', '?')}:{(a.get('title') or '')[:40]}" for a in tied]
            logger.warning(
                f"[MATCH AMBIGU] req={request_id_short} date={request_date} "
                f"room='{request_room}' for_who='{request_for_who}' time='{request_time}' — "
                f"{len(tied)} RV ex-aequo à {best_score} signaux ({best_signals}): "
                f"{tied_titles} — aucun lien créé (intervention humaine requise)"
            )
            return None

        logger.info(
            f"[MATCH OK] req={request_id_short} → apt={best_match.get('external_id')} "
            f"(score={best_score}, signaux={best_signals}, "
            f"marge+{best_score - second_score})"
        )
        return best_match

    def _find_matching_appointment_for_orphan(
        self,
        gazelle_apt: Dict,
        pda_requests: List[Dict]
    ) -> Optional[Dict]:
        """
        Vérifie si un RV Gazelle correspond à une demande PDA existante
        (sans lien appointment_id). Matching inverse strict: on part du RV
        Gazelle et on cherche une demande correspondante.

        Utilise le même moteur de signaux que _find_matching_appointment()
        pour garantir la symétrie et éviter les amalgames. Pour accepter
        un lien, exige ≥ 2 signaux et une marge ≥ 1 sur le 2e candidat.
        """
        apt_date_str = gazelle_apt.get('appointment_date', '')
        if not apt_date_str:
            return None

        apt_ext_id = gazelle_apt.get('external_id', '?')

        # Réutiliser le moteur de scoring: pour chaque demande candidate
        # du même jour, calculer son score contre CE RV Gazelle, puis
        # appliquer les mêmes règles (≥2 signaux, marge ≥1).
        candidates = []
        for req in pda_requests:
            if req.get('appointment_id'):
                continue

            req_date_str = req.get('appointment_date', '')
            if not req_date_str:
                continue
            if str(req_date_str)[:10] != apt_date_str[:10]:
                continue

            # Appeler le matcher sur une liste d'un seul RV pour obtenir
            # le score — mais on veut le score brut, pas le filtrage final.
            score, signals = self._score_request_vs_appointment(req, gazelle_apt)
            candidates.append((score, signals, req))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_signals, best_req = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else 0

        if best_score < 2:
            return None

        if best_score == second_score:
            logger.warning(
                f"[ORPHAN AMBIGU] apt={apt_ext_id} — "
                f"plusieurs demandes ex-aequo à {best_score} signaux — non lié"
            )
            return None

        logger.info(
            f"[ORPHAN MATCH] apt={apt_ext_id} → req={str(best_req.get('id', ''))[:8]} "
            f"(score={best_score}, signaux={best_signals})"
        )
        return best_req

    def _score_request_vs_appointment(
        self,
        request: Dict,
        apt: Dict
    ) -> tuple:
        """
        Calcule le score (nombre de signaux indépendants) entre une
        demande PDA et un RV Gazelle. Retourne (score, liste_signaux).

        Signaux: SALLE, FOR_WHO, HEURE, PIANO — voir _find_matching_appointment().
        """
        import re

        request_time = request.get('time', '') or ''
        request_room = (request.get('room', '') or '').upper().strip()
        request_for_who = (request.get('for_who', '') or '').upper().strip()
        request_piano = (request.get('piano', '') or '').upper().strip()

        request_hour = None
        if request_time:
            hr_match = re.search(r'(\d{1,2})\s*H', request_time.upper())
            if hr_match:
                request_hour = int(hr_match.group(1))

        apt_hour = None
        apt_time_str = apt.get('appointment_time', '')
        if apt_time_str:
            try:
                apt_hour = int(str(apt_time_str).split(':')[0])
            except Exception:
                pass

        apt_title = (apt.get('title', '') or '').upper()
        apt_location = (apt.get('location', '') or '').upper()
        apt_description = (apt.get('description', '') or '').upper()
        apt_notes = (apt.get('notes', '') or '').upper()
        apt_all = f"{apt_title} {apt_location} {apt_description} {apt_notes}"

        def _word_in(needle: str, haystack: str) -> bool:
            if not needle or not haystack:
                return False
            return re.search(r'\b' + re.escape(needle) + r'\b', haystack) is not None

        signals = []

        if request_room and (_word_in(request_room, apt_title)
                             or _word_in(request_room, apt_location)
                             or _word_in(request_room, apt_description)):
            signals.append('SALLE')

        for_who_words = re.findall(r'[A-ZÉÈÊÀÂÔÙÏ]{3,}', request_for_who)
        if for_who_words and any(_word_in(w, apt_title) or _word_in(w, apt_description)
                                  for w in for_who_words):
            signals.append('FOR_WHO')

        if request_hour is not None and apt_hour is not None:
            if abs(apt_hour - request_hour) <= 1:
                signals.append('HEURE')

        piano_keywords = []
        if request_piano:
            for kw in ('STEINWAY', 'YAMAHA', 'BALDWIN', 'BÖSENDORFER',
                       'BOSENDORFER', 'FAZIOLI', 'KAWAI'):
                if kw in request_piano:
                    piano_keywords.append(kw)
        if piano_keywords and any(kw in apt_all for kw in piano_keywords):
            signals.append('PIANO')

        return (len(signals), signals)

    # IDs des vrais techniciens (pas "À attribuer")
    # Inclure aussi les IDs alternatifs qui correspondent aux mêmes techniciens
    REAL_TECHNICIAN_IDS = {
        'usr_HcCiFk7o0vZ9xAI0',  # Nick
        'usr_ofYggsCDt2JAVeNP',  # Allan
        'usr_ReUSmIJmBF86ilY1',  # JP (ID standard)
        'usr_QmEpdeM2xMgZVkDS',  # JP (ID alternatif si différent dans Gazelle)
    }
    
    # Mapping pour normaliser les IDs alternatifs vers les IDs standards
    TECH_ID_NORMALIZATION = {
        'usr_QmEpdeM2xMgZVkDS': 'usr_ReUSmIJmBF86ilY1',  # ID alternatif JP → ID standard JP
    }
    
    def _normalize_technician_id(self, tech_id: Optional[str]) -> Optional[str]:
        """Normalise un ID technicien (convertit les IDs alternatifs vers les standards)."""
        if not tech_id:
            return None
        return self.TECH_ID_NORMALIZATION.get(tech_id, tech_id)

    def _link_request_to_appointment(
        self,
        request_id: str,
        appointment_id: str,
        technician_id: Optional[str] = None,
        parking: Optional[str] = None
    ) -> bool:
        """Lie une demande PDA à un RV Gazelle et met à jour le technicien."""
        try:
            # Vérifier si c'est un vrai technicien (pas "À attribuer")
            is_real_technician = technician_id in self.REAL_TECHNICIAN_IDS

            update_data = {
                'appointment_id': appointment_id,
                'updated_at': datetime.now().isoformat()
            }

            # Toujours mettre à jour le technicien depuis Gazelle (source de vérité)
            if technician_id:
                update_data['technician_id'] = technician_id

            # Marquer "CREATED_IN_GAZELLE" si le RV existe (même avec "À attribuer")
            update_data['status'] = 'CREATED_IN_GAZELLE'

            # Mettre à jour le stationnement si détecté
            if parking is not None:
                update_data['parking'] = parking

            result = self.storage.client.table('place_des_arts_requests')\
                .update(update_data)\
                .eq('id', request_id)\
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Erreur lien demande {request_id}: {e}")
            return False

    def _extract_parking_from_appointment(self, gazelle_apt: Dict) -> Optional[str]:
        """
        Extrait le montant de stationnement depuis la description/notes d'un RV Gazelle
        ET depuis les timeline entries (notes de service) du même jour.

        Cherche dans:
        1. Les champs 'description', 'notes' et 'title' du RV
        2. Les gazelle_timeline_entries du même jour et même client (notes de service)
        """
        # 1. Chercher dans les champs du RV Gazelle
        for field in ('description', 'notes', 'title'):
            text = gazelle_apt.get(field) or ''
            amount = extract_parking_amount(text)
            if amount:
                return amount

        # 2. Chercher dans les timeline entries (notes de service du technicien)
        apt_date = gazelle_apt.get('appointment_date')
        apt_ext_id = gazelle_apt.get('external_id')
        if apt_date:
            try:
                # Récupérer les timeline entries du même jour pour le client PDA
                date_str = apt_date[:10] if isinstance(apt_date, str) else str(apt_date)[:10]
                result = self.storage.client.table('gazelle_timeline_entries')\
                    .select('title, description')\
                    .eq('client_id', self.PDA_CLIENT_ID)\
                    .gte('occurred_at', f"{date_str}T00:00:00")\
                    .lte('occurred_at', f"{date_str}T23:59:59")\
                    .execute()

                if result.data:
                    for entry in result.data:
                        for field in ('title', 'description'):
                            text = entry.get(field) or ''
                            amount = extract_parking_amount(text)
                            if amount:
                                logger.info(f"🅿️ Stationnement trouvé dans timeline entry: {amount}$ (RV {apt_ext_id})")
                                return amount
            except Exception as e:
                logger.warning(f"Erreur lecture timeline entries pour parking (RV {apt_ext_id}): {e}")

        return None

    def _update_request_status(self, request_id: str, status: str, parking: Optional[str] = None) -> bool:
        """Met à jour le statut d'une demande PDA (et optionnellement le stationnement)."""
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            if parking is not None:
                update_data['parking'] = parking

            result = self.storage.client.table('place_des_arts_requests')\
                .update(update_data)\
                .eq('id', request_id)\
                .execute()

            return bool(result.data)
        except Exception as e:
            logger.error(f"Erreur mise à jour statut demande {request_id}: {e}")
            return False


# Fonction helper pour utilisation depuis CLI
def sync_place_des_arts(dry_run: bool = False) -> Dict:
    """
    Synchronise toutes les demandes Place des Arts avec Gazelle.
    
    Args:
        dry_run: Si True, simulation sans mise à jour
    
    Returns:
        Résultat de la synchronisation
    """
    service = GazelleSyncService()
    return service.sync_requests_with_gazelle(dry_run=dry_run)


if __name__ == "__main__":
    # Test du service
    import argparse
    
    parser = argparse.ArgumentParser(description="Synchroniser Place des Arts avec Gazelle")
    parser.add_argument('--dry-run', action='store_true', help='Simulation sans mise à jour')
    args = parser.parse_args()
    
    result = sync_place_des_arts(dry_run=args.dry_run)
    
    print(f"\n✅ Synchronisation terminée")
    print(f"   Résultat: {result.get('message')}")
