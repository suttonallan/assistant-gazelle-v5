# Spécification: Système de Gestion d'États pour Tournées Vincent d'Indy

## Vue d'ensemble

Ce document spécifie l'implémentation du système de gestion d'états pour les tournées Vincent d'Indy avec push intelligent vers Gazelle.

## 1. Gestion des États & Couleurs

### 1.1 États et Transitions

```
BLANC (normal/idle)
  ↓ [Gestionnaire définit priorité]
JAUNE (proposed - Standard) OU AMBRE (top - Haute priorité)
  ↓ [Technicien saisit note sans cocher "Travail complété"]
BLEU (work_in_progress - Information partagée)
  ↓ [Technicien coche "Travail complété"]
VERT (completed - Prêt pour Gazelle)
```

### 1.2 Mapping États → Couleurs UI

| État (`status`) | Couleur UI | CSS Class | Description |
|-----------------|------------|-----------|-------------|
| `normal` | Blanc | `bg-white` | État initial, aucune action |
| `proposed` | Jaune | `bg-yellow-200` | Priorité standard définie par gestionnaire |
| `top` | Ambre | `bg-amber-200` | Haute priorité (urgent) |
| `work_in_progress` | Bleu | `bg-blue-200` | Travail débuté, note saisie, non terminé |
| `completed` | Vert | `bg-green-200` | Travail terminé, prêt pour sync Gazelle |

### 1.3 Logique de Transition

**Règles:**
1. **Blanc → Jaune/Ambre**: Gestionnaire définit priorité via dropdown ou clic
2. **Jaune/Ambre → Bleu**: Technicien saisit `travail` OU `observations` SANS cocher "Travail complété"
3. **Bleu → Vert**: Technicien coche checkbox "Travail complété" (`is_work_completed = true`)
4. **Vert → Blanc**: Reset manuel ou après push Gazelle réussi

**Conditions:**
- Bleu uniquement si: `(travail IS NOT NULL OR observations IS NOT NULL) AND is_work_completed = false`
- Vert uniquement si: `status = 'completed' AND completed_in_tournee_id = active_tournee_id`

## 2. Modifications du Schéma de Base de Données

### 2.1 Table `vincent_dindy_piano_updates`

**Nouveaux champs à ajouter:**

```sql
ALTER TABLE public.vincent_dindy_piano_updates
ADD COLUMN IF NOT EXISTS is_work_completed BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS sync_status TEXT CHECK (sync_status IN ('pending', 'pushed', 'modified', 'error')) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_error TEXT,
ADD COLUMN IF NOT EXISTS gazelle_event_id TEXT;  -- ID de l'événement créé dans Gazelle

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_piano_updates_sync_status
  ON public.vincent_dindy_piano_updates(sync_status);

CREATE INDEX IF NOT EXISTS idx_piano_updates_work_completed
  ON public.vincent_dindy_piano_updates(is_work_completed);
```

**Description des nouveaux champs:**

- `is_work_completed`: Checkbox "Travail complété" cochée ou non
- `sync_status`: État de synchronisation avec Gazelle
  - `pending`: Jamais envoyé à Gazelle, en attente
  - `pushed`: Envoyé avec succès à Gazelle
  - `modified`: Modifié après push, nécessite re-sync
  - `error`: Erreur lors du dernier push
- `last_sync_at`: Timestamp du dernier push réussi
- `sync_error`: Message d'erreur si sync a échoué
- `gazelle_event_id`: ID de l'événement Gazelle créé (pour traçabilité)

### 2.2 Mise à jour des états existants

**Contrainte CHECK mise à jour:**

```sql
ALTER TABLE public.vincent_dindy_piano_updates
DROP CONSTRAINT IF EXISTS vincent_dindy_piano_updates_status_check;

ALTER TABLE public.vincent_dindy_piano_updates
ADD CONSTRAINT vincent_dindy_piano_updates_status_check
  CHECK (status IN ('normal', 'proposed', 'top', 'work_in_progress', 'completed'));
```

## 3. Système de Push Intelligent

### 3.1 Architecture

```
Frontend UI
  ↓ (user action: manual push)
API Endpoint: POST /vincent-dindy/push-to-gazelle
  ↓
Push Service (core/gazelle_push_service.py)
  ↓
Gazelle API Client (push_technician_service_with_measurements)
  ↓
Gazelle GraphQL API
```

### 3.2 Logique de Push

