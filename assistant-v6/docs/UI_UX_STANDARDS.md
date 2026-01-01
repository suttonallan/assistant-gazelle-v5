# UI/UX Standards - Assistant Gazelle V6

## 📋 Document "Source de Vérité"

**Objectif:** Définir les standards d'interface utilisateur, patterns UX, et principes de design

**Date création:** 2025-12-29
**Dernière mise à jour:** 2025-12-29

---

## 🎯 Principe Fondamental: Progressive Disclosure

**Vision:**
```
Niveau 1 (Cards)    →    Niveau 2 (Drawer)    →    Niveau 3 (Modal)
  Vue d'ensemble          Détails complets           Actions avancées
  Scannable rapide        Deep dive                  Modifications
  Mobile-first            Contexte riche             Admin/Power users
```

**Pourquoi:**
- Technicien sur terrain: scan rapide de sa journée
- Assistant au bureau: détails complets pour coordination
- Admin: accès complet pour gestion

---

## 📱 Mobile-First Design

### Principe: Thumb-Friendly

**Zone accessible au pouce:**
```
┌─────────────────────┐
│  Header (Safe)      │ ← Pas d'actions critiques
│                     │
│  ✅ Content Zone   │ ← Toutes les cards ici
│     (Scrollable)    │
│                     │
│  ✅ Action Zone    │ ← Boutons principaux ici
│     (Bottom 1/3)    │
└─────────────────────┘
```

**Règles:**
- Boutons importants: bottom 30% de l'écran
- Pas de menu hamburger haut-gauche (trop loin du pouce)
- Swipe gestures pour actions secondaires

### Tailles Tactiles

| Élément | Taille Min | Taille Idéale |
|---------|-----------|---------------|
| Bouton | 44x44 px | 48x48 px |
| Card clickable | Pleine largeur | Pleine largeur |
| Chip/Tag | 32x32 px | 36x36 px |
| Icon button | 40x40 px | 48x48 px |

**Code:**
```css
/* Base touch target */
.btn {
  min-height: 48px;
  min-width: 48px;
  padding: 12px 16px;
}

/* Card */
.appointment-card {
  padding: 16px;
  margin-bottom: 12px;
  cursor: pointer;
  /* Touch feedback */
  transition: transform 0.1s, box-shadow 0.2s;
}

.appointment-card:active {
  transform: scale(0.98);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

---

## 🎨 Design System

### Palette de Couleurs

```css
:root {
  /* Primary (Piano Tek Blue) */
  --color-primary: #1976d2;
  --color-primary-dark: #1565c0;
  --color-primary-light: #42a5f5;

  /* Semantic */
  --color-success: #4caf50;   /* Nouveau client */
  --color-warning: #ff9800;   /* Alerte */
  --color-error: #f44336;     /* Erreur */
  --color-info: #2196f3;      /* Info */

  /* Neutral */
  --color-gray-50: #fafafa;
  --color-gray-100: #f5f5f5;
  --color-gray-200: #eeeeee;
  --color-gray-600: #757575;
  --color-gray-800: #424242;
  --color-gray-900: #212121;

  /* Text */
  --color-text-primary: #1a202c;
  --color-text-secondary: #718096;
  --color-text-disabled: #a0aec0;

  /* Backgrounds */
  --color-bg-page: #f7fafc;
  --color-bg-card: #ffffff;
  --color-bg-hover: #edf2f7;
}
```

### Typographie

```css
/* Famille */
--font-family-base: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--font-family-mono: "Monaco", "Courier New", monospace;

/* Tailles */
--font-size-xs: 12px;    /* Labels, captions */
--font-size-sm: 14px;    /* Body text */
--font-size-base: 16px;  /* Default */
--font-size-lg: 18px;    /* Card titles */
--font-size-xl: 24px;    /* Page headers */
--font-size-2xl: 32px;   /* Hero */

/* Weights */
--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;

