# 💰 Guide Rapide - Calculateur de Frais de Déplacement

Guide d'utilisation du calculateur de frais de déplacement Piano-Tek intégré dans l'assistant.

## 🎯 Cas d'Usage

### 1. Dans le Sommaire de Journée

Les frais de déplacement s'affichent **automatiquement** dans les formats `detailed` et `v4`:

```bash
python scripts/train_summaries.py
# Menu: 1 (Sommaire de journée)
# Format: 2 (Détaillé)
```

**Résultat:**
```
🕐 09:00 - Accordage
   👤 Lucie Poirier
   📍 123 Rue Example, Montréal
   📞 514-555-1234

💰 **Frais de déplacement:**

👤 Nicolas: **GRATUIT** (18.2 km, 22 min)
   Allan: **12.50$** (52.4 km, 38 min)
   Jean-Philippe: **15.80$** (58.1 km, 42 min)

💡 **Recommandation:** Nicolas est gratuit pour ce déplacement
```

### 2. Requête Conversationnelle

**Utilisateur:** "frais de déplacement pour Lucie Poirier"

**Assistant:**
```python
from modules.travel_fees.calculator import calculate_travel_fee

# L'assistant récupère le code postal de Lucie (ex: H3Z 2Y7)
result = calculate_travel_fee("H3Z 2Y7")
# → Affiche les frais pour tous les techniciens
```

### 3. Interface Web - Onglet Code Postal

Pour permettre à l'utilisateur d'entrer manuellement un code postal:

**Frontend (exemple React):**
```jsx
function TravelFeeCalculator() {
  const [postalCode, setPostalCode] = useState('');
  const [fees, setFees] = useState(null);

  const calculateFees = async () => {
    const response = await fetch('/api/calculate-travel-fees', {
      method: 'POST',
      body: JSON.stringify({ postal_code: postalCode })
    });
    const data = await response.json();
    setFees(data.formatted_text);
  };

  return (
    <div>
      <input
        value={postalCode}
        onChange={(e) => setPostalCode(e.target.value)}
        placeholder="Code postal (ex: H3Z 2Y7)"
      />
      <button onClick={calculateFees}>Calculer</button>
      <pre>{fees}</pre>
    </div>
  );
}
```

**Backend (API endpoint):**
```python
from fastapi import APIRouter
from modules.travel_fees.calculator import TravelFeeCalculator

router = APIRouter()

@router.post("/calculate-travel-fees")
async def calculate_fees(request: dict):
    """Calcule les frais de déplacement pour un code postal."""
    postal_code = request.get('postal_code')
    assigned_tech = request.get('assigned_technician')  # optionnel

    calculator = TravelFeeCalculator()
    results = calculator.calculate_all_technicians(postal_code)
    formatted = calculator.format_for_assistant(postal_code, assigned_tech)

    return {
        "results": [
            {
                "technician": r.technician_name,
                "total_fee": r.total_fee,
                "distance_km": r.distance_km,
                "duration_minutes": r.duration_minutes,
                "is_free": r.is_free
            }
            for r in results
        ],
        "formatted_text": formatted,
        "cheapest": results[0].technician_name if results else None
    }
```

## 🚀 Configuration Initiale

### Étape 1: Obtenir une Clé API Google Maps

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un projet (ou sélectionner existant)
3. Activer **Distance Matrix API**:
   - Menu → APIs & Services → Library
   - Rechercher "Distance Matrix API"
   - Cliquer "Enable"
4. Créer une clé API:
   - Menu → APIs & Services → Credentials
   - Create Credentials → API Key
   - Copier la clé

### Étape 2: Configurer dans .env

```bash
# Ajouter dans .env
GOOGLE_MAPS_API_KEY=AIza...votre_clé_ici
```

### Étape 3: Tester

```bash
# Test CLI
python modules/travel_fees/calculator.py "H3B 4W8"

# Test dans train_summaries
python scripts/train_summaries.py
# → Les frais devraient s'afficher automatiquement
```

## 📊 Comprendre les Frais

### Zone Gratuite

- **Distance:** 40 km aller-retour (20 km chaque sens)
- **Temps:** 40 minutes aller-retour (20 min chaque sens)

Si les deux conditions sont respectées → **GRATUIT**

### Calcul de l'Excédent

```
Distance excédent = max(0, distance_totale - 40 km)
Temps excédent = max(0, temps_total - 40 minutes)

Frais distance = Distance excédent × 0.59$
Frais temps = Temps excédent × (57.50$ / 60 min)

Total = Frais distance + Frais temps
```

### Exemples Concrets

**Exemple 1: Dans la Zone Gratuite**
```
Distance: 35 km aller-retour
Temps: 32 minutes aller-retour

Distance excédent = 0 km
Temps excédent = 0 min
→ GRATUIT
```

**Exemple 2: Distance Excédentaire**
```
Distance: 55 km aller-retour
Temps: 38 minutes aller-retour

Distance excédent = 55 - 40 = 15 km
Temps excédent = 0 min

Frais = 15 km × 0.59$ = 8.85$
→ Total: 8.85$
```

**Exemple 3: Distance et Temps Excédentaires**
```
Distance: 65 km aller-retour
Temps: 55 minutes aller-retour

Distance excédent = 65 - 40 = 25 km
Temps excédent = 55 - 40 = 15 min

Frais distance = 25 km × 0.59$ = 14.75$
Frais temps = 15 min × (57.50$ / 60) = 14.38$
→ Total: 29.13$
```

