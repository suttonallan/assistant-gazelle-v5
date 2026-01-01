-- Test: La vue existe-t-elle et retourne-t-elle des données?
SELECT COUNT(*) as total_rows FROM gazelle_client_timeline;

-- Test: Voir les premières lignes
SELECT
    timeline_id,
    client_external_id,
    company_name,
    source_type,
    occurred_at
FROM gazelle_client_timeline
LIMIT 10;
