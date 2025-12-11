# 📋 PLAN DE MIGRATION - Assistant Gazelle Web

**Date de création :** 2025-11-24  
**Objectif :** Créer une version 100% web déployable, accessible sans ngrok/Remote Desktop  
**Règle absolue :** Ne rien casser dans la version actuelle basée sur SQL Server local

---

## 🎯 OBJECTIF

Préparer une version 100% web de l'Assistant Gazelle (déployable, accessible sans ngrok/Remote Desktop), **TOUT EN CONSERVANT** la version actuelle fonctionnelle en parallèle.

---

## 📊 ÉTAPE 1 - ANALYSE

### 1. Liste des tables NÉCESSAIRES (seulement)

Basé sur l'analyse de `docs/SCHEMA_DATABASE.md` et `app/assistant_gazelle_v4_secure.py`, voici les tables **ESSENTIELLES** pour le fonctionnement de base :

#### Tables principales (OBLIGATOIRES)

1. **`Clients`**
   - Colonnes : `Id`, `CompanyName`, `FirstName`, `LastName`, `Status`, `Tags`, `DefaultContactId`, `CreatedAt`, `UpdatedAt`
   - Usage : Recherche clients, résumés clients

2. **`Contacts`**
   - Colonnes : `Id`, `ClientId`, `FirstName`, `LastName`
   - Usage : Informations de contact des clients

3. **`Pianos`**
   - Colonnes : `Id`, `ClientId`, `Make`, `Model`, `SerialNumber`, `Type`, `Year`, `Notes`, `Location`
   - Usage : Informations sur les pianos des clients

4. **`Appointments`**
   - Colonnes : `Id`, `ClientId`, `TechnicianId`, `PianoId`, `Description`, `AppointmentStatus`, `EventType`, `StartAt`, `Duration`, `IsAllDay`, `Notes`, `ConfirmedByClient`
   - Usage : Rendez-vous des techniciens, requêtes "mes rv de demain"

5. **`TimelineEntries`**
   - Colonnes : `Id`, `ClientId`, `PianoId`, `InvoiceId`, `EstimateId`, `OccurredAt`, `EntryType`, `Title`, `Details`, `UserId`
   - Usage : Historique complet des clients, résumés intelligents

6. **`Invoices`**
   - Colonnes : `Id`, `ClientId`, `Number`, `Status`, `SubTotal`, `Total`, `Notes`, `CreatedAt`, `DueOn`
   - Usage : Factures (optionnel pour résumés clients)

7. **`InvoiceItems`**
   - Colonnes : `Id`, `InvoiceId`, `PianoId`, `Description`, `Quantity`, `Amount`, `Total`
   - Usage : Lignes de factures (optionnel)

#### Tables optionnelles (pour fonctionnalités avancées)

8. **`Estimates`** (optionnel)
   - Colonnes : `Id`, `Number`, `ClientId`, `PianoId`, `ContactId`, `AssignedToId`, `Status`, `Total`
   - Usage : Devis (peut être omis pour MVP)

#### Tables à RETIRER (superflu pour MVP web)

- ❌ `inv.Products` (inventaire - fonctionnalité séparée)
- ❌ `inv.Inventory` (inventaire - fonctionnalité séparée)
- ❌ `inv.Transactions` (inventaire - fonctionnalité séparée)
- ❌ `PlaceDesArtsRequests` (fonctionnalité spécifique, peut être ajoutée plus tard)
- ❌ `MaintenanceAlerts` (fonctionnalité spécifique)
- ❌ `Feedback` (peut être omis pour MVP)

---

### 2. Correspondance exacte : SQL Server → SQLite

#### Mapping des types de données

| SQL Server | SQLite | Notes |
|------------|--------|-------|
| `NVARCHAR(n)` | `TEXT` | Pas de limite de longueur en SQLite |
| `DATETIME` | `TEXT` (ISO format) ou `INTEGER` (Unix timestamp) | **Recommandation : TEXT avec format ISO 8601** |
| `DATETIMEOFFSET` | `TEXT` (ISO format) | Convertir en ISO 8601 |
| `BIT` | `INTEGER` (0 ou 1) | |
| `INT` | `INTEGER` | |
| `DECIMAL(10,2)` | `REAL` ou `TEXT` | **Recommandation : REAL pour calculs** |
| `UNIQUEIDENTIFIER` | `TEXT` | IDs Gazelle sont des strings |

