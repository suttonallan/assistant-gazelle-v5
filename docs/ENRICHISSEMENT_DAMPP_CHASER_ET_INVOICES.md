# Enrichissement Dampp-Chaser et Invoice Items

**Date:** 2025-12-27
**Statut:** ✅ Prêt pour exécution

## 🎯 Objectifs

1. **Système d'humidité** - Afficher si un piano a un système Dampp-Chaser installé
2. **Items vendus** - Lister les services vs accessoires vendus par facture

## 📋 Changements Implémentés

### 1. Client API GraphQL Enrichi

**Fichier:** `core/gazelle_api_client.py`

#### A) Pianos - Ajout champs Dampp-Chaser
```python
# Champs ajoutés à la query GetPianos:
damppChaserInstalled         # Boolean - Système installé?
damppChaserHumidistatModel   # String - Modèle du thermostat
damppChaserMfgDate           # Date - Date de fabrication
```

#### B) Invoices - Ajout line items
```python
# Ajout de la structure allInvoiceItems dans GetInvoices:
allInvoiceItems {
    nodes {
        id                    # External ID de l'item
        description          # Description du service/produit
        type                 # SERVICE, PRODUCT, etc.
        quantity             # Quantité
        amount               # Montant unitaire
        subTotal, taxTotal, total  # Totaux
        billable, taxable    # Flags
        sequenceNumber       # Ordre d'affichage
    }
}
```

### 2. Schéma SQL Supabase

#### A) Colonnes Dampp-Chaser sur `gazelle_pianos`

**Script:** `scripts/add_dampp_chaser_columns.sql`

```sql
ALTER TABLE gazelle_pianos
ADD COLUMN IF NOT EXISTS dampp_chaser_installed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS dampp_chaser_humidistat_model TEXT,
ADD COLUMN IF NOT EXISTS dampp_chaser_mfg_date DATE;

-- Index pour recherche rapide
CREATE INDEX idx_pianos_dampp_chaser
ON gazelle_pianos(dampp_chaser_installed)
WHERE dampp_chaser_installed = TRUE;
```

**À exécuter dans:** Supabase SQL Editor

#### B) Table `gazelle_invoice_items`

**Script:** `scripts/create_invoice_items_table.sql`

```sql
CREATE TABLE gazelle_invoice_items (
    id SERIAL PRIMARY KEY,
    external_id TEXT UNIQUE NOT NULL,
    invoice_external_id TEXT NOT NULL,

    -- Détails
    description TEXT,
    type TEXT,  -- SERVICE, PRODUCT, etc.
    sequence_number INTEGER,

    -- Montants
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

-- Index pour recherches
CREATE INDEX idx_invoice_items_invoice ON gazelle_invoice_items(invoice_external_id);
CREATE INDEX idx_invoice_items_type ON gazelle_invoice_items(type);
```

**À exécuter dans:** Supabase SQL Editor

### 3. Script d'Import Invoice Items

**Fichier:** `scripts/import_invoice_items.py`

**Fonctionnalités:**
- Récupère toutes les factures avec leurs line items via GraphQL
- Extrait les items (services + produits)
- Insère dans `gazelle_invoice_items` par lots de 100
- Affiche statistiques par type (SERVICE vs PRODUCT)

**Usage:**
```bash
python3 scripts/import_invoice_items.py
```

## 🚀 Plan d'Exécution

### Étape 1: Mise à jour Supabase (SQL)

```bash
# Dans Supabase SQL Editor, exécuter dans l'ordre:
1. scripts/add_dampp_chaser_columns.sql
2. scripts/create_invoice_items_table.sql
```

### Étape 2: Réimport des Pianos (avec Dampp-Chaser)

```bash
# Le script existant utilise maintenant les nouveaux champs automatiquement
python3 scripts/import_pianos.py
```

**Résultat attendu:**
```
✅ X pianos importés
  - Y avec Dampp-Chaser installé
  - Modèles: [liste des modèles d'humidistat]
```

### Étape 3: Import des Invoice Items

```bash
python3 scripts/import_invoice_items.py
```

**Résultat attendu:**
```
✅ X line items synchronisés
📊 Statistiques par type:
  - SERVICE: X items
  - PRODUCT: Y items
  - [autres types...]
```

## 📊 Cas d'Usage

### 1. Affichage Système Humidité dans RV

