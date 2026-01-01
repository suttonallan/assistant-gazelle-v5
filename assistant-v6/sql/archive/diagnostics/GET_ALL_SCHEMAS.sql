-- Toutes les colonnes de toutes les tables Gazelle
SELECT
    table_name,
    column_name,
    data_type,
    ordinal_position
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('gazelle_clients', 'gazelle_contacts', 'gazelle_pianos', 'gazelle_timeline_entries')
ORDER BY table_name, ordinal_position;
