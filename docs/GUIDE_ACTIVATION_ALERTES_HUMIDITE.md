# Guide d'activation des Alertes d'Humidité

## Étape 1: Exécuter le SQL sur Supabase

### Option A: Via l'interface Supabase (Recommandé)

1. Ouvre ton projet Supabase: https://supabase.com/dashboard/project/YOUR_PROJECT_ID
2. Va dans **SQL Editor** (dans le menu de gauche)
3. Clique sur **New Query**
4. Copie-colle le contenu du fichier `sql/add_archived_to_humidity_alerts_fixed.sql`
5. Clique sur **Run** (ou Ctrl+Enter)
6. Vérifie qu'il n'y a pas d'erreurs

### Option B: Via script Python (Si Supabase UI ne fonctionne pas)

Crée un fichier `scripts/apply_humidity_sql.py`:

```python
#!/usr/bin/env python3
"""Applique la migration SQL pour les alertes d'humidité."""

import os
from pathlib import Path
from dotenv import load_dotenv
from core.supabase_storage import SupabaseStorage

# Charger .env
load_dotenv()

def apply_migration():
    """Applique le SQL de migration."""
    sql_path = Path(__file__).parent.parent / "sql" / "add_archived_to_humidity_alerts_fixed.sql"

    print(f"📂 Lecture du fichier SQL: {sql_path}")
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    print("🔌 Connexion à Supabase...")
    storage = SupabaseStorage()

    print("🚀 Exécution du SQL...")
    try:
        # Utiliser l'API REST pour exécuter du SQL brut
        import requests
        url = f"{storage.api_url}/rpc/exec_sql"

        # Si cette fonction n'existe pas, on utilise une autre approche
        # On peut exécuter chaque commande séparément

        # Pour l'instant, afficher le SQL pour copier-coller manuellement
        print("\n" + "="*60)
        print("⚠️  Copie ce SQL et exécute-le manuellement dans Supabase SQL Editor:")
        print("="*60)
        print(sql_content)
        print("="*60)

    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("\n💡 Solution: Copie le SQL ci-dessus et exécute-le manuellement dans Supabase SQL Editor")

if __name__ == "__main__":
    apply_migration()
```

Puis exécute:
```bash
python scripts/apply_humidity_sql.py
```

## Étape 2: Vérifier que tout fonctionne

### Test 1: Vérifier la vue

Dans Supabase SQL Editor, exécute:

```sql
-- Vérifier que la vue existe
SELECT * FROM humidity_alerts_active LIMIT 5;
```

Si tu vois des résultats (ou 0 résultats mais pas d'erreur), c'est bon! ✅

### Test 2: Vérifier les fonctions

```sql
-- Vérifier que les fonctions existent
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN ('resolve_humidity_alert', 'archive_humidity_alert');
```

Tu devrais voir 2 lignes. ✅

### Test 3: Vérifier les colonnes

```sql
-- Vérifier que les nouvelles colonnes existent
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'humidity_alerts'
  AND column_name IN ('archived', 'resolved_at', 'resolution_notes');
```

Tu devrais voir 3 lignes. ✅

## Étape 3: Tester l'API

Une fois le SQL appliqué, teste l'endpoint:

```bash
# Test 1: Stats globales
curl http://localhost:8000/api/humidity-alerts/stats

# Test 2: Alertes non résolues
curl http://localhost:8000/api/humidity-alerts/unresolved

# Test 3: Alertes résolues
curl http://localhost:8000/api/humidity-alerts/resolved
```

Si tu reçois des JSON (même vides), c'est bon! ✅

## Étape 4: Tester le frontend

1. Démarre le frontend: `npm run dev`
2. Va sur l'onglet **Configuration**
3. Clique sur **Actualiser** dans la section Alertes Maintenance Institutionnelle
4. Si tu vois "0 alertes" au lieu d'une erreur 500, c'est bon! ✅

## Dépannage

### Erreur: "relation humidity_alerts_active does not exist"
→ Le SQL n'a pas été exécuté. Retourne à l'Étape 1.

### Erreur: "column archived does not exist"
→ Les colonnes n'ont pas été ajoutées. Exécute manuellement:
```sql
ALTER TABLE humidity_alerts ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;
ALTER TABLE humidity_alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE humidity_alerts ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
```

### Erreur: "function resolve_humidity_alert does not exist"
→ Les fonctions n'ont pas été créées. Copie-colle la section des fonctions du SQL.

## Scanner automatique

Pour lancer un scan manuel des alertes:

```bash
python -c "from modules.alerts.humidity_scanner_safe import HumidityScannerSafe; scanner = HumidityScannerSafe(); print(scanner.scan_new_entries(days_back=7))"
```

Le scanner automatique quotidien se lance à 16h (défini dans `api/humidity_alerts_routes.py` ligne 488).

## Configuration des institutions surveillées

Les institutions surveillées sont définies dans:
- `api/humidity_alerts_routes.py` ligne 58-62

Actuellement:
- Vincent d'Indy
- Place des Arts
- Orford

Pour ajouter d'autres institutions, modifie la liste `INSTITUTIONAL_CLIENTS`.

---

**Une fois ces étapes complétées, le système d'alertes d'humidité sera complètement opérationnel!** ✅
