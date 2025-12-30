# Data Dictionary - Assistant Gazelle V6

## 📋 Document "Source de Vérité"

**Objectif:** Définir le schéma complet des tables Supabase, colonnes, types de données, relations et contraintes

**Date création:** 2025-12-29
**Dernière mise à jour:** 2025-12-29

---

## 🎯 Principe Fondamental: Contact-Centric Architecture

**Vision V6:**
```
Contact (personne physique)
  ↓ a une
Location (adresse avec codes d'accès)
  ↓ appartient à un
Client (entité de facturation)
```

**Différence avec V5:**
- V5: Tout mélangé dans `gazelle_clients` (company_name peut être une personne!)
- V6: Séparation claire **Contact** (terrain) vs **Client** (facturation)

---

## 📊 Vue d'Ensemble des Tables

### Tables Production (Données Normalisées)

| # | Table | Rôle | Clé Primaire | Relations |
|---|-------|------|--------------|-----------|
| 1 | `gazelle_contacts` | Personnes physiques rencontrées | `external_id` | → `gazelle_clients` |
| 2 | `gazelle_locations` | Adresses avec codes d'accès | `id` (UUID) | → `gazelle_contacts` |
| 3 | `gazelle_clients` | Entités de facturation | `external_id` | - |
| 4 | `gazelle_pianos` | Instruments | `external_id` | → `gazelle_locations` |
| 5 | `gazelle_appointments` | Rendez-vous | `external_id` | → `contacts`, `locations`, `clients` |
| 6 | `gazelle_timeline_entries` | Historique interventions | `id` (UUID) | → `clients`, `pianos` |
| 7 | `gazelle_invoices` | Factures | `external_id` | → `clients` |
| 8 | `gazelle_invoice_items` | Lignes de facture | `external_id` | → `invoices`, `pianos` |

### Tables Staging (Données Brutes)

| # | Table | Rôle | Contenu |
|---|-------|------|---------|
| 1 | `staging_appointments` | Backup RV bruts Gazelle | JSONB complet |
| 2 | `staging_clients` | Backup clients bruts | JSONB complet |
| 3 | `staging_pianos` | Backup pianos bruts | JSONB complet |
| 4 | `staging_timeline` | Backup timeline bruts | JSONB complet |

### Tables Système

| # | Table | Rôle |
|---|-------|------|
| 1 | `sync_metadata` | Derniers sync timestamps |
| 2 | `reconciler_audit` | Logs transformations Reconciler |
| 3 | `data_quality_issues` | Anomalies détectées |

---

## 📐 Diagramme des Relations V6

```
                    ┌─────────────────┐
                    │ GAZELLE_CLIENTS │
                    │  (Facturation)  │
                    │  external_id    │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
           ┌────────────────┐  ┌──────────────┐
           │GAZELLE_CONTACTS│  │GAZELLE_      │
           │ (Personnes)    │  │INVOICES      │
           │  external_id   │  │              │
           └────────┬───────┘  └──────────────┘
                    │
                    ▼
           ┌────────────────┐
           │GAZELLE_         │
           │LOCATIONS       │
           │ (Adresses)     │
           │  id (UUID)     │
           └────────┬───────┘
                    │
           ┌────────┴────────┬──────────────┐
           │                 │              │
           ▼                 ▼              ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │GAZELLE_      │  │GAZELLE_      │  │GAZELLE_      │
    │APPOINTMENTS  │  │PIANOS        │  │TIMELINE_     │
    │              │  │              │  │ENTRIES       │
    └──────────────┘  └──────────────┘  └──────────────┘
```

**Principe clé:** Toute information "sur place" (codes, chien, stationnement) est liée à **Location**, pas à Client.

---

## 🗂️ Tables Détaillées

---

### 1. gazelle_contacts (Personnes Physiques)

**Responsabilité:** Personnes rencontrées sur le terrain.

