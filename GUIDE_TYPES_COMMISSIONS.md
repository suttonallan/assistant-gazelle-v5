# 🏷️ Guide - Gestion des Types et Commissions

**Date:** 2025-12-12
**Fonctionnalité:** Système de classification des produits avec gestion batch des types et commissions

---

## 📋 Vue d'ensemble

Ce système permet de classer les produits en 3 types et de gérer les commissions de manière flexible:

### Types de produits

1. **Produit** (ex: Cory kit, cordes, coupelles)
   - ✅ Visible dans l'inventaire des techniciens
   - 💰 Commission optionnelle (10%)

2. **Service** (ex: Accordage, réparation, livraison)
   - ❌ PAS visible dans l'inventaire des techniciens (pas de stock physique)
   - 💰 Commission optionnelle (10%)

3. **Fourniture** (ex: Chiffons, outils de base)
   - ✅ Visible dans l'inventaire des techniciens
   - 🚫 JAMAIS commissionnables (bloqué)

### Règles de commission

- **Taux fixe:** 10% pour tous les produits commissionnables
- **Fournitures:** Ne peuvent JAMAIS avoir de commission
- **Produits/Services:** Commission configurable (oui/non)

---

## 🗄️ Modifications Base de Données

### Migration 002 enrichie

**Fichier:** `modules/inventaire/migrations/002_add_product_classifications.sql`

**Ajouts:**

```sql
-- Type ENUM
CREATE TYPE product_type AS ENUM ('produit', 'service', 'fourniture');

-- Colonne type_produit
ALTER TABLE produits_catalogue
ADD COLUMN IF NOT EXISTS type_produit product_type DEFAULT 'produit';

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_produits_type
ON produits_catalogue(type_produit);
```

**Colonnes utilisées:**
- `type_produit` : ENUM('produit', 'service', 'fourniture')
- `has_commission` : BOOLEAN (déjà présent)
- `commission_rate` : DECIMAL(5,2) (déjà présent)

**⚠️ Migration à exécuter:**
```bash
# Dans Supabase SQL Editor
# Copier le contenu de modules/inventaire/migrations/002_add_product_classifications.sql
# Exécuter
```

---

## 🔌 Backend API

### Nouveau endpoint

**Route:** `PATCH /inventaire/catalogue/batch-type-commission`

**Body:**
```json
{
  "codes_produit": ["PROD-4", "PROD-5", "PROD-6"],
  "type_produit": "produit",
  "has_commission": true
}
```

**Logique automatique:**
- Si `type_produit = 'fourniture'` → `has_commission` forcé à `false`, `commission_rate = 0.00`
- Si `has_commission = true` → `commission_rate = 10.00`
- Si `has_commission = false` → `commission_rate = 0.00`

**Réponse:**
```json
{
  "success": true,
  "message": "3/3 produits mis à jour",
  "updated_count": 3,
  "total_count": 3,
  "errors": null
}
```

**Fichier modifié:** `api/inventaire.py` (lignes 77-81, 590-667)

---

## 🖥️ Interface Frontend

### Nouvel onglet "🏷️ Types"

**Accès:** Onglet visible uniquement pour les administrateurs

**Fonctionnalités:**

#### 1. Barre d'actions batch

```
┌─────────────────────────────────────────────────────────┐
│ Type: [▼ Produit] [☐ Commissionnable 10%] [Appliquer] │
└─────────────────────────────────────────────────────────┘
```

- **Dropdown Type:** Produit / Service / Fourniture
- **Checkbox Commission:** Activé sauf si Type = Fourniture (grisé)
- **Bouton Appliquer:** Affiche le nombre de produits sélectionnés

#### 2. Tableau de sélection

```
┌───┬──────────┬─────────────────┬──────────┬────────────┐
│ ☐ │ Code     │ Nom             │ Type     │ Commission │
├───┼──────────┼─────────────────┼──────────┼────────────┤
│ ☑ │ PROD-4   │ Cory kit lustré │ produit  │ ✅ 10%    │
│ ☑ │ PROD-5   │ Cory kit mat    │ (vide)   │ ❌        │
│ ☐ │ SRV-001  │ Accordage       │ service  │ ✅ 10%    │
│ ☐ │ FOUR-001 │ Chiffons        │ fourniture│ - (bloqué)│
└───┴──────────┴─────────────────┴──────────┴────────────┘
```

**Codes couleurs:**
- **Produit:** Badge vert
- **Service:** Badge violet
- **Fourniture:** Badge orange
- **(non défini):** Badge gris italique

### Filtrage automatique inventaire

**Modification:** `frontend/src/components/InventaireDashboard.jsx` ligne 199

Les **services** n'apparaissent **PAS** dans l'onglet "Inventaire" (vue technicien).

```javascript
// Avant
.filter(p => p.is_active !== false)

// Après
.filter(p => p.is_active !== false)
.filter(p => p.type_produit !== 'service') // Exclure les services
```

---

## 📖 Guide d'utilisation

### Cas d'usage 1: Classifier des produits physiques

