-- ============================================================================
-- DIAGNOSTIC: Voir les colonnes EXACTES de la vue matérialisée
-- ============================================================================
-- Exécute ça APRÈS avoir créé la vue
-- Copie-moi le résultat COMPLET
-- ============================================================================

SELECT
    column_name,
    ordinal_position,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'gazelle_client_timeline'
ORDER BY ordinal_position;
