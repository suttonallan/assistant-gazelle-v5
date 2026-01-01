# Chat Intelligent - Implémentation V5 et Spécifications V6

## 📋 Vue d'Ensemble

Le **Chat Intelligent** est une interface conversationnelle pour que les techniciens consultent leur journée de travail de manière naturelle et mobile-first.

**Date Implémentation V5:** 2025-12-29
**Status:** ✅ Opérationnel en V5, Spécifications V6 complètes

---

## 🏗️ Architecture V5 (Actuelle)

### Stack Technique

#### Backend
```
FastAPI (Python 3.9+)
├── api/chat_routes.py         # Routes REST (/api/chat/*)
├── api/chat/
│   ├── __init__.py           # Exports publics
│   ├── schemas.py            # Modèles Pydantic v2
│   ├── service.py            # Logique métier (ChatService)
│   └── geo_mapping.py        # Mapping codes postaux → quartiers
└── core/
    └── gazelle_api_client.py # Client Supabase (V5)
```

#### Frontend
```
React 18.3.1 + Vite
├── src/components/
│   └── ChatIntelligent.jsx    # Composant principal
├── src/App.jsx                 # Intégration routing
└── Dependencies:
    ├── @mui/material@7.3.6    # UI Components
    ├── @mui/icons-material     # Icônes
    └── axios@1.13.2            # HTTP Client

⚠️ IMPORTANT: Vite utilise import.meta.env, PAS process.env
   Toujours utiliser: import.meta.env.VITE_API_URL
```

### Endpoints API

#### 1. Health Check
```http
GET /api/chat/health
Response: {"status": "healthy", "service": "chat_intelligent", "data_source": "v5"}
```

#### 2. Query Natural Language
```http
POST /api/chat/query
Body: {"query": "Ma journée de demain"}

Response:
{
  "query_interpreted": "Demain (2025-12-30)",
  "day_overview": {
    "date": "2025-12-30",
    "total_appointments": 3,
    "total_pianos": 4,
    "estimated_duration_hours": 5.5,
    "neighborhoods": ["Rosemont", "Villeray", "Plateau"],
    "appointments": [
      {
        "appointment_id": "evt_xxx",
        "time_slot": "09:00 - 11:00",
        "client_name": "M. Tremblay",
        "neighborhood": "Rosemont (H2G)",
        "address_short": "4520 rue St-Denis",
        "piano_brand": "Yamaha",
        "piano_model": "U1",
        "piano_type": "Droit",
        "is_new_client": false,
        "has_alerts": true,
        "priority": "normal",
        "action_items": ["Apporter cordes #3"],
        "last_visit_date": "2024-11-15",
        "days_since_last_visit": 45
      }
    ]
  }
}
```

#### 3. Day Overview (Direct)
```http
GET /api/chat/day/{date}?technician_id=allan

Response: (même structure que day_overview ci-dessus)
```

#### 4. Appointment Detail
```http
GET /api/chat/appointment/{appointment_id}

Response:
{
  "overview": { ... },  # Même structure que card
  "comfort": {
    "contact_name": "M. Jean Tremblay",
    "contact_phone": "514-555-1234",
    "access_code": "1234#",
    "access_instructions": "Sonner chez Mme Roy au 2e",
    "dog_name": "Max",
    "dog_breed": "Golden Retriever",
    "dog_notes": "Très gentil",
    "parking_info": "Rue, zone payante",
    "special_notes": "Ascenseur de service à droite"
  },
  "billing": {                    # NULL si client == contact
    "client_name": "École de Musique XYZ",
    "balance_due": 450.00,
    "last_payment_date": "2024-11-15"
  },
  "timeline_summary": "Dernière visite il y a 45 jours. Piano accordé, cordes changées.",
  "timeline_entries": [
    {
      "date": "2024-11-15",
      "type": "Accord",
      "technician": "Allan",
      "summary": "Accord complet, remplacement cordes #3",
      "temperature": 20,
      "humidity": 45
    }
  ]
}
```

---

## 🎨 Design UI/UX

### Architecture Progressive Disclosure

**Niveau 1: Cards (Liste)**
- Vue compacte, scannable rapidement
- Infos critiques seulement: heure, client, lieu, piano
- Badges visuels: Nouveau client, Alertes, Priorité
- Optimisée pour mobile (cards empilées)

