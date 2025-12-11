# 📥 Instructions d'import dans Supabase

## Étape 1 : Exporter les données actuelles

Sur votre système actuel (Windows/SQL Server), exécutez :
```bash
python export_inventory_data.py
```

Cela génère les fichiers CSV dans le dossier `export_data/`.

## Étape 2 : Préparer Supabase

1. Connectez-vous à votre projet Supabase
2. Allez dans **Table Editor**
3. Vérifiez que les tables suivantes existent :
   - `inv.Products`
   - `inv.Inventory`
   - `inv.ProductDisplay` (optionnel)
   - `inv.Transactions` (optionnel)

## Étape 3 : Importer les données

### Option A : Via l'interface Supabase

1. Ouvrez la table `inv.Products`
2. Cliquez sur **Import** → **Import CSV**
3. Sélectionnez `products.csv`
4. Répétez pour `inventory.csv`

### Option B : Via SQL (recommandé pour gros volumes)

```sql
-- Importer Products
COPY "inv"."Products" (ProductId, Name, Sku, UnitCost, RetailPrice, Active, CreatedAt)
FROM '/chemin/vers/products.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- Importer Inventory
COPY "inv"."Inventory" (InventoryId, ProductId, TechnicianId, Quantity, ReorderThreshold, UpdatedAt)
FROM '/chemin/vers/inventory.csv'
WITH (FORMAT csv, HEADER true, DELIMITER ',');
```

### Option C : Via Python (script personnalisé)

Créez un script `import_to_supabase.py` :

```python
import psycopg2
import csv
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('SUPABASE_HOST'),
    database=os.getenv('SUPABASE_DATABASE'),
    user=os.getenv('SUPABASE_USER'),
    password=os.getenv('SUPABASE_PASSWORD'),
    port=os.getenv('SUPABASE_PORT', 5432)
)

cursor = conn.cursor()

# Importer Products
with open('export_data/products.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cursor.execute("""
            INSERT INTO "inv"."Products" 
            (ProductId, Name, Sku, UnitCost, RetailPrice, Active, CreatedAt)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ProductId) DO UPDATE SET
                Name = EXCLUDED.Name,
                Sku = EXCLUDED.Sku,
                UnitCost = EXCLUDED.UnitCost,
                RetailPrice = EXCLUDED.RetailPrice,
                Active = EXCLUDED.Active
        """, (
            row['ProductId'],
            row['Name'],
            row['Sku'] or None,
            float(row['UnitCost']) if row['UnitCost'] else 0.0,
            float(row['RetailPrice']) if row['RetailPrice'] else 0.0,
            row['Active'].lower() == 'true',
            row['CreatedAt'] if row['CreatedAt'] else None
        ))

conn.commit()
print("✅ Products importés")

# Répétez pour Inventory, etc.
conn.close()
```

## ⚠️ Notes importantes

1. **Vérifiez les types de données** : Les colonnes doivent correspondre entre SQL Server et Supabase
2. **IDs existants** : Utilisez `ON CONFLICT` pour éviter les doublons
3. **TechnicianId** : Assurez-vous que les IDs Gazelle sont bien des strings dans Supabase
4. **Dates** : Les formats de date peuvent différer, vérifiez les conversions

## 🔍 Vérification après import

Exécutez `inventory_checker.py` pour vérifier que les données sont bien importées :

```bash
python inventory_checker.py
```