#### 3.2.1 Push Manuel (Gestionnaire)

**Déclencheur:** Bouton "Envoyer à Gazelle" dans UI Nicolas

**Critères de sélection:**
- `status = 'completed'`
- `is_work_completed = true`
- `sync_status IN ('pending', 'modified', 'error')`
- Piano a un `travail` OU `observations` non vide

**Processus:**
1. Filtrer pianos éligibles
2. Pour chaque piano:
   a. Créer service note avec `push_technician_service_with_measurements()`
   b. Parser température/humidité si présent
   c. Créer measurement si détecté
   d. Mettre à jour `sync_status = 'pushed'`, `last_sync_at = NOW()`, `gazelle_event_id = event_id`
3. Afficher résumé: X pianos envoyés, Y erreurs

#### 3.2.2 Push Automatique (Scheduled Task)

**Déclencheur:** Cron job quotidien à 01:00 AM

**Critères de sélection:** MÊMES que push manuel

**Différence:** Exécuté sans interaction utilisateur, logs dans fichier

**Implémentation:**
```python
# scripts/scheduled_push_to_gazelle.py
# Exécuté via cron: 0 1 * * * /usr/bin/python3 /path/to/scripts/scheduled_push_to_gazelle.py
```

### 3.3 Gestion des Erreurs

**Stratégies:**
1. **Erreur individuelle**: Marquer piano avec `sync_status = 'error'`, `sync_error = message`
2. **Erreur réseau**: Retry 3 fois avec backoff exponentiel (1s, 2s, 4s)
3. **Erreur Gazelle API**: Logger erreur, ne pas bloquer autres pianos
4. **Rollback**: Ne PAS modifier `status` du piano en cas d'erreur

**Notification:**
- Push manuel: Afficher toast d'erreur dans UI
- Push automatique: Email au gestionnaire (optional)

## 4. Nettoyage de l'Interface (Bouton Masquer)

### 4.1 Logique de Masquage

**Champ existant:** `is_hidden` dans `vincent_dindy_piano_updates`

**Comportement:**
- Si `is_hidden = true` → Piano disparaît de:
  - Vue Tournées (sélection de pianos)
  - Vue Technicien (liste des pianos)
  - Inventaire (sauf avec toggle "Tout voir")

**Cascade avec tag Gazelle:**
- Si piano a tag `'NON'` dans Gazelle → Auto-hide (`is_hidden = true`)
- Si gestionnaire masque piano manuellement → Optionnellement ajouter tag `'NON'` dans Gazelle

### 4.2 Batch Operations

**Boutons à ajouter:**
1. "Masquer de l'inventaire" → `is_in_csv = false`
2. "Masquer complètement" → `is_hidden = true`
3. "Réinitialiser statut" → `status = 'normal'`, `is_work_completed = false`, `sync_status = 'pending'`

## 5. UI/UX Changes

### 5.1 Vue Technicien - Ajout Checkbox

**Emplacement:** Dans le formulaire développé (expanded accordion)

**Disposition:**
```jsx
<div className="space-y-4">
  <div>
    <label>Travail effectué</label>
    <textarea
      value={travailInput}
      onChange={(e) => setTravailInput(e.target.value)}
      placeholder="Décrivez le travail effectué..."
    />
  </div>

  <div>
    <label>Observations</label>
    <textarea
      value={observationsInput}
      onChange={(e) => setObservationsInput(e.target.value)}
      placeholder="Notes techniques, température, humidité..."
    />
  </div>

  <div className="flex items-center gap-2">
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

  <button onClick={handleSave}>Enregistrer</button>
</div>
```

### 5.2 Vue Nicolas - Bouton Push Gazelle

**Emplacement:** Dans toolbar batch operations

```jsx
<div className="batch-toolbar">
  {/* Boutons existants */}
  <button onClick={handleStatusChange}>Changer statut</button>
  <button onClick={handleAddToTournee}>Ajouter à tournée</button>

  {/* NOUVEAU */}
  <button
    onClick={handlePushToGazelle}
    className="bg-green-600 text-white px-4 py-2 rounded"
    disabled={!hasCompletedPianos}
  >
    📤 Envoyer à Gazelle ({completedCount} pianos)
  </button>
</div>
```

**Indicateur de sync status:**
- Icône à côté du piano dans la liste:
  - ⏳ `pending`: En attente
  - ✅ `pushed`: Envoyé
  - ⚠️ `error`: Erreur
  - 🔄 `modified`: Modifié depuis dernier push

