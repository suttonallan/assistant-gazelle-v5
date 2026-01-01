# 📦 Setup: Association Services → Fournitures

## 🎯 Objectif

Associer les **services MSL Gazelle** (ex: "Accord Piano") avec les **matériaux consommés** (ex: "Cordes", "Feutres") pour:
1. Calculer automatiquement l'impact sur l'inventaire lors de la facturation
2. Suivre la consommation réelle de matériel par service
3. Prédire les besoins de réapprovisionnement

---

## 📊 Architecture

### Modèle de données

```
Table: service_inventory_consumption
├─ service_gazelle_id (TEXT) - ID MSL Gazelle (priorité 1)
├─ service_code_produit (TEXT) - Code interne (fallback)
├─ material_code_produit (TEXT) - Code matériau
├─ quantity (DECIMAL) - Quantité consommée par service
├─ is_optional (BOOLEAN) - Optionnel ou obligatoire
└─ created_at, updated_at
```

### Logique de filtrage

**DÉCLENCHEURS (Colonne gauche)**
- Items avec `gazelle_product_id` (importés MSL)
- Items de type `service` ou `accessoire`
- **Critère**: Ce sont les items qui DÉCLENCHENT la consommation

**FOURNITURES (Colonne droite)**
- Items avec `is_inventory_item = true`
- Items de type `produit` ou `fourniture`
- **Critère**: Ce sont les items CONSOMMÉS

### Clés de liaison

**Priorité Gazelle ID:**
```javascript
const serviceKey = service.gazelle_product_id || service.code_produit
```

1. **Si `gazelle_product_id` existe**: Utiliser l'ID MSL Gazelle
2. **Sinon**: Utiliser le code interne

---

## 🚀 Installation

### Étape 1: Créer la table dans Supabase

**Option A: Via Supabase Dashboard** ✅ Recommandé

