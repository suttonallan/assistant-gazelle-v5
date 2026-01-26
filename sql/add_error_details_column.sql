-- Ajouter la colonne error_details manquante à sync_logs
-- À exécuter dans Supabase SQL Editor

ALTER TABLE sync_logs
ADD COLUMN IF NOT EXISTS error_details TEXT;

-- Copier les error_message existants vers error_details si la colonne error_message existe
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name = 'sync_logs' AND column_name = 'error_message') THEN
        UPDATE sync_logs
        SET error_details = error_message
        WHERE error_details IS NULL AND error_message IS NOT NULL;
    END IF;
END $$;

-- Vérification
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'sync_logs'
ORDER BY ordinal_position;
