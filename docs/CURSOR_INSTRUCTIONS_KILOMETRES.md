# 📋 Instructions pour Cursor - Calculateur de Kilomètres Parcourus

**Objectif:** Créer un système de calcul des kilomètres parcourus par technicien sur une période donnée, intégré dans l'assistant admin.

## 🎯 Spécifications Exactes

### Fonctionnalité Demandée

**Interface Admin:**
1. Sélection du technicien (dropdown: Allan, Nicolas, Jean-Philippe, ou "Tous")
2. Sélection de la période (dropdown prédéfini + dates personnalisées):
   - Ce trimestre (Q1, Q2, Q3, Q4 selon date actuelle)
   - Trimestre dernier
   - Cette année
   - Année dernière
   - Personnalisé (date début → date fin)
3. Bouton "Calculer"
4. Affichage résultats

**Résultats à Afficher:**
- Nombre total de rendez-vous
- Distance totale parcourue (km)
- Distance moyenne par rendez-vous
- Temps total de déplacement
- Temps moyen par déplacement
- Coût total des déplacements (basé sur tarification existante)
- Breakdown par mois (tableau ou graphique)

## 🏗️ Architecture à Suivre

### Fichier à Créer

**`modules/admin/services/kilometre_calculator.py`**

```python
"""
Calculateur de kilomètres parcourus pour rapports admin.

Utilise le TravelFeeCalculator existant pour obtenir distances réelles.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from core.supabase_storage import SupabaseStorage
from modules.assistant.services.queries import GazelleQueries
from modules.travel_fees.calculator import TravelFeeCalculator


@dataclass
class MonthlyStats:
    """Statistiques mensuelles."""
    year: int
    month: int
    appointments_count: int
    total_distance_km: float
    total_duration_minutes: float
    total_cost: float
    avg_distance_km: float
    avg_duration_minutes: float


@dataclass
class PeriodReport:
    """Rapport de kilomètres pour une période."""
    technician_name: str
    period_start: date
    period_end: date
    total_appointments: int
    total_distance_km: float
    total_duration_minutes: float
    total_cost: float
    avg_distance_km: float
    avg_duration_minutes: float
    monthly_breakdown: List[MonthlyStats]


class KilometreCalculator:
    """Calculateur de kilomètres parcourus."""

    def __init__(self):
        self.storage = SupabaseStorage()
        self.queries = GazelleQueries(self.storage)
        self.travel_calculator = TravelFeeCalculator()
        self.timezone = ZoneInfo('America/Toronto')

    def calculate_for_period(
        self,
        technician_name: Optional[str],
        start_date: date,
        end_date: date
    ) -> PeriodReport:
        """
        Calcule les kilomètres pour une période donnée.

        Args:
            technician_name: Nom du technicien (None = tous)
            start_date: Date de début (inclusive)
            end_date: Date de fin (inclusive)

        Returns:
            PeriodReport avec toutes les statistiques
        """
        # TODO: Implémenter
        pass

    def calculate_current_quarter(
        self,
        technician_name: Optional[str] = None
    ) -> PeriodReport:
        """Calcule pour le trimestre en cours."""
        start, end = self._get_current_quarter_dates()
        return self.calculate_for_period(technician_name, start, end)

    def calculate_last_quarter(
        self,
        technician_name: Optional[str] = None
    ) -> PeriodReport:
        """Calcule pour le trimestre dernier."""
        start, end = self._get_last_quarter_dates()
        return self.calculate_for_period(technician_name, start, end)

    def _get_current_quarter_dates(self) -> Tuple[date, date]:
        """Retourne (start_date, end_date) du trimestre actuel."""
        # TODO: Implémenter
        pass

    def _get_last_quarter_dates(self) -> Tuple[date, date]:
        """Retourne (start_date, end_date) du trimestre dernier."""
        # TODO: Implémenter
        pass

    def _calculate_distance_for_appointment(
        self,
        appt: Dict
    ) -> Tuple[float, float, float]:
        """
        Calcule distance, temps et coût pour un RV.

        Returns:
            (distance_km, duration_minutes, cost)
        """
        # TODO: Implémenter en utilisant TravelFeeCalculator
        pass
```