#### Correspondance des colonnes par table

##### `Clients`
```sql
-- SQL Server
Id NVARCHAR(50)
CompanyName NVARCHAR(255)
FirstName NVARCHAR(255)
LastName NVARCHAR(255)
Status NVARCHAR(50)
Tags NVARCHAR(MAX)
DefaultContactId NVARCHAR(50)
CreatedAt DATETIME
UpdatedAt DATETIME

-- SQLite
Id TEXT PRIMARY KEY
CompanyName TEXT
FirstName TEXT
LastName TEXT
Status TEXT
Tags TEXT
DefaultContactId TEXT
CreatedAt TEXT  -- ISO 8601 format
UpdatedAt TEXT  -- ISO 8601 format
```

##### `Contacts`
```sql
-- SQL Server
Id NVARCHAR(50)
ClientId NVARCHAR(50)
FirstName NVARCHAR(255)
LastName NVARCHAR(255)

-- SQLite
Id TEXT PRIMARY KEY
ClientId TEXT
FirstName TEXT
LastName TEXT
FOREIGN KEY (ClientId) REFERENCES Clients(Id)
```

##### `Pianos`
```sql
-- SQL Server
Id NVARCHAR(50)
ClientId NVARCHAR(50)
Make NVARCHAR(255)
Model NVARCHAR(255)
SerialNumber NVARCHAR(255)
Type NVARCHAR(50)
Year INT
Notes NVARCHAR(MAX)
Location NVARCHAR(255)

-- SQLite
Id TEXT PRIMARY KEY
ClientId TEXT
Make TEXT
Model TEXT
SerialNumber TEXT
Type TEXT
Year INTEGER
Notes TEXT
Location TEXT
FOREIGN KEY (ClientId) REFERENCES Clients(Id)
```

##### `Appointments`
```sql
-- SQL Server
Id NVARCHAR(50)
ClientId NVARCHAR(50)
TechnicianId NVARCHAR(50)
PianoId NVARCHAR(50)
Description NVARCHAR(MAX)
AppointmentStatus NVARCHAR(50)
EventType NVARCHAR(50)
StartAt DATETIME
Duration INT
IsAllDay BIT
Notes NVARCHAR(MAX)
ConfirmedByClient BIT

-- SQLite
Id TEXT PRIMARY KEY
ClientId TEXT
TechnicianId TEXT
PianoId TEXT
Description TEXT
AppointmentStatus TEXT
EventType TEXT
StartAt TEXT  -- ISO 8601 format
Duration INTEGER
IsAllDay INTEGER  -- 0 ou 1
Notes TEXT
ConfirmedByClient INTEGER  -- 0 ou 1
FOREIGN KEY (ClientId) REFERENCES Clients(Id)
FOREIGN KEY (PianoId) REFERENCES Pianos(Id)
```

##### `TimelineEntries`
```sql
-- SQL Server
Id NVARCHAR(50)
ClientId NVARCHAR(50)
PianoId NVARCHAR(50)
InvoiceId NVARCHAR(50)
EstimateId NVARCHAR(50)
OccurredAt DATETIME
EntryType NVARCHAR(50)
Title NVARCHAR(255)
Details NVARCHAR(MAX)
UserId NVARCHAR(50)

-- SQLite
Id TEXT PRIMARY KEY
ClientId TEXT
PianoId TEXT
InvoiceId TEXT
EstimateId TEXT
OccurredAt TEXT  -- ISO 8601 format
EntryType TEXT
Title TEXT
Details TEXT
UserId TEXT
FOREIGN KEY (ClientId) REFERENCES Clients(Id)
FOREIGN KEY (PianoId) REFERENCES Pianos(Id)
```

