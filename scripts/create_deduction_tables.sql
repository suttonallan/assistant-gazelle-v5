-- ============================================================
-- Tables pour Configuration des Déductions d'Inventaire
-- ============================================================

-- Table pour règles de déduction par mots-clés
CREATE TABLE IF NOT EXISTS keyword_deduction_rules (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    material_code_produit TEXT NOT NULL,
    quantity FLOAT DEFAULT 1.0,
    case_sensitive BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour recherche rapide par keyword
CREATE INDEX IF NOT EXISTS idx_keyword_deduction_rules_keyword
ON keyword_deduction_rules(keyword);

-- Index pour recherche par produit
CREATE INDEX IF NOT EXISTS idx_keyword_deduction_rules_material
ON keyword_deduction_rules(material_code_produit);

-- Trigger pour auto-update de updated_at
CREATE OR REPLACE FUNCTION update_keyword_deduction_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_keyword_deduction_rules_updated_at ON keyword_deduction_rules;
CREATE TRIGGER trigger_keyword_deduction_rules_updated_at
BEFORE UPDATE ON keyword_deduction_rules
FOR EACH ROW
EXECUTE FUNCTION update_keyword_deduction_rules_updated_at();

-- ============================================================
-- Exemples de règles par défaut
-- ============================================================

-- Règle 1: Buvard remplacé
INSERT INTO keyword_deduction_rules (keyword, material_code_produit, quantity, case_sensitive, notes)
VALUES (
    'Buvard remplacé',
    'BUV-001',
    1.0,
    false,
    'Déduction automatique quand le mot "Buvard remplacé" est détecté dans les notes'
) ON CONFLICT DO NOTHING;

-- Règle 2: Hygrostat sec
INSERT INTO keyword_deduction_rules (keyword, material_code_produit, quantity, case_sensitive, notes)
VALUES (
    'Hygrostat sec',
    'HYGRO-SEC',
    1.0,
    false,
    'Déduction automatique pour hygrostat sec'
) ON CONFLICT DO NOTHING;

-- Règle 3: Gaine changée
INSERT INTO keyword_deduction_rules (keyword, material_code_produit, quantity, case_sensitive, notes)
VALUES (
    'Gaine changée',
    'GAIN-001',
    1.0,
    false,
    'Déduction automatique quand une gaine est changée'
) ON CONFLICT DO NOTHING;

-- ============================================================
-- Commentaires sur les tables
-- ============================================================

COMMENT ON TABLE keyword_deduction_rules IS
'Règles de déduction basées sur la détection de mots-clés dans les notes de factures';

COMMENT ON COLUMN keyword_deduction_rules.keyword IS
'Mot-clé à détecter (ex: "Buvard remplacé")';

COMMENT ON COLUMN keyword_deduction_rules.material_code_produit IS
'Code du produit à déduire du stock';

COMMENT ON COLUMN keyword_deduction_rules.quantity IS
'Quantité à déduire (défaut: 1.0)';

COMMENT ON COLUMN keyword_deduction_rules.case_sensitive IS
'Si true, la détection est sensible à la casse';

COMMENT ON COLUMN keyword_deduction_rules.notes IS
'Notes explicatives sur la règle';

-- ============================================================
-- Vérification des tables existantes
-- ============================================================

-- Vérifier que service_inventory_consumption existe déjà
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name IN ('service_inventory_consumption', 'keyword_deduction_rules')
ORDER BY table_name, ordinal_position;
