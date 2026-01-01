# VDI Refactor - Architecture TypeScript Réutilisable

## 🎯 Vision

Système de gestion de tournées d'accordage **robuste, élégant et performant** avec:
- **TypeScript strict** pour éliminer les bugs
- **Supabase Realtime** pour sync multi-devices (Mac ↔ iPad)
- **Hooks personnalisés** pour séparation logique/présentation
- **Architecture réutilisable** pour toutes institutions (Vincent d'Indy, Orford, etc.)

## 📐 Principes d'Architecture

### 1. **Généricité**
Chaque institution hérite d'une base commune configurable:
```typescript
// config/institutions.ts
const VINCENT_DINDY: InstitutionConfig = {
  id: 'vincent-dindy',
  gazelleClientId: 'client_id_vdi',
  maxPianos: 100,
  features: { tournees: true, topPriority: true },
  colorRules: { /* custom */ }
}
```

### 2. **Type Safety**
- Interfaces strictes pour Piano, Tournee, Updates
- Validation Zod pour data incoming/outgoing
- Pas de `any`, pas de `as unknown`

### 3. **Separation of Concerns**
```
Hooks (logique métier)
  ↓
Components (présentation)
  ↓
Lib (services externes: Supabase, Gazelle API)
```

### 4. **Performance**
- `useMemo` pour calculs coûteux (filtrage, tri)
- Realtime subscriptions optimisées (1 par resource)
- Batch updates pour modifications groupées

## 🗂️ Structure

```
refactor/vdi/
├── types/
│   ├── piano.types.ts        # Piano, PianoStatus, PianoUpdate
│   ├── tournee.types.ts      # Tournee, TourneeStatus
│   ├── institution.types.ts  # Config multi-institutions
│   └── supabase.types.ts     # DB row types
│
├── hooks/
│   ├── usePianos.ts          # Fetch + Realtime pianos
│   ├── useTournees.ts        # CRUD tournées + Realtime
│   ├── useRangeSelection.ts  # Shift+Clic selection
│   ├── usePianoColors.ts     # Business logic couleurs
│   └── useBatchOperations.ts # Bulk updates
│
├── lib/
│   ├── supabase.client.ts    # Supabase + Realtime setup
│   ├── validators.ts         # Zod schemas
│   └── utils.ts              # Date format, ID generation
│
├── components/
│   ├── VDIInventory/         # /vdi/inventaire
│   ├── VDITournees/          # Dashboard principal
│   └── shared/               # Composants réutilisables
│
├── config/
│   └── institutions.ts       # Config par institution
│
└── tests/
    ├── piano-colors.test.ts  # Logique critique
    └── range-selection.test.ts
```

## 🎨 Règles Métier VDV7

### Logique Couleurs (Priorité Descendante)
1. **Ambre** (`bg-amber-200`): Piano `status === 'top'` (concert)
2. **Vert** (`bg-green-200`): Piano `status === 'completed'` ET `completedInTourneeId === activeTourneeId`
3. **Jaune** (`bg-yellow-200`): Piano `status === 'proposed'` OU dans tournée active
4. **Blanc** (`bg-white`): Défaut

### Reset Automatique
Quand nouvelle tournée activée:
- Tous pianos Vert → Jaune (si dans nouvelle tournée) ou Blanc
- `completedInTourneeId` reset pour pianos hors nouvelle tournée

### Délai Last Tuned
Format compact: `+3s` (3 semaines depuis dernier accord)
- Calculé: `Math.floor(daysSince / 7)` semaines
- Affiché en très petit à côté du nom piano

## 🔄 Synchronisation Realtime

### Piano Updates
```typescript
supabase
  .channel('vincent_dindy_piano_updates')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'vincent_dindy_piano_updates'
  }, (payload) => {
    // Merge payload avec état local
  })
  .subscribe()
```

### Tournées
```typescript
supabase
  .channel('tournees')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'tournees',
    filter: `etablissement=eq.vincent-dindy`
  }, (payload) => {
    // Update liste tournées
  })
  .subscribe()
```

## 🧪 Tests

### Coverage Minimale
- ✅ Logique couleur (tous cas edge)
- ✅ Shift+Clic range selection
- ✅ Batch operations (status updates)
- ✅ Tournée activation/désactivation
- ✅ Reset Vert → Jaune

### Stack
- **Vitest**: Tests unitaires hooks
- **Testing Library**: Tests composants React
- **MSW**: Mock Supabase API (si nécessaire)

## 🚀 Migration Plan

### Phase 1: Types & Infrastructure (CURRENT)
- [x] Structure dossiers
- [x] TypeScript config strict
- [ ] Types de base (Piano, Tournee)
- [ ] Supabase client setup

### Phase 2: Database
- [ ] Créer table `tournees`
- [ ] Ajouter colonne `completed_in_tournee_id`
- [ ] Supprimer localStorage (tournées tests)

### Phase 3: Hooks
- [ ] `usePianos` + Realtime
- [ ] `useTournees` + Realtime
- [ ] `usePianoColors`
- [ ] `useRangeSelection`
- [ ] `useBatchOperations`

### Phase 4: Components
- [ ] `VDIInventory` page
- [ ] Refactor `PianosTable`
- [ ] `BatchToolbar`
- [ ] `LastTunedBadge`

### Phase 5: Testing & Docs
- [ ] Tests unitaires
- [ ] Documentation hooks
- [ ] Guide migration autres institutions

## 📚 Ressources

- [Supabase Realtime Docs](https://supabase.com/docs/guides/realtime)
- [Zod Validation](https://zod.dev/)
- [React Hooks Best Practices](https://react.dev/reference/react)

---

**Architecture by Claude Code** 🤖
Conçue pour robustesse maximale, élégance et réutilisabilité.
