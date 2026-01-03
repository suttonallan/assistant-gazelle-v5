# Fonctionnalités Critiques - Vincent d'Indy Dashboard

**Date de création**: 2026-01-02  
**But**: Documenter les fonctionnalités critiques à préserver lors des refactorisations

---

## 1. 📊 Push vers Gazelle avec Mesures d'Humidité et Notes de Service

### Vue d'ensemble

Le système permet de pousser automatiquement vers Gazelle :
- Les notes de service (travail effectué + observations)
- Les mesures d'humidité et température (parsing automatique)

### Flux technique

#### Frontend (`VincentDIndyDashboard.jsx`)

1. **Saisie des données par le technicien** :
   - Champ "Travail effectué" (`travail`)
   - Champ "Observations" (`observations`) - peut contenir humidité/température
   - Checkbox "Travail complété" (`is_work_completed`)

2. **Bouton "Envoyer à Gazelle"** :
   - Appelle `/api/vincent-dindy/push-to-gazelle`
   - Peut être déclenché pour des pianos individuels ou par tournée

#### Backend (`api/vincent_dindy.py`)

**Endpoint**: `POST /api/vincent-dindy/push-to-gazelle`

**Request Body**:
```json
{
  "piano_ids": ["ins_abc123", ...],  // Optional
  "tournee_id": "tournee_123",       // Optional
  "technician_id": "usr_xyz",        // Default: Nick
  "dry_run": false                   // Default: false
}
```

**Processus**:
1. Identifie les pianos prêts (status='completed', is_work_completed=true, sync_status IN ('pending', 'modified', 'error'))
2. Pour chaque piano, appelle `GazellePushService.push_piano_to_gazelle()`

#### Service de Push (`core/gazelle_push_service.py`)

**Méthode**: `push_piano_to_gazelle()`

**Fusion des notes**:
```python
note_parts = []
if a_faire:
    note_parts.append(f"📋 Note de Nick: {a_faire}")
if travail:
    note_parts.append(f"🔧 Travail effectué: {travail}")
if observations:
    note_parts.append(f"📝 Observations: {observations}")

service_note = "\n\n".join(note_parts) if note_parts else "Service effectué"
```

**Push vers Gazelle**:
- Appelle `api_client.push_technician_service_with_measurements()`
- Utilise la date de complétion (`completed_at`) au lieu de la date actuelle

#### Client API (`core/gazelle_api_client.py`)

**Méthode**: `push_technician_service_with_measurements()`

**Processus**:
1. Crée la note de service via `push_technician_service()`
2. Parse température/humidité via `parse_temperature_humidity()`
3. Crée une measurement si détectée via `create_piano_measurement()`

**Parsing automatique** (`parse_temperature_humidity()`):

Patterns détectés:
- Température: `(\d+)\s*(?:°\s*(?:Celsius|C)?|c(?:elsius)?(?:\s|\.|\b))`
  - Exemples: "24c.", "22°C", "24celsius"
- Humidité: `(?:humidité|humidity)[^0-9]*(\d+)\s*%` ou `(\d+)\s*%` (premier pourcentage trouvé)
  - Exemples: "humidité 34%", "humidity 45%", "34%"

Validation:
- Température: -20°C à 50°C
- Humidité: 0% à 100%
- Les deux valeurs doivent être présentes pour créer une measurement

**Fichiers critiques**:
- `api/vincent_dindy.py` : Endpoints push-to-gazelle
- `core/gazelle_push_service.py` : Logique de push batch
- `core/gazelle_api_client.py` : `push_technician_service_with_measurements()`, `parse_temperature_humidity()`, `create_piano_measurement()`
- `frontend/src/components/VincentDIndyDashboard.jsx` : Interface utilisateur, bouton push

---

## 2. 🎹 Gestion des Tournées

### Vue d'ensemble

Système de gestion des tournées permettant d'organiser les pianos à accorder, avec création, activation, terminaison et push par tournée.

### Architecture

#### Stockage

**localStorage** (`tournees_accords`):
```json
[
  {
    "id": "tournee_123",
    "nom": "Tournée Orford - Janvier 2026",
    "date_debut": "2026-01-15",
    "date_fin": "2026-01-20",
    "status": "planifiee" | "en_cours" | "terminee",
    "piano_ids": ["ins_abc123", "ins_def456", ...],  // IDs Gazelle uniquement
    "technicien_assigne": "Nicolas"
  },
  ...
]
```

**Important**: Les `piano_ids` stockent UNIQUEMENT les `gazelleId`, pas les IDs Supabase.

#### Frontend (`VincentDIndyDashboard.jsx`)

**États**:
- `tournees`: Liste des tournées depuis localStorage
- `selectedTourneeId`: Tournée actuellement sélectionnée
- `newTournee`: État pour formulaire de création

**Fonctions clés**:

1. **`loadTournees()`**:
   - Charge depuis localStorage
   - Met à jour l'état `tournees`

2. **`getTourneePianos(tourneeId)`**:
   - Retourne les `piano_ids` d'une tournée
   - Utilisé pour filtrer l'affichage

