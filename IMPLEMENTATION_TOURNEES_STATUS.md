# Implémentation: Système de Gestion d'États pour Tournées Vincent d'Indy

## 📋 Résumé

Ce document récapitule l'implémentation du système de gestion d'états (Blanc → Jaune/Ambre → Bleu → Vert) avec push intelligent vers Gazelle.

**Date:** 2026-01-02
**Version:** 1.0

---

## ✅ Backend: Implémenté

### 1. Migration Base de Données

**Fichier:** [`refactor/vdi/sql/011_add_sync_tracking.sql`](refactor/vdi/sql/011_add_sync_tracking.sql)

**Nouveaux champs ajoutés à `vincent_dindy_piano_updates`:**
- `is_work_completed` (BOOLEAN): Checkbox "Travail complété"
- `sync_status` (TEXT): État sync avec Gazelle (`pending`, `pushed`, `modified`, `error`)
- `last_sync_at` (TIMESTAMPTZ): Date du dernier push réussi
- `sync_error` (TEXT): Message d'erreur si échec push
- `gazelle_event_id` (TEXT): ID événement Gazelle créé

**Contrainte status mise à jour:**
```sql
CHECK (status IN ('normal', 'proposed', 'top', 'work_in_progress', 'completed'))
```

**Fonctions PostgreSQL créées:**
- `get_pianos_ready_for_push(tournee_id, limit)`: Récupère pianos prêts
- `mark_piano_as_pushed(piano_id, event_id)`: Marque piano comme pushé
- `mark_piano_push_error(piano_id, error)`: Marque piano avec erreur
- `auto_mark_sync_modified()`: TRIGGER auto-marque `modified` si piano pushé est modifié

**Index pour performance:**
- `idx_piano_updates_sync_status` sur `sync_status`
- `idx_piano_updates_work_completed` sur `is_work_completed`
- `idx_piano_updates_completed_ready_for_push` (composite)

### 2. Service de Push Intelligent

**Fichier:** [`core/gazelle_push_service.py`](core/gazelle_push_service.py)

**Classe:** `GazellePushService`

**Méthodes:**
- `get_pianos_ready_for_push()`: Filtre pianos éligibles
- `push_piano_to_gazelle()`: Push un piano avec retry logic
- `push_batch()`: Push multiple pianos en batch
- `schedule_daily_push()`: Push automatique quotidien

**Fonctionnalités:**
- ✅ Utilise `push_technician_service_with_measurements` (service note + measurements auto)
- ✅ Parse température/humidité automatiquement
- ✅ Retry logic avec backoff exponentiel (3 tentatives, 1s/2s/4s)
- ✅ Mise à jour sync_status dans Supabase
- ✅ Gestion d'erreurs granulaire (un échec ne bloque pas les autres)

### 3. Script Scheduled

**Fichier:** [`scripts/scheduled_push_to_gazelle.py`](scripts/scheduled_push_to_gazelle.py)

**Usage:**
```bash
# Configuration cron (01:00 chaque jour)
0 1 * * * /usr/bin/python3 /path/to/scripts/scheduled_push_to_gazelle.py
```

**Comportement:**
- Push automatique de tous les pianos prêts (toutes tournées)
- Logs dans `/var/log/gazelle_push.log`
- Exit code 0 si succès, 1 si erreurs

### 4. API Endpoints

**Fichier:** [`api/vincent_dindy.py`](api/vincent_dindy.py)

#### POST `/vincent-dindy/push-to-gazelle`

**Push manuel de pianos vers Gazelle.**

**Body:**
```json
{
  "piano_ids": ["ins_abc123", "ins_def456"],  // Optional
  "tournee_id": "tournee_123",                 // Optional
  "technician_id": "usr_HcCiFk7o0vZ9xAI0",    // Default: Nick
  "dry_run": false                             // Default: false
}
```

