# Guide d'Import - Inventaire

## 📋 Scripts d'Import Disponibles

### 1. Import Catalogue (Produits)

**Script:** `scripts/import_gazelle_product_display.py`  
**Fichier .bat:** `IMPORT_FINAL.bat`

**Utilisation:**
- Double-cliquer sur `IMPORT_FINAL.bat` (Windows)
- Importe les produits depuis SQL Server Gazelle vers Supabase

**Prérequis:**
- Migration 001 exécutée (table `produits_catalogue`)
- Migration 002 exécutée (colonnes de classification)
- Variables d'environnement configurées (`.env`)

### 2. Import Inventaire Techniciens

**Script:** `scripts/import_inventaire_techniciens.py`  
**Fichier .bat:** `IMPORT_INVENTAIRE_TECHNICIENS.bat`

**Utilisation:**
- Double-cliquer sur `IMPORT_INVENTAIRE_TECHNICIENS.bat` (Windows)
- Importe les stocks des techniciens depuis SQL Server Gazelle

**Prérequis:**
- Catalogue importé (les produits doivent exister)
- Migration 001 exécutée

**Post-import:**
- Exécuter `MAPPER_TECHNICIENS.bat` pour mapper les IDs vers les noms

### 3. Mapping Techniciens

**Script:** `scripts/mapper_techniciens.py`  
**Fichier .bat:** `MAPPER_TECHNICIENS.bat`

**Utilisation:**
- Double-cliquer sur `MAPPER_TECHNICIENS.bat`
- Convertit les IDs Supabase (`usr_xxx`) en noms de techniciens

## 🔄 Workflow Complet

1. **Exécuter les migrations SQL** (dans Supabase SQL Editor)
   - `001_create_inventory_tables.sql`
   - `002_add_product_classifications.sql`
   - `003_create_product_mapping.sql` (pour mapping API Gazelle)

2. **Importer le catalogue**
   - `IMPORT_FINAL.bat`

3. **Importer l'inventaire des techniciens**
   - `IMPORT_INVENTAIRE_TECHNICIENS.bat`

4. **Mapper les techniciens**
   - `MAPPER_TECHNICIENS.bat`

## 📝 Notes pour Futurs Imports

### Import depuis API Gazelle (GraphQL)

Pour les imports futurs depuis l'API Gazelle (pas SQL Server):

1. **Vérifier les mappings existants**
   - Utiliser l'interface admin: Onglet "Mapping Gazelle"
   - Ou API: `GET /inventaire/mapping/mappings`

2. **Importer avec mapping**
   - Le script d'import vérifie `produits_mapping`
   - Si mapping existe → UPDATE produit existant
   - Si pas de mapping → Créer nouveau + proposer mapping

3. **Créer les mappings manquants**
   - Via l'interface admin
   - Ou API: `POST /inventaire/mapping/mappings`

## 🛠️ Scripts Utiles (Réutilisables)

### `scripts/gestion_migrations.py`
Vérifie l'état des migrations Supabase. Réutilisable pour d'autres modules.

### `scripts/mapper_techniciens.py`
Pattern réutilisable pour mapper des IDs externes vers des noms.

### `core/supabase_storage.py`
Classe générique pour interactions Supabase. Réutilisable partout.

## 📚 Documentation Importante

- `docs/STRATÉGIE_MAPPING_PRODUITS.md` - Stratégie complète de mapping
- `docs/CLARIFICATION_MAPPING.md` - Clarifications importantes
- `docs/SCHEMA_PRODUITS_CATALOGUE.md` - Schéma de la table produits
