-- Table pour l'apprentissage des preferences de revision de soumissions
-- Stocke les decisions d'Allan (acceptees ET refusees) pour que l'agent apprenne

CREATE TABLE IF NOT EXISTS estimate_review_preferences (
    id serial PRIMARY KEY,
    category text NOT NULL,          -- 'naming', 'description', 'missing_item', 'price_adjustment', 'bonus_item', 'notes'
    item_key text NOT NULL,          -- MSL item ID (mit_xxx) ou nom generique
    original text,                   -- ce qui existait ou ce que l'agent avait propose
    preferred text NOT NULL,         -- ce qu'Allan a valide/corrige
    accepted boolean NOT NULL DEFAULT true,  -- true = accepte, false = refuse
    scope text DEFAULT 'global',     -- 'global' ou 'estimate_12345' (ponctuel)
    created_at timestamptz DEFAULT now()
);

-- Index pour recherche rapide par categorie et item
CREATE INDEX IF NOT EXISTS idx_erp_category ON estimate_review_preferences(category);
CREATE INDEX IF NOT EXISTS idx_erp_item_key ON estimate_review_preferences(item_key);
CREATE INDEX IF NOT EXISTS idx_erp_scope ON estimate_review_preferences(scope);
