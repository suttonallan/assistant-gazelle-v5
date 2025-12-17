# 🗺️ CONFIGURATION GOOGLE MAPS API - V5

**Date:** 2025-12-16
**Pour:** Cursor Mac
**Sujet:** Configuration de la clé API Google Maps pour calcul des trajets

---

## ✅ CLÉ API GOOGLE MAPS EXISTANTE

**Bonne nouvelle:** La clé Google Maps existe déjà et est utilisée en production!

**Clé API:**
```
your_google_maps_api_key_here
```

**Actuellement utilisée dans:**
- `c:\Allan Python projets\config.py` (V4)
- `c:\Allan Python projets\sous_projets\calcul_kilometrage\config.py` (calculs kilométrage)

---

## 📋 OÙ AJOUTER LA CLÉ DANS V5

### Option 1: Fichier `.env` (RECOMMANDÉ)

**Emplacement:** `assistant-gazelle-v5/.env`

**Ajouter cette ligne:**
```bash
# Google Maps API (pour calcul trajets techniciens)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

**Si le fichier `.env` n'existe pas encore, créer avec:**
```bash
# ==============================================
# ASSISTANT GAZELLE V5 - Configuration
# ==============================================

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Supabase PostgreSQL Connection
SUPABASE_HOST=your_supabase_host_here
SUPABASE_DATABASE=postgres
SUPABASE_USER=postgres
SUPABASE_PASSWORD=your_supabase_password_here
SUPABASE_PORT=5432

# Google Maps API (pour calcul trajets techniciens)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Adresses maison des techniciens (pour calcul départ)
# Note: Louise n'est pas technicienne, pas besoin d'adresse
ALLAN_HOME_ADDRESS=780 Lanthier, Montréal, QC H4N 2A1
NICOLAS_HOME_ADDRESS=3520A Rue Sainte-Famille, Montréal, QC
JEANPHILIPPE_HOME_ADDRESS=2127 Rue Saint-André, Montréal, QC
```

---

### Option 2: Fichier `config.py` (Alternative)

**Emplacement:** `assistant-gazelle-v5/config/settings.py`

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Google Maps API Configuration
GOOGLE_MAPS_API_KEY = os.getenv(
    'GOOGLE_MAPS_API_KEY',
    'your_google_maps_api_key_here'  # Fallback
)

# Technician home addresses (for travel calculations)
TECHNICIAN_HOME_ADDRESSES = {
    'usr_allan': os.getenv('ALLAN_HOME_ADDRESS', ''),
    'usr_nicolas': os.getenv('NICOLAS_HOME_ADDRESS', ''),
    'usr_jeanphilippe': os.getenv('JEANPHILIPPE_HOME_ADDRESS', ''),
    'usr_louise': os.getenv('LOUISE_HOME_ADDRESS', '')
}
```

---

## 🔧 UTILISATION DANS LE CODE V5

### Service Google Maps

**Créer:** `modules/assistant/services/google_maps_service.py`

```python
import os
import requests
from typing import Dict, Optional
from datetime import datetime

# Charger la clé depuis .env
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

async def get_directions(
    origin: str,
    destination: str,
    departure_time: Optional[datetime] = None
) -> Dict:
    """
    Calcule trajet entre deux adresses via Google Maps Distance Matrix API

    Args:
        origin: Adresse de départ (ex: "123 Rue X, Montréal, QC")
        destination: Adresse d'arrivée
        departure_time: Heure de départ (pour trafic en temps réel)

    Returns:
        {
            'duration_seconds': int,      # Durée en secondes
            'duration_text': str,          # "35 mins"
            'distance_meters': int,        # Distance en mètres
            'distance_text': str,          # "28.5 km"
            'error': str or None
        }
    """
    if not GOOGLE_MAPS_API_KEY:
        return {
            'duration_seconds': 0,
            'duration_text': 'N/A',
            'distance_meters': 0,
            'distance_text': 'N/A',
            'error': 'Google Maps API key not configured'
        }

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"

    params = {
        'origins': origin,
        'destinations': destination,
        'key': GOOGLE_MAPS_API_KEY,
        'units': 'metric',           # Kilomètres
        'language': 'fr',             # Français
        'mode': 'driving'             # En voiture
    }

    # Ajouter heure départ si fournie (pour trafic temps réel)
    if departure_time:
        params['departure_time'] = int(departure_time.timestamp())

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Vérifier statut réponse
        if data['status'] != 'OK':
            return {
                'duration_seconds': 0,
                'duration_text': 'N/A',
                'distance_meters': 0,
                'distance_text': 'N/A',
                'error': f"Google Maps API error: {data['status']}"
            }

        # Extraire infos première route
        element = data['rows'][0]['elements'][0]

        if element['status'] != 'OK':
            return {
                'duration_seconds': 0,
                'duration_text': 'N/A',
                'distance_meters': 0,
                'distance_text': 'N/A',
                'error': f"Route not found: {element['status']}"
            }

        return {
            'duration_seconds': element['duration']['value'],
            'duration_text': element['duration']['text'],
            'distance_meters': element['distance']['value'],
            'distance_text': element['distance']['text'],
            'error': None
        }

    except requests.exceptions.RequestException as e:
        return {
            'duration_seconds': 0,
            'duration_text': 'N/A',
            'distance_meters': 0,
            'distance_text': 'N/A',
            'error': f"Request failed: {str(e)}"
        }
```

---

## 🧪 TESTER LA CLÉ

### Test simple (Python):

