# Critères de Filtrage - Rapports Timeline V5

**Source:** `ptm_report_sheets.py` lignes 58-143, 249-253
**Pour:** Cursor Mac - Migration V5
**Date:** 2025-12-22

---

## 📊 RÈGLES DE FILTRAGE PAR INSTITUTION

### Mapping Institutions → Filtres SQL

```python
institutions = {
    "UQAM": "c.CompanyName LIKE '%UQAM%' OR c.CompanyName LIKE '%Pierre-Péladeau%' OR c.CompanyName LIKE '%Pierre Peladeau%'",
    "Vincent": "c.CompanyName LIKE '%Vincent-d''Indy%' OR c.CompanyName LIKE '%Vincent d Indy%'",
    "Place des Arts": "c.CompanyName LIKE '%Place des Arts%'"
}
```

### Équivalent Supabase (V5)

**Table:** `gazelle_clients`
**Colonne:** `company_name`

```python
# Pour UQAM
supabase.table('timeline_entries') \
    .select('*, piano:gazelle_pianos(*, client:gazelle_clients(*)), user:users(*)') \
    .or_('client.company_name.ilike.%UQAM%,client.company_name.ilike.%Pierre-Péladeau%,client.company_name.ilike.%Pierre Peladeau%')

# Pour Vincent
supabase.table('timeline_entries') \
    .select('*, piano:gazelle_pianos(*, client:gazelle_clients(*)), user:users(*)') \
    .or_('client.company_name.ilike.%Vincent-d''Indy%,client.company_name.ilike.%Vincent d Indy%')

# Pour Place des Arts
supabase.table('timeline_entries') \
    .select('*, piano:gazelle_pianos(*, client:gazelle_clients(*)), user:users(*)') \
    .ilike('client.company_name', '%Place des Arts%')
```

---

## 🗂️ SOURCES DE DONNÉES (MAPPING SQL → SUPABASE)

### Requête V4 (SQL Server)

```sql
SELECT
    CONVERT(varchar, te.OccurredAt, 120) AS DateEvenement,
    p.Id as PianoId,
    CASE
        WHEN te.EntryType = 'SERVICE_ENTRY_MANUAL' THEN 'Service'
        WHEN te.EntryType = 'PIANO_MEASUREMENT' THEN 'Mesure'
        ELSE te.EntryType
    END AS TypeEvenement,
    CASE
        WHEN te.Title IS NOT NULL AND te.Title != '' THEN te.Title
        WHEN te.Details IS NOT NULL AND te.Details != '' THEN te.Details
        ELSE 'Evenement'
    END AS Description,
    ISNULL(c.CompanyName, 'Client non specifie') AS NomClient,
    ISNULL(p.Make, '') AS Marque,
    ISNULL(p.Model, '') AS Modele,
    ISNULL(p.SerialNumber, '') AS NumeroSerie,
    ISNULL(p.Type, '') AS TypePiano,
    ISNULL(CAST(p.Year AS varchar), '') AS Annee,
    ISNULL(p.Location, '') AS Local,
    ISNULL(u.FirstName, '') AS Technicien,
    ISNULL(p.Notes, '') AS NotesGenerales
FROM TimelineEntries te
LEFT JOIN Pianos p ON p.Id = te.PianoId
LEFT JOIN Users u ON u.Id = te.UserId
LEFT JOIN Clients c ON c.Id = p.ClientId
WHERE te.OccurredAt >= '2025-07-01'
  AND ({filter_sql})
  AND te.EntryType IN ('SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT')
ORDER BY te.OccurredAt DESC
```

### Mapping colonnes Supabase (V5)

| Colonne Rapport | Table Supabase | Colonne Supabase | Notes |
|----------------|----------------|------------------|-------|
| **DateEvenement** | `timeline_entries` | `occurred_at` | Convertir UTC → Montreal |
| **PianoId** | `timeline_entries` | `piano_id` | ID Gazelle |
| **TypeEvenement** | `timeline_entries` | `entry_type` | Mapper: `SERVICE_ENTRY_MANUAL` → `'Service'`, `PIANO_MEASUREMENT` → `'Mesure'` |
| **Description** | `timeline_entries` | `title` ou `details` | Priorité: `title` si existe, sinon `details` |
| **NomClient** | `gazelle_clients` | `company_name` | Via `piano.client.company_name` |
| **Marque** | `gazelle_pianos` | `make` | Via `piano.make` |
| **Modele** | `gazelle_pianos` | `model` | Via `piano.model` |
| **NumeroSerie** | `gazelle_pianos` | `serial_number` | Via `piano.serial_number` |
| **TypePiano** | `gazelle_pianos` | `type` | Via `piano.type` |
| **Annee** | `gazelle_pianos` | `year` | Via `piano.year` (convertir en string) |
| **Local** | `gazelle_pianos` | `location` | Via `piano.location` |
| **Technicien** | `users` | `full_name` ou `username` | Via `user.full_name` |
| **NotesGenerales** | `gazelle_pianos` | `notes` | Via `piano.notes` |