## 📝 Tâches pour Cursor

### Tâche 1: Créer le Module de Calcul

**Instructions:**

```
Crée le fichier modules/admin/services/kilometre_calculator.py en suivant
la structure fournie ci-dessus.

Implémente les méthodes suivantes:

1. calculate_for_period():
   - Récupérer tous les RV entre start_date et end_date
   - Filtrer par technicien si spécifié
   - Pour chaque RV, appeler _calculate_distance_for_appointment()
   - Agréger les résultats par mois
   - Calculer moyennes
   - Retourner PeriodReport

2. _calculate_distance_for_appointment():
   - Récupérer adresse/code postal du RV
   - Récupérer technicien assigné
   - Appeler TravelFeeCalculator pour obtenir distance/temps
   - Retourner (distance_km, duration_minutes, cost)

3. _get_current_quarter_dates():
   - Déterminer trimestre actuel (Q1: Jan-Mar, Q2: Apr-Jun, etc.)
   - Retourner dates de début et fin

4. _get_last_quarter_dates():
   - Calculer trimestre précédent
   - Retourner dates de début et fin

Utilise:
- self.queries.get_appointments() pour récupérer les RV
- self.travel_calculator.calculate_fee_for_technician() pour distances
- ZoneInfo('America/Toronto') pour timezone
- Gestion d'erreurs appropriée

Test avec:
- Trimestre actuel, Allan
- Trimestre dernier, tous les techniciens
```

### Tâche 2: Créer l'Endpoint API Admin

**Instructions:**

```
Dans modules/admin/api.py (ou crée-le si n'existe pas), ajoute:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import Optional

from modules.admin.services.kilometre_calculator import KilometreCalculator

router = APIRouter(prefix="/admin/kilometres", tags=["admin"])

class KilometreRequest(BaseModel):
    technician_name: Optional[str] = None  # None = tous
    start_date: date
    end_date: date

@router.post("/calculate")
async def calculate_kilometres(request: KilometreRequest):
    """Calcule les kilomètres parcourus pour une période."""
    try:
        calculator = KilometreCalculator()
        report = calculator.calculate_for_period(
            request.technician_name,
            request.start_date,
            request.end_date
        )

        return {
            "technician": report.technician_name or "Tous",
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat()
            },
            "summary": {
                "total_appointments": report.total_appointments,
                "total_distance_km": round(report.total_distance_km, 1),
                "total_duration_hours": round(report.total_duration_minutes / 60, 1),
                "total_cost": round(report.total_cost, 2),
                "avg_distance_km": round(report.avg_distance_km, 1),
                "avg_duration_minutes": round(report.avg_duration_minutes, 1)
            },
            "monthly_breakdown": [
                {
                    "month": f"{stat.year}-{stat.month:02d}",
                    "appointments": stat.appointments_count,
                    "distance_km": round(stat.total_distance_km, 1),
                    "duration_hours": round(stat.total_duration_minutes / 60, 1),
                    "cost": round(stat.total_cost, 2)
                }
                for stat in report.monthly_breakdown
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current-quarter/{technician_name}")
@router.get("/current-quarter")
async def current_quarter(technician_name: Optional[str] = None):
    """Raccourci pour trimestre actuel."""
    calculator = KilometreCalculator()
    report = calculator.calculate_current_quarter(technician_name)
    # Retourner même format que /calculate
    # ...
```

Assure-toi de:
- Gérer les erreurs (RV sans adresse, API Google Maps en erreur)
- Retourner JSON structuré
- Documenter les endpoints
```

### Tâche 3: Créer l'Interface Admin (Frontend)

**Instructions:**

```
Crée un composant React pour l'interface admin de calcul de kilomètres.

