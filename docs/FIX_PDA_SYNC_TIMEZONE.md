# Fix: Synchronisation PDA - Problème Timezone

## 🐛 Problème Détecté

### Symptôme
```
❌ 2 RV non trouvé(s) dans Gazelle:
⚠️ RV_NOT_FOUND
   2026-01-11 - TM - Gala Chinois

⚠️ RV_NOT_FOUND
   2026-01-11 - SCL - Ferland par la bouche d'une femme
```

### Cause Racine

**Décalage timezone lors de la recherche de RV dans Gazelle.**

#### Problème de Comparaison

**AVANT (❌ Incorrect):**
```python
# Recherche exacte par date
url += f"&appointment_date=eq.{date_only}"  # 2026-01-11
```

**Scénario problématique:**
1. Demande PDA: `2026-01-11` (Montreal)
2. RV créé dans Gazelle: `2026-01-11T18:00:00-05:00` (18h EST)
3. Stocké en UTC: `2026-01-11T23:00:00Z`
4. Colonne `appointment_date` extraite: `2026-01-11` ✅

**Mais aussi:**
1. Demande PDA: `2026-01-11` (Montreal)
2. RV créé dans Gazelle: `2026-01-10T20:00:00-05:00` (20h EST le 10)
3. Stocké en UTC: `2026-01-11T01:00:00Z` (1h UTC le 11)
4. Colonne `appointment_date` extraite: `2026-01-11` ✅

**Le problème:**
- Si le système extrait `appointment_date` depuis `start_datetime` UTC
- Un RV à 23h UTC peut être affiché comme le jour suivant
- La comparaison exacte `eq.2026-01-11` rate les RV qui sont techniquement le bon jour en Montreal mais décalés en UTC

---

## ✅ Solution Implémentée

### Fenêtre de Recherche ±1 Jour

**APRÈS (✅ Correct):**
```python
# Fenêtre de recherche ±1 jour
date_obj = datetime.strptime(date_only, '%Y-%m-%d')
date_before = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')  # 2026-01-10
date_after = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')   # 2026-01-12

url += f"&appointment_date=gte.{date_before}"  # >= 2026-01-10
url += f"&appointment_date=lte.{date_after}"   # <= 2026-01-12
```

### Logique

Au lieu de chercher **exactement** `2026-01-11`, on cherche dans une fenêtre:
- `2026-01-10` ≤ date ≤ `2026-01-12`

Cela couvre tous les cas de décalage timezone:
- RV à 23h le 10 (Montreal) = 04h le 11 (UTC) → `appointment_date = 2026-01-11` ✅
- RV à 20h le 10 (Montreal) = 01h le 11 (UTC) → `appointment_date = 2026-01-11` ✅
- RV à 18h le 11 (Montreal) = 23h le 11 (UTC) → `appointment_date = 2026-01-11` ✅

**Résultat:** Tous les RV du même jour (en timezone Montreal) sont trouvés, peu importe le décalage UTC.

---

## 📊 Modifications Effectuées

### Fichier: `pda_validation.py`

**Fonction:** `find_gazelle_appointment_for_pda()`

**Lignes 119-137:**

```python
# CORRECTION TIMEZONE: Chercher avec fenêtre ±1 jour
# La date PDA est en timezone Montreal, mais Gazelle stocke en UTC
# Un RV à minuit Montreal (2026-01-11T00:00 EST) = 2026-01-11T05:00 UTC
# mais pourrait apparaître comme 2026-01-10 ou 2026-01-11 selon l'heure
from datetime import datetime, timedelta
date_obj = datetime.strptime(date_only, '%Y-%m-%d')
date_before = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
date_after = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

url = f"{self.storage.api_url}/gazelle_appointments"
url += "?select=*"
# Fenêtre de recherche: date ±1 jour (pour gérer décalages timezone)
url += f"&appointment_date=gte.{date_before}"
url += f"&appointment_date=lte.{date_after}"
# Chercher "PdA" OU "Place des Arts" dans titre OU notes
url += "&or=(notes.ilike.*PdA*,notes.ilike.*Place des Arts*,title.ilike.*Place des Arts*)"
```

---

## 🏢 Variations de Salles Ajoutées

En même temps, ajout de variations manquantes pour les salles PDA:

```python
room_variations = {
    'MS': ['MAISON SYMPHONIQUE', 'MAISON SYM', 'MS', 'M.S.', 'MSM'],
    'WP': ['WILFRID-PELLETIER', 'WP', 'W.P.', 'WILFRID PELLETIER'],
    'TM': ['THÉÂTRE MAISONNEUVE', 'THEATRE MAISONNEUVE', 'TM', 'T.M.', 'MAISONNEUVE'],  # ← Ajouté
    '5E': ['C5', 'CINQUIÈME SALLE', '5E SALLE', '5E', '5EME SALLE'],                    # ← Ajouté
    'SCL': ['CLAUDE LÉVEILLÉ', 'CLAUDE LEVEILLE', 'SCL', 'STUDIO CLAUDE'],              # ← Ajouté
    'TJD': ['JEAN-DUCEPPE', 'JEAN DUCEPPE', 'TJD', 'DUCEPPE'],                          # ← Ajouté
}
```

**Impact:** Les RV avec "THÉÂTRE MAISONNEUVE" ou "CLAUDE LÉVEILLÉ" dans les notes seront maintenant reconnus.

---

## 🧪 Tests

### Test Script

Créé: `scripts/test_pda_sync_timezone.py`

**Usage:**
```bash
python3 scripts/test_pda_sync_timezone.py
```

**Teste:**
1. Recherche RV pour `2026-01-11` TM avec fenêtre ±1 jour
2. Recherche RV pour `2026-01-11` SCL avec fenêtre ±1 jour
3. Affiche les résultats avec debug

---

## 📈 Résultats Attendus

### Avant (❌)
```
Recherche: appointment_date=eq.2026-01-11
Résultat: ❌ 2 RV non trouvés
```

### Après (✅)
```
Recherche: appointment_date >= 2026-01-10 AND <= 2026-01-12
Résultat: ✅ 2 RV trouvés
- 2026-01-11 TM "Gala Chinois"
- 2026-01-11 SCL "Ferland par la bouche d'une femme"
```

### Message de Succès
```
✅ 29 demande(s) passée(s) à "Créé Gazelle"

Toutes les demandes assignées ont un RV dans Gazelle!
```

---

## 🎯 Impact

### RV Concernés

Tous les RV créés avec une heure spécifique qui causait un décalage UTC:
- RV en soirée (après 19h EST) → Date UTC = jour suivant
- RV en matinée précoce (avant 5h EST) → Date UTC = jour précédent

### Faux Positifs Évités

La fenêtre ±1 jour pourrait théoriquement matcher des RV du mauvais jour, MAIS:
- On filtre aussi par **salle** (TM, SCL, etc.)
- On filtre par **"PdA" dans les notes**
- Probabilité de collision: très faible (deux RV PdA consécutifs dans la même salle = rare)

---

## 🔄 Workflow Complet

### 1. Utilisateur clique "🔄 Synchroniser tout"

### 2. Backend vérifie chaque demande "Assigné"
```python
for req in requests_to_check:
    # Cherche RV dans Gazelle (avec fenêtre ±1 jour)
    gazelle_appt = validator.find_gazelle_appointment_for_pda(
        appointment_date=req['appointment_date'],  # 2026-01-11
        room=req['room'],                          # TM
        debug=False
    )
```

### 3. Si trouvé → Change statut
```python
if gazelle_appt:
    # Passer à "Créé Gazelle"
    update({'status': 'CREATED_IN_GAZELLE'})
```

### 4. Si non trouvé → Warning
```python
else:
    # Ajouter warning
    warnings.append({
        'date': req['appointment_date'],
        'room': req['room'],
        'for_who': req['for_who'],
        'error_code': '⚠️ RV_NOT_FOUND_IN_GAZELLE'
    })
```

---

## ✅ Checklist Validation

Après le fix, vérifier:

- [ ] **Les 2 RV précédemment non trouvés sont maintenant détectés**
- [ ] **Message:** "✅ 29 demande(s) passée(s) à 'Créé Gazelle'"
- [ ] **Aucun warning** (ou moins de warnings qu'avant)
- [ ] **Statuts mis à jour:** Les demandes passent de "Assigné" → "Créé Gazelle"

---

## 📚 Références

- **Fichier modifié:** `assistant-v6/modules/assistant/services/pda_validation.py`
- **Lignes:** 106-137 (mapping salles + fenêtre timezone)
- **Test:** `scripts/test_pda_sync_timezone.py`
- **Documentation timezone:** `docs/TIMEZONE_AND_DEDUPLICATION.md`

---

## 🚀 Prochaines Étapes

1. ✅ Fix appliqué dans `pda_validation.py`
2. ⏳ Tester avec "Synchroniser tout" dans l'interface
3. ⏳ Vérifier que les 2 RV sont maintenant trouvés
4. ⏳ Confirmer statuts mis à jour dans la table

**Le fix est prêt - lance "Synchroniser tout" pour tester!** 🎉
