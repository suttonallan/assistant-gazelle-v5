# Chat Intelligent - Porte d'Entrée de la Journée

**Interface conversationnelle moderne pour les techniciens piano.**

Interface optimisée mobile qui permet au technicien de préparer sa journée en quelques secondes.

---

## 🎯 Objectif

**"Ma journée de demain"** → Vue complète et actionnable en un clic.

### Niveau 1: Aperçu Rapide (Cards)
- ⏰ Heure du RDV
- 📍 Quartier (PRIORITÉ terrain)
- 🎹 Piano (marque/modèle)
- 📋 Action items (à apporter/faire)
- 🏷️ Badges (nouveau client, alertes, priorité)

### Niveau 2: Deep Dive (Drawer)
- 🦴 Infos confort (chien, code porte, parking)
- 📖 Historique timeline (résumé + entrées)
- 📞 Contacts
- 📸 Photos (futur)

---

## 🏗️ Architecture

### Bridge V5/V6

```
┌─────────────────────────────────────────────┐
│  Frontend (React)                           │
│  ChatIntelligent.jsx                        │
└──────────────┬──────────────────────────────┘
               │
               │ REST API
               ↓
┌─────────────────────────────────────────────┐
│  FastAPI Routes                             │
│  /api/chat/query                            │
│  /api/chat/day/{date}                       │
│  /api/chat/appointment/{id}                 │
└──────────────┬──────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────┐
│  ChatService (Strategy Pattern)             │
│  ├─ V5DataProvider  ← Actuellement actif    │
│  └─ V6DataProvider  ← Futur (Reconciler)    │
└──────────────┬──────────────────────────────┘
               │
      ┌────────┴────────┐
      ↓                 ↓
┌──────────┐     ┌────────────┐
│ Supabase │     │ V6 Staging │  (futur)
│ V5 Tables│     │ + Reconcil.│
└──────────┘     └────────────┘
```

### Modularité

**Principe:** Toute la logique de transformation est isolée dans `V5DataProvider`.

Quand V6 sera prêt:
```python
# Avant
service = ChatService(data_source="v5")

# Après
service = ChatService(data_source="v6")
# ✅ Zéro changement dans le frontend ou les routes!
```

---

## 📁 Structure Fichiers

```
api/chat/
├── __init__.py              # Exports publics
├── README.md                # Ce fichier
├── schemas.py               # Pydantic models (Niveau 1 & 2)
└── service.py               # ChatService + V5DataProvider

api/
└── chat_routes.py           # Routes FastAPI

frontend/src/components/
└── ChatIntelligent.jsx      # Interface React

docs/
└── CHAT_INTELLIGENT_SQL.md  # Documentation SQL
```

---

## 🚀 Usage

### Backend (FastAPI)

#### 1. Importer les routes dans main.py

```python
from api.chat_routes import router as chat_router

app.include_router(chat_router)
```

#### 2. Démarrer le serveur

```bash
cd api
uvicorn main:app --reload --port 8000
```

### Frontend (React)

#### 1. Ajouter la route

```jsx
// App.jsx
import ChatIntelligent from './components/ChatIntelligent';

<Route path="/chat" element={<ChatIntelligent />} />
```

#### 2. Configurer l'URL API

```.env
REACT_APP_API_URL=http://localhost:8000
```

#### 3. Démarrer

```bash
cd frontend
npm start
```

---

## 📡 API Endpoints

### POST /api/chat/query

Requête naturelle → Réponse structurée.

**Request:**
```json
{
  "query": "Ma journée de demain",
  "technician_id": "usr_xxx"  // optionnel
}
```

**Response:**
```json
{
  "interpreted_query": "Journée du 2025-12-30",
  "query_type": "day_overview",
  "day_overview": {
    "date": "2025-12-30",
    "technician_name": "Nicolas Lessard",
    "total_appointments": 5,
    "total_pianos": 5,
    "estimated_duration_hours": 7.5,
    "neighborhoods": ["Plateau", "Mile-End"],
    "appointments": [
      {
        "appointment_id": "apt_123",
        "time_slot": "09:00 - 11:00",
        "client_name": "UQAM - Pavillon Musique",
        "neighborhood": "Quartier Latin",
        "piano_brand": "Yamaha",
        "piano_model": "C7",
        "action_items": ["Apporter cordes #3", "Vérifier humidité"],
        "priority": "high"
      }
      // ... autres RDV
    ]
  },
  "data_source": "v5",
  "generated_at": "2025-12-29T10:30:00Z"
}
```

