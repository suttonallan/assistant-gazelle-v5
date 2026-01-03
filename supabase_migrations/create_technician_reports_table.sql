-- Table pour stocker les rapports de techniciens
-- Remplace l'ancien système GitHub Gist par du stockage Supabase natif

CREATE TABLE IF NOT EXISTS technician_reports (
    id TEXT PRIMARY KEY,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processed')),
    report JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index pour améliorer les performances de recherche
CREATE INDEX IF NOT EXISTS idx_technician_reports_status ON technician_reports(status);
CREATE INDEX IF NOT EXISTS idx_technician_reports_submitted_at ON technician_reports(submitted_at DESC);

-- Commentaires pour la documentation
COMMENT ON TABLE technician_reports IS 'Rapports soumis par les techniciens via Vincent d''Indy ou autres assistants';
COMMENT ON COLUMN technician_reports.id IS 'ID unique du rapport (format: report_YYYYMMDD_HHMMSS)';
COMMENT ON COLUMN technician_reports.submitted_at IS 'Date et heure de soumission du rapport';
COMMENT ON COLUMN technician_reports.status IS 'Statut du rapport (pending, processed)';
COMMENT ON COLUMN technician_reports.report IS 'Données complètes du rapport (format JSONB pour flexibilité)';