Fichier: frontend/src/components/admin/KilometreCalculator.tsx (ou .jsx)

Spécifications:

1. Formulaire:
   - Dropdown technicien: ["Tous", "Allan", "Nicolas", "Jean-Philippe"]
   - Dropdown période prédéfinie:
     * "Trimestre actuel"
     * "Trimestre dernier"
     * "Cette année"
     * "Année dernière"
     * "Personnalisé"
   - Si "Personnalisé" sélectionné, afficher:
     * Date picker début
     * Date picker fin
   - Bouton "Calculer"

2. Affichage Résultats:
   - Carte résumé avec:
     * Nombre total de RV
     * Distance totale (km)
     * Temps total (heures)
     * Coût total ($)
     * Moyennes (distance/RV, temps/RV)

   - Tableau breakdown mensuel:
     * Colonnes: Mois | RV | Distance (km) | Temps (h) | Coût ($)
     * Triable par colonne

   - (Optionnel) Graphique:
     * Chart.js ou Recharts
     * Barres: distance par mois
     * Ligne: nombre de RV par mois

3. États:
   - Loading pendant calcul
   - Erreur si API échoue
   - Résultats affichés

4. Design:
   - Utilise Tailwind CSS (déjà dans le projet)
   - Cards pour résumé
   - Table responsive pour breakdown
   - Bouton primaire pour "Calculer"

Exemple de structure:

```tsx
function KilometreCalculator() {
  const [technician, setTechnician] = useState('Tous');
  const [period, setPeriod] = useState('current-quarter');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCalculate = async () => {
    setLoading(true);
    try {
      const response = await fetch('/admin/kilometres/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technician_name: technician === 'Tous' ? null : technician,
          start_date: startDate,
          end_date: endDate
        })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      {/* Formulaire */}
      {/* Résultats */}
    </div>
  );
}
```

Assure-toi de:
- Valider que end_date > start_date
- Gérer cas où aucun RV trouvé
- Formatter nombres (séparateurs milliers, 2 décimales pour $)
```

### Tâche 4: Tests

**Instructions:**

```
Crée scripts/test_kilometres.py pour tester le calculateur.

Tests à inclure:

1. Test calcul trimestre actuel (Allan)
2. Test calcul trimestre dernier (tous)
3. Test période personnalisée (1 mois)
4. Test avec technicien qui n'a aucun RV
5. Test avec RV sans adresse (doit skip gracefully)

Utilise pytest ou unittest.

Exemple:

```python
def test_current_quarter_allan():
    calc = KilometreCalculator()
    report = calc.calculate_current_quarter("Allan")

    assert report.technician_name == "Allan"
    assert report.total_appointments >= 0
    assert report.total_distance_km >= 0
    # etc.
```

