-- Expansion complète de la contrainte CHECK sur entry_type
-- pour refléter l'enum TimelineEntryType de Gazelle (28 valeurs)
-- + 2 valeurs legacy déjà présentes en base.
--
-- Contexte : depuis le 9 avril 2026, Gazelle envoie des entrées de type
-- CONTACT_PHONE_MANUAL_TALKED que la contrainte précédente (9 valeurs
-- seulement) rejetait, causant 1 erreur par sync quotidienne et le
-- status "warning" sur GitHub_Full_Sync. Introspection du schéma
-- Gazelle le 2026-04-12 a permis de récupérer la liste complète.
--
-- Risque : contrainte plus permissive → aucune ligne existante ne
-- peut être rejetée. Zéro réécriture de données.
--
-- Date: 2026-04-12

ALTER TABLE gazelle_timeline_entries
DROP CONSTRAINT IF EXISTS gazelle_timeline_entries_entry_type_check;

ALTER TABLE gazelle_timeline_entries
ADD CONSTRAINT gazelle_timeline_entries_entry_type_check
CHECK (entry_type IN (
    -- Valeurs Gazelle TimelineEntryType (introspection 2026-04-12)
    'CONTACT_EMAIL_AUTOMATED', 'CONTACT_EMAIL_MANUAL',
    'CONTACT_SMS_AUTOMATED', 'CONTACT_SMS_MANUAL',
    'CONTACT_PHONE_AUTOMATED',
    'CONTACT_PHONE_MANUAL_TALKED', 'CONTACT_PHONE_MANUAL_MESSAGE',
    'CONTACT_POST_AUTOMATED', 'CONTACT_POST_MANUAL',
    'CONTACT_OTHER_MANUAL',
    'ERROR_MESSAGE', 'SYSTEM_MESSAGE', 'SYSTEM_NOTIFICATION',
    'USER_COMMENT',
    'SERVICE_ENTRY_AUTOMATED', 'SERVICE_ENTRY_MANUAL',
    'APPOINTMENT', 'APPOINTMENT_LOG', 'APPOINTMENT_COMPLETION',
    'INVOICE', 'INVOICE_LOG', 'INVOICE_PAYMENT', 'INVOICE_SYNC',
    'PIANO_MEASUREMENT',
    'SCHEDULED_MESSAGE_EMAIL', 'SCHEDULED_MESSAGE_SMS', 'SCHEDULED_MESSAGE_PHONE',
    'ESTIMATE', 'ESTIMATE_LOG',
    -- Legacy (valeurs déjà en base, normalisées par le sync script
    -- avant l'introspection — à ne pas retirer sinon rows existantes casseraient)
    'NOTE', 'CONTACT_EMAIL'
));

NOTIFY pgrst, 'reload schema';

COMMENT ON CONSTRAINT gazelle_timeline_entries_entry_type_check
ON gazelle_timeline_entries
IS 'Autorise les 28 TimelineEntryType de Gazelle + 2 valeurs legacy. Introspection 2026-04-12.';