**Avant RV, le technicien voit:**
```
📅 RV Michelle Alie - 2026-01-10 14h00
🎹 Piano: Yamaha C3 (1995)
💧 Dampp-Chaser: ✅ Installé (Modèle: DCS-2000, Mfg: 2010-03-15)
   → Apporter: Buvards de rechange, solution nettoyante
```

**Query pour récupérer l'info:**
```python
piano = supabase.table('gazelle_pianos').select('*').eq('id', piano_id).single().execute()

if piano.data.get('dampp_chaser_installed'):
    model = piano.data.get('dampp_chaser_humidistat_model')
    print(f"💧 Dampp-Chaser: ✅ Installé (Modèle: {model})")
else:
    print(f"💧 Pas de système de contrôle d'humidité")
```

### 2. Liste Items Vendus pour Michelle Alie

**Query pour récupérer les items:**
```python
# 1. Trouver les invoice_id dans la timeline
timeline = supabase.table('gazelle_timeline_entries')\
    .select('invoice_id')\
    .eq('client_external_id', 'cli_vHOW5lpHtNqGv9cY')\
    .not_.is_('invoice_id', 'null')\
    .execute()

invoice_ids = [e['invoice_id'] for e in timeline.data]

# 2. Récupérer les items pour ces factures
items = supabase.table('gazelle_invoice_items')\
    .select('*')\
    .in_('invoice_external_id', invoice_ids)\
    .execute()

# 3. Grouper par type
services = [i for i in items.data if i['type'] == 'SERVICE']
products = [i for i in items.data if i['type'] == 'PRODUCT']

print(f"📊 Items vendus:")
print(f"  🔧 Services: {len(services)} ({sum(s['total'] for s in services)}$)")
print(f"  📦 Produits: {len(products)} ({sum(p['total'] for p in products)}$)")
```

**Affichage attendu:**
```
📊 Items vendus à Michelle Alie:

🔧 SERVICES (8 items - 1,840.00$):
  - Accord 442hz (2024-10-02): 180.00$
  - Grand entretien piano à queue (2023-12-14): 360.00$
  - Calibration système Quiet Time (2024-02-19): 120.00$
  - Lubrification pivots marteaux (2024-10-02): 80.00$
  [...]

📦 PRODUITS/ACCESSOIRES (3 items - 125.00$):
  - Buvards Dampp-Chaser (2024-10-02): 45.00$
  - Solution nettoyante (2023-12-14): 35.00$
  - [...]

💰 TOTAL: 1,965.00$
```

## ✅ Vérification Post-Import

### Pianos avec Dampp-Chaser
```sql
SELECT
    make,
    model,
    dampp_chaser_humidistat_model,
    dampp_chaser_mfg_date
FROM gazelle_pianos
WHERE dampp_chaser_installed = TRUE
LIMIT 10;
```

### Invoice Items par Type
```sql
SELECT
    type,
    COUNT(*) as count,
    SUM(total) as total_amount
FROM gazelle_invoice_items
GROUP BY type
ORDER BY count DESC;
```

### Items pour une facture spécifique
```sql
SELECT
    description,
    type,
    quantity,
    amount,
    total
FROM gazelle_invoice_items
WHERE invoice_external_id = 'inv_xxx'
ORDER BY sequence_number;
```

## 📝 Notes Importantes

1. **Dampp-Chaser vs Piano Life Saver:**
   - GraphQL expose seulement les champs Dampp-Chaser
   - Si Piano Life Saver est mentionné, il sera dans le champ `notes` du piano
   - Pour détecter PLS, analyser `notes` avec regex/keywords

2. **Types d'Invoice Items:**
   - Le champ `type` contient des valeurs comme `SERVICE`, `PRODUCT`
   - Vérifier les valeurs réelles après import pour ajuster les filtres

3. **Performance:**
   - Index créés sur `dampp_chaser_installed` et `invoice_external_id`
   - Requêtes optimisées pour recherches fréquentes

## 🔄 Maintenance

**Fréquence de réimport recommandée:**
- **Pianos:** Hebdomadaire (pour capturer nouveaux pianos + mises à jour Dampp-Chaser)
- **Invoice Items:** Quotidien (pour suivre les ventes récentes)

**Commandes:**
```bash
# Import hebdomadaire complet
python3 scripts/import_pianos.py
python3 scripts/import_invoice_items.py
```
