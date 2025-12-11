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
    
    # Flag pour savoir si commission_rate existe (cache)
    _commission_columns_available = None
    
    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """
        Initialise le stockage Supabase.
        
        Args:
            supabase_url: URL du projet Supabase (si None, utilise SUPABASE_URL de l'environnement)
            supabase_key: Clé API Supabase (si None, utilise SUPABASE_KEY de l'environnement)
        """
        self.supabase_url = supabase_url or os.environ.get('SUPABASE_URL')
        self.supabase_key = supabase_key or os.environ.get('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "SUPABASE_URL et SUPABASE_KEY requis. "
                "Ajoutez-les dans les variables d'environnement."
            )
        
        self.api_url = f"{self.supabase_url}/rest/v1"
        self.table = "vincent_dindy_piano_updates"
    
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
    
    def get_all_piano_updates(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les modifications de pianos depuis Supabase.
        
        Returns:
            Dictionnaire {piano_id: modifications}
        """
        try:
            url = f"{self.api_url}/{self.table}?select=*"
            response = requests.get(url, headers=self._get_headers())
            
            if response.status_code == 200:
                data = response.json()
                # Convertir en dictionnaire avec piano_id comme clé
                return {
                    item['piano_id']: item
                    for item in data
                }
            
            return {}
            
        except Exception as e:
            print(f"⚠️ Erreur lors de la récupération des pianos: {e}")
            return {}
    
    def update_piano(self, piano_id: str, updates: Dict[str, Any]) -> bool:
        """
        Sauvegarde les modifications d'un piano dans Supabase en utilisant UPSERT.
        Une seule requête au lieu de 2 (GET + PATCH/POST).

        Args:
            piano_id: ID du piano
            updates: Dictionnaire des champs à mettre à jour

        Returns:
            True si mis à jour avec succès
        """
        try:
            data = {
                "piano_id": piano_id,
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
                print(f"✅ Piano {piano_id} sauvegardé dans Supabase (UPSERT)")
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
        upsert: bool = True
    ) -> bool:
        """
        Méthode générique pour mettre à jour ou insérer des données dans n'importe quelle table Supabase.

        Args:
            table_name: Nom de la table Supabase
            data: Dictionnaire des données à sauvegarder
            id_field: Nom du champ servant d'identifiant unique (défaut: "id")
            upsert: Si True, utilise UPSERT (insert ou update). Si False, uniquement UPDATE.

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
            # Correction automatique des colonnes incorrectes pour produits_catalogue
            if table_name == "produits_catalogue":
                # Vérifier si la migration 002 est exécutée (une seule fois, en cache)
                if SupabaseStorage._commission_columns_available is None:
                    # Tester si display_order existe (colonne de la migration 002)
                    try:
                        test_url = f"{self.api_url}/produits_catalogue?select=display_order&limit=1"
                        test_response = requests.get(test_url, headers=self._get_headers())
                        SupabaseStorage._commission_columns_available = test_response.status_code == 200
                    except:
                        SupabaseStorage._commission_columns_available = False
                
                # Colonnes de la migration 002
                migration_002_columns = {
                    "has_commission", "commission_rate", "variant_group", "variant_label",
                    "display_order", "is_active", "gazelle_product_id", "last_sync_at"
                }
                
                # Liste des colonnes de BASE (migration 001) - TOUJOURS disponibles
                valid_columns = {
                    "code_produit", "nom", "categorie", "description", "unite_mesure",
                    "prix_unitaire", "fournisseur", "updated_at"
                }
                
                # Ajouter les colonnes de la migration 002 seulement si elles existent
                if SupabaseStorage._commission_columns_available:
                    valid_columns.update(migration_002_columns)
                else:
                    # RETIRER TOUTES les colonnes de la migration 002 si elles n'existent pas
                    for col in migration_002_columns:
                        if col in data:
                            del data[col]
                
                # Corrections automatiques (toutes les variantes possibles)
                corrections = {
                    "product_id": "gazelle_product_id",
                    "ProductId": "gazelle_product_id",
                    "PRODUCT_ID": "gazelle_product_id",
                    "active": "is_active",
                    "Active": "is_active",
                    "IsActive": "is_active",
                    "ACTIVE": "is_active",
                }
                
                # Appliquer les corrections - VERSION ROBUSTE
                corrected_data = {}
                for key, value in data.items():
                    # Ignorer les colonnes auto-générées
                    if key in ("id", "created_at"):
                        continue
                    
                    # Appliquer les corrections de noms (insensible à la casse)
                    key_lower = key.lower()
                    new_key = key  # Par défaut, garder le nom original
                    
                    # Chercher une correction (insensible à la casse)
                    for old_key, new_key_val in corrections.items():
                        if old_key.lower() == key_lower:
                            new_key = new_key_val
                            break
                    
                    # Garder uniquement les colonnes valides
                    if new_key in valid_columns:
                        if new_key not in corrected_data:  # Ne pas écraser si déjà présent
                            corrected_data[new_key] = value
                    # Ignorer silencieusement les colonnes invalides
                
                # Si commission_rate ou has_commission n'existent pas encore (migration 002 pas exécutée),
                # les retirer AVANT d'envoyer pour éviter les erreurs
                # On peut détecter ça en essayant une requête de test, mais pour l'instant on les retire
                # si on a déjà eu une erreur précédemment (on pourrait mettre un flag, mais simplifions)
                # Pour l'instant, on les garde et on les retirera seulement si erreur
                
                data = corrected_data
                
                # Vérifier que les colonnes requises sont présentes
                if not data.get("code_produit"):
                    raise ValueError("code_produit est requis pour produits_catalogue")
            
            # Ajouter updated_at automatiquement
            if "updated_at" not in data:
                data["updated_at"] = datetime.now().isoformat()

            headers = self._get_headers()

            if upsert:
                # Mode UPSERT : insère ou met à jour
                # Pour Supabase, si id_field n'est pas "id", on doit utiliser PATCH avec le filtre
                if id_field != "id" and id_field in data:
                    id_value = data[id_field]
                    # Essayer d'abord un PATCH (update si existe)
                    url = f"{self.api_url}/{table_name}?{id_field}=eq.{id_value}"
                    response = requests.patch(url, headers=headers, json=data)
                    
                    # Si 404 (n'existe pas), faire un POST (insert)
                    if response.status_code == 404:
                        url = f"{self.api_url}/{table_name}"
                        headers["Prefer"] = "return=representation"
                        response = requests.post(url, headers=headers, json=data)
                else:
                    # UPSERT standard avec "id"
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
                return True
            else:
                # Afficher l'erreur complète pour diagnostic
                try:
                    error_json = response.json()
                    error_msg = error_json.get('message', response.text)
                    error_full = f"❌ Erreur Supabase {response.status_code}: {error_msg}"
                except:
                    error_msg = response.text
                    error_full = f"❌ Erreur Supabase {response.status_code}: {error_msg}"
                
                # Si l'erreur concerne une colonne de la migration 002, mettre à jour le flag et réessayer
                migration_002_cols = ["commission_rate", "has_commission", "display_order", "is_active", 
                                     "variant_group", "variant_label", "gazelle_product_id", "last_sync_at"]
                if table_name == "produits_catalogue" and any(col in error_msg.lower() for col in migration_002_cols):
                    # Marquer que la migration 002 n'est pas exécutée
                    SupabaseStorage._commission_columns_available = False
                    
                    # Retirer TOUTES les colonnes de la migration 002
                    for col in migration_002_cols:
                        if col in data:
                            del data[col]
                    
                    # Réessayer sans ces colonnes
                    headers_retry = self._get_headers()
                    if upsert:
                        headers_retry["Prefer"] = "resolution=merge-duplicates"
                        url_retry = f"{self.api_url}/{table_name}"
                        response_retry = requests.post(url_retry, headers=headers_retry, json=data)
                    else:
                        id_value = data.get(id_field)
                        if id_value:
                            url_retry = f"{self.api_url}/{table_name}?{id_field}=eq.{id_value}"
                            response_retry = requests.patch(url_retry, headers=headers_retry, json=data)
                        else:
                            response_retry = response
                    
                    if response_retry.status_code in [200, 201, 204]:
                        return True
                    else:
                        # Si ça échoue encore, afficher l'erreur
                        try:
                            error_retry = response_retry.json().get('message', response_retry.text)
                            print(f"❌ Erreur Supabase {response_retry.status_code}: {error_retry}", flush=True)
                        except:
                            print(f"❌ Erreur Supabase {response_retry.status_code}: {response_retry.text}", flush=True)
                
                print(error_full, flush=True)
                return False

        except Exception as e:
            error_msg = f"⚠️ Erreur lors de la mise à jour de {table_name}: {e}"
            print(error_msg, flush=True)
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

            return response.status_code == 204

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
            success = self.update_data(
                "inventaire_techniciens",
                {
                    "code_produit": code_produit,
                    "technicien": technicien,
                    "quantite_stock": nouveau_stock,
                    "emplacement": emplacement,
                    "derniere_verification": datetime.now().isoformat()
                }
            )

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

            return self.update_data("transactions_inventaire", transaction_data)

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

