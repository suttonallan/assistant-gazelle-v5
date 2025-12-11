# 📊 Rapport - Classification des Produits pour Migration Supabase

**Date:** 2025-12-09
**Projet:** Assistant Gazelle V5
**Objectif:** Identifier et migrer les classifications de produits depuis Gazelle vers Supabase

---

## 1. Source de Classification

### Table Gazelle: `inv.ProductDisplay`

**Emplacement:** SQL Server Gazelle
**Schéma:** `inv`
**Relation:** 1:1 avec `inv.Products` via `ProductId`

### Fichiers de référence

- **Migration SQL:** `modules/inventaire/migrations/002_add_product_classifications.sql`
- **Script d'import:** `scripts/import_gazelle_product_display.py`

---

## 2. Schéma Complet

### Colonnes de Commission

| Colonne SQL Server | Type SQL Server | Colonne Supabase | Type PostgreSQL | Description |
|-------------------|-----------------|------------------|-----------------|-------------|
| `HasCommission` | BIT (BOOLEAN) | `has_commission` | BOOLEAN | Indique si le produit est sujet à commission |
| `CommissionRate` | DECIMAL(5,2) | `commission_rate` | DECIMAL(5,2) | Taux de commission (ex: 15.00 = 15%) |

### Colonnes de Catégorisation

| Colonne SQL Server | Type SQL Server | Colonne Supabase | Type PostgreSQL | Description |
|-------------------|-----------------|------------------|-----------------|-------------|
| `Category` | VARCHAR(50) | `categorie` | TEXT | Catégorie du produit (enrichie) |

**Valeurs possibles:**
- `"Cordes"`
- `"Feutres"`
- `"Accessoire"`
- `"Service"`
- `"Fourniture"`
- `"Produit"`
- `"Frais"`

### Colonnes de Variantes

| Colonne SQL Server | Type SQL Server | Colonne Supabase | Type PostgreSQL | Description |
|-------------------|-----------------|------------------|-----------------|-------------|
| `VariantGroup` | VARCHAR(100) | `variant_group` | TEXT | Groupe de variantes (ex: "Cordes Piano") |
| `VariantLabel` | VARCHAR(100) | `variant_label` | TEXT | Label de la variante (ex: "Do#3") |

### Colonnes d'Affichage

| Colonne SQL Server | Type SQL Server | Colonne Supabase | Type PostgreSQL | Description |
|-------------------|-----------------|------------------|-----------------|-------------|
| `DisplayOrder` | INT | `display_order` | INTEGER | Ordre d'affichage dans les listes |
| `IsActive` | BIT (BOOLEAN) | `is_active` | BOOLEAN | Produit actif/inactif |

### Colonnes de Synchronisation

| Colonne SQL Server | Type SQL Server | Colonne Supabase | Type PostgreSQL | Description |
|-------------------|-----------------|------------------|-----------------|-------------|
| `ProductId` | INT | `gazelle_product_id` | INTEGER | ID du produit dans Gazelle |
| N/A | N/A | `last_sync_at` | TIMESTAMPTZ | Dernière synchronisation |

---

## 3. Requête SQL d'Export depuis Gazelle

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

---

## 4. Code Utilisant ces Classifications

### Backend API (FastAPI)

**Fichier:** `api/inventaire.py`

**Endpoints concernés:**
- `GET /inventaire/catalogue` - Filtrage par catégorie enrichie
- `GET /inventaire/catalogue?has_commission=true` - Produits avec commission
- `GET /inventaire/catalogue?variant_group=Cordes` - Par groupe de variantes

**Exemple de modification à faire:**

```python
# Ajouter des filtres pour les nouvelles colonnes
@router.get("/catalogue")
async def get_catalogue(
    categorie: Optional[str] = None,
    has_commission: Optional[bool] = None,
    variant_group: Optional[str] = None,
    is_active: Optional[bool] = True
):
    filters = {}
    if categorie:
        filters["categorie"] = categorie
    if has_commission is not None:
        filters["has_commission"] = has_commission
    if variant_group:
        filters["variant_group"] = variant_group
    if is_active is not None:
        filters["is_active"] = is_active

    produits = storage.get_data("produits_catalogue", filters=filters)
    return {"produits": produits, "count": len(produits)}
```

### Frontend (React)

**Fichier:** `frontend/src/components/InventaireDashboard.jsx`

**Modifications à faire:**