**Response:**
```json
{
  "success": true,
  "pushed_count": 5,
  "error_count": 1,
  "total_pianos": 6,
  "results": [
    {
      "status": "success",
      "piano_id": "ins_abc123",
      "gazelle_event_id": "evt_xyz789",
      "measurement_created": true,
      "parsed_values": {"temperature": 22, "humidity": 45}
    },
    {
      "status": "error",
      "piano_id": "ins_def456",
      "error": "Client ID not found"
    }
  ],
  "summary": "5/6 pianos pushés avec succès, 1 erreur"
}
```

#### GET `/vincent-dindy/pianos-ready-for-push`

**Récupère pianos prêts pour push.**

**Query params:**
- `tournee_id` (optional): Filtrer par tournée
- `limit` (optional): Max pianos (défaut: 100)

**Response:**
```json
{
  "pianos": [
    {
      "piano_id": "ins_abc123",
      "travail": "Piano accordé, cordes changées",
      "observations": "Température 22°C, humidité 45%",
      "completed_in_tournee_id": "tournee_123",
      "sync_status": "pending",
      "updated_at": "2026-01-02T10:30:00Z"
    }
  ],
  "count": 1,
  "ready_for_push": true
}
```

#### PUT `/vincent-dindy/pianos/{piano_id}`

**Mise à jour piano avec nouveaux champs.**

**Nouveaux champs acceptés:**
- `isWorkCompleted` (boolean): Checkbox "Travail complété"
- `isHidden` (boolean): Masquer complètement le piano

**Logique de transition automatique:**
```python
# Si travail/observations remplis ET is_work_completed = false → work_in_progress
if (travail or observations) and not is_work_completed:
    status = 'work_in_progress'

# Si is_work_completed = true → completed
if is_work_completed:
    status = 'completed'
```

---

## ⏳ Frontend: À Implémenter

### 1. Checkbox "Travail complété"

**Fichier:** `frontend/src/components/VincentDIndyDashboard.jsx`

**Emplacement:** Dans formulaire technicien (vue expanded)

**Code à ajouter:**
```jsx
// État local
const [isWorkCompleted, setIsWorkCompleted] = useState(false);

// Dans le formulaire
<div className="flex items-center gap-2 mt-4">
  <input
    type="checkbox"
    id={`completed-${piano.gazelleId}`}
    checked={isWorkCompleted}
    onChange={(e) => setIsWorkCompleted(e.target.checked)}
    className="w-4 h-4"
  />
  <label htmlFor={`completed-${piano.gazelleId}`} className="font-medium">
    ✅ Travail complété (prêt pour Gazelle)
  </label>
</div>

// Dans handleSave
await updatePiano(piano.gazelleId, {
  travail: travailInput,
  observations: observationsInput,
  isWorkCompleted: isWorkCompleted,  // NOUVEAU
  updated_by: currentUser
});
```

### 2. Mise à Jour Logique Couleur

**Fonction `getRowClass()` à modifier:**

```javascript
const getRowClass = (piano) => {
  const updates = piano.updates || {};
  const { status, is_work_completed, sync_status } = updates;

  // Priorité 1: Sélection (mauve)
  if (selectedIds.has(piano.gazelleId)) {
    return 'bg-purple-100';
  }

  // Priorité 2: Haute priorité (ambre)
  if (status === 'top') {
    return 'bg-amber-200';
  }

  // Priorité 3: Travail complété (vert)
  if (status === 'completed' && is_work_completed) {
    return 'bg-green-200';
  }

  // Priorité 4: Travail en cours (bleu) -- NOUVEAU
  if (status === 'work_in_progress' ||
      ((updates.travail || updates.observations) && !is_work_completed)) {
    return 'bg-blue-200';
  }

  // Priorité 5: Proposé ou à faire (jaune)
  if (status === 'proposed' || updates.a_faire) {
    return 'bg-yellow-200';
  }

  // Défaut: Blanc
  return 'bg-white';
};
```

### 3. Bouton "Envoyer à Gazelle"

**Emplacement:** Dans toolbar batch operations (vue Nicolas)

