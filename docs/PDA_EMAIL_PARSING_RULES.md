# Règles d'Extraction Emails PDA - Documentation

## 🎯 Objectif

Améliorer la logique de parsing des courriels Place des Arts selon 4 règles strictes pour garantir la qualité et la cohérence des données extraites.

---

## ✅ Règle 1: Champ Demandeur Vierge

### Principe
**Si le Demandeur n'est pas explicitement nommé (nom de personne), laisser le champ VIDE.**

### Interdiction
- ❌ Ne JAMAIS deviner depuis un code de salle (WP, TM, MS, SCL, etc.)
- ❌ Ne JAMAIS utiliser d'initiales non reconnues

### Logique Implémentée

```python
# Si c'est un code de salle → VIDER
room_codes = ['wp', 'tm', 'ms', 'tjd', '5e', 'scl', 'cl', 'sd', 'c5', 'odm']
if requester_lower in room_codes:
    result['requester'] = ''  # Champ vide
```

### Mapping Noms Connus
```python
requester_mapping = {
    'isabelle': 'IC',           # Isabelle Clairoux
    'isabelle clairoux': 'IC',
    'isabelle constantineau': 'IC',
    'clairoux': 'IC',          # Nom de famille seul
}
```

**RÈGLE SPÉCIALE:** Quand c'est Isabelle (peu importe variante), **toujours IC**.

### Validation
- Initiales courtes (1-2 lettres) → Vérifier si code connu (IC, AJ, PT)
- Si code inconnu → Vider le champ

---

## ✅ Règle 2: Utiliser le Champ Commentaire

### Principe
**Utiliser le champ 'Commentaire' (existant) pour extraire les infos contextuelles.**

### Exemples
- ✅ "alternative du samedi 10 janvier" → `notes` field
- ✅ "si possible avant midi" → `notes` field
- ✅ Jour de la semaine (samedi/dimanche) → Ajouté au `notes` field

### Implémentation

**Format tabulaire (colonnes):**
```
Colonne 9: Commentaire (notes contextuelles)
```

**Logique:**
```python
# Colonne 9 = Commentaire
notes_raw = parts[9] if len(parts) >= 10 else ''

# Si c'est un weekend, enrichir avec le jour
if is_weekend:
    if notes_raw:
        notes = f"{jour_semaine} - {notes_raw}"
    else:
        notes = jour_semaine
else:
    notes = notes_raw
```

### Résultat
- L'information contextuelle n'est JAMAIS perdue
- Les alternatives/notes spéciales sont préservées
- Le jour (samedi/dimanche) est automatiquement ajouté si pertinent

---

## ✅ Règle 3: Standardisation des Salles

### Principe
**La PDA n'a que quelques salles fixes. Mapper les abréviations vers noms standards SANS inventer de préfixes.**

### Salles Fixes PDA

| Code | Nom Complet |
|------|-------------|
| **MS** | Maison Symphonique |
| **5E** | 5e salle |
| **TM** | Théâtre Maisonneuve |
| **TJD** | Théâtre Jean-Duceppe |
| **WP** | Wilfrid-Pelletier |
| **WP loge A** | Wilfrid-Pelletier loge A |
| **SCL** | Claude-Léveillée |

### Normalisation

**Interdiction:**
- ❌ "Studio Claude-Léveillée" → Juste **SCL**
- ❌ "Salle Claude-Léveillée" → Juste **SCL**
- ❌ Inventer des préfixes ("Studio", "Salle", etc.)

**Mapping:**
```python
# CL → SCL (standard)
if room_text.upper() == 'CL':
    return 'SCL'

# Abréviations → Codes standards
room_mapping = {
    'claude-léveillée': 'SCL',       # PAS "Studio SCL"
    'claude léveillée': 'SCL',       # PAS "Salle SCL"
    'wilfrid': 'WP',
    'pelletier': 'WP',
    'maisonneuve': 'TM',
    '5e salle': '5E',
    'jean-duceppe': 'TJD',
}
```

### Cas Spécial: WP loge A
```python
if 'loge' in room_text.lower() and 'wp' in room_text.lower():
    return 'WP loge A'
```

---

## ✅ Règle 4: Séparation Date / Heure

### Principe
**Ne JAMAIS mélanger la date et l'heure dans le même champ.**

### Structure

**Date:**
- Format: `YYYY-MM-DD` uniquement
- Champ: `appointment_date`
- Exemple: `2026-01-15`

**Heure:**
- Format: Texte libre (ex: "Avant 10h", "14h30", "10h")
- Champ: `time`
- Exemple: `"Avant 10h"`, `"14h30"`

### Implémentation

```python
# Date RDV (colonne 1) - YYYY-MM-DD seulement
appt_date = parse_date_with_year(appt_date_raw, current_date)

# Heure (colonne 7) - Texte libre
time_str = parts[7] if len(parts) >= 8 else ''

# Stockage séparé
{
    'date': appt_date,          # datetime object → YYYY-MM-DD
    'time': time_str,           # String: "Avant 10h", "14h30"
}
```

