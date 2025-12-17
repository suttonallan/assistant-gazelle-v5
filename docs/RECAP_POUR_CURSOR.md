# 📋 Récapitulatif - Travail à Faire avec Cursor

**Date:** 2025-12-16

## 🎯 Objectif Principal

Implémenter un **calculateur de kilomètres parcourus** par technicien sur une période donnée (trimestre, année, personnalisé) pour l'interface admin.

## 📁 Documents Préparés pour Toi

### 1. Instructions Complètes
**Fichier:** [CURSOR_INSTRUCTIONS_KILOMETRES.md](CURSOR_INSTRUCTIONS_KILOMETRES.md)

**Contenu:**
- Spécifications détaillées
- Structure exacte des fichiers à créer
- Exemples de code
- Architecture complète
- 4 tâches bien définies avec exemples
- Critères de succès
- Références aux modules existants

**Utilisation:** Lire en entier avant de commencer avec Cursor

### 2. Prompt Direct à Copier-Coller
**Fichier:** [CURSOR_PROMPT_KILOMETRES.md](CURSOR_PROMPT_KILOMETRES.md)

**Contenu:**
- Version condensée des instructions
- Prêt à être copié-collé dans Cursor
- Focus sur l'essentiel pour démarrer rapidement

**Utilisation:** Copier-coller directement dans le chat Cursor pour qu'il démarre

### 3. Structure Module Admin
**Fichier:** [modules/admin/README.md](../modules/admin/README.md)

**Contenu:**
- Documentation du module admin
- Roadmap des fonctionnalités
- Standards à respecter
- Exemples d'usage futur

**Utilisation:** Référence pour comprendre où s'intègre le calculateur

## 🚀 Workflow Recommandé avec Cursor

### Étape 1: Préparation (5 min)

1. **Ouvrir Cursor IDE** dans le projet:
   ```bash
   cd /Users/allansutton/Documents/assistant-gazelle-v5
   cursor .
   ```

2. **Lire rapidement** [CURSOR_INSTRUCTIONS_KILOMETRES.md](CURSOR_INSTRUCTIONS_KILOMETRES.md) pour comprendre l'ensemble

3. **Avoir sous les yeux** les modules existants à réutiliser:
   - [modules/travel_fees/calculator.py](../modules/travel_fees/calculator.py)
   - [modules/assistant/services/queries.py](../modules/assistant/services/queries.py)

### Étape 2: Lancer Cursor sur Tâche 1 (Backend)

1. **Ouvrir le chat Cursor** (Cmd+L ou icône)

2. **Copier-coller** le contenu de [CURSOR_PROMPT_KILOMETRES.md](CURSOR_PROMPT_KILOMETRES.md)

3. **Ajouter cette instruction:**
   ```
   Commence par créer modules/admin/services/kilometre_calculator.py
   avec la structure complète (dataclasses + méthodes).

   Utilise EXACTEMENT ces modules existants:
   - TravelFeeCalculator (modules/travel_fees/calculator.py)
   - GazelleQueries (modules/assistant/services/queries.py)

   Demande-moi si tu as des questions avant de commencer.
   ```

4. **Laisser Cursor créer** le fichier

5. **Vérifier** que:
   - Les imports sont corrects
   - Les dataclasses sont bien définies
   - Les méthodes ont des docstrings
   - La logique utilise bien TravelFeeCalculator

### Étape 3: Tester le Backend

1. **Demander à Cursor** de créer `scripts/test_kilometres.py`

2. **Exécuter:**
   ```bash
   python scripts/test_kilometres.py
   ```

3. **Si erreurs:**
   - Copier l'erreur dans Cursor
   - Demander: "Corrige cette erreur"
   - Re-tester

### Étape 4: Créer l'API Endpoint

1. **Dans Cursor, demander:**
   ```
   Maintenant crée l'endpoint API dans modules/admin/api.py
   selon les spécifications du document.

   L'endpoint doit:
   - Accepter POST /admin/kilometres/calculate
   - Prendre technician_name, start_date, end_date
   - Retourner JSON structuré avec summary + monthly_breakdown
   ```

