-- ============================================================================
-- NETTOYAGE: Supprimer les vues de test (SANS RISQUE)
-- ============================================================================
-- Ce script supprime UNIQUEMENT les vues créées pour les tests
-- Les tables de données (gazelle_clients, gazelle_pianos, etc.) ne sont PAS touchées
-- ============================================================================

-- Supprimer les vues de test qui pourraient exister
DROP VIEW IF EXISTS test_client_timeline CASCADE;
DROP VIEW IF EXISTS test_client_only CASCADE;
DROP MATERIALIZED VIEW IF EXISTS test_timeline CASCADE;

-- Note: On garde les vues principales:
-- - gazelle_client_timeline (MATERIALIZED VIEW)
-- - gazelle_client_search (VIEW)
-- - gazelle_piano_list (VIEW)
-- - refresh_gazelle_views() (FUNCTION)

-- Vérification: Lister les vues qui restent
SELECT
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'gazelle_%'
ORDER BY table_name;
