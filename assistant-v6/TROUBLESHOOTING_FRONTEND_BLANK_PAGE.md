# Troubleshooting: Frontend Blank Page

## Date: 2025-12-29

## Symptôme
- URL: http://localhost:5173/
- Affichage: Page blanche
- Backend: Opérationnel (✅ 200 OK sur `/api/chat/health`)
- Frontend: Vite running sur port 5173

## Diagnostics Effectués

### 1. Serveurs
```
✅ Backend (uvicorn): Port 8000 - Opérationnel
✅ Frontend (vite): Port 5173 - Opérationnel
✅ API Health Check: 200 OK
```

### 2. Dépendances Frontend
```json
{
  "@emotion/react": "^11.14.0",
  "@emotion/styled": "^11.14.1",
  "@mui/icons-material": "^7.3.6",
  "@mui/material": "^7.3.6",
  "axios": "^1.13.2",
  "react": "^18.2.0",
  "react-dom": "^18.2.0"
}
```

✅ Toutes les dépendances requises installées

### 3. Composant ChatIntelligent.jsx
- ✅ Imports corrects (axios, @mui/material, @mui/icons-material)
- ✅ Structure complète (Cards + Drawer)
- ✅ useEffect() auto-load au mount
- ✅ Intégré dans App.jsx

## Causes Possibles

### A. Erreurs JavaScript Runtime
**Probabilité: Élevée**

Page blanche = généralement erreur JS non gérée

Vérifier:
1. Console navigateur pour erreurs
2. Network tab pour requêtes API bloquées
3. React DevTools pour erreurs de composants

### B. CORS / API Configuration
**Probabilité: Moyenne**

