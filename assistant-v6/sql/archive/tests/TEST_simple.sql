-- Test ultra simple: SELECT sans créer de vue
SELECT
    t.id as timeline_id,
    t.created_at,
    c.external_id as client_external_id,
    c.company_name
FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_clients c ON (t.entity_id = c.external_id AND t.entity_type = 'CLIENT')
LIMIT 5;
