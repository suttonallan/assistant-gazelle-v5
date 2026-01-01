-- ============================================================================
-- Vues SQL Supabase - VERSION SIMPLE (basée sur colonnes RÉELLES vérifiées)
-- ============================================================================
--
-- Structure VÉRIFIÉE dans Supabase:
-- - gazelle_timeline_entries a piano_id ET client_id directement !
-- - Pas besoin de entity_type/entity_id pour les cas simples
-- - Jointures via external_id pour Piano→Client
--
-- ============================================================================

-- ============================================================================
-- Vue 1: Client Timeline (VERSION SIMPLE)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS gazelle_client_timeline AS
SELECT
    -- Timeline entry fields (VÉRIFIÉS)
    t.id as timeline_id,
    t.external_id as timeline_external_id,
    t.created_at,
    t.occurred_at,
    t.entry_type,
    t.event_type,
    t.title,
    t.description,
    t.user_id,
    t.piano_id,
    t.client_id,

    -- Piano fields (VÉRIFIÉS)
    p.id as piano_internal_id,
    p.external_id as piano_external_id,
    p.make as piano_make,
    p.model as piano_model,
    p.serial_number as piano_serial,
    p.location as piano_location,
    p.year as piano_year,
    p.type as piano_type,

    -- Client fields (VÉRIFIÉS)
    c.id as client_internal_id,
    c.external_id as client_external_id,
    c.company_name,
    c.address as client_address,
    c.phone as client_phone,
    c.email as client_email,

    -- Contact fields (VÉRIFIÉS)
    ct.id as contact_id,
    ct.first_name as contact_first_name,
    ct.last_name as contact_last_name,
    ct.email as contact_email,
    ct.phone as contact_phone,

    -- Search text
    COALESCE(ct.first_name || ' ' || ct.last_name, '') || ' ' ||
    COALESCE(c.company_name, '') || ' ' ||
    COALESCE(t.description, '') || ' ' ||
    COALESCE(t.title, '') as search_text

FROM public.gazelle_timeline_entries t

-- Option 1: Jointure via piano_id (quand timeline a un piano)
LEFT JOIN public.gazelle_pianos p ON t.piano_id = p.external_id

-- Option 2: Jointure Client via client_id direct OU via piano
LEFT JOIN public.gazelle_clients c ON (
    t.client_id = c.external_id  -- Timeline→Client direct
    OR p.client_external_id = c.external_id  -- Timeline→Piano→Client
)

-- Jointure Contact
LEFT JOIN public.gazelle_contacts ct ON ct.client_id = c.id

-- Tri
ORDER BY t.created_at DESC;


-- Index
CREATE INDEX IF NOT EXISTS idx_client_timeline_client_ext
ON gazelle_client_timeline(client_external_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_client_timeline_piano_ext
ON gazelle_client_timeline(piano_external_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_client_timeline_search
ON gazelle_client_timeline USING gin(to_tsvector('french', search_text));


-- ============================================================================
-- Vue 2: Client Search (VERSION SIMPLE)
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
    c.address as client_address,
    c.phone as client_phone,
    (SELECT COUNT(*) FROM public.gazelle_pianos p
     WHERE p.client_external_id = c.external_id) as piano_count,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE t.client_id = c.external_id
        OR t.piano_id IN (SELECT external_id FROM public.gazelle_pianos WHERE client_external_id = c.external_id)
    ) as timeline_count
FROM public.gazelle_contacts ct
LEFT JOIN public.gazelle_clients c ON ct.client_id = c.id

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
    c.address as client_address,
    c.phone as client_phone,
    (SELECT COUNT(*) FROM public.gazelle_pianos p
     WHERE p.client_external_id = c.external_id) as piano_count,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE t.client_id = c.external_id
        OR t.piano_id IN (SELECT external_id FROM public.gazelle_pianos WHERE client_external_id = c.external_id)
    ) as timeline_count
FROM public.gazelle_clients c;


-- ============================================================================
-- Vue 3: Piano List (VERSION SIMPLE)
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
    c.address as client_address,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE t.piano_id = p.external_id) as timeline_count,
    (SELECT ct.first_name || ' ' || ct.last_name
     FROM public.gazelle_contacts ct
     WHERE ct.client_id = c.id
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


-- ============================================================================
-- Test rapide
-- ============================================================================

-- Vérifier que ça fonctionne
-- SELECT COUNT(*) FROM gazelle_client_timeline;
-- SELECT * FROM gazelle_client_search WHERE search_name ILIKE '%Monique%' LIMIT 5;
-- SELECT * FROM gazelle_piano_list LIMIT 5;
