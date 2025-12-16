# 🎯 Instructions Fiables - Ce Que Cursor Peut Accomplir

**Date:** 2025-12-15
**Version:** 5.0.0
**Statut:** ✅ Production Ready

---

## ✅ CE QUI FONCTIONNE DE FAÇON FIABLE

### 1. **Synchronisation Gazelle → Supabase** ✅

**Script:** [modules/sync_gazelle/sync_to_supabase.py](modules/sync_gazelle/sync_to_supabase.py)

**Ce qui est opérationnel:**
- ✅ **Clients:** 994 synchronisés (UPSERT idempotent)
- ✅ **Pianos:** 1,000 synchronisés (UPSERT idempotent)
- ✅ Gestion automatique des doublons (409 = success)
- ✅ Gestion des valeurs nulles (company_name avec fallback)
- ✅ Durée: ~4 minutes pour 2,000 records

**Comment lancer le sync:**
```bash
python3 modules/sync_gazelle/sync_to_supabase.py
```

**Résultat attendu:**
```
✅ SYNCHRONISATION TERMINÉE
⏱️  Durée: 263.79s

📊 Résumé:
   • Clients:       994 synchronisés,  6 erreurs
   • Pianos:       1000 synchronisés,  0 erreurs
```

**Instructions fiables pour Cursor:**
1. Cursor peut lancer ce script en toute confiance
2. Cursor peut analyser les logs d'erreur dans `modules/sync_gazelle/sync.log`
3. Cursor peut modifier les paramètres de batch size (actuellement 100 par lot)
4. Cursor peut ajouter des filtres de date si besoin

**Ce que Cursor NE DOIT PAS faire:**
- ❌ Ne pas toucher à `sync_appointments()` - ligne 371 commentée intentionnellement
- ❌ Ne pas essayer de déboguer l'API GraphQL pour appointments (trop complexe)
- ❌ Ne pas modifier la structure des requêtes GraphQL pour pianos (fonctionne bien)

---

### 2. **API Assistant Conversationnel** ✅

**Fichiers:** [api/assistant.py](api/assistant.py), [modules/assistant/](modules/assistant/)

**Ce qui est opérationnel:**
- ✅ **Parser NLP:** Analyse des questions en langage naturel
- ✅ **Vector Search:** 126,519 entrées chargées (1.5 GB)
- ✅ **Routes FastAPI:** `/assistant/chat` et `/assistant/health`
- ✅ **Health Check:** Tous composants chargés

**Comment tester:**
```bash
# Health check
curl -s http://localhost:8000/assistant/health | python3 -m json.tool

# Résultat attendu:
{
    "status": "healthy",
    "parser_loaded": true,
    "queries_loaded": true,
    "vector_search_loaded": true,
    "vector_index_size": 126519
}
```

