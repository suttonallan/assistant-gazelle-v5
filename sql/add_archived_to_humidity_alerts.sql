-- Ajoute la colonne archived à humidity_alerts pour système 3 listes
-- (Non résolues / Résolues / Archivées)

-- Ajouter colonne archived
ALTER TABLE humidity_alerts
ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

-- Ajouter colonne resolved_at
ALTER TABLE humidity_alerts
ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;

-- Ajouter colonne resolution_notes
ALTER TABLE humidity_alerts
ADD COLUMN IF NOT EXISTS resolution_notes TEXT;

-- Index pour requêtes rapides
CREATE INDEX IF NOT EXISTS idx_humidity_alerts_archived ON humidity_alerts(archived);

-- Mettre à jour la vue pour inclure les alertes résolues aussi
CREATE OR REPLACE VIEW humidity_alerts_active AS
SELECT
    a.*,
    c.company_name AS client_name,
    p.make AS piano_make,
    p.model AS piano_model
FROM humidity_alerts a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
LEFT JOIN gazelle_pianos p ON a.piano_id::integer = p.id
WHERE a.archived = FALSE
ORDER BY a.is_resolved ASC, a.observed_at DESC;

-- Fonction: Marquer alerte comme résolue (avec notes)
CREATE OR REPLACE FUNCTION resolve_humidity_alert(
    alert_id UUID,
    notes TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE humidity_alerts
    SET
        is_resolved = TRUE,
        resolved_at = NOW(),
        resolution_notes = notes,
        updated_at = NOW()
    WHERE id = alert_id;
END;
$$ LANGUAGE plpgsql;

-- Fonction: Archiver une alerte
CREATE OR REPLACE FUNCTION archive_humidity_alert(alert_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE humidity_alerts
    SET
        archived = TRUE,
        updated_at = NOW()
    WHERE id = alert_id;
END;
$$ LANGUAGE plpgsql;

-- Commentaires
COMMENT ON COLUMN humidity_alerts.archived IS 'TRUE si alerte archivée (masquée de l''interface)';
COMMENT ON COLUMN humidity_alerts.resolved_at IS 'Date/heure de résolution';
COMMENT ON COLUMN humidity_alerts.resolution_notes IS 'Notes du technicien lors de la résolution';
