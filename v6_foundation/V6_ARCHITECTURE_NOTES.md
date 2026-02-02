# Notes pour l'Architecture V6

## Gestion des Roles Utilisateurs

### Probleme actuel (V5)
- Les alertes sont envoyees a tous les utilisateurs assignes dans Gazelle
- Pas de distinction entre technicien, assistant, admin
- Louise (assistante) recoit des alertes destinees aux techniciens

### Solution V6
- Utiliser un systeme de roles coherent pour filtrer les alertes
- Champs suggeres dans la table `users`:
  - `role`: enum ('admin', 'technicien', 'assistant')
  - `is_technicien`: boolean (recoit alertes RV)
  - `is_assistant`: boolean (recoit relances Louise)
  - `receives_rv_alerts`: boolean (opt-in/opt-out explicite)

### Cas d'usage des alertes par role
| Type d'alerte | Admin | Technicien | Assistant |
|---------------|-------|------------|-----------|
| RV non confirme | Non | Oui | Non |
| Late Assignment | Non | Oui | Non |
| Relance vieux RV | Non | Non | Oui |
| Humidite critique | Oui | Oui | Non |

### Implementation suggeree
```python
# V6: Filtrer par role au lieu de GAZELLE_IDS hardcode
def get_technicians_for_alerts():
    """Retourne uniquement les utilisateurs avec role technicien."""
    return users.filter(
        is_technicien=True,
        receives_rv_alerts=True
    )
```

---

## Autres notes V6

### Inventaire
- Simplifier la cle unique: `(code_produit, technicien)` seulement
- Enlever `emplacement` completement
- Normalisation automatique des noms (Nick -> Nicolas)

### Institutions
- Table `institutions` avec discovery automatique depuis Gazelle
- Detection par mots-cles dans titre/location/description
- Support pour Vincent-d'Indy, Place des Arts, Orford, etc.

---

## Gestion Centralisee des Dates (PRIORITE HAUTE)

### Probleme actuel (V5)
- **~80 references** a `new Date()` dispersees dans **20+ composants**
- Aucun module centralise pour le frontend
- Bug recurrent: `new Date("2026-02-02")` interprete comme UTC → affiche la veille en EST
- Pattern correct (`+ 'T00:00:00'`) applique au cas par cas

### Composants affectes
| Composant | Nb refs | Problemes potentiels |
|-----------|---------|---------------------|
| MaJournee.jsx | 9 | Corrige (T00:00:00) |
| PlaceDesArtsDashboard.jsx | 10 | A verifier |
| VincentDIndyDashboard.jsx | 7 | A verifier |
| OrfordDashboard.jsx | 7 | A verifier |
| SyncDashboard.jsx | 7 | A verifier |
| LouiseDashboard.jsx | 4 | A verifier |
| JeanPhilippeDashboard.jsx | 4 | A verifier |
| TableauDeBord.jsx | 4 | A verifier |
| AlertesRV.jsx | 3 | A verifier |
| KilometersCalculator.jsx | 3 | A verifier |
| Autres (10+) | ~20 | A verifier |

### Solution V6: Creer `frontend/src/utils/dateUtils.js`

```javascript
/**
 * Utilitaires de dates centralises - America/Montreal
 * TOUJOURS utiliser ces fonctions au lieu de new Date() directement
 */

// Parser une date string (YYYY-MM-DD) en heure LOCALE (pas UTC)
export const parseLocalDate = (dateStr) => {
  if (!dateStr) return null
  return new Date(dateStr + 'T00:00:00')
}

// Obtenir aujourd'hui en format YYYY-MM-DD
export const getTodayLocal = () => {
  const now = new Date()
  return now.toLocaleDateString('en-CA') // Format YYYY-MM-DD
}

// Formater pour affichage francais (ex: "lundi 2 fevrier")
export const formatDateFR = (dateStr, options = {}) => {
  const date = parseLocalDate(dateStr)
  if (!date) return 'N/A'
  const defaultOpts = { weekday: 'long', day: 'numeric', month: 'long' }
  return date.toLocaleDateString('fr-CA', { ...defaultOpts, ...options })
}

// Formater date+heure depuis ISO string (ex: "2 fev 14:30")
export const formatDateTimeFR = (isoString) => {
  if (!isoString) return 'N/A'
  const date = new Date(isoString)
  return date.toLocaleDateString('fr-CA', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
  })
}

// Calculer difference en jours
export const daysDiff = (dateStr1, dateStr2 = null) => {
  const d1 = parseLocalDate(dateStr1)
  const d2 = dateStr2 ? parseLocalDate(dateStr2) : new Date()
  return Math.ceil((d2 - d1) / (1000 * 60 * 60 * 24))
}

// Ajouter/soustraire jours
export const addDays = (dateStr, days) => {
  const date = parseLocalDate(dateStr)
  date.setDate(date.getDate() + days)
  return date.toLocaleDateString('en-CA')
}
```

### Migration V6: Etapes
1. Creer `frontend/src/utils/dateUtils.js` avec les fonctions ci-dessus
2. Migrer composant par composant:
   - Remplacer `new Date(dateStr)` → `parseLocalDate(dateStr)`
   - Remplacer `new Date().toISOString().split('T')[0]` → `getTodayLocal()`
   - Remplacer `date.toLocaleDateString('fr-CA', ...)` → `formatDateFR(dateStr, ...)`
3. Tester chaque composant apres migration
4. Supprimer les patterns ad-hoc (`+ 'T00:00:00'`)

### Backend (deja OK)
- `core/timezone_utils.py` existe et fonctionne
- Utilise `MONTREAL_TZ = pytz.timezone('America/Montreal')`
- Fonctions: `parse_gazelle_datetime`, `format_for_supabase`, `extract_date_time`

---
*Derniere mise a jour: 2026-02-02*
