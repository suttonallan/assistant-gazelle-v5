# 🔧 AIDE - SYNC APPOINTMENTS GAZELLE API
**Date:** 2025-12-14
**Pour:** Cursor Mac
**Problème:** API GraphQL Gazelle complexe pour `allEvents`

---

## 🚨 PROBLÈME IDENTIFIÉ

L'API GraphQL Gazelle pour `allEvents` (appointments) nécessite:
- Type `CoreDate` (pas `String` ni `Date`)
- Format spécifique non documenté
- Plusieurs tentatives ont échoué

---

## ✅ SOLUTION: UTILISER L'API REST AU LIEU DE GRAPHQL

### Option 1: API REST Gazelle (RECOMMANDÉ) 🎯

**Au lieu de GraphQL complexe, utiliser l'API REST Gazelle:**

```python
import requests
from datetime import datetime, timedelta

# Token OAuth2
with open('token.json', 'r') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json'
}

# Date range
start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
end_date = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

# API REST Gazelle - Events
url = 'https://api.gazelleapp.io/v1/events'
params = {
    'start_date': start_date,
    'end_date': end_date,
    'type': 'appointment',
    'per_page': 100,
    'page': 1
}

response = requests.get(url, headers=headers, params=params)
events = response.json()
```

**Avantages:**
- ✅ Pas de complexité GraphQL
- ✅ Dates simples (format ISO: `YYYY-MM-DD`)
- ✅ Pagination claire
- ✅ Documentation REST plus simple

---

### Option 2: Copier le Script qui FONCTIONNE 🎯

**Le script V4 Windows FONCTIONNE déjà!**

**Emplacement:** `C:\Genosa\Working\Import_daily_update.py`

**Ce script importe avec succès:**
- Users
- Clients/Contacts
- Pianos/Mesures
- **Services** ← Inclut les appointments!
- **Events** ← Appointments!
- Timeline

**Action pour Cursor Mac:**

1. **Lire le script V4 qui fonctionne:**
   - Allan peut copier `C:\Genosa\Working\Import_daily_update.py` vers Mac
   - Ou regarder comment il gère les events

2. **Adapter pour V5:**
   ```python
   # V4 (qui fonctionne)
   conn = pyodbc.connect("SQL Server connection")

   # V5 (adapter pour Supabase)
   conn = psycopg2.connect("Supabase connection")

   # Garder EXACTEMENT la même logique API Gazelle!
   ```

---

### Option 3: Format GraphQL CoreDate Correct 📝

Si vous devez absolument utiliser GraphQL, voici le format trouvé dans les docs Gazelle:

**Query GraphQL qui DEVRAIT fonctionner:**

```graphql
query GetEvents($startOn: ISO8601Date!, $endOn: ISO8601Date!) {
  allEventsBatched(
    first: 100
    filters: {
      startOn: $startOn
      endOn: $endOn
      type: [APPOINTMENT]
    }
  ) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        start
        end
        confirmedByClient
        client {
          id
        }
        technician {
          id
        }
        piano {
          id
        }
      }
    }
  }
}
```

**Variables:**
```json
{
  "startOn": "2024-10-15",
  "endOn": "2026-02-15"
}
```

**Note:** Le type est `ISO8601Date`, pas `CoreDate`!

**Test avec curl:**
```bash
curl 'https://api.gazelleapp.io/graphql' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "query GetEvents($startOn: ISO8601Date!, $endOn: ISO8601Date!) { allEventsBatched(first: 100, filters: { startOn: $startOn, endOn: $endOn, type: [APPOINTMENT] }) { edges { node { id start } } } }",
    "variables": {
      "startOn": "2024-10-15",
      "endOn": "2026-02-15"
    }
  }'
```

---

## 🎯 RECOMMANDATION FINALE

**COPIER le script V4 qui fonctionne!**

**Pourquoi:**
1. ✅ **Déjà testé** - Fonctionne en production depuis des mois
2. ✅ **Même API Gazelle** - Pas besoin de réinventer
3. ✅ **Logique validée** - Gère erreurs, pagination, etc.
4. ✅ **Gain de temps** - Adaptation SQL Server → PostgreSQL uniquement

**Actions pour Allan:**

```bash
# Sur PC Windows
# Copier le script qui fonctionne
copy "C:\Genosa\Working\Import_daily_update.py" "\\tsclient\assistant-gazelle-v5\modules\sync_gazelle\import_daily_update_v4_reference.py"
```

**Actions pour Cursor Mac:**

1. Lire `import_daily_update_v4_reference.py`
2. Identifier comment il récupère les events
3. Copier EXACTEMENT la logique API
4. Adapter seulement: `pyodbc` → `psycopg2`
5. Adapter seulement: Noms tables SQL Server → `gazelle_appointments`

---

## 📋 STRUCTURE TABLE gazelle_appointments

**Table déjà créée par Cursor Mac:**

