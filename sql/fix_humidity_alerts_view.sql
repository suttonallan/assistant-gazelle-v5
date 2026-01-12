-- Correction de la vue humidity_alerts_active
-- Problème: piano_id peut être un ID d'instrument (ins_xxx) ou de piano
-- Solution: Garder piano_id comme TEXT et ne pas le convertir

DROP VIEW IF EXISTS humidity_alerts_active;

CREATE OR REPLACE VIEW humidity_alerts_active AS
SELECT
    a.*,
    c.company_name AS client_name,
    -- Essayer d'abord de joindre avec les pianos par ID numérique
    COALESCE(
        (SELECT make FROM gazelle_pianos WHERE id::text = a.piano_id LIMIT 1),
        NULL
    ) AS piano_make,
    COALESCE(
        (SELECT model FROM gazelle_pianos WHERE id::text = a.piano_id LIMIT 1),
        NULL
    ) AS piano_model
FROM humidity_alerts a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
WHERE a.archived = FALSE
ORDER BY a.is_resolved ASC, a.observed_at DESC;

COMMENT ON VIEW humidity_alerts_active IS 'Vue des alertes d''humidité non archivées avec informations client et piano';
