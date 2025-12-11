# 📦 Intégration Product Display - Classification des Produits

**Date:** 2025-12-09
**Projet:** Assistant Gazelle V5
**Statut:** ✅ Intégration Backend/Frontend complétée - En attente de migration SQL

---

## Vue d'ensemble

Cette intégration ajoute les métadonnées de classification de produits depuis Gazelle `inv.ProductDisplay` vers Supabase `produits_catalogue`. Ces données enrichissent le catalogue avec:

- **Commissions** - Taux de commission par produit
- **Variantes** - Groupes de variantes (ex: Cordes Piano)
- **Affichage** - Ordre d'affichage et statut actif/inactif
- **Synchronisation** - Lien avec Gazelle et horodatage

---

## 📋 Checklist d'Intégration

### ✅ Complété

- [x] Migration SQL créée ([002_add_product_classifications.sql](modules/inventaire/migrations/002_add_product_classifications.sql))
- [x] Script d'import créé ([import_gazelle_product_display.py](scripts/import_gazelle_product_display.py))
- [x] API backend mise à jour avec nouveaux filtres ([api/inventaire.py](api/inventaire.py:71-109))
- [x] Frontend mis à jour avec affichage commission ([frontend/src/components/InventaireDashboard.jsx](frontend/src/components/InventaireDashboard.jsx:126-199))
- [x] Documentation complète ([RAPPORT_CLASSIFICATION_PRODUITS.md](docs/RAPPORT_CLASSIFICATION_PRODUITS.md))

### ⏳ À Faire

- [ ] **Exécuter la migration SQL dans Supabase** (voir section Migration)
- [ ] **Implémenter la connexion SQL Server** dans `fetch_from_gazelle()` (Cursor PC)
- [ ] **Tester l'import** avec `--dry-run`
- [ ] **Exécuter l'import réel** depuis Gazelle
- [ ] **Vérifier les données** dans le frontend

---

## 🗂️ Fichiers Créés/Modifiés

### 1. Migration SQL

**Fichier:** [modules/inventaire/migrations/002_add_product_classifications.sql](modules/inventaire/migrations/002_add_product_classifications.sql)

**Ajoute 8 nouvelles colonnes:**
- `has_commission` (BOOLEAN) - Produit avec commission
- `commission_rate` (DECIMAL) - Taux de commission en %
- `variant_group` (TEXT) - Groupe de variantes
- `variant_label` (TEXT) - Label de la variante
- `display_order` (INTEGER) - Ordre d'affichage
- `is_active` (BOOLEAN) - Produit actif/inactif
- `gazelle_product_id` (INTEGER) - ID Gazelle
- `last_sync_at` (TIMESTAMPTZ) - Dernière synchro

**Index de performance:**
- `idx_produits_has_commission` - Filtre par commission
- `idx_produits_variant_group` - Filtre par groupe
- `idx_produits_gazelle_id` - Lien Gazelle
- `idx_produits_active` - Produits actifs

### 2. Script d'Import Python

**Fichier:** [scripts/import_gazelle_product_display.py](scripts/import_gazelle_product_display.py)

**Fonctionnalités:**
- `fetch_from_gazelle()` - Récupère depuis SQL Server (TODO)
- `map_gazelle_to_supabase()` - Convertit les données
- `import_product()` - UPSERT dans Supabase
- Support `--dry-run` pour tests

**Utilisation:**
```bash
# Test sans modification
python3 scripts/import_gazelle_product_display.py --dry-run

# Import réel
python3 scripts/import_gazelle_product_display.py
```

### 3. API Backend (FastAPI)

**Fichier:** [api/inventaire.py](api/inventaire.py:71-109)

**Endpoint mis à jour:**
```python
GET /inventaire/catalogue
  ?categorie=Cordes
  &has_commission=true
  &variant_group=Cordes Piano
  &is_active=true
```

**Nouveaux query params:**
- `has_commission` (bool) - Filtre par commission
- `variant_group` (str) - Filtre par groupe de variantes
- `is_active` (bool) - Filtre par statut actif (défaut: true)

### 4. Frontend (React)

**Fichier:** [frontend/src/components/InventaireDashboard.jsx](frontend/src/components/InventaireDashboard.jsx:126-199)

**Modifications:**
- Nouveau filtre "Commission" (Tous / Avec / Sans)
- Nouvelle colonne "Commission" dans le tableau
- Affichage en vert du taux de commission
- Indicateur "-" pour produits sans commission

