-- ============================================================================
-- Créer les vues restantes (client_search et piano_list)
-- ============================================================================

CREATE OR REPLACE VIEW gazelle_client_search AS
-- Contacts
SELECT
    'contact' as source_type,
    ct.id,
    ct.first_name || ' ' || ct.last_name as display_name,
    ct.first_name || ' ' || ct.last_name as search_name,
    ct.email,
    ct.phone,
    c.id as client_id,
    c.external_id as client_external_id,
    c.company_name,
    c.city as client_city,
    c.postal_code as client_postal_code,
    c.phone as client_phone,
    (SELECT COUNT(*) FROM public.gazelle_pianos p
     WHERE p.client_external_id = c.external_id) as piano_count,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE (t.entity_type = 'CLIENT' AND t.entity_id = c.external_id)
        OR (t.entity_type = 'PIANO' AND t.entity_id::integer IN
            (SELECT p.id FROM public.gazelle_pianos p WHERE p.client_external_id = c.external_id))
    ) as timeline_count
FROM public.gazelle_contacts ct
LEFT JOIN public.gazelle_clients c ON ct.client_external_id = c.external_id

UNION ALL

-- Clients
SELECT
    'client' as source_type,
    c.id,
    c.company_name as display_name,
    c.company_name as search_name,
    c.email,
    c.phone,
    c.id as client_id,
    c.external_id as client_external_id,
    c.company_name,
    c.city as client_city,
    c.postal_code as client_postal_code,
    c.phone as client_phone,
    (SELECT COUNT(*) FROM public.gazelle_pianos p
     WHERE p.client_external_id = c.external_id) as piano_count,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE (t.entity_type = 'CLIENT' AND t.entity_id = c.external_id)
        OR (t.entity_type = 'PIANO' AND t.entity_id::integer IN
            (SELECT p.id FROM public.gazelle_pianos p WHERE p.client_external_id = c.external_id))
    ) as timeline_count
FROM public.gazelle_clients c;


-- ============================================================================
-- Vue Piano List
-- ============================================================================

CREATE OR REPLACE VIEW gazelle_piano_list AS
SELECT
    p.id as piano_id,
    p.external_id as piano_external_id,
    p.make,
    p.model,
    p.serial_number,
    p.location,
    p.year,
    p.type,
    p.notes,
    c.id as client_id,
    c.external_id as client_external_id,
    c.company_name,
    c.city as client_city,
    c.postal_code as client_postal_code,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE t.entity_type = 'PIANO' AND t.entity_id::integer = p.id) as timeline_count,
    (SELECT ct.first_name || ' ' || ct.last_name
     FROM public.gazelle_contacts ct
     WHERE ct.client_external_id = c.external_id
     LIMIT 1) as primary_contact
FROM public.gazelle_pianos p
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id;


-- ============================================================================
-- Fonction de refresh
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_gazelle_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY gazelle_client_timeline;
    RAISE NOTICE 'Gazelle views refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;
