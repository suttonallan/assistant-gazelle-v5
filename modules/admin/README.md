# 📊 Module Admin - Piano-Tek V5

Module pour les fonctionnalités d'administration et de reporting.

## 🎯 Fonctionnalités

### En Production

*Aucune pour l'instant - module créé pour accueillir les fonctionnalités admin.*

### En Développement

#### Calculateur de Kilomètres Parcourus

**Statut:** 🚧 À implémenter par Cursor

**Description:** Système de calcul des kilomètres parcourus par technicien sur une période donnée (trimestre, année, personnalisé).

**Fichiers Prévus:**
- `services/kilometre_calculator.py` - Logique de calcul
- `api.py` - Endpoints API REST
- Frontend (React) - Interface utilisateur admin

**Documentation:**
- [Instructions Cursor](../../docs/CURSOR_INSTRUCTIONS_KILOMETRES.md) - Guide complet
- [Prompt Direct Cursor](../../docs/CURSOR_PROMPT_KILOMETRES.md) - Prompt copier-coller

**Dépendances:**
- `modules/travel_fees/calculator.py` - Pour calcul distances
- `modules/assistant/services/queries.py` - Pour récupération RV
- Google Maps Distance Matrix API

## 🏗️ Structure

```
modules/admin/
├── __init__.py
├── README.md (ce fichier)
├── services/
│   ├── __init__.py
│   └── kilometre_calculator.py  # À créer
└── api.py  # À créer
```

## 📋 Roadmap

### Phase 1: Calculateur de Kilomètres (Priorité 1)

- [ ] Créer `kilometre_calculator.py`
- [ ] Créer endpoint API `/admin/kilometres/calculate`
- [ ] Créer interface React admin
- [ ] Tests unitaires
- [ ] Documentation

### Phase 2: Rapports Supplémentaires (Futur)

- [ ] Rapport revenus par technicien
- [ ] Rapport types de services (accordage vs réparation)
- [ ] Rapport clients les plus fréquents
- [ ] Statistiques par zone géographique

### Phase 3: Dashboard Admin (Futur)

- [ ] Vue d'ensemble avec KPIs
- [ ] Graphiques interactifs
- [ ] Export PDF/Excel
- [ ] Planification automatique RV

## 🚀 Démarrage Rapide

### Pour Implémenter le Calculateur de Kilomètres

**Avec Cursor:**

1. Ouvre Cursor IDE
2. Copie le contenu de [docs/CURSOR_PROMPT_KILOMETRES.md](../../docs/CURSOR_PROMPT_KILOMETRES.md)
3. Colle dans le chat Cursor
4. Laisse Cursor créer les fichiers

**Manuellement:**

1. Lire [docs/CURSOR_INSTRUCTIONS_KILOMETRES.md](../../docs/CURSOR_INSTRUCTIONS_KILOMETRES.md)
2. Créer `kilometre_calculator.py` selon spécifications
3. Créer endpoint API
4. Créer interface frontend
5. Tester avec `scripts/test_kilometres.py`

## 📊 Exemple d'Usage (Une fois Implémenté)

### API

```bash
# Calculer kilomètres pour Nicolas, Q4 2025
curl -X POST http://localhost:8000/admin/kilometres/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "technician_name": "Nicolas",
    "start_date": "2025-10-01",
    "end_date": "2025-12-31"
  }'
```

### Python

```python
from modules.admin.services.kilometre_calculator import KilometreCalculator

calc = KilometreCalculator()

# Trimestre actuel pour Allan
report = calc.calculate_current_quarter("Allan")

print(f"Total RV: {report.total_appointments}")
print(f"Distance: {report.total_distance_km} km")
print(f"Coût: {report.total_cost}$")

# Breakdown mensuel
for month_stat in report.monthly_breakdown:
    print(f"{month_stat.year}-{month_stat.month:02d}: {month_stat.total_distance_km} km")
```

## 🔗 Intégrations

### Modules Utilisés

- **`travel_fees/calculator.py`** - Calcul distances via Google Maps
- **`assistant/services/queries.py`** - Récupération rendez-vous
- **`core/supabase_storage.py`** - Accès base de données

### Données Requises

- Rendez-vous (table `gazelle_appointments`)
- Clients/Contacts (tables `gazelle_clients`, `gazelle_contacts`)
- Code postal des clients (pour calcul distance)

## 🎓 Pour les Développeurs

### Ajouter une Nouvelle Fonctionnalité Admin

1. **Créer le service:**
   ```python
   # modules/admin/services/my_feature.py
   class MyFeatureService:
       def calculate_something(self):
           # Logic here
           pass
   ```

2. **Créer l'endpoint API:**
   ```python
   # modules/admin/api.py
   @router.get("/admin/my-feature")
   async def my_feature_endpoint():
       service = MyFeatureService()
       return service.calculate_something()
   ```

3. **Créer l'interface:**
   ```tsx
   // frontend/src/components/admin/MyFeature.tsx
   function MyFeature() {
       // Component logic
   }
   ```

4. **Ajouter tests:**
   ```python
   # scripts/test_my_feature.py
   def test_my_feature():
       service = MyFeatureService()
       result = service.calculate_something()
       assert result is not None
   ```

### Standards à Respecter

- **Timezone:** Toujours `ZoneInfo('America/Toronto')`
- **Dates:** Format ISO 8601 (YYYY-MM-DD)
- **Erreurs:** Logging + gestion gracieuse (ne pas crash)
- **Documentation:** Docstrings pour toutes les classes/méthodes
- **Tests:** Au moins tests basiques pour nouvelles fonctionnalités

## 📚 Documentation

- [Instructions Cursor - Kilomètres](../../docs/CURSOR_INSTRUCTIONS_KILOMETRES.md)
- [Prompt Cursor - Kilomètres](../../docs/CURSOR_PROMPT_KILOMETRES.md)
- [Calculateur Frais Déplacement](../travel_fees/README.md)

## 🤝 Contribution

Pour ajouter de nouvelles fonctionnalités admin:

1. Discuter avec l'équipe de la fonctionnalité
2. Créer le service backend
3. Créer l'endpoint API
4. Créer l'interface frontend
5. Ajouter tests
6. Mettre à jour ce README

---

**Créé:** 2025-12-16
**Statut:** 🚧 En construction
**Prochaine Feature:** Calculateur de kilomètres parcourus
