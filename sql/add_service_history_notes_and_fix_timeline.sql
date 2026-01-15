-- Migration pour aligner Supabase avec Gazelle serviceHistoryNotes
-- Basé sur l'analyse NotebookLM et les instructions de Luke

-- 1. Ajout de la colonne pour l'alignement strict avec Gazelle serviceHistoryNotes
ALTER TABLE technician_reports
ADD COLUMN IF NOT EXISTS service_history_notes TEXT;

-- 2. Correction du mapping : Transférer les descriptions existantes vers les notes de service
UPDATE technician_reports
SET service_history_notes = description
WHERE service_history_notes IS NULL;

-- 3. Mise à jour de la table de synchronisation de la timeline pour éviter de perdre les données de Luke
-- Correction du type 'SERVICE' (hallucination) vers les types réels de Gazelle (Source 44)

-- 3a. D'abord, supprimer la contrainte existante si elle existe
ALTER TABLE gazelle_timeline_entries
DROP CONSTRAINT IF EXISTS gazelle_timeline_entries_entry_type_check;

-- 3b. Corriger les données existantes : Remplacer 'SERVICE' par 'NOTE'
UPDATE gazelle_timeline_entries
SET entry_type = 'NOTE'
WHERE entry_type = 'SERVICE';

-- 3c. Corriger tous les types invalides vers 'NOTE' (fallback sécuritaire)
UPDATE gazelle_timeline_entries
SET entry_type = 'NOTE'
WHERE entry_type NOT IN ('APPOINTMENT', 'CONTACT_EMAIL', 'NOTE', 'APPOINTMENT_COMPLETION', 'SYSTEM_NOTIFICATION');

-- 3d. Maintenant, ajouter la contrainte avec les types valides
ALTER TABLE gazelle_timeline_entries
ADD CONSTRAINT gazelle_timeline_entries_entry_type_check
CHECK (entry_type IN ('APPOINTMENT', 'CONTACT_EMAIL', 'NOTE', 'APPOINTMENT_COMPLETION', 'SYSTEM_NOTIFICATION'));

-- 4. Création d'un index pour accélérer le "Global Watcher" recommandé par Gamini (Source 11)
CREATE INDEX IF NOT EXISTS idx_timeline_occurred_at_get
ON gazelle_timeline_entries (occurred_at DESC);

-- 5. Commentaire de documentation pour l'Assistant
COMMENT ON COLUMN technician_reports.service_history_notes IS 'Contenu envoyé à Gazelle via serviceHistoryNotes dans la mutation completeEvent';