Si l'API ne répond pas depuis le frontend:
```javascript
// ChatIntelligent.jsx:33
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

Vérifier:
- Variable d'environnement `REACT_APP_API_URL`
- CORS activé dans FastAPI backend
- Requête OPTIONS préflight

### C. Route React Router
**Probabilité: Faible**

L'intégration dans App.jsx:
```javascript
} else if (currentView === 'chat') {
  return <ChatIntelligent />
```

Pas de React Router utilisé, donc peu probable.

## Actions de Diagnostic à Effectuer

### 1. Console Navigateur
```
Ouvrir: http://localhost:5173/
F12 → Console
Chercher: Erreurs rouges
```

### 2. Network Tab
```
F12 → Network
Rafraîchir page
Vérifier:
- Requête GET http://localhost:8000/api/chat/query (POST "aujourd'hui")
- Status codes (200 vs 500 vs CORS error)
```

### 3. Vite Logs Détaillés
```bash
cd frontend
# Regarder les logs en temps réel pour erreurs de compilation
```

### 4. Test Composant Isolé
Créer un test minimal dans App.jsx:
```javascript
return <div>Test React fonctionne</div>
```

Si ça s'affiche → erreur dans ChatIntelligent
Si ça ne s'affiche pas → problème de base React/Vite

## Solutions Possibles

### Solution 1: CORS Backend
Ajouter dans `api/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Solution 2: Variable d'environnement
Créer `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000
```

### Solution 3: Rebuild Frontend
```bash
cd frontend
rm -rf node_modules/.vite
npm run dev
```

Force Vite à reconstruire le cache des dépendances.

### Solution 4: Gestion d'Erreur dans ChatIntelligent
Ajouter Error Boundary React:
```javascript
class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    console.error('ChatIntelligent Error:', error, errorInfo);
  }

  render() {
    if (this.state?.hasError) {
      return <div>Erreur chargement chat</div>;
    }
    return this.props.children;
  }
}

// Dans App.jsx:
<ErrorBoundary>
  <ChatIntelligent />
</ErrorBoundary>
```

## Prochaines Étapes

1. **IMMÉDIAT**: Vérifier console navigateur
2. **SI CORS**: Ajouter middleware CORS
3. **SI API**: Vérifier network tab
4. **SI REACT**: Ajouter Error Boundary

## Notes pour V6

### Learnings Architecture:
1. **Toujours ajouter Error Boundary** dès le début
2. **Configurer CORS** explicitement dans FastAPI
3. **Logging frontend** pour debugging
4. **Health checks frontend** (pas juste backend)

### Améliorations V6:
```typescript
// v6/frontend/src/components/ChatIntelligent.tsx
export default function ChatIntelligent() {
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Health check API au mount
    axios.get(`${API_BASE}/api/chat/health`)
      .then(() => console.log('✅ API accessible'))
      .catch(err => {
        console.error('❌ API inaccessible:', err);
        setError(err);
      });
  }, []);

  if (error) {
    return (
      <Alert severity="error">
        Impossible de contacter l'API. Vérifier que le backend est démarré.
      </Alert>
    );
  }

  // ... reste du composant
}
```

### Tests à Automatiser V6:
1. **E2E Playwright**: Vérifier page ne reste pas blanche
2. **API Contract Tests**: Frontend/Backend en sync
3. **CORS Tests**: Vérifier preflight OPTIONS

## Résultats d'Investigation

### ✅ Vérifications Complétées:

1. **Backend (FastAPI)**
   - ✅ Serveur uvicorn en cours d'exécution (port 8000)
   - ✅ CORS configuré correctement (allow_origins=["*"])
   - ✅ Endpoint `/api/chat/health` répond 200 OK
   - ✅ Endpoint `/api/chat/query` retourne des données valides

2. **Frontend (Vite + React)**
   - ✅ Serveur Vite en cours d'exécution (port 5173)
   - ✅ Dépendances installées correctement:
     - react@18.3.1
     - react-dom@18.3.1
     - @mui/material@7.3.6
     - @mui/icons-material@7.3.6
     - axios@1.13.2
   - ✅ Structure fichiers correcte:
     - index.html avec `<div id="root">`
     - src/main.jsx avec ReactDOM.createRoot
     - src/App.jsx avec composants
     - src/config/roles.js présent

3. **Composant ChatIntelligent**
   - ✅ Imports corrects (axios, MUI)
   - ✅ Structure complète (Cards + Drawer)
   - ✅ Intégré dans App.jsx (route 'chat')
   - ✅ Accessible aux rôles admin et louise

### 🔍 Diagnostic Final

La "page blanche" est probablement **NORMALE** et s'explique par le flux d'authentification:

1. **Au premier chargement** → LoginScreen s'affiche
2. **Après connexion** → currentView='dashboard' (par défaut)
3. **Pour voir le Chat** → Cliquer sur bouton "💬 Ma Journée"

### 📋 Instructions pour l'Utilisateur

#### Étape 1: Accéder au Site
```
URL: http://localhost:5173/
```

#### Étape 2: Se Connecter
Utiliser les identifiants de test:
- **Allan**: PIN 6342 (admin - accès complet)
- **Louise**: PIN 6343 (assistante - peut voir Chat)
- **Nick**: PIN 6344 (technicien)
- **JP**: PIN 6345 (technicien)

#### Étape 3: Naviguer vers Chat
Après connexion, chercher le bouton dans le header:
```
💬 Ma Journée
```

Ce bouton est visible uniquement pour **admin** et **louise**.

### 🛠️ Si Vraiment Rien Ne S'Affiche

**Test 1: Vérifier Console Navigateur**
```
1. Ouvrir http://localhost:5173/
2. Appuyer F12 (DevTools)
3. Onglet "Console"
4. Chercher erreurs en rouge
```

**Test 2: Vérifier Network**
```
F12 → Network
Rafraîchir page
Vérifier:
- main.jsx chargé? (200 OK)
- index.css chargé? (200 OK)
- Erreurs 404?
```

**Test 3: Hard Refresh**
```
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

**Test 4: Rebuild Frontend**
```bash
cd frontend
rm -rf node_modules/.vite
rm -rf dist
npm run dev
```

### 🎯 Test Rapide API depuis Frontend

Une fois connecté, ouvrir Console et tester:
```javascript
fetch('http://localhost:8000/api/chat/health')
  .then(r => r.json())
  .then(console.log)
// Devrait afficher: {status: "healthy", service: "chat_intelligent", data_source: "v5"}
```

## Status
✅ **PROBLÈME RÉSOLU**

### 🎯 Cause Racine Identifiée

**Erreur:** `Uncaught ReferenceError: process is not defined`
**Location:** `ChatIntelligent.jsx:33`

**Problème:**
```javascript
// ❌ INCORRECT (syntaxe Create React App)
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

Vite n'utilise PAS `process.env`. Il utilise `import.meta.env`.

**Solution Appliquée:**
```javascript
// ✅ CORRECT (syntaxe Vite)
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

### 📝 Learning pour V6

**Différences Vite vs Create React App:**

| Feature | Create React App | Vite |
|---------|------------------|------|
| Variables env | `process.env.REACT_APP_*` | `import.meta.env.VITE_*` |
| Fichier env | `.env` | `.env` |
| Prefix obligatoire | `REACT_APP_` | `VITE_` |
| Disponibilité | Runtime | Build-time |

**Fichier .env (Vite):**
```bash
# ✅ Correct pour Vite
VITE_API_URL=http://localhost:8000

# ❌ Incorrect (sera ignoré)
REACT_APP_API_URL=http://localhost:8000
```

### 🔧 Variables d'Environnement Vite Standard

```javascript
// Variables toujours disponibles:
import.meta.env.MODE        // 'development' ou 'production'
import.meta.env.BASE_URL    // '/' par défaut
import.meta.env.PROD        // boolean: true si production
import.meta.env.DEV         // boolean: true si développement
import.meta.env.SSR         // boolean: true si server-side

// Variables custom (prefix VITE_ obligatoire):
import.meta.env.VITE_API_URL
import.meta.env.VITE_SUPABASE_URL
import.meta.env.VITE_FEATURE_FLAG_X
```

### ✅ Résolution Complète

Après correction, la page charge maintenant correctement avec:
1. ✅ LoginScreen s'affiche
2. ✅ Connexion fonctionnelle
3. ✅ Navigation vers Chat Intelligent opérationnelle

Dernière mise à jour: 2025-12-29 15:10 EST
