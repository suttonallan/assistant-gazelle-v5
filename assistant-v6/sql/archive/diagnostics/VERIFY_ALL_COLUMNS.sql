-- ============================================================================
-- VÉRIFICATION COMPLÈTE: Toutes les colonnes de toutes les tables
-- ============================================================================
-- Exécute ça et copie-moi TOUT le résultat
-- Comme ça on arrête de deviner !
-- ============================================================================

-- Table 1: gazelle_clients
SELECT 'gazelle_clients' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'gazelle_clients'
ORDER BY ordinal_position;

-- Table 2: gazelle_contacts
SELECT 'gazelle_contacts' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'gazelle_contacts'
ORDER BY ordinal_position;

-- Table 3: gazelle_pianos
SELECT 'gazelle_pianos' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'gazelle_pianos'
ORDER BY ordinal_position;

-- Table 4: gazelle_timeline_entries
SELECT 'gazelle_timeline_entries' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'gazelle_timeline_entries'
ORDER BY ordinal_position;
