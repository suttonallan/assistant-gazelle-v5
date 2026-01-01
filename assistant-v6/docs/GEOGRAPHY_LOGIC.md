# Geography Logic - Assistant Gazelle V6

## 📋 Document "Source de Vérité"

**Objectif:** Définir la logique de mapping codes postaux → quartiers pour optimisation des tournées

**Date création:** 2025-12-29
**Dernière mise à jour:** 2025-12-29

---

## 🎯 Principe Fondamental: Quartiers > Villes

**Problème à résoudre:**
```
❌ MAUVAIS (trop vague)
- Montréal (45+ quartiers)
- Laval (15+ quartiers)

✅ BON (précis)
- Rosemont (H2G)
- Plateau Mont-Royal (H2W)
- Laval (Chomedey) (H7V)
```

**Pourquoi:**
- Technicien planifie tournée: "Je fais Rosemont demain"
- Gain de temps: grouper RV par quartier, pas par ville
- Estimation km: Rosemont → Plateau = 5 km, Rosemont → Anjou = 20 km

---

## 🗺️ Architecture Géographique

### Zones Couvertes

```
RÉGION MÉTROPOLITAINE MONTRÉAL
├── Montréal (île)
│   ├── Centre (Plateau, McGill, Centre-Sud)
│   ├── Nord (Rosemont, Villeray, Ahuntsic)
│   ├── Ouest (NDG, Westmount, Côte-des-Neiges)
│   ├── Est (Hochelaga, Mercier, Anjou)
│   └── Ouest-de-l'île (Pointe-Claire, Kirkland)
│
├── Laval
│   ├── Pont-Viau (H7N)
│   ├── Chomedey (H7V)
│   ├── Sainte-Rose (H7W)
│   └── Vimont (H7X)
│
├── Rive-Sud
│   ├── Longueuil (J4J, J4K, J4L)
│   ├── Brossard (J4W, J4X, J4Y, J4Z)
│   ├── Saint-Lambert (J5A)
│   └── Saint-Bruno (J3V)
│
└── Rive-Nord
    ├── Terrebonne (J6A, J6W)
    ├── Blainville (J7H)
    ├── Saint-Eustache (J7J)
    └── Repentigny (J7A)
```

---

## 📚 Dictionnaire Postal

### Format Code Postal Canadien

**Structure:** `A9A 9A9`
- Exemple: `H2G 2J8`
- Les **3 premiers caractères** déterminent la zone

**Utilisation:**
```python
code_complet = "H2G 2J8"
zone = code_complet[:3]  # "H2G"
quartier = mapping[zone]  # "Rosemont"
```

### Mapping Complet (100+ Codes)

**Fichier:** `api/chat/geo_mapping.py` (V5) → `core/utils/geography.py` (V6)

