# Refonte Architecture Tournées - Document pour Gemini

## Contexte du Projet

Application de gestion de pianos pour l'établissement Vincent d'Indy (conservatoire de musique). Le système permet de:
- Gérer un inventaire de ~200 pianos
- Planifier des tournées d'accordage (Nicolas, le technicien)
- Suivre le statut de maintenance de chaque piano

**Stack technique actuel:**
- Backend: Python/FastAPI
- Frontend: React (Vite)
- Source de données: API GraphQL Gazelle (système tiers)
- Stockage tournées: localStorage (navigateur)

---

## Le Problème Principal

### Symptôme
Quand l'utilisateur clique sur "test4" (une tournée), il voit les pianos de "test3" (une autre tournée) affichés en jaune comme s'ils appartenaient à test4.

### Historique des Problèmes

#### 1. **Confusion sur l'identifiant unique**
Au début, nous utilisions `serial` (numéro de série) comme ID unique. Problème découvert: **deux pianos différents peuvent avoir le même numéro de série** dans Gazelle.

Exemple:
- Piano 1: serial "2125147", gazelleId "ins_8HOR0byGIBquifag", local "VD431"
- Piano 2: serial "2125147", gazelleId "ins_mffGCA0a8DsFJkTm", local "VD"

**Solution appliquée:** Utiliser UNIQUEMENT `gazelleId` (format `ins_xxxxx`) comme identifiant unique.

#### 2. **Code de compatibilité problématique**
Beaucoup de code essayait de supporter à la fois:
- Anciens IDs (serial numbers)
- Nouveaux IDs (gazelleId)

Cela créait des bugs de matching où le système ne trouvait pas les correspondances.

**Solution appliquée:** Supprimer TOUT le code de compatibilité, n'utiliser QUE gazelleId.

#### 3. **État React vs localStorage non synchronisés**
Le système stocke les tournées dans `localStorage` mais utilise un state React `tournees` pour l'affichage. Parfois:
- `tournees` (state React) n'est pas à jour
- `localStorage` contient les bonnes données mais React ne les reflète pas
- Les clics sur les tournées ne déclenchent pas toujours un re-render