2. **Vérifier** que:
   - Le routing est correct
   - Les modèles Pydantic sont définis
   - La gestion d'erreurs est présente

### Étape 5: Frontend (Optionnel si tu as le temps)

1. **Dans Cursor, demander:**
   ```
   Crée le composant React frontend/src/components/admin/KilometreCalculator.tsx

   Avec:
   - Formulaire: dropdown technicien + période + dates personnalisées
   - Affichage: cards résumé + tableau breakdown mensuel
   - Tailwind CSS pour le style
   - Loading states et error handling
   ```

2. **Tester** l'interface dans le navigateur

## 🎯 Ce que Cursor Doit Créer

### Fichiers Backend

1. **`modules/admin/services/kilometre_calculator.py`** (~200-300 lignes)
   - Classe `KilometreCalculator`
   - Dataclasses `PeriodReport` et `MonthlyStats`
   - Méthodes de calcul par période
   - Logique de trimestres
   - Intégration avec TravelFeeCalculator

2. **`modules/admin/api.py`** (~100-150 lignes)
   - Router FastAPI
   - Endpoint POST `/admin/kilometres/calculate`
   - Modèles Pydantic pour request/response
   - Gestion d'erreurs

3. **`scripts/test_kilometres.py`** (~100-150 lignes)
   - Tests unitaires
   - Tests d'intégration
   - Tests cas limites

### Fichiers Frontend (Optionnel)

4. **`frontend/src/components/admin/KilometreCalculator.tsx`** (~200-300 lignes)
   - Composant React
   - Formulaire avec dropdowns
   - Affichage résultats
   - Tailwind CSS

## ⚠️ Points d'Attention pour Cursor

### Choses à LUI RAPPELER Explicitement

1. **Réutiliser TravelFeeCalculator - NE PAS réimplémenter:**
   ```python
   # BON ✅
   from modules.travel_fees.calculator import TravelFeeCalculator
   calculator = TravelFeeCalculator()
   result = calculator.calculate_fee_for_technician(tech, destination)

   # MAUVAIS ❌
   # Ne pas recoder le calcul Google Maps
   ```

2. **Timezone America/Toronto:**
   ```python
   from zoneinfo import ZoneInfo
   tz = ZoneInfo('America/Toronto')
   ```

3. **Gestion d'erreurs gracieuse:**
   ```python
   # Si un RV échoue, skip et continue (ne pas crash)
   for appt in appointments:
       try:
           distance = calculate_distance(appt)
       except Exception as e:
           logger.warning(f"Skip RV {appt['id']}: {e}")
           continue
   ```

4. **Format dates ISO 8601:**
   ```python
   start_date.isoformat()  # "2025-10-01"
   ```

## 🧪 Tests à Faire Après Implémentation

### Test 1: Backend Seul

```bash
python scripts/test_kilometres.py
```

**Vérifier:**
- Tous les tests passent
- Aucune erreur de calcul
- Gestion des cas limites OK

### Test 2: API Endpoint

```bash
# Lancer le serveur (si tu as FastAPI configuré)
uvicorn main:app --reload

# Ou tester directement le module
python -c "
from modules.admin.services.kilometre_calculator import KilometreCalculator
from datetime import date

calc = KilometreCalculator()
report = calc.calculate_for_period('Nicolas', date(2025, 10, 1), date(2025, 12, 31))
print(report)
"
```

**Vérifier:**
- Calculs corrects (comparer manuellement avec quelques RV)
- Temps de réponse acceptable (<5 sec pour ~50 RV)
- Breakdown mensuel correct

### Test 3: Frontend (Si créé)

1. Ouvrir l'interface admin
2. Sélectionner "Nicolas" + "Trimestre actuel"
3. Cliquer "Calculer"
4. Vérifier affichage résultats

## 💡 Conseils pour Travailler avec Cursor

