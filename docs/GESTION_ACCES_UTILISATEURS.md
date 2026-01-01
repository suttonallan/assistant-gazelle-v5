# GESTION DES ACCÈS UTILISATEURS - ASSISTANT GAZELLE V5

## 📋 Vue d'Ensemble

Le système V5 utilise une **architecture à deux niveaux** pour gérer les accès:

1. **Frontend (React)**: Contrôle l'affichage des dashboards et onglets
2. **Backend (FastAPI)**: Pas de contrôle d'accès (pour l'instant)

## 🎯 Principe de Fonctionnement

### Architecture Actuelle

```
Utilisateur (email)
    ↓
Frontend: roles.js → Détecte le rôle
    ↓
Frontend: Dashboard component → Affiche les onglets autorisés
    ↓
Backend: API endpoints → OUVERT À TOUS (pas de vérification)
```

**Note importante**: Le backend ne vérifie PAS les permissions. Le contrôle se fait uniquement côté frontend (donc contournable si quelqu'un modifie le code client).

## 📂 Fichiers Clés

### 1. Configuration des Rôles (Frontend)

**Fichier**: `/frontend/src/config/roles.js`

**Responsabilité**: Définit qui a accès à quoi

**Structure**:
```javascript
export const ROLES = {
  admin: {
    name: 'Administrateur',
    email: 'asutton@piano-tek.com',
    permissions: ['*'],  // Tout
    dashboards: ['inventaire', 'commissions', 'stats', 'admin', 'sync_gazelle', 'tournees'],
    technicianName: 'allan'
  },

  nick: {
    name: 'Nick (Gestionnaire)',
    email: 'nlessard@piano-tek.com',
    permissions: [
      'view_inventory',
      'manage_own_inventory',
      'create_tours',
      'view_tours',
      'use_assistant'
    ],
    dashboards: ['inventaire', 'tournees', 'vincent-dindy']
  },

  louise: {
    name: 'Louise (Assistante)',
    email: 'info@piano-tek.com',
    permissions: [
      'view_inventory',
      'edit_inventory',
      'view_tours',
      'use_assistant'
    ],
    dashboards: ['inventaire', 'tournees']
  },

  jeanphilippe: {
    name: 'Jean-Philippe (Technicien)',
    email: 'jpreny@gmail.com',
    permissions: [
      'view_inventory',
      'edit_inventory',
      'view_tours',
      'use_assistant'
    ],
    dashboards: ['inventaire', 'tournees']
  }
}
```

**Fonctions utilitaires**:
- `getUserRole(email)`: Retourne le nom du rôle basé sur l'email
- `hasPermission(email, permission)`: Vérifie si un utilisateur a une permission
- `getAvailableDashboards(email)`: Retourne la liste des dashboards accessibles

### 2. Composants Dashboard Spécifiques

Chaque utilisateur a son propre composant dashboard avec des **onglets spécifiques**:

#### a) **AdminDashboard.jsx**
**Chemin**: `/frontend/src/components/dashboards/AdminDashboard.jsx`

**Onglets**: Tous (accès complet)

#### b) **NickDashboard.jsx**
**Chemin**: `/frontend/src/components/dashboards/NickDashboard.jsx`

**Onglets**:
- 📦 Inventaire techniciens
- 🎹 Tournées d'accords
- 🎵 Vincent d'Indy
- 💰 Calculateur

**Code des onglets** (lignes 168-210):
```javascript
<nav className="flex gap-4">
  <button
    onClick={() => setActiveTab('inventaire')}
    className={/* styles */}
  >
    📦 Inventaire techniciens
  </button>
  <button
    onClick={() => setActiveTab('tournees')}
    className={/* styles */}
  >
    🎹 Tournées d'accords
  </button>
  <button
    onClick={() => setActiveTab('vincent-dindy')}
    className={/* styles */}
  >
    🎵 Vincent d'Indy
  </button>
  <button
    onClick={() => setActiveTab('calculateur')}
    className={/* styles */}
  >
    💰 Calculateur
  </button>
</nav>

{/* Contenu selon onglet */}
{activeTab === 'inventaire' && (
  <TechniciensInventaireTable currentUser={currentUser} allowComment={true} />
)}

{activeTab === 'vincent-dindy' && (
  <VincentDIndyDashboard currentUser={currentUser} />
)}

{activeTab === 'tournees' && (
  <div>{/* Formulaire tournées */}</div>
)}

{activeTab === 'calculateur' && (
  <div>{/* Calculateurs */}</div>
)}
```

#### c) **LouiseDashboard.jsx**
**Chemin**: `/frontend/src/components/dashboards/LouiseDashboard.jsx`

**Onglets**:
- 📦 Inventaire techniciens
- 🎹 Tournées d'accords

#### d) **JeanPhilippeDashboard.jsx**
**Chemin**: `/frontend/src/components/dashboards/JeanPhilippeDashboard.jsx`

**Onglets**:
- 📦 Inventaire techniciens
- 🎹 Tournées d'accords

### 3. Point d'Entrée (App.jsx)

**Fichier**: `/frontend/src/App.jsx`

**Responsabilité**: Router vers le bon dashboard selon l'utilisateur

**Code** (lignes ~80-120):
```javascript
const renderDashboard = () => {
  const role = getUserRole(effectiveUser)

  switch (role) {
    case 'admin':
      return <AdminDashboard currentUser={effectiveUser} />

    case 'nick':
      return <NickDashboard currentUser={effectiveUser} />

    case 'louise':
      return <LouiseDashboard currentUser={effectiveUser} />

    case 'jeanphilippe':
      return <JeanPhilippeDashboard currentUser={effectiveUser} />

    default:
      return <AdminDashboard currentUser={effectiveUser} />
  }
}
```

## 🔧 Comment Ajouter un Nouvel Accès

### Exemple: Donner accès à Vincent d'Indy à Nick

#### Étape 1: Ajouter le dashboard dans roles.js

```javascript
nick: {
  name: 'Nick (Gestionnaire)',
  email: 'nlessard@piano-tek.com',
  permissions: [...],
  dashboards: ['inventaire', 'tournees', 'vincent-dindy']  // ✅ Ajouté
}
```

#### Étape 2: Ajouter l'onglet dans le composant Dashboard

**Fichier**: `/frontend/src/components/dashboards/NickDashboard.jsx`

**Ajouter le bouton d'onglet** (après tournees):
```javascript
<button
  onClick={() => setActiveTab('vincent-dindy')}
  className={`px-4 py-2 border-b-2 font-medium ${
    activeTab === 'vincent-dindy'
      ? 'border-blue-600 text-blue-600'
      : 'border-transparent text-gray-600 hover:text-gray-900'
  }`}
>
  🎵 Vincent d'Indy
</button>
```

**Ajouter le contenu de l'onglet** (après inventaire):
```javascript
{activeTab === 'vincent-dindy' && (
  <VincentDIndyDashboard currentUser={currentUser} />
)}
```

#### Étape 3: S'assurer que le composant est importé

```javascript
import VincentDIndyDashboard from '../VincentDIndyDashboard'
```

#### Étape 4: Rafraîchir le navigateur

L'utilisateur doit rafraîchir (F5) pour voir les changements.

## 📍 Modules Disponibles

### Liste des Dashboards/Modules Actuels

| Module | Chemin Composant | Description |
|--------|------------------|-------------|
| **inventaire** | `/components/TechniciensInventaireTable.jsx` | Gestion inventaire des techniciens |
| **tournees** | `/components/dashboards/*Dashboard.jsx` | Création/gestion tournées d'accords |
| **vincent-dindy** | `/components/VincentDIndyDashboard.jsx` | Gestion pianos Vincent d'Indy |
| **place-des-arts** | `/components/PlaceDesArtsDashboard.jsx` | Demandes Place des Arts |
| **commissions** | `/components/CommissionsDashboard.jsx` | Calcul commissions |
| **stats** | `/components/StatsDashboard.jsx` | Statistiques générales |
| **admin** | `/components/AdminPanel.jsx` | Panel administration |
| **sync_gazelle** | `/components/SyncGazelleDashboard.jsx` | Synchronisation Gazelle |
| **alertes-rv** | `/components/AlertesRV.jsx` | Alertes rendez-vous |

### Endpoints Backend Correspondants

| Module Frontend | Endpoint Backend | Fichier API |
|----------------|------------------|-------------|
| inventaire | `/inventaire/*` | `api/inventaire.py` |
| tournees | `/tournees/*` | `api/tournees.py` |
| vincent-dindy | `/vincent-dindy/*` | `api/vincent_dindy.py` |
| place-des-arts | `/place-des-arts/*` | `api/place_des_arts.py` |
| chat | `/api/chat/*` | `api/chat/` |
| admin | `/admin/*` | `api/admin.py` |

## 🔐 Permissions Disponibles

### Liste des Permissions Actuelles

| Permission | Description | Utilisé Par |
|-----------|-------------|-------------|
| `*` | Accès complet à tout | Admin |
| `view_inventory` | Voir l'inventaire | Nick, Louise, JP |
| `edit_inventory` | Modifier l'inventaire | Louise, JP |
| `manage_own_inventory` | Gérer son propre inventaire | Nick |
| `create_tours` | Créer des tournées | Nick |
| `view_tours` | Voir les tournées | Tous sauf Admin |
| `use_assistant` | Utiliser le chat assistant | Nick, Louise, JP |

**Note**: Ces permissions sont définies mais **PAS ENCORE UTILISÉES** dans le code pour contrôler l'accès. Elles servent seulement de documentation pour l'instant.

## 🚨 Limitations Actuelles

### 1. Pas de Contrôle Backend

**Problème**: Les endpoints API sont ouverts à tous sans vérification.

**Exemple**:
```javascript
// Frontend: Nick n'a pas accès admin
// Mais il pourrait faire:
fetch('/admin/sync-gazelle', { method: 'POST' })
// ✅ Ça fonctionnerait car le backend ne vérifie pas!
```

**Solution future**: Ajouter un middleware FastAPI pour vérifier les permissions.

### 2. Contrôle Basé sur Email

**Problème**: L'authentification se base uniquement sur l'email (pas de mot de passe).

**Risque**: Quelqu'un pourrait se connecter avec l'email d'une autre personne.

**Solution future**: Implémenter OAuth Google ou un système d'auth complet.

### 3. Permissions Non Utilisées

**Problème**: Les permissions dans `roles.js` sont documentées mais pas vérifiées dans le code.

**Exemple**: `hasPermission()` existe mais n'est jamais appelé.

**Solution future**: Utiliser `hasPermission()` avant d'afficher certains boutons sensibles.

## 📝 Bonnes Pratiques

### 1. Ajouter un Nouveau Module

1. **Créer le composant** dans `/frontend/src/components/`
2. **Ajouter le module** dans `roles.js` pour chaque utilisateur qui doit y accéder
3. **Ajouter l'onglet** dans le Dashboard component correspondant
4. **Créer l'endpoint API** dans `/api/`
5. **Tester avec plusieurs utilisateurs**

### 2. Modifier les Accès Existants

1. **Modifier `roles.js`**: Ajouter/retirer le dashboard de la liste
2. **Modifier le Dashboard component**: Ajouter/retirer l'onglet
3. **Rafraîchir le navigateur** pour voir les changements

### 3. Debug des Problèmes d'Accès

**Checklist**:
- [ ] L'email utilisateur correspond-il exactement à celui dans `roles.js`?
- [ ] Le dashboard est-il dans la liste `dashboards` du rôle?
- [ ] L'onglet est-il bien ajouté dans le composant Dashboard?
- [ ] Le composant est-il bien importé?
- [ ] Le navigateur a-t-il été rafraîchi (F5)?

**Debug dans la console**:
```javascript
// Vérifier le rôle détecté
import { getUserRole, getAvailableDashboards } from './config/roles'
console.log(getUserRole('nlessard@piano-tek.com'))
// Devrait afficher: "nick"

console.log(getAvailableDashboards('nlessard@piano-tek.com'))
// Devrait afficher: ["inventaire", "tournees", "vincent-dindy"]
```

## 🔮 Améliorations Futures

### 1. Backend Authorization Middleware

```python
# api/core/auth.py (à créer)
from fastapi import HTTPException, Header

def verify_permission(required_permission: str):
    async def permission_checker(user_email: str = Header(alias="X-User-Email")):
        user_role = get_user_role(user_email)
        if not has_permission(user_role, required_permission):
            raise HTTPException(status_code=403, detail="Permission denied")
        return user_email
    return permission_checker

# Utilisation dans un endpoint
@router.post("/admin/sync")
async def sync_gazelle(
    user: str = Depends(verify_permission("admin"))
):
    # Code de sync
```

### 2. Authentification OAuth Google

Remplacer le système d'email par une vraie authentification:
- Google OAuth pour Piano-Tek (@piano-tek.com)
- Session tokens côté serveur
- Refresh tokens pour mobile

### 3. Permissions Granulaires

Au lieu de dashboards entiers, permettre:
- `vincent-dindy:read`: Voir Vincent d'Indy
- `vincent-dindy:write`: Modifier les pianos
- `vincent-dindy:admin`: Gérer les utilisateurs

### 4. Interface de Gestion

Créer un panel admin pour:
- Ajouter/retirer des utilisateurs
- Modifier les permissions
- Voir l'historique d'accès

## 📚 Référence Complète

### Mapping Utilisateur → Dashboard

| Utilisateur | Email | Dashboard Component | Onglets |
|-------------|-------|---------------------|---------|
| Allan (Admin) | asutton@piano-tek.com | AdminDashboard | Tous les modules |
| Nick | nlessard@piano-tek.com | NickDashboard | Inventaire, Tournées, Vincent d'Indy, Calculateur |
| Louise | info@piano-tek.com | LouiseDashboard | Inventaire, Tournées |
| Jean-Philippe | jpreny@gmail.com | JeanPhilippeDashboard | Inventaire, Tournées |

### Mapping ID Technicien Gazelle

Pour référence (lié aux permissions):

| Nom | Email | ID Gazelle | Utilisation |
|-----|-------|------------|-------------|
| Allan | asutton@piano-tek.com | `usr_ofYggsCDt2JAVeNP` | Chat assistant, assignations |
| Nicolas (Nick) | nlessard@piano-tek.com | `usr_HcCiFk7o0vZ9xAI0` | Chat assistant, assignations |
| Jean-Philippe | jpreny@gmail.com | (voir users table) | Chat assistant |

**Note**: Les IDs Gazelle sont différents des rôles frontend. Voir [MIGRATION_TECHNICIENS_IDS.md](./MIGRATION_TECHNICIENS_IDS.md) pour plus de détails.

## 🎯 Résumé TL;DR

**Pour donner accès à un module:**

1. **`roles.js`**: Ajouter le module dans `dashboards: []`
2. **`Dashboard.jsx`**: Ajouter l'onglet + le contenu
3. **Rafraîchir**: F5 dans le navigateur

**Fichiers à modifier**:
- `/frontend/src/config/roles.js` (configuration)
- `/frontend/src/components/dashboards/[User]Dashboard.jsx` (UI)

**Backend**: Pas de modification nécessaire (endpoints ouverts à tous).

---

**Date de création**: 2025-12-29
**Dernière mise à jour**: 2025-12-29
**Auteur**: Claude Sonnet 4.5 + Allan Sutton
