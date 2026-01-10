-- Migration: Créer table scheduler_logs
-- Date: 2026-01-10
-- Problème: Table scheduler_logs n'existe pas (erreur 404 répétitive dans logs)

-- Créer la table scheduler_logs
CREATE TABLE IF NOT EXISTS scheduler_logs (
    id BIGSERIAL PRIMARY KEY,
    job_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',  -- 'running', 'success', 'error'
    error_message TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_scheduler_logs_started_at ON scheduler_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scheduler_logs_job_name ON scheduler_logs(job_name);
CREATE INDEX IF NOT EXISTS idx_scheduler_logs_status ON scheduler_logs(status);

-- Commentaires
COMMENT ON TABLE scheduler_logs IS 'Logs d''exécution des tâches planifiées (cron jobs, background tasks)';
COMMENT ON COLUMN scheduler_logs.job_name IS 'Nom de la tâche (ex: "sync_gazelle", "humidity_scanner")';
COMMENT ON COLUMN scheduler_logs.status IS 'Status: running, success, error';
COMMENT ON COLUMN scheduler_logs.details IS 'Détails JSON de l''exécution (stats, erreurs, etc.)';

-- Politique RLS (si activée)
-- ALTER TABLE scheduler_logs ENABLE ROW LEVEL SECURITY;

-- Exemple d'insertion
-- INSERT INTO scheduler_logs (job_name, status, details)
-- VALUES ('sync_gazelle', 'success', '{"clients": 1344, "pianos": 1031}'::jsonb);