/* Line Heights */
--line-height-tight: 1.25;
--line-height-normal: 1.5;
--line-height-relaxed: 1.75;
```

### Espacements

**System: 8px Base Unit**

```css
--spacing-1: 8px;    /* 0.5rem */
--spacing-2: 16px;   /* 1rem */
--spacing-3: 24px;   /* 1.5rem */
--spacing-4: 32px;   /* 2rem */
--spacing-6: 48px;   /* 3rem */
--spacing-8: 64px;   /* 4rem */
```

**Usage:**
```css
.card {
  padding: var(--spacing-2);        /* 16px intérieur */
  margin-bottom: var(--spacing-2);  /* 16px entre cards */
}

.section-header {
  margin-bottom: var(--spacing-3);  /* 24px avant contenu */
}
```

---

## 🧩 Composants Standards

### 1. AppointmentCard (Niveau 1)

**Responsabilité:** Affichage compact d'un RV pour scan rapide.

**Anatomie:**
```
┌────────────────────────────────────────┐
│ ⏰ 09:00 - 11:00          🏷️ Nouveau   │ ← Header (time + badges)
│                                        │
│ M. Jean Tremblay                       │ ← Contact name (bold)
│ Facturer à: École XYZ                  │ ← Billing (subtle)
│                                        │
│ 📍 Rosemont (H2G)                      │ ← Location (quartier!)
│ 4520 rue St-Denis                      │
│                                        │
│ 🎹 Yamaha U1 (Droit)                   │ ← Piano
│                                        │
│ 📋 Apporter cordes #3                  │ ← Action items (chips)
└────────────────────────────────────────┘
```

**Code React (MUI):**
```tsx
// v6/frontend/src/components/AppointmentCard.tsx
import { Card, CardContent, Typography, Chip, Box } from '@mui/material';
import { AccessTime, LocationOn, Piano } from '@mui/icons-material';

interface AppointmentCardProps {
  appointment: AppointmentOverview;
  onClick: () => void;
}

