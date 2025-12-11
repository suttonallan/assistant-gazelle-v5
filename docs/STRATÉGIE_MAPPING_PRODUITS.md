# Stratégie de Mapping des Produits Gazelle ↔ Supabase

## 🎯 Objectif

Créer un système de mapping persistant entre les produits importés depuis l'**API Gazelle (CRM)** et les produits dans **Supabase V5**, pour que les correspondances soient conservées lors des imports futurs (changements de prix, ajouts d'items, etc.).

## 📋 Architecture

### 1. Base de données

**Table `produits_mapping`** (Migration 003)
- `gazelle_product_id` (TEXT, UNIQUE) - ID du produit dans Gazelle API
- `code_produit` (TEXT, FK) - Code du produit dans Supabase
- `gazelle_sku`, `gazelle_name` - Infos du produit Gazelle (pour référence)
- `mapped_by`, `mapped_at` - Qui/quand a créé le mapping
- `sync_status`, `last_synced_at` - Statut de synchronisation

### 2. Backend (FastAPI)

**Fichier:** `api/product_mapping.py`

**Endpoints:**
- `GET /inventaire/mapping/gazelle-products` - Liste tous les produits Gazelle
- `GET /inventaire/mapping/unmapped-gazelle` - Produits Gazelle non mappés
- `GET /inventaire/mapping/unmapped-supabase` - Produits Supabase sans mapping
- `GET /inventaire/mapping/mappings` - Tous les mappings existants
- `POST /inventaire/mapping/mappings` - Créer un mapping
- `DELETE /inventaire/mapping/mappings/{gazelle_product_id}` - Supprimer un mapping

**Client API:** `core/gazelle_api_client.py`
- Méthode `get_products()` - Récupère les produits depuis l'API GraphQL Gazelle

### 3. Frontend (React)

**Composant:** `ProductMappingInterface.jsx` (à créer)

**Fonctionnalités:**
- Vue côte à côte: Produits Gazelle (gauche) ↔ Produits Supabase (droite)
- Drag & drop ou sélection pour créer des mappings
- Liste des mappings existants avec possibilité de modifier/supprimer
- Filtres de recherche (nom, SKU, catégorie)
- Indicateurs visuels (mappé/non mappé)

## 🔄 Workflow d'Import avec Mapping

### Scénario 1: Premier Import (sans mapping)

1. **Récupérer produits depuis Gazelle API**
   ```python
   gazelle_products = api_client.get_products()
   ```

2. **Pour chaque produit Gazelle:**
   - Vérifier si `gazelle_product_id` existe dans `produits_mapping`
   - Si **OUI**: Utiliser le `code_produit` mappé → **UPDATE** produit existant
   - Si **NON**: Créer nouveau produit → Proposer mapping dans l'interface

3. **Après import:**
   - Afficher les produits non mappés dans l'interface
   - Permettre à l'utilisateur de créer les mappings

### Scénario 2: Import Futur (avec mapping existant)

1. **Récupérer produits depuis Gazelle API**
2. **Pour chaque produit:**
   - Chercher dans `produits_mapping` par `gazelle_product_id`
   - Si mapping trouvé:
     - Utiliser `code_produit` mappé
     - **UPDATE** le produit Supabase (prix, nom, etc.)
     - Mettre à jour `sync_status = 'synced'`, `last_synced_at = NOW()`
   - Si pas de mapping:
     - Créer nouveau produit
     - Proposer mapping dans l'interface

### Scénario 3: Nouveau Produit dans Gazelle

1. Détecter nouveau produit (pas dans mapping)
2. Créer produit dans Supabase
3. Proposer mapping automatique ou manuel

## 🎨 Interface Utilisateur

### Vue Principale: Mapping Manager

