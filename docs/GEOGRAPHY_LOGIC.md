# GÉOGRAPHIE TEMPORELLE - LOGIQUE MÉTIER

## 🌍 Axiome Temporel Fondamental

**Gazelle API fournit du VRAI UTC (marqué 'Z').**

Cette vérité est absolue et non négociable. Toute tentative de "corriger" ou "interpréter" différemment cette donnée mène à la corruption des timestamps.

## 📍 Fuseaux Horaires en Jeu

### 1. America/Toronto (Eastern Time)
- **Utilisé par**: Interface web Gazelle (affichage uniquement)
- **Offset UTC**: -05:00 (hiver) / -04:00 (été)
- **Exemple**: Un RDV à 09:15 le matin

### 2. UTC (Coordinated Universal Time)
- **Utilisé par**:
  - API Gazelle (transmission des données)
  - Base de données Supabase (stockage)
- **Offset**: +00:00 (par définition)
- **Exemple**: Le même RDV à 14:15Z (09:15 + 5h)

### 3. America/Montreal
- **Utilisé par**: Service Python (affichage final)
- **Offset UTC**: -05:00 (hiver) / -04:00 (été)
- **Note**: Identique à Toronto pour nos besoins

## 🎯 Le Cas Caroline Lessard - Leçon Historique