export function AppointmentCard({ appointment, onClick }: AppointmentCardProps) {
  return (
    <Card
      onClick={onClick}
      sx={{
        mb: 2,
        cursor: 'pointer',
        transition: 'all 0.2s',
        '&:hover': {
          boxShadow: 4,
          transform: 'translateY(-2px)',
        },
        '&:active': {
          transform: 'translateY(0)',
          boxShadow: 2,
        }
      }}
    >
      <CardContent>
        {/* Header: Time + Badges */}
        <Box display="flex" justifyContent="space-between" mb={1}>
          <Box display="flex" alignItems="center" gap={1}>
            <AccessTime fontSize="small" color="primary" />
            <Typography variant="h6" fontWeight="bold">
              {appointment.time_slot}
            </Typography>
          </Box>

          <Box display="flex" gap={0.5}>
            {appointment.is_new_client && (
              <Chip label="Nouveau" size="small" color="success" />
            )}
            {appointment.has_alerts && (
              <Chip label="⚠️" size="small" color="warning" />
            )}
          </Box>
        </Box>

        {/* Contact Name */}
        <Typography variant="h6" mb={1}>
          {appointment.client_name}
        </Typography>

        {/* Billing (if different) */}
        {appointment.billing_client && (
          <Typography variant="body2" color="text.secondary" mb={1} fontStyle="italic">
            Facturer à: {appointment.billing_client}
          </Typography>
        )}

        {/* Location */}
        <Box display="flex" alignItems="center" gap={0.5} mb={1}>
          <LocationOn fontSize="small" color="action" />
          <Typography variant="body2" color="text.secondary" fontWeight={600}>
            {appointment.neighborhood}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • {appointment.address_short}
          </Typography>
        </Box>

        {/* Piano */}
        {appointment.piano_brand && (
          <Box display="flex" alignItems="center" gap={0.5} mb={1}>
            <Piano fontSize="small" color="action" />
            <Typography variant="body2">
              {appointment.piano_brand} {appointment.piano_model}
              {appointment.piano_type && ` (${appointment.piano_type})`}
            </Typography>
          </Box>
        )}

        {/* Action Items (Chips) */}
        {appointment.action_items.length > 0 && (
          <Box display="flex" gap={0.5} flexWrap="wrap" mt={1}>
            {appointment.action_items.map((item, i) => (
              <Chip
                key={i}
                label={item}
                size="small"
                variant="outlined"
                color="primary"
              />
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
```

**Règles Visuelles:**
- **Contact name:** Font 18px, Bold, Noir (#1a202c)
- **Billing client:** Font 12px, Italic, Gris (#718096)
- **Location:** Font 14px, Quartier en **Bold** (#2d3748)
- **Icons:** Taille "small" (20px), couleur "action" (gris neutre)

---

### 2. AppointmentDetailDrawer (Niveau 2)

**Responsabilité:** Détails complets avec infos confort + timeline.

**Anatomie:**
```
┌────────────────────────────────────────┐
│ M. Jean Tremblay                    ✕  │ ← Header + Close
│ ────────────────────────────────────── │
│                                        │
│ 👤 SUR PLACE                           │ ← Section 1: Contact
│ ────────────────────────────────────── │
│ 📞 514-555-1234                        │
│ 📍 4520 rue St-Denis                   │
│    Montréal H2G 2J8                    │
│                                        │
│ 🔑 Code: 1234#                         │ ← Security info
│ 🦴 Chien: Max (golden retriever)       │
│    Très gentil, laisser entrer         │
│                                        │
│ 🅿️  Stationnement: Rue, zone payante   │
│                                        │
│ ────────────────────────────────────── │
│                                        │
│ 💼 FACTURATION                         │ ← Section 2: Billing
│ ────────────────────────────────────── │
│ École de Musique XYZ                   │
│ Solde impayé: 450,00$                  │
│ Dernier paiement: 15 nov 2024          │
│                                        │
│ ────────────────────────────────────── │
│                                        │
│ 📖 HISTORIQUE                          │ ← Section 3: Timeline
│ ────────────────────────────────────── │
│ 15 nov 2024 • Accordage • par Nicolas  │
│ Piano en bon état, léger ajustement... │
│ 21°C • 45% humidité                    │
│                                        │
│ 10 mai 2024 • Accordage • par JP       │
│ Remplacement corde #3...               │
│                                        │
└────────────────────────────────────────┘
```

**Code React (Drawer):**
```tsx
// v6/frontend/src/components/AppointmentDetailDrawer.tsx
import { Drawer, Box, Typography, IconButton, Divider } from '@mui/material';
import { Close, InfoOutlined, Pets, VpnKey, LocalParking, Phone } from '@mui/icons-material';

interface AppointmentDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  appointment: AppointmentDetail | null;
  loading: boolean;
}

export function AppointmentDetailDrawer({
  open,
  onClose,
  appointment,
  loading
}: AppointmentDetailDrawerProps) {
  if (loading) {
    return (
      <Drawer anchor="bottom" open={open} onClose={onClose}>
        <Box p={3} textAlign="center">
          <CircularProgress />
          <Typography mt={2}>Chargement des détails...</Typography>
        </Box>
      </Drawer>
    );
  }

  if (!appointment) return null;

  const { overview, comfort, billing, timeline_summary, timeline_entries } = appointment;

  return (
    <Drawer
      anchor="bottom"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          maxHeight: '90vh',
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
        }
      }}
    >
      <Box p={3}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" mb={2}>
          <Typography variant="h5" fontWeight="bold">
            {overview.client_name}
          </Typography>
          <IconButton onClick={onClose}>
            <Close />
          </IconButton>
        </Box>

        {/* Section 1: Sur Place */}
        <SectionHeader icon={<InfoOutlined />} title="SUR PLACE" />

        {comfort.contact_phone && (
          <InfoRow icon={<Phone />} text={comfort.contact_phone} />
        )}

        <InfoRow
          icon={<LocationOn />}
          text={`${comfort.address}\n${comfort.city} ${comfort.postal_code}`}
        />

        {comfort.access_code && (
          <Box mb={1}>
            <Box display="flex" alignItems="center" gap={1}>
              <VpnKey fontSize="small" />
              <Typography
                component="span"
                sx={{
                  fontFamily: 'monospace',
                  color: '#dd6b20',
                  backgroundColor: '#fef5e7',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  fontWeight: 600,
                }}
              >
                Code: {comfort.access_code}
              </Typography>
            </Box>
          </Box>
        )}

        {comfort.dog_name && (
          <InfoRow
            icon={<Pets />}
            text={`Chien: ${comfort.dog_name}${comfort.dog_notes ? `\n${comfort.dog_notes}` : ''}`}
          />
        )}

        {comfort.parking_info && (
          <InfoRow icon={<LocalParking />} text={comfort.parking_info} />
        )}

        <Divider sx={{ my: 2 }} />

        {/* Section 2: Facturation (if different from contact) */}
        {billing && (
          <>
            <SectionHeader icon={<AccountBalance />} title="FACTURATION" />

            <Typography mb={1}>{billing.client_name}</Typography>

            {billing.balance_due && (
              <Typography variant="body2" color="error.main" mb={1}>
                Solde impayé: {billing.balance_due.toFixed(2)}$
              </Typography>
            )}

            {billing.last_payment_date && (
              <Typography variant="body2" color="text.secondary">
                Dernier paiement: {billing.last_payment_date}
              </Typography>
            )}

            <Divider sx={{ my: 2 }} />
          </>
        )}

        {/* Section 3: Historique */}
        <SectionHeader icon={<History />} title="HISTORIQUE" />

        <Typography variant="body2" sx={{ p: 1, bgcolor: 'blue.50', borderRadius: 1, mb: 2 }}>
          {timeline_summary}
        </Typography>

        {timeline_entries && timeline_entries.length > 0 && (
          <List dense>
            {timeline_entries.map((entry, i) => (
              <TimelineEntry key={i} entry={entry} />
            ))}
          </List>
        )}
      </Box>
    </Drawer>
  );
}

// Helper Components
function SectionHeader({ icon, title }: { icon: React.ReactNode, title: string }) {
  return (
    <Typography
      variant="subtitle2"
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        mb: 1,
        color: 'text.primary',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}
    >
      {icon}
      {title}
    </Typography>
  );
}

function InfoRow({ icon, text }: { icon: React.ReactNode, text: string }) {
  return (
    <Box display="flex" alignItems="flex-start" gap={1} mb={1}>
      {icon}
      <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
        {text}
      </Typography>
    </Box>
  );
}
```

**Règles Visuelles:**
- **Section Headers:** Font 14px, Bold, Uppercase, Gris foncé (#2d3748)
- **Codes d'accès:** Font monospace, Orange (#dd6b20), Background beige (#fef5e7)
- **Dividers:** Gris clair (#e2e8f0), margin 16px vertical
- **Timeline:** Police plus petite (12px), dates en bold

---

### 3. QuickActionChips

**Responsabilité:** Filtres rapides / actions fréquentes.

**Usage:**
```tsx
<Box display="flex" gap={1} mb={2} flexWrap="wrap">
  <Chip
    label="Aujourd'hui"
    onClick={() => handleQuickQuery("aujourd'hui")}
    color="primary"
    variant="outlined"
  />
  <Chip
    label="Demain"
    onClick={() => handleQuickQuery("demain")}
    color="primary"
    variant="outlined"
  />
  <Chip
    label="Cette semaine"
    onClick={() => handleQuickQuery("cette semaine")}
    color="primary"
    variant="outlined"
  />
</Box>
```

**Règles:**
- Toujours `variant="outlined"` (pas de background solide)
- Max 5 chips visibles (reste en "Voir plus")
- Mobile: wrap sur plusieurs lignes

---

## 📐 Layout Standards

### Page Structure

```tsx
// Standard page layout
<Box sx={{ p: 2, maxWidth: 800, mx: 'auto' }}>
  {/* Header */}
  <Typography variant="h4" gutterBottom fontWeight="bold">
    🎵 Ma Journée
  </Typography>

  {/* Quick Actions */}
  <Box mb={3}>
    <QuickActionChips />
  </Box>

  {/* Search Bar */}
  <SearchBar />

  {/* Overview Stats */}
  <OverviewStats />

  {/* Main Content (Cards) */}
  <Box>
    {appointments.map(apt => (
      <AppointmentCard key={apt.id} appointment={apt} onClick={...} />
    ))}
  </Box>

  {/* Empty State */}
  {appointments.length === 0 && <EmptyState />}
</Box>
```

**Règles:**
- **Max-width:** 800px (lisibilité optimale)
- **Padding:** 16px (mobile), 24px (desktop)
- **Margin auto:** Centre le contenu

---

## 🎭 States & Feedback

### Loading States

```tsx
// Skeleton Card (pendant chargement)
<Card sx={{ mb: 2 }}>
  <CardContent>
    <Skeleton variant="text" width="40%" height={32} />
    <Skeleton variant="text" width="80%" />
    <Skeleton variant="text" width="60%" />
    <Skeleton variant="rectangular" height={60} sx={{ mt: 1 }} />
  </CardContent>
</Card>

// Spinner centré
<Box textAlign="center" py={4}>
  <CircularProgress />
  <Typography mt={2} color="text.secondary">
    Chargement...
  </Typography>
</Box>
```

### Empty States

```tsx
<Box textAlign="center" py={4} color="text.secondary">
  <Piano sx={{ fontSize: 64, opacity: 0.3 }} />
  <Typography variant="h6" mt={2}>
    Aucun rendez-vous pour cette journée
  </Typography>
  <Typography variant="body2">
    Profitez de votre temps libre! 🎵
  </Typography>
</Box>
```

### Error States

```tsx
<Alert severity="error" sx={{ mb: 2 }}>
  <AlertTitle>Erreur de chargement</AlertTitle>
  Impossible de récupérer les rendez-vous. Vérifiez votre connexion.
  <Button size="small" onClick={retry} sx={{ mt: 1 }}>
    Réessayer
  </Button>
</Alert>
```

### Success Feedback

```tsx
// Toast notification (Snackbar)
<Snackbar
  open={showSuccess}
  autoHideDuration={3000}
  onClose={handleClose}
>
  <Alert severity="success">
    Rendez-vous modifié avec succès!
  </Alert>
</Snackbar>
```

---

## ♿ Accessibilité

### ARIA Labels

```tsx
<IconButton
  onClick={onClose}
  aria-label="Fermer les détails"
>
  <Close />
</IconButton>

<TextField
  label="Rechercher un rendez-vous"
  aria-describedby="search-helper-text"
/>
<FormHelperText id="search-helper-text">
  Ex: Demain, 30 décembre, Rosemont
</FormHelperText>
```

### Keyboard Navigation

```tsx
<Card
  tabIndex={0}
  onClick={handleClick}
  onKeyPress={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  }}
  sx={{
    cursor: 'pointer',
    '&:focus': {
      outline: '2px solid',
      outlineColor: 'primary.main',
      outlineOffset: '2px',
    }
  }}
>
  {/* Card content */}
</Card>
```

### Color Contrast

**Minimum Ratios (WCAG AA):**
- Text normal: 4.5:1
- Text large (18px+): 3:1
- UI components: 3:1

```css
/* ✅ BON - Contraste suffisant */
.card-title {
  color: #1a202c;  /* Noir sur blanc = 16:1 */
}

.secondary-text {
  color: #718096;  /* Gris sur blanc = 4.6:1 */
}

/* ❌ MAUVAIS - Contraste insuffisant */
.low-contrast {
  color: #cbd5e0;  /* Trop pâle = 1.8:1 */
}
```

---

## 🌐 Internationalisation

### Français Canadien (fr-CA)

**Formats:**
```tsx
// Dates
const formatDate = (date: Date) => {
  return date.toLocaleDateString('fr-CA', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  // "29 décembre 2025"
};

// Heures (24h format)
const formatTime = (time: string) => {
  // "12:00" (pas "12:00 PM")
  return time;
};

// Montants
const formatCurrency = (amount: number) => {
  return amount.toLocaleString('fr-CA', {
    style: 'currency',
    currency: 'CAD'
  });
  // "450,00 $" (virgule, espace avant $)
};
```

**Textes:**
```tsx
const MESSAGES = {
  today: "Aujourd'hui",
  tomorrow: "Demain",
  loading: "Chargement...",
  noAppointments: "Aucun rendez-vous",
  newClient: "Nouveau",
  billTo: "Facturer à",
  accessCode: "Code",
  dog: "Chien",
  parking: "Stationnement",
};
```

---

## 📊 Responsive Breakpoints

```css
/* Mobile First */
@media (min-width: 600px) {  /* Tablet */
  .card {
    padding: 24px;
  }
}

@media (min-width: 960px) {  /* Desktop */
  .container {
    max-width: 800px;
  }
}

@media (min-width: 1280px) {  /* Large Desktop */
  .container {
    max-width: 1200px;
  }
}
```

**MUI Breakpoints:**
```tsx
<Box
  sx={{
    p: { xs: 2, sm: 3, md: 4 },  // Padding responsive
    display: { xs: 'block', md: 'flex' },  // Layout change
  }}
>
```

---

## 🧪 Testing UX

### Visual Regression Tests

```typescript
// tests/visual/appointment-card.spec.ts
import { test, expect } from '@playwright/test';

test('AppointmentCard matches snapshot', async ({ page }) => {
  await page.goto('/chat');

  const card = page.locator('.appointment-card').first();
  await expect(card).toHaveScreenshot('appointment-card.png');
});

test('AppointmentCard hover state', async ({ page }) => {
  await page.goto('/chat');

  const card = page.locator('.appointment-card').first();
  await card.hover();

  await expect(card).toHaveScreenshot('appointment-card-hover.png');
});
```

### Accessibility Tests

```typescript
// tests/a11y/chat.spec.ts
import { test, expect } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';

test('Chat page is accessible', async ({ page }) => {
  await page.goto('/chat');
  await injectAxe(page);

  await checkA11y(page, null, {
    detailedReport: true,
    detailedReportOptions: {
      html: true,
    },
  });
});
```

---

## 🔗 Documents Liés

- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - Schéma données affichées
- [USER_ROLES_SECURITY.md](USER_ROLES_SECURITY.md) - Permissions UI
- [GEOGRAPHY_LOGIC.md](GEOGRAPHY_LOGIC.md) - Affichage quartiers

---

## 📝 Règles Critiques

### ✅ DO (À FAIRE)

1. **Toujours mobile-first**
   ```tsx
   // ✅ BON
   <Box sx={{ p: { xs: 2, md: 3 } }} />

   // ❌ MAUVAIS
   <Box sx={{ p: 3 }} />  // Trop grand sur mobile
   ```

2. **Toujours progressive disclosure**
   - Card: Info minimale
   - Drawer: Détails complets
   - Pas de "tout afficher" dès le début

3. **Toujours touch-friendly**
   - Boutons ≥ 48px
   - Espaces entre éléments cliquables

4. **Toujours accessible**
   - ARIA labels
   - Keyboard navigation
   - Contraste suffisant

### ❌ DON'T (À ÉVITER)

1. **Jamais de menu hamburger top-left**
   ```tsx
   // ❌ MAUVAIS (trop loin du pouce)
   <IconButton sx={{ position: 'absolute', top: 16, left: 16 }}>
     <Menu />
   </IconButton>

   // ✅ BON (bottom navigation)
   <BottomNavigation />
   ```

2. **Jamais d'overflow horizontal sur mobile**
   ```tsx
   // ❌ MAUVAIS
   <Box sx={{ width: '1200px' }} />

   // ✅ BON
   <Box sx={{ width: '100%', maxWidth: 800 }} />
   ```

3. **Jamais de texte < 14px sur mobile**
   ```tsx
   // ❌ MAUVAIS
   <Typography sx={{ fontSize: 12 }} />

   // ✅ BON
   <Typography variant="body2" sx={{ fontSize: { xs: 14, md: 12 } }} />
   ```

4. **Jamais d'actions sans feedback**
   ```tsx
   // ❌ MAUVAIS
   <Button onClick={handleSave}>Sauvegarder</Button>

   // ✅ BON
   <Button onClick={handleSave} disabled={saving}>
     {saving ? <CircularProgress size={24} /> : 'Sauvegarder'}
   </Button>
   ```

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après tests utilisateurs V6

**RAPPEL CRITIQUE:** Mobile-first, Progressive Disclosure, Touch-Friendly!