```python
MTL_POSTAL_TO_NEIGHBORHOOD = {
    # ============================================================
    # MONTRÉAL CENTRAL & PLATEAU
    # ============================================================
    'H2W': 'Plateau Mont-Royal',
    'H2J': 'Plateau Mont-Royal',
    'H2T': 'Plateau Mont-Royal',
    'H2H': 'Plateau (Est)',
    'H2X': 'McGill / Place-des-Arts',
    'H2L': 'Centre-Sud',

    # ============================================================
    # NORD & ROSEMONT
    # ============================================================
    'H2R': 'Villeray',
    'H2S': 'Petite-Patrie',
    'H2G': 'Rosemont',
    'H1Y': 'Rosemont (Est)',
    'H2E': 'Villeray (Nord)',
    'H2P': 'Villeray (Parc-Jarry)',

    # ============================================================
    # OUEST & SUD-OUEST
    # ============================================================
    'H3Y': 'Westmount',
    'H3Z': 'Westmount',
    'H4C': 'Saint-Henri',
    'H3J': 'Petite-Bourgogne',
    'H4E': 'Verdun / Ville Émard',
    'H3K': 'Pointe-Saint-Charles',
    'H3H': 'Downtown / Shaughnessy',

    # ============================================================
    # OUTREMONT & CÔTE-DES-NEIGES
    # ============================================================
    'H2V': 'Outremont',
    'H3P': 'Mont-Royal (TMR)',
    'H3S': 'Côte-des-Neiges',
    'H3T': 'Côte-des-Neiges (Ouest)',

    # ============================================================
    # HOCHELAGA & EST
    # ============================================================
    'H1W': 'Hochelaga',
    'H1V': 'Maisonneuve',
    'H1N': 'Mercier',
    'H1M': 'Anjou',

    # ============================================================
    # NDG & OUEST-DE-L'ÎLE
    # ============================================================
    'H4A': 'NDG (Sherbrooke)',
    'H4B': 'NDG (Ouest)',
    'H3N': 'NDG (Monkland)',
    'H9A': 'Pointe-Claire',
    'H9B': 'Beaconsfield',
    'H9H': 'Kirkland',

    # ============================================================
    # LAVAL
    # ============================================================
    'H7N': 'Laval (Pont-Viau)',
    'H7V': 'Laval (Chomedey)',
    'H7W': 'Laval (Sainte-Rose)',
    'H7X': 'Laval (Vimont)',
    'H7Y': 'Laval (Auteuil)',
    'H7E': 'Laval (Duvernay)',

    # ============================================================
    # RIVE-SUD (LONGUEUIL & ENVIRONS)
    # ============================================================
    'J4J': 'Longueuil',
    'J4K': 'Longueuil',
    'J4L': 'Longueuil',
    'J4M': 'Longueuil (Saint-Hubert)',
    'J4N': 'Longueuil (Saint-Hubert)',
    'J3Y': 'Saint-Hubert',
    'J4B': 'Boucherville',
    'J4G': 'Greenfield Park',
    'J4H': 'Greenfield Park',

    # ============================================================
    # RIVE-SUD (AUTRES)
    # ============================================================
    'J4W': 'Brossard',
    'J4X': 'Brossard',
    'J4Y': 'Brossard',
    'J4Z': 'Brossard',
    'J5A': 'Saint-Lambert',
    'J3V': 'Saint-Bruno',

    # ============================================================
    # RIVE-NORD
    # ============================================================
    'J7H': 'Blainville',
    'J7C': 'Rosemère',
    'J7A': 'Repentigny',
    'J6A': 'Terrebonne',
    'J6W': 'Terrebonne (Lachenaie)',
    'J7J': 'Saint-Eustache',
    'J7R': 'Boisbriand',

    # ============================================================
    # AUTRES ZONES FRÉQUENTES
    # ============================================================
    'H1K': 'Montréal-Nord',
    'H1H': 'Rivière-des-Prairies',
    'H1G': 'Pointe-aux-Trembles',
    'H8R': 'LaSalle',
    'H8N': 'LaSalle',
    'H8P': 'LaSalle',
    'H9K': 'Dollard-des-Ormeaux',
    'H9J': 'Pierrefonds',
}
```

**Coverage:** 100+ codes postaux couvrant:
- Île de Montréal complète
- Laval complète
- Rive-Sud (Longueuil, Brossard, Saint-Lambert, Saint-Bruno)
- Rive-Nord (Terrebonne, Blainville, Repentigny)

---

## 🔧 Fonctions Utilitaires

### Fonction 1: get_neighborhood_from_postal_code()

**Responsabilité:** Convertir code postal → quartier

**Signature:**
```python
def get_neighborhood_from_postal_code(
    postal_code: str,
    fallback_city: str = None
) -> str:
    """
    Extrait le quartier à partir d'un code postal.

    Args:
        postal_code: Code postal complet (ex: "H2G 2J8")
        fallback_city: Ville à utiliser si le code postal n'est pas dans le mapping

    Returns:
        Nom du quartier ou ville

    Examples:
        >>> get_neighborhood_from_postal_code("H2G 2J8")
        'Rosemont'

        >>> get_neighborhood_from_postal_code("J9Z 1A1", "Sainte-Thérèse")
        'Sainte-Thérèse'

        >>> get_neighborhood_from_postal_code("", "Montréal")
        'Montréal'
    """
```

**Logique:**
```python
# 1. Nettoyer le code postal
cleaned = ''.join(c.upper() for c in postal_code if c.isalnum())[:3]
# "H2G 2J8" → "H2G"
# "h2g2j8"  → "H2G"

# 2. Lookup dans le dictionnaire
neighborhood = MTL_POSTAL_TO_NEIGHBORHOOD.get(cleaned)
# "H2G" → "Rosemont"

# 3. Fallback si non trouvé
if not neighborhood:
    return fallback_city or cleaned
# "J9Z" → "Sainte-Thérèse" (fallback)
```

### Fonction 2: format_neighborhood_display()

**Responsabilité:** Formatter pour affichage UI

**Signature:**
```python
def format_neighborhood_display(
    postal_code: str,
    city: str = None
) -> str:
    """
    Formate l'affichage du quartier avec le code postal entre parenthèses.

    Examples:
        >>> format_neighborhood_display("H2G 2J8", "Montréal")
        'Rosemont (H2G)'

        >>> format_neighborhood_display("J9Z 1A1", "Sainte-Thérèse")
        'Sainte-Thérèse'
    """
```

