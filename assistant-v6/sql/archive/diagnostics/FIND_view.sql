-- Chercher la vue dans TOUS les schémas
SELECT
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_name = 'gazelle_client_timeline';