**Niveau 2: Drawer (Détails)**
- Swipe up sur mobile / Click sur desktop
- 3 sections:
  1. **Sur Place** (ComfortInfo) - Codes, chien, parking
  2. **Facturation** (BillingInfo) - Si client ≠ contact
  3. **Historique** (Timeline) - Dernières interventions

### Wireframe Card (Niveau 1)

```
┌────────────────────────────────────────┐
│ ⏰ 09:00 - 11:00          🏷️ Nouveau   │
│                                        │
│ M. Jean Tremblay                       │  ← Contact (priorité)
│ Facturer à: École XYZ                  │  ← Client (si différent)
│                                        │
│ 📍 Rosemont (H2G)                      │  ← Quartier (pas "Montréal")
│ 4520 rue St-Denis                      │
│                                        │
│ 🎹 Yamaha U1 (Droit)                   │
│                                        │
│ 📋 Apporter cordes #3                  │  ← Action items
└────────────────────────────────────────┘
```

### Wireframe Drawer (Niveau 2)

```
┌────────────────────────────────────────┐
│ M. Jean Tremblay                    ✕  │
│ ────────────────────────────────────── │
│                                        │
│ 👤 SUR PLACE                           │  ← Section 1
│ ────────────────────────────────────── │
│ 📞 514-555-1234                        │
│ 📍 4520 rue St-Denis, Montréal H2G 2J8 │
│                                        │
│ 🔑 Code: 1234#                         │  ← Orange, monospace
│ 🦴 Chien: Max (golden retriever)       │
│    Très gentil, laisser entrer         │
│                                        │
│ 🅿️  Stationnement: Rue, zone payante   │
│                                        │
│ ────────────────────────────────────── │
│                                        │
│ 💼 FACTURATION                         │  ← Section 2 (si ≠ contact)
│ ────────────────────────────────────── │
│ École de Musique XYZ                   │
│ Solde impayé: 450,00$                  │
│ Dernier paiement: 15 nov 2024          │
│                                        │
│ ────────────────────────────────────── │
│                                        │
│ 📖 HISTORIQUE                          │  ← Section 3
│ Dernière visite il y a 45 jours        │
│ Accord complet, cordes #3 changées     │
│                                        │
│ 15 nov 2024 • Accord • par Allan       │
│ Température: 20°C • Humidité: 45%      │
│                                        │
└────────────────────────────────────────┘
```

---

## 📊 Mapping Géographique

### Objectif
Transformer `H2G 2J8` en `"Rosemont"` au lieu de `"Montréal"` générique.

### Implémentation V5

**Fichier:** `api/chat/geo_mapping.py`

**Dictionnaire:** 100+ codes postaux Montréal + Région

```python
MTL_POSTAL_TO_NEIGHBORHOOD = {
    # MONTRÉAL CENTRAL
    'H2W': 'Plateau Mont-Royal',
    'H2J': 'Plateau Mont-Royal',
    'H2G': 'Rosemont',
    'H2S': 'Villeray',
    'H1V': 'Mercier-Est',

    # LAVAL
    'H7E': 'Laval-des-Rapides',
    'H7L': 'Vimont',

    # RIVE-SUD
    'J4J': 'Boucherville',
    'J4K': 'Longueuil (Greenfield Park)',

    # ... 100+ codes
}

def get_neighborhood_from_postal_code(postal_code: str, fallback_city: str = None) -> str:
    """
    Extrait quartier depuis code postal.

    Args:
        postal_code: "H2G 2J8" ou "H2G2J8"
        fallback_city: "Montréal" (utilisé si code inconnu)

    Returns:
        "Rosemont" ou fallback_city
    """
    if not postal_code:
        return fallback_city or ""

    # Nettoyer: H2G2J8 → H2G
    cleaned = ''.join(c.upper() for c in postal_code if c.isalnum())[:3]

    neighborhood = MTL_POSTAL_TO_NEIGHBORHOOD.get(cleaned)

    if neighborhood:
        return neighborhood

    return fallback_city or cleaned
```

### Utilisation dans Service

```python
# api/chat/service.py:_map_to_overview()

from .geo_mapping import get_neighborhood_from_postal_code

postal_code = client.get("default_location_postal_code") or ""
municipality = client.get("default_location_municipality") or ""

# Mapping géographique
neighborhood = get_neighborhood_from_postal_code(postal_code, municipality)
```

### ⚠️ Limitation V5