## 💡 Recommandations Automatiques

Le système affiche automatiquement des recommandations quand:

### Cas 1: Technicien Assigné Pas Optimal

```
👤 Allan: **25.50$** (68 km, 45 min)  ← Assigné
   Nicolas: **GRATUIT** (18 km, 22 min)
   Jean-Philippe: **15.80$** (58 km, 42 min)

💡 **Recommandation:** Nicolas serait gratuit pour ce déplacement
```

### Cas 2: Économies Significatives (>10$)

```
👤 Jean-Philippe: **32.50$** (85 km, 58 min)  ← Assigné
   Nicolas: **18.20$** (62 km, 48 min)
   Allan: **22.10$** (70 km, 52 min)

💡 **Recommandation:** Nicolas économiserait 14.30$
```

## 🔧 Personnalisation

### Modifier les Tarifs

Éditer [modules/travel_fees/calculator.py](../modules/travel_fees/calculator.py):

```python
class TravelFeeCalculator:
    # Modifier ces valeurs selon vos besoins
    FREE_DISTANCE_KM = 40.0      # Zone gratuite distance
    FREE_TIME_SECONDS = 2400     # Zone gratuite temps (40 min)
    PRICE_PER_KM = 0.59          # Prix par km excédent
    PRICE_PER_HOUR = 57.50       # Prix par heure excédent
```

### Ajouter un Technicien

```python
TECHNICIANS = [
    Technician("Allan", "H4N 2A1"),
    Technician("Nicolas", "H2X 2L1"),
    Technician("Jean-Philippe", "H2L 3V2"),
    Technician("Nouveau Tech", "H1X 1X1"),  # Ajouter ici
]
```

Et ajouter l'adresse complète dans `ADDRESSES`:

```python
ADDRESSES = {
    "Allan": "H4N 2A1, Montréal, QC",
    "Nicolas": "H2X 2L1, Montréal, QC",
    "Jean-Philippe": "H2L 3V2, Montréal, QC",
    "Nouveau Tech": "H1X 1X1, Montréal, QC",  # Ajouter ici
}
```

## 🐛 Dépannage

### Erreur: "Google Maps API key required"

**Cause:** Variable `GOOGLE_MAPS_API_KEY` non définie dans `.env`

**Solution:**
```bash
# Vérifier que .env contient:
GOOGLE_MAPS_API_KEY=AIza...

# Relancer le script
```

### Erreur: "REQUEST_DENIED"

**Cause:** API Distance Matrix pas activée

**Solution:**
1. [Google Cloud Console](https://console.cloud.google.com/)
2. APIs & Services → Library
3. Chercher "Distance Matrix API"
4. Cliquer "Enable"

### Frais ne s'affichent pas dans train_summaries

**Message:**
```
⚠️ Google Maps API key non trouvée - frais de déplacement désactivés
   Définir GOOGLE_MAPS_API_KEY dans .env pour activer
```

**Solution:** Ajouter la clé dans `.env` (voir Configuration Initiale)

### Adresse non trouvée

**Erreur:** "Route calculation error: NOT_FOUND"

**Cause:** Code postal invalide ou adresse introuvable

**Solution:**
- Vérifier le format du code postal (ex: "H3B 4W8" avec espace)
- Essayer avec adresse complète: "123 Rue Example, Montréal, QC"
- Vérifier l'orthographe

## 📚 Ressources

- [README Complet](../modules/travel_fees/README.md)
- [Code Source](../modules/travel_fees/calculator.py)
- [Google Maps Distance Matrix API Docs](https://developers.google.com/maps/documentation/distance-matrix)

## 🎓 Formation Recommandée

### Pour Utilisateurs Non-Techniques

1. **Tester avec des codes postaux connus:**
   ```bash
   python modules/travel_fees/calculator.py "H2X 2L1"  # Près de Nicolas
   python modules/travel_fees/calculator.py "H4N 2A1"  # Près d'Allan
   python modules/travel_fees/calculator.py "J4H 3M3"  # Loin (Saint-Hubert)
   ```

2. **Observer les patterns:**
   - Qui est le plus proche pour chaque zone de Montréal?
   - À partir de quelle distance les frais apparaissent?
   - Comment le temps affecte les frais?

3. **Utiliser dans train_summaries:**
   - Tester avec des journées réelles
   - Comparer les 3 formats
   - Donner feedback sur l'utilité des frais affichés

### Pour Développeurs

1. **Comprendre le code:**
   - Lire [calculator.py](../modules/travel_fees/calculator.py)
   - Examiner l'intégration dans [train_summaries.py](../scripts/train_summaries.py)

2. **Tester l'API:**
   ```python
   from modules.travel_fees.calculator import TravelFeeCalculator

   calc = TravelFeeCalculator()
   results = calc.calculate_all_technicians("H3B 4W8")
   for r in results:
       print(f"{r.technician_name}: {r.total_fee:.2f}$")
   ```

3. **Créer des endpoints personnalisés:**
   - Ajouter dans l'API de l'assistant
   - Créer interfaces web
   - Intégrer dans workflows automatiques

---

**Créé:** 2025-12-16
**Version:** 1.0
**Basé sur:** Code JavaScript original Piano-Tek