### Événement de Référence
- **ID**: evt_xMjKE8YJCDQmRg7K
- **Description**: Événement "vd" (Vincent d'Indy)
- **Date**: 2026-01-03
- **Heure locale**: 09:15 - 16:40 (Toronto)

### L'Erreur Historique (2025-12-29)

**Ce qui s'est passé:**

1. **Interface Gazelle affiche**: 09:15 (Toronto)
2. **API Gazelle retourne**: `2026-01-03T14:15:00Z` (UTC correct: 09:15 + 5h)
3. **Code Python (ERRONÉ) faisait**:
   - Enlève le 'Z': `14:15`
   - Interprète comme Eastern: `14:15-05:00`
   - Convertit en UTC: `19:15+00:00` ❌ (double conversion!)
4. **DB contenait**: `19:15:00` (5h de trop)
5. **Service affichait**: 19:15 - 5h = 14:15 ❌ (au lieu de 09:15)

**Résultat:** Décalage de +5 heures pour TOUS les rendez-vous.

### La Correction

**Code corrigé:**
```python
# Respecter l'UTC de l'API (le 'Z' est fiable)
dt_utc = dt.fromisoformat(start_time)  # Parse '2026-01-03T14:15:00Z'
appointment_time = dt_utc.time().isoformat()  # Stocke '14:15:00'
```

**Résultat:**
1. API retourne: `14:15Z` (UTC)
2. DB stocke: `14:15:00` (UTC) ✅
3. Service convertit: 14:15 - 5h = 09:15 (Montreal) ✅
4. Interface affiche: 09:15 ✅

### Pourquoi Caroline est Notre Étalon

Caroline Lessard est le **cas de test obligatoire** pour toute modification du système de timestamps:

- **Si Caroline affiche 09:15 → Le système est correct**
- **Si Caroline affiche autre chose → Le système est cassé**

Avant de commit tout code touchant aux timestamps, vérifier Caroline:

```bash
# Test API
curl "http://localhost:8000/api/chat/appointment/evt_xMjKE8YJCDQmRg7K"
# Doit afficher: 09:15 - 16:40
```

## ⚖️ Règle de Conversion - La Loi V6

### INTERDICTION FORMELLE

Il est **STRICTEMENT INTERDIT** de convertir l'heure lors de l'import.

**❌ Ne JAMAIS faire:**
```python
# Forcer un timezone sur une valeur qui a déjà 'Z'
dt_obj = dt.fromisoformat(start_time.replace('Z', ''))
dt_eastern = dt_obj.replace(tzinfo=eastern_tz)
dt_utc = dt_eastern.astimezone(ZoneInfo('UTC'))
```

**✅ TOUJOURS faire:**
```python
# Respecter le 'Z' (c'est du vrai UTC)
dt_utc = dt.fromisoformat(start_time)
appointment_time = dt_utc.time().isoformat()
```

### UNIQUE CONVERSION AUTORISÉE

La **seule et unique** conversion timezone permise est:

**UTC → America/Montreal au moment de l'affichage final**

**Emplacement:** `api/chat/service.py`, fonction `_convert_utc_to_montreal()` (lignes 689-725)

**Logique:**
```python
def _convert_utc_to_montreal(self, time_utc_str: str) -> str:
    """Convertit UTC → Montreal pour affichage."""
    # Parse l'heure UTC depuis la DB
    hour, minute = time_utc_str.split(":")[:2]
    utc_time = time(int(hour), int(minute))

    # Créer datetime UTC
    utc_tz = pytz.UTC
    montreal_tz = pytz.timezone('America/Montreal')
    today = datetime.now().date()
    utc_datetime = datetime.combine(today, utc_time)
    utc_datetime = utc_tz.localize(utc_datetime)

    # Convertir en Montreal
    montreal_datetime = utc_datetime.astimezone(montreal_tz)

    return montreal_datetime.strftime("%H:%M")
```

## 🔄 Flux de Données Complet

### 1. Gazelle Web → API
```
Utilisateur entre: 09:15 (Toronto)
↓
Gazelle stocke en interne: 09:15 Eastern
↓
API GraphQL retourne: 2026-01-03T14:15:00Z (UTC)
```

### 2. API → Python Fetcher → Supabase
```
Python reçoit: "2026-01-03T14:15:00Z"
↓
Python parse: datetime(2026, 1, 3, 14, 15, 0, tzinfo=UTC)
↓
Python extrait: time(14, 15, 0)
↓
Supabase stocke: "14:15:00" (colonne TIMESTAMPTZ en UTC)
```

### 3. Supabase → Python Service → Frontend
```
Python lit: "14:15:00"
↓
Python convertit: _convert_utc_to_montreal("14:15:00")
↓
Python retourne: "09:15"
↓
Frontend affiche: "09:15 - 16:40"
```

## 🚨 Détection d'Anomalies

### Symptômes d'une Corruption Timezone

1. **Décalage constant** de 5h (hiver) ou 4h (été) entre Gazelle et le Chat
2. **Caroline n'affiche pas 09:15** dans le Chat
3. **DB contient 19:15** au lieu de 14:15 pour Caroline
4. **Utilisateurs rapportent** des heures incorrectes

### Diagnostic Rapide

```bash
# Vérifier l'heure de Caroline en DB
curl "$SUPABASE_URL/rest/v1/gazelle_appointments?external_id=eq.evt_xMjKE8YJCDQmRg7K&select=appointment_time" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY"

# Doit retourner: "14:15:00"
# Si retourne "19:15:00" → Double conversion détectée
```

### Procédure de Correction

**❌ Ne PAS faire:**
- Créer une vue SQL qui soustrait des heures
- Ajouter un offset dans `service.py`
- Patcher les données manuellement avec UPDATE

**✅ Faire:**
1. Corriger le code Python (`sync_to_supabase.py`)
2. Vider la table (`TRUNCATE gazelle_appointments`)
3. Réimporter complètement (exécuter `sync_all()`)
4. Valider avec Caroline

**Référence:** Voir [SYNC_STRATEGY.md](./SYNC_STRATEGY.md#procédure-de-migration-reset-complet)

## 🧠 Intelligence pour l'IA

### Contexte pour Claude/Cursor

Quand tu lis ce document, comprends que:

1. **Le 'Z' n'est pas une erreur** - C'est le marqueur UTC standard (ISO 8601)
2. **Gazelle ne "ment" pas** - L'API retourne correctement du UTC
3. **La donnée en DB est la source de vérité** - Ne jamais "corriger" une donnée propre
4. **Caroline est ton test** - Avant tout commit, vérifie que Caroline affiche 09:15

### Heuristique de Validation

```python
# Avant de modifier du code touchant aux timestamps:

def validate_timezone_logic():
    """
    Vérifie que Caroline Lessard affiche 09:15.

    Si elle affiche autre chose, STOP et debug.
    """
    apt = get_appointment("evt_xMjKE8YJCDQmRg7K")

    # DB doit contenir 14:15:00 UTC
    assert apt['appointment_time'] == '14:15:00', "DB corrompue"

    # Service doit afficher 09:15 Montreal
    display_time = convert_utc_to_montreal('14:15:00')
    assert display_time == '09:15', "Conversion cassée"

    return True
```

## 📚 Documentation Liée

- [SYNC_STRATEGY.md](./SYNC_STRATEGY.md) - Implémentation technique
- [TIMEZONE_BUG_GAZELLE.md](./TIMEZONE_BUG_GAZELLE.md) - Historique du bug
- [TIMEZONE_SOLUTION_FINALE.md](./TIMEZONE_SOLUTION_FINALE.md) - Solution implémentée

## 📅 Historique

- **2025-12-29**: Découverte du bug de double conversion (décalage +5h)
- **2025-12-29**: Correction du code + réimportation complète
- **2025-12-29**: Création de ce document (GEOGRAPHY_LOGIC.md)

---

**Auteur**: Claude Sonnet 4.5 + Allan Sutton + Gemini
**Validation**: Caroline Lessard (evt_xMjKE8YJCDQmRg7K) ✅
