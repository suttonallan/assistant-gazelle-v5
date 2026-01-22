# V6 - Leçons Apprises de la V5

**Consolidation des incidents, optimisations et bonnes pratiques**
**Dernière mise à jour :** 2026-01-21

---

## Table des Matières

1. [Timezone et Dates](#1-timezone-et-dates)
2. [Synchronisation et Protection des Données](#2-synchronisation-et-protection-des-données)
3. [Import et Performance](#3-import-et-performance)
4. [Rapport Timeline](#4-rapport-timeline)
5. [Checklist V6](#checklist-v6)

---

## 1. Timezone et Dates

### Incident du 2026-01-21 : Dates décalées d'un jour

**Symptôme :**
- "Demain" affichait après-demain
- "Après-demain" affichait la même date que demain
- Services envoyés à Gazelle datés du lendemain

**Cause racine :**
Le serveur Render fonctionne en **UTC**. À 22h Montréal = 03:00 UTC **le lendemain**.

```python
# BUG : datetime.now() retourne UTC sur le serveur
event_date = datetime.now().isoformat()  # 2026-01-22T03:00:00 (lendemain!)

# CORRIGÉ : Utiliser le timezone Montréal
from core.timezone_utils import MONTREAL_TZ
event_date = datetime.now(MONTREAL_TZ).isoformat()  # 2026-01-21T22:00:00-05:00
```

### Règles V6

#### 1.1 Toujours utiliser MONTREAL_TZ

```python
from core.timezone_utils import MONTREAL_TZ
from datetime import datetime, timedelta

# Date/heure actuelle
now = datetime.now(MONTREAL_TZ)

# Demain, après-demain
tomorrow = (now + timedelta(days=1)).date()
day_after = (now + timedelta(days=2)).date()
```

#### 1.2 Patterns manuels AVANT dateparser

dateparser peut être incohérent. Les patterns courants doivent être vérifiés EN PREMIER :

```python
now_mtl = datetime.now(MONTREAL_TZ)

# PRIORITÉ : après-demain EN PREMIER (contient "demain")
if "après-demain" in query_lower:
    return (now_mtl + timedelta(days=2)).date()

if "demain" in query_lower:
    return (now_mtl + timedelta(days=1)).date()

if "aujourd'hui" in query_lower:
    return now_mtl.date()

# ENSUITE : dateparser pour formats complexes
parsed = dateparser.parse(query, settings={'RELATIVE_BASE': now_mtl})
```

#### 1.3 Module timezone_utils

Utiliser `core/timezone_utils.py` qui fournit :
- `MONTREAL_TZ` - ZoneInfo pour America/Montreal
- `montreal_to_utc()` - Convertir vers UTC
- `utc_to_montreal()` - Convertir depuis UTC
- `format_for_gazelle_filter()` - Format ISO pour API Gazelle

#### 1.4 Tests recommandés

Tester les calculs de dates à différentes heures :
- 10h Montréal (15h UTC même jour) ✓
- 20h Montréal (01h UTC lendemain) ⚠️
- 23h Montréal (04h UTC lendemain) ⚠️ **Zone critique**

### Fichiers corrigés en V5
- `core/gazelle_api_client.py`
- `core/gazelle_push_service.py`
- `api/chat/service.py`
- `api/tableau_de_bord_routes.py`
- `modules/alertes_rv/checker.py`
- `modules/alertes_rv/service.py`

---

## 2. Synchronisation et Protection des Données

### Incident du 2026-01-19 : Perte des Tags Institutionnels

**Symptôme :**
- Inventaire institutionnel invisible
- Badge PLS disparu
- 340 pianos ont perdu le flag `dampp_chaser_installed`

**Cause racine :**
L'UPSERT écrasait les tags avec `[]` si l'API Gazelle n'en retournait pas.

```python
# BUG : Écrase les tags même si vide
client_record = {
    'tags': tags,  # Si tags=[] → écrase les tags manuels!
}

# CORRIGÉ : Ne pas inclure si vide
client_record = { ... }
if tags:  # Seulement si l'API retourne des tags
    client_record['tags'] = tags
```

### Règles V6

#### 2.1 Préserver les données manuelles

```python
# Champs "manuels" à ne JAMAIS écraser si vide:
PROTECTED_FIELDS = [
    'tags',              # Tags manuels (institutional)
    'dampp_chaser_installed',  # Flag PLS manuel
    'notes',             # Notes manuelles
]

# Pattern de protection:
for field in PROTECTED_FIELDS:
    value = api_data.get(field)
    if value:  # Seulement si l'API retourne une valeur
        record[field] = value
    # Sinon : PostgreSQL préserve la valeur existante
```

#### 2.2 Documenter les champs manuels

| Table | Champ | Source | Protection |
|-------|-------|--------|------------|
| `gazelle_clients` | `tags` | Manuel (institutional) | Ne pas écraser si vide |
| `gazelle_pianos` | `dampp_chaser_installed` | Script détection | Ne pas écraser si vide |
| `gazelle_pianos` | `notes` | Manuel | Ne pas écraser si vide |

#### 2.3 Effets en cascade

Toujours considérer les **dépendances** entre tables :
```
tags perdus → Clients non identifiés
           → Inventaire invisible
           → Sync pianos échoue aussi
           → Flags PLS perdus
           → Badge invisible
```

### Clients institutionnels à protéger

| Institution | External ID |
|-------------|-------------|
| École Vincent-d'Indy | `cli_9UMLkteep8EsISbG` |
| Place des Arts | `cli_HbEwl9rN11pSuDEU` |
| UQAM (Pierre-Péladeau) | `cli_sos6RK8t4htOApiM` |
| SMCQ | `cli_UVMjT9g1b1wDkRHr` |
| Fondation Vincent-d'Indy | `cli_xkMYNQrSX7T7E1q0` |

---

## 3. Import et Performance

### Comparaison V4 vs V5

| Aspect | V4 Windows | V5 Mac | V6 Recommandé |
|--------|------------|--------|---------------|
| Sync quotidienne | 60j passé + 90j futur | 7j passé | **30j passé + 90j futur** |
| Performance | 5-10 min | <30 sec | 1-2 min |
| Corrections tardives | ✅ (60j) | ⚠️ (7j) | ✅ (30j) |
| Planification future | ✅ (90j) | ❌ | ✅ (90j) |

### Règles V6

#### 3.1 Fenêtre temporelle optimale

```python
# Mode balanced (défaut recommandé)
cutoff_past = now - timedelta(days=30)    # 30 jours passé
cutoff_future = now + timedelta(days=90)  # 90 jours futur

# Rationnelle:
# - 30j passé: Capture corrections tardives des techniciens
# - 90j futur: Capture planification rendez-vous
# - Performance: ~1-2 minutes (vs 30s v5, 5-10min v4)
```

#### 3.2 Modes configurables

```python
SYNC_MODES = {
    "fast": {
        "days_past": 7,
        "days_future": 30,
        "use_case": "Debug rapide, tests"
    },
    "balanced": {
        "days_past": 30,
        "days_future": 90,
        "use_case": "Sync quotidienne (défaut)"
    },
    "exhaustive": {
        "days_past": 60,
        "days_future": 365,
        "use_case": "Après maintenance, rattrapage"
    }
}
```

#### 3.3 UPSERT anti-doublons

```python
# Toujours utiliser on_conflict avec external_id
supabase.upsert(records, on_conflict='external_id')

# Garantie mathématique: pas de doublons
```

#### 3.4 Gestion d'erreurs multi-niveaux

```python
try:
    # 1. Tentative batch
    supabase.upsert(batch)
except:
    # 2. Retry entrée par entrée
    for record in batch:
        try:
            supabase.upsert(record)
        except:
            # 3. Fallback: user_id=NULL si FK manquante
            record['user_id'] = None
            supabase.upsert(record)
```

---

## 4. Rapport Timeline

### Structure et Déduplication

**Problème identifié :** Données importées avec 2 préfixes (`tle_` et `tme_`)

**Solution :**
```python
# Déduplication par signature
signature = f"{date[:10]}|||{description[:200]}"

# Priorité: garder tme_ (nouveau système)
if len(group) > 1:
    tme_entries = [e for e in group if e['external_id'].startswith('tme_')]
    if tme_entries:
        return tme_entries[0]
```

### Mots-clés alertes maintenance

**38 mots-clés officiels** dans `core/humidity_alert_detector.py` :

| Catégorie | Exemples |
|-----------|----------|
| Housse | housse retirée, sans housse |
| Dampp-Chaser | débranché, pls off, rebranché |
| Réservoir | réservoir vide, tank empty |
| Environnement | fenêtre ouverte, trop froid |
| Humidité | humidité haute, très sec |

### Conversion timezone dans rapports

```python
from zoneinfo import ZoneInfo
MONTREAL_TZ = ZoneInfo("America/Montreal")

# UTC → Montréal pour affichage
dt = datetime.fromisoformat(occurred_at)
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
date_montreal = dt.astimezone(MONTREAL_TZ).strftime("%Y-%m-%d")
```

---

## Checklist V6

### Timezone
- [ ] Auditer tous les `datetime.now()` sans timezone
- [ ] Remplacer par `datetime.now(MONTREAL_TZ)`
- [ ] Patterns manuels avant dateparser
- [ ] Tests unitaires avec mock de différentes heures (10h, 20h, 23h)

### Synchronisation
- [ ] Protéger champs manuels (tags, dampp_chaser, notes)
- [ ] Documenter tous les champs protégés
- [ ] Ajouter test: "Sync ne doit pas écraser les tags institutionnels"
- [ ] Script de vérification post-sync

### Import
- [ ] Implémenter mode `balanced` (30j passé + 90j futur)
- [ ] Configurer `SYNC_MODE` dans `.env`
- [ ] UPSERT avec `on_conflict=external_id` partout
- [ ] Gestion erreurs multi-niveaux

### Monitoring
- [ ] Logs détaillés (window_config, stats)
- [ ] Alertes si `execution_time > seuil`
- [ ] Alertes si `errors > 5%`
- [ ] Vérification automatique tags institutionnels

---

## Documents Sources

| Document | Contenu |
|----------|---------|
| [INCIDENT_2026-01-19_TAGS_PERDUS.md](INCIDENT_2026-01-19_TAGS_PERDUS.md) | Post-mortem tags perdus |
| [RAPPORT_TIMELINE_V5_RECETTE.md](RAPPORT_TIMELINE_V5_RECETTE.md) | Documentation rapport |
| [V4_IMPORT_CHARACTERIZATION.md](V4_IMPORT_CHARACTERIZATION.md) | Comparaison V4/V5 |

---

**Consolidé par :** Claude + Allan Sutton
**Date :** 2026-01-21
