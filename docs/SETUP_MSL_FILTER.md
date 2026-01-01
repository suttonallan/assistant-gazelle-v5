# 📋 Setup: Filtrage et Gestion des Items MSL

## 🎯 Objectif

Visualiser et gérer tous les items de la **Master Service List (MSL) Gazelle** importés dans le catalogue local, avec capacité de:
1. Filtrer par statut (exclu/inclus)
2. Distinguer items commission vs inventaire
3. Voir les associations avec l'inventaire
4. Identifier rapidement les items sans configuration

---

## 🔑 Concepts Clés

### Statut d'un Item MSL

**EXCLU** 🚫
- N'a pas de règle de consommation
- N'affecte pas la commission
- Exemple: Services obsolètes, items non utilisés

**INCLUS** ✅
- A une règle de consommation OU affecte la commission
- Exemple: Accord Piano (inventaire), Grand entretien (commission)

### Types d'Impact

**Commission** 💰
- Item marqué `affects_commission = true`
- Génère une commission pour le technicien
- N'affecte PAS l'inventaire
- Exemple: Grand entretien, Évaluation

**Inventaire** 📦
- Item avec règles de consommation dans `service_inventory_consumption`
- Consomme des matériaux/fournitures
- Peut également générer une commission
- Exemple: Entretien annuel PLS (consomme feutres, cordes)

**Aucun Impact** ⚪
- Ni commission, ni inventaire
- Items exclus ou non configurés

---

## 📊 Architecture

### Nouvelle Colonne: `affects_commission`

```sql
ALTER TABLE produits_catalogue
ADD COLUMN affects_commission BOOLEAN DEFAULT FALSE;
```

Cette colonne permet de marquer explicitement les services qui génèrent une commission SANS affecter l'inventaire.

### Relations

```
produits_catalogue
├─ gazelle_product_id (TEXT) - ID MSL Gazelle
├─ affects_commission (BOOLEAN) - Génère commission?
└─ code_produit (TEXT)

service_inventory_consumption
├─ service_gazelle_id → produits_catalogue.gazelle_product_id
└─ material_code_produit → produits_catalogue.code_produit
```

### Logique de Filtrage

```javascript
// Un item est EXCLU si:
const isExcluded = (item) => {
  const hasConsumptionRule = consumptionRules.some(
    rule => rule.service_gazelle_id === item.gazelle_product_id
  )
  const affectsCommission = item.affects_commission === true

  return !hasConsumptionRule && !affectsCommission
}

// Type d'impact:
const getItemType = (item) => {
  if (hasConsumptionRule) return 'inventory'
  if (item.affects_commission) return 'commission'
  return 'none'
}
```

---

## 🚀 Installation

### Étape 1: Ajouter la colonne `affects_commission`

**Option A: Via Supabase Dashboard** ✅ Recommandé

