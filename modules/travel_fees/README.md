# 💰 Calculateur de Frais de Déplacement Piano-Tek

Module Python pour calculer automatiquement les frais de déplacement des techniciens en utilisant Google Maps Distance Matrix API.

## 🎯 Objectif

Calculer les frais de déplacement en fonction de:
- Distance réelle (aller-retour) via Google Maps
- Temps de trajet (aller-retour) via Google Maps
- Zone gratuite: 40 km / 40 minutes aller-retour
- Tarification excédent: 0.59$/km + 57.50$/heure

## 📋 Techniciens

| Nom | Code Postal | Adresse Complète |
|-----|-------------|------------------|
| Allan | H4N 2A1 | H4N 2A1, Montréal, QC |
| Nicolas | H2X 2L1 | H2X 2L1, Montréal, QC |
| Jean-Philippe | H2L 3V2 | H2L 3V2, Montréal, QC |

## 💵 Tarification

### Zone Gratuite
- **Distance gratuite:** 40 km aller-retour (20 km chaque sens)
- **Temps gratuit:** 40 minutes aller-retour (20 min chaque sens)

### Tarifs Excédent
- **Distance:** 0.59$ / km
- **Temps:** 57.50$ / heure (0.96$ / minute)

### Calcul

```
Excédent Distance = max(0, distance_totale - 40 km)
Excédent Temps = max(0, temps_total - 40 minutes)

Frais Distance = Excédent Distance × 0.59$
Frais Temps = Excédent Temps × 57.50$ / 60

Total = Frais Distance + Frais Temps
```

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install requests
```

### 2. Obtenir une clé API Google Maps

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un projet ou sélectionner un projet existant
3. Activer l'API "Distance Matrix API"
4. Créer une clé API
5. (Recommandé) Restreindre la clé à "Distance Matrix API" seulement

### 3. Configurer la clé API

Ajouter dans [.env](../../.env):

```bash
GOOGLE_MAPS_API_KEY=your_api_key_here
```

## 📖 Usage

### CLI (Ligne de commande)

```bash
# Calculer pour un code postal
python modules/travel_fees/calculator.py "H3B 4W8"

# Calculer pour une adresse complète
python modules/travel_fees/calculator.py "123 Rue Example, Montréal, QC"
```

**Exemple de sortie:**

```
🎯 Calcul des frais de déplacement pour: H3B 4W8

💰 **Frais de déplacement:**

Nicolas: **GRATUIT** (18.2 km, 22 min)
Allan: **12.50$** (52.4 km, 38 min)
    ↳ +12.4 km × 0.59$ = 7.32$ + +0 min × 0.96$/min = 5.18$
Jean-Philippe: **15.80$** (58.1 km, 42 min)
    ↳ +18.1 km × 0.59$ = 10.68$ + +2 min × 0.96$/min = 5.12$
```

### Python (Fonction Utilitaire)

```python
from modules.travel_fees.calculator import calculate_travel_fee

# Calculer pour une destination
result = calculate_travel_fee("H3B 4W8")
print(result)
```

### Python (Classe Complète)

```python
from modules.travel_fees.calculator import TravelFeeCalculator

# Initialiser (utilise GOOGLE_MAPS_API_KEY de .env)
calculator = TravelFeeCalculator()

# Ou avec clé explicite
calculator = TravelFeeCalculator(api_key="your_key_here")

# Calculer pour tous les techniciens
results = calculator.calculate_all_technicians("H3B 4W8")
for result in results:
    print(f"{result.technician_name}: {result.total_fee:.2f}$")

# Trouver le moins cher
cheapest = calculator.get_cheapest_technician("H3B 4W8")
print(f"Moins cher: {cheapest.technician_name} - {cheapest.total_fee:.2f}$")

