#!/usr/bin/env python3
"""
Smart Query Engine — Moteur de questions intelligent avec apprentissage.

Quand une question n'est pas reconnue par le parser:
1. Cherche une "recette" déjà apprise dans learned_queries
2. Si trouvée → exécute directement (gratuit, instantané)
3. Si pas trouvée → appelle Claude Haiku pour analyser et générer la requête
4. Sauvegarde la recette pour la prochaine fois

Usage:
    engine = SmartQueryEngine()
    result = engine.answer(question="quelles sont les dernières églises accordées", user_id="asutton@piano-tek.com")
"""

import os
import re
import json
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import requests

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from core.supabase_storage import SupabaseStorage


# ═══════════════════════════════════════════════════════════════════
# Schéma des tables Supabase (fourni au LLM pour générer les requêtes)
# ═══════════════════════════════════════════════════════════════════

SUPABASE_SCHEMA = """
Tables disponibles dans Supabase (API REST PostgREST):

1. gazelle_clients (entreprises/institutions)
   - external_id (TEXT, PK, ex: cli_abc123)
   - company_name (TEXT) — nom de l'entreprise ou de la personne
   - address, city, postal_code, province (TEXT)
   - phone, email (TEXT)
   - notes (TEXT) — notes internes
   - status (TEXT) — active/inactive
   - created_at, updated_at (TIMESTAMP)

2. gazelle_contacts (personnes liées à un client)
   - external_id (TEXT, PK, ex: con_abc123)
   - client_external_id (TEXT, FK → gazelle_clients)
   - first_name, last_name (TEXT)
   - phone, email (TEXT)
   - city, address, postal_code (TEXT)

3. gazelle_appointments (rendez-vous)
   - external_id (TEXT, PK)
   - client_external_id (TEXT, FK → gazelle_clients)
   - piano_external_id (TEXT, FK → gazelle_pianos)
   - title (TEXT) — souvent le nom du client
   - description, notes (TEXT)
   - appointment_date (DATE, ex: 2025-03-15)
   - appointment_time (TIME, ex: 09:00)
   - duration_minutes (INT)
   - technicien (TEXT) — ID du technicien (usr_xxx)
   - status (TEXT) — ACTIVE, CANCELLED, COMPLETED
   - created_at, updated_at (TIMESTAMP)

4. gazelle_pianos (instruments)
   - external_id (TEXT, PK, ex: pia_abc123)
   - client_external_id (TEXT, FK → gazelle_clients)
   - make (TEXT) — marque (Steinway, Yamaha, etc.)
   - model (TEXT)
   - serial_number (TEXT)
   - type (TEXT) — Grand, Upright, Digital
   - year (TEXT) — année de fabrication
   - notes (TEXT) — notes techniques
   - location (TEXT)

5. gazelle_timeline_entries (historique de service / notes)
   - external_id (TEXT, PK)
   - entity_id (TEXT) — ID du client, piano ou contact lié
   - client_external_id (TEXT)
   - entity_type (TEXT) — client, piano, contact
   - description (TEXT) — contenu de la note de service
   - entry_date (TIMESTAMP)
   - event_type (TEXT)
   - created_at (TIMESTAMP)

6. gazelle_invoices (factures)
   - external_id (TEXT, PK)
   - client_external_id (TEXT, FK → gazelle_clients)
   - invoice_number (TEXT)
   - total_amount (NUMERIC)
   - status (TEXT) — paid, unpaid, partial
   - invoice_date (DATE)
   - due_date (DATE)

7. gazelle_invoice_items (lignes de facture)
   - external_id (TEXT, PK)
   - invoice_external_id (TEXT, FK → gazelle_invoices)
   - description (TEXT) — description du service/produit
   - quantity (NUMERIC)
   - unit_price (NUMERIC)
   - total (NUMERIC)

8. gazelle_estimates (devis/soumissions)
   - external_id (TEXT, PK)
   - client_external_id (TEXT, FK → gazelle_clients)
   - total_amount (NUMERIC)
   - status (TEXT)
   - estimate_date (DATE)

Techniciens connus:
- usr_ofYggsCDt2JAVeNP = Allan Sutton (admin)
- usr_HcCiFk7o0vZ9xAI0 = Nicolas Lessard
- usr_ReUSmIJmBF86ilY1 = Jean-Philippe Reny

API REST PostgREST:
- Filtres: eq, neq, gt, gte, lt, lte, like, ilike, in, is
- Combinaisons: or=(filter1,filter2), and=(filter1,filter2)
- Tri: order=column.asc ou order=column.desc
- Limite: limit=N
- Sélection: select=col1,col2
"""


