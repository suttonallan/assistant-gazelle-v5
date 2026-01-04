-- Ajouter institution_slug à vincent_dindy_piano_updates pour isolation des données
-- Cette migration permet à plusieurs institutions de partager la même table

-- 1. Ajouter la colonne institution_slug (NULL pour l'instant)
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS institution_slug TEXT;

-- 2. Mettre à jour les données existantes (assumer vincent-dindy pour l'historique)
UPDATE public.vincent_dindy_piano_updates
SET institution_slug = 'vincent-dindy'
WHERE institution_slug IS NULL;

-- 3. Rendre la colonne NOT NULL maintenant qu'elle est remplie
ALTER TABLE public.vincent_dindy_piano_updates
ALTER COLUMN institution_slug SET NOT NULL;

-- 4. Définir la valeur par défaut pour les nouveaux inserts
ALTER TABLE public.vincent_dindy_piano_updates
ALTER COLUMN institution_slug SET DEFAULT 'vincent-dindy';

-- 5. Créer un index composite sur (institution_slug, piano_id) pour performance
CREATE INDEX IF NOT EXISTS idx_piano_updates_institution_piano
  ON public.vincent_dindy_piano_updates(institution_slug, piano_id);

-- 6. Créer un index sur institution_slug seul
CREATE INDEX IF NOT EXISTS idx_piano_updates_institution
  ON public.vincent_dindy_piano_updates(institution_slug);

-- 7. Modifier la PRIMARY KEY pour inclure institution_slug
-- ATTENTION: Ceci nécessite de dropper et recréer la contrainte
-- Commenté pour sécurité - à exécuter manuellement si nécessaire
-- ALTER TABLE public.vincent_dindy_piano_updates DROP CONSTRAINT vincent_dindy_piano_updates_pkey;
-- ALTER TABLE public.vincent_dindy_piano_updates ADD PRIMARY KEY (institution_slug, piano_id);

COMMENT ON COLUMN public.vincent_dindy_piano_updates.institution_slug IS
  'Slug de l''institution (vincent-dindy, orford, place-des-arts) - Permet l''isolation des données';
