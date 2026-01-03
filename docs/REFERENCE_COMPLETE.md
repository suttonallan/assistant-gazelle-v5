# 📚 Document de Référence Complet - Assistant Gazelle V5

**⚠️ DOCUMENT OFFICIEL - À CONSULTER AVANT TOUTE MODIFICATION**

Ce document contient toutes les informations de référence pour éviter les suppositions et erreurs.

---

## 👥 Mapping des Techniciens (IDs Supabase → Noms)

**Source officielle:** `README.md` (lignes 48-60)

```python
TECHNICIENS_MAPPING = {
    'usr_ofYggsCDt2JAVeNP': {
        'name': 'Allan',
        'email': 'asutton@piano-tek.com'
    },
    'usr_HcCiFk7o0vZ9xAI0': {
        'name': 'Nicolas',
        'email': 'nlessard@piano-tek.com'
    },
    'usr_ReUSmIJmBF86ilY1': {
        'name': 'Jean-Philippe',
        'email': 'jpreny@gmail.com'
    }
}
```

**⚠️ IMPORTANT:** 
- **NE JAMAIS DEVINER** les mappings
- **TOUJOURS** consulter ce document avant de créer/modifier un script de mapping
- Si un nouvel ID apparaît, **DEMANDER** à l'utilisateur avant de mapper

---

## 📊 Schéma des Tables Supabase

### Table: `produits_catalogue`

**Migration:** `modules/inventaire/migrations/001_create_inventory_tables.sql` + `002_add_product_classifications.sql`

#### Colonnes de BASE (Migration 001) - TOUJOURS disponibles:
```sql
code_produit TEXT PRIMARY KEY          -- Code unique du produit (ex: "PROD-123", "CORD-001")
nom TEXT NOT NULL                      -- Nom du produit
categorie TEXT                         -- Catégorie (ex: "Cordes", "Outils")
description TEXT                       -- Description détaillée
unite_mesure TEXT                      -- Unité (ex: "unité", "litre")
prix_unitaire DECIMAL(10,2)            -- Prix unitaire
fournisseur TEXT                       -- Nom du fournisseur
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()
```

#### Colonnes de CLASSIFICATION (Migration 002) - Peuvent ne pas exister:
```sql
has_commission BOOLEAN DEFAULT FALSE
commission_rate DECIMAL(5,2) DEFAULT 0.00
variant_group TEXT                     -- Groupe de variantes (ex: "Cordes Piano")
variant_label TEXT                     -- Label de variante (ex: "Do", "Ré")
display_order INTEGER DEFAULT 0        -- Ordre d'affichage
is_active BOOLEAN DEFAULT TRUE
gazelle_product_id INTEGER             -- ID du produit dans Gazelle API
last_sync_at TIMESTAMPTZ               -- Dernière synchronisation
```

