# 📋 Schéma de Référence: Table `produits_catalogue`

**Document de référence officiel** pour tous les scripts d'import/export.

**⚠️ IMPORTANT:** Utilisez UNIQUEMENT ces colonnes. Ne créez pas de nouvelles colonnes sans migration SQL.

---

## ✅ Colonnes Valides (après migrations 001 et 002)

### Colonnes de Base (Migration 001)

| Colonne | Type | Contraintes | Valeur par défaut | Description |
|---------|------|-------------|-------------------|-------------|
| `id` | UUID | PRIMARY KEY | `gen_random_uuid()` | **Auto-généré, ne pas envoyer** |
| `code_produit` | TEXT | UNIQUE, NOT NULL | - | Code unique du produit (ex: "CORD-001") |
| `nom` | TEXT | NOT NULL | - | Nom du produit |
| `categorie` | TEXT | NOT NULL | - | Catégorie (ex: "Cordes", "Feutres", "Outils") |
| `description` | TEXT | NULL | NULL | Description détaillée |
| `unite_mesure` | TEXT | NULL | `'unité'` | Unité (ex: "unité", "mètre", "kg") |
| `prix_unitaire` | DECIMAL(10,2) | NULL | NULL | Prix de référence |
| `fournisseur` | TEXT | NULL | NULL | Nom du fournisseur principal |
| `created_at` | TIMESTAMPTZ | - | `NOW()` | **Auto-généré, ne pas envoyer** |
| `updated_at` | TIMESTAMPTZ | - | `NOW()` | **Auto-généré, ne pas envoyer** |

### Colonnes de Classification (Migration 002)

| Colonne | Type | Contraintes | Valeur par défaut | Description |
|---------|------|-------------|-------------------|-------------|
| `has_commission` | BOOLEAN | NULL | `FALSE` | Indique si le produit est sujet à commission |
| `commission_rate` | DECIMAL(5,2) | NULL | `0.00` | Taux de commission en % (ex: 15.00 = 15%) |
| `variant_group` | TEXT | NULL | NULL | Groupe de variantes (ex: "Cordes Piano") |
| `variant_label` | TEXT | NULL | NULL | Label de la variante (ex: "Do#3") |
| `display_order` | INTEGER | NULL | `0` | Ordre d'affichage dans les listes |
| `is_active` | BOOLEAN | NULL | `TRUE` | Produit actif/inactif |
| `gazelle_product_id` | INTEGER | NULL | NULL | ID du produit dans Gazelle inv.Products |
| `last_sync_at` | TIMESTAMPTZ | NULL | NULL | Dernière synchronisation depuis Gazelle |

---

## ❌ Colonnes qui N'EXISTENT PAS

**⚠️ NE JAMAIS UTILISER:**

- ❌ `product_id` → Utiliser `gazelle_product_id` à la place
- ❌ `active` → Utiliser `is_active` à la place
- ❌ `ProductId` → Utiliser `gazelle_product_id` à la place
- ❌ `Active` → Utiliser `is_active` à la place

---

## 📝 Mapping Correct pour Scripts d'Import

### Depuis Gazelle V4 (SQL Server) vers Supabase V5

```python
{
    # Colonnes de base
    "code_produit": gazelle_product.get("Sku"),  # inv.Products.Sku
    "nom": gazelle_product.get("Name"),  # inv.Products.Name
    "categorie": gazelle_product.get("Category", "Produit"),  # inv.ProductDisplay.Category
    "description": gazelle_product.get("Description"),  # inv.Products.Description
    "unite_mesure": gazelle_product.get("Unit", "unité"),  # inv.Products.Unit
    "prix_unitaire": float(gazelle_product.get("UnitPrice", 0)),  # inv.Products.UnitPrice
    "fournisseur": gazelle_product.get("Supplier"),  # inv.Products.Supplier
    
    # Colonnes de classification (migration 002)
    "has_commission": False,  # N'existe pas dans V4, initialiser à FALSE
    "commission_rate": 0.00,  # N'existe pas dans V4, initialiser à 0.00
    "variant_group": gazelle_product.get("VariantGroup"),  # inv.ProductDisplay.VariantGroup
    "variant_label": gazelle_product.get("VariantLabel"),  # inv.ProductDisplay.VariantLabel
    "display_order": int(gazelle_product.get("DisplayOrder", 0)),  # inv.ProductDisplay.DisplayOrder
    "is_active": bool(gazelle_product.get("IsActive", True)),  # inv.ProductDisplay.IsActive
    "gazelle_product_id": gazelle_product.get("ProductId"),  # inv.Products.ProductId
    "last_sync_at": datetime.now().isoformat(),  # Timestamp de synchronisation
    
    # ❌ NE PAS INCLURE:
    # - "id" (auto-généré)
    # - "created_at" (auto-généré)
    # - "updated_at" (auto-généré)
    # - "product_id" (n'existe pas)
    # - "active" (n'existe pas)
}
```

---

## 🔍 Vérification du Schéma

Pour vérifier les colonnes dans Supabase:

```sql
-- Dans Supabase SQL Editor
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'produits_catalogue'
ORDER BY ordinal_position;
```

---

## 📚 Références

- Migration 001: `modules/inventaire/migrations/001_create_inventory_tables.sql`
- Migration 002: `modules/inventaire/migrations/002_add_product_classifications.sql`

---

## ✅ Checklist pour Nouveaux Scripts

Avant d'écrire un script d'import/export:

- [ ] Consulter ce document pour les colonnes valides
- [ ] Vérifier que toutes les colonnes utilisées existent dans ce document
- [ ] Ne pas créer de nouvelles colonnes sans migration SQL
- [ ] Utiliser `gazelle_product_id` (pas `product_id`)
- [ ] Utiliser `is_active` (pas `active`)
- [ ] Ne pas envoyer `id`, `created_at`, `updated_at` (auto-générés)

---

**Dernière mise à jour:** Après migrations 001 et 002