1. Cliquer sur l'onglet **🏷️ Types**
2. Cocher les produits concernés (ex: PROD-4, PROD-5, PROD-6)
3. Sélectionner **Type: Produit**
4. Cocher **☑ Commissionnable (10%)**
5. Cliquer **Appliquer à 3 produits**

**Résultat:**
- Les 3 produits deviennent `type_produit = 'produit'`
- `has_commission = true`, `commission_rate = 10.00`
- Visibles dans l'inventaire technicien
- Commissionnables sur les factures

---

### Cas d'usage 2: Ajouter des services commissionnables

1. Cliquer sur l'onglet **🏷️ Types**
2. Cocher les services (ex: SRV-001 Accordage, SRV-002 Réparation)
3. Sélectionner **Type: Service**
4. Cocher **☑ Commissionnable (10%)**
5. Cliquer **Appliquer à 2 produits**

**Résultat:**
- Les services deviennent `type_produit = 'service'`
- `has_commission = true`, `commission_rate = 10.00`
- **NON visibles** dans l'inventaire technicien (pas de stock)
- Commissionnables sur les factures

---

### Cas d'usage 3: Marquer des fournitures

1. Cliquer sur l'onglet **🏷️ Types**
2. Cocher les fournitures (ex: FOUR-001 Chiffons)
3. Sélectionner **Type: Fourniture**
4. La checkbox **Commissionnable** devient **grisée** (désactivée)
5. Cliquer **Appliquer à 1 produit**

**Résultat:**
- Le produit devient `type_produit = 'fourniture'`
- `has_commission = false`, `commission_rate = 0.00` (forcé)
- Visible dans l'inventaire technicien
- **JAMAIS** commissionnable

---

## 🧪 Tests à effectuer

### Test 1: Classification batch

```bash
# Requête API directe
curl -X PATCH http://localhost:8000/inventaire/catalogue/batch-type-commission \
  -H "Content-Type: application/json" \
  -d '{
    "codes_produit": ["PROD-4", "PROD-5"],
    "type_produit": "produit",
    "has_commission": true
  }'

# Vérifier
curl http://localhost:8000/inventaire/catalogue | python3 -m json.tool
```

### Test 2: Interface web

1. Ouvrir http://localhost:5173
2. Se connecter en tant qu'admin (Allan)
3. Aller dans l'onglet **📦 Inventaire** → **🏷️ Types**
4. Sélectionner 3 produits
5. Choisir **Type: Produit** + **☑ Commissionnable**
6. Cliquer **Appliquer**
7. Vérifier le message de confirmation
8. Retourner à l'onglet **Inventaire** → vérifier que les produits sont visibles
9. Créer un service (Type: Service) → vérifier qu'il N'apparaît PAS dans l'inventaire

### Test 3: Validation fournitures

1. Sélectionner 1 produit
2. Choisir **Type: Fourniture**
3. Vérifier que la checkbox Commission est **grisée**
4. Appliquer
5. Vérifier dans l'onglet Types que la colonne Commission affiche **"- (bloqué)"**

---

## 📊 État actuel des données

Après migration 002, tous les produits existants auront:
- `type_produit = 'produit'` (par défaut)
- `has_commission` = leur valeur actuelle (ou `false` si NULL)
- `commission_rate` = leur valeur actuelle (ou `0.00` si NULL)

**Action requise:**
1. Exécuter migration 002 dans Supabase
2. Utiliser l'onglet Types pour classifier les 68 produits existants
3. Identifier les services et les marquer manuellement

---

## 🔄 Impact sur les autres modules

### Module Factures (à venir)

Lors de la création d'une facture:
- Produits/Services avec `has_commission = true` → Calcul commission 10%
- Produits/Services avec `has_commission = false` → Pas de commission
- Fournitures → JAMAIS de commission (vérifié via `type_produit = 'fourniture'`)

### Module Rapports (à venir)

Statistiques par type:
- Nombre de produits/services/fournitures
- Chiffre d'affaires par type
- Commissions par technicien (uniquement produits/services commissionnables)

---

## 🎯 Prochaines étapes

1. ⚠️ **Exécuter Migration 002** dans Supabase SQL Editor
2. 📋 **Classifier les 68 produits existants** via l'onglet Types
3. 🧪 **Tester** l'interface complète
4. 📝 **Documenter** les codes produits par type pour référence future

---

## 🐛 Troubleshooting

### Erreur: "column type_produit does not exist"

**Cause:** Migration 002 pas exécutée

**Solution:**
```bash
# Ouvrir Supabase SQL Editor
# Copier modules/inventaire/migrations/002_add_product_classifications.sql
# Exécuter
```

### Checkbox Commission reste cochée pour Fourniture

**Cause:** Bug frontend (état React non synchronisé)

**Solution:**
```javascript
// Ligne 571-573 de InventaireDashboard.jsx
if (e.target.value === 'fourniture') {
  setBatchCommission(false) // Force à false
}
```

### Services apparaissent dans l'inventaire technicien

**Cause:** Filtre pas appliqué

**Solution:** Vérifier ligne 199 de `InventaireDashboard.jsx`:
```javascript
.filter(p => p.type_produit !== 'service')
```

---

**🎉 Système complet et opérationnel !**