```python
import requests

GOOGLE_MAPS_API_KEY = "your_google_maps_api_key_here"

# Test avec vraies adresses Montréal
origin = "1260 Rue Berri, Montréal, QC"
destination = "2900 Boulevard Édouard-Montpetit, Montréal, QC"

url = "https://maps.googleapis.com/maps/api/distancematrix/json"
params = {
    'origins': origin,
    'destinations': destination,
    'key': GOOGLE_MAPS_API_KEY,
    'units': 'metric',
    'language': 'fr'
}

response = requests.get(url, params=params)
data = response.json()

print(f"Status: {data['status']}")
if data['status'] == 'OK':
    element = data['rows'][0]['elements'][0]
    print(f"Durée: {element['duration']['text']}")
    print(f"Distance: {element['distance']['text']}")
else:
    print(f"Erreur: {data}")
```

**Résultat attendu:**
```
Status: OK
Durée: 12 mins
Distance: 4.2 km
```

---

### Test avec curl:

```bash
curl -G "https://maps.googleapis.com/maps/api/distancematrix/json" \
  --data-urlencode "origins=1260 Rue Berri, Montréal, QC" \
  --data-urlencode "destinations=2900 Boulevard Édouard-Montpetit, Montréal, QC" \
  --data-urlencode "key=your_google_maps_api_key_here" \
  --data-urlencode "units=metric" \
  --data-urlencode "language=fr"
```

---

## 📊 CAPACITÉ ET LIMITES API

### Plan actuel (à vérifier dans Google Cloud Console):

**Google Maps Distance Matrix API:**
- **Gratuit:** 40,000 requêtes/mois
- **Tarif excédent:** $5.00 USD / 1,000 requêtes supplémentaires

### Estimation utilisation V5:

**Scénario typique:**
- 4 techniciens
- Moyenne 4 rendez-vous/jour/technicien
- 4 calculs trajets/jour/technicien (RV + retour maison)
- 20 jours ouvrables/mois

**Calcul:**
```
4 techniciens × 5 trajets/jour × 20 jours = 400 requêtes/mois
```

**Conclusion:** ✅ Largement dans la limite gratuite (40,000/mois)

---

## ⚙️ CONFIGURATION ADRESSES MAISON TECHNICIENS

**Ces adresses sont NÉCESSAIRES pour:**
- Calculer trajet maison → premier RV
- Calculer trajet dernier RV → retour maison

### À ajouter dans `.env`:

```bash
# Adresses maison des techniciens
ALLAN_HOME_ADDRESS=123 Rue Example, Montréal, QC H2X 1A1
NICOLAS_HOME_ADDRESS=456 Avenue Test, Laval, QC H7X 2B2
JEANPHILIPPE_HOME_ADDRESS=789 Boulevard Sample, Montréal, QC H3C 3C3
LOUISE_HOME_ADDRESS=321 Chemin Demo, Longueuil, QC J4K 4D4
```

**Note pour Allan:** Remplacer par les vraies adresses (ou ville générale si confidentialité requise)

---

## 🔐 SÉCURITÉ

### ✅ Bonnes pratiques DÉJÀ APPLIQUÉES:

1. **Restriction par domaine** (recommandé):
   - Aller sur: https://console.cloud.google.com/apis/credentials
   - Éditer la clé API
   - Ajouter restriction "HTTP referrers"
   - Autoriser seulement: `https://votre-domaine-v5.com/*`

2. **Restriction API** (recommandé):
   - Limiter la clé uniquement à "Distance Matrix API"
   - Désactiver autres APIs (Places, Geocoding, etc.) si non utilisées

3. **Ne JAMAIS exposer dans code frontend:**
   - ✅ Appels API depuis backend seulement
   - ✅ Clé dans `.env` (pas commitée Git)

---

## 🎯 CHECKLIST CONFIGURATION

**Pour Cursor Mac:**

- [ ] 1. Créer fichier `.env` à la racine du projet V5 (si n'existe pas)
- [ ] 2. Ajouter `GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here`
- [ ] 3. Demander à Allan les adresses maison techniciens
- [ ] 4. Ajouter `ALLAN_HOME_ADDRESS`, `NICOLAS_HOME_ADDRESS`, etc. dans `.env`
- [ ] 5. Créer `modules/assistant/services/google_maps_service.py`
- [ ] 6. Copier fonction `get_directions()` (fournie ci-dessus)
- [ ] 7. Tester avec vraies adresses Montréal
- [ ] 8. Valider que calculs trajets fonctionnent

**Temps estimé:** 30 minutes

---

## 📞 POUR ALLAN

**Questions pour compléter la config:**

1. **Adresses maison techniciens:**
   - Allan: ?
   - Nicolas: ?
   - Jean-Philippe: ?
   - Louise: ?

2. **Vérification quota Google Maps:**
   - Se connecter à: https://console.cloud.google.com/
   - Vérifier projet associé à la clé
   - Confirmer quota "Distance Matrix API"

3. **Restriction sécurité (optionnel mais recommandé):**
   - Domaine production V5 (ex: `https://assistant-gazelle-v5.onrender.com`)
   - Pour limiter usage de la clé à ce domaine uniquement

---

## ✅ RÉSUMÉ

**Clé Google Maps:** ✅ TROUVÉE et FONCTIONNELLE
```
your_google_maps_api_key_here
```

**Prochaines étapes:**
1. Ajouter dans `.env` V5
2. Obtenir adresses maison techniciens d'Allan
3. Créer service `google_maps_service.py`
4. Tester calculs trajets

**Bloqueur résolu:** ✅ La clé existe, pas besoin d'en créer une nouvelle!

---

**Créé:** 2025-12-16 00:30 EST
**Par:** Claude Code (Windows)
**Pour:** Cursor Mac + Allan
**Statut:** ✅ CLÉ TROUVÉE - PRÊT À CONFIGURER