**Logique:**
```python
neighborhood = get_neighborhood_from_postal_code(postal_code, city)

# Si mapping trouvé, ajouter code entre parenthèses
if cleaned_code in MTL_POSTAL_TO_NEIGHBORHOOD:
    return f"{neighborhood} ({cleaned_code})"
# "Rosemont (H2G)"

# Sinon, juste le nom de ville
return neighborhood
# "Sainte-Thérèse"
```

---

## 🧪 Tests de Mapping

### Test 1: Codes Connus

```python
# tests/unit/test_geography.py
def test_known_postal_codes():
    """Test codes postaux connus."""

    assert get_neighborhood_from_postal_code("H2G 2J8") == "Rosemont"
    assert get_neighborhood_from_postal_code("H2W 1A1") == "Plateau Mont-Royal"
    assert get_neighborhood_from_postal_code("J4W 2B2") == "Brossard"
    assert get_neighborhood_from_postal_code("H7V 3C3") == "Laval (Chomedey)"
```

### Test 2: Codes Inconnus avec Fallback

```python
def test_unknown_postal_codes_with_fallback():
    """Test codes inconnus utilisent fallback."""

    result = get_neighborhood_from_postal_code("J9Z 1A1", "Sainte-Thérèse")
    assert result == "Sainte-Thérèse"

    result = get_neighborhood_from_postal_code("X0X 0X0", "Autre Ville")
    assert result == "Autre Ville"
```

### Test 3: Formats Variés

```python
def test_postal_code_formats():
    """Test différents formats de codes postaux."""

    # Avec espace
    assert get_neighborhood_from_postal_code("H2G 2J8") == "Rosemont"

    # Sans espace
    assert get_neighborhood_from_postal_code("H2G2J8") == "Rosemont"

    # Minuscules
    assert get_neighborhood_from_postal_code("h2g 2j8") == "Rosemont"

    # Avec caractères bizarres
    assert get_neighborhood_from_postal_code("H2G-2J8") == "Rosemont"
```

---

## 📊 Statistiques de Couverture

### Par Région

```sql
-- Requête: Nombre de clients par région
SELECT
    SUBSTRING(postal_code, 1, 1) as region_code,
    CASE
        WHEN SUBSTRING(postal_code, 1, 1) = 'H' THEN 'Montréal & Laval'
        WHEN SUBSTRING(postal_code, 1, 1) = 'J' THEN 'Rive-Sud & Rive-Nord'
        ELSE 'Autre'
    END as region,
    COUNT(*) as client_count
FROM gazelle_clients
WHERE postal_code IS NOT NULL
GROUP BY region_code
ORDER BY client_count DESC;

-- Résultat attendu:
-- H | Montréal & Laval | 850
-- J | Rive-Sud & Nord  | 320
```

### Par Quartier

```python
# Script analytics
from collections import Counter

def analyze_neighborhood_distribution():
    """Analyse distribution des clients par quartier."""

    clients = supabase.table('gazelle_clients').select('postal_code').execute()

    neighborhoods = []
    for client in clients.data:
        postal = client.get('postal_code')
        if postal:
            neighborhood = get_neighborhood_from_postal_code(postal)
            neighborhoods.append(neighborhood)

    # Count
    counter = Counter(neighborhoods)

    # Top 10 quartiers
    print("Top 10 quartiers:")
    for neighborhood, count in counter.most_common(10):
        print(f"{neighborhood}: {count} clients")

# Output attendu:
# Rosemont: 120 clients
# Plateau Mont-Royal: 95 clients
# Westmount: 75 clients
# Côte-des-Neiges: 68 clients
# ...
```

---

## 🚗 Optimisation de Tournées

### Grouper RV par Quartier

**Use Case:** "Afficher tous mes RV de demain groupés par quartier"

```python
# api/chat/service.py
def group_appointments_by_neighborhood(appointments):
    """
    Groupe les RV par quartier pour optimisation tournée.

    Returns:
        {
            'Rosemont': [appt1, appt2, appt3],
            'Plateau Mont-Royal': [appt4, appt5],
            ...
        }
    """
    grouped = {}

    for apt in appointments:
        # Extraire quartier
        postal_code = apt.get('location', {}).get('postal_code')
        city = apt.get('location', {}).get('city')

        neighborhood = get_neighborhood_from_postal_code(postal_code, city)

        # Grouper
        if neighborhood not in grouped:
            grouped[neighborhood] = []

        grouped[neighborhood].append(apt)

    return grouped
```

