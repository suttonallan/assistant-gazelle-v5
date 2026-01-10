# 📦 Déductions d'Inventaire Automatiques

## Objectif

Suivre automatiquement la consommation de matériel (buvards, gaines, cordes, etc.) lorsque les techniciens effectuent des services facturés. Chaque déduction est enregistrée dans la table `sync_logs` pour visibilité complète dans l'interface.

## Architecture

### 1. Tables Supabase

#### `service_inventory_consumption`
Règles de consommation: quel service consomme quels matériaux.

```sql
CREATE TABLE service_inventory_consumption (
    id SERIAL PRIMARY KEY,
    service_gazelle_id TEXT NOT NULL,      -- ID du service dans Gazelle (ex: "mit_...")
    service_code_produit TEXT,             -- Code produit local (optionnel)
    material_code_produit TEXT NOT NULL,   -- Code du matériel consommé (ex: "BUV-001")
    quantity FLOAT DEFAULT 1.0,            -- Quantité consommée par service
    is_optional BOOLEAN DEFAULT false,     -- Si la consommation est optionnelle
    notes TEXT,                            -- Notes explicatives
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(service_gazelle_id, material_code_produit)  -- Éviter doublons
);
```

**Exemple de règles**:
| service_gazelle_id | material_code_produit | quantity | notes |
|--------------------|----------------------|----------|-------|
| mit_EntretienAnn... | BUV-001 | 1.0 | Buvard standard |
| mit_EntretienAnn... | GAIN-001 | 1.0 | Gaine vinyle |
| mit_GrandEntretien | BUV-001 | 2.0 | Double buvard |
| mit_GrandEntretien | DOUB-001 | 1.0 | Doublure feutre |

#### `sync_logs`
Table centrale pour tous les logs de synchronisation ET déductions.

```sql
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    script_name TEXT NOT NULL,             -- 'Deduction_Inventaire_Auto' pour déductions
    status TEXT NOT NULL,                  -- 'success', 'error', 'warning'
    tables_updated JSONB,                  -- Détails de la déduction
    details TEXT,                          -- Description lisible
    execution_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Format `tables_updated` pour déductions**:
```json
{
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
}
```

### 2. Module de traitement

**Fichier**: `modules/inventory_deductions/process_deductions.py`

**Classe principale**: `InventoryDeductionProcessor`

#### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Récupérer factures récentes (X derniers jours)          │
│    API: api_client.get_invoices()                           │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Charger règles de consommation                          │
│    Table: service_inventory_consumption                     │
│    Index par service_gazelle_id pour accès rapide          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Pour chaque facture:                                     │
│    - Identifier le technicien (user_id → nom local)         │
│    - Pour chaque line item:                                 │
│      • Vérifier si le type d'item a des règles              │
│      • Si oui, appliquer chaque règle                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Pour chaque déduction:                                   │
│    a) Créer log dans sync_logs                              │
│    b) Mettre à jour inventaire technicien (stock -= qty)    │
│    c) Incrémenter stats['deductions_created']               │
└─────────────────────────────────────────────────────────────┘
```

#### Méthodes principales

```python
class InventoryDeductionProcessor:
    def __init__(self, days_lookback: int = 7)
        # Initialise avec nombre de jours à analyser

    def process_recent_invoices() -> Dict[str, int]
        # Point d'entrée principal - retourne stats

    def _get_consumption_rules() -> List[Dict[str, Any]]
        # Charge rules depuis Supabase, indexe par service_id

    def _process_invoice(invoice, rules)
        # Traite une facture complète

    def _process_invoice_item(invoice_id, item, technicien, date)
        # Traite un line item spécifique

    def _create_deduction_log(...) -> bool
        # Crée entrée dans sync_logs

    def _update_technician_inventory(tech, material, qty) -> bool
        # Met à jour inventaire (appelle storage.update_stock)

    def _get_technicien_from_user_id(user_id) -> str
        # Mappe user_id Gazelle → nom technicien local
```

### 3. API Endpoints