### 5.3 Logique de Couleur Mise à Jour

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

  // Priorité 4: Travail en cours (bleu)
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

## 6. API Endpoints

### 6.1 Nouvel Endpoint: Push to Gazelle

**Route:** `POST /vincent-dindy/push-to-gazelle`

**Body:**
```json
{
  "piano_ids": ["ins_abc123", "ins_def456"],  // Optional: specific pianos
  "tournee_id": "tournee_1234567890",         // Optional: filter by tournee
  "dry_run": false                             // Optional: test without pushing
}
```

**Response:**
```json
{
  "success": true,
  "pushed_count": 5,
  "error_count": 1,
  "results": [
    {
      "piano_id": "ins_abc123",
      "status": "success",
      "gazelle_event_id": "evt_xyz789",
      "measurement_created": true
    },
    {
      "piano_id": "ins_def456",
      "status": "error",
      "error": "Client ID not found"
    }
  ]
}
```

### 6.2 Endpoint Modifié: Update Piano

**Route:** `PUT /vincent-dindy/pianos/{piano_id}`

**Nouveaux champs acceptés:**
```json
{
  "status": "work_in_progress",
  "travail": "Piano accordé, cordes changées",
  "observations": "Température 22°C, humidité 45%",
  "is_work_completed": true,      // NOUVEAU
  "is_hidden": false
}
```

**Logique de transition automatique:**
```python
# Si travail ou observations remplis ET is_work_completed = false
if (travail or observations) and not is_work_completed:
    status = 'work_in_progress'

# Si is_work_completed = true
if is_work_completed:
    status = 'completed'
    completed_in_tournee_id = active_tournee_id
```

## 7. Évolutivité & Architecture

### 7.1 Table `piano_tournee_status` (Future)

**Si la table `vincent_dindy_piano_updates` devient trop lourde:**

```sql
CREATE TABLE IF NOT EXISTS public.piano_tournee_status (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Relations
  piano_id TEXT NOT NULL,  -- gazelleId
  tournee_id TEXT NOT NULL REFERENCES public.tournees(id) ON DELETE CASCADE,

  -- État spécifique à cette tournée
  status TEXT CHECK (status IN ('normal', 'proposed', 'top', 'work_in_progress', 'completed')),
  travail TEXT,
  observations TEXT,
  is_work_completed BOOLEAN DEFAULT false,

  -- Sync
  sync_status TEXT CHECK (sync_status IN ('pending', 'pushed', 'modified', 'error')),
  last_sync_at TIMESTAMPTZ,
  gazelle_event_id TEXT,

  -- Audit
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  CONSTRAINT unique_piano_tournee UNIQUE(piano_id, tournee_id)
);
```

**Avantages:**
- État séparé par tournée (même piano peut avoir statuts différents selon tournée)
- Historique complet des tournées passées
- Performance: filtrage plus rapide par tournée

**Migration:** À considérer si nombre de tournées > 100 ou pianos > 500

### 7.2 Service Architecture

**Nouveau fichier:** `core/gazelle_push_service.py`

```python
class GazellePushService:
    """Service pour push intelligent vers Gazelle."""

    def __init__(self):
        self.api_client = GazelleAPIClient()
        self.supabase = SupabaseStorage()

    def get_pianos_to_push(self, filters: dict) -> List[dict]:
        """Récupère pianos éligibles pour push."""
        pass

    def push_piano_to_gazelle(self, piano_data: dict) -> dict:
        """Push un piano vers Gazelle."""
        pass

    def push_batch(self, piano_ids: List[str]) -> dict:
        """Push multiple pianos avec retry logic."""
        pass

    def schedule_daily_push(self):
        """Scheduled task pour push automatique."""
        pass
```

## 8. Migration & Déploiement

### 8.1 Ordre d'Exécution

1. **Migration DB** (`refactor/vdi/sql/011_add_sync_tracking.sql`)
2. **Backend Changes** (`core/gazelle_push_service.py`, `api/vincent_dindy.py`)
3. **Frontend Changes** (`VincentDIndyDashboard.jsx`)
4. **Test manuel** (push 1-2 pianos)
5. **Setup cron job** (push automatique)
6. **Documentation utilisateur** (guide gestionnaire + technicien)

### 8.2 Rollback Plan