1. Connectez-vous à [Supabase Dashboard](https://supabase.com/dashboard)
2. Sélectionnez votre projet
3. Allez dans **SQL Editor**
4. Cliquez sur **New Query**
5. Copiez le contenu de [`scripts/add_affects_commission_column.sql`](../scripts/add_affects_commission_column.sql)
6. Exécutez (bouton **Run**)
7. Vérifiez le message de succès

**Vérification:**

```sql
-- Dans SQL Editor Supabase
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'produits_catalogue'
  AND column_name = 'affects_commission';
```

Résultat attendu:
```
column_name         | data_type | column_default
--------------------+-----------+----------------
affects_commission  | boolean   | false
```

### Étape 2: Vérifier l'interface

1. Connectez-vous comme **Admin**
2. Menu **Inventaire** → Onglet **📋 Filtrer MSL**
3. Vous devriez voir:
   - Statistiques globales
   - Filtres (recherche, exclu/inclus, type)
   - Table des items MSL avec associations

---

## 🎨 Interface Utilisateur

### Accès

1. Connectez-vous comme **Admin**
2. Menu **Inventaire** → Onglet **📋 Filtrer MSL**

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│  📋 Gestion des Items MSL Gazelle                       │
├─────────────────────────────────────────────────────────┤
│  Statistiques:                                           │
│  [TOTAL: 143] [INCLUS: 45] [EXCLUS: 98]                │
│  [COMMISSION: 12] [INVENTAIRE: 33]                      │
├─────────────────────────────────────────────────────────┤
│  Filtres:                                                │
│  [Recherche...] [Tous/Inclus/Exclus] [Type] [Refresh]  │
├─────────────────────────────────────────────────────────┤
│  Table:                                                  │
│  Item MSL | ID Gazelle | Type | Statut | Commission |...│
│  ─────────────────────────────────────────────────────  │
│  Accord   | mit_...    | Svc  | INCLUS | ✓ Oui      |...│
│  Grand    | mit_...    | Svc  | INCLUS | ✓ Oui      |...│
└─────────────────────────────────────────────────────────┘
```

### Fonctionnalités

**Statistiques** 📊
- Total d'items MSL importés
- Nombre d'items inclus vs exclus
- Répartition commission vs inventaire

**Filtres** 🔍
- Recherche par nom
- Filtre exclu/inclus/tous
- Filtre par type (commission/inventaire/tous)
- Bouton actualiser

**Actions** ⚙️
- Toggle checkbox "Commission" (inline)
- Voir associations inventaire (liste)

---

## 🔗 Exemples de Configuration

### Exemple 1: Service avec Commission uniquement

**Contexte:** Grand entretien génère commission, ne consomme pas de matériel

```sql
UPDATE produits_catalogue
SET affects_commission = true
WHERE gazelle_product_id = 'mit_grand_entretien'
  AND nom ILIKE '%grand entretien%';
```

**Résultat dans l'interface:**
- Statut: **INCLUS** (vert)
- Commission: **✓ Oui** (checkbox cochée)
- Associations Inventaire: **Aucune association** (gris)

### Exemple 2: Service avec Inventaire uniquement

**Contexte:** Accord Piano consomme cordes, pas de commission

1. Créer règle de consommation:
```sql
INSERT INTO service_inventory_consumption (
  service_gazelle_id,
  service_code_produit,
  material_code_produit,
  quantity
) VALUES (
  'mit_accord_piano',
  'SERVICE-001',
  'PROD-4',  -- Cordes
  0.5
);
```

2. Ne PAS cocher `affects_commission`

**Résultat dans l'interface:**
- Statut: **INCLUS** (vert)
- Commission: **❌ Non** (checkbox non cochée)
- Associations Inventaire: **Cordes (×0.5)** (badge)

### Exemple 3: Service Hybride (Commission + Inventaire)

**Contexte:** Entretien annuel PLS génère commission ET consomme matériel

1. Marquer commission:
```sql
UPDATE produits_catalogue
SET affects_commission = true
WHERE gazelle_product_id = 'mit_entretien_annuel_pls';
```

2. Créer règles de consommation:
```sql
INSERT INTO service_inventory_consumption (
  service_gazelle_id,
  service_code_produit,
  material_code_produit,
  quantity
) VALUES
  ('mit_entretien_annuel_pls', 'SERVICE-010', 'PROD-4', 1.0),  -- Cordes
  ('mit_entretien_annuel_pls', 'SERVICE-010', 'PROD-8', 2.0);  -- Feutres
```

**Résultat dans l'interface:**
- Statut: **INCLUS** (vert)
- Commission: **✓ Oui** (checkbox cochée)
- Associations Inventaire: **Cordes (×1.0), Feutres (×2.0)** (badges)

### Exemple 4: Service Exclu

**Contexte:** Service obsolète, jamais utilisé

**Configuration:** Aucune (état par défaut)
- `affects_commission = false`
- Aucune règle dans `service_inventory_consumption`

**Résultat dans l'interface:**
- Statut: **EXCLU** (gris)
- Commission: **❌ Non**
- Associations Inventaire: **Aucune association**

---

## 🧪 Tests

### Test 1: Marquer un item comme affectant la commission

1. Onglet **📋 Filtrer MSL**
2. Chercher "Grand entretien"
3. Cocher la checkbox **Commission**
4. Vérifier le badge passe de **EXCLU** à **INCLUS**
5. Rafraîchir → badge reste **INCLUS**

### Test 2: Filtrer les items exclus

1. Sélectionner filtre **Exclus uniquement**
2. Vérifier que seuls les items avec badge **EXCLU** apparaissent
3. Compter le nombre → doit correspondre à la statistique "EXCLUS"

### Test 3: Voir associations inventaire

1. Chercher "Accord Piano"
2. Vérifier colonne **Associations Inventaire**
3. Doit afficher les matériaux associés avec quantités
4. Exemple: "Cordes (×0.5)"

### Test 4: Vérification Supabase

```sql
-- Items avec commission activée
SELECT
  nom,
  gazelle_product_id,
  affects_commission
FROM produits_catalogue
WHERE affects_commission = true
  AND gazelle_product_id IS NOT NULL
ORDER BY nom;

-- Items avec règles de consommation
SELECT
  p.nom AS service,
  m.nom AS materiau,
  sic.quantity
FROM service_inventory_consumption sic
JOIN produits_catalogue p ON p.gazelle_product_id = sic.service_gazelle_id
JOIN produits_catalogue m ON m.code_produit = sic.material_code_produit
ORDER BY p.nom, m.nom;

-- Items EXCLUS (ni commission ni inventaire)
SELECT
  p.nom,
  p.gazelle_product_id,
  p.affects_commission,
  COUNT(sic.id) AS nb_rules
FROM produits_catalogue p
LEFT JOIN service_inventory_consumption sic
  ON sic.service_gazelle_id = p.gazelle_product_id
WHERE p.gazelle_product_id IS NOT NULL
GROUP BY p.id, p.nom, p.gazelle_product_id, p.affects_commission
HAVING p.affects_commission = false
  AND COUNT(sic.id) = 0
ORDER BY p.nom;
```

---

## 🔧 Workflow Typique

### Scénario: Configurer tous les items MSL après import

**Étape 1: Importer le MSL**
1. Onglet **🔄 Sync Gazelle**
2. Cliquer **📥 Importer tous les items MSL**
3. Attendre confirmation (ex: 143 items importés)

**Étape 2: Identifier les items à configurer**
1. Aller onglet **📋 Filtrer MSL**
2. Regarder statistique **EXCLUS** (ex: 98)
3. Sélectionner filtre **Exclus uniquement**

**Étape 3: Trier les items**

Pour chaque item exclu, décider:
- **Commission?** → Cocher la checkbox **Commission**
- **Inventaire?** → Aller onglet **📦 Consommation** et créer règles
- **Les deux?** → Faire les deux actions
- **Aucun?** → Laisser tel quel (reste exclu)

**Étape 4: Vérifier la progression**
- Rafraîchir la page
- Vérifier statistique **EXCLUS** diminue
- Vérifier statistiques **COMMISSION** et **INVENTAIRE** augmentent

**Objectif:** Réduire le nombre d'items **EXCLUS** à zéro (ou proche)

---

## 🐛 Troubleshooting

### Problème: Colonne "affects_commission" n'existe pas

**Erreur:**
```
column "affects_commission" does not exist
```

**Solution:**
1. Vérifier que le SQL [`scripts/add_affects_commission_column.sql`](../scripts/add_affects_commission_column.sql) a été exécuté
2. Re-exécuter le SQL dans Supabase Dashboard
3. Rafraîchir l'application

### Problème: Aucun item MSL visible

**Causes possibles:**
- Aucun item avec `gazelle_product_id` dans le catalogue
- MSL pas encore importé

**Solution:**
1. Aller onglet **🔄 Sync Gazelle**
2. Cliquer **📥 Importer tous les items MSL**
3. Attendre confirmation
4. Revenir onglet **📋 Filtrer MSL**

### Problème: Associations inventaire ne s'affichent pas

**Causes possibles:**
- Table `service_inventory_consumption` vide
- Aucune règle créée pour ce service

**Solution:**
1. Vérifier que la table `service_inventory_consumption` existe (voir [`docs/SETUP_SERVICE_CONSUMPTION.md`](./SETUP_SERVICE_CONSUMPTION.md))
2. Créer des règles via onglet **📦 Consommation**
3. Rafraîchir l'onglet **📋 Filtrer MSL**

### Problème: Checkbox "Commission" ne se sauvegarde pas

**Causes possibles:**
- Erreur API
- Problème de permissions Supabase

**Solution:**
1. Ouvrir la console navigateur (F12)
2. Regarder les erreurs réseau
3. Vérifier permissions RLS sur `produits_catalogue`:
```sql
-- Dans Supabase SQL Editor
SELECT tablename, policyname
FROM pg_policies
WHERE tablename = 'produits_catalogue';
```

---

## 📝 TODO après installation

- [ ] Exécuter le SQL `add_affects_commission_column.sql` dans Supabase Dashboard
- [ ] Vérifier que l'onglet **📋 Filtrer MSL** apparaît (admin uniquement)
- [ ] Importer le MSL complet (onglet **🔄 Sync Gazelle**)
- [ ] Identifier les 10-20 services prioritaires
- [ ] Marquer les services commission (Grand entretien, Évaluation, etc.)
- [ ] Créer les règles de consommation inventaire (onglet **📦 Consommation**)
- [ ] Vérifier que les statistiques correspondent:
  - TOTAL = items importés MSL
  - INCLUS = items avec commission OU inventaire
  - EXCLUS = items sans configuration

---

## 🔗 Intégration avec autres fonctionnalités

### Lien avec Service Consumption (📦 Consommation)

- Les associations inventaire affichées dans **Filtrer MSL** proviennent de `service_inventory_consumption`
- Pour créer/modifier ces associations, utiliser l'onglet **📦 Consommation**

### Lien avec Sync Gazelle (🔄)

- Le MSL doit être importé via **Sync Gazelle** avant d'utiliser **Filtrer MSL**
- La synchronisation des prix peut être faite via **Sync auto**

### Lien avec Facturation

- Les items avec `affects_commission = true` génèrent des commissions sur les factures
- Les items avec règles de consommation déduisent automatiquement l'inventaire

---

## 📚 Ressources

- SQL Migration: [`scripts/add_affects_commission_column.sql`](../scripts/add_affects_commission_column.sql)
- Component: [`frontend/src/components/MSLFilterManager.jsx`](../frontend/src/components/MSLFilterManager.jsx)
- Integration: [`frontend/src/components/InventaireDashboard.jsx`](../frontend/src/components/InventaireDashboard.jsx) (lignes 4, 465-473, 677-680)
- Service Consumption: [`docs/SETUP_SERVICE_CONSUMPTION.md`](./SETUP_SERVICE_CONSUMPTION.md)

---

**Version**: 1.0
**Date**: 2025-12-21
**Auteur**: Assistant Gazelle V5 Setup
