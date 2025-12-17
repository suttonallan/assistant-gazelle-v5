# 🚀 Démarrage Rapide - Calculateur de Frais de Déplacement

Guide en 5 minutes pour commencer à utiliser le calculateur de frais de déplacement.

## ⚡ Étape 1: Obtenir Clé API Google Maps (5 min)

### 1. Créer Projet Google Cloud

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Cliquer "Select a project" → "New Project"
3. Nom: "Piano-Tek" (ou autre)
4. Cliquer "Create"

### 2. Activer Distance Matrix API

1. Menu ☰ → "APIs & Services" → "Library"
2. Chercher: "Distance Matrix API"
3. Cliquer sur le résultat
4. Cliquer "Enable"

### 3. Créer Clé API

1. Menu ☰ → "APIs & Services" → "Credentials"
2. Cliquer "Create Credentials" → "API Key"
3. **Copier la clé** (AIza...longue_string)

### 4. (Recommandé) Sécuriser la Clé

1. Cliquer "Edit API key" (icône crayon)
2. "API restrictions" → "Restrict key"
3. Sélectionner uniquement "Distance Matrix API"
4. Cliquer "Save"

## ⚙️ Étape 2: Configurer le Projet (1 min)

### Ajouter la Clé dans .env

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Éditer .env (ou créer si n'existe pas)
nano .env
```

**Ajouter cette ligne:**
```bash
GOOGLE_MAPS_API_KEY=AIza...votre_clé_copiée_ici
```

Sauvegarder (Ctrl+O, Enter, Ctrl+X).

## 🧪 Étape 3: Tester (2 min)

### Test 1: CLI Simple

```bash
python modules/travel_fees/calculator.py "H2X 2L1"
```

**Résultat attendu:**
```
🎯 Calcul des frais de déplacement pour: H2X 2L1

💰 **Frais de déplacement:**

Nicolas: **GRATUIT** (2.4 km, 8 min)
Jean-Philippe: **GRATUIT** (12.1 km, 15 min)
Allan: **25.50$** (68.2 km, 45 min)
    ↳ +28.2 km × 0.59$ = 16.64$ + +5 min × 0.96$/min = 8.86$
```

### Test 2: Suite Complète

```bash
python scripts/test_travel_fees.py
```

**Résultat attendu:**
```
🧪 TESTS DU CALCULATEUR DE FRAIS DE DÉPLACEMENT
======================================================================

✅ Clé API Google Maps trouvée: AIza...

[Exécute 5 tests]

📊 RÉSUMÉ DES TESTS
======================================================================
✅ RÉUSSI - Test 1: Usage Basique
✅ RÉUSSI - Test 2: Usage Classe
✅ RÉUSSI - Test 3: Technicien le Moins Cher
✅ RÉUSSI - Test 4: Format Assistant
✅ RÉUSSI - Test 5: Cas Limites

Résultat: 5/5 tests réussis

🎉 Tous les tests ont réussi!
```

### Test 3: Dans train_summaries

```bash
python scripts/train_summaries.py
```

**Dans le menu:**
```
Choix: 1 (Sommaire de journée)
Date: 1 (Aujourd'hui)
Technicien: 2 (Nick)
Format: 2 (Détaillé)
```

**Résultat:** Les frais de déplacement devraient s'afficher automatiquement pour chaque RV!

## 🎯 Cas d'Usage Rapides

### Usage 1: Calculer pour un Client Spécifique

```python
from modules.travel_fees.calculator import calculate_travel_fee

# Code postal de Lucie Poirier
print(calculate_travel_fee("H3Z 2Y7"))
```

### Usage 2: Trouver le Technicien le Moins Cher

```python
from modules.travel_fees.calculator import TravelFeeCalculator

calc = TravelFeeCalculator()
cheapest = calc.get_cheapest_technician("H3B 4W8")

print(f"Le moins cher: {cheapest.technician_name}")
print(f"Coût: {cheapest.total_fee:.2f}$")
```

### Usage 3: Comparer Tous les Techniciens

```python
from modules.travel_fees.calculator import TravelFeeCalculator

calc = TravelFeeCalculator()
results = calc.calculate_all_technicians("J4H 3M3")

for r in results:
    status = "GRATUIT" if r.is_free else f"{r.total_fee:.2f}$"
    print(f"{r.technician_name}: {status}")
```

## 📱 Prochaine Étape: Intégration Assistant

Pour répondre à: **"frais de déplacement pour Lucie Poirier"**

### Option A: Fonction Simple (Recommandée pour Débuter)

Ajouter dans `modules/assistant/api.py` ou créer nouvelle route:

```python
from modules.travel_fees.calculator import calculate_travel_fee

def handle_travel_fee_query(client_name: str):
    """Répond à 'frais de déplacement pour [client]'."""

    # 1. Chercher le client dans Supabase
    client = queries.search_clients([client_name])[0]

    # 2. Récupérer code postal
    postal_code = client.get('postal_code') or client.get('city')

    # 3. Calculer frais
    if postal_code:
        return calculate_travel_fee(postal_code)
    else:
        return "❌ Code postal non trouvé pour ce client"
```

### Option B: Endpoint API Complet

```python
from fastapi import APIRouter
from modules.travel_fees.calculator import TravelFeeCalculator

router = APIRouter()

@router.post("/api/travel-fees")
async def calculate_fees(postal_code: str, assigned_tech: str = None):
    calc = TravelFeeCalculator()
    results = calc.calculate_all_technicians(postal_code)
    formatted = calc.format_for_assistant(postal_code, assigned_tech)

    return {
        "results": [
            {
                "technician": r.technician_name,
                "total": r.total_fee,
                "distance_km": r.distance_km,
                "duration_min": r.duration_minutes,
                "is_free": r.is_free
            }
            for r in results
        ],
        "formatted": formatted,
        "cheapest": results[0].technician_name
    }
```

## 🎨 Interface Web - Onglet Code Postal

Pour créer l'onglet où on entre le code postal:

### Frontend (React)

```jsx
import { useState } from 'react';

function TravelFeeCalculator() {
  const [postalCode, setPostalCode] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/travel-fees', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ postal_code: postalCode })
      });
      const data = await res.json();
      setResults(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h2>💰 Calculateur de Frais de Déplacement</h2>

      <div className="flex gap-2 mt-4">
        <input
          type="text"
          value={postalCode}
          onChange={(e) => setPostalCode(e.target.value)}
          placeholder="Code postal (ex: H3Z 2Y7)"
          className="border px-3 py-2 rounded"
        />
        <button
          onClick={calculate}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          {loading ? 'Calcul...' : 'Calculer'}
        </button>
      </div>

      {results && (
        <div className="mt-4">
          <h3>Résultats:</h3>
          {results.results.map((r) => (
            <div key={r.technician} className="border-b py-2">
              <span className="font-bold">{r.technician}:</span>{' '}
              {r.is_free ? (
                <span className="text-green-600">GRATUIT</span>
              ) : (
                <span className="text-orange-600">{r.total.toFixed(2)}$</span>
              )}
              <span className="text-gray-500 ml-2">
                ({r.distance_km.toFixed(1)} km, {r.duration_min.toFixed(0)} min)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TravelFeeCalculator;
```

## 📚 Documentation Complète

- **Guide Complet:** [docs/GUIDE_FRAIS_DEPLACEMENT.md](GUIDE_FRAIS_DEPLACEMENT.md)
- **README Module:** [modules/travel_fees/README.md](../modules/travel_fees/README.md)
- **Intégration:** [docs/INTEGRATION_FRAIS_DEPLACEMENT.md](INTEGRATION_FRAIS_DEPLACEMENT.md)

## ❓ Problèmes Fréquents

### Erreur: "Google Maps API key required"

**Solution:**
```bash
# Vérifier que .env contient la clé
cat .env | grep GOOGLE_MAPS

# Si absent, ajouter:
echo "GOOGLE_MAPS_API_KEY=votre_clé" >> .env
```

### Erreur: "REQUEST_DENIED"

**Solution:**
1. Vérifier que Distance Matrix API est activée
2. Vérifier les restrictions de la clé (doit inclure Distance Matrix API)

### Frais ne s'affichent pas dans train_summaries

**Vérifier:**
```bash
# Message au lancement:
⚠️ Google Maps API key non trouvée - frais de déplacement désactivés
```

**Solution:** Ajouter clé dans `.env` et relancer.

## 🎉 C'est Tout!

Tu es maintenant prêt à utiliser le calculateur de frais de déplacement!

**Prochaines étapes suggérées:**
1. Tester avec tes codes postaux réels
2. Intégrer dans l'assistant conversationnel
3. Créer l'interface web

---

**Questions?** Consulter [docs/GUIDE_FRAIS_DEPLACEMENT.md](GUIDE_FRAIS_DEPLACEMENT.md)
