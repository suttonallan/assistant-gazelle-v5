# Architecture des tournées d'accords

## Vue d'ensemble

Système de gestion des tournées d'accords avec workflow de création → activation → conclusion.

## Structure actuelle (V1)

### Modèle de données

```javascript
{
  id: 'tournee_1234567890',
  nom: 'Tournée Place des Arts - Janvier 2025',
  date_debut: '2025-01-15',
  date_fin: '2025-01-20',
  notes: 'Notes additionnelles',
  technicien_responsable: 'nicolas@example.com',
  techniciens_assignes: [], // Vide pour V1
  status: 'planifiee' | 'en_cours' | 'terminee',
  created_at: '2025-01-10T10:00:00Z'
}
```

### Workflow des statuts

1. **planifiee** : Tournée créée mais pas encore commencée
   - Visible par: Admin, Nick
   - Actions: Activer, Supprimer, Voir les pianos

2. **en_cours** : Tournée active (UNE SEULE à la fois en V1)
   - Visible par: Admin, Nick, Louise, Jean-Philippe
   - Actions: Conclure, Voir les pianos
   - Activer une nouvelle tournée désactive automatiquement l'ancienne

3. **terminee** : Tournée conclue (archive)
   - Visible par: Admin, Nick
   - Actions: Voir les pianos (lecture seule)

## Permissions par rôle (V1)

### Admin & Nick (Gestionnaire)
- ✅ Voir toutes les tournées (tous statuts)
- ✅ Créer des tournées
- ✅ Activer une tournée (passe de planifiee → en_cours)
- ✅ Conclure une tournée (passe de en_cours → terminee)
- ✅ Supprimer une tournée
- ✅ Voir les pianos de n'importe quelle tournée

### Louise & Jean-Philippe (Assistante/Technicien)
- ✅ Voir UNIQUEMENT la tournée active (status = en_cours)
- ✅ Voir les pianos de la tournée active
- ❌ Ne peuvent PAS créer, activer, conclure ou supprimer

## Extensions futures (V2+)

### 1. Assignation de techniciens

**Objectif**: Permettre d'assigner des techniciens spécifiques à une tournée.

**Changements**:
```javascript
{
  // ...
  techniciens_assignes: ['jeanphilippe@example.com', 'nicolas@example.com'],
  // ...
}
```

**Logique de filtrage** (déjà préparée dans le code):
```javascript
// Dans JeanPhilippeDashboard et LouiseDashboard
const myEmail = currentUser?.email
const myTournees = allTournees.filter(t =>
  t.status === 'en_cours' &&
  (t.techniciens_assignes.length === 0 || t.techniciens_assignes.includes(myEmail))
)
```

**Interface Nick/Admin**:
- Ajouter un sélecteur multi-choix dans le formulaire de création
- Liste des techniciens disponibles
- Pouvoir modifier l'assignation d'une tournée existante

### 2. Tournées multiples actives simultanément

**Objectif**: Permettre plusieurs tournées en_cours en même temps (utile si plusieurs équipes).

**Changements**:
```javascript
// Supprimer la logique qui désactive les autres tournées lors de l'activation
const handleActiverTournee = async (tourneeId) => {
  // Avant (V1):
  // status: t.id === tourneeId ? 'en_cours' : (t.status === 'en_cours' ? 'planifiee' : t.status)

  // Après (V2):
  // status: t.id === tourneeId ? 'en_cours' : t.status
}
```

**Filtrage techniciens**:
- Si `techniciens_assignes` est vide: voir toutes les tournées actives
- Si assigné: voir uniquement les tournées où ils sont assignés

### 3. Institutions multiples

**Objectif**: Gérer tournées pour Vincent-d'Indy, Place des Arts, etc.

**Changements**:
```javascript
{
  // ...
  institution_id: 'inst_vincent_dindy',
  // ...
}
```

**Voir**: `docs/ARCHITECTURE_MULTI_INSTITUTIONS.md`

### 4. Base de données Supabase

**Migration** de localStorage vers Supabase:

```sql
CREATE TABLE tournees_accords (
  id TEXT PRIMARY KEY,
  nom TEXT NOT NULL,
  date_debut DATE NOT NULL,
  date_fin DATE,
  notes TEXT,
  technicien_responsable TEXT NOT NULL,
  techniciens_assignes TEXT[], -- Array de emails
  institution_id TEXT REFERENCES institutions(id) DEFAULT 'inst_vincent_dindy',
  status TEXT CHECK (status IN ('planifiee', 'en_cours', 'terminee')) DEFAULT 'planifiee',
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Compatibilité ascendante

**Important**: Toutes les extensions futures doivent rester compatibles avec V1:
- `techniciens_assignes = []` signifie "tous les techniciens" (comportement V1)
- Une seule tournée active par défaut (peut être étendu)
- localStorage → Supabase avec migration transparente

## Exemples de code pour V2

### Assignation de techniciens (Nick/Admin)

```javascript
const [newTournee, setNewTournee] = useState({
  nom: '',
  date_debut: '',
  date_fin: '',
  notes: '',
  techniciens_assignes: [] // Nouveau champ
})

// Dans le formulaire:
<div className="mb-4">
  <label className="block text-sm font-medium text-gray-700 mb-2">
    Techniciens assignés (optionnel)
  </label>
  <select
    multiple
    value={newTournee.techniciens_assignes}
    onChange={(e) => setNewTournee({
      ...newTournee,
      techniciens_assignes: Array.from(e.target.selectedOptions, opt => opt.value)
    })}
    className="w-full px-3 py-2 border border-gray-300 rounded-md"
  >
    <option value="nicolas@example.com">Nick</option>
    <option value="jeanphilippe@example.com">Jean-Philippe</option>
    <option value="allan@example.com">Allan</option>
  </select>
  <p className="text-xs text-gray-500 mt-1">
    Vide = tous les techniciens peuvent voir cette tournée
  </p>
</div>
```

### Filtrage côté technicien

```javascript
const getMyActiveTournees = (allTournees, userEmail) => {
  return allTournees.filter(t => {
    // Tournée doit être active
    if (t.status !== 'en_cours') return false

    // Si aucun technicien assigné, tous peuvent voir
    if (!t.techniciens_assignes || t.techniciens_assignes.length === 0) {
      return true
    }

    // Sinon, vérifier si l'utilisateur est assigné
    return t.techniciens_assignes.includes(userEmail)
  })
}
```

## Migration V1 → V2

### Étape 1: Ajouter le champ sans casser V1
- ✅ Déjà fait: `techniciens_assignes: []` dans la création

### Étape 2: Ajouter l'UI d'assignation
- Formulaire Nick/Admin pour sélectionner techniciens
- Optionnel: laisser vide = tous (comportement V1)

### Étape 3: Activer le filtrage
- Décommenter le code dans JeanPhilippeDashboard et LouiseDashboard
- Tester que `[]` fonctionne comme "tous"

### Étape 4: Permettre tournées multiples
- Modifier `handleActiverTournee`
- Interface pour voir quelle tournée est la "sienne"
