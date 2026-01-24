-- Migration SQL pour compléter le schéma de sync_logs
-- Ajoute les colonnes manquantes utilisées par SyncLogger
-- Compatible avec le modèle de données attendu par le code

-- ============================================================
-- Colonnes manquantes à ajouter
-- ============================================================

-- task_type: Type de tâche ('sync', 'report', 'chain', 'backup')
ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS task_type VARCHAR(50) DEFAULT 'sync';

-- message: Message de succès ou description
ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS message TEXT;

-- stats: Statistiques structurées (JSONB pour flexibilité)
ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS stats JSONB DEFAULT '{}'::jsonb;

-- error_details: Message d'erreur détaillé (remplace/duplique error_message pour compatibilité)
ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS error_details TEXT;

-- triggered_by: Mode de déclenchement ('scheduler', 'manual', 'api')
ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(50) DEFAULT 'scheduler';

-- triggered_by_user: Email utilisateur si déclenchement manuel
ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS triggered_by_user VARCHAR(255);

-- ============================================================
-- Index pour améliorer les performances
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_sync_logs_task_type ON sync_logs(task_type);
CREATE INDEX IF NOT EXISTS idx_sync_logs_triggered_by ON sync_logs(triggered_by);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status_task_type ON sync_logs(status, task_type);

-- ============================================================
-- Migration des données existantes
-- ============================================================

-- Remplir task_type='sync' pour les enregistrements existants
UPDATE sync_logs
SET task_type = 'sync'
WHERE task_type IS NULL;

-- Remplir triggered_by='scheduler' pour les enregistrements existants
UPDATE sync_logs
SET triggered_by = 'scheduler'
WHERE triggered_by IS NULL;

-- Migrer error_message vers error_details si error_details est vide
UPDATE sync_logs
SET error_details = error_message
WHERE error_message IS NOT NULL AND error_details IS NULL;

-- Migrer tables_updated (JSON string) vers stats (JSONB) si stats est vide
UPDATE sync_logs
SET stats = CASE 
    WHEN tables_updated IS NOT NULL AND tables_updated::text != 'null' THEN
        CASE 
            WHEN tables_updated::text LIKE '{%' THEN tables_updated::jsonb
            ELSE ('{' || tables_updated::text || '}')::jsonb
        END
    ELSE '{}'::jsonb
END
WHERE (stats IS NULL OR stats = '{}'::jsonb) AND tables_updated IS NOT NULL;

-- ============================================================
-- Commentaires pour documentation
-- ============================================================

COMMENT ON COLUMN sync_logs.task_type IS 'Type de tâche: sync, report, chain, backup';
COMMENT ON COLUMN sync_logs.message IS 'Message de succès ou description de la synchronisation';
COMMENT ON COLUMN sync_logs.stats IS 'Statistiques structurées (JSONB) - remplace tables_updated';
COMMENT ON COLUMN sync_logs.error_details IS 'Message d''erreur détaillé (remplace error_message)';
COMMENT ON COLUMN sync_logs.triggered_by IS 'Mode de déclenchement: scheduler, manual, api';
COMMENT ON COLUMN sync_logs.triggered_by_user IS 'Email utilisateur si déclenchement manuel';

-- ============================================================
-- Vérification
-- ============================================================

-- Afficher un résumé (sera visible dans les logs Supabase)
DO $$
DECLARE
    total_count INTEGER;
    with_task_type INTEGER;
    with_message INTEGER;
    with_stats INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM sync_logs;
    SELECT COUNT(*) INTO with_task_type FROM sync_logs WHERE task_type IS NOT NULL;
    SELECT COUNT(*) INTO with_message FROM sync_logs WHERE message IS NOT NULL;
    SELECT COUNT(*) INTO with_stats FROM sync_logs WHERE stats IS NOT NULL AND stats != '{}'::jsonb;
    
    RAISE NOTICE 'Migration sync_logs terminée:';
    RAISE NOTICE '  Total enregistrements: %', total_count;
    RAISE NOTICE '  Avec task_type: %', with_task_type;
    RAISE NOTICE '  Avec message: %', with_message;
    RAISE NOTICE '  Avec stats: %', with_stats;
END $$;