##### `Invoices`
```sql
-- SQL Server
Id NVARCHAR(50)
ClientId NVARCHAR(50)
Number NVARCHAR(50)
Status NVARCHAR(50)
SubTotal DECIMAL(10,2)
Total DECIMAL(10,2)
Notes NVARCHAR(MAX)
CreatedAt DATETIME
DueOn DATETIME

-- SQLite
Id TEXT PRIMARY KEY
ClientId TEXT
Number TEXT
Status TEXT
SubTotal REAL
Total REAL
Notes TEXT
CreatedAt TEXT  -- ISO 8601 format
DueOn TEXT  -- ISO 8601 format
FOREIGN KEY (ClientId) REFERENCES Clients(Id)
```

##### `InvoiceItems`
```sql
-- SQL Server
Id NVARCHAR(50)
InvoiceId NVARCHAR(50)
PianoId NVARCHAR(50)
Description NVARCHAR(MAX)
Quantity DECIMAL(10,2)
Amount DECIMAL(10,2)
Total DECIMAL(10,2)

-- SQLite
Id TEXT PRIMARY KEY
InvoiceId TEXT
PianoId TEXT
Description TEXT
Quantity REAL
Amount REAL
Total REAL
FOREIGN KEY (InvoiceId) REFERENCES Invoices(Id)
FOREIGN KEY (PianoId) REFERENCES Pianos(Id)
```

---

### 3. Liste des scripts existants réutilisables

#### Scripts d'import via API Gazelle (dans `C:\Genosa\Working`)

⚠️ **RÈGLE ABSOLUE :** Ces scripts sont en production critique et **NE DOIVENT PAS** être modifiés.

**Scripts à analyser (lecture seule) :**

1. **`Import_all_data.py`**
   - Fonction : Import complet depuis l'API Gazelle GraphQL
   - Tables importées : Clients, Contacts, Pianos, Appointments, TimelineEntries, Invoices, InvoiceItems, Estimates
   - Authentification : OAuth2 avec `CLIENT_ID` et `CLIENT_SECRET`
   - Endpoint : `https://gazelleapp.io/graphql/private/`
   - **Réutilisable pour :** Créer `import_gazelle_to_sqlite.py` qui utilise la même logique mais écrit dans SQLite

2. **`timeline.py`** (si existe)
   - Fonction : Import spécifique de la timeline
   - **Réutilisable pour :** Import ciblé de TimelineEntries

3. **`import_confirmed_status.py`** (dans `scripts/`)
   - Fonction : Import rapide du statut de confirmation des rendez-vous
   - **Réutilisable pour :** Mise à jour des rendez-vous

#### Scripts dans le projet actuel (réutilisables)

1. **`app/assistant_gazelle_v4_secure.py`**
   - Classe `GazelleDataManager` : Logique de chargement des données
   - **À adapter :** Créer `SQLiteDataManager` avec même interface

2. **`app/conversational_queries.py`**
   - Classe `ConversationalQueries` : Requêtes SQL pour l'assistant
   - **À adapter :** Modifier les requêtes pour SQLite (syntaxe légèrement différente)

3. **`app/unified_assistant.py`**
   - Classe `UnifiedAssistant` : Logique de l'assistant conversationnel
   - **Réutilisable :** Sans modification majeure (utilise les queries)

4. **`app/gazelle_vector_index.py`**
   - Classe `GazelleVectorIndex` : Indexation vectorielle
   - **Réutilisable :** Sans modification (utilise les données chargées)

---

## 🔄 ÉTAPE 2 - PREMIER IMPORT SÉCURISÉ

### Script à créer : `scripts/import_gazelle_to_sqlite.py`

**Fonctionnalités :**

1. **Authentification OAuth2** (même logique que `C:\Genosa\Working\Import_all_data.py`)
   - Utiliser les mêmes `CLIENT_ID` et `CLIENT_SECRET`
   - Gérer le refresh token automatiquement

2. **Création de la DB SQLite**
   - Créer `data/gazelle_web.db` si n'existe pas
   - Créer les tables avec le schéma défini ci-dessus

