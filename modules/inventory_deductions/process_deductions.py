#!/usr/bin/env python3
"""
Module de traitement des déductions d'inventaire automatiques.

Détecte les services facturés qui consomment des consommables et crée des logs
dans sync_logs avec le format:
  script_name: 'Deduction_Inventaire_Auto'
  tables_updated: '{"produits": {"code": "BUV-001", "quantite": 1}, "ventes": 1}'
  status: 'success'
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from core.supabase_storage import SupabaseStorage
from core.gazelle_api_client import GazelleAPIClient


class InventoryDeductionProcessor:
    """
    Processeur de déductions d'inventaire automatiques.

    Workflow:
    1. Récupère les factures récentes (X derniers jours)
    2. Pour chaque line item de facture, vérifie s'il correspond à un service avec règles de consommation
    3. Si oui, crée une entrée dans sync_logs pour tracer la déduction
    4. Met à jour l'inventaire du technicien (diminue le stock)
    """

    def __init__(self, days_lookback: int = 7):
        """
        Initialize le processeur.

        Args:
            days_lookback: Nombre de jours à analyser (défaut: 7 jours)
        """
        self.storage = SupabaseStorage()
        self.api_client = GazelleAPIClient()
        self.days_lookback = days_lookback
        self.stats = {
            'invoices_processed': 0,
            'deductions_created': 0,
            'errors': 0
        }

    def process_recent_invoices(self) -> Dict[str, int]:
        """
        Traite les factures récentes pour détecter les déductions d'inventaire.

        Returns:
            Statistiques du traitement
        """
        print(f"\n🔍 Analyse des factures des {self.days_lookback} derniers jours...")

        # 1. Récupérer les factures récentes
        cutoff_date = datetime.now() - timedelta(days=self.days_lookback)
        print(f"📅 Depuis: {cutoff_date.isoformat()}")

        try:
            # Récupérer toutes les factures et filtrer par date
            all_invoices = self.api_client.get_invoices(limit=None)

            # Filtrer les factures récentes
            recent_invoices = []
            for invoice in all_invoices:
                created_at = invoice.get('createdAt', '')
                if created_at:
                    invoice_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if invoice_date >= cutoff_date:
                        recent_invoices.append(invoice)

            print(f"📄 {len(recent_invoices)} factures récentes trouvées")

            # 2. Récupérer les factures déjà traitées (anti-doublon)
            self._already_processed = self._get_processed_invoice_ids()
            print(f"🔒 {len(self._already_processed)} factures déjà traitées (anti-doublon)")

            # 3. Récupérer les règles de consommation
            consumption_rules = self._get_consumption_rules()
            print(f"📋 {len(consumption_rules)} règles de consommation actives")

            if not consumption_rules:
                print("⚠️  Aucune règle de consommation définie - aucune déduction ne sera créée")
                return self.stats

            # 3. Traiter chaque facture
            for invoice in recent_invoices:
                self._process_invoice(invoice, consumption_rules)

            print(f"\n✅ Traitement terminé:")
            print(f"   Factures traitées: {self.stats['invoices_processed']}")
            print(f"   Déductions créées: {self.stats['deductions_created']}")
            print(f"   Erreurs: {self.stats['errors']}")

            return self.stats

        except Exception as e:
            print(f"❌ Erreur lors du traitement des factures: {e}")
            self.stats['errors'] += 1
            raise

    def _get_processed_invoice_ids(self) -> set:
        """Récupère les IDs de factures déjà traitées depuis sync_logs."""
        try:
            import requests
            url = (
                f"{self.storage.api_url}/sync_logs"
                f"?script_name=eq.Deduction_Inventaire_Auto"
                f"&status=eq.success"
                f"&select=tables_updated"
            )
            resp = requests.get(url, headers=self.storage._get_headers(), timeout=10)
            if resp.status_code == 200:
                ids = set()
                for log in resp.json():
                    try:
                        data = json.loads(log.get('tables_updated', '{}'))
                        inv_id = data.get('invoice', {}).get('id')
                        if inv_id:
                            ids.add(inv_id)
                    except Exception:
                        pass
                return ids
        except Exception as e:
            print(f"⚠️  Erreur récupération factures déjà traitées: {e}")
        return set()

    def _get_consumption_rules(self) -> List[Dict[str, Any]]:
        """
        Récupère les règles de consommation depuis Supabase.

        Returns:
            Liste des règles {service_gazelle_id, material_code_produit, quantity, ...}
        """
        try:
            rules = self.storage.get_data("service_inventory_consumption")

            # Grouper les règles par service_gazelle_id pour accès rapide
            rules_by_service = {}
            for rule in rules:
                service_id = rule.get('service_gazelle_id')
                if service_id:
                    if service_id not in rules_by_service:
                        rules_by_service[service_id] = []
                    rules_by_service[service_id].append(rule)

            self.rules_by_service = rules_by_service
            return rules

        except Exception as e:
            print(f"⚠️  Erreur récupération règles de consommation: {e}")
            return []

    def _process_invoice(self, invoice: Dict[str, Any], consumption_rules: List[Dict[str, Any]]):
        """
        Traite une facture pour détecter les déductions.

        Args:
            invoice: Données de la facture Gazelle
            consumption_rules: Liste des règles de consommation
        """
        try:
            invoice_id = invoice.get('id')
            invoice_number = invoice.get('number', 'N/A')

            # Récupérer le technicien (user) de la facture
            user_obj = invoice.get('user', {})
            user_id = user_obj.get('id') if user_obj else None

            # Mapper user_id Gazelle → technicien local
            technicien = self._get_technicien_from_user_id(user_id)
            if not technicien:
                # Impossible de déterminer le technicien, skip cette facture
                return

            # Récupérer les line items de la facture
            items_connection = invoice.get('allInvoiceItems', {})
            items = items_connection.get('nodes', [])

            if not items:
                return

            # Anti-doublon : skip si déjà traitée
            if invoice_id in self._already_processed:
                return

            self.stats['invoices_processed'] += 1

            # Traiter chaque line item
            for item in items:
                self._process_invoice_item(
                    invoice_id=invoice_id,
                    invoice_number=invoice_number,
                    item=item,
                    technicien=technicien,
                    invoice_date=invoice.get('createdAt')
                )

        except Exception as e:
            print(f"❌ Erreur traitement facture {invoice.get('id', 'unknown')}: {e}")
            self.stats['errors'] += 1

    def _process_invoice_item(
        self,
        invoice_id: str,
        invoice_number: str,
        item: Dict[str, Any],
        technicien: str,
        invoice_date: str
    ):
        """
        Traite un line item de facture pour détecter si c'est un service avec consommables.

        Args:
            invoice_id: ID de la facture
            invoice_number: Numéro de facture (pour logs)
            item: Line item de la facture
            technicien: Nom du technicien
            invoice_date: Date de la facture
        """
        try:
            item_id = item.get('id')
            item_type = item.get('type')
            description = item.get('description', '')

            # Vérifier si ce line item a des règles de consommation
            # Note: On utilise le type du line item pour matcher avec les règles
            # Si le type correspond à un service_gazelle_id dans les règles, on applique

            if item_type not in self.rules_by_service:
                # Pas de règles de consommation pour ce type d'item
                return

            rules = self.rules_by_service[item_type]

            # Pour chaque règle, créer une déduction
            for rule in rules:
                material_code = rule.get('material_code_produit')
                quantity_per_service = float(rule.get('quantity', 1.0))
                quantity_services = float(item.get('quantity', 1.0))

                # Quantité totale à déduire
                total_quantity = quantity_per_service * quantity_services

                # Créer l'entrée dans sync_logs
                success = self._create_deduction_log(
                    invoice_id=invoice_id,
                    invoice_number=invoice_number,
                    item_id=item_id,
                    service_description=description,
                    material_code=material_code,
                    quantity=total_quantity,
                    technicien=technicien,
                    date_service=invoice_date
                )

                if success:
                    # Mettre à jour l'inventaire du technicien (diminuer le stock)
                    self._update_technician_inventory(
                        technicien=technicien,
                        material_code=material_code,
                        quantity=-total_quantity  # Négatif pour retrait
                    )

                    self.stats['deductions_created'] += 1
                    print(f"  ✅ Déduction créée: {material_code} × {total_quantity} pour {technicien}")

        except Exception as e:
            print(f"❌ Erreur traitement item {item.get('id', 'unknown')}: {e}")
            self.stats['errors'] += 1

    def _create_deduction_log(
        self,
        invoice_id: str,
        invoice_number: str,
        item_id: str,
        service_description: str,
        material_code: str,
        quantity: float,
        technicien: str,
        date_service: str
    ) -> bool:
        """
        Crée une entrée dans sync_logs pour tracer la déduction.

        Format attendu:
          script_name: 'Deduction_Inventaire_Auto'
          tables_updated: '{"produits": {"code": "BUV-001", "quantite": 1}, "ventes": 1}'
          status: 'success'

        Returns:
            True si succès, False sinon
        """
        try:
            # Préparer les données du log
            tables_updated = {
                "produits": {
                    "code": material_code,
                    "quantite": quantity,
                    "technicien": technicien
                },
                "ventes": 1,
                "invoice": {
                    "id": invoice_id,
                    "number": invoice_number,
                    "item_id": item_id
                }
            }

            log_entry = {
                'script_name': 'Deduction_Inventaire_Auto',
                'status': 'success',
                'tables_updated': json.dumps(tables_updated),
                'details': f"Service: {service_description[:100]} | Matériel: {material_code} × {quantity}",
                'execution_time_seconds': 0,  # Déduction instantanée
                'created_at': datetime.now().isoformat()
            }

            # Insérer dans sync_logs
            success = self.storage.update_data(
                "sync_logs",
                log_entry,
                id_field="id",
                upsert=True
            )

            return success

        except Exception as e:
            print(f"❌ Erreur création log de déduction: {e}")
            return False

    def _update_technician_inventory(
        self,
        technicien: str,
        material_code: str,
        quantity: float
    ) -> bool:
        """
        Met à jour l'inventaire du technicien (ajout ou retrait).

        Args:
            technicien: Nom du technicien
            material_code: Code du produit
            quantity: Quantité (positif = ajout, négatif = retrait)

        Returns:
            True si succès, False sinon
        """
        try:
            success = self.storage.update_stock(
                code_produit=material_code,
                technicien=technicien,
                quantite_ajustement=quantity,
                emplacement="Atelier",
                motif=f"Déduction automatique - consommation service",
                created_by="system_auto"
            )

            return success

        except Exception as e:
            print(f"⚠️  Erreur mise à jour inventaire {technicien}/{material_code}: {e}")
            return False

    def _get_technicien_from_user_id(self, user_id: Optional[str]) -> Optional[str]:
        """
        Récupère le nom du technicien local depuis le user_id Gazelle.
        Utilise la config centralisée (techniciens_config.py).
        """
        if not user_id:
            return None

        try:
            from config.techniciens_config import get_technicien_by_id
            tech = get_technicien_by_id(user_id)
            if tech:
                return tech.get('username', tech.get('prenom', 'inconnu')).lower()
            return None
        except Exception as e:
            print(f"⚠️  Erreur mapping user_id → technicien: {e}")
            return None


def main():
    """
    Point d'entrée principal du script.

    Usage:
        python3 modules/inventory_deductions/process_deductions.py
    """
    print("\n" + "="*80)
    print("📦 TRAITEMENT DES DÉDUCTIONS D'INVENTAIRE AUTOMATIQUES")
    print("="*80)

    try:
        processor = InventoryDeductionProcessor(days_lookback=7)
        stats = processor.process_recent_invoices()

        print("\n" + "="*80)
        print("📊 RÉSUMÉ")
        print("="*80)
        print(f"✅ Factures traitées: {stats['invoices_processed']}")
        print(f"✅ Déductions créées: {stats['deductions_created']}")
        print(f"❌ Erreurs: {stats['errors']}")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