```
┌─────────────────────────────────────────────────────────────┐
│  📦 Gestionnaire de Mapping Produits                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Onglets: Non mappés | Tous les mappings | Historique]    │
│                                                              │
│  ┌──────────────────────┐  ↔  ┌──────────────────────┐    │
│  │ Produits Gazelle     │     │ Produits Supabase    │    │
│  │ (Non mappés)         │     │ (Sans mapping)       │    │
│  ├──────────────────────┤     ├──────────────────────┤    │
│  │ 🔍 Recherche...      │     │ 🔍 Recherche...      │    │
│  ├──────────────────────┤     ├──────────────────────┤    │
│  │ ✅ Piano Steinway    │     │ ✅ PROD-123          │    │
│  │    SKU: PIANO-001    │  →  │    Piano Steinway    │    │
│  │    Prix: $5000       │     │    Cat: Instruments   │    │
│  ├──────────────────────┤     ├──────────────────────┤    │
│  │ ⚠️  Corde #1         │     │ ⚠️  PROD-456         │    │
│  │    SKU: CORD-001     │     │    Corde #1          │    │
│  └──────────────────────┘     └──────────────────────┘    │
│                                                              │
│  [Créer Mapping] [Annuler]                                   │
└─────────────────────────────────────────────────────────────┘
```

### Fonctionnalités UI

1. **Recherche/Filtres:**
   - Par nom, SKU, catégorie
   - Afficher seulement non mappés
   - Tri par nom, date, etc.

2. **Création de Mapping:**
   - Sélection multiple (checkbox)
   - Drag & drop visuel
   - Mapping automatique par SKU similaire (suggestion)

3. **Gestion des Mappings:**
   - Liste des mappings avec statut (synced/pending/error)
   - Modifier mapping (changer code_produit)
   - Supprimer mapping
   - Forcer re-sync

## 📝 Étapes d'Implémentation

### ✅ Phase 1: Backend (FAIT)

- [x] Migration SQL `003_create_product_mapping.sql`
- [x] Méthode `get_products()` dans `GazelleAPIClient`
- [x] Endpoints API dans `api/product_mapping.py`
- [x] Router enregistré dans `api/main.py`

### 🔄 Phase 2: Script d'Import Modifié (À FAIRE)

Modifier `scripts/import_gazelle_product_display.py` pour:
1. Utiliser `produits_mapping` lors de l'import
2. Créer automatiquement les mappings pour nouveaux produits
3. Mettre à jour `sync_status` après import réussi

### 🎨 Phase 3: Interface React (À FAIRE)

Créer `frontend/src/components/ProductMappingInterface.jsx`:
1. Composant de liste (produits Gazelle vs Supabase)
2. Système de sélection/mapping
3. Gestion des mappings existants
4. Intégration dans `InventaireDashboard.jsx`

## 🚀 Utilisation

### 1. Exécuter la Migration

```sql
-- Dans Supabase SQL Editor
-- Copier le contenu de: modules/inventaire/migrations/003_create_product_mapping.sql
```

### 2. Tester l'API

```bash
# Lister produits Gazelle
curl http://localhost:8000/inventaire/mapping/gazelle-products

# Lister produits non mappés
curl http://localhost:8000/inventaire/mapping/unmapped-gazelle
curl http://localhost:8000/inventaire/mapping/unmapped-supabase

# Créer un mapping
curl -X POST http://localhost:8000/inventaire/mapping/mappings \
  -H "Content-Type: application/json" \
  -d '{
    "gazelle_product_id": "prod_123",
    "code_produit": "PROD-456",
    "mapped_by": "Allan"
  }'
```

### 3. Interface (à venir)

Accéder à: `/inventaire/mapping` dans l'interface React

## 🔍 Cas d'Usage

### Cas 1: Premier Import
1. Importer produits depuis Gazelle → Créer dans Supabase
2. Ouvrir interface mapping
3. Mapper manuellement ou automatiquement (par SKU)
4. Sauvegarder mappings

### Cas 2: Import Futur (Prix changé)
1. Importer produits depuis Gazelle
2. Système trouve mapping existant
3. Met à jour automatiquement le produit Supabase (prix, nom, etc.)
4. Pas besoin de re-mapper

### Cas 3: Nouveau Produit Gazelle
1. Détecte nouveau produit (pas dans mapping)
2. Créer dans Supabase
3. Propose mapping dans interface
4. Utilisateur confirme ou modifie

## 📊 Métriques

- Nombre de produits mappés vs non mappés
- Taux de synchronisation réussie
- Erreurs de mapping (produits supprimés, etc.)

## 🔐 Sécurité

- Vérifier que `code_produit` existe avant de créer mapping
- Vérifier que `gazelle_product_id` est valide
- Logs des opérations de mapping (qui/quand)
