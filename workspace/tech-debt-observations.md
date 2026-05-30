# Observations techniques — Dette, fragilités, améliorations possibles

> Ce fichier est maintenu par Claude Code au fil des sessions. Chaque observation est datée et catégorisée. L'objectif : donner à un développeur qui arrive sur le projet une vue claire de ce qui est fragile, incohérent ou à améliorer.
>
> **Convention** : ✅ = corrigé · ⚠️ = à faire · 💡 = idée d'amélioration

---

## Robustesse des données / Supabase

### ⚠️ Aucune pagination systématique sur les requêtes Supabase REST
**Vu le** : 2026-04-27
**Où** : `core/supabase_storage.py` → `get_data()`, `modules/reports/service_reports.py` → `_fetch_clients_map()`
**Problème** : Le défaut PostgREST retourne max 1000 rows. Aucun mécanisme de pagination générique. Avec 4000+ clients, les requêtes sans `limit` tronquent silencieusement.
**Impact constaté** : Rapport timeline vide pour PDA/VDI/UQAM pendant des semaines. `clients_map` ne contenait que 1000/4000 clients.
**Corrigé partiellement** : `_fetch_clients_map()` paginé. Mais `get_data()` dans `supabase_storage.py` ne pagine toujours pas — tout appelant qui reçoit >1000 rows est silencieusement tronqué.
**Recommandation** : Ajouter un paramètre `paginate=True` à `get_data()` ou un wrapper `get_all_data()` qui boucle automatiquement.

### ✅ Erreurs 409 Supabase avalées silencieusement
**Vu le** : 2026-04-26
**Où** : `modules/sync_gazelle/sync_to_supabase.py` — upsert clients, appointments
**Problème** : Le code traitait TOUS les 409 comme "conflit d'upsert normal". Mais les FK violations (erreur PostgreSQL 23503) retournent aussi 409 → des records disparaissaient sans trace.
**Corrigé** : Vérification de `23503` dans le body du 409.

### ✅ Colonnes fantômes dans l'upsert clients
**Vu le** : 2026-04-26
**Où** : `modules/sync_gazelle/sync_to_supabase.py` → `sync_clients()`
**Problème** : 11 colonnes envoyées à Supabase (`client_type`, `locale`, `preferred_technician_id`, etc.) qui n'existent pas dans la table → erreur 400 → AUCUN client synchée.
**Corrigé** : Colonnes retirées.
**Leçon** : Quand on ajoute des champs au code de sync, s'assurer que la migration SQL a été exécutée en prod. Idéalement, valider les colonnes contre le schéma au démarrage.

### ⚠️ Pas de validation schéma au boot
**Vu le** : 2026-04-26
**Problème** : Le serveur démarre sans vérifier que les tables Supabase ont les colonnes attendues. Un écart entre le code et le schéma prod casse silencieusement.
**Recommandation** : Au démarrage, requêter `information_schema.columns` pour les tables critiques et logger un warning si des colonnes attendues manquent.

---

## Sync Gazelle → Supabase

### ⚠️ Le sync horaire ne sync que les RV, pas les clients
**Vu le** : 2026-04-26
**Où** : `.github/workflows/hourly_appointments_sync.yml`
**Problème** : Si un client est créé dans Gazelle entre deux nightly syncs, ses RV échouent en FK violation jusqu'au prochain nightly (22h). Pendant ~20h, les RV de ce client sont invisibles.
**Recommandation** : Ajouter un mini-sync clients (incrémental, 1 page de 100 les plus récents) avant le sync des appointments dans le workflow horaire.

### ⚠️ Le mode legacy `get_clients()` ne pagine pas
**Vu le** : 2026-04-26
**Où** : `core/gazelle_api_client.py` → `get_clients(limit=1000)`
**Problème** : `allClients { nodes { ... } }` sans pagination + troncature à `limit`. Avec 4011 clients, seuls les 1000 premiers sont retournés.
**Impact** : Le nightly full sync en mode non-incrémental ne sync que 1000/4011 clients.
**Recommandation** : Ajouter la pagination comme dans `get_appointments()`.

### ⚠️ Le `dateGet` filter dans l'incrémental est suspect
**Vu le** : 2026-04-26
**Où** : `core/gazelle_api_client_incremental.py` → `get_appointments_incremental()`
**Problème** : Le filtre `dateGet` avec `sortBy: START_DESC` retourne les events du futur lointain en premier. Avec 399 events, ça pagine en 4 pages donc ça marche. Mais si le volume augmente, les events récents pourraient être en page 10+ → lenteur.
**Recommandation** : Utiliser `startOn` + `endOn` comme le mode legacy, plus prévisible.

### ⚠️ Le client incremental sort par `CREATED_AT_DESC` avec early exit
**Vu le** : 2026-04-26
**Où** : `core/gazelle_api_client_incremental.py` → `get_clients_incremental()`
**Problème** : L'early exit sur `createdAt < last_sync_date` ne rattrape PAS les clients créés avant la dernière sync qui n'ont jamais été synchés (ex: si le sync a échoué ce jour-là). Seulement les NOUVEAUX clients depuis la dernière sync sont capturés.
**Recommandation** : Sortir par `UPDATED_AT_DESC` (pas `CREATED_AT_DESC`) et early-exit sur `updatedAt` — capture aussi les clients modifiés.