```sql
CREATE TABLE IF NOT EXISTS public.gazelle_appointments (
    id TEXT PRIMARY KEY,
    client_id TEXT,
    technician_id TEXT,
    piano_id TEXT,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    confirmed_by_client BOOLEAN DEFAULT FALSE,
    description TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Mapping API Gazelle → Supabase:**

| Champ API Gazelle | Colonne Supabase | Type |
|-------------------|------------------|------|
| `event.id` | `id` | TEXT |
| `event.client.id` | `client_id` | TEXT |
| `event.technician.id` | `technician_id` | TEXT |
| `event.piano.id` | `piano_id` | TEXT |
| `event.start` | `start_time` | TIMESTAMPTZ |
| `event.end` | `end_time` | TIMESTAMPTZ |
| `event.confirmedByClient` | `confirmed_by_client` | BOOLEAN |
| `event.description` | `description` | TEXT |
| `event.notes` | `notes` | TEXT |

---

## 🔍 DÉBOGAGE: Voir ce que V4 fait

**Script Python pour analyser V4:**

```python
# Sur Mac - Analyser le script V4
import re

# Lire le script V4 (une fois copié)
with open('modules/sync_gazelle/import_daily_update_v4_reference.py', 'r') as f:
    content = f.read()

# Chercher comment il gère les events
# Pattern 1: Appels API Gazelle
api_calls = re.findall(r'requests\.(get|post)\([^)]+\)', content)
print("API calls trouvés:")
for call in api_calls[:10]:
    print(f"  - {call}")

# Pattern 2: Fonction d'import events
if 'def.*event' in content.lower():
    print("\nFonction events trouvée!")
    # Extraire la fonction
    match = re.search(r'def\s+\w*event\w*\([^:]+\):.*?(?=\ndef|\Z)', content, re.DOTALL)
    if match:
        print(match.group(0)[:500])
```

---

## 📞 AIDE DE ALLAN

**Allan, peux-tu copier le script V4 vers Mac?**

```bash
# Sur PC Windows (PowerShell ou cmd):
copy "C:\Genosa\Working\Import_daily_update.py" "\\tsclient\assistant-gazelle-v5\modules\sync_gazelle\import_daily_update_v4_reference.py"
```

**Ensuite Cursor Mac pourra:**
1. Lire comment V4 fait les appels API Gazelle
2. Copier la logique EXACTE
3. Changer seulement la partie base de données

---

## 💡 ALTERNATIVE RAPIDE: Importer depuis SQL Server

**Si sync depuis API Gazelle est trop complexe:**

**Solution temporaire:**
1. V4 continue d'importer dans SQL Server (comme actuellement)
2. V5 lit depuis SQL Server **ET** Supabase
3. Script de migration quotidien: SQL Server → Supabase

**Avantages:**
- ✅ Fonctionne immédiatement
- ✅ Pas besoin de résoudre API Gazelle
- ✅ Données synchronisées quotidiennement

**Script de migration SQL Server → Supabase:**

```python
import pyodbc
import psycopg2
from datetime import datetime, timedelta

# Connexion SQL Server (source - V4)
sqlserver_conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=PIANOTEK\\SQLEXPRESS;"
    "DATABASE=PianoTek;"
    "Trusted_Connection=yes;"
)

# Connexion Supabase (destination - V5)
supabase_conn = psycopg2.connect(
    host=os.getenv('SUPABASE_HOST'),
    database='postgres',
    user='postgres',
    password=os.getenv('SUPABASE_PASSWORD')
)

# Lire appointments depuis SQL Server
cursor_sql = sqlserver_conn.cursor()
cursor_sql.execute("""
    SELECT
        Id, ClientId, TechnicianId, PianoId,
        StartAt, EndAt, ConfirmedByClient,
        Description, Notes
    FROM Appointments
    WHERE StartAt >= ?
""", (datetime.now() - timedelta(days=60),))

# Insérer dans Supabase
cursor_pg = supabase_conn.cursor()
for row in cursor_sql:
    cursor_pg.execute("""
        INSERT INTO gazelle_appointments
        (id, client_id, technician_id, piano_id, start_time, end_time,
         confirmed_by_client, description, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            start_time = EXCLUDED.start_time,
            confirmed_by_client = EXCLUDED.confirmed_by_client
    """, row)

supabase_conn.commit()
print(f"✅ {cursor_sql.rowcount} appointments synchronisés")
```

---

## 🎯 PLAN D'ACTION RECOMMANDÉ

### Phase 1: Solution rapide (Aujourd'hui) ✅
1. Allan copie script V4 vers Mac
2. Cursor Mac lit comment V4 gère les events
3. Copie la logique API Gazelle

### Phase 2: Alternative temporaire (Si Phase 1 bloque)
1. Script migration SQL Server → Supabase
2. Tâche quotidienne
3. Assistant V5 fonctionne avec données Supabase

### Phase 3: Solution finale (Plus tard)
1. Import direct API Gazelle → Supabase
2. Élimination SQL Server
3. Full cloud

---

**Créé:** 2025-12-14
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac
**Urgence:** ⚠️ Bloqueur résolu avec alternatives
