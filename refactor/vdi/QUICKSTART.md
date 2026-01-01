## 🚀 VDV7 - Guide de Démarrage Rapide

Bienvenue dans VDV7, le système de gestion de tournées TypeScript ultra-robuste.

---

## 📦 Installation

### 1. Installer les dépendances

```bash
cd refactor/vdi
npm install
```

### 2. Configurer l'environnement

Copier `.env.example` → `.env` et remplir:

```bash
cp .env.example .env
```

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
VITE_GAZELLE_CLIENT_ID_VDI=client_vincent_dindy
VITE_DEFAULT_INSTITUTION=vincent-dindy
VITE_ENABLE_REALTIME=true
```

### 3. Exécuter les migrations SQL

```bash
# Migration 1: Créer table tournees
psql $DATABASE_URL -f sql/001_create_tournees_table.sql

# Migration 2: Ajouter colonne completed_in_tournee_id
psql $DATABASE_URL -f sql/002_alter_piano_updates_add_tournee.sql
```

Ou via Supabase Dashboard:
1. Aller dans SQL Editor
2. Copier-coller le contenu de chaque fichier SQL
3. Exécuter

---

## 🎯 Utilisation de Base

### Exemple 1: Afficher liste de pianos

```tsx
import { usePianos, LastTunedBadge } from '@/refactor/vdi';

function PianosList() {
  const { pianos, loading, error } = usePianos('vincent-dindy');

  if (loading) return <div>Chargement...</div>;
  if (error) return <div>Erreur: {error}</div>;

  return (
    <ul>
      {pianos.map(piano => (
        <li key={piano.gazelleId}>
          {piano.make} {piano.model} - {piano.location}
          <LastTunedBadge lastTuned={piano.lastTuned} />
        </li>
      ))}
    </ul>
  );
}
```

### Exemple 2: Créer une tournée

```tsx
import { useTournees } from '@/refactor/vdi';

function CreateTourneeForm() {
  const { createTournee, loading } = useTournees('vincent-dindy');

  const handleSubmit = async (e) => {
    e.preventDefault();

    const newTournee = await createTournee({
      nom: 'Tournée Hiver 2025',
      dateDebut: new Date('2025-01-15'),
      dateFin: new Date('2025-02-15'),
      etablissement: 'vincent-dindy',
      technicienResponsable: 'nicolas@example.com'
    });

    console.log('Tournée créée:', newTournee);
  };

  return <form onSubmit={handleSubmit}>...</form>;
}
```

### Exemple 3: Couleurs dynamiques

```tsx
import { usePianoColors, useTournees } from '@/refactor/vdi';

function PianoRow({ piano }) {
  const { activeTournee } = useTournees('vincent-dindy');
  const { getColor, getColorWithReason } = usePianoColors('vincent-dindy', {
    activeTourneeId: activeTournee?.id
  });

  const className = getColor(piano);
  const { reason } = getColorWithReason(piano);

  return (
    <tr className={className} title={reason}>
      <td>{piano.make}</td>
      <td>{piano.location}</td>
    </tr>
  );
}
```

### Exemple 4: Batch operations

```tsx
import { useBatchOperations, useRangeSelection } from '@/refactor/vdi';

function BatchToolbar({ pianos }) {
  const { selectedIds, handleClick, selectAll, clearAll } = useRangeSelection(
    pianos.map(p => p.gazelleId)
  );

  const { batchUpdateStatus, loading } = useBatchOperations();

  const markAsTop = async () => {
    await batchUpdateStatus(selectedIds, 'top', {
      onSuccess: (count) => alert(`${count} pianos marqués Top!`),
      onError: (err) => alert(`Erreur: ${err}`)
    });

    clearAll();
  };

  return (
    <div>
      <button onClick={selectAll}>Tout sélectionner</button>
      <button onClick={clearAll}>Désélectionner</button>
      <button onClick={markAsTop} disabled={loading || selectedIds.size === 0}>
        Marquer comme Top ({selectedIds.size})
      </button>

      {pianos.map(piano => (
        <label key={piano.gazelleId}>
          <input
            type="checkbox"
            checked={selectedIds.has(piano.gazelleId)}
            onClick={(e) => handleClick(piano.gazelleId, e.shiftKey)}
          />
          {piano.make}
        </label>
      ))}
    </div>
  );
}
```

---

## 🎨 Logique Couleur VDV7

Les pianos changent de couleur selon leur statut:

| Couleur | Condition | Classe CSS |
|---------|-----------|-----------|
| **Ambre** | `status === 'top'` (piano de concert) | `bg-amber-200 border-amber-400` |
| **Vert** | `status === 'completed'` ET dans tournée active | `bg-green-200 border-green-400` |
| **Jaune** | `status === 'proposed'` OU dans tournée active | `bg-yellow-200 border-yellow-400` |
| **Blanc** | Défaut | `bg-white border-gray-200` |

### Règle Important: Reset Automatique

Quand une nouvelle tournée est **activée**:

1. Toutes les autres tournées passent en `planifiee`
2. Les pianos Vert des anciennes tournées **redeviennent Blanc/Jaune**
3. Trigger SQL fait ça automatiquement ✨

```typescript
// Activer tournée (fait reset automatique)
const { activateTournee } = useTournees('vincent-dindy');
await activateTournee('tournee_12345');

