-- ============================================================================
-- ÉTAPE 1 CORRIGÉE: Créer la vue matérialisée (sans conversion problématique)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS gazelle_client_timeline AS

-- Source 1: Timeline entries directement liées au client (entity_type = 'CLIENT')
SELECT
    t.id as timeline_id,
    t.external_id as timeline_external_id,
    t.created_at,
    t.occurred_at,
    t.entry_type,
    t.event_type,
    t.title,
    t.description,
    t.user_id,

    -- Piano fields (NULL pour les entrées CLIENT)
    NULL::integer as piano_id,
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
    t.occurred_at,
    t.entry_type,
    t.event_type,
    t.title,
    t.description,
    t.user_id,

    -- Piano fields (présents pour les entrées PIANO)
    p.id as piano_id,
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
INNER JOIN public.gazelle_pianos p ON (CAST(t.entity_id AS INTEGER) = p.id AND t.entity_type = 'PIANO')
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
LEFT JOIN public.gazelle_contacts ct ON ct.client_external_id = c.external_id

ORDER BY 3 DESC;
