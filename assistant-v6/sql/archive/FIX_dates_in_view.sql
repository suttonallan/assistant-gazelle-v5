-- ============================================================================
-- CORRECTION: Utiliser entry_date au lieu de occurred_at pour le tri
-- ============================================================================

-- Vérifier d'abord si entry_date a des valeurs pour Monique
SELECT
    t.id as timeline_id,
    t.entry_date,
    t.occurred_at,
    t.created_at,
    t.title
FROM gazelle_timeline_entries t
WHERE t.client_external_id = 'cli_Pc3O0Ybqvve64xcF'
ORDER BY t.entry_date DESC NULLS LAST
LIMIT 5;
