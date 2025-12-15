#!/usr/bin/env python3
"""
Service de recherche vectorielle pour l'assistant conversationnel.

Utilise OpenAI embeddings et l'index vectoriel pré-calculé (gazelle_vectors.pkl)
pour trouver les contextes les plus pertinents selon la question posée.
"""

import os
import pickle
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from pathlib import Path
import openai


class VectorSearch:
    """Gestionnaire de recherche vectorielle avec OpenAI embeddings."""

    def __init__(self, vector_file_path: Optional[str] = None):
        """
        Initialise le service de recherche vectorielle.

        Args:
            vector_file_path: Chemin vers le fichier .pkl (défaut: data/gazelle_vectors.pkl)
        """
        # Configuration OpenAI
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY non défini dans les variables d'environnement")

        openai.api_key = self.api_key

        # Chemin vers le fichier vectoriel
        if vector_file_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            vector_file_path = project_root / "data" / "gazelle_vectors.pkl"

        self.vector_file_path = Path(vector_file_path)

        # Charger l'index vectoriel
        self.index_data = self._load_vector_index()

        print(f"✅ Vector search initialisé: {len(self.index_data.get('texts', []))} entrées")

    def _load_vector_index(self) -> Dict[str, Any]:
        """
        Charge l'index vectoriel depuis le fichier .pkl.

        Returns:
            Dictionnaire contenant texts, vectors, sources, metadata, etc.
        """
        if not self.vector_file_path.exists():
            raise FileNotFoundError(
                f"Fichier vectoriel non trouvé: {self.vector_file_path}\n"
                f"Assurez-vous que gazelle_vectors.pkl existe dans le dossier data/"
            )

        try:
            with open(self.vector_file_path, 'rb') as f:
                data = pickle.load(f)

            # Valider la structure
            required_keys = ['texts', 'vectors', 'sources', 'metadata']
            missing_keys = [key for key in required_keys if key not in data]

            if missing_keys:
                raise ValueError(f"Clés manquantes dans l'index: {missing_keys}")

            return data

        except Exception as e:
            raise RuntimeError(f"Erreur lors du chargement de l'index vectoriel: {e}")

    def get_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """
        Génère l'embedding OpenAI pour un texte donné.

        Args:
            text: Texte à transformer en vecteur
            model: Modèle OpenAI à utiliser

        Returns:
            Vecteur d'embedding (liste de floats)
        """
        try:
            # Nettoyer le texte
            text = text.replace("\n", " ").strip()

            # Appeler l'API OpenAI
            response = openai.embeddings.create(
                input=text,
                model=model
            )

            return response.data[0].embedding

        except Exception as e:
            print(f"❌ Erreur lors de la génération de l'embedding: {e}")
            raise

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calcule la similarité cosinus entre deux vecteurs.

        Args:
            vec1: Premier vecteur
            vec2: Deuxième vecteur

        Returns:
            Score de similarité (0 à 1, 1 = identique)
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        # Éviter division par zéro
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Recherche les contextes les plus pertinents pour une question.

        Args:
            query: Question de l'utilisateur
            top_k: Nombre de résultats à retourner
            min_similarity: Seuil minimum de similarité (0-1)

        Returns:
            Liste de dictionnaires contenant:
                - text: Texte du contexte
                - source: Source du contexte (table, ID, etc.)
                - metadata: Métadonnées additionnelles
                - similarity: Score de similarité (0-1)
        """
        # Générer l'embedding de la question
        query_vector = self.get_embedding(query)

        # Calculer les similarités avec tous les vecteurs de l'index
        texts = self.index_data['texts']
        vectors = self.index_data['vectors']
        sources = self.index_data['sources']
        metadata = self.index_data['metadata']

        similarities = []
        for i, doc_vector in enumerate(vectors):
            similarity = self.cosine_similarity(query_vector, doc_vector)

            if similarity >= min_similarity:
                similarities.append({
                    'text': texts[i],
                    'source': sources[i],
                    'metadata': metadata[i],
                    'similarity': similarity,
                    'index': i
                })

        # Trier par similarité décroissante
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        # Retourner les top_k résultats
        return similarities[:top_k]

    def get_context_for_query(
        self,
        query: str,
        max_context_length: int = 3000,
        top_k: int = 5
    ) -> str:
        """
        Récupère le contexte le plus pertinent pour une question, formaté pour l'assistant.

        Args:
            query: Question de l'utilisateur
            max_context_length: Longueur maximale du contexte (en caractères)
            top_k: Nombre de résultats à combiner

        Returns:
            Contexte formaté (concaténation des top résultats)
        """
        results = self.search(query, top_k=top_k)

        if not results:
            return "Aucun contexte pertinent trouvé."

        # Construire le contexte
        context_parts = []
        current_length = 0

        for result in results:
            text = result['text']
            source = result['source']
            similarity = result['similarity']

            # Format: [Source] (Score: 0.XX) Texte
            formatted = f"[{source}] (Score: {similarity:.2f})\n{text}\n"

            # Vérifier si on dépasse la limite
            if current_length + len(formatted) > max_context_length:
                break

            context_parts.append(formatted)
            current_length += len(formatted)

        return "\n---\n".join(context_parts)

    def reload_index(self):
        """Recharge l'index vectoriel depuis le disque (utile après mise à jour)."""
        self.index_data = self._load_vector_index()
        print(f"✅ Index rechargé: {len(self.index_data.get('texts', []))} entrées")


# Instance globale (singleton) pour éviter de recharger le fichier à chaque requête
_vector_search_instance: Optional[VectorSearch] = None


def get_vector_search() -> VectorSearch:
    """
    Retourne l'instance singleton de VectorSearch.

    Returns:
        Instance de VectorSearch (crée si nécessaire)
    """
    global _vector_search_instance

    if _vector_search_instance is None:
        _vector_search_instance = VectorSearch()

    return _vector_search_instance
