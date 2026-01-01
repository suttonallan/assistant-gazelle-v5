-- ============================================================================
-- CORRECTION: Éliminer les doublons causés par LEFT JOIN contacts
-- ============================================================================
--
-- PROBLÈME: La vue actuelle fait LEFT JOIN sur contacts, ce qui crée
-- N lignes pour chaque timeline entry si le client a N contacts.
--
-- SOLUTION: Utiliser DISTINCT ON (timeline_id) pour garder une seule ligne
-- par timeline entry, en priorisant le premier contact trouvé.
--
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS gazelle_client_timeline CASCADE;

CREATE MATERIALIZED VIEW gazelle_client_timeline AS

SELECT DISTINCT ON (timeline_id)
    -- Timeline entry fields
    timeline_id,
    timeline_external_id,
    entry_date,
    occurred_at,
    created_at,
    entry_type,
    event_type,
    title,
    description,
    user_id,

    -- Piano fields
    piano_id,
    piano_external_id,
    piano_make,
    piano_model,
    piano_serial,
    piano_location,
    piano_year,
    piano_type,

    -- Client fields
    client_internal_id,
    client_external_id,
    company_name,
    client_city,
    client_postal_code,
    client_phone,
    client_email,

    -- Contact fields (premier contact trouvé)
    contact_id,
    contact_first_name,
    contact_last_name,
    contact_email,
    contact_phone,

    -- Search text
    search_text,

    -- Source type
    source_type

FROM (
    -- Source 1: Timeline entries directement liées au client (entity_type = 'CLIENT')
    SELECT
        t.id as timeline_id,
        t.external_id as timeline_external_id,
        t.entry_date,
        t.occurred_at,
        t.created_at,
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

        -- Contact fields (premier contact seulement)
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
        t.entry_date,
        t.occurred_at,
        t.created_at,
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

        -- Contact fields (premier contact seulement)
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
) AS combined_timeline

-- DISTINCT ON élimine les doublons en gardant la première ligne pour chaque timeline_id
ORDER BY timeline_id, contact_id NULLS LAST;


-- Index (inchangés)
CREATE INDEX idx_client_timeline_client_ext
ON gazelle_client_timeline(client_external_id);

CREATE INDEX idx_client_timeline_piano_ext
ON gazelle_client_timeline(piano_external_id)
WHERE piano_external_id IS NOT NULL;

CREATE INDEX idx_client_timeline_entry_date
ON gazelle_client_timeline(entry_date DESC NULLS LAST);

CREATE INDEX idx_client_timeline_search
ON gazelle_client_timeline USING gin(to_tsvector('french', search_text));

CREATE INDEX idx_client_timeline_source
ON gazelle_client_timeline(source_type);


-- Test de validation: Vérifier qu'il n'y a plus de doublons
SELECT
    timeline_id,
    COUNT(*) as occurrences
FROM gazelle_client_timeline
GROUP BY timeline_id
HAVING COUNT(*) > 1;

-- Devrait retourner 0 lignes si les doublons sont éliminés


-- Test: Historique de Monique (devrait avoir 27 entrées uniques, pas 50+)
SELECT
    COUNT(*) as total_entries,
    COUNT(DISTINCT timeline_id) as unique_entries
FROM gazelle_client_timeline
WHERE client_external_id = 'cli_Pc3O0Ybqvve64xcF';

-- Les deux nombres devraient être identiques
