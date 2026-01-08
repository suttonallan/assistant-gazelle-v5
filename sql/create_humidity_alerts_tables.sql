-- Tables pour système d'alertes humidité
-- Porté depuis V4 (SQL Server) vers V5 (Supabase)
-- Source: MaintenanceAlerts (V4)

-- Table principale: alertes humidité détectées
CREATE TABLE IF NOT EXISTS humidity_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timeline_entry_id TEXT NOT NULL,
    client_id TEXT,
    piano_id TEXT,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('housse', 'alimentation', 'reservoir', 'autre')),
    description TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Index
    UNIQUE(timeline_entry_id, alert_type)
);

-- Index pour recherche rapide
CREATE INDEX IF NOT EXISTS idx_humidity_alerts_client ON humidity_alerts(client_id);
CREATE INDEX IF NOT EXISTS idx_humidity_alerts_piano ON humidity_alerts(piano_id);
CREATE INDEX IF NOT EXISTS idx_humidity_alerts_type ON humidity_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_humidity_alerts_resolved ON humidity_alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_humidity_alerts_observed ON humidity_alerts(observed_at DESC);

-- Table historique: timeline entries déjà scannées
CREATE TABLE IF NOT EXISTS humidity_alerts_history (
    timeline_entry_id TEXT PRIMARY KEY,
    scanned_at TIMESTAMPTZ DEFAULT NOW(),
    found_issues BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_humidity_history_scanned ON humidity_alerts_history(scanned_at DESC);

-- Vue: Alertes actives (non résolues)
CREATE OR REPLACE VIEW humidity_alerts_active AS
SELECT
    a.*,
    c.company_name AS client_name,
    p.make AS piano_make,
    p.model AS piano_model
FROM humidity_alerts a
LEFT JOIN gazelle_clients c ON a.client_id = c.external_id
LEFT JOIN gazelle_pianos p ON a.piano_id::integer = p.id
WHERE a.is_resolved = FALSE
ORDER BY a.observed_at DESC;

-- Vue: Stats par type
CREATE OR REPLACE VIEW humidity_alerts_stats AS
SELECT
    alert_type,
    COUNT(*) AS total,
    SUM(CASE WHEN is_resolved THEN 1 ELSE 0 END) AS resolved,
    SUM(CASE WHEN NOT is_resolved THEN 1 ELSE 0 END) AS active,
    MAX(observed_at) AS last_occurrence
FROM humidity_alerts
GROUP BY alert_type
ORDER BY total DESC;

-- Fonction: Marquer alerte comme résolue
CREATE OR REPLACE FUNCTION resolve_humidity_alert(alert_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE humidity_alerts
    SET
        is_resolved = TRUE,
        updated_at = NOW()
    WHERE id = alert_id;
END;
$$ LANGUAGE plpgsql;

-- Commentaires
COMMENT ON TABLE humidity_alerts IS 'Alertes humidité détectées automatiquement dans timeline entries';
COMMENT ON TABLE humidity_alerts_history IS 'Historique des timeline entries scannées (évite double scan)';
COMMENT ON COLUMN humidity_alerts.alert_type IS 'Type: housse | alimentation | reservoir | autre';
COMMENT ON COLUMN humidity_alerts.is_resolved IS 'TRUE si problème résolu (détecté dans même entry ou entry ultérieure)';
