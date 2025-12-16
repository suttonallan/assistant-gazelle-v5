# 🗄️ Migration des Schémas BDD Centraux - V5

**Date:** 2025-12-11
**Objectif:** Créer les tables maîtresses (clients, pianos, appointments, invoices) dans Supabase pour remplacer SQL Server

---

## ✅ Travail Réalisé

### 1. Scripts de Migration SQL

#### **Migration 003 - Schémas Centraux** ✅ CRÉÉ
- **Fichier:** [scripts/migrations/003_create_central_schemas.sql](scripts/migrations/003_create_central_schemas.sql)
- **Contenu:**
  - 📋 Table `clients` - Clients et prospects (avec `gazelle_id` pour sync)
  - 🎹 Table `pianos` - Pianos référencés (lié à `clients`)
  - 📅 Table `appointments` - Rendez-vous techniciens (lié à `clients` + `pianos`)
  - 🧾 Table `invoices` - Factures clients
  - 📝 Table `invoice_items` - Lignes de facture
  - 🔍 2 vues SQL : `v_appointments_full`, `v_invoices_with_totals`
  - ⚙️ Triggers auto-update `updated_at`

#### **Migration 002 - Colonnes V4 Inventaire** ✅ CRÉÉ
- **Fichier:** [scripts/migrations/002_add_v4_columns_to_produits.sql](scripts/migrations/002_add_v4_columns_to_produits.sql)
- **Contenu:**
  - Ajoute 6 colonnes à `produits_catalogue`:
    - `has_commission`, `commission_rate`
    - `variant_group`, `variant_label`
    - `display_order`, `is_active`

---

### 2. Script de Vérification

#### **`initial_schema_creator.py`** ✅ CRÉÉ
- **Fichier:** [scripts/data/initial_schema_creator.py](scripts/data/initial_schema_creator.py)
- **Usage:**
  ```bash
  python scripts/data/initial_schema_creator.py --check   # Vérifier tables
  python scripts/data/initial_schema_creator.py --create  # Guide création
  ```

- **Fonctionnalités:**
  - ✅ Vérifie les 8 tables attendues (clients, pianos, appointments, invoices, invoice_items, produits_catalogue, inventaire_techniciens, transactions_inventaire)
  - ✅ Détecte les colonnes manquantes par table
  - ✅ Affiche un rapport détaillé + prochaines étapes
  - ✅ Guide pour exécuter les migrations dans Supabase Dashboard

---

### 3. Utilitaire d'Import Gazelle → Supabase

#### **`importer_utils.py`** ✅ CRÉÉ
- **Fichier:** [scripts/data/importer_utils.py](scripts/data/importer_utils.py)
- **Classe principale:** `GazelleImporter`

**Fonctionnalités:**
- 📄 Lecture CSV/JSON (exports Gazelle)
- 🔄 Mapping automatique colonnes Gazelle → Supabase
- 🔗 Résolution des clés étrangères (`gazelle_id` → UUID Supabase)
- 📦 Import par lots (batch de 100 lignes)
- ⏱️ Timestamp de synchronisation (`last_sync_gazelle`)

**Exemple d'utilisation:**
```python
from scripts.data.importer_utils import GazelleImporter

importer = GazelleImporter()
importer.import_clients_from_csv('data/export_gazelle_clients.csv')
importer.import_pianos_from_csv('data/export_gazelle_pianos.csv')
importer.import_appointments_from_csv('data/export_gazelle_appointments.csv')
```

**Mapping des colonnes:**
```python
# Clients
'GazelleClientId' → 'gazelle_id'
'LastName' → 'nom'
'FirstName' → 'prenom'
'Email' → 'email'
...

# Pianos
'GazellePianoId' → 'gazelle_id'
'GazelleClientId' → résolu en 'client_id' (UUID Supabase)
'SerialNumber' → 'numero_serie'
...

# Appointments
'GazelleAppointmentId' → 'gazelle_id'
'GazelleClientId' → résolu en 'client_id'
'GazellePianoId' → résolu en 'piano_id'
...
```

---

## 📊 État Actuel des Schémas

**Résultat de la vérification (`--check`) :**

```
✅ Tables existantes: 3/8
   - produits_catalogue
   - inventaire_techniciens
   - transactions_inventaire

❌ Tables manquantes: 5
   - clients
   - pianos
   - appointments
   - invoices
   - invoice_items

⚠️  Tables incomplètes: 1
   - produits_catalogue: is_active (+ 5 autres colonnes V4)
```

---

## 🚀 Prochaines Étapes - Guide d'Exécution

### **Étape 1: Créer les Tables Centrales**

1. **Ouvrir Supabase Dashboard:**
   - URL: https://beblgzvmjqkcillmcavk.supabase.com
   - Aller dans **SQL Editor**

2. **Exécuter Migration 003:**
   - Copier le contenu complet de [scripts/migrations/003_create_central_schemas.sql](scripts/migrations/003_create_central_schemas.sql)
   - Coller dans SQL Editor
   - Cliquer **Run**

