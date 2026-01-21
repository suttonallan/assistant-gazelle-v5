-- ============================================================
-- Table: sync_logs
-- Description: Logs des synchronisations et chaînes de tâches
-- Usage: Tracer toutes les exécutions de sync (Gazelle, Timeline, etc.)
-- ============================================================

CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- Identification de la tâche
    script_name TEXT NOT NULL,              -- Nom du script (ex: 'Sync Gazelle Totale')
    task_type TEXT NOT NULL,                -- Type (ex: 'sync', 'report', 'chain')
    
    -- Statut
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'warning', 'running')),
    
    -- Détails
    message TEXT,                           -- Message de succès ou d'erreur
    stats JSONB DEFAULT '{}'::jsonb,        -- Statistiques (nb clients, pianos, etc.)
    error_details TEXT,                     -- Stack trace si erreur
    
    -- Traçabilité
    triggered_by TEXT DEFAULT 'scheduler',  -- 'scheduler', 'manual', 'api'
    triggered_by_user TEXT,                 -- Email utilisateur si manuel
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    execution_time_seconds INTEGER,         -- Durée d'exécution
    
    -- Index pour performance
    CONSTRAINT sync_logs_status_check CHECK (status IN ('success', 'error', 'warning', 'running'))
);

-- Index pour requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_sync_logs_created_at ON sync_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_task_type ON sync_logs(task_type);

-- Vue pratique pour le Dashboard
CREATE OR REPLACE VIEW v_recent_sync_logs AS
SELECT 
    id,
    script_name,
    task_type,
    status,
    message,
    stats,
    triggered_by,
    created_at,
    execution_time_seconds,
    CASE 
        WHEN status = 'success' THEN '✅'
        WHEN status = 'error' THEN '❌'
        WHEN status = 'warning' THEN '⚠️'
        WHEN status = 'running' THEN '⏳'
        ELSE '❓'
    END as status_emoji
FROM sync_logs
ORDER BY created_at DESC
LIMIT 50;

-- Commentaires pour documentation
COMMENT ON TABLE sync_logs IS 'Logs des synchronisations et chaînes de tâches orchestrées';
COMMENT ON COLUMN sync_logs.script_name IS 'Nom lisible de la tâche (ex: "Sync Gazelle Totale")';
COMMENT ON COLUMN sync_logs.task_type IS 'Type de tâche: sync, report, chain, backup';
COMMENT ON COLUMN sync_logs.stats IS 'Statistiques JSON (clients, pianos, timeline, etc.)';
COMMENT ON COLUMN sync_logs.execution_time_seconds IS 'Durée totale d''exécution en secondes';