**Instructions fiables pour Cursor:**
1. Cursor peut ajouter de nouveaux types de questions dans [modules/assistant/services/parser.py:13-21](modules/assistant/services/parser.py#L13-L21)
2. Cursor peut ajouter de nouvelles queries dans [modules/assistant/services/queries.py](modules/assistant/services/queries.py)
3. Cursor peut améliorer les patterns de parsing dans `parser.py`
4. Cursor peut optimiser les requêtes Supabase existantes

**Ce que Cursor NE DOIT PAS faire:**
- ❌ Ne pas supprimer `data/gazelle_vectors.pkl` (fichier volumineux critique)
- ❌ Ne pas modifier la structure de chargement des embeddings dans `vector_search.py`
- ❌ Ne pas changer l'URL Supabase dans les queries (préfixe `gazelle_*` requis)

---

### 3. **Tables Supabase** ✅

**Schema:** `public.gazelle_*` (pas `gazelle.*`)

**Tables créées et fonctionnelles:**
```sql
✅ public.gazelle_clients (994 records)
✅ public.gazelle_pianos (1,000 records)
✅ public.gazelle_contacts (créée, vide)
✅ public.gazelle_appointments (créée, vide)
✅ public.gazelle_timeline_entries (créée, vide)
```

**Instructions fiables pour Cursor:**
1. Cursor peut lire ces tables via REST API:
   ```python
   url = f"{SUPABASE_URL}/rest/v1/gazelle_clients"
   headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
   response = requests.get(url, headers=headers)
   ```
2. Cursor peut créer des index supplémentaires si besoin
3. Cursor peut ajouter des colonnes (ALTER TABLE)
4. Cursor peut créer des vues pour simplifier les requêtes

**Ce que Cursor NE DOIT PAS faire:**
- ❌ Ne pas créer de tables dans le schéma `gazelle.*` (REST API ne supporte que `public`)
- ❌ Ne pas utiliser le port PostgreSQL 5432 (Supabase free tier utilise REST API)
- ❌ Ne pas supprimer les politiques RLS existantes

---

### 4. **Client Gazelle API** ✅

**Fichier:** [core/gazelle_api_client.py](core/gazelle_api_client.py)

**Ce qui est opérationnel:**
- ✅ **OAuth2 Token Refresh:** Automatique
- ✅ **get_clients():** Récupère tous les clients
- ✅ **get_pianos():** Récupère tous les pianos avec relations
- ✅ Pagination GraphQL automatique

**Instructions fiables pour Cursor:**
1. Cursor peut utiliser `get_clients()` et `get_pianos()` en toute confiance
2. Cursor peut ajouter de nouvelles méthodes pour d'autres entités (contacts, timeline)
3. Cursor peut améliorer la gestion d'erreurs

**Ce que Cursor NE DOIT PAS faire:**
- ❌ Ne pas toucher à `get_appointments()` - méthode non fiable (voir section problèmes)
- ❌ Ne pas modifier la structure des requêtes GraphQL existantes qui fonctionnent
- ❌ Ne pas changer la logique de refresh token (fonctionne bien)

---

## ⚠️ CE QUI NÉCESSITE UNE DÉCISION UTILISATEUR

### 1. **Synchronisation des Rendez-vous (Appointments)** ⚠️

**Statut:** Bloqué - API GraphQL trop complexe

**Problème:**
- L'API GraphQL Gazelle pour les événements/rendez-vous a une structure complexe
- Type `CoreDate` non documenté
- Filtres de date requis mais format inconnu
- Multiple tentatives échouées

**Ligne désactivée:** [modules/sync_gazelle/sync_to_supabase.py:371](modules/sync_gazelle/sync_to_supabase.py#L371)
```python
# self.sync_appointments()  # TODO: Choisir une des 3 options documentées
```

**3 Options Documentées (par Claude PC):**

#### **Option A: Utiliser REST API Gazelle** (recommandé)
- Contacter support Gazelle pour obtenir documentation REST API
- Plus simple que GraphQL
- Pattern CRUD standard

#### **Option B: Copier Logique V4**
- Réutiliser le script Windows qui fonctionne
- Localisation: Ancien projet V4 (SQLite)
- Adapter les requêtes pour Supabase

#### **Option C: Migration SQL Server → Supabase**
- Si V4 sync fonctionne dans SQL Server
- Créer un pont temporaire SQL Server → Supabase
- Désactiver ensuite

**Instructions pour Cursor:**
- ❌ **NE PAS** essayer de déboguer l'API GraphQL pour appointments
- ❌ **NE PAS** décommenter la ligne 371 sans décision utilisateur
- ✅ **PEUT** préparer le code pour l'option choisie une fois décidée
- ✅ **PEUT** documenter les tentatives déjà faites

---

### 2. **Synchronisation Contacts et Timeline** 🔜

**Statut:** Tables créées, code template prêt

**Ce qui manque:**
```python
# Dans sync_to_supabase.py, lignes ~372-373
# self.sync_contacts()        # TODO: Implémenter
# self.sync_timeline_entries() # TODO: Implémenter
```

**Instructions pour Cursor:**
1. ✅ Cursor PEUT implémenter `sync_contacts()` en suivant le pattern de `sync_clients()`
2. ✅ Cursor PEUT implémenter `sync_timeline_entries()` de la même façon
3. ✅ Cursor PEUT tester avec la méthode `get_contacts()` du GazelleAPIClient (si elle existe)

**Pattern à suivre:**
```python
def sync_contacts(self):
    """Synchronise les contacts depuis Gazelle vers Supabase."""
    self.logger.info("📞 Synchronisation des contacts...")

    # 1. Récupérer depuis Gazelle
    contacts = self.gazelle_client.get_contacts()  # À vérifier si méthode existe

    # 2. Transform
    for contact in contacts:
        contact_record = {
            "external_id": contact["id"],
            "client_external_id": contact["client"]["id"],
            "first_name": contact.get("firstName"),
            "last_name": contact.get("lastName"),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "is_default": contact.get("isDefault", False)
        }

        # 3. UPSERT vers Supabase
        self._upsert_contact(contact_record)
```

---

## 🛠️ MAINTENANCE QUOTIDIENNE

### Configurer le CRON pour Sync Automatique

**Option 1: Mac Local (Dev)**
```bash
# Ajouter au crontab
crontab -e

# Sync à 2h du matin chaque jour
0 2 * * * cd /Users/allansutton/Documents/assistant-gazelle-v5 && /usr/bin/python3 modules/sync_gazelle/sync_to_supabase.py >> logs/sync_gazelle.log 2>&1

# Créer le dossier logs
mkdir -p logs
```

**Option 2: Render Cron Job (Production)** ⭐ **Recommandé**
1. Créer nouveau Cron Job sur Render.com
2. Repository: Votre repo GitHub
3. Command: `python3 modules/sync_gazelle/sync_to_supabase.py`
4. Schedule: `0 2 * * *` (2h AM)
5. Variables d'environnement:
   - `GAZELLE_CLIENT_ID`
   - `GAZELLE_CLIENT_SECRET`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

**Instructions pour Cursor:**
- ✅ Cursor PEUT créer le fichier de config CRON
- ✅ Cursor PEUT aider à tester le cron localement
- ❌ Cursor NE PEUT PAS déployer sur Render (nécessite accès utilisateur)

---

## 📊 VÉRIFICATION POST-SYNC

### Vérifier que le Sync a Fonctionné

**1. Dans Supabase Dashboard:**
```sql
-- Compter les clients
SELECT COUNT(*) FROM public.gazelle_clients;
-- Attendu: ~994

-- Compter les pianos
SELECT COUNT(*) FROM public.gazelle_pianos;
-- Attendu: ~1,000

-- Voir exemples
SELECT company_name, city, email
FROM public.gazelle_clients
LIMIT 10;
```

**2. Via l'API Assistant:**
```bash
curl -X POST http://localhost:8000/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": ".stats", "user_id": "test"}'
```

**Instructions pour Cursor:**
- ✅ Cursor PEUT créer un script de vérification automatique
- ✅ Cursor PEUT ajouter des alertes si le nombre de records diminue
- ✅ Cursor PEUT créer un dashboard de monitoring

---

## 🧪 TESTS FIABLES

### Tests Automatisés Existants

**Fichier:** [tests/test_assistant_api.py](tests/test_assistant_api.py)

**Statut des tests:**
```
✅ test_health_check - PASS
✅ test_parse_help_command - PASS
✅ test_parse_appointments - PASS
⚠️  test_parse_search (données manquantes - normal)
⚠️  test_vector_search (données manquantes - normal)
```

**Lancer les tests:**
```bash
python3 tests/test_assistant_api.py
```

**Instructions pour Cursor:**
1. ✅ Cursor PEUT ajouter de nouveaux tests unitaires
2. ✅ Cursor PEUT créer des tests d'intégration pour le sync
3. ✅ Cursor PEUT mocker les appels à Gazelle API pour tests rapides
4. ❌ Cursor NE DOIT PAS s'attendre à ce que tous les tests passent avant le sync complet

---

## 🚨 TROUBLESHOOTING COMMUN

### Erreur: "Table does not exist"
```
❌ Could not find the table 'public.gazelle_clients'
```

**Solution:**
Exécuter [modules/sync_gazelle/create_tables_public.sql](modules/sync_gazelle/create_tables_public.sql) dans Supabase SQL Editor

---

### Erreur: "OPENAI_API_KEY non défini"
```
❌ OPENAI_API_KEY environment variable not set
```

**Solution:**
```bash
# Vérifier .env
grep OPENAI .env

# Si manquant, ajouter:
echo "OPENAI_API_KEY=sk-..." >> .env
```

---

### Erreur: "psycopg2 connection timeout"
```
❌ Operation timed out (port 5432)
```

**Solution:**
✅ **C'EST NORMAL !** Supabase free tier utilise REST API, pas PostgreSQL direct.
Le projet utilise correctement REST API via `requests`.

---

### Erreur: "409 Conflict" dans les logs
```
❌ Erreur UPSERT client: 409
```

**Solution:**
✅ **C'EST NORMAL !** 409 = duplicate, ce qui est attendu avec UPSERT.
Le code compte maintenant 409 comme succès (ligne 207 de `sync_to_supabase.py`).

---

## 📈 AMÉLIORATIONS POSSIBLES

### Ce Que Cursor PEUT Implémenter

**1. Dashboard de Monitoring**
- Créer une page React pour visualiser les stats de sync
- Afficher le nombre de records par table
- Afficher l'historique des syncs (via `gazelle_sync_logs`)

**2. Alertes Automatiques**
- Email si le sync échoue
- Slack notification si moins de 900 clients synchronisés
- Log détaillé dans Supabase

**3. Optimisations Performance**
- Paralléliser les UPSERT (actuellement séquentiel)
- Augmenter le batch size de 100 à 500
- Utiliser `asyncio` pour requêtes concurrentes

**4. Sync Incrémental**
- Ne synchroniser que les clients modifiés depuis dernière sync
- Utiliser `updated_at` pour filtrer
- Réduire la durée de 4 min à ~30 sec

**5. Tests End-to-End**
- Créer un environnement de test Supabase
- Mock complet de Gazelle API
- CI/CD avec GitHub Actions

---

## ✅ CHECKLIST AVANT MODIFICATIONS

Avant que Cursor modifie du code critique, vérifier:

- [ ] Le fichier `data/gazelle_vectors.pkl` existe (1.5 GB)
- [ ] L'API principale répond: `curl http://localhost:8000/health`
- [ ] L'assistant health check passe: `curl http://localhost:8000/assistant/health`
- [ ] Les tables Supabase existent: Vérifier dans dashboard
- [ ] Le `.env` contient toutes les clés nécessaires
- [ ] Le sync récent a fonctionné: Vérifier `modules/sync_gazelle/sync.log`

---

## 🎯 RÉSUMÉ POUR CURSOR

### ✅ Fiable - Cursor Peut Modifier Sans Risque

1. **Parser de questions** ([modules/assistant/services/parser.py](modules/assistant/services/parser.py))
2. **Queries Supabase** ([modules/assistant/services/queries.py](modules/assistant/services/queries.py))
3. **Sync clients/pianos** ([modules/sync_gazelle/sync_to_supabase.py](modules/sync_gazelle/sync_to_supabase.py) lignes 150-350)
4. **Tests unitaires** ([tests/test_assistant_api.py](tests/test_assistant_api.py))
5. **Documentation**

### ⚠️ Nécessite Décision Utilisateur

1. **Sync appointments** (ligne 371 - 3 options documentées)
2. **CRON production** (Render vs local)
3. **Optimisations performance** (si problèmes de temps)

### ❌ Ne Pas Toucher

1. **Vector search loading** ([modules/assistant/services/vector_search.py:45-60](modules/assistant/services/vector_search.py#L45-L60))
2. **OAuth2 token refresh** ([core/gazelle_api_client.py:50-80](core/gazelle_api_client.py#L50-L80))
3. **Requêtes GraphQL pianos** ([core/gazelle_api_client.py:120-145](core/gazelle_api_client.py#L120-L145))
4. **Schéma Supabase public.gazelle_*** (ne pas passer à `gazelle.*`)

---

**Créé par:** Claude Code
**Pour:** Cursor IDE
**Objectif:** Instructions fiables et claires sur ce qui peut être modifié sans risque