3. **Vérifier:**
   ```bash
   python scripts/data/initial_schema_creator.py --check
   ```
   - Devrait afficher 8/8 tables existantes

---

### **Étape 2: Compléter Produits Catalogue**

1. **Exécuter Migration 002:**
   - Copier [scripts/migrations/002_add_v4_columns_to_produits.sql](scripts/migrations/002_add_v4_columns_to_produits.sql)
   - Coller dans SQL Editor
   - Cliquer **Run**

2. **Vérifier:**
   ```bash
   python scripts/run_migration.py scripts/migrations/002_add_v4_columns_to_produits.sql
   ```
   - Devrait afficher "✅ Toutes les colonnes V4 sont présentes!"

---

### **Étape 3: Importer les Données Historiques**

**Pré-requis:**
- Exporter les données depuis Gazelle au format CSV ou JSON
- Respecter les noms de colonnes du mapping (voir `importer_utils.py`)

**Ordre d'import recommandé:**
1. **Clients** (d'abord car référencés par pianos/appointments)
2. **Pianos** (nécessite clients)
3. **Appointments** (nécessite clients + pianos)
4. **Invoices** (optionnel, nécessite clients + appointments)

**Commandes:**
```python
from scripts.data.importer_utils import GazelleImporter

importer = GazelleImporter()

# 1. Clients
importer.import_clients_from_csv('data/export_clients_gazelle.csv')
# ou JSON:
# importer.import_from_json('data/clients.json', 'clients')

# 2. Pianos
importer.import_pianos_from_csv('data/export_pianos_gazelle.csv')

# 3. Appointments
importer.import_appointments_from_csv('data/export_appointments_gazelle.csv')
```

---

## 🔧 Adaptation pour Autres Modules

### **Migration Briefings**

Une fois les schémas centraux créés, le module Briefings pourra :
1. Utiliser `SupabaseStorage()` au lieu de SQL Server
2. Requêter les clients via `storage.get_data('clients')`
3. Requêter les appointments via `storage.get_data('appointments')`
4. Utiliser la vue `v_appointments_full` pour données enrichies

**Exemple:**
```python
from core.supabase_storage import SupabaseStorage

storage = SupabaseStorage()

# Récupérer les RDV non confirmés (pour alertes)
rdv = storage.get_data(
    'appointments',
    filters={
        'statut': 'planifié',
        'date_debut': f'gte.{date_debut}'
    }
)

# Ou via vue enrichie
rdv_full = storage.client.table('v_appointments_full') \
    .select('*') \
    .eq('statut', 'planifié') \
    .gte('date_debut', date_debut) \
    .execute()
```

---

### **Migration Alertes**

Module Alertes pourra :
1. Lire `appointments` pour détecter RDV non confirmés
2. Utiliser `SlackNotifier` (déjà créé pour inventaire)
3. Envoyer des notifications aux techniciens

**Exemple:**
```python
from core.slack_notifier import SlackNotifier
from core.supabase_storage import SupabaseStorage

storage = SupabaseStorage()

# Détecter RDV non confirmés J-2
rdv_urgents = storage.get_data(
    'appointments',
    filters={'statut': 'planifié', 'date_debut': f'eq.{demain}'}
)

for rdv in rdv_urgents:
    SlackNotifier.notify_technician(
        rdv['technicien_nom'],
        f"⚠️ RDV non confirmé demain: {rdv['titre']} chez {rdv['client_nom']}"
    )
```

---

## 📚 Références Techniques

### **Architecture de Base**
- **Tables maîtresses:** clients, pianos, appointments, invoices, invoice_items
- **Tables inventaire:** produits_catalogue, inventaire_techniciens, transactions_inventaire
- **Clé de synchronisation:** `gazelle_id` (TEXT UNIQUE) dans chaque table
- **Foreign keys:** Toutes les relations via UUID (pas de gazelle_id)

### **Colonnes Standard par Table**
Toutes les tables ont :
- `id` (UUID, PK)
- `created_at` (TIMESTAMPTZ)
- `updated_at` (TIMESTAMPTZ, auto-trigger)
- `gazelle_id` (TEXT UNIQUE, optionnel)
- `last_sync_gazelle` (TIMESTAMPTZ, optionnel)

### **Vues SQL Disponibles**
1. **`v_appointments_full`** - Rendez-vous avec infos client/piano
2. **`v_invoices_with_totals`** - Factures avec totaux et client

---

## 🎯 Résumé

**✅ Schémas SQL centraux créés** - Prêts pour migration modules
**✅ Script de vérification opérationnel** - `initial_schema_creator.py`
**✅ Utilitaire d'import CSV/JSON** - `importer_utils.py`
**✅ Mapping Gazelle → Supabase défini**
**⚠️ Actions requises:**
1. Exécuter migrations 002 et 003 dans Supabase SQL Editor
2. Exporter données historiques depuis Gazelle
3. Importer avec `GazelleImporter`

---

**📌 Statut:** Infrastructure BDD prête pour migration Briefings + Alertes
