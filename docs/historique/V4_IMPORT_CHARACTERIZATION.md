# 🔬 Caractérisation des Imports Timeline v4 vs v5

**Date:** 2026-01-18
**Source:** Analyse comparative Windows (C:\Genosa\Working) vs Mac (assistant-gazelle-v5)

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Système v4 (Windows - C:\Genosa\Working)](#système-v4-windows)
3. [Système v5 (Mac - assistant-gazelle-v5)](#système-v5-mac)
4. [Comparaison Détaillée](#comparaison-détaillée)
5. [Recommandations pour v6](#recommandations-pour-v6)

---

## Vue d'ensemble

### Architecture v4 (Windows)
- **Plateforme:** Windows
- **Base de données:** SQL Server local
- **API:** GraphQL Gazelle (privée)
- **Mode d'import:** Historique complet + mises à jour quotidiennes
- **Scripts principaux:** `Import_all_data.py`, `Import_daily_update.py`, `timeline.py`

### Architecture v5 (Mac)
- **Plateforme:** macOS
- **Base de données:** Supabase (PostgreSQL cloud)
- **API:** GraphQL Gazelle (privée) avec OAuth2
- **Mode d'import:** Fenêtre glissante 7 jours + backfills historiques
- **Scripts principaux:** `sync_to_supabase.py`, `history_recovery_year_by_year.py`

---

## Système v4 (Windows)

### 📂 Structure des Scripts

#### 1. `Import_all_data.py` - Import Historique Complet

**Fenêtre temporelle:**
```python
EVENTS_END_DATE = datetime.now() + timedelta(days=365)   # +1 an futur
EVENTS_START_DATE = datetime.now() - timedelta(days=10*365)  # -10 ans passé
```

**Caractéristiques:**
- ✅ Récupère **10 ans d'historique**
- ✅ Inclut **1 an dans le futur** (rendez-vous planifiés)
- ✅ Utilise les filtres GraphQL `startOn` et `endOn`
- ⏱️ **Durée:** Longue (~plusieurs heures pour import complet)
- 🎯 **Usage:** Import initial ou réinitialisation complète

**Filtres GraphQL:**
```python
initial_filters = {
    "startOn": EVENTS_START_DATE.strftime('%Y-%m-%d'),
    "endOn": EVENTS_END_DATE.strftime('%Y-%m-%d'),
    "type": ["APPOINTMENT", "PERSONAL", "MEMO", "SYNCED"]
}
```

---

#### 2. `Import_daily_update.py` - Mises à Jour Quotidiennes

**Fenêtre temporelle:**
```python
EVENTS_END_DATE = datetime.now() + timedelta(days=90)   # +90 jours futur
EVENTS_START_DATE = datetime.now() - timedelta(days=60)  # -60 jours passé
```

**Caractéristiques:**
- ✅ Récupère **60 jours passés + 90 jours futurs** (150 jours total)
- ✅ Capture les modifications récentes et rendez-vous à venir
- ⏱️ **Durée:** Rapide (~quelques minutes)
- 🎯 **Usage:** Synchronisation quotidienne automatique
- 🔄 **Fréquence:** 1x par jour (cron/scheduler)

**Rationnelle:**
- 60 jours passés = capture corrections/notes tardives des techniciens
- 90 jours futurs = capture planification 3 mois à l'avance

---

#### 3. `timeline.py` - Timeline Entries

**Configuration:**
```python
# Set to 0 for a full re-import of all timeline entries.
# Set to any other number (e.g., 365) for a faster incremental sync.
LOOKBACK_DAYS = 365
```

**Caractéristiques:**
- ✅ **Mode 1:** `LOOKBACK_DAYS = 0` → Import complet (toutes les entrées)
- ✅ **Mode 2:** `LOOKBACK_DAYS = 365` → Dernière année seulement
- 🎯 **Flexibilité:** Paramètre configurable selon besoin
- ⏱️ **Durée:** Variable (0 = plusieurs heures, 365 = ~30 min)

**Usage typique:**
- Import initial: `LOOKBACK_DAYS = 0`
- Syncs quotidiennes: `LOOKBACK_DAYS = 365`

---

### 🔑 Points Clés v4

1. **Stratégie Double:**
   - Import complet (`Import_all_data.py`) → Utilisé rarement (setup initial)
   - Import incrémental (`Import_daily_update.py`) → Utilisé quotidiennement

2. **Fenêtres Temporelles:**
   - **Historique complet:** 10 ans passé + 1 an futur = **11 ans total**
   - **Quotidien:** 60 jours passé + 90 jours futur = **150 jours total**

3. **Filtres GraphQL:**
   - Utilise `startOn` et `endOn` pour limiter les données récupérées
   - Types filtrés: `APPOINTMENT`, `PERSONAL`, `MEMO`, `SYNCED`

4. **Base de données:**
   - SQL Server local (Windows)
   - Pas de contraintes de bande passante cloud

---

## Système v5 (Mac)

### 📂 Structure des Scripts

#### 1. `sync_to_supabase.py::sync_timeline_entries()` - Sync Quotidienne

**Fenêtre temporelle:**
```python
# Date de cutoff: 7 jours en arrière (fenêtre glissante)
now = datetime.now()
cutoff_date = now - timedelta(days=7)  # -7 jours uniquement
```

**Caractéristiques:**
- ✅ **Fenêtre glissante 7 jours** (optimisation 2026-01-11)
- ✅ Utilise filtre API `occurredAtGet` (>= cutoff)
- ✅ **UPSERT** avec `on_conflict=external_id` (anti-doublons)
- ⏱️ **Durée:** <30 secondes (~100-500 entrées)
- 🎯 **Usage:** Synchronisation automatique (scheduler 01:00 AM)

**Requête GraphQL:**
```graphql
query GetTimelineEntries($cursor: String, $occurredAtGet: CoreDateTime) {
    allTimelineEntries(first: 100, after: $cursor, occurredAtGet: $occurredAtGet) {
        edges {
            node {
                id
                occurredAt
                type
                summary
                comment
                client { id }
                piano { id }
                invoice { id }
                estimate { id }
                user { id }
            }
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
```

**Rationnelle 7 jours:**
- Base historique déjà dans Supabase
- Capture notes récentes de Margot et techniciens
- Corrections de la semaine incluses
- Performance optimisée (20x plus rapide que historique complet)
- Protection: Si sync échoue, le lendemain rattrape automatiquement

---

#### 2. `history_recovery_year_by_year.py` - Backfill Historique

**Fenêtre temporelle:**
```python
# Import année par année (ex: 2024 → 2016)
start_date = f"{year}-01-01T00:00:00Z"
end_date = f"{year}-12-31T23:59:59Z"
```

**Caractéristiques:**
- ✅ Import **année par année** (stratégie robuste)
- ✅ Batch de **500 entrées** par insertion
- ✅ **Gestion d'erreurs isolées** (continue si batch échoue)
- ✅ Retry entrée par entrée si batch échoue (FK manquantes)
- ⏱️ **Durée:** Variable (dépend du nombre d'années)
- 🎯 **Usage:** Récupération historique one-time

**Process:**
1. Récupère toutes les entrées depuis le début de l'année (`since_date`)
2. Filtre pour garder uniquement l'année cible
3. Insert par batch de 500 avec UPSERT (`on_conflict=external_id`)
4. Si batch échoue, retry entrée par entrée avec `user_id=NULL`

**Mapping des types:**
```python
type_mapping = {
    'APPOINTMENT': 'APPOINTMENT',
    'CONTACT_EMAIL': 'CONTACT_EMAIL',
    'CONTACT_EMAIL_AUTOMATED': 'CONTACT_EMAIL',
    'SERVICE_ENTRY_AUTOMATED': 'SERVICE_ENTRY_MANUAL',
    'SYSTEM_MESSAGE': 'SYSTEM_NOTIFICATION',
    'INVOICE': 'INVOICE_PAYMENT',
    'service': 'SERVICE_ENTRY_MANUAL',
    # ... défaut: 'NOTE'
}
```

**Extraction de mesures:**
```python
# Extrait humidité (%), température (°), fréquence (Hz) du texte
humidity_match = re.search(r'(\d+)\s*%', text)
temp_match = re.search(r'(\d+)\s*°', text)
freq_match = re.search(r'(\d+)\s*Hz', text, re.IGNORECASE)
```

---

#### 3. `core/gazelle_api_client.py::get_timeline_entries()` - API Client

**Méthode:**
```python
def get_timeline_entries(
    self,
    limit: Optional[int] = None,
    since_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Récupère les entrées de timeline avec pagination automatique.

    Args:
        limit: Nombre max d'entrées (None = toutes)
        since_date: Date ISO depuis laquelle récupérer (filtre occurredAtGet)
    """
```

**Caractéristiques:**
- ✅ **Pagination automatique** (cursor-based)
- ✅ Récupère 100 entrées par page (`first: 100`)
- ✅ Filtre optionnel `occurredAtGet` (>= date)
- ✅ Continue jusqu'à `hasNextPage = false`
- 🔄 **Retry automatique** sur erreurs réseau

**Champs récupérés:**
- `id` (external_id dans Supabase)
- `occurredAt` (CoreDateTime UTC)
- `type` (APPOINTMENT, SERVICE_ENTRY_MANUAL, etc.)
- `summary` (title dans Supabase)
- `comment` (description dans Supabase)
- `client { id }`, `piano { id }`, `user { id }`
- `invoice { id }`, `estimate { id }`

---

### 🔑 Points Clés v5

1. **Stratégie Hybride:**
   - Sync quotidienne: **7 jours glissants** (performance optimisée)
   - Backfill historique: **Année par année** (robustesse)

2. **Optimisations:**
   - UPSERT avec `on_conflict=external_id` → Aucun doublon
   - Fenêtre 7 jours → 20x plus rapide que v4 quotidien
   - Pagination automatique → Gère volumes importants

3. **Base de données:**
   - Supabase (PostgreSQL cloud)
   - Contraintes de bande passante → Optimisation critique

4. **Gestion d'erreurs:**
   - Retry par entrée si batch échoue
   - Mapping flexible des types (fallback `NOTE`)
   - Extraction automatique de mesures depuis texte

---

## Comparaison Détaillée

### 📊 Fenêtres Temporelles

| Aspect | v4 Windows | v5 Mac |
|--------|------------|--------|
| **Import Complet** | 10 ans passé + 1 an futur<br/>(11 ans total) | Année par année<br/>(flexible) |
| **Sync Quotidienne** | 60 jours passé + 90 jours futur<br/>(150 jours total) | 7 jours passé<br/>(7 jours total) |
| **Performance Quotidienne** | ~5-10 minutes | <30 secondes |
| **Gain v5 vs v4** | - | **20x plus rapide** |

### 🎯 Stratégies d'Import

#### v4 Windows - Approche "Large Filet"
```
┌─────────────────────────────────────────────┐
│  Import Quotidien: -60 jours → +90 jours   │
│  ════════════════════════════════════════   │
│  [────────────●─────────────────────────]   │
│        60j passé   NOW    90j futur         │
│                                              │
│  Volume: ~10,000-50,000 entrées/jour        │
│  Durée: 5-10 minutes                        │
└─────────────────────────────────────────────┘
```

**Avantages:**
- ✅ Capture exhaustive (3 mois de données)
- ✅ Rattrape corrections tardives (60 jours)
- ✅ Planification long terme (90 jours futurs)

**Inconvénients:**
- ❌ Volume élevé quotidiennement
- ❌ Durée d'exécution longue
- ❌ Bande passante importante

---

#### v5 Mac - Approche "Fenêtre Glissante"
```
┌─────────────────────────────────────────────┐
│  Sync Quotidienne: -7 jours seulement       │
│  ══════════════════════════════             │
│         [───────●]                          │
│          7j   NOW                           │
│                                              │
│  Volume: ~100-500 entrées/jour              │
│  Durée: <30 secondes                        │
└─────────────────────────────────────────────┘
```

**Avantages:**
- ✅ Performance ultra-rapide (20x)
- ✅ Bande passante minimale
- ✅ Capture notes récentes (Margot)
- ✅ Protection: Rattrapage automatique si échec

**Inconvénients:**
- ⚠️ Nécessite historique pré-chargé
- ⚠️ Moins de marge pour corrections tardives

**Solution v5:**
- Historique pré-chargé via `history_recovery_year_by_year.py`
- Backfills ponctuels si nécessaire

---

### 🔄 Gestion des Doublons

| Aspect | v4 Windows | v5 Mac |
|--------|------------|--------|
| **Méthode** | MERGE SQL Server | UPSERT Supabase |
| **Clé unique** | `id` (probablement) | `external_id` |
| **Comportement** | INSERT ou UPDATE | `on_conflict=external_id` |
| **Garantie** | Dépend config SQL | Mathématique (constraint unique) |

**v5 Protection anti-doublons:**
```python
# UPSERT avec on_conflict sur external_id (clé unique Gazelle)
url = f"{supabase_url}/gazelle_timeline_entries?on_conflict=external_id"
headers["Prefer"] = "resolution=merge-duplicates"

# Comportement:
# Sync 1: INSERT entry_123 → ✅ Créé
# Sync 2: UPSERT entry_123 → ✅ MAJ (pas de doublon)
# Sync 3: UPSERT entry_123 → ✅ MAJ (toujours pas de doublon)
```

---

### 📝 Mapping des Données

#### v4 Windows - Filtres de Types
```python
# Filtres explicites dans la requête
initial_filters = {
    "type": ["APPOINTMENT", "PERSONAL", "MEMO", "SYNCED"]
}
```

#### v5 Mac - Mapping Flexible
```python
# Accepte tous les types, mappe vers schéma Supabase
type_mapping = {
    'CONTACT_EMAIL_AUTOMATED': 'CONTACT_EMAIL',
    'SERVICE_ENTRY_AUTOMATED': 'SERVICE_ENTRY_MANUAL',
    'INVOICE': 'INVOICE_PAYMENT',
    'service': 'SERVICE_ENTRY_MANUAL',
    # ... défaut: 'NOTE'
}
```

**Avantage v5:**
- ✅ Plus flexible (accepte types inconnus)
- ✅ Fallback automatique (`NOTE`)
- ✅ Extraction automatique de mesures (%, °, Hz)

---

### 🛠️ Extraction de Mesures

| Aspect | v4 Windows | v5 Mac |
|--------|------------|--------|
| **Température** | ❓ (non documenté) | ✅ Regex: `(\d+)\s*°` |
| **Humidité** | ❓ (non documenté) | ✅ Regex: `(\d+)\s*%` |
| **Fréquence** | ❓ (non documenté) | ✅ Regex: `(\d+)\s*Hz` |
| **Stockage** | ❓ | `metadata` (JSONB) |

**v5 Exemple:**
```python
# Texte: "Piano accordé. 23°, 47%, 440Hz"
measurements = extract_measurements(comment)
# → {
#     "temperature": 23.0,
#     "humidity": 47.0,
#     "frequency": 440.0
# }
```

---

### ⚙️ Gestion d'Erreurs

#### v4 Windows
- ❓ Non documenté (probablement retry global)

#### v5 Mac
```python
# Stratégie multi-niveaux:
# 1. Tentative batch de 500
try:
    supabase.upsert(batch, on_conflict='external_id')
except:
    # 2. Retry entrée par entrée
    for record in batch:
        try:
            # 3. Fallback: user_id=NULL si FK manquante
            safe_record = record.copy()
            safe_record['user_id'] = None
            supabase.upsert(safe_record)
        except:
            stats['errors'] += 1
```

**Avantages v5:**
- ✅ Isolation d'erreurs (une entrée cassée ne bloque pas le batch)
- ✅ Fallback automatique (FK manquantes)
- ✅ Stats détaillées (success/errors/batches)

---

## Recommandations pour v6

### 🎯 Ce qui Fonctionne Bien

#### De v4 (à conserver):
1. **Fenêtre 60 jours passé pour corrections tardives**
   - Les techniciens ajoutent parfois notes 2-4 semaines après service
   - Recommandation v6: **Augmenter de 7 jours → 30 jours**

2. **Planification future (90 jours)**
   - Important pour dashboard rendez-vous
   - Recommandation v6: **Ajouter filtre futur si nécessaire**

3. **Double stratégie (complet + incrémental)**
   - Import initial + syncs quotidiennes
   - v5 fait déjà ça (backfill + 7 jours)

#### De v5 (à conserver):
1. **UPSERT avec on_conflict** → Anti-doublons mathématique
2. **Extraction automatique mesures** → Enrichissement données
3. **Mapping flexible types** → Robustesse
4. **Gestion erreurs multi-niveaux** → Fiabilité

---

### 📈 Améliorations Proposées v6

#### 1. **Fenêtre Temporelle Optimale**

**Proposition:**
```python
# Sync quotidienne v6 (compromis v4/v5)
cutoff_date_past = now - timedelta(days=30)     # 30 jours passé (vs 7 v5, 60 v4)
cutoff_date_future = now + timedelta(days=90)   # 90 jours futur (comme v4)

# Rationnelle:
# - 30 jours passé: Capture corrections tardives (compromis 7/60)
# - 90 jours futur: Capture planification (comme v4)
# - Volume: ~1,000-3,000 entrées (vs 100-500 v5, 10,000+ v4)
# - Durée estimée: 1-2 minutes (vs 30s v5, 5-10min v4)
```

**Avantages:**
- ✅ Meilleur équilibre performance/exhaustivité
- ✅ Capture corrections tardives (30 jours vs 7)
- ✅ Planification rendez-vous (90 jours futurs)
- ✅ Toujours 5x plus rapide que v4

---

#### 2. **Enrichissement avec PrivatePianoMeasurement**

**v5 déjà implémenté:**
```python
def _enrich_timeline_with_measurements(self):
    """
    v6: Enrichit timeline avec mesures de PrivatePianoMeasurement.

    Stratégie:
    1. Pour chaque piano récent, interroger allPianoMeasurements
    2. Si mesure existe dans PrivatePianoMeasurement → prioritaire
    3. Sinon, garder extraction texte (metadata)
    """
```

**Recommandation v6:**
- ✅ Conserver cette logique
- ✅ Ajouter logging pour traçabilité
- ✅ Stocker source mesure (`text_extraction` vs `piano_measurement`)

---

#### 3. **Mode Hybride Configurable**

**Proposition:**
```python
# Config dynamique selon contexte
SYNC_MODE = os.getenv("TIMELINE_SYNC_MODE", "balanced")  # fast|balanced|exhaustive

sync_configs = {
    "fast": {
        "days_past": 7,
        "days_future": 30,
        "description": "Mode rapide (<30s) - Notes récentes uniquement"
    },
    "balanced": {
        "days_past": 30,
        "days_future": 90,
        "description": "Mode équilibré (1-2min) - Corrections + planification"
    },
    "exhaustive": {
        "days_past": 60,
        "days_future": 365,
        "description": "Mode exhaustif (5-10min) - Maximum de données"
    }
}
```

**Usage:**
- Sync quotidienne: `SYNC_MODE=balanced` (défaut)
- Après maintenance: `SYNC_MODE=exhaustive` (ponctuel)
- Debug rapide: `SYNC_MODE=fast`

---

#### 4. **Monitoring et Alertes**

**Proposition:**
```python
# Logs détaillés dans sync_logs
{
    "script_name": "sync_timeline_v6",
    "sync_mode": "balanced",
    "window_config": {
        "days_past": 30,
        "days_future": 90,
        "cutoff_past": "2026-01-01T00:00:00Z",
        "cutoff_future": "2026-04-01T00:00:00Z"
    },
    "stats": {
        "fetched": 2500,
        "success": 2485,
        "errors": 15,
        "measurements_extracted": 342,
        "measurements_enriched": 89
    },
    "execution_time_seconds": 87,
    "status": "success"
}
```

**Alertes:**
- ⚠️ Si `execution_time_seconds` > seuil (mode dépendant)
- ⚠️ Si `errors` > 5% du total
- ⚠️ Si `fetched` = 0 (problème API)

---

### 📋 Checklist Migration v4 → v6

#### Phase 1: Analyse (FAIT ✅)
- [x] Documenter stratégie v4 Windows
- [x] Documenter stratégie v5 Mac
- [x] Identifier forces/faiblesses
- [x] Proposer optimisations v6

#### Phase 2: Implémentation
- [ ] Implémenter mode `balanced` (30j passé + 90j futur)
- [ ] Configurer `SYNC_MODE` dans `.env`
- [ ] Ajouter logging détaillé (window_config, stats)
- [ ] Implémenter alertes (execution_time, errors)

#### Phase 3: Tests
- [ ] Tester mode `fast` (7j passé, 30j futur)
- [ ] Tester mode `balanced` (30j passé, 90j futur)
- [ ] Tester mode `exhaustive` (60j passé, 365j futur)
- [ ] Vérifier performance (durée, volume)
- [ ] Vérifier qualité (aucun doublon, mesures extraites)

#### Phase 4: Validation
- [ ] Comparer volume v4 vs v6 (mode balanced)
- [ ] Vérifier corrections tardives capturées (30j passé)
- [ ] Vérifier rendez-vous futurs (90j futur)
- [ ] Valider extraction mesures vs PrivatePianoMeasurement

---

## 🎓 Leçons Apprises

### De v4 Windows:
1. **Large fenêtre = Sécurité mais coût performance**
   - 60 jours passé + 90 jours futur = exhaustif
   - Mais: 5-10 minutes quotidiennement

2. **Planification future importante**
   - Dashboard rendez-vous nécessite +90 jours
   - Ne pas optimiser au point de perdre cette vue

3. **Corrections tardives réelles**
   - Techniciens ajoutent notes 2-4 semaines après
   - 7 jours v5 probablement trop court

### De v5 Mac:
1. **UPSERT = Sécurité anti-doublons**
   - Constraint unique + on_conflict = mathématique
   - Permet syncs multiples sans risque

2. **Extraction automatique = Enrichissement**
   - Regex sur texte → mesures structurées
   - Valorise données existantes

3. **Gestion erreurs multi-niveaux = Robustesse**
   - Batch → Entrée individuelle → Fallback FK
   - Maximise taux de succès

### Pour v6:
1. **Compromis > Extrêmes**
   - Ni 7 jours (trop court) ni 60 jours (trop long)
   - 30 jours = sweet spot

2. **Configuration > Hard-code**
   - Modes (fast/balanced/exhaustive)
   - Adaptable selon contexte

3. **Monitoring > Espoir**
   - Logs détaillés + alertes
   - Détection proactive problèmes

---

## 📚 Références

### Documents v5 Mac:
- [RECAP_FINAL_IMPORTS.md](../RECAP_FINAL_IMPORTS.md) - Optimisation fenêtre 7 jours
- [VALIDATION_IMPORTS_NUIT.md](../docs/VALIDATION_IMPORTS_NUIT.md) - Validation stratégie v5
- [CSV_TO_SUPABASE_MAPPING.md](../CSV_TO_SUPABASE_MAPPING.md) - Mapping CSV → Supabase

### Scripts v5 Mac:
- [modules/sync_gazelle/sync_to_supabase.py](../modules/sync_gazelle/sync_to_supabase.py) - Sync quotidienne 7j
- [scripts/history_recovery_year_by_year.py](../scripts/history_recovery_year_by_year.py) - Backfill année par année
- [core/gazelle_api_client.py](../core/gazelle_api_client.py) - Client API GraphQL

### Scripts v4 Windows (C:\Genosa\Working):
- `Import_all_data.py` - Import complet 10 ans
- `Import_daily_update.py` - Sync quotidienne 60j passé + 90j futur
- `timeline.py` - Timeline avec LOOKBACK_DAYS configurable

---

**Document créé le:** 2026-01-18
**Par:** Assistant Claude Code + Allan Sutton
**Statut:** ✅ ANALYSE COMPLÈTE - PRÊT POUR v6
