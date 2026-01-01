-- ============================================================================
-- Supprimer TOUTES les vues Gazelle existantes
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS gazelle_client_timeline CASCADE;
DROP VIEW IF EXISTS gazelle_client_search CASCADE;
DROP VIEW IF EXISTS gazelle_piano_list CASCADE;
DROP FUNCTION IF EXISTS refresh_gazelle_views() CASCADE;
