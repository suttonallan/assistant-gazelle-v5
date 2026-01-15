-- CORRECTIF URGENT: Ajouter SERVICE_ENTRY_MANUAL et PIANO_MEASUREMENT à la contrainte
-- Ces types sont ESSENTIELS pour le rapport Google Sheets
--
-- PROBLÈME: La migration add_service_history_notes_and_fix_timeline.sql avait une contrainte
-- trop restrictive qui bloquait les services et mesures depuis le 10 janvier
--
-- Date: 2026-01-15
-- Ticket: Rapports Google Sheets vides depuis le 10 janvier

-- 1. Supprimer l'ancienne contrainte trop restrictive
ALTER TABLE gazelle_timeline_entries
DROP CONSTRAINT IF EXISTS gazelle_timeline_entries_entry_type_check;

-- 2. Ajouter la nouvelle contrainte avec TOUS les types valides
ALTER TABLE gazelle_timeline_entries
ADD CONSTRAINT gazelle_timeline_entries_entry_type_check
CHECK (entry_type IN (
    'APPOINTMENT',
    'CONTACT_EMAIL',
    'NOTE',
    'APPOINTMENT_COMPLETION',
    'SYSTEM_NOTIFICATION',
    'SERVICE_ENTRY_MANUAL',      -- ⚠️ CRITIQUE pour rapports Google Sheets
    'PIANO_MEASUREMENT',          -- ⚠️ CRITIQUE pour rapports Google Sheets
    'INVOICE_PAYMENT',            -- Paiements factures
    'ERROR_MESSAGE'               -- Messages d'erreur système
));

-- 3. Forcer le reload du schéma PostgREST
NOTIFY pgrst, 'reload schema';

-- 4. Commentaire de documentation
COMMENT ON CONSTRAINT gazelle_timeline_entries_entry_type_check
ON gazelle_timeline_entries
IS 'Contrainte sur entry_type incluant SERVICE_ENTRY_MANUAL et PIANO_MEASUREMENT pour sync rapports';
