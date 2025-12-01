# PLAN DE MIGRATION V4 → V5 (SQLite + API Gazelle)

**Date**: 2025-01-27  
**Objectif**: Système autonome sur Mac synchronisé directement avec l'API Gazelle

---

## 1. RÉSUMÉ : Système V4 (SQL Server)

### Architecture V4
- **Base de données**: SQL Server avec IDs string (format: `cli_xxx`, `usr_xxx`, `pno_xxx`)
- **Synchronisation**: Export CSV manuel → Import dans SQL Server
- **Tables principales**:
  - Clients (avec Contacts liés)
  - Pianos (liés aux Clients)
  - MaintenanceAlerts (alertes d'humidité/maintenance)
  - Invoices/InvoiceItems (facturation)
  - Products/Inventory (inventaire)
  - Appointments (rendez-vous)
  - TimelineEntries (historique)

### Problèmes V4
- Dépendance à SQL Server (Windows)
- IDs string complexes
- Synchronisation manuelle (CSV)
- Pas d'accès direct à l'API

---

## 2. SCHÉMA SQLITE V5

### Schéma complet proposé (`schema.sql`)

```sql
-- ============================================
-- SCHEMA SQLite V5 - Assistant Gazelle
-- ============================================

-- TABLE: Clients
CREATE TABLE Clients (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    CompanyName TEXT NOT NULL,
    FirstName TEXT,
    LastName TEXT,
    Status TEXT NOT NULL DEFAULT 'ACTIVE',
    Tags TEXT,
    DefaultContactId INTEGER,
    Email TEXT,
    Phone TEXT,
    Address TEXT,
    CreatedAt TEXT,
    UpdatedAt TEXT,
    -- Mapping V4 → V5
    ExternalId TEXT UNIQUE  -- ID Gazelle original (cli_xxx)
);

-- TABLE: Contacts
CREATE TABLE Contacts (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientId INTEGER NOT NULL,
    FirstName TEXT,
    LastName TEXT,
    Email TEXT,
    Phone TEXT,
    ExternalId TEXT UNIQUE,  -- con_xxx
    FOREIGN KEY (ClientId) REFERENCES Clients(Id) ON DELETE CASCADE
);

-- TABLE: Pianos
CREATE TABLE Pianos (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientId INTEGER NOT NULL,
    Make TEXT NOT NULL,
    Model TEXT,
    SerialNumber TEXT,
    Type TEXT,
    Year INTEGER,
    Location TEXT,
    Notes TEXT,
    ExternalId TEXT UNIQUE,  -- pno_xxx
    FOREIGN KEY (ClientId) REFERENCES Clients(Id) ON DELETE CASCADE
);

-- TABLE: MaintenanceAlerts
CREATE TABLE MaintenanceAlerts (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientId INTEGER NOT NULL,
    PianoId INTEGER,
    DateObservation TEXT NOT NULL,
    Location TEXT,
    AlertType TEXT NOT NULL,
    Description TEXT,
    IsResolved INTEGER DEFAULT 0,
    ResolvedDate TEXT,
    Archived INTEGER DEFAULT 0,
    Notes TEXT,
    RecipientEmail TEXT,
    CreatedBy TEXT,
    CreatedAt TEXT,
    UpdatedAt TEXT,
    ExternalId TEXT UNIQUE,  -- ID Gazelle original
    FOREIGN KEY (ClientId) REFERENCES Clients(Id),
    FOREIGN KEY (PianoId) REFERENCES Pianos(Id) ON DELETE SET NULL
);

-- TABLE: Products (Inventaire)
CREATE TABLE Products (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Sku TEXT UNIQUE,
    Description TEXT,
    UnitCost REAL DEFAULT 0,
    RetailPrice REAL DEFAULT 0,
    Active INTEGER DEFAULT 1,
    CreatedAt TEXT,
    ExternalId TEXT UNIQUE  -- ID Gazelle original
);

-- TABLE: Inventory (Stock par technicien)
CREATE TABLE Inventory (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ProductId INTEGER NOT NULL,
    TechnicianId TEXT NOT NULL,  -- usr_xxx (reste TEXT)
    Quantity INTEGER DEFAULT 0,
    ReorderThreshold INTEGER DEFAULT 0,
    UpdatedAt TEXT,
    FOREIGN KEY (ProductId) REFERENCES Products(Id) ON DELETE CASCADE
);

-- TABLE: Invoices (Facturation)
CREATE TABLE Invoices (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientId INTEGER NOT NULL,
    Number TEXT NOT NULL,
    InvoiceDate TEXT NOT NULL,
    Status TEXT NOT NULL DEFAULT 'UNPAID',
    SubTotal REAL NOT NULL DEFAULT 0,
    Total REAL NOT NULL DEFAULT 0,
    Notes TEXT,
    CreatedAt TEXT,
    DueOn TEXT,
    ExternalId TEXT UNIQUE,  -- ID Gazelle original
    FOREIGN KEY (ClientId) REFERENCES Clients(Id) ON DELETE CASCADE
);

-- TABLE: InvoiceItems
CREATE TABLE InvoiceItems (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    InvoiceId INTEGER NOT NULL,
    PianoId INTEGER,
    Description TEXT NOT NULL,
    Quantity REAL NOT NULL DEFAULT 1,
    Amount REAL,
    UnitPrice REAL,
    Total REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (InvoiceId) REFERENCES Invoices(Id) ON DELETE CASCADE,
    FOREIGN KEY (PianoId) REFERENCES Pianos(Id) ON DELETE SET NULL
);

-- TABLE: Appointments
CREATE TABLE Appointments (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientId INTEGER NOT NULL,
    TechnicianId TEXT NOT NULL,  -- usr_xxx
    PianoId INTEGER,
    Description TEXT,
    AppointmentStatus TEXT NOT NULL DEFAULT 'ACTIVE',
    EventType TEXT NOT NULL DEFAULT 'APPOINTMENT',
    StartAt TEXT NOT NULL,
    Duration INTEGER,
    IsAllDay INTEGER DEFAULT 0,
    Notes TEXT,
    ConfirmedByClient INTEGER DEFAULT 0,
    ExternalId TEXT UNIQUE,
    FOREIGN KEY (ClientId) REFERENCES Clients(Id) ON DELETE CASCADE,
    FOREIGN KEY (PianoId) REFERENCES Pianos(Id) ON DELETE SET NULL
);

-- TABLE: TimelineEntries
CREATE TABLE TimelineEntries (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientId INTEGER NOT NULL,
    PianoId INTEGER,
    InvoiceId INTEGER,
    EstimateId INTEGER,
    OccurredAt TEXT NOT NULL,
    EntryType TEXT NOT NULL,
    Title TEXT,
    Details TEXT,
    UserId TEXT,  -- usr_xxx
    ExternalId TEXT UNIQUE,
    FOREIGN KEY (ClientId) REFERENCES Clients(Id) ON DELETE CASCADE,
    FOREIGN KEY (PianoId) REFERENCES Pianos(Id) ON DELETE SET NULL
);

-- INDEXES pour performance
CREATE INDEX idx_clients_externalid ON Clients(ExternalId);
CREATE INDEX idx_clients_status ON Clients(Status);
CREATE INDEX idx_maintenancealerts_clientid ON MaintenanceAlerts(ClientId);
CREATE INDEX idx_maintenancealerts_isresolved ON MaintenanceAlerts(IsResolved);
CREATE INDEX idx_invoices_clientid ON Invoices(ClientId);
CREATE INDEX idx_invoices_status ON Invoices(Status);
CREATE INDEX idx_pianos_clientid ON Pianos(ClientId);
CREATE INDEX idx_appointments_clientid ON Appointments(ClientId);
CREATE INDEX idx_appointments_startat ON Appointments(StartAt);
```

---

## 3. MODULES À CRÉER (ordre de priorité)

### Module 1: `gazelle_api_client.py` ⭐ PRIORITÉ 1
**Rôle**: Client API pour communiquer avec Gazelle  
**Fonctionnalités**:
- Authentification (API key/token)
- GET/POST/PUT/DELETE vers endpoints Gazelle
- Gestion des erreurs et retry
- Cache des réponses

**Dépendances**: `requests`, `python-dotenv`

---

### Module 2: `sync_gazelle_to_sqlite.py` ⭐ PRIORITÉ 1
**Rôle**: Synchronisation bidirectionnelle API → SQLite  
**Fonctionnalités**:
- Pull: Récupérer données depuis API Gazelle
- Push: Envoyer modifications locales vers API
- Mapping IDs string (Gazelle) ↔ IDs entiers (SQLite)
- Détection des conflits
- Logs de synchronisation

**Dépendances**: `gazelle_api_client.py`, `sqlite3`

---

### Module 3: `migration_v4_to_v5.py` ⭐ PRIORITÉ 2
**Rôle**: Migration unique des données CSV existantes  
**Fonctionnalités**:
- Importer tous les CSV V4
- Créer mappings ExternalId → Id
- Valider l'intégrité des données
- Générer rapport de migration

**Dépendances**: `import_sqlite_data.py` (amélioré)

---

### Module 4: `alert_system.py` ⭐ PRIORITÉ 2
**Rôle**: Système d'alertes de maintenance (amélioration de `humidity_alert_system_MAC.py`)  
**Fonctionnalités**:
- Vérification automatique des alertes
- Notifications (email/console)
- Résolution d'alertes
- Historique

**Dépendances**: `sqlite3`, `gazelle_api_client.py` (pour push)

---

### Module 5: `inventory_manager.py` ⭐ PRIORITÉ 3
**Rôle**: Gestion de l'inventaire  
**Fonctionnalités**:
- Suivi des stocks par technicien
- Alertes de réapprovisionnement
- Synchronisation avec API

**Dépendances**: `gazelle_api_client.py`, `sqlite3`

---

### Module 6: `invoice_manager.py` ⭐ PRIORITÉ 3
**Rôle**: Gestion des factures  
**Fonctionnalités**:
- Création/modification de factures
- Calculs automatiques
- Synchronisation avec API

**Dépendances**: `gazelle_api_client.py`, `sqlite3`

---

### Module 7: `appointment_scheduler.py` ⭐ PRIORITÉ 3
**Rôle**: Gestion des rendez-vous  
**Fonctionnalités**:
- Création/modification de rendez-vous
- Calendrier
- Synchronisation avec API

**Dépendances**: `gazelle_api_client.py`, `sqlite3`

---

## 4. ORDRE DE MIGRATION

### Phase 1: Infrastructure (Semaine 1)
1. **Module 1** (`gazelle_api_client.py`)
   - Pourquoi: Base de tout le système
   - Tester avec endpoints simples (GET clients)

2. **Module 2** (`sync_gazelle_to_sqlite.py`) - Partie Pull
   - Pourquoi: Récupérer les données actuelles depuis API
   - Tester avec Clients d'abord

### Phase 2: Migration des données (Semaine 1-2)
3. **Module 3** (`migration_v4_to_v5.py`)
   - Pourquoi: Migrer les données CSV existantes
   - Créer les mappings ExternalId

### Phase 3: Fonctionnalités essentielles (Semaine 2)
4. **Module 4** (`alert_system.py`)
   - Pourquoi: Système critique pour le business
   - Améliorer `humidity_alert_system_MAC.py`

5. **Module 2** - Partie Push
   - Pourquoi: Permettre les modifications locales

### Phase 4: Fonctionnalités avancées (Semaine 3+)
6. Modules 5, 6, 7 selon besoins

---

## 5. SCRIPT D'IMPORT GAZELLE

### Adaptation de `Import_daily_update.py` → `sync_gazelle_to_sqlite.py`

#### Changements principaux:

1. **Source de données**:
   - ❌ Ancien: Lecture CSV local
   - ✅ Nouveau: Appels API Gazelle

2. **Mapping des IDs**:
   - ❌ Ancien: Mapping CSV → SQL Server (IDs string)
   - ✅ Nouveau: Mapping API (IDs string) → SQLite (IDs entiers)
   - Utiliser colonne `ExternalId` pour garder référence

3. **Structure**:
```python
# Ancien (Import_daily_update.py)
def import_from_csv(csv_file):
    # Lit CSV
    # Insère dans SQL Server

# Nouveau (sync_gazelle_to_sqlite.py)
def sync_from_api():
    # 1. GET depuis API Gazelle
    data = api_client.get_clients()
    # 2. Mapper ExternalId → Id local
    # 3. INSERT/UPDATE dans SQLite
    # 4. Gérer conflits
```

4. **Fonctions à adapter**:
   - `import_clients()` → `sync_clients_from_api()`
   - `import_maintenance_alerts()` → `sync_alerts_from_api()`
   - `import_invoices()` → `sync_invoices_from_api()`
   - Ajouter: `sync_to_api()` pour push

5. **Gestion des conflits**:
   - Timestamp `UpdatedAt` pour détecter modifications
   - Stratégie: Last-Write-Wins ou merge manuel

6. **Configuration**:
   - Fichier `.env` pour API key
   - URL base API
   - Intervalle de synchronisation

---

## 6. ARCHITECTURE FINALE

```
assistant-gazelle-v5/
├── config/
│   └── .env                    # API keys, URLs
├── modules/
│   ├── gazelle_api_client.py   # Client API
│   ├── sync_gazelle_to_sqlite.py
│   ├── alert_system.py
│   ├── inventory_manager.py
│   └── ...
├── data/
│   └── db_test_v5.sqlite       # Base SQLite locale
├── scripts/
│   ├── migration_v4_to_v5.py
│   └── import_sqlite_data.py   # (legacy, pour migration initiale)
└── main.py                      # Point d'entrée principal
```

---

## 7. POINTS D'ATTENTION

### IDs et Mapping
- **Problème**: Gazelle utilise IDs string (`cli_xxx`), SQLite utilise INTEGER
- **Solution**: Colonne `ExternalId` dans chaque table pour mapping
- **Table de mapping**: `external_id_mapping` (optionnel, pour cache)

### Synchronisation
- **Fréquence**: Toutes les heures (configurable)
- **Mode**: Pull d'abord, Push après validation
- **Conflits**: Dernière modification gagne (ou merge manuel)

### Performance
- Index sur `ExternalId` pour recherches rapides
- Batch inserts pour grandes quantités
- Cache API pour réduire appels

---

## 8. PROCHAINES ÉTAPES IMMÉDIATES

1. ✅ Créer `gazelle_api_client.py` avec authentification
2. ✅ Tester connexion API avec endpoint simple
3. ✅ Créer `sync_gazelle_to_sqlite.py` - Pull Clients
4. ✅ Valider synchronisation Clients
5. ⏭️ Étendre à autres tables (MaintenanceAlerts, etc.)

---

**Note**: Ce plan est évolutif. Commencer simple (Clients + MaintenanceAlerts), puis étendre progressivement.