1. Connectez-vous à [Supabase Dashboard](https://supabase.com/dashboard)
2. Sélectionnez votre projet
3. Allez dans **SQL Editor**
4. Cliquez sur **New Query**
5. Copiez le contenu de [`scripts/create_service_consumption_table.sql`](../scripts/create_service_consumption_table.sql)
6. Exécutez (bouton **Run**)
7. Vérifiez le message de succès

**Option B: Via Script Python**

```bash
python3 scripts/create_service_consumption_table.py
```

Le script:
- Affiche le SQL à exécuter
- Vérifie si la table existe déjà
- Donne des instructions claires

**Option C: Via psql (si accès direct)**

```bash
psql 'postgresql://[USER]:[PASSWORD]@[HOST]:5432/postgres' \
  -f scripts/create_service_consumption_table.sql
```

### Étape 2: Vérifier l'installation

Après exécution du SQL, vérifiez:

```sql
-- Dans SQL Editor Supabase
SELECT * FROM service_inventory_consumption LIMIT 1;
```

Si aucune erreur → ✅ Table créée!

---

## 🎨 Interface Utilisateur

### Accès

1. Connectez-vous comme **Admin**
2. Menu **Inventaire** → Onglet **📦 Consommation**

### Workflow

```
GAUCHE: Liste des services
  ↓ Cliquer sur "Accord Piano"

DROITE: Matériaux consommés
  → Rechercher "Cordes"
  → Ajouter: quantité 0.5
  → Badge vert ✓ apparaît sur le service
```

### Fonctionnalités

**Colonne gauche (Services)**
- ⭐ Étoile favori (localStorage)
- 🟢 Toggle suivi inventaire
- 🔢 Badge nombre de matériaux associés
- 🔍 Recherche par nom
- ☑️ Filtre "Suivi activé uniquement"

**Colonne droite (Matériaux)**
- ➕ Ajouter matériau
- ✏️ Éditer quantité inline
- 🗑️ Supprimer association
- 🔍 Recherche prédictive
- 📊 Liste des matériaux déjà associés

---

## 🔗 Exemples d'associations

### Exemple 1: Accord Piano

```json
{
  "service_gazelle_id": "mit_accord_piano_2024",
  "service_code_produit": "SERVICE-001",
  "material_code_produit": "PROD-4",
  "quantity": 0.5,
  "is_optional": false
}
```

**Interprétation**: Chaque accord consomme **0.5 unité** de cordes (PROD-4)

### Exemple 2: Installation Dampp-Chaser

```json
{
  "service_gazelle_id": "mit_dampp_chaser_install",
  "service_code_produit": "SERVICE-015",
  "material_code_produit": "PROD-12",
  "quantity": 1.0,
  "is_optional": false
}
```

**Interprétation**: Chaque installation consomme **1 système** Dampp-Chaser complet

### Exemple 3: Matériau optionnel

```json
{
  "service_gazelle_id": "mit_reparation_mecanique",
  "service_code_produit": "SERVICE-003",
  "material_code_produit": "PROD-33",
  "quantity": 2.0,
  "is_optional": true
}
```

**Interprétation**: La réparation peut utiliser **2 chevilles** (optionnel, pas de déduction auto)

---

## 🔧 API Endpoints

### Lister les règles

```bash
GET /inventaire/service-consumption/rules
GET /inventaire/service-consumption/rules?service_gazelle_id=mit_xxx
```

### Créer une règle

```bash
POST /inventaire/service-consumption/rules
Content-Type: application/json

{
  "service_gazelle_id": "mit_accord_piano",
  "service_code_produit": "SERVICE-001",
  "material_code_produit": "PROD-4",
  "quantity": 0.5,
  "is_optional": false
}
```

### Supprimer une règle

```bash
DELETE /inventaire/service-consumption/rules/{rule_id}
```

---

## 🧪 Tests

### Test 1: Créer une association

1. Onglet **Consommation**
2. Sélectionner un service à gauche
3. Chercher un matériau à droite
4. Cliquer **Ajouter**
5. Vérifier le badge vert sur le service

### Test 2: Vérifier dans Supabase

```sql
SELECT
  s.nom AS service_nom,
  m.nom AS materiau_nom,
  sic.quantity,
  sic.is_optional
FROM service_inventory_consumption sic
JOIN produits_catalogue s ON s.gazelle_product_id = sic.service_gazelle_id
JOIN produits_catalogue m ON m.code_produit = sic.material_code_produit
LIMIT 10;
```

### Test 3: Filtrage UI

**Test "Déclencheurs uniquement":**
- Colonne gauche doit afficher SEULEMENT les services MSL + accessoires
- Pas de produits physiques à gauche

**Test "Fournitures uniquement":**
- Colonne droite doit afficher SEULEMENT produits + fournitures
- Pas de services à droite

---

## 📝 TODO après installation

- [ ] Exécuter le SQL dans Supabase Dashboard
- [ ] Tester l'interface dans l'onglet Consommation
- [ ] Mapper les 5-10 services prioritaires:
  - Accord Piano → Cordes
  - Dampp-Chaser → Système Dampp-Chaser
  - Réparation mécanique → Feutres, Chevilles
  - Installation Accessoires → Items spécifiques
- [ ] Valider le workflow end-to-end:
  - Créer une facture avec un service
  - Vérifier l'impact sur l'inventaire
  - Confirmer la déduction automatique

---

## 🐛 Troubleshooting

### Erreur 404: Table n'existe pas

```
Could not find the table 'service_inventory_consumption'
```

**Solution**: Exécuter le SQL dans Supabase Dashboard

### Colonne gauche vide

**Causes possibles**:
- Aucun service avec `gazelle_product_id` dans le catalogue
- Aucun item de type `service` ou `accessoire`

**Solution**: Importer des services MSL via l'onglet **Sync Gazelle**

### Colonne droite vide

**Causes possibles**:
- Aucun produit avec `is_inventory_item = true`
- Aucun item de type `produit` ou `fourniture`

**Solution**: Marquer des produits comme "suivi inventaire" dans l'onglet **Admin**

---

## 📚 Ressources

- SQL: [`scripts/create_service_consumption_table.sql`](../scripts/create_service_consumption_table.sql)
- Script: [`scripts/create_service_consumption_table.py`](../scripts/create_service_consumption_table.py)
- Component: [`frontend/src/components/ServiceConsumptionManager.jsx`](../frontend/src/components/ServiceConsumptionManager.jsx)
- API: [`api/inventaire.py`](../api/inventaire.py) (lignes 1700+)

---

**Version**: 1.0
**Date**: 2025-12-21
**Auteur**: Assistant Gazelle V5 Setup
