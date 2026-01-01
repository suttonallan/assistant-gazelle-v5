-- ============================================================================
-- Vue SQL pour Assistant v6 - Timeline Unifié
-- ============================================================================
--
-- Cette vue matérialisée combine:
-- - Contacts (personnes)
-- - Clients (entreprises)
-- - Pianos (instruments)
-- - Timeline entries (historique de service)
--
-- Avantages:
-- 1. Import quotidien simplifié (un seul REFRESH)
-- 2. Requêtes Python ultra-simples (1 query au lieu de 4)
-- 3. Performance optimisée (PostgreSQL gère les JOINs)
-- 4. Maintenance facile (modifier la vue, pas le code Python)
--
-- ============================================================================

-- Vue matérialisée: Timeline complet avec toutes les relations
CREATE MATERIALIZED VIEW IF NOT EXISTS client_timeline_view AS
SELECT
    -- Timeline entry
    t.id as timeline_id,
    t.created_at,
    t.occurred_at,
    t.entry_type,
    t.title,
    t.description,

    -- Piano
    p.id as piano_id,
    p.make as piano_make,
    p.model as piano_model,
    p.serial_number as piano_serial,

    -- Client (entreprise)
    cl.id as client_id,
    cl.company_name,
    cl.address as client_address,
    cl.phone as client_phone,

    -- Contact (personne)
    c.id as contact_id,
    c.full_name as contact_name,
    c.email as contact_email,
    c.phone as contact_phone,

    -- Pour recherche full-text
    COALESCE(c.full_name, '') || ' ' ||
    COALESCE(cl.company_name, '') || ' ' ||
    COALESCE(t.description, '') as search_text

FROM gazelle.timeline_entries t
JOIN gazelle.pianos p ON t.piano_id = p.id
JOIN gazelle.clients cl ON p.client_id = cl.id
LEFT JOIN gazelle.contacts c ON c.client_id = cl.id

ORDER BY t.created_at DESC;

-- Index pour recherche rapide par client
CREATE INDEX IF NOT EXISTS idx_timeline_view_client
ON client_timeline_view(client_id, created_at DESC);

-- Index pour recherche rapide par contact
CREATE INDEX IF NOT EXISTS idx_timeline_view_contact
ON client_timeline_view(contact_id, created_at DESC);

-- Index pour recherche rapide par piano
CREATE INDEX IF NOT EXISTS idx_timeline_view_piano
ON client_timeline_view(piano_id, created_at DESC);

-- Index full-text pour recherche par nom/description
CREATE INDEX IF NOT EXISTS idx_timeline_view_search
ON client_timeline_view USING gin(to_tsvector('french', search_text));


-- ============================================================================
-- Vue pour recherche de clients/contacts (sans timeline)
-- ============================================================================

CREATE OR REPLACE VIEW client_search_view AS
-- Contacts (personnes)
SELECT
    'contact' as source_type,
    c.id,
    c.full_name as display_name,
    c.full_name as search_name,
    c.email,
    c.phone,
    cl.id as client_id,
    cl.company_name,
    COUNT(DISTINCT p.id) as piano_count
FROM gazelle.contacts c
LEFT JOIN gazelle.clients cl ON c.client_id = cl.id
LEFT JOIN gazelle.pianos p ON p.client_id = cl.id
GROUP BY c.id, c.full_name, c.email, c.phone, cl.id, cl.company_name

UNION ALL

-- Clients (entreprises)
SELECT
    'client' as source_type,
    cl.id,
    cl.company_name as display_name,
    cl.company_name as search_name,
    NULL as email,
    cl.phone,
    cl.id as client_id,
    cl.company_name,
    COUNT(DISTINCT p.id) as piano_count
FROM gazelle.clients cl
LEFT JOIN gazelle.pianos p ON p.client_id = cl.id
GROUP BY cl.id, cl.company_name, cl.phone;


-- ============================================================================
-- Fonction pour refresh quotidien
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_timeline_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY client_timeline_view;
    RAISE NOTICE 'Timeline view refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Planifier le refresh quotidien (nécessite pg_cron)
-- ============================================================================
--
-- SELECT cron.schedule('refresh-timeline', '0 2 * * *', 'SELECT refresh_timeline_view()');
-- (Tous les jours à 2h du matin)
--


-- ============================================================================
-- Exemples de requêtes simplifiées
-- ============================================================================

-- 1. Rechercher un contact/client par nom
-- SELECT * FROM client_search_view
-- WHERE search_name ILIKE '%Monique Hallé%'
-- LIMIT 10;

-- 2. Timeline complet d'un client
-- SELECT * FROM client_timeline_view
-- WHERE client_id = 'cli_xxx'
-- ORDER BY created_at DESC
-- LIMIT 100;

-- 3. Timeline d'un contact spécifique
-- SELECT * FROM client_timeline_view
-- WHERE contact_id = 'con_xxx'
-- ORDER BY created_at DESC
-- LIMIT 100;

-- 4. Recherche full-text dans timeline
-- SELECT * FROM client_timeline_view
-- WHERE search_text @@ to_tsquery('french', 'accordage')
-- ORDER BY created_at DESC
-- LIMIT 50;

-- ============================================================================
-- Statistiques
-- ============================================================================

-- Nombre total d'entrées timeline
-- SELECT COUNT(*) FROM client_timeline_view;

-- Nombre d'entrées par client
-- SELECT client_id, company_name, COUNT(*) as entry_count
-- FROM client_timeline_view
-- GROUP BY client_id, company_name
-- ORDER BY entry_count DESC
-- LIMIT 20;

-- Distribution par type d'événement
-- SELECT entry_type, COUNT(*) as count
-- FROM client_timeline_view
-- GROUP BY entry_type
-- ORDER BY count DESC;