---

## 🔍 FILTRES APPLIQUÉS

### 1. Filtre de date

**V4:**
```sql
WHERE te.OccurredAt >= '2025-07-01'
```

**V5:**
```python
.gte('occurred_at', '2025-07-01T00:00:00Z')
```

### 2. Filtre de type d'événement

**V4:**
```sql
AND te.EntryType IN ('SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT')
```

**V5:**
```python
.in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT'])
```

### 3. Filtre par institution

**Voir section [Règles de filtrage](#📊-règles-de-filtrage-par-institution)**

---

## 📐 LOGIQUE D'AGRÉGATION (MESURES D'HUMIDITÉ)

### Règle importante: Grouper mesures par piano ET par jour

**V4 (lignes 100-143):**

```python
# 1. Créer colonne DateOnly (sans heure)
df['DateOnly'] = pd.to_datetime(df['DateEvenement']).dt.tz_convert('America/Montreal').dt.date

# 2. Isoler les mesures
mesures = df[df['TypeEvenement'] == 'Mesure'].copy()

# 3. Simplifier description mesure
def simplify_mesure(desc):
    if 'Piano measurement taken:' in desc:
        return desc.split(':', 1)[1].strip()
    elif '°' in desc and '%' in desc:
        return desc.strip()
    return ''

mesures['MesureHumidite'] = mesures['Description'].apply(simplify_mesure)

# 4. Agréger les mesures PAR PIANO ET PAR JOUR
aggregated_mesures = mesures.groupby(['PianoId', 'DateOnly']).agg(
    MesureHumidite=('MesureHumidite', lambda x: ' | '.join(x.dropna()))
).reset_index()

# 5. Fusionner avec services
services = df[df['TypeEvenement'] == 'Service'].copy()
df_merged = pd.merge(
    services,
    aggregated_mesures,
    on=['PianoId', 'DateOnly'],
    how='left'
)

# 6. Ajouter mesures orphelines (sans service le même jour)
merged_check = pd.merge(mesures, services, on=['PianoId', 'DateOnly'], how='left', indicator=True)
orphelines = merged_check[merged_check['_merge'] == 'left_only']

# 7. Combiner tout
df_final = pd.concat([df_merged, orphelines], ignore_index=True).sort_values(by='DateEvenement', ascending=False)
```

### Exemples de transformation

**Mesure brute:**
```
"Piano measurement taken: 20°C, 42%"
```

**Mesure simplifiée:**
```
"20°C, 42%"
```

**Plusieurs mesures le même jour:**
```
"20°C, 42% | 21°C, 45%"
```

---

## 📋 COLONNES FINALES DU RAPPORT

**Ordre des colonnes dans le Google Sheet:**

1. `DateEvenement` - Date/heure au fuseau Montreal (YYYY-MM-DD HH:MM)
2. `TypeEvenement` - "Service" ou "Mesure"
3. `Description` - Description de l'événement
4. `NomClient` - Nom du client (UQAM, Vincent, Place des Arts)
5. `Marque` - Marque du piano (Steinway, Yamaha, etc.)
6. `Modele` - Modèle du piano
7. `NumeroSerie` - Numéro de série
8. `TypePiano` - Type (Grand, Upright, etc.)
9. `Annee` - Année de fabrication
10. `Local` - Localisation du piano
11. `Technicien` - Nom du technicien
12. `NotesGenerales` - Notes générales du piano
13. `MesureHumidite` - Mesures agrégées (seulement si service ou mesure orpheline)

---

## 🎯 EXEMPLE DE CODE V5

```python
from modules.core.storage import SupabaseStorage
import pandas as pd
from datetime import datetime
import pytz

def get_institution_data_v5(storage: SupabaseStorage, institution_filter: str):
    """
    Récupère les données timeline pour une institution (V5 Supabase)

    Args:
        storage: Instance SupabaseStorage
        institution_filter: Filtre Supabase (ex: "client.company_name.ilike.%UQAM%")
    """

    # 1. Récupérer les timeline entries avec relations
    response = storage.client.table('timeline_entries') \
        .select('''
            occurred_at,
            piano_id,
            entry_type,
            title,
            details,
            user_id,
            piano:gazelle_pianos (
                id,
                make,
                model,
                serial_number,
                type,
                year,
                location,
                notes,
                client:gazelle_clients (
                    company_name
                )
            ),
            user:users (
                full_name
            )
        ''') \
        .gte('occurred_at', '2025-07-01T00:00:00Z') \
        .in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT']) \
        .or_(institution_filter) \
        .order('occurred_at', desc=True) \
        .execute()

    # 2. Convertir en DataFrame
    data = response.data
    if not data:
        return pd.DataFrame()

    # 3. Mapper les colonnes
    rows = []
    for entry in data:
        piano = entry.get('piano') or {}
        client = piano.get('client') or {}
        user = entry.get('user') or {}

        # Type événement
        entry_type_map = {
            'SERVICE_ENTRY_MANUAL': 'Service',
            'PIANO_MEASUREMENT': 'Mesure'
        }
        type_evt = entry_type_map.get(entry.get('entry_type'), entry.get('entry_type'))

        # Description
        description = entry.get('title') or entry.get('details') or 'Evenement'

        rows.append({
            'DateEvenement': entry.get('occurred_at'),
            'PianoId': entry.get('piano_id'),
            'TypeEvenement': type_evt,
            'Description': description,
            'NomClient': client.get('company_name') or 'Client non specifie',
            'Marque': piano.get('make') or '',
            'Modele': piano.get('model') or '',
            'NumeroSerie': piano.get('serial_number') or '',
            'TypePiano': piano.get('type') or '',
            'Annee': str(piano.get('year') or ''),
            'Local': piano.get('location') or '',
            'Technicien': user.get('full_name') or '',
            'NotesGenerales': piano.get('notes') or ''
        })

    df = pd.DataFrame(rows)

    # 4. Appliquer logique d'agrégation mesures (identique V4)
    # ... (code lignes 100-143 de V4)

    return df
```

---

## ⚠️ POINTS CRITIQUES

### 1. Conversion fuseau horaire

**OBLIGATOIRE:** Convertir toutes les dates UTC → America/Montreal

```python
from datetime import datetime
import pytz

def convert_to_montreal_time(utc_datetime_str):
    if not utc_datetime_str:
        return ""

    # Parser ISO 8601 (Supabase retourne ce format)
    dt = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))

    # Convertir vers Montreal
    montreal_tz = pytz.timezone('America/Montreal')
    montreal_dt = dt.astimezone(montreal_tz)

    return montreal_dt.strftime('%Y-%m-%d %H:%M')
```

### 2. Agrégation par jour (DateOnly)

**CRITIQUE:** Utiliser la date **après conversion** vers Montreal, pas l'UTC

```python
df['DateOnly'] = pd.to_datetime(df['DateEvenement']).dt.tz_convert('America/Montreal').dt.date
```

### 3. Mesures orphelines

**Ne PAS oublier** d'inclure les mesures qui n'ont pas de service le même jour:

```python
# Identifier mesures sans service
merged_check = pd.merge(mesures, services, on=['PianoId', 'DateOnly'], how='left', indicator=True)
orphelines = merged_check[merged_check['_merge'] == 'left_only']

# Les ajouter au résultat final
df_final = pd.concat([df_merged, orphelines], ignore_index=True)
```

---

## 📝 CHECKLIST DE VALIDATION V4 vs V5

Avant de considérer la migration complète:

- [ ] Même nombre de lignes par institution
- [ ] Dates converties identiquement (UTC → Montreal)
- [ ] Mesures agrégées identiquement par piano+jour
- [ ] Mesures orphelines incluses
- [ ] Ordre des colonnes identique
- [ ] Formatage dates identique (YYYY-MM-DD HH:MM)
- [ ] Valeurs NULL remplacées par '' (chaîne vide)

---

**Créé:** 2025-12-22
**Pour:** Cursor Mac - Migration V5
**Source:** `ptm_report_sheets.py` lignes 58-143, 249-253
