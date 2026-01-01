# Import Timeline Entries depuis l'API Gazelle

**Date:** 2025-12-22
**Objectif:** Importer les timeline entries directement depuis l'API Gazelle vers Supabase (pas via SQL Server)

---

## 🎯 APPROCHE RECOMMANDÉE

**Importer depuis l'API Gazelle** plutôt que SQL Server car:
- ✅ Source de vérité unique (Gazelle)
- ✅ Pas besoin de maintenir 2 pipelines (SQL Server → Supabase + Gazelle → SQL Server)
- ✅ Données toujours à jour
- ✅ Peut être automatisé quotidiennement sur le cloud (Render)

---

## 📡 REQUÊTE GRAPHQL GAZELLE

### Query complète

```graphql
query($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
    allTimelineEntries(first: $first, after: $after, occurredAtGet: $occurredAtGet) {
        totalCount
        nodes {
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
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
```

### Variables

```json
{
  "first": 100,
  "after": null,
  "occurredAtGet": "2025-07-01T00:00:00Z"
}
```

**Note:** `occurredAtGet` filtre les entries **≥ date spécifiée**

---

## 🗂️ MAPPING API GAZELLE → SUPABASE

| Champ GraphQL | Chemin | Colonne Supabase | Type | Notes |
|--------------|--------|------------------|------|-------|
| `id` | `node.id` | `id` | TEXT | ID unique Gazelle |
| `occurredAt` | `node.occurredAt` | `occurred_at` | TIMESTAMPTZ | Date/heure UTC |
| `type` | `node.type` | `entry_type` | TEXT | Ex: `SERVICE_ENTRY_MANUAL`, `PIANO_MEASUREMENT` |
| `summary` | `node.summary` | `title` | TEXT | Titre court |
| `comment` | `node.comment` | `description` | TEXT | Description détaillée |
| `client.id` | `node.client.id` | `client_id` | TEXT | ID client Gazelle (peut être NULL) |
| `piano.id` | `node.piano.id` | `piano_id` | TEXT | 🚨 **ID piano Gazelle** (peut être NULL) |
| `invoice.id` | `node.invoice.id` | `invoice_id` | TEXT | ID facture (peut être NULL) |
| `estimate.id` | `node.estimate.id` | `estimate_id` | TEXT | ID estimation (peut être NULL) |
| `user.id` | `node.user.id` | `user_id` | TEXT | 🚨 **ID technicien Gazelle** (peut être NULL) |

---

## 📊 STATISTIQUES V4 (RÉFÉRENCE)

**Total timeline entries:** 154,242

**NULL values:**
- `PianoId NULL`: 122,259 (79%)
- `UserId NULL`: 71,260 (46%)

**⚠️ IMPORTANT:** Beaucoup d'entries n'ont pas de `piano_id` ou `user_id` - c'est normal!

---

## 🔧 CODE PYTHON D'IMPORT

### 1. Script d'import one-shot

```python
import requests
import json
from datetime import datetime, timedelta
from supabase import create_client
import os

# Configuration
GAZELLE_API_URL = "https://gazelleapp.io/graphql/private/"
GAZELLE_ACCESS_TOKEN = os.getenv('GAZELLE_ACCESS_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Connexion Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_timeline_entries(start_date='2025-07-01T00:00:00Z'):
    """Récupère toutes les timeline entries depuis Gazelle API"""

    query = """
    query($first: Int, $after: String, $occurredAtGet: CoreDateTime) {
        allTimelineEntries(first: $first, after: $after, occurredAtGet: $occurredAtGet) {
            totalCount
            nodes {
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
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """

    all_entries = []
    cursor = None
    page = 0

    while True:
        page += 1
        print(f"  Fetching page {page}...")

        variables = {
            "first": 100,
            "after": cursor,
            "occurredAtGet": start_date
        }

        payload = {"query": query, "variables": variables}
        headers = {"Authorization": f"Bearer {GAZELLE_ACCESS_TOKEN}"}

        response = requests.post(GAZELLE_API_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        data = response.json()

        if 'errors' in data:
            print(f"  ❌ GraphQL Error: {data['errors']}")
            break

        connection = data['data']['allTimelineEntries']
        nodes = connection['nodes']

        if page == 1:
            print(f"  Total entries to fetch: {connection['totalCount']}")

        all_entries.extend(nodes)

        page_info = connection['pageInfo']
        if not page_info['hasNextPage']:
            break

        cursor = page_info['endCursor']

    print(f"  ✅ Fetched {len(all_entries)} timeline entries")
    return all_entries

def transform_entry(entry):
    """Transforme une entry Gazelle en format Supabase"""
    return {
        'id': entry.get('id'),
        'occurred_at': entry.get('occurredAt'),
        'entry_type': entry.get('type'),
        'title': entry.get('summary'),
        'description': entry.get('comment'),
        'client_id': (entry.get('client') or {}).get('id'),
        'piano_id': (entry.get('piano') or {}).get('id'),
        'invoice_id': (entry.get('invoice') or {}).get('id'),
        'estimate_id': (entry.get('estimate') or {}).get('id'),
        'user_id': (entry.get('user') or {}).get('id')
    }

def upsert_to_supabase(entries, batch_size=100):
    """Insère ou met à jour les entries dans Supabase"""

    print(f"\n📥 Upserting {len(entries)} entries to Supabase...")

    # Transformer les données
    transformed = [transform_entry(e) for e in entries]

    # Upsert par lots
    for i in range(0, len(transformed), batch_size):
        batch = transformed[i:i+batch_size]
        print(f"  Batch {i//batch_size + 1}: upserting {len(batch)} entries...")

        result = supabase.table('gazelle_timeline_entries').upsert(
            batch,
            on_conflict='id'
        ).execute()

        print(f"    ✅ Done")

    print(f"✅ All entries upserted successfully")

def main():
    """Import timeline entries depuis Gazelle vers Supabase"""

    print("="*80)
    print("IMPORT TIMELINE ENTRIES: Gazelle API → Supabase")
    print("="*80)

    # 1. Récupérer depuis Gazelle
    print("\n📡 Fetching from Gazelle API...")
    entries = fetch_timeline_entries(start_date='2025-07-01T00:00:00Z')

    # 2. Upsert dans Supabase
    upsert_to_supabase(entries)

    print("\n="*80)
    print("✅ IMPORT COMPLETED")
    print("="*80)

if __name__ == '__main__':
    main()
```

