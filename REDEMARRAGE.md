# Guide de Redémarrage - Assistant Gazelle

## État Actuel du Projet

### Bug en Cours
**Problème:** Quand on clique sur "test4" (tournée), on voit les pianos de "test3" affichés en jaune.

### Fichiers Modifiés (Non Committés)

```
M .DS_Store
M .cursorrules
M api/assistant.py
M api/chat/schemas.py
M api/chat/service.py
M api/main.py
M api/place_des_arts.py
M core/gazelle_api_client.py
M frontend/package-lock.json
M frontend/package.json
M frontend/src/App.jsx
M frontend/src/components/AssistantWidget.jsx
M frontend/src/components/ChatIntelligent.jsx
M frontend/src/components/ClickableMessage.jsx
M frontend/src/components/ClientDetailsModal.jsx
M frontend/src/components/VincentDIndyDashboard.jsx  ⚠️ IMPORTANT
M frontend/src/components/dashboards/NickDashboard.jsx
M frontend/src/config/roles.js
M modules/assistant/services/parser.py
M modules/assistant/services/queries.py
M modules/reports/service_reports.py
M modules/sync_gazelle/sync_to_supabase.py
M modules/travel_fees/calculator.py
M requirements.txt
```

### Fichiers Nouveaux Créés

```
frontend/debug_tournees.html           ⚠️ OUTIL DE DEBUG
REFONTE_TOURNEES_ARCHITECTURE.md       ⚠️ DOCUMENT POUR GEMINI
REDEMARRAGE.md                         ⚠️ CE FICHIER
```

---

## Après Redémarrage - Checklist

