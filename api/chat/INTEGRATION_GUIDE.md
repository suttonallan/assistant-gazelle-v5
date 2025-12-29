# Guide d'Intégration - Chat Intelligent

✅ **Status:** Intégré et testé

Ce guide documente l'intégration complète du Chat Intelligent dans l'application Assistant Gazelle V5.

---

## 🎯 Résumé de l'Intégration

Le Chat Intelligent est maintenant **complètement intégré** et **testé** dans l'application V5.

### Fonctionnalités Actives

✅ **Backend API (FastAPI):**
- POST `/api/chat/query` - Requêtes naturelles
- GET `/api/chat/day/{date}` - Vue journée directe
- GET `/api/chat/appointment/{id}` - Détails complets RDV
- GET `/api/chat/health` - Health check

✅ **Frontend React:**
- Composant `ChatIntelligent.jsx` intégré dans `App.jsx`
- Accessible via le menu "💬 Ma Journée"
- Disponible pour les rôles admin et louise

✅ **Tests d'Intégration:**
- Script `test_chat_integration.py`
- 4/4 tests passent ✅
- Tous les endpoints validés

---

## 📁 Fichiers Créés/Modifiés

### Backend

#### Nouveaux Fichiers
```
api/chat/
├── __init__.py                 # Exports publics
├── schemas.py                  # Modèles Pydantic (Niveau 1 & 2)
├── service.py                  # ChatService + V5DataProvider
└── README.md                   # Documentation complète

api/chat_routes.py              # Routes FastAPI
test_chat_integration.py        # Script de test

docs/CHAT_INTELLIGENT_SQL.md    # Documentation SQL
```

#### Fichiers Modifiés
```
api/main.py                     # Import et enregistrement des routes chat
  - Ligne 33: from api.chat_routes import router as chat_router
  - Ligne 99: app.include_router(chat_router)
```

### Frontend

#### Nouveaux Fichiers
```
frontend/src/components/ChatIntelligent.jsx    # Interface React complète
```

#### Fichiers Modifiés
```
frontend/src/App.jsx
  - Ligne 13: import ChatIntelligent
  - Ligne 159-160: Route pour currentView === 'chat'
  - Lignes 329-341: Bouton navigation "💬 Ma Journée"
```

---

## 🚀 Comment Utiliser

### 1. Démarrer le Backend

```bash
cd api
source ../.env
python3 -m uvicorn main:app --reload --port 8000
```

Le serveur devrait afficher:
```
✅ API PRÊTE
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 2. Tester les Endpoints

```bash
# Health check
curl http://localhost:8000/api/chat/health

# Requête naturelle
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "demain"}'

# Vue journée directe
curl http://localhost:8000/api/chat/day/2025-12-30
```

Ou lancer le script de test complet:

```bash
python3 test_chat_integration.py
```

**Résultat attendu:**
```
🎉 Tous les tests sont passés!
Total: 4/4 tests réussis
```

### 3. Utiliser le Frontend

1. **Démarrer le frontend React:**
   ```bash
   cd frontend
   npm start
   ```

2. **Se connecter** en tant qu'admin ou Louise

3. **Cliquer sur "💬 Ma Journée"** dans le menu de navigation

4. **Interface disponible:**
   - Chips rapides: "Aujourd'hui", "Demain", "Après-demain"
   - Barre de recherche naturelle
   - Cards compactes (Niveau 1)
   - Drawer détails (Niveau 2) - cliquer sur une card

---

## 🔧 Configuration

### Variables d'Environnement

Assurez-vous que `.env` contient:

```env
# Supabase (requis pour V5DataProvider)
SUPABASE_URL=https://beblgzvmjqkcillmcavk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...