### GET /api/chat/day/{date}

Vue journée directe (bypass NLP).

**Example:**
```http
GET /api/chat/day/2025-12-30?technician_id=usr_xxx
```

### GET /api/chat/appointment/{id}

Détails complets d'un RDV.

**Example:**
```http
GET /api/chat/appointment/apt_123
```

**Response:**
```json
{
  "overview": { /* AppointmentOverview */ },
  "comfort": {
    "dog_name": "Max",
    "access_code": "1234#",
    "parking_info": "Rue St-Denis, zone payante",
    "contact_phone": "514-xxx-xxxx"
  },
  "timeline_summary": "Dernière visite le 15 nov 2024 par Nicolas...",
  "timeline_entries": [
    {
      "date": "2024-11-15",
      "type": "service",
      "technician": "Nicolas Lessard",
      "summary": "Accord 442Hz, humidité 45%",
      "temperature": 23.0,
      "humidity": 45.0
    }
  ]
}
```

---

## 🎨 UI/UX Design

### Mobile-First

**Principes:**
- ✅ Cards compactes (scan rapide)
- ✅ Quartier GROS et visible (priorité logistique)
- ✅ Drawer swipe-up (détails accessibles, pas intrusifs)
- ✅ Icônes pour scannabilité (🦴 🔑 📍 ⏰)
- ✅ Badges visuels (nouveau, urgent, alertes)

### Quick Actions

**Chips en haut:**
- "Aujourd'hui"
- "Demain"
- "Après-demain"

→ 1 tap = vue complète

### Progressive Disclosure

**Niveau 1 (Card):** Info critique terrain
**Niveau 2 (Drawer):** Confort + historique

Utilisateur ne voit que ce dont il a besoin, quand il en a besoin.

---

## 🔧 Développement

### Ajouter un Nouveau Champ

#### 1. Modifier le schéma

```python
# schemas.py
class AppointmentOverview(BaseModel):
    # ... champs existants
    new_field: Optional[str] = None  # Nouveau champ
```

#### 2. Mapper dans le provider

```python
# service.py - V5DataProvider._map_to_overview()
return AppointmentOverview(
    # ... mappings existants
    new_field=apt_raw.get("new_field_source")
)
```

#### 3. Afficher dans l'UI

```jsx
// ChatIntelligent.jsx - AppointmentCard
{appointment.new_field && (
  <Typography>{appointment.new_field}</Typography>
)}
```

### Améliorer le NLP

Actuellement: Simple pattern matching.

**Améliorations possibles:**
- [ ] Utiliser `dateparser` pour parsing dates avancé
- [ ] Intégrer spaCy pour NER (Named Entity Recognition)
- [ ] Support multi-langue (FR/EN)
- [ ] Intent classification (ML model)

---

## 📊 Données Requises

### Tables V5 Utilisées

| Table                     | Colonnes Clés                          |
|---------------------------|----------------------------------------|
| `gazelle_appointments`    | date, time, notes, client_id, piano_id |
| `gazelle_clients`         | name, address, municipality            |
| `gazelle_pianos`          | make, model, type                      |
| `gazelle_timeline_entries`| occurred_at, type, title, details      |
| `users`                   | first_name, last_name                  |

### Données Manquantes (À Enrichir)

- [ ] **Codes d'accès** - Ajouter colonne `access_code` sur clients
- [ ] **Nom du chien/chat** - Parser notes ou ajouter champ dédié
- [ ] **Préférence accordage** - Champ `preferred_hz` sur piano
- [ ] **Photos piano** - Table `piano_photos` avec URLs
- [ ] **Dernière visite** - Calculer depuis timeline (lent) → materialized view?

---

## 🧪 Tests

### Test Unitaire (Service)

```python
def test_map_v5_to_overview():
    v5_data = {
        "external_id": "apt_123",
        "appointment_date": "2025-12-30",
        "appointment_time": "09:00",
        "client": {
            "company_name": "UQAM",
            "default_location_municipality": "Montréal"
        },
        "piano": {
            "make": "Yamaha",
            "model": "C7"
        }
    }

    provider = V5DataProvider(storage)
    overview = provider._map_to_overview(v5_data, "2025-12-30")

    assert overview.client_name == "UQAM"
    assert overview.neighborhood == "Montréal"
    assert overview.piano_brand == "Yamaha"
```