3. **`isPianoInTournee(piano, tourneeId)`**:
   - Vérifie si un piano est dans une tournée
   - **Utilise UNIQUEMENT `piano.gazelleId` ou `piano.id`**
   - Ne pas utiliser `piano.piano_id` (ID Supabase)

4. **`getPianoUniqueId(piano)`**:
   - Retourne `piano.gazelleId` (UNIQUEMENT)
   - Utilisé pour associer un piano à une tournée

5. **`handleAddPianoToTournee(piano)`**:
   - Ajoute un piano à la tournée sélectionnée
   - Utilise `getPianoUniqueId()` pour obtenir le gazelleId
   - Met à jour localStorage

6. **`handleRemovePianoFromTournee(piano)`**:
   - Retire un piano d'une tournée
   - Met à jour localStorage

7. **`handleCreateTournee()`**:
   - Crée une nouvelle tournée
   - Initialise `piano_ids: []`
   - Status: `planifiee`

8. **`handleActiverTournee(tourneeId)`**:
   - Change le status à `en_cours`

9. **`handleConclureTournee(tourneeId)`**:
   - Change le status à `terminee`

10. **`handleDeleteTournee(tourneeId)`**:
    - Supprime une tournée

**Interface utilisateur**:

- **Sidebar gauche** (vue Nicolas uniquement):
  - Formulaire de création de tournée
  - Liste des tournées avec:
    - Nom, date, nombre de pianos
    - Status (○ planifiée, ▶ en cours, ✓ terminée)
    - Actions: Activer, Terminer, Supprimer
    - Assignation technicien

- **Filtrage**:
  - Bouton "Pianos de cette tournée" : Affiche uniquement les pianos de la tournée sélectionnée
  - Utilise `showOnlySelected` + `selectedTourneeId`

- **Push par tournée**:
  - Le bouton "Envoyer à Gazelle" peut être utilisé avec `tournee_id`
  - Push tous les pianos complétés de la tournée

#### Backend

**Endpoint**: `POST /api/vincent-dindy/push-to-gazelle`

**Paramètre**: `tournee_id` (optionnel)
- Si fourni, filtre les pianos par tournée avant le push
- Le filtrage exact est géré côté backend via `get_pianos_ready_for_push(tournee_id)`

**Fichiers critiques**:
- `frontend/src/components/VincentDIndyDashboard.jsx` : Toute la logique de gestion des tournées
- `api/vincent_dindy.py` : Support `tournee_id` dans push-to-gazelle
- `core/gazelle_push_service.py` : Méthode `get_pianos_ready_for_push(tournee_id)`

---

## ⚠️ Points Critiques à Préserver

### 1. Parsing Humidité/Température

- **NE PAS modifier** les patterns regex dans `parse_temperature_humidity()`
- Les patterns sont testés et fonctionnent avec les formats réels utilisés par les techniciens
- La validation des plages (-20 à 50°C, 0 à 100%) est importante

### 2. Identification des Pianos dans les Tournées

- **CRITIQUE**: Utiliser UNIQUEMENT `gazelleId` pour identifier les pianos dans les tournées
- **NE PAS** utiliser `piano_id` (ID Supabase) car il change lors des syncs
- La fonction `getPianoUniqueId()` doit toujours retourner `piano.gazelleId`

### 3. Fusion des Notes

- L'ordre de fusion est important:
  1. Note de Nick (`a_faire`)
  2. Travail effectué (`travail`)
  3. Observations (`observations`)
- Les emojis (📋, 🔧, 📝) aident à la lisibilité dans Gazelle

### 4. Date de Complétion

- Utiliser `completed_at` (date de complétion) au lieu de `now()` pour l'événement Gazelle
- Permet de conserver l'historique correct dans Gazelle même si le push est fait plus tard

### 5. Statuts de Sync

- `sync_status` peut être: `pending`, `pushed`, `modified`, `error`
- Un piano est "prêt pour push" si:
  - `status = 'completed'`
  - `is_work_completed = true`
  - `sync_status IN ('pending', 'modified', 'error')`
  - `travail IS NOT NULL OR observations IS NOT NULL`

---

## 🔍 Tests à Effectuer Après Refactorisation

1. **Test Push avec Humidité**:
   - Saisir "24c. 34%" dans observations
   - Cocher "Travail complété"
   - Push vers Gazelle
   - Vérifier que la measurement est créée dans Gazelle

2. **Test Tournée**:
   - Créer une tournée
   - Ajouter des pianos (vérifier que les gazelleId sont stockés)
   - Sélectionner la tournée
   - Vérifier que seuls les pianos de la tournée s'affichent
   - Push par tournée et vérifier que seuls les pianos de la tournée sont pushés

3. **Test Fusion Notes**:
   - Ajouter "À faire" (Nick)
   - Ajouter "Travail effectué" (technicien)
   - Ajouter "Observations" (technicien)
   - Push et vérifier que les 3 sections apparaissent dans Gazelle