### Si Cursor est Bloqué

**"Je ne comprends pas où chercher les RV"**
→ Montre-lui:
```python
from modules.assistant.services.queries import GazelleQueries
queries = GazelleQueries(storage)
appointments = queries.get_appointments(date=some_date)
```

**"Comment calculer la distance?"**
→ Montre-lui:
```python
from modules.travel_fees.calculator import TravelFeeCalculator
calc = TravelFeeCalculator()
# Voir calculator.py pour usage exact
```

**"Quelle structure de données utiliser?"**
→ Montre-lui les dataclasses du document CURSOR_INSTRUCTIONS

### Si Cursor Propose du Code Non-Optimal

**Exemple: Il veut recoder Google Maps**
→ Arrête-le:
```
STOP. N'implémente pas le calcul Google Maps.
Utilise TravelFeeCalculator qui existe déjà.
Montre-moi comment tu l'utilises.
```

**Exemple: Il ne gère pas les erreurs**
→ Demande:
```
Ajoute la gestion d'erreurs:
- Try/except autour de chaque calcul de RV
- Logger les erreurs avec logging
- Continuer même si un RV échoue
```

## 📊 Résultat Attendu Final

Après que Cursor ait terminé, tu devrais pouvoir:

### En Python:
```python
from modules.admin.services.kilometre_calculator import KilometreCalculator

calc = KilometreCalculator()
report = calc.calculate_current_quarter("Nicolas")

print(f"Nicolas - Q{report.quarter} {report.year}")
print(f"RV: {report.total_appointments}")
print(f"Distance: {report.total_distance_km:.1f} km")
print(f"Coût: {report.total_cost:.2f}$")
```

### Via API (Si endpoint créé):
```bash
curl -X POST http://localhost:8000/admin/kilometres/calculate \
  -H "Content-Type: application/json" \
  -d '{"technician_name": "Nicolas", "start_date": "2025-10-01", "end_date": "2025-12-31"}'
```

### Via Interface Web (Si frontend créé):
1. Ouvrir `/admin/kilometres`
2. Sélectionner Nicolas + Trimestre actuel
3. Cliquer "Calculer"
4. Voir résultats affichés

## ✅ Checklist Finale

Avant de considérer la tâche terminée:

- [ ] `kilometre_calculator.py` créé avec toutes les méthodes
- [ ] Dataclasses `PeriodReport` et `MonthlyStats` définies
- [ ] Utilise bien `TravelFeeCalculator` (pas de réimplémentation)
- [ ] Utilise bien `GazelleQueries` pour récupérer RV
- [ ] Gestion d'erreurs robuste (try/except, logging)
- [ ] Timezone `America/Toronto` utilisé partout
- [ ] `test_kilometres.py` créé et tous les tests passent
- [ ] Endpoint API créé (optionnel)
- [ ] Frontend créé (optionnel)
- [ ] Documentation ajoutée (docstrings)

## 📞 Si Tu as Besoin d'Aide

1. **Relis** [CURSOR_INSTRUCTIONS_KILOMETRES.md](CURSOR_INSTRUCTIONS_KILOMETRES.md) - section pertinente
2. **Vérifie** que Cursor utilise bien les modules existants
3. **Teste** avec `test_kilometres.py` pour identifier le problème
4. **Demande à Cursor** de corriger en lui montrant l'erreur exacte

## 🎉 Après Implémentation

Une fois que Cursor a terminé et que tout fonctionne:

1. **Teste avec vraies données** (trimestre actuel pour un technicien)
2. **Vérifie calculs manuellement** (prends 2-3 RV et calcule à la main)
3. **Documente** tout problème rencontré
4. **Prochaine étape:** Intégrer dans l'interface admin principale

---

**Bon courage avec Cursor!** Les instructions sont détaillées pour qu'il puisse travailler de manière autonome. N'hésite pas à lui donner le prompt direct (CURSOR_PROMPT_KILOMETRES.md) pour démarrer rapidement.
