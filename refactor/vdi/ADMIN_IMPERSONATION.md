# Admin Impersonation - Guide d'utilisation

## Date: 2026-01-01

## Vue d'ensemble

Le système **Admin Impersonation** (ou "User View Simulation") permet à l'administrateur de visualiser l'interface selon différents rôles utilisateurs **sans changer ses permissions réelles**.

### Cas d'usage

1. **Support technique**: "L'assistante dit qu'elle ne voit pas le bouton X" → Switcher sur sa vue pour comprendre
2. **Validation UX**: Tester que les permissions d'affichage fonctionnent correctement
3. **Debug rapide**: Pas besoin de se déconnecter/reconnecter avec différents comptes

---

## Architecture

### Principe de séparation (CRITIQUE)

```
🎨 activeViewRole  → Ce qui s'AFFICHE (UI, conditional rendering)
🔒 realRole         → Ce qui est CHARGÉ (données, permissions Supabase)
```

### Sécurité

**RÈGLE D'OR**: Les requêtes Supabase utilisent **TOUJOURS** le `realRole`, jamais le `activeViewRole`.

```tsx
// ❌ MAUVAIS - Dangereux!
const { data } = await supabase
  .from('pianos')
  .eq('assigned_to', activeViewRole); // FAILLE DE SÉCURITÉ

// ✅ BON - Sécurisé
const { user } = useAuth(); // Vraie session
const { data } = await supabase
  .from('pianos')
  .eq('assigned_to', user.email); // Utilise vrai rôle
```

---

## Composants créés

### 1. Types (`types/auth.types.ts`)

```typescript
export type UserRole = 'admin' | 'assistant' | 'technicien';

export interface ViewContext {
  realRole: UserRole;          // Rôle réel (immuable)
  activeViewRole: UserRole;    // Rôle visualisé (changeable par admin)
  isImpersonating: boolean;    // true si simulation active
  canImpersonate: boolean;     // true si admin
  switchView: (role) => void;  // Changer de vue
  resetView: () => void;       // Retour à sa vue
}
```

### 2. Hook (`hooks/useViewContext.ts`)

```tsx
import { useViewContext } from '@hooks/useViewContext';

function MyComponent() {
  const { activeViewRole, isImpersonating, switchView } = useViewContext();

  return (
    <>
      {/* UI basée sur activeViewRole */}
      {activeViewRole === 'admin' && <AdminPanel />}
      {['admin', 'technicien'].includes(activeViewRole) && <TourneeView />}
    </>
  );
}
```

### 3. Bandeau Admin (`components/shared/AdminImpersonationBar.tsx`)

Le bandeau s'affiche **automatiquement** en haut de toutes les pages si l'utilisateur est admin.

Features:
- **Dropdown** pour changer de vue (Admin / Assistant / Technicien)
- **Indicateur visuel** orange quand en mode simulation
- **Bouton "Retour à ma vue"** pour reset
- **Persistance** via localStorage (survit au refresh)

---

## Utilisation

### Dans un composant

```tsx
import { useViewContext } from '@hooks/useViewContext';

function Dashboard() {
  const { activeViewRole } = useViewContext();

  // Filtrer contenu selon rôle actif
  const visibleCards = cards.filter((card) => {
    // Sync Gazelle: Admin uniquement
    if (card.id === 'sync' && activeViewRole !== 'admin') {
      return false;
    }
    return true;
  });

  return (
    <div>
      {visibleCards.map((card) => (
        <Card key={card.id} {...card} />
      ))}
    </div>
  );
}
```

### Permissions par rôle

```typescript
// Exemple de logique conditionnelle
const canEdit = (role: UserRole) => {
  return ['admin', 'assistant'].includes(role);
};

const canManageTournees = (role: UserRole) => {
  return role === 'admin' || role === 'assistant';
};

const canViewAllPianos = (role: UserRole) => {
  return role !== 'technicien'; // Techniciens voient seulement les leurs
};
```

---

## Flow utilisateur (Admin)