---

## 🔄 AUTOMATISATION QUOTIDIENNE

### Option 1: APScheduler dans FastAPI (Render)

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

# Importer chaque nuit à 3h du matin (America/Montreal)
scheduler.add_job(
    import_timeline_entries,
    trigger=CronTrigger(hour=3, minute=0, timezone='America/Montreal'),
    id='import_timeline_entries_daily'
)

scheduler.start()
```

### Option 2: Cron job GitHub Actions

```yaml
# .github/workflows/sync-timeline.yml
name: Sync Timeline Entries

on:
  schedule:
    - cron: '0 8 * * *'  # 3h AM Montreal = 8h AM UTC
  workflow_dispatch:  # Manuel aussi

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install requests supabase
      - run: python scripts/import_timeline_entries.py
        env:
          GAZELLE_ACCESS_TOKEN: ${{ secrets.GAZELLE_ACCESS_TOKEN }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

---

## ⚠️ POINTS IMPORTANTS

### 1. Credentials Gazelle

**Token OAuth2:**
- Utilise le même token que pour les autres imports Gazelle
- Fichier: `data/token.json` ou variable d'environnement
- Expire et doit être rafraîchi (voir `timeline.py.old` lignes 41-56)

### 2. Gestion des NULL

**Beaucoup de NULL values:**
- `piano_id` NULL pour 79% des entries
- `user_id` NULL pour 46% des entries
- Les rapports Timeline utilisent `LEFT JOIN` pour gérer ces cas

### 3. Filtrage par date

**Pour rapports Timeline:**
- Filtre: `occurredAtGet: "2025-07-01T00:00:00Z"`
- Récupère seulement 686 entries (vs 154K total)
- Beaucoup plus rapide

### 4. Types d'entries pour rapports

**Filtrer dans Supabase après import:**
```python
.in_('entry_type', ['SERVICE_ENTRY_MANUAL', 'PIANO_MEASUREMENT'])
```

---

## 📋 CHECKLIST

### Avant l'import:

- [ ] Exécuter migration SQL pour ajouter colonnes dans Supabase
- [ ] Vérifier que `GAZELLE_ACCESS_TOKEN` est valide
- [ ] Vérifier que table `users` existe (pour foreign key `user_id`)
- [ ] Vérifier que table `gazelle_pianos` existe (pour foreign key `piano_id`)

### Import:

- [ ] Créer script `scripts/import_timeline_entries.py`
- [ ] Tester import avec 1 page (100 entries)
- [ ] Import complet depuis 2025-07-01
- [ ] Vérifier comptage: `SELECT COUNT(*) FROM gazelle_timeline_entries`

### Validation:

- [ ] Vérifier jointures fonctionnent:
  ```sql
  SELECT te.*, p.make, u.full_name
  FROM gazelle_timeline_entries te
  LEFT JOIN gazelle_pianos p ON p.id = te.piano_id
  LEFT JOIN users u ON u.gazelle_user_id = te.user_id
  LIMIT 10;
  ```
- [ ] Re-tester génération rapports Timeline
- [ ] Comparer avec V4 (même nombre de lignes par institution)

---

## 🚀 PROCHAINES ÉTAPES

1. **Cursor Mac:** Exécuter migration SQL (ajouter colonnes)
2. **Cursor Mac:** Créer `scripts/import_timeline_entries.py`
3. **Cursor Mac:** Tester import manuel
4. **Cursor Mac:** Automatiser avec APScheduler
5. **Tester rapports Timeline** avec vraies données

---

**Créé:** 2025-12-22
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac
**Source:** `timeline.py.old` (Gazelle import v2)