**Schéma SQL:**
```sql
CREATE TABLE gazelle_contacts (
    -- Identifiant
    external_id TEXT PRIMARY KEY,  -- "con_xxxxx" depuis Gazelle

    -- Identité
    title TEXT,                    -- "M.", "Mme", "Dr."
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    suffix TEXT,                   -- "Jr.", "PhD"

    -- Contact
    email TEXT,
    phone TEXT,
    wants_email BOOLEAN DEFAULT true,
    wants_text BOOLEAN DEFAULT true,
    wants_phone_calls BOOLEAN DEFAULT true,

    -- Relations
    client_id TEXT REFERENCES gazelle_clients(external_id),  -- Qui paie?

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    synced_from_gazelle_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_contacts_client ON gazelle_contacts(client_id);
CREATE INDEX idx_contacts_name ON gazelle_contacts(last_name, first_name);
```

**Colonnes Critiques:**

| Colonne | Type | Description | Exemple | Contraintes |
|---------|------|-------------|---------|-------------|
| `external_id` | TEXT | ID Gazelle unique | `con_M7JWG5NfrgOS7AKd` | PRIMARY KEY, NOT NULL |
| `first_name` | TEXT | Prénom | `Jean` | NOT NULL |
| `last_name` | TEXT | Nom | `Tremblay` | NOT NULL |
| `client_id` | TEXT | Lien vers entité facturation | `cli_j3CIqBa4AjxyUSFN` | FK → `gazelle_clients` |
| `phone` | TEXT | Téléphone direct | `514-555-1234` | Format libre |
| `email` | TEXT | Email personnel | `jean.t@email.com` | Format email |

**Règles de Validation:**
```python
# core/models/contact.py
from pydantic import BaseModel, EmailStr, Field

class Contact(BaseModel):
    """Personne physique rencontrée sur place."""

    external_id: str = Field(..., regex=r'^con_[a-zA-Z0-9]+$')
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, regex=r'^\+?[\d\s\-\(\)\.]+$')
    email: Optional[EmailStr] = None
    client_id: str = Field(..., regex=r'^cli_[a-zA-Z0-9]+$')
```

---

### 2. gazelle_locations (Adresses Physiques)

**Responsabilité:** Adresses avec TOUTES les infos "sur place" (codes, chien, parking).

**Schéma SQL:**
```sql
CREATE TABLE gazelle_locations (
    -- Identifiant
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE,       -- Si provient de Gazelle "loc_xxx"

    -- Relations
    contact_id TEXT NOT NULL REFERENCES gazelle_contacts(external_id),

    -- Adresse
    address_line1 TEXT NOT NULL,   -- "4520 rue St-Denis"
    address_line2 TEXT,            -- "App. 302"
    city TEXT NOT NULL,            -- "Montréal"
    province TEXT NOT NULL,        -- "QC"
    postal_code TEXT NOT NULL,     -- "H2G 2J8"
    country_code TEXT DEFAULT 'CA',

    -- Géolocalisation
    latitude NUMERIC(10, 7),
    longitude NUMERIC(10, 7),
    what3words TEXT,

    -- Infos Confort (🔑 CRITIQUE - Liées à CET endroit seulement!)
    access_code TEXT,              -- "1234#"
    access_code_type TEXT,         -- "door", "building", "gate"
    access_instructions TEXT,      -- "Sonner chez Mme Roy au 2e"

    dog_name TEXT,                 -- "Max"
    dog_breed TEXT,                -- "Golden Retriever"
    dog_notes TEXT,                -- "Très gentil, laisser entrer"

    parking_type TEXT,             -- "street", "driveway", "garage"
    parking_notes TEXT,            -- "Zone payante, parcomètre"

    special_access_notes TEXT,     -- "Ascenseur de service"

    -- Métadonnées
    is_default BOOLEAN DEFAULT false,  -- Adresse principale du contact
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_locations_contact ON gazelle_locations(contact_id);
CREATE INDEX idx_locations_postal ON gazelle_locations(postal_code);
CREATE INDEX idx_locations_default ON gazelle_locations(contact_id, is_default);
```

**⚠️ RÈGLE CRITIQUE:**

> **JAMAIS** stocker `access_code` dans `gazelle_clients`.
> Le code d'accès est lié à UNE adresse physique, PAS à un client (qui peut avoir plusieurs adresses).