### Étape 1: Vue par défaut (Admin)
```
┌─────────────────────────────────────┐
│ 👑 Admin  [Dropdown: Vue Admin ▼]  │  ← Bandeau bleu
└─────────────────────────────────────┘

Dashboard affiché avec:
- Inventaire complet
- Tournées
- Techniciens
- Sync Gazelle
```

### Étape 2: Simulation "Assistant"
```
┌─────────────────────────────────────────────────────────┐
│ 🎭 Mode Simulation  [Dropdown: Vue Assistant ▼]        │  ← Bandeau orange
│                     Vue active: 📋 Assistant            │
│                     [Retour à ma vue →]                 │
└─────────────────────────────────────────────────────────┘

Dashboard affiché avec:
- Inventaire complet
- Tournées
- Techniciens
- ❌ Sync Gazelle (masqué)
```

### Étape 3: Simulation "Technicien"
```
┌─────────────────────────────────────────────────────────┐
│ 🎭 Mode Simulation  [Dropdown: Vue Technicien ▼]       │  ← Bandeau orange
│                     Vue active: 🔧 Technicien           │
│                     [Retour à ma vue →]                 │
└─────────────────────────────────────────────────────────┘

Dashboard affiché avec:
- ❌ Inventaire complet (masqué)
- Tournées (seulement celles assignées)
- ❌ Techniciens (masqué)
- ❌ Sync Gazelle (masqué)
```

---

## Exemple complet

### VDIDashboard avec filtrage

```tsx
export function VDIDashboard({ onNavigate }: Props) {
  const { activeViewRole } = useViewContext();

  // Filtrer cards selon rôle actif
  const visibleCards = ALL_CARDS.filter((card) => {
    // Sync Gazelle: Admin uniquement
    if (card.id === 'sync' && activeViewRole !== 'admin') {
      return false;
    }

    // Inventaire complet: Pas accessible aux techniciens
    if (card.id === 'inventory' && activeViewRole === 'technicien') {
      return false;
    }

    return true;
  });

  return (
    <div>
      {visibleCards.map((card) => (
        <NavigationCard
          key={card.id}
          {...card}
          onClick={() => onNavigate(card.id)}
        />
      ))}
    </div>
  );
}
```

---

## Persistance

Le rôle simulé est **sauvegardé dans localStorage** pour survivre au refresh:

```typescript
// Sauvegarde automatique
localStorage.setItem('vdi_active_view_role', activeViewRole);

// Restauration au chargement
const saved = localStorage.getItem('vdi_active_view_role');
if (saved) setActiveViewRole(saved);
```

**Reset**: Cliquer sur "Retour à ma vue" ou fermer le navigateur.

---

## Tests

### Test manuel

1. Se connecter en tant qu'admin
2. Vérifier que le bandeau bleu apparaît en haut
3. Changer dropdown → "Vue Assistant"
4. Vérifier:
   - ✅ Bandeau devient orange
   - ✅ Card "Sync Gazelle" disparaît
   - ✅ Bouton "Retour à ma vue" apparaît
5. Changer dropdown → "Vue Technicien"
6. Vérifier:
   - ✅ Card "Inventaire" disparaît
   - ✅ Card "Sync Gazelle" disparaît
7. Cliquer "Retour à ma vue"
8. Vérifier:
   - ✅ Bandeau redevient bleu
   - ✅ Toutes les cards réapparaissent

---

## TODO Future

- [ ] Ajouter logs d'audit (tracker qui simule quoi)
- [ ] Afficher warning si admin tente action critique en mode simulation
- [ ] Ajouter raccourci clavier (ex: `Ctrl+Shift+R` pour reset)
- [ ] Stats: "Temps passé en simulation X"

---

## Notes de sécurité

### ✅ Sécurisé
- Les données chargées dépendent du **vrai rôle** uniquement
- RLS Supabase applique les vraies permissions
- Impossible d'escalader ses privilèges

### ⚠️ À surveiller
- Ne pas oublier qu'on est en mode simulation (indicateur visuel orange)
- Les actions (créer tournée, masquer piano) utilisent les **vraies permissions**

---

## Conclusion

Le système d'impersonation est un outil **puissant et sécurisé** pour tester l'UX sans compromettre les données.

**Règle d'or**: UI = `activeViewRole`, Data = `realRole` ✅
