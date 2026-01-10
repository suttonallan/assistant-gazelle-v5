# Diagnostic Complet: Erreurs Synchronisation Gazelle

## 🔍 Diagnostic Effectué

Date: 2026-01-09
Analysé par: Claude

---

## 📊 Résultats du Diagnostic

### 1. Compteurs Tables (✅ BON)

| Table | Count | Status |
|-------|-------|--------|
| **gazelle_clients** | 1344 | ✅ Pagination OK (> 1000) |
| **gazelle_pianos** | 1031 | ✅ Pagination OK (> 1000) |
| **gazelle_appointments** | 11460 | ✅ Données complètes |
| **gazelle_timeline_entries** | 13902 | ✅ Données complètes |
| **users** | 4 | ⚠️ Normal (optimisation skip activée) |

**Conclusion**: ✅ Les compteurs ne sont PAS bloqués à 1000. La pagination fonctionne correctement.

---

### 2. Problème start_datetime NULL (❌ CRITIQUE)

**Constat:**
```
❌ start_datetime NULL: 11194 RV (97.7%)
✅ start_datetime rempli: 266 RV (2.3%)
```

**Analyse:**
- RV récents (2026-04-09): ✅ `start_datetime` rempli correctement
- RV anciens (avant 2026-04-07): ❌ `start_datetime = NULL`

**Cause Racine:**
La migration SQL ajoutant la colonne `start_datetime` a été effectuée **après** l'import initial des 11000+ RV. Ces anciens RV n'ont jamais été re-synchronisés pour remplir la nouvelle colonne.

**Code de sync (ligne 494):**
```python
appointment_record = {
    'start_datetime': start_time_utc,  # ← Assigné correctement
    ...
}
```

Le code est **correct**. Le problème est que les RV créés **avant** la migration SQL n'ont jamais été mis à jour.

---

### 3. Users = 4 (⚠️ Expliqué)

**Status**: ⚠️ Normal avec optimisation activée

