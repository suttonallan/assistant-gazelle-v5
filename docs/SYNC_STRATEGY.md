# STRATÉGIE DE SYNCHRONISATION GAZELLE → SUPABASE

## 🔴 RÈGLE ABSOLUE: RESPECTER LES TIMESTAMPS UTC DE L'API

### Principe Fondamental

**L'API Gazelle fournit du VRAI UTC (le 'Z' est fiable).**

Toute tentative de forcer un offset 'Eastern' lors de l'importation est une **erreur grave** qui crée une double conversion et corrompt les données.

### Comment Gazelle Fonctionne

1. **Interface Web**: Affiche les heures en temps local (America/Toronto)
   - Exemple: 09:15 - 16:40

2. **API GraphQL**: Retourne les heures en UTC avec 'Z'
   - Exemple: `2026-01-03T14:15:00Z`
   - Conversion correcte: 09:15 Toronto + 5h = 14:15 UTC ✅

3. **Base de Données Supabase**: Stocke en UTC (colonne TIMESTAMPTZ)
   - Doit contenir exactement ce que l'API retourne
   - Exemple: `14:15:00` (UTC)

4. **Service Python** (`service.py`): Convertit UTC → Montreal pour affichage
   - Lit: `14:15:00` (UTC)
   - Convertit: 14:15 UTC - 5h = 09:15 Montreal ✅
   - Affiche: "09:15" ✅

### 🚫 L'ERREUR À NE JAMAIS REFAIRE

**Code incorrect (AVANT - lignes 440-456 de sync_to_supabase.py):**

```python
# ❌ FAUX: Double conversion
dt_obj = dt.fromisoformat(start_time.replace('Z', ''))
eastern_tz = ZoneInfo('America/Toronto')
dt_eastern = dt_obj.replace(tzinfo=eastern_tz)
dt_utc = dt_eastern.astimezone(ZoneInfo('UTC'))
```

**Résultat:**
- API retourne: `14:15Z` (UTC)
- Code interprète comme Eastern: `14:15-05:00`
- Code convertit en UTC: `19:15+00:00` ❌ (ajoute ENCORE 5h)
- DB contient: `19:15:00` (5h de trop)
- Service affiche: 19:15 - 5h = 14:15 ❌ (au lieu de 09:15)

**Code correct (MAINTENANT - lignes 440-452):**

```python
# ✅ CORRECT: Respecter l'UTC de l'API
dt_utc = dt.fromisoformat(start_time)
appointment_date = dt_utc.date().isoformat()
appointment_time = dt_utc.time().isoformat()
```

**Résultat:**
- API retourne: `14:15Z` (UTC)
- Code stocke: `14:15:00` (UTC) ✅
- Service affiche: 14:15 - 5h = 09:15 ✅

## 📋 PROCÉDURE DE MIGRATION (Reset Complet)

Après correction du code, il FAUT vider et réimporter toutes les données:

### Étape 1: Vider la table corrompue

```sql
TRUNCATE TABLE gazelle_appointments CASCADE;
```

### Étape 2: Relancer l'importation complète

```bash
python3 modules/sync_gazelle/sync_to_supabase.py
```

### Étape 3: Valider avec Caroline Lessard (Étalon)

```bash
# Vérifier que l'heure est correcte
curl "$SUPABASE_URL/rest/v1/gazelle_appointments?external_id=eq.evt_xMjKE8YJCDQmRg7K&select=appointment_time" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY"

# Doit retourner: "14:15:00" (pas 19:15:00)
```

### Étape 4: Tester l'affichage dans le Chat

```
Nick: "samedi"
→ Doit afficher: 09:15 - 16:40 ✅
```

## 🎯 CAS DE RÉFÉRENCE: Caroline Lessard

