# ✅ Session: Finalisation des Déductions d'Inventaire

## Date
2026-01-08

## Objectifs de la session

Louise voulait finaliser la section "Déductions d'inventaire" avec:
1. Déplacement des Logs Sync de l'Inventaire vers Notifications (✅ déjà fait lors session précédente)
2. Logique de déduction automatique écrivant dans `sync_logs`
3. Affichage chronologique des déductions dans l'onglet "Déductions d'inventaire"
4. Bouton "Sync RV & Alertes" devant importer les appointments d'abord

## Travaux effectués

### 1. API Endpoints créés ✅

#### `GET /api/inventaire/deduction-logs?limit=100`
Récupère les logs de déductions depuis `sync_logs` où `script_name = 'Deduction_Inventaire_Auto'`.

**Localisation**: [api/inventaire.py:2160-2200](api/inventaire.py:2160-2200)

**Fonctionnalités**:
- Filtre les logs par script_name
- Trie par date décroissante (plus récents d'abord)
- Limite configurable (défaut: 100)

#### `GET /api/inventaire/deduction-summary?days=30`
Résumé statistique des déductions sur X jours.

**Localisation**: [api/inventaire.py:2203-2274](api/inventaire.py:2203-2274)

**Fonctionnalités**:
- Agrège déductions par produit
- Calcule quantités totales et nombre d'occurrences
- Trie par quantité décroissante

#### `POST /api/inventaire/process-deductions?days=7`
Déclenche le traitement manuel des déductions.

**Localisation**: [api/inventaire.py:2277-2318](api/inventaire.py:2277-2318)

**Fonctionnalités**:
- Lance le processeur de déductions
- Retourne statistiques complètes
- Gestion d'erreurs avec traceback

### 2. Module de traitement des déductions ✅

**Fichier créé**: [modules/inventory_deductions/process_deductions.py](modules/inventory_deductions/process_deductions.py)

**Classe**: `InventoryDeductionProcessor`

#### Workflow complet

```
Factures Gazelle (7 derniers jours)
         ↓
Règles de consommation (table service_inventory_consumption)
         ↓
Pour chaque facture:
  - Identifier technicien (user_id → nom)
  - Pour chaque line item:
    • Vérifier si service a règles
    • Appliquer chaque règle
         ↓
Pour chaque déduction:
  1. Créer log dans sync_logs
  2. Mettre à jour inventaire technicien (stock -= qty)
  3. Incrémenter stats
```

#### Méthodes implémentées

| Méthode | Description |
|---------|-------------|
| `__init__(days_lookback)` | Initialise avec nombre de jours à analyser |
| `process_recent_invoices()` | Point d'entrée principal, retourne stats |
| `_get_consumption_rules()` | Charge et indexe règles par service_id |
| `_process_invoice()` | Traite une facture complète |
| `_process_invoice_item()` | Traite un line item spécifique |
| `_create_deduction_log()` | Crée entrée dans sync_logs |
| `_update_technician_inventory()` | Met à jour stock technicien |
| `_get_technicien_from_user_id()` | Mappe user_id Gazelle → nom local |

#### Format des logs créés

```json
{
  "script_name": "Deduction_Inventaire_Auto",
  "status": "success",
  "tables_updated": {
    "produits": {
      "code": "BUV-001",
      "quantite": 1.0,
      "technicien": "Allan"
    },
    "ventes": 1,
    "invoice": {
      "id": "inv_xyz123",
      "number": "2024-001",
      "item_id": "ii_abc456"
    }
  },
  "details": "Service: Entretien annuel | Matériel: BUV-001 × 1.0",
  "execution_time_seconds": 0,
  "created_at": "2026-01-08T14:30:00Z"
}
```

### 3. Frontend - Affichage des déductions ✅

**Composant**: [frontend/src/components/NotificationsPanel.jsx](frontend/src/components/NotificationsPanel.jsx)

**Onglet**: "Déductions d'inventaire"

#### États React ajoutés (lignes 9-10)

```jsx
const [deductionLogs, setDeductionLogs] = useState([])
const [deductionsLoading, setDeductionsLoading] = useState(true)
```

#### Fonction de chargement (lignes 37-50)

```jsx
const loadDeductionLogs = async () => {
  try {
    setDeductionsLoading(true)
    const response = await fetch(`${API_URL}/api/inventaire/deduction-logs?limit=100`)
    const data = await response.json()
    setDeductionLogs(data.logs || [])
    setError(null)
  } catch (err) {
    console.error('Erreur chargement logs déduction:', err)
    setError(err.message)
  } finally {
    setDeductionsLoading(false)
  }
}
```

#### Affichage UI

L'onglet "Déductions d'inventaire" affiche maintenant:
1. **Résumé statistique** (30 derniers jours) - via `loadImportSummary()`
2. **Journal chronologique** (100 plus récentes) - via `loadDeductionLogs()`

### 4. Bouton "Sync RV + Scan Notifications" ✅

**Vérification effectuée**: Le bouton fonctionne déjà correctement!

**Localisation**: [core/scheduler.py:278-327](core/scheduler.py:278-327)

**Fonction**: `task_sync_rv_and_alerts()`

**Workflow actuel** (déjà correct):
```python
def task_sync_rv_and_alerts():
    # 1. Sync appointments FIRST
    syncer = GazelleToSupabaseSync()
    appointments_count = syncer.sync_appointments()

    # 2. THEN send alerts
    service = UnconfirmedAlertsService(...)
    result = service.send_alerts(target_date=tomorrow)
```

**Conclusion**: Aucune modification nécessaire, le bouton import déjà les RV avant de scanner les alertes. ✅

### 5. Documentation complète ✅

**Fichier créé**: [docs/DEDUCTIONS_INVENTAIRE_AUTO.md](docs/DEDUCTIONS_INVENTAIRE_AUTO.md)

**Contenu**:
- Architecture complète (tables, modules, API)
- Workflow détaillé avec diagrammes
- Configuration initiale (créer règles, identifier IDs Gazelle)
- Tests pas-à-pas
- Gestion des erreurs courantes
- Optimisations et métriques de performance
- Limitations et améliorations futures (V2, V3, V4)

## Structure finale de l'interface

```
📊 Notifications & Logs
├── 📦 Déductions d'inventaire (onglet)
│   ├── Résumé (30 derniers jours)
│   │   └── Tableau: Produit | Qté Total | Nb Déductions
│   └── Journal chronologique (100 plus récentes)
│       └── Liste: Date | Technicien | Produit | Quantité | Service
│
├── 🔔 Alertes RV (onglet)
│   ├── Alertes en attente
│   └── Historique des alertes
│
└── ⏰ Tâches & Imports (onglet)
    ├── SchedulerJournal
    │   ├── Tâches planifiées
    │   ├── Imports individuels
    │   ├── Importations récentes (NOUVEAU session précédente)
    │   └── Journal exécutions manuelles
    └── Logs de synchronisation GitHub (DÉPLACÉ session précédente)
        ├── Statistiques (4 cartes)
        └── Tableau des logs
```

## Configuration requise (À FAIRE par Louise)

### Étape 1: Créer les règles de consommation

**Exemple pour "Entretien annuel"**:
```bash
curl -X POST http://localhost:5174/api/inventaire/service-consumption/rules/batch \
  -H "Content-Type: application/json" \
  -d '{
    "service_gazelle_id": "mit_EntretienAnnuel",
    "materials": [
      {"material_code_produit": "BUV-001", "quantity": 1.0, "notes": "Buvard standard"},
      {"material_code_produit": "GAIN-001", "quantity": 1.0, "notes": "Gaine vinyle"}
    ]
  }'
```

**Exemple pour "Grand entretien"**:
```bash
curl -X POST http://localhost:5174/api/inventaire/service-consumption/rules/batch \
  -H "Content-Type: application/json" \
  -d '{
    "service_gazelle_id": "mit_GrandEntretien",
    "materials": [
      {"material_code_produit": "BUV-001", "quantity": 2.0},
      {"material_code_produit": "GAIN-001", "quantity": 1.0},
      {"material_code_produit": "DOUB-001", "quantity": 1.0, "is_optional": true}
    ]
  }'
```

### Étape 2: Identifier les service_gazelle_id

```bash
# Récupérer la liste des produits Gazelle
curl http://localhost:5174/api/inventaire/gazelle/products | jq '.products[] | {id, nom: .nom_fr, type}'
```

Chercher les services comme:
- "Entretien annuel"
- "Grand entretien"
- "Tuning"
- "Réparation de mécaniques"

Noter leurs IDs (format: `mit_CX6CvWXbjs08vg70`)

### Étape 3: Tester le traitement

```bash
# Traiter les 7 derniers jours
curl -X POST "http://localhost:5174/api/inventaire/process-deductions?days=7"
```

### Étape 4: Vérifier les résultats

1. **Dans l'interface**: Aller dans **Notifications → Déductions d'inventaire**
2. **Via API**:
   ```bash
   curl "http://localhost:5174/api/inventaire/deduction-logs?limit=10"
   ```

## Tests recommandés

### Test 1: Endpoint deduction-logs
```bash
curl "http://localhost:5174/api/inventaire/deduction-logs?limit=5"
```
**Résultat attendu**: Liste vide `{"success": true, "logs": [], "count": 0}` (normal si aucune déduction n'a été créée encore)

### Test 2: Endpoint deduction-summary
```bash
curl "http://localhost:5174/api/inventaire/deduction-summary?days=30"
```
**Résultat attendu**: Résumé vide `{"success": true, "summary": [], "total_deductions": 0, ...}`

### Test 3: Créer une règle test
```bash
curl -X POST http://localhost:5174/api/inventaire/service-consumption/rules \
  -H "Content-Type: application/json" \
  -d '{
    "service_gazelle_id": "mit_TEST",
    "material_code_produit": "TEST-001",
    "quantity": 1.0
  }'
```

### Test 4: Traiter les déductions
```bash
curl -X POST "http://localhost:5174/api/inventaire/process-deductions?days=1"
```
**Résultat attendu**:
```json
{
  "success": true,
  "message": "Traitement terminé: X déductions créées",
  "stats": {
    "invoices_processed": N,
    "deductions_created": X,
    "errors": 0
  }
}
```

## Fichiers modifiés

| Fichier | Lignes | Modifications |
|---------|--------|---------------|
| [api/inventaire.py](api/inventaire.py) | +159 | Ajout 3 endpoints: deduction-logs, deduction-summary, process-deductions |
| [modules/inventory_deductions/process_deductions.py](modules/inventory_deductions/process_deductions.py) | +425 | Module complet de traitement des déductions |

## Fichiers créés

| Fichier | Description |
|---------|-------------|
| [modules/inventory_deductions/process_deductions.py](modules/inventory_deductions/process_deductions.py) | Module principal de traitement |
| [docs/DEDUCTIONS_INVENTAIRE_AUTO.md](docs/DEDUCTIONS_INVENTAIRE_AUTO.md) | Documentation complète (85+ lignes) |
| [docs/SESSION_DEDUCTIONS_FINALE.md](docs/SESSION_DEDUCTIONS_FINALE.md) | Ce fichier (résumé session) |

## Prochaines étapes (optionnelles)

### Automatisation quotidienne

Ajouter un Cron Job dans [core/scheduler.py](core/scheduler.py):

```python
@scheduler.scheduled_job('cron', hour=2, minute=0, timezone=TZ)
def scheduled_process_deductions():
    """02:00 - Traitement des déductions d'inventaire (quotidien)"""
    task_process_inventory_deductions(triggered_by='scheduler')
```

### Interface de gestion des règles

Créer un composant React pour gérer les règles visuellement:
- Liste des règles existantes
- Formulaire d'ajout/édition
- Suppression de règles
- Preview des matériaux associés à chaque service

### Table dédiée (V2)

Remplacer les logs dans `sync_logs` par une table spécialisée `inventory_deductions` pour:
- Requêtes plus rapides
- Possibilité d'annuler une déduction
- Meilleure traçabilité

## Récapitulatif des sessions

### Session précédente (2026-01-08 matin)
1. ✅ Fix UPSERT 409 Conflicts (ajout `?on_conflict=external_id`)
2. ✅ Réorganisation UI (déplacement Logs Sync vers Notifications)
3. ✅ Affichage importations récentes (sync_logs dans SchedulerJournal)

### Session actuelle (2026-01-08 après-midi)
1. ✅ API endpoints pour déductions (logs + summary + trigger)
2. ✅ Module de traitement automatique (InventoryDeductionProcessor)
3. ✅ Vérification bouton RV (déjà correct, import appointments first)
4. ✅ Documentation complète

## État du système

| Fonctionnalité | Status | Notes |
|----------------|--------|-------|
| Endpoints API | ✅ Prêt | 3 endpoints créés et testables |
| Module traitement | ✅ Prêt | Classe complète avec gestion erreurs |
| Frontend affichage | ✅ Prêt | Appels API en place, manque juste règles |
| Documentation | ✅ Complète | 85+ lignes avec exemples et tests |
| Règles consommation | ⚠️ À configurer | Louise doit créer les règles selon besoins |
| Automatisation | 📋 Optionnel | Cron job à ajouter si désiré |

## Notes importantes

1. **Aucune déduction ne sera créée avant la configuration des règles** dans `service_inventory_consumption`
2. Le frontend affichera une liste vide jusqu'à ce que:
   - Des règles soient créées
   - Le traitement soit exécuté
   - Des factures correspondantes existent
3. Le bouton "Sync RV & Alertes" fonctionne déjà correctement (import RV avant scan)

---

**Session complétée avec succès! 🎉**

Tous les objectifs de Louise ont été atteints:
- ✅ Logs Sync déplacés (session précédente)
- ✅ Logique de déduction avec écriture dans sync_logs
- ✅ Affichage dans l'onglet Déductions d'inventaire
- ✅ Bouton RV & Alertes vérifié (déjà correct)

La prochaine étape est la **configuration des règles de consommation** selon les besoins réels de Piano-Tek.
