-- ============================================================================
-- Historique complet de Monique Hallé (cli_Pc3O0Ybqvve64xcF)
-- ============================================================================

-- Étape 1: Rafraîchir la vue matérialisée
SELECT refresh_gazelle_views();

-- Étape 2: Récupérer TOUT l'historique de Monique Hallé
SELECT
    timeline_id,
    timeline_external_id,
    occurred_at,
    created_at,
    entry_type,
    event_type,
    title,
    description,
    source_type,
    piano_make,
    piano_model,
    piano_serial,
    contact_first_name,
    contact_last_name
FROM gazelle_client_timeline
WHERE client_external_id = 'cli_Pc3O0Ybqvve64xcF'
ORDER BY
    COALESCE(occurred_at, created_at) DESC NULLS LAST,
    timeline_id DESC;