---

## 🚀 Migration SQL

### Étape 1: Ouvrir Supabase SQL Editor

1. Aller sur [Supabase Dashboard](https://supabase.com/dashboard)
2. Sélectionner le projet **Assistant Gazelle V5**
3. Cliquer sur "SQL Editor" dans le menu

### Étape 2: Exécuter la Migration

1. Cliquer sur "New query"
2. Copier le contenu de [modules/inventaire/migrations/002_add_product_classifications.sql](modules/inventaire/migrations/002_add_product_classifications.sql)
3. Coller dans l'éditeur
4. Cliquer sur "Run"

### Étape 3: Vérifier la Migration

```sql
-- Vérifier les nouvelles colonnes
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'produits_catalogue';

-- Vérifier les index
SELECT indexname
FROM pg_indexes
WHERE tablename = 'produits_catalogue';

-- Voir un exemple de produit avec nouvelles colonnes
SELECT code_produit, nom, has_commission, commission_rate, variant_group
FROM produits_catalogue
LIMIT 5;
```

---

## 📥 Import depuis Gazelle

### Prérequis

Le script `fetch_from_gazelle()` doit être implémenté avec la connexion SQL Server. Voir [scripts/import_gazelle_product_display.py:34-70](scripts/import_gazelle_product_display.py:34-70) pour la requête SQL.

### Requête SQL (SQL Server)

```sql
SELECT
    p.ProductId,
    p.Code AS code_produit,
    p.Name AS nom,
    pd.Category AS categorie,
    p.Description AS description,
    p.Unit AS unite_mesure,
    p.UnitPrice AS prix_unitaire,
    p.Supplier AS fournisseur,
    pd.HasCommission AS has_commission,
    pd.CommissionRate AS commission_rate,
    pd.VariantGroup AS variant_group,
    pd.VariantLabel AS variant_label,
    pd.DisplayOrder AS display_order,
    pd.IsActive AS is_active
FROM inv.Products p
LEFT JOIN inv.ProductDisplay pd ON p.ProductId = pd.ProductId
WHERE p.IsDeleted = 0
ORDER BY pd.DisplayOrder, p.Code;
```

### Test avec Dry-Run

```bash
python3 scripts/import_gazelle_product_display.py --dry-run
```

**Sortie attendue:**
```
🔄 Importation des classifications de produits depuis Gazelle...
⚠️  MODE DRY-RUN: Aucune modification ne sera effectuée

📥 Récupération depuis Gazelle inv.ProductDisplay...
   150 produits récupérés

📦 Importation des produits...
  🔍 [DRY-RUN] CORD-001: Corde Piano Do#3
  🔍 [DRY-RUN] FELT-001: Feutre de marteau
  ...

📊 Statistiques d'importation:
   Total traité: 150
   ✅ Créés: 0
   ✅ Mis à jour: 0
   ⚠️  Ignorés: 0
   ❌ Erreurs: 0
```

### Import Réel

```bash
python3 scripts/import_gazelle_product_display.py
```

---

## 🎨 Interface Utilisateur

### Filtres Ajoutés

**Localisation:** [frontend/src/components/InventaireDashboard.jsx:128-159](frontend/src/components/InventaireDashboard.jsx:128-159)

```jsx
<select value={filterCommission} onChange={(e) => setFilterCommission(e.target.value)}>
  <option value="">Tous les produits</option>
  <option value="true">Avec commission</option>
  <option value="false">Sans commission</option>
</select>
```

### Colonne Commission

**Localisation:** [frontend/src/components/InventaireDashboard.jsx:184-192](frontend/src/components/InventaireDashboard.jsx:184-192)

```jsx
<td className="px-4 py-3 text-sm">
  {produit.has_commission ? (
    <span className="text-green-600 font-medium">
      {produit.commission_rate}%
    </span>
  ) : (
    <span className="text-gray-400">-</span>
  )}
</td>
```

**Affichage:**
- Produits avec commission: **15.0%** (en vert)
- Produits sans commission: **-** (en gris)

---

## 📊 Cas d'Usage

### 1. Filtrer les produits avec commission

**Frontend:**
1. Aller sur l'onglet "Inventaire"
2. Sélectionner "Avec commission" dans le filtre Commission
3. Voir uniquement les produits générant des commissions

**Backend:**
```bash
curl "http://localhost:8000/inventaire/catalogue?has_commission=true"
```

### 2. Voir toutes les variantes d'un groupe

**Backend:**
```bash
curl "http://localhost:8000/inventaire/catalogue?variant_group=Cordes%20Piano"
```

**Résultat:** Toutes les cordes de piano (Do#3, Ré, Mi, etc.)

### 3. Calculer le total des commissions

**Python:**
```python
from core.supabase_storage import SupabaseStorage

storage = SupabaseStorage()
produits = storage.get_data("produits_catalogue", filters={"has_commission": True})

total_commission = sum(
    p["prix_unitaire"] * (p["commission_rate"] / 100)
    for p in produits
)

print(f"Total commissions: ${total_commission:.2f}")
```

---

## 🔍 Tests

### 1. Test Backend

```bash
# Tous les produits
curl http://localhost:8000/inventaire/catalogue | jq '.count'

# Seulement les produits avec commission
curl "http://localhost:8000/inventaire/catalogue?has_commission=true" | jq '.produits[] | {code_produit, commission_rate}'

# Filtrer par catégorie ET commission
curl "http://localhost:8000/inventaire/catalogue?categorie=Cordes&has_commission=true" | jq '.produits'
```

### 2. Test Frontend

1. Ouvrir http://localhost:5173
2. Aller sur "Inventaire" → "Catalogue"
3. Vérifier que le filtre "Commission" fonctionne
4. Vérifier que la colonne "Commission" affiche les taux

### 3. Test SQL Direct (Supabase)

```sql
-- Produits avec commission
SELECT code_produit, nom, commission_rate
FROM produits_catalogue
WHERE has_commission = TRUE;

-- Groupes de variantes
SELECT DISTINCT variant_group
FROM produits_catalogue
WHERE variant_group IS NOT NULL;

-- Produits actifs seulement
SELECT code_produit, nom, is_active
FROM produits_catalogue
WHERE is_active = TRUE;
```

---

## 📚 Ressources

### Documentation

- [RAPPORT_CLASSIFICATION_PRODUITS.md](docs/RAPPORT_CLASSIFICATION_PRODUITS.md) - Rapport complet de Cursor PC
- [INTEGRATION_INVENTAIRE_COMPLETE.md](INTEGRATION_INVENTAIRE_COMPLETE.md) - Intégration module inventaire

### Fichiers Clés

- **Migration SQL:** [modules/inventaire/migrations/002_add_product_classifications.sql](modules/inventaire/migrations/002_add_product_classifications.sql)
- **Script Import:** [scripts/import_gazelle_product_display.py](scripts/import_gazelle_product_display.py)
- **API Backend:** [api/inventaire.py](api/inventaire.py:71-109)
- **Frontend:** [frontend/src/components/InventaireDashboard.jsx](frontend/src/components/InventaireDashboard.jsx:126-199)

### Dépendances

- `psycopg2-binary>=2.9.9` - Connexion PostgreSQL (déjà installé)
- `pyodbc` - Connexion SQL Server Gazelle (à installer pour l'import)

---

## ⚠️ Notes Importantes

### Compatibilité Ascendante

Les colonnes existantes dans `produits_catalogue` ne sont **pas modifiées**. La migration utilise `ADD COLUMN IF NOT EXISTS` pour garantir l'idempotence.

### Valeurs par Défaut

- `has_commission` = FALSE
- `commission_rate` = 0.00
- `display_order` = 0
- `is_active` = TRUE

### Performance

Les index partiels (`WHERE has_commission = TRUE`, etc.) optimisent les requêtes tout en minimisant l'espace disque.

### Synchronisation

Le champ `last_sync_at` permet de tracker la fraîcheur des données depuis Gazelle. Recommandation: exécuter l'import 1x/jour via un Cron Job.

---

## 🎯 Prochaines Étapes

1. **Exécuter la migration SQL dans Supabase** (priorité haute)
2. **Implémenter `fetch_from_gazelle()`** avec SQL Server (Cursor PC)
3. **Tester l'import en dry-run**
4. **Importer les données réelles**
5. **Vérifier dans le frontend**
6. **Configurer un Cron Job** pour synchronisation quotidienne

---

**Dernière mise à jour:** 2025-12-09
**Responsable:** Allan Sutton
**Statut:** ✅ Backend/Frontend prêts - Migration SQL en attente
