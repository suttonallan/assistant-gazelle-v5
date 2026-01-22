-- Table pour les alertes affichées sur le Dashboard
-- Type 'URGENCE_CONFIRMATION' pour les RV non confirmés J-1

CREATE TABLE IF NOT EXISTS dashboard_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(50) NOT NULL,  -- 'URGENCE_CONFIRMATION', etc.
    severity VARCHAR(20) NOT NULL DEFAULT 'warning',  -- 'info', 'warning', 'error', 'success'
    title VARCHAR(255) NOT NULL,
    message TEXT,
    technician_id VARCHAR(255),  -- ID du technicien concerné
    technician_name VARCHAR(255),  -- Nom du technicien
    appointment_id VARCHAR(255),  -- ID du rendez-vous concerné
    client_name VARCHAR(255),  -- Nom du client
    appointment_date DATE,
    appointment_time TIME,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(255),
    metadata JSONB,  -- Données supplémentaires (flexible)
    
    CONSTRAINT dashboard_alerts_type_check CHECK (type IN ('URGENCE_CONFIRMATION', 'SYNC_ERROR', 'HUMIDITY_ALERT', 'OTHER')),
    CONSTRAINT dashboard_alerts_severity_check CHECK (severity IN ('info', 'warning', 'error', 'success'))
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_dashboard_alerts_type ON dashboard_alerts(type);
CREATE INDEX IF NOT EXISTS idx_dashboard_alerts_technician ON dashboard_alerts(technician_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_alerts_acknowledged ON dashboard_alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_dashboard_alerts_created ON dashboard_alerts(created_at DESC);

-- Vue pour les alertes non reconnues (pour le Dashboard)
CREATE OR REPLACE VIEW v_dashboard_alerts_pending AS
SELECT 
    id,
    type,
    severity,
    title,
    message,
    technician_id,
    technician_name,
    appointment_id,
    client_name,
    appointment_date,
    appointment_time,
    created_at,
    metadata
FROM dashboard_alerts
WHERE acknowledged = FALSE
ORDER BY created_at DESC;

COMMENT ON TABLE dashboard_alerts IS 'Alertes affichées sur le Dashboard (RV non confirmés, erreurs, etc.)';
COMMENT ON COLUMN dashboard_alerts.type IS 'Type d''alerte: URGENCE_CONFIRMATION pour RV non confirmés J-1';
COMMENT ON COLUMN dashboard_alerts.severity IS 'Niveau de sévérité: warning (rouge) pour URGENCE_CONFIRMATION';