# Stop words français pour normalisation
STOP_WORDS_FR = {
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'au', 'aux',
    'et', 'ou', 'mais', 'donc', 'car', 'ni', 'que', 'qui', 'quoi',
    'ce', 'cette', 'ces', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes',
    'son', 'sa', 'ses', 'notre', 'nos', 'votre', 'vos', 'leur', 'leurs',
    'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'on',
    'ne', 'pas', 'plus', 'en', 'y', 'se', 'si',
    'est', 'sont', 'a', 'ont', 'fait', 'été', 'avons', 'avez',
    'dans', 'sur', 'sous', 'avec', 'pour', 'par', 'chez',
    'quels', 'quelles', 'quel', 'quelle', 'combien', 'comment',
    'où', 'quand', 'pourquoi',
}


def normalize_keywords(text: str) -> List[str]:
    """
    Extrait et normalise les mots-clés d'une question.
    Retire les stop words, accents, et normalise en minuscules.
    """
    # Retirer accents
    text_clean = unicodedata.normalize('NFD', text.lower())
    text_clean = ''.join(c for c in text_clean if unicodedata.category(c) != 'Mn')

    # Extraire les mots (alphanumériques uniquement)
    words = re.findall(r'[a-z0-9]+', text_clean)

    # Retirer stop words et mots courts
    keywords = [w for w in words if w not in STOP_WORDS_FR and len(w) > 2]

    return sorted(set(keywords))


def keywords_similarity(kw1: List[str], kw2: List[str]) -> float:
    """Calcule le score de similarité entre deux ensembles de mots-clés (Jaccard)."""
    set1 = set(kw1)
    set2 = set(kw2)
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union)


