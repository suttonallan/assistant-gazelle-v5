# Architecture Map - Assistant Gazelle V6

## 📋 Document "Source de Vérité"

**Objectif:** Définir la structure des dossiers et le rôle de chaque module

**Date création:** 2025-12-29
**Dernière mise à jour:** 2025-12-29

---

## 🗂️ Structure Globale

```
assistant-v6/
├── docs/                          # Documentation vivante (6 piliers)
│   ├── ARCHITECTURE_MAP.md        # Ce document
│   ├── DATA_DICTIONARY.md         # Tables, colonnes, relations
│   ├── USER_ROLES_SECURITY.md     # Voûtes et permissions
│   ├── GEOGRAPHY_LOGIC.md         # Mapping codes postaux
│   ├── UI_UX_STANDARDS.md         # Standards interface
│   └── SYNC_STRATEGY.md           # Stratégie sync Gazelle
│
├── core/                          # Noyau du système
│   ├── __init__.py
│   ├── fetcher/                   # Récupération données externes
│   │   ├── __init__.py
│   │   ├── gazelle_fetcher.py     # Fetch depuis Gazelle API
│   │   └── supabase_fetcher.py    # Fetch depuis Supabase
│   │
│   ├── reconciler/                # ❤️ CŒUR DU SYSTÈME
│   │   ├── __init__.py
│   │   ├── base_reconciler.py     # Classe abstraite
│   │   ├── client_reconciler.py   # Logique Client vs Contact
│   │   ├── piano_reconciler.py    # Logique Pianos
│   │   └── appointment_reconciler.py
│   │
│   ├── models/                    # Modèles Pydantic (schémas)
│   │   ├── __init__.py
│   │   ├── client.py              # Client, Contact, Location
│   │   ├── piano.py               # Piano, PianoType
│   │   ├── appointment.py         # Appointment
│   │   └── timeline.py            # TimelineEntry
│   │
│   └── utils/                     # Utilitaires partagés
│       ├── __init__.py
│       ├── geography.py           # Mapping codes postaux
│       ├── date_utils.py          # Parsing dates
│       └── vault_security.py      # Filtrage par voûte
│
├── api/                           # FastAPI routes
│   ├── __init__.py
│   ├── main.py                    # Point d'entrée API
│   ├── chat/                      # Module Chat Intelligent
│   │   ├── __init__.py
│   │   ├── routes.py              # Endpoints /api/chat/*
│   │   ├── service.py             # ChatService (V6DataProvider)
│   │   └── schemas.py             # Schémas requête/réponse
│   │
│   ├── appointments/              # CRUD appointments
│   ├── clients/                   # CRUD clients
│   └── reports/                   # Génération rapports
│
├── frontend/                      # React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatIntelligent.tsx    # Chat principal
│   │   │   └── ...
│   │   ├── hooks/
│   │   │   └── useReconciler.ts       # Hook pour appeler Reconciler
│   │   └── types/
│   │       └── api.ts                 # Types TypeScript
│   │
│   └── ...
│
├── sync/                          # Jobs synchronisation
│   ├── __init__.py
│   ├── gazelle_to_staging.py      # Gazelle → Staging Table
│   ├── staging_to_production.py   # Staging → Production (Reconciler)
│   └── scheduler.py               # APScheduler jobs
│
├── tests/                         # Tests automatisés
│   ├── unit/                      # Tests unitaires
│   │   ├── test_reconciler.py
│   │   └── ...
│   ├── integration/               # Tests intégration
│   │   └── test_chat_api.py
│   └── e2e/                       # Tests end-to-end (Playwright)
│       └── test_chat_flow.spec.ts
│
└── scripts/                       # Scripts utilitaires
    ├── migrate_v5_to_v6.py        # Migration données
    ├── enrich_postal_codes.py     # Enrichissement géo
    └── seed_dev_data.py           # Données de développement
```

---

## 🏗️ Rôle de Chaque Module

### 1. **core/fetcher/** - Récupération Données

**Responsabilité:**
Récupérer les données **brutes** depuis les sources externes (Gazelle API, Supabase).

**Principe:**
- ❌ **NE FAIT PAS** de transformation
- ✅ **FAIT** uniquement la récupération
- ✅ Gère les erreurs réseau, retry, pagination