### Exemples

| Input Email | Date Extraite | Heure Extraite |
|-------------|---------------|----------------|
| "15 janvier avant 10h" | `2026-01-15` | `"avant 10h"` |
| "20 jan 14h30" | `2026-01-20` | `"14h30"` |
| "5 février après 9h" | `2026-02-05` | `"après 9h"` |

### Interdiction
- ❌ Date + heure mélangées: `"2026-01-15 avant 10h"`
- ❌ Heure dans le champ date
- ❌ Date dans le champ heure

---

## 📊 Format de Sortie

### Structure Complète

```python
{
    'date': datetime(2026, 1, 15),  # YYYY-MM-DD (datetime object)
    'request_date': datetime(2026, 1, 10) or None,
    'time': "Avant 10h",            # Heure (string)
    'room': "SCL",                  # Code standardisé (pas de préfixe)
    'piano': "Steinway D (9')",
    'for_who': "Concert Orchestre",
    'diapason': "442",
    'requester': "IC",              # Code ou VIDE (jamais code de salle)
    'notes': "samedi - alternative du 10 janvier",  # Commentaire enrichi
    'technician': "Allan",
    'technician_id': "usr_allan",
    'service': "Accord standard",
    'confidence': 1.0,
    'warnings': []
}
```

---

## 🧪 Tests de Validation

### Test 1: Demandeur Vierge

**Input:**
```
Demandeur: WP
```

**Attendu:**
```python
result['requester'] = ''  # Vide (code de salle)
```

---

### Test 2: Mapping Isabelle → IC

**Input:**
```
Demandeur: Isabelle Clairoux
```

**Attendu:**
```python
result['requester'] = 'IC'
```

**Input:**
```
Demandeur: clairoux
```

**Attendu:**
```python
result['requester'] = 'IC'
```

---

### Test 3: Standardisation Salle

**Input:**
```
Salle: CL
```

**Attendu:**
```python
result['room'] = 'SCL'  # PAS "Studio CL", juste "SCL"
```

**Input:**
```
Salle: Studio Claude-Léveillée
```

**Attendu:**
```python
result['room'] = 'SCL'  # PAS "Studio SCL"
```

---

### Test 4: Séparation Date/Heure

**Input:**
```
15 janvier avant 10h
```

**Attendu:**
```python
{
    'date': datetime(2026, 1, 15),  # Date seule
    'time': 'avant 10h'              # Heure seule
}
```

---

### Test 5: Commentaire Préservé

**Input (colonne 9):**
```
Commentaire: alternative du samedi 10 janvier
```

**Attendu:**
```python
result['notes'] = 'samedi - alternative du samedi 10 janvier'
# Jour weekend ajouté + commentaire préservé
```

---

## 📂 Fichiers Modifiés

### `modules/place_des_arts/services/email_parser.py`

**Fonctions modifiées:**
1. `normalize_room()` - Règle 3 (standardisation salles)
2. `parse_tabular_rows()` - Règles 1, 2, 4 (demandeur, commentaire, date/heure)
3. `parse_email_block()` - Règle 1 (demandeur vierge)

**Lignes clés:**
- Lignes 131-210: `normalize_room()` avec salles fixes PDA
- Lignes 247-322: `parse_tabular_rows()` avec 4 règles appliquées
- Lignes 595-626: Validation demandeur (pas de codes de salle)

---

## 🚀 Utilisation

### Import

```python
from modules.place_des_arts.services.email_parser import parse_email_text
```

### Exemple

```python
email_text = """
15 janvier avant 10h - SCL - Piano Steinway - Accord 442
Pour: Concert Orchestre
Demandeur: Isabelle Clairoux
Commentaire: alternative du samedi 10 janvier si possible
"""

requests = parse_email_text(email_text)

print(requests[0])
# {
#     'date': datetime(2026, 1, 15),
#     'time': 'avant 10h',
#     'room': 'SCL',
#     'requester': 'IC',
#     'notes': 'samedi - alternative du samedi 10 janvier si possible',
#     ...
# }
```

---

## ✅ Checklist Conformité

Avant de valider une extraction, vérifier:

- [ ] **Demandeur:** Vide si pas un nom de personne (pas de code de salle)
- [ ] **Isabelle:** Toujours mappé à "IC"
- [ ] **Salle:** Code standard SANS préfixe (SCL, pas "Studio SCL")
- [ ] **Date:** Format `YYYY-MM-DD` uniquement
- [ ] **Heure:** Champ séparé (ex: "Avant 10h")
- [ ] **Commentaire:** Infos contextuelles préservées dans `notes`

---

## 📞 Support

Pour questions ou ajustements des règles de parsing:
- Consulter ce document
- Vérifier `email_parser.py` (lignes indiquées)
- Tester avec `parse_email_text()` sur échantillons réels