class SmartQueryEngine:
    """Moteur de questions intelligent avec apprentissage automatique."""

    # Seuil de similarité pour réutiliser une recette
    SIMILARITY_THRESHOLD = 0.55

    def __init__(self):
        self.storage = SupabaseStorage(silent=True)

        # Initialiser Anthropic (même pattern que AIExtractionEngine)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            try:
                settings = self.storage.get_data('system_settings', filters={'key': 'anthropic_api_key'})
                if settings and settings[0].get('value'):
                    api_key = settings[0]['value']
            except Exception:
                pass

        if api_key and Anthropic:
            self.anthropic = Anthropic(api_key=api_key)
        else:
            self.anthropic = None
            print("⚠️  SmartQueryEngine: ANTHROPIC_API_KEY manquante — mode recettes uniquement")

    @property
    def is_available(self) -> bool:
        return self.anthropic is not None

    # ═══════════════════════════════════════════════════════════════
    # POINT D'ENTRÉE PRINCIPAL
    # ═══════════════════════════════════════════════════════════════

    def answer(self, question: str, user_id: str = None) -> Dict[str, Any]:
        """
        Répond à une question en langage naturel.

        1. Cherche une recette existante
        2. Si pas trouvée, génère via LLM
        3. Exécute la requête
        4. Sauvegarde la recette

        Returns:
            {
                "answer": "Texte de la réponse formatée",
                "data": [...],
                "source": "learned" | "llm_generated",
                "recipe_id": int | None,
                "query_type": "smart_query"
            }
        """
        keywords = normalize_keywords(question)
        print(f"🧠 SmartQuery: question='{question}' keywords={keywords}")

        # 1. Chercher une recette existante
        recipe = self._find_matching_recipe(keywords)

        if recipe:
            print(f"✅ SmartQuery: recette trouvée (id={recipe['id']}, times_used={recipe.get('times_used', 0)})")
            try:
                result = self._execute_recipe(recipe, question)
                self._increment_usage(recipe['id'])
                result['source'] = 'learned'
                result['recipe_id'] = recipe['id']
                return result
            except Exception as e:
                print(f"⚠️  SmartQuery: erreur exécution recette {recipe['id']}: {e}")
                # Fallback to LLM si la recette échoue

        # 2. Pas de recette → générer via LLM
        if not self.anthropic:
            return {
                'answer': "Je ne connais pas encore ce type de question. L'IA n'est pas configurée pour apprendre de nouvelles requêtes.",
                'data': None,
                'source': 'unavailable',
                'recipe_id': None,
                'query_type': 'smart_query'
            }

        print(f"🤖 SmartQuery: génération LLM pour '{question}'")
        try:
            recipe_data = self._generate_recipe_via_llm(question)
            if not recipe_data:
                return {
                    'answer': "Je n'ai pas réussi à comprendre cette question. Essayez de reformuler.",
                    'data': None,
                    'source': 'llm_failed',
                    'recipe_id': None,
                    'query_type': 'smart_query'
                }

            # 3. Exécuter la requête générée
            result = self._execute_recipe(recipe_data, question)

            # 4. Sauvegarder la recette pour la prochaine fois
            recipe_id = self._save_recipe(
                original_question=question,
                keywords=keywords,
                query_template=recipe_data.get('query_template', {}),
                response_template=recipe_data.get('response_template', ''),
                category=recipe_data.get('category', 'general'),
                user_id=user_id
            )

            result['source'] = 'llm_generated'
            result['recipe_id'] = recipe_id
            return result

        except Exception as e:
            print(f"❌ SmartQuery: erreur LLM: {e}")
            import traceback
            traceback.print_exc()
            return {
                'answer': f"Erreur lors de l'analyse de votre question: {str(e)}",
                'data': None,
                'source': 'error',
                'recipe_id': None,
                'query_type': 'smart_query'
            }

    # ═══════════════════════════════════════════════════════════════
    # RECHERCHE DE RECETTES
    # ═══════════════════════════════════════════════════════════════

    def _find_matching_recipe(self, keywords: List[str]) -> Optional[Dict]:
        """Cherche une recette existante qui matche les mots-clés."""
        try:
            url = f"{self.storage.api_url}/learned_queries?select=*&order=times_used.desc&limit=50"
            response = requests.get(url, headers=self.storage._get_headers())

            if response.status_code != 200:
                print(f"⚠️  SmartQuery: erreur lecture learned_queries: {response.status_code}")
                return None

            recipes = response.json()
            if not recipes:
                return None

            # Trouver la meilleure correspondance
            best_match = None
            best_score = 0.0

            for recipe in recipes:
                stored_keywords = recipe.get('normalized_keywords', [])
                score = keywords_similarity(keywords, stored_keywords)

                if score > best_score:
                    best_score = score
                    best_match = recipe

            if best_score >= self.SIMILARITY_THRESHOLD:
                print(f"🔍 SmartQuery: meilleur match score={best_score:.2f} (seuil={self.SIMILARITY_THRESHOLD})")
                return best_match

            print(f"🔍 SmartQuery: pas de match suffisant (best={best_score:.2f})")
            return None

        except Exception as e:
            print(f"⚠️  SmartQuery: erreur recherche recettes: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # GÉNÉRATION VIA LLM
    # ═══════════════════════════════════════════════════════════════

    def _generate_recipe_via_llm(self, question: str) -> Optional[Dict]:
        """Appelle Claude Haiku pour analyser la question et générer une requête."""
        try:
            system_prompt = f"""Tu es un assistant qui traduit des questions en langage naturel en requêtes Supabase REST API (PostgREST).

{SUPABASE_SCHEMA}

IMPORTANT:
- Génère des requêtes REST PostgREST (pas du SQL)
- Utilise les noms de colonnes exacts du schéma
- Pour chercher du texte, utilise ilike avec des wildcards (*terme*)
- Pour les dates, utilise gte/lte avec le format YYYY-MM-DD
- La date d'aujourd'hui est {datetime.now().strftime('%Y-%m-%d')}
- Réponds UNIQUEMENT avec un JSON valide, sans commentaires
- Si la question nécessite de croiser plusieurs tables, fais plusieurs étapes (steps)
- Chaque step doit avoir: table, select, filters (dict PostgREST), order, limit
- Pour les filtres PostgREST: utilise le format "column=operator.value"
  Exemples: "company_name=ilike.*église*", "appointment_date=gte.2025-01-01", "status=eq.ACTIVE"
"""

            user_prompt = f"""Question: "{question}"

Génère un JSON avec:
1. "query_template": {{
     "steps": [
       {{
         "table": "nom_table",
         "select": "col1,col2,...",
         "filters": {{"colonne": "operateur.valeur"}},
         "order": "colonne.desc",
         "limit": 20
       }}
     ],
     "join_key": "champ pour joindre les étapes (optionnel)"
   }}
2. "response_template": "Template de réponse avec {{count}} et {{results}}"
3. "category": "clients|appointments|invoices|pianos|stats|general"
4. "explanation": "Brève explication de la stratégie de requête"

JSON:"""

            response = self.anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            raw_text = response.content[0].text.strip()

            # Extraire le JSON (peut être entouré de ```json ... ```)
            json_match = re.search(r'\{[\s\S]*\}', raw_text)
            if not json_match:
                print(f"⚠️  SmartQuery: pas de JSON dans la réponse LLM: {raw_text[:200]}")
                return None

            recipe_data = json.loads(json_match.group())
            print(f"✅ SmartQuery: recette générée — {recipe_data.get('explanation', 'N/A')}")
            return recipe_data

        except json.JSONDecodeError as e:
            print(f"⚠️  SmartQuery: JSON invalide du LLM: {e}")
            return None
        except Exception as e:
            print(f"❌ SmartQuery: erreur LLM: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # EXÉCUTION DE RECETTES
    # ═══════════════════════════════════════════════════════════════

    def _execute_recipe(self, recipe: Dict, question: str) -> Dict[str, Any]:
        """Exécute une recette (sauvegardée ou générée) et formate la réponse."""
        query_template = recipe.get('query_template', {})
        if isinstance(query_template, str):
            query_template = json.loads(query_template)

        steps = query_template.get('steps', [])
        response_template = recipe.get('response_template', '')

        all_data = []
        step_results = {}

        for i, step in enumerate(steps):
            table = step.get('table', '')
            select = step.get('select', '*')
            filters = step.get('filters', {})
            order = step.get('order', '')
            limit = step.get('limit', 50)

            # Construire l'URL
            url = f"{self.storage.api_url}/{table}?select={select}"

            for col, filter_val in filters.items():
                # Supporter le format "col": "operator.value"
                url += f"&{col}={filter_val}"

            if order:
                url += f"&order={order}"
            url += f"&limit={limit}"

            print(f"   📡 Step {i+1}: GET {url[:150]}...")

            try:
                resp = requests.get(url, headers=self.storage._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    step_results[f'step_{i}'] = data
                    all_data.extend(data)
                    print(f"   ✅ Step {i+1}: {len(data)} résultats")
                else:
                    print(f"   ⚠️  Step {i+1}: HTTP {resp.status_code} — {resp.text[:100]}")
                    step_results[f'step_{i}'] = []
            except Exception as e:
                print(f"   ❌ Step {i+1}: {e}")
                step_results[f'step_{i}'] = []

        # Si plusieurs steps avec join_key, croiser les résultats
        join_key = query_template.get('join_key')
        if join_key and len(step_results) > 1:
            all_data = self._join_results(step_results, join_key)

        # Formater la réponse
        answer = self._format_answer(all_data, response_template, question)

        return {
            'answer': answer,
            'data': all_data[:50],  # Limiter les données brutes
            'query_type': 'smart_query',
            'count': len(all_data)
        }

    def _join_results(self, step_results: Dict, join_key: str) -> List[Dict]:
        """Croise les résultats de plusieurs steps via un champ commun."""
        if len(step_results) < 2:
            return step_results.get('step_0', [])

        # Prendre la première étape comme base
        base = step_results.get('step_0', [])
        lookup_data = step_results.get('step_1', [])

        # Construire un index de lookup
        lookup_index = {}
        for item in lookup_data:
            key_val = item.get(join_key) or item.get('external_id')
            if key_val:
                lookup_index[key_val] = item

        # Enrichir la base
        joined = []
        for item in base:
            key_val = item.get(join_key) or item.get('external_id') or item.get('client_external_id')
            if key_val and key_val in lookup_index:
                merged = {**item, **lookup_index[key_val]}
                joined.append(merged)
            else:
                joined.append(item)

        return joined

    def _format_answer(self, data: List[Dict], template: str, question: str) -> str:
        """Formate la réponse à partir des données et du template."""
        if not data:
            return "Aucun résultat trouvé pour votre question."

        count = len(data)

        # Si un template est fourni, l'utiliser comme header
        if template:
            header = template.replace('{count}', str(count))
        else:
            header = f"**{count} résultat(s) trouvé(s) :**"

        # Formater les résultats automatiquement
        lines = [header, ""]

        for item in data[:15]:  # Max 15 lignes
            line = self._format_item(item)
            if line:
                lines.append(f"- {line}")

        if count > 15:
            lines.append(f"\n... et {count - 15} autres résultats.")

        return "\n".join(lines)

    def _format_item(self, item: Dict) -> str:
        """Formate un élément de résultat en une ligne lisible."""
        parts = []

        # Date
        for date_field in ['appointment_date', 'invoice_date', 'entry_date', 'estimate_date']:
            val = item.get(date_field)
            if val:
                parts.append(f"**{str(val)[:10]}**")
                break

        # Nom
        for name_field in ['company_name', 'title', 'name', 'description']:
            val = item.get(name_field)
            if val and len(str(val).strip()) > 0:
                parts.append(str(val).strip()[:80])
                break

        # Ville
        city = item.get('city', '')
        if city:
            parts.append(f"({city})")

        # Montant
        for amount_field in ['total_amount', 'total', 'unit_price']:
            val = item.get(amount_field)
            if val is not None:
                try:
                    parts.append(f"**{float(val):.2f}$**")
                except (ValueError, TypeError):
                    pass
                break

        # Piano
        make = item.get('make', '')
        model = item.get('model', '')
        if make or model:
            parts.append(f"{make} {model}".strip())

        # Technicien
        tech = item.get('technicien', '')
        if tech:
            tech_names = {
                'usr_ofYggsCDt2JAVeNP': 'Allan',
                'usr_HcCiFk7o0vZ9xAI0': 'Nicolas',
                'usr_ReUSmIJmBF86ilY1': 'Jean-Philippe',
            }
            parts.append(f"[{tech_names.get(tech, tech)}]")

        return " — ".join(parts) if parts else ""

    # ═══════════════════════════════════════════════════════════════
    # SAUVEGARDE ET GESTION DES RECETTES
    # ═══════════════════════════════════════════════════════════════

    def _save_recipe(self, original_question: str, keywords: List[str],
                     query_template: Dict, response_template: str,
                     category: str, user_id: str = None) -> Optional[int]:
        """Sauvegarde une nouvelle recette dans learned_queries."""
        try:
            data = {
                'original_question': original_question,
                'normalized_keywords': keywords,
                'query_template': json.dumps(query_template),
                'response_template': response_template,
                'category': category,
                'times_used': 1,
                'last_used_at': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'created_by': user_id
            }

            url = f"{self.storage.api_url}/learned_queries"
            headers = self.storage._get_headers()
            headers["Prefer"] = "return=representation"

            resp = requests.post(url, headers=headers, json=data)

            if resp.status_code in [200, 201]:
                result = resp.json()
                recipe_id = result[0]['id'] if isinstance(result, list) and result else None
                print(f"💾 SmartQuery: recette sauvegardée (id={recipe_id})")
                return recipe_id
            else:
                print(f"⚠️  SmartQuery: erreur sauvegarde recette: {resp.status_code} — {resp.text[:100]}")
                return None

        except Exception as e:
            print(f"⚠️  SmartQuery: erreur sauvegarde: {e}")
            return None

    def _increment_usage(self, recipe_id: int):
        """Incrémente le compteur d'utilisation d'une recette."""
        try:
            # Lire la valeur actuelle
            url = f"{self.storage.api_url}/learned_queries?id=eq.{recipe_id}&select=times_used"
            resp = requests.get(url, headers=self.storage._get_headers())

            if resp.status_code == 200 and resp.json():
                current = resp.json()[0].get('times_used', 0)
                # Mettre à jour
                patch_url = f"{self.storage.api_url}/learned_queries?id=eq.{recipe_id}"
                patch_data = {
                    'times_used': current + 1,
                    'last_used_at': datetime.now().isoformat()
                }
                requests.patch(patch_url, headers=self.storage._get_headers(), json=patch_data)

        except Exception as e:
            print(f"⚠️  SmartQuery: erreur increment usage: {e}")

    # ═══════════════════════════════════════════════════════════════
    # API PUBLIQUE — gestion des recettes
    # ═══════════════════════════════════════════════════════════════

    def list_recipes(self) -> List[Dict]:
        """Liste toutes les recettes apprises."""
        try:
            url = f"{self.storage.api_url}/learned_queries?select=*&order=times_used.desc"
            resp = requests.get(url, headers=self.storage._get_headers())
            if resp.status_code == 200:
                return resp.json()
            return []
        except Exception:
            return []

    def delete_recipe(self, recipe_id: int) -> bool:
        """Supprime une recette."""
        try:
            url = f"{self.storage.api_url}/learned_queries?id=eq.{recipe_id}"
            resp = requests.delete(url, headers=self.storage._get_headers())
            return resp.status_code in [200, 204]
        except Exception:
            return False


# Singleton
_engine_instance: Optional[SmartQueryEngine] = None


def get_smart_engine() -> SmartQueryEngine:
    """Retourne l'instance singleton du SmartQueryEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SmartQueryEngine()
    return _engine_instance
