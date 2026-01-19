# 🤖 Résumés Intelligents - Guide Technique

**Date:** 2026-01-18
**Feature:** Génération automatique de résumés contextuels pour clients et pianos

---

## 🎯 Objectif

Générer des résumés intelligents qui analysent automatiquement l'historique d'un client ou d'un piano pour fournir un contexte rapide et pertinent au technicien.

### Avant (limité):
```
Client: Harry Kirschner
Téléphone: (438) 990-8650
Services: Heintzman Upright - Accord 2h ($250)
```

### Après (intelligent):
```
🤖 Résumé Intelligent

👤 Client:
Client depuis 2018 (8 ans), fait accorder son piano chaque année en septembre.
⚠️ Présence de chien nerveux. Préfère communiquer en anglais.

🎹 Piano:
Heintzman Upright de 1975 (51 ans), accordé 1x/an, climat stable.
Dernière réparation: changement feutres (2023).
```

---

## 📊 Architecture

### 1. Backend - Génération (`api/chat/smart_summaries.py`)

```python
class SmartSummaryGenerator:
    def generate_client_summary(
        self,
        client_id: str,
        timeline_entries: List[Dict],
        comfort_info: Dict
    ) -> str:
        """
        Analyse l'historique client et génère un résumé contextuel.

        Infos extraites:
        - Ancienneté (depuis quelle année)
        - Fréquence de service (1x/an, 2x/an, etc.)
        - Mois préféré pour services
        - Langue préférée
        - Animaux (priorité visuelle ⚠️)
        - Tempérament
        - Notes spéciales importantes
        """

    def generate_piano_summary(
        self,
        piano_id: str,
        timeline_entries: List[Dict],
        piano_info: Dict
    ) -> str:
        """
        Analyse l'historique piano et génère un résumé contextuel.

        Infos extraites:
        - Info de base (marque, modèle, année, âge)
        - Life Saver System (Dampp-Chaser)
        - Fréquence d'accord
        - Stabilité climatique (humidité/température)
        - Réparations majeures récentes
        - Problèmes récurrents
        """
```

### 2. API - Intégration (`api/chat/service.py`)

```python
def get_appointment_detail(self, appointment_id: str) -> AppointmentDetail:
    # ... récupération données ...

    # Génération résumés intelligents
    summary_generator = SmartSummaryGenerator(self.storage)

    client_smart_summary = summary_generator.generate_client_summary(
        client_id=client_id,
        timeline_entries=timeline_dict,
        comfort_info=comfort_dict
    )

    piano_smart_summary = summary_generator.generate_piano_summary(
        piano_id=piano_id,
        timeline_entries=timeline_dict,
        piano_info=piano_info
    )

    return AppointmentDetail(
        # ... autres champs ...
        client_smart_summary=client_smart_summary,
        piano_smart_summary=piano_smart_summary
    )
```

### 3. Frontend - Affichage (`frontend/src/components/ChatIntelligent.jsx`)

```jsx
{/* RÉSUMÉS INTELLIGENTS IA */}
{(detail.client_smart_summary || detail.piano_smart_summary) && (
  <Box>
    <Typography variant="h6">🤖 Résumé Intelligent</Typography>

    {/* Résumé Client */}
    {detail.client_smart_summary && (
      <Box sx={{ bgcolor: 'info.light' }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          👤 Client:
        </Typography>
        <Typography>{detail.client_smart_summary}</Typography>
      </Box>
    )}

    {/* Résumé Piano */}
    {detail.piano_smart_summary && (
      <Box sx={{ bgcolor: 'success.light' }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          🎹 Piano:
        </Typography>
        <Typography>{detail.piano_smart_summary}</Typography>
      </Box>
    )}
  </Box>
)}
```

---

## 🔍 Analyses Effectuées

### Résumé Client

#### 1. Ancienneté
```python
first_entry_date = min(timeline_entries, key=lambda x: x['occurred_at'])
years = (datetime.now() - first_entry_date).days // 365

# Output: "Client depuis 2018 (8 ans)"
```

#### 2. Fréquence de Service
```python
# Compter services dernière année
recent_services = filter(
    lambda e: e['entry_type'] in ['SERVICE_ENTRY_MANUAL', 'APPOINTMENT']
              and e['occurred_at'] >= one_year_ago,
    timeline_entries
)

# Output: "accordé 3x/an" | "accordé 2x/an" | "accordé 1x/an"
```

