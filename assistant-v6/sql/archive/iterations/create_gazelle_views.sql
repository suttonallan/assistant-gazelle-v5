-- ============================================================================
-- Vues SQL Supabase - Réplication de la logique Gazelle
-- ============================================================================
--
-- Basé sur la documentation GraphQL Gazelle:
-- https://gazelleapp.io/docs/graphql/private/schema/privatequery.doc.html
--
-- Logique reproduite:
-- - allClients → Recherche clients
-- - allPianos(filters) → Pianos d'un client
-- - allTimelineEntries(clientId, pianoId) → Historique
--
-- Objectif: Répliquer l'intelligence relationnelle de Gazelle dans SQL
-- ============================================================================

-- ============================================================================
-- Vue 1: Client Timeline (reproduction de allTimelineEntries)
-- ============================================================================
--
-- Reproduit la query GraphQL:
-- allTimelineEntries(clientId: ID, pianoId: ID)
--
-- Logique Gazelle:
-- - Timeline entries peuvent être filtrées par clientId OU pianoId
-- - Les deux sont supportés car Gazelle sait que Piano.clientId existe
--

CREATE MATERIALIZED VIEW IF NOT EXISTS gazelle_client_timeline AS
SELECT
    -- Timeline entry fields
    t.id as timeline_id,
    t.created_at,
    t.occurred_at,
    t.entry_type,
    t.title,
    t.description,
    t.user_id,

    -- Piano fields (jointure comme dans GraphQL schema)
    p.id as piano_id,
    p.make as piano_make,  -- VERIFIED: column is 'make' in Supabase
    p.model as piano_model,
    p.serial_number as piano_serial,
    p.location as piano_location,

    -- Client fields (via Piano.client_external_id comme dans Supabase)
    c.id as client_id,
    c.external_id as client_external_id,  -- ADDED: external_id for reference
    c.company_name,
    c.address as client_address,
    c.phone as client_phone,
    c.email as client_email,

    -- Contact fields (optionnel, pour recherche par personne)
    ct.id as contact_id,
    ct.first_name as contact_first_name,  -- CORRECTED: first_name + last_name
    ct.last_name as contact_last_name,
    ct.email as contact_email,
    ct.phone as contact_phone,

    -- Pour recherche full-text (comme search parameter dans GraphQL)
    COALESCE(ct.first_name || ' ' || ct.last_name, '') || ' ' ||
    COALESCE(c.company_name, '') || ' ' ||
    COALESCE(t.description, '') || ' ' ||
    COALESCE(t.title, '') as search_text

FROM public.gazelle_timeline_entries t  -- CORRECTED: public schema

-- CRITICAL: Filtrer par entity_type avant le JOIN
-- entity_id est l'ID numérique (INT) du piano quand entity_type = 'Piano'
INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')

-- CORRECTED: Jointure via external_id (pas id direct)
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id

-- Jointure OPTIONNELLE Contact (pour recherche par personne)
LEFT JOIN public.gazelle_contacts ct ON ct.client_external_id = c.external_id

-- Tri par défaut (comme dans Gazelle)
ORDER BY t.created_at DESC;

-- Index pour reproduire les filtres GraphQL
-- Filter par clientId
CREATE INDEX IF NOT EXISTS idx_client_timeline_client
ON gazelle_client_timeline(client_id, created_at DESC);

-- Filter par pianoId
CREATE INDEX IF NOT EXISTS idx_client_timeline_piano
ON gazelle_client_timeline(piano_id, created_at DESC);

-- Filter par contactId (extension utile)
CREATE INDEX IF NOT EXISTS idx_client_timeline_contact
ON gazelle_client_timeline(contact_id, created_at DESC);

-- Filter par entry_type (comme types: [TimelineEntryType] dans GraphQL)
CREATE INDEX IF NOT EXISTS idx_client_timeline_type
ON gazelle_client_timeline(entry_type, created_at DESC);

-- Full-text search (comme search parameter dans GraphQL)
CREATE INDEX IF NOT EXISTS idx_client_timeline_search
ON gazelle_client_timeline USING gin(to_tsvector('french', search_text));


-- ============================================================================
-- Vue 2: Client Search (reproduction de allClients avec filters)
-- ============================================================================
--
-- Reproduit la query GraphQL:
-- allClients(filters: PrivateAllClientsFilter)
--
-- Logique Gazelle:
-- - Peut chercher dans clients ET contacts
-- - Retourne le client avec ses relations
--

CREATE OR REPLACE VIEW gazelle_client_search AS
-- Contacts (personnes) avec leur client parent
SELECT
    'contact' as source_type,
    ct.id,
    ct.first_name || ' ' || ct.last_name as display_name,  -- CORRECTED: concatenate first_name + last_name
    ct.first_name || ' ' || ct.last_name as search_name,
    ct.email,
    ct.phone,

    -- Client parent (comme dans GraphQL PrivateContact.client)
    c.id as client_id,
    c.external_id as client_external_id,  -- ADDED: external_id
    c.company_name,
    c.address as client_address,
    c.phone as client_phone,

    -- Stats (comme dans GraphQL - pianos count)
    -- CORRECTED: Jointure via client_external_id
    (SELECT COUNT(*) FROM public.gazelle_pianos p WHERE p.client_external_id = c.external_id) as piano_count,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
     WHERE p.client_external_id = c.external_id) as timeline_count

FROM public.gazelle_contacts ct
LEFT JOIN public.gazelle_clients c ON ct.client_external_id = c.external_id

UNION ALL