---

## Place des Arts

### ✅ `entry_type` incorrect pour extraction parking
**Vu le** : 2026-04-29
**Où** : `modules/place_des_arts/services/gazelle_sync.py` → `_extract_parking_from_appointment()`
**Problème** : Filtre `entry_type='SERVICE'` qui n'existe pas (devrait être `SERVICE_ENTRY_MANUAL`/`SERVICE_ENTRY_AUTOMATED`).
**Corrigé** : Filtre corrigé.

### ✅ Parser tabulaire ne supportait pas les dates ISO
**Vu le** : 2026-04-28
**Où** : `modules/place_des_arts/services/email_parser.py` → `parse_date_flexible()`
**Problème** : Format `YYYY-MM-DD` non reconnu → lignes entières ignorées silencieusement.
**Corrigé** : Pattern ISO ajouté.

### ✅ Parser tabulaire ne gère pas les colonnes décalées
**Vu le** : 2026-04-28
**Où** : `modules/place_des_arts/services/email_parser.py` → `parse_tabular_rows()`
**Problème** : Quand la PDA envoie un nom de salle en colonne 0, tout le mapping est décalé.
**Corrigé** : Détection auto du décalage.

### ⚠️ Warnings gravés dans `notes` jamais nettoyés
**Vu le** : 2026-04-28
**Où** : `modules/place_des_arts/services/event_manager.py` → `_normalize_row()`
**Problème** : Les warnings ("champ manquant: room") sont écrits dans le champ `notes` du record. Même si le champ est corrigé plus tard, le warning reste dans les notes pour toujours.
**Recommandation** : Soit ne pas écrire les warnings dans `notes`, soit les nettoyer quand le champ est rempli.

---

## Briefings (Ma Journée)

### ⚠️ Génération lente (~10 sec)
**Vu le** : 2026-04-28
**Où** : `/api/briefing/daily`
**Problème** : Chaque briefing appelle Claude Haiku individuellement + fetch Gazelle API live pour les soumissions + multiples requêtes Supabase. Sans cache, 10+ secondes.
**Impact** : Mauvaise UX au premier chargement après un redéploiement Render (cache vidé).
**Recommandation** : Pré-chauffer le cache immédiatement après déploiement. Possibilité de fetch les soumissions Gazelle en batch (1 appel pour tous les clients du jour au lieu de N appels).

### ⚠️ Cache briefings invalidé à chaque redéploiement
**Vu le** : 2026-04-28
**Problème** : Chaque `git push` → redéploiement Render → cache en mémoire perdu → première visite lente.
**Recommandation** : Persister le cache dans Supabase (table `briefing_cache`) au lieu de le garder en mémoire.

### ⚠️ La détection de complétion des soumissions fait N requêtes par estimate
**Vu le** : 2026-04-28
**Où** : `modules/briefing/client_intelligence_service.py` → `_enrich_estimates_completion()`
**Problème** : Pour chaque soumission, une requête HTTP vers Supabase pour chercher les SERVICE_ENTRY. Avec 3 soumissions par client, ça fait 3 requêtes supplémentaires.
**Recommandation** : Batch fetch toutes les SERVICE_ENTRY du client en une seule requête, filtrer en Python.

---

## Architecture générale

### ⚠️ Pas de tests automatisés
**Vu le** : 2026-04-26
**Problème** : Aucun pytest, aucun CI test. Les bugs (colonnes fantômes, entry_type incorrect, 409 silencieux) auraient été détectés par des tests d'intégration basiques.
**Recommandation** : Au minimum, des tests de smoke pour les méthodes de sync (mock Supabase, vérifier que les records ont les bonnes colonnes).

### ⚠️ Émojis dans les `print()` cassent sur Windows cp1252
**Vu le** : 2026-04-26
**Problème** : `print("🔧 ...")` lance un `UnicodeEncodeError` sur Windows. Contourné avec `PYTHONIOENCODING=utf-8` mais fragile.
**Recommandation** : Utiliser `logging` au lieu de `print()`. Ou wrapper les prints pour gérer l'encoding.

### ⚠️ Singleton SupabaseStorage instancié partout
**Vu le** : 2026-04-26
**Problème** : `SupabaseStorage()` est instancié dans chaque module, chaque méthode, parfois plusieurs fois dans le même appel. Pas un vrai singleton malgré le commentaire.
**Recommandation** : Implémenter un vrai singleton ou un registry d'injection de dépendances.

### 💡 Typage Python inexistant
**Vu le** : 2026-04-26
**Problème** : Quasi aucun type hint. Les dicts passent partout sans contrat clair. Difficile de savoir ce qu'un `Dict` contient sans lire l'implémentation.
**Recommandation** : Ajouter des `TypedDict` ou `dataclass` pour les structures principales (appointment, client, briefing, estimate).

### 💡 Pas de healthcheck Supabase/Gazelle au démarrage
**Vu le** : 2026-04-26
**Problème** : Le serveur démarre même si Supabase ou Gazelle sont inaccessibles. Les erreurs arrivent au runtime, au milieu d'une requête utilisateur.
**Recommandation** : Endpoint `/health` qui vérifie Supabase (ping table) + Gazelle (token valide) + retourne le statut.
