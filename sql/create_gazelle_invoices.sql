-- Table des factures Gazelle
CREATE TABLE IF NOT EXISTS gazelle_invoices (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    client_id TEXT,
    invoice_number TEXT,
    invoice_date DATE,
    status TEXT,
    sub_total NUMERIC(10,2),
    total NUMERIC(10,2),
    notes TEXT,
    due_on DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoices_client ON gazelle_invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON gazelle_invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_number ON gazelle_invoices(invoice_number);

-- Table des lignes de facture
CREATE TABLE IF NOT EXISTS gazelle_invoice_items (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    invoice_external_id TEXT REFERENCES gazelle_invoices(external_id),
    description TEXT,
    item_type TEXT,
    quantity NUMERIC(10,2),
    amount NUMERIC(10,2),
    sub_total NUMERIC(10,2),
    tax_total NUMERIC(10,2),
    total NUMERIC(10,2),
    billable BOOLEAN DEFAULT TRUE,
    taxable BOOLEAN DEFAULT TRUE,
    sequence_number INTEGER
);

CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON gazelle_invoice_items(invoice_external_id);
CREATE INDEX IF NOT EXISTS idx_invoice_items_desc ON gazelle_invoice_items USING gin(to_tsvector('french', description));

COMMENT ON TABLE gazelle_invoices IS 'Factures synchronisées depuis Gazelle API';
COMMENT ON TABLE gazelle_invoice_items IS 'Lignes de facture détaillées';
