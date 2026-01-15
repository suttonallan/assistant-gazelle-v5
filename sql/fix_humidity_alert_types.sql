-- Fix: Autoriser le type "environnement" dans humidity_alerts
-- Problème: La contrainte CHECK n'accepte pas "environnement"
-- Solution: Modifier la contrainte pour inclure tous les types nécessaires

-- Étape 1: Supprimer l'ancienne contrainte
ALTER TABLE humidity_alerts
DROP CONSTRAINT IF EXISTS humidity_alerts_alert_type_check;

-- Étape 2: Créer la nouvelle contrainte avec tous les types
ALTER TABLE humidity_alerts
ADD CONSTRAINT humidity_alerts_alert_type_check
CHECK (alert_type IN ('housse', 'alimentation', 'reservoir', 'environnement'));

-- Vérification
SELECT conname, pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'humidity_alerts'::regclass
AND conname = 'humidity_alerts_alert_type_check';
