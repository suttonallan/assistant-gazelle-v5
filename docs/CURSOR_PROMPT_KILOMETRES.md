# 🤖 Prompt Direct pour Cursor - Calculateur Kilomètres

**Copie-colle ce prompt à Cursor pour démarrer:**

---

Je veux que tu crées un système de calcul des kilomètres parcourus par technicien pour l'interface admin.

## Fonctionnalité Demandée

**Interface admin permettant de:**
1. Sélectionner un technicien (Allan, Nicolas, Jean-Philippe, ou "Tous")
2. Sélectionner une période (Trimestre actuel, Trimestre dernier, Cette année, Année dernière, ou Personnalisé)
3. Calculer et afficher:
   - Nombre total de rendez-vous
   - Distance totale parcourue (km)
   - Temps total de déplacement
   - Coût total
   - Moyennes (distance/RV, temps/RV)
   - Breakdown mensuel

## Fichiers à Créer

### 1. Backend: `modules/admin/services/kilometre_calculator.py`

Crée une classe `KilometreCalculator` avec:

```python
from modules.travel_fees.calculator import TravelFeeCalculator
from modules.assistant.services.queries import GazelleQueries

class KilometreCalculator:
    def calculate_for_period(self, technician_name, start_date, end_date):
        """
        Pour chaque RV dans la période:
        1. Récupérer via GazelleQueries.get_appointments()
        2. Filtrer par technicien si spécifié
        3. Pour chaque RV:
           - Obtenir code postal client
           - Appeler TravelFeeCalculator.calculate_fee_for_technician()
           - Récupérer distance_km, duration_minutes, total_fee
        4. Agréger par mois
        5. Retourner PeriodReport (dataclass)
        """
        pass

    def calculate_current_quarter(self, technician_name=None):
        """Calcule pour Q1/Q2/Q3/Q4 selon date actuelle."""
        pass
```

**Dataclasses à utiliser:**
- `PeriodReport`: summary + monthly_breakdown
- `MonthlyStats`: stats pour un mois donné

### 2. API: `modules/admin/api.py` (ou ajoute endpoint)

```python
@router.post("/admin/kilometres/calculate")
async def calculate_kilometres(
    technician_name: Optional[str],
    start_date: date,
    end_date: date
):
    calc = KilometreCalculator()
    report = calc.calculate_for_period(...)
    return {
        "summary": {...},
        "monthly_breakdown": [...]
    }
```

### 3. Frontend: Composant React

Crée `frontend/src/components/admin/KilometreCalculator.tsx` avec:

**Formulaire:**
- Dropdown technicien
- Dropdown période (avec option "Personnalisé" → affiche date pickers)
- Bouton "Calculer"

**Affichage:**
- Cards résumé (total RV, km, heures, coût, moyennes)
- Tableau breakdown mensuel

**Utilise:**
- Tailwind CSS pour le style
- States pour loading/error/results
- Fetch vers endpoint API

## Modules Existants à Réutiliser

**IMPORTANT:** Utilise ces modules déjà créés:

1. **`modules/travel_fees/calculator.py`** - Pour calculer distances/temps
   ```python
   calculator = TravelFeeCalculator()
   tech = Technician("Nicolas", "H2X 2L1")
   result = calculator.calculate_fee_for_technician(tech, "H3B 4W8")
   # result.distance_km, result.duration_minutes, result.total_fee
   ```

2. **`modules/assistant/services/queries.py`** - Pour récupérer RV
   ```python
   queries = GazelleQueries(storage)
   appointments = queries.get_appointments(date=date_obj, technicien="Nicolas")
   ```

3. **`core.supabase_storage`** - Pour accès base de données

## Logique des Trimestres

- **Q1:** Janvier-Mars (1-3)
- **Q2:** Avril-Juin (4-6)
- **Q3:** Juillet-Septembre (7-9)
- **Q4:** Octobre-Décembre (10-12)

## Gestion d'Erreurs

- Si RV sans adresse/code postal → skip et logger warning
- Si Google Maps API échoue → retry 1 fois, sinon skip
- Si aucun RV trouvé → retourner rapport avec 0 partout

## Exemple de Retour API

```json
{
  "technician": "Nicolas",
  "period": {"start": "2025-10-01", "end": "2025-12-31"},
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
    // ...
  ]
}
```

## Ordre d'Implémentation

1. **Créer le calculateur backend** (kilometre_calculator.py)
2. **Créer tests** (scripts/test_kilometres.py)
3. **Créer endpoint API**
4. **Créer interface frontend**

## Questions Résolues

- **Distance:** Aller-retour (comme TravelFeeCalculator)
- **Types de RV:** Tous (accordage, réparation, etc.)
- **Arrondis:** 1 décimale pour km, 1 pour heures, 2 pour $
- **Timezone:** America/Toronto (toujours)

## Notes Importantes

- Utilise `ZoneInfo('America/Toronto')` pour dates
- Réutilise `TravelFeeCalculator` - NE PAS réimplémenter calcul distance
- Gère gracieusement les erreurs (ne pas crash si un RV échoue)
- Ajoute logging pour debugging
- Docstrings pour toutes les méthodes

---

**Commence par créer la structure du backend (kilometre_calculator.py) avec les dataclasses et méthodes principales. Demande-moi si quelque chose n'est pas clair.**