**Si problèmes détectés:**
1. Désactiver cron job (`crontab -e`, commenter ligne)
2. Reverser migration SQL (DROP COLUMN)
3. Restaurer version UI précédente via git
4. Analyser logs pour comprendre échec

## 9. Tests

### 9.1 Scénarios de Test

**Test 1: Transition d'états**
- [ ] Blanc → Jaune (clic statut)
- [ ] Jaune → Bleu (saisie note sans checkbox)
- [ ] Bleu → Vert (cocher checkbox)
- [ ] Vérifier couleurs UI

**Test 2: Push manuel**
- [ ] Sélectionner 3 pianos completed
- [ ] Cliquer "Envoyer à Gazelle"
- [ ] Vérifier événements créés dans Gazelle
- [ ] Vérifier sync_status = 'pushed'

**Test 3: Push avec température/humidité**
- [ ] Piano avec observations "22°C, 45%"
- [ ] Push to Gazelle
- [ ] Vérifier measurement créé dans Gazelle

**Test 4: Masquage**
- [ ] Masquer piano via bouton
- [ ] Vérifier disparition de tournées
- [ ] Vérifier disparition vue technicien
- [ ] Vérifier toujours visible avec "Tout voir"

**Test 5: Erreurs**
- [ ] Push avec piano sans client_id
- [ ] Vérifier sync_status = 'error'
- [ ] Vérifier message d'erreur affiché
- [ ] Vérifier autres pianos pushés quand même

### 9.2 Script de Test

```python
# scripts/test_push_workflow.py
def test_complete_workflow():
    """Test workflow complet: White → Blue → Green → Gazelle."""

    piano_id = "ins_testpiano123"

    # 1. État initial (blanc)
    assert get_piano_status(piano_id) == 'normal'

    # 2. Saisie note (bleu)
    update_piano(piano_id, travail="Piano accordé", is_work_completed=False)
    assert get_piano_status(piano_id) == 'work_in_progress'

    # 3. Marquer complété (vert)
    update_piano(piano_id, is_work_completed=True)
    assert get_piano_status(piano_id) == 'completed'

    # 4. Push to Gazelle
    result = push_to_gazelle([piano_id])
    assert result['success'] == True
    assert get_sync_status(piano_id) == 'pushed'

    # 5. Vérifier événement Gazelle créé
    event = get_gazelle_event(result['gazelle_event_id'])
    assert event['status'] == 'COMPLETE'
```

## 10. Documentation Utilisateur

### 10.1 Guide Gestionnaire (Nicolas)

**Workflow:**
1. Définir priorités: Cliquer status → Jaune (standard) ou Ambre (urgent)
2. Assigner tâches: Remplir colonne "À faire"
3. Suivre progression: Couleurs indiquent état (Bleu = en cours, Vert = terminé)
4. Envoyer à Gazelle: Bouton "Envoyer à Gazelle" quand pianos verts
5. Vérifier sync: Icône ✅ confirme envoi réussi

### 10.2 Guide Technicien

**Workflow:**
1. Voir tâches: Filtre "À faire" affiche pianos jaunes/ambre
2. Ouvrir piano: Cliquer pour développer formulaire
3. Saisir travail: Remplir "Travail effectué" et "Observations"
4. Cocher si terminé: ✅ "Travail complété" si fini
5. Enregistrer: Bouton "Enregistrer" sauvegarde

**Astuces:**
- Inclure température/humidité dans observations (ex: "22°C, 45%")
- Laisser checkbox décochée si travail partiel
- Piano devient bleu dès que note saisie, vert quand checkbox cochée

---

## Résumé: Checklist d'Implémentation

- [ ] Migration SQL: Ajouter champs `is_work_completed`, `sync_status`, etc.
- [ ] Backend: Créer `GazellePushService` avec logique push
- [ ] Backend: Endpoint `POST /vincent-dindy/push-to-gazelle`
- [ ] Backend: Modifier `PUT /pianos/{id}` pour transitions auto
- [ ] Frontend: Ajouter checkbox "Travail complété"
- [ ] Frontend: Bouton "Envoyer à Gazelle"
- [ ] Frontend: Indicateurs sync_status (icônes ⏳✅⚠️🔄)
- [ ] Frontend: Fonction `getRowClass()` mise à jour pour couleur bleue
- [ ] Script: `scheduled_push_to_gazelle.py`
- [ ] Cron: Setup job quotidien 01:00
- [ ] Tests: Script de test automatisé
- [ ] Docs: Guide utilisateur gestionnaire + technicien