#### 3. Mois Préféré
```python
# Trouver mois le plus fréquent (si pattern évident)
month_counts = Counter([entry['occurred_at'].month for entry in services])
most_common = month_counts.most_common(1)[0]

if most_common[1] >= 3:  # Au moins 3 services dans ce mois
    # Output: "Services habituellement en septembre"
```

#### 4. Animaux (Priorité)
```python
if comfort_info.get('dog_name') or comfort_info.get('cat_name'):
    # Output: "⚠️ Présence de chien Fido (Labrador) et chat Whiskers"
```

#### 5. Notes Importantes
```python
keywords = ['attention', 'prudence', 'nerveux', 'difficile', 'allergique']
if any(keyword in notes.lower() for keyword in keywords):
    # Output: Extrait des notes (max 100 chars)
```

---

### Résumé Piano

#### 1. Info de Base
```python
make = piano_info.get('make')  # "Steinway"
model = piano_info.get('model')  # "D"
year = piano_info.get('year')  # 1968
age = datetime.now().year - int(year)  # 58 ans

# Output: "Steinway D de 1968 (58 ans)"
```

#### 2. Life Saver System
```python
if piano_info.get('has_dampp_chaser'):
    # Output: "équipé Life Saver System"
```

#### 3. Stabilité Climatique
```python
humidity_readings = [entry['metadata']['humidity'] for entry in timeline]
variation = max(humidity_readings) - min(humidity_readings)

if variation <= 5:
    status = "climat très stable"
elif variation <= 10:
    status = "climat stable"
else:
    status = "⚠️ climat instable"

# Output: "climat très stable"
```

#### 4. Réparations Majeures
```python
major_keywords = [
    'remplacement cordes', 'changement cordes',
    'refection', 'réparation majeure', 'restauration'
]

recent_repairs = [
    entry for entry in timeline
    if any(keyword in entry['description'].lower() for keyword in major_keywords)
    and entry['occurred_at'] >= three_years_ago
]

# Output: "Réparations: Changement cordes (2023), Refection marteaux (2022)"
```

#### 5. Problèmes Récurrents
```python
issue_keywords = [
    'humidité', 'désaccord', 'touches collantes',
    'pédale', 'feutres usés', 'cordes cassées'
]

issue_counts = Counter([
    keyword for entry in timeline
    for keyword in issue_keywords
    if keyword in entry['description'].lower()
])

recurring = [issue for issue, count in issue_counts.items() if count >= 3]

# Output: "⚠️ Problème récurrent: humidité"
```

---

## 🎨 Design UI

### Placement
Les résumés intelligents apparaissent dans le drawer de détails d'un rendez-vous, **entre** la section "Sur Place" et la section "Historique":

```
┌─────────────────────────────────────┐
│ 🏠 Sur Place                        │
│   • Contact, téléphone, email       │
│   • Code d'accès, animaux           │
│   • Stationnement, notes spéciales  │
├─────────────────────────────────────┤
│ 🤖 Résumé Intelligent               │ ← NOUVEAU
│                                     │
│ 👤 Client:                          │
│ Client depuis 2018 (8 ans), fait    │
│ accorder son piano chaque année...  │
│                                     │
│ 🎹 Piano:                           │
│ Steinway D de 1968, accordé 3x/an...│
├─────────────────────────────────────┤
│ 📖 Historique                       │
│   • Dernières visites               │
│   • Timeline entries                │
└─────────────────────────────────────┘
```

### Couleurs
- **Client** (bleu clair): `bgcolor: 'info.light'`, bordure `info.main`
- **Piano** (vert clair): `bgcolor: 'success.light'`, bordure `success.main`

### Émojis
- 🤖 = Résumé Intelligent (section header)
- 👤 = Client
- 🎹 = Piano
- ⚠️ = Attention/Alerte (animaux, problèmes)

---

## 📈 Exemples Réels

### Exemple 1: Client Régulier avec Chien

**Input:**
- Client depuis: 2018-03-15
- Services: 2019-09, 2020-09, 2021-09, 2022-09, 2023-09, 2024-09
- Animaux: Chien "Max" (Golden Retriever)
- Notes: "Chien très amical mais excité"

**Output:**
```
👤 Client:
Client depuis 2018 (8 ans), fait accorder son piano chaque année en septembre.
Services habituellement en septembre. ⚠️ Présence de chien Max (Golden Retriever).
Chien très amical mais excité.
```

