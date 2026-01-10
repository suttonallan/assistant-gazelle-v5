# Gestion des Timezones et Déduplication - Recommandations API Gazelle

## 📅 Contexte

Ce document décrit les 4 optimisations critiques implémentées pour la synchronisation Gazelle → Supabase, basées sur les recommandations officielles de la documentation API Gazelle.

## ✅ 1. Timezone: Conversion America/Montreal → UTC

### Problème

L'API Gazelle utilise **America/Montreal** (EST/EDT) comme timezone locale, mais l'API GraphQL attend des timestamps en **UTC** (ISO-8601 avec 'Z' ou offset) pour les filtres de date.

### Solution

Toutes les dates envoyées à Gazelle sont maintenant converties de Montreal → UTC via le module `core/timezone_utils.py`.

**Exemples:**
```python
# AVANT (❌ Incorrect - envoyé en timezone locale)
start_date = "2026-01-09"  # Ambigu - quelle timezone?

# APRÈS (✅ Correct - converti en UTC)
start_date = format_for_gazelle_filter(date(2026, 1, 9))
# → "2026-01-09T05:00:00Z"  # 00:00 EST = 05:00 UTC
```

**Filtres affectés:**
- `occurredAtGet` (Timeline entries)
- `start` dans `allEventsBatched` (Appointments)
- Tous les filtres de date/heure dans les queries GraphQL

### Fonctions utilitaires

```python
from core.timezone_utils import (
    format_for_gazelle_filter,  # Date Montreal → UTC pour filtres API
    parse_gazelle_datetime,     # Parser CoreDateTime de Gazelle
    format_for_supabase,        # Formater pour stockage Supabase
    extract_date_time           # Extraire date/heure séparées (Montreal)
)
```

## ✅ 2. Déduplication: UPSERT avec clés uniques

### Problème

Avant, les syncs créaient des doublons si un enregistrement existait déjà.

### Solution

Utilisation systématique de la méthode `.upsert()` de Supabase avec les IDs uniques de Gazelle comme clés de conflit.

**Implémentation REST API:**
```python
url = f"{supabase_url}/gazelle_appointments?on_conflict=external_id"
headers["Prefer"] = "resolution=merge-duplicates"
response = requests.post(url, headers=headers, json=record)
```

**Clés de déduplication par table:**
- `gazelle_clients`: `external_id` (Gazelle client ID)
- `gazelle_contacts`: `external_id` (Gazelle contact ID)
- `gazelle_pianos`: `external_id` (Gazelle piano ID)
- `gazelle_appointments`: `external_id` (Gazelle event ID)
- `gazelle_timeline_entries`: `external_id` (Gazelle timeline entry ID)

**Comportement:**
- Si l'enregistrement existe → **UPDATE** (écrase avec nouvelles valeurs)
- Si l'enregistrement n'existe pas → **INSERT** (crée nouveau)
- Aucun doublon possible, même en cas de syncs multiples

## ✅ 3. Format: CoreDateTime complet avec timezone

### Problème

Avant, on stockait seulement `appointment_date` (date) et `appointment_time` (time) séparément, perdant l'information de timezone.

### Solution

Ajout de la colonne `start_datetime TIMESTAMPTZ` dans `gazelle_appointments` pour stocker le **CoreDateTime complet** avec timezone.

**Migration SQL:**
```sql
ALTER TABLE gazelle_appointments
ADD COLUMN IF NOT EXISTS start_datetime TIMESTAMPTZ;

-- Index pour requêtes par date
CREATE INDEX idx_gazelle_appointments_start_datetime
ON gazelle_appointments(start_datetime);
```

**Stockage:**
```python
# CoreDateTime de Gazelle: "2026-01-09T19:30:00Z"
dt_parsed = parse_gazelle_datetime(start_time)
start_datetime_utc = format_for_supabase(dt_parsed)
# → "2026-01-09T19:30:00Z" (UTC)

# Stockage dans Supabase
appointment_record = {
    'start_datetime': start_datetime_utc,      # CoreDateTime complet (UTC)
    'appointment_date': appointment_date,       # Date en Montreal (legacy)
    'appointment_time': appointment_time,       # Heure en Montreal (legacy)
    'created_at': start_datetime_utc,
    'updated_at': format_for_supabase(datetime.now())
}
```

