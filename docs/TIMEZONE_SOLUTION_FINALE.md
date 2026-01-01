# Solution Finale: Timezone UTC pour Rendez-vous Gazelle

**Date:** 2025-12-26
**Statut:** ✅ RÉSOLU

## 🎯 Problème Initial

Les rendez-vous importés de l'API Gazelle avaient un problème de timezone:
- L'API retourne les heures en **UTC** (ex: `12:00:00Z` pour 7h AM Montréal)
- Les heures étaient affichées incorrectement (12h PM au lieu de 7h AM)
- Place des Arts ne trouvait pas les RV à la bonne heure

## ✅ Solution Finale (CORRECTE)

### Principe: Stockage UTC Pur

**Architecture:**
```
API Gazelle (UTC) → Stockage Supabase (UTC) → Affichage (Montréal)
     12:00Z       →      12:00:00           →      07:00
```

### 1. Suppression du Trigger SQL

**Problème:** Un trigger DB soustrayait automatiquement 10h de toutes les heures importées.

**Solution:** Supprimer le trigger (déjà fait dans Supabase):
```sql
DROP TRIGGER IF EXISTS tr_fix_api_import ON public.gazelle_appointments;
DROP FUNCTION IF EXISTS public.fn_fix_gazelle_api_time();
```

### 2. Script d'Import Corrigé

**Fichier:** `scripts/import_appointments_fixed.py`

**Logique:**
```python
# STOCKAGE UTC PUR - AUCUNE CONVERSION
dt_utc = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

# AUCUNE COMPENSATION - Stockage UTC pur
appointment_date = dt_utc.date().isoformat()
appointment_time = dt_utc.time().isoformat()
```

**Ce qu'on NE fait PAS:**
- ❌ Pas de conversion `astimezone()`
- ❌ Pas de compensation `+ timedelta(hours=5)` ou `+ timedelta(hours=10)`
- ❌ Pas de `replace(tzinfo=...)`

**Ce qu'on fait:**
- ✅ Parser l'heure UTC de l'API
- ✅ Stocker tel quel dans la DB
- ✅ Laisser la conversion à Python/SQL lors de l'affichage

### 3. Conversion pour Affichage

**En Python:**
```python
from datetime import datetime
from zoneinfo import ZoneInfo

# Lire depuis DB (UTC)
time_utc = "12:00:00"
date = "2026-01-09"

# Convertir pour affichage
dt_utc = datetime.fromisoformat(f"{date} {time_utc}").replace(tzinfo=ZoneInfo('UTC'))
dt_mtl = dt_utc.astimezone(ZoneInfo('America/Toronto'))
time_montreal = dt_mtl.strftime('%H:%M')  # "07:00"
```

**En SQL (vues):**
```sql
SELECT
    appointment_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Toronto' as time_montreal
FROM gazelle_appointments;
```

### 4. Validation Place des Arts

**Fichier:** `assistant-v6/modules/assistant/services/pda_validation.py`

**Corrections appliquées:**

1. **Recherche dans titre ET notes** (ligne 117):
```python
url += "&or=(notes.ilike.*PdA*,notes.ilike.*Place des Arts*,title.ilike.*Place des Arts*)"
```

2. **Mapping salles MSM** (lignes 103-104):
```python
room_variations = {
    'MS': ['MAISON SYMPHONIQUE', 'MAISON SYM', 'MS', 'M.S.', 'MSM'],
    'MSM': ['MAISON SYMPHONIQUE', 'MAISON SYM', 'MS', 'M.S.', 'MSM'],
    # ...
}
```

## 📊 Résultats

### Import Réussi
- ✅ 500 rendez-vous importés avec UTC pur
- ✅ "Tire le Coyote avant 8h": Stocké `12:00:00 UTC` → Affiché `07:00 Montréal`
- ✅ "Tire le Coyote à 18h": Stocké `23:00:00 UTC` → Affiché `18:00 Montréal`

### Validation Place des Arts
- ✅ Trouve les RV à la bonne heure
- ✅ Match par salle MSM/Maison Symphonique
- ✅ Synchronisation statut `CREATED_IN_GAZELLE` fonctionne

## 🚀 Commandes Utiles

### Réimporter tous les RV
```bash
python3 scripts/import_appointments_fixed.py
```

### Vérifier les heures stockées
```bash
python3 << 'EOF'
from core.supabase_storage import SupabaseStorage
from supabase import create_client

storage = SupabaseStorage()
supabase = create_client(storage.supabase_url, storage.supabase_key)

result = supabase.table('gazelle_appointments').select('*').ilike('title', '%Place des Arts%').limit(5).execute()

for appt in result.data:
    print(f"{appt['title'][:50]}: {appt['appointment_time']} UTC")
EOF
```

### Tester la validation PDA
```bash
python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "assistant-v6" / "modules" / "assistant" / "services"))

from pda_validation import PlaceDesArtsValidator

validator = PlaceDesArtsValidator()
result = validator.find_gazelle_appointment_for_pda(
    appointment_date='2026-01-09',
    room='MSM',
    debug=True
)
print(f"Trouvé: {result['title'] if result else 'Non trouvé'}")
EOF
```

## ⚠️ Ce qu'il NE FAUT PAS faire

1. **Ne jamais** réactiver un trigger qui modifie les heures
2. **Ne jamais** ajouter de compensation (+5h, +10h) dans le script d'import
3. **Ne jamais** utiliser `replace(tzinfo=...)` pour la conversion (utiliser `astimezone()`)
4. **Ne jamais** stocker des heures en "heure locale" dans la DB

## ✅ Bonnes Pratiques

1. **Toujours** stocker en UTC dans la base de données
2. **Toujours** convertir pour l'affichage (Python/SQL)
3. **Toujours** utiliser `zoneinfo.ZoneInfo('America/Toronto')` pour Montréal
4. **Toujours** tester avec "Tire le Coyote" comme référence

## 📝 Historique

- **2025-12-24:** Problème découvert (heures affichées 5h trop tard)
- **2025-12-26:** Tentatives de compensation (+5h, +10h) - ÉCHEC
- **2025-12-26:** Solution finale: Suppression trigger + Stockage UTC pur - ✅ SUCCÈS

## 🎓 Crédits

Solution inspirée par la recommandation de Gemini:
> "Supprime le Trigger dans Supabase, vide la table (TRUNCATE), et relance l'importation 'pure'.
> C'est le seul moyen d'avoir des données justes."

Cette approche s'est avérée correcte et a résolu tous les problèmes de timezone.