---

### Exemple 2: Piano Ancien avec Problèmes Récurrents

**Input:**
- Piano: Steinway M, 1952
- Life Saver: Oui
- Humidité: [42%, 44%, 43%, 41%, 45%] (stable)
- Réparations: "Changement cordes" (2023)
- Timeline: 8 mentions de "désaccord fréquent"

**Output:**
```
🎹 Piano:
Steinway M de 1952 (74 ans), accordé 2x/an, équipé Life Saver System.
Climat stable. Réparations: Changement cordes (2023).
⚠️ Problème récurrent: désaccord.
```

---

### Exemple 3: Nouveau Client

**Input:**
- Client depuis: 2025-11-01 (récent)
- Services: 1 seul (2025-11-15)
- Langue: Anglais
- Piano: Yamaha U1, 2010

**Output:**
```
👤 Client:
Nouveau client. Préfère communiquer en anglais.

🎹 Piano:
Yamaha U1 de 2010 (16 ans), accordé 1x/an.
```

---

## 🚀 Utilisation

### Pour le Technicien

1. **Ouvrir l'assistant chat** (http://localhost:5174)
2. **Demander rendez-vous**: "mes rv après-demain"
3. **Cliquer sur une carte** de rendez-vous
4. **Drawer s'ouvre** avec détails complets
5. **Lire résumé intelligent** 🤖 (entre "Sur Place" et "Historique")

### Pour le Développeur

```bash
# Tester la génération de résumé
curl -X POST http://localhost:8000/api/chat/appointments/appt_xxx/detail \
  -H "Content-Type: application/json"

# Réponse contient:
{
  "overview": { ... },
  "comfort": { ... },
  "client_smart_summary": "Client depuis 2018 (8 ans)...",
  "piano_smart_summary": "Steinway D de 1968...",
  "timeline_summary": "...",
  "timeline_entries": [...]
}
```

---

## 🔧 Configuration

### Ajuster les Seuils

Dans `api/chat/smart_summaries.py`:

```python
# Fréquence de service (ajuster selon besoin)
if len(recent_services) >= 3:
    return f"accordé {len(recent_services)}x/an"

# Mois préféré (minimum 3 services)
if count >= 3:  # Ajuster ce seuil
    return month_names[most_common_month]

# Stabilité climatique (variation humidité)
if variation <= 5:      # Très stable
    return "climat très stable"
elif variation <= 10:    # Stable
    return "climat stable"
elif variation <= 15:    # Variable
    return "climat variable"
else:                   # Instable
    return "⚠️ climat instable"

# Problème récurrent (minimum 3 occurrences)
recurring = [issue for issue, count in issue_counts.items() if count >= 3]
```

---

## 🐛 Débogage

### Résumé Manquant

**Symptôme:** Drawer affiche détails mais pas de résumé intelligent

**Causes possibles:**
1. Pas assez d'historique (< 3 entrées)
2. Timeline entries vides
3. Erreur dans génération (voir logs backend)

**Solution:**
```bash
# Vérifier logs backend
tail -f backend.log | grep "smart_summary"

# Tester génération manuellement
python3 -c "
from api.chat.smart_summaries import SmartSummaryGenerator
from core.supabase_storage import SupabaseStorage

gen = SmartSummaryGenerator(SupabaseStorage())
summary = gen.generate_client_summary(
    client_id='cli_xxx',
    timeline_entries=[...],
    comfort_info={...}
)
print(summary)
"
```

---

### Résumé Trop Court

**Symptôme:** Résumé affiche seulement 1-2 phrases

**Cause:** Pas assez de données historiques

**Solution:** Normal pour nouveaux clients. Le résumé s'enrichira au fil du temps.

---

## 📚 Références

### Fichiers Modifiés

- `api/chat/smart_summaries.py` - Générateur de résumés (nouveau)
- `api/chat/schemas.py` - Ajout champs `client_smart_summary` et `piano_smart_summary`
- `api/chat/service.py` - Intégration génération dans `get_appointment_detail()`
- `frontend/src/components/ChatIntelligent.jsx` - Affichage dans drawer

### Dépendances

Aucune nouvelle dépendance Python requise. Utilise:
- `datetime` (stdlib)
- `re` (stdlib)
- `typing` (stdlib)

---

**Créé le:** 2026-01-18
**Par:** Claude Code
**Statut:** ✅ PRODUCTION READY
**Testé:** ✅ API + Frontend
