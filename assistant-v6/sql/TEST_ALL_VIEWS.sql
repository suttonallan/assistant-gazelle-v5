-- ============================================================================
-- TEST: Vérifier que toutes les vues fonctionnent
-- ============================================================================

-- Test 1: gazelle_client_timeline
SELECT 'gazelle_client_timeline' as vue, COUNT(*) as nb_lignes
FROM gazelle_client_timeline;

-- Test 2: gazelle_client_search
SELECT 'gazelle_client_search' as vue, COUNT(*) as nb_lignes
FROM gazelle_client_search;

-- Test 3: gazelle_piano_list
SELECT 'gazelle_piano_list' as vue, COUNT(*) as nb_lignes
FROM gazelle_piano_list;

-- Test 4: Timeline pour Monique Hallé (cli_Pc3O0Ybqvve64xcF)
SELECT
    timeline_id,
    client_external_id,
    company_name,
    source_type,
    title,
    occurred_at
FROM gazelle_client_timeline
WHERE client_external_id = 'cli_Pc3O0Ybqvve64xcF'
ORDER BY occurred_at DESC NULLS LAST
LIMIT 10;

-- Test 5: Recherche "Monique"
SELECT
    source_type,
    display_name,
    client_external_id,
    piano_count,
    timeline_count
FROM gazelle_client_search
WHERE search_name ILIKE '%Monique%'
LIMIT 10;
