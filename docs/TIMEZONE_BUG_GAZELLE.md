# BUG TIMEZONE GAZELLE - DOCUMENTATION

## 🔴 Problème Identifié

### Observation
Les heures de rendez-vous dans la DB sont décalées de **+5 heures** par rapport à l'affichage Gazelle.

**Exemple (Caroline Lessard - evt_xMjKE8YJCDQmRg7K):**
- Gazelle affiche: 09:15 (Toronto time)
- API Gazelle retourne: `2026-01-03T14:15:00Z` (UTC)
- DB contient: `19:15:00` (UTC) ❌
- Chat affiche: 14:15 (19:15 UTC - 5h) ❌

### Cause Racine

**Fichier**: `modules/sync_gazelle/sync_to_supabase.py` (lignes 439-456)

**Code problématique:**
```python
# IMPORTANT: Gazelle stocke les heures en Eastern Time (America/Toronto)
# mais ajoute un 'Z' trompeur. On doit interpréter comme Eastern, pas UTC.
dt_obj = dt.fromisoformat(start_time.replace('Z', ''))

# Marquer comme étant en Eastern Time (c'est ce que Gazelle utilise)
eastern_tz = ZoneInfo('America/Toronto')
dt_eastern = dt_obj.replace(tzinfo=eastern_tz)

# Stocker en UTC dans Supabase (TIMESTAMPTZ)
dt_utc = dt_eastern.astimezone(ZoneInfo('UTC'))
```

**Le commentaire est FAUX!**

Le 'Z' n'est PAS "trompeur" - c'est la vraie heure UTC. Gazelle retourne correctement:
- Affiche 09:15 à l'écran (Toronto)
- Retourne 14:15Z dans l'API (UTC, donc 09:15 + 5h = 14:15) ✅

**L'erreur:**
1. API retourne: `14:15Z` (déjà en UTC)
2. Code enlève le Z et interprète comme Eastern: `14:15-05:00`
3. Code convertit en UTC: `19:15+00:00` ❌ (ajoute ENCORE 5h)

**Résultat:** Double conversion = +5 heures d'erreur

## ✅ Solution

### Option 1: Correction SQL (Vue Normalisatrice)
**Principe:** Ne PAS toucher au code Python (Pilier 1), corriger via une vue SQL.

```sql
-- Vue qui soustrait les 5 heures en trop
CREATE OR REPLACE VIEW v_appointments_normalized AS
SELECT
    id,
    external_id,
    client_external_id,
    title,
    description,
    appointment_date,
    -- CORRECTION: Soustraire 5 heures
    (appointment_time::time - interval '5 hours')::time as appointment_time,
    duration_minutes,
    status,
    technicien,
    location,
    notes,
    created_at,
    updated_at
FROM gazelle_appointments;
```

**Utilisation:** Le Chat utilise `v_appointments_normalized` au lieu de `gazelle_appointments`.

### Option 2: Fix dans le Code (Non Recommandé)
Si vraiment nécessaire, corriger `sync_to_supabase.py`:

```python
# CORRECT: Gazelle retourne déjà en UTC (le 'Z' est fiable)
dt_utc = datetime.fromisoformat(start_time)  # Parse avec le Z
appointment_time = dt_utc.time().isoformat()
```

**⚠️ ATTENTION:** Cette option nécessite de re-sync TOUTES les données historiques.

## 📊 Validation

### Test avec Caroline Lessard
```bash
# Vérifier que l'heure est correcte
curl "$SUPABASE_URL/rest/v1/v_appointments_normalized?external_id=eq.evt_xMjKE8YJCDQmRg7K&select=appointment_time"
# Doit retourner: 09:15:00
```

### Étalon de Mesure
Caroline Lessard (evt_xMjKE8YJCDQmRg7K) est notre **cas de référence**:
- Gazelle: 09:15 - 16:40 (Toronto)
- DB corrigée: 09:15 (Montreal) = 14:15 (UTC)

Si Caroline affiche 09:15, tout le reste est correct.

## 📝 Constante de Correction

```python
# Constante documentée pour référence
GAZELLE_TIMEZONE_BUG_OFFSET_HOURS = 5

# Application (dans la vue SQL uniquement)
corrected_time = appointment_time - interval '5 hours'
```

## 🔒 Règle V6

**LA LOI DE LA "SOURCE SALE":**

> Si la donnée dans la DB est corrompue, il est INTERDIT de corriger ça dans le code de l'assistant (Python).
> Pourquoi ? Parce qu'un jour tu auras une donnée propre, et ton "correctif" la brisera à son tour.

**Action à prendre:**
1. ✅ Créer une vue SQL de correction (`v_appointments_normalized`)
2. ✅ Documenter le bug (ce fichier)
3. ✅ Utiliser la vue comme source unique pour le Chat
4. ❌ NE PAS toucher au code `service.py`

## 📅 Date de Découverte

**Date:** 2025-12-29
**Session:** Conversation sur le fix de Vincent d'Indy
**Découvert par:** Analyse comparative Gazelle API vs DB

## 🔗 Fichiers Liés

- `modules/sync_gazelle/sync_to_supabase.py` (lignes 439-456) - Code problématique
- `api/chat/service.py` (lignes 689-725) - Conversion UTC→Montreal (correcte)
- `assistant-v6/sql/CREATE_VIEW_appointments_normalized.sql` - Vue de correction
