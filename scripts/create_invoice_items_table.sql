-- Créer la table gazelle_invoice_items
-- Date: 2025-12-27

CREATE TABLE IF NOT EXISTS gazelle_invoice_items (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    invoice_external_id TEXT NOT NULL,
    
    -- Détails de l'item
    description TEXT,
    type TEXT,  -- SERVICE, PRODUCT, etc.
    sequence_number INTEGER,
    
    -- Quantités et montants
    quantity DECIMAL(10, 2),
    amount DECIMAL(10, 2),
    sub_total DECIMAL(10, 2),
    tax_total DECIMAL(10, 2),
    total DECIMAL(10, 2),
    
    -- Flags
    billable BOOLEAN DEFAULT TRUE,
    taxable BOOLEAN DEFAULT TRUE,
    
    -- Métadonnées
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index pour recherches par facture
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice
ON gazelle_invoice_items(invoice_external_id);

-- Index pour recherches par type (service vs produit)
CREATE INDEX IF NOT EXISTS idx_invoice_items_type
ON gazelle_invoice_items(type);

-- Index pour recherches par external_id
CREATE INDEX IF NOT EXISTS idx_invoice_items_external_id
ON gazelle_invoice_items(external_id);

COMMENT ON TABLE gazelle_invoice_items IS 'Line items des factures Gazelle (services et produits vendus)';
COMMENT ON COLUMN gazelle_invoice_items.type IS 'Type d''item: SERVICE, PRODUCT, etc.';
COMMENT ON COLUMN gazelle_invoice_items.invoice_external_id IS 'Référence à la facture parente (format: inv_xxx)';