Exécution: python scripts/test_kilometres.py
```

## 📊 Données à Utiliser

### Sources de Données

1. **Rendez-vous:** Table `gazelle_appointments`
   - Filtrer par `assigned_to_name` (technicien)
   - Filtrer par `start_time` (période)
   - Récupérer `client_external_id` pour lookup adresse

2. **Adresses Clients:** Table `gazelle_clients` ou `gazelle_contacts`
   - Récupérer `postal_code` ou `address` + `city`

3. **Distances:** Module `TravelFeeCalculator`
   - Appeler avec code postal destination
   - Récupérer distance, temps, coût pour technicien assigné

### Gestion des Cas Limites

- **RV sans adresse:** Skip et logger warning
- **API Google Maps timeout:** Retry 1 fois, sinon skip
- **Technicien pas dans liste:** Lever erreur claire
- **Période invalide (end < start):** Lever ValueError
- **Aucun RV trouvé:** Retourner rapport avec 0 partout

## 🎨 Exemple de Résultat Attendu

**Requête:**
```json
{
  "technician_name": "Nicolas",
  "start_date": "2025-10-01",
  "end_date": "2025-12-31"
}
```

**Réponse:**
```json
{
  "technician": "Nicolas",
  "period": {
    "start": "2025-10-01",
    "end": "2025-12-31"
  },
  "summary": {
    "total_appointments": 45,
    "total_distance_km": 1285.4,
    "total_duration_hours": 32.5,
    "total_cost": 425.80,
    "avg_distance_km": 28.6,
    "avg_duration_minutes": 43.3
  },
  "monthly_breakdown": [
    {
      "month": "2025-10",
      "appointments": 18,
      "distance_km": 512.3,
      "duration_hours": 13.2,
      "cost": 168.50
    },
    {
      "month": "2025-11",
      "appointments": 15,
      "distance_km": 425.8,
      "duration_hours": 10.8,
      "cost": 142.30
    },
    {
      "month": "2025-12",
      "appointments": 12,
      "distance_km": 347.3,
      "duration_hours": 8.5,
      "cost": 115.00
    }
  ]
}
```

## ✅ Critères de Succès

### Backend

- [ ] Module `kilometre_calculator.py` créé avec toutes les méthodes
- [ ] API endpoint `/admin/kilometres/calculate` fonctionnel
- [ ] Tests passent tous
- [ ] Gestion d'erreurs robuste
- [ ] Documentation docstrings complète

### Frontend

- [ ] Interface admin créée et responsive
- [ ] Sélection technicien et période fonctionnelle
- [ ] Affichage résultats clair et formaté
- [ ] Loading states et error handling
- [ ] Design cohérent avec reste de l'app

### Intégration

- [ ] Calculs corrects (vérifier manuellement avec quelques RV)
- [ ] Performance acceptable (<5 sec pour 100 RV)
- [ ] Fonctionne avec tous les techniciens
- [ ] Fonctionne pour différentes périodes

## 🚀 Ordre d'Exécution Recommandé

1. **Tâche 1 (Backend - Calculateur)** → Commence par ça, c'est la fondation
2. **Tâche 4 (Tests)** → Valide que le calculateur fonctionne
3. **Tâche 2 (API Endpoint)** → Expose les fonctionnalités
4. **Tâche 3 (Frontend)** → Interface visuelle en dernier

## 📚 Références

- **TravelFeeCalculator:** [modules/travel_fees/calculator.py](../modules/travel_fees/calculator.py)
- **GazelleQueries:** [modules/assistant/services/queries.py](../modules/assistant/services/queries.py)
- **Timezone:** Toujours utiliser `ZoneInfo('America/Toronto')`
- **Format dates:** ISO 8601 (YYYY-MM-DD)

## 💡 Conseils pour Cursor

1. **Commence par la structure** (dataclasses, méthodes vides)
2. **Implémente méthode par méthode** en testant chacune
3. **Utilise les modules existants** (TravelFeeCalculator, GazelleQueries)
4. **Ajoute logging** pour debugging
5. **Gère les erreurs gracieusement** (ne pas crash si un RV échoue)

## ❓ Questions à Résoudre

Avant de commencer, clarifie avec l'utilisateur:

1. **Distance aller-retour ou aller simple?**
   → Probablement aller-retour (comme TravelFeeCalculator)

2. **Inclure tous les types de RV ou filtrer?**
   → Probablement tous (accordage, réparation, inspection, etc.)

3. **Arrondir les statistiques à combien de décimales?**
   → Suggestion: 1 pour km, 1 pour heures, 2 pour $

4. **Graphique obligatoire ou optionnel?**
   → Optionnel pour MVP, peut être ajouté après

5. **Export Excel/PDF nécessaire?**
   → Probablement plus tard, pas pour MVP

---

**Créé:** 2025-12-16
**Pour:** Cursor IDE
**Objectif:** Système de calcul kilomètres parcourus par trimestre