**⚠️ RÈGLES:**
- **NE JAMAIS** utiliser de colonnes qui n'existent pas dans les migrations
- **TOUJOURS** vérifier si la migration 002 est exécutée avant d'utiliser ses colonnes
- **NE JAMAIS** inventer de noms de colonnes (ex: "product_id" au lieu de "gazelle_product_id")
- **NE JAMAIS** utiliser "active" (n'existe pas) → utiliser "is_active"

### Table: `inventaire_techniciens`

**Migration:** `modules/inventaire/migrations/001_create_inventory_tables.sql`

```sql
id UUID PRIMARY KEY
code_produit TEXT NOT NULL REFERENCES produits_catalogue(code_produit)
technicien TEXT NOT NULL              -- Nom du technicien (ex: "Allan", "Nicolas")
quantite_stock DECIMAL(10,2) NOT NULL DEFAULT 0
emplacement TEXT                       -- Localisation (ex: "Atelier", "Camion")
notes TEXT
derniere_verification TIMESTAMPTZ
created_at TIMESTAMPTZ DEFAULT NOW()
updated_at TIMESTAMPTZ DEFAULT NOW()

UNIQUE(code_produit, technicien, emplacement)
```

**⚠️ IMPORTANT:**
- `technicien` doit être un **NOM** (pas un ID Supabase)
- Utiliser le mapping des techniciens pour convertir les IDs

### Table: `transactions_inventaire`

**Migration:** `modules/inventaire/migrations/001_create_inventory_tables.sql`

```sql
id UUID PRIMARY KEY
inventaire_id UUID REFERENCES inventaire_techniciens(id)
code_produit TEXT NOT NULL REFERENCES produits_catalogue(code_produit)
technicien TEXT NOT NULL
type_transaction TEXT NOT NULL         -- "ajout", "retrait", "transfert", "correction"
quantite DECIMAL(10,2) NOT NULL
quantite_avant DECIMAL(10,2)
quantite_apres DECIMAL(10,2)
motif TEXT
reference_client TEXT
reference_facture TEXT
notes TEXT
created_by TEXT
created_at TIMESTAMPTZ DEFAULT NOW()
```

---

## 🔌 Schéma SQL Server Gazelle (V4)

**⚠️ RÈGLE IMPORTANTE:** On lit SEULEMENT depuis V4, on ne modifie JAMAIS V4.

### Table: `inv.Products`

```sql
ProductId INTEGER PRIMARY KEY
Sku TEXT                                -- Code produit (peut être NULL)
Name TEXT                               -- Nom du produit
UnitCost DECIMAL(10,2)                  -- Prix unitaire
Active BIT                              -- 1 = actif, 0 = inactif
```

**⚠️ COLONNES QUI N'EXISTENT PAS:**
- ❌ `Code` (n'existe pas, utiliser `Sku`)
- ❌ `IsDeleted` (n'existe pas, utiliser `Active`)
- ❌ `Description` (n'existe pas dans Products)
- ❌ `Unit` (n'existe pas dans Products)
- ❌ `Supplier` (n'existe pas dans Products)
- ❌ `UnitPrice` (n'existe pas, utiliser `UnitCost`)

### Table: `inv.ProductDisplay`

```sql
ProductId INTEGER REFERENCES inv.Products(ProductId)
Category TEXT                           -- Catégorie
VariantGroup TEXT                       -- Groupe de variantes
VariantLabel TEXT                       -- Label de variante
DisplayOrder INTEGER                    -- Ordre d'affichage
Active BIT                              -- 1 = actif, 0 = inactif
```

**⚠️ COLONNES QUI N'EXISTENT PAS:**
- ❌ `HasCommission` (n'existe pas dans V4)
- ❌ `CommissionRate` (n'existe pas dans V4)
- ❌ Ces colonnes sont initialisées à FALSE/0.00 dans V5

### Table: `inv.Inventory`

```sql
InventoryId INTEGER PRIMARY KEY
ProductId INTEGER REFERENCES inv.Products(ProductId)
TechnicianId TEXT                       -- ID du technicien (peut être un ID Supabase)
Quantity DECIMAL(10,2)                  -- Quantité en stock
ReorderThreshold DECIMAL(10,2)         -- Seuil de réapprovisionnement
UpdatedAt DATETIME                      -- Dernière mise à jour
```

**⚠️ IMPORTANT:**
- `TechnicianId` peut être un ID Supabase (`usr_xxx`) ou un nom
- Il faut mapper vers un nom avant d'insérer dans `inventaire_techniciens`

---

## 🔄 Mapping des Colonnes (V4 → V5)

### Produits (inv.Products + inv.ProductDisplay → produits_catalogue)

| V4 (SQL Server) | V5 (Supabase) | Notes |
|----------------|---------------|-------|
| `p.Sku` | `code_produit` | Si NULL, utiliser `PROD-{ProductId}` |
| `p.Name` | `nom` | |
| `pd.Category` ou `'Produit'` | `categorie` | Fallback si NULL |
| `NULL` | `description` | N'existe pas dans V4 |
| `'unité'` | `unite_mesure` | Valeur par défaut |
| `p.UnitCost` | `prix_unitaire` | |
| `NULL` | `fournisseur` | N'existe pas dans V4 |
| `pd.VariantGroup` | `variant_group` | |
| `pd.VariantLabel` | `variant_label` | |
| `pd.DisplayOrder` ou `0` | `display_order` | |
| `pd.Active` ou `p.Active` ou `1` | `is_active` | |
| `p.ProductId` | `gazelle_product_id` | (Migration 002) |
| `FALSE` | `has_commission` | Initialisé dans V5 |
| `0.00` | `commission_rate` | Initialisé dans V5 |

### Inventaire (inv.Inventory → inventaire_techniciens)

| V4 (SQL Server) | V5 (Supabase) | Notes |
|----------------|---------------|-------|
| `p.Sku` ou `PROD-{ProductId}` | `code_produit` | |
| `i.TechnicianId` → **mappé** | `technicien` | **MUST MAP** vers nom |
| `i.Quantity` | `quantite_stock` | |
| `'Atelier'` | `emplacement` | Valeur par défaut |
| `i.UpdatedAt` | `derniere_verification` | |

---

## 📝 Règles d'Import

### 1. **NE JAMAIS modifier V4 (SQL Server)**
- Lecture SEULEMENT
- V4 continue de fonctionner normalement

### 2. **Vérifier les migrations avant d'importer**
- Migration 001: Tables de base
- Migration 002: Colonnes de classification (optionnel)
- Si migration 002 non exécutée, retirer ses colonnes des données

### 3. **Mapping des techniciens**
- **TOUJOURS** mapper les IDs Supabase vers les noms
- **NE JAMAIS** laisser des IDs (`usr_xxx`) dans le champ `technicien`
- Utiliser le mapping officiel ci-dessus

### 4. **Gestion des NULL**
- Si `Sku` est NULL → utiliser `PROD-{ProductId}`
- Si `Category` est NULL → utiliser `'Produit'`
- Si `DisplayOrder` est NULL → utiliser `0`
- Si `Active` est NULL → utiliser `1` (actif)

### 5. **Colonnes qui n'existent pas**
- Si une colonne n'existe pas dans V4 → mettre `NULL` ou valeur par défaut
- **NE JAMAIS** essayer de lire une colonne qui n'existe pas (erreur SQL)

---

## 🔍 Où Trouver les Informations

### Pour les techniciens:
- **Fichier:** `README.md` (section "Mapping des techniciens")
- **Script:** `scripts/mapper_techniciens.py` (contient le mapping)

### Pour les colonnes:
- **Migrations SQL:** `modules/inventaire/migrations/001_*.sql` et `002_*.sql`
- **Schéma Supabase:** Vérifier dans Supabase Dashboard → Table Editor

### Pour SQL Server:
- **Scripts existants:** `scripts/import_gazelle_product_display.py` (lignes 150-195)
- **Scripts existants:** `scripts/import_inventaire_techniciens.py` (lignes 60-77)

---

## ⚠️ Checklist Avant de Créer/Modifier un Script

- [ ] J'ai consulté le mapping des techniciens
- [ ] J'ai vérifié les colonnes dans les migrations SQL
- [ ] J'ai vérifié quelles colonnes existent dans SQL Server V4
- [ ] J'ai vérifié le mapping V4 → V5
- [ ] Je n'ai pas inventé de noms de colonnes
- [ ] J'ai géré les cas NULL correctement
- [ ] J'ai mappé les IDs techniciens vers les noms

---

## 📞 En Cas de Doute

**NE PAS DEVINER.** Toujours:
1. Consulter ce document
2. Vérifier les migrations SQL
3. Vérifier les scripts existants
4. Demander à l'utilisateur si nécessaire