# Format pour l'assistant conversationnel
text = calculator.format_for_assistant("H3B 4W8", assigned_technician="Nicolas")
print(text)
```

## 🔌 Intégration dans l'Assistant

### Dans train_summaries.py

Le calculateur est automatiquement intégré dans les sommaires de journée:

```python
# Formats "detailed" et "v4" incluent automatiquement les frais
trainer = SummaryTrainer()  # Initialise le calculateur
summary = trainer.generate_day_summary(
    date=datetime.now(),
    technicien="Nicolas",
    format_style="detailed"
)
```

**Sortie automatique dans le sommaire:**

```
🕐 09:00 - Accordage
   👤 Yannick Nézet-Séguin
   📍 123 Rue Example, Montréal
   📞 514-555-1234

💰 **Frais de déplacement:**

👤 Nicolas: **GRATUIT** (18.2 km, 22 min)
   Allan: **12.50$** (52.4 km, 38 min)
   Jean-Philippe: **15.80$** (58.1 km, 42 min)

💡 **Recommandation:** Nicolas est gratuit pour ce déplacement
```

### Dans l'API Assistant (modules/assistant/api.py)

Pour usage conversationnel:

```python
from modules.travel_fees.calculator import TravelFeeCalculator

# Dans une fonction de l'assistant
def calculate_travel_fees_for_client(client_postal_code: str):
    """Répond à: 'frais de déplacement pour Lucie Poirier'"""
    calculator = TravelFeeCalculator()
    return calculator.format_for_assistant(client_postal_code)
```

## 📊 Structure de Données

### TravelFeeResult

```python
@dataclass
class TravelFeeResult:
    technician_name: str           # "Nicolas"
    distance_km: float             # 18.2 (aller-retour)
    duration_minutes: float        # 22.0 (aller-retour)
    distance_fee: float            # 0.00 (dans zone gratuite)
    time_fee: float                # 0.00 (dans zone gratuite)
    total_fee: float               # 0.00
    is_free: bool                  # True
```

## 🎨 Cas d'Usage

### 1. Sommaire de Journée Automatique

```bash
python scripts/train_summaries.py
# Menu: 1 (Sommaire de journée)
# Format: 2 (Détaillé)
# → Affiche automatiquement les frais pour chaque RV
```

### 2. Requête Conversationnelle

**User:** "frais de déplacement pour Lucie Poirier"

**Assistant:**
```
💰 **Frais de déplacement pour Lucie Poirier (H3Z 2Y7):**

👤 Jean-Philippe: **GRATUIT** (15.8 km, 18 min)
   Nicolas: **5.20$** (42.3 km, 28 min)
   Allan: **8.90$** (55.1 km, 35 min)
```

### 3. Interface Web avec Champ Code Postal

```javascript
// Frontend envoie code postal
POST /api/calculate-travel-fees
{
  "postal_code": "H3Z 2Y7",
  "assigned_technician": "Nicolas"  // optionnel
}

// Backend retourne
{
  "results": [
    {
      "technician": "Jean-Philippe",
      "total_fee": 0.00,
      "is_free": true,
      "distance_km": 15.8,
      "duration_minutes": 18
    },
    ...
  ],
  "cheapest": "Jean-Philippe",
  "formatted_text": "💰 **Frais de déplacement:**\n..."
}
```

## ⚙️ Configuration

### Variables d'Environnement

```bash
# .env
GOOGLE_MAPS_API_KEY=AIza...your_key_here
```

### Personnalisation des Tarifs

Modifier dans [calculator.py](calculator.py:26-29):

```python
class TravelFeeCalculator:
    # Constantes de tarification
    FREE_DISTANCE_KM = 40.0        # Modifier si nécessaire
    FREE_TIME_SECONDS = 2400       # Modifier si nécessaire
    PRICE_PER_KM = 0.59           # Modifier si tarif change
    PRICE_PER_HOUR = 57.50        # Modifier si tarif change
