-- Migration V6: Création des tables Staging
-- Date: 2025-12-28
-- Description: Zone de transit pour données Gazelle brutes
--
-- Principe: ACCEPTER TOUT, ne jamais rejeter
-- Ces tables sont des buffers temporaires avant réconciliation

-- ============================================================
-- TABLE: stg_timeline_entries
-- ============================================================
CREATE TABLE IF NOT EXISTS stg_timeline_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Données brutes Gazelle (JSON complet)
    raw_data JSONB NOT NULL,

    -- Métadata de sync
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    external_id TEXT,                     -- ID Gazelle (pour dédupe)

    -- État de traitement
    processed BOOLEAN DEFAULT FALSE,
    processing_attempts INT DEFAULT 0,
    last_processed_at TIMESTAMPTZ,

    -- Gestion erreurs
    last_error TEXT,
    error_details JSONB,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_stg_timeline_processed
    ON stg_timeline_entries(processed);

CREATE INDEX IF NOT EXISTS idx_stg_timeline_fetched
    ON stg_timeline_entries(fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_stg_timeline_external_id
    ON stg_timeline_entries(external_id);

-- Index pour queries fréquentes
CREATE INDEX IF NOT EXISTS idx_stg_timeline_unprocessed
    ON stg_timeline_entries(created_at)
    WHERE processed = FALSE;

COMMENT ON TABLE stg_timeline_entries IS
    'Buffer staging pour timeline entries Gazelle (V6)';

-- ============================================================
-- TABLE: stg_clients
-- ============================================================
CREATE TABLE IF NOT EXISTS stg_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    external_id TEXT,
    processed BOOLEAN DEFAULT FALSE,
    processing_attempts INT DEFAULT 0,
    last_processed_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stg_clients_processed
    ON stg_clients(processed);
CREATE INDEX IF NOT EXISTS idx_stg_clients_external_id
    ON stg_clients(external_id);

COMMENT ON TABLE stg_clients IS
    'Buffer staging pour clients Gazelle (V6)';

-- ============================================================
-- TABLE: stg_pianos
-- ============================================================
CREATE TABLE IF NOT EXISTS stg_pianos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    external_id TEXT,
    processed BOOLEAN DEFAULT FALSE,
    processing_attempts INT DEFAULT 0,
    last_processed_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stg_pianos_processed
    ON stg_pianos(processed);
CREATE INDEX IF NOT EXISTS idx_stg_pianos_external_id
    ON stg_pianos(external_id);

COMMENT ON TABLE stg_pianos IS
    'Buffer staging pour pianos Gazelle (V6)';

-- ============================================================
-- TABLE: stg_users
-- ============================================================
CREATE TABLE IF NOT EXISTS stg_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_data JSONB NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    external_id TEXT,
    processed BOOLEAN DEFAULT FALSE,
    processing_attempts INT DEFAULT 0,
    last_processed_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stg_users_processed
    ON stg_users(processed);
CREATE INDEX IF NOT EXISTS idx_stg_users_external_id
    ON stg_users(external_id);

COMMENT ON TABLE stg_users IS
    'Buffer staging pour users/techniciens Gazelle (V6)';

-- ============================================================
-- TRIGGER: Auto-update updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Appliquer trigger à toutes les tables staging
CREATE TRIGGER update_stg_timeline_updated_at
    BEFORE UPDATE ON stg_timeline_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stg_clients_updated_at
    BEFORE UPDATE ON stg_clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stg_pianos_updated_at
    BEFORE UPDATE ON stg_pianos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stg_users_updated_at
    BEFORE UPDATE ON stg_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- FUNCTION: Nettoyage automatique des données traitées
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_processed_staging_data(retention_days INT DEFAULT 30)
RETURNS TABLE(table_name TEXT, rows_deleted BIGINT) AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;

    -- Timeline entries
    DELETE FROM stg_timeline_entries
    WHERE processed = TRUE AND updated_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'stg_timeline_entries';
    RETURN NEXT;

    -- Clients
    DELETE FROM stg_clients
    WHERE processed = TRUE AND updated_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'stg_clients';
    RETURN NEXT;

    -- Pianos
    DELETE FROM stg_pianos
    WHERE processed = TRUE AND updated_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'stg_pianos';
    RETURN NEXT;

    -- Users
    DELETE FROM stg_users
    WHERE processed = TRUE AND updated_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'stg_users';
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_processed_staging_data IS
    'Nettoie les données staging traitées de plus de X jours';

-- ============================================================
-- VÉRIFICATION
-- ============================================================
DO $$
DECLARE
    v_count INT;
BEGIN
    -- Compter les tables staging créées
    SELECT COUNT(*) INTO v_count
    FROM information_schema.tables
    WHERE table_name LIKE 'stg_%'
    AND table_schema = 'public';

    RAISE NOTICE '✓ % tables staging créées', v_count;

    -- Vérifier les index
    SELECT COUNT(*) INTO v_count
    FROM pg_indexes
    WHERE tablename LIKE 'stg_%';

    RAISE NOTICE '✓ % index créés', v_count;

    -- Vérifier les triggers
    SELECT COUNT(*) INTO v_count
    FROM pg_trigger
    WHERE tgname LIKE '%stg_%';

    RAISE NOTICE '✓ % triggers créés', v_count;
END $$;

-- ============================================================
-- USAGE
-- ============================================================
-- Insérer une entrée:
-- INSERT INTO stg_timeline_entries (raw_data, external_id)
-- VALUES ('{"id": "tme_123", ...}'::JSONB, 'tme_123');

-- Marquer comme traité:
-- UPDATE stg_timeline_entries
-- SET processed = TRUE, last_processed_at = NOW()
-- WHERE id = '...';

-- Nettoyer les anciennes données (30 jours par défaut):
-- SELECT * FROM cleanup_processed_staging_data(30);

-- Voir les erreurs de processing:
-- SELECT external_id, last_error, processing_attempts
-- FROM stg_timeline_entries
-- WHERE processing_attempts > 0
-- ORDER BY processing_attempts DESC;