**Exemple:**
```python
# core/fetcher/gazelle_fetcher.py
class GazelleFetcher:
    def fetch_clients(self, since: datetime) -> List[Dict]:
        """Récupère les clients depuis Gazelle API."""
        # Retourne les données BRUTES (JSON)
        pass
```

**V5 Current:**
Pas de fetcher séparé, tout mélangé dans `core/gazelle_api_client.py`

**V6 Target:**
Fetchers dédiés, testables, réutilisables

---

### 2. **core/reconciler/** - ❤️ CŒUR DU SYSTÈME

**Responsabilité:**
Transformer les données brutes en données **normalisées** et **relationnelles**.

**Principe:**
- ✅ **SEUL ENDROIT** où on décide : "Ce client a ce contact à cette adresse"
- ✅ Crée les relations Contact → Location → Client
- ✅ Déduplique, enrichit, valide
- ❌ **NE FAIT PAS** de requêtes SQL directes (utilise les Models)

**Exemple:**
```python
# core/reconciler/client_reconciler.py
class ClientReconciler(BaseReconciler):
    def reconcile_client(self, raw_data: Dict) -> ClientWithRelations:
        """
        Prend les données brutes Gazelle et retourne:
        - Client (entité facturation)
        - Contact (personne physique)
        - Location (adresse avec codes)
        """
        # Logique critique Client vs Contact
        pass
```

**V5 Current:**
Logique mélangée dans `api/chat/service.py` → fonction `_map_to_overview()`

**V6 Target:**
Reconciler centralisé, réutilisable partout (Chat, Reports, API)

---

### 3. **core/models/** - Schémas de Données

**Responsabilité:**
Définir les **contrats de données** (Pydantic models)

**Principe:**
- ✅ Un modèle = Une table Supabase
- ✅ Validation automatique des types
- ✅ Sérialisation JSON

**Exemple:**
```python
# core/models/client.py
class Contact(BaseModel):
    """Personne physique rencontrée sur place."""
    external_id: str
    first_name: str
    last_name: str
    phone: Optional[str]
    client_id: str  # FK vers Client (facturation)

class Location(BaseModel):
    """Adresse physique avec codes d'accès."""
    id: UUID
    contact_id: str  # FK vers Contact
    street: str
    city: str
    postal_code: str
    access_code: Optional[str]  # 🔑 Code lié à CETTE adresse
    dog_name: Optional[str]
```

**V5 Current:**
Schémas dans `api/chat/schemas.py`, incomplets

**V6 Target:**
Modèles complets, relation 1:N:1 claire

---

### 4. **core/utils/** - Utilitaires Partagés

**Responsabilité:**
Fonctions réutilisables sans dépendances lourdes

**Sous-modules:**

#### `geography.py` - Mapping Géographique
```python
def get_neighborhood_from_postal_code(postal_code: str, fallback: str) -> str:
    """H2G → 'Rosemont' au lieu de 'Montréal'."""
    # Dictionnaire 100+ codes (déjà fait en V5)
```

#### `vault_security.py` - Filtrage par Voûte
```python
def filter_by_vault(data: List[Dict], user_role: str) -> List[Dict]:
    """
    Filtre les données selon les permissions de voûte.
    Admin: Voit tout
    Technicien: Voit seulement SES rendez-vous
    Stagiaire: Vue lecture seule
    """
```

**V5 Current:**
Fonction géo existe (`api/chat/geo_mapping.py`), pas de voûte

**V6 Target:**
Géo + Voûte + Date utils centralisés

---

### 5. **api/chat/** - Module Chat Intelligent

**Responsabilité:**
Interface conversationnelle pour les techniciens

**Architecture:**

```python
# api/chat/service.py
class ChatService:
    def __init__(self):
        self.reconciler = ClientReconciler()  # ❤️ Utilise le Reconciler

    def process_query(self, query: str) -> ChatResponse:
        """
        1. Interpréter requête ("demain")
        2. Appeler Reconciler pour données normalisées
        3. Retourner format Chat
        """
```

**V5 Current:**
Service fait tout (fetch + transform + format)

**V6 Target:**
Service **orchestre** seulement, délègue au Reconciler

---

### 6. **sync/** - Synchronisation Gazelle

**Responsabilité:**
Garder Supabase à jour avec Gazelle

**Architecture 2-stages:**

```
Gazelle API
    ↓ (gazelle_to_staging.py)
Staging Tables (données brutes)
    ↓ (staging_to_production.py + Reconciler)
Production Tables (données normalisées)
```

