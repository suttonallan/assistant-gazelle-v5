-- ============================================================
-- FIX: Contrainte unique pour inventaire_techniciens
-- ============================================================
-- Problème: Les changements de quantité ne persistent pas
-- Cause probable: Pas de contrainte unique sur (code_produit, technicien, emplacement)
-- Solution: Créer un index unique partiel ou une contrainte unique

-- Vérifier si la contrainte existe déjà
DO $$
BEGIN
    -- Vérifier si l'index unique existe
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'inventaire_techniciens' 
        AND indexname = 'idx_inventaire_techniciens_unique'
    ) THEN
        -- Créer un index unique sur (code_produit, technicien, emplacement)
        -- Cela permettra à l'UPSERT de fonctionner correctement
        CREATE UNIQUE INDEX IF NOT EXISTS idx_inventaire_techniciens_unique 
        ON inventaire_techniciens(code_produit, technicien, emplacement);
        
        RAISE NOTICE '✅ Index unique créé sur (code_produit, technicien, emplacement)';
    ELSE
        RAISE NOTICE '✅ Index unique existe déjà';
    END IF;
END $$;

-- Commentaire pour documentation
COMMENT ON INDEX idx_inventaire_techniciens_unique IS 
'Contrainte unique pour permettre UPSERT correct sur inventaire_techniciens. 
Permet de mettre à jour le stock d''un produit pour un technicien à un emplacement spécifique.';
