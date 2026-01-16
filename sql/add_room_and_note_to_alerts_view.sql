-- Enrichir la vue humidity_alerts_active avec:
-- 1. room_number (numéro de local du piano)
-- 2. technician_note (texte exact de la timeline entry)

DROP VIEW IF EXISTS humidity_alerts_active;

CREATE OR REPLACE VIEW humidity_alerts_active AS
SELECT
    a.*,
    c.company_name AS client_name,
    -- Piano info (make & model)
    COALESCE(
        (SELECT make FROM gazelle_pianos WHERE external_id = a.piano_id LIMIT 1),
        NULL
    ) AS piano_make,
    COALESCE(
        (SELECT model FROM gazelle_pianos WHERE external_id = a.piano_id LIMIT 1),
        NULL
    ) AS piano_model,
    -- NOUVEAU: Numéro de local
    COALESCE(
        (SELECT location FROM gazelle_pianos WHERE external_id = a.piano_id LIMIT 1),
        'N/A'
    ) AS room_number,
    -- NOUVEAU: Texte exact du technicien depuis timeline entry
    COALESCE(
        (SELECT description FROM gazelle_timeline_entries WHERE external_id = a.timeline_entry_id LIMIT 1),
        (SELECT title FROM gazelle_timeline_entries WHERE external_id = a.timeline_entry_id LIMIT 1),
        a.description  -- Fallback sur la description de l'alerte
    ) AS technician_note
FROM humidity_alerts a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
WHERE a.archived = FALSE
ORDER BY a.is_resolved ASC, a.observed_at DESC;

COMMENT ON VIEW humidity_alerts_active IS 'Vue des alertes d''humidité non archivées avec informations enrichies: client, piano, local et note technicien';
