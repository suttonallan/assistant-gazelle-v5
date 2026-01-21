-- Ajouter la colonne task_label à scheduler_logs pour le système de logging
-- Cette colonne stocke le libellé lisible de la tâche (ex: "Sync Gazelle Totale")

ALTER TABLE scheduler_logs 
ADD COLUMN IF NOT EXISTS task_label TEXT;

-- Ajouter un commentaire pour documenter
COMMENT ON COLUMN scheduler_logs.task_label IS 'Libellé affiché dans l''UI pour la tâche planifiée';

-- Mettre à jour les lignes existantes (si elles existent) avec des valeurs par défaut
UPDATE scheduler_logs
SET task_label = 
    CASE 
        WHEN task_name = 'sync_gazelle' THEN 'Sync Gazelle Totale'
        WHEN task_name = 'rapport_timeline' THEN 'Rapport Timeline Google Sheets'
        WHEN task_name = 'backup_database' THEN 'Backup SQL'
        WHEN task_name = 'sync_rv_alerts' THEN 'Sync RV & Alertes'
        ELSE task_name
    END
WHERE task_label IS NULL;