**Code à ajouter:**
```jsx
// État local
const [readyForPushCount, setReadyForPushCount] = useState(0);
const [pushInProgress, setPushInProgress] = useState(false);

// Charger compteur pianos prêts
useEffect(() => {
  const loadReadyCount = async () => {
    try {
      const response = await fetch(`${API_URL}/vincent-dindy/pianos-ready-for-push`);
      const data = await response.json();
      setReadyForPushCount(data.count);
    } catch (err) {
      console.error('Erreur chargement pianos prêts:', err);
    }
  };

  loadReadyCount();
}, [pianos]); // Recharger quand pianos change

// Fonction push
const handlePushToGazelle = async () => {
  if (!confirm(`Envoyer ${readyForPushCount} pianos vers Gazelle?`)) {
    return;
  }

  setPushInProgress(true);

  try {
    const response = await fetch(`${API_URL}/vincent-dindy/push-to-gazelle`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        tournee_id: selectedTourneeId, // Optional: filtre par tournée
        technician_id: 'usr_HcCiFk7o0vZ9xAI0',
        dry_run: false
      })
    });

    const result = await response.json();

    if (result.success) {
      alert(`✅ ${result.pushed_count}/${result.total_pianos} pianos envoyés avec succès!`);
      loadPianosFromAPI(); // Recharger pour mettre à jour sync_status
    } else {
      alert(`⚠️  ${result.pushed_count}/${result.total_pianos} pianos envoyés, ${result.error_count} erreurs.\n\nVoir console pour détails.`);
      console.error('Erreurs push:', result.results.filter(r => r.status === 'error'));
    }
  } catch (err) {
    alert(`❌ Erreur lors du push: ${err.message}`);
    console.error(err);
  } finally {
    setPushInProgress(false);
  }
};

// Dans JSX toolbar
<button
  onClick={handlePushToGazelle}
  className="bg-green-600 text-white px-4 py-2 rounded disabled:opacity-50"
  disabled={readyForPushCount === 0 || pushInProgress}
>
  {pushInProgress ? (
    '⏳ Envoi en cours...'
  ) : (
    `📤 Envoyer à Gazelle (${readyForPushCount})`
  )}
</button>
```

### 4. Indicateur Sync Status

**Affichage icône sync status dans liste pianos:**

```jsx
// Fonction helper
const getSyncStatusIcon = (syncStatus) => {
  switch (syncStatus) {
    case 'pending': return '⏳';
    case 'pushed': return '✅';
    case 'modified': return '🔄';
    case 'error': return '⚠️';
    default: return '';
  }
};

// Dans cellule tableau
<td>
  {piano.updates?.sync_status && (
    <span title={`Sync: ${piano.updates.sync_status}`}>
      {getSyncStatusIcon(piano.updates.sync_status)}
    </span>
  )}
  {piano.serialNumber}
</td>
```

---

## 🔧 Configuration Déploiement

### 1. Exécuter Migration SQL

```bash
# Supabase Web UI → SQL Editor
# Copier/coller contenu de refactor/vdi/sql/011_add_sync_tracking.sql
# Exécuter
```

### 2. Setup Cron Job

```bash
# Ouvrir crontab
crontab -e

# Ajouter ligne
0 1 * * * /usr/bin/python3 /path/to/scripts/scheduled_push_to_gazelle.py >> /var/log/gazelle_cron.log 2>&1

# Sauvegarder et quitter
```

### 3. Créer Fichier Log

```bash
sudo touch /var/log/gazelle_push.log
sudo chmod 666 /var/log/gazelle_push.log
```

### 4. Tester Push Manuel

```bash
# Dry run
python3 core/gazelle_push_service.py --dry-run

# Push réel (pianos de tournée spécifique)
python3 core/gazelle_push_service.py --tournee-id tournee_123

# Push scheduled (cron simulation)
python3 scripts/scheduled_push_to_gazelle.py
```

---

## 📊 Diagramme de Flux

