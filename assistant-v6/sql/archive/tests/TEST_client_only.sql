-- Test: Créer la vue avec SEULEMENT les entrées CLIENT (sans PIANO)
-- Si ça fonctionne, le problème vient de la partie PIANO

CREATE MATERIALIZED VIEW IF NOT EXISTS gazelle_client_timeline AS

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
LEFT JOIN public.gazelle_contacts ct ON ct.client_external_id = c.external_id;
