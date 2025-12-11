# 📦 Export Inventaire - Gazelle V5

Scripts pour vérifier les stocks et exporter les données d'inventaire vers Supabase.

## 📋 Contenu

- **`inventory_checker.py`** : Script de vérification et d'alerte des stocks bas
- **`export_inventory_data.py`** : Script d'export des données actuelles (CSV/JSON)
- **`requirements.txt`** : Dépendances Python nécessaires

## 🚀 Installation

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. Configurer les variables d'environnement (`.env`) :
```env
# Pour Supabase (PostgreSQL)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_PASSWORD=votre_mot_de_passe
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PORT=5432

# OU pour SQL Server (fallback)
DB_CONN_STR=DRIVER={ODBC Driver 17 for SQL Server};SERVER=PIANOTEK\SQLEXPRESS;DATABASE=PianoTek;Trusted_Connection=yes;
```

## 📊 Utilisation

### 1. Vérifier les stocks bas

```bash
python inventory_checker.py
```

Ce script :
- ✅ Vérifie les produits avec `Quantity <= ReorderThreshold`
- ✅ Identifie les ruptures de stock (`Quantity = 0`)
- ✅ Affiche un résumé des alertes

### 2. Exporter les données actuelles

```bash
python export_inventory_data.py
```

Ce script génère dans le dossier `export_data/` :
- `products.csv` / `products.json` : Catalogue des produits
- `inventory.csv` / `inventory.json` : Stock par technicien
- `product_display.csv` / `product_display.json` : Métadonnées d'affichage (si existe)
- `transactions.csv` / `transactions.json` : Historique des transactions (1000 dernières)

## 📁 Structure des données exportées

### Products
- `ProductId` : ID du produit
- `Name` : Nom du produit
- `Sku` : Code SKU
- `UnitCost` : Coût unitaire
- `RetailPrice` : Prix de vente
- `Active` : Produit actif (True/False)
- `CreatedAt` : Date de création

### Inventory
- `InventoryId` : ID de l'entrée
- `ProductId` : ID du produit
- `TechnicianId` : ID Gazelle du technicien
- `Quantity` : Quantité en stock
- `ReorderThreshold` : Seuil de réapprovisionnement
- `UpdatedAt` : Dernière mise à jour

## 🔄 Import dans Supabase

Les fichiers CSV peuvent être importés directement dans Supabase via :
1. L'interface Supabase Dashboard → Table Editor → Import CSV
2. Ou via SQL :
```sql
COPY "inv"."Products" FROM '/chemin/vers/products.csv' WITH CSV HEADER;
```

## ⚠️ Notes

- Les scripts détectent automatiquement si vous utilisez Supabase ou SQL Server
- Les données sont exportées en UTF-8 avec BOM pour Excel (CSV)
- Les transactions sont limitées à 1000 pour éviter des fichiers trop volumineux

