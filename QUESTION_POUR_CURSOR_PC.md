# Question pour Cursor PC - Interface Admin Inventaire V4

**Date:** 2025-12-09
**Contexte:** Migration V4 → V5 - Module Inventaire

---

## Question

Dans Gazelle V4, comment fonctionnait l'interface d'administration de l'inventaire?

Nous avons besoin de comprendre:

### 1. Interface Utilisateur V4

**Où se trouvait l'admin inventaire?**
- URL d'accès (ex: `/admin/inventory`)?
- Était-ce dans l'application Flask?
- Était-ce dans l'interface Gazelle Desktop?
- Était-ce une page web séparée?

### 2. Fonctionnalités Disponibles

**Que pouvait-on faire dans l'admin inventaire V4?**

Nous supposons:
- ✅ Voir le catalogue de produits
- ✅ Modifier les produits (nom, prix, catégorie)
- ✅ Configurer les commissions (`HasCommission`, `CommissionRate`)
- ✅ Gérer les variantes (`VariantGroup`, `VariantLabel`)
- ✅ Voir les stocks par technicien
- ✅ Ajuster les quantités en stock
- ✅ Voir les alertes de stock bas
- ❓ Export de données?
- ❓ Historique des transactions?

**Quelle était la fonctionnalité la plus utilisée?**

### 3. Fichiers Source V4

**Peux-tu nous indiquer:**

1. **Templates HTML** (si Flask):
   - Chemin vers les fichiers `.html` de l'admin inventaire
   - Ex: `templates/admin/inventory.html`?

2. **Routes Backend** (Flask):
   - Fichiers contenant les routes admin
   - Ex: `app/admin_routes.py` ou `app/inventory_admin.py`?

3. **JavaScript Frontend**:
   - Fichiers JS pour l'interface admin
   - Ex: `static/js/inventory_admin.js`?

4. **Configuration**:
   - Y avait-il des permissions/rôles pour l'admin?
   - Seulement Allan avait accès ou tous les techs?

### 4. Workflow Typique

**Exemple de cas d'usage V4:**

Comment configurait-on une commission pour un produit?

1. Aller sur quelle page?
2. Cliquer sur quoi?
3. Remplir quels champs?
4. Sauvegarder comment?

---

## Objectif pour V5

Nous voulons recréer une interface admin similaire dans V5 (React) qui permette:

### Interface Admin V5 (à créer)

```
URL: /inventaire (avec onglet "Admin" visible seulement pour role=admin)

┌─────────────────────────────────────────────────────────┐
│ Inventaire - Mode Admin                                │
├─────────────────────────────────────────────────────────┤
│ [Catalogue] [Stock] [Transactions] [⚙️ Admin]          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ 📦 Catalogue de Produits (Mode Admin)                  │
│                                                         │
│ [+ Nouveau Produit]                                     │
│                                                         │
│ ┌───────────────────────────────────────────────────┐  │
│ │ Code   │ Nom           │ Prix    │ Commission │ ⚙️│  │
│ ├───────────────────────────────────────────────────┤  │
│ │ CORD-1 │ Corde Do#3    │ $12.50  │ 15.0% ✓   │ ✏️│  │
│ │ FELT-1 │ Feutre marteau│ $8.75   │ -         │ ✏️│  │
│ └───────────────────────────────────────────────────┘  │
│                                                         │
│ Clic sur ✏️ → Modal:                                   │
│ ┌─────────────────────────────┐                        │
│ │ Modifier CORD-1             │                        │
│ │ Nom: [Corde Do#3         ]  │                        │
│ │ Prix: [$12.50            ]  │                        │
│ │ ☑️ Activer commission        │                        │
│ │ Taux: [15.0] %              │                        │
│ │ [Annuler] [Sauvegarder]     │                        │
│ └─────────────────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

### Endpoints API Nécessaires

```python
# Déjà existants
GET  /inventaire/catalogue         # Lire catalogue
POST /inventaire/catalogue         # Créer produit
GET  /inventaire/stock/{tech}      # Lire stock

# À créer?
PUT   /inventaire/catalogue/{code}  # Modifier produit
DELETE /inventaire/catalogue/{code} # Supprimer produit
PATCH /inventaire/catalogue/{code}/commission  # Config commission
```

---

## Réponses Attendues

Cursor PC, peux-tu:

1. **Décrire l'interface admin V4** (captures d'écran si possible)
2. **Lister les fichiers source** (HTML, Python, JS)
3. **Expliquer le workflow** de configuration d'une commission
4. **Identifier les fonctionnalités critiques** à reproduire en V5

Merci! Ces informations nous permettront de créer une interface admin V5 fidèle à V4.

---

**Contexte Technique:**
- V4: Flask + SQLite/SQL Server + Templates HTML
- V5: FastAPI + Supabase (PostgreSQL) + React (Vite)
- Migration déjà complétée: Pianos, Alertes RV, Inventaire (lecture seule)
- En cours: Admin Inventaire avec configuration commissions