**Exemple de Piège à Éviter:**
```python
# ❌ MAUVAIS - Code lié au client
client = Client(
    external_id="cli_xxx",
    company_name="École XYZ",
    access_code="1234#"  # FAUX! L'école a 10 adresses, chacune avec SON code
)

# ✅ BON - Code lié à la location
location_salle301 = Location(
    contact_id="con_xxx",
    address="123 rue A, Salle 301",
    access_code="1234#"  # Bon! Code de CETTE salle
)

location_salle102 = Location(
    contact_id="con_yyy",
    address="123 rue A, Salle 102",
    access_code="5678#"  # Autre code pour CETTE salle
)
```

**Colonnes Critiques:**

| Colonne | Type | Description | Pourquoi Critique |
|---------|------|-------------|-------------------|
| `access_code` | TEXT | Code d'accès | **Sécurité** - Doit être à CETTE adresse |
| `dog_name` | TEXT | Nom du chien | **Sécurité** - Spécifique à CET endroit |
| `parking_notes` | TEXT | Info stationnement | **Efficacité** - Différent selon l'adresse |
| `is_default` | BOOLEAN | Adresse principale | **UX** - Quelle adresse afficher par défaut |

---

### 3. gazelle_clients (Entités de Facturation)

**Responsabilité:** Qui paie la facture (peut être différent du contact).

**Schéma SQL:**
```sql
CREATE TABLE gazelle_clients (
    -- Identifiant
    external_id TEXT PRIMARY KEY,  -- "cli_xxxxx" depuis Gazelle

    -- Identité
    status TEXT NOT NULL,          -- "ACTIVE", "INACTIVE"
    company_name TEXT,             -- Nom entreprise/institution
    client_type TEXT,              -- "Résidentiel", "Institutionnel"

    -- Contact facturation
    billing_email TEXT,
    billing_phone TEXT,
    billing_address TEXT,
    billing_city TEXT,
    billing_postal_code TEXT,
    billing_province TEXT,

    -- Préférences
    region TEXT,                   -- "Montréal", "Rive-Sud"
    preferred_technician TEXT,     -- "Nicolas", "JP"
    locale TEXT DEFAULT 'fr_CA',

    -- Gestion
    reference_id TEXT,             -- ID externe client
    no_contact_until DATE,
    no_contact_reason TEXT,
    reason_inactive TEXT,

    -- Notes
    preference_notes TEXT,
    personal_notes TEXT,

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    synced_from_gazelle_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_clients_status ON gazelle_clients(status);
CREATE INDEX idx_clients_region ON gazelle_clients(region);
CREATE INDEX idx_clients_company ON gazelle_clients(company_name);
```

**Colonnes Critiques:**

| Colonne | Type | Description | Exemple |
|---------|------|-------------|---------|
| `external_id` | TEXT | ID Gazelle | `cli_j3CIqBa4AjxyUSFN` |
| `company_name` | TEXT | Nom entité | `École de Musique XYZ` |
| `billing_email` | TEXT | Email pour factures | `comptabilite@ecole.com` |
| `status` | TEXT | Statut actif/inactif | `ACTIVE` |

**Relation Client ↔ Contact:**

```python
# Un Client peut avoir plusieurs Contacts
client = Client(external_id="cli_xxx", company_name="École XYZ")

contact_prof1 = Contact(
    external_id="con_aaa",
    first_name="Jean",
    client_id="cli_xxx"  # Travaille pour l'école
)

contact_prof2 = Contact(
    external_id="con_bbb",
    first_name="Marie",
    client_id="cli_xxx"  # Travaille aussi pour l'école
)

# Mais chaque Contact n'a qu'UN seul Client (employer/payeur)
```

---

### 4. gazelle_appointments (Rendez-vous)

**Responsabilité:** Rendez-vous planifiés avec liens complets.