```
┌─────────────────┐
│ Technicien UI   │
└────────┬────────┘
         │ 1. Saisit travail/observations
         │ 2. Coche "Travail complété"
         ▼
┌─────────────────┐
│ API PUT /pianos │
│ /piano_id       │
└────────┬────────┘
         │ 3. Auto-transition: work_in_progress → completed
         │ 4. sync_status = pending
         ▼
┌─────────────────┐
│ Supabase        │
│ piano_updates   │
└────────┬────────┘
         │
         ├──► 5a. Push MANUEL (gestionnaire clique bouton)
         │         ▼
         │    ┌──────────────────────────┐
         │    │ POST /push-to-gazelle    │
         │    └──────────┬───────────────┘
         │               │
         └──► 5b. Push AUTO (cron 01:00)
                  │      ▼
                  │ ┌─────────────────────────┐
                  │ │ scheduled_push_to       │
                  │ │ _gazelle.py             │
                  │ └──────────┬──────────────┘
                  │            │
                  ▼            ▼
         ┌──────────────────────────┐
         │ GazellePushService       │
         │ .push_batch()            │
         └──────────┬───────────────┘
                    │ 6. get_pianos_ready_for_push()
                    │    (status=completed, is_work_completed=true, sync_status∈{pending,modified,error})
                    ▼
         ┌──────────────────────────┐
         │ Pour chaque piano:       │
         │                          │
         │ 7. push_technician_      │
         │    service_with_         │
         │    measurements()        │
         │                          │
         │ 8. Parse temp/humidity   │
         │                          │
         │ 9. Create measurement    │
         │    si détecté            │
         └──────────┬───────────────┘
                    │ 10. Succès → mark_piano_as_pushed()
                    │     Erreur → mark_piano_push_error()
                    ▼
         ┌──────────────────────────┐
         │ Gazelle API              │
         │ - Service note créé      │
         │ - Measurement créé (opt) │
         │ - Event ID retourné      │
         └──────────┬───────────────┘
                    │ 11. Mise à jour Supabase:
                    │     sync_status = pushed
                    │     gazelle_event_id = evt_xxx
                    │     last_sync_at = NOW()
                    ▼
         ┌──────────────────────────┐
         │ UI: Icône ✅ affichée    │
         │ Piano reste vert         │
         └──────────────────────────┘
```

---

## 🧪 Tests

### Test 1: Transition États

```bash
# 1. État initial (blanc)
curl -X PUT http://localhost:8000/vincent-dindy/pianos/ins_test123 \
  -H "Content-Type: application/json" \
  -d '{"status": "normal"}'

# 2. Saisir note sans checkbox (bleu)
curl -X PUT http://localhost:8000/vincent-dindy/pianos/ins_test123 \
  -H "Content-Type: application/json" \
  -d '{"travail": "Piano accordé", "isWorkCompleted": false}'

# Vérifier: status devrait être "work_in_progress"

# 3. Cocher checkbox (vert)
curl -X PUT http://localhost:8000/vincent-dindy/pianos/ins_test123 \
  -H "Content-Type: application/json" \
  -d '{"isWorkCompleted": true}'

# Vérifier: status devrait être "completed", sync_status = "pending"
```

### Test 2: Push Manuel

```bash
# 1. Lister pianos prêts
curl http://localhost:8000/vincent-dindy/pianos-ready-for-push

# 2. Push dry-run
curl -X POST http://localhost:8000/vincent-dindy/push-to-gazelle \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# 3. Push réel
curl -X POST http://localhost:8000/vincent-dindy/push-to-gazelle \
  -H "Content-Type: application/json" \
  -d '{
    "piano_ids": ["ins_test123"],
    "technician_id": "usr_HcCiFk7o0vZ9xAI0"
  }'

# Vérifier dans Gazelle:
# - Événement créé (evt_xxx)
# - Note de service visible
# - Measurement créé si temp/humidity détecté
```

### Test 3: Auto-mark Modified

```bash
# 1. Push piano
curl -X POST http://localhost:8000/vincent-dindy/push-to-gazelle \
  -H "Content-Type: application/json" \
  -d '{"piano_ids": ["ins_test123"]}'

# Vérifier: sync_status = "pushed"

# 2. Modifier piano
curl -X PUT http://localhost:8000/vincent-dindy/pianos/ins_test123 \
  -H "Content-Type: application/json" \
  -d '{"observations": "Nouvelle observation"}'

# Vérifier: sync_status devrait être "modified" (via trigger SQL)
```