**Affichage UI:**
```
📍 ROSEMONT (3 RV)
  09:00 - M. Tremblay
  11:00 - École Primaire XYZ
  14:00 - Mme Dubois

📍 PLATEAU MONT-ROYAL (2 RV)
  10:30 - M. Lavoie
  15:00 - Mme Roy
```

### Estimation Distances

**V6 Future:** Intégration Google Maps Distance Matrix API

```python
# core/utils/geography.py (V6)
from geopy.distance import geodesic

def estimate_travel_time(from_neighborhood: str, to_neighborhood: str) -> int:
    """
    Estime le temps de trajet entre deux quartiers (minutes).

    Args:
        from_neighborhood: "Rosemont"
        to_neighborhood: "Plateau Mont-Royal"

    Returns:
        Temps estimé en minutes
    """
    # Lookup coordonnées centrales de chaque quartier
    coords_from = NEIGHBORHOOD_CENTERS.get(from_neighborhood)
    coords_to = NEIGHBORHOOD_CENTERS.get(to_neighborhood)

    if not coords_from or not coords_to:
        return 30  # Fallback

    # Distance à vol d'oiseau
    distance_km = geodesic(coords_from, coords_to).kilometers

    # Estimation: 30 km/h en ville
    travel_minutes = int((distance_km / 30) * 60)

    return max(travel_minutes, 10)  # Minimum 10 min
```

---

## 🗺️ Coordonnées Centres de Quartiers (V6)

**Pour calculs de distance:**

```python
NEIGHBORHOOD_CENTERS = {
    # Format: (latitude, longitude)
    'Rosemont': (45.5415, -73.6008),
    'Plateau Mont-Royal': (45.5200, -73.5800),
    'Westmount': (45.4833, -73.6000),
    'Côte-des-Neiges': (45.4942, -73.6308),
    'NDG': (45.4700, -73.6167),
    'Hochelaga': (45.5567, -73.5400),
    'Longueuil': (45.5333, -73.5167),
    'Brossard': (45.4500, -73.4500),
    'Laval (Chomedey)': (45.5500, -73.7333),
    # ... etc (100+ quartiers)
}
```

**Source:** Google Maps API Geocoding + validation manuelle

---

## 📝 Enrichissement Données V5 → V6

### Phase 1: Extraction Codes Postaux

**Problème V5:**
Les `gazelle_clients` ont des champs:
- `default_contact_default_city` → "Montréal" (trop vague!)
- `default_contact_default_postal_code` → Souvent vide

**Solution:**
```sql
-- Compter codes postaux manquants
SELECT
    COUNT(*) as total_clients,
    COUNT(default_contact_default_postal_code) as with_postal,
    ROUND(COUNT(default_contact_default_postal_code) * 100.0 / COUNT(*), 2) as pct_with_postal
FROM gazelle_clients;

-- Résultat V5 actuel:
-- total_clients | with_postal | pct_with_postal
-- 1200          | 450         | 37.5%
```

**Action V6:**
1. Importer codes postaux depuis Gazelle API (champ `postal_code`)
2. Remplir `gazelle_locations.postal_code`
3. Valider format (regex: `^[A-Z]\d[A-Z] \d[A-Z]\d$`)

### Phase 2: Validation Mapping

```python
# scripts/validate_postal_codes.py
def validate_postal_code_coverage():
    """Vérifie combien de clients ont un mapping quartier."""

    clients = supabase.table('gazelle_clients').select('postal_code, city').execute()

    total = len(clients.data)
    mapped = 0
    unmapped_codes = set()

    for client in clients.data:
        postal = client.get('postal_code')
        if not postal:
            continue

        neighborhood = get_neighborhood_from_postal_code(postal, client.get('city'))

        # Vérifier si c'est un mapping ou un fallback
        cleaned = ''.join(c.upper() for c in postal if c.isalnum())[:3]
        if cleaned in MTL_POSTAL_TO_NEIGHBORHOOD:
            mapped += 1
        else:
            unmapped_codes.add(cleaned)

    print(f"Total clients: {total}")
    print(f"Mapped: {mapped} ({mapped/total*100:.1f}%)")
    print(f"Codes non mappés: {unmapped_codes}")
```

### Phase 3: Ajout Nouveaux Codes

