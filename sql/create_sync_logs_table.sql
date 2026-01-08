-- Table pour tracker les synchronisations automatiques (GitHub Actions, cron jobs, etc.)
-- Permet de monitorer les exécutions et diagnostiquer les problèmes

CREATE TABLE IF NOT EXISTS sync_logs (
    id BIGSERIAL PRIMARY KEY,
    script_name TEXT NOT NULL,              -- Nom du script (ex: 'GitHub_Timeline_Sync')
    status TEXT NOT NULL,                   -- 'success', 'error', 'warning'
    tables_updated JSONB,                   -- {"timeline": 50, "clients": 10}
    error_message TEXT,                     -- Message d'erreur si status='error'
    execution_time_seconds NUMERIC(10, 2),  -- Durée d'exécution
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour requêtes rapides
CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at ON sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_script_name ON sync_logs(script_name);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);

-- Commentaire
COMMENT ON TABLE sync_logs IS 'Logs des synchronisations automatiques (GitHub Actions, cron jobs)';