```jsx
// Ajouter des filtres dans l'interface
<select value={filterCommission} onChange={(e) => setFilterCommission(e.target.value)}>
  <option value="">Tous les produits</option>
  <option value="true">Avec commission</option>
  <option value="false">Sans commission</option>
</select>

// Afficher le taux de commission
<td className="px-4 py-3 text-sm">
  {produit.has_commission ? (
    <span className="text-green-600">
      {produit.commission_rate}%
    </span>
  ) : (
    <span className="text-gray-400">-</span>
  )}
</td>
```

---

## 5. Schéma SQL Supabase

**Fichier:** `modules/inventaire/migrations/002_add_product_classifications.sql`

Le script ajoute les colonnes suivantes à `produits_catalogue`:

```sql
ALTER TABLE produits_catalogue
ADD COLUMN IF NOT EXISTS has_commission BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS commission_rate DECIMAL(5,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS variant_group TEXT,
ADD COLUMN IF NOT EXISTS variant_label TEXT,
ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS gazelle_product_id INTEGER,
ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;
```

**Index créés pour performance:**

```sql
CREATE INDEX idx_produits_has_commission ON produits_catalogue(has_commission);
CREATE INDEX idx_produits_variant_group ON produits_catalogue(variant_group);
CREATE INDEX idx_produits_gazelle_id ON produits_catalogue(gazelle_product_id);
CREATE INDEX idx_produits_active ON produits_catalogue(is_active);
```

---

## 6. Plan de Migration

### Étape 1: Exécuter la migration SQL

```bash
# Dans Supabase SQL Editor
modules/inventaire/migrations/002_add_product_classifications.sql
```

### Étape 2: Tester l'import (dry-run)

```bash
python3 scripts/import_gazelle_product_display.py --dry-run
```

### Étape 3: Exécuter l'import réel

```bash
python3 scripts/import_gazelle_product_display.py
```

### Étape 4: Vérifier les données

```bash
curl http://localhost:8000/inventaire/catalogue | jq '.produits[] | {code_produit, has_commission, commission_rate}'
```

### Étape 5: Mettre à jour le frontend

- Ajouter les colonnes dans le tableau
- Ajouter les filtres de recherche
- Afficher les badges de commission

---

## 7. Cas d'Usage

### Filtrer les produits avec commission

```python
# Backend
produits_commission = storage.get_data(
    "produits_catalogue",
    filters={"has_commission": True}
)

# Calculer le total des commissions
total_commission = sum(
    p["prix_unitaire"] * (p["commission_rate"] / 100)
    for p in produits_commission
)
```

### Grouper par variantes

```python
# Backend - Récupérer toutes les variantes d'un groupe
variantes_cordes = storage.get_data(
    "produits_catalogue",
    filters={"variant_group": "Cordes Piano"},
    order_by="display_order"
)
```

### Afficher seulement les produits actifs

```python
# Backend
produits_actifs = storage.get_data(
    "produits_catalogue",
    filters={"is_active": True},
    order_by="display_order"
)
```

---

## 8. Résumé pour Migration

### ✅ Complété

1. Schéma SQL documenté
2. Script de migration créé
3. Script d'import créé
4. Documentation complète

### ⏳ À faire (par Cursor PC)

1. Implémenter `fetch_from_gazelle()` avec connexion SQL Server
2. Tester l'import avec données réelles
3. Mettre à jour l'API FastAPI avec nouveaux filtres
4. Mettre à jour le frontend React

### 📋 Colonnes essentielles

| Priorité | Colonne | Utilité |
|----------|---------|---------|
| 🔴 Haute | `has_commission` | Facturation |
| 🔴 Haute | `commission_rate` | Calcul commissions |
| 🟡 Moyenne | `variant_group` | Organisation |
| 🟡 Moyenne | `is_active` | Filtrage |
| 🟢 Basse | `display_order` | Affichage |
| 🟢 Basse | `variant_label` | Identification |

---

## 9. Ressources

- **Documentation Supabase:** https://supabase.com/docs
- **Script d'import:** [scripts/import_gazelle_product_display.py](../scripts/import_gazelle_product_display.py)
- **Migration SQL:** [modules/inventaire/migrations/002_add_product_classifications.sql](../modules/inventaire/migrations/002_add_product_classifications.sql)

---

**Dernière mise à jour:** 2025-12-09
**Responsable:** Allan Sutton
**Statut:** ✅ Documentation complète - En attente d'implémentation