**Workflow:**
```bash
# 1. Exécuter validation
python3 scripts/validate_postal_codes.py

# Output:
# Codes non mappés: {'J9Z', 'J3P', 'H0H'}

# 2. Rechercher quartiers manuellement
# J9Z → Sainte-Thérèse (Rive-Nord)
# J3P → Chambly (Rive-Sud)

# 3. Ajouter au dictionnaire
MTL_POSTAL_TO_NEIGHBORHOOD['J9Z'] = 'Sainte-Thérèse'
MTL_POSTAL_TO_NEIGHBORHOOD['J3P'] = 'Chambly'

# 4. Re-run validation → Coverage devrait augmenter
```

---

## 🔗 Intégration avec Autres Modules

### Chat Intelligent

**Fichier:** `api/chat/service.py`

```python
# Import
from core.utils.geography import get_neighborhood_from_postal_code

def _map_to_overview(apt_raw):
    """Map RV brut vers AppointmentOverview."""

    # Récupérer code postal
    client = apt_raw.get('client')
    postal_code = client.get('postal_code') if client else ""
    municipality = client.get('city') if client else ""

    # Mapper quartier
    neighborhood = get_neighborhood_from_postal_code(postal_code, municipality)

    return AppointmentOverview(
        client_name=client_name,
        neighborhood=neighborhood,  # ← "Rosemont (H2G)" au lieu de "Montréal"
        address_short=address_short,
        # ...
    )
```

### Rapports Timeline

**Use Case:** "Rapport par technicien et quartier"

```python
def generate_technician_neighborhood_report(technician: str, date_range):
    """
    Rapport: Combien de RV par quartier pour ce technicien.

    Output:
        Rosemont: 12 RV
        Plateau: 8 RV
        Westmount: 5 RV
    """
    appointments = fetch_appointments(technician, date_range)

    # Grouper par quartier
    by_neighborhood = group_appointments_by_neighborhood(appointments)

    # Stats
    for neighborhood, apts in sorted(by_neighborhood.items()):
        print(f"{neighborhood}: {len(apts)} RV")
```

---

## 🔗 Documents Liés

- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - Schéma `gazelle_locations.postal_code`
- [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md) - Affichage quartiers dans Chat
- [SYNC_STRATEGY.md](SYNC_STRATEGY.md) - Import codes postaux depuis Gazelle

---

## ✅ Checklist V6

### Données
- [ ] Importer codes postaux depuis Gazelle API
- [ ] Remplir `gazelle_locations.postal_code`
- [ ] Valider format codes postaux (regex)
- [ ] Atteindre 90%+ coverage mapping

### Code
- [ ] Déplacer `geo_mapping.py` vers `core/utils/geography.py`
- [ ] Ajouter tests unitaires (100+ codes)
- [ ] Ajouter `NEIGHBORHOOD_CENTERS` avec coordonnées
- [ ] Implémenter `estimate_travel_time()`

### UI
- [ ] Afficher quartiers dans Chat Intelligent
- [ ] Grouper RV par quartier dans vue journée
- [ ] Ajouter filtre par quartier dans dashboard

---

## 📝 Règles Critiques

### ✅ DO (À FAIRE)

1. **Toujours utiliser les 3 premiers caractères**
   ```python
   cleaned = postal_code[:3].upper()  # ✅ "H2G"
   ```

2. **Toujours fournir fallback_city**
   ```python
   neighborhood = get_neighborhood_from_postal_code(postal, city)  # ✅
   ```

3. **Valider format avant stockage**
   ```python
   if re.match(r'^[A-Z]\d[A-Z] \d[A-Z]\d$', postal_code):
       # Stocker
   ```

### ❌ DON'T (À ÉVITER)

1. **Ne jamais hardcoder "Montréal"**
   ```python
   # ❌ MAUVAIS
   neighborhood = "Montréal"

   # ✅ BON
   neighborhood = get_neighborhood_from_postal_code(postal_code, "Montréal")
   ```

2. **Ne jamais ignorer codes inconnus**
   ```python
   # ❌ MAUVAIS
   if code not in mapping:
       return ""  # Perd l'info!

   # ✅ BON
   if code not in mapping:
       return fallback_city  # Garde au moins la ville
   ```

3. **Ne jamais oublier nettoyage**
   ```python
   # ❌ MAUVAIS
   neighborhood = mapping[postal_code]  # Crash si "h2g 2j8"

   # ✅ BON
   cleaned = ''.join(c.upper() for c in postal_code if c.isalnum())[:3]
   neighborhood = mapping.get(cleaned, fallback)
   ```

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après enrichissement codes postaux V6

**RAPPEL:** Toujours fournir `fallback_city` pour codes inconnus!
