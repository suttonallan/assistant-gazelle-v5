-- Table pour stocker les rapports de techniciens (Vincent d'Indy)
CREATE TABLE IF NOT EXISTS technician_reports (
    id TEXT PRIMARY KEY,
    technician_name TEXT NOT NULL,
    client_name TEXT,
    client_id TEXT,
    date TEXT NOT NULL,
    report_type TEXT NOT NULL,
    description TEXT NOT NULL,
    notes TEXT,
    hours_worked FLOAT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour améliorer les performances des requêtes
CREATE INDEX IF NOT EXISTS idx_technician_reports_status ON technician_reports(status);
CREATE INDEX IF NOT EXISTS idx_technician_reports_date ON technician_reports(date);
CREATE INDEX IF NOT EXISTS idx_technician_reports_submitted_at ON technician_reports(submitted_at DESC);

-- Trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_technician_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER technician_reports_updated_at
    BEFORE UPDATE ON technician_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_technician_reports_updated_at();
