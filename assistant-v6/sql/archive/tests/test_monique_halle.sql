-- ============================================================================
-- Test SQL pour Monique Hallé
-- ============================================================================
--
-- External ID: cli_Pc300Ybqvve64xcF
-- Internal ID: 202
--
-- Basé sur la structure VÉRIFIÉE par Gemini:
-- - Tables: public.gazelle_clients, public.gazelle_pianos,
--           public.gazelle_contacts, public.gazelle_timeline_entries
-- - Jointures via external_id (pas id direct)
-- - Piano.brand (pas make)
-- - Contact.first_name + last_name (pas full_name)
-- ============================================================================

-- ============================================================================
-- Étape 1: Vérifier que Monique Hallé existe
-- ============================================================================

-- 1a. Chercher dans les clients
SELECT
    id,
    external_id,
    company_name,
    'client' as source
FROM public.gazelle_clients
WHERE external_id = 'cli_Pc300Ybqvve64xcF'
   OR id = 202
   OR company_name ILIKE '%Monique Hallé%';

-- 1b. Chercher dans les contacts
SELECT
    id,
    client_id,
    first_name,
    last_name,
    first_name || ' ' || last_name as full_name,
    'contact' as source
FROM public.gazelle_contacts
WHERE first_name ILIKE '%Monique%'
   OR last_name ILIKE '%Hallé%'
   OR (first_name || ' ' || last_name) ILIKE '%Monique Hallé%';


-- ============================================================================
-- Étape 2: Trouver les pianos de Monique Hallé
-- ============================================================================

-- CRITICAL: Jointure via client_external_id (pas client_id)
SELECT
    p.id as piano_id,
    p.brand,
    p.model,
    p.serial_number,
    p.location,
    p.client_external_id,
    c.company_name,
    c.id as client_internal_id
FROM public.gazelle_pianos p
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
WHERE c.external_id = 'cli_Pc300Ybqvve64xcF'
   OR c.id = 202;


-- ============================================================================
-- Étape 3: Trouver la timeline des pianos de Monique Hallé
-- ============================================================================

-- CRITICAL:
-- - entity_type = 'Piano' pour filtrer
-- - entity_id = piano.id (ID numérique INT)
SELECT
    t.id as timeline_id,
    t.created_at,
    t.occurred_at,
    t.entry_type,
    t.title,
    t.description,
    t.entity_type,
    t.entity_id,
    p.id as piano_id,
    p.brand,
    p.model,
    c.company_name
FROM public.gazelle_timeline_entries t
-- Jointure Piano via entity_id (INT) quand entity_type = 'Piano'
INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
-- Jointure Client via external_id
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
WHERE c.external_id = 'cli_Pc300Ybqvve64xcF'
   OR c.id = 202
ORDER BY t.created_at DESC
LIMIT 100;


-- ============================================================================
-- Étape 4: Compter les entrées de timeline pour Monique Hallé
-- ============================================================================

SELECT
    COUNT(*) as total_timeline_entries,
    COUNT(DISTINCT p.id) as total_pianos,
    c.company_name,
    c.external_id
FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
WHERE c.external_id = 'cli_Pc300Ybqvve64xcF'
   OR c.id = 202
GROUP BY c.company_name, c.external_id;


-- ============================================================================
-- Étape 5: Vérifier les autres types d'entity_type
-- ============================================================================

-- Timeline entries directement liées au client (entity_type = 'Client')
SELECT
    t.id,
    t.created_at,
    t.title,
    t.entity_type,
    t.entity_id,
    'Direct client link' as note
FROM public.gazelle_timeline_entries t
WHERE t.entity_type = 'Client'
  AND t.entity_id = 'cli_Pc300Ybqvve64xcF'
ORDER BY t.created_at DESC
LIMIT 50;


-- ============================================================================
-- Étape 6: Vue complète unifiée (Piano + Client timeline)
-- ============================================================================

-- Timeline via Pianos
SELECT
    t.id,
    t.created_at,
    t.title,
    t.description,
    t.entity_type,
    'Via Piano' as source,
    p.brand || ' ' || p.model as piano_info
FROM public.gazelle_timeline_entries t
INNER JOIN public.gazelle_pianos p ON (t.entity_id = p.id AND t.entity_type = 'Piano')
INNER JOIN public.gazelle_clients c ON p.client_external_id = c.external_id
WHERE c.external_id = 'cli_Pc300Ybqvve64xcF'

UNION ALL

-- Timeline directement liée au client
SELECT
    t.id,
    t.created_at,
    t.title,
    t.description,
    t.entity_type,
    'Direct Client' as source,
    NULL as piano_info
FROM public.gazelle_timeline_entries t
WHERE t.entity_type = 'Client'
  AND t.entity_id = 'cli_Pc300Ybqvve64xcF'

ORDER BY created_at DESC
LIMIT 100;


-- ============================================================================
-- Notes importantes
-- ============================================================================
--
-- 1. TOUJOURS utiliser:
--    - public.gazelle_* (pas gazelle.*)
--    - client_external_id (pas client_id) pour jointures Piano→Client
--    - entity_id + entity_type pour Timeline
--    - brand (pas make) pour Piano
--    - first_name + last_name (pas full_name) pour Contact
--
-- 2. entity_type peut être:
--    - 'Piano' → entity_id est un INT (piano.id)
--    - 'Client' → entity_id est une STRING (client.external_id)
--    - 'Contact' → entity_id est un INT (contact.id)
--
-- 3. Pour avoir TOUTE la timeline d'un client:
--    - Timeline via Pianos (entity_type = 'Piano')
--    - Timeline directe (entity_type = 'Client')
--    - UNION ALL pour combiner
--
-- ============================================================================