---

## 📝 Documentation Utilisateur

### Guide Gestionnaire (Nicolas)

**Workflow quotidien:**

1. **Définir priorités**
   - Cliquer status → Jaune (standard) ou Ambre (urgent)
   - Remplir colonne "À faire" avec instructions

2. **Suivre progression**
   - **Blanc** = Pas encore traité
   - **Jaune** = Standard, en attente technicien
   - **Ambre** = Urgent, haute priorité
   - **Bleu** = Technicien a commencé, note saisie
   - **Vert** = Travail terminé, prêt pour Gazelle

3. **Envoyer à Gazelle**
   - Bouton "📤 Envoyer à Gazelle (X)" apparaît si pianos verts
   - Cliquer pour push manuel
   - Vérifier icônes:
     - ⏳ = En attente push
     - ✅ = Envoyé avec succès
     - 🔄 = Modifié après push, nécessite re-push
     - ⚠️ = Erreur lors push

### Guide Technicien

**Workflow terrain:**

1. **Voir tâches**
   - Filtre "À faire" affiche pianos jaunes/ambre
   - Pianos triés par priorité (ambre en premier)

2. **Travailler piano**
   - Cliquer piano pour développer
   - Remplir "Travail effectué"
   - Remplir "Observations" (inclure temp/humidity si possible: "22°C, 45%")

3. **Marquer progression**
   - **NE PAS cocher** "Travail complété" si travail partiel
   - Piano devient **bleu** dès que note saisie
   - **COCHER** "Travail complété" uniquement si vraiment fini
   - Piano devient **vert** quand checkbox cochée

4. **Astuces**
   - Format température/humidité: "22°C, 45%" ou "22c. 45%"
   - Données parsées automatiquement et envoyées à Gazelle
   - Checkbox peut être cochée/décochée plusieurs fois

---

## 🚀 Prochaines Étapes

### Phase 1: Frontend (À faire maintenant)
- [ ] Implémenter checkbox "Travail complété"
- [ ] Mettre à jour logique couleur (bleu)
- [ ] Ajouter bouton "Envoyer à Gazelle"
- [ ] Afficher indicateurs sync_status

### Phase 2: Tests & Validation
- [ ] Tester transition états UI
- [ ] Tester push manuel (1-2 pianos)
- [ ] Vérifier événements créés dans Gazelle
- [ ] Valider parsing température/humidité

### Phase 3: Déploiement
- [ ] Exécuter migration SQL en production
- [ ] Setup cron job serveur
- [ ] Surveiller logs pendant 1 semaine
- [ ] Former utilisateurs (Nicolas + techniciens)

### Phase 4: Optimisations Futures
- [ ] Table `piano_tournee_status` pour historique complet
- [ ] Email notifications si erreurs push
- [ ] Dashboard analytics (pianos pushés/jour)
- [ ] Export rapport mensuel vers Excel

---

## 🔗 Fichiers Modifiés

### Backend
1. ✅ `refactor/vdi/sql/011_add_sync_tracking.sql` (NOUVEAU)
2. ✅ `core/gazelle_push_service.py` (NOUVEAU)
3. ✅ `scripts/scheduled_push_to_gazelle.py` (NOUVEAU)
4. ✅ `api/vincent_dindy.py` (MODIFIÉ - +2 endpoints, +logique transition)

### Frontend (À faire)
5. ⏳ `frontend/src/components/VincentDIndyDashboard.jsx`

### Documentation
6. ✅ `SPECIFICATION_TOURNEES_ETATS.md` (NOUVEAU)
7. ✅ `IMPLEMENTATION_TOURNEES_STATUS.md` (CE FICHIER)

---

## 📞 Support

**Questions/Problèmes:**
- Backend: Vérifier logs dans `/var/log/gazelle_push.log`
- Frontend: Console browser DevTools
- Supabase: Table `vincent_dindy_piano_updates`, colonnes `sync_status` et `sync_error`
- Gazelle: Vérifier événements créés via API ou UI

**Contact:** Allan Sutton