**Explication:**
- [sync_to_supabase.py:696-722](../modules/sync_gazelle/sync_to_supabase.py#L696-L722) a l'optimisation `skip if not empty`
- Si la table `users` n'est pas vide, la sync est skippée automatiquement
- Message affiché: `"⏭️  Users déjà synchronisés (table non vide) - skip"`

**Compteurs actuels:**
```python
url = f"{SUPABASE_URL}/rest/v1/users?select=id"
# Retourne 4 users: usr_HcCiFk7o0vZ9xAI0, ...
```

**Est-ce un problème?**
- Si vous avez réellement 4 techniciens: ✅ Normal
- Si vous avez plus de techniciens dans Gazelle: ⚠️ Forcer re-sync avec `sync_users(force=True)`

---

### 4. "1 erreurs" dans Logs (❌ À INVESTIGUER)

**Constat:** Logs GitHub Actions montrent "1 erreurs" systématiquement

**Causes Possibles:**

#### A. Foreign Key Violation
```python
# Si performed_by_user_id référence un user qui n'existe pas
INSERT INTO gazelle_timeline_entries (performed_by_user_id, ...)
  VALUES ('usr_INEXISTANT', ...)
# → FK Error
```

**Solution**: S'assurer que tous les users référencés existent avant d'importer timeline

#### B. Client Name Empty
```python
# Ligne 111 de sync_to_supabase.py
if not company_name:
    print(f"⚠️  Client {external_id} ignoré (nom vide)")
    self.stats['clients']['errors'] += 1  # ← Incrémente erreurs
```

**Solution**: Acceptable - clients sans nom sont rejetés

#### C. start_datetime Parsing Failure
```python
# Ligne 449 de sync_to_supabase.py
except Exception as e:
    print(f"⚠️ Erreur conversion heure '{start_time}': {e}")
    pass  # ← Continue sans incrémenter erreurs
```

Mais ce n'est **pas** compté dans `self.stats['appointments']['errors']`.

---

## ✅ Solutions

### Solution 1: Re-Remplir start_datetime (RECOMMANDÉ)

**Option A: Update SQL Direct**

Utilise les colonnes `appointment_date` et `appointment_time` existantes pour reconstruire `start_datetime`:

```sql
-- Dashboard Supabase → SQL Editor
UPDATE gazelle_appointments
SET start_datetime = (
    CASE
        WHEN appointment_date IS NOT NULL AND appointment_time IS NOT NULL
        THEN (appointment_date::text || ' ' || appointment_time::text)::timestamptz
        ELSE NULL
    END
)
WHERE start_datetime IS NULL
  AND appointment_date IS NOT NULL
  AND appointment_time IS NOT NULL;

-- Vérifier
SELECT COUNT(*)
FROM gazelle_appointments
WHERE start_datetime IS NULL;
-- Devrait retourner ~200 au lieu de 11194
```

**Option B: Re-Sync Complète**

Force une re-sync de tous les RV pour remplir `start_datetime`:

```python
from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync
from datetime import datetime, timedelta

sync = GazelleToSupabaseSync()

# Sync sur fenêtre large (6 mois au lieu de 7 jours)
# Modifie temporairement la fenêtre dans sync_appointments()
# OU lance une sync manuelle avec start_date ancien
```

**Temps estimé:**
- Option A (SQL): 1-2 secondes
- Option B (Re-sync): 5-10 minutes

---

### Solution 2: Forcer Re-Sync Users (Si Besoin)

Si vous avez plus de 4 techniciens dans Gazelle:

```python
from modules.sync_gazelle.sync_to_supabase import GazelleToSupabaseSync

sync = GazelleToSupabaseSync()
count = sync.sync_users(force=True)  # Force la re-sync
print(f"✅ {count} users synchronisés")
```

---

### Solution 3: Débugger "1 erreurs"

**Activer logs détaillés:**

```python
# Dans sync_to_supabase.py, après chaque erreur:
print(f"❌ Erreur détaillée: {type(e).__name__}: {str(e)}")
import traceback
traceback.print_exc()
```

**Vérifier le log GitHub Actions:**
1. Va sur: https://github.com/allansutton/assistant-gazelle-v5/actions
2. Clique sur la dernière exécution "🔄 Sync Gazelle Complète"
3. Cherche `⚠️` ou `❌` dans les logs
4. Identifie l'erreur exacte (KeyError, DatabaseError, etc.)

---

## 🧪 Tests de Validation

### Test 1: Vérifier start_datetime après fix

```bash
python3 -c "
import sys, os
sys.path.insert(0, '/Users/allansutton/Documents/assistant-gazelle-v5')
from dotenv import load_dotenv
load_dotenv()
import requests

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

url = f'{SUPABASE_URL}/rest/v1/gazelle_appointments?select=id&start_datetime=is.null'
headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Range': '0-0',
    'Prefer': 'count=exact'
}

response = requests.get(url, headers=headers)
count_header = response.headers.get('Content-Range', '').split('/')[-1]
print(f'RV avec start_datetime NULL: {count_header}')
print('✅ OK' if int(count_header) < 500 else '⚠️ Encore trop de NULL')
"
```

**Résultat attendu après fix:**
```
RV avec start_datetime NULL: 200
✅ OK
```

### Test 2: Compter erreurs sync

Ajouter dans `sync_to_supabase.py` à la fin de `run_sync()`:

```python
# Ligne ~800
print("\n📊 Résumé Erreurs:")
for table, stats in self.stats.items():
    if stats['errors'] > 0:
        print(f"  ❌ {table}: {stats['errors']} erreur(s)")
```

---

## 📝 Checklist Action

- [ ] **Fix start_datetime NULL**
  - [ ] Option A: Exécuter UPDATE SQL (2 sec)
  - [ ] Option B: Re-sync complète (10 min)
  - [ ] Vérifier: `<500` RV NULL

- [ ] **Vérifier users**
  - [ ] Compter users dans Gazelle (API)
  - [ ] Si > 4, forcer `sync_users(force=True)`

- [ ] **Débugger "1 erreurs"**
  - [ ] Consulter logs GitHub Actions
  - [ ] Identifier code d'erreur exact
  - [ ] Appliquer fix selon type

- [ ] **Valider pagination**
  - [x] Clients: 1344 (✅ Bon)
  - [x] Pianos: 1031 (✅ Bon)

---

## 📚 Références

- **Diagnostic script**: [scripts/diagnostic_sync_errors.py](../scripts/diagnostic_sync_errors.py)
- **Sync code**: [modules/sync_gazelle/sync_to_supabase.py](../modules/sync_gazelle/sync_to_supabase.py)
- **Timezone utils**: [core/timezone_utils.py](../core/timezone_utils.py)
- **Migration SQL**: [scripts/migrations/add_start_datetime_to_appointments.sql](../scripts/migrations/add_start_datetime_to_appointments.sql)

---

## 🎯 Résumé Exécutif

| Problème | Sévérité | Status | Solution |
|----------|----------|--------|----------|
| **Pagination bloquée à 1000** | ✅ | Non, fonctionne | Aucune action |
| **start_datetime NULL (97%)** | ❌ Critique | À corriger | UPDATE SQL ou re-sync |
| **Users = 4** | ⚠️ | Normal | Vérifier si complet |
| **"1 erreurs" logs** | ⚠️ | À investiguer | Logs détaillés GitHub |

**Action immédiate recommandée**: Exécuter l'UPDATE SQL pour remplir `start_datetime` (~11000 RV en 2 sec).