**Événement:** evt_xMjKE8YJCDQmRg7K (vd - Vincent d'Indy)

| Source | Heure | Format |
|--------|-------|--------|
| Gazelle Web | 09:15 - 16:40 | Toronto (local) |
| Gazelle API | 14:15Z | UTC |
| DB Supabase | 14:15:00 | UTC |
| Chat Assistant | 09:15 - 16:40 | Montreal (converti) |

**Si Caroline n'affiche pas 09:15, tout le système est cassé.**

## 🔍 AUDIT DES DONNÉES (À Faire Régulièrement)

Pour vérifier qu'il n'y a pas de corruption:

```python
# Compare API vs DB pour les 10 derniers RDV
from core.gazelle_api_client import GazelleAPIClient
from core.supabase_storage import SupabaseStorage

client = GazelleAPIClient()
storage = SupabaseStorage()

api_apts = client.get_appointments(limit=10)

for apt in api_apts:
    api_time = apt.get('start')  # Ex: 2026-01-03T14:15:00Z
    external_id = apt.get('id')

    # Récupérer depuis DB
    db_apt = storage.get_appointment(external_id)
    db_time = db_apt.get('appointment_time')  # Ex: 14:15:00

    # Comparer
    expected = dt.fromisoformat(api_time).time().isoformat()
    if db_time != expected:
        print(f"❌ CORRUPTION: {external_id}")
        print(f"   API: {expected}")
        print(f"   DB:  {db_time}")
```

## 📝 RÈGLES DE DÉVELOPPEMENT

### Pour l'Import (Fetcher)

1. **NE JAMAIS** forcer un timezone sur une valeur qui a déjà un 'Z'
2. **NE JAMAIS** deviner que l'API "ment" sur son timezone
3. **TOUJOURS** stocker exactement ce que l'API retourne
4. **DOCUMENTER** toute logique de conversion avec des cas de test

### Pour l'Affichage (Service)

1. La conversion UTC → Montreal se fait UNIQUEMENT dans `service.py`
2. Fonction: `_convert_utc_to_montreal()` (lignes 689-725)
3. Toute modification de cette fonction DOIT être testée avec Caroline

### Pour le Debugging

1. **Cas de test obligatoire**: Caroline Lessard (evt_xMjKE8YJCDQmRg7K)
2. **Heure attendue**: 09:15 Montreal (14:15 UTC en DB)
3. **Si ça ne marche pas pour Caroline, ne commit pas le code**

## 🚨 ALERTES

### Signal d'une Corruption

- Un rendez-vous affiché dans le chat a un décalage de 5h par rapport à Gazelle
- La DB contient des heures comme 19:15 pour un RDV qui devrait être à 09:15
- Plusieurs utilisateurs rapportent des heures incorrectes

### Action à Prendre

1. **NE PAS créer de vue SQL pour "corriger"** - c'est un pansement dangereux
2. **Corriger le code Python** (sync_to_supabase.py)
3. **Vider et réimporter** (TRUNCATE + sync complet)
4. **Valider avec Caroline**

## 📚 DOCUMENTATION LIÉE

- [TIMEZONE_BUG_GAZELLE.md](./TIMEZONE_BUG_GAZELLE.md) - Historique du bug découvert le 2025-12-29
- [TIMEZONE_SOLUTION_FINALE.md](./TIMEZONE_SOLUTION_FINALE.md) - Solution finale implémentée
- `modules/sync_gazelle/sync_to_supabase.py` (lignes 440-452) - Code corrigé
- `api/chat/service.py` (lignes 689-725) - Conversion UTC → Montreal

## ✅ VALIDATION FINALE

Avant de considérer que le problème est résolu:

1. [ ] Code corrigé dans sync_to_supabase.py
2. [ ] Table gazelle_appointments vidée (TRUNCATE)
3. [ ] Réimportation complète exécutée
4. [ ] Caroline affiche 09:15 dans le chat
5. [ ] 5 autres RDV testés et corrects
6. [ ] Documentation mise à jour
7. [ ] Commit avec message: "fix(sync): Corriger double conversion timezone Gazelle"

---

**Date de création**: 2025-12-29
**Dernière mise à jour**: 2025-12-29
**Auteur**: Claude Sonnet 4.5 + Allan Sutton