#### 4. **Sémantique confuse des sélections**
Il y avait confusion entre:
- **Checkboxes** (sélection visuelle pour actions batch)
- **Piano dans tournée** (appartenance réelle à la tournée)
- **Piano affiché en couleur** (indicateur visuel d'état)

Initialement, les checkboxes étaient cochées automatiquement pour les pianos dans la tournée, créant de la confusion.

**Solution appliquée:**
- Checkboxes = actions batch uniquement
- Couleur jaune = piano dans tournée OU status "proposed" OU champ "À faire" rempli
- Les checkboxes sont vidées quand on change de tournée

---

## Architecture Actuelle (Problématique)

### Backend: `/api/vincent_dindy.py`

```python
# Retourne toujours gazelleId comme ID
piano = {
    "id": gz_id,              # gazelleId (ex: "ins_xxxxx")
    "gazelleId": gz_id,       # Même chose (redondant)
    "serie": serial,          # Numéro de série (peut être dupliqué!)
    "local": "VD431",
    "piano": "Yamaha",
    # ... autres champs
}
```

**Problème:** Redondance `id` et `gazelleId`, mais nécessaire car le code frontend utilise les deux.

### Frontend: `/frontend/src/components/VincentDIndyDashboard.jsx`

**States React:**
```javascript
const [pianos, setPianos] = useState([])           // Liste complète des pianos
const [tournees, setTournees] = useState([])       // Tournées chargées depuis localStorage
const [selectedTourneeId, setSelectedTourneeId] = useState(null)  // Tournée active
const [selectedIds, setSelectedIds] = useState(new Set())  // Checkboxes cochées
```

**Fonctions clés:**

```javascript
// Charge les tournées depuis localStorage
const loadTournees = async () => {
    const saved = localStorage.getItem('tournees_accords')
    if (saved) {
        setTournees(JSON.parse(saved))
    }
}

// Obtenir les piano_ids d'une tournée
const getTourneePianos = (tourneeId) => {
    const tournee = tournees.find(t => t.id === tourneeId)
    return tournee?.piano_ids || []
}

// Vérifier si un piano est dans une tournée
const isPianoInTournee = (piano, tourneeId) => {
    const tourneePianoIds = getTourneePianos(tourneeId)
    const pianoGzId = piano.gazelleId || piano.id
    return tourneePianoIds.includes(pianoGzId)
}

// Détermine la couleur de la ligne
const getRowClass = (piano) => {
    if (piano.status === 'top') return 'bg-amber-200'
    if (piano.status === 'completed') return 'bg-green-200'

    // JAUNE si: dans tournée OU proposed OU "à faire" rempli
    if (
        (selectedTourneeId && isPianoInTournee(piano, selectedTourneeId)) ||
        piano.status === 'proposed' ||
        (piano.aFaire && piano.aFaire.trim() !== '')
    ) return 'bg-yellow-200'

    if (selectedIds.has(piano.id)) return 'bg-purple-100'  // Coché
    return 'bg-white'
}
```

**Structure localStorage:**
```json
{
  "tournees_accords": [
    {
      "id": "tournee_1234567890",
      "nom": "test3",
      "date_debut": "2025-01-15",
      "etablissement": "vincent-dindy",
      "status": "draft",
      "piano_ids": [
        "ins_8HOR0byGIBquifag",
        "ins_mffGCA0a8DsFJkTm",
        "ins_abc123def456"
      ]
    },
    {
      "id": "tournee_0987654321",
      "nom": "test4",
      "date_debut": "2025-01-20",
      "etablissement": "vincent-dindy",
      "status": "draft",
      "piano_ids": [
        "ins_xyz789uvw012",
        "ins_qrs345tuv678"
      ]
    }
  ]
}
```

---

## Bugs Actuels Non Résolus

### Bug #1: test4 montre les pianos de test3

**Comportement observé:**
1. Utilisateur clique sur tournée "test3" → pianos de test3 s'affichent en jaune ✅
2. Utilisateur clique sur tournée "test4" → pianos de test3 RESTENT en jaune ❌

**Hypothèses:**
1. `tournees` (state React) n'est pas synchronisé avec localStorage
2. `getTourneePianos()` retourne les mauvais IDs
3. Le re-render ne se déclenche pas correctement après le clic
4. Les `piano_ids` dans localStorage sont corrompus/dupliqués

**Code suspect:**
```javascript
// Clic sur tournée (ligne ~954)
onClick={() => {
    setSelectedTourneeId(tournee.id);
    setShowOnlySelected(false);
    setSelectedIds(new Set());  // Vide les checkboxes
}}
```

Après `setSelectedTourneeId()`, le composant devrait re-render et `getRowClass()` devrait recalculer les couleurs. Mais quelque chose empêche ça.

### Bug #2: localStorage parfois pas à jour

Quand on ajoute/retire un piano d'une tournée:

```javascript
const togglePianoInTournee = async (piano) => {
    const pianoId = piano.gazelleId || piano.id

    // Modifier localStorage
    const tourneeData = JSON.parse(localStorage.getItem('tournees_accords') || '[]')
    const tournee = tourneeData.find(t => t.id === selectedTourneeId)

    // ... modification de tournee.piano_ids ...

    localStorage.setItem('tournees_accords', JSON.stringify(tourneeData))

    // Recharger le state React
    await loadTournees()
}
```

**Problème:** Le `await loadTournees()` ne garantit pas que React a fini de re-render avec les nouvelles données.

---

## Ce Qui a Été Essayé

### ✅ Migrations de données
- Scripts pour convertir anciens IDs (serial) vers nouveaux (gazelleId)
- Fichiers: `migrate_tournees.html`, `reset_tournees.html`
- Utilisateur a supprimé toutes les anciennes tournées et recréé test3/test4 avec système propre

### ✅ Simplification du code
- Suppression de tout le code de compatibilité
- N'utilise plus QUE gazelleId
- Suppression de la colonne "Dans tournée" (trop confus)

### ✅ Clarification de la sémantique
- Checkboxes = actions batch seulement
- Couleur = état du piano (tournée, proposed, à faire)
- Vidage des checkboxes au changement de tournée

### ⚠️ Debug logs
- Ajout de `window.DEBUG_TOURNEES` pour activer logs détaillés
- Code à ligne 127-144 dans VincentDIndyDashboard.jsx

### ❌ Synchronisation React/localStorage
- Toujours problématique
- `loadTournees()` est async mais pas attendu partout
- Pas de mécanisme de garantie de cohérence

---

## Architecture Cible (Propre)

### Principes

1. **Une seule source de vérité pour les IDs**
   - UNIQUEMENT `gazelleId` (format `ins_xxxxx`)
   - Jamais utiliser `serial` comme ID
   - Backend retourne `id` = `gazelleId` (pas de redondance)

2. **État React est la source de vérité**
   - localStorage = persistance seulement
   - Toujours lire depuis `tournees` (state), jamais directement depuis localStorage
   - Synchronisation explicite après chaque modification

3. **Séparation claire des responsabilités**
   - **Tournée active** (`selectedTourneeId`) = quelle tournée on regarde
   - **Sélection batch** (`selectedIds`) = checkboxes pour actions multiples
   - **Couleur de ligne** = calculée à partir de l'état du piano (status, tournée, à faire)

4. **Immutabilité des données**
   - Ne jamais modifier directement les objets tournée
   - Toujours créer de nouveaux objets/arrays
   - Garantit que React détecte les changements

### Structure de Données Recommandée

```typescript
// Types TypeScript (pour clarté)

type GazelleId = string  // Format: "ins_xxxxx"

interface Piano {
  id: GazelleId              // Identifiant unique (gazelleId)
  serie: string              // Numéro de série (non-unique!)
  local: string              // Ex: "VD431"
  piano: string              // Marque: "Yamaha"
  modele: string
  type: 'G' | 'U' | 'D'      // Grand/Upright/Droit
  status: 'normal' | 'proposed' | 'top' | 'completed'
  aFaire: string             // Notes pour le technicien
  dernierAccord: string      // ISO date
  // ... autres champs
}

interface Tournee {
  id: string                 // Format: "tournee_" + timestamp
  nom: string                // Ex: "Janvier 2025"
  date_debut: string         // ISO date
  etablissement: 'vincent-dindy' | 'orford'
  status: 'draft' | 'active' | 'completed'
  piano_ids: GazelleId[]     // Liste des gazelleId
  created_at: string         // ISO timestamp
  updated_at: string         // ISO timestamp
}

interface AppState {
  pianos: Piano[]            // Tous les pianos (depuis API)
  tournees: Tournee[]        // Toutes les tournées (depuis localStorage)
  selectedTourneeId: string | null  // Tournée active
  selectedIds: Set<GazelleId>       // Checkboxes cochées
}
```

### Actions Recommandées

```javascript
// Action: Charger les tournées depuis localStorage
function loadTournees() {
  const data = localStorage.getItem('tournees_accords')
  const tournees = data ? JSON.parse(data) : []
  setTournees(tournees)
  return tournees
}

// Action: Sauvegarder les tournées dans localStorage
function saveTournees(tournees) {
  localStorage.setItem('tournees_accords', JSON.stringify(tournees))
  setTournees([...tournees])  // Force re-render
}

// Action: Sélectionner une tournée
function selectTournee(tourneeId) {
  setSelectedTourneeId(tourneeId)
  setSelectedIds(new Set())  // Vider les checkboxes
}

// Action: Ajouter un piano à la tournée active
function addPianoToActiveTournee(pianoId) {
  if (!selectedTourneeId) return

  const updatedTournees = tournees.map(t => {
    if (t.id !== selectedTourneeId) return t

    // Immutabilité: créer nouveau tableau
    const newPianoIds = t.piano_ids.includes(pianoId)
      ? t.piano_ids  // Déjà présent
      : [...t.piano_ids, pianoId]

    return {
      ...t,
      piano_ids: newPianoIds,
      updated_at: new Date().toISOString()
    }
  })

  saveTournees(updatedTournees)
}

// Action: Retirer un piano de la tournée active
function removePianoFromActiveTournee(pianoId) {
  if (!selectedTourneeId) return

  const updatedTournees = tournees.map(t => {
    if (t.id !== selectedTourneeId) return t

    return {
      ...t,
      piano_ids: t.piano_ids.filter(id => id !== pianoId),
      updated_at: new Date().toISOString()
    }
  })

  saveTournees(updatedTournees)
}

// Sélecteur: Obtenir la tournée active
function getActiveTournee() {
  return tournees.find(t => t.id === selectedTourneeId) || null
}

// Sélecteur: Vérifier si un piano est dans la tournée active
function isPianoInActiveTournee(pianoId) {
  const tournee = getActiveTournee()
  return tournee?.piano_ids.includes(pianoId) || false
}
```

### Rendu Optimisé

```javascript
// Calcul de couleur (pur, prévisible)
function getPianoRowColor(piano, activeTournee) {
  // Priorité 1: Status spéciaux
  if (piano.status === 'top') return 'bg-amber-200'
  if (piano.status === 'completed') return 'bg-green-200'

  // Priorité 2: Travail à faire (jaune)
  const inTournee = activeTournee?.piano_ids.includes(piano.id)
  const isProposed = piano.status === 'proposed'
  const hasTask = piano.aFaire?.trim() !== ''

  if (inTournee || isProposed || hasTask) {
    return 'bg-yellow-200'
  }

  // Priorité 3: Sélection batch (mauve)
  if (selectedIds.has(piano.id)) {
    return 'bg-purple-100'
  }

  // Par défaut
  return 'bg-white'
}

// Dans le rendu
const activeTournee = getActiveTournee()

return (
  <table>
    <tbody>
      {pianos.map(piano => (
        <tr
          key={piano.id}
          className={getPianoRowColor(piano, activeTournee)}
        >
          {/* ... cellules ... */}
        </tr>
      ))}
    </tbody>
  </table>
)
```

---

## Recommandations pour Refonte

### Phase 1: Audit et Nettoyage
1. **Exporter les données actuelles** de localStorage (backup)
2. **Inspecter les `piano_ids`** de test3 et test4 (avec debug_tournees.html)
3. **Vérifier la cohérence** des gazelleId dans l'API backend
4. **Supprimer tout code mort** (compatibilité, anciens IDs)

### Phase 2: Refactorisation Backend
1. **Éliminer la redondance** `id` et `gazelleId` (garder seulement `id`)
2. **Ajouter validation** côté backend: gazelleId doit toujours être au format `ins_xxxxx`
3. **Endpoint de debug** pour lister tous les gazelleId disponibles

### Phase 3: Refactorisation Frontend
1. **Extraire la logique tournées** dans un hook custom `useTournees()`
2. **Utiliser useReducer** au lieu de multiples useState pour état cohérent
3. **Synchronisation explicite** après chaque modification localStorage
4. **Tests unitaires** pour les fonctions de sélecteur

### Phase 4: Architecture Moderne (Optionnel)
Si le projet grandit, considérer:
- **Redux Toolkit** ou Zustand pour state management global
- **React Query** pour cache et synchronisation API
- **Backend persistance** (PostgreSQL) au lieu de localStorage
- **WebSocket** pour synchronisation temps réel entre utilisateurs

---

## Fichiers à Modifier/Créer

### À modifier:
1. `/api/vincent_dindy.py` - Éliminer redondance id/gazelleId
2. `/frontend/src/components/VincentDIndyDashboard.jsx` - Refactoriser logique tournées
3. `/frontend/src/hooks/useTournees.js` - **NOUVEAU** Custom hook pour gérer tournées

### À créer:
1. `/frontend/src/hooks/useTournees.js` - Hook custom pour state tournées
2. `/frontend/src/utils/tourneeHelpers.js` - Fonctions pures pour logique métier
3. `/frontend/src/types/index.d.ts` - Types TypeScript (si migration TS)

### Outils de debug à garder:
- `/frontend/debug_tournees.html` - Inspecteur localStorage
- `/frontend/migrate_tournees.html` - Migration données (au cas où)

---

## Questions pour Gemini

1. **Architecture state management:** useReducer suffit ou vaut mieux Redux/Zustand?
2. **Persistance:** Rester sur localStorage ou migrer vers backend DB?
3. **Synchronisation:** Comment garantir cohérence React state ↔ localStorage?
4. **Performance:** 200 pianos, re-renders fréquents, optimisations nécessaires?
5. **Tests:** Stratégie de test pour éviter régressions futures?
6. **Migration:** Comment migrer en douceur sans casser l'app en production?

---

## Contexte Utilisateur

**Niveau technique:** L'utilisateur (Allan) est développeur mais pas expert React. Il préfère:
- Solutions simples et prévisibles
- Pas de magie (hooks complexes, HOC, etc.)
- Code commenté en français
- Logs de debug explicites

**Contraintes:**
- Application déjà en production (utilisée par Nicolas le technicien)
- Pas de temps pour réécriture complète
- Migration incrémentale préférée
- Doit rester compatible avec l'API Gazelle existante

---

## Conclusion

Le système actuel souffre principalement de:
1. **Synchronisation state React vs localStorage** non fiable
2. **Logique métier dispersée** dans le composant (pas modulaire)
3. **Pas de tests** pour valider les comportements

**Objectif:** Repartir sur bases solides avec:
- État prévisible et cohérent
- Séparation claire des responsabilités
- Code testable et maintenable
- Migration douce sans casser l'existant

**Question clé pour Gemini:** Comment structurer l'architecture pour que quand on clique sur "test4", SEULEMENT les pianos de test4 s'affichent en jaune, de façon 100% fiable?