#### `GET /api/inventaire/deduction-logs?limit=100`
Récupère les logs de déductions depuis `sync_logs`.

**Réponse**:
```json
{
  "success": true,
  "logs": [
    {
      "id": 123,
      "script_name": "Deduction_Inventaire_Auto",
      "status": "success",
      "tables_updated": {
        "produits": {"code": "BUV-001", "quantite": 1, "technicien": "Allan"},
        "ventes": 1,
        "invoice": {"id": "inv_xyz", "number": "2024-001"}
      },
      "details": "Service: Entretien annuel | Matériel: BUV-001 × 1.0",
      "created_at": "2026-01-08T14:30:00Z"
    }
  ],
  "count": 1
}
```

#### `GET /api/inventaire/deduction-summary?days=30`
Résumé statistique des déductions sur X jours.

**Réponse**:
```json
{
  "success": true,
  "summary": [
    {
      "code_produit": "BUV-001",
      "total_quantity": 45.0,
      "deduction_count": 45
    },
    {
      "code_produit": "GAIN-001",
      "total_quantity": 38.0,
      "deduction_count": 38
    }
  ],
  "total_deductions": 83,
  "period_start": "2025-12-09T00:00:00Z",
  "period_end": "2026-01-08T15:00:00Z",
  "days": 30
}
```

#### `POST /api/inventaire/process-deductions?days=7`
Déclenche le traitement manuel des déductions.

**Réponse**:
```json
{
  "success": true,
  "message": "Traitement terminé: 12 déductions créées",
  "stats": {
    "invoices_processed": 8,
    "deductions_created": 12,
    "errors": 0
  }
}
```

### 4. Interface Frontend

**Composant**: `frontend/src/components/NotificationsPanel.jsx`

**Onglet**: "Déductions d'inventaire"

#### Affichage

```
┌──────────────────────────────────────────────────────────┐
│ 📦 Notifications & Logs                                  │
├──────────────────────────────────────────────────────────┤
│ [Déductions d'inventaire] [Alertes RV] [Tâches & Imports]│
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 📊 Résumé (30 derniers jours)                           │
│ ┌─────────────┬──────────────┬─────────────────────┐   │
│ │ Produit     │ Qté Total    │ Nb Déductions       │   │
│ ├─────────────┼──────────────┼─────────────────────┤   │
│ │ BUV-001     │ 45           │ 45                  │   │
│ │ GAIN-001    │ 38           │ 38                  │   │
│ │ DOUB-001    │ 12           │ 12                  │   │
│ └─────────────┴──────────────┴─────────────────────┘   │
│                                                          │
│ 📋 Journal des Déductions (100 plus récentes)           │
│ ┌──────────────────┬─────────────────────────────────┐  │
│ │ Date & Heure     │ Détails                         │  │
│ ├──────────────────┼─────────────────────────────────┤  │
│ │ 2026-01-08 14:30 │ Allan: BUV-001 × 1 (Entretien)  │  │
│ │ 2026-01-08 11:15 │ Vincent: GAIN-001 × 1 (Tuning) │  │
│ └──────────────────┴─────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

#### État React

```jsx
const [deductionLogs, setDeductionLogs] = useState([])
const [deductionsLoading, setDeductionsLoading] = useState(true)

const loadDeductionLogs = async () => {
  const response = await fetch(`${API_URL}/api/inventaire/deduction-logs?limit=100`)
  const data = await response.json()
  setDeductionLogs(data.logs || [])
}
```

## Configuration Initiale

### Étape 1: Définir les règles de consommation

**Via API**:
```bash
# Créer une règle: "Entretien annuel" consomme 1 buvard
curl -X POST http://localhost:5174/api/inventaire/service-consumption/rules \
  -H "Content-Type: application/json" \
  -d '{
    "service_gazelle_id": "mit_EntretienAnnuel",
    "material_code_produit": "BUV-001",
    "quantity": 1.0,
    "is_optional": false,
    "notes": "Buvard standard pour entretien annuel"
  }'