# Frontend (optionnel si différent de localhost:8000)
REACT_APP_API_URL=http://localhost:8000
```

### Permissions d'Accès

Le Chat Intelligent est accessible aux rôles suivants:
- **admin** ✅
- **louise** ✅
- **nick** ❌
- **jean-philippe** ❌

Pour modifier, éditer [frontend/src/App.jsx:330](../../../frontend/src/App.jsx#L330):

```jsx
{(effectiveRole === 'admin' || effectiveRole === 'louise') && (
  <button onClick={() => setCurrentView('chat')}>
    💬 Ma Journée
  </button>
)}
```

---

## 🧪 Tests et Validation

### Tests Automatiques

Le script `test_chat_integration.py` valide:

1. ✅ **Health Check** - Service disponible
2. ✅ **Requête Naturelle** - Parsing et interprétation
3. ✅ **Vue Journée** - Récupération des RDV
4. ✅ **Détails RDV** - Niveau 2 complet

**Lancer les tests:**
```bash
python3 test_chat_integration.py
```

### Tests Manuels (Frontend)

1. Ouvrir http://localhost:3000
2. Se connecter en admin
3. Naviguer vers "💬 Ma Journée"
4. Tester les scénarios:

   **Scénario 1: Chips rapides**
   - Cliquer "Demain"
   - Vérifier affichage des cards
   - Vérifier stats (X RDV, Y pianos, Zh)

   **Scénario 2: Recherche naturelle**
   - Taper "ma journée de demain"
   - Appuyer Enter
   - Vérifier résultats similaires

   **Scénario 3: Drawer détails**
   - Cliquer sur une card
   - Vérifier ouverture du drawer
   - Vérifier infos confort (🦴 🔑 🅿️)
   - Vérifier timeline

---

## 📊 Données Requises

### Tables Supabase V5

Le Chat Intelligent utilise les tables suivantes:

| Table | Colonnes Utilisées | Optionnel |
|-------|-------------------|-----------|
| `gazelle_appointments` | external_id, appointment_date, appointment_time, notes, client_id, piano_id | Non |
| `gazelle_clients` | external_id, company_name, default_location_municipality, default_location_street | Non |
| `gazelle_pianos` | external_id, make, model, type | Oui |
| `gazelle_timeline_entries` | piano_id, occurred_at, entry_type, title, details, user_id | Oui |
| `users` | id, first_name, last_name | Oui |

**Note:** Si certaines données sont manquantes, le Chat affichera des valeurs par défaut (ex: "Client inconnu").

### Améliorer la Qualité des Données

Pour améliorer l'expérience:

1. **Quartiers manquants:** Enrichir `default_location_municipality` dans `gazelle_clients`
2. **Infos confort:** Ajouter colonnes `access_code`, `dog_name`, `parking_info`
3. **Action items:** Parser les champs `notes` pour extraire "À apporter:"

Voir [CHAT_INTELLIGENT_SQL.md](../../../docs/CHAT_INTELLIGENT_SQL.md) pour les requêtes d'enrichissement.

---

## 🛠️ Dépannage

### Problème: "Module 'api.chat' not found"

**Cause:** Les routes chat ne sont pas importées dans main.py

**Solution:**
```python
# api/main.py
from api.chat_routes import router as chat_router
app.include_router(chat_router)
```

### Problème: "TypeError: unsupported operand type(s) for |"

**Cause:** Syntaxe Python 3.10+ utilisée avec Python 3.9

**Solution:** Utiliser `Optional` au lieu de `str | None`:
```python
from typing import Optional

# Avant (Python 3.10+)
technician_id: str | None = None

# Après (Python 3.9 compatible)
technician_id: Optional[str] = None
```

### Problème: "Aucun rendez-vous"

**Causes possibles:**
1. Aucun RDV dans Supabase pour la date demandée
2. Filtre technicien trop restrictif
3. Problème de sync Gazelle → Supabase

**Debug:**
```sql
-- Vérifier données dans Supabase
SELECT COUNT(*)
FROM gazelle_appointments
WHERE appointment_date = '2025-12-30';
```

### Problème: "Chat Intelligent ne s'affiche pas dans le menu"

**Cause:** Rôle utilisateur non autorisé

**Solution:** Se connecter en tant qu'admin ou louise, ou modifier les permissions dans App.jsx

---

## 🔄 Migration V6 (Futur)

Le Chat Intelligent est **prêt pour la migration V6** grâce au Bridge Pattern.

### Quand V6 sera prêt:

1. Créer `V6DataProvider` dans `api/chat/service.py`
2. Modifier une seule ligne dans `api/chat_routes.py`:

```python
# Avant
chat_service = ChatService(data_source="v5")

# Après
chat_service = ChatService(data_source="v6")
```

**Zéro changement** requis dans:
- Frontend (ChatIntelligent.jsx)
- Routes API (chat_routes.py)
- Schémas (schemas.py)

Les schémas Pydantic restent identiques entre V5 et V6.

---

## 📈 Prochaines Étapes

### Améliorations Possibles

1. **NLP Avancé:**
   - Utiliser `dateparser` pour dates complexes ("le 15 janvier", "dans 3 jours")
   - Intégrer spaCy pour NER

2. **UI/UX:**
   - Mode offline (PWA)
   - Notifications push
   - Dark mode

3. **Performance:**
   - Caching Redis pour journée du jour
   - WebSocket pour updates real-time
   - Predictive loading (preload demain à minuit)

4. **Données:**
   - Photos piano
   - Préférences accordage (Hz)
   - Historique météo/humidité

Voir [api/chat/README.md](README.md) pour la roadmap complète.

---

## 📞 Support

**Documentation:**
- [README.md](README.md) - Architecture et usage
- [CHAT_INTELLIGENT_SQL.md](../../../docs/CHAT_INTELLIGENT_SQL.md) - Requêtes SQL

**Tests:**
- [test_chat_integration.py](../../../test_chat_integration.py) - Script de validation

**Fichiers Clés:**
- Backend: [service.py](service.py), [schemas.py](schemas.py), [chat_routes.py](../chat_routes.py)
- Frontend: [ChatIntelligent.jsx](../../../frontend/src/components/ChatIntelligent.jsx)

---

**Dernière mise à jour:** 2025-12-29
**Status:** ✅ Production-ready (V5)