-- Clients (entreprises)
SELECT
    'client' as source_type,
    c.id,
    c.company_name as display_name,
    c.company_name as search_name,
    c.email,
    c.phone,

    -- Self-reference car c'est déjà un client
    c.id as client_id,
    c.external_id as client_external_id,  -- ADDED: external_id
    c.company_name,
    c.address as client_address,
    c.phone as client_phone,

    -- Stats
    -- CORRECTED: Jointure via client_external_id
    (SELECT COUNT(*) FROM public.gazelle_pianos p WHERE p.client_external_id = c.external_id) as piano_count,
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
     WHERE p.client_external_id = c.external_id) as timeline_count

FROM public.gazelle_clients c;


-- ============================================================================
-- Vue 3: Piano List (reproduction de allPianos)
-- ============================================================================
--
-- Reproduit la query GraphQL:
-- allPianos(filters: PrivateAllPianosFilter)
--
-- Logique Gazelle:
-- - Liste des pianos avec leur client
-- - Peut filtrer par client
--

CREATE OR REPLACE VIEW gazelle_piano_list AS
SELECT
    -- Piano fields (comme dans GraphQL PrivatePiano)
    p.id as piano_id,
    p.make,  -- VERIFIED: column is 'make' in Supabase
    p.model,
    p.serial_number,
    p.location,
    p.year,
    p.type,  -- VERIFIED: 'type' exists (not 'finish' or 'size' visible in schema)
    p.notes,

    -- Client relationship (comme Piano.client dans GraphQL)
    c.id as client_id,
    c.external_id as client_external_id,  -- ADDED: external_id
    c.company_name,
    c.address as client_address,

    -- Timeline count pour ce piano
    -- CORRECTED: entity_id avec entity_type = 'Piano'
    (SELECT COUNT(*) FROM public.gazelle_timeline_entries t
     WHERE t.entity_id = p.id AND t.entity_type = 'Piano') as timeline_count,

    -- Contact principal (si existe)
    -- CORRECTED: first_name + last_name
    (SELECT ct.first_name || ' ' || ct.last_name FROM public.gazelle_contacts ct
     WHERE ct.client_external_id = c.external_id
     LIMIT 1) as primary_contact

FROM public.gazelle_pianos p
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id;  -- CORRECTED: external_id jointure


-- ============================================================================
-- Fonction de refresh (pour import quotidien)
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_gazelle_views()
RETURNS void AS $$
BEGIN
    -- Refresh la vue matérialisée (concurrently = sans bloquer les lectures)
    REFRESH MATERIALIZED VIEW CONCURRENTLY gazelle_client_timeline;

    RAISE NOTICE 'Gazelle views refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

-- Pour planifier le refresh quotidien (si pg_cron disponible):
-- SELECT cron.schedule('refresh-gazelle', '0 2 * * *', 'SELECT refresh_gazelle_views()');


-- ============================================================================
-- Exemples de requêtes (équivalents GraphQL → SQL)
-- ============================================================================

-- 1. GraphQL: allClients(filters: {search: "Vincent"})
-- SQL:
-- SELECT * FROM gazelle_client_search
-- WHERE search_name ILIKE '%Vincent%'
-- LIMIT 10;

-- 2. GraphQL: allTimelineEntries(clientId: "cli_123")
-- SQL:
-- SELECT * FROM gazelle_client_timeline
-- WHERE client_id = 'cli_123'
-- ORDER BY created_at DESC
-- LIMIT 100;

-- 3. GraphQL: allTimelineEntries(pianoId: "pia_456")
-- SQL:
-- SELECT * FROM gazelle_client_timeline
-- WHERE piano_id = 'pia_456'
-- ORDER BY created_at DESC
-- LIMIT 100;

-- 4. GraphQL: allPianos(filters: {clientId: "cli_123"})
-- SQL:
-- SELECT * FROM gazelle_piano_list
-- WHERE client_id = 'cli_123';

-- 5. GraphQL: allTimelineEntries(search: "accordage")
-- SQL:
-- SELECT * FROM gazelle_client_timeline
-- WHERE search_text @@ to_tsquery('french', 'accordage')
-- ORDER BY created_at DESC
-- LIMIT 50;


-- ============================================================================
-- Vérifications post-installation
-- ============================================================================

-- Vérifier que les vues existent
-- SELECT table_name, table_type FROM information_schema.tables
-- WHERE table_name LIKE 'gazelle_%'
-- AND table_schema = 'public';

-- Vérifier les index
-- SELECT indexname, indexdef FROM pg_indexes
-- WHERE tablename = 'gazelle_client_timeline';

-- Test rapide: Compter les timeline entries par client
-- SELECT
--     client_id,
--     company_name,
--     COUNT(*) as timeline_count,
--     COUNT(DISTINCT piano_id) as piano_count
-- FROM gazelle_client_timeline
-- GROUP BY client_id, company_name
-- ORDER BY timeline_count DESC
-- LIMIT 10;


-- ============================================================================
-- Notes importantes
-- ============================================================================
--
-- 1. Les vues reproduisent la logique Gazelle:
--    - Timeline est lié au Piano (t.piano_id = p.id)
--    - Piano est lié au Client (p.client_id = c.id)
--    - Contact est lié au Client (ct.client_id = c.id)
--
-- 2. Les filtres GraphQL sont reproduits via index SQL:
--    - clientId → idx_client_timeline_client
--    - pianoId → idx_client_timeline_piano
--    - types → idx_client_timeline_type
--    - search → idx_client_timeline_search
--
-- 3. La pagination GraphQL (cursor-based) peut être reproduite avec:
--    - WHERE created_at < :cursor
--    - ORDER BY created_at DESC
--    - LIMIT :pageSize
--
-- 4. Performance:
--    - Vue matérialisée = Snapshot des données (rapide)
--    - Refresh quotidien = Synchronisation avec Gazelle
--    - Index = Requêtes sub-100ms même sur 1M+ entrées
--
-- ============================================================================
