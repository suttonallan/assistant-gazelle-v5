-- Migration V6: Table de Monitoring/Observabilité
-- Date: 2025-12-28
-- Description: Tracking de l'état des synchronisations
--
-- Cette table répond aux 3 questions critiques:
-- 1. Quand a eu lieu le dernier succès?
-- 2. Combien de lignes ont été ignorées/échouées?
-- 3. Quelle est la fraîcheur des données?

-- ============================================================
-- TABLE: sync_status
-- ============================================================
CREATE TABLE IF NOT EXISTS sync_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification
    sync_type TEXT NOT NULL,              -- 'timeline', 'clients', 'pianos', 'users'
    sync_mode TEXT DEFAULT 'incremental', -- 'incremental', 'full', 'repair'

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_seconds FLOAT,

    -- État
    status TEXT NOT NULL,                 -- 'running', 'success', 'partial', 'failed'
    CHECK (status IN ('running', 'success', 'partial', 'failed')),

    -- Métriques de données
    records_fetched INT DEFAULT 0,        -- Récupérés depuis Gazelle
    records_staged INT DEFAULT 0,         -- Insérés dans staging
    records_processed INT DEFAULT 0,      -- Transformés en production
    records_skipped INT DEFAULT 0,        -- Ignorés (validation failed)
    records_failed INT DEFAULT 0,         -- Échecs techniques

    -- Métriques de santé
    error_rate FLOAT GENERATED ALWAYS AS (
        CASE
            WHEN records_fetched > 0
            THEN (records_failed::FLOAT / records_fetched::FLOAT) * 100
            ELSE 0
        END
    ) STORED,

    data_freshness_score FLOAT,           -- 0-100% (calculé par reconciler)

    -- Détails techniques
    api_calls_made INT DEFAULT 0,
    api_rate_limit_hits INT DEFAULT 0,

    -- Debugging
    error_summary JSONB,                  -- Résumé des erreurs par type
    performance_metrics JSONB,            -- Temps par étape, etc.
    metadata JSONB,                       -- Infos contextuelles

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour queries fréquentes
CREATE INDEX IF NOT EXISTS idx_sync_status_type_created
    ON sync_status(sync_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sync_status_status
    ON sync_status(status);

CREATE INDEX IF NOT EXISTS idx_sync_status_completed
    ON sync_status(completed_at DESC) WHERE completed_at IS NOT NULL;

-- Index partiel pour syncs actifs
CREATE INDEX IF NOT EXISTS idx_sync_status_running
    ON sync_status(started_at DESC)
    WHERE status = 'running';

COMMENT ON TABLE sync_status IS
    'Historique et monitoring des synchronisations Gazelle (V6)';

-- ============================================================
-- FUNCTION: Démarrer une nouvelle sync
-- ============================================================
CREATE OR REPLACE FUNCTION start_sync(
    p_sync_type TEXT,
    p_sync_mode TEXT DEFAULT 'incremental'
)
RETURNS UUID AS $$
DECLARE
    v_sync_id UUID;
BEGIN
    INSERT INTO sync_status (sync_type, sync_mode, started_at, status)
    VALUES (p_sync_type, p_sync_mode, NOW(), 'running')
    RETURNING id INTO v_sync_id;

    RETURN v_sync_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION: Terminer une sync avec succès
-- ============================================================
CREATE OR REPLACE FUNCTION complete_sync(
    p_sync_id UUID,
    p_records_fetched INT DEFAULT 0,
    p_records_staged INT DEFAULT 0,
    p_records_processed INT DEFAULT 0,
    p_records_skipped INT DEFAULT 0,
    p_records_failed INT DEFAULT 0,
    p_data_freshness_score FLOAT DEFAULT NULL,
    p_performance_metrics JSONB DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_started_at TIMESTAMPTZ;
    v_duration FLOAT;
    v_final_status TEXT;
BEGIN
    -- Récupérer start time
    SELECT started_at INTO v_started_at
    FROM sync_status
    WHERE id = p_sync_id;

    -- Calculer durée
    v_duration := EXTRACT(EPOCH FROM (NOW() - v_started_at));

    -- Déterminer status final
    IF p_records_failed > 0 THEN
        v_final_status := 'partial';
    ELSE
        v_final_status := 'success';
    END IF;

    -- Update
    UPDATE sync_status
    SET
        completed_at = NOW(),
        duration_seconds = v_duration,
        status = v_final_status,
        records_fetched = p_records_fetched,
        records_staged = p_records_staged,
        records_processed = p_records_processed,
        records_skipped = p_records_skipped,
        records_failed = p_records_failed,
        data_freshness_score = p_data_freshness_score,
        performance_metrics = p_performance_metrics
    WHERE id = p_sync_id;

    RAISE NOTICE '✓ Sync % completed: % records processed in % seconds',
        p_sync_id, p_records_processed, v_duration;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- FUNCTION: Marquer sync comme échouée
-- ============================================================
CREATE OR REPLACE FUNCTION fail_sync(
    p_sync_id UUID,
    p_error_message TEXT,
    p_error_details JSONB DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_started_at TIMESTAMPTZ;
    v_duration FLOAT;
BEGIN
    SELECT started_at INTO v_started_at
    FROM sync_status
    WHERE id = p_sync_id;

    v_duration := EXTRACT(EPOCH FROM (NOW() - v_started_at));

    UPDATE sync_status
    SET
        completed_at = NOW(),
        duration_seconds = v_duration,
        status = 'failed',
        error_summary = jsonb_build_object(
            'message', p_error_message,
            'details', p_error_details
        )
    WHERE id = p_sync_id;

    RAISE WARNING '✗ Sync % failed after % seconds: %',
        p_sync_id, v_duration, p_error_message;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VIEW: Dashboard de santé
-- ============================================================
CREATE OR REPLACE VIEW v_sync_health AS
SELECT
    sync_type,
    MAX(completed_at) as last_successful_sync,
    COUNT(*) FILTER (WHERE status = 'failed' AND created_at > NOW() - INTERVAL '24 hours') as failures_last_24h,
    COUNT(*) FILTER (WHERE status = 'running') as currently_running,
    AVG(data_freshness_score) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as avg_freshness_7d,
    AVG(duration_seconds) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as avg_duration_7d,
    SUM(records_processed) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as records_last_24h
FROM sync_status
WHERE completed_at IS NOT NULL
GROUP BY sync_type
ORDER BY sync_type;

COMMENT ON VIEW v_sync_health IS
    'Dashboard rapide de santé des syncs par type';

-- ============================================================
-- VIEW: Dernières erreurs
-- ============================================================
CREATE OR REPLACE VIEW v_recent_errors AS
SELECT
    sync_type,
    started_at,
    completed_at,
    duration_seconds,
    records_fetched,
    records_failed,
    error_rate,
    error_summary->>'message' as error_message
FROM sync_status
WHERE status IN ('failed', 'partial')
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 50;

COMMENT ON VIEW v_recent_errors IS
    'Dernières erreurs de sync (7 derniers jours)';

-- ============================================================
-- FUNCTION: Stats rapides pour API
-- ============================================================
CREATE OR REPLACE FUNCTION get_sync_stats()
RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
BEGIN
    SELECT jsonb_object_agg(
        sync_type,
        jsonb_build_object(
            'last_sync', last_successful_sync,
            'freshness', COALESCE(avg_freshness_7d, 0),
            'status', CASE
                WHEN currently_running > 0 THEN 'running'
                WHEN failures_last_24h > 3 THEN 'unhealthy'
                WHEN failures_last_24h > 0 THEN 'degraded'
                ELSE 'healthy'
            END,
            'records_24h', COALESCE(records_last_24h, 0)
        )
    )
    INTO v_result
    FROM v_sync_health;

    RETURN COALESCE(v_result, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_sync_stats IS
    'Retourne stats JSON pour API /api/v6/health';

-- ============================================================
-- FUNCTION: Nettoyer ancien historique
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_sync_history(retention_days INT DEFAULT 90)
RETURNS BIGINT AS $$
DECLARE
    v_deleted BIGINT;
BEGIN
    DELETE FROM sync_status
    WHERE created_at < NOW() - (retention_days || ' days')::INTERVAL
      AND status IN ('success', 'partial');  -- Garder les erreurs plus longtemps

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RAISE NOTICE '✓ Deleted % old sync records (> % days)',
        v_deleted, retention_days;

    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- VÉRIFICATION
-- ============================================================
DO $$
BEGIN
    -- Vérifier table créée
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sync_status') THEN
        RAISE NOTICE '✓ Table sync_status créée';
    END IF;

    -- Vérifier views
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'v_sync_health') THEN
        RAISE NOTICE '✓ View v_sync_health créée';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'v_recent_errors') THEN
        RAISE NOTICE '✓ View v_recent_errors créée';
    END IF;
END $$;

-- ============================================================
-- USAGE EXAMPLES
-- ============================================================

-- 1. Démarrer une sync:
-- SELECT start_sync('timeline', 'incremental');
-- Retourne: UUID du sync job

-- 2. Terminer une sync avec succès:
-- SELECT complete_sync(
--     'uuid-du-sync',
--     1000,  -- fetched
--     1000,  -- staged
--     995,   -- processed
--     5,     -- skipped
--     0,     -- failed
--     98.5   -- freshness score
-- );

-- 3. Marquer comme échec:
-- SELECT fail_sync('uuid-du-sync', 'API Gazelle timeout');

-- 4. Voir dashboard:
-- SELECT * FROM v_sync_health;

-- 5. Voir erreurs récentes:
-- SELECT * FROM v_recent_errors;

-- 6. Stats API JSON:
-- SELECT get_sync_stats();

-- 7. Nettoyer historique (garder 90 jours):
-- SELECT cleanup_sync_history(90);