**Schéma SQL:**
```sql
CREATE TABLE gazelle_appointments (
    -- Identifiant
    external_id TEXT PRIMARY KEY,  -- "evt_xxxxx" depuis Gazelle

    -- Date & Heure (🔴 TOUJOURS UTC - Voir SYNC_STRATEGY.md)
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,  -- STOCKÉ EN UTC!

    -- Relations (🔑 Triple lien)
    contact_id TEXT REFERENCES gazelle_contacts(external_id),    -- Qui rencontrer
    location_id UUID REFERENCES gazelle_locations(id),           -- Où aller
    client_id TEXT REFERENCES gazelle_clients(external_id),      -- Qui paie
    piano_external_id TEXT REFERENCES gazelle_pianos(external_id),

    -- Détails
    title TEXT,                    -- "Accordage", "Place des Arts", etc.
    description TEXT,
    notes TEXT,                    -- Notes technicien
    technicien TEXT,               -- "Nicolas", "JP"

    -- Statut
    status TEXT,                   -- "scheduled", "completed", "cancelled"
    is_personal_event BOOLEAN DEFAULT false,  -- Événement personnel (pas de client)

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    synced_from_gazelle_at TIMESTAMPTZ,

    -- Contraintes
    CHECK (is_personal_event = true OR client_id IS NOT NULL)
);

-- Indexes
CREATE INDEX idx_appt_date ON gazelle_appointments(appointment_date, appointment_time);
CREATE INDEX idx_appt_contact ON gazelle_appointments(contact_id);
CREATE INDEX idx_appt_location ON gazelle_appointments(location_id);
CREATE INDEX idx_appt_tech ON gazelle_appointments(technicien, appointment_date);
```

**⏰ RÈGLE CRITIQUE TIMEZONE:**

> **TOUJOURS** stocker `appointment_time` en **UTC**.
> Conversion Montréal seulement pour affichage.