### 1. Relancer les Services

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Terminal 1: Backend API
source venv/bin/activate  # ou source .venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend React
cd frontend
npm run dev
```

**URLs à vérifier:**
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs

### 2. Vérifier que les Tournées Sont Toujours Là

Ouvrir dans le navigateur:
```
file:///Users/allansutton/Documents/assistant-gazelle-v5/frontend/debug_tournees.html
```

**Ce que vous devriez voir:**
- Tournée "test3" avec ses piano_ids
- Tournée "test4" avec ses piano_ids
- Les piano_ids doivent être au format `ins_xxxxx`

### 3. Reproduire le Bug

1. Ouvrir http://localhost:5173
2. Aller sur l'onglet "Nicolas"
3. Cliquer sur tournée "test3" → noter quels pianos sont en jaune
4. Cliquer sur tournée "test4" → **BUG:** les pianos de test3 restent en jaune

### 4. Activer le Mode Debug

Ouvrir la console développeur (F12), puis taper:

```javascript
window.DEBUG_TOURNEES = true
```

Ensuite cliquer sur test3, puis test4, et regarder les logs.

---

## Options de Fix

### Option A: Fix Rapide (Recommandé pour Continuer)

Ajouter un `useEffect` qui force le re-render quand `selectedTourneeId` change:

```javascript
// Dans VincentDIndyDashboard.jsx
useEffect(() => {
  if (selectedTourneeId) {
    console.log('🔄 Tournée changée:', selectedTourneeId)
    const tournee = tournees.find(t => t.id === selectedTourneeId)
    console.log('   Piano IDs:', tournee?.piano_ids)

    // Force re-render en vidant et re-remplissant
    setSelectedIds(new Set())
  }
}, [selectedTourneeId, tournees])
```

### Option B: Refonte Complète (Recommandé pour Stabilité)

Lire [REFONTE_TOURNEES_ARCHITECTURE.md](REFONTE_TOURNEES_ARCHITECTURE.md) et suivre le plan de migration.

---

## Backup des Tournées (au cas où)

Si vous voulez sauvegarder les tournées avant de redémarrer:

1. Ouvrir http://localhost:5173
2. F12 → Console
3. Copier le résultat de:

```javascript
JSON.stringify(JSON.parse(localStorage.getItem('tournees_accords')), null, 2)
```

4. Sauvegarder dans un fichier texte

Pour restaurer:

```javascript
localStorage.setItem('tournees_accords', '[COLLER_ICI_LE_JSON]')
```

---

## Variables d'Environnement Nécessaires

Fichier: `/Users/allansutton/Documents/assistant-gazelle-v5/.env`

Doit contenir (minimum):
```
GAZELLE_ACCESS_TOKEN=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
GOOGLE_APPLICATION_CREDENTIALS=/Users/allansutton/Documents/assistant-gazelle-v5/data/credentials_ptm.json
```

---

## Commandes Utiles Post-Redémarrage

### Vérifier l'état Git
```bash
git status
git diff frontend/src/components/VincentDIndyDashboard.jsx
```

### Tester l'API Backend
```bash
curl http://localhost:8000/vincent-dindy/pianos | jq '.count'
```

### Nettoyer les node_modules si problème
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Vérifier les logs Backend
```bash
# Dans le terminal où tourne uvicorn
# Les logs s'affichent en temps réel
```

---

## Dernières Modifications Importantes

### VincentDIndyDashboard.jsx (lignes 602-617)

**Changement:** Unifié les couleurs jaunes pour:
- Pianos dans la tournée active
- Pianos avec status "proposed"
- Pianos avec "À faire" rempli

```javascript
const getRowClass = (piano) => {
  if (piano.status === 'top') return 'bg-amber-200'
  if (piano.status === 'completed') return 'bg-green-200'

  // JAUNE si: dans tournée OU proposed OU "à faire" rempli
  if (
    (selectedTourneeId && isPianoInTournee(piano, selectedTourneeId)) ||
    piano.status === 'proposed' ||
    (piano.aFaire && piano.aFaire.trim() !== '')
  ) return 'bg-yellow-200'

  if (selectedIds.has(piano.id)) return 'bg-purple-100'
  return 'bg-white'
}
```

### VincentDIndyDashboard.jsx (lignes 126-144)

**Changement:** Ajout du mode debug avec `window.DEBUG_TOURNEES`

```javascript
const isPianoInTournee = (piano, tourneeId) => {
  const tourneePianoIds = getTourneePianos(tourneeId)
  const pianoGzId = piano.gazelleId || piano.id
  const isIn = tourneePianoIds.includes(pianoGzId)

  if (window.DEBUG_TOURNEES) {
    console.log(`🔍 isPianoInTournee: ${piano.serie}`)
    console.log(`   tourneeId demandée: ${tourneeId}`)
    console.log(`   piano.gazelleId: ${piano.gazelleId}`)
    console.log(`   piano.id: ${piano.id}`)
    console.log(`   pianoGzId utilisé: ${pianoGzId}`)
    console.log(`   tourneePianoIds:`, tourneePianoIds)
    console.log(`   Résultat: ${isIn}`)
  }

  return isIn
}
```

---

## Contact avec Claude

Si vous reprenez la conversation avec Claude Code après le redémarrage:

**Message suggéré:**
```
Je reviens après redémarrage. Le bug "test4 montre les pianos de test3"
n'est toujours pas résolu. J'ai le document REFONTE_TOURNEES_ARCHITECTURE.md
prêt pour Gemini. Que faire maintenant?

Options:
1. Essayer un fix rapide sur VincentDIndyDashboard.jsx
2. Partir sur la refonte avec l'architecture proposée dans le doc
3. D'abord debugger avec window.DEBUG_TOURNEES pour comprendre la cause
```

---

## Notes Importantes

⚠️ **NE PAS COMMITTER** avant d'avoir résolu le bug des tournées
⚠️ **localStorage persiste** après redémarrage (les tournées seront toujours là)
⚠️ **Le backend doit tourner** pour que le frontend fonctionne
⚠️ **Port 8000 et 5173** doivent être libres

---

## Ressources de Debug

1. **debug_tournees.html** - Inspecteur localStorage tournées
2. **migrate_tournees.html** - Migration/nettoyage tournées (si besoin)
3. **reset_tournees.html** - Supprimer toutes les tournées
4. **Console F12** - Logs JavaScript + `window.DEBUG_TOURNEES`
5. **Network tab** - Vérifier les appels API

---

## Si Rien ne Marche

### Reset Complet

```bash
# 1. Arrêter tous les processus
pkill -f uvicorn
pkill -f vite

# 2. Nettoyer le frontend
cd frontend
rm -rf node_modules dist .vite
npm install

# 3. Redémarrer les services
cd ..
source venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000

# Dans un autre terminal:
cd frontend
npm run dev
```

### Supprimer les Tournées et Recommencer

Dans la console du navigateur:
```javascript
localStorage.removeItem('tournees_accords')
location.reload()
```

Puis recréer test3 et test4 manuellement.

---

**Bon redémarrage! 🔄**