**Problème:** Données V5 n'ont PAS de code postal dans la DB

```sql
-- V5 actuel (gazelle_clients):
SELECT default_location_postal_code FROM gazelle_clients LIMIT 1;
-- Résultat: NULL (colonne n'existe pas ou vide)
```

**Workaround:** Code prêt, mais attend enrichissement données.

**Solutions Possibles:**
1. Ajouter colonne + parser adresses existantes
2. Import manuel depuis Gazelle API
3. Attendre migration V6 complète

---

## 🔑 Distinction Client vs Contact (CRITIQUE)

### Principe Fondamental

**CONTACT = Personne physique rencontrée sur place**
**CLIENT = Entité qui paie la facture**

### Règles d'Affichage

1. **Priorité absolue au CONTACT** dans l'UI
2. Afficher "Facturer à: [Client]" SEULEMENT si différent
3. **Codes d'accès** TOUJOURS liés à l'adresse physique (location), JAMAIS au client
4. Sections séparées dans Drawer: "Sur Place" vs "Facturation"

### Exemples de Cas

#### Cas 1: Particulier (Contact = Client)
```
M. Dupont possède son piano et paie lui-même

Affichage Card:
  M. Dupont              ← Contact
  📍 Rosemont

PAS de mention "Facturer à"
```

#### Cas 2: École (Contact ≠ Client)
```
Contact: M. Tremblay (prof de musique)
Client: École de Musique XYZ
Location: 4520 rue St-Denis (chez M. Tremblay)

Affichage Card:
  M. Jean Tremblay                ← Contact (priorité)
  Facturer à: École de Musique XYZ  ← Client (discret)
  📍 Rosemont
  🔑 Code: 1234#  ← Code de l'adresse de M. Tremblay

Drawer Section Facturation:
  💼 FACTURATION
  École de Musique XYZ
  Solde: 450$
```

#### Cas 3: Université Multiples Contacts
```
Client: Université de Montréal
Contact A: Mme Roy (Salle 301)
Contact B: M. Lee (Salle 102)

Chaque contact a:
- SON code d'accès (lié à SA salle)
- SON adresse (location_id différent)
- SON chien éventuel
- Même client facturé
```

### Schéma Tables V6 (Recommandé)

```sql
-- Table gazelle_contacts (personnes physiques)
CREATE TABLE gazelle_contacts (
    external_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    email TEXT,
    client_id TEXT REFERENCES gazelle_clients(external_id)
);

-- Table gazelle_locations (adresses physiques)
CREATE TABLE gazelle_locations (
    id UUID PRIMARY KEY,
    contact_id TEXT REFERENCES gazelle_contacts(external_id),
    street TEXT,
    municipality TEXT,
    postal_code TEXT,
    region TEXT,

    -- Infos sécurité (liées à l'adresse)
    access_code TEXT,
    access_code_type TEXT,  -- "door", "building", "gate"
    access_instructions TEXT,

    dog_name TEXT,
    dog_breed TEXT,
    dog_notes TEXT,

    parking_type TEXT,  -- "street", "driveway", "garage"
    parking_notes TEXT,

    special_access_notes TEXT
);

-- Table gazelle_appointments (rendez-vous)
ALTER TABLE gazelle_appointments
  ADD COLUMN contact_id TEXT REFERENCES gazelle_contacts(external_id),
  ADD COLUMN location_id UUID REFERENCES gazelle_locations(id);
```

### Logique d'Affichage (Code V5 Temporaire)

```python
def get_display_name(appointment):
    """
    Retourne nom à afficher (TOUJOURS contact en priorité).
    """
    # 1. Contact (priorité absolue)
    contact = appointment.get("contact")
    if contact:
        first_name = contact.get("first_name", "")
        last_name = contact.get("last_name", "")
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()

    # 2. Client (fallback si pas de contact)
    client = appointment.get("client")
    if client:
        company_name = client.get("company_name")
        if company_name:
            return company_name

    # 3. Dernier recours
    return "Contact non spécifié"


def get_billing_info(appointment):
    """
    Retourne infos facturation.
    Retourne None si contact == client.
    """
    contact = appointment.get("contact")
    client = appointment.get("client")

    # Si contact EST le client, pas de mention séparée
    if contact and client:
        contact_id = contact.get("external_id")
        client_id = client.get("external_id")

        if contact_id == client_id:
            return None  # Même entité

    # Client différent du contact
    if client:
        return {
            "name": client.get("company_name"),
            "balance_due": client.get("balance_due"),
            "last_payment_date": client.get("last_payment_date")
        }

    return None
```