```

### Ajouter/Modifier Techniciens

Modifier dans [calculator.py](calculator.py:73-77):

```python
TECHNICIANS = [
    Technician("Allan", "H4N 2A1"),
    Technician("Nicolas", "H2X 2L1"),
    Technician("Jean-Philippe", "H2L 3V2"),
    Technician("Nouveau Tech", "H1X 1X1"),  # Ajouter ici
]
```

## 🔍 Dépannage

### Erreur: "Google Maps API key required"

**Cause:** Variable d'environnement `GOOGLE_MAPS_API_KEY` non définie

**Solution:**
```bash
# Ajouter dans .env
GOOGLE_MAPS_API_KEY=your_key_here

# Ou passer directement:
calculator = TravelFeeCalculator(api_key="your_key_here")
```

### Erreur: "Google Maps API error: REQUEST_DENIED"

**Cause:** API Distance Matrix pas activée ou clé restreinte incorrectement

**Solution:**
1. Aller dans [Google Cloud Console](https://console.cloud.google.com/)
2. Activer "Distance Matrix API"
3. Vérifier les restrictions de la clé API

### Frais désactivés dans train_summaries.py

**Message:** "⚠️ Google Maps API key non trouvée - frais de déplacement désactivés"

**Solution:** Ajouter `GOOGLE_MAPS_API_KEY` dans `.env` et relancer

## 💡 Exemples Réels

### Exemple 1: Client dans Zone Gratuite

```python
>>> calculate_travel_fee("H2X 3C5")  # Près de Nicolas

💰 **Frais de déplacement:**

Nicolas: **GRATUIT** (12.4 km, 15 min)
Jean-Philippe: **GRATUIT** (18.2 km, 19 min)
Allan: **25.80$** (68.5 km, 45 min)
    ↳ +28.5 km × 0.59$ = 16.82$ + +5 min × 0.96$/min = 9.00$
```

### Exemple 2: Client Loin (Frais pour Tous)

```python
>>> calculate_travel_fee("J4H 3M3")  # Saint-Hubert

💰 **Frais de déplacement:**

Nicolas: **18.50$** (65.2 km, 52 min)
    ↳ +25.2 km × 0.59$ = 14.87$ + +12 min × 0.96$/min = 3.63$
Jean-Philippe: **22.30$** (72.8 km, 58 min)
    ↳ +32.8 km × 0.59$ = 19.35$ + +18 min × 0.96$/min = 2.95$
Allan: **15.20$** (58.4 km, 48 min)
    ↳ +18.4 km × 0.59$ = 10.86$ + +8 min × 0.96$/min = 4.34$

💡 **Recommandation:** Allan économiserait 3.30$
```

### Exemple 3: Technicien Assigné vs Optimal

```python
>>> calculator = TravelFeeCalculator()
>>> print(calculator.format_for_assistant("H3B 4W8", assigned_technician="Allan"))

💰 **Frais de déplacement:**

Nicolas: **GRATUIT** (18.2 km, 22 min)
👤 Allan: **12.50$** (52.4 km, 38 min)
Jean-Philippe: **15.80$** (58.1 km, 42 min)

💡 **Recommandation:** Nicolas serait gratuit pour ce déplacement
```

## 📚 Ressources

- [Google Maps Distance Matrix API](https://developers.google.com/maps/documentation/distance-matrix)
- [JavaScript Version Original](../../docs/ORIGINAL_TRAVEL_FEE_CALCULATOR.js) (référence)
- [train_summaries.py](../../scripts/train_summaries.py) (intégration)

## 🔄 Historique

**Version 1.0** (2025-12-16)
- Implémentation initiale basée sur code JavaScript existant
- Support 3 techniciens (Allan, Nicolas, Jean-Philippe)
- Intégration dans train_summaries.py formats detailed et v4
- CLI et API Python

---

**Créé:** 2025-12-16
**Basé sur:** Code JavaScript original du calculateur Piano-Tek
**Intégré dans:** Système d'entraînement des sommaires V5
