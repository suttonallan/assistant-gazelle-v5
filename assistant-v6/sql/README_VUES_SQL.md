# Guide: Vues SQL pour Assistant v6

## 🎯 Pourquoi des Vues SQL?

### Problème actuel (v6 standard)
```python
# 4 requêtes séparées:
1. Chercher contact "Monique Hallé" → gazelle.contacts
2. Remonter au client parent → gazelle.clients
3. Trouver les pianos du client → gazelle.pianos
4. Récupérer timeline des pianos → gazelle.timeline_entries

# Total: 4 round-trips réseau + logique Python complexe
```

### Solution avec Vues SQL
```sql
-- Une seule requête optimisée:
SELECT * FROM client_timeline_view
WHERE contact_name ILIKE '%Monique Hallé%'
ORDER BY created_at DESC
LIMIT 100;

-- Total: 1 round-trip + JOINs optimisés par PostgreSQL
```

## 📊 Comparaison

| Aspect | Sans Vues | Avec Vues |
|--------|-----------|-----------|
| **Requêtes** | 4 | 1 |
| **Code Python** | ~150 lignes | ~50 lignes |
| **Performance** | 200-500ms | 50-100ms |
| **Maintenance** | Difficile | Facile |
| **Import quotidien** | 4 tables à sync | 1 REFRESH |

## 🚀 Installation

### Étape 1: Créer les vues dans Supabase

1. Ouvrir **Supabase Dashboard** → **SQL Editor**
2. Copier le contenu de `create_timeline_view.sql`
3. Exécuter le script
4. Vérifier:

```sql
-- Vérifier que les vues existent
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_name IN ('client_timeline_view', 'client_search_view');

-- Devrait retourner:
-- client_timeline_view | MATERIALIZED VIEW
-- client_search_view   | VIEW
```

### Étape 2: Tester les vues

```sql
-- Test 1: Recherche client
SELECT * FROM client_search_view
WHERE search_name ILIKE '%Vincent%'
LIMIT 5;

-- Test 2: Timeline d'un client
SELECT * FROM client_timeline_view
WHERE company_name ILIKE '%Vincent%'
ORDER BY created_at DESC
LIMIT 10;

-- Test 3: Statistiques
SELECT
    company_name,
    COUNT(*) as timeline_count,
    COUNT(DISTINCT piano_id) as piano_count
FROM client_timeline_view
GROUP BY company_name
ORDER BY timeline_count DESC
LIMIT 10;
```

### Étape 3: Configurer le refresh quotidien

```sql
-- Option A: Avec pg_cron (si disponible)
SELECT cron.schedule(
    'refresh-timeline',
    '0 2 * * *',  -- Tous les jours à 2h du matin
    'SELECT refresh_timeline_view()'
);

-- Option B: Manuellement (ajouter au script d'import)
REFRESH MATERIALIZED VIEW CONCURRENTLY client_timeline_view;
```

### Étape 4: Activer dans v6

```python
# Dans assistant_v6.py, remplacer:
# from modules.assistant.services.queries_v6 import QueriesServiceV6
# par:
from modules.assistant.services.queries_v6_with_views import QueriesServiceV6WithViews as QueriesServiceV6
```

## 📈 Optimisations avancées

### 1. Partitionnement par date (pour grande base)

```sql
-- Si timeline > 1M d'entrées, partitionner par année
CREATE TABLE timeline_entries_partitioned (LIKE gazelle.timeline_entries)
PARTITION BY RANGE (EXTRACT(YEAR FROM created_at));

-- Partitions
CREATE TABLE timeline_2023 PARTITION OF timeline_entries_partitioned
    FOR VALUES FROM (2023) TO (2024);

CREATE TABLE timeline_2024 PARTITION OF timeline_entries_partitioned
    FOR VALUES FROM (2024) TO (2025);

-- Etc.
```

### 2. Index composites pour recherches fréquentes

```sql
-- Index pour: "Historique de [Client] en [Année]"
CREATE INDEX idx_timeline_client_year
ON client_timeline_view(client_id, EXTRACT(YEAR FROM created_at), created_at DESC);

-- Index pour: Recherche full-text dans descriptions
CREATE INDEX idx_timeline_description_fts
ON client_timeline_view
USING gin(to_tsvector('french', description));
```

### 3. Vues matérialisées filtrées (pour sous-ensembles)

```sql
-- Vue pour derniers 12 mois (refresh plus rapide)
CREATE MATERIALIZED VIEW client_timeline_recent AS
SELECT * FROM client_timeline_view
WHERE created_at >= NOW() - INTERVAL '12 months';

-- Index
CREATE INDEX idx_timeline_recent_client
ON client_timeline_recent(client_id, created_at DESC);
```

## 🔍 Debugging

### Vérifier la performance

```sql
-- Analyser le plan d'exécution
EXPLAIN ANALYZE
SELECT * FROM client_timeline_view
WHERE client_id = 'cli_xxx'
ORDER BY created_at DESC
LIMIT 100;

-- Vérifier la taille de la vue
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE '%timeline%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Vérifier les index

```sql
-- Lister les index sur la vue
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'client_timeline_view';

-- Statistiques d'utilisation
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'client_timeline_view'
ORDER BY idx_scan DESC;
```

## 📋 Checklist de déploiement

- [ ] Script SQL exécuté dans Supabase
- [ ] Vues créées et testées
- [ ] Index créés sur les colonnes fréquentes
- [ ] Refresh quotidien configuré (cron ou manuel)
- [ ] Code Python mis à jour (queries_v6_with_views.py)
- [ ] Tests A/B effectués (v6 standard vs v6 avec vues)
- [ ] Performance vérifiée (logs de temps de réponse)
- [ ] Documentation mise à jour

## 🎓 Ressources

- [PostgREST Views](https://postgrest.org/en/stable/references/api/views.html)
- [PostgreSQL Materialized Views](https://www.postgresql.org/docs/current/sql-creatematerializedview.html)
- [Supabase Performance](https://supabase.com/docs/guides/database/query-optimization)

## ✨ Résultat attendu

**Avant (v6 standard):**
```
🔍 Recherche contacts dans gazelle.contacts...
🔍 Recherche contacts dans gazelle_contacts...
🔍 Recherche contacts dans contacts...
🏢 Client parent trouvé
🎹 Recherche pianos dans gazelle.pianos...
📜 Recherche timeline dans gazelle.timeline_entries...
⏱️  Temps total: 450ms
```

**Après (v6 avec vues):**
```
🔍 Recherche via client_timeline_view
✅ Timeline: 153 entrées (sur 200 total)
⏱️  Temps total: 80ms
```

**Gain: 5.6x plus rapide + code 3x plus simple!** 🚀
