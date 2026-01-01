-- ============================================================
-- TABLE: scheduler_logs
-- Description: Journal des exécutions des tâches planifiées
-- ============================================================

CREATE TABLE IF NOT EXISTS scheduler_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Informations sur la tâche
    task_name TEXT NOT NULL,  -- 'sync_gazelle', 'rapport_timeline', 'backup', 'rv_alerts'
    task_label TEXT NOT NULL, -- 'Sync Gazelle Totale', 'Rapport Timeline', etc.

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER, -- Durée en secondes

    -- Résultat
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'running')),
    message TEXT, -- Message de détail ou erreur

    -- Statistiques (optionnel, JSON pour flexibilité)
    stats JSONB DEFAULT '{}'::jsonb,

    -- Trigger
    triggered_by TEXT DEFAULT 'scheduler', -- 'scheduler', 'manual', 'api'
    triggered_by_user TEXT, -- Email de l'utilisateur si manual

    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_scheduler_logs_started_at ON scheduler_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduler_logs_task_name ON scheduler_logs(task_name);
CREATE INDEX IF NOT EXISTS idx_scheduler_logs_status ON scheduler_logs(status);

-- RLS (Row Level Security) - Lecture seule pour tous les utilisateurs authentifiés
ALTER TABLE scheduler_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Lecture publique des logs scheduler"
ON scheduler_logs FOR SELECT
USING (true);

CREATE POLICY "Insertion via service_role uniquement"
ON scheduler_logs FOR INSERT
WITH CHECK (auth.role() = 'service_role');

-- Commentaires
COMMENT ON TABLE scheduler_logs IS 'Journal des exécutions des tâches planifiées du scheduler';
COMMENT ON COLUMN scheduler_logs.task_name IS 'Nom technique de la tâche';
COMMENT ON COLUMN scheduler_logs.task_label IS 'Libellé affiché dans l''UI';
COMMENT ON COLUMN scheduler_logs.status IS 'Statut: success, error, running';
COMMENT ON COLUMN scheduler_logs.stats IS 'Statistiques JSON (ex: {clients: 150, pianos: 250})';
COMMENT ON COLUMN scheduler_logs.triggered_by IS 'Mode de déclenchement: scheduler, manual, api';
