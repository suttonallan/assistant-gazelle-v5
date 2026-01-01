-- ============================================================================
-- VUES SQL GAZELLE - VERSION CORRECTE (colonnes vérifiées)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS gazelle_client_timeline AS

-- Source 1: Timeline entries directement liées au client (entity_type = 'CLIENT')
SELECT
    t.id as timeline_id,
    t.external_id as timeline_external_id,
    t.created_at,
    t.entry_date as occurred_at,
    t.entry_type,
    t.event_type,
    t.title,
    t.description,
    t.user_id,

    -- Piano fields (NULL pour les entrées CLIENT)
    NULL::text as piano_id,
    NULL::text as piano_external_id,
    NULL::text as piano_make,
    NULL::text as piano_model,
    NULL::text as piano_serial,
    NULL::text as piano_location,
    NULL::integer as piano_year,
    NULL::text as piano_type,

    -- Client fields
    c.id as client_internal_id,
    c.external_id as client_external_id,
    c.company_name,
    c.city as client_city,
    c.postal_code as client_postal_code,
    c.phone as client_phone,
    c.email as client_email,

    -- Contact fields
    ct.id as contact_id,
    ct.first_name as contact_first_name,
    ct.last_name as contact_last_name,
    ct.email as contact_email,
    ct.phone as contact_phone,

    -- Search text
    COALESCE(ct.first_name || ' ' || ct.last_name, '') || ' ' ||
    COALESCE(c.company_name, '') || ' ' ||
    COALESCE(t.description, '') || ' ' ||
    COALESCE(t.title, '') as search_text,

    'CLIENT' as source_type

FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_clients c ON (t.entity_id = c.external_id AND t.entity_type = 'CLIENT')
LEFT JOIN public.gazelle_contacts ct ON ct.client_external_id = c.external_id

UNION ALL

-- Source 2: Timeline entries liées via piano (entity_type = 'PIANO')
SELECT
    t.id as timeline_id,
    t.external_id as timeline_external_id,
    t.created_at,
    t.entry_date as occurred_at,
    t.entry_type,
    t.event_type,
    t.title,
    t.description,
    t.user_id,

    -- Piano fields (présents pour les entrées PIANO)
    p.id::text as piano_id,
    p.external_id as piano_external_id,
    p.make as piano_make,
    p.model as piano_model,
    p.serial_number as piano_serial,
    p.location as piano_location,
    p.year as piano_year,
    p.type as piano_type,

    -- Client fields (via piano)
    c.id as client_internal_id,
    c.external_id as client_external_id,
    c.company_name,
    c.city as client_city,
    c.postal_code as client_postal_code,
    c.phone as client_phone,
    c.email as client_email,

    -- Contact fields
    ct.id as contact_id,
    ct.first_name as contact_first_name,
    ct.last_name as contact_last_name,
    ct.email as contact_email,
    ct.phone as contact_phone,

    -- Search text
    COALESCE(ct.first_name || ' ' || ct.last_name, '') || ' ' ||
    COALESCE(c.company_name, '') || ' ' ||
    COALESCE(t.description, '') || ' ' ||
    COALESCE(t.title, '') as search_text,

    'PIANO' as source_type

FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_pianos p ON (t.entity_id::integer = p.id AND t.entity_type = 'PIANO')
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
LEFT JOIN public.gazelle_contacts ct ON ct.client_external_id = c.external_id

ORDER BY 3 DESC;


-- Index
CREATE INDEX IF NOT EXISTS idx_client_timeline_client_ext
ON gazelle_client_timeline(client_external_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_client_timeline_piano_ext
ON gazelle_client_timeline(piano_external_id, created_at DESC)
WHERE piano_external_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_client_timeline_search
ON gazelle_client_timeline USING gin(to_tsvector('french', search_text));

CREATE INDEX IF NOT EXISTS idx_client_timeline_source
ON gazelle_client_timeline(source_type, created_at DESC);


-- ============================================================================
-- Vue 2: Client Search
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
-- Vue 3: Piano List
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
