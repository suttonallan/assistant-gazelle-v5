#!/usr/bin/env python3
"""
Utilitaires pour stocker les modifications des pianos dans Supabase.

Plus rapide, fiable et scalable que GitHub Gist.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests


class SupabaseStorage:
    """Gère le stockage des modifications de pianos dans Supabase."""
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None, silent: bool = False):
        """
        Initialise le stockage Supabase.

        Args:
            supabase_url: URL du projet Supabase (si None, utilise SUPABASE_URL de l'environnement)
            supabase_key: Clé API Supabase (si None, utilise SUPABASE_KEY de l'environnement)
            silent: Si True, ne pas afficher les messages d'initialisation (pour éviter les logs répétés)
        """
        if not silent:
            print("🔧 Initialisation SupabaseStorage...")
        self.supabase_url = supabase_url or os.environ.get('SUPABASE_URL')
        # Fallback: essaye SUPABASE_SERVICE_ROLE_KEY puis SUPABASE_KEY
        self.supabase_key = supabase_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY', os.getenv('SUPABASE_KEY'))
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL et SUPABASE_KEY (ou SUPABASE_SERVICE_ROLE_KEY) requis. "
                "Ajoutez-les dans les variables d'environnement."
            )

        self.api_url = f"{self.supabase_url}/rest/v1"
        self.table = "vincent_dindy_piano_updates"
        if not silent:
            print(f"✅ SupabaseStorage initialisé: {self.supabase_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requêtes Supabase API."""
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def get_piano_updates(self, piano_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les modifications d'un piano depuis Supabase.
        
        Args:
            piano_id: ID du piano
            
        Returns:
            Dictionnaire des modifications ou None si aucune
        """
        try:
            url = f"{self.api_url}/{self.table}?piano_id=eq.{piano_id}&select=*"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Retourner la modification la plus récente
                    return data[0]
            
            return None
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération du piano {piano_id}: {e}")
            return None
    
    def get_all_piano_updates(self, institution_slug: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les modifications de pianos depuis Supabase.

        Args:
            institution_slug: Si fourni, filtre par institution (ex: 'vincent-dindy', 'orford')

        Returns:
            Dictionnaire {piano_id: modifications}
        """
        try:
            # Construire l'URL avec filtre optionnel
            url = f"{self.api_url}/{self.table}?select=*"
            if institution_slug:
                url += f"&institution_slug=eq.{institution_slug}"

            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                data = response.json()
                # Convertir en dictionnaire avec piano_id comme clé
                # Filtrer les items qui n'ont pas de piano_id
                return {
                    item['piano_id']: item
                    for item in data
                    if item.get('piano_id')  # Vérifier que piano_id existe
                }

            return {}
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des pianos: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def update_piano(self, piano_id: str, updates: Dict[str, Any], institution_slug: str = 'vincent-dindy') -> bool:
        """
        Sauvegarde les modifications d'un piano dans Supabase en utilisant UPSERT.
        Une seule requête au lieu de 2 (GET + PATCH/POST).

        Args:
            piano_id: ID du piano
            updates: Dictionnaire des champs à mettre à jour
            institution_slug: Slug de l'institution (défaut: vincent-dindy pour compatibilité)

        Returns:
            True si mis à jour avec succès
        """
        try:
            data = {
                "piano_id": piano_id,
                "institution_slug": institution_slug,
                **updates,
                "updated_at": datetime.now().isoformat()
            }

            # UPSERT : insère si n'existe pas, met à jour sinon
            # Header special pour UPSERT : resolution=merge-duplicates
            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            url = f"{self.api_url}/{self.table}"
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                print(f"✅ Piano {piano_id} sauvegardé dans Supabase pour {institution_slug} (UPSERT)")
                return True
            else:
                print(f"❌ Erreur Supabase {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de la mise à jour du piano {piano_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def batch_update_pianos(self, updates: List[Dict[str, Any]]) -> bool:
        """
        Met à jour plusieurs pianos en une seule requête (batch UPSERT).
        Beaucoup plus rapide que plusieurs appels individuels.

        Args:
            updates: Liste de dictionnaires contenant piano_id et les champs à mettre à jour
                     Ex: [{"piano_id": "A-001", "status": "top"}, ...]

        Returns:
            True si tous mis à jour avec succès
        """
        try:
            if not updates:
                return True

            # Ajouter updated_at à chaque entrée
            data = [
                {
                    **update,
                    "updated_at": datetime.now().isoformat()
                }
                for update in updates
            ]

            # UPSERT batch
            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            url = f"{self.api_url}/{self.table}"
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                print(f"✅ {len(updates)} pianos sauvegardés dans Supabase (batch UPSERT)")
                return True
            else:
                print(f"❌ Erreur Supabase batch {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors du batch update: {e}")
            import traceback
            traceback.print_exc()
            return False

    def delete_piano_updates(self, piano_id: str) -> bool:
        """
        Supprime les modifications d'un piano.

        Args:
            piano_id: ID du piano

        Returns:
            True si supprimé avec succès
        """
        try:
            url = f"{self.api_url}/{self.table}?piano_id=eq.{piano_id}"
            response = requests.delete(url, headers=self._get_headers())

            return response.status_code == 204

        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression du piano {piano_id}: {e}")
            return False

    # ============================================================
    # Méthodes génériques pour toutes les tables Supabase
    # ============================================================

    def update_data(
        self,
        table_name: str,
        data: Dict[str, Any],
        id_field: str = "id",
        upsert: bool = True,
        auto_timestamp: bool = True
    ) -> bool:
        """
        Méthode générique pour mettre à jour ou insérer des données dans n'importe quelle table Supabase.

        Args:
            table_name: Nom de la table Supabase
            data: Dictionnaire des données à sauvegarder
            id_field: Nom du champ servant d'identifiant unique (défaut: "id")
            upsert: Si True, utilise UPSERT (insert ou update). Si False, uniquement UPDATE.
            auto_timestamp: Si True, ajoute automatiquement updated_at (défaut: True)

        Returns:
            True si l'opération a réussi

        Exemple:
            # Ajouter un produit au catalogue
            storage.update_data(
                "produits_catalogue",
                {
                    "code_produit": "CORD-001",
                    "nom": "Corde #1",
                    "categorie": "Cordes",
                    "prix_unitaire": 12.50
                },
                id_field="code_produit"
            )
        """
        try:
            # Ajouter updated_at automatiquement (sauf pour transactions)
            if auto_timestamp and "updated_at" not in data:
                data["updated_at"] = datetime.now().isoformat()

            headers = self._get_headers()

            if upsert:
                # Mode UPSERT : insère ou met à jour
                headers["Prefer"] = "resolution=merge-duplicates"
                url = f"{self.api_url}/{table_name}"
                response = requests.post(url, headers=headers, json=data)
            else:
                # Mode UPDATE uniquement : requiert que l'enregistrement existe
                if id_field not in data:
                    raise ValueError(f"Le champ {id_field} est requis pour UPDATE")

                id_value = data[id_field]
                url = f"{self.api_url}/{table_name}?{id_field}=eq.{id_value}"
                response = requests.patch(url, headers=headers, json=data)

            if response.status_code in [200, 201, 204]:
                print(f"✅ Données sauvegardées dans {table_name}")
                return True
            else:
                print(f"❌ Erreur Supabase {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de la mise à jour de {table_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_data(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        select: str = "*",
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Méthode générique pour récupérer des données depuis n'importe quelle table Supabase.

        Args:
            table_name: Nom de la table Supabase
            filters: Dictionnaire de filtres {champ: valeur} (ex: {"technicien": "Allan"})
            select: Champs à récupérer (défaut: "*" pour tous)
            order_by: Champ de tri (ex: "created_at.desc")

        Returns:
            Liste de dictionnaires des résultats

        Exemple:
            # Récupérer tous les produits de catégorie "Cordes"
            produits = storage.get_data(
                "produits_catalogue",
                filters={"categorie": "Cordes"},
                order_by="nom.asc"
            )
        """
        try:
            url = f"{self.api_url}/{table_name}?select={select}"

            # Ajouter les filtres
            if filters:
                for field, value in filters.items():
                    url += f"&{field}=eq.{value}"

            # Ajouter le tri
            if order_by:
                url += f"&order={order_by}"

            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erreur Supabase {response.status_code}: {response.text}")
                return []

        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération depuis {table_name}: {e}")
            return []

    def delete_data(
        self,
        table_name: str,
        id_field: str,
        id_value: Any
    ) -> bool:
        """
        Méthode générique pour supprimer des données d'une table Supabase.

        Args:
            table_name: Nom de la table
            id_field: Nom du champ identifiant
            id_value: Valeur de l'identifiant

        Returns:
            True si supprimé avec succès

        Exemple:
            # Supprimer un produit
            storage.delete_data("produits_catalogue", "code_produit", "CORD-001")
        """
        try:
            url = f"{self.api_url}/{table_name}?{id_field}=eq.{id_value}"
            response = requests.delete(url, headers=self._get_headers())

            # Supabase peut retourner 204 (No Content) ou 200 (OK) pour une suppression réussie
            if response.status_code in [200, 204]:
                return True
            elif response.status_code == 404:
                print(f"⚠️ Élément non trouvé dans {table_name}: {id_field}={id_value}")
                return False
            else:
                print(f"⚠️ Erreur lors de la suppression depuis {table_name}: Status {response.status_code}, {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression depuis {table_name}: {e}")
            return False

    # ============================================================
    # Méthodes spécifiques pour le module Inventaire
    # ============================================================

    def get_produits_catalogue(self, categorie: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère les produits du catalogue, optionnellement filtrés par catégorie.

        Args:
            categorie: Catégorie à filtrer (ex: "Cordes", "Feutres") ou None pour tous

        Returns:
            Liste des produits
        """
        filters = {"categorie": categorie} if categorie else None
        return self.get_data("produits_catalogue", filters=filters, order_by="nom.asc")

    def get_inventaire_technicien(self, technicien: str) -> List[Dict[str, Any]]:
        """
        Récupère l'inventaire complet d'un technicien.

        Args:
            technicien: Nom du technicien (ex: "Allan")

        Returns:
            Liste des produits en stock pour ce technicien
        """
        return self.get_data(
            "inventaire_techniciens",
            filters={"technicien": technicien},
            order_by="emplacement.asc"
        )

    def update_stock(
        self,
        code_produit: str,
        technicien: str,
        quantite_ajustement: float,
        emplacement: str = "Atelier",
        motif: str = "",
        created_by: str = "system"
    ) -> bool:
        """
        Ajuste le stock d'un produit pour un technicien et enregistre la transaction.

        Args:
            code_produit: Code du produit
            technicien: Nom du technicien
            quantite_ajustement: Quantité à ajouter (positif) ou retirer (négatif)
            emplacement: Localisation du stock
            motif: Raison de l'ajustement
            created_by: Qui effectue l'ajustement

        Returns:
            True si l'opération a réussi
        """
        try:
            # 1. Récupérer l'inventaire actuel
            inventaire = self.get_data(
                "inventaire_techniciens",
                filters={
                    "code_produit": code_produit,
                    "technicien": technicien,
                    "emplacement": emplacement
                }
            )

            if inventaire:
                # Stock existant
                stock_actuel = float(inventaire[0].get("quantite_stock", 0))
                inventaire_id = inventaire[0]["id"]
            else:
                # Nouveau produit pour ce technicien
                stock_actuel = 0
                inventaire_id = None

            nouveau_stock = stock_actuel + quantite_ajustement

            # 2. Mettre à jour l'inventaire
            data_inventaire = {
                "code_produit": code_produit,
                "technicien": technicien,
                "quantite_stock": nouveau_stock,
                "emplacement": emplacement,
                "derniere_verification": datetime.now().isoformat()
            }

            # Ajouter l'id si l'inventaire existe déjà
            if inventaire_id:
                data_inventaire["id"] = inventaire_id

            success = self.update_data("inventaire_techniciens", data_inventaire)

            if not success:
                return False

            # 3. Enregistrer la transaction
            type_transaction = "ajout" if quantite_ajustement > 0 else "retrait"

            transaction_data = {
                "inventaire_id": inventaire_id,
                "code_produit": code_produit,
                "technicien": technicien,
                "type_transaction": type_transaction,
                "quantite": abs(quantite_ajustement),
                "quantite_avant": stock_actuel,
                "quantite_apres": nouveau_stock,
                "motif": motif,
                "created_by": created_by
            }

            return self.update_data("transactions_inventaire", transaction_data, auto_timestamp=False)

        except Exception as e:
            print(f"⚠️ Erreur lors de l'ajustement du stock: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_transactions_inventaire(
        self,
        technicien: Optional[str] = None,
        code_produit: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des transactions d'inventaire.

        Args:
            technicien: Filtrer par technicien (optionnel)
            code_produit: Filtrer par produit (optionnel)
            limit: Nombre maximum de transactions à retourner

        Returns:
            Liste des transactions, triées par date décroissante
        """
        filters = {}
        if technicien:
            filters["technicien"] = technicien
        if code_produit:
            filters["code_produit"] = code_produit

        url = f"{self.api_url}/transactions_inventaire?select=*"

        for field, value in filters.items():
            url += f"&{field}=eq.{value}"

        url += f"&order=created_at.desc&limit={limit}"

        try:
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des transactions: {e}")
            return []

    # ============================================================
    # Méthodes pour system_settings (OAuth tokens, config, etc.)
    # ============================================================

    def save_system_setting(self, key: str, value: Any) -> bool:
        """
        Sauvegarde un paramètre système dans Supabase (UPSERT).

        Utilisé pour stocker les tokens OAuth, configurations, etc.

        Args:
            key: Identifiant du paramètre (ex: "gazelle_oauth_token")
            value: Valeur (dict, str, int, etc.) - sera stockée en JSONB

        Returns:
            True si sauvegardé avec succès

        Exemple:
            storage.save_system_setting("gazelle_oauth_token", {
                "access_token": "xxx",
                "refresh_token": "yyy",
                "expires_in": 3600
            })
        """
        try:
            data = {
                "key": key,
                "value": value
            }

            headers = self._get_headers()
            headers["Prefer"] = "resolution=merge-duplicates"

            url = f"{self.api_url}/system_settings"
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [200, 201]:
                print(f"✅ Paramètre système '{key}' sauvegardé dans Supabase")
                return True
            else:
                print(f"❌ Erreur sauvegarde system_setting '{key}': {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"⚠️ Erreur lors de la sauvegarde de '{key}': {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_system_setting(self, key: str) -> Optional[Any]:
        """
        Récupère un paramètre système depuis Supabase.

        Args:
            key: Identifiant du paramètre (ex: "gazelle_oauth_token")

        Returns:
            Valeur du paramètre (dict, str, etc.) ou None si non trouvé

        Exemple:
            token = storage.get_system_setting("gazelle_oauth_token")
            if token:
                access_token = token.get("access_token")
        """
        try:
            url = f"{self.api_url}/system_settings?key=eq.{key}&select=value"
            response = requests.get(url, headers=self._get_headers())

            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0].get("value")

            return None

        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération de '{key}': {e}")
            return None

    def delete_system_setting(self, key: str) -> bool:
        """
        Supprime un paramètre système.

        Args:
            key: Identifiant du paramètre

        Returns:
            True si supprimé avec succès
        """
        try:
            url = f"{self.api_url}/system_settings?key=eq.{key}"
            response = requests.delete(url, headers=self._get_headers())

            return response.status_code in [200, 204]

        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression de '{key}': {e}")
            return False