### ⚠️ Sécurité: Codes d'Accès

**RÈGLE CRITIQUE:**
Les codes d'accès sont **TOUJOURS** liés à l'**adresse physique** (location), **JAMAIS** au client.

**Exemple Dangereux (à éviter):**
```python
# ❌ MAUVAIS
client = get_client(client_id)
access_code = client.access_code  # FAUX! Siège social ailleurs
```

**Exemple Correct:**
```python
# ✅ BON
location = get_location(appointment.location_id)
access_code = location.access_code  # Bon! Code de CET endroit
```

---

## 🔄 Bridge Pattern V5 → V6

### Objectif
Préparer migration V6 sans casser V5 actuelle.

### Strategy Pattern pour DataProvider

```python
# api/chat/service.py

class ChatService:
    def __init__(self, data_source: str = "v5"):
        """
        Args:
            data_source: "v5" ou "v6"
        """
        if data_source == "v5":
            self.provider = V5DataProvider()
        else:
            self.provider = V6DataProvider()

    async def get_day_overview(self, date: str, technician_id: Optional[str] = None):
        """Interface publique (stable entre V5 et V6)."""
        return await self.provider.get_day_overview(date, technician_id)


class V5DataProvider:
    """Implémentation actuelle (Supabase V5)."""

    def _map_to_overview(self, apt_raw: Dict):
        """FONCTION CRITIQUE pour bridge V5→V6."""
        # Transformation données V5 → format API unifié
        # ...


class V6DataProvider:
    """Future implémentation (Reconciler V6)."""

    def _map_to_overview(self, apt_raw: Dict):
        """Utilise tables normalisées V6."""
        # Accès direct à contacts, locations, clients séparés
        # ...
```

### Avantages

1. **Frontend inchangé** lors migration V6
2. **Routes API identiques** (contrats stables)
3. **Tests réutilisables** (même schémas Pydantic)
4. **Rollback facile** (switch data_source="v5")

---

## 📚 Configuration Centenant

**Fichier:** `.centenantrc`

### 6 Règles Critiques du Projet

```bash
## RÈGLE #1: Distinction Client vs Contact (CRITIQUE)
# Ne JAMAIS confondre:
# - CONTACT = Personne physique rencontrée sur place
# - CLIENT = Entité qui paie la facture
# Priorité ABSOLUE au CONTACT dans l'interface utilisateur
# Codes d'accès TOUJOURS liés à l'adresse physique

## RÈGLE #2: Mapping Géographique
# Utiliser api/chat/geo_mapping.py pour transformer codes postaux
# Priorité: Quartier spécifique > Ville générique
# Ex: H2G → "Rosemont" (pas "Montréal")

## RÈGLE #3: Bridge V5/V6
# Toujours isoler logique de transformation dans DataProvider
# Frontend et routes NE DOIVENT PAS changer lors migration V6
# Pattern: Strategy Pattern avec V5DataProvider / V6DataProvider

## RÈGLE #4: Mobile-First Design
# Interface Chat optimisée pour mobile
# Niveau 1 (Cards): Info critique uniquement
# Niveau 2 (Drawer): Détails accessibles mais pas intrusifs

## RÈGLE #5: Tests d'Intégration
# TOUJOURS tester les 3 endpoints après modification:
# - POST /api/chat/query
# - GET /api/chat/day/{date}
# - GET /api/chat/appointment/{id}

## RÈGLE #6: Sécurité Codes d'Accès
# Les codes d'accès sont SENSIBLES
# - Liés à l'adresse physique (location), jamais au client
# - Affichés uniquement dans Drawer (Niveau 2)
# - Font monospace, couleur orange
# - Jamais dans logs ou traces
```

---

## ✅ Tests Intégration

### Script de Test

**Fichier:** `test_chat_integration.py`