```

**Via batch (plusieurs matériaux pour un service)**:
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

Pour trouver les IDs Gazelle des services:

```bash
# Récupérer la liste des produits Gazelle
curl http://localhost:5174/api/inventaire/gazelle/products
```

Format des IDs: `mit_CX6CvWXbjs08vg70` (Master Item ID)

### Étape 3: Tester le traitement

```bash
# Traiter les 7 derniers jours de factures
curl -X POST http://localhost:5174/api/inventaire/process-deductions?days=7
```

**Résultat attendu**:
```
📦 TRAITEMENT DES DÉDUCTIONS D'INVENTAIRE AUTOMATIQUES
========================================================
🔍 Analyse des factures des 7 derniers jours...
📅 Depuis: 2026-01-01T15:00:00Z
📄 8 factures récentes trouvées
📋 3 règles de consommation actives

  ✅ Déduction créée: BUV-001 × 1.0 pour Allan
  ✅ Déduction créée: GAIN-001 × 1.0 pour Allan
  ✅ Déduction créée: BUV-001 × 1.0 pour Vincent

✅ Traitement terminé:
   Factures traitées: 8
   Déductions créées: 12
   Erreurs: 0
```

## Automatisation

### Cron Job (à ajouter dans le scheduler)

**Fréquence recommandée**: Quotidiennement à 02:00 (après sync Gazelle de 01:00)

```python
# Dans core/scheduler.py

@scheduler.scheduled_job('cron', hour=2, minute=0, timezone=TZ)
def scheduled_process_deductions():
    """
    02:00 - Traitement des déductions d'inventaire (quotidien)

    Analyse les factures des 7 derniers jours et crée les logs de déduction.
    """
    task_process_inventory_deductions(triggered_by='scheduler')

def task_process_inventory_deductions(triggered_by='auto', user_email=None):
    """Tâche planifiée pour traiter les déductions."""
    print("\n" + "="*70)
    print("📦 DÉDUCTIONS INVENTAIRE - Démarrage")
    print(f"   Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    try:
        from modules.inventory_deductions.process_deductions import InventoryDeductionProcessor

        processor = InventoryDeductionProcessor(days_lookback=7)
        stats = processor.process_recent_invoices()

        # Enregistrer dans sync_logs
        from core.supabase_storage import SupabaseStorage
        storage = SupabaseStorage()

        log_entry = {
            'script_name': 'process_deductions_scheduler',
            'status': 'success' if stats['errors'] == 0 else 'warning',
            'tables_updated': json.dumps(stats),
            'details': f"Factures: {stats['invoices_processed']}, Déductions: {stats['deductions_created']}",
            'execution_time_seconds': 0,
            'created_at': datetime.now().isoformat()
        }

        storage.update_data("sync_logs", log_entry, id_field="id", upsert=True)

        print("\n✅ Déductions traitées avec succès")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Erreur traitement déductions: {e}")
        import traceback
        traceback.print_exc()
```

## Mapping Technicien

**Fonction**: `_get_technicien_from_user_id(user_id)`

**Logique**:
1. Récupérer l'utilisateur depuis la table `users` via `gazelle_user_id`
2. Extraire l'email
3. Mapper email → nom technicien selon convention:
   - `asutton@piano-tek.com` → `Allan`
   - `vstucker@piano-tek.com` → `Vincent`
   - `nprudhomme@piano-tek.com` → `Nick`
   - Autres: Extraire prénom depuis email

**Important**: Si le user_id n'est pas trouvé, la facture est ignorée (pas de déduction créée).

## Gestion des Erreurs

### Erreur 1: Règle de consommation introuvable
**Symptôme**: Aucune déduction créée malgré des factures récentes

**Solution**: Vérifier que les règles existent dans `service_inventory_consumption`
```sql
SELECT * FROM service_inventory_consumption;
```

### Erreur 2: Technicien non identifié
**Symptôme**: Log "⚠️ Impossible de déterminer le technicien, skip cette facture"

**Solution**: S'assurer que le `user_id` de la facture existe dans la table `users`
```sql
SELECT * FROM users WHERE gazelle_user_id = 'usr_...';
```

### Erreur 3: Stock négatif
**Symptôme**: Inventaire d'un technicien devient négatif après déduction

**Solution**:
- Vérifier le stock initial du technicien
- Ajuster manuellement via l'interface
- Considérer augmenter les quantités de départ

### Erreur 4: Doublons de déduction
**Symptôme**: Même déduction créée plusieurs fois

**Solution**:
- Vérifier que le script n'est pas exécuté plusieurs fois simultanément
- Ajouter une contrainte UNIQUE sur `(invoice_id, item_id, material_code)` dans une table dédiée si nécessaire

## Tests

### Test 1: Créer une règle simple
```bash
# 1. Créer règle
curl -X POST http://localhost:5174/api/inventaire/service-consumption/rules \
  -H "Content-Type: application/json" \
  -d '{
    "service_gazelle_id": "mit_TEST",
    "material_code_produit": "TEST-001",
    "quantity": 1.0
  }'