**Voir:** [SYNC_STRATEGY.md - Solution Timezone UTC](SYNC_STRATEGY.md#-solution-timezone-utc-critique)

**Triple Relation:**

```python
# Rendez-vous COMPLET avec 3 liens
appointment = Appointment(
    external_id="evt_abc123",
    contact_id="con_xxx",    # Rencontrer Jean
    location_id="loc_123",   # Aller à 4520 rue St-Denis (code 1234#)
    client_id="cli_yyy",     # Facturer École XYZ
    appointment_date="2026-01-09",
    appointment_time="12:00:00"  # 🔴 UTC! (07:00 Montréal)
)

# Événement personnel (pas de client)
personal_event = Appointment(
    external_id="evt_def456",
    title="Place des Arts",
    location="Salle Wilfrid-Pelletier",
    is_personal_event=True,
    client_id=None  # OK, car is_personal_event=true
)
```

**Colonnes Critiques:**

| Colonne | Type | Description | Contraintes |
|---------|------|-------------|-------------|
| `appointment_time` | TIME | Heure **UTC** | NOT NULL, stockage pur UTC |
| `contact_id` | TEXT | Qui rencontrer | FK → contacts |
| `location_id` | UUID | Où aller (avec codes!) | FK → locations |
| `is_personal_event` | BOOLEAN | Pas de client/facturation | Si true, client_id peut être NULL |

---

### 5. gazelle_pianos (Instruments)

**Responsabilité:** Instruments suivis.

**🔍 RÈGLE CRITIQUE: IDs Gazelle**

> **Source de Vérité:** Les IDs de pianos DOIVENT TOUJOURS provenir de Gazelle (`ins_xxxxx`).
> **Matching Key:** Le `serialNumber` est la clé primaire pour réconcilier CSV ↔ Gazelle.
> **Voir:** [REGLE_IDS_GAZELLE.md](../../docs/REGLE_IDS_GAZELLE.md)

**Schéma GraphQL Gazelle (Type: PrivatePiano)**

D'après l'exploration du schéma GraphQL Gazelle du 2025-12-30:

```graphql
type PrivatePiano {
    id: String!                    # Format: "ins_xxxxxxxxxxxxx" (ex: "ins_3GqzIOJxFLknZX7g")
    client: PrivateClient          # Relation → Client propriétaire
    make: String                   # Marque (ex: "Steinway", "Yamaha")
    model: String                  # Modèle (ex: "D Hambourg", "U1")
    serialNumber: String           # Numéro de série (🔑 CLÉ DE MATCHING)
    type: String                   # Type (ex: "GRAND", "UPRIGHT")
    year: Int                      # Année de fabrication
    location: String               # Localisation textuelle
    notes: String                  # Notes sur l'instrument
    damppChaserInstalled: Boolean  # Dampp Chaser installé
    damppChaserHumidistatModel: String  # Modèle humidistat
    damppChaserMfgDate: String     # Date fabrication Dampp Chaser
    referenceId: String            # ID référence externe (non utilisé dans nos données)
    tags: [String]                 # Tags (rarement utilisé)
}
```

**Statistiques Réelles (100 premiers pianos - 2025-12-30):**
- **87/100** pianos ont un `serialNumber` (87%)
- **13/100** pianos SANS `serialNumber` (13%)
- **0/100** pianos ont un `referenceId`
- **1/100** piano a des `tags`

**⚠️ IMPLICATION CRITIQUE:**
> **13% des pianos n'ont PAS de serialNumber!**
> → Stratégie de fallback OBLIGATOIRE: matcher par `make` + `location` si `serialNumber` manquant.

**Schéma SQL V6:**
```sql
CREATE TABLE gazelle_pianos (
    -- Identifiant (🔑 TOUJOURS ID GAZELLE)
    external_id TEXT PRIMARY KEY,  -- "ins_xxxxx" depuis Gazelle GraphQL

    -- Relations
    location_id UUID REFERENCES gazelle_locations(id),  -- Où est le piano
    client_id TEXT REFERENCES gazelle_clients(external_id),  -- Propriétaire

    -- Caractéristiques (noms alignés sur GraphQL Gazelle)
    make TEXT,                     -- "Steinway", "Yamaha" (champ GraphQL: make)
    model TEXT,                    -- "D Hambourg", "U1" (champ GraphQL: model)
    serial_number TEXT,            -- Numéro série (champ GraphQL: serialNumber)
    piano_type TEXT,               -- "GRAND", "UPRIGHT" (champ GraphQL: type)
    manufacture_year INTEGER,      -- Année fabrication (champ GraphQL: year)
    location_text TEXT,            -- Localisation textuelle (champ GraphQL: location)
    notes TEXT,                    -- Notes instrument (champ GraphQL: notes)

    -- Dampp Chaser
    dampp_chaser_installed BOOLEAN DEFAULT false,
    dampp_chaser_humidistat_model TEXT,
    dampp_chaser_mfg_date DATE,

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    synced_from_gazelle_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_pianos_location ON gazelle_pianos(location_id);
CREATE INDEX idx_pianos_client ON gazelle_pianos(client_id);
CREATE INDEX idx_pianos_make ON gazelle_pianos(make, model);
CREATE UNIQUE INDEX idx_pianos_serial ON gazelle_pianos(serial_number) WHERE serial_number IS NOT NULL;
```

**Colonnes Critiques:**

| Colonne | Type GraphQL | Type SQL | Description | Règles de Validation |
|---------|--------------|----------|-------------|---------------------|
| `external_id` | `id: String!` | TEXT | **ID Gazelle (source de vérité)** | Format: `^ins_[a-zA-Z0-9]+$`, PRIMARY KEY |
| `serial_number` | `serialNumber: String` | TEXT | **Clé de matching CSV ↔ Gazelle** | UNIQUE (si présent), peut être NULL |
| `make` | `make: String` | TEXT | Marque du piano | Non vide recommandé |
| `model` | `model: String` | TEXT | Modèle | Peut être NULL |
| `location_text` | `location: String` | TEXT | Localisation textuelle dans Gazelle | Différent de `location_id` (relation FK) |

**Stratégie de Matching CSV → Gazelle:**

```python
# 1. Matching primaire par serialNumber (87% des cas)
def match_by_serial(csv_piano: dict, gazelle_pianos: list) -> Optional[str]:
    """Retourne external_id Gazelle si serialNumber match."""
    csv_serial = csv_piano.get('serie', '').strip()
    if not csv_serial:
        return None

    for gz_piano in gazelle_pianos:
        if gz_piano.get('serialNumber', '').strip() == csv_serial:
            return gz_piano['id']  # "ins_xxxxx"
    return None

# 2. Matching secondaire par make + location (13% des cas sans serial)
def match_by_make_location(csv_piano: dict, gazelle_pianos: list) -> Optional[str]:
    """Fallback: matcher par marque + localisation."""
    csv_make = csv_piano.get('marque', '').strip().lower()
    csv_location = csv_piano.get('local', '').strip().lower()

    for gz_piano in gazelle_pianos:
        gz_make = gz_piano.get('make', '').strip().lower()
        gz_location = gz_piano.get('location', '').strip().lower()

        if csv_make == gz_make and csv_location == gz_location:
            return gz_piano['id']  # "ins_xxxxx"
    return None

# 3. Piano non matché → rapport_erreurs.md
def handle_unmatched(csv_piano: dict):
    """Lister dans rapport d'erreurs."""
    error_entry = {
        'serie': csv_piano.get('serie', 'N/A'),
        'marque': csv_piano.get('marque', 'N/A'),
        'local': csv_piano.get('local', 'N/A'),
        'raison': 'Aucun match trouvé dans Gazelle (ni serial ni make+location)'
    }
    return error_entry
```

**Lien Piano → Location (Important!):**

```python
# Piano lié à une Location (pas directement au Client)
location = Location(
    id="loc_123",
    contact_id="con_xxx",
    address="4520 rue St-Denis, App 302"
)

piano = Piano(
    external_id="pia_abc",
    brand="Yamaha",
    model="U1",
    location_id="loc_123",  # Le piano est ICI
    client_id="cli_yyy"     # Mais appartient à ce client
)

# Pourquoi?
# Si le client déménage le piano, on change seulement location_id
# Les codes d'accès restent liés à location, pas au piano
```

---

### 6. gazelle_timeline_entries (Historique)

**Responsabilité:** Historique des interventions.

**Schéma SQL:**
```sql
CREATE TABLE gazelle_timeline_entries (
    -- Identifiant
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE,       -- Si provient de Gazelle

    -- Relations
    client_id TEXT REFERENCES gazelle_clients(external_id),
    piano_external_id TEXT REFERENCES gazelle_pianos(external_id),
    appointment_id TEXT REFERENCES gazelle_appointments(external_id),

    -- Contenu
    entry_date DATE NOT NULL,
    entry_type TEXT NOT NULL,      -- "Accordage", "Réparation", "Estimation"
    summary TEXT NOT NULL,
    details TEXT,
    technician TEXT,

    -- Conditions
    temperature NUMERIC(4, 1),     -- 21.5°C
    humidity NUMERIC(4, 1),        -- 45.0%

    -- Métadonnées
    created_at TIMESTAMPTZ DEFAULT now(),
    synced_from_gazelle_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_timeline_client ON gazelle_timeline_entries(client_id, entry_date DESC);
CREATE INDEX idx_timeline_piano ON gazelle_timeline_entries(piano_external_id, entry_date DESC);
CREATE INDEX idx_timeline_date ON gazelle_timeline_entries(entry_date DESC);
```

---

## 🗄️ Tables Staging (2-Stage Sync)

**Voir:** [SYNC_STRATEGY.md](SYNC_STRATEGY.md) pour détails complets.

### staging_appointments

```sql
CREATE TABLE staging_appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT NOT NULL,
    raw_data JSONB NOT NULL,       -- Données brutes Gazelle
    fetched_at TIMESTAMPTZ NOT NULL,
    sync_status TEXT NOT NULL,     -- 'pending' | 'processed' | 'error'
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX idx_staging_appt_external
ON staging_appointments(external_id, fetched_at);
```

**Principe:** Backup complet JSON avant transformation par Reconciler.

---

## 🔍 Requêtes Courantes

### Récupérer Rendez-vous avec Toutes Relations

```sql
SELECT
    a.external_id,
    a.appointment_date,
    a.appointment_time AT TIME ZONE 'UTC' AT TIME ZONE 'America/Toronto' as time_montreal,

    -- Contact (personne à rencontrer)
    c.first_name,
    c.last_name,
    c.phone as contact_phone,

    -- Location (où aller + codes)
    l.address_line1,
    l.city,
    l.postal_code,
    l.access_code,
    l.dog_name,
    l.parking_notes,

    -- Client (facturation)
    cl.company_name,
    cl.billing_email,

    -- Piano
    p.brand,
    p.model,
    p.piano_type

FROM gazelle_appointments a
LEFT JOIN gazelle_contacts c ON a.contact_id = c.external_id
LEFT JOIN gazelle_locations l ON a.location_id = l.id
LEFT JOIN gazelle_clients cl ON a.client_id = cl.external_id
LEFT JOIN gazelle_pianos p ON a.piano_external_id = p.external_id

WHERE a.appointment_date = '2026-01-09'
  AND a.technicien = 'Nicolas'
ORDER BY a.appointment_time;
```

### Vérifier Codes d'Accès par Quartier

```sql
SELECT
    l.postal_code,
    l.city,
    COUNT(*) as locations_with_code,
    COUNT(l.access_code) as has_code,
    ROUND(COUNT(l.access_code) * 100.0 / COUNT(*), 2) as pct_with_code

FROM gazelle_locations l
GROUP BY l.postal_code, l.city
ORDER BY pct_with_code DESC;
```

---

## 🧪 Tests de Qualité des Données

### Test 1: Contraintes Relationnelles

```python
# tests/integration/test_data_integrity.py
def test_appointments_have_valid_relations():
    """Vérifie que chaque RV a des relations valides."""

    # Récupérer RV avec relations
    appointments = supabase.table('gazelle_appointments')\
        .select('''
            external_id,
            contact:contact_id(external_id),
            location:location_id(id),
            client:client_id(external_id)
        ''')\
        .execute()

    for apt in appointments.data:
        # Si pas événement personnel, doit avoir contact ET location
        if not apt.get('is_personal_event'):
            assert apt['contact'] is not None, f"RV {apt['external_id']} sans contact"
            assert apt['location'] is not None, f"RV {apt['external_id']} sans location"
```

### Test 2: Timezone UTC

```python
def test_appointment_times_are_utc():
    """Vérifie que les heures stockées sont bien en UTC."""

    # Récupérer un RV connu (Tire le Coyote avant 8h)
    apt = supabase.table('gazelle_appointments')\
        .select('appointment_time, title')\
        .ilike('title', '%Tire le Coyote avant 8h%')\
        .single()\
        .execute()

    # L'heure stockée doit être 12:00 (UTC), pas 07:00 (Montréal)
    assert apt.data['appointment_time'] == '12:00:00'
```

---

## 📝 Règles de Nommage

### Conventions Tables

```
gazelle_{entity}          # Tables production
staging_{entity}          # Tables staging
v_{entity}_{purpose}      # Vues SQL
```

### Conventions Colonnes

```
{name}_id        # Clés étrangères (ex: client_id, contact_id)
external_id      # ID provenant de Gazelle (clé primaire)
{name}_at        # Timestamps (ex: created_at, synced_from_gazelle_at)
is_{condition}   # Booléens (ex: is_default, is_personal_event)
{metric}_notes   # Champs texte libres
```

---

## 🔗 Documents Liés

- [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) - Structure modules et Reconciler
- [SYNC_STRATEGY.md](SYNC_STRATEGY.md) - Stratégie sync 2-stages et timezone UTC
- [DISTINCTION_CLIENT_CONTACT.md](/docs/DISTINCTION_CLIENT_CONTACT.md) - Spécification Contact vs Client (V5)
- [GAZELLE_DATA_DICTIONARY.md](/GAZELLE_DATA_DICTIONARY.md) - Schéma source Gazelle (référence)

---

## ✅ Checklist Migration V5 → V6

### Phase 1: Nouvelles Tables
- [ ] Créer `gazelle_contacts`
- [ ] Créer `gazelle_locations`
- [ ] Ajouter colonnes relations à `gazelle_appointments`
- [ ] Créer tables staging

### Phase 2: Migration Données
- [ ] Script migration clients → contacts + clients
- [ ] Extraction codes d'accès → locations
- [ ] Mise à jour liens appointments

### Phase 3: Validation
- [ ] Tests contraintes FK
- [ ] Tests timezone UTC
- [ ] Tests qualité données (codes, téléphones)

---

**Version:** 1.0
**Auteur:** Assistant Gazelle Team
**Prochaine révision:** Après création tables V6

**RAPPEL CRITIQUE:** Toujours stocker `appointment_time` en UTC! Voir [SYNC_STRATEGY.md](SYNC_STRATEGY.md).