### Test E2E (API)

```bash
# Journée de demain
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"query": "demain"}'

# Détails RDV
curl http://localhost:8000/api/chat/appointment/apt_123
```

### Test UI (Cypress)

```javascript
describe('Chat Intelligent', () => {
  it('charge la journée de demain', () => {
    cy.visit('/chat');
    cy.contains('Demain').click();
    cy.get('[data-testid="appointment-card"]').should('have.length.greaterThan', 0);
  });

  it('ouvre le drawer détails', () => {
    cy.get('[data-testid="appointment-card"]').first().click();
    cy.get('[data-testid="detail-drawer"]').should('be.visible');
  });
});
```

---

## 🚀 Migration V6

### Phase 1: Préparation (Fait ✅)

- [x] Schémas Pydantic isolés
- [x] Strategy Pattern (V5DataProvider)
- [x] Documentation SQL complète
- [x] Frontend découplé (appelle API, pas DB directe)

### Phase 2: V6 Data Provider (À faire)

```python
# api/chat/service_v6.py
class V6DataProvider:
    """
    Récupère données depuis V6 (Staging + Reconciler).
    """

    def __init__(self, reconciler: ReconcilerService):
        self.reconciler = reconciler

    def get_day_overview(self, date, technician_id):
        # 1. Récupérer depuis staging ou cache
        cached = self.check_cache(date, technician_id)
        if cached:
            return cached

        # 2. Fetch depuis Reconciler
        appointments = self.reconciler.get_appointments(
            date=date,
            technician_id=technician_id
        )

        # 3. Transform (même fonction que V5!)
        overview = self._map_to_overview(appointments)

        # 4. Cache
        self.cache_result(overview)

        return overview
```

### Phase 3: Switchover

```python
# api/chat_routes.py
# Avant
chat_service = ChatService(data_source="v5")

# Après
chat_service = ChatService(data_source="v6")

# Migration progressive
data_source = os.getenv("CHAT_DATA_SOURCE", "v5")  # Feature flag
chat_service = ChatService(data_source=data_source)
```

### Phase 4: Optimisations V6

- [ ] **Caching Redis** - Journée du jour (invalidation auto)
- [ ] **WebSocket** - Updates real-time si changements
- [ ] **Predictive Loading** - Preload demain à minuit
- [ ] **Offline Mode** - Service Worker pour PWA

---

## 📈 Métriques de Succès

### Utilisation
- **Adoption:** % techniciens utilisant quotidiennement
- **Temps de préparation:** Réduction de X min → Y sec
- **Satisfaction:** NPS score

### Performance
- **Load time:** < 2s pour journée complète
- **API latency:** < 500ms pour /query
- **Cache hit rate:** > 80% (journée du jour)

### Qualité Données
- **Complétude:** % RDV avec toutes infos (quartier, piano, etc.)
- **Fraîcheur:** Délai entre sync Gazelle et affichage

---

## 🐛 Troubleshooting

### "Aucun rendez-vous"

**Causes possibles:**
1. Aucun RDV dans Supabase pour cette date
2. Filtre technicien trop restrictif
3. Problème sync Gazelle → Supabase

**Debug:**
```sql
-- Vérifier données
SELECT COUNT(*) FROM gazelle_appointments
WHERE appointment_date = '2025-12-30';
```

### "Technicien vide"

La colonne `user_id` est NULL dans `gazelle_timeline_entries`.

**Fix:** Lancer `fix_timeline_user_ids.py` (déjà fait normalement).

### "Quartier manquant"

Le client n'a pas de `default_location_municipality`.

**Fix:** Enrichir données client dans Gazelle ou Supabase.

---

## 📞 Support

Questions? Voir:
- [Leçons apprises](../../docs/historique/V6_LECONS_APPRISES.md) - Leçons apprises (ex-V6)
- [CHAT_INTELLIGENT_SQL.md](../../docs/CHAT_INTELLIGENT_SQL.md) - SQL queries

---

**Status:** ✅ Production-ready (V5)
**Next:** V6 Data Provider + Caching