3. **Import contrôlé**
   - Limiter à 100 clients max pour test initial
   - Importer les données associées (contacts, pianos, appointments, timeline, invoices)
   - Gérer les erreurs gracieusement

4. **Validation**
   - Vérifier que les données sont cohérentes
   - Afficher un résumé de l'import

**Résultat attendu :**
- Fichier `data/gazelle_web.db` fonctionnel
- Tables créées avec bon schéma
- Données de test valides (100 clients + données associées)

---

## 🏗️ ÉTAPE 3 - DUPLICATION MINIMALE DU BACKEND

### Fichiers à créer dans `assistant-gazelle-web/app/`

1. **`sqlite_data_manager.py`**
   - Adaptation de `GazelleDataManager` pour SQLite
   - Même interface publique
   - Utilise `sqlite3` ou `sqlalchemy`

2. **`assistant_web.py`**
   - Copie adaptée de `assistant_gazelle_v4_secure.py`
   - Remplace `GazelleDataManager` par `SQLiteDataManager`
   - Garde tous les endpoints `/api/assistant`, `/api/search`, etc.
   - Configuration SQLite : `sqlite:///data/gazelle_web.db`

3. **`run_web.py`** (à la racine de `assistant-gazelle-web/`)
   - Point d'entrée pour lancer le serveur Flask
   - Configuration minimale
   - Port différent (ex: 5001) pour éviter conflit avec V4

**Résultat attendu :**
- `python run_web.py` démarre le serveur
- `/health` retourne `OK`
- Connexion à SQLite fonctionnelle

---

## 🖥️ ÉTAPE 4 - CONNEXION À L'INTERFACE UNIFIÉE

### Modifications minimales

1. **`templates/assistant.html`**
   - Aucune modification nécessaire si les endpoints sont identiques
   - Tester que les requêtes fonctionnent

2. **Tests à effectuer :**
   - ✅ "mes rv de demain"
   - ✅ "client daniel markwell"
   - ✅ "clients de nicolas"
   - ✅ Résumé client complet

**Résultat attendu :**
- Même comportement qu'avant
- Données alimentées par SQLite local
- Interface identique

---

## 🚀 ÉTAPE 5 - PRÉPARATION DÉPLOIEMENT WEB

### Fichier à créer : `DEPLOYMENT.md`

**Options de déploiement :**

1. **Render** (recommandé pour simplicité)
2. **Railway** (alternative moderne)
3. **VPS** (plus de contrôle)

**Contenu :**
- Procédure de déploiement
- Variables d'environnement nécessaires
- Commandes de build
- Configuration de la base SQLite (fichier ou volume persistant)

---

## 📝 NOTES IMPORTANTES

### Règles absolues

1. ✅ **Ne rien casser** dans la version actuelle
2. ✅ **Aucun fichier existant** ne doit être supprimé
3. ✅ **Tout nouveau travail** dans `/assistant-gazelle-web/`
4. ✅ **Version actuelle** continue de fonctionner pendant la migration
5. ✅ **Notifier Slack** à chaque grande étape

### Priorité

**Tant que la version WEB n'est pas validée à 100%, la V4 locale reste la version officielle de production.**

---

## ✅ PROCHAINES ÉTAPES

1. ✅ Créer `/assistant-gazelle-web/` (FAIT)
2. ✅ Créer `MIGRATION_PLAN.md` (FAIT)
3. ⏳ Créer `scripts/import_gazelle_to_sqlite.py` (ÉTAPE 2)
4. ⏳ Créer `app/sqlite_data_manager.py` (ÉTAPE 3)
5. ⏳ Créer `app/assistant_web.py` (ÉTAPE 3)
6. ⏳ Créer `run_web.py` (ÉTAPE 3)
7. ⏳ Tester connexion interface (ÉTAPE 4)
8. ⏳ Créer `DEPLOYMENT.md` (ÉTAPE 5)

---

**Dernière mise à jour :** 2025-11-24  
**Statut :** Étape 1 terminée - Prêt pour Étape 2

