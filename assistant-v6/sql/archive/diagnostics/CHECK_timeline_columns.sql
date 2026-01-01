-- Vérifier les colonnes EXACTES de gazelle_timeline_entries
SELECT
    column_name,
    data_type,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'gazelle_timeline_entries'
ORDER BY ordinal_position;