# 2. Vérifier
curl http://localhost:5174/api/inventaire/service-consumption/rules?service_gazelle_id=mit_TEST
```

### Test 2: Traiter les déductions
```bash
# Traiter dernières 24h
curl -X POST "http://localhost:5174/api/inventaire/process-deductions?days=1"
```

### Test 3: Vérifier les logs
```bash
# Récupérer les logs
curl "http://localhost:5174/api/inventaire/deduction-logs?limit=10"

# Vérifier dans sync_logs
curl "http://localhost:5174/api/sync-logs/recent?limit=50" | \
  jq '.logs[] | select(.script_name == "Deduction_Inventaire_Auto")'
```

### Test 4: Vérifier impact inventaire
```sql
-- Avant traitement
SELECT technicien, code_produit, quantite_stock
FROM inventaire_techniciens
WHERE code_produit = 'BUV-001';

-- [Exécuter traitement déductions]

-- Après traitement
SELECT technicien, code_produit, quantite_stock
FROM inventaire_techniciens
WHERE code_produit = 'BUV-001';

-- Les quantités doivent avoir diminué selon les déductions
```

## Performance

### Optimisations appliquées

1. **Index par service_gazelle_id**: Règles groupées en mémoire pour accès O(1)
2. **Batch limité**: Traiter seulement X derniers jours (défaut: 7)
3. **Filtrage précoce**: Ignorer factures sans items ou sans technicien
4. **Traitement asynchrone**: API endpoint lance traitement en background (à implémenter si nécessaire)

### Métriques attendues

- **8 factures, 3 règles**: ~500ms
- **50 factures, 10 règles**: ~2-3s
- **200 factures, 30 règles**: ~10-15s

## Limitations Actuelles

1. **Pas de gestion des annulations**: Si une facture est annulée, la déduction reste
2. **Pas de traçabilité bidirectionnelle**: Difficile de retrouver quelle déduction correspond à quelle facture exactement
3. **Mapping technicien basique**: Utilise email comme proxy, pas robuste si email change

## Améliorations Futures

### V2: Table dédiée `inventory_deductions`
Remplacer les logs dans `sync_logs` par une table spécialisée:

```sql
CREATE TABLE inventory_deductions (
    id SERIAL PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    invoice_item_id TEXT NOT NULL,
    service_gazelle_id TEXT NOT NULL,
    material_code_produit TEXT NOT NULL,
    quantity FLOAT NOT NULL,
    technicien TEXT NOT NULL,
    date_service TIMESTAMPTZ NOT NULL,
    processed BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(invoice_item_id, material_code_produit)  -- Éviter doublons
);
```

Avantages:
- Requêtes plus rapides
- Pas de parsing JSON
- Possibilité d'annuler une déduction spécifique

### V3: Détection automatique via Timeline
Au lieu de traiter les factures, analyser les entrées `SERVICE_ENTRY_MANUAL` dans la timeline.

### V4: Interface de gestion des règles
Créer un UI admin pour gérer les règles de consommation visuellement.

---

**Date de création**: 2026-01-08
**Auteur**: Claude
**Status**: ✅ Implémenté et documenté