**Avantages:**
- Précision maximale (conserve timezone, pas de perte d'info)
- Requêtes timezone-aware possibles (ex: calculs de durée)
- Compatibilité avec les colonnes legacy (`appointment_date` / `appointment_time`)

## ✅ 4. Logique d'alerte: Timeline plutôt que champ manuel

### Problème

Les alertes de maintenance institutionnelle utilisaient le champ `lastTunedDate` du piano, qui est mis à jour **manuellement** et peut être incorrect.

### Solution

**Basculer les alertes sur `occurred_at` des entrées de Timeline** (type `SERVICE_ENTRY_MANUAL`), qui reflètent les événements réels.

**Query Supabase recommandée:**
```sql
-- Trouver la dernière maintenance pour un piano
SELECT
    piano_id,
    MAX(occurred_at) as last_service_date
FROM gazelle_timeline_entries
WHERE
    entry_type = 'SERVICE_ENTRY_MANUAL'
    AND piano_id IS NOT NULL
GROUP BY piano_id;
```

**Logique d'alerte (à implémenter):**
```python
# Pour chaque piano institutionnel
last_service = get_last_timeline_service(piano_id)

if last_service:
    days_since_service = (datetime.now() - last_service['occurred_at']).days

    if days_since_service > 365:
        create_maintenance_alert(
            piano_id=piano_id,
            last_service_date=last_service['occurred_at'],
            days_overdue=days_since_service - 365
        )
```

**Avantages:**
- Source de vérité fiable (Timeline = événements réels)
- Automatique (pas besoin de mise à jour manuelle du champ `lastTunedDate`)
- Auditabilité (Timeline conserve l'historique complet)

## 📊 Impact des Changements

### Avant (❌ Problèmes)

1. **Timezone**: Dates ambiguës → résultats API incorrects
2. **Déduplication**: Doublons créés à chaque sync
3. **Format**: Perte d'info timezone (date/time séparés)
4. **Alertes**: Basées sur champ manuel potentiellement incorrect

### Après (✅ Optimisé)

1. **Timezone**: Dates UTC précises → résultats API corrects
2. **Déduplication**: UPSERT automatique → aucun doublon
3. **Format**: CoreDateTime complet → précision maximale
4. **Alertes**: Timeline comme source → données fiables

## 🧪 Tests de Validation

### Test 1: Timezone Conversion

```python
from core.timezone_utils import format_for_gazelle_filter
from datetime import date

# 2026-01-09 00:00 Montreal (hiver = EST)
result = format_for_gazelle_filter(date(2026, 1, 9))
assert result == "2026-01-09T05:00:00Z"  # EST = UTC-5
```

### Test 2: Déduplication

```bash
# Lancer sync 2 fois
python3 modules/sync_gazelle/sync_to_supabase.py
python3 modules/sync_gazelle/sync_to_supabase.py

# Vérifier aucun doublon
SELECT external_id, COUNT(*) as count
FROM gazelle_appointments
GROUP BY external_id
HAVING COUNT(*) > 1;
-- Résultat attendu: 0 rows
```

### Test 3: CoreDateTime Stockage

```sql
-- Vérifier que start_datetime contient timezone
SELECT
    external_id,
    start_datetime,
    EXTRACT(TIMEZONE FROM start_datetime) as tz_offset
FROM gazelle_appointments
LIMIT 5;
-- tz_offset doit être 0 (UTC)
```

## 📚 Références

- **Gazelle API Docs**: https://docs.gazelle-api.com
- **CoreDateTime**: Format ISO-8601 avec timezone obligatoire
- **occurredAtGet**: Filtre de date pour Timeline (≥ date fournie)
- **America/Montreal**: Timezone locale (EST/EDT)
- **UPSERT Supabase**: https://supabase.com/docs/guides/database/postgres/upsert

## 🔄 Prochaines Étapes

1. ✅ Implémenter `timezone_utils.py`
2. ✅ Modifier `sync_to_supabase.py` pour utiliser conversions timezone
3. ✅ Ajouter colonne `start_datetime` à `gazelle_appointments`
4. ⏳ Migrer alertes maintenance pour utiliser Timeline
5. ⏳ Ajouter tests unitaires pour conversions timezone
6. ⏳ Documenter logique d'alerte Timeline dans code

## 📞 Support

Pour questions sur les timezones ou la déduplication:
- Consulter la doc API Gazelle
- Lire les commentaires dans `core/timezone_utils.py`
- Vérifier les logs de sync dans Dashboard → Notifications → Tâches & Imports