```python
#!/usr/bin/env python3
import requests

API_BASE = "http://localhost:8000"

def test_health():
    """Test 1: Health check."""
    response = requests.get(f"{API_BASE}/api/chat/health")
    assert response.status_code == 200
    print("✅ Test 1: Health check OK")

def test_query_natural():
    """Test 2: Query naturelle."""
    response = requests.post(
        f"{API_BASE}/api/chat/query",
        json={"query": "demain"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "day_overview" in data
    print("✅ Test 2: Query naturelle OK")
    return data["day_overview"]["appointments"][0]["appointment_id"]

def test_day_direct(date=None):
    """Test 3: GET /day/{date}."""
    if not date:
        from datetime import datetime, timedelta
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    response = requests.get(f"{API_BASE}/api/chat/day/{date}")
    assert response.status_code == 200
    print("✅ Test 3: Day overview OK")

def test_appointment_detail(appointment_id):
    """Test 4: GET /appointment/{id}."""
    response = requests.get(
        f"{API_BASE}/api/chat/appointment/{appointment_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "comfort" in data
    assert "timeline_entries" in data
    print("✅ Test 4: Appointment detail OK")

if __name__ == "__main__":
    test_health()
    apt_id = test_query_natural()
    test_day_direct()
    test_appointment_detail(apt_id)
    print("\n🎉 Tous les tests passent! (4/4)")
```

### Résultats

```
✅ Test 1: Health check OK
✅ Test 2: Query naturelle OK
✅ Test 3: Day overview OK
✅ Test 4: Appointment detail OK

🎉 Tous les tests passent! (4/4)
```

---

## 🚀 Instructions Déploiement

### Backend (FastAPI)

```bash
cd /Users/allansutton/Documents/assistant-gazelle-v5

# Démarrer API
source .env
python3 -m uvicorn api.main:app --reload --port 8000

# Vérifier health
curl http://localhost:8000/api/chat/health
# {"status":"healthy","service":"chat_intelligent","data_source":"v5"}
```

### Frontend (Vite)

```bash
cd frontend

# Installer dépendances (si première fois)
npm install

# Démarrer dev server
npm run dev

# URL: http://localhost:5173/
```

### Accès Interface

1. **Ouvrir:** http://localhost:5173/
2. **Se connecter:**
   - Allan: PIN 6342 (admin - accès complet)
   - Louise: PIN 6343 (peut voir Chat)
3. **Naviguer:** Cliquer sur bouton "💬 Ma Journée" dans header
4. **Tester:** Utiliser boutons "Aujourd'hui", "Demain", ou requête personnalisée

---

## 🎯 Améliorations V6

### 1. Tables Normalisées

Implémenter schéma complet:
- `gazelle_contacts` (personnes physiques)
- `gazelle_locations` (adresses + codes accès)
- Relations propres dans `gazelle_appointments`

### 2. Reconciler Intégré

```python
class V6DataProvider:
    def __init__(self):
        self.reconciler = GazelleReconcilerV6()

    async def get_day_overview(self, date, tech_id):
        # Utilise Reconciler pour garantir relations correctes
        appointments = await self.reconciler.get_appointments(
            date=date,
            technician_id=tech_id,
            expand=["contact", "location", "client", "piano"]
        )
        # ...
```

### 3. Codes Postaux Enrichis

```sql
-- Enrichir données existantes
UPDATE gazelle_locations
SET postal_code = SUBSTRING(full_address FROM '[A-Z][0-9][A-Z] ?[0-9][A-Z][0-9]')
WHERE postal_code IS NULL;
```

### 4. Error Boundary Frontend

```typescript
// v6/frontend/src/components/ChatIntelligent.tsx
export default function ChatIntelligent() {
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Health check API au mount
    axios.get(`${API_BASE}/api/chat/health`)
      .then(() => console.log('✅ API accessible'))
      .catch(err => setError(err));
  }, []);

  if (error) {
    return (
      <Alert severity="error">
        Impossible de contacter l'API.
      </Alert>
    );
  }

  // ... reste
}
```

### 5. TypeScript Complet

```typescript
// v6/api/chat/schemas.ts
export interface AppointmentDetail {
  overview: AppointmentOverview;
  comfort: ComfortInfo;
  billing: BillingInfo | null;  // NULL si contact == client
  timeline_summary: string;
  timeline_entries: TimelineEntry[];
}

export interface ComfortInfo {
  contact_name?: string;
  contact_phone?: string;
  access_code?: string;
  dog_name?: string;
  parking_info?: string;
}
```

### 6. Tests E2E Automatisés

