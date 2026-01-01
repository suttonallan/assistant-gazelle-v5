-- ============================================================================
-- Diagnostic: Quelles colonnes existent VRAIMENT dans gazelle_pianos ?
-- ============================================================================

-- Voir TOUTES les colonnes de la table gazelle_pianos
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'gazelle_pianos'
ORDER BY ordinal_position;

-- Voir un exemple de ligne
SELECT * FROM public.gazelle_pianos LIMIT 1;