**Avantage:**
- Staging = backup des données brutes
- Si Reconciler bug, on peut rejouer depuis staging
- Audit trail complet

**V5 Current:**
Script `sync_to_supabase.py` direct, pas de staging

**V6 Target:**
2-stages avec Reconciler

---

## 🎯 Patterns Architecturaux

### Pattern 1: Separation of Concerns

```
Fetcher → Récupère
Reconciler → Transforme
Service → Orchestre
API → Expose
```

**Chaque couche a UNE responsabilité.**

### Pattern 2: Strategy Pattern (V5/V6 Coexistence)

```python
# api/chat/service.py
class ChatService:
    def __init__(self, data_source: str = "v6"):
        if data_source == "v5":
            self.provider = V5DataProvider()  # Ancien code
        else:
            self.provider = V6DataProvider()  # Avec Reconciler
```

**Permet rollback facile si V6 a des bugs.**

### Pattern 3: Repository Pattern

```python
# core/reconciler/client_reconciler.py
class ClientReconciler:
    def __init__(self, storage: SupabaseStorage):
        self.storage = storage  # Injection de dépendance

    def get_client_with_relations(self, client_id: str):
        # Utilise storage, pas de SQL direct
```

**Facilite les tests unitaires (mock storage).**

---

## 📐 Principes de Design

### ✅ DO (À FAIRE)

1. **Un fichier = Une responsabilité**
   - `client_reconciler.py` s'occupe SEULEMENT des clients
   - PAS de logique piano dedans

2. **Reconciler = Source de Vérité**
   - Toutes les transformations passent par le Reconciler
   - Chat, Reports, API → tous utilisent le même Reconciler

3. **Models Pydantic partout**
   - Pas de `Dict[str, Any]` qui traîne
   - Types stricts

4. **Tests à chaque niveau**
   - Unit: Reconciler seul (mock fetcher)
   - Integration: API complète
   - E2E: Browser avec Playwright

### ❌ DON'T (À ÉVITER)

1. **Pas de logique métier dans les routes**
   ```python
   # ❌ MAUVAIS
   @router.get("/clients/{id}")
   def get_client(id: str):
       raw = supabase.select("*").eq("id", id)
       # Transformation ici → NON!

   # ✅ BON
   @router.get("/clients/{id}")
   def get_client(id: str):
       return client_service.get_client(id)  # Service appelle Reconciler
   ```

2. **Pas de hardcoded SQL**
   - Utiliser les Models Pydantic
   - ORM ou Query Builder

3. **Pas de transformation différente selon l'endpoint**
   - Même client_id → même structure partout
   - Un seul Reconciler

---

## 🚀 Migration V5 → V6

### Phase 1: Infrastructure (Semaine 1-2)
- [ ] Créer tables V6 (contacts, locations)
- [ ] Implémenter Reconciler de base
- [ ] Tests unitaires Reconciler

### Phase 2: API (Semaine 3-4)
- [ ] Migrer Chat API vers V6DataProvider
- [ ] Ajouter Strategy Pattern (v5/v6 switch)
- [ ] Tests intégration

### Phase 3: Frontend (Semaine 5)
- [ ] Migrer vers TypeScript
- [ ] Utiliser nouveaux types API
- [ ] Tests E2E

### Phase 4: Sync (Semaine 6)
- [ ] Implémenter staging tables
- [ ] 2-stage sync avec Reconciler
- [ ] Monitoring et alertes

---

## 📝 Règles de Mise à Jour

**Ce document est "vivant":**

1. **Ajouter un module?**
   - Mettre à jour la structure ASCII
   - Expliquer son rôle
   - Indiquer les dépendances

2. **Modifier un pattern?**
   - Documenter V5 Current vs V6 Target
   - Expliquer le pourquoi

3. **Nouvelle décision architecturale?**
   - Ajouter dans "Principes de Design"
   - Exemples DO/DON'T

**❌ NE JAMAIS:**
- Réécrire tout le document
- Supprimer l'historique V5 Current
- Changer sans justification

---

## 🔗 Documents Liés

- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) - Tables et colonnes
- [SYNC_STRATEGY.md](SYNC_STRATEGY.md) - Détails sync 2-stages
- [UI_UX_STANDARDS.md](UI_UX_STANDARDS.md) - Interface Chat

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après implémentation Phase 1