```typescript
// v6/tests/e2e/chat.spec.ts (Playwright)
test('Chat Intelligent - Journée technicien', async ({ page }) => {
  await page.goto('http://localhost:5173/');

  // Login
  await page.click('text=Allan');
  await page.fill('input[type="password"]', '6342');
  await page.click('button:has-text("Connexion")');

  // Naviguer vers Chat
  await page.click('text=💬 Ma Journée');

  // Vérifier cards s'affichent
  await expect(page.locator('.appointment-card')).toHaveCount(3);

  // Cliquer sur premier rendez-vous
  await page.locator('.appointment-card').first().click();

  // Vérifier drawer s'ouvre
  await expect(page.locator('text=SUR PLACE')).toBeVisible();
  await expect(page.locator('text=Code:')).toBeVisible();
});
```

### 7. Cache Redis (Performance)

```python
# v6/api/chat/cache.py
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_day_overview(date: str, data: dict, ttl: int = 3600):
    """Cache overview journée (1h)."""
    key = f"chat:day:{date}"
    redis_client.setex(key, ttl, json.dumps(data))

def get_cached_day(date: str) -> Optional[dict]:
    """Récupère overview depuis cache."""
    key = f"chat:day:{date}"
    cached = redis_client.get(key)
    return json.loads(cached) if cached else None
```

---

## 📝 Checklist Implémentation V6

### Phase 1: Infrastructure
- [ ] Créer tables `gazelle_contacts`
- [ ] Créer tables `gazelle_locations`
- [ ] Ajouter colonnes `contact_id`, `location_id` à `gazelle_appointments`
- [ ] Scripts migration données V5 → V6
- [ ] Enrichir codes postaux depuis adresses

### Phase 2: Backend
- [ ] Implémenter `V6DataProvider`
- [ ] Intégrer Reconciler V6
- [ ] Mapping géographique activé (données enrichies)
- [ ] Tests unitaires + intégration V6
- [ ] Cache Redis pour performance

### Phase 3: Frontend
- [ ] Migrer vers TypeScript
- [ ] Ajouter Error Boundary
- [ ] Améliorer drawer (3 sections claires)
- [ ] Tests E2E Playwright
- [ ] Responsive mobile (touch gestures)

### Phase 4: Qualité
- [ ] Documentation API OpenAPI/Swagger
- [ ] Logs structurés (JSON)
- [ ] Monitoring (Sentry/Datadog)
- [ ] CI/CD GitHub Actions
- [ ] Code coverage > 80%

---

## 📚 Références

### Documents Projet
- `.centenantrc` - 6 règles critiques
- `docs/DISTINCTION_CLIENT_CONTACT.md` - Spécification complète
- `test_chat_integration.py` - Tests intégration
- `assistant-v6/TROUBLESHOOTING_FRONTEND_BLANK_PAGE.md` - Debug frontend

### Code Source
- `api/chat_routes.py` - Routes FastAPI
- `api/chat/schemas.py` - Modèles Pydantic
- `api/chat/service.py` - Logique métier
- `api/chat/geo_mapping.py` - Mapping géographique
- `frontend/src/components/ChatIntelligent.jsx` - UI React

### Dépendances
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic v2: https://docs.pydantic.dev/latest/
- Material-UI: https://mui.com/
- Axios: https://axios-http.com/

---

## 🎓 Learnings & Best Practices

### Ce qui Fonctionne Bien (V5)

1. **Bridge Pattern** - Permet évolution sans casser l'existant
2. **Progressive Disclosure** - UI simple mais complète
3. **Mobile-First** - Design adapté aux techniciens terrain
4. **Tests Intégration** - Détection rapide des régressions
5. **Centenant Config** - Mémoire règles critiques

### Points d'Attention V6

1. **Relations DB** - Absolument besoin de contact/client/location séparés
2. **Codes Postaux** - Enrichissement données essentiel pour mapping
3. **Sécurité Codes** - Toujours vérifier lien location (pas client)
4. **Performance** - Cache nécessaire pour requêtes fréquentes
5. **Tests E2E** - Automatiser pour éviter régressions UI

### Anti-Patterns à Éviter

❌ Confondre contact et client dans l'UI
❌ Lier codes d'accès au client (siège social)
❌ Afficher "Montréal" générique au lieu du quartier
❌ Surcharger cards Niveau 1 (garder simple)
❌ Oublier tests après modifications

---

**Date Document:** 2025-12-29
**Version:** 1.0
**Status:** ✅ Complet pour migration V6