// → Anciennes tournées désactivées
// → Leurs pianos Vert → Blanc
// → Nouvelle tournée activée
```

---

## 🔄 Realtime Sync (Mac ↔ iPad)

Le système synchronise automatiquement les changements entre devices:

```typescript
// Sur Mac: Michelle modifie piano
await updatePiano('gz_123', { status: 'completed' });

// Sur iPad: Nicolas voit le changement INSTANTANÉMENT
// (via Supabase Realtime subscription)
```

### Comment ça marche?

1. `usePianos` s'abonne aux changements de `vincent_dindy_piano_updates`
2. `useTournees` s'abonne aux changements de `tournees`
3. Quand DB change → Callback appelé → UI re-render
4. Pas de polling, pas de latence!

---

## 📁 Structure des Fichiers

```
refactor/vdi/
├── types/              ← Interfaces TypeScript strictes
│   ├── piano.types.ts
│   ├── tournee.types.ts
│   └── institution.types.ts
│
├── config/             ← Configuration par institution
│   └── institutions.ts
│
├── lib/                ← Services externes
│   ├── supabase.client.ts   (Realtime)
│   ├── validators.ts        (Zod schemas)
│   └── utils.ts             (Helpers)
│
├── hooks/              ← Logique métier (hooks personnalisés)
│   ├── usePianos.ts         (Fetch + Realtime pianos)
│   ├── useTournees.ts       (CRUD tournées)
│   ├── usePianoColors.ts    (Logique couleur)
│   ├── useRangeSelection.ts (Shift+Clic)
│   └── useBatchOperations.ts (Bulk updates)
│
├── components/         ← UI React
│   └── shared/
│       ├── LastTunedBadge.tsx
│       └── PianoStatusPill.tsx
│
├── sql/                ← Migrations DB
│   ├── 001_create_tournees_table.sql
│   └── 002_alter_piano_updates_add_tournee.sql
│
└── index.ts            ← Exports centralisés
```

---

## 🧪 Tests

```bash
# Run tests
npm test

# Run tests avec UI
npm run test:ui

# Coverage
npm run test:coverage
```

### Tests prioritaires

1. **Logique couleur** (`usePianoColors`)
   - Vert seulement si `completedInTourneeId === activeTourneeId`
   - Ambre > Vert > Jaune > Blanc

2. **Shift+Clic** (`useRangeSelection`)
   - Sélection plage correcte
   - Edge cases (premier/dernier item)

3. **Batch operations**
   - Rollback si erreur
   - Progress tracking

---

## 🔧 TypeScript Strict Mode

Tous les fichiers sont en **strict mode**:

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noUncheckedIndexedAccess": true
  }
}
```

**Avantages**:
- Bugs détectés au compile-time
- Autocomplete IntelliSense parfait
- Refactoring safe (renommage, etc.)
- Pas de `any`, pas de surprises runtime

---

## 📚 Prochaines Étapes

### Phase 3 (À implémenter)

1. **VDIInventory** - Page `/vdi/inventaire`
   - Gestion bulk `isHidden`
   - Filtres avancés

2. **PianosTable** - Refactor avec hooks TypeScript
   - Intégration `useRangeSelection`
   - Tri + filtres

3. **TourneesSidebar** - CRUD tournées
   - Création/modification
   - Activation/désactivation
   - Drag&drop pianos?

4. **Tests E2E** - Playwright
   - Workflow complet: créer tournée → ajouter pianos → activer → compléter

---

## 🐛 Troubleshooting

### Erreur: "Missing Supabase env vars"

→ Vérifier `.env` contient `VITE_SUPABASE_URL` et `VITE_SUPABASE_ANON_KEY`

### Erreur: "Table tournees does not exist"

→ Exécuter migration SQL `001_create_tournees_table.sql`

### Realtime ne fonctionne pas

1. Vérifier plan Supabase supporte Realtime
2. Check logs: `supabase.getChannels()` dans console
3. Activer debug: `VITE_ENABLE_DEBUG_LOGS=true` dans `.env`

### TypeScript errors partout

→ Run `npm run typecheck` pour voir tous les problèmes

---

## 🎯 Philosophie VDV7

1. **Type Safety First**: Zéro `any`, validation partout
2. **Separation of Concerns**: Hooks (logique) ≠ Components (UI)
3. **Optimistic Updates**: UI rapide, sync en background
4. **Realtime by Default**: Pas de polling, subscriptions Supabase
5. **Réutilisable**: Config-based pour multi-institutions

---

## 📞 Support

Questions? Voir:
- [README.md](./README.md) - Architecture détaillée
- [types/](./types/) - Documentation inline dans types
- [Tests](./tests/) - Exemples d'utilisation

**Conçu avec ❤️ par Claude Code pour robustesse maximale** 🚀
